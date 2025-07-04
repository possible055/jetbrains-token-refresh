from pathlib import Path

from jetbrain_refresh_token.logging_setup import setup_logging

BASE_PATH = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_PATH.parent
LOG_PATH = PROJECT_ROOT / "logs"
LOG_PATH.mkdir(parents=True, exist_ok=True)

root_logger = setup_logging()
