"""
每日交易数据推送模块

功能：
- 每个交易日 16:00 推送当日数据汇总
- 包含期货收盘价、涨跌幅、持仓变化
- 包含现货价格、仓单数据（如有）
- 计算基差等关键指标

重要原则：禁止推送过期数据误导用户！
"""

from datetime import datetime, date, timedelta
from typing import Optional
from src.storage.database import SessionLocal
from src.storage.crud import get_futures_quotes, get_spot_prices, get_futures_receipts
from src.collectors.futures_collector import SUPPORTED_SYMBOLS
from src.notification.feishu import send_feishu_message
from src.utils.logger import log


def _is_data_today(data_date_str: str) -> bool:
    """检查数据日期是否为今天"""
    try:
        data_date = datetime.strptime(data_date_str, "%Y-%m-%d").date()
        return data_date == date.today()
    except:
        return False


def _is_data_fresh(data_date_str: str, max_days: int = 1) -> bool:
    """检查数据是否新鲜（不超过指定天数）"""
    try:
        data_date = datetime.strptime(data_date_str, "%Y-%m-%d").date()
        return (date.today() - data_date).days <= max_days
    except:
        return False


def get_latest_futures_data(symbol: str = "JD2609") -> Optional[dict]:
    """获取最新期货数据（严格验证日期）"""
    db = SessionLocal()
    try:
        quotes = get_futures_quotes(db, symbol, limit=2)
        if not quotes:
            log.error(f"[DailyReport] No futures data found for {symbol}")
            return None
        
        latest = quotes[0]
        data_date = latest.datetime.date()
        today = date.today()
        
        if data_date != today:
            days_old = (today - data_date).days
            log.error(f"[DATA STALE] {symbol} latest data is {days_old} days old ({data_date}), cannot use!")
            return None
        
        prev = quotes[1] if len(quotes) > 1 else None
        
        change_pct = 0.0
        if prev and prev.close:
            change_pct = ((latest.close - prev.close) / prev.close) * 100
        
        oi_change = 0
        if prev and prev.open_interest:
            oi_change = latest.open_interest - prev.open_interest
        
        return {
            "symbol": latest.symbol,
            "date": latest.datetime.strftime("%Y-%m-%d"),
            "close": latest.close,
            "change_pct": round(change_pct, 2),
            "open_interest": latest.open_interest,
            "oi_change": oi_change,
            "volume": latest.volume
        }
    finally:
        db.close()


def get_latest_spot_data(category: str = "egg") -> Optional[dict]:
    """获取最新现货数据"""
    db = SessionLocal()
    try:
        prices = get_spot_prices(db, category=category, limit=1)
        if not prices:
            return None
        
        latest = prices[0]
        return {
            "category": latest.category,
            "date": latest.date.strftime("%Y-%m-%d"),
            "price": latest.price,
            "region": latest.region,
            "unit": latest.unit
        }
    finally:
        db.close()


def get_all_spot_prices() -> dict:
    """获取所有现货价格（鸡蛋、玉米、豆粕）"""
    result = {}
    
    # 鸡蛋价格
    egg_data = get_latest_spot_data("egg")
    if egg_data:
        result["egg"] = egg_data
    
    # 玉米价格
    corn_data = get_latest_spot_data("corn")
    if corn_data:
        result["corn"] = corn_data
    
    # 豆粕价格
    soymeal_data = get_latest_spot_data("soymeal")
    if soymeal_data:
        result["soymeal"] = soymeal_data
    
    # 淘汰禽价格
    eliminate_data = get_latest_spot_data("eliminate")
    if eliminate_data:
        result["eliminate"] = eliminate_data
    
    return result


def get_latest_receipt_data(symbol: str = "jd") -> Optional[dict]:
    """获取最新仓单数据"""
    db = SessionLocal()
    try:
        receipts = get_futures_receipts(db, symbol, limit=1)
        if not receipts:
            return None
        
        latest = receipts[0]
        return {
            "date": latest.date.strftime("%Y-%m-%d"),
            "receipt_qty": latest.receipt_qty,
            "change": latest.change
        }
    finally:
        db.close()


def calculate_basis(futures_close: float, spot_price: float) -> float:
    """计算基差（现货 - 期货）"""
    return spot_price - futures_close


