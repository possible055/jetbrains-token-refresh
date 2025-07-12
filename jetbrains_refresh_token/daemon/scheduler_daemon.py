import argparse
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
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

logger = get_logger("scheduler_daemon")


class JetBrainsDaemon:
    """Enhanced APScheduler daemon for JetBrains token management."""

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        daemon_config_path: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize the daemon.

        Args:
            config_path: Path to the main configuration file
            daemon_config_path: Path to the daemon configuration file
        """
        self.config_path = Path(config_path) if config_path else Path("config.json")
        # 預設使用 daemon 目錄下的配置文件
        if daemon_config_path:
            self.daemon_config_path = Path(daemon_config_path)
        else:
            # 嘗試使用 daemon 目錄下的配置文件
            daemon_dir_config = Path(__file__).parent / "daemon_config.json"
            if daemon_dir_config.exists():
                self.daemon_config_path = daemon_dir_config
            else:
                # 回退到根目錄的配置文件
                self.daemon_config_path = Path("daemon_config.json")

        # 載入 daemon 配置
        self.daemon_config = self._load_daemon_config()

        # 從配置設定路徑
        paths_config = self.daemon_config.get("paths", {})
        self.status_file = Path(paths_config.get("status_file", "logs/daemon_status.json"))
        self.command_file = Path(paths_config.get("command_file", "logs/daemon_commands.json"))

        # Job execution history
        self.job_history: List[Dict] = []
        logging_config = self.daemon_config.get("logging", {})
        self.max_history = logging_config.get("max_history", 100)

        # Daemon start time
        self.start_time = datetime.now()

        # 確保必要目錄存在
        self._ensure_directories()

        # 初始化狀態文件
        self._init_status_file()

        # 從配置設定 APScheduler
        scheduler_config = self.daemon_config.get("scheduler", {})
        jobstores = {'default': MemoryJobStore()}
        executors = {
            'default': ThreadPoolExecutor(max_workers=scheduler_config.get("max_workers", 3))
        }
        job_defaults = {
            'coalesce': scheduler_config.get("coalesce", True),
            'max_instances': scheduler_config.get("max_instances", 1),
            'misfire_grace_time': scheduler_config.get("misfire_grace_time", 300),
        }

        self.scheduler = BlockingScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=scheduler_config.get("timezone", "Asia/Taipei"),
        )

        # 添加事件監聽器
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)

        # 註冊信號處理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_daemon_config(self) -> Dict:
        """載入 daemon 配置文件"""
        try:
            if self.daemon_config_path.exists():
                with open(self.daemon_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"已載入 daemon 配置: {self.daemon_config_path}")
                return config
            else:
                logger.warning(f"Daemon 配置文件不存在: {self.daemon_config_path}，使用預設配置")
                return self._get_default_daemon_config()
        except Exception as e:
            logger.error(f"載入 daemon 配置失敗: {e}，使用預設配置")
            return self._get_default_daemon_config()

    def _get_default_daemon_config(self) -> Dict:
        """獲取預設 daemon 配置"""
        return {
            "scheduler": {
                "timezone": "Asia/Taipei",
                "max_workers": 3,
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
            "jobs": {
                "token_refresh": {
                    "enabled": True,
                    "interval_minutes": 5,
                    "description": "自動檢查並刷新過期的 JWT tokens",
                },
                "quota_check": {
                    "enabled": True,
                    "interval_minutes": 2,
                    "description": "檢查所有帳戶的配額使用情況",
                },
                "health_check": {
                    "enabled": True,
                    "interval_minutes": 1,
                    "description": "Daemon 健康檢查和狀態更新",
                },
            },
            "logging": {"level": "INFO", "max_history": 100, "status_update_interval": 30},
            "paths": {
                "status_file": "logs/daemon_status.json",
                "command_file": "logs/daemon_commands.json",
                "log_directory": "logs",
            },
        }

    def _ensure_directories(self):
        """確保必要的目錄存在"""
        paths_config = self.daemon_config.get("paths", {})
        log_directory = paths_config.get("log_directory", "logs")
        directories = [log_directory]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def _init_status_file(self):
        """初始化狀態文件"""
        initial_status = {
            "daemon_status": "starting",
            "start_time": self.start_time.isoformat(),
            "last_update": datetime.now().isoformat(),
            "jobs": {},
            "job_history": [],
            "config_path": str(self.config_path),
            "health": {"status": "healthy", "last_check": datetime.now().isoformat()},
        }
        self._write_status(initial_status)

    def _write_status(self, status: Dict):
        """寫入狀態到文件"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to write status file: %s", e)

    def _job_executed_listener(self, event):
        """任務執行成功監聽器"""
        # 處理時區問題
        execution_time = datetime.now()
        scheduled_time = event.scheduled_run_time

        # 確保兩個時間都是同一時區
        if scheduled_time.tzinfo is not None and execution_time.tzinfo is None:
            # 如果 scheduled_time 有時區，execution_time 沒有，則添加本地時區
            from datetime import timezone

            execution_time = execution_time.replace(tzinfo=timezone.utc)
        elif scheduled_time.tzinfo is None and execution_time.tzinfo is not None:
            # 如果 execution_time 有時區，scheduled_time 沒有，則移除時區
            execution_time = execution_time.replace(tzinfo=None)

        job_info = {
            "job_id": event.job_id,
            "scheduled_time": scheduled_time.isoformat(),
            "execution_time": execution_time.isoformat(),
            "status": "success",
            "duration": (
                (execution_time - scheduled_time).total_seconds()
                if scheduled_time.tzinfo == execution_time.tzinfo
                else 0
            ),
        }
        self._add_job_history(job_info)
        logger.info("Job %s executed successfully", event.job_id)

    def _job_error_listener(self, event):
        """任務執行錯誤監聽器"""
        # 處理時區問題
        execution_time = datetime.now()
        scheduled_time = event.scheduled_run_time

        # 確保兩個時間都是同一時區
        if scheduled_time.tzinfo is not None and execution_time.tzinfo is None:
            from datetime import timezone

            execution_time = execution_time.replace(tzinfo=timezone.utc)
        elif scheduled_time.tzinfo is None and execution_time.tzinfo is not None:
            execution_time = execution_time.replace(tzinfo=None)

        job_info = {
            "job_id": event.job_id,
            "scheduled_time": scheduled_time.isoformat(),
            "execution_time": execution_time.isoformat(),
            "status": "error",
            "error": str(event.exception),
            "duration": (
                (execution_time - scheduled_time).total_seconds()
                if scheduled_time.tzinfo == execution_time.tzinfo
                else 0
            ),
        }
        self._add_job_history(job_info)
        logger.error(f"Job {event.job_id} failed: {event.exception}")

    def _add_job_history(self, job_info: Dict):
        """添加任務歷史記錄"""
        self.job_history.append(job_info)
        # 保持歷史記錄在限制範圍內
        if len(self.job_history) > self.max_history:
            self.job_history = self.job_history[-self.max_history :]

    def _signal_handler(self, signum, frame):
        """處理停止信號"""
        logger.info(f"Received signal: {signum}")
        self._update_status("stopping")
        self.stop()
        sys.exit(0)

    def _update_status(self, daemon_status: str = "running"):
        """更新狀態文件"""
        try:
            jobs_info = {}
            for job in self.scheduler.get_jobs():
                # 安全地獲取 next_run_time
                next_run_time = None
                try:
                    if hasattr(job, 'next_run_time') and job.next_run_time:
                        next_run_time = job.next_run_time.isoformat()
                except (AttributeError, TypeError):
                    # 如果無法獲取 next_run_time，嘗試從 trigger 計算
                    try:
                        if hasattr(job.trigger, 'get_next_fire_time'):
                            next_fire_time = job.trigger.get_next_fire_time(None, datetime.now())
                            if next_fire_time:
                                next_run_time = next_fire_time.isoformat()
                    except Exception:
                        pass

                jobs_info[job.id] = {
                    "name": job.name,
                    "next_run_time": next_run_time,
                    "trigger": str(job.trigger),
                    "max_instances": getattr(job, 'max_instances', 1),
                }

            status = {
                "daemon_status": daemon_status,
                "start_time": self.start_time.isoformat(),
                "last_update": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "jobs": jobs_info,
                "job_history": self.job_history[-10:],  # 最近10條記錄
                "config_path": str(self.config_path),
                "health": {
                    "status": "healthy" if daemon_status == "running" else "unhealthy",
                    "last_check": datetime.now().isoformat(),
                },
            }
            self._write_status(status)
        except Exception as e:
            logger.error(f"Failed to update status: {e}")

    def token_refresh_job(self):
        """Token 刷新任務"""
        try:
            logger.info("開始執行 token 刷新任務")
            success = refresh_expired_access_tokens()
            if success:
                logger.info("Token 刷新任務完成")
            else:
                logger.error("Token 刷新任務失敗")
            return success
        except Exception as e:
            logger.error(f"Token 刷新任務異常: {e}")
            raise

    def quota_check_job(self):
        """Quota 檢查任務"""
        try:
            logger.info("開始執行 quota 檢查任務")
            success = check_quota_remaining()
            if success:
                logger.info("Quota 檢查任務完成")
            else:
                logger.error("Quota 檢查任務失敗")
            return success
        except Exception as e:
            logger.error(f"Quota 檢查任務異常: {e}")
            raise

    def health_check_job(self):
        """健康檢查任務"""
        try:
            logger.debug("執行健康檢查")
            self._update_status("running")
            logger.debug("健康檢查完成")
            return True
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            raise

    def setup_jobs(self):
        """設定排程任務"""
        jobs_added = 0
        jobs_config = self.daemon_config.get("jobs", {})

        # Token 刷新任務
        token_config = jobs_config.get("token_refresh", {})
        if token_config.get("enabled", True):
            interval_minutes = token_config.get("interval_minutes", 5)
            self.scheduler.add_job(
                self.token_refresh_job,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='token_refresh',
                name='JetBrains Token Refresh',
                replace_existing=True,
            )
            jobs_added += 1
            logger.info(f"Token 刷新任務已啟用 (每{interval_minutes}分鐘)")

        # Quota 檢查任務
        quota_config = jobs_config.get("quota_check", {})
        if quota_config.get("enabled", True):
            interval_minutes = quota_config.get("interval_minutes", 2)
            self.scheduler.add_job(
                self.quota_check_job,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='quota_check',
                name='JetBrains Quota Check',
                replace_existing=True,
            )
            jobs_added += 1
            logger.info(f"Quota 檢查任務已啟用 (每{interval_minutes}分鐘)")

        # 健康檢查任務
        health_config = jobs_config.get("health_check", {})
        if health_config.get("enabled", True):
            interval_minutes = health_config.get("interval_minutes", 1)
            self.scheduler.add_job(
                self.health_check_job,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id='health_check',
                name='Daemon Health Check',
                replace_existing=True,
            )
            jobs_added += 1
            logger.info(f"健康檢查任務已啟用 (每{interval_minutes}分鐘)")

        logger.info(f"已設定 {jobs_added} 個排程任務")

    def start(self):
        """啟動daemon"""
        logger.info("正在啟動 JetBrains Scheduler Daemon...")

        # 檢查配置文件
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")

        self.setup_jobs()
        self._update_status("running")

        # 顯示已排程的任務
        jobs = self.scheduler.get_jobs()
        logger.info(f"已載入 {len(jobs)} 個任務:")
        for job in jobs:
            # 安全地獲取 next_run_time
            next_run = '未知'
            try:
                if hasattr(job, 'next_run_time') and job.next_run_time:
                    next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            except (AttributeError, TypeError):
                pass
            logger.info(f"  - {job.name} ({job.id}): 下次執行 {next_run}")

        try:
            logger.info("Daemon 啟動成功，開始執行任務...")
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("收到鍵盤中斷信號")
            self.stop()

    def stop(self):
        """停止daemon"""
        logger.info("正在停止 Daemon...")
        self._update_status("stopped")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        logger.info("Daemon 已停止")


def main():
    """主程式"""

    parser = argparse.ArgumentParser(description="JetBrains Scheduler Daemon")
    parser.add_argument("--config", help="Path to config file", default="config.json")
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode with faster intervals"
    )
    args = parser.parse_args()

    logger.info("啟動 JetBrains Scheduler Daemon")

    # 創建並啟動daemon
    daemon = JetBrainsDaemon(config_path=args.config)

    if args.test:
        logger.info("運行在測試模式...")
        # 在測試模式下使用更短的間隔
        daemon.scheduler.add_job(
            daemon.token_refresh_job,
            trigger=IntervalTrigger(seconds=30),
            id='token_refresh_test',
            name='Token Refresh (Test)',
            replace_existing=True,
        )
        daemon.scheduler.add_job(
            daemon.quota_check_job,
            trigger=IntervalTrigger(minutes=1),
            id='quota_check_test',
            name='Quota Check (Test)',
            replace_existing=True,
        )

    daemon.start()


if __name__ == "__main__":
    main()
