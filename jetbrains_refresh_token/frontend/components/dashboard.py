"""
Dashboard Page - Main overview page for JetBrains Token Manager
Displays system status, warnings, and quick statistics
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import streamlit as st


def render():
    """Render the dashboard page"""
    st.markdown('<h1 class="main-header">🏠 主控台</h1>', unsafe_allow_html=True)

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

    # Recent operations section
    render_recent_operations()

    # Update last refresh time
    st.session_state.last_refresh = datetime.now()


def render_system_overview(config_helper):
    """Render system overview cards"""
    st.subheader("🔍 系統概覽")

    # Get system info
    system_info = config_helper.get_system_info()
    accounts = config_helper.get_accounts()

    # Create columns for overview cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
        <div class="status-card">
            <h3>📁 配置檔案</h3>
            <p><strong>狀態:</strong> {'✅ 正常' if system_info.get('config_exists', False) else '❌ 不存在'}</p>
            <p><strong>大小:</strong> {system_info.get('config_size', 0)} bytes</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="status-card">
            <h3>👥 帳戶總數</h3>
            <p><strong>總計:</strong> {len(accounts)}</p>
            <p><strong>活躍:</strong> {sum(1 for acc in accounts if acc['status'] == '🟢 正常')}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        expired_tokens = sum(1 for acc in accounts if acc['access_token_expired'])
        st.markdown(
            f"""
        <div class="{'warning-card' if expired_tokens > 0 else 'status-card'}">
            <h3>🔑 Token 狀態</h3>
            <p><strong>過期:</strong> {expired_tokens}</p>
            <p><strong>正常:</strong> {len(accounts) - expired_tokens}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        last_refresh = st.session_state.get('last_refresh')
        refresh_time = last_refresh.strftime('%H:%M:%S') if last_refresh else '未知'
        st.markdown(
            f"""
        <div class="status-card">
            <h3>🔄 最後更新</h3>
            <p><strong>時間:</strong> {refresh_time}</p>
            <p><strong>狀態:</strong> {'🟢 已同步' if last_refresh else '⚪ 未同步'}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_warnings_section(config_helper):
    """Render warnings and alerts section"""
    st.subheader("⚠️ 警告與提醒")

    accounts = config_helper.get_accounts()
    warnings = generate_warnings(accounts)

    if not warnings:
        st.success("✅ 沒有警告訊息，所有系統運作正常")
    else:
        for warning in warnings:
            warning_type = warning['type']
            message = warning['message']
            account = warning.get('account', '')

            if warning_type == 'error':
                st.markdown(
                    f"""
                <div class="error-card">
                    <strong>❌ 錯誤</strong> - {account}<br>
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
    st.subheader("📊 統計資訊")

    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚無帳戶資料")
        return

    # Create tabs for different statistics
    tab1, tab2, tab3 = st.tabs(["Token 狀態", "配額使用", "帳戶活動"])

    with tab1:
        render_token_statistics(accounts)

    with tab2:
        render_quota_statistics(accounts)

    with tab3:
        render_activity_statistics(accounts)


def render_token_statistics(accounts: List[Dict[str, Any]]):
    """Render token status statistics"""
    col1, col2 = st.columns(2)

    with col1:
        # ID token statistics
        id_expired = sum(1 for acc in accounts if acc['id_token_expired'])
        id_valid = len(accounts) - id_expired

        st.write("**ID Token 狀態**")
        st.write(f"🟢 有效: {id_valid}")
        st.write(f"🔴 過期: {id_expired}")

        if len(accounts) > 0:
            valid_percentage = (id_valid / len(accounts)) * 100
            st.progress(valid_percentage / 100)
            st.write(f"有效率: {valid_percentage:.1f}%")

    with col2:
        # Access token statistics
        access_expired = sum(1 for acc in accounts if acc['access_token_expired'])
        access_valid = len(accounts) - access_expired

        st.write("**Access Token 狀態**")
        st.write(f"🟢 有效: {access_valid}")
        st.write(f"🔴 過期: {access_expired}")

        # Simple progress bar simulation
        if len(accounts) > 0:
            valid_percentage = (access_valid / len(accounts)) * 100
            st.progress(valid_percentage / 100)
            st.write(f"有效率: {valid_percentage:.1f}%")


def render_quota_statistics(accounts: List[Dict[str, Any]]):
    """Render quota usage statistics"""
    quota_accounts = [acc for acc in accounts if acc.get('quota_info')]

    if not quota_accounts:
        st.info("📊 尚無配額資訊")
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
        st.metric("🔴 危險", critical_accounts)

    # Quota usage details
    st.write("**配額使用詳情**")
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
    st.write("**帳戶活動統計**")

    # Show account creation times
    current_time = datetime.now()
    for account in accounts:
        created_time = account.get('created_time')
        if created_time:
            created_dt = datetime.fromtimestamp(created_time)
            days_old = (current_time - created_dt).days
            st.write(
                f"👤 {account['name']}: 建立於 {created_dt.strftime('%Y-%m-%d')} ({days_old} 天前)"
            )
        else:
            st.write(f"👤 {account['name']}: 建立時間未知")


def render_recent_operations():
    """Render recent operations section"""
    st.subheader("📋 最近操作")

    # Get session logs from state manager
    state_manager = st.session_state.get('state_manager')
    if not state_manager:
        st.info("📝 無操作記錄")
        return

    session_id = st.session_state.get('session_id', '')
    logs = state_manager.get_session_logs(session_id, limit=10)

    if not logs:
        st.info("📝 本次會話尚無操作記錄")
        return

    for action, details, timestamp in logs:
        formatted_time = datetime.fromisoformat(timestamp).strftime('%H:%M:%S')
        st.write(f"🕐 {formatted_time} - {action}")
        if details:
            st.write(f"   └─ {details}")


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
                    'message': 'Access Token 已過期，需要立即刷新',
                }
            )

        if account['id_token_expired']:
            warnings.append(
                {
                    'type': 'error',
                    'account': account_name,
                    'message': 'ID Token 已過期，需要立即刷新',
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
                    'message': f'配額使用率過高 ({quota_info.get("usage_percentage", 0):.1f}%)',
                }
            )
        elif quota_status == 'warning':
            warnings.append(
                {
                    'type': 'warning',
                    'account': account_name,
                    'message': f'配額使用率偏高 ({quota_info.get("usage_percentage", 0):.1f}%)',
                }
            )

        # Check for token expiration in near future
        access_expires_at = account.get('access_expires_at')
        if access_expires_at:
            expires_dt = datetime.fromtimestamp(access_expires_at)
            time_until_expiry = expires_dt - datetime.now()

            if time_until_expiry < timedelta(minutes=30):
                warnings.append(
                    {
                        'type': 'warning',
                        'account': account_name,
                        'message': f'Access Token 將在 {time_until_expiry.seconds // 60} 分鐘後過期',
                    }
                )

    return warnings


