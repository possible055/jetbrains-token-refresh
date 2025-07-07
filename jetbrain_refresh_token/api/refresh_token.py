from pathlib import Path
from typing import Optional, Union

from jetbrain_refresh_token.api.scheme import refresh_jwt
from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.config import (
    is_jwt_expired,
    load_config,
)
from jetbrain_refresh_token.config.operate import save_jwt_to_config
from jetbrain_refresh_token.constants import CONFIG_PATH


def refresh_account_jwt():
    pass


def refresh_accounts_jwt(config_path: Optional[Union[str, Path]] = None) -> bool:
    """
    檢查所有帳號並在需要時刷新其 JWT token，並將新的 token 保存到配置文件中。

    Args:
        config_path (Optional[Union[str, Path]], optional): 配置文件路徑。默認為 None，使用系統預設路徑。

    Returns:
        bool: 成功刷新或不需要刷新返回 True，失敗返回 False
    """
    config = load_config(config_path)
    if not config:
        return False

    # If no configuration path is specified, use the default path
    if config_path is None:
        config_path = CONFIG_PATH
    elif isinstance(config_path, str):
        config_path = Path(config_path)

    all_successful = True  # Keeping track of the refresh status for all accounts

    for account_name, account_data in config["accounts"].items():
        # A JWT token requires both an auth_token and a license_id
        auth_token = account_data.get("auth_token", "N/A")
        license_id = account_data.get("license_id", "N/A")

        old_jwt = account_data.get("jwt_token", "N/A")

        if not is_jwt_expired(old_jwt):
            logger.info(
                "JWT token for account '%s' is still valid and does not require renewal.",
                account_name,
            )
            continue

        logger.info(
            "The JWT token for account '%s' is nearing expiration. Initiating refresh.",
            account_name,
        )

        new_jwt = refresh_jwt(auth_token, license_id)
        if not new_jwt:
            logger.error(
                "Failed to refresh the JWT token. "
                "Please verify that the auth token and license ID are correct."
            )
            all_successful = False
            continue

        tokens = {"jwt_token": new_jwt}

        if old_jwt != "N/A":
            tokens["jwt_token_previous"] = old_jwt

        # Save JWT token
        if not save_jwt_to_config(account_name, tokens, config, config_path):
            logger.error("Failed to save updated JWT token for account: %s", account_name)
            all_successful = False
            continue

        logger.info("JWT token refresh successful for account: %s", account_name)

    return all_successful
