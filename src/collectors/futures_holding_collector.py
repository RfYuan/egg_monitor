"""
大商所前20会员持仓数据采集器
数据来源: 大商所官方API /api/market/top20_holding
"""

from datetime import date, timedelta
from typing import Optional, Dict

from src.collectors.dce_client import get_dce_client
from src.storage.database import SessionLocal
from src.storage.crud import create_futures_holding, get_futures_holdings_by_date
from src.notification.notifier import notify_warning, notify_info
from src.utils.logger import log

# 鸡蛋合约代码
EGG_CONTRACTS = ["JD2609"]


def _get_last_friday() -> date:
    """获取上一周五（持仓数据每周五更新）"""
    today = date.today()
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0 and today.weekday() == 4:
        # 今天是周五，检查是否已过17:00（简化处理：取今天）
        return today
    return today - timedelta(days=days_since_friday if days_since_friday > 0 else 7)


def collect_holding(contract_id: str, trade_date: date = None) -> bool:
    """
    采集指定合约和日期的持仓数据
    
    Args:
        contract_id: 合约代码，如 "JD2609"
        trade_date: 交易日期，默认为上一周五
    
    Returns:
        是否采集成功
    """
    if trade_date is None:
        trade_date = _get_last_friday()
    
    trade_date_str = trade_date.strftime("%Y-%m-%d")
    log.info(f"[Holding] 开始采集持仓数据，合约: {contract_id}, 日期: {trade_date_str}")
    
    db = SessionLocal()
    try:
        client = get_dce_client()
        raw_data = client.get_top20_holding(contract_id.upper(), trade_date_str)
        
        if raw_data is None:
            log.error(f"[Holding] API调用失败或无数据: {contract_id} @ {trade_date_str}")
            notify_warning("DCE_HOLDING", f"持仓数据采集失败: {contract_id} @ {trade_date_str}")
            return False
        
        # 检查是否已存在
        existing = get_futures_holdings_by_date(db, contract_id.upper(), trade_date)
        if existing:
            log.info(f"[Holding] 数据已存在，跳过: {contract_id} @ {trade_date_str}")
            return True
        
        # 提取汇总数据
        # API返回结构示例: {"long_qty": 12345, "short_qty": 12300, "long_change": 100, "short_change": -50, ...}
        long_qty = raw_data.get("long_qty", 0)
        short_qty = raw_data.get("short_qty", 0)
        long_change = raw_data.get("long_change", 0)
        short_change = raw_data.get("short_change", 0)
        
        # 计算多空比
        total = long_qty + short_qty
        long_ratio = (long_qty / total * 100) if total > 0 else 0
        short_ratio = (short_qty / total * 100) if total > 0 else 0
        
        holding_data = {
            "date": trade_date,
            "symbol": contract_id.upper(),
            "long_qty": int(long_qty),
            "short_qty": int(short_qty),
            "long_change": int(long_change) if long_change else None,
            "short_change": int(short_change) if short_change else None,
            "long_ratio": round(long_ratio, 2),
            "short_ratio": round(short_ratio, 2)
        }
        
        create_futures_holding(db, holding_data)
        log.info(f"[Holding] 已保存: {holding_data}")
        
        # 计算净持仓变化
        net_change = (long_change or 0) - (short_change or 0)
        if abs(net_change) > 5000:  # 净持仓变化超过5000手
            direction = "多头" if net_change > 0 else "空头"
            notify_info("DCE_HOLDING", f"持仓异动预警: {contract_id} {direction}净增 {abs(net_change)} 手")
        
        return True
        
    except Exception as e:
        log.error(f"[Holding] 采集异常: {e}")
        notify_warning("DCE_HOLDING", f"持仓采集异常: {e}")
        return False
    finally:
        db.close()


def collect_and_save_holding(contract_id: str = "JD2609") -> bool:
    """
    定时任务入口：采集最新持仓数据
    每周五17:00后执行
    """
    return collect_holding(contract_id)


def get_holding_summary(symbol: str, weeks: int = 4) -> Optional[Dict]:
    """
    获取持仓汇总（用于分析）
    
    Args:
        symbol: 合约代码
        weeks: 统计最近周数
    
    Returns:
        汇总数据
    """
    from src.storage.crud import get_futures_holdings
    
    db = SessionLocal()
    try:
        holdings = get_futures_holdings(db, symbol.upper(), limit=weeks)
        if not holdings:
            return None
        
        latest = holdings[0]
        long_short_ratio = round(latest.long_ratio / latest.short_ratio, 2) if latest.short_ratio > 0 else 0
        
        return {
            "symbol": symbol,
            "date": latest.date,
            "long_qty": latest.long_qty,
            "short_qty": latest.short_qty,
            "long_ratio": latest.long_ratio,
            "short_ratio": latest.short_ratio,
            "long_short_ratio": long_short_ratio,
            "long_change": latest.long_change,
            "short_change": latest.short_change
        }
    finally:
        db.close()


def get_fund_flow(symbol: str, weeks: int = 4) -> Optional[Dict]:
    """
    计算资金流向指标（基于多空持仓变化）
    
    Args:
        symbol: 合约代码
        weeks: 统计最近周数
    
    Returns:
        资金流向数据 {net_flow, flow_direction, strength}
    """
    from src.storage.crud import get_futures_holdings
    
    db = SessionLocal()
    try:
        holdings = get_futures_holdings(db, symbol.upper(), limit=weeks)
        if len(holdings) < 2:
            return None
        
        # 计算净持仓变化
        net_flow = 0
        flow_directions = []
        for i in range(len(holdings) - 1):
            current = holdings[i]
            previous = holdings[i + 1]
            
            long_delta = current.long_qty - previous.long_qty
            short_delta = current.short_qty - previous.short_qty
            
            # 多头增仓 + 空头减仓 = 资金流入
            net_flow += long_delta - short_delta
            flow_directions.append("流入" if long_delta - short_delta > 0 else "流出")
        
        direction_count = sum(1 for d in flow_directions if d == "流入")
        strength = direction_count / len(flow_directions) if flow_directions else 0
        
        return {
            "symbol": symbol,
            "net_flow": net_flow,
            "flow_direction": "流入" if net_flow > 0 else "流出",
            "strength": round(strength * 100, 1),  # 百分比
            "weekly_flows": flow_directions
        }
    finally:
        db.close()
