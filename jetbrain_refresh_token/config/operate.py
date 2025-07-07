import json
from pathlib import Path
from typing import Dict, Optional, Union

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.config import load_config, parse_jwt_token_expiration
from jetbrain_refresh_token.constants import CONFIG_PATH


def save_jwt_to_config(
    account_name: str,
    tokens: Dict,
    config: Dict,
    config_path: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Save or update account tokens in the configuration file.

    Args:
        account_name (str): Name of the account to save.
        tokens (Dict): Dictionary containing token information.
        config (Dict): Configuration dictionary that has been loaded.
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            If None, uses default config location.

    Returns:
        bool: True if successful, False otherwise.
    """
    # 確保配置有效
    if config is None:
        logger.error("無效的配置物件")
        return False

    # 確保配置路徑有效
    if config_path is None:
        config_path = CONFIG_PATH
    elif isinstance(config_path, str):
        config_path = Path(config_path)

    try:
        # 處理舊的 JWT token 和解析過期時間
        if account_name in config["accounts"] and "jwt_token" in tokens:
            existing_account = config["accounts"][account_name]
            # 如果已有 JWT token，始終將其保存為 jwt_token_previous
            if "jwt_token" in existing_account:
                tokens["jwt_token_previous"] = existing_account["jwt_token"]
                logger.info("Previous JWT token saved for account: %s", account_name)
            else:
                # 如果沒有舊的 JWT token，設置 jwt_token_previous 為空字串
                tokens["jwt_token_previous"] = ""
                logger.info("No previous JWT token found for account: %s", account_name)

            # 解析 JWT token 過期時間
            if "jwt_token" in tokens:
                expires_at = parse_jwt_token_expiration(str(tokens["jwt_token"]))
                if expires_at is not None:
                    tokens["jwt_expired"] = expires_at
                    logger.info("JWT token expiration time set for account: %s", account_name)
                else:
                    logger.warning(
                        "Could not parse JWT expiration time for account: %s", account_name
                    )

        # Update account information - 只更新特定欄位，而非完全覆蓋
        if account_name in config["accounts"]:
            # 更新現有帳戶的特定欄位，保留其他原有資料
            for key, value in tokens.items():
                config["accounts"][account_name][key] = value
        else:
            # 如果帳戶不存在，則創建新帳戶
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