def format_daily_report(futures_data: dict, spot_prices: Optional[dict], receipt_data: Optional[dict]) -> str:
    """格式化每日数据报告"""
    lines = []
    
    # 期货数据
    change_str = f"+{futures_data['change_pct']}" if futures_data['change_pct'] >= 0 else str(futures_data['change_pct'])
    oi_change_str = f"+{futures_data['oi_change']}" if futures_data['oi_change'] >= 0 else str(futures_data['oi_change'])
    
    lines.append(f"**期货收盘：{futures_data['close']} ({change_str}%)**")
    lines.append(f"持仓：{futures_data['open_interest']}手 ({oi_change_str})")
    lines.append(f"成交量：{futures_data['volume']}手")
    lines.append("")
    
    # 现货数据 - 鸡蛋
    if spot_prices and "egg" in spot_prices:
        egg_data = spot_prices["egg"]
        lines.append(f"**鸡蛋现货：{egg_data['region']} {egg_data['price']}{egg_data['unit']}**")
        
        basis = calculate_basis(futures_data['close'], egg_data['price'])
        basis_str = f"+{basis:.0f}" if basis >= 0 else f"{basis:.0f}"
        lines.append(f"基差：{basis_str}元 (现货-期货)")
    else:
        lines.append("**鸡蛋现货：暂无数据**")
    lines.append("")
    
    # 现货数据 - 玉米
    if spot_prices and "corn" in spot_prices:
        corn_data = spot_prices["corn"]
        lines.append(f"**玉米现货：{corn_data['region']} {corn_data['price']}{corn_data['unit']}**")
    else:
        lines.append("**玉米现货：暂无数据**")
    lines.append("")
    
    # 现货数据 - 豆粕
    if spot_prices and "soymeal" in spot_prices:
        soymeal_data = spot_prices["soymeal"]
        lines.append(f"**豆粕现货：{soymeal_data['region']} {soymeal_data['price']}{soymeal_data['unit']}**")
    else:
        lines.append("**豆粕现货：暂无数据**")
    lines.append("")
    
    # 现货数据 - 淘汰禽
    if spot_prices and "eliminate" in spot_prices:
        eliminate_data = spot_prices["eliminate"]
        lines.append(f"**淘汰禽现货：{eliminate_data['region']} {eliminate_data['price']}{eliminate_data['unit']}**")
    else:
        lines.append("**淘汰禽现货：暂无数据**")
    lines.append("")
    
    # 仓单数据
    if receipt_data:
        change_str = f"+{receipt_data['change']}" if receipt_data['change'] >= 0 else str(receipt_data['change'])
        lines.append(f"**仓单数据：{receipt_data['receipt_qty']}张 ({change_str})**")
    else:
        lines.append("**仓单数据：今日无更新**")
    
    return "\n".join(lines)


def send_daily_report(symbol: str = "JD2609") -> bool:
    """发送每日数据报告（严格验证数据有效性）"""
    log.info(f"Generating daily report for {symbol}...")
    
    futures_data = get_latest_futures_data(symbol)
    if not futures_data:
        log.error(f"[CRITICAL] No valid futures data for {symbol}! Sending data missing alert.")
        today = date.today().strftime("%Y-%m-%d")
        title = f"⚠️ 【数据异常】{symbol} 今日数据获取失败"
        content = f"""**紧急通知：{symbol} 今日数据获取失败**

原因：期货行情数据缺失或过期

建议：
1. 检查网络连接和 AKShare API 可用性
2. 手动确认 {symbol} 今日收盘价
3. 关注系统日志排查问题

🕐 检测时间：{today}"""
        return send_feishu_message(title, content, level="danger")
    
    spot_prices = get_all_spot_prices()
    receipt_data = get_latest_receipt_data("jd")
    
    today = date.today().strftime("%Y-%m-%d")
    title = f"📊 {symbol} 每日数据汇总 ({today})"
    content = format_daily_report(futures_data, spot_prices, receipt_data)
    
    result = send_feishu_message(title, content, level="info")
    
    if result:
        log.info(f"Daily report sent successfully for {symbol}")
    else:
        log.error(f"Failed to send daily report for {symbol}")
    
    return result


def job_send_daily_report():
    """定时任务：发送每日数据报告"""
    send_multi_contract_report(SUPPORTED_SYMBOLS)


# 支持多合约推送
def send_multi_contract_report(symbols: list = ["JD2607", "JD2608", "JD2609"]) -> dict:
    """发送多合约每日数据报告"""
    results = {}
    for symbol in symbols:
        results[symbol] = send_daily_report(symbol)
    return results