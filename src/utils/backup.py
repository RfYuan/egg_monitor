"""
数据备份任务

每周自动备份数据库和日志文件

使用方法：
    # 命令行运行
    python -m src.utils.backup

    # 在定时任务中调用
    from src.utils.backup import run_backup
    run_backup()
"""

import sys
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from loguru import logger


class DataBackup:
    """数据备份器"""

    def __init__(self):
        # 项目根目录（src/utils/backup.py -> 项目根目录）
        # __file__ = d:\code\egg_monitor\src\utils\backup.py
        # parent = d:\code\egg_monitor\src\utils
        # grandparent = d:\code\egg_monitor\src
        # great-grandparent = d:\code\egg_monitor
        self.project_root = Path(__file__).parent.parent.parent

        # 备份目录
        self.backup_dir = self.project_root / "data" / "backup"

        # 数据库文件
        self.db_file = self.project_root / "data" / "db" / "egg_monitor.db"

        # 日志目录
        self.log_dir = self.project_root / "logs"

        # 确保备份目录存在
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Optional[str]:
        """
        执行备份

        Returns:
            备份文件路径，如果失败返回None
        """
        logger.info("[Backup] 开始数据备份...")

        try:
            # 1. 验证数据库文件
            if not self.db_file.exists():
                logger.error(f"[Backup] 数据库文件不存在: {self.db_file}")
                return None

            logger.info(f"[Backup] 数据库文件: {self.db_file}")

            # 2. 创建备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"egg_monitor_backup_{timestamp}"
            backup_dir = self.backup_dir / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 3. 备份数据库
            db_backup = backup_dir / "egg_monitor.db"
            shutil.copy2(self.db_file, db_backup)
            logger.info(f"[Backup] 数据库已备份: {db_backup}")

            # 4. 备份日志文件（只保留最近7天的）
            log_backup_dir = backup_dir / "logs"
            log_backup_dir.mkdir(parents=True, exist_ok=True)

            if self.log_dir.exists():
                # 获取最近7天的日志文件
                import time
                seven_days_ago = time.time() - 7 * 24 * 60 * 60

                for log_file in self.log_dir.glob("*.log"):
                    if log_file.stat().st_mtime >= seven_days_ago:
                        shutil.copy2(log_file, log_backup_dir / log_file.name)

                logger.info(f"[Backup] 日志文件已备份到: {log_backup_dir}")

            # 5. 创建ZIP压缩包
            zip_path = self.backup_dir / f"{backup_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加数据库备份
                zipf.write(db_backup, db_backup.name)

                # 添加日志文件
                if log_backup_dir.exists():
                    for log_file in log_backup_dir.glob("*.log"):
                        zipf.write(log_file, f"logs/{log_file.name}")

            logger.info(f"[Backup] ZIP压缩包已创建: {zip_path}")

            # 6. 清理临时目录
            shutil.rmtree(backup_dir)

            # 7. 清理旧备份（保留最近4周）
            self._cleanup_old_backups()

            logger.info("[Backup] 数据备份完成！")

            return str(zip_path)

        except Exception as e:
            logger.error(f"[Backup] 数据备份失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _cleanup_old_backups(self):
        """清理旧的备份文件（保留最近4周）"""
        logger.info("[Backup] 清理旧备份文件...")

        try:
            # 计算4周前的时间戳
            import time
            four_weeks_ago = time.time() - 28 * 24 * 60 * 60

            # 获取所有备份文件
            backup_files = list(self.backup_dir.glob("egg_monitor_backup_*.zip"))

            deleted_count = 0
            for backup_file in backup_files:
                if backup_file.stat().st_mtime < four_weeks_ago:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"[Backup] 删除旧备份: {backup_file.name}")

            if deleted_count > 0:
                logger.info(f"[Backup] 已删除 {deleted_count} 个旧备份文件")
            else:
                logger.info("[Backup] 没有需要清理的旧备份")

        except Exception as e:
            logger.error(f"[Backup] 清理旧备份失败: {e}")

    def get_backup_info(self) -> dict:
        """
        获取备份信息

        Returns:
            备份信息字典
        """
        backup_files = list(self.backup_dir.glob("egg_monitor_backup_*.zip"))

        total_size = sum(f.stat().st_size for f in backup_files)

        # 获取最近的备份
        latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime) if backup_files else None

        return {
            "total_backups": len(backup_files),
            "total_size": total_size,
            "latest_backup": latest_backup.name if latest_backup else None,
            "backup_dir": str(self.backup_dir)
        }


def run_backup() -> bool:
    """
    运行数据备份任务

    Returns:
        备份是否成功
    """
    try:
        logger.info("="*50)
        logger.info("开始执行数据备份任务")
        logger.info("="*50)

        backup = DataBackup()
        result = backup.run()

        if result:
            logger.info(f"备份文件: {result}")

            # 获取备份信息
            info = backup.get_backup_info()
            logger.info(f"当前备份统计:")
            logger.info(f"  - 备份总数: {info['total_backups']}")
            logger.info(f"  - 总大小: {info['total_size'] / 1024 / 1024:.2f} MB")

            logger.info("="*50)
            logger.info("数据备份任务完成")
            logger.info("="*50)

            return True
        else:
            logger.error("数据备份失败")
            return False

    except Exception as e:
        logger.error(f"数据备份任务异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 命令行直接运行
    run_backup()
