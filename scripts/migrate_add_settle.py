"""数据库迁移脚本：添加 settle 字段到 futures_quote 表"""
import sqlite3
import os

db_path = "data/db/egg_monitor.db"

if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查 settle 列是否已存在
cursor.execute("PRAGMA table_info(futures_quote)")
columns = [col[1] for col in cursor.fetchall()]

if "settle" in columns:
    print("settle 列已存在，无需迁移")
else:
    print("添加 settle 列...")
    try:
        cursor.execute("ALTER TABLE futures_quote ADD COLUMN settle NUMERIC(10, 2)")
        conn.commit()
        print("迁移成功！")
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()

conn.close()