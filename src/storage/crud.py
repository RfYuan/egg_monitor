from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session
from src.storage.models import (
    FuturesQuote,
    FuturesReceipt,
    FuturesHolding,
    SpotPrice,
    IndustrialInventory,
    AlertRecord,
    SystemLog
)

# Futures Quote
def create_futures_quote(db: Session, quote: dict):
    db_quote = FuturesQuote(**quote)
    db.add(db_quote)
    db.commit()
    db.refresh(db_quote)
    return db_quote

def get_futures_quotes(db: Session, symbol: str, limit: int = 100):
    return db.query(FuturesQuote).filter(FuturesQuote.symbol == symbol.upper()).order_by(FuturesQuote.datetime.desc()).limit(limit).all()

def get_futures_quotes_by_date_range(db: Session, symbol: str, start_date: datetime, end_date: datetime) -> List:
    """查询指定合约在日期范围内的所有行情记录（升序）"""
    return (db.query(FuturesQuote)
            .filter(FuturesQuote.symbol == symbol,
                    FuturesQuote.datetime >= start_date,
                    FuturesQuote.datetime <= end_date)
            .order_by(FuturesQuote.datetime.asc())
            .all())

def get_futures_quote_dates(db: Session, symbol: str) -> set:
    """获取指定合约在数据库中已有的所有日期集合，用于去重判断"""
    rows = db.query(FuturesQuote.datetime).filter(FuturesQuote.symbol == symbol).all()
    return {r.datetime.date() for r in rows}

# Futures Receipt
def create_futures_receipt(db: Session, receipt: dict):
    db_receipt = FuturesReceipt(**receipt)
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    return db_receipt

def get_futures_receipts(db: Session, symbol: str, limit: int = 100):
    return db.query(FuturesReceipt).filter(FuturesReceipt.symbol == symbol).order_by(FuturesReceipt.date.desc()).limit(limit).all()

def get_futures_receipts_by_date(db: Session, symbol: str, target_date: date):
    """查询指定合约和日期的仓单数据"""
    return db.query(FuturesReceipt).filter(
        FuturesReceipt.symbol == symbol,
        FuturesReceipt.date == target_date
    ).all()

# Futures Holding
def create_futures_holding(db: Session, holding: dict):
    db_holding = FuturesHolding(**holding)
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    return db_holding

def get_futures_holdings(db: Session, symbol: str, limit: int = 100):
    return db.query(FuturesHolding).filter(FuturesHolding.symbol == symbol).order_by(FuturesHolding.date.desc()).limit(limit).all()

def get_futures_holdings_by_date(db: Session, symbol: str, target_date: date):
    """查询指定合约和日期的持仓数据"""
    return db.query(FuturesHolding).filter(
        FuturesHolding.symbol == symbol,
        FuturesHolding.date == target_date
    ).all()

# Spot Price
def create_spot_price(db: Session, price: dict):
    db_price = SpotPrice(**price)
    db.add(db_price)
    db.commit()
    db.refresh(db_price)
    return db_price

def get_spot_prices(db: Session, category: Optional[str] = None, limit: int = 100):
    query = db.query(SpotPrice)
    if category:
        query = query.filter(SpotPrice.category == category)
    return query.order_by(SpotPrice.date.desc()).limit(limit).all()

# Industrial Inventory
def create_industrial_inventory(db: Session, inventory: dict):
    db_inv = IndustrialInventory(**inventory)
    db.add(db_inv)
    db.commit()
    db.refresh(db_inv)
    return db_inv

def get_industrial_inventories(db: Session, category: Optional[str] = None, limit: int = 100):
    query = db.query(IndustrialInventory)
    if category:
        query = query.filter(IndustrialInventory.category == category)
    return query.order_by(IndustrialInventory.date.desc()).limit(limit).all()

def get_latest_industrial_inventory(db: Session, category: str) -> Optional[IndustrialInventory]:
    """获取指定类型的最新产业数据"""
    return (db.query(IndustrialInventory)
            .filter(IndustrialInventory.category == category)
            .order_by(IndustrialInventory.date.desc())
            .first())

# Alert Record
def create_alert_record(db: Session, alert: dict):
    db_alert = AlertRecord(**alert)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_alert_records(db: Session, status: Optional[str] = None, limit: int = 100):
    query = db.query(AlertRecord)
    if status:
        query = query.filter(AlertRecord.status == status)
    return query.order_by(AlertRecord.created_at.desc()).limit(limit).all()

def resolve_alert(db: Session, alert_id: int, remark: Optional[str] = None):
    alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if alert:
        alert.status = "resolved"
        alert.resolved_at = datetime.now()
        alert.remark = remark
        db.commit()
        db.refresh(alert)
    return alert

# System Log
def create_system_log(db: Session, log: dict):
    db_log = SystemLog(**log)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