# Quick action buttons
def render_quick_actions():
    """Render quick action buttons"""
    st.subheader("⚡ 快速操作")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 刷新所有 Access Token", key="refresh_all_access"):
            config_helper = st.session_state.get('config_helper')
            if config_helper:
                with st.spinner("正在刷新 Access Token..."):
                    success = config_helper.refresh_all_access_tokens()
                    if success:
                        st.success("✅ 所有 Access Token 刷新成功")
                        st.session_state.last_refresh = datetime.now()
                    else:
                        st.error("❌ 部分 Access Token 刷新失敗")

    with col2:
        if st.button("🔄 刷新所有 ID Token", key="refresh_all_id"):
            config_helper = st.session_state.get('config_helper')
            if config_helper:
                with st.spinner("正在刷新 ID Token..."):
                    success = config_helper.refresh_all_id_tokens()
                    if success:
                        st.success("✅ 所有 ID Token 刷新成功")
                        st.session_state.last_refresh = datetime.now()
                    else:
                        st.error("❌ 部分 ID Token 刷新失敗")

    with col3:
        if st.button("📊 檢查所有配額", key="check_all_quotas"):
            config_helper = st.session_state.get('config_helper')
            if config_helper:
                with st.spinner("正在檢查配額..."):
                    success = config_helper.check_all_quotas()
                    if success:
                        st.success("✅ 所有配額檢查完成")
                        st.session_state.last_refresh = datetime.now()
                    else:
                        st.error("❌ 部分配額檢查失敗")

    with col4:
        if st.button("💾 備份配置", key="backup_config"):
            config_helper = st.session_state.get('config_helper')
            if config_helper:
                with st.spinner("正在備份配置..."):
                    success = config_helper.backup_config()
                    if success:
                        st.success("✅ 配置備份成功")
                    else:
                        st.error("❌ 配置備份失敗")
