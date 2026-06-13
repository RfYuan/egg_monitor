"""
数据库初始化脚本

初始化数据库表结构
"""

import sys
import os
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from loguru import logger
from src.storage.database import engine, Base, get_db
from src.storage.models import (
    FuturesQuote,
    FuturesReceipt,
    FuturesHolding,
    SpotPrice,
    IndustrialInventory,
    AlertRecord,
    SystemLog
)


def init_database():
    """初始化数据库"""
    logger.info("="*50)
    logger.info("开始初始化数据库")
    logger.info("="*50)

    try:
        # 删除旧数据库（如果存在）
        db_path = "data/db/egg_monitor.db"
        if os.path.exists(db_path):
            logger.warning(f"[DB] 删除旧数据库: {db_path}")
            os.remove(db_path)

        # 创建所有表
        logger.info("[DB] 创建数据库表...")
        Base.metadata.create_all(bind=engine)

        # 验证表创建
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        logger.info(f"[DB] 数据库初始化完成!")
        logger.info(f"[DB] 创建的表: {', '.join(tables)}")

        # 显示表结构
        for table_name in tables:
            columns = inspector.get_columns(table_name)
            logger.info(f"\n[DB] 表 {table_name} 的列:")
            for col in columns:
                logger.info(f"  - {col['name']}: {col['type']}")

        logger.info("\n" + "="*50)
        logger.info("数据库初始化成功!")
        logger.info("="*50)

        return True

    except Exception as e:
        logger.error(f"[DB] 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
