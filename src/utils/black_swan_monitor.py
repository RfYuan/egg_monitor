"""
黑天鹅关键词监测模块

监测以下数据源的关键词：
1. 中国禽病网 - 禽流感、活禽关停、扑杀
2. 财联社/金十数据 - 抛储、储备蛋
3. 中国天气网 - 主产区灾害天气

使用方法：
    # 命令行运行
    python -m src.utils.black_swan_monitor

    # 在定时任务中调用
    from src.utils.black_swan_monitor import check_black_swan
    check_black_swan()
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import requests
from loguru import logger
from bs4 import BeautifulSoup


class BlackSwanMonitor:
    """黑天鹅关键词监测器"""

    # 监测关键词
    KEYWORDS = {
        "禽流感": {
            "keywords": ["禽流感", "H5N1", "H7N9", "活禽关停", "扑杀", "疫情"],
            "level": "critical",  # 最高级别
            "action": "无条件全平所有多头"
        },
        "抛储": {
            "keywords": ["抛储", "投放储备蛋", "储备鸡蛋", "中央储备"],
            "level": "high",
            "action": "减仓50%，观察后续力度"
        },
        "灾害天气": {
            "keywords": ["洪涝", "暴雨", "封控", "交通中断", "高温", "梅雨"],
            "level": "medium",
            "action": "减仓避险"
        },
        "政策风险": {
            "keywords": ["政策", "监管", "限仓", "提高保证金"],
            "level": "medium",
            "action": "关注官方公告"
        }
    }

    # 监测URL（示例，实际使用时需要更新）
    MONITOR_URLS = {
        "禽病网": "https://www.qinbing.cn/",
        "财联社": "https://www.cls.cn/searchPage?keyword=%E9%B8%A6%E8%9B%8B%E6%8A%95%E5%80%89",
        "金十数据": "https://www.jin10.com/",
    }

    def __init__(self):
        self.findings = []

    def check_all(self) -> List[Dict]:
        """
        检查所有数据源

        Returns:
            发现的风险列表
        """
        logger.info("[BlackSwan] 开始黑天鹅关键词监测")

        self.findings = []

        # 检查禽病网（实际生产环境需要更新URL）
        # self._check_qinbing()

        # 检查财联社
        # self._check_cls()

        # 检查关键词匹配（从缓存或数据库）
        self._check_keyword_alerts()

        logger.info(f"[BlackSwan] 监测完成，发现 {len(self.findings)} 个风险")

        return self.findings

    def _check_qinbing(self):
        """检查禽病网"""
        logger.info("[BlackSwan] 检查禽病网...")

        try:
            # TODO: 实际实现禽病网爬虫
            # response = requests.get(self.MONITOR_URLS["禽病网"], timeout=10)
            # soup = BeautifulSoup(response.text, 'html.parser')
            # ...

            logger.info("[BlackSwan] 禽病网检查完成（待实现）")

        except Exception as e:
            logger.error(f"[BlackSwan] 禽病网检查失败: {e}")

    def _check_cls(self):
        """检查财联社"""
        logger.info("[BlackSwan] 检查财联社...")

        try:
            # TODO: 实际实现财联社爬虫
            # response = requests.get(self.MONITOR_URLS["财联社"], timeout=10)
            # ...

            logger.info("[BlackSwan] 财联社检查完成（待实现）")

        except Exception as e:
            logger.error(f"[BlackSwan] 财联社检查失败: {e}")

    def _check_keyword_alerts(self):
        """
        检查关键词告警

        这个方法可以从以下来源获取内容：
        1. 数据库中的系统日志（包含爬取的新闻标题）
        2. 缓存的最新资讯
        3. RSS订阅源
        """
        logger.info("[BlackSwan] 检查关键词告警...")

        # TODO: 从数据库或缓存获取最新资讯内容
        # 示例：从系统日志中搜索关键词

        sample_content = [
            "农业农村部发布禽流感防控指南",
            "中央储备蛋投放市场",
            "河北地区暴雨预警",
        ]

        # 检查每个内容片段
        for content in sample_content:
            for category, info in self.KEYWORDS.items():
                for keyword in info["keywords"]:
                    if keyword in content:
                        self.findings.append({
                            "category": category,
                            "keyword": keyword,
                            "content": content,
                            "level": info["level"],
                            "action": info["action"],
                            "timestamp": datetime.now()
                        })

        logger.info(f"[BlackSwan] 关键词告警检查完成，发现 {len(self.findings)} 个风险")

    def check_content(self, content: str) -> Optional[Dict]:
        """
        检查单条内容是否包含风险关键词

        Args:
            content: 待检查的内容

        Returns:
            如果发现风险，返回风险信息；否则返回None
        """
        for category, info in self.KEYWORDS.items():
            for keyword in info["keywords"]:
                if keyword in content:
                    return {
                        "category": category,
                        "keyword": keyword,
                        "content": content,
                        "level": info["level"],
                        "action": info["action"],
                        "timestamp": datetime.now()
                    }

        return None

    def format_findings(self) -> str:
        """
        格式化风险发现为飞书消息

        Returns:
            格式化的消息文本
        """
        if not self.findings:
            return "✅ **黑天鹅监测**: 今日未发现重大风险"

        lines = ["⚠️ **黑天鹅预警**"]

        # 按级别分组
        by_level = {}
        for finding in self.findings:
            level = finding["level"]
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(finding)

        # 按严重程度排序
        level_order = ["critical", "high", "medium"]

        for level in level_order:
            if level not in by_level:
                continue

            level_names = {
                "critical": "🔴 最高级别",
                "high": "🟠 高级",
                "medium": "🟡 中级"
            }

            lines.append(f"\n{level_names.get(level, level)}:")

            for finding in by_level[level]:
                keyword = finding["keyword"]
                content = finding["content"]
                action = finding["action"]
                timestamp = finding["timestamp"].strftime("%H:%M")

                lines.append(f"  • {keyword} - {content}")
                lines.append(f"    建议: {action} [{timestamp}]")

        return "\n".join(lines)


def check_black_swan() -> bool:
    """
    执行黑天鹅检查并发送通知

    Returns:
        是否发现风险
    """
    try:
        logger.info("[BlackSwan] 开始黑天鹅检查...")

        monitor = BlackSwanMonitor()
        findings = monitor.check_all()

        if findings:
            # 发现风险，发送飞书通知
            from src.notification.feishu import send_feishu_message

            message = monitor.format_findings()

            success = send_feishu_message(
                title="⚠️ 黑天鹅预警",
                content=message
            )

            if success:
                logger.info(f"[BlackSwan] 已发送预警通知，发现 {len(findings)} 个风险")
            else:
                logger.error("[BlackSwan] 预警通知发送失败")

            return True
        else:
            logger.info("[BlackSwan] 未发现黑天鹅风险")
            return False

    except Exception as e:
        logger.error(f"[BlackSwan] 黑天鹅检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 命令行直接运行
    check_black_swan()
