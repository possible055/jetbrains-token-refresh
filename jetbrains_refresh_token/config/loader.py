import json
from typing import Dict, Optional

from jsonschema import ValidationError, validate

from jetbrains_refresh_token.config import logger
from jetbrains_refresh_token.config.utils import is_valid_jwt_format
from jetbrains_refresh_token.constants import CONFIG_PATH, SCHEMA_PATH


def load_config() -> Dict:
    """
    Load configuration from a JSON file.

    Returns:
        Dict: Configuration dictionary on success.

    Raises:
        FileNotFoundError: When configuration file is not found.
        json.JSONDecodeError: When configuration file contains invalid JSON.
    """
    try:
        with CONFIG_PATH.open('r', encoding='utf-8') as f:
            config = json.load(f)

        validate_config_format(config)
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", CONFIG_PATH)
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse configuration file: %s", e)
        raise

    return config


def load_config_schema() -> Dict:
    """
    Load configuration schema from JSON file.

    Returns:
        Dict: Schema dictionary on success.

    Raises:
        FileNotFoundError: When schema file is not found.
        json.JSONDecodeError: When schema file contains invalid JSON.
    """
    try:
        with SCHEMA_PATH.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Configuration schema file not found: %s", SCHEMA_PATH)
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse configuration schema: %s", e)
        raise


def validate_config_format(config: Dict) -> None:
    """
    Validate the format of configuration file fields.

    Args:
        config (Dict): Configuration dictionary that has been loaded.

    Raises:
        ValueError: If the configuration format is invalid or JWT format is invalid.
    """
    # Load and validate using JSON Schema
    schema = load_config_schema()

    try:
        validate(instance=config, schema=schema)
        logger.info("Configuration format is valid based on the schema.")
    except ValidationError as e:
        logger.error("Schema validation failed: %s", e.message)
        logger.error("Failed on instance path: /%s", "/".join(map(str, e.path)))
        raise ValueError(f"Schema validation failed: {e.message}") from e

    # Additional JWT format validation (only what schema cannot handle)
    for account_name, account_data in config["accounts"].items():
        jwt_validations = [
            ("id_token", True),
            ("access_token", True),
        ]

        for field, allow_empty in jwt_validations:
            if field in account_data:
                value = account_data[field]

                # Check for empty string
                if not allow_empty and not value:
                    logger.error("Account '%s' field '%s' cannot be empty", account_name, field)
                    raise ValueError(f"Account '{account_name}' field '{field}' cannot be empty")

                # Check for valid JWT format when value is not empty
                if value and not is_valid_jwt_format(value):
                    logger.error(
                        "Account '%s' field '%s' has invalid JWT format", account_name, field
                    )
                    raise ValueError(
                        f"Account '{account_name}' field '{field}' has invalid JWT format"
                    )
