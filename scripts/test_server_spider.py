"""
服务器爬虫测试脚本 - 验证IPv4修复

运行方式: python scripts/test_server_spider.py
"""

import os
import sys
import socket
import requests

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 先测试原始socket行为
print("=" * 60)
print("【测试1】原始socket解析行为")
print("=" * 60)

domain = "www.cnfowl.com"

try:
    # 原始getaddrinfo（可能返回IPv6）
    print(f"\n原始 getaddrinfo({domain}, 443):")
    results = socket.getaddrinfo(domain, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
    for res in results:
        family, socktype, proto, canonname, sockaddr = res
        family_name = "IPv6" if family == socket.AF_INET6 else "IPv4"
        print(f"  {family_name}: {sockaddr}")
except Exception as e:
    print(f"  错误: {e}")

# 强制IPv4
print("\n" + "=" * 60)
print("【测试2】强制IPv4后解析行为")
print("=" * 60)

orig_getaddrinfo = socket.getaddrinfo

def new_getaddrinfo(host, port, family=0, socktype=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, socktype, proto, flags)

socket.getaddrinfo = new_getaddrinfo

try:
    print(f"\n强制IPv4后 getaddrinfo({domain}, 443):")
    results = socket.getaddrinfo(domain, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
    for res in results:
        family, socktype, proto, canonname, sockaddr = res
        family_name = "IPv6" if family == socket.AF_INET6 else "IPv4"
        print(f"  {family_name}: {sockaddr}")
except Exception as e:
    print(f"  错误: {e}")

# 测试HTTP请求
print("\n" + "=" * 60)
print("【测试3】HTTP请求测试")
print("=" * 60)

urls = [
    ("养殖网HTTPS", "https://www.cnfowl.com/quote/"),
    ("养殖网HTTP", "http://www.cnfowl.com/quote/"),
    ("百度（基准）", "https://www.baidu.com"),
]

for name, url in urls:
    print(f"\n测试 {name}: {url}")
    try:
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        print(f"  ✓ 状态码: {response.status_code}")
        print(f"  ✓ 内容长度: {len(response.text)} 字符")
        
        # 保存HTML
        if response.status_code == 200:
            filename = f"data/diagnose/test_{name.replace(' ', '_')}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"  ✓ HTML已保存: {filename}")
            
    except requests.exceptions.Timeout:
        print(f"  ✗ 超时")
    except requests.exceptions.ConnectionError as e:
        print(f"  ✗ 连接失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")

# 测试爬虫
print("\n" + "=" * 60)
print("【测试4】爬虫功能测试")
print("=" * 60)

try:
    from src.collectors.cnfowl_spider import CnfowlSpider
    
    print("\n初始化爬虫...")
    spider = CnfowlSpider(use_local=False)
    
    print("\n测试 fetch()...")
    html = spider.fetch()
    
    if html:
        print(f"  ✓ fetch() 成功，HTML长度: {len(html)}")
        
        # 测试 parse()
        print("\n测试 parse()...")
        data = spider.parse(html)
        
        if data:
            print(f"  ✓ parse() 成功，解析到 {len(data)} 条数据")
            print(f"  数据示例:")
            for item in data[:3]:
                print(f"    {item}")
        else:
            print(f"  ✗ parse() 失败")
    else:
        print(f"  ✗ fetch() 失败")
        
except Exception as e:
    print(f"  ✗ 异常: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)