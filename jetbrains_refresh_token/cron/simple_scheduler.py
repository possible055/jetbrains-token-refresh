import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from jetbrains_refresh_token.api.auth import (
    check_quota_remaining,
    refresh_expired_access_tokens,
)
from jetbrains_refresh_token.log_config import get_logger

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


logger = get_logger("simple_scheduler")


class SimpleJetBrainsScheduler:
    """Simple APScheduler daemon for JetBrains token management."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the simple scheduler.

        Args:
            config_path: Path to the main configuration file
        """
        self.config_path = config_path

        # 確保日誌目錄存在
        self._ensure_directories()

        # 使用簡單的記憶體存儲
        jobstores = {'default': MemoryJobStore()}

        # 配置執行器
        executors = {
            'default': ThreadPoolExecutor(max_workers=3),
        }

        # 作業默認設定
        job_defaults = {'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 300}

        # 初始化排程器
        self.scheduler = BlockingScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Taipei',
        )

        # 註冊信號處理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def _ensure_directories(self):
        """確保必要的目錄存在"""
        directories = ['logs']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def signal_handler(self, signum, frame):
        """處理停止信號"""
        logger.info("收到停止信號: %s", signum)
        self.stop()
        sys.exit(0)

    def token_refresh_job(self):
        """Token 刷新任務"""
        try:
            logger.info("開始執行 token 刷新任務")
            success = refresh_expired_access_tokens(self.config_path)
            if success:
                logger.info("Token 刷新任務完成")
            else:
                logger.error("Token 刷新任務失敗")
        except Exception as e:
            logger.error("Token 刷新任務異常: %s", e)

    def quota_check_job(self):
        """Quota 檢查任務"""
        try:
            logger.info("開始執行 quota 檢查任務")
            success = check_quota_remaining(self.config_path)
            if success:
                logger.info("Quota 檢查任務完成")
            else:
                logger.error("Quota 檢查任務失敗")
        except Exception as e:
            logger.error("Quota 檢查任務異常: %s", e)

    def health_check_job(self):
        """健康檢查任務"""
        try:
            logger.debug("執行健康檢查")
            # 寫入健康檢查檔案
            health_file = Path('logs/scheduler_health')
            with open(health_file, 'w') as f:
                f.write(f"{datetime.now().isoformat()}\n")
                f.write("scheduler_status=running\n")
                f.write(f"jobs_count={len(self.scheduler.get_jobs())}\n")
            logger.debug("健康檢查完成")
        except Exception as e:
            logger.error("健康檢查失敗: %s", e)

    def setup_jobs(self):
        """設定排程任務"""
        jobs_added = 0

        # Token 刷新 - 每30分鐘檢查一次
        self.scheduler.add_job(
            self.token_refresh_job,
            trigger=IntervalTrigger(minutes=30),
            id='token_refresh',
            name='JetBrains Token Refresh',
            replace_existing=True,
        )
        jobs_added += 1
        logger.info("Token 刷新任務已啟用 (每30分鐘)")

        # Quota 檢查 - 每2小時檢查一次
        self.scheduler.add_job(
            self.quota_check_job,
            trigger=IntervalTrigger(hours=2),
            id='quota_check',
            name='JetBrains Quota Check',
            replace_existing=True,
        )
        jobs_added += 1
        logger.info("Quota 檢查任務已啟用 (每2小時)")

        # 健康檢查 - 每5分鐘執行一次
        self.scheduler.add_job(
            self.health_check_job,
            trigger=IntervalTrigger(minutes=5),
            id='health_check',
            name='Scheduler Health Check',
            replace_existing=True,
        )
        jobs_added += 1
        logger.info("健康檢查任務已啟用 (每5分鐘)")

        logger.info("已設定 %d 個排程任務", jobs_added)

    def start(self):
        """啟動排程器"""
        logger.info("正在啟動 JetBrains 簡單排程器...")
        self.setup_jobs()

        # 顯示已排程的任務
        jobs = self.scheduler.get_jobs()
        logger.info("已載入 %d 個任務:", len(jobs))
        for job in jobs:
            next_run = getattr(job, 'next_run_time', '未知')
            logger.info("  - %s (%s): 下次執行 %s", job.name, job.id, next_run)

        try:
            logger.info("排程器啟動成功，開始執行任務...")
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("收到鍵盤中斷信號")
            self.stop()

    def stop(self):
        """停止排程器"""
        logger.info("正在停止排程器...")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        logger.info("排程器已停止")


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(description="JetBrains Simple Token Scheduler")
    parser.add_argument("--config", help="Path to config file")
    args = parser.parse_args()

    logger.info("啟動 JetBrains 簡單排程器服務")

    # 創建並啟動排程器
    scheduler = SimpleJetBrainsScheduler(config_path=args.config)
    scheduler.start()


if __name__ == "__main__":
    main()
