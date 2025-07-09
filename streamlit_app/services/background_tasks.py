"""
Background Tasks Module for Streamlit Application
Provides task management and monitoring capabilities
"""

import json
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TaskStatus:
    """Task status constants"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackgroundTask:
    """Individual background task"""

    def __init__(
        self,
        task_id: str,
        name: str,
        func: Callable,
        args: tuple = None,
        kwargs: dict = None,
        priority: int = 0,
    ):
        self.task_id = task_id
        self.name = name
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.progress = 0
        self.thread = None

    def start(self):
        """Start the task execution"""
        if self.status != TaskStatus.PENDING:
            return False

        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()

        # Create and start thread
        self.thread = threading.Thread(target=self._execute)
        self.thread.daemon = True
        self.thread.start()

        return True

    def _execute(self):
        """Execute the task"""
        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.status = TaskStatus.COMPLETED
            self.progress = 100
        except Exception as e:
            self.error = str(e)
            self.status = TaskStatus.FAILED
        finally:
            self.completed_at = datetime.now()

    def cancel(self):
        """Cancel the task if possible"""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.CANCELLED
            self.completed_at = datetime.now()
            return True
        return False

    def get_info(self) -> Dict[str, Any]:
        """Get task information"""
        duration = None
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': self.status,
            'priority': self.priority,
            'progress': self.progress,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': duration,
            'result': str(self.result) if self.result else None,
            'error': self.error,
        }


class BackgroundTasks:
    """Background task management system"""

    def __init__(self, config_helper=None, state_manager=None):
        self.config_helper = config_helper
        self.state_manager = state_manager
        self.tasks = {}
        self.task_history = []
        self.max_history = 100
        self.worker_threads = []
        self.max_workers = 3
        self.running = False
        self.task_queue = []
        self.lock = threading.Lock()

        # Start worker threads
        self.start_workers()

    def start_workers(self):
        """Start worker threads"""
        if self.running:
            return

        self.running = True

        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, args=(i,))
            worker.daemon = True
            worker.start()
            self.worker_threads.append(worker)

        if self.state_manager:
            self.state_manager.log_action(
                "Background workers started", f"Started {self.max_workers} worker threads"
            )

    def stop_workers(self):
        """Stop worker threads"""
        self.running = False

        if self.state_manager:
            self.state_manager.log_action(
                "Background workers stopped", f"Stopped {len(self.worker_threads)} worker threads"
            )

        self.worker_threads = []

    def _worker_loop(self, worker_id: int):
        """Worker thread loop"""
        while self.running:
            try:
                # Get next task from queue
                task = self._get_next_task()

                if task:
                    # Execute task
                    task.start()

                    # Wait for completion
                    if task.thread:
                        task.thread.join()

                    # Move to history
                    self._add_to_history(task)

                    # Remove from active tasks
                    with self.lock:
                        if task.task_id in self.tasks:
                            del self.tasks[task.task_id]

                else:
                    # No tasks available, sleep briefly
                    time.sleep(0.1)

            except Exception as e:
                if self.state_manager:
                    self.state_manager.log_action(f"Worker {worker_id} error", f"Error: {str(e)}")
                time.sleep(1)

    def _get_next_task(self) -> Optional[BackgroundTask]:
        """Get next task from queue"""
        with self.lock:
            if not self.task_queue:
                return None

            # Sort by priority (higher priority first)
            self.task_queue.sort(key=lambda t: t.priority, reverse=True)

            # Get highest priority pending task
            for task in self.task_queue:
                if task.status == TaskStatus.PENDING:
                    self.task_queue.remove(task)
                    return task

            return None

    def _add_to_history(self, task: BackgroundTask):
        """Add task to history"""
        with self.lock:
            self.task_history.append(task)

            # Keep only recent history
            if len(self.task_history) > self.max_history:
                self.task_history = self.task_history[-self.max_history :]

    def add_task(
        self, name: str, func: Callable, args: tuple = None, kwargs: dict = None, priority: int = 0
    ) -> str:
        """Add a new background task"""
        task_id = str(uuid.uuid4())

        task = BackgroundTask(
            task_id=task_id, name=name, func=func, args=args, kwargs=kwargs, priority=priority
        )

        with self.lock:
            self.tasks[task_id] = task
            self.task_queue.append(task)

        if self.state_manager:
            self.state_manager.log_action(
                f"Added background task: {name}", f"Task ID: {task_id}, Priority: {priority}"
            )

        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                return task.get_info()

            # Check history
            for task in self.task_history:
                if task.task_id == task_id:
                    return task.get_info()

        return None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all active tasks"""
        with self.lock:
            return [task.get_info() for task in self.tasks.values()]

    def get_task_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get task history"""
        with self.lock:
            recent_history = self.task_history[-limit:] if self.task_history else []
            return [task.get_info() for task in recent_history]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                success = task.cancel()

                if success and self.state_manager:
                    self.state_manager.log_action(
                        f"Cancelled task: {task.name}", f"Task ID: {task_id}"
                    )

                return success

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        with self.lock:
            active_tasks = len(self.tasks)
            completed_tasks = len(
                [t for t in self.task_history if t.status == TaskStatus.COMPLETED]
            )
            failed_tasks = len([t for t in self.task_history if t.status == TaskStatus.FAILED])

            # Status distribution
            status_counts = {}
            for task in self.tasks.values():
                status_counts[task.status] = status_counts.get(task.status, 0) + 1

            return {
                'active_tasks': active_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'total_history': len(self.task_history),
                'queue_length': len(self.task_queue),
                'worker_count': len(self.worker_threads),
                'workers_running': self.running,
                'status_distribution': status_counts,
            }

    def refresh_access_tokens_task(self, account_name: str = None, forced: bool = False):
        """Background task to refresh access tokens"""
        if account_name:
            # Refresh specific account
            return self.config_helper.refresh_account_access_token(account_name, forced)
        else:
            # Refresh all accounts
            return self.config_helper.refresh_all_access_tokens(forced)

    def refresh_id_tokens_task(self, account_name: str = None, forced: bool = False):
        """Background task to refresh ID tokens"""
        if account_name:
            # Refresh specific account
            return self.config_helper.refresh_account_id_token(account_name, forced)
        else:
            # Refresh all accounts
            return self.config_helper.refresh_all_id_tokens(forced)

    def check_quotas_task(self, account_name: str = None):
        """Background task to check quotas"""
        if account_name:
            # Check specific account quota
            accounts = self.config_helper.get_accounts()
            for account in accounts:
                if account['name'] == account_name:
                    return self.config_helper.check_all_quotas()
            return False
        else:
            # Check all quotas
            return self.config_helper.check_all_quotas()

    def backup_config_task(self):
        """Background task to backup configuration"""
        return self.config_helper.backup_config()

    def add_refresh_access_tokens_task(
        self, account_name: str = None, forced: bool = False, priority: int = 5
    ):
        """Add refresh access tokens task"""
        task_name = f"Refresh Access Tokens"
        if account_name:
            task_name += f" - {account_name}"

        return self.add_task(
            name=task_name,
            func=self.refresh_access_tokens_task,
            kwargs={'account_name': account_name, 'forced': forced},
            priority=priority,
        )

    def add_refresh_id_tokens_task(
        self, account_name: str = None, forced: bool = False, priority: int = 5
    ):
        """Add refresh ID tokens task"""
        task_name = f"Refresh ID Tokens"
        if account_name:
            task_name += f" - {account_name}"

        return self.add_task(
            name=task_name,
            func=self.refresh_id_tokens_task,
            kwargs={'account_name': account_name, 'forced': forced},
            priority=priority,
        )

    def add_check_quotas_task(self, account_name: str = None, priority: int = 3):
        """Add check quotas task"""
        task_name = f"Check Quotas"
        if account_name:
            task_name += f" - {account_name}"

        return self.add_task(
            name=task_name,
            func=self.check_quotas_task,
            kwargs={'account_name': account_name},
            priority=priority,
        )

    def add_backup_config_task(self, priority: int = 1):
        """Add backup configuration task"""
        return self.add_task(
            name="Backup Configuration", func=self.backup_config_task, priority=priority
        )

    def clear_history(self):
        """Clear task history"""
        with self.lock:
            self.task_history = []

        if self.state_manager:
            self.state_manager.log_action(
                "Task history cleared", f"Cleared at {datetime.now().isoformat()}"
            )

    def get_active_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get active tasks by status"""
        with self.lock:
            filtered_tasks = [
                task.get_info() for task in self.tasks.values() if task.status == status
            ]
            return filtered_tasks

    def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information"""
        with self.lock:
            queue_info = {
                'total_queued': len(self.task_queue),
                'pending_tasks': len(
                    [t for t in self.task_queue if t.status == TaskStatus.PENDING]
                ),
                'queue_by_priority': {},
            }

            # Group by priority
            for task in self.task_queue:
                priority = task.priority
                if priority not in queue_info['queue_by_priority']:
                    queue_info['queue_by_priority'][priority] = 0
                queue_info['queue_by_priority'][priority] += 1

            return queue_info
