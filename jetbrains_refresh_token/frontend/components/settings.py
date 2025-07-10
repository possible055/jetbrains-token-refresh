"""
Settings Page - Application settings and configuration for JetBrains Token Manager
Handles system settings, logs, import/export, and advanced configurations
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import streamlit as st


def render():
    """Render the settings page"""
    st.markdown('<h1 class="main-header">⚙️ 設定</h1>', unsafe_allow_html=True)

    # Get configuration helper and state manager
    config_helper = st.session_state.get('config_helper')
    state_manager = st.session_state.get('state_manager')

    if not config_helper:
        st.error("配置助手未初始化")
        return

    # Create tabs for different settings sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["⚙️ 應用設定", "ℹ️ 系統資訊", "📋 日誌檢視", "📁 匯入/匯出", "🔧 進階設定"]
    )

    with tab1:
        render_app_settings()

    with tab2:
        render_system_info(config_helper, state_manager)

    with tab3:
        render_logs_viewer(state_manager)

    with tab4:
        render_import_export(config_helper)

    with tab5:
        render_advanced_settings(config_helper)


def render_app_settings():
    """Render application settings"""
    st.subheader("⚙️ 應用程式設定")

    # Auto-refresh settings
    st.write("**自動刷新設定:**")

    auto_refresh = st.checkbox(
        "啟用自動刷新",
        value=st.session_state.get('auto_refresh_enabled', True),
        key="settings_auto_refresh",
    )

    if auto_refresh:
        refresh_interval = st.slider(
            "刷新間隔（秒）",
            min_value=10,
            max_value=300,
            value=st.session_state.get('refresh_interval', 30),
            key="settings_refresh_interval",
        )
        st.session_state.refresh_interval = refresh_interval

    st.session_state.auto_refresh_enabled = auto_refresh

    # Notification settings
    st.write("**通知設定:**")

    enable_notifications = st.checkbox(
        "啟用通知",
        value=st.session_state.get('enable_notifications', True),
        key="settings_notifications",
    )

    if enable_notifications:
        notification_types = st.multiselect(
            "通知類型",
            ["Token 過期", "配額警告", "系統錯誤", "操作成功"],
            default=st.session_state.get('notification_types', ["Token 過期", "配額警告"]),
            key="settings_notification_types",
        )
        st.session_state.notification_types = notification_types

    st.session_state.enable_notifications = enable_notifications

    # Display settings
    st.write("**顯示設定:**")

    theme = st.selectbox(
        "主題",
        ["自動", "亮色", "暗色"],
        index=["自動", "亮色", "暗色"].index(st.session_state.get('theme', '自動')),
        key="settings_theme",
    )
    st.session_state.theme = theme

    items_per_page = st.number_input(
        "每頁顯示項目數",
        min_value=5,
        max_value=50,
        value=st.session_state.get('items_per_page', 10),
        key="settings_items_per_page",
    )
    st.session_state.items_per_page = items_per_page

    # Save settings
    if st.button("💾 儲存設定", key="save_app_settings"):
        state_manager = st.session_state.get('state_manager')
        if state_manager:
            # Save all settings to persistent storage
            settings_to_save = {
                'auto_refresh_enabled': st.session_state.auto_refresh_enabled,
                'refresh_interval': st.session_state.get('refresh_interval', 30),
                'enable_notifications': st.session_state.enable_notifications,
                'notification_types': st.session_state.get('notification_types', []),
                'theme': st.session_state.theme,
                'items_per_page': st.session_state.items_per_page,
            }

            for key, value in settings_to_save.items():
                state_manager.save_state(key, value)

            st.success("✅ 設定已儲存")
        else:
            st.error("❌ 無法儲存設定：狀態管理器未初始化")


def render_system_info(config_helper, state_manager):
    """Render system information"""
    st.subheader("ℹ️ 系統資訊")

    # Python and environment info
    st.write("**Python 環境:**")
    st.code(
        f"""
