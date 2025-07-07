import json
from pathlib import Path
from typing import Optional, Union

from jetbrain_refresh_token.api.scheme import refresh_jwt
from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.config import (
    is_jwt_expired,
    load_config,
    parse_jwt_token_expiration,
)
from jetbrain_refresh_token.config.operate import backup_config_file, save_jwt_to_config
from jetbrain_refresh_token.constants import CONFIG_PATH


def refresh_account_jwt():
    pass


def refresh_accounts_jwt(config_path: Optional[Union[str, Path]] = None) -> bool:
    """
    Refreshes JWT tokens for all accounts if needed.

    Args:
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            Defaults to None, using the system default path.

    Returns:
        bool: Returns True if refresh is successful or not needed; returns False on failure.
    """

    config = load_config(config_path)
    if not config:
        return False

    # If no configuration path is specified, use the default path
    if config_path is None:
        config_path = CONFIG_PATH
    elif isinstance(config_path, str):
        config_path = Path(config_path)

    # Keeping track of the refresh status for all accounts
    all_successful = True
    config_updated = False

    for account_name, account_data in config["accounts"].items():
        # A JWT token requires both an auth_token and a license_id
        id_token = account_data.get("id_token", "N/A")
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

        new_jwt = refresh_jwt(id_token, license_id)
        if not new_jwt:
            logger.error(
                "Failed to refresh the JWT token. "
                "Please verify that the auth token and license ID are correct."
            )
            all_successful = False
            continue

        if old_jwt != "N/A":
            config["accounts"][account_name]["jwt_token_previous"] = old_jwt

        config["accounts"][account_name]["jwt_token"] = new_jwt

        # Parse and save the JWT expiration time
        expires_at = parse_jwt_token_expiration(str(new_jwt))
        if expires_at is not None:
            config["accounts"][account_name]["jwt_expired"] = expires_at
            logger.info("JWT token expiration time set for account: %s", account_name)
        else:
            logger.warning("Could not parse JWT expiration time for account: %s", account_name)

        config_updated = True
        logger.info("JWT token refresh successful for account: %s", account_name)

    # Save the configuration file if the JWT for any account has been updated
    if config_updated:
        try:
            logger.info("Backing up the configuration file before saving updates.")
            backup_config_file(config_path)

            with open(config_path, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=2)
            logger.info("Successfully saved all updated JWT tokens to config file")

        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("Failed to save config file: %s", e)
            all_successful = False

    return all_successful
