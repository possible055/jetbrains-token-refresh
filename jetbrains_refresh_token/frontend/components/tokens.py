from datetime import datetime, timedelta
from typing import Any, Dict, List

import streamlit as st

from jetbrains_refresh_token.constants import DEFAULT_TIMEZONE


def render():
    """Render the tokens monitoring page"""
    st.markdown('<h1 class="main-header">金钥监控</h1>', unsafe_allow_html=True)

    # Get configuration helper
    config_helper = st.session_state.get('config_helper')
    if not config_helper:
        st.error("配置助手未初始化")
        return

    # Auto-refresh toggle
    # render_auto_refresh_control()

    # Token overview section
    render_token_overview(config_helper)

    # Token details section
    render_token_details(config_helper)

    # # Token history section
    # render_token_history()


# def render_auto_refresh_control():
#     """Render auto-refresh control"""
#     st.subheader("🔄 自动刷新设定")

#     col1, col2, col3 = st.columns([2, 2, 1])

#     with col1:
#         auto_refresh = st.checkbox(
#             "启用自动刷新",
#             value=st.session_state.get('auto_refresh_enabled', True),
#             key='auto_refresh_toggle',
#         )
#         st.session_state.auto_refresh_enabled = auto_refresh

#     with col2:
#         if auto_refresh:
#             refresh_interval = st.slider(
#                 "刷新间隔（秒）",
#                 min_value=30,
#                 max_value=300,
#                 value=st.session_state.get('refresh_interval', 30),
#                 key='refresh_interval_slider',
#             )
#             st.session_state.refresh_interval = refresh_interval
#         else:
#             st.write("自动刷新已停用")

#     with col3:
#         if st.button("🔄 立即刷新", key="manual_refresh"):
#             st.rerun()

#     # Auto-refresh status display (background tasks handle actual refresh)
#     if auto_refresh:
#         refresh_placeholder = st.empty()
#         with refresh_placeholder:
#             # Check if background services are available
#             if (
#                 st.session_state.get('scheduler_service')
#                 and st.session_state.scheduler_service.is_running
#             ):
#                 st.success(
#                     f"🔄 自动刷新已启用 - 背景服务每 {st.session_state.get('refresh_interval', 30)} 秒检查更新"
#                 )
#             else:
#                 st.warning("⚠️ 背景服务未运行，自动刷新功能不可用")


def render_token_overview(config_helper):
    """Render token status overview"""
    st.subheader("📊 金钥状态概览")

    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚无帐号资料")
        return

    # Calculate statistics
    total_accounts = len(accounts)
    access_expired = sum(1 for acc in accounts if acc['access_token_expired'])

    # Create overview cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("总帐号数", total_accounts, help="系统中的总帐号数量")

    with col2:
        healthy_accounts = total_accounts - access_expired
        st.metric(
            "健康帐户",
            healthy_accounts,
            delta=f"{healthy_accounts}/{total_accounts}",
            delta_color="normal",
        )

    with col3:
        st.metric(
            "Access Token 过期",
            access_expired,
            delta=f"{access_expired}/{total_accounts}",
            delta_color="inverse",
        )

    # Token expiration timeline
    render_expiration_timeline(accounts)


def render_expiration_timeline(accounts: List[Dict[str, Any]]):
    """Render token expiration timeline"""
    st.subheader("⏰ 时间轴")

    now = datetime.now(DEFAULT_TIMEZONE)
    upcoming_expirations = []

    for account in accounts:
        # Check access token expiration
        if account['access_expires_at']:
            expires_dt = datetime.fromtimestamp(account['access_expires_at'], tz=DEFAULT_TIMEZONE)
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

    # Sort by expiration time
    upcoming_expirations.sort(key=lambda x: x['expires_at'])

    if not upcoming_expirations:
        st.info("📅 没有即将过期的金钥")
        return

    # Display timeline
    for exp in upcoming_expirations[:10]:  # Show only next 10 expirations
        urgency_color = {'critical': 'error', 'warning': 'warning', 'normal': 'info'}.get(
            exp['urgency'], 'info'
        )

        time_str = format_time_delta(exp['time_until'])

        getattr(st, urgency_color)(
            f"🕐 {exp['account']} - {exp['token_type']} 将在 {time_str} 后过期 "
            f"({exp['expires_at'].strftime('%Y-%m-%d %H:%M:%S')})"
        )


