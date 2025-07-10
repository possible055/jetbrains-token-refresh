"""
Tokens Page - Token monitoring and management for JetBrains Token Manager
Displays token status, expiration times, and provides manual refresh options
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import streamlit as st


def render():
    """Render the tokens monitoring page"""
    st.markdown('<h1 class="main-header">🔑 Token 監控</h1>', unsafe_allow_html=True)

    # Get configuration helper
    config_helper = st.session_state.get('config_helper')
    if not config_helper:
        st.error("配置助手未初始化")
        return

    # Auto-refresh toggle
    render_auto_refresh_control()

    # Token overview section
    render_token_overview(config_helper)

    # Token details section
    render_token_details(config_helper)

    # Token history section
    render_token_history()


def render_auto_refresh_control():
    """Render auto-refresh control"""
    st.subheader("🔄 自動刷新設定")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        auto_refresh = st.checkbox(
            "啟用自動刷新",
            value=st.session_state.get('auto_refresh_enabled', True),
            key='auto_refresh_toggle',
        )
        st.session_state.auto_refresh_enabled = auto_refresh

    with col2:
        if auto_refresh:
            refresh_interval = st.slider(
                "刷新間隔（秒）",
                min_value=10,
                max_value=300,
                value=st.session_state.get('refresh_interval', 30),
                key='refresh_interval_slider',
            )
            st.session_state.refresh_interval = refresh_interval
        else:
            st.write("自動刷新已停用")

    with col3:
        if st.button("🔄 立即刷新", key="manual_refresh"):
            st.rerun()

    # Auto-refresh logic (using placeholder instead of blocking sleep)
    if auto_refresh:
        refresh_placeholder = st.empty()
        with refresh_placeholder:
            st.info(f"🔄 自動刷新啟用 - 每 {st.session_state.get('refresh_interval', 30)} 秒更新")
        
        # Use session state to track last refresh time
        current_time = time.time()
        last_refresh_time = st.session_state.get('last_token_refresh', 0)
        
        if current_time - last_refresh_time >= st.session_state.get('refresh_interval', 30):
            st.session_state.last_token_refresh = current_time
            st.rerun()


def render_token_overview(config_helper):
    """Render token status overview"""
    st.subheader("📊 Token 狀態概覽")

    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚無帳戶資料")
        return

    # Calculate statistics
    total_accounts = len(accounts)
    access_expired = sum(1 for acc in accounts if acc['access_token_expired'])
    id_expired = sum(1 for acc in accounts if acc['id_token_expired'])

    # Create overview cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("總帳戶數", total_accounts, help="系統中的總帳戶數量")

    with col2:
        st.metric(
            "Access Token 過期",
            access_expired,
            delta=f"{access_expired}/{total_accounts}",
            delta_color="inverse",
        )

    with col3:
        st.metric(
            "ID Token 過期",
            id_expired,
            delta=f"{id_expired}/{total_accounts}",
            delta_color="inverse",
        )

    with col4:
        healthy_accounts = total_accounts - max(access_expired, id_expired)
        st.metric(
            "健康帳戶",
            healthy_accounts,
            delta=f"{healthy_accounts}/{total_accounts}",
            delta_color="normal",
        )

    # Token expiration timeline
    render_expiration_timeline(accounts)


def render_expiration_timeline(accounts: List[Dict[str, Any]]):
    """Render token expiration timeline"""
    st.subheader("⏰ Token 過期時間軸")

    now = datetime.now()
    upcoming_expirations = []

    for account in accounts:
        # Check access token expiration
        if account['access_expires_at']:
            expires_dt = datetime.fromtimestamp(account['access_expires_at'])
            time_until = expires_dt - now

            if time_until > timedelta(0):  # Future expiration
                upcoming_expirations.append(
                    {
                        'account': account['name'],
                        'token_type': 'Access Token',
                        'expires_at': expires_dt,
                        'time_until': time_until,
                        'urgency': get_urgency_level(time_until),
                    }
                )

        # Check ID token expiration
        if account['id_token_expires_at']:
            expires_dt = datetime.fromtimestamp(account['id_token_expires_at'])
            time_until = expires_dt - now

            if time_until > timedelta(0):  # Future expiration
                upcoming_expirations.append(
                    {
                        'account': account['name'],
                        'token_type': 'ID Token',
                        'expires_at': expires_dt,
                        'time_until': time_until,
                        'urgency': get_urgency_level(time_until),
                    }
                )

    # Sort by expiration time
    upcoming_expirations.sort(key=lambda x: x['expires_at'])

    if not upcoming_expirations:
        st.info("📅 沒有即將過期的 Token")
        return

    # Display timeline
    for exp in upcoming_expirations[:10]:  # Show only next 10 expirations
        urgency_color = {'critical': 'error', 'warning': 'warning', 'normal': 'info'}.get(
            exp['urgency'], 'info'
        )

        time_str = format_time_delta(exp['time_until'])

        getattr(st, urgency_color)(
            f"🕐 {exp['account']} - {exp['token_type']} 將在 {time_str} 後過期 "
            f"({exp['expires_at'].strftime('%Y-%m-%d %H:%M:%S')})"
        )


def render_token_details(config_helper):
    """Render detailed token information"""
    st.subheader("🔍 Token 詳細資訊")

    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚無帳戶資料")
        return

    # Account selection
    account_names = [acc['name'] for acc in accounts]
    selected_account = st.selectbox("選擇帳戶", account_names, key="token_detail_account_select")

    if not selected_account:
        return

    # Find selected account
    account = next((acc for acc in accounts if acc['name'] == selected_account), None)
    if not account:
        st.error("找不到選定的帳戶")
        return

    # Display token details
    render_account_token_details(account, config_helper)


def render_account_token_details(account: Dict[str, Any], config_helper):
    """Render token details for specific account"""
    st.write(f"**帳戶:** {account['name']}")

    # Create tabs for different token types
    tab1, tab2 = st.tabs(["🔑 Access Token", "🆔 ID Token"])

    with tab1:
        render_access_token_details(account, config_helper)

    with tab2:
        render_id_token_details(account, config_helper)


def render_access_token_details(account: Dict[str, Any], config_helper):
    """Render access token details"""
    st.subheader("🔑 Access Token 詳細資訊")

    # Token status
    status = "🔴 過期" if account['access_token_expired'] else "🟢 正常"
    st.write(f"**狀態:** {status}")

    # Expiration time
    if account['access_expires_at']:
        expires_dt = datetime.fromtimestamp(account['access_expires_at'])
        st.write(f"**過期時間:** {expires_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # Time until expiration
        now = datetime.now()
        time_until = expires_dt - now

        if time_until > timedelta(0):
            st.write(f"**剩餘時間:** {format_time_delta(time_until)}")
        else:
            st.write("**剩餘時間:** 已過期")
    else:
        st.write("**過期時間:** 未知")

    # Refresh button
    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("🔄 手動刷新", key=f"refresh_access_detail_{account['name']}"):
            with st.spinner("正在刷新 Access Token..."):
                success = config_helper.refresh_account_access_token(account['name'], forced=True)
                if success:
                    st.success("✅ Access Token 刷新成功")
                    st.rerun()
                else:
                    st.error("❌ Access Token 刷新失敗")

    with col2:
        if st.button("🔄 強制刷新", key=f"force_refresh_access_detail_{account['name']}"):
            with st.spinner("正在強制刷新 Access Token..."):
                success = config_helper.refresh_account_access_token(account['name'], forced=True)
                if success:
                    st.success("✅ Access Token 強制刷新成功")
                    st.rerun()
                else:
                    st.error("❌ Access Token 強制刷新失敗")


def render_id_token_details(account: Dict[str, Any], config_helper):
    """Render ID token details"""
    st.subheader("🆔 ID Token 詳細資訊")

    # Token status
    status = "🔴 過期" if account['id_token_expired'] else "🟢 正常"
    st.write(f"**狀態:** {status}")

    # Expiration time
    if account['id_token_expires_at']:
        expires_dt = datetime.fromtimestamp(account['id_token_expires_at'])
        st.write(f"**過期時間:** {expires_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # Time until expiration
        now = datetime.now()
        time_until = expires_dt - now

        if time_until > timedelta(0):
            st.write(f"**剩餘時間:** {format_time_delta(time_until)}")
        else:
            st.write("**剩餘時間:** 已過期")
    else:
        st.write("**過期時間:** 未知")

    # Refresh button
    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("🔄 手動刷新", key=f"refresh_id_detail_{account['name']}"):
            with st.spinner("正在刷新 ID Token..."):
                success = config_helper.refresh_account_id_token(account['name'], forced=True)
                if success:
                    st.success("✅ ID Token 刷新成功")
                    st.rerun()
                else:
                    st.error("❌ ID Token 刷新失敗")

    with col2:
        if st.button("🔄 強制刷新", key=f"force_refresh_id_detail_{account['name']}"):
            with st.spinner("正在強制刷新 ID Token..."):
                success = config_helper.refresh_account_id_token(account['name'], forced=True)
                if success:
                    st.success("✅ ID Token 強制刷新成功")
                    st.rerun()
                else:
                    st.error("❌ ID Token 強制刷新失敗")


def render_token_history():
    """Render token refresh history"""
    st.subheader("📋 Token 操作歷史")

    # Get session logs from state manager
    state_manager = st.session_state.get('state_manager')
    if not state_manager:
        st.info("📝 無歷史記錄")
        return

    session_id = st.session_state.get('session_id', '')
    logs = state_manager.get_session_logs(session_id, limit=50)

    if not logs:
        st.info("📝 本次會話尚無操作記錄")
        return

    # Filter token-related logs
    token_logs = [
        log
        for log in logs
        if any(keyword in log[0].lower() for keyword in ['token', 'refresh', 'access', 'id'])
    ]

    if not token_logs:
        st.info("📝 本次會話尚無 Token 相關操作記錄")
        return

    # Display logs in a table-like format
    st.write("最近的 Token 操作:")

    for i, (action, details, timestamp) in enumerate(
        token_logs[:20]
    ):  # Show last 20 token operations
        formatted_time = datetime.fromisoformat(timestamp).strftime('%H:%M:%S')

        with st.expander(f"🕐 {formatted_time} - {action}", expanded=False):
            if details:
                st.write(details)
            else:
                st.write("無詳細資訊")


def get_urgency_level(time_until: timedelta) -> str:
    """Get urgency level based on time until expiration"""
    if time_until < timedelta(hours=1):
        return 'critical'
    elif time_until < timedelta(days=1):
        return 'warning'
    else:
        return 'normal'


def format_time_delta(td: timedelta) -> str:
    """Format timedelta to human-readable string"""
    total_seconds = int(td.total_seconds())

    if total_seconds < 0:
        return "已過期"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if days > 0:
        return f"{days}天 {hours}小時 {minutes}分鐘"
    elif hours > 0:
        return f"{hours}小時 {minutes}分鐘"
    elif minutes > 0:
        return f"{minutes}分鐘 {seconds}秒"
    else:
        return f"{seconds}秒"


# Additional utility functions for token monitoring
def get_token_health_score(accounts: List[Dict[str, Any]]) -> float:
    """Calculate overall token health score"""
    if not accounts:
        return 0.0

    healthy_count = 0
    for account in accounts:
        if not account['access_token_expired'] and not account['id_token_expired']:
            healthy_count += 1

    return (healthy_count / len(accounts)) * 100


def predict_next_refresh_time(account: Dict[str, Any]) -> datetime:
    """Predict when the next token refresh will be needed"""
    now = datetime.now()
    next_refresh = now + timedelta(days=30)  # Default to 30 days from now

    # Check access token expiration
    if account['access_expires_at']:
        access_expires = datetime.fromtimestamp(account['access_expires_at'])
        # Refresh 5 minutes before expiration
        access_refresh_time = access_expires - timedelta(minutes=5)
        if access_refresh_time > now:
            next_refresh = min(next_refresh, access_refresh_time)

    # Check ID token expiration
    if account['id_token_expires_at']:
        id_expires = datetime.fromtimestamp(account['id_token_expires_at'])
        # Refresh 5 minutes before expiration
        id_refresh_time = id_expires - timedelta(minutes=5)
        if id_refresh_time > now:
            next_refresh = min(next_refresh, id_refresh_time)

    return next_refresh