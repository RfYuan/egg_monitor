"""
HTTP 工具模块
封装 requests，统一请求头和管理会话
"""

import time
import socket
import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin

from src.utils.logger import log
from src.collectors.base.retry import with_retry


def _force_ipv4():
    """
    强制使用IPv4
    
    解决服务器环境下IPv6不可达的问题：
    - Python的requests库默认优先尝试IPv6连接
    - 如果服务器没有配置IPv6，会立即失败
    - 此函数通过修改socket.getaddrinfo强制只使用IPv4
    """
    try:
        orig_getaddrinfo = socket.getaddrinfo
        
        def new_getaddrinfo(host, port, family=0, socktype=0, proto=0, flags=0):
            # 强制使用IPv4（socket.AF_INET）
            return orig_getaddrinfo(host, port, socket.AF_INET, socktype, proto, flags)
        
        socket.getaddrinfo = new_getaddrinfo
        log.debug("[HttpClient] 已强制使用IPv4")
    except Exception as e:
        log.warning(f"[HttpClient] 强制IPv4失败: {e}")


# 标准浏览器请求头
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


# 模块初始化时强制使用IPv4
_force_ipv4()


class HttpClient:
    """
    HTTP 客户端封装
    
    提供：
    - 单例模式的会话管理
    - 标准请求头
    - 自动重试
    - 请求频率限制
    """
    
    _instance: Optional["HttpClient"] = None
    _session: Optional[requests.Session] = None
    
    # 请求间隔配置（秒）
    MIN_REQUEST_INTERVAL = 1.0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(DEFAULT_HEADERS)
            self._last_request_time = 0.0
            log.debug("[HttpClient] HTTP客户端初始化完成")
    
    def _wait_for_rate_limit(self):
        """请求频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()
    
    @with_retry(max_retries=3, retry_delay=2)
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        **kwargs
    ) -> requests.Response:
        """
        发送 GET 请求
        
        Args:
            url: 请求URL
            params: URL参数
            headers: 请求头（会与默认请求头合并）
            timeout: 超时时间（秒）
            **kwargs: 其他 requests 参数
        
        Returns:
            Response 对象
        """
        self._wait_for_rate_limit()
        
        request_headers = dict(DEFAULT_HEADERS)
        if headers:
            request_headers.update(headers)
        
        log.debug(f"[HttpClient] GET {url}")
        
        try:
            response = self._session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=timeout,
                **kwargs
            )
            response.raise_for_status()
            log.debug(f"[HttpClient] 响应: {response.status_code} ({len(response.text)} bytes)")
            return response
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                log.warning(f"[HttpClient] 页面不存在: {url}")
            raise
        except requests.exceptions.RequestException as e:
            log.error(f"[HttpClient] 请求失败: {e}")
            raise
    
    @with_retry(max_retries=3, retry_delay=2)
    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        **kwargs
    ) -> requests.Response:
        """
        发送 POST 请求
        
        Args:
            url: 请求URL
            data: 表单数据
            json: JSON数据
            headers: 请求头
            timeout: 超时时间（秒）
            **kwargs: 其他 requests 参数
        
        Returns:
            Response 对象
        """
        self._wait_for_rate_limit()
        
        request_headers = dict(DEFAULT_HEADERS)
        if headers:
            request_headers.update(headers)
        
        log.debug(f"[HttpClient] POST {url}")
        
        try:
            response = self._session.post(
                url,
                data=data,
                json=json,
                headers=request_headers,
                timeout=timeout,
                **kwargs
            )
            response.raise_for_status()
            log.debug(f"[HttpClient] 响应: {response.status_code} ({len(response.text)} bytes)")
            return response
        except requests.exceptions.RequestException as e:
            log.error(f"[HttpClient] 请求失败: {e}")
            raise
    
    def fetch_html(self, url: str, encoding: Optional[str] = None) -> Optional[str]:
        """
        获取网页HTML内容
        
        Args:
            url: 目标URL
            encoding: 响应编码（可选，默认自动检测）
        
        Returns:
            HTML文本内容
        """
        try:
            response = self.get(url)
            if encoding:
                response.encoding = encoding
            return response.text
        except Exception as e:
            log.error(f"[HttpClient] 获取HTML失败: {e}")
            return None
    
    def fetch_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """
        获取 JSON 数据
        
        Args:
            url: 目标URL
            params: URL参数
        
        Returns:
            JSON解析后的数据
        """
        try:
            response = self.get(url, params=params)
            return response.json()
        except Exception as e:
            log.error(f"[HttpClient] 获取JSON失败: {e}")
            return None
    
    def close(self):
        """关闭会话"""
        if self._session:
            self._session.close()
            log.debug("[HttpClient] 会话已关闭")


# 模块级单例访问函数
_http_client: Optional[HttpClient] = None


def get_session() -> HttpClient:
    """获取 HTTP 客户端单例"""
    global _http_client
    if _http_client is None:
        _http_client = HttpClient()
    return _http_client


def fetch_html(url: str, encoding: Optional[str] = None) -> Optional[str]:
    """便捷函数：获取网页HTML"""
    return get_session().fetch_html(url, encoding)


def fetch_json(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """便捷函数：获取JSON数据"""
    return get_session().fetch_json(url, params)
