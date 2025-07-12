from datetime import datetime, timedelta
from typing import Any, Dict, List

import streamlit as st

from jetbrains_refresh_token.constants import DEFAULT_TIMEZONE


def render():
    """Render the dashboard page"""
    st.markdown('<h1 class="main-header">控制台</h1>', unsafe_allow_html=True)

    # Get configuration helper
    config_helper = st.session_state.get('config_helper')
    if not config_helper:
        st.error("配置助手未初始化")
        return

    # System overview section
    render_system_overview(config_helper)

    # Quick actions section
    render_quick_actions()

    # Warnings and alerts section
    render_warnings_section(config_helper)

    # Statistics section
    render_statistics_section(config_helper)

    # # Recent operations section
    # render_recent_operations()

    # Update last refresh time
    st.session_state.last_refresh = datetime.now(DEFAULT_TIMEZONE)


def render_system_overview(config_helper):
    """Render system overview cards"""
    st.subheader("系统概览")

    # Get system info
    system_info = config_helper.get_system_info()
    accounts = config_helper.get_accounts()

    # Create columns for overview cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
        <div class="status-card">
            <h4>📁 配置档案</h4>
            <p><strong>状态:</strong> {'✅ 正常' if system_info.get('config_exists', False) else '❌ 不存在'}</p>
            <p><strong>大小:</strong> {system_info.get('config_size', 0)} bytes</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="status-card">
            <h4>👥 帐号总数</h4>
            <p><strong>总计:</strong> {len(accounts)}</p>
            <p><strong>活跃:</strong> {sum(1 for acc in accounts if acc['status'] == '🟢 正常')}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        expired_tokens = sum(1 for acc in accounts if acc['access_token_expired'])
        st.markdown(
            f"""
        <div class="{'warning-card' if expired_tokens > 0 else 'status-card'}">
            <h4>🔑 金钥状态</h4>
            <p><strong>正常:</strong> {len(accounts) - expired_tokens}</p>
            <p><strong>过期:</strong> {expired_tokens}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # with col4:
    #     last_refresh = st.session_state.get('last_refresh')
    #     refresh_time = last_refresh.strftime('%H:%M:%S') if last_refresh else '未知'
    #     st.markdown(
    #         f"""
    #     <div class="status-card">
    #         <h4>🔄 最后更新</h4>
    #         <p><strong>状态:</strong> {'🟢 已同步' if last_refresh else '⚪ 未同步'}</p>
    #         <p><strong>时间:</strong> {refresh_time}</p>
    #     </div>
    #     """,
    #         unsafe_allow_html=True,
    #     )


def render_warnings_section(config_helper):
    """Render warnings and alerts section"""
    st.subheader("警告与提醒")

    accounts = config_helper.get_accounts()
    warnings = generate_warnings(accounts)

    if not warnings:
        st.success("✅ 所有系统运作正常")
    else:
        for warning in warnings:
            warning_type = warning['type']
            message = warning['message']
            account = warning.get('account', '')

            if warning_type == 'error':
                st.markdown(
                    f"""
                <div class="error-card">
                    <strong>❌ 错误</strong> - {account}<br>
                    {message}
                </div>
                """,
                    unsafe_allow_html=True,
                )
            elif warning_type == 'warning':
                st.markdown(
                    f"""
                <div class="warning-card">
                    <strong>⚠️ 警告</strong> - {account}<br>
                    {message}
                </div>
                """,
                    unsafe_allow_html=True,
                )


def render_statistics_section(config_helper):
    """Render statistics section"""
    st.subheader("统计资讯")

    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚无帐户资料")
        return

    # Create tabs for different statistics
    tab1, tab2, tab3 = st.tabs(["金钥状态", "配额使用", "帐户活动"])

    with tab1:
        render_token_statistics(accounts)

    with tab2:
        render_quota_statistics(accounts)

    with tab3:
        render_activity_statistics(accounts)


def render_token_statistics(accounts: List[Dict[str, Any]]):
    """Render token status statistics"""
    (col1,) = st.columns(1)

    with col1:
        # Access token statistics
        access_expired = sum(1 for acc in accounts if acc['access_token_expired'])
        access_valid = len(accounts) - access_expired

        st.write("**Access Token 状态**")
        st.write(f"🟢 有效: {access_valid}")
        st.write(f"🔴 过期: {access_expired}")

        # Simple progress bar simulation
        if len(accounts) > 0:
            valid_percentage = (access_valid / len(accounts)) * 100
            st.progress(valid_percentage / 100)
            st.write(f"有效率: {valid_percentage:.1f}%")


def render_quota_statistics(accounts: List[Dict[str, Any]]):
    """Render quota usage statistics"""
    quota_accounts = [acc for acc in accounts if acc.get('quota_info')]

    if not quota_accounts:
        st.info("📊 尚无配额资讯")
        return

    # Calculate quota statistics
    total_accounts = len(quota_accounts)
    critical_accounts = sum(
        1 for acc in quota_accounts if acc['quota_info'].get('status') == 'critical'
    )
    warning_accounts = sum(
        1 for acc in quota_accounts if acc['quota_info'].get('status') == 'warning'
    )
    normal_accounts = total_accounts - critical_accounts - warning_accounts

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("🟢 正常", normal_accounts)

    with col2:
        st.metric("🟡 警告", warning_accounts)

    with col3:
        st.metric("🔴 危险", critical_accounts)

    # Quota usage details
    st.write("**配额使用详情**")
    for account in quota_accounts:
        quota_info = account['quota_info']
        usage = quota_info.get('usage_percentage', 0)
        status = quota_info.get('status', 'unknown')

        status_color = {'normal': '🟢', 'warning': '🟡', 'critical': '🔴', 'unknown': '⚪'}.get(
            status, '⚪'
        )

        st.write(f"{status_color} {account['name']}: {usage:.1f}%")


def render_activity_statistics(accounts: List[Dict[str, Any]]):
    """Render account activity statistics"""
    st.write("**帐户活动统计**")

    # Show account creation times
    current_time = datetime.now(DEFAULT_TIMEZONE)
    for account in accounts:
        created_time = account.get('created_time')
        if created_time:
            created_dt = datetime.fromtimestamp(created_time, tz=DEFAULT_TIMEZONE)
            days_old = (current_time - created_dt).days
            st.write(
                f"👤 {account['name']}: 建立于 {created_dt.strftime('%Y-%m-%d')} ({days_old} 天前)"
            )
        else:
            st.write(f"👤 {account['name']}: 建立时间未知")


# def render_recent_operations():
#     """Render recent operations section"""
#     st.subheader("最近操作")

#     # Get session logs from state manager
#     state_manager = st.session_state.get('state_manager')
#     if not state_manager:
#         st.info("📝 无操作记录")
#         return

#     session_id = st.session_state.get('session_id', '')
#     logs = state_manager.get_session_logs(session_id, limit=10)

#     if not logs:
#         st.info("📝 本次会话尚无操作记录")
#         return

#     for action, details, timestamp in logs:
#         # Parse timestamp and ensure it has timezone info
#         dt = datetime.fromisoformat(timestamp)
#         if dt.tzinfo is None:
#             dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
#         formatted_time = dt.strftime('%H:%M:%S')
#         st.write(f"🕐 {formatted_time} - {action}")
#         if details:
#             st.write(f"   └─ {details}")


def generate_warnings(accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate warnings based on account status"""
    warnings = []

    for account in accounts:
        account_name = account['name']

        # Check for expired tokens
        if account['access_token_expired']:
            warnings.append(
                {
                    'type': 'error',
                    'account': account_name,
                    'message': 'Access Token 已过期，需要立即刷新',
                }
            )

        # Check for quota warnings
        quota_info = account.get('quota_info', {})
        quota_status = quota_info.get('status', 'unknown')

        if quota_status == 'critical':
            warnings.append(
                {
                    'type': 'error',
                    'account': account_name,
                    'message': f'配额使用率过高 ({quota_info.get("usage_percentage", 0):.1f}%)',
                }
            )
        elif quota_status == 'warning':
            warnings.append(
                {
                    'type': 'warning',
                    'account': account_name,
                    'message': f'配额使用率偏高 ({quota_info.get("usage_percentage", 0):.1f}%)',
                }
            )

        # Check for token expiration in near future
        access_expires_at = account.get('access_expires_at')
        if access_expires_at:
            expires_dt = datetime.fromtimestamp(access_expires_at, tz=DEFAULT_TIMEZONE)
            time_until_expiry = expires_dt - datetime.now(DEFAULT_TIMEZONE)

            if time_until_expiry < timedelta(minutes=30):
                warnings.append(
                    {
                        'type': 'warning',
                        'account': account_name,
                        'message': f'Access Token 将在 {time_until_expiry.seconds // 60} 分钟后过期',
                    }
                )

    return warnings


# Quick action buttons
def render_quick_actions():
    """Render quick action buttons"""
    st.subheader("快速操作")

    # Display daemon status information
    daemon_reader = st.session_state.get('daemon_status_reader')
    if daemon_reader:
        summary = daemon_reader.get_daemon_summary()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="🔄 Daemon 狀態",
                value="運行中" if summary['is_running'] else "已停止",
                delta="正常" if summary['is_running'] else "異常",
            )

        with col2:
            st.metric(
                label="⏱️ 運行時間", value=summary['uptime'], delta=f"{summary['jobs_count']} 個任務"
            )

        with col3:
            st.metric(
                label="📊 執行統計",
                value=f"成功 {summary['recent_success_count']}",
                delta=f"失敗 {summary['recent_error_count']}",
            )

        # Show next job runs
        st.write("**即將執行的任務:**")
        next_runs = daemon_reader.get_next_job_runs()
        if next_runs:
            for job_run in next_runs[:3]:  # Show next 3 jobs
                time_until = job_run['next_run_datetime'] - datetime.now(DEFAULT_TIMEZONE)
                if time_until.total_seconds() > 0:
                    hours = int(time_until.total_seconds() // 3600)
                    minutes = int((time_until.total_seconds() % 3600) // 60)
                    time_str = f"{hours}小時{minutes}分鐘後"
                else:
                    time_str = "即將執行"
                st.info(f"🔄 {job_run['job_name']} - {time_str}")
        else:
            st.info("📝 目前沒有即將執行的任務")
    else:
        st.warning("⚠️ 無法連接到 Daemon 服務")

    # with col3:
    #     # Backup configuration button (separate row)
    #     if st.button("💾 备份配置", key="backup_config"):
    #         config_helper = st.session_state.get('config_helper')
    #         if config_helper:
    #             with st.spinner("正在备份配置..."):
    #                 success = config_helper.backup_config()
    #                 if success:
    #                     st.success("✅ 配置备份成功")
    #                 else:
    #                     st.error("❌ 配置备份失败")
