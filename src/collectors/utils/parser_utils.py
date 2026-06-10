"""
解析工具模块
提供 BeautifulSoup 常用解析方法
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from bs4 import BeautifulSoup, Tag, ResultSet

from src.utils.logger import log


def create_soup(html: str, parser: str = "lxml") -> BeautifulSoup:
    """
    创建 BeautifulSoup 解析器
    
    Args:
        html: HTML内容
        parser: 解析器类型（lxml, html.parser, html5lib）
    
    Returns:
        BeautifulSoup 对象
    """
    return BeautifulSoup(html, parser)


def parse_table(
    soup: BeautifulSoup,
    table_index: int = 0,
    headers_row: int = 0,
    skip_empty_rows: bool = True
) -> Tuple[List[str], List[List[str]]]:
    """
    解析 HTML 表格
    
    Args:
        soup: BeautifulSoup 对象
        table_index: 表格索引（从0开始）
        headers_row: 表头所在行（默认第0行）
        skip_empty_rows: 是否跳过空行
    
    Returns:
        (表头列表, 数据行列表)
    """
    tables = soup.find_all("table")
    
    if not tables or table_index >= len(tables):
        log.warning(f"[Parser] 未找到表格，索引: {table_index}")
        return [], []
    
    table = tables[table_index]
    rows = table.find_all("tr")
    
    if not rows:
        return [], []
    
    # 解析表头
    header_cells = rows[headers_row].find_all(["th", "td"])
    headers = [cell.get_text(strip=True) for cell in header_cells]
    
    # 解析数据行
    data_rows = []
    for row in rows[headers_row + 1:]:
        cells = row.find_all(["th", "td"])
        if skip_empty_rows and not any(cell.get_text(strip=True) for cell in cells):
            continue
        
        row_data = [cell.get_text(strip=True) for cell in cells]
        if row_data:
            data_rows.append(row_data)
    
    log.debug(f"[Parser] 解析表格: {len(headers)} 列, {len(data_rows)} 行")
    return headers, data_rows


def parse_table_to_dict(
    soup: BeautifulSoup,
    table_index: int = 0,
    headers_row: int = 0
) -> List[Dict[str, str]]:
    """
    解析表格为字典列表
    
    Args:
        soup: BeautifulSoup 对象
        table_index: 表格索引
        headers_row: 表头行
    
    Returns:
        字典列表，每行一个字典
    """
    headers, data_rows = parse_table(soup, table_index, headers_row)
    
    if not headers or not data_rows:
        return []
    
    result = []
    for row in data_rows:
        row_dict = {}
        for i, header in enumerate(headers):
            if i < len(row):
                row_dict[header] = row[i]
            else:
                row_dict[header] = ""
        result.append(row_dict)
    
    return result


def parse_price(price_str: str) -> Optional[float]:
    """
    解析价格字符串
    
    Args:
        price_str: 价格字符串，如 "4,320.00" 或 "4320元/吨"
    
    Returns:
        解析后的价格数值，或 None
    """
    if not price_str:
        return None
    
    # 去除空格和常见单位
    cleaned = price_str.strip()
    cleaned = re.sub(r"[\s,，元/吨斤万百千亿个每]+", "", cleaned)
    
    # 处理"万"等单位
    multiplier = 1.0
    if "万" in price_str:
        multiplier = 10000.0
        cleaned = cleaned.replace("万", "")
    elif "千" in price_str:
        multiplier = 1000.0
        cleaned = cleaned.replace("千", "")
    
    # 提取数字
    numbers = re.findall(r"[-+]?\d*\.?\d+", cleaned)
    if not numbers:
        return None
    
    try:
        return float(numbers[0]) * multiplier
    except (ValueError, IndexError):
        return None


def parse_percentage(pct_str: str) -> Optional[float]:
    """
    解析百分比字符串
    
    Args:
        pct_str: 百分比字符串，如 "+2.35%" 或 "-1.5%"
    
    Returns:
        解析后的百分比数值，或 None
    """
    if not pct_str:
        return None
    
    # 去除空格和百分号
    cleaned = pct_str.strip().replace("%", "").replace("％", "")
    
    # 处理带括号表示负数的情况，如 "(2.35)" -> "-2.35"
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str: str) -> Optional[str]:
    """
    解析日期字符串为标准格式
    
    Args:
        date_str: 日期字符串
    
    Returns:
        标准格式日期字符串 "YYYY-MM-DD"，或 None
    """
    if not date_str:
        return None
    
    # 清理日期字符串
    cleaned = date_str.strip()
    
    # 尝试多种格式
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y年%m月%d日",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # 尝试正则提取
    patterns = [
        r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?",
        r"(\d{4})(\d{2})(\d{2})",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            try:
                year, month, day = match.groups()
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    
    return None


def extract_text(element: Tag, selector: str, default: str = "") -> str:
    """
    使用 CSS 选择器提取文本
    
    Args:
        element: BeautifulSoup 元素
        selector: CSS 选择器
        default: 默认值
    
    Returns:
        提取的文本
    """
    found = element.select_one(selector)
    return found.get_text(strip=True) if found else default


def extract_links(element: Tag, selector: str = "a") -> List[Tuple[str, str]]:
    """
    提取链接列表
    
    Args:
        element: BeautifulSoup 元素
        selector: 链接选择器
    
    Returns:
        [(链接文本, URL), ...]
    """
    links = []
    for a in element.select(selector):
        text = a.get_text(strip=True)
        href = a.get("href", "")
        if text and href:
            links.append((text, href))
    return links


def find_by_keywords(element: Tag, keywords: List[str], selector: str = "*") -> List[Tag]:
    """
    根据关键词查找元素
    
    Args:
        element: BeautifulSoup 元素
        keywords: 关键词列表（满足任一即匹配）
        selector: 选择器
    
    Returns:
        匹配的元素列表
    """
    results = []
    for tag in element.select(selector):
        text = tag.get_text(strip=True)
        if any(kw in text for kw in keywords):
            results.append(tag)
    return results
