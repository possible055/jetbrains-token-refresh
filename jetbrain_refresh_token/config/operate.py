import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from jsonschema import ValidationError, validate

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.config import (
    load_config,
    load_config_schema,
    resolve_config_path,
)
from jetbrain_refresh_token.config.utils import is_vaild_jwt_format
from jetbrain_refresh_token.constants import CONFIG_BACKUP_PATH


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


def validate_config_format(config: Dict) -> bool:
    """
    Validate the format of configuration file fields.

    Args:
        config (Dict): Configuration dictionary that has been loaded.

    Returns:
        bool: True if the configuration format is valid, False otherwise.
    """
    # Load and validate using JSON Schema
    schema = load_config_schema()
    if schema is None:
        logger.error("Failed to load configuration schema")
        return False

    try:
        validate(instance=config, schema=schema)
        logger.info("Configuration format is valid based on the schema.")
    except ValidationError as e:
        logger.error("Schema validation failed: %s", e.message)
        logger.error("Failed on instance path: /%s", "/".join(map(str, e.path)))
        return False

    # Additional JWT format validation (only what schema cannot handle)
    for account_name, account_data in config["accounts"].items():
        # Validate JWT fields that require format checking
        jwt_fields = ["id_token", "access_token", "previous_access_token"]
        for field in jwt_fields:
            if field in account_data:
                value = account_data[field]
                # previous_access_token can be empty string
                if field == "previous_access_token":
                    if value and not is_vaild_jwt_format(value):
                        logger.error(
                            "Account '%s' field '%s' has invalid JWT format", account_name, field
                        )
                        return False
                else:
                    # id_token and access_token must be valid JWT
                    if not value or not is_vaild_jwt_format(value):
                        logger.error(
                            "Account '%s' field '%s' has invalid JWT format", account_name, field
                        )
                        return False

        # Check for required expiration fields (one of them should exist)
        if not account_data.get("access_token_expires_at") and not account_data.get(
            "auth_token_expired"
        ):
            logger.error(
                "Account '%s' must have either 'access_token_expires_at' field",
                account_name,
            )
            return False

    return True


def list_accounts(config_path: Optional[Union[str, Path]] = None) -> List[str]:
    """
    List all accounts in the configuration.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, uses default config location.

    Returns:
        List[str]: A list of account names.
    """
    # 直接使用 load_config，它內部已使用 resolve_config_path
    config = load_config(config_path)
    if not config:
        return []

    return list(config["accounts"].keys())


def list_accounts_data(config_path: Optional[Union[str, Path]] = None) -> None:
    """
    Print all account data from the configuration file in a bullet-point format.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, the default configuration location will be used.
    """
    config = load_config(config_path)
    if not config:
        return

    accounts = config["accounts"]
    fields_order = [
        "id_token",
        "id_token_expires_at",
        "access_token",
        "access_token_expires_at",
        "license_id",
        "created_time",
    ]
    timestamp_fields = ["id_token_expires_at", "access_token_expires_at", "created_time"]

    for account_name, account_data in accounts.items():
        print(f"Account: {account_name}")
        for field in fields_order:
            if field in account_data:
                value = account_data[field]
                if field in timestamp_fields and isinstance(value, (int, float)):
                    date_time = datetime.fromtimestamp(value)
                    print(f"{field}: {date_time.strftime('%Y-%m-%d %H:%M:%S')}")
                elif isinstance(value, str) and len(value) > 40:
                    print(f"{field}: {value[:40]}...")
                else:
                    print(f"{field}: {value}")
        print("-" * 50)


def save_access_tokens(
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
