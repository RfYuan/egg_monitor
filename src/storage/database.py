from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from pathlib import Path
from loguru import logger

engine = create_engine(
    settings.DB_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DB_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from src.storage.models import (
        FuturesQuote,
        FuturesReceipt,
        FuturesHolding,
        SpotPrice,
        IndustrialInventory,
        AlertRecord,
        SystemLog
    )
    
    # 在创建表之前先执行迁移检查
    _run_migration_check()
    
    Base.metadata.create_all(bind=engine)

def _run_migration_check():
    """执行数据库迁移检查"""
    try:
        from src.storage.database_migration import init_database_if_needed
        
        project_root = Path(__file__).parent.parent.parent
        init_database_if_needed(project_root)
    except Exception as e:
        logger.error(f"数据库迁移检查失败: {e}")
