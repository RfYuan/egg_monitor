"""
测试脚本：获取 JD2607 / JD2608 / JD2609 过去一个月的日行情，并存入 SQLite

用法：
    python test_futures_history.py
    python test_futures_history.py 2026-05-01  # 指定起始日期
    python test_futures_history.py 2026-05-01 2026-06-08  # 指定日期范围
"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.storage.database import init_db, SessionLocal
from src.storage.crud import get_futures_quotes
from src.collectors.futures_collector import (
    SUPPORTED_SYMBOLS,
    fetch_multi_history,
    collect_and_save_history,
)
from src.utils.logger import log
from config.settings import settings


def main():
    # ---- 1. 解析参数 ----
    today = date.today()
    one_month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    start_date = sys.argv[1] if len(sys.argv) > 1 else one_month_ago
    end_date = sys.argv[2] if len(sys.argv) > 2 else today_str

    symbols = SUPPORTED_SYMBOLS

    print("=" * 60)
    print(f"  Egg Futures History Import Test")
    print(f"  Symbols : {symbols}")
    print(f"  Range   : {start_date} ~ {end_date}")
    print("=" * 60)

    # ---- 2. 初始化数据库 ----
    settings.ensure_dirs()
    init_db()
    print(f"\n[1/4] Database initialized: {settings.DB_PATH}")

    # ---- 3. 获取数据（先预览不存库） ----
    print(f"\n[2/4] Fetching raw data from AKShare...")
    raw_data = fetch_multi_history(symbols, start_date, end_date)

    total = 0
    for sym, records in raw_data.items():
        count = len(records)
        total += count
        if count > 0:
            first = records[0]
            last = records[-1]
            print(f"  {sym.upper():8s} | {count:3d} records | "
                  f"{first['datetime'].strftime('%Y-%m-%d')} ~ {last['datetime'].strftime('%Y-%m-%d')} "
                  f"| last close={last['close']}")
        else:
            print(f"  {sym.upper():8s} | --- no data ---")

    if total == 0:
        print("\n No data fetched. Check symbol names or network.")
        return

    # ---- 4. 存入数据库 ----
    print(f"\n[3/4] Saving {total} records to database...")
    counts = collect_and_save_history(symbols, start_date, end_date)

    for sym, cnt in counts.items():
        print(f"  {sym.upper():8s} -> saved {cnt} records")

    # ---- 5. 验证回读 ----
    print(f"\n[4/4] Verifying stored data...")
    db = SessionLocal()
    try:
        for sym in symbols:
            rows = get_futures_quotes(db, sym.upper(), limit=3)
            if rows:
                latest = rows[0]
                print(f"  {sym.upper():8s} | DB has data, "
                      f"latest={latest.datetime.strftime('%Y-%m-%d')} "
                      f"close={latest.close} vol={latest.volume}")
            else:
                print(f"  {sym.upper():8s} | no records in DB yet")
    finally:
        db.close()

    print(f"\n{'=' * 60}")
    print(f"  Done! Total {total} records imported.")
    print(f"  DB file: {settings.DB_PATH}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