def render_token_details(config_helper):
    """Render detailed token information"""
    st.subheader("🔍 金钥详细资讯")

    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚无帐号资料")
        return

    # Account selection
    account_names = [acc['name'] for acc in accounts]
    selected_account = st.selectbox("选择帐号", account_names, key="token_detail_account_select")

    if not selected_account:
        return

    # Find selected account
    account = next((acc for acc in accounts if acc['name'] == selected_account), None)
    if not account:
        st.error("找不到选定的帐号")
        return

    # Display token details
    render_account_token_details(account, config_helper)


def render_account_token_details(account: Dict[str, Any], config_helper):
    """Render token details for specific account"""
    st.write(f"**帐号:** {account['name']}")

    # Display Access Token details
    render_access_token_details(account, config_helper)


def render_access_token_details(account: Dict[str, Any], config_helper):
    """Render access token details"""
    st.subheader("🔑 Access Token 详细资讯")

    # Token status
    status = "🔴 过期" if account['access_token_expired'] else "🟢 正常"
    st.write(f"**状态:** {status}")

    # Expiration time
    if account['access_expires_at']:
        expires_dt = datetime.fromtimestamp(account['access_expires_at'], tz=DEFAULT_TIMEZONE)
        st.write(f"**过期时间:** {expires_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # Time until expiration
        now = datetime.now(DEFAULT_TIMEZONE)
        time_until = expires_dt - now

        if time_until > timedelta(0):
            st.write(f"**剩余时间:** {format_time_delta(time_until)}")
        else:
            st.write("**剩余时间:** 已過期")
    else:
        st.write("**过期时间:** 未知")

    # Refresh button
    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("🔄 手動刷新", key=f"refresh_access_detail_{account['name']}"):
            # Direct execution (background tasks handled by daemon)
            with st.spinner("正在刷新 Access Token..."):
                success = config_helper.refresh_account_access_token(account['name'], forced=False)
                if success:
                    st.success("✅ Access Token 刷新成功")
                    st.rerun()
                else:
                    st.error("❌ Access Token 刷新失敗")

    with col2:
        if st.button("🔄 強制刷新", key=f"force_refresh_access_detail_{account['name']}"):
            # Direct execution (background tasks handled by daemon)
            with st.spinner("正在強制刷新 Access Token..."):
                success = config_helper.refresh_account_access_token(account['name'], forced=True)
                if success:
                    st.success("✅ Access Token 強制刷新成功")
                    st.rerun()
                else:
                    st.error("❌ Access Token 強制刷新失敗")


# def render_token_history():
#     """Render token refresh history"""
#     st.subheader("📋 Token 操作歷史")

#     # Get session logs from state manager
#     state_manager = st.session_state.get('state_manager')
#     if not state_manager:
#         st.info("📝 無歷史記錄")
#         return

#     session_id = st.session_state.get('session_id', '')
#     logs = state_manager.get_session_logs(session_id, limit=50)

#     if not logs:
#         st.info("📝 本次會話尚無操作記錄")
#         return

#     # Filter token-related logs
#     token_logs = [
#         log
#         for log in logs
#         if any(keyword in log[0].lower() for keyword in ['token', 'refresh', 'access', 'id'])
#     ]

#     if not token_logs:
#         st.info("📝 本次會話尚無 Token 相關操作記錄")
#         return

#     # Display logs in a table-like format
#     st.write("最近的 Token 操作:")

#     for action, details, timestamp in token_logs[:20]:  # Show last 20 token operations
#         # Parse timestamp and ensure it has timezone info
#         dt = datetime.fromisoformat(timestamp)
#         if dt.tzinfo is None:
#             dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
#         formatted_time = dt.strftime('%H:%M:%S')

#         with st.expander(f"🕐 {formatted_time} - {action}", expanded=False):
#             if details:
#                 st.write(details)
#             else:
#                 st.write("無詳細資訊")


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
    now = datetime.now(DEFAULT_TIMEZONE)
    next_refresh = now + timedelta(days=30)  # Default to 30 days from now

    # Check access token expiration
    if account['access_expires_at']:
        access_expires = datetime.fromtimestamp(account['access_expires_at'], tz=DEFAULT_TIMEZONE)
        # Refresh 5 minutes before expiration
        access_refresh_time = access_expires - timedelta(minutes=5)
        if access_refresh_time > now:
            next_refresh = min(next_refresh, access_refresh_time)

    return next_refresh
