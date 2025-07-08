import base64
import json
from pathlib import Path
from typing import Dict, Optional, Union

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.constants import CONFIG_PATH, SCHEMA_PATH


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


def load_config(config_path: Optional[Union[str, Path]] = None) -> Optional[Dict]:
    """
    Load configuration from a JSON file.

    If `config_path` is None, the default config location will be used.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, uses default config.json in config directory.

    Returns:
        Optional[Dict]: Configuration dictionary on success; otherwise, None.
    """
    config_path = resolve_config_path(config_path)

    try:
        with config_path.open('r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", config_path)
        return None
    except json.JSONDecodeError as e:
        logger.error("Failed to parse configuration file: %s", e)
        return None
    except OSError as e:
        logger.error("OS error accessing configuration: %s", e)
        return None

    # Validate required structure
    if (
        "accounts" not in config
        or not isinstance(config["accounts"], dict)
        or not config["accounts"]
    ):
        logger.error("Invalid configuration: 'accounts' section missing, invalid, or empty")
        return None

    return config


def load_config_schema() -> Optional[Dict]:
    """
    Load configuration schema from JSON file.

    Returns:
        Optional[Dict]: Schema dictionary on success; otherwise, None.
    """
    schema_path = SCHEMA_PATH

    try:
        with schema_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Configuration schema file not found: %s", schema_path)
        return None
    except json.JSONDecodeError as e:
        logger.error("Failed to parse configuration schema file: %s", e)
        return None
    except OSError as e:
        logger.error("OS error accessing configuration schema: %s", e)
        return None


def parse_jwt_expiration(token: str) -> Optional[int]:
    """
    Parse the expiration time from a JWT token.

    Args:
        jwt_token (str): JWT token string.

    Returns:
        Optional[int]: The expiration time as a UNIX timestamp, or None if it cannot be parsed.
    """
    try:
        # A JWT token consists of three parts separated by dots: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            logger.error("Invalid JWT token format: expected 3 parts")
            return None

        # Decode the payload part (base64url encoded)
        # Padding characters '=' may need to be added
        payload = parts[1]
        payload_padded = payload + '=' * (4 - len(payload) % 4) if len(payload) % 4 else payload

        try:
            decoded_bytes = base64.urlsafe_b64decode(payload_padded)
            payload_data = json.loads(decoded_bytes.decode('utf-8'))
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("Failed to decode JWT payload: %s", e)
            return None

        # Extract the expiration time (exp claim) from the payload
        if 'exp' in payload_data:
            return payload_data['exp']

        logger.warning("JWT token does not contain expiration time (exp claim)")
        return None
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Error parsing JWT token: %s", e)
        return None
