"""
数据库初始化与迁移模块

在应用启动时自动检查数据库结构，并在需要时执行迁移。
确保数据库表结构与代码模型保持一致。
"""

import sqlite3
from pathlib import Path
from loguru import logger

def check_and_migrate_database(db_path: Path) -> bool:
    """
    检查数据库结构并执行必要的迁移
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        是否迁移成功
    """
    if not db_path.exists():
        logger.warning(f"数据库文件不存在: {db_path}")
        return True  # 让后续代码创建新数据库
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 定义需要检查的表和字段
        migrations = [
            {
                "table": "industrial_inventory",
                "columns": [
                    {"name": "category", "type": "TEXT", "default": "'存栏量'"},
                ]
            },
            {
                "table": "futures_receipt",
                "columns": [
                    {"name": "warehouse", "type": "TEXT", "default": "NULL"},
                ]
            },
        ]
        
        all_success = True
        
        for migration in migrations:
            table_name = migration["table"]
            columns = migration["columns"]
            
            # 检查表是否存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                logger.info(f"表 {table_name} 不存在，跳过迁移")
                continue
            
            # 获取现有字段
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {col[1] for col in cursor.fetchall()}
            
            # 检查每个字段
            for col in columns:
                col_name = col["name"]
                col_type = col["type"]
                col_default = col.get("default", "NULL")
                
                if col_name in existing_columns:
                    logger.debug(f"字段 {table_name}.{col_name} 已存在")
                    continue
                
                # 添加缺失的字段
                try:
                    # 对于SQLite，添加字段时需要指定默认值
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} DEFAULT {col_default}")
                    conn.commit()
                    logger.info(f"✅ 成功添加字段 {table_name}.{col_name}")
                except Exception as e:
                    logger.error(f"❌ 添加字段 {table_name}.{col_name} 失败: {e}")
                    all_success = False
        
        conn.close()
        
        if all_success:
            logger.info("数据库迁移检查完成")
        else:
            logger.warning("部分数据库迁移失败，请检查日志")
        
        return all_success
        
    except Exception as e:
        logger.error(f"数据库迁移检查失败: {e}")
        return False

def init_database_if_needed(project_root: Path) -> bool:
    """
    在应用启动时初始化数据库
    
    Args:
        project_root: 项目根目录
        
    Returns:
        是否初始化成功
    """
    db_dir = project_root / "data" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = db_dir / "egg_monitor.db"
    
    # 执行迁移检查
    return check_and_migrate_database(db_path)