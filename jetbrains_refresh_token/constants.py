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

# Create logs directory if it doesn't exist
LOG_PATH.mkdir(parents=True, exist_ok=True)


FRONTEND_APP_PATH = BASE_PATH / "frontend" / "streamlit_app.py"

# ID Token expiration extension time (in seconds)
# When refreshing ID tokens, extend the expiration time by this amount
# 3 days = 3 * 24 * 60 * 60 = 259200 seconds
ID_TOKEN_EXPIRATION_EXTENSION_SECONDS = 259200
