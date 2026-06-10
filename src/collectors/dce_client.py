"""
大连商品交易所(DCE)官方API客户端
认证方式: 先获取accessToken，再携带token访问业务接口
优化: 添加token本地文件缓存，减少token申请次数
"""

import os
import time
import json
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Any

import requests

from config.settings import settings
from src.utils.logger import log


class DCEClient:
    """大商所API客户端"""
    
    # token缓存文件路径
    _TOKEN_CACHE_DIR = "data/cache"
    _TOKEN_CACHE_FILE = "dce_token.json"
    
    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = None):
        self.api_key = api_key or settings.DCE_API_KEY
        self.api_secret = api_secret or settings.DCE_API_SECRET
        self.base_url = (base_url or settings.DCE_API_URL).rstrip("/")
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "EggMonitor/1.0",
            "Content-Type": "application/json"
        })
        # 尝试从本地缓存加载token
        self._load_token_from_cache()
    
    def _get_token_cache_path(self) -> str:
        """获取token缓存文件路径"""
        os.makedirs(self._TOKEN_CACHE_DIR, exist_ok=True)
        return os.path.join(self._TOKEN_CACHE_DIR, self._TOKEN_CACHE_FILE)
    
    def _load_token_from_cache(self) -> bool:
        """从本地缓存加载token"""
        cache_path = self._get_token_cache_path()
        if not os.path.exists(cache_path):
            log.debug("[DCE] 未找到token缓存文件")
            return False
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.access_token = data.get("access_token")
            expires_at_str = data.get("expires_at")
            
            if self.access_token and expires_at_str:
                self.token_expires_at = datetime.fromisoformat(expires_at_str)
                
                if datetime.now() < self.token_expires_at:
                    # 预留5分钟缓冲时间
                    remaining = (self.token_expires_at - datetime.now()).total_seconds() / 60
                    log.info(f"[DCE] 从缓存加载token成功，剩余有效期约 {int(remaining)} 分钟")
                    return True
                else:
                    log.info(f"[DCE] 缓存token已过期")
            else:
                log.warning("[DCE] 缓存文件格式无效")
                
        except Exception as e:
            log.error(f"[DCE] 读取token缓存失败: {e}")
        
        return False
    
    def _save_token_to_cache(self, token: str, expires_at: datetime):
        """保存token到本地缓存"""
        try:
            cache_path = self._get_token_cache_path()
            data = {
                "access_token": token,
                "expires_at": expires_at.isoformat(),
                "saved_at": datetime.now().isoformat()
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            log.debug(f"[DCE] token已保存到缓存: {cache_path}")
        except Exception as e:
            log.error(f"[DCE] 保存token缓存失败: {e}")
    
    def _get_access_token(self) -> Optional[str]:
        """获取accessToken（优先使用本地缓存，token有效期8小时）"""
        # 检查内存缓存的token是否有效
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # 尝试从本地缓存加载
        if self._load_token_from_cache():
            return self.access_token
        
        # 获取新token
        url = f"{self.base_url}/dceapi/cms/auth/accessToken"
        headers = {"apikey": self.api_key}
        body = {"secret": self.api_secret}
        
        try:
            resp = self.session.post(url, json=body, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 200 and data.get("success"):
                    self.access_token = data.get("data", {}).get("token")
                    # token有效期8小时，提前5分钟过期
                    self.token_expires_at = datetime.now() + timedelta(hours=8, minutes=-5)
                    
                    # 保存到本地缓存
                    self._save_token_to_cache(self.access_token, self.token_expires_at)
                    
                    log.info(f"[DCE] 获取accessToken成功，有效期8小时")
                    return self.access_token
                else:
                    log.error(f"[DCE] 获取token失败: {data.get('msg')}")
            else:
                log.error(f"[DCE] 获取token请求失败: {resp.status_code}")
        except requests.exceptions.RequestException as e:
            log.error(f"[DCE] 获取token异常: {e}")
        
        return None
    
    def _request(self, method: str, path: str, params: Dict = None, retry: int = 2) -> Optional[Dict]:
        """
        发送API请求（自动添加token和重试）
        
        Args:
            method: HTTP方法 (GET/POST)
            path: API业务路径（不含base_url）
            params: URL参数
            retry: 重试次数
        
        Returns:
            API响应数据或None
        """
        # 确保有有效token
        token = self._get_access_token()
        if not token:
            log.error("[DCE] 无法获取accessToken，请求中止")
            return None
        
        url = f"{self.base_url}/dceapi{path}"
        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {token}"
        }
        
        for attempt in range(retry + 1):
            try:
                if attempt > 0:
                    log.info(f"[DCE] 重试请求 {path} (第{attempt + 1}次)")
                    time.sleep(2)
                
                if method.upper() == "GET":
                    resp = self.session.get(url, params=params, headers=headers, timeout=30)
                else:
                    resp = self.session.post(url, json=params, headers=headers, timeout=30)
                
                if resp.status_code == 200:
                    data = resp.json()
                    # 业务错误码判断（成功为 code=200）
                    if data.get("code") == 200:
                        return data.get("data")
                    elif data.get("code") == 401:
                        # token失效，清除缓存重新获取
                        log.warning("[DCE] token失效，重新获取...")
                        self.access_token = None
                        self.token_expires_at = None
                        # 清除本地缓存
                        cache_path = self._get_token_cache_path()
                        if os.path.exists(cache_path):
                            os.remove(cache_path)
                        token = self._get_access_token()
                        if token:
                            headers["Authorization"] = f"Bearer {token}"
                            continue
                    else:
                        log.error(f"[DCE] API错误 {path}: {data.get('msg')}")
                        return None
                elif resp.status_code == 429:
                    log.warning(f"[DCE] 请求频率超限，等待60秒...")
                    time.sleep(60)
                    continue
                else:
                    log.error(f"[DCE] HTTP错误 {path}: {resp.status_code} - {resp.text}")
                    
            except requests.exceptions.Timeout:
                log.warning(f"[DCE] 请求超时 {path}")
            except requests.exceptions.RequestException as e:
                log.error(f"[DCE] 请求异常 {path}: {e}")
        
        return None
    
    def get_variety_list(self) -> Optional[List[Dict]]:
        """
        获取品种列表
        
        Returns:
            品种列表数据
        """
        path = "/forward/publicweb/variety"
        
        data = self._request("GET", path, params={})
        return data
    
    def get_daily_quotes(self, trade_date: str, variety_id: str = "all", trade_type: int = 2, lang: str = "zh") -> Optional[List[Dict]]:
        """
        获取日行情数据
        
        Args:
            trade_date: 交易日期 "YYYYMMDD" 或 "YYYY-MM-DD"
            variety_id: 品种id，全部为"all"，鸡蛋为"jd"
            trade_type: 1期货，2期权，默认为2
            lang: "zh"中文，"en"英文
        
        Returns:
            行情数据列表
        """
        path = "/forward/publicweb/dailystat/dayQuotes"
        
        # 确保日期格式为 YYYYMMDD
        date_str = trade_date.replace("-", "")
        
        params = {
            "varietyId": variety_id,
            "tradeDate": date_str,
            "tradeType": str(trade_type),
            "lang": lang,
            "statisticsType": 2
        }
        
        data = self._request("POST", path, params=params)
        return data
    
    def get_warehouse_receipt(self, trade_date: str = None) -> Optional[List[Dict]]:
        """
        获取仓单日报数据
        
        Args:
            trade_date: 交易日期 "YYYYMMDD" 或 "YYYY-MM-DD"，默认为上一交易日
        
        Returns:
            仓单数据列表
        """
        path = "/delivery/warehouse/receipt"
        
        # 确保日期格式为 YYYYMMDD
        if trade_date:
            date_str = trade_date.replace("-", "")
        else:
            # 获取上一交易日
            from datetime import date, timedelta
            today = date.today()
            if today.weekday() == 0:
                date_str = (today - timedelta(days=3)).strftime("%Y%m%d")
            else:
                date_str = (today - timedelta(days=1)).strftime("%Y%m%d")
        
        params = {
            "varietyCode": "jd",  # 鸡蛋品种
            "tradeDate": date_str
        }
        
        data = self._request("GET", path, params=params)
        
        # 处理返回数据，转为标准格式
        if data and isinstance(data, list):
            result = []
            for item in data:
                result.append({
                    "variety": item.get("varietyName", ""),
                    "contract_id": item.get("contractId", ""),
                    "receipt_qty": item.get("receiptQty", 0),
                    "change": item.get("changeQty", 0),
                    "warehouse": item.get("warehouseName", "")
                })
            return result
        
        return data
    
    def get_top20_holding(self, contract_id: str = None, trade_date: str = None) -> Optional[Dict]:
        """
        获取前20会员持仓数据
        
        Args:
            contract_id: 合约代码，如 "JD2609"
            trade_date: 交易日期 "YYYYMMDD" 或 "YYYY-MM-DD"，默认为上一交易日
        
        Returns:
            持仓数据（含多空双方汇总）
        """
        path = "/member/daily/ranking"
        
        # 确保日期格式为 YYYYMMDD
        if trade_date:
            date_str = trade_date.replace("-", "")
        else:
            # 获取上一交易日
            from datetime import date, timedelta
            today = date.today()
            if today.weekday() == 0:
                date_str = (today - timedelta(days=3)).strftime("%Y%m%d")
            else:
                date_str = (today - timedelta(days=1)).strftime("%Y%m%d")
        
        # 提取品种代码（去掉数字，如 "JD2609" -> "jd"）
        if contract_id:
            variety_id = contract_id[:2].lower()
            contract_id_full = contract_id.upper()
        else:
            variety_id = "jd"
            contract_id_full = "JD2609"
        
        params = {
            "varietyID": variety_id,
            "contractID": contract_id_full,
            "tradeDate": date_str,
            "tradeType": "1"  # 1=期货
        }
        
        data = self._request("GET", path, params=params)
        
        # 处理返回数据，转为汇总格式
        # API返回 BuyFutureList(持买) 和 SellFutureList(持卖)
        if data and isinstance(data, dict):
            buy_list = data.get("buyFutureList", [])
            sell_list = data.get("sellFutureList", [])
            
            # 计算持买/持卖汇总
            total_long = sum(int(item.get("qty", 0)) for item in buy_list)
            total_short = sum(int(item.get("qty", 0)) for item in sell_list)
            
            # 计算净持仓变化（需要对比昨日数据，这里简化处理）
            return {
                "long_qty": total_long,
                "short_qty": total_short,
                "long_change": None,  # API不直接提供变化量，需要历史对比
                "short_change": None,
                "buy_list": buy_list[:20] if buy_list else [],  # 前20会员
                "sell_list": sell_list[:20] if sell_list else []
            }
        
        return data
    
    def get_notice_list(self, category: str = None, page: int = 1, page_size: int = 20) -> Optional[Dict]:
        """
        获取交易所公告列表
        
        Args:
            category: 公告分类，可选值:
                - "244": 交易所公告
                - "245": 交易所通知
                - "1076": 期权公告
                - "242": 新闻
                默认 "244" (交易所公告)
            page: 页码，默认 1
            page_size: 每页条数，默认 20
        
        Returns:
            公告列表数据
        """
        path = "/news/article/byPage"
        
        params = {
            "columnId": category or "244",  # 默认交易所公告
            "pageNo": page,
            "pageSize": page_size,
            "siteID": 5
        }
        
        data = self._request("GET", path, params=params)
        return data


# 单例模式
_dce_client: Optional[DCEClient] = None

def get_dce_client() -> DCEClient:
    """获取大商所API客户端单例"""
    global _dce_client
    if _dce_client is None:
        _dce_client = DCEClient()
    return _dce_client