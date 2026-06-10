"""
BaseSpider - 爬虫基类
定义统一的爬虫接口和生命周期管理
"""

import os
import hashlib
from datetime import datetime, date
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from src.utils.logger import log


class BaseSpider(ABC):
    """
    爬虫基类
    
    职责：
    - 定义统一的爬虫接口
    - 管理爬虫生命周期（fetch -> parse -> validate -> save）
    - 支持本地文件模式（开发测试用）
    """
    
    def __init__(
        self,
        name: str,
        use_local: bool = False,
        save_raw_html: bool = True,
        raw_html_dir: str = "data/raw_html"
    ):
        """
        初始化爬虫
        
        Args:
            name: 爬虫名称（用于日志和目录命名）
            use_local: 是否使用本地文件模式（开发测试用）
            save_raw_html: 是否保存原始HTML
            raw_html_dir: 原始HTML存储目录
        """
        self.name = name
        self.use_local = use_local
        self.save_raw_html = save_raw_html
        self.raw_html_dir = raw_html_dir
        
        # 确保目录存在
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保目录存在"""
        if self.save_raw_html:
            path = os.path.join(self.raw_html_dir, self.name)
            os.makedirs(path, exist_ok=True)
    
    def _get_raw_html_path(self, suffix: str = "") -> str:
        """
        获取原始HTML文件路径
        
        Args:
            suffix: 文件后缀，如 "农业农村部"
        
        Returns:
            完整的文件路径
        """
        today_str = date.today().strftime("%Y-%m-%d")
        if suffix:
            filename = f"{today_str}_{suffix}.html"
        else:
            filename = f"{today_str}_{self.name}.html"
        return os.path.join(self.raw_html_dir, self.name, filename)
    
    def _save_raw_html(self, html: str, suffix: str = "") -> str:
        """
        保存原始HTML到本地
        
        Args:
            html: HTML内容
            suffix: 文件后缀
        
        Returns:
            保存的文件路径
        """
        if not self.save_raw_html or not html:
            return ""
        
        filepath = self._get_raw_html_path(suffix)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            log.debug(f"[{self.name}] 原始HTML已保存: {filepath}")
        except Exception as e:
            log.warning(f"[{self.name}] 保存原始HTML失败: {e}")
        
        return filepath
    
    def _load_local_html(self, suffix: str = "") -> Optional[str]:
        """
        从本地加载HTML文件
        
        Args:
            suffix: 文件后缀
        
        Returns:
            HTML内容，如果文件不存在返回None
        """
        filepath = self._get_raw_html_path(suffix)
        if not os.path.exists(filepath):
            log.warning(f"[{self.name}] 本地文件不存在: {filepath}")
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html = f.read()
            log.info(f"[{self.name}] 从本地加载HTML: {filepath}")
            return html
        except Exception as e:
            log.error(f"[{self.name}] 读取本地文件失败: {e}")
            return None
    
    @abstractmethod
    def fetch(self) -> Optional[str]:
        """
        抓取数据 - 子类实现
        
        Returns:
            原始HTML内容或API响应数据
        """
        raise NotImplementedError
    
    @abstractmethod
    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        """
        解析数据 - 子类实现
        
        Args:
            raw_data: fetch返回的原始数据
        
        Returns:
            解析后的数据列表
        """
        raise NotImplementedError
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        校验数据
        
        Args:
            data: 单条数据
        
        Returns:
            数据是否有效
        """
        from src.collectors.base.data_validator import DataValidator
        return DataValidator.validate(data)
    
    def save(self, data: List[Dict[str, Any]]) -> int:
        """
        保存数据
        
        Args:
            data: 数据列表
        
        Returns:
            保存成功的记录数
        """
        # 子类可重写此方法
        return len(data)
    
    def run(self) -> bool:
        """
        执行完整流程
        
        Returns:
            是否执行成功
        """
        log.info(f"[{self.name}] 爬虫启动")
        
        # 1. 获取数据
        raw_data = self.fetch()
        if not raw_data:
            log.error(f"[{self.name}] 数据获取失败")
            return False
        
        # 2. 解析数据
        parsed_data = self.parse(raw_data)
        if not parsed_data:
            log.warning(f"[{self.name}] 无解析数据")
            return False
        
        log.info(f"[{self.name}] 解析到 {len(parsed_data)} 条数据")
        
        # 3. 校验并保存
        valid_data = [d for d in parsed_data if self.validate(d)]
        if len(valid_data) < len(parsed_data):
            invalid_count = len(parsed_data) - len(valid_data)
            log.warning(f"[{self.name}] 过滤掉 {invalid_count} 条无效数据")
        
        if not valid_data:
            log.error(f"[{self.name}] 无有效数据可保存")
            return False
        
        saved_count = self.save(valid_data)
        log.info(f"[{self.name}] 保存成功 {saved_count} 条数据")
        
        return saved_count > 0
