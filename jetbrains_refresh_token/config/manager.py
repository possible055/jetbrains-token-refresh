import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from jetbrains_refresh_token.config import logger
from jetbrains_refresh_token.config.loader import (
    load_config,
    resolve_config_path,
)
from jetbrains_refresh_token.constants import CONFIG_BACKUP_PATH


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
        "quota_info",
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
                elif field == "quota_info" and isinstance(value, dict):
                    print(f"{field}:")
                    print(f"  Remaining: {value.get('remaining_amount', 'N/A')}")
                    print(f"  Usage: {value.get('usage_percentage', 0):.1f}%")
                    print(f"  Status: {value.get('status', 'unknown')}")
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


def export_to_jetbrainsai_format(
    config_path: Optional[Union[str, Path]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Export configuration to jetbrainsai.json format for external package compatibility.

    Converts from internal format:
    {
      "accounts": {
        "account_name": {
          "access_token": "...",
          "id_token": "...",
          "license_id": "..."
        }
      }
    }

    To external format:
    [
      {
        "jwt": "access_token_value",
        "licenseId": "license_id_value",
        "authorization": "id_token_value"
      }
    ]

    Args:
        config_path (Optional[Union[str, Path]]): Path to the source configuration file.
            If None, uses default config location.
        output_path (Optional[Union[str, Path]]): Path for the output jetbrainsai.json file.
            If None, uses 'jetbrainsai.json' in the same directory as config.

    Returns:
        bool: True if export succeeds, False otherwise.
    """
    try:
        # Load the current configuration
        config = load_config(config_path)
        if not config or "accounts" not in config:
            logger.error("No valid configuration found or no accounts in config")
            return False

        # Determine output path
        if output_path is None:
            config_path_resolved = resolve_config_path(config_path)
            output_path = config_path_resolved.parent / "jetbrainsai.json"
        else:
            output_path = Path(output_path)

        # Convert to jetbrainsai format
        jetbrainsai_data = []

        for account_name, account_data in config["accounts"].items():
            # Extract required fields
            access_token = account_data.get("access_token", "")
            id_token = account_data.get("id_token", "")
            license_id = account_data.get("license_id", "")

            # Validate required fields
            if not access_token:
                logger.warning("Account '%s' missing access_token, skipping", account_name)
                continue
            if not license_id:
                logger.warning("Account '%s' missing license_id, skipping", account_name)
                continue
            if not id_token:
                logger.warning("Account '%s' missing id_token, skipping", account_name)
                continue

            # Create jetbrainsai format entry
            jetbrainsai_entry = {
                "jwt": access_token,
                "licenseId": license_id,
                "authorization": id_token,
            }

            jetbrainsai_data.append(jetbrainsai_entry)
            logger.debug("Converted account '%s' to jetbrainsai format", account_name)

        if not jetbrainsai_data:
            logger.error("No valid accounts found to export")
            return False

        # Write to jetbrainsai.json
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(jetbrainsai_data, file, indent=2)

        logger.info(
            "Successfully exported %d account(s) to jetbrainsai format: %s",
            len(jetbrainsai_data),
            output_path,
        )
        return True

    except Exception as e:
        logger.error("Failed to export to jetbrainsai format: %s", e)
        return False


def save_quota_info(
    config: Dict,
    account_name: str,
    quota_data: Dict,
    config_path: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Save quota information for a specific account to the configuration file.

    Args:
        account_name (str): The name of the account to save quota info for.
        quota_data (Dict): The quota information to save.
        config_path (Optional[Union[str, Path]], optional): Path to the configuration file.
            If None, uses default config location.

    Returns:
        bool: True if successful, False otherwise.
    """
    config_path = resolve_config_path(config_path)

    try:
        # Process quota data to extract key information
        current_data = quota_data.get('current', {})
        if current_data:
            maximum_amount = current_data.get('maximum', {}).get('amount', 'N/A')
            current_amount = current_data.get('current', {}).get('amount', 'N/A')

            # Calculate remaining amount and usage percentage
            remaining_amount = 'N/A'
            usage_percentage = 0.0
            status = 'unknown'

            try:
                if current_amount != 'N/A' and maximum_amount != 'N/A':
                    current_float = float(current_amount.rstrip('.'))
                    maximum_float = float(maximum_amount.rstrip('.'))
                    remaining_float = maximum_float - current_float
                    remaining_amount = str(remaining_float)
                    usage_percentage = (current_float / maximum_float) * 100

                    # Determine status based on usage percentage
                    if usage_percentage > 90:
                        status = 'critical'
                    elif usage_percentage > 80:
                        status = 'warning'
                    else:
                        status = 'normal'
            except (ValueError, TypeError, ZeroDivisionError):
                logger.warning(
                    "Could not calculate quota statistics for account '%s'", account_name
                )

            # Save quota information to config (simplified structure)
            quota_info = {
                'remaining_amount': remaining_amount,
                'usage_percentage': usage_percentage,
                'status': status,
            }

            config["accounts"][account_name]["quota_info"] = quota_info
            logger.info("Quota information processed for account '%s'", account_name)
        else:
            logger.warning("No current quota data found for account '%s'", account_name)
            return False

        # Backup the configuration file before making changes
        backup_result = backup_config_file(config_path)
        if not backup_result:
            logger.warning("Failed to back up config file, but will continue with save operation")

        # Write back to file
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=2)

        logger.info("Successfully saved quota information for account: %s", account_name)
        return True
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("Failed to save quota information for account '%s': %s", account_name, e)
        return False