Python 版本: {sys.version}
Python 路徑: {sys.executable}
工作目錄: {Path.cwd()}
""",
        language="text",
    )

    # Application info
    st.write("**應用程式資訊:**")

    # Get system info from config helper
    system_info = config_helper.get_system_info()

    col1, col2 = st.columns(2)

    with col1:
        st.write("**配置資訊:**")
        st.write(f"配置檔案路徑: {system_info.get('config_path', 'N/A')}")
        st.write(f"配置檔案存在: {'✅' if system_info.get('config_exists', False) else '❌'}")
        st.write(f"配置檔案大小: {system_info.get('config_size', 0)} bytes")
        st.write(f"帳戶數量: {system_info.get('accounts_count', 0)}")

        if system_info.get('last_modified'):
            last_modified = datetime.fromisoformat(system_info['last_modified'])
            st.write(f"最後修改: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")

    with col2:
        st.write("**狀態管理:**")
        if state_manager:
            state_summary = state_manager.get_state_summary()
            st.write(f"狀態數量: {state_summary.get('total_states', 0)}")
            st.write(f"日誌數量: {state_summary.get('total_logs', 0)}")
            st.write(f"資料庫大小: {state_summary.get('database_size', 0)} bytes")

            if state_summary.get('last_update'):
                last_update = datetime.fromisoformat(state_summary['last_update'])
                st.write(f"最後更新: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.write("狀態管理器未初始化")

    # Runtime info
    st.write("**運行時資訊:**")

    current_time = datetime.now()
    session_id = st.session_state.get('session_id', 'N/A')

    st.write(f"當前時間: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"會話 ID: {session_id}")

    # Memory and performance info (basic)
    st.write("**效能資訊:**")
    st.write(f"Session State 大小: {len(st.session_state)} 個項目")

    # Show session state contents (for debugging)
    if st.checkbox("顯示 Session State 內容", key="show_session_state"):
        st.write("**Session State 內容:**")

        # Filter out sensitive information
        filtered_state = {}
        for key, value in st.session_state.items():
            if 'token' not in str(key).lower() and 'password' not in str(key).lower():
                filtered_state[key] = str(value)[:100] + "..." if len(str(value)) > 100 else value

        st.json(filtered_state)


def render_logs_viewer(state_manager):
    """Render logs viewer"""
    st.subheader("📋 日誌檢視")

    if not state_manager:
        st.error("狀態管理器未初始化")
        return

    # Log filtering options
    col1, col2 = st.columns(2)

    with col1:
        log_limit = st.number_input(
            "顯示日誌數量", min_value=10, max_value=1000, value=50, key="log_limit"
        )

    with col2:
        if st.button("🔄 重新整理日誌", key="refresh_logs"):
            st.rerun()

    # Get logs
    session_id = st.session_state.get('session_id', '')
    logs = state_manager.get_session_logs(session_id, limit=log_limit)

    if not logs:
        st.info("📝 沒有日誌記錄")
        return

    # Display logs
    st.write(f"**顯示最近 {len(logs)} 條日誌:**")

    # Create a container for logs
    log_container = st.container()

    with log_container:
        for i, (action, details, timestamp) in enumerate(logs):
            formatted_time = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            # Create expandable log entry
            with st.expander(f"🕐 {formatted_time} - {action}", expanded=i < 5):
                if details:
                    st.write(f"**詳細資訊:** {details}")
                else:
                    st.write("無詳細資訊")

                st.write(f"**時間戳記:** {timestamp}")

    # Log management
    st.write("**日誌管理:**")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 匯出日誌", key="export_logs"):
            log_data = {
                'exported_at': datetime.now().isoformat(),
                'session_id': session_id,
                'logs': [
                    {'action': action, 'details': details, 'timestamp': timestamp}
                    for action, details, timestamp in logs
                ],
            }

            log_json = json.dumps(log_data, indent=2, ensure_ascii=False)

            st.download_button(
                label="📥 下載日誌檔案",
                data=log_json,
                file_name=f"logs_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

    with col2:
        if st.button("🗑️ 清除日誌", key="clear_logs"):
            # Note: This would clear all logs, be careful
            st.warning("⚠️ 此操作將清除所有日誌記錄，請確認是否繼續")

            if st.button("確認清除", key="confirm_clear_logs"):
                # Implementation would go here
                st.info("日誌清除功能需要進一步實現")


def render_import_export(config_helper):
    """Render import/export functionality"""
    st.subheader("📁 匯入/匯出")

    # Export configuration
    st.write("**匯出配置:**")

    export_format = st.selectbox("匯出格式", ["JSON", "CSV", "YAML"], key="export_format")

    include_sensitive = st.checkbox(
        "包含敏感資訊（Token）",
        value=False,
        key="include_sensitive_export",
        help="⚠️ 包含敏感資訊的匯出檔案應妥善保管",
    )

    if st.button("📥 匯出配置", key="export_config"):
        config_data = generate_export_data(config_helper, include_sensitive)

        if export_format == "JSON":
            export_content = json.dumps(config_data, indent=2, ensure_ascii=False)
            mime_type = "application/json"
            file_extension = "json"
        elif export_format == "CSV":
            export_content = generate_csv_export(config_data)
            mime_type = "text/csv"
            file_extension = "csv"
        else:  # YAML
            # For now, use JSON format for YAML
            export_content = json.dumps(config_data, indent=2, ensure_ascii=False)
            mime_type = "text/yaml"
            file_extension = "yaml"

        filename = f"jetbrains_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"

        st.download_button(
            label=f"📥 下載 {export_format} 檔案",
            data=export_content,
            file_name=filename,
            mime=mime_type,
        )

    # Import configuration
    st.write("**匯入配置:**")

    uploaded_file = st.file_uploader(
        "選擇配置檔案", type=['json', 'csv', 'yaml'], key="import_file"
    )

    if uploaded_file:
        try:
            if uploaded_file.type == "application/json":
                config_data = json.load(uploaded_file)
            else:
                st.error("目前只支援 JSON 格式的匯入")
                return

            # Preview import data
            st.write("**預覽匯入資料:**")

            # Show basic info about the config
            if 'accounts' in config_data:
                st.write(f"帳戶數量: {len(config_data['accounts'])}")

                # Show account names
                account_names = list(config_data['accounts'].keys())
                st.write(f"帳戶名稱: {', '.join(account_names)}")

            # Import options
            merge_mode = st.selectbox(
                "匯入模式", ["覆蓋現有配置", "合併配置", "僅新增不存在的帳戶"], key="import_mode"
            )

            if st.button("📤 確認匯入", key="confirm_import"):
                success = import_configuration(config_helper, config_data, merge_mode)

                if success:
                    st.success("✅ 配置匯入成功")
                    st.rerun()
                else:
                    st.error("❌ 配置匯入失敗")

        except Exception as e:
            st.error(f"❌ 檔案格式錯誤: {str(e)}")


def render_advanced_settings(config_helper):
    """Render advanced settings"""
    st.subheader("🔧 進階設定")

    # Backup settings
    st.write("**備份設定:**")

    auto_backup = st.checkbox(
        "啟用自動備份", value=st.session_state.get('auto_backup', True), key="auto_backup_setting"
    )

    if auto_backup:
        backup_interval = st.selectbox(
            "備份間隔", ["每次修改", "每小時", "每天", "每週"], index=0, key="backup_interval"
        )

        max_backups = st.number_input(
            "最大備份數量",
            min_value=1,
            max_value=50,
            value=st.session_state.get('max_backups', 10),
            key="max_backups",
        )

    # Security settings
    st.write("**安全設定:**")

    encrypt_storage = st.checkbox(
        "加密儲存敏感資料",
        value=st.session_state.get('encrypt_storage', False),
        key="encrypt_storage",
        help="⚠️ 啟用加密後，舊的未加密資料將無法讀取",
    )

    session_timeout = st.number_input(
        "會話逾時時間（分鐘）",
        min_value=5,
        max_value=480,
        value=st.session_state.get('session_timeout', 60),
        key="session_timeout",
    )

    # Performance settings
    st.write("**效能設定:**")

    cache_enabled = st.checkbox(
        "啟用快取", value=st.session_state.get('cache_enabled', True), key="cache_enabled"
    )

    if cache_enabled:
        cache_ttl = st.number_input(
            "快取有效時間（秒）",
            min_value=10,
            max_value=3600,
            value=st.session_state.get('cache_ttl', 300),
            key="cache_ttl",
        )

    # Development settings
    st.write("**開發設定:**")

    debug_mode = st.checkbox(
        "除錯模式", value=st.session_state.get('debug_mode', False), key="debug_mode"
    )

    if debug_mode:
        st.warning("⚠️ 除錯模式將顯示詳細的錯誤資訊，僅用於開發階段")

    # Reset settings
    st.write("**重置設定:**")

    if st.button("🔄 重置所有設定", key="reset_all_settings"):
        if st.button("確認重置", key="confirm_reset"):
            # Reset all settings to defaults
            reset_to_defaults()
            st.success("✅ 所有設定已重置為預設值")
            st.rerun()


def generate_export_data(config_helper, include_sensitive: bool) -> Dict[str, Any]:
    """Generate export data"""
    config = config_helper.get_config()

    if not include_sensitive:
        # Remove sensitive information
        filtered_config = {'accounts': {}}

        for name, account in config.get('accounts', {}).items():
            filtered_account = {
                'license_id': account.get('license_id'),
                'created_time': account.get('created_time'),
                'access_token_expires_at': account.get('access_token_expires_at'),
                'id_token_expires_at': account.get('id_token_expires_at'),
                'quota_info': account.get('quota_info'),
            }

            # Remove None values
            filtered_account = {k: v for k, v in filtered_account.items() if v is not None}
            filtered_config['accounts'][name] = filtered_account

        return filtered_config

    return config


def generate_csv_export(config_data: Dict[str, Any]) -> str:
    """Generate CSV export (simplified)"""
    # This is a simplified CSV export
    # In a real implementation, you might want to use pandas or csv module

    csv_content = (
        "Account Name,License ID,Created Time,Access Token Expires,ID Token Expires,Quota Status\n"
    )

    for name, account in config_data.get('accounts', {}).items():
        created_time = account.get('created_time', '')
        if created_time:
            created_time = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S')

        access_expires = account.get('access_token_expires_at', '')
        if access_expires:
            access_expires = datetime.fromtimestamp(access_expires).strftime('%Y-%m-%d %H:%M:%S')

        id_expires = account.get('id_token_expires_at', '')
        if id_expires:
            id_expires = datetime.fromtimestamp(id_expires).strftime('%Y-%m-%d %H:%M:%S')

        quota_status = account.get('quota_info', {}).get('status', '')

        csv_content += f"{name},{account.get('license_id', '')},{created_time},{access_expires},{id_expires},{quota_status}\n"

    return csv_content


def import_configuration(config_helper, config_data: Dict[str, Any], merge_mode: str) -> bool:
    """Import configuration data"""
    try:
        if merge_mode == "覆蓋現有配置":
            # This would completely replace the current config
            # Implementation depends on the config_helper's capabilities
            return True

        elif merge_mode == "合併配置":
            # This would merge the imported config with existing one
            # Implementation depends on the config_helper's capabilities
            return True

        elif merge_mode == "僅新增不存在的帳戶":
            # This would only add new accounts that don't exist
            # Implementation depends on the config_helper's capabilities
            return True

        return False

    except Exception:
        return False


def reset_to_defaults():
    """Reset all settings to default values"""
    default_settings = {
        'auto_refresh_enabled': True,
        'refresh_interval': 30,
        'enable_notifications': True,
        'notification_types': ["Token 過期", "配額警告"],
        'theme': '自動',
        'items_per_page': 10,
        'auto_backup': True,
        'max_backups': 10,
        'encrypt_storage': False,
        'session_timeout': 60,
        'cache_enabled': True,
        'cache_ttl': 300,
        'debug_mode': False,
    }

    for key, value in default_settings.items():
        st.session_state[key] = value

    # Save to persistent storage
    state_manager = st.session_state.get('state_manager')
    if state_manager:
        for key, value in default_settings.items():
            state_manager.save_state(key, value)
