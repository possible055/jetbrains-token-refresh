import base64
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.constants import BASE_PATH, CONFIG_PATH


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
    if config_path is None:
        config_path = BASE_PATH / "config" / "config.json"
    elif isinstance(config_path, str):
        config_path = Path(config_path)

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
        # 例如：讀檔過程中 permission 被拒
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


def get_account_tokens(
    account_name: str, config_path: Optional[Union[str, Path]] = None
) -> Optional[Dict]:
    """
    Retrieve tokens for a specified account from the configuration.

    If `account_name` is None, the default account will be used.
    If `config_path` is None, the default config location is used.

    Args:
        account_name (str, optional): Account name to retrieve tokens for.
            If None, uses the default account.
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, uses default config location.

    Returns:
        Optional[Dict]: Dictionary of account tokens if available; otherwise None.
    """
    config = load_config(config_path)
    if not config:
        return None

    # Check if account exists
    if account_name not in config["accounts"]:
        logger.error("Account '%s' not found in configuration", account_name)
        return None

    account_data = config["accounts"][account_name]

    # Validate required token fields
    required_fields = ["access_token", "refresh_token", "jwt_token", "license_id"]
    missing_fields = [field for field in required_fields if field not in account_data]

    if missing_fields:
        logger.error(
            "Missing required fields in account configuration: %s", {', '.join(missing_fields)}
        )
        return None

    return account_data


def list_accounts(config_path: Optional[Union[str, Path]] = None) -> List[Tuple[str, bool]]:
    """
    List all accounts in the configuration, indicating which one is the default.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.

    Returns:
        List[Tuple[str, bool]]: A list of (account_name, is_default) tuples.
    """
    config = load_config(config_path)
    if not config:
        return []

    return list(config["accounts"].keys())


def save_account_tokens(
    account_name: str,
    tokens: Dict,
    config_path: Optional[Union[str, Path]] = CONFIG_PATH,
) -> bool:
    """
    Save or update account tokens in the configuration file.

    Args:
        account_name (str): Name of the account to save.
            tokens (Dict): Dictionary containing token information.
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, uses default config location.
        set_as_default (bool, optional): Whether to set this account as default. Defaults to False.

    Returns:
        bool: True if successful, False otherwise.
    """
    if config_path is None:
        config_path = BASE_PATH / "config" / "config.json"
    elif isinstance(config_path, str):
        config_path = Path(config_path)

    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as file:
                config: Dict[str, Any] = json.load(file)
        else:
            config: Dict[str, Any] = {"accounts": {}}
            config_path.parent.mkdir(parents=True, exist_ok=True)

        if "accounts" not in config:
            config["accounts"] = {}

        # 處理舊的 JWT token 和解析過期時間
        if account_name in config["accounts"] and "jwt_token" in tokens:
            existing_account = config["accounts"][account_name]
            # 如果已有 JWT token，將其保存為 previous_jwt_token
            if "jwt_token" in existing_account:
                # 只有當新的 JWT token 與舊的不同時才更新
                if existing_account["jwt_token"] != tokens["jwt_token"]:
                    tokens["previous_jwt_token"] = existing_account["jwt_token"]
                # 如果舊設定中已有 previous_jwt_token，且我們不需要更新它，則保留
                elif "previous_jwt_token" in existing_account:
                    tokens["previous_jwt_token"] = existing_account["previous_jwt_token"]

            # 如果舊設定中有 previous_jwt_token 但新 tokens 中沒有，則保留
            elif "previous_jwt_token" in existing_account and "previous_jwt_token" not in tokens:
                tokens["previous_jwt_token"] = existing_account["previous_jwt_token"]

            # 解析 JWT token 過期時間
            if "jwt_token" in tokens:
                expires_at = parse_jwt_token_expiration(tokens["jwt_token"])
                if expires_at is not None:
                    tokens["jwt_expires_at"] = expires_at
                    logger.info(f"JWT token expiration time set for account: {account_name}")
                else:
                    logger.warning(
                        f"Could not parse JWT expiration time for account: {account_name}"
                    )

        # Update account information
        config["accounts"][account_name] = tokens

        # Write back to file
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2)

        logger.info("Successfully saved tokens for account: %s", account_name)
        return True
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Failed to save account tokens: %s", e)
        return False


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


def is_jwt_token_expired(account_name: str, config_path: Optional[Union[str, Path]] = None) -> bool:
    """
    Check whether the JWT token for the specified account has expired.

    If the expiration time cannot be determined, or the account data cannot be loaded,
    the token is assumed to be expired for safety.
    A token with less than 5 minutes of remaining validity is also considered expired.

    Args:
        account_name (str, optional): The name of the account to check.
            If None, the default account is used.
        config_path (Union[str, Path], optional): The path to the configuration file.
            If None, the default configuration location is used.

    Returns:
        bool: True if the token is expired, about to expire, or its expiration
            time cannot be determined; otherwise, False.
    """
    # Retrieve account tokens
    account_data = get_account_tokens(account_name, config_path)
    if not account_data:
        return True

    # Check if expiration time information is available
    if "jwt_expires_at" not in account_data:
        # If expiration time info is missing, attempt to parse the existing token
        if "jwt_token" in account_data:
            expires_at = parse_jwt_token_expiration(account_data["jwt_token"])

            if expires_at is None:
                return True

            account_data["jwt_expires_at"] = expires_at
        else:
            return True

    expires_at = account_data["jwt_expires_at"]

    # Check if the token has expired or has less than 5 minutes (300 seconds) remaining
    current_time = int(time.time())
    return current_time >= expires_at or (expires_at - current_time) < 300
