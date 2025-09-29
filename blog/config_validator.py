"""Configuration validation module."""

import logging
import os
from typing import Any, cast

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


def validate_config(config: dict[str, Any]) -> list[str]:  # pyright: ignore[reportExplicitAny]
    """Validate the application configuration.

    Args:
        config: The configuration dictionary to validate

    Returns:
        list of validation warnings (non-fatal issues)

    Raises:
        ConfigValidationError: If critical configuration is missing or invalid
    """
    warnings: list[str] = []

    # Validate SECRET_KEY
    secret_key = config.get("SECRET_KEY")
    if not secret_key:
        raise ConfigValidationError(
            "SECRET_KEY is required but not set. "
            + "Set the SECRET_KEY environment variable."
        )
    elif secret_key == "hard to guess string":
        warnings.append(
            "Using default SECRET_KEY. "
            + "For production, set a strong SECRET_KEY environment variable."
        )

    # Validate SQLALCHEMY_DATABASE_URI
    db_uri = config.get("SQLALCHEMY_DATABASE_URI")
    if not db_uri:
        warnings.append(
            "SQLALCHEMY_DATABASE_URI is not set. "
            + "Using default database URI which may not be suitable for production."
        )
    else:
        # Basic validation of database URI
        if not isinstance(db_uri, str):
            raise ConfigValidationError("SQLALCHEMY_DATABASE_URI must be a string")

        # Check for common database URI prefixes
        valid_schemes = ("sqlite://", "postgresql://", "mysql://", "oracle://")
        if not any(db_uri.startswith(scheme) for scheme in valid_schemes):
            warnings.append(
                f"SQLALCHEMY_DATABASE_URI '{db_uri}' uses an uncommon scheme. "
                + "Supported schemes: sqlite://, postgresql://, mysql://, oracle://"
            )

    # Validate PAGE_CATEGORY
    page_category = config.get("PAGE_CATEGORY")
    print(page_category, type(page_category))
    if page_category is not None:
        if not isinstance(page_category, list):
            raise ConfigValidationError("PAGE_CATEGORY must be a list of integers")
        for item in cast("list[Any]", page_category):  # pyright: ignore[reportExplicitAny]
            if not isinstance(item, int):
                raise ConfigValidationError("PAGE_CATEGORY must contain only integers")

    # Validate PORT
    port = config.get("PORT")
    if port:
        try:
            port_int = int(port)
            if port_int <= 0 or port_int > 65535:
                raise ConfigValidationError(
                    f"PORT must be between 1 and 65535, got {port_int}"
                )
        except ValueError:
            raise ConfigValidationError(f"PORT must be a valid integer, got '{port}'")

    # Validate CACHE settings for production
    env = os.environ.get("FLASK_ENV", "development")
    if env == "production":
        cache_type = config.get("CACHE_TYPE", "NullCache")
        if cache_type == "NullCache":
            warnings.append(
                "Using NullCache in production. "
                + "Consider using a proper cache implementation for better performance."
            )

    logger.info("Configuration validation completed with %d warnings", len(warnings))
    return warnings


def validate_required_configs(config: dict[str, Any], required_keys: list[str]) -> None:  # pyright: ignore[reportExplicitAny]
    """Validate that all required configuration keys are present.

    Args:
        config: The configuration dictionary to validate
        required_keys: list of required configuration keys

    Raises:
        ConfigValidationError: If any required configuration is missing
    """
    missing_keys: list[str] = []
    for key in required_keys:
        if key not in config or config[key] is None:
            missing_keys.append(key)

    if missing_keys:
        raise ConfigValidationError(
            f"Missing required configuration keys: {', '.join(missing_keys)}. "
            + "Set these environment variables or check your configuration."
        )


def validate_environment_specific_configs(config: dict[str, Any]) -> list[str]:  # pyright: ignore[reportExplicitAny]
    """Validate environment-specific configurations.

    Args:
        config: The configuration dictionary to validate

    Returns:
        list of validation warnings
    """
    warnings: list[str] = []
    env = os.environ.get("FLASK_ENV", "development")

    if env == "production":
        # Additional validations for production environment
        if config.get("DEBUG", False):
            warnings.append(
                "DEBUG mode is enabled in production. "
                + "Disable DEBUG mode for security reasons."
            )

        if config.get("TESTING", False):
            warnings.append(
                "TESTING mode is enabled in production. "
                + "Disable TESTING mode for security reasons."
            )

    elif env == "testing":
        # Validations for testing environment
        pass

    elif env == "development":
        # Validations for development environment
        pass

    return warnings
