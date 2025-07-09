from pathlib import Path
from typing import Dict, Optional, Union

from jetbrains_refresh_token.api.client import (
    request_access_token,
    request_id_token,
    request_quota_info,
)
from jetbrains_refresh_token.config import logger
from jetbrains_refresh_token.config.loader import (
    load_config,
    resolve_config_path,
)
from jetbrains_refresh_token.config.manager import (
    save_access_tokens,
    save_id_tokens,
    save_quota_info,
)
from jetbrains_refresh_token.config.utils import (
    is_id_token_expired,
    is_jwt_expired,
    parse_jwt_expiration,
)


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


def refresh_expired_access_token(
    account_name: str, config_path: Optional[Union[str, Path]] = None, forced: bool = False
) -> bool:
    """
    Refreshes JWT for a single account if needed.

    Args:
        account_name (str): The name of the account to refresh.
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            Defaults to None, using the system default path.
        forced (bool, optional): If True, forces refresh of the access token regardless of
            expiration status. Defaults to False.

    Returns:
        bool: Returns True if refresh is successful or not needed; returns False on failure.
    """
    config_path = resolve_config_path(config_path)

    config = load_config(config_path)
    if not config:
        return False

    # Check if account exists
    if account_name not in config["accounts"]:
        logger.error("Account '%s' not found in configuration", account_name)
        return False

    account_data = config["accounts"][account_name]

    # A JWT token requires both an auth_token and a license_id
    id_token = account_data.get("id_token", "N/A")
    license_id = account_data.get("license_id", "N/A")

    current_access_token = account_data.get("access_token", "N/A")

    if not forced and not is_jwt_expired(current_access_token):
        logger.info(
            "Access token for account '%s' is still valid and does not require renewal.",
            account_name,
        )
        return True

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
    save_result = save_access_tokens(
        config=config, config_path=config_path, updated_accounts=[account_name]
    )

    if not save_result:
        logger.error("Failed to save updated Access token to config file")
        return False

    logger.info("Access token refresh successful for account: %s", account_name)
    return True


