"""
Daemon Status Component
Displays daemon service status and information (read-only)
"""

from datetime import datetime

import streamlit as st

from jetbrains_refresh_token.constants import DEFAULT_TIMEZONE


def render_daemon_status():
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

    # Display job history
    render_job_history(daemon_reader)


def render_scheduled_jobs(daemon_reader):
    """Render scheduled jobs section"""
    st.write("**排程任務:**")

    jobs = daemon_reader.get_jobs_info()

    if not jobs:
        st.info("📝 目前沒有排程任務")
        return

    # Create a table for scheduled jobs
    job_data = []
    for job_id, job_info in jobs.items():
        next_run = job_info.get('next_run_time', '未知')
        if next_run and next_run != '未知':
            try:
                next_run_dt = datetime.fromisoformat(next_run)
                next_run_str = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                next_run_str = str(next_run)
        else:
            next_run_str = "未知"

        job_data.append(
            {
                "ID": job_id,
                "名稱": job_info.get('name', '未知'),
                "觸發器": job_info.get('trigger', '未知'),
                "下次執行": next_run_str,
                "最大實例": job_info.get('max_instances', 1),
            }
        )

    if job_data:
        st.dataframe(job_data, use_container_width=True)

        # Refresh button only (read-only interface)
        if st.button("🔄 刷新排程列表", key="refresh_scheduled_jobs"):
            daemon_reader.refresh_status()
            st.rerun()


def render_job_history(daemon_reader):
    """Render job execution history section"""
    st.write("**執行歷史:**")

    history = daemon_reader.get_recent_job_results(limit=20)

    if not history:
        st.info("📝 目前沒有執行歷史記錄")
        return

    # Create a table for job history
    history_data = []
    for record in history:
        status_emoji = "✅" if record.get('status') == 'success' else "❌"

        execution_time = record.get('execution_time', '')
        if execution_time:
            try:
                exec_dt = datetime.fromisoformat(execution_time)
                exec_time_str = exec_dt.strftime("%m-%d %H:%M:%S")
            except ValueError:
                exec_time_str = execution_time
        else:
            exec_time_str = "未知"

        duration = record.get('duration', 0)
        duration_str = f"{duration:.1f}s" if duration else "N/A"

        history_data.append(
            {
                "狀態": status_emoji,
                "任務ID": record.get('job_id', '未知'),
                "執行時間": exec_time_str,
                "持續時間": duration_str,
                "錯誤": record.get('error', '') if record.get('status') == 'error' else '',
            }
        )

    if history_data:
        st.dataframe(history_data, use_container_width=True)

        # Refresh button only (read-only interface)
        if st.button("🔄 刷新執行歷史", key="refresh_job_history"):
            daemon_reader.refresh_status()
            st.rerun()


def render_next_job_runs(daemon_reader):
    """Render next scheduled job runs"""
    st.write("**即將執行的任務:**")

    next_runs = daemon_reader.get_next_job_runs()

    if not next_runs:
        st.info("📝 目前沒有即將執行的任務")
        return

    # Display next 5 upcoming jobs
    for job_run in next_runs[:5]:
        time_until = job_run['next_run_datetime'] - datetime.now(DEFAULT_TIMEZONE)

        if time_until.total_seconds() > 0:
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            time_str = f"{hours}小時{minutes}分鐘後"
        else:
            time_str = "即將執行"

        st.write(f"**{job_run['job_name']}** - {time_str}")


def render_daemon_health(daemon_reader):
    """Render daemon health information"""
    st.write("**健康狀態:**")

    health_info = daemon_reader.get_health_info()
    uptime_info = daemon_reader.get_uptime_info()

    col1, col2 = st.columns(2)

    with col1:
        health_status = health_info.get('status', 'unknown')
        if health_status == 'healthy':
            st.success("✅ 健康")
        else:
            st.error(f"❌ {health_status}")

        last_check = health_info.get('last_check', '')
        if last_check:
            try:
                check_dt = datetime.fromisoformat(last_check)
                check_str = check_dt.strftime("%H:%M:%S")
                st.write(f"最後檢查: {check_str}")
            except ValueError:
                st.write(f"最後檢查: {last_check}")

    with col2:
        st.write(f"運行時間: {uptime_info.get('uptime_human', '未知')}")

        last_update = uptime_info.get('last_update', '')
        if last_update:
            try:
                update_dt = datetime.fromisoformat(last_update)
                update_str = update_dt.strftime("%H:%M:%S")
                st.write(f"最後更新: {update_str}")
            except ValueError:
                st.write(f"最後更新: {last_update}")


# Backward compatibility - keep the old function name
def render_background_tasks_status():
    """Backward compatibility wrapper"""
    render_daemon_status()
