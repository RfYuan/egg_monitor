"""
大商所仓单数据采集器
数据来源: 大商所官方API /api/market/warehouse_receipt
"""

from datetime import date, timedelta
from typing import Optional, List, Dict

from src.collectors.dce_client import get_dce_client
from src.storage.database import SessionLocal
from src.storage.crud import create_futures_receipt, get_futures_receipts_by_date
from src.notification.notifier import notify_warning, notify_info
from src.utils.logger import log

# 鸡蛋合约代码映射（大商所使用 JD + 合约月份）
EGG_CONTRACTS = ["JD2607", "JD2608", "JD2609", "JD2610", "JD2611", "JD2612"]


def _get_last_trading_day() -> date:
    """获取上一交易日（简单逻辑：跳过周末）"""
    today = date.today()
    if today.weekday() == 0:  # 周一
        return today - timedelta(days=3)
    else:
        return today - timedelta(days=1)


def collect_receipt(trade_date: date = None) -> bool:
    """
    采集指定日期的仓单数据
    
    Args:
        trade_date: 交易日期，默认为上一交易日
    
    Returns:
        是否采集成功
    """
    if trade_date is None:
        trade_date = _get_last_trading_day()
    
    trade_date_str = trade_date.strftime("%Y-%m-%d")
    log.info(f"[Receipt] 开始采集仓单数据，日期: {trade_date_str}")
    
    db = SessionLocal()
    try:
        client = get_dce_client()
        raw_data = client.get_warehouse_receipt(trade_date_str)
        
        if raw_data is None:
            log.error(f"[Receipt] API调用失败或无数据: {trade_date_str}")
            notify_warning("DCE_API", f"仓单数据采集失败: {trade_date_str}")
            return False
        
        saved_count = 0
        for item in raw_data:
            contract_id = item.get("contract_id", "")
            
            # 只处理鸡蛋合约
            if not contract_id.upper().startswith("JD"):
                continue
            
            # 检查是否已存在
            existing = get_futures_receipts_by_date(db, contract_id.upper(), trade_date)
            if existing:
                log.info(f"[Receipt] 数据已存在，跳过: {contract_id} @ {trade_date_str}")
                continue
            
            receipt_data = {
                "date": trade_date,
                "symbol": contract_id.upper(),
                "receipt_qty": int(item.get("receipt_qty", 0)),
                "change": int(item.get("change", 0)),
                "warehouse": item.get("warehouse", "")
            }
            
            try:
                create_futures_receipt(db, receipt_data)
                saved_count += 1
                log.debug(f"[Receipt] 已保存: {receipt_data}")
            except Exception as e:
                log.error(f"[Receipt] 保存失败 {item}: {e}")
        
        log.info(f"[Receipt] 仓单采集完成，保存 {saved_count} 条记录")
        
        # 计算仓单总量变化（用于预警）
        total_receipt = sum(int(item.get("receipt_qty", 0)) for item in raw_data if item.get("contract_id", "").upper().startswith("JD"))
        if saved_count > 0:
            notify_info("DCE_RECEIPT", f"仓单数据已更新，总量: {total_receipt} 手")
        
        return True
        
    except Exception as e:
        log.error(f"[Receipt] 采集异常: {e}")
        notify_warning("DCE_RECEIPT", f"仓单采集异常: {e}")
        return False
    finally:
        db.close()


def collect_and_save_receipt() -> bool:
    """
    定时任务入口：采集最新仓单数据
    优先使用API，失败时记录告警
    """
    return collect_receipt()


def get_receipt_summary(symbol: str, days: int = 7) -> Optional[Dict]:
    """
    获取仓单汇总（用于分析）
    
    Args:
        symbol: 合约代码
        days: 统计最近天数
    
    Returns:
        汇总数据 {total, change, trend}
    """
    from datetime import datetime, timedelta
    from src.storage.crud import get_futures_receipts
    
    db = SessionLocal()
    try:
        receipts = get_futures_receipts(db, symbol.upper(), limit=days)
        if not receipts:
            return None
        
        total = sum(r.receipt_qty for r in receipts)
        change = receipts[0].change if receipts else 0
        
        # 计算趋势（近7天变化）
        if len(receipts) >= 2:
            trend = receipts[0].receipt_qty - receipts[-1].receipt_qty
        else:
            trend = 0
        
        return {
            "symbol": symbol,
            "total": total,
            "change": change,
            "trend": trend,
            "date": receipts[0].date if receipts else None
        }
    finally:
        db.close()
