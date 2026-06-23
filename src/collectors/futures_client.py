"""
统一期货数据客户端

提供统一的API接口，抽象底层数据源差异：
- 大商所API（DCE）: 使用品种ID + 合约代码
- AKShare: 使用统一合约代码

上层调用者使用统一的symbol格式（如 "jd2609"），客户端自动适配底层数据源。
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Protocol

from src.collectors.dce_client import DCEClient
from src.utils.logger import log

# 统一symbol格式规范
# 格式: {品种代码}{年份后两位}{月份}
# 示例: jd2609 (鸡蛋2026年9月合约), m2609 (豆粕2026年9月合约)

# 品种映射表
VARIETY_MAP = {
    "jd": {"name": "鸡蛋", "exchange": "DCE", "dce_id": "jd"},
    "m": {"name": "豆粕", "exchange": "DCE", "dce_id": "m"},
    "y": {"name": "豆油", "exchange": "DCE", "dce_id": "y"},
    "c": {"name": "玉米", "exchange": "DCE", "dce_id": "c"},
    "cs": {"name": "玉米淀粉", "exchange": "DCE", "dce_id": "cs"},
    "a": {"name": "豆一", "exchange": "DCE", "dce_id": "a"},
    "b": {"name": "豆二", "exchange": "DCE", "dce_id": "b"},
}

# 数据源类型
class DataSourceType:
    DCE = "dce"
    AKShare = "akshare"


class FuturesDataSource(Protocol):
    """期货数据源协议（抽象接口）"""
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """获取最新行情"""
        ...
    
    def get_historical_quotes(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """获取历史行情"""
        ...


class DCEAdapter:
    """大商所API适配器"""
    
    def __init__(self):
        self.client = DCEClient()
    
    def _parse_symbol(self, symbol: str) -> tuple:
        """
        解析统一symbol，提取品种ID和合约信息
        
        Args:
            symbol: 统一格式，如 "jd2609"
        
        Returns:
            (variety_id, contract_id)
        """
        symbol_lower = symbol.lower()
        
        # 查找品种ID（最长匹配）
        for variety_id in sorted(VARIETY_MAP.keys(), key=len, reverse=True):
            if symbol_lower.startswith(variety_id):
                contract_code = symbol_lower[len(variety_id):]
                return variety_id, symbol_lower
        
        # 默认取前2位作为品种ID
        return symbol_lower[:2], symbol_lower
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """
        从大商所API获取最新行情
        
        Args:
            symbol: 统一格式，如 "jd2609"
        
        Returns:
            行情数据字典
        """
        try:
            today = date.today()
            trade_date = today.strftime("%Y%m%d")
            variety_id, contract_id = self._parse_symbol(symbol)
            
            log.info(f"[DCE] 获取最新行情: symbol={symbol}, variety_id={variety_id}, contract_id={contract_id}, trade_date={trade_date}")
            
            # 调用大商所API
            quotes = self.client.get_daily_quotes(
                trade_date=trade_date,
                variety_id=variety_id,
                trade_type=1  # 期货
            )
            
            if not quotes:
                log.warning(f"[DCE] API返回空数据: symbol={symbol}")
                return None
            
            # 查找目标合约（大商所返回的contractId是小写的）
            for quote in quotes:
                if quote.get("contractId") == contract_id:
                    log.info(f"[DCE] 找到合约: {contract_id}, close={quote.get('close')}")
                    
                    # 解析日期
                    quote_trade_date = quote.get("tradeDate")
                    if quote_trade_date:
                        dt = datetime.strptime(quote_trade_date, "%Y%m%d")
                    else:
                        dt = datetime.strptime(trade_date, "%Y%m%d")
                    
                    return {
                        "symbol": symbol.upper(),
                        "datetime": dt,
                        "open": float(quote.get("open", 0)),
                        "high": float(quote.get("high", 0)),
                        "low": float(quote.get("low", 0)),
                        "close": float(quote.get("close", 0)),
                        "settle": float(quote.get("settlementPrice", 0)) if quote.get("settlementPrice") else None,
                        "volume": int(quote.get("volumn", 0)),
                        "open_interest": int(quote.get("openInterest", 0)),
                        "source": "DCE",
                    }
            
            log.warning(f"[DCE] 未找到合约: {contract_id}")
            log.info(f"[DCE] 可用合约: {[q.get('contractId') for q in quotes]}")
            return None
            
        except Exception as e:
            log.error(f"[DCE] 获取行情失败: symbol={symbol}, error={e}")
            import traceback
            log.error(f"[DCE] 详细错误: {traceback.format_exc()}")
            return None
    
    def get_historical_quotes(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """获取历史行情（大商所API暂不支持历史数据批量查询）"""
        log.warning(f"[DCE] 历史行情查询暂不支持，symbol={symbol}")
        return []


class AKShareAdapter:
    """AKShare适配器"""
    
    def __init__(self):
        import akshare as ak
        self.ak = ak
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """
        从AKShare获取最新行情
        
        AKShare futures_zh_daily_sina接口使用统一合约代码（如 "jd2609"），
        返回字段：date, open, high, low, close, volume, hold, settle
        
        Args:
            symbol: 统一格式，如 "jd2609"
        
        Returns:
            行情数据字典
        """
        try:
            log.info(f"[AKShare] 获取最新行情: symbol={symbol}")
            
            # AKShare使用统一合约代码（小写或大写均可）
            df = self.ak.futures_zh_daily_sina(symbol=symbol)
            
            if df is None or df.empty:
                log.warning(f"[AKShare] 返回空数据: symbol={symbol}")
                return None
            
            log.info(f"[AKShare] 返回 {len(df)} 条数据")
            
            # 取最新一条
            row = df.iloc[-1]
            
            return {
                "symbol": symbol.upper(),
                "datetime": datetime.strptime(str(row["date"]), "%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "settle": float(row["settle"]),
                "volume": int(row["volume"]),
                "open_interest": int(row["hold"]),
                "source": "AKShare",
            }
            
        except Exception as e:
            log.error(f"[AKShare] 获取行情失败: symbol={symbol}, error={e}")
            import traceback
            log.error(f"[AKShare] 详细错误: {traceback.format_exc()}")
            return None
    
    def get_historical_quotes(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """
        获取历史行情
        
        Args:
            symbol: 统一格式，如 "jd2609"
            start_date: 起始日期 "YYYY-MM-DD"
            end_date: 结束日期 "YYYY-MM-DD"
        
        Returns:
            行情数据列表
        """
        try:
            log.info(f"[AKShare] 获取历史行情: symbol={symbol}, start={start_date}, end={end_date}")
            
            df = self.ak.futures_zh_daily_sina(symbol=symbol)
            
            if df is None or df.empty:
                log.warning(f"[AKShare] 返回空数据: symbol={symbol}")
                return []
            
            results = []
            for _, row in df.iterrows():
                try:
                    dt = datetime.strptime(str(row["date"]), "%Y-%m-%d")
                except ValueError:
                    continue
                
                dt_str_ymd = dt.strftime("%Y-%m-%d")
                if start_date <= dt_str_ymd <= end_date:
                    results.append({
                        "symbol": symbol.upper(),
                        "datetime": dt,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "settle": float(row["settle"]),
                        "volume": int(row["volume"]),
                        "open_interest": int(row["hold"]),
                        "source": "AKShare",
                    })
            
            log.info(f"[AKShare] 找到 {len(results)} 条历史数据")
            return results
            
        except Exception as e:
            log.error(f"[AKShare] 获取历史行情失败: symbol={symbol}, error={e}")
            return []


class FuturesDataClient:
    """
    统一期货数据客户端
    
    使用统一的symbol格式访问多个数据源，自动处理底层差异。
    
    示例：
        client = FuturesDataClient()
        data = client.get_latest_quote("jd2609")  # 使用统一symbol
    """
    
    def __init__(self, primary_source: str = DataSourceType.DCE):
        """
        初始化客户端
        
        Args:
            primary_source: 主数据源，可选 "dce" 或 "akshare"
        """
        self.dce_adapter = DCEAdapter()
        self.akshare_adapter = AKShareAdapter()
        
        # 设置数据源优先级
        if primary_source == DataSourceType.DCE:
            self.primary_adapter = self.dce_adapter
            self.secondary_adapter = self.akshare_adapter
            self.primary_name = "大商所API"
            self.secondary_name = "AKShare"
        else:
            self.primary_adapter = self.akshare_adapter
            self.secondary_adapter = self.dce_adapter
            self.primary_name = "AKShare"
            self.secondary_name = "大商所API"
        
        log.info(f"[FuturesClient] 初始化完成，主数据源: {self.primary_name}，备用数据源: {self.secondary_name}")
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """
        获取最新行情（自动尝试多个数据源）
        
        Args:
            symbol: 统一格式，如 "jd2609"
        
        Returns:
            行情数据字典，或None
        """
        log.info(f"[FuturesClient] 获取最新行情: symbol={symbol}")
        
        # 尝试主数据源
        log.info(f"[FuturesClient] 尝试主数据源: {self.primary_name}")
        data = self.primary_adapter.get_latest_quote(symbol)
        
        if data:
            log.info(f"[FuturesClient] 主数据源成功: {self.primary_name}, close={data['close']}")
            return data
        
        # 主数据源失败，尝试备用数据源
        log.warning(f"[FuturesClient] 主数据源失败: {self.primary_name}, 尝试备用数据源: {self.secondary_name}")
        data = self.secondary_adapter.get_latest_quote(symbol)
        
        if data:
            log.info(f"[FuturesClient] 备用数据源成功: {self.secondary_name}, close={data['close']}")
            return data
        
        # 所有数据源均失败
        log.error(f"[FuturesClient] 所有数据源均失败: symbol={symbol}")
        return None
    
    def get_historical_quotes(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """
        获取历史行情
        
        Args:
            symbol: 统一格式，如 "jd2609"
            start_date: 起始日期 "YYYY-MM-DD"
            end_date: 结束日期 "YYYY-MM-DD"
        
        Returns:
            行情数据列表
        """
        log.info(f"[FuturesClient] 获取历史行情: symbol={symbol}, start={start_date}, end={end_date}")
        
        # 历史行情优先使用AKShare（大商所API暂不支持）
        data = self.akshare_adapter.get_historical_quotes(symbol, start_date, end_date)
        
        if not data:
            log.warning(f"[FuturesClient] 历史行情获取失败: symbol={symbol}")
        
        return data
    
    def get_variety_info(self, symbol: str) -> Optional[Dict]:
        """
        获取品种信息
        
        Args:
            symbol: 统一格式，如 "jd2609"
        
        Returns:
            品种信息字典
        """
        symbol_lower = symbol.lower()
        
        for variety_id in sorted(VARIETY_MAP.keys(), key=len, reverse=True):
            if symbol_lower.startswith(variety_id):
                return {
                    "variety_id": variety_id,
                    "name": VARIETY_MAP[variety_id]["name"],
                    "exchange": VARIETY_MAP[variety_id]["exchange"],
                    "contract_code": symbol_lower[len(variety_id):],
                }
        
        return None