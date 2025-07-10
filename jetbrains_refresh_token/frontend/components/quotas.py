import json
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st


def render():
    """Render the quotas monitoring page"""
    st.markdown('<h1 class="main-header">📊 配額管理</h1>', unsafe_allow_html=True)

    # Get configuration helper
    config_helper = st.session_state.get('config_helper')
    if not config_helper:
        st.error("配置助手未初始化")
        return

    # Quota overview section
    render_quota_overview(config_helper)

    # Quota details section
    render_quota_details(config_helper)

    # Quota alerts section
    render_quota_alerts(config_helper)

    # Quota management section
    render_quota_management(config_helper)


def render_quota_overview(config_helper):
    """Render quota overview section"""
    st.subheader("📈 配額概覽")

    accounts = config_helper.get_accounts()
    quota_accounts = [acc for acc in accounts if acc.get('quota_info')]

    if not quota_accounts:
        st.warning("⚠️ 沒有配額資訊，請點擊「檢查所有配額」按鈕獲取資訊")

        if st.button("📊 檢查所有配額", key="check_all_quotas_overview"):
            with st.spinner("正在檢查所有帳戶的配額..."):
                success = config_helper.check_all_quotas()
                if success:
                    st.success("✅ 所有配額檢查完成")
                    st.rerun()
                else:
                    st.error("❌ 配額檢查失敗")
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

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("總帳戶數", total_accounts, help="擁有配額資訊的帳戶總數")

    with col2:
        st.metric(
            "🟢 正常",
            normal_accounts,
            delta=f"{(normal_accounts/total_accounts*100):.1f}%" if total_accounts > 0 else "0%",
        )

    with col3:
        st.metric(
            "🟡 警告",
            warning_accounts,
            delta=f"{(warning_accounts/total_accounts*100):.1f}%" if total_accounts > 0 else "0%",
            delta_color="off",
        )

    with col4:
        st.metric(
            "🔴 危險",
            critical_accounts,
            delta=f"{(critical_accounts/total_accounts*100):.1f}%" if total_accounts > 0 else "0%",
            delta_color="inverse",
        )

    # Quota usage chart
    render_quota_usage_chart(quota_accounts)


def render_quota_usage_chart(quota_accounts: List[Dict[str, Any]]):
    """Render quota usage visualization"""
    st.subheader("📊 配額使用圖表")

    # Create a simple bar chart representation
    chart_data = []
    for account in quota_accounts:
        quota_info = account.get('quota_info', {})
        usage = quota_info.get('usage_percentage', 0)

        chart_data.append(
            {
                'account': account['name'],
                'usage': usage,
                'status': quota_info.get('status', 'unknown'),
            }
        )

    # Sort by usage percentage
    chart_data.sort(key=lambda x: x['usage'], reverse=True)

    # Display as progress bars
    for data in chart_data:
        status_color = {'critical': '🔴', 'warning': '🟡', 'normal': '🟢', 'unknown': '⚪'}.get(
            data['status'], '⚪'
        )

        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"{status_color} {data['account']}")
            st.progress(data['usage'] / 100)

        with col2:
            st.write(f"{data['usage']:.1f}%")


def render_quota_details(config_helper):
    """Render detailed quota information"""
    st.subheader("🔍 配額詳細資訊")

    accounts = config_helper.get_accounts()
    quota_accounts = [acc for acc in accounts if acc.get('quota_info')]

    if not quota_accounts:
        st.info("📝 沒有配額資訊")
        return

    # Account selection
    account_names = [acc['name'] for acc in quota_accounts]
    selected_account = st.selectbox("選擇帳戶", account_names, key="quota_detail_account_select")

    if not selected_account:
        return

    # Find selected account
    account = next((acc for acc in quota_accounts if acc['name'] == selected_account), None)
    if not account:
        st.error("找不到選定的帳戶")
        return

    # Display quota details
    render_account_quota_details(account, config_helper)


