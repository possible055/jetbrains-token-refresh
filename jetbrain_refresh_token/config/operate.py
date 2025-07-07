import json
from pathlib import Path
from typing import Dict, Optional, Union

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.config import load_config, parse_jwt_token_expiration
from jetbrain_refresh_token.constants import CONFIG_PATH


def save_account_tokens(
    account_name: str,
    tokens: Dict,
    config_path: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Save or update account tokens in the configuration file.

    Args:
        account_name (str): Name of the account to save.
        tokens (Dict): Dictionary containing token information.
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, uses default config location.

    Returns:
        bool: True if successful, False otherwise.
    """
    config = load_config(config_path)
    if config is None:
        return False

    if config_path is None:
        config_path = CONFIG_PATH

    try:
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
                    logger.info("JWT token expiration time set for account: %s", account_name)
                else:
                    logger.warning(
                        "Could not parse JWT expiration time for account: %s", account_name
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
