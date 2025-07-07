from pathlib import Path

# Define paths
BASE_PATH = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_PATH.parent
LOG_PATH = PROJECT_ROOT / "logs"
CONFIG_PATH = PROJECT_ROOT / "config.json"
CONFIG_BACKUP_PATH = PROJECT_ROOT / "config-backup.json"


# Create logs directory if it doesn't exist
LOG_PATH.mkdir(parents=True, exist_ok=True)
