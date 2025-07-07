import json
import shutil
from pathlib import Path
from typing import Dict, Optional, Union

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.config import parse_jwt_token_expiration
from jetbrain_refresh_token.constants import CONFIG_BACKUP_PATH, resolve_config_path


def backup_config_file(config_path: Optional[Union[str, Path]] = None) -> bool:
    """
    Back up the configuration file to the default backup location.

    Args:
        config_path (Union[str, Path]): Path to the configuration file to be backed up.

    Returns:
        bool: Returns True if the backup succeeds, False otherwise.
    """
    config_path = resolve_config_path(config_path)

    if not config_path.exists():
        logger.warning(
            "Failed to back up the configuration file; file does not exist: %s", config_path
        )
        return False

    try:
        shutil.copy2(config_path, CONFIG_BACKUP_PATH)
        logger.info("Successfully backed up the configuration file to: %s", CONFIG_BACKUP_PATH)
        return True
    except (PermissionError, OSError) as e:
        logger.error("File system error occurred while backing up the configuration file: %s", e)
        return False


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
    config_path = resolve_config_path(config_path)

    try:
        backup_result = backup_config_file(config_path)
        if not backup_result:
            logger.warning("Failed to back up config file, but will continue with save operation")

        # Process the old JWT token and parse the expiration time
        if account_name in config["accounts"] and "jwt_token" in tokens:
            existing_account = config["accounts"][account_name]
            # Save the original JWT token to the 'jwt_token_previous' field
            if "jwt_token" in existing_account:
                tokens["jwt_token_previous"] = existing_account["jwt_token"]
                logger.info("Previous JWT token saved for account: %s", account_name)
            else:
                # If there is no old JWT token, set 'jwt_token_previous' to an empty string
                tokens["jwt_token_previous"] = ""
                logger.info("No previous JWT token found for account: %s", account_name)

            if "jwt_token" in tokens:
                expires_at = parse_jwt_token_expiration(str(tokens["jwt_token"]))
                if expires_at is not None:
                    tokens["jwt_expired"] = expires_at
                    logger.info("JWT token expiration time set for account: %s", account_name)
                else:
                    logger.warning(
                        "Could not parse JWT expiration time for account: %s", account_name
                    )

        if account_name in config["accounts"]:
            # Update existing account with new tokens and expiration time
            for key, value in tokens.items():
                config["accounts"][account_name][key] = value

        # Write back to file
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2)

        logger.info("Successfully saved tokens for account: %s", account_name)
        return True
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Failed to save account tokens: %s", e)
        return False


def save_multiple_jwt_to_config(
    config: Dict,
    config_path: Optional[Union[str, Path]] = None,
    updated_accounts: Optional[list] = None,
) -> bool:
    """
    Save or update multiple accounts' tokens in the configuration file.

    Args:
        config (Dict): Configuration dictionary that has been loaded.
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            If None, uses default config location.
        updated_accounts (Optional[list], optional): List of account names that were updated.
            If None, assumes all accounts in config need to be saved.

    Returns:
        bool: True if successful, False otherwise.
    """
    config_path = resolve_config_path(config_path)

    try:
        # Backup the configuration file before making changes
        backup_result = backup_config_file(config_path)
        if not backup_result:
            logger.warning("Failed to back up config file, but will continue with save operation")

        # Write back to file
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2)

        # Log which accounts were updated
        if updated_accounts:
            accounts_str = ", ".join(updated_accounts)
            logger.info("Successfully saved tokens for accounts: %s", accounts_str)
        else:
            logger.info("Successfully saved all account tokens to config file")

        return True
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Failed to save account tokens: %s", e)
        return False
