"""
现货价格爬虫
基于 BaseSpider 框架实现农业农村部等数据源的现货价格采集
"""

from datetime import date
from typing import Optional, List, Dict, Any

import yaml

from src.collectors.base.base_spider import BaseSpider
from src.collectors.utils.http_utils import get_session
from src.collectors.utils.parser_utils import (
    create_soup, parse_table_to_dict, parse_price, parse_date
)
from src.storage.database import SessionLocal
from src.storage.crud import create_spot_price
from src.utils.logger import log


class SpotPriceSpider(BaseSpider):
    """现货价格爬虫"""
    
    # 农业农村部官网价格页面URL
    MOA_PRICE_URL = "http://www.moa.gov.cn/"
    
    def __init__(self, use_local: bool = False):
        super().__init__(
            name="spot_price",
            use_local=use_local,
            save_raw_html=True,
            raw_html_dir="data/raw_html"
        )
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载爬虫配置"""
        config_path = "config/spider_config.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self.config = config.get("spot_price", {})
        except Exception as e:
            log.warning(f"[SpotPrice] 配置文件加载失败: {e}")
            self.config = {}
    
    def fetch(self) -> Optional[str]:
        """
        抓取网页HTML
        
        Returns:
            HTML内容
        """
        # 优先使用本地文件（开发测试用）
        if self.use_local:
            return self._load_local_html(suffix="农业农村部")
        
        client = get_session()
        
        # 农业农村部网站结构复杂，这里用示例URL
        # 实际项目中需要根据网站结构调整
        log.info("[SpotPrice] 开始抓取现货价格数据...")
        
        try:
            # 这里应该是实际的农业农村部价格页面
            # 由于网站结构需要抓包确认，暂时使用示例逻辑
            html = client.fetch_html(self.MOA_PRICE_URL)
            
            if html:
                self._save_raw_html(html, suffix="农业农村部")
            
            return html
        except Exception as e:
            log.error(f"[SpotPrice] 抓取失败: {e}")
            return None
    
    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        """
        解析HTML，提取现货价格数据
        
        Args:
            raw_data: HTML内容
        
        Returns:
            价格数据列表
        """
        if not raw_data:
            return []
        
        soup = create_soup(raw_data)
        
        # 尝试解析表格数据
        # 实际项目中需要根据网站结构调整选择器
        try:
            table_data = parse_table_to_dict(soup, table_index=0)
            
            if table_data:
                result = []
                for row in table_data:
                    # 根据实际表格结构调整字段映射
                    price_info = self._extract_price_info(row)
                    if price_info:
                        result.append(price_info)
                
                if result:
                    return result
        except Exception as e:
            log.debug(f"[SpotPrice] 表格解析失败: {e}")
        
        # 如果无法解析，返回空列表
        # 后续人工确认网站结构后更新解析逻辑
        log.error("[SpotPrice] 无法解析页面结构，返回空数据")
        return []
    
    def _extract_price_info(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        从表格行提取价格信息
        
        Args:
            row: 表格行字典
        
        Returns:
            标准化的价格数据
        """
        # 根据实际表格结构调整字段映射
        # 这里先做通用处理
        try:
            price_str = row.get("价格") or row.get("price") or ""
            price = parse_price(price_str)
            
            if price is None:
                return None
            
            # 确定品种分类
            category = self._detect_category(row)
            
            # 确定地区
            region = row.get("地区") or row.get("region") or "全国"
            
            return {
                "date": date.today(),
                "category": category,
                "region": region,
                "price": price,
                "unit": "元/500kg" if category == "egg" else "元/吨",
                "source": "农业农村部"
            }
        except Exception as e:
            log.debug(f"[SpotPrice] 提取价格信息失败: {e}")
            return None
    
    def _detect_category(self, row: Dict[str, str]) -> str:
        """
        检测品种分类
        
        Args:
            row: 表格行数据
        
        Returns:
            品种分类
        """
        # 尝试从品名字段检测
        name = row.get("品名") or row.get("name") or row.get("品种", "")
        
        name_lower = name.lower()
        
        if "鸡蛋" in name or "蛋" in name:
            return "egg"
        elif "玉米" in name:
            return "corn"
        elif "豆粕" in name or "粕" in name:
            return "soymeal"
        elif "鸡" in name:
            return "egg"
        
        return "egg"  # 默认鸡蛋
    
    def save(self, data: List[Dict[str, Any]]) -> int:
        """
        保存数据到数据库
        
        Args:
            data: 数据列表
        
        Returns:
            保存成功的记录数
        """
        if not data:
            return 0
        
        db = SessionLocal()
        saved_count = 0
        
        try:
            for item in data:
                try:
                    create_spot_price(db, item)
                    saved_count += 1
                except Exception as e:
                    log.error(f"[SpotPrice] 保存失败: {item}, error: {e}")
            
            db.commit()
            log.info(f"[SpotPrice] 成功保存 {saved_count} 条数据")
        except Exception as e:
            log.error(f"[SpotPrice] 数据库操作失败: {e}")
            db.rollback()
        finally:
            db.close()
        
        return saved_count


def collect_and_save_spot(use_local: bool = False) -> bool:
    """
    采集并保存现货价格（供调度器调用）
    
    Args:
        use_local: 是否使用本地文件
    
    Returns:
        是否成功
    """
    spider = SpotPriceSpider(use_local=use_local)
    return spider.run()


# 保留原有函数签名，兼容调度器
def collect_and_save_spot_original() -> List[Dict[str, Any]]:
    """
    原有接口，保留兼容性
    使用示例数据
    """
    log.info("[SpotPrice] 使用示例数据...")
    today = date.today()
    
    sample_data = [
        {"date": today, "category": "egg", "region": "山东", "price": 4200.0, "unit": "元/500kg", "source": "示例"},
        {"date": today, "category": "corn", "region": "全国", "price": 2800.0, "unit": "元/吨", "source": "示例"},
        {"date": today, "category": "soymeal", "region": "全国", "price": 3800.0, "unit": "元/吨", "source": "示例"},
    ]
    
    db = SessionLocal()
    saved_count = 0
    
    try:
        for data in sample_data:
            try:
                create_spot_price(db, data)
                saved_count += 1
            except Exception as e:
                log.error(f"[SpotPrice] 保存失败: {e}")
        
        db.commit()
        log.info(f"[SpotPrice] 保存 {saved_count} 条示例数据")
    except Exception as e:
        log.error(f"[SpotPrice] 操作失败: {e}")
        db.rollback()
    finally:
        db.close()
    
    return sample_data


# 如果直接运行脚本，执行测试
if __name__ == "__main__":
    print("现货价格爬虫测试")
    print("=" * 50)
    
    # 测试使用本地文件模式
    result = collect_and_save_spot(use_local=False)
    
    if result:
        print("采集成功")
    else:
        print("采集失败或无数据")
