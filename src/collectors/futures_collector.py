
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Set
import akshare as ak
from src.storage.database import SessionLocal
from src.storage.crud import (
    create_futures_quote,
    get_futures_quotes_by_date_range,
    get_futures_quote_dates,
)
from src.utils.logger import log

SUPPORTED_SYMBOLS = ["jd2607", "jd2608", "jd2609"]


# ===================================================================
#  公开接口 — 均走 DB 优先缓存策略
# ===================================================================

def fetch_latest_quote(symbol: str) -> Optional[Dict]:
    """
    获取单个合约最新一日行情（优先从数据库读取）

    策略：
      1. 查库 → 最近一条记录的日期 == 今天 → 直接返回
      2. 库中无今天数据 → 调 AKShare 获取最新并存入
    """
    today = date.today()
    db = SessionLocal()
    try:
        # 1) 尝试从 DB 取最近一条
        rows = get_futures_quotes_by_date_range(
            db, symbol.upper(),
            datetime(today.year, today.month, today.day),
            datetime(today.year, today.month, today.day, 23, 59, 59),
        )
        if rows:
            latest = rows[-1]
            log.info(f"[CACHE HIT] {symbol} latest quote from DB: close={latest.close}")
            return _orm_to_dict(latest)
    except Exception as e:
        log.warning(f"DB query failed for {symbol}: {e}, fallback to API")
    finally:
        db.close()

    # 2) 库中没有 → 调 API
    log.info(f"[CACHE MISS] {symbol} fetching latest from AKShare...")
    try:
        df = _fetch_akshare(symbol)
        if df is not None and not df.empty:
            row = _row_to_dict(df.iloc[-1], symbol)
            # 写回 DB 供下次命中
            _save_one(row)
            return row
    except Exception as e:
        log.error(f"API fetch failed for {symbol}: {e}")
    return None


def fetch_history(symbol: str, start_date: str, end_date: Optional[str] = None) -> List[Dict]:
    """
    获取单个合约历史日行情（DB 优先，仅补拉缺失日期）

    流程：
      1. 查询 DB 中 [start_date, end_date] 区间已有数据
      2. 计算缺失日期集合
      3. 若有缺口 → 调 AKShare 补拉缺口日期的数据
      4. 合并去重，按日期升序返回

    Args:
        symbol: 合约代码，如 "jd2609"
        start_date: 起始日期 "YYYY-MM-DD"
        end_date: 结束日期 "YYYY-MM-DD"，默认为今天

    Returns:
        行情字典列表，按日期升序
    """
    if end_date is None:
        end_date = date.today().strftime("%Y-%m-%d")

    dt_start = datetime.strptime(start_date, "%Y-%m-%d")
    dt_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(hours=23, minutes=59)

    # ---- 1. 从 DB 取已有数据 ----
    db = SessionLocal()
    db_rows = []
    existing_dates: Set[date] = set()
    try:
        db_rows = get_futures_quotes_by_date_range(db, symbol.upper(), dt_start, dt_end)
        existing_dates = get_futures_quote_dates(db, symbol.upper())
    finally:
        db.close()

    db_results = [_orm_to_dict(r) for r in db_rows]
    log.info(f"[DB] {symbol}: found {len(db_results)} records in [{start_date} ~ {end_date}]")

    # ---- 2. 计算缺失日期 ----
    all_dates = _date_range(start_date, end_date)
    missing_dates = all_dates - existing_dates

    if not missing_dates:
        log.info(f"[CACHE FULL] {symbol}: all {len(all_dates)} dates already in DB")
        return sorted(db_results, key=lambda x: x["datetime"])

    log.info(f"[GAP] {symbol}: need to fetch {len(missing_dates)} missing dates: "
             f"{sorted(missing_dates)[0]} ~ {sorted(missing_dates)[-1]}")

    # ---- 3. 仅对缺失日期调 API ----
    api_results = _fetch_missing_from_api(symbol, missing_dates)

    # ---- 4. 合并去重返回 ----
    merged = {r["datetime"].date(): r for r in db_results}
    for r in api_results:
        merged[r["datetime"].date()] = r

    result = sorted(merged.values(), key=lambda x: x["datetime"])
    log.info(f"[MERGE] {symbol}: total {len(result)} records "
             f"(DB={len(db_results)}, API={len(api_results)})")
    return result


