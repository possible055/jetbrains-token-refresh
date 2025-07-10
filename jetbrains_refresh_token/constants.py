import logging
from pathlib import Path

logger = logging.getLogger("jetbrain_refresh_token.constants")

# Define paths
BASE_PATH = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_PATH.parent
LOG_PATH = PROJECT_ROOT / "logs"
CONFIG_PATH = PROJECT_ROOT / "config.json"
CONFIG_BACKUP_PATH = PROJECT_ROOT / "config-backup.json"
SCHEMA_PATH = BASE_PATH / 'config' / "config_schema.json"

# Define constants for API endpoints
# These URLs are used for OAuth and JWT token management
# Ensure these URLs are correct and up-to-date with JetBrains API documentation
OAUTH_URL = "https://oauth.account.jetbrains.com/oauth2/token"
JWT_AUTH_URL = "https://api.jetbrains.ai/auth/jetbrains-jwt/provide-access/license/v2"
JWT_QUOTA_URL = "https://api.jetbrains.ai/user/v5/quota/get"
CLIENT_ID = "ide"

# Create logs directory if it doesn't exist
LOG_PATH.mkdir(parents=True, exist_ok=True)


FRONTEND_APP_PATH = BASE_PATH / "frontend" / "streamlit_app.py"
