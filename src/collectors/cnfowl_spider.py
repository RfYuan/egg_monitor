"""
养殖网现货价格爬虫
数据源: https://www.cnfowl.com/quote/
支持鸡蛋、玉米、豆粕、淘汰禽价格采集
"""

import re
from datetime import date
from typing import Optional, List, Dict, Any

from src.collectors.base.base_spider import BaseSpider
from src.collectors.utils.http_utils import get_session
from src.collectors.utils.parser_utils import create_soup, parse_price, parse_table_to_dict
from src.storage.database import SessionLocal
from src.storage.crud import create_spot_price
from src.utils.logger import log


class CnfowlSpider(BaseSpider):
    """养殖网爬虫"""
    
    BASE_URL = "https://www.cnfowl.com"
    QUOTE_URL = "https://www.cnfowl.com/quote/"
    
    def __init__(self, use_local: bool = False):
        super().__init__(
            name="cnfowl",
            use_local=use_local,
            save_raw_html=True,
            raw_html_dir="data/raw_html"
        )
        
    def fetch(self) -> Optional[str]:
        """
        抓取行情列表页
        """
        if self.use_local:
            return self._load_local_html(suffix="养殖网首页")
        
        client = get_session()
        log.info("[Cnfowl] 开始抓取养殖网行情首页...")
        
        try:
            html = client.fetch_html(self.QUOTE_URL)
            if html:
                self._save_raw_html(html, suffix="养殖网首页")
            return html
        except Exception as e:
            log.error(f"[Cnfowl] 抓取首页失败: {e}")
            return None
    
    def parse(self, raw_data: str) -> List[Dict[str, Any]]:
        """
        解析首页，提取价格详情页链接
        """
        if not raw_data:
            return []
        
        result = []
        
        # 用正则提取今日价格链接
        # 鸡蛋价格链接
        egg_links = self._extract_links(raw_data, r'<a[^>]*href="([^"]*show-\d+\.html)"[^>]*title="[^"]*鸡蛋[^"]*"')
        # 玉米价格链接
        corn_links = self._extract_links(raw_data, r'<a[^>]*href="([^"]*show-\d+\.html)"[^>]*title="[^"]*玉米[^"]*"')
        # 豆粕价格链接
        meal_links = self._extract_links(raw_data, r'<a[^>]*href="([^"]*show-\d+\.html)"[^>]*title="[^"]*豆粕[^"]*"')
        # 淘汰禽价格链接
        eliminate_links = self._extract_links(raw_data, r'<a[^>]*href="([^"]*show-\d+\.html)"[^>]*title="[^"]*淘汰[^"]*"')
        
        log.info(f"[Cnfowl] 找到鸡蛋:{len(egg_links)} 玉米:{len(corn_links)} 豆粕:{len(meal_links)} 淘汰禽:{len(eliminate_links)}")
        
        # 抓取今日详情页数据
        today = date.today().strftime("%Y-%m-%d")
        
        # 鸡蛋价格
        if egg_links:
            egg_data = self._parse_detail_page(egg_links[0], "egg", today)
            if egg_data:
                result.extend(egg_data)
        
        # 玉米价格
        if corn_links:
            corn_data = self._parse_detail_page(corn_links[0], "corn", today)
            if corn_data:
                result.extend(corn_data)
        
        # 豆粕价格
        if meal_links:
            meal_data = self._parse_detail_page(meal_links[0], "soymeal", today)
            if meal_data:
                result.extend(meal_data)
        
        # 淘汰禽价格
        if eliminate_links:
            eliminate_data = self._parse_detail_page(eliminate_links[0], "eliminate", today)
            if eliminate_data:
                result.extend(eliminate_data)
        
        return result
    
    def _extract_links(self, html: str, pattern: str) -> List[str]:
        """
        用正则提取链接
        """
        matches = re.findall(pattern, html)
        # 去重并转换为完整URL
        unique_links = []
        seen = set()
        for link in matches:
            full_url = self.BASE_URL + link if link.startswith('/') else link
            if full_url not in seen:
                seen.add(full_url)
                unique_links.append(full_url)
        return unique_links
    
    def _parse_detail_page(self, url: str, category: str, date_str: str) -> List[Dict[str, Any]]:
        """
        解析详情页获取价格数据
        """
        log.info(f"[Cnfowl] 抓取详情页: {url}")
        
        try:
            client = get_session()
            html = client.fetch_html(url)
            
            if not html:
                return []
            
            # 保存详情页HTML
            suffix = f"{category}_detail"
            self._save_raw_html(html, suffix=suffix)
            
            # 解析HTML提取价格数据
            data = self._extract_price_from_detail(html, category, date_str)
            return data
            
        except Exception as e:
            log.error(f"[Cnfowl] 解析详情页失败 {url}: {e}")
            return []
    
    def _extract_price_from_detail(self, html: str, category: str, date_str: str) -> List[Dict[str, Any]]:
        """
        从详情页提取价格数据
        """
        soup = create_soup(html)
        
        # 获取标题中的日期
        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else ""
        
        # 查找价格数据区域
        content = soup.find('div', class_='content')
        if not content:
            content = soup.find('div', class_='quote-content')
        
        if not content:
            log.warning(f"[Cnfowl] 未找到内容区域: {category}")
            return []
        
        # 直接解析表格（处理跨行合并）
        tables = soup.find_all('table')
        if not tables:
            log.warning(f"[Cnfowl] 未找到表格: {category}")
            return []
        
        table = tables[0]
        rows = table.find_all('tr')
        
        if not rows:
            log.warning(f"[Cnfowl] 表格为空: {category}")
            return []
        
        # 获取表头
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # 确定列索引
        region_idx = None
        province_idx = None
        price_idx = None
        
        for i, header in enumerate(headers):
            if "区域" in header:
                region_idx = i
            elif any(k in header for k in ["省", "市"]):
                province_idx = i
            elif re.match(r'\d{2}-\d{2}', header) or "价格" in header:
                price_idx = i
        
        if province_idx is None or price_idx is None:
            log.warning(f"[Cnfowl] 无法确定列索引: {category}, headers: {headers}")
            return []
        
        # 解析数据行
        result = []
        current_region = ""
        
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # 处理跨行合并：如果列数少于表头，说明有合并单元格
            if len(cell_texts) == len(headers):
                # 正常行
                if region_idx is not None and region_idx < len(cell_texts):
                    region = cell_texts[region_idx]
                    if region:
                        current_region = region
                province = cell_texts[province_idx]
                price_str = cell_texts[price_idx]
            else:
                # 跨行合并的行，区域使用上一行的区域
                # 单元格可能错位，需要根据实际情况处理
                if region_idx == 0 and len(cell_texts) == len(headers) - 1:
                    # 区域被合并了，单元格整体左移一位
                    province = cell_texts[province_idx - 1] if (province_idx - 1) < len(cell_texts) else ""
                    price_str = cell_texts[price_idx - 1] if (price_idx - 1) < len(cell_texts) else ""
                else:
                    continue
            
            # 跳过无效数据
            if not province or not price_str or province == "均价":
                continue
            
            # 跳过纯数字的"省市名"（可能是跨行合并导致的错位）
            if province.isdigit():
                continue
            
            # 解析价格
            price = parse_price(price_str)
            if price is None:
                continue
            
            # 确定单位（根据品类）并进行单位转换
            unit = self._get_default_unit(category)
            
            # 鸡蛋和淘汰禽价格需要乘以1000（从元/斤转换为元/500kg）
            if category in ["egg", "eliminate"]:
                price = price * 1000
            
            result.append({
                "date": date_str,
                "category": category,
                "region": province,
                "price": price,
                "unit": unit,
                "source": "养殖网"
            })
        
        # 如果没有解析到数据，尝试从meta description提取
        if not result:
            result = self._extract_from_meta_description(html, category, date_str)
        
        log.info(f"[Cnfowl] 从详情页提取到 {len(result)} 条数据")
        return result
    
    def _extract_from_meta_description(self, html: str, category: str, date_str: str) -> List[Dict[str, Any]]:
        """
        从meta description标签提取价格数据（备用方案）
        """
        result = []
        
        # 提取description内容
        desc_pattern = r'<meta name="description" content="([^"]+)"'
        match = re.search(desc_pattern, html)
        if not match:
            return result
        
        desc = match.group(1)
        
        # 尝试解析描述中的价格数据
        # 模式: 省市名+数字价格（如"辽宁4.96"）
        # 先找到区域分隔符
        regions = ["东北", "华北", "华东", "华中", "华南", "西北", "西南"]
        price_pattern = r'([\u4e00-\u9fa5]{2,4})(\d+\.?\d*)'
        
        matches = re.findall(price_pattern, desc)
        for province, price_str in matches:
            # 跳过区域名称
            if province in regions:
                continue
            
            # 跳过"均价"等非省市名称
            if province in ["均价", "区域", "价格", "涨跌"]:
                continue
            
            price = parse_price(price_str)
            if price is None:
                continue
            
            unit = self._get_default_unit(category)
            
            result.append({
                "date": date_str,
                "category": category,
                "region": province,
                "price": price,
                "unit": unit,
                "source": "养殖网"
            })
        
        return result
    
    def _get_default_unit(self, category: str) -> str:
        """
        根据品类获取默认单位
        """
        if category == "egg":
            return "元/500kg"
        elif category == "eliminate":
            return "元/500kg"
        else:
            return "元/吨"
    
    def _normalize_unit(self, unit: str, category: str) -> str:
        """
        标准化单位
        """
        unit = unit.lower()
        if '吨' in unit:
            return "元/吨"
        elif '500kg' in unit or '斤' in unit:
            return "元/500kg"
        elif 'kg' in unit:
            return "元/吨"  # 默认转换为吨
        else:
            # 根据品类默认
            return "元/500kg" if category == "egg" else "元/吨"
    
    def save(self, data: List[Dict[str, Any]]) -> int:
        """
        保存数据到数据库
        """
        if not data:
            return 0
        
        db = SessionLocal()
        saved_count = 0
        
        try:
            for item in data:
                try:
                    # 转换日期格式
                    if isinstance(item.get("date"), str):
                        from datetime import datetime
                        item["date"] = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    
                    create_spot_price(db, item)
                    saved_count += 1
                except Exception as e:
                    log.error(f"[Cnfowl] 保存失败: {item}, error: {e}")
            
            db.commit()
            log.info(f"[Cnfowl] 成功保存 {saved_count} 条数据")
        except Exception as e:
            log.error(f"[Cnfowl] 数据库操作失败: {e}")
            db.rollback()
        finally:
            db.close()
        
        return saved_count


def collect_cnfowl_spot(use_local: bool = False) -> bool:
    """
    采集养殖网现货价格
    """
    spider = CnfowlSpider(use_local=use_local)
    return spider.run()


# 测试
if __name__ == "__main__":
    print("养殖网爬虫测试")
    print("=" * 50)
    
    # 测试使用网络模式
    result = collect_cnfowl_spot(use_local=False)
    print(f"采集结果: {'成功' if result else '失败'}")
