import sys
from pathlib import Path

import streamlit as st

from jetbrains_refresh_token.frontend.components import (
    accounts,
    daemon_status,
    dashboard,
    quotas,
    settings,
    tokens,
)
from jetbrains_refresh_token.frontend.services.daemon_status_reader import (
    DaemonStatusReader,
)
from jetbrains_refresh_token.frontend.utils.config_helper import ConfigHelper
from jetbrains_refresh_token.frontend.utils.state_manager import PersistentStateManager

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Page configuration
st.set_page_config(
    page_title="JetBrains Token Manager",
    # page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .warning-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #ffc107;
    }
    .error-card {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #dc3545;
    }
    .success-card {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_app():
    """Initialize the application with necessary components"""
    if 'state_manager' not in st.session_state:
        st.session_state.state_manager = PersistentStateManager()

    if 'config_helper' not in st.session_state:
        st.session_state.config_helper = ConfigHelper()

    # Initialize persistent state
    st.session_state.state_manager.init_session_state()

    # Initialize daemon status reader
    if 'daemon_status_reader' not in st.session_state:
        st.session_state.daemon_status_reader = DaemonStatusReader()


def render_sidebar():
    """Render the sidebar navigation"""
    st.sidebar.title("Token Manager")

    # Navigation menu
    pages = {
        "🏠 控制台": "dashboard",
        "👤 帐户管理": "accounts",
        "🔑 金钥监控": "tokens",
        "📊 配额管理": "quotas",
        "🔄 背景任务": "background_tasks",
        "⚙️ 设定": "settings",
    }

    # Get current page from session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # Page selection
    for page_name, page_key in pages.items():
        if st.sidebar.button(page_name, key=f"nav_{page_key}"):
            st.session_state.current_page = page_key
            st.rerun()

    st.sidebar.markdown("---")

    # System status in sidebar
    st.sidebar.subheader("系统状态")

    # Load config status
    try:
        config_status = st.session_state.config_helper.get_config_status()
        if config_status['valid']:
            st.sidebar.success(f"配置档案: 正常 ({config_status['accounts_count']} 个帐号)")
        else:
            st.sidebar.error("配置档案: 错误")
    except Exception as e:
        st.sidebar.error(f"配置档案: 无法读取 ({str(e)})")

    # Background services are now handled by daemon

    # Quick actions are now handled by daemon


def render_main_content():
    """Render the main content area based on current page"""
    current_page = st.session_state.current_page

    if current_page == 'dashboard':
        dashboard.render()
    elif current_page == 'accounts':
        accounts.render()
    elif current_page == 'tokens':
        tokens.render()
    elif current_page == 'quotas':
        quotas.render()
    elif current_page == 'background_tasks':
        daemon_status.render_daemon_status()
    elif current_page == 'settings':
        settings.render()
    else:
        st.error(f"未知页面: {current_page}")


def main():
    """Main application entry point"""
    # Initialize the application
    initialize_app()

    # Render sidebar
    render_sidebar()

    # Render main content
    render_main_content()


if __name__ == "__main__":
    main()
