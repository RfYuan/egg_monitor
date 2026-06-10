"""
数据校验器模块
验证数据完整性和合理性
"""

from typing import Dict, Any, List, Optional
from datetime import date, datetime

from src.utils.logger import log


class DataValidator:
    """
    数据校验器
    
    提供通用的数据校验方法：
    - 必填字段检查
    - 数据类型验证
    - 数值范围校验
    - 日期格式验证
    """
    
    # 品种分类枚举
    CATEGORIES = {"egg", "corn", "soymeal", "eliminate"}
    
    # 地区枚举
    REGIONS = {"山东", "全国", "河南", "河北", "江苏", "湖北", "广东"}
    
    # 合理价格范围（元/单位）
    PRICE_RANGES = {
        "egg": (3000, 8000),      # 鸡蛋：3000-8000元/500kg
        "corn": (2000, 3500),     # 玉米：2000-3500元/吨
        "soymeal": (2500, 5000),  # 豆粕：2500-5000元/吨
    }
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> bool:
        """
        验证单条数据
        
        Args:
            data: 待验证的数据字典
        
        Returns:
            数据是否有效
        """
        # 必填字段检查
        required_fields = ["date", "category", "price"]
        for field in required_fields:
            if field not in data or data[field] is None:
                log.debug(f"[Validator] 缺少必填字段: {field}")
                return False
        
        # 品种分类验证
        if data.get("category") not in cls.CATEGORIES:
            log.debug(f"[Validator] 无效品种分类: {data.get('category')}")
            return False
        
        # 价格类型和范围验证
        price = data.get("price")
        if not isinstance(price, (int, float)):
            try:
                price = float(price)
            except (ValueError, TypeError):
                log.debug(f"[Validator] 价格格式无效: {price}")
                return False
        
        category = data.get("category")
        if category in cls.PRICE_RANGES:
            min_price, max_price = cls.PRICE_RANGES[category]
            if not (min_price <= price <= max_price):
                log.debug(f"[Validator] 价格超出合理范围: {price} (期望 {min_price}-{max_price})")
                return False
        
        return True
    
    @classmethod
    def validate_batch(cls, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量验证数据
        
        Args:
            data_list: 数据列表
        
        Returns:
            有效数据列表（无效数据被过滤）
        """
        valid_data = []
        invalid_count = 0
        
        for data in data_list:
            if cls.validate(data):
                valid_data.append(data)
            else:
                invalid_count += 1
        
        if invalid_count > 0:
            log.warning(f"[Validator] 批量验证：过滤 {invalid_count} 条无效数据，保留 {len(valid_data)} 条")
        
        return valid_data
    
    @classmethod
    def check_date(cls, date_value: Any) -> Optional[date]:
        """
        验证并转换日期
        
        Args:
            date_value: 日期值（可为 date, str, datetime）
        
        Returns:
            date对象或None
        """
        if isinstance(date_value, date):
            return date_value
        
        if isinstance(date_value, datetime):
            return date_value.date()
        
        if isinstance(date_value, str):
            # 尝试多种日期格式
            formats = ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%Y-%d-%m"]
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt).date()
                except ValueError:
                    continue
        
        log.debug(f"[Validator] 无法解析日期: {date_value}")
        return None
    
    @classmethod
    def check_price_range(cls, category: str, price: float) -> bool:
        """
        检查价格是否在合理范围内
        
        Args:
            category: 品种分类
            price: 价格
        
        Returns:
            是否在合理范围
        """
        if category not in cls.PRICE_RANGES:
            return True  # 未知分类不校验
        
        min_price, max_price = cls.PRICE_RANGES[category]
        return min_price <= price <= max_price
    
    @classmethod
    def check_mom_yoy(cls, value: Optional[float]) -> bool:
        """
        检查环比/同比值是否合理
        
        Args:
            value: 环比或同比值（百分比）
        
        Returns:
            是否合理
        """
        if value is None:
            return True
        
        # 环比/同比合理范围：-50% 到 +50%
        return -50 <= value <= 50
