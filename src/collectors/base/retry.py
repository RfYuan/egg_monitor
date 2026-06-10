"""
重试装饰器模块
处理网络异常，自动重试
"""

import time
import functools
from typing import Callable, Tuple, Type

import requests

from src.utils.logger import log


# 默认重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2  # 秒
DEFAULT_RETRY_BACKOFF = 2  # 指数退避因子

# 默认捕获的异常类型
DEFAULT_RETRY_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.HTTPError,
)


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    backoff_factor: float = DEFAULT_RETRY_BACKOFF,
    exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRY_EXCEPTIONS,
    retry_on_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)
) -> Callable:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟（秒）
        backoff_factor: 指数退避因子（每次重试延迟 = delay * backoff^attempt）
        exceptions: 需要重试的异常类型元组
        retry_on_status_codes: 需要重试的HTTP状态码
    
    Returns:
        装饰器函数
    
    Example:
        @with_retry(max_retries=3, retry_delay=2)
        def fetch_data(url):
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # 计算延迟时间（指数退避）
                        delay = retry_delay * (backoff_factor ** attempt)
                        
                        # 如果是429状态码（请求过于频繁），等待更长时间
                        if isinstance(e, requests.exceptions.HTTPError):
                            if e.response is not None and e.response.status_code == 429:
                                delay = max(delay, 60)  # 至少等60秒
                        
                        log.warning(
                            f"[Retry] {func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}), "
                            f"{delay:.1f}秒后重试: {e}"
                        )
                        time.sleep(delay)
                    else:
                        log.error(f"[Retry] {func.__name__} 已达最大重试次数 ({max_retries + 1})")
            
            # 所有重试都失败，抛出最后异常
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_on_condition(
    condition: Callable[[any], bool],
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY
) -> Callable:
    """
    条件重试装饰器 - 当函数返回满足条件时重试
    
    Args:
        condition: 条件函数，返回True时表示需要重试
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    
    Returns:
        装饰器函数
    
    Example:
        @retry_on_condition(condition=lambda r: r is None or r.status_code != 200)
        def fetch_data(url):
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_result = None
            
            for attempt in range(max_retries + 1):
                result = func(*args, **kwargs)
                last_result = result
                
                if not condition(result):
                    return result
                
                if attempt < max_retries:
                    log.warning(
                        f"[Retry] {func.__name__} 条件不满足 (尝试 {attempt + 1}/{max_retries + 1}), "
                        f"{retry_delay}秒后重试"
                    )
                    time.sleep(retry_delay)
            
            log.error(f"[Retry] {func.__name__} 已达最大重试次数 ({max_retries + 1})")
            return last_result
        
        return wrapper
    return decorator
