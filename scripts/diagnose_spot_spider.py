"""
现货价格爬虫诊断脚本

用于对比本地和服务器环境差异，定位爬虫失败原因。

诊断项目：
1. 网络连接测试
2. HTML内容对比
3. 请求头检查
4. 解析结果对比
5. 反爬虫检测
"""

import os
import sys
from datetime import date
import requests
from bs4 import BeautifulSoup

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.utils.http_utils import get_session
from src.utils.logger import log


def diagnose_network():
    """诊断网络连接"""
    print("\n" + "=" * 60)
    print("【诊断1】网络连接测试")
    print("=" * 60)
    
    test_urls = [
        ("养殖网首页", "https://www.cnfowl.com/quote/"),
        ("百度（基准）", "https://www.baidu.com"),
        ("大商所官网", "http://www.dce.com.cn"),
    ]
    
    for name, url in test_urls:
        try:
            print(f"\n测试 {name}: {url}")
            response = requests.get(url, timeout=10)
            print(f"  ✓ 状态码: {response.status_code}")
            print(f"  ✓ 内容长度: {len(response.text)} 字符")
            print(f"  ✓ 响应时间: {response.elapsed.total_seconds():.2f} 秒")
            
            # 检查是否有反爬虫标识
            if "验证" in response.text or "blocked" in response.text.lower():
                print(f"  ⚠️ 可能触发反爬虫机制")
            
        except requests.exceptions.Timeout:
            print(f"  ✗ 超时（>10秒）")
        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ 连接失败: {e}")
        except Exception as e:
            print(f"  ✗ 异常: {e}")


def diagnose_html_content():
    """诊断HTML内容"""
    print("\n" + "=" * 60)
    print("【诊断2】HTML内容对比")
    print("=" * 60)
    
    url = "https://www.cnfowl.com/quote/"
    
    try:
        print(f"\n抓取首页: {url}")
        client = get_session()
        html = client.fetch_html(url)
        
        if not html:
            print("  ✗ HTML获取失败")
            return
        
        print(f"  ✓ HTML长度: {len(html)} 字符")
        
        # 保存HTML到文件
        output_file = "data/diagnose/cnfowl_homepage.html"
        os.makedirs("data/diagnose", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ HTML已保存到: {output_file}")
        
        # 检查关键元素
        soup = BeautifulSoup(html, 'html.parser')
        
        # 检查标题
        title = soup.find('title')
        print(f"\n  页面标题: {title.get_text() if title else '未找到'}")
        
        # 检查表格
        tables = soup.find_all('table')
        print(f"  找到表格数量: {len(tables)}")
        
        # 检查链接
        links = soup.find_all('a')
        print(f"  找到链接数量: {len(links)}")
        
        # 检查是否有价格相关内容
        price_keywords = ["鸡蛋", "玉米", "豆粕", "淘汰", "价格"]
        found_keywords = []
        for keyword in price_keywords:
            if keyword in html:
                found_keywords.append(keyword)
        
        print(f"  价格关键词: {found_keywords}")
        
        # 检查是否有JavaScript渲染内容
        if "<script" in html:
            print(f"  ⚠️ 页面包含JavaScript，可能需要动态渲染")
        
        # 检查是否有验证码或反爬虫
        anti_keywords = ["验证码", "验证", "blocked", "captcha", "robot"]
        found_anti = []
        for keyword in anti_keywords:
            if keyword.lower() in html.lower():
                found_anti.append(keyword)
        
        if found_anti:
            print(f"  ⚠️ 反爬虫关键词: {found_anti}")
        
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        import traceback
        traceback.print_exc()


def diagnose_request_headers():
    """诊断请求头"""
    print("\n" + "=" * 60)
    print("【诊断3】请求头检查")
    print("=" * 60)
    
    url = "https://www.cnfowl.com/quote/"
    
    # 测试不同的请求头配置
    headers_configs = [
        ("默认请求头", {}),
        ("浏览器请求头", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }),
        ("移动端请求头", {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        }),
    ]
    
    for name, headers in headers_configs:
        try:
            print(f"\n测试 {name}:")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  ✓ 状态码: {response.status_code}")
            print(f"  ✓ 内容长度: {len(response.text)} 字符")
            
            # 检查响应头
            print(f"  响应头:")
            for key in ["Content-Type", "Server", "X-Frame-Options", "Set-Cookie"]:
                if key in response.headers:
                    print(f"    {key}: {response.headers[key]}")
            
        except Exception as e:
            print(f"  ✗ 异常: {e}")


