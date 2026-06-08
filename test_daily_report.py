"""
每日数据推送测试脚本

测试流程：
1. 初始化数据库
2. 获取最新期货数据
3. 生成每日报告
4. 发送飞书推送
5. 验证推送结果
"""

import sys
from datetime import date

# 添加项目根目录到路径
sys.path.insert(0, ".")

from src.storage.database import init_db
from src.notification.daily_report import (
    get_latest_futures_data,
    get_latest_spot_data,
    get_latest_receipt_data,
    format_daily_report,
    send_daily_report,
    send_multi_contract_report
)
from src.utils.logger import log
from config.settings import settings


def test_daily_report():
    """测试每日数据推送"""
    print("=" * 60)
    print("每日数据推送测试")
    print("=" * 60)
    
    # 1. 初始化数据库
    print("\n[1] 初始化数据库...")
    init_db()
    print("✅ 数据库初始化完成")
    
    # 2. 检查飞书配置
    print("\n[2] 检查飞书配置...")
    if settings.FEISHU_WEBHOOK_URL:
        print(f"✅ 飞书 Webhook 已配置")
    else:
        print("❌ 飞书 Webhook 未配置，请检查 .env 文件")
        return
    
    # 3. 获取期货数据
    print("\n[3] 获取 JD2609 最新期货数据...")
    futures_data = get_latest_futures_data("JD2609")
    if futures_data:
        print(f"✅ 期货数据获取成功:")
        print(f"   - 日期: {futures_data['date']}")
        print(f"   - 收盘价: {futures_data['close']}")
        print(f"   - 涨跌幅: {futures_data['change_pct']}%")
        print(f"   - 持仓量: {futures_data['open_interest']}手")
        print(f"   - 持仓变化: {futures_data['oi_change']}手")
    else:
        print("❌ 无期货数据，请先运行 test_futures_history.py 获取历史数据")
        return
    
    # 4. 获取现货数据
    print("\n[4] 获取鸡蛋现货数据...")
    spot_data = get_latest_spot_data("egg")
    if spot_data:
        print(f"✅ 现货数据获取成功:")
        print(f"   - 日期: {spot_data['date']}")
        print(f"   - 价格: {spot_data['price']}元/{spot_data['unit']}")
        print(f"   - 地区: {spot_data['region']}")
    else:
        print("⚠️ 无现货数据（现货爬虫待完善）")
    
    # 5. 获取仓单数据
    print("\n[5] 获取仓单数据...")
    receipt_data = get_latest_receipt_data("jd")
    if receipt_data:
        print(f"✅ 仓单数据获取成功:")
        print(f"   - 日期: {receipt_data['date']}")
        print(f"   - 仓单量: {receipt_data['receipt_qty']}张")
        print(f"   - 变化: {receipt_data['change']}张")
    else:
        print("⚠️ 无仓单数据（仓单采集待开发）")
    
    # 6. 生成报告
    print("\n[6] 生成每日数据报告...")
    content = format_daily_report(futures_data, spot_data, receipt_data)
    print("✅ 报告生成成功:")
    print("-" * 40)
    print(content)
    print("-" * 40)
    
    # 7. 发送飞书推送
    print("\n[7] 发送飞书推送...")
    result = send_daily_report("JD2609")
    if result:
        print("✅ 飞书推送成功！请检查飞书群消息")
    else:
        print("❌ 飞书推送失败，请检查网络和配置")
    
    # 8. 测试多合约推送
    print("\n[8] 测试多合约推送...")
    results = send_multi_contract_report(["JD2607", "JD2608", "JD2609"])
    for symbol, success in results.items():
        status = "✅" if success else "❌"
        print(f"   {status} {symbol}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_daily_report()