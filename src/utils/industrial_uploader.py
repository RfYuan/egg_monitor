"""
产业数据CSV上传接口

支持从我的农产品网、卓创资讯等渠道下载的报表，
提取存栏、鸡苗销量、淘汰鸡出栏、冷库库存等数据，
写入数据库。

使用方法:
    # 命令行上传
    python -m src.utils.industrial_uploader data/industrial_2026_06_13.csv

    # Python API
    from src.utils.industrial_uploader import process_csv_file
    process_csv_file("data/industrial_2026_06_13.csv")
"""

import csv
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.storage.database import get_db
from src.storage.crud import create_industrial_inventory


class IndustrialDataUploader:
    """产业数据CSV上传处理器"""

    # 支持的数据类型
    DATA_TYPES = {
        "存栏": "存栏量",
        "鸡苗": "鸡苗销量",
        "淘汰鸡": "淘汰鸡出栏",
        "冷库": "冷库库存",
        "老鸡": "老鸡占比",
        "后备": "后备存栏"
    }

    # CSV格式定义
    EXPECTED_COLUMNS = ["date", "category", "inventory", "mom", "yoy", "source"]

    def __init__(self, dry_run: bool = False):
        """
        初始化上传器

        Args:
            dry_run: 如果为True，仅验证不写入数据库
        """
        self.dry_run = dry_run
        self.records = []
        self.errors = []
        self.warnings = []

    def process_csv_file(self, file_path: str) -> bool:
        """
        处理CSV文件

        Args:
            file_path: CSV文件路径

        Returns:
            处理是否成功
        """
        logger.info(f"[IndustrialUpload] 开始处理文件: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"[IndustrialUpload] 文件不存在: {file_path}")
            return False

        # 读取CSV文件
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                # 验证列名
                if not self._validate_columns(reader.fieldnames):
                    return False

                # 处理每一行
                for row_num, row in enumerate(reader, start=2):
                    self._process_row(row, row_num)

        except Exception as e:
            logger.error(f"[IndustrialUpload] 读取文件失败: {e}")
            return False

        # 输出统计
        logger.info(f"[IndustrialUpload] 处理完成:")
        logger.info(f"  - 成功记录: {len(self.records)}")
        logger.info(f"  - 错误数: {len(self.errors)}")
        logger.info(f"  - 警告数: {len(self.warnings)}")

        # 写入数据库
        if self.errors:
            logger.error(f"[IndustrialUpload] 存在错误，跳过数据库写入")
            return False

        if not self.dry_run and self.records:
            self._write_to_database()

        return True

    def process_csv_content(self, csv_content: str) -> bool:
        """
        处理CSV内容字符串

        Args:
            csv_content: CSV格式的字符串

        Returns:
            处理是否成功
        """
        import io

        logger.info("[IndustrialUpload] 开始处理CSV内容")

        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            # 验证列名
            if not self._validate_columns(reader.fieldnames):
                return False

            # 处理每一行
            for row_num, row in enumerate(reader, start=2):
                self._process_row(row, row_num)

            # 输出统计
            logger.info(f"[IndustrialUpload] 处理完成:")
            logger.info(f"  - 成功记录: {len(self.records)}")
            logger.info(f"  - 错误数: {len(self.errors)}")

            if self.errors:
                return False

            if not self.dry_run and self.records:
                self._write_to_database()

            return True

        except Exception as e:
            logger.error(f"[IndustrialUpload] 处理CSV内容失败: {e}")
            return False

    def _validate_columns(self, fieldnames: List[str]) -> bool:
        """验证CSV列名"""
        if not fieldnames:
            logger.error("[IndustrialUpload] CSV文件没有列名")
            return False

        # 标准化列名（去除空格、转小写）
        fieldnames = [col.strip().lower() for col in fieldnames]

        # 检查必需列
        required = ["date", "inventory"]
        missing = [col for col in required if col not in fieldnames]

        if missing:
            logger.error(f"[IndustrialUpload] 缺少必需列: {missing}")
            logger.info(f"[IndustrialUpload] 实际列名: {fieldnames}")
            logger.info(f"[IndustrialUpload] 期望列名: {self.EXPECTED_COLUMNS}")
            return False

        return True

    def _process_row(self, row: Dict, row_num: int):
        """处理CSV行"""
        try:
            # 标准化键名
            row = {k.strip().lower(): v.strip() if v else "" for k, v in row.items()}

            # 验证日期
            date_str = row.get("date", "")
            if not date_str:
                self.errors.append(f"行{row_num}: 缺少日期")
                return

            # 解析日期
            parsed_date = self._parse_date(date_str)
            if not parsed_date:
                self.errors.append(f"行{row_num}: 日期格式错误: {date_str}")
                return

            # 解析数量
            inventory_str = row.get("inventory", "")
            if not inventory_str:
                self.errors.append(f"行{row_num}: 缺少数量")
                return

            inventory = self._parse_number(inventory_str)
            if inventory is None:
                self.errors.append(f"行{row_num}: 数量格式错误: {inventory_str}")
                return

            # 解析环比（可选）
            mom = self._parse_percent(row.get("mom", ""))

            # 解析同比（可选）
            yoy = self._parse_percent(row.get("yoy", ""))

            # 来源
            source = row.get("source", "人工录入")

            # 类型（如果有）
            category = row.get("category", "存栏量")
            if not category:
                category = "存栏量"

            # 构建记录
            record = {
                "date": parsed_date,
                "category": category,
                "inventory": inventory,
                "mom": mom,
                "yoy": yoy,
                "source": source
            }

            self.records.append(record)
            logger.debug(f"[IndustrialUpload] 记录: {parsed_date} - {inventory} ({source})")

        except Exception as e:
            self.errors.append(f"行{row_num}: 处理失败: {str(e)}")

    def _parse_date(self, date_str: str) -> Optional[date]:
        """解析日期字符串"""
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y%m%d",
            "%Y年%m月%d日",
            "%Y-%m-%d %H:%M:%S"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def _parse_number(self, num_str: str) -> Optional[float]:
        """解析数字字符串"""
        if not num_str:
            return None

        # 去除空格和逗号
        num_str = num_str.strip().replace(",", "").replace("，", "")

        # 处理单位（亿羽、万羽、吨等）
        multiplier = 1.0

        # 检查并去除单位后缀
        for unit, mult in [("亿", 100000000), ("万", 10000)]:
            if unit in num_str:
                multiplier = mult
                # 去除单位，保留数字部分
                num_str = num_str.replace(unit, "")
                break

        # 去除其他非数字字符（保留小数点）
        import re
        num_str = re.sub(r"[^\d.]", "", num_str)

        if not num_str:
            return None

        try:
            return float(num_str) * multiplier
        except ValueError:
            return None

    def _parse_percent(self, percent_str: str) -> Optional[float]:
        """解析百分比字符串"""
        if not percent_str or percent_str.strip() == "":
            return None

        # 去除空格和百分号
        percent_str = percent_str.strip().replace("%", "").replace("％", "")

        if percent_str in ["-", "N/A", "NA", ""]:
            return None

        try:
            return float(percent_str)
        except ValueError:
            return None

    def _write_to_database(self):
        """写入数据库"""
        logger.info(f"[IndustrialUpload] 开始写入数据库，共 {len(self.records)} 条记录")

        db = next(get_db())
        success_count = 0
        error_count = 0

        for record in self.records:
            try:
                create_industrial_inventory(db, record)
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"[IndustrialUpload] 写入失败: {record} - {e}")

        logger.info(f"[IndustrialUpload] 数据库写入完成:")
        logger.info(f"  - 成功: {success_count}")
        logger.info(f"  - 失败: {error_count}")

    def get_report(self) -> str:
        """生成处理报告"""
        report = []
        report.append("=" * 50)
        report.append("产业数据CSV上传报告")
        report.append("=" * 50)
        report.append(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"成功记录: {len(self.records)}")
        report.append(f"错误数: {len(self.errors)}")
        report.append(f"警告数: {len(self.warnings)}")

        if self.records:
            report.append("\n成功记录预览:")
            for record in self.records[:5]:
                report.append(f"  - {record['date']}: {record['inventory']:,.0f} ({record['source']})")

        if self.errors:
            report.append("\n错误列表:")
            for error in self.errors:
                report.append(f"  ❌ {error}")

        if self.warnings:
            report.append("\n警告列表:")
            for warning in self.warnings:
                report.append(f"  ⚠️ {warning}")

        return "\n".join(report)


def process_csv_file(file_path: str, dry_run: bool = False) -> bool:
    """
    处理CSV文件的便捷函数

    Args:
        file_path: CSV文件路径
        dry_run: 是否仅验证不写入

    Returns:
        处理是否成功
    """
    uploader = IndustrialDataUploader(dry_run=dry_run)
    success = uploader.process_csv_file(file_path)

    if success:
        print(uploader.get_report())

    return success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="产业数据CSV上传工具")
    parser.add_argument("file", help="CSV文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅验证不写入数据库")

    args = parser.parse_args()

    success = process_csv_file(args.file, dry_run=args.dry_run)

    sys.exit(0 if success else 1)