def fetch_multi_history(symbols: List[str], start_date: str, end_date: Optional[str] = None) -> Dict[str, List[Dict]]:
    """批量获取多个合约的历史行情"""
    return {sym: fetch_history(sym, start_date, end_date) for sym in symbols}


def collect_and_save_latest(symbols: Optional[List[str]] = None) -> Dict[str, Optional[Dict]]:
    """采集并保存多个合约的最新行情"""
    if symbols is None:
        symbols = SUPPORTED_SYMBOLS
    results = {}
    for sym in symbols:
        results[sym] = fetch_latest_quote(sym)
    return results


def collect_and_save_history(symbols: List[str], start_date: str, end_date: Optional[str] = None) -> Dict[str, int]:
    """
    批量采集历史行情并存入数据库（自动跳过已存在的记录）

    Returns:
        { symbol: newly_saved_count }
    """
    raw = fetch_multi_history(symbols, start_date, end_date)
    counts = {}
    db = SessionLocal()
    try:
        # 已有日期集合，用于跳过重复写入
        saved_counts = {}
        for sym in symbols:
            existing = get_futures_quote_dates(db, sym.upper())
            quotes = raw.get(sym, [])
            new_count = 0
            for q in quotes:
                if q["datetime"].date() not in existing:
                    create_futures_quote(db, q)
                    new_count += 1
            counts[sym] = new_count
            if new_count > 0:
                log.info(f"Saved {new_count} NEW records for {sym}")
            else:
                log.info(f"{sym}: all records already exist, 0 new saves")
    except Exception as e:
        log.error(f"Failed to save history: {e}")
    finally:
        db.close()
    return counts


# ===================================================================
#  内部函数
# ===================================================================

def _fetch_akshare(symbol: str):
    """调用 AKShare 获取原始 DataFrame"""
    return ak.futures_zh_daily_sina(symbol=symbol)


def _fetch_missing_from_api(symbol: str, missing_dates: Set[date]) -> List[Dict]:
    """仅拉取缺失日期的数据"""
    if not missing_dates:
        return []

    try:
        df = _fetch_akshare(symbol)
        if df is None or df.empty:
            log.warning(f"[API] No data returned for {symbol} (may be not listed yet)")
            return []

        results = []
        for _, row in df.iterrows():
            # 兼容列名：date/日期
            dt_str = str(row.get("date", row.get("日期")))
            dt = _parse_date(dt_str)
            if dt and dt.date() in missing_dates:
                results.append(_row_to_dict(row, symbol))

        log.info(f"[API] {symbol}: fetched {len(results)} records for missing dates")
        return results
    except Exception as e:
        log.error(f"[API] Failed to fetch missing data for {symbol}: {e}")
        return []


def _row_to_dict(row, symbol: str) -> Dict:
    """AKShare DataFrame 行 → 字典（兼容中英文列名）"""
    # 兼容列名
    dt_str = str(row.get("date", row.get("日期")))
    dt = _parse_date(dt_str) or datetime.now()

    return {
        "symbol": symbol.upper(),
        "datetime": dt,
        "open": float(row.get("open", row.get("开盘"))),
        "high": float(row.get("high", row.get("最高"))),
        "low": float(row.get("low", row.get("最低"))),
        "close": float(row.get("close", row.get("收盘"))),
        "volume": int(row.get("volume", row.get("成交量"))),
        "open_interest": int(row.get("hold", row.get("持仓量", 0))),
    }


def _orm_to_dict(orm_obj) -> Dict:
    """SQLAlchemy ORM 对象 → 字典"""
    return {
        "symbol": orm_obj.symbol,
        "datetime": orm_obj.datetime,
        "open": float(orm_obj.open),
        "high": float(orm_obj.high),
        "low": float(orm_obj.low),
        "close": float(orm_obj.close),
        "volume": int(orm_obj.volume),
        "open_interest": int(orm_obj.open_interest),
    }


def _parse_date(dt_str: str) -> Optional[datetime]:
    """兼容多种日期格式解析"""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def _date_range(start: str, end: str) -> Set[date]:
    """生成起止日期之间的所有日期集合"""
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    days = []
    cur = s
    while cur <= e:
        days.append(cur)
        cur += timedelta(days=1)
    return set(days)


def _save_one(quote: Dict):
    """单条写入数据库"""
    db = SessionLocal()
    try:
        create_futures_quote(db, quote)
    except Exception as e:
        log.warning(f"Save one record failed (may be duplicate): {e}")
    finally:
        db.close()
