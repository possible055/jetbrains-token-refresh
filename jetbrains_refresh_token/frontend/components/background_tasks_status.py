"""
Background Tasks Status Component
Displays background task status and management interface
"""

from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from jetbrains_refresh_token.constants import DEFAULT_TIMEZONE


def render_background_tasks_status():
    """Render background tasks status section"""
    st.subheader("🔄 背景任務狀態")

    # Check if background services are available
    background_tasks = st.session_state.get('background_tasks')
    scheduler_service = st.session_state.get('scheduler_service')

    if not background_tasks or not scheduler_service:
        st.warning("⚠️ 背景服務未啟用")
        return

    # Display service status
    col1, col2 = st.columns(2)

    with col1:
        st.write("**任務管理器狀態:**")
        task_stats = background_tasks.get_statistics()

        if task_stats['workers_running']:
            st.success(f"✅ 運行中 ({task_stats['worker_count']} 個工作執行緒)")
        else:
            st.error("❌ 已停止")

        st.metric("活躍任務", task_stats['active_tasks'])
        st.metric("已完成任務", task_stats['completed_tasks'])
        st.metric("失敗任務", task_stats['failed_tasks'])

    with col2:
        st.write("**調度器狀態:**")
        scheduler_status = scheduler_service.get_status()

        if scheduler_status['running']:
            st.success(f"✅ 運行中 ({scheduler_status['jobs_count']} 個排程任務)")
        else:
            st.error("❌ 已停止")

        st.metric("排程任務數", scheduler_status['jobs_count'])
        st.metric("歷史記錄", scheduler_status['history_count'])

    # Display active tasks
    render_active_tasks(background_tasks)

    # Display scheduled jobs
    render_scheduled_jobs(scheduler_service)

    # Display task history
    render_task_history(background_tasks)


def render_active_tasks(background_tasks):
    """Render active tasks section"""
    st.write("**活躍任務:**")

    active_tasks = background_tasks.get_all_tasks()

    if not active_tasks:
        st.info("📝 目前沒有活躍任務")
        return

    for task in active_tasks:
        with st.expander(f"{task['name']} - {task['status']}", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**任務 ID:** {task['task_id'][:8]}...")
                st.write(f"**狀態:** {task['status']}")
                st.write(f"**優先級:** {task['priority']}")

            with col2:
                st.write(f"**進度:** {task['progress']}%")
                if task['created_at']:
                    created_time = datetime.fromisoformat(task['created_at'])
                    st.write(f"**創建時間:** {created_time.strftime('%H:%M:%S')}")
                if task['started_at']:
                    started_time = datetime.fromisoformat(task['started_at'])
                    st.write(f"**開始時間:** {started_time.strftime('%H:%M:%S')}")

            with col3:
                if task['duration']:
                    st.write(f"**執行時間:** {task['duration']:.2f} 秒")
                if task['error']:
                    st.error(f"**錯誤:** {task['error']}")
                if task['result']:
                    st.success(f"**結果:** {task['result']}")

                # Cancel button for pending tasks
                if task['status'] == 'pending':
                    if st.button("❌ 取消", key=f"cancel_{task['task_id']}"):
                        success = background_tasks.cancel_task(task['task_id'])
                        if success:
                            st.success("任務已取消")
                            st.rerun()


def render_scheduled_jobs(scheduler_service):
    """Render scheduled jobs section"""
    st.write("**排程任務:**")

    jobs = scheduler_service.get_jobs()

    if not jobs:
        st.info("📝 目前沒有排程任務")
        return

    for job in jobs:
        with st.expander(f"{job['name'] or job['id']} - {job['trigger']}", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**任務 ID:** {job['id']}")
                st.write(f"**函數:** {job['func']}")
                st.write(f"**觸發器:** {job['trigger']}")

            with col2:
                if job['next_run_time']:
                    next_run = datetime.fromisoformat(job['next_run_time'])
                    st.write(f"**下次執行:** {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**最大實例數:** {job['max_instances']}")
                st.write(f"**容錯時間:** {job['misfire_grace_time']} 秒")

                # Job control buttons
                col_pause, col_resume, col_remove = st.columns(3)

                with col_pause:
                    if st.button("⏸️ 暫停", key=f"pause_{job['id']}"):
                        success = scheduler_service.pause_job(job['id'])
                        if success:
                            st.success("任務已暫停")
                            st.rerun()

                with col_resume:
                    if st.button("▶️ 恢復", key=f"resume_{job['id']}"):
                        success = scheduler_service.resume_job(job['id'])
                        if success:
                            st.success("任務已恢復")
                            st.rerun()

                with col_remove:
                    if st.button("🗑️ 移除", key=f"remove_{job['id']}"):
                        success = scheduler_service.remove_job(job['id'])
                        if success:
                            st.success("任務已移除")
                            st.rerun()


def render_task_history(background_tasks):
    """Render task history section"""
    st.write("**任務歷史:**")

    history = background_tasks.get_task_history(limit=10)

    if not history:
        st.info("📝 目前沒有任務歷史記錄")
        return

    # Display in table format
    history_data = []
    for task in history:
        completed_time = "進行中"
        if task['completed_at']:
            dt = datetime.fromisoformat(task['completed_at'])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
            completed_time = dt.strftime('%H:%M:%S')

        history_data.append(
            {
                "任務名稱": task['name'],
                "狀態": task['status'],
                "完成時間": completed_time,
                "執行時間": f"{task['duration']:.2f}s" if task['duration'] else "N/A",
                "結果": task['result'] or task['error'] or "無",
            }
        )

    st.dataframe(history_data, use_container_width=True)

    # Clear history button
    if st.button("🗑️ 清除歷史記錄", key="clear_task_history"):
        background_tasks.clear_history()
        st.success("任務歷史記錄已清除")
        st.rerun()


# def render_task_controls():
#     """Render manual task control section"""
#     st.subheader("🎛️ 手動任務控制")

#     background_tasks = st.session_state.get('background_tasks')
#     if not background_tasks:
#         st.warning("⚠️ 背景任務服務未啟用")
#         return

#     col1, col2, col3 = st.columns(3)

#     with col1:
#         if st.button("🔄 刷新所有 Token", key="manual_refresh_all_tokens"):
#             task_id = background_tasks.add_refresh_access_tokens_task(priority=8)
#             st.success(f"✅ 已添加任務 (ID: {task_id[:8]})")

#     with col2:
#         if st.button("📊 檢查所有配額", key="manual_check_all_quotas"):
#             task_id = background_tasks.add_check_quotas_task(priority=5)
#             st.success(f"✅ 已添加任務 (ID: {task_id[:8]})")

#     with col3:
#         if st.button("💾 備份配置", key="manual_backup_config"):
#             task_id = background_tasks.add_backup_config_task(priority=3)
#             st.success(f"✅ 已添加任務 (ID: {task_id[:8]})")


def render():
    """Main render function for background tasks status page"""
    st.title("🔄 背景任務管理")

    # Status overview
    render_background_tasks_status()

    st.markdown("---")

    # # Manual controls
    # render_task_controls()
