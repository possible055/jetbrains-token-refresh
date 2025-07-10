from datetime import datetime
from typing import Any, Dict, List

import streamlit as st


def render():
    """Render the accounts management page"""
    st.markdown('<h1 class="main-header">👤 帳戶管理</h1>', unsafe_allow_html=True)

    # Get configuration helper
    config_helper = st.session_state.get('config_helper')
    if not config_helper:
        st.error("配置助手未初始化")
        return

    # Create tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📋 帳戶列表", "➕ 新增帳戶", "⚙️ 批次操作"])

    with tab1:
        render_accounts_list(config_helper)

    with tab2:
        render_add_account(config_helper)

    with tab3:
        render_batch_operations(config_helper)


def render_accounts_list(config_helper):
    """Render the accounts list with management options"""
    st.subheader("📋 帳戶列表")

    # Get accounts
    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚無帳戶資料，請先新增帳戶")
        return

    # Search and filter options
    col1, col2 = st.columns([3, 1])

    with col1:
        search_term = st.text_input("🔍 搜尋帳戶", placeholder="輸入帳戶名稱進行搜尋")

    with col2:
        status_filter = st.selectbox("篩選狀態", ["全部", "🟢 正常", "🟡 警告", "🔴 錯誤"])

    # Filter accounts
    filtered_accounts = filter_accounts(accounts, search_term, status_filter)

    if not filtered_accounts:
        st.warning("🔍 沒有找到符合條件的帳戶")
        return

    # Display accounts
    st.write(f"共 {len(filtered_accounts)} 個帳戶")

    for account in filtered_accounts:
        render_account_card(account, config_helper)


