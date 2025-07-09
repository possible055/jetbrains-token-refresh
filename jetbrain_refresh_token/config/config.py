import json
from pathlib import Path
from typing import Dict, Optional, Union

from jsonschema import ValidationError, validate

from jetbrain_refresh_token.config import logger
from jetbrain_refresh_token.config.utils import is_vaild_jwt_format, parse_jwt_expiration
from jetbrain_refresh_token.constants import CONFIG_PATH, SCHEMA_PATH


def resolve_config_path(config_path: Optional[Union[str, Path]] = None) -> Path:
    """
    Parse the configuration path parameter into a standardized Path object.

    Args:
        config_path (Optional[Union[str, Path]], optional): The path to the configuration file.
            If None, the default path will be used.

    Returns:
        Path: A standardized Path object for the configuration file.
    """

    if config_path is None:
        logger.info("Using default configuration path: %s", CONFIG_PATH)
        return CONFIG_PATH
    if isinstance(config_path, str):
        path_obj = Path(config_path)
        logger.info("Using custom configuration path (converted from string): %s", path_obj)
        return path_obj
    logger.info("Using custom configuration path: %s", config_path)
    return config_path


def load_config(config_path: Optional[Union[str, Path]] = None) -> Optional[Dict]:
    """
    Load configuration from a JSON file.

    If `config_path` is None, the default config location will be used.

    Args:
        config_path (Union[str, Path], optional): Path to the configuration file.
            If None, uses default config.json in config directory.

    Returns:
        Optional[Dict]: Configuration dictionary on success; None if file system errors occur.

    Raises:
        RuntimeError: If the configuration schema cannot be loaded.
        ValueError: If the configuration format is invalid or JWT format is invalid.
    """
    config_path = resolve_config_path(config_path)

    try:
        with config_path.open('r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", config_path)
        return None
    except json.JSONDecodeError as e:
        logger.error("Failed to parse configuration file: %s", e)
        return None
    except OSError as e:
        logger.error("OS error accessing configuration: %s", e)
        return None

    # Validate configuration format using comprehensive validation
    # This will raise ValueError for format errors, RuntimeError for schema loading errors
    validate_config_format(config)

    return config


def load_config_schema() -> Optional[Dict]:
    """
    Load configuration schema from JSON file.

    Returns:
        Optional[Dict]: Schema dictionary on success; otherwise, None.
    """
    schema_path = SCHEMA_PATH

    try:
        with schema_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Configuration schema file not found: %s", schema_path)
        return None
    except json.JSONDecodeError as e:
        logger.error("Failed to parse configuration schema file: %s", e)
        return None
    except OSError as e:
        logger.error("OS error accessing configuration schema: %s", e)
        return None


def validate_config_format(config: Dict) -> None:
    """
    Validate the format of configuration file fields.

    Args:
        config (Dict): Configuration dictionary that has been loaded.

    Raises:
        RuntimeError: If the configuration schema cannot be loaded.
        ValueError: If the configuration format is invalid or JWT format is invalid.
    """
    # Load and validate using JSON Schema
    schema = load_config_schema()
    if schema is None:
        logger.error("Failed to load configuration schema")
        raise RuntimeError("Failed to load configuration schema")

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
            ("previous_access_token", True),
            ("previous_id_token", True),
        ]

        for field, allow_empty in jwt_validations:
            if field in account_data:
                value = account_data[field]

                # Check for empty string
                if not allow_empty and not value:
                    logger.error("Account '%s' field '%s' cannot be empty", account_name, field)
                    raise ValueError(f"Account '{account_name}' field '{field}' cannot be empty")

                # Check for valid JWT format (skip JWT format check for previous_access_token)
                if value and field != "previous_access_token" and not is_vaild_jwt_format(value):
                    logger.error(
                        "Account '%s' field '%s' has invalid JWT format", account_name, field
                    )
                    raise ValueError(
                        f"Account '{account_name}' field '{field}' has invalid JWT format"
                    )