def refresh_expired_id_tokens(
    config_path: Optional[Union[str, Path]] = None, forced: bool = False
) -> bool:
    """
    Refreshes ID tokens for all accounts if needed.

    Args:
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            Defaults to None, using the system default path.
        forced (bool, optional): If True, forces refresh of all ID tokens regardless of
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
        # ID token refresh requires a refresh_token
        refresh_token = account_data.get("refresh_token", "N/A")
        if refresh_token == "N/A":
            logger.warning(
                "No refresh_token found for account '%s'. Skipping ID token refresh.",
                account_name,
            )
            continue

        current_id_token = account_data.get("id_token", "N/A")

        if not forced and not is_id_token_expired(current_id_token):
            logger.info(
                "ID token for account '%s' is still valid and does not require renewal.",
                account_name,
            )
            continue

        if forced:
            logger.info(
                "Forced refresh mode: Initiating ID token refresh for account '%s'.",
                account_name,
            )
        else:
            logger.info(
                "ID token for account '%s' is nearing expiration. Initiating refresh.",
                account_name,
            )

        token_data = request_id_token(refresh_token)
        if not token_data:
            logger.error(
                "Failed to refresh the ID token for account '%s'. "
                "Please verify that the refresh token is correct.",
                account_name,
            )
            all_successful = False
            continue

        # Store previous tokens
        if current_id_token != "N/A":
            config["accounts"][account_name]["previous_id_token"] = current_id_token

        # Update tokens from the response
        config["accounts"][account_name]["id_token"] = token_data["id_token"]
        config["accounts"][account_name]["access_token"] = token_data["access_token"]
        config["accounts"][account_name]["refresh_token"] = token_data["refresh_token"]

        # Parse and save the ID token expiration time
        id_expires_at = parse_jwt_expiration(str(token_data["id_token"]))
        if id_expires_at is not None:
            config["accounts"][account_name]["id_token_expires_at"] = id_expires_at
            logger.info("ID token expiration time set for account: %s", account_name)
        else:
            logger.warning("Could not parse ID token expiration time for account: %s", account_name)

        # Parse and save the access token expiration time
        access_expires_at = parse_jwt_expiration(str(token_data["access_token"]))
        if access_expires_at is not None:
            config["accounts"][account_name]["access_token_expires_at"] = access_expires_at
            logger.info("Access token expiration time set for account: %s", account_name)
        else:
            logger.warning(
                "Could not parse Access token expiration time for account: %s", account_name
            )

        config_updated = True
        updated_accounts.append(account_name)
        logger.info("ID token refresh successful for account: %s", account_name)

    # Save the configuration file if any account has been updated
    if config_updated:
        save_result = save_id_tokens(
            config=config, config_path=config_path, updated_accounts=updated_accounts
        )

        if not save_result:
            logger.error("Failed to save updated ID tokens to config file")
            all_successful = False

    return all_successful


def refresh_expired_id_token(
    account_name: str, config_path: Optional[Union[str, Path]] = None, forced: bool = False
) -> bool:
    """
    Refreshes ID token for a single account if needed.

    Args:
        account_name (str): The name of the account to refresh.
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            Defaults to None, using the system default path.
        forced (bool, optional): If True, forces refresh of the ID token regardless of
            expiration status. Defaults to False.

    Returns:
        bool: Returns True if refresh is successful or not needed; returns False on failure.
    """
    config_path = resolve_config_path(config_path)

    config = load_config(config_path)
    if not config:
        return False

    # Check if account exists
    if account_name not in config["accounts"]:
        logger.error("Account '%s' not found in configuration", account_name)
        return False

    account_data = config["accounts"][account_name]

    # ID token refresh requires a refresh_token
    refresh_token = account_data.get("refresh_token", "N/A")
    if refresh_token == "N/A":
        logger.error(
            "No refresh_token found for account '%s'. Cannot refresh ID token.",
            account_name,
        )
        return False

    current_id_token = account_data.get("id_token", "N/A")

    if not forced and not is_id_token_expired(current_id_token):
        logger.info(
            "ID token for account '%s' is still valid and does not require renewal.",
            account_name,
        )
        return True

    if forced:
        logger.info(
            "Forced refresh mode: Initiating ID token refresh for account '%s'.",
            account_name,
        )
    else:
        logger.info(
            "ID token for account '%s' is nearing expiration. Initiating refresh.",
            account_name,
        )

    token_data = request_id_token(refresh_token)
    if not token_data:
        logger.error(
            "Failed to refresh the ID token for account '%s'. "
            "Please verify that the refresh token is correct.",
            account_name,
        )
        return False

    # Store previous tokens
    if current_id_token != "N/A":
        config["accounts"][account_name]["previous_id_token"] = current_id_token

    # Update tokens from the response
    config["accounts"][account_name]["id_token"] = token_data["id_token"]
    config["accounts"][account_name]["access_token"] = token_data["access_token"]
    config["accounts"][account_name]["refresh_token"] = token_data["refresh_token"]

    # Parse and save the ID token expiration time
    id_expires_at = parse_jwt_expiration(str(token_data["id_token"]))
    if id_expires_at is not None:
        config["accounts"][account_name]["id_token_expires_at"] = id_expires_at
        logger.info("ID token expiration time set for account: %s", account_name)
    else:
        logger.warning("Could not parse ID token expiration time for account: %s", account_name)

    # Parse and save the access token expiration time
    access_expires_at = parse_jwt_expiration(str(token_data["access_token"]))
    if access_expires_at is not None:
        config["accounts"][account_name]["access_token_expires_at"] = access_expires_at
        logger.info("Access token expiration time set for account: %s", account_name)
    else:
        logger.warning("Could not parse Access token expiration time for account: %s", account_name)

    # Save the configuration file
    save_result = save_id_tokens(
        config=config, config_path=config_path, updated_accounts=[account_name]
    )

    if not save_result:
        logger.error("Failed to save updated ID token to config file")
        return False

    logger.info("ID token refresh successful for account: %s", account_name)
    return True


def check_quota_remaining(config_path: Optional[Union[str, Path]] = None) -> bool:
    """
    Check the remaining quota for all accounts' access tokens.

    Args:
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            Defaults to None, using the system default path.

    Returns:
        bool: Returns True if all quota checks are successful or not needed; returns False on failure.
    """
    config_path = resolve_config_path(config_path)

    config = load_config(config_path)
    if not config:
        logger.error("Failed to load configuration")
        return False

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
        save_result = save_quota_info(config, account_name, quota_info, config_path)
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
