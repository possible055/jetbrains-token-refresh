import base64
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.constants import resolve_config_path


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


def list_accounts(config_path: Optional[Union[str, Path]] = None) -> List[str]:
    """
    List all accounts in the configuration.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, uses default config location.

    Returns:
        List[str]: A list of account names.
    """
    # 直接使用 load_config，它內部已使用 resolve_config_path
    config = load_config(config_path)
    if not config:
        return []

    return list(config["accounts"].keys())


def show_accounts_data(config_path: Optional[Union[str, Path]] = None) -> None:
    """
    Print all account data from the configuration file in a bullet-point format.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, the default configuration location will be used.
    """
    # 直接使用 load_config，它內部已使用 resolve_config_path
    config = load_config(config_path)
    if not config:
        return

    accounts = config["accounts"]
    fields_order = [
        "license_id",
        "refresh_token",
        "jwt_token",
        "created_time",
        "jwt_expired",
    ]
    timestamp_fields = ["created_time", "jwt_expired"]

    for account_name, account_data in accounts.items():
        print(f"Account: {account_name}")
        for field in fields_order:
            if field in account_data:
                value = account_data[field]
                if field in timestamp_fields and isinstance(value, (int, float)):
                    date_time = datetime.fromtimestamp(value)
                    print(f"{field}: {date_time.strftime('%Y-%m-%d %H:%M:%S')}")
                elif isinstance(value, str) and len(value) > 40:
                    print(f"{field}: {value[:40]}...")
                else:
                    print(f"{field}: {value}")
        print("-" * 50)


def parse_jwt_token_expiration(jwt_token: str) -> Optional[int]:
    """
    Parse the expiration time from a JWT token.

    Args:
        jwt_token (str): JWT token string.

    Returns:
        Optional[int]: The expiration time as a UNIX timestamp, or None if it cannot be parsed.
    """
    try:
        # A JWT token consists of three parts separated by dots: header.payload.signature
        parts = jwt_token.split('.')
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


def is_jwt_expired(jwt: str) -> bool:
    """
    Check whether the JWT token for the specified account has expired.

    Args:
        jwt (str): JWT string to check.

    Returns:
        bool: True if the token is expired, about to expire, or its expiration
            time cannot be determined; otherwise, False.
    """

    expires_at = parse_jwt_token_expiration(jwt)
    if expires_at is None:
        return True

    # Check if the token has expired or has less than 5 minutes (300 seconds) remaining
    current_time = int(time.time())
    return current_time >= expires_at or (expires_at - current_time) < 300


def is_id_token_expired(expired_at: int) -> bool:
    """
    Check whether the ID token has expired.

    Args:
        expired_at (int): Expiration time as a UNIX timestamp.

    Returns:
        bool: True if the token is expired, False otherwise.
    """
    current_time = int(time.time())
    return current_time >= expired_at or (expired_at - current_time) < 300
