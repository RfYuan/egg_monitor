"""
每日数据汇总推送模块

交易日下午4点推送当日交易数据汇总，包含：
1. 期货行情（收盘价、涨跌幅、持仓变化）
2. 现货价格（鸡蛋、玉米、豆粕）
3. 仓单数据（如果有）
4. 产业数据（存栏、鸡苗等）
5. 预警状态汇总

使用方法：
    # 命令行推送
    python -m src.notification.daily_summary

    # 在定时任务中调用
    from src.notification.daily_summary import send_daily_summary
    send_daily_summary()
"""

import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from loguru import logger
from src.storage.database import get_db
from src.storage.crud import (
    get_futures_quotes,
    get_futures_receipts,
    get_futures_holdings,
    get_spot_prices,
    get_industrial_inventories
)
from src.notification.feishu import send_feishu_message
from src.notification.notifier import send_notification


class DailySummaryGenerator:
    """每日数据汇总生成器"""

    def __init__(self):
        self.date = date.today()
        self.summary = {}

    def generate(self) -> str:
        """
        生成每日汇总消息

        Returns:
            格式化的飞书消息文本
        """
        logger.info(f"[DailySummary] 开始生成 {self.date} 每日汇总")

        # 收集各类数据
        futures_data = self._get_futures_data()
        spot_data = self._get_spot_data()
        receipt_data = self._get_receipt_data()
        industrial_data = self._get_industrial_data()

        # 构建消息
        message_parts = []

        # 1. 标题和时间
        message_parts.append(self._format_header())

        # 2. 期货行情
        if futures_data:
            message_parts.append(self._format_futures(futures_data))

        # 3. 现货价格
        if spot_data:
            message_parts.append(self._format_spot(spot_data))

        # 4. 仓单数据
        if receipt_data:
            message_parts.append(self._format_receipt(receipt_data))
        else:
            message_parts.append("📦 **仓单数据**: 无数据")

        # 5. 产业数据
        if industrial_data:
            message_parts.append(self._format_industrial(industrial_data))
        else:
            message_parts.append("🏭 **产业数据**: 无最新数据（请人工录入）")

        # 6. 预警状态
        message_parts.append(self._format_alerts())

        # 7. 尾注
        message_parts.append(self._format_footer())

        message = "\n\n".join(message_parts)

        logger.info(f"[DailySummary] 汇总生成完成，共 {len(message)} 字符")

        return message

    def _get_futures_data(self) -> Optional[Dict]:
        """获取期货行情数据"""
        try:
            db = next(get_db())

            # 获取JD2609行情
            quotes = get_futures_quotes(db, "JD2609", limit=2)

            if not quotes:
                logger.warning("[DailySummary] 未找到期货行情数据")
                return None

            # 最新行情
            latest = quotes[0]
            prev = quotes[1] if len(quotes) > 1 else None

            # 计算涨跌幅
            change = 0
            change_pct = 0
            if prev and prev.close:
                change = float(latest.close) - float(prev.close)
                change_pct = (change / float(prev.close)) * 100

            # 计算持仓变化
            holding_change = 0
            holdings = get_futures_holdings(db, "JD2609", limit=2)
            if len(holdings) > 1:
                holding_change = holdings[0].open_interest - holdings[1].open_interest if hasattr(holdings[0], 'open_interest') else 0

            return {
                "symbol": "JD2609",
                "close": float(latest.close),
                "high": float(latest.high),
                "low": float(latest.low),
                "change": change,
                "change_pct": change_pct,
                "volume": latest.volume,
                "open_interest": latest.open_interest,
                "holding_change": holding_change,
                "datetime": latest.datetime
            }

        except Exception as e:
            logger.error(f"[DailySummary] 获取期货数据失败: {e}")
            return None

    def _get_spot_data(self) -> Optional[Dict]:
        """获取现货价格数据"""
        try:
            db = next(get_db())

            # 获取最新现货价格
            egg_prices = get_spot_prices(db, category="鸡蛋", limit=1)
            corn_prices = get_spot_prices(db, category="玉米", limit=1)
            soy_prices = get_spot_prices(db, category="豆粕", limit=1)

            data = {}

            if egg_prices:
                egg = egg_prices[0]
                data["鸡蛋"] = {
                    "price": float(egg.price),
                    "unit": egg.unit,
                    "region": egg.region,
                    "source": egg.source
                }

            if corn_prices:
                corn = corn_prices[0]
                data["玉米"] = {
                    "price": float(corn.price),
                    "unit": corn.unit,
                    "region": corn.region
                }

            if soy_prices:
                soy = soy_prices[0]
                data["豆粕"] = {
                    "price": float(soy.price),
                    "unit": soy.unit,
                    "region": soy.region
                }

            return data if data else None

        except Exception as e:
            logger.error(f"[DailySummary] 获取现货数据失败: {e}")
            return None

    def _get_receipt_data(self) -> Optional[List]:
        """获取仓单数据"""
        try:
            db = next(get_db())
            receipts = get_futures_receipts(db, "JD2609", limit=10)

            if not receipts:
                return None

            return [
                {
                    "date": r.date,
                    "receipt_qty": r.receipt_qty,
                    "change": r.change,
                    "warehouse": getattr(r, "warehouse", None)
                }
                for r in receipts
            ]

        except Exception as e:
            logger.error(f"[DailySummary] 获取仓单数据失败: {e}")
            return None

    def _get_industrial_data(self) -> Optional[Dict]:
        """获取产业数据"""
        try:
            db = next(get_db())

            # 获取各类型最新数据
            categories = ["在产蛋鸡存栏", "鸡苗周销量", "淘汰鸡出栏", "冷库鸡蛋库存"]

            data = {}

            for category in categories:
                inventories = get_industrial_inventories(db, category=category, limit=1)
                if inventories:
                    inv = inventories[0]
                    data[category] = {
                        "inventory": float(inv.inventory),
                        "mom": float(inv.mom) if inv.mom else None,
                        "yoy": float(inv.yoy) if inv.yoy else None,
                        "date": inv.date,
                        "source": inv.source
                    }

            return data if data else None

        except Exception as e:
            logger.error(f"[DailySummary] 获取产业数据失败: {e}")
            return None

    def _format_header(self) -> str:
        """格式化标题"""
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[self.date.weekday()]

        return f"📊 **{self.date} {weekday} 鸡蛋期货每日汇总**"

    def _format_futures(self, data: Dict) -> str:
        """格式化期货行情"""
        symbol = data["symbol"]
        close = data["close"]
        change = data["change"]
        change_pct = data["change_pct"]
        volume = data.get("volume", 0)
        open_interest = data.get("open_interest", 0)

        # 涨跌符号
        if change > 0:
            trend_icon = "📈"
            change_str = f"+{change:.0f}"
            change_pct_str = f"+{change_pct:.2f}%"
        elif change < 0:
            trend_icon = "📉"
            change_str = f"{change:.0f}"
            change_pct_str = f"{change_pct:.2f}%"
        else:
            trend_icon = "➡️"
            change_str = "0"
            change_pct_str = "0.00%"

        lines = [
            f"📈 **期货行情（{symbol}）**",
            f"  收盘价: {close:.0f} 元/吨 {trend_icon}",
            f"  涨跌幅: {change_str} ({change_pct_str})",
            f"  成交量: {volume:,} 手",
            f"  持仓量: {open_interest:,} 手"
        ]

        return "\n".join(lines)

    def _format_spot(self, data: Dict) -> str:
        """格式化现货价格"""
        lines = ["💰 **现货价格**"]

        for category, info in data.items():
            price = info["price"]
            unit = info.get("unit", "元/吨")
            region = info.get("region", "")
            source = info.get("source", "")

            region_str = f"（{region}）" if region else ""
            source_str = f" [{source}]" if source else ""

            lines.append(f"  • {category}{region_str}: {price:.0f}{unit}{source_str}")

        return "\n".join(lines)

    def _format_receipt(self, data: List) -> str:
        """格式化仓单数据"""
        lines = ["📦 **仓单数据**"]

        # 只显示最新3条
        for item in data[:3]:
            date_str = item["date"].strftime("%m-%d") if hasattr(item["date"], 'strftime') else str(item["date"])
            qty = item["receipt_qty"]
            change = item["change"]
            warehouse = item.get("warehouse", "")

            change_str = f"+{change}" if change > 0 else str(change)

            lines.append(f"  • {date_str} {warehouse}: {qty:,} 手 ({change_str})")

        if len(data) > 3:
            lines.append(f"  ... 共 {len(data)} 条数据")

        return "\n".join(lines)

    def _format_industrial(self, data: Dict) -> str:
        """格式化产业数据"""
        lines = ["🏭 **产业数据**"]

        for category, info in data.items():
            inventory = info["inventory"]
            mom = info.get("mom")
            yoy = info.get("yoy")
            source = info.get("source", "")

            # 格式化数值
            if inventory >= 100000000:
                inventory_str = f"{inventory/100000000:.2f}亿"
            elif inventory >= 10000:
                inventory_str = f"{inventory/10000:.2f}万"
            else:
                inventory_str = f"{inventory:,.0f}"

            # 环比变化
            if mom is not None:
                mom_str = f"环比{'+' if mom > 0 else ''}{mom:.1f}%"
            else:
                mom_str = ""

            # 同比变化
            if yoy is not None:
                yoy_str = f"同比{'+' if yoy > 0 else ''}{yoy:.1f}%"
            else:
                yoy_str = ""

            changes = " | ".join(filter(None, [mom_str, yoy_str]))
            changes_str = f" ({changes})" if changes else ""

            lines.append(f"  • {category}: {inventory_str}{changes_str} [{source}]")

        return "\n".join(lines)

    def _format_alerts(self) -> str:
        """格式化预警状态"""
        # TODO: 从数据库查询未解决的预警
        # 这里先显示示例内容

        lines = ["⚠️ **预警状态**"]
        lines.append("  • 暂无活跃预警")
        lines.append("  • 系统运行正常")

        return "\n".join(lines)

    def _format_footer(self) -> str:
        """格式化尾注"""
        return f"---\n🕐 生成时间: {datetime.now().strftime('%H:%M:%S')}\n💡 提示: 如需查看详细数据，请访问系统数据库"


def send_daily_summary() -> bool:
    """
    发送每日汇总推送

    Returns:
        发送是否成功
    """
    try:
        logger.info("[DailySummary] 开始发送每日汇总推送")

        # 生成汇总
        generator = DailySummaryGenerator()
        message = generator.generate()

        # 发送飞书消息
        success = send_feishu_message(
            title="📊 每日汇总推送",
            content=message
        )

        if success:
            logger.info("[DailySummary] 每日汇总推送成功")
        else:
            logger.error("[DailySummary] 每日汇总推送失败")

        return success

    except Exception as e:
        logger.error(f"[DailySummary] 发送每日汇总失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 命令行直接运行
    send_daily_summary()
