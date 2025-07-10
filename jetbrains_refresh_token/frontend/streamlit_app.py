import sys
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from jetbrains_refresh_token.frontend.components import (
    accounts,
    dashboard,
    quotas,
    settings,
    tokens,
)
from jetbrains_refresh_token.frontend.utils.config_helper import ConfigHelper
from jetbrains_refresh_token.frontend.utils.state_manager import PersistentStateManager

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Import services with proper type checking
if TYPE_CHECKING:
    from jetbrains_refresh_token.frontend.services.background_tasks import (
        BackgroundTasks as BackgroundTasksClass,
    )
    from jetbrains_refresh_token.frontend.services.scheduler_service import (
        SchedulerService as SchedulerServiceClass,
    )

# Runtime imports for services
BackgroundTasksClass = None
SchedulerServiceClass = None
SERVICES_AVAILABLE = False

try:
    from jetbrains_refresh_token.frontend.services.background_tasks import (
        BackgroundTasks as BackgroundTasksClass,
    )
    from jetbrains_refresh_token.frontend.services.scheduler_service import (
        SchedulerService as SchedulerServiceClass,
    )

    SERVICES_AVAILABLE = True
except ImportError as e:
    SERVICES_AVAILABLE = False
    print(f"Warning: Background services not available: {e}")

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

    # Initialize background services if available
    if (
        SERVICES_AVAILABLE
        and BackgroundTasksClass is not None
        and SchedulerServiceClass is not None
    ):
        if 'scheduler_service' not in st.session_state:
            st.session_state.scheduler_service = SchedulerServiceClass(
                config_helper=st.session_state.config_helper,
                state_manager=st.session_state.state_manager,
            )

        if 'background_tasks' not in st.session_state:
            st.session_state.background_tasks = BackgroundTasksClass(
                config_helper=st.session_state.config_helper,
                state_manager=st.session_state.state_manager,
            )

        # Start scheduler if not already running
        if not st.session_state.scheduler_service.is_running:
            st.session_state.scheduler_service.start()
            st.session_state.scheduler_service.setup_default_jobs()


def render_sidebar():
    """Render the sidebar navigation"""
    st.sidebar.title("Token Manager")

    # Navigation menu
    pages = {
        "🏠 主控台": "dashboard",
        "👤 帳戶管理": "accounts",
        "🔑 金鑰監控": "tokens",
        "📊 配額管理": "quotas",
        "⚙️ 設定": "settings",
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
    st.sidebar.subheader("系統狀態")

    # Load config status
    try:
        config_status = st.session_state.config_helper.get_config_status()
        if config_status['valid']:
            st.sidebar.success(f"配置檔案: 正常 ({config_status['accounts_count']} 個帳戶)")
        else:
            st.sidebar.error("配置檔案: 錯誤")
    except Exception as e:
        st.sidebar.error(f"配置檔案: 無法讀取 ({str(e)})")

    # Background services status
    if SERVICES_AVAILABLE and 'scheduler_service' in st.session_state:
        scheduler_service = st.session_state.scheduler_service
        if scheduler_service is not None:
            scheduler_status = scheduler_service.get_status()
            if scheduler_status['running']:
                st.sidebar.success(f"背景服務: 運行中 ({scheduler_status['jobs_count']} 個任務)")
            else:
                st.sidebar.warning("背景服務: 已停止")
        else:
            st.sidebar.info("背景服務: 未啟用")
    else:
        st.sidebar.info("背景服務: 未啟用")

    # Quick actions
    st.sidebar.subheader("快速操作")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄", key="refresh"):
            st.session_state.config_helper.refresh_config()
            st.rerun()

    with col2:
        if st.button("💾", key="backup"):
            success = st.session_state.config_helper.backup_config()
            if success:
                st.sidebar.success("備份成功")
            else:
                st.sidebar.error("備份失敗")


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
    elif current_page == 'settings':
        settings.render()
    else:
        st.error(f"未知頁面: {current_page}")


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