def diagnose_detail_page():
    """诊断详情页解析"""
    print("\n" + "=" * 60)
    print("【诊断4】详情页解析测试")
    print("=" * 60)
    
    # 测试详情页链接（使用已知存在的链接）
    test_urls = [
        ("鸡蛋详情页", "https://www.cnfowl.com/show-70571.html"),
        ("玉米详情页", "https://www.cnfowl.com/show-70572.html"),
    ]
    
    for name, url in test_urls:
        try:
            print(f"\n测试 {name}: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"  ✗ 状态码: {response.status_code}")
                continue
            
            print(f"  ✓ 状态码: {response.status_code}")
            print(f"  ✓ 内容长度: {len(response.text)} 字符")
            
            # 保存HTML
            output_file = f"data/diagnose/{name.replace(' ', '_')}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"  ✓ HTML已保存到: {output_file}")
            
            # 解析表格
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            print(f"  找到表格数量: {len(tables)}")
            
            if tables:
                # 解析第一个表格
                table = tables[0]
                rows = table.find_all('tr')
                print(f"  表格行数: {len(rows)}")
                
                # 显示前3行内容
                for i, row in enumerate(rows[:3]):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    print(f"    行{i}: {cell_texts}")
            
        except Exception as e:
            print(f"  ✗ 异常: {e}")


def diagnose_spider_logic():
    """诊断爬虫逻辑"""
    print("\n" + "=" * 60)
    print("【诊断5】爬虫逻辑测试")
    print("=" * 60)
    
    try:
        from src.collectors.cnfowl_spider import CnfowlSpider
        
        print("\n初始化爬虫...")
        spider = CnfowlSpider(use_local=False)
        
        print("\n测试 fetch()...")
        html = spider.fetch()
        
        if html:
            print(f"  ✓ fetch() 成功，HTML长度: {len(html)}")
        else:
            print(f"  ✗ fetch() 失败")
            return
        
        print("\n测试 parse()...")
        data = spider.parse(html)
        
        if data:
            print(f"  ✓ parse() 成功，解析到 {len(data)} 条数据")
            print(f"  数据示例:")
            for item in data[:3]:
                print(f"    {item}")
        else:
            print(f"  ✗ parse() 失败，未解析到数据")
        
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        import traceback
        traceback.print_exc()


def diagnose_environment():
    """诊断环境信息"""
    print("\n" + "=" * 60)
    print("【诊断6】环境信息")
    print("=" * 60)
    
    import platform
    
    print(f"\n操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    print(f"机器架构: {platform.machine()}")
    
    # 检查requests版本
    try:
        import requests
        print(f"requests版本: {requests.__version__}")
    except:
        print("requests未安装")
    
    # 检查BeautifulSoup版本
    try:
        import bs4
        print(f"BeautifulSoup版本: {bs4.__version__}")
    except:
        print("BeautifulSoup未安装")
    
    # 检查网络代理
    print(f"\nHTTP代理: {os.environ.get('HTTP_PROXY', '未设置')}")
    print(f"HTTPS代理: {os.environ.get('HTTPS_PROXY', '未设置')}")


def main():
    """运行所有诊断"""
    print("\n" + "=" * 60)
    print("现货价格爬虫诊断工具")
    print("=" * 60)
    print(f"运行时间: {date.today()}")
    
    # 创建诊断目录
    os.makedirs("data/diagnose", exist_ok=True)
    
    # 运行所有诊断
    diagnose_environment()
    diagnose_network()
    diagnose_html_content()
    diagnose_request_headers()
    diagnose_detail_page()
    diagnose_spider_logic()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
    print("\n诊断文件已保存到: data/diagnose/")
    print("请对比本地和服务器环境的差异")


if __name__ == "__main__":
    main()