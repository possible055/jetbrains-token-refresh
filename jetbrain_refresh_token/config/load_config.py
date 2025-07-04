import json
import base64
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from jetbrain_refresh_token import BASE_PATH
from jetbrain_refresh_token.config import logger


def load_config(config_path: Optional[Union[str, Path]] = None) -> Optional[Dict]:
    """
    Load configuration from a JSON file.

    If `config_path` is None, the default config location will be used.

    Args:
        config_path (Union[str, Path], optional):
            Path to the configuration file.
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
    if "accounts" not in config or not isinstance(config["accounts"], dict):
        logger.error("Invalid configuration: 'accounts' section missing or invalid")
        return None

    if "default_account" not in config:
        logger.warning("No default account specified in configuration")

    return config


def get_account_tokens(
    account_name: Optional[str] = None, config_path: Optional[Union[str, Path]] = None
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

    # If no account specified, use default
    if account_name is None:
        if "default_account" not in config:
            logger.error("No account specified and no default account in configuration")
            return None

        account_name = config["default_account"]

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
        
    # 檢查是否有新欄位 (非必須欄位)
    if "jwt_expires_at" not in account_data:
        logger.debug("JWT expiration time not available for account: %s", account_name)
        
    if "previous_jwt_token" not in account_data:
        logger.debug("Previous JWT token not available for account: %s", account_name)
    else:
        logger.debug("Previous JWT token available for account: %s", account_name)

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
    if not config or "accounts" not in config:
        return []

    default_account = config.get("default_account", "")

    return [
        (account_name, account_name == default_account)
        for account_name in config["accounts"].keys()
    ]


def save_account_tokens(
    account_name: str,
    tokens: Dict,
    config_path: Optional[Union[str, Path]] = None,
    set_as_default: bool = False,
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
    try:
        # If no path provided, use default location
        if config_path is None:
            config_path = BASE_PATH / "config" / "config.json"
        # If string path provided, convert to Path object
        elif isinstance(config_path, str):
            config_path = Path(config_path)

        # Load existing config or create new one
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as file:
                config: Dict[str, Any] = json.load(file)
        else:
            config: Dict[str, Any] = {"accounts": {}}

            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure required structure exists
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
                    logger.warning(f"Could not parse JWT expiration time for account: {account_name}")

        # Update account information
        config["accounts"][account_name] = tokens

        # Set as default if requested
        if set_as_default:
            config["default_account"] = account_name

        # Write back to file
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2)

        logger.info(f"Successfully saved tokens for account: {account_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to save account tokens: {e}")
        return False


def parse_jwt_token_expiration(jwt_token: str) -> Optional[int]:
    """
    從 JWT token 解析過期時間。
    
    Args:
        jwt_token (str): JWT token 字串。
        
    Returns:
        Optional[int]: 以 UNIX 時間戳格式的過期時間，如果無法解析則返回 None。
    """
    try:
        # JWT token 由三部分組成，以點號分隔：header.payload.signature
        parts = jwt_token.split('.')
        if len(parts) != 3:
            logger.error("Invalid JWT token format: expected 3 parts")
            return None
            
        # 解碼 payload 部分 (base64url 編碼)
        # 可能需要添加填充字符 '='
        payload = parts[1]
        payload_padded = payload + '=' * (4 - len(payload) % 4) if len(payload) % 4 else payload
        
        try:
            decoded_bytes = base64.urlsafe_b64decode(payload_padded)
            payload_data = json.loads(decoded_bytes.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to decode JWT payload: {e}")
            return None
            
        # 從 payload 中提取過期時間 (exp claim)
        if 'exp' in payload_data:
            return payload_data['exp']
        
        logger.warning("JWT token does not contain expiration time (exp claim)")
        return None
    except Exception as e:
        logger.error(f"Error parsing JWT token: {e}")
        return None


def is_jwt_token_expired(
    account_name: Optional[str] = None, config_path: Optional[Union[str, Path]] = None
) -> bool:
    """
    檢查指定帳戶的 JWT token 是否已過期。
    
    如果無法確定過期時間，或無法載入帳戶資料，將安全地假設 token 已過期。
    
    Args:
        account_name (str, optional): 要檢查的帳戶名稱。
                                      如果為 None，使用預設帳戶。
        config_path (Union[str, Path], optional): 配置檔案路徑。
                                                 如果為 None，使用預設配置位置。
    
    Returns:
        bool: 如果 token 已過期或無法確定過期時間則返回 True，否則返回 False。
    """
    # 獲取帳戶 tokens
    account_data = get_account_tokens(account_name, config_path)
    if not account_data:
        # 如果無法獲取帳戶數據，安全地假設已過期
        return True
    
    # 檢查是否有過期時間資訊
    if "jwt_expires_at" not in account_data:
        # 如果沒有過期時間資訊，嘗試解析現有的 token
        if "jwt_token" in account_data:
            expires_at = parse_jwt_token_expiration(account_data["jwt_token"])
            if expires_at is None:
                # 無法解析過期時間，安全地假設已過期
                return True
            # 使用解析出的過期時間繼續檢查
        else:
            # 沒有 JWT token，安全地假設已過期
            return True
    else:
        expires_at = account_data["jwt_expires_at"]
    
    # 比較過期時間與當前時間
    current_time = int(time.time())
    return current_time >= expires_at


def get_jwt_token_remaining_time(
    account_name: Optional[str] = None, config_path: Optional[Union[str, Path]] = None
) -> Optional[int]:
    """
    獲取指定帳戶的 JWT token 剩餘有效時間（秒）。
    
    Args:
        account_name (str, optional): 要檢查的帳戶名稱。
                                      如果為 None，使用預設帳戶。
        config_path (Union[str, Path], optional): 配置檔案路徑。
                                                 如果為 None，使用預設配置位置。
    
    Returns:
        Optional[int]: 剩餘秒數，如果已過期則返回 0，如果無法確定則返回 None。
    """
    # 獲取帳戶 tokens
    account_data = get_account_tokens(account_name, config_path)
    if not account_data:
        # 如果無法獲取帳戶數據，返回 None
        return None
    
    # 檢查是否有過期時間資訊
    if "jwt_expires_at" not in account_data:
        # 如果沒有過期時間資訊，嘗試解析現有的 token
        if "jwt_token" in account_data:
            expires_at = parse_jwt_token_expiration(account_data["jwt_token"])
            if expires_at is None:
                # 無法解析過期時間
                return None
            # 使用解析出的過期時間繼續計算
        else:
            # 沒有 JWT token
            return None
    else:
        expires_at = account_data["jwt_expires_at"]
    
    # 計算剩餘時間
    current_time = int(time.time())
    remaining_time = expires_at - current_time
    
    # 如果已過期，返回 0
    return max(0, remaining_time)
