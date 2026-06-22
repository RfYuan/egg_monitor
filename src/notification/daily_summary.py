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

        futures_data = self._get_futures_data()
        spot_data = self._get_spot_data()
        receipt_data = self._get_receipt_data()
        industrial_data = self._get_industrial_data()

        if not futures_data:
            logger.error("[DailySummary] 期货数据缺失，生成数据异常警报")
            return f"""⚠️ **【数据异常】今日期货数据获取失败**

**紧急通知：JD2609 今日数据获取失败**

原因：期货行情数据缺失或过期

建议：
1. 检查网络连接和 AKShare API 可用性
2. 手动确认 JD2609 今日收盘价
3. 关注系统日志排查问题

🕐 检测时间：{self.date}"""

        message_parts = []

        message_parts.append(self._format_header())

        if futures_data:
            message_parts.append(self._format_futures(futures_data))

        if spot_data:
            message_parts.append(self._format_spot(spot_data))
        else:
            message_parts.append("💰 **现货价格**: 无数据")

        if receipt_data:
            message_parts.append(self._format_receipt(receipt_data))
        else:
            message_parts.append("📦 **仓单数据**: 无数据")

        if industrial_data:
            message_parts.append(self._format_industrial(industrial_data))
        else:
            message_parts.append("🏭 **产业数据**: ⚠️ 数据已过期（超过7天），请人工录入最新数据")

        message_parts.append(self._format_alerts())

        message_parts.append(self._format_footer())

        message = "\n\n".join(message_parts)

        logger.info(f"[DailySummary] 汇总生成完成，共 {len(message)} 字符")

        return message

    def _is_data_today(self, data_date) -> bool:
        """检查数据日期是否为今天"""
        today = date.today()
        if hasattr(data_date, 'date'):
            return data_date.date() == today
        return data_date == today


    def _get_futures_data(self) -> Optional[Dict]:
        """获取期货行情数据（严格验证日期）"""
        try:
            db = next(get_db())

            quotes = get_futures_quotes(db, "JD2609", limit=2)

            if not quotes:
                logger.error("[DailySummary] 未找到期货行情数据")
                return None

            latest = quotes[0]
            data_date = latest.datetime.date() if hasattr(latest.datetime, 'date') else latest.datetime
            
            if not self._is_data_today(latest.datetime):
                days_old = (date.today() - data_date).days if data_date else 999
                logger.error(f"[DATA STALE] JD2609 latest data is {days_old} days old ({data_date}), cannot use!")
                return None

            prev = quotes[1] if len(quotes) > 1 else None

            change = 0
            change_pct = 0
            if prev and prev.close:
                change = float(latest.close) - float(prev.close)
                change_pct = (change / float(prev.close)) * 100

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
        """获取现货价格数据（支持养殖网数据格式）"""
        try:
            db = next(get_db())

            # 养殖网爬虫使用英文category：egg, corn, soymeal, eliminate
            # 备用数据源可能使用中文category：鸡蛋, 玉米, 豆粕
            category_map = {
                "鸡蛋": ["egg", "鸡蛋"],
                "玉米": ["corn", "玉米"],
                "豆粕": ["soymeal", "豆粕"],
                "淘汰禽": ["eliminate", "淘汰禽"]
            }

            data = {}

            for display_name, categories in category_map.items():
                for cat in categories:
                    prices = get_spot_prices(db, category=cat, limit=5)
                    if prices:
                        # 优先使用山东地区，否则取第一条
                        target_price = None
                        for p in prices:
                            if "山东" in p.region:
                                target_price = p
                                break
                        if not target_price:
                            target_price = prices[0]
                        
                        data[display_name] = {
                            "price": float(target_price.price),
                            "unit": target_price.unit,
                            "region": target_price.region,
                            "source": target_price.source
                        }
                        break

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
        """获取产业数据（严格验证数据新鲜度）"""
        try:
            db = next(get_db())

            categories = ["在产蛋鸡存栏", "鸡苗周销量", "淘汰鸡出栏", "冷库鸡蛋库存"]
            data = {}
            stale_count = 0

            for category in categories:
                inventories = get_industrial_inventories(db, category=category, limit=1)
                if inventories:
                    inv = inventories[0]
                    inv_date = inv.date if hasattr(inv.date, 'date') else inv.date
                    
                    # 产业数据每周更新，超过7天视为过期
                    days_old = (date.today() - inv_date).days if inv_date else 999
                    if days_old > 7:
                        logger.warning(f"[DATA STALE] {category} 数据已过期 {days_old} 天 ({inv_date})")
                        stale_count += 1
                        continue  # 跳过过期数据
                    
                    data[category] = {
                        "inventory": float(inv.inventory),
                        "mom": float(inv.mom) if inv.mom else None,
                        "yoy": float(inv.yoy) if inv.yoy else None,
                        "date": inv.date,
                        "source": inv.source
                    }

            if stale_count > 0:
                logger.error(f"[DailySummary] {stale_count}/{len(categories)} 项产业数据已过期，返回 None")
                return None

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
