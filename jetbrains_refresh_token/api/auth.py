from jetbrains_refresh_token.api.client import (
    request_access_token,
    request_quota_info,
)
from jetbrains_refresh_token.config import logger
from jetbrains_refresh_token.config.loader import (
    load_config,
)
from jetbrains_refresh_token.config.manager import (
    save_access_tokens,
    save_quota_info,
)
from jetbrains_refresh_token.config.utils import (
    is_access_token_expired,
    parse_jwt_expiration,
)


def refresh_expired_access_tokens(is_forced: bool = False) -> bool:
    """
    Refreshes JWT for all accounts if needed.

    Args:
        is_forced (bool, optional): If True, forces refresh of all access tokens regardless of
            expiration status. Defaults to False.

    Returns:
        bool: Returns True if refresh is successful or not needed; returns False on failure.
    """
    config = load_config()

    # Keeping track of the refresh status for all accounts
    all_successful = True
    config_updated = False
    updated_accounts = []  # Track which accounts are updated

    for account_name, account_data in config["accounts"].items():
        id_token = account_data.get("id_token")
        license_id = account_data.get("license_id")
        current_access_token = account_data.get("access_token")

        if not all([current_access_token, id_token, license_id]):
            logger.error(
                "Missing required fields for account '%s': id_token, license_id, or access_token.",
                account_name,
            )
            all_successful = False
            continue

        if is_forced:
            logger.info(
                "Forced refresh mode: Initiating refresh for account '%s'.",
                account_name,
            )
        else:
            if not is_access_token_expired(current_access_token):
                logger.info(
                    "Access token for account '%s' is still valid and does not require renewal.",
                    account_name,
                )
                continue

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
        save_access_tokens(config=config, updated_accounts=updated_accounts)

    return all_successful


def refresh_expired_access_token(account_name: str, is_forced: bool = False) -> bool:
    """
    Refreshes JWT for a single account if needed.

    Args:
        account_name (str): The name of the account to refresh.
        is_forced (bool, optional): If True, forces refresh of the access token regardless of
            expiration status. Defaults to False.

    Returns:
        bool: Returns True if refresh is successful or not needed; returns False on failure.
    """
    config = load_config()

    account_data = config["accounts"][account_name]

    # A JWT token requires both an auth_token and a license_id
    id_token = account_data.get("id_token")
    license_id = account_data.get("license_id")
    current_access_token = account_data.get("access_token")

    if not all([current_access_token, id_token, license_id]):
        logger.error(
            "Missing required fields for account '%s': id_token, license_id, or access_token.",
            account_name,
        )
        return False

    if is_forced:
        logger.info(
            "Forced refresh mode: Initiating refresh for account '%s'.",
            account_name,
        )
    else:
        if not is_access_token_expired(current_access_token):
            logger.info(
                "Access token for account '%s' is still valid and does not require renewal.",
                account_name,
            )
            return True

        logger.info(
            "Access token for account '%s' is nearing expiration. Initiating refresh.",
            account_name,
        )

    new_access_token = request_access_token(id_token, license_id)
    if not new_access_token:
        logger.error(
            "Failed to refresh the JWT token for account '%s'. "
            "Please verify that the auth token and license ID are correct.",
            account_name,
        )
        return False

    if current_access_token != "N/A":
        config["accounts"][account_name]["previous_access_token"] = current_access_token

    config["accounts"][account_name]["access_token"] = new_access_token

    # Parse and save the JWT expiration time
    expires_at = parse_jwt_expiration(str(new_access_token))
    if expires_at is not None:
        config["accounts"][account_name]["access_token_expires_at"] = expires_at
        logger.info("Access token expiration time set for account: %s", account_name)
    else:
        logger.warning("Could not parse Access token expiration time for account: %s", account_name)

    # Save the configuration file
    save_access_tokens(config=config, updated_accounts=[account_name])

    logger.info("Access token refresh successful for account: %s", account_name)
    return True


def check_quota_remaining() -> bool:
    """
    Check the remaining quota for all accounts' access tokens.

    Returns:
        bool: Returns True if all quota checks are successful or not needed;
            returns False on failure.
    """
    config = load_config()

    # Keeping track of the quota check status for all accounts
    all_successful = True
    config_updated = False
    updated_accounts = []  # Track which accounts are updated

    logger.info("Starting quota check for all accounts")

    for account_name, account_data in config["accounts"].items():
        # Get access token
        access_token = account_data.get("access_token", "N/A")
        if access_token == "N/A":
            logger.warning(
                "No access token found for account '%s'. Skipping quota check.", account_name
            )
            continue

        logger.info("Checking quota information for account: %s", account_name)

        # Request quota information
        quota_info = request_quota_info(access_token)
        if not quota_info:
            logger.error("Failed to retrieve quota information for account '%s'", account_name)
            all_successful = False
            continue

        logger.info("Successfully retrieved quota information for account: %s", account_name)
        logger.debug("Quota info for account '%s': %s", account_name, quota_info)

        # Save quota information to config file
        save_result = save_quota_info(config, account_name, quota_info)
        if save_result:
            logger.info("Quota information saved to config for account: %s", account_name)
            config_updated = True
            updated_accounts.append(account_name)
        else:
            logger.warning(
                "Failed to save quota information to config for account: %s", account_name
            )
            all_successful = False

    # Final save if any account was updated
    if config_updated:
        logger.info("Quota check completed for accounts: %s", ", ".join(updated_accounts))
    else:
        logger.info("No quota information was saved")

    return all_successful
