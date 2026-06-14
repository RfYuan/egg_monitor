"""
数据库迁移脚本：为 futures_receipt 表添加 warehouse 字段
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

import sqlite3

def add_warehouse_column():
    """为 futures_receipt 表添加 warehouse 字段"""
    db_path = project_root / "data" / "db" / "egg_monitor.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查 warehouse 字段是否已存在
        cursor.execute("PRAGMA table_info(futures_receipt)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "warehouse" in columns:
            print("✅ warehouse 字段已存在")
            conn.close()
            return True
        
        # 添加 warehouse 字段
        cursor.execute("ALTER TABLE futures_receipt ADD COLUMN warehouse TEXT")
        conn.commit()
        
        print("✅ 成功添加 warehouse 字段")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        return False

if __name__ == "__main__":
    add_warehouse_column()