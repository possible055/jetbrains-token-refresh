"""
Daemon Status Component
Displays daemon service status and information (read-only)
"""

from datetime import datetime

import streamlit as st


def render_background_tasks_status():
    """Render daemon status section"""
    st.subheader("🔄 Daemon 服務狀態")

    # Check if daemon status reader is available
    daemon_reader = st.session_state.get('daemon_status_reader')

    if not daemon_reader:
        st.warning("⚠️ Daemon 狀態讀取器未啟用")
        return

    # Get daemon summary
    summary = daemon_reader.get_daemon_summary()

    # Display daemon status
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Daemon 狀態:**")

        if summary['is_running']:
            st.success(f"✅ 運行中")
        else:
            st.error(f"❌ {summary['daemon_status']}")

        st.metric("運行時間", summary['uptime'])
        st.metric("排程任務數", summary['jobs_count'])

    with col2:
        st.write("**執行統計:**")

        if summary['is_stale']:
            st.warning("⚠️ 狀態資訊過時")
        else:
            st.success("✅ 狀態資訊最新")

        st.metric("最近成功", summary['recent_success_count'])
        st.metric("最近失敗", summary['recent_error_count'])

    # Display scheduled jobs
    render_scheduled_jobs(daemon_reader)

    # # Display job history
    # render_job_history(daemon_reader)


# This function is no longer used since background tasks are handled by daemon
# def render_active_tasks(background_tasks):
#     """Render active tasks section (deprecated - now handled by daemon)"""
#     pass


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


# This function is no longer used since background tasks are handled by daemon
# def render_task_history(background_tasks):
#     """Render task history section (deprecated - now handled by daemon)"""
#     pass


# Manual task controls are no longer needed since tasks are handled by daemon


def render():
    """Main render function for background tasks status page"""
    st.title("🔄 背景任務管理")

    # Status overview
    render_background_tasks_status()

    st.markdown("---")

    # Manual controls are handled by daemon
