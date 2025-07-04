import logging
from pathlib import Path

from jetbrain_refresh_token.constants import LOG_PATH


def setup_logging():
    """
    Setup central logging configuration for the application.

    Returns:
        logging.Logger: Root logger instance
    """

    Path(LOG_PATH).mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger("jetbrain_refresh_token")
    root_logger.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # File handler
    file_handler = logging.FileHandler(f"{LOG_PATH}/jetbrain_api.log")
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers to the root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name):
    """
    Get a module-specific logger.

    Args:
        name (str): Name of the module requesting the logger

    Returns:
        logging.Logger: Logger instance for the specified module
    """
    # Get a logger with the given name, which inherits the root logger's configuration
    logger = logging.getLogger(f"jetbrain_refresh_token.{name}")
    return logger
