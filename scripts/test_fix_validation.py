"""
测试修复：Symbol大小写匹配和数据保存
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
from src.storage.database import SessionLocal
from src.storage.crud import get_futures_quotes, create_futures_quote
from src.collectors.futures_collector import _save_one, fetch_latest_quote

print("=" * 60)
print("测试1：数据库查询大小写匹配")
print("=" * 60)

db = SessionLocal()

# 测试数据
test_data = {
    "symbol": "JD2609",
    "datetime": datetime(date.today().year, date.today().month, date.today().day),
    "open": 4200,
    "high": 4250,
    "low": 4180,
    "close": 4230,
    "volume": 100000,
    "open_interest": 50000,
}

try:
    # 清除测试数据
    db.query(FuturesQuote).filter(FuturesQuote.symbol == "JD2609", 
                                   FuturesQuote.datetime >= datetime(date.today().year, date.today().month, date.today().day)).delete()
    db.commit()
    print("已清除今日测试数据")
    
    # 保存数据（大写）
    create_futures_quote(db, test_data)
    print(f"保存成功: symbol={test_data['symbol']}")
    
    # 测试小写查询
    result_lower = get_futures_quotes(db, "jd2609", limit=1)
    print(f"小写查询 'jd2609': {'成功' if result_lower else '失败'}")
    
    # 测试大写查询
    result_upper = get_futures_quotes(db, "JD2609", limit=1)
    print(f"大写查询 'JD2609': {'成功' if result_upper else '失败'}")
    
    # 测试混合大小写查询
    result_mixed = get_futures_quotes(db, "Jd2609", limit=1)
    print(f"混合查询 'Jd2609': {'成功' if result_mixed else '失败'}")
    
    if result_lower and result_upper and result_mixed:
        print("\n✓ 所有查询都成功！大小写不敏感修复生效")
    else:
        print("\n✗ 查询失败")
        
finally:
    db.close()

print("\n" + "=" * 60)
print("测试2：保存成功日志")
print("=" * 60)

# 测试保存函数
try:
    save_test_data = {
        "symbol": "JD2608",
        "datetime": datetime(date.today().year, date.today().month, date.today().day),
        "open": 4300,
        "high": 4350,
        "low": 4280,
        "close": 4330,
        "volume": 80000,
        "open_interest": 40000,
        "source": "TEST",
    }
    _save_one(save_test_data)
    print("保存成功日志已输出到控制台")
    
except Exception as e:
    print(f"保存失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)