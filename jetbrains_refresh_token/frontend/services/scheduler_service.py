"""
Scheduler Service for Streamlit Application
Manages APScheduler for background tasks and automatic token refresh
"""

import json
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

# Import streamlit for session state access
try:
    import streamlit as st

    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Define protocols for type safety
class JobProtocol(Protocol):
    """Protocol for job objects"""

    id: str
    name: str
    func: Callable
    trigger: Any
    next_run_time: Optional[datetime]
    max_instances: int
    misfire_grace_time: int


class EventProtocol(Protocol):
    """Protocol for event objects"""

    job_id: str
    scheduled_run_time: datetime
    exception: Optional[Exception]


class TriggerProtocol(Protocol):
    """Protocol for trigger objects"""

    pass


class SchedulerProtocol(Protocol):
    """Protocol for scheduler objects"""

    def start(self) -> None: ...
    def shutdown(self) -> None: ...
    def add_job(self, *args, **kwargs) -> None: ...
    def get_jobs(self) -> List[JobProtocol]: ...
    def add_listener(self, func: Callable, event_type: str) -> None: ...
    def remove_job(self, job_id: str) -> None: ...
    def pause_job(self, job_id: str) -> None: ...
    def resume_job(self, job_id: str) -> None: ...
    def modify_job(self, job_id: str, **changes) -> None: ...


# Import APScheduler with proper type handling
APSCHEDULER_AVAILABLE = False
EVENT_JOB_EXECUTED = "job_executed"
EVENT_JOB_ERROR = "job_error"

try:
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore
    from apscheduler.triggers.cron import CronTrigger  # type: ignore
    from apscheduler.triggers.interval import IntervalTrigger  # type: ignore

    APSCHEDULER_AVAILABLE = True

except ImportError:
    # Fallback implementations when APScheduler is not available
    class BackgroundScheduler:
        def __init__(self):
            self.running = False
            self._jobs: List[Any] = []

        def start(self):
            self.running = True

        def shutdown(self):
            self.running = False

        def add_job(self, *args, **kwargs):
            pass

        def get_jobs(self):
            return []

        def add_listener(self, func, event_type):
            pass

        def remove_job(self, job_id):
            pass

        def pause_job(self, job_id):
            pass

        def resume_job(self, job_id):
            pass

        def modify_job(self, job_id, **changes):
            pass

    class IntervalTrigger:
        def __init__(self, **kwargs):
            pass

    class CronTrigger:
        def __init__(self, **kwargs):
            pass


