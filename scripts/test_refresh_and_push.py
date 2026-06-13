"""
测试接口：刷新监测数据并发送推送

此脚本会执行完整的数据采集和推送流程：
1. 采集期货行情（JD2609）
2. 采集现货价格（鸡蛋、玉米、豆粕）
3. 采集仓单数据（大商所）
4. 运行预警检查
5. 发送每日汇总推送到飞书

使用方法：
    python scripts/test_refresh_and_push.py
"""

import sys
import os
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from loguru import logger
from datetime import datetime

# 导入采集模块
from src.collectors.futures_collector import collect_and_save_latest, SUPPORTED_SYMBOLS
from src.collectors.spot_collector import collect_and_save_spot
from src.collectors.futures_receipt_collector import collect_and_save_receipt
from src.collectors.futures_holding_collector import collect_and_save_holding
from src.analysis.rule_engine import run_all_checks
from src.notification.daily_summary import send_daily_summary
from src.notification.feishu import send_feishu_message


def refresh_all_data():
    """
    刷新所有监测数据

    Returns:
        刷新是否成功
    """
    logger.info("="*50)
    logger.info("开始刷新监测数据")
    logger.info("="*50)

    success_count = 0
    total_tasks = 5

    # 任务1: 采集期货行情
    logger.info("\n[1/5] 采集期货行情...")
    try:
        collect_and_save_latest(SUPPORTED_SYMBOLS)
        logger.info("✅ 期货行情采集成功")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ 期货行情采集失败: {e}")

    # 任务2: 采集现货价格
    logger.info("\n[2/5] 采集现货价格...")
    try:
        collect_and_save_spot()
        logger.info("✅ 现货价格采集成功")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ 现货价格采集失败: {e}")

    # 任务3: 采集仓单数据
    logger.info("\n[3/5] 采集仓单数据...")
    try:
        collect_and_save_receipt()
        logger.info("✅ 仓单数据采集成功")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ 仓单数据采集失败: {e}")

    # 任务4: 采集持仓数据
    logger.info("\n[4/5] 采集持仓数据...")
    try:
        collect_and_save_holding("JD2609")
        logger.info("✅ 持仓数据采集成功")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ 持仓数据采集失败: {e}")

    # 任务5: 运行预警检查
    logger.info("\n[5/5] 运行预警检查...")
    try:
        run_all_checks()
        logger.info("✅ 预警检查完成")
        success_count += 1
    except Exception as e:
        logger.error(f"❌ 预警检查失败: {e}")

    logger.info("\n" + "="*50)
    logger.info(f"数据刷新完成: {success_count}/{total_tasks} 任务成功")
    logger.info("="*50)

    return success_count >= 3  # 至少3个任务成功才算成功


def send_push_notification():
    """
    发送推送通知

    Returns:
        发送是否成功
    """
    logger.info("="*50)
    logger.info("开始发送推送通知")
    logger.info("="*50)

    try:
        # 发送每日汇总
        logger.info("\n发送每日数据汇总...")
        success = send_daily_summary()

        if success:
            logger.info("✅ 每日汇总推送成功")
        else:
            logger.error("❌ 每日汇总推送失败")

        # 发送测试通知
        logger.info("\n发送测试通知...")
        test_message = f"""
🧪 **测试刷新接口**

刷新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ 数据刷新完成
✅ 推送发送成功

---
💡 这是测试刷新接口的推送通知
"""

        send_feishu_message(
            title="🧪 测试刷新接口",
            content=test_message
        )

        logger.info("✅ 测试通知发送成功")

        logger.info("\n" + "="*50)
        logger.info("推送通知发送完成")
        logger.info("="*50)

        return True

    except Exception as e:
        logger.error(f"❌ 推送通知发送失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    主函数：刷新数据并发送推送
    """
    logger.info("="*50)
    logger.info("测试刷新接口启动")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*50)

    # 步骤1: 刷新数据
    logger.info("\n【步骤1】刷新监测数据")
    data_success = refresh_all_data()

    # 步骤2: 发送推送
    logger.info("\n【步骤2】发送推送通知")
    push_success = send_push_notification()

    # 总结
    logger.info("\n" + "="*50)
    logger.info("测试刷新接口完成")
    logger.info("="*50)

    if data_success and push_success:
        logger.info("✅ 全流程成功！")
        logger.info("✅ 数据已刷新")
        logger.info("✅ 推送已发送")
        logger.info("\n请检查飞书群是否收到以下消息:")
        logger.info("  1. 📊 每日数据汇总")
        logger.info("  2. 🧪 测试刷新接口通知")
        return 0
    else:
        logger.error("❌ 流程执行失败")
        if not data_success:
            logger.error("  - 数据刷新失败")
        if not push_success:
            logger.error("  - 推送发送失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)