def render_account_card(account: Dict[str, Any], config_helper):
    """Render individual account card"""
    with st.expander(f"{account['status']} {account['name']}", expanded=False):
        col1, col2 = st.columns([2, 1])

        with col1:
            # Account information
            st.write(f"**帳戶名稱:** {account['name']}")
            st.write(f"**License ID:** {account['license_id']}")
            st.write(f"**狀態:** {account['status']}")

            # Token status
            st.write("**Token 狀態:**")
            access_status = "🔴 過期" if account['access_token_expired'] else "🟢 正常"

            st.write(f"- Access Token: {access_status}")

            # Expiration times
            if account['access_expires_at']:
                expires_dt = datetime.fromtimestamp(account['access_expires_at'])
                st.write(f"- Access Token 過期時間: {expires_dt.strftime('%Y-%m-%d %H:%M:%S')}")

            # Quota information
            quota_info = account.get('quota_info', {})
            if quota_info:
                st.write("**配額資訊:**")
                usage = quota_info.get('usage_percentage', 0)
                remaining = quota_info.get('remaining_amount', 'N/A')
                status = quota_info.get('status', 'unknown')

                st.write(f"- 使用率: {usage:.1f}%")
                st.write(f"- 剩餘額度: {remaining}")
                st.write(f"- 配額狀態: {status}")

            # Creation time
            if account.get('created_time'):
                created_dt = datetime.fromtimestamp(account['created_time'])
                st.write(f"**建立時間:** {created_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        with col2:
            # Action buttons
            st.write("**操作:**")

            if st.button("🔄 刷新 Access Token", key=f"refresh_access_{account['name']}"):
                with st.spinner("正在刷新 Access Token..."):
                    success = config_helper.refresh_account_access_token(account['name'])
                    if success:
                        st.success("✅ Access Token 刷新成功")
                        st.rerun()
                    else:
                        st.error("❌ Access Token 刷新失敗")

            if st.button("📊 檢查配額", key=f"check_quota_{account['name']}"):
                with st.spinner("正在檢查配額..."):
                    success = config_helper.check_all_quotas()
                    if success:
                        st.success("✅ 配額檢查完成")
                        st.rerun()
                    else:
                        st.error("❌ 配額檢查失敗")

            if st.button("✏️ 編輯", key=f"edit_{account['name']}"):
                st.session_state.edit_account = account['name']
                st.rerun()

            if st.button("🗑️ 刪除", key=f"delete_{account['name']}"):
                st.session_state.delete_account = account['name']
                st.rerun()

    # Handle edit account
    if st.session_state.get('edit_account') == account['name']:
        render_edit_account_modal(account, config_helper)

    # Handle delete account
    if st.session_state.get('delete_account') == account['name']:
        render_delete_account_modal(account, config_helper)


def render_edit_account_modal(account: Dict[str, Any], config_helper):
    """Render edit account modal"""
    st.subheader(f"✏️ 編輯帳戶: {account['name']}")

    with st.form(f"edit_account_{account['name']}"):
        # Get current config to pre-fill form
        config = config_helper.get_config()
        account_data = config.get('accounts', {}).get(account['name'], {})

        license_id = st.text_input("License ID", value=account_data.get('license_id', ''))
        refresh_token = st.text_input(
            "Refresh Token", value=account_data.get('refresh_token', ''), type='password'
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("💾 儲存"):
                if license_id and refresh_token:
                    success = config_helper.update_account(
                        account['name'],
                        license_id=license_id,
                        refresh_token=refresh_token,
                    )
                    if success:
                        st.success("✅ 帳戶更新成功")
                        st.session_state.edit_account = None
                        st.rerun()
                    else:
                        st.error("❌ 帳戶更新失敗")
                else:
                    st.error("❌ 請填寫所有必填欄位")

        with col2:
            if st.form_submit_button("❌ 取消"):
                st.session_state.edit_account = None
                st.rerun()


def render_delete_account_modal(account: Dict[str, Any], config_helper):
    """Render delete account confirmation modal"""
    st.subheader(f"🗑️ 刪除帳戶: {account['name']}")

    st.warning(f"⚠️ 您確定要刪除帳戶 '{account['name']}' 嗎？此操作無法復原。")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ 確定刪除", key=f"confirm_delete_{account['name']}"):
            success = config_helper.delete_account(account['name'])
            if success:
                st.success("✅ 帳戶刪除成功")
                st.session_state.delete_account = None
                st.rerun()
            else:
                st.error("❌ 帳戶刪除失敗")

    with col2:
        if st.button("❌ 取消", key=f"cancel_delete_{account['name']}"):
            st.session_state.delete_account = None
            st.rerun()


def render_add_account(config_helper):
    """Render add account form"""
    st.subheader("➕ 新增帳戶")

    with st.form("add_account"):
        st.write("請填寫以下資訊來新增帳戶：")

        account_name = st.text_input("帳戶名稱 *", placeholder="輸入帳戶名稱")
        license_id = st.text_input("License ID *", placeholder="輸入 JetBrains License ID")
        refresh_token = st.text_input(
            "Refresh Token *", type="password", placeholder="輸入 Refresh Token"
        )

        st.markdown("*為必填欄位")

        if st.form_submit_button("➕ 新增帳戶"):
            if all([account_name, license_id, refresh_token]):
                # Check if account already exists
                existing_accounts = config_helper.get_accounts()
                if any(acc['name'] == account_name for acc in existing_accounts):
                    st.error("❌ 帳戶名稱已存在，請使用其他名稱")
                else:
                    success = config_helper.add_account(account_name, refresh_token, license_id)
                    if success:
                        st.success("✅ 帳戶新增成功")
                        st.rerun()
                    else:
                        st.error("❌ 帳戶新增失敗")
            else:
                st.error("❌ 請填寫所有必填欄位")

    # Add account form help
    with st.expander("❓ 如何獲取所需資訊"):
        st.write(
            """
        **License ID**: 您的 JetBrains 授權 ID
                
        **Refresh Token**: 用於自動刷新 Token 的 Refresh Token
        
        **注意**: 請確保所有 Token 都是有效的，否則帳戶將無法正常工作。
        """
        )


def render_batch_operations(config_helper):
    """Render batch operations section"""
    st.subheader("⚙️ 批次操作")

    accounts = config_helper.get_accounts()

    if not accounts:
        st.info("📝 尚無帳戶資料")
        return

    # Account selection
    st.write("**選擇要操作的帳戶:**")

    select_all = st.checkbox("全選", key="select_all_accounts")

    if select_all:
        selected_accounts = [acc['name'] for acc in accounts]
    else:
        selected_accounts = []
        for account in accounts:
            if st.checkbox(
                f"{account['status']} {account['name']}", key=f"select_{account['name']}"
            ):
                selected_accounts.append(account['name'])

    if not selected_accounts:
        st.info("📝 請選擇要操作的帳戶")
        return

    st.write(f"已選擇 {len(selected_accounts)} 個帳戶")

    # Batch operations
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 批次刷新 Access Token", key="batch_refresh_access"):
            with st.spinner("正在批次刷新 Access Token..."):
                success_count = 0
                for account_name in selected_accounts:
                    if config_helper.refresh_account_access_token(account_name):
                        success_count += 1

                if success_count == len(selected_accounts):
                    st.success(f"✅ 所有 {len(selected_accounts)} 個帳戶的 Access Token 刷新成功")
                else:
                    st.warning(
                        f"⚠️ {success_count}/{len(selected_accounts)} 個帳戶的 Access Token 刷新成功"
                    )
                st.rerun()

    with col2:
        if st.button("📊 批次檢查配額", key="batch_check_quota"):
            with st.spinner("正在批次檢查配額..."):
                success = config_helper.check_all_quotas()
                if success:
                    st.success("✅ 所有帳戶的配額檢查完成")
                else:
                    st.error("❌ 部分帳戶的配額檢查失敗")
                st.rerun()

    # Batch delete warning
    st.markdown("---")
    st.write("**⚠️ 危險操作:**")

    if st.button("🗑️ 批次刪除選中的帳戶", key="batch_delete"):
        st.session_state.batch_delete_accounts = selected_accounts
        st.rerun()

    # Batch delete confirmation
    if st.session_state.get('batch_delete_accounts'):
        st.error(f"⚠️ 您確定要刪除以下 {len(st.session_state.batch_delete_accounts)} 個帳戶嗎？")
        for account_name in st.session_state.batch_delete_accounts:
            st.write(f"- {account_name}")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ 確定刪除", key="confirm_batch_delete"):
                success_count = 0
                for account_name in st.session_state.batch_delete_accounts:
                    if config_helper.delete_account(account_name):
                        success_count += 1

                if success_count == len(st.session_state.batch_delete_accounts):
                    st.success(
                        f"✅ 所有 {len(st.session_state.batch_delete_accounts)} 個帳戶刪除成功"
                    )
                else:
                    st.warning(
                        f"⚠️ {success_count}/{len(st.session_state.batch_delete_accounts)} 個帳戶刪除成功"
                    )

                st.session_state.batch_delete_accounts = None
                st.rerun()

        with col2:
            if st.button("❌ 取消", key="cancel_batch_delete"):
                st.session_state.batch_delete_accounts = None
                st.rerun()


def filter_accounts(
    accounts: List[Dict[str, Any]], search_term: str, status_filter: str
) -> List[Dict[str, Any]]:
    """Filter accounts based on search term and status"""
    filtered = accounts

    # Apply search filter
    if search_term:
        filtered = [acc for acc in filtered if search_term.lower() in acc['name'].lower()]

    # Apply status filter
    if status_filter != "全部":
        filtered = [acc for acc in filtered if status_filter in acc['status']]

    return filtered
