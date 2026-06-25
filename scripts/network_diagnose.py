"""
网络诊断脚本 - 排查服务器无法访问养殖网的原因

运行方式: python scripts/network_diagnose.py
"""

import os
import subprocess
import sys

def run_command(cmd, desc):
    """运行命令并输出结果"""
    print(f"\n{'='*60}")
    print(f"【{desc}】")
    print(f"{'='*60}")
    print(f"命令: {cmd}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(f"错误: {result.stderr.strip()}")
        print(f"退出码: {result.returncode}")
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("超时！")
        return -1, "", "超时"
    except Exception as e:
        print(f"异常: {e}")
        return -1, "", str(e)


def main():
    """运行所有诊断"""
    print("\n" + "="*60)
    print("网络诊断工具 - 排查养殖网访问问题")
    print("="*60)
    
    domain = "www.cnfowl.com"
    
    # 1. DNS解析测试
    run_command(f"nslookup {domain}", "DNS解析测试（nslookup）")
    run_command(f"dig {domain}", "DNS解析测试（dig）")
    run_command(f"getent hosts {domain}", "DNS解析测试（getent）")
    
    # 2. IP连通性测试
    run_command(f"ping -c 3 {domain}", "Ping测试")
    run_command(f"ping -c 3 baidu.com", "Ping百度（对比）")
    
    # 3. 端口连通性测试
    run_command(f"nc -zv {domain} 443", "443端口测试（nc）")
    run_command(f"nc -zv {domain} 80", "80端口测试（nc）")
    run_command(f"nc -zv baidu.com 443", "百度443端口测试（对比）")
    
    # 4. 路由追踪
    run_command(f"traceroute {domain}", "路由追踪（traceroute）")
    run_command(f"mtr --report {domain}", "MTR路由分析（需要mtr）")
    
    # 5. 防火墙检查
    run_command("iptables -L OUTPUT -n", "防火墙规则（iptables）")
    run_command("ufw status", "防火墙状态（ufw）")
    
    # 6. 网络配置检查
    run_command("cat /etc/resolv.conf", "DNS配置")
    run_command("cat /etc/hosts", "Hosts文件")
    run_command("ip route show", "路由表")
    run_command("ip addr show", "网络接口")
    
    # 7. 代理检查
    run_command("env | grep -i proxy", "环境变量代理")
    
    # 8. SELinux检查
    run_command("getenforce", "SELinux状态")
    
    # 9. curl测试
    run_command(f"curl -v -I https://{domain}/quote/ 2>&1 | head -50", "curl详细请求")
    run_command(f"curl -v -I https://baidu.com 2>&1 | head -20", "curl百度（对比）")
    
    # 10. 使用IP直接访问
    print("\n" + "="*60)
    print("【尝试使用IP直接访问】")
    print("="*60)
    
    # 获取IP
    result = subprocess.run(f"dig {domain} +short", shell=True, capture_output=True, text=True)
    ips = result.stdout.strip().split()
    
    if ips:
        print(f"解析到的IP: {ips}")
        
        for ip in ips[:3]:
            print(f"\n尝试访问 IP: {ip}")
            cmd = f"curl -v --resolve {domain}:443:{ip} https://{domain}/quote/ 2>&1 | head -30"
            subprocess.run(cmd, shell=True)
    else:
        print("无法解析到IP")
    
    # 11. 检查安全组/云服务商限制
    print("\n" + "="*60)
    print("【安全组检查】")
    print("="*60)
    print("请检查云服务商安全组是否允许出站访问443端口")
    print("腾讯云/阿里云/华为云等需要配置出站规则")
    
    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)


if __name__ == "__main__":
    main()