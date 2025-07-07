import logging
from pathlib import Path
from typing import Optional, Union

# 使用標準 logging 而不是從 logging_setup 導入
logger = logging.getLogger("jetbrain_refresh_token.constants")

# Define paths
BASE_PATH = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_PATH.parent
LOG_PATH = PROJECT_ROOT / "logs"
CONFIG_PATH = PROJECT_ROOT / "config.json"
CONFIG_BACKUP_PATH = PROJECT_ROOT / "config-backup.json"


# Create logs directory if it doesn't exist
LOG_PATH.mkdir(parents=True, exist_ok=True)


def resolve_config_path(config_path: Optional[Union[str, Path]] = None) -> Path:
    """
    Parse the configuration path parameter into a standardized Path object.

    Args:
        config_path (Optional[Union[str, Path]], optional): The path to the configuration file.
            If None, the default path will be used.

    Returns:
        Path: A standardized Path object for the configuration file.
    """

    if config_path is None:
        logger.info("Using default configuration path: %s", CONFIG_PATH)
        return CONFIG_PATH
    if isinstance(config_path, str):
        path_obj = Path(config_path)
        logger.info("Using custom configuration path (converted from string): %s", path_obj)
        return path_obj
    logger.info("Using custom configuration path: %s", config_path)
    return config_path
