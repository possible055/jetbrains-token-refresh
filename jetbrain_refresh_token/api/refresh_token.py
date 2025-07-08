from pathlib import Path
from typing import Optional, Union

from jetbrain_refresh_token.api.scheme import request_access_token
from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.config import (
    load_config,
    parse_jwt_expiration,
    resolve_config_path,
)
from jetbrain_refresh_token.config.operate import (
    save_access_tokens,
)
from jetbrain_refresh_token.config.utils import is_jwt_expired


def refresh_expired_access_tokens(
    config_path: Optional[Union[str, Path]] = None, forced: bool = False
) -> bool:
    """
    Refreshes JWT for all accounts if needed.

    Args:
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            Defaults to None, using the system default path.
        forced (bool, optional): If True, forces refresh of all access tokens regardless of
            expiration status. Defaults to False.

    Returns:
        bool: Returns True if refresh is successful or not needed; returns False on failure.
    """
    config_path = resolve_config_path(config_path)

    config = load_config(config_path)
    if not config:
        return False

    # Keeping track of the refresh status for all accounts
    all_successful = True
    config_updated = False
    updated_accounts = []  # Track which accounts are updated

    for account_name, account_data in config["accounts"].items():
        # A JWT token requires both an auth_token and a license_id
        id_token = account_data.get("id_token", "N/A")
        license_id = account_data.get("license_id", "N/A")

        current_access_token = account_data.get("access_token", "N/A")

        if not forced and not is_jwt_expired(current_access_token):
            logger.info(
                "Access token for account '%s' is still valid and does not require renewal.",
                account_name,
            )
            continue

        if forced:
            logger.info(
                "Forced refresh mode: Initiating refresh for account '%s'.",
                account_name,
            )
        else:
            logger.info(
                "Access token for account '%s' is nearing expiration. Initiating refresh.",
                account_name,
            )

        new_access_token = request_access_token(id_token, license_id)
        if not new_access_token:
            logger.error(
                "Failed to refresh the JWT token. "
                "Please verify that the auth token and license ID are correct."
            )
            all_successful = False
            continue

        if current_access_token != "N/A":
            config["accounts"][account_name]["previous_access_token"] = current_access_token

        config["accounts"][account_name]["access_token"] = new_access_token

        # Parse and save the JWT expiration time
        expires_at = parse_jwt_expiration(str(new_access_token))
        if expires_at is not None:
            config["accounts"][account_name]["access_token_expires_at"] = expires_at
            logger.info("Access token expiration time set for account: %s", account_name)
        else:
            logger.warning(
                "Could not parse Access token expiration time for account: %s", account_name
            )

        config_updated = True
        updated_accounts.append(account_name)
        logger.info("Access token refresh successful for account: %s", account_name)

    # Save the configuration file if the JWT for any account has been updated
    if config_updated:
        # Use the new function to save multiple JWT tokens
        save_result = save_access_tokens(
            config=config, config_path=config_path, updated_accounts=updated_accounts
        )

        if not save_result:
            logger.error("Failed to save updated Access tokens to config file")
            all_successful = False

    return all_successful