class SchedulerService:
    """Background scheduler service for automated tasks"""

    def __init__(self, config_helper=None, state_manager=None):
        self.config_helper = config_helper
        self.state_manager = state_manager
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.job_history = []
        self.max_history = 100
        self.event_listeners = {}

        # Setup event listeners
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Setup scheduler event listeners"""
        try:
            self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        except Exception as e:
            print(f"Warning: Could not setup event listeners: {e}")

    def _job_executed_listener(self, event):
        """Handle job execution events"""
        job_info = {
            'job_id': event.job_id,
            'scheduled_run_time': event.scheduled_run_time.isoformat(),
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
        }

        self._add_job_history(job_info)

        # Log to state manager if available
        if self.state_manager:
            session_id = 'system'
            if STREAMLIT_AVAILABLE and st is not None:
                try:
                    session_id = st.session_state.get('session_id', 'system')
                except:
                    session_id = 'system'

            self.state_manager.log_action(
                session_id,
                f"Job {event.job_id} completed",
                f"Scheduled time: {event.scheduled_run_time}",
            )

    def _job_error_listener(self, event):
        """Handle job error events"""
        job_info = {
            'job_id': event.job_id,
            'scheduled_run_time': event.scheduled_run_time.isoformat(),
            'status': 'error',
            'error': str(event.exception),
            'timestamp': datetime.now().isoformat(),
        }

        self._add_job_history(job_info)

        # Log to state manager if available
        if self.state_manager:
            session_id = 'system'
            if STREAMLIT_AVAILABLE and st is not None:
                try:
                    session_id = st.session_state.get('session_id', 'system')
                except:
                    session_id = 'system'

            self.state_manager.log_action(
                session_id, f"Job {event.job_id} failed", f"Error: {event.exception}"
            )

    def _add_job_history(self, job_info: Dict[str, Any]):
        """Add job execution to history"""
        self.job_history.append(job_info)

        # Keep only recent history
        if len(self.job_history) > self.max_history:
            self.job_history = self.job_history[-self.max_history :]

    def start(self) -> bool:
        """Start the scheduler"""
        try:
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True

                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    self.state_manager.log_action(
                        session_id, "Scheduler started", "Background scheduler service started"
                    )

                return True
            return False
        except Exception as e:
            print(f"Error starting scheduler: {e}")
            return False

    def stop(self) -> bool:
        """Stop the scheduler"""
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False

                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    self.state_manager.log_action(
                        session_id, "Scheduler stopped", "Background scheduler service stopped"
                    )

                return True
            return False
        except Exception as e:
            print(f"Error stopping scheduler: {e}")
            return False

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """Add interval-based job"""
        try:
            self.scheduler.add_job(
                func,
                trigger=IntervalTrigger(seconds=seconds, minutes=minutes, hours=hours),
                id=job_id,
                replace_existing=True,
                **kwargs,
            )

            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                interval_str = f"{hours or 0}h {minutes or 0}m {seconds or 0}s"
                self.state_manager.log_action(
                    session_id, f"Added interval job: {job_id}", f"Interval: {interval_str}"
                )

            return True
        except Exception as e:
            print(f"Error adding interval job {job_id}: {e}")
            return False

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """Add cron-based job"""
        try:
            self.scheduler.add_job(
                func,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=job_id,
                replace_existing=True,
                **kwargs,
            )

            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                cron_str = f"{hour or '*'}:{minute or '*'}"
                self.state_manager.log_action(
                    session_id, f"Added cron job: {job_id}", f"Schedule: {cron_str}"
                )

            return True
        except Exception as e:
            print(f"Error adding cron job {job_id}: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)

            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(session_id, f"Removed job: {job_id}", None)

            return True
        except Exception as e:
            print(f"Error removing job {job_id}: {e}")
            return False

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                job_info = {
                    'id': job.id,
                    'name': job.name,
                    'func': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                    'trigger': str(job.trigger),
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'max_instances': job.max_instances,
                    'misfire_grace_time': job.misfire_grace_time,
                }
                jobs.append(job_info)

            return jobs
        except Exception as e:
            print(f"Error getting jobs: {e}")
            return []

    def get_job_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent job execution history"""
        return self.job_history[-limit:] if self.job_history else []

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            'running': self.is_running,
            'jobs_count': len(self.scheduler.get_jobs()) if self.is_running else 0,
            'history_count': len(self.job_history),
            'uptime': self._calculate_uptime() if self.is_running else 0,
        }

    def _calculate_uptime(self) -> str:
        """Calculate scheduler uptime"""
        # This is a simplified implementation
        # In a real application, you'd track start time
        return "Running"

    def setup_default_jobs(self):
        """Setup default scheduled jobs"""
        if not self.config_helper:
            return

        # Auto-refresh access tokens every 30 minutes
        self.add_interval_job(
            func=self._refresh_access_tokens_job,
            job_id="auto_refresh_access_tokens",
            seconds=0,
            minutes=30,
            hours=0,
            max_instances=1,
        )

        # Auto-refresh ID tokens every 4 hours
        self.add_interval_job(
            func=self._refresh_id_tokens_job,
            job_id="auto_refresh_id_tokens",
            seconds=0,
            minutes=0,
            hours=4,
            max_instances=1,
        )

        # Check quotas every hour
        self.add_interval_job(
            func=self._check_quotas_job,
            job_id="auto_check_quotas",
            seconds=0,
            minutes=0,
            hours=1,
            max_instances=1,
        )

        # Backup config daily at 2 AM
        self.add_cron_job(
            func=self._backup_config_job,
            job_id="daily_config_backup",
            hour=2,
            minute=0,
            max_instances=1,
        )

    def _refresh_access_tokens_job(self):
        """Background job to refresh access tokens"""
        try:
            if self.config_helper is not None:
                success = self.config_helper.refresh_all_access_tokens()

                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    status = "Success" if success else "Failed"
                    self.state_manager.log_action(
                        session_id,
                        f"Auto refresh access tokens: {status}",
                        f"Timestamp: {datetime.now().isoformat()}",
                    )
            else:
                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    self.state_manager.log_action(
                        session_id,
                        "Auto refresh access tokens: Error",
                        "Config helper not available",
                    )
        except Exception as e:
            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(
                    session_id, "Auto refresh access tokens: Error", f"Error: {str(e)}"
                )

    def _refresh_id_tokens_job(self):
        """Background job to refresh ID tokens"""
        try:
            if self.config_helper is not None:
                success = self.config_helper.refresh_all_id_tokens()

                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    status = "Success" if success else "Failed"
                    self.state_manager.log_action(
                        session_id,
                        f"Auto refresh ID tokens: {status}",
                        f"Timestamp: {datetime.now().isoformat()}",
                    )
            else:
                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    self.state_manager.log_action(
                        session_id, "Auto refresh ID tokens: Error", "Config helper not available"
                    )
        except Exception as e:
            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(
                    session_id, "Auto refresh ID tokens: Error", f"Error: {str(e)}"
                )

    def _check_quotas_job(self):
        """Background job to check quotas"""
        try:
            if self.config_helper is not None:
                success = self.config_helper.check_all_quotas()

                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    status = "Success" if success else "Failed"
                    self.state_manager.log_action(
                        session_id,
                        f"Auto check quotas: {status}",
                        f"Timestamp: {datetime.now().isoformat()}",
                    )
            else:
                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    self.state_manager.log_action(
                        session_id, "Auto check quotas: Error", "Config helper not available"
                    )
        except Exception as e:
            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(
                    session_id, "Auto check quotas: Error", f"Error: {str(e)}"
                )

    def _backup_config_job(self):
        """Background job to backup configuration"""
        try:
            if self.config_helper is not None:
                success = self.config_helper.backup_config()

                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    status = "Success" if success else "Failed"
                    self.state_manager.log_action(
                        session_id,
                        f"Auto backup config: {status}",
                        f"Timestamp: {datetime.now().isoformat()}",
                    )
            else:
                if self.state_manager:
                    session_id = 'system'
                    if STREAMLIT_AVAILABLE and st is not None:
                        try:
                            session_id = st.session_state.get('session_id', 'system')
                        except:
                            session_id = 'system'

                    self.state_manager.log_action(
                        session_id, "Auto backup config: Error", "Config helper not available"
                    )
        except Exception as e:
            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(
                    session_id, "Auto backup config: Error", f"Error: {str(e)}"
                )

    def pause_job(self, job_id: str) -> bool:
        """Pause a specific job"""
        try:
            self.scheduler.pause_job(job_id)

            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(
                    session_id, f"Paused job: {job_id}", f"Timestamp: {datetime.now().isoformat()}"
                )

            return True
        except Exception as e:
            print(f"Error pausing job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)

            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(
                    session_id, f"Resumed job: {job_id}", f"Timestamp: {datetime.now().isoformat()}"
                )

            return True
        except Exception as e:
            print(f"Error resuming job {job_id}: {e}")
            return False

    def modify_job(self, job_id: str, **changes) -> bool:
        """Modify an existing job"""
        try:
            self.scheduler.modify_job(job_id, **changes)

            if self.state_manager:
                session_id = 'system'
                if STREAMLIT_AVAILABLE and st is not None:
                    try:
                        session_id = st.session_state.get('session_id', 'system')
                    except:
                        session_id = 'system'

                self.state_manager.log_action(
                    session_id, f"Modified job: {job_id}", f"Changes: {changes}"
                )

            return True
        except Exception as e:
            print(f"Error modifying job {job_id}: {e}")
            return False