def render_account_quota_details(account: Dict[str, Any], config_helper):
    """Render quota details for specific account"""
    st.write(f"**帳戶:** {account['name']}")

    quota_info = account.get('quota_info', {})

    if not quota_info:
        st.warning("此帳戶沒有配額資訊")
        return

    # Create columns for quota information
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 配額統計")

        usage_percentage = quota_info.get('usage_percentage', 0)
        remaining_amount = quota_info.get('remaining_amount', 'N/A')
        status = quota_info.get('status', 'unknown')

        # Status indicator
        status_colors = {'critical': '🔴', 'warning': '🟡', 'normal': '🟢', 'unknown': '⚪'}

        st.markdown(
            f"""
        <div class="status-card">
            <p><strong>狀態:</strong> {status_colors.get(status, '⚪')} {status}</p>
            <p><strong>使用率:</strong> {usage_percentage:.1f}%</p>
            <p><strong>剩餘額度:</strong> {remaining_amount}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Usage progress bar
        st.progress(usage_percentage / 100)

        # Usage level warnings
        if usage_percentage > 90:
            st.error("🚨 配額使用率超過 90%，請注意使用量")
        elif usage_percentage > 80:
            st.warning("⚠️ 配額使用率超過 80%，建議注意使用量")
        else:
            st.success("✅ 配額使用率正常")

    with col2:
        st.subheader("🔄 配額操作")

        # Refresh quota button
        if st.button("🔄 重新檢查配額", key=f"refresh_quota_{account['name']}"):
            with st.spinner("正在重新檢查配額..."):
                success = config_helper.check_all_quotas()
                if success:
                    st.success("✅ 配額檢查完成")
                    st.rerun()
                else:
                    st.error("❌ 配額檢查失敗")

        # Quota history (if available)
        st.subheader("📋 配額歷史")
        st.info("配額歷史功能開發中...")


def render_quota_alerts(config_helper):
    """Render quota alerts and warnings"""
    st.subheader("⚠️ 配額警告")

    accounts = config_helper.get_accounts()
    quota_accounts = [acc for acc in accounts if acc.get('quota_info')]

    alerts = generate_quota_alerts(quota_accounts)

    if not alerts:
        st.success("✅ 沒有配額警告")
        return

    # Display alerts
    for alert in alerts:
        alert_type = alert['type']
        message = alert['message']
        account = alert['account']

        if alert_type == 'critical':
            st.error(f"🚨 **{account}**: {message}")
        elif alert_type == 'warning':
            st.warning(f"⚠️ **{account}**: {message}")


def render_quota_management(config_helper):
    """Render quota management section"""
    st.subheader("⚙️ 配額管理")

    # Batch operations
    st.write("**批次操作:**")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 檢查所有配額", key="batch_check_quotas"):
            with st.spinner("正在檢查所有帳戶的配額..."):
                success = config_helper.check_all_quotas()
                if success:
                    st.success("✅ 所有配額檢查完成")
                    st.rerun()
                else:
                    st.error("❌ 部分配額檢查失敗")

    with col2:
        if st.button("📥 導出配額報告", key="export_quota_report"):
            quota_report = generate_quota_report(config_helper)
            if quota_report:
                st.download_button(
                    label="📥 下載配額報告",
                    data=quota_report,
                    file_name=f"quota_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
            else:
                st.error("❌ 無法生成配額報告")

    with col3:
        if st.button("🔄 重置配額快取", key="reset_quota_cache"):
            # Clear quota cache (if implemented)
            st.info("配額快取重置功能開發中...")

    # Quota settings
    st.write("**配額設定:**")

    with st.expander("⚙️ 配額警告設定", expanded=False):
        warning_threshold = st.slider(
            "警告閾值 (%)",
            min_value=50,
            max_value=95,
            value=80,
            help="當配額使用率超過此值時顯示警告",
        )

        critical_threshold = st.slider(
            "危險閾值 (%)",
            min_value=85,
            max_value=100,
            value=90,
            help="當配額使用率超過此值時顯示危險警告",
        )

        if st.button("💾 儲存設定", key="save_quota_settings"):
            # Save settings to session state
            st.session_state.quota_warning_threshold = warning_threshold
            st.session_state.quota_critical_threshold = critical_threshold
            st.success("✅ 配額設定已儲存")


def generate_quota_alerts(quota_accounts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate quota alerts based on usage"""
    alerts = []

    warning_threshold = st.session_state.get('quota_warning_threshold', 80)
    critical_threshold = st.session_state.get('quota_critical_threshold', 90)

    for account in quota_accounts:
        quota_info = account.get('quota_info', {})
        usage = quota_info.get('usage_percentage', 0)
        account_name = account['name']

        if usage >= critical_threshold:
            alerts.append(
                {
                    'type': 'critical',
                    'account': account_name,
                    'message': f'配額使用率過高 ({usage:.1f}%)，請立即注意使用量',
                }
            )
        elif usage >= warning_threshold:
            alerts.append(
                {
                    'type': 'warning',
                    'account': account_name,
                    'message': f'配額使用率偏高 ({usage:.1f}%)，建議注意使用量',
                }
            )

    return alerts


def generate_quota_report(config_helper) -> str:
    """Generate quota usage report"""
    try:
        accounts = config_helper.get_accounts()
        quota_accounts = [acc for acc in accounts if acc.get('quota_info')]

        report = {
            'generated_at': datetime.now().isoformat(),
            'total_accounts': len(quota_accounts),
            'accounts': [],
        }

        for account in quota_accounts:
            quota_info = account.get('quota_info', {})

            account_report = {
                'name': account['name'],
                'license_id': account['license_id'],
                'quota_info': {
                    'usage_percentage': quota_info.get('usage_percentage', 0),
                    'remaining_amount': quota_info.get('remaining_amount', 'N/A'),
                    'status': quota_info.get('status', 'unknown'),
                },
                'token_status': {
                    'access_token_expired': account['access_token_expired'],
                    'id_token_expired': account['id_token_expired'],
                },
            }

            report['accounts'].append(account_report)

        return json.dumps(report, indent=2, ensure_ascii=False)

    except Exception as e:
        st.error(f"生成配額報告失敗: {str(e)}")
        return ""


def get_quota_trend(account_name: str) -> Dict[str, Any]:
    """Get quota usage trend for account (placeholder)"""
    # This would be implemented with historical data
    return {'trend': 'stable', 'change_percentage': 0.0, 'prediction': 'normal'}


def calculate_quota_efficiency(quota_accounts: List[Dict[str, Any]]) -> float:
    """Calculate overall quota efficiency"""
    if not quota_accounts:
        return 0.0

    total_usage = sum(acc['quota_info'].get('usage_percentage', 0) for acc in quota_accounts)
    average_usage = total_usage / len(quota_accounts)

    # Efficiency is inversely related to usage (more headroom = more efficient)
    efficiency = max(0, 100 - average_usage)
    return efficiency


def render_quota_analytics():
    """Render quota analytics section (advanced feature)"""
    st.subheader("📈 配額分析")

    # This would include:
    # - Usage trends over time
    # - Prediction models
    # - Optimization recommendations
    # - Cost analysis

    st.info("📊 配額分析功能開發中...")

    # Placeholder for future analytics features
    st.write("未來功能預覽:")
    st.write("- 使用趨勢分析")
    st.write("- 配額預測模型")
    st.write("- 最佳化建議")
    st.write("- 成本分析")
