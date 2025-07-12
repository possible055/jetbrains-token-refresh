"""
Daemon Status Reader for Streamlit Frontend

This module provides functionality to read status information from the
independent APScheduler daemon service.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from jetbrains_refresh_token.constants import DEFAULT_TIMEZONE
from jetbrains_refresh_token.log_config import get_logger

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
logger = get_logger("daemon_status_reader")


class DaemonStatusReader:
    """Reader for daemon status information."""

    def __init__(self, status_file_path: Optional[str] = None):
        """
        Initialize the status reader.

        Args:
            status_file_path: Path to the daemon status file
        """
        self.status_file = (
            Path(status_file_path) if status_file_path else Path("logs/scheduler_status.json")
        )
        self._last_read_time = None
        self._cached_status = None

    def is_daemon_running(self) -> bool:
        """
        Check if the daemon is currently running.

        Returns:
            bool: True if daemon is running, False otherwise
        """
        try:
            status = self.get_status()
            return status.get("scheduler_status") == "running"
        except Exception:
            return False

    def get_status(self, use_cache: bool = True) -> Dict:
        """
        Get the current daemon status.

        Args:
            use_cache: Whether to use cached status if available

        Returns:
            Dict: Status information from daemon
        """
        try:
            # Check if file exists
            if not self.status_file.exists():
                return self._get_default_status("file_not_found")

            # Get file modification time
            file_mtime = self.status_file.stat().st_mtime

            # Use cache if available and file hasn't changed
            if (
                use_cache
                and self._cached_status
                and self._last_read_time
                and file_mtime <= self._last_read_time
            ):
                return self._cached_status

            # Read status file
            with open(self.status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)

            # Update cache
            self._cached_status = status
            self._last_read_time = file_mtime

            return status

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse status file: {e}")
            return self._get_default_status("parse_error")
        except Exception as e:
            logger.error(f"Failed to read status file: {e}")
            return self._get_default_status("read_error")

    def get_jobs_info(self) -> Dict:
        """
        Get information about scheduled jobs.

        Returns:
            Dict: Jobs information
        """
        status = self.get_status()
        return status.get("jobs", {})

    def get_job_history(self) -> List[Dict]:
        """
        Get job execution history.

        Returns:
            List[Dict]: List of job execution records
        """
        status = self.get_status()
        return status.get("job_history", [])

    def get_health_info(self) -> Dict:
        """
        Get daemon health information.

        Returns:
            Dict: Health information
        """
        status = self.get_status()
        return status.get("health", {})

    def get_uptime_info(self) -> Dict:
        """
        Get daemon uptime information.

        Returns:
            Dict: Uptime information including start time and duration
        """
        status = self.get_status()

        uptime_info = {
            "start_time": status.get("start_time"),
            "uptime_seconds": status.get("uptime_seconds", 0),
            "last_update": status.get("last_update"),
            "status": status.get("scheduler_status", "unknown"),
        }

        # Calculate human-readable uptime
        if uptime_info["uptime_seconds"]:
            uptime_seconds = uptime_info["uptime_seconds"]
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            uptime_info["uptime_human"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            uptime_info["uptime_human"] = "00:00:00"

        return uptime_info

    def get_next_job_runs(self) -> List[Dict]:
        """
        Get information about next scheduled job runs.

        Returns:
            List[Dict]: List of upcoming job runs
        """
        jobs = self.get_jobs_info()
        next_runs = []

        for job_id, job_info in jobs.items():
            next_run_time = job_info.get("next_run_time")
            if next_run_time:
                try:
                    next_run_dt = datetime.fromisoformat(next_run_time)
                    # Ensure datetime is timezone-aware
                    if next_run_dt.tzinfo is None:
                        next_run_dt = next_run_dt.replace(tzinfo=DEFAULT_TIMEZONE)
                    next_runs.append(
                        {
                            "job_id": job_id,
                            "job_name": job_info.get("name", job_id),
                            "next_run_time": next_run_time,
                            "next_run_datetime": next_run_dt,
                            "trigger": job_info.get("trigger", "unknown"),
                        }
                    )
                except ValueError:
                    logger.warning(f"Invalid datetime format for job {job_id}: {next_run_time}")

        # Sort by next run time
        next_runs.sort(key=lambda x: x["next_run_datetime"])
        return next_runs

    def get_recent_job_results(self, limit: int = 10) -> List[Dict]:
        """
        Get recent job execution results.

        Args:
            limit: Maximum number of results to return

        Returns:
            List[Dict]: Recent job execution results
        """
        history = self.get_job_history()

        # Sort by execution time (most recent first)
        sorted_history = sorted(history, key=lambda x: x.get("execution_time", ""), reverse=True)

        return sorted_history[:limit]

    def _get_default_status(self, error_type: str) -> Dict:
        """
        Get default status when daemon is not available.

        Args:
            error_type: Type of error encountered

        Returns:
            Dict: Default status information
        """
        return {
            "scheduler_status": "unavailable",
            "error_type": error_type,
            "start_time": None,
            "last_update": datetime.now().isoformat(),
            "uptime_seconds": 0,
            "jobs": {},
            "job_history": [],
            "config_path": "config.json",
            "health": {"status": "unhealthy", "last_check": datetime.now().isoformat()},
        }

    def refresh_status(self) -> Dict:
        """
        Force refresh of status (bypass cache).

        Returns:
            Dict: Fresh status information
        """
        return self.get_status(use_cache=False)

    def is_status_stale(self, max_age_seconds: int = 300) -> bool:
        """
        Check if the status information is stale.

        Args:
            max_age_seconds: Maximum age in seconds before considering stale

        Returns:
            bool: True if status is stale, False otherwise
        """
        status = self.get_status()
        last_update = status.get("last_update")

        if not last_update:
            return True

        try:
            last_update_dt = datetime.fromisoformat(last_update)
            age_seconds = (datetime.now() - last_update_dt).total_seconds()
            return age_seconds > max_age_seconds
        except ValueError:
            return True

    def get_daemon_summary(self) -> Dict:
        """
        Get a summary of daemon status for display.

        Returns:
            Dict: Summary information
        """
        status = self.get_status()
        uptime_info = self.get_uptime_info()
        jobs = self.get_jobs_info()
        recent_history = self.get_recent_job_results(5)

        # Count successful vs failed jobs in recent history
        success_count = sum(1 for job in recent_history if job.get("status") == "success")
        error_count = sum(1 for job in recent_history if job.get("status") == "error")

        return {
            "daemon_status": status.get("scheduler_status", "unknown"),
            "is_running": self.is_daemon_running(),
            "uptime": uptime_info.get("uptime_human", "00:00:00"),
            "jobs_count": len(jobs),
            "recent_success_count": success_count,
            "recent_error_count": error_count,
            "is_stale": self.is_status_stale(),
            "last_update": status.get("last_update"),
            "health_status": status.get("health", {}).get("status", "unknown"),
        }
