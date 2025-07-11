import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from jetbrains_refresh_token.config import logger
from jetbrains_refresh_token.config.loader import load_config
from jetbrains_refresh_token.constants import (
    COMPATIBLE_CONFIG_PATH,
    CONFIG_BACKUP_PATH,
    CONFIG_PATH,
)


def backup_config_file() -> bool:
    try:
        shutil.copy2(CONFIG_PATH, CONFIG_BACKUP_PATH)
        logger.info("Successfully backed up the configuration file to: %s", CONFIG_BACKUP_PATH)
        return True
    except (PermissionError, OSError) as e:
        logger.error("File system error occurred while backing up the configuration file: %s", e)
        return False


def list_accounts() -> List[str]:
    config = load_config()
    if not config:
        return []

    return list(config["accounts"].keys())


def list_accounts_data() -> None:
    """
    Print all account data from the configuration file in a bullet-point format.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, the default configuration location will be used.
    """
    config = load_config()
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
    updated_accounts: Optional[list] = None,
) -> None:
    """
    Save or update multiple accounts' tokens in the configuration file.

    Args:
        config (Dict): Configuration dictionary that has been loaded.
        updated_accounts (Optional[list], optional): List of account names that were updated.
            If None, assumes all accounts in config need to be saved.

    Returns:
        None
    """
    try:
        backup_config_file()
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.warning("Failed to back up config file: %s. Continuing with save operation.", e)

    with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=2)

    if updated_accounts:
        accounts_str = ", ".join(updated_accounts)
        logger.info("Successfully saved tokens for accounts: %s", accounts_str)
    else:
        logger.info("Successfully saved all account tokens to config file")

    try:
        export_to_another_format()
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.warning("Failed to export to another format: %s", e)


def export_to_another_format() -> bool:
    """
    Export configuration to jetbrainsai.json format for external package compatibility.

    Returns:
        bool: True if export succeeds, False otherwise.
    """

    config = load_config()
    external_config = []

    for account_name, account_data in config["accounts"].items():
        if not isinstance(account_data, dict):
            continue

        access_token = account_data.get("access_token")
        id_token = account_data.get("id_token")
        license_id = account_data.get("license_id")

        if all([access_token, id_token, license_id]):
            external_config.append(
                {"jwt": access_token, "licenseId": license_id, "authorization": id_token}
            )

        with open(COMPATIBLE_CONFIG_PATH, 'w', encoding='utf-8') as file:
            json.dump(external_config, file, indent=2, ensure_ascii=False)

        logger.info(
            "Successfully exported %d account(s) to jetbrainsai format: %s",
            len(external_config),
            COMPATIBLE_CONFIG_PATH,
        )
        return True

    return False


def save_quota_info(
    config: Dict,
    account_name: str,
    quota_data: Dict,
) -> bool:
    """
    Save quota information for a specific account to the configuration file.

    Args:
        config (Dict): Configuration dictionary that has been loaded.
        account_name (str): The name of the account to save quota info for.
        quota_data (Dict): The quota information to save.

    Returns:
        bool: True if successful, False otherwise.
    """
    # Backup the configuration file before making changes
    backup_result = backup_config_file()
    if not backup_result:
        logger.warning("Failed to back up config file, but will continue with save operation")

    try:
        # Process quota data to extract key information
        current_data = quota_data.get('current', {})
    except ValueError:
        logger.warning("No current quota data found for account '%s'", account_name)
        return False

    maximum_amount = current_data.get('maximum').get('amount')
    current_amount = current_data.get('current').get('amount')

    # Calculate remaining amount and usage percentage
    remaining_amount = 'N/A'
    usage_percentage = 0.0
    status = 'unknown'

    try:
        if current_amount != 'N/A' and maximum_amount != 'N/A':
            remaining_amount = str(
                float(maximum_amount.rstrip('.')) - float(current_amount.rstrip('.'))
            )
            usage_percentage = (
                float(current_amount.rstrip('.')) / float(maximum_amount.rstrip('.'))
            ) * 100

            # Determine status based on usage percentage
            if usage_percentage > 95:
                status = 'critical'
            elif usage_percentage > 80:
                status = 'warning'
            else:
                status = 'normal'
    except (ValueError, TypeError, ZeroDivisionError):
        logger.warning("Could not calculate quota statistics for account '%s'", account_name)
        return False

    # Save quota information to config (simplified structure)
    quota_info = {
        'remaining_amount': remaining_amount,
        'usage_percentage': usage_percentage,
        'status': status,
    }

    config["accounts"][account_name]["quota_info"] = quota_info
    logger.info("Quota information processed for account '%s'", account_name)

    with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=2)

    logger.info("Successfully saved quota information for account: %s", account_name)

    # Auto-export to jetbrainsai.json format after saving quota info
    if export_to_another_format():
        logger.info("Successfully exported quota information to jetbrainsai format")
        return True

    return False
