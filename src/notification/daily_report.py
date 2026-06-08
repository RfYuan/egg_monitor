"""
每日交易数据推送模块

功能：
- 每个交易日 16:00 推送当日数据汇总
- 包含期货收盘价、涨跌幅、持仓变化
- 包含现货价格、仓单数据（如有）
- 计算基差等关键指标
"""

from datetime import datetime, date
from typing import Optional
from src.storage.database import SessionLocal
from src.storage.crud import get_futures_quotes, get_spot_prices, get_futures_receipts
from src.collectors.futures_collector import SUPPORTED_SYMBOLS
from src.notification.feishu import send_feishu_message
from src.utils.logger import log


def get_latest_futures_data(symbol: str = "JD2609") -> Optional[dict]:
    """获取最新期货数据"""
    db = SessionLocal()
    try:
        quotes = get_futures_quotes(db, symbol, limit=2)
        if not quotes:
            return None
        
        latest = quotes[0]
        prev = quotes[1] if len(quotes) > 1 else None
        
        # 计算涨跌幅
        change_pct = 0.0
        if prev and prev.close:
            change_pct = ((latest.close - prev.close) / prev.close) * 100
        
        # 计算持仓变化
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


def format_daily_report(futures_data: dict, spot_data: Optional[dict], receipt_data: Optional[dict]) -> str:
    """格式化每日数据报告"""
    lines = []
    
    # 期货数据
    change_str = f"+{futures_data['change_pct']}" if futures_data['change_pct'] >= 0 else str(futures_data['change_pct'])
    oi_change_str = f"+{futures_data['oi_change']}" if futures_data['oi_change'] >= 0 else str(futures_data['oi_change'])
    
    lines.append(f"**期货收盘：{futures_data['close']} ({change_str}%)**")
    lines.append(f"持仓：{futures_data['open_interest']}手 ({oi_change_str})")
    lines.append(f"成交量：{futures_data['volume']}手")
    lines.append("")
    
    # 现货数据
    if spot_data:
        lines.append(f"**现货价格：{spot_data['region']}鸡蛋 {spot_data['price']}元/{spot_data['unit']}**")
        
        # 计算基差
        basis = calculate_basis(futures_data['close'], spot_data['price'])
        basis_str = f"+{basis}" if basis >= 0 else str(basis)
        lines.append(f"基差：{basis_str} (现货-期货)")
    else:
        lines.append("**现货价格：暂无数据**")
    lines.append("")
    
    # 仓单数据
    if receipt_data:
        change_str = f"+{receipt_data['change']}" if receipt_data['change'] >= 0 else str(receipt_data['change'])
        lines.append(f"**仓单数据：{receipt_data['receipt_qty']}张 ({change_str})**")
    else:
        lines.append("**仓单数据：今日无更新**")
    
    return "\n".join(lines)


def send_daily_report(symbol: str = "JD2609") -> bool:
    """发送每日数据报告"""
    log.info(f"Generating daily report for {symbol}...")
    
    # 获取数据
    futures_data = get_latest_futures_data(symbol)
    if not futures_data:
        log.warning(f"No futures data available for {symbol}")
        return False
    
    spot_data = get_latest_spot_data("egg")
    receipt_data = get_latest_receipt_data("jd")
    
    # 格式化报告
    today = date.today().strftime("%Y-%m-%d")
    title = f"📊 {symbol} 每日数据汇总 ({today})"
    content = format_daily_report(futures_data, spot_data, receipt_data)
    
    # 发送飞书消息
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