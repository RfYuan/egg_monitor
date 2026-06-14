"""
数据库迁移脚本：为所有表添加缺失的字段
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

import sqlite3

def check_and_add_column(db_path, table_name, column_name, column_type):
    """检查并添加缺失的字段"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查字段是否已存在
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    
    if column_name in columns:
        print(f"  ✅ {table_name}.{column_name} 已存在")
        conn.close()
        return True
    
    # 添加字段
    try:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        conn.commit()
        print(f"  ✅ 成功添加 {table_name}.{column_name}")
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ 添加 {table_name}.{column_name} 失败: {e}")
        conn.close()
        return False

def migrate_database():
    """执行所有数据库迁移"""
    db_path = project_root / "data" / "db" / "egg_monitor.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    print(f"📦 开始数据库迁移，目标: {db_path}")
    print("="*50)
    
    # 定义需要添加的字段
    migrations = [
        # (表名, 字段名, 字段类型)
        ("industrial_inventory", "category", "TEXT"),
        ("futures_receipt", "warehouse", "TEXT"),
    ]
    
    success_count = 0
    total_count = len(migrations)
    
    for table_name, column_name, column_type in migrations:
        print(f"\n处理 {table_name}.{column_name}...")
        if check_and_add_column(db_path, table_name, column_name, column_type):
            success_count += 1
    
    print("\n" + "="*50)
    print(f"迁移完成: {success_count}/{total_count} 字段处理成功")
    
    return success_count == total_count

if __name__ == "__main__":
    migrate_database()