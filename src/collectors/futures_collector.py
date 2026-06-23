from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Set

from src.storage.database import SessionLocal
from src.storage.crud import (
    create_futures_quote,
    get_futures_quotes_by_date_range,
    get_futures_quote_dates,
)
from src.utils.logger import log
from src.collectors.futures_client import FuturesDataClient, DataSourceType

SUPPORTED_SYMBOLS = ["jd2607", "jd2608", "jd2609"]

# 全局统一客户端实例（大商所为第一数据源）
_futures_client = None


def _get_client() -> FuturesDataClient:
    """获取统一期货数据客户端实例"""
    global _futures_client
    if _futures_client is None:
        _futures_client = FuturesDataClient(primary_source=DataSourceType.DCE)
    return _futures_client


def _is_today_data(data_date: date) -> bool:
    """检查数据日期是否为今天"""
    return data_date == date.today()


def _is_data_fresh(data_date: date, max_days_old: int = 1) -> bool:
    """检查数据是否新鲜（不超过指定天数）"""
    return (date.today() - data_date).days <= max_days_old


def fetch_latest_quote(symbol: str) -> Optional[Dict]:
    """
    获取单个合约最新一日行情（优先从数据库读取，但严格验证日期）

    数据源优先级：
      1. 数据库缓存（如果日期为今天）
      2. 大商所官方API（第一优先级）
      3. AKShare（备用数据源）

    重要原则：禁止返回过期数据误导用户
    """
    today = date.today()
    client = _get_client()
    
    # ---- 1. 尝试从数据库读取 ----
    db = SessionLocal()
    try:
        rows = get_futures_quotes_by_date_range(
            db, symbol.upper(),
            datetime(today.year, today.month, today.day),
            datetime(today.year, today.month, today.day, 23, 59, 59),
        )
        if rows:
            latest = rows[-1]
            log.info(f"[CACHE HIT] {symbol} latest quote from DB: close={latest.close}, date={latest.datetime.date()}")
            return _orm_to_dict(latest)
        else:
            log.info(f"[CACHE MISS] {symbol} no today data in DB, fetching from API...")
    except Exception as e:
        log.warning(f"[DB ERROR] {symbol} query failed: {e}, fallback to API")
    finally:
        db.close()

    # ---- 2. 使用统一客户端从API获取 ----
    log.info(f"[API] {symbol} 尝试从统一客户端获取数据...")
    data = client.get_latest_quote(symbol)
    
    if data:
        if _is_today_data(data["datetime"].date()):
            log.info(f"[API SUCCESS] {symbol} 获取今日数据成功: close={data['close']}, source={data['source']}")
            _save_one(data)
            return data
        else:
            log.warning(f"[API STALE] {symbol} API返回过期数据: {data['datetime'].date()}, source={data['source']}")
    else:
        log.warning(f"[API FAILED] {symbol} 所有数据源均失败")
    
    log.error(f"[CRITICAL] {symbol} 无法获取今日数据！禁止返回过期数据误导用户。")
    return None


def fetch_history(symbol: str, start_date: str, end_date: Optional[str] = None) -> List[Dict]:
    """
    获取单个合约历史日行情（DB 优先，仅补拉缺失日期）

    流程：
      1. 查询 DB 中 [start_date, end_date] 区间已有数据
      2. 计算缺失日期集合
      3. 若有缺口 → 调统一客户端补拉缺口日期的数据
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

    # ---- 3. 使用统一客户端获取缺失日期数据 ----
    client = _get_client()
    api_results = client.get_historical_quotes(symbol, start_date, end_date)
    
    # 过滤出确实缺失的日期
    filtered_results = []
    for r in api_results:
        if r["datetime"].date() in missing_dates:
            filtered_results.append(r)

    # ---- 4. 合并去重返回 ----
    merged = {r["datetime"].date(): r for r in db_results}
    for r in filtered_results:
        merged[r["datetime"].date()] = r

    result = sorted(merged.values(), key=lambda x: x["datetime"])
    log.info(f"[MERGE] {symbol}: total {len(result)} records "
             f"(DB={len(db_results)}, API={len(filtered_results)})")
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


def _orm_to_dict(orm_obj) -> Dict:
    """SQLAlchemy ORM 对象 → 字典"""
    data = {
        "symbol": orm_obj.symbol,
        "datetime": orm_obj.datetime,
        "open": float(orm_obj.open),
        "high": float(orm_obj.high),
        "low": float(orm_obj.low),
        "close": float(orm_obj.close),
        "volume": int(orm_obj.volume),
        "open_interest": int(orm_obj.open_interest),
    }
    if hasattr(orm_obj, 'settle') and orm_obj.settle is not None:
        data["settle"] = float(orm_obj.settle)
    return data


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
        # 过滤掉数据库模型不支持的字段
        valid_fields = ["symbol", "datetime", "open", "high", "low", "close", "settle", "volume", "open_interest"]
        clean_quote = {k: v for k, v in quote.items() if k in valid_fields}
        create_futures_quote(db, clean_quote)
    except Exception as e:
        log.warning(f"Save one record failed (may be duplicate): {e}")
    finally:
        db.close()