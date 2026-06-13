from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, Text, JSON
from sqlalchemy.sql import func
from src.storage.database import Base

class FuturesQuote(Base):
    __tablename__ = "futures_quote"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    datetime = Column(DateTime, nullable=False, index=True)
    open = Column(Numeric(10, 2), nullable=False)
    high = Column(Numeric(10, 2), nullable=False)
    low = Column(Numeric(10, 2), nullable=False)
    close = Column(Numeric(10, 2), nullable=False)
    volume = Column(Integer, nullable=False)
    open_interest = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class FuturesReceipt(Base):
    __tablename__ = "futures_receipt"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    receipt_qty = Column(Integer, nullable=False)
    change = Column(Integer, nullable=False)
    warehouse = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class FuturesHolding(Base):
    __tablename__ = "futures_holding"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    long_qty = Column(Integer, nullable=False)
    short_qty = Column(Integer, nullable=False)
    long_change = Column(Integer, nullable=True)
    short_change = Column(Integer, nullable=True)
    long_ratio = Column(Numeric(6, 2), nullable=True)
    short_ratio = Column(Numeric(6, 2), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class SpotPrice(Base):
    __tablename__ = "spot_price"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    category = Column(String(20), nullable=False, index=True)
    region = Column(String(50), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False)
    source = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class IndustrialInventory(Base):
    __tablename__ = "industrial_inventory"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)  # 数据类型：存栏量、鸡苗销量、淘汰鸡出栏、冷库库存等
    inventory = Column(Numeric(12, 2), nullable=False)      # 存栏数量
    mom = Column(Numeric(6, 2), nullable=True)               # 环比变化
    yoy = Column(Numeric(6, 2), nullable=True)               # 同比变化
    source = Column(String(50), nullable=False)               # 数据来源
    created_at = Column(DateTime, server_default=func.now())

class AlertRecord(Base):
    __tablename__ = "alert_record"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    level = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    rule_id = Column(String(50), nullable=False)
    data_snapshot = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, index=True, default="pending")
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, index=True, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

class SystemLog(Base):
    __tablename__ = "system_log"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    extra = Column(JSON, nullable=True)
