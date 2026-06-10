"""
爬虫基类模块
提供统一的爬虫接口和生命周期管理
"""

from src.collectors.base.base_spider import BaseSpider
from src.collectors.base.retry import with_retry
from src.collectors.base.data_validator import DataValidator

__all__ = ["BaseSpider", "with_retry", "DataValidator"]
