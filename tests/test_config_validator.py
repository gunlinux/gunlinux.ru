"""Unit tests for the configuration validator."""

import pytest
import os

from blog.config_validator import (
    validate_config,
    validate_required_configs,
    validate_environment_specific_configs,
    ConfigValidationError,
)


def test_validate_config_valid_secret_key():
    """Test that validate_config accepts a valid SECRET_KEY."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }

    # Should not raise an exception
    warnings = validate_config(config)
    assert isinstance(warnings, list)


def test_validate_config_default_secret_key_warning():
    """Test that validate_config warns about default SECRET_KEY."""
    config = {
        "SECRET_KEY": "hard to guess string",  # Default value
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }

    warnings = validate_config(config)
    assert len(warnings) >= 1
    assert any("SECRET_KEY" in warning for warning in warnings)


def test_validate_config_missing_secret_key():
    """Test that validate_config raises an error for missing SECRET_KEY."""

    os.environ["FLASK_ENV"] = "production"
    config = {
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }

    with pytest.raises(ConfigValidationError, match="SECRET_KEY is required"):
        validate_config(config)


def test_validate_config_invalid_database_uri():
    """Test that validate_config handles invalid database URIs."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "SQLALCHEMY_DATABASE_URI": 123,  # Invalid type
    }

    with pytest.raises(ConfigValidationError, match="must be a string"):
        validate_config(config)


def test_validate_config_uncommon_database_uri():
    """Test that validate_config warns about uncommon database URIs."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "SQLALCHEMY_DATABASE_URI": "mongodb://localhost/mydb",  # Uncommon scheme
    }

    warnings = validate_config(config)
    assert any("uncommon scheme" in warning for warning in warnings)


def test_validate_config_missing_database_uri():
    """Test that validate_config warns about missing database URI."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
    }

    warnings = validate_config(config)
    assert any("SQLALCHEMY_DATABASE_URI" in warning for warning in warnings)


def test_validate_config_invalid_port():
    """Test that validate_config handles invalid ports."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "PORT": "invalid-port",
    }

    with pytest.raises(ConfigValidationError, match="PORT must be a valid integer"):
        validate_config(config)


def test_validate_config_port_out_of_range():
    """Test that validate_config handles ports out of range."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "PORT": "99999",  # Too high
    }

    with pytest.raises(ConfigValidationError, match="PORT must be between 1 and 65535"):
        validate_config(config)


def test_validate_config_valid_port():
    """Test that validate_config accepts valid ports."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "PORT": "8080",
    }

    # Should not raise an exception
    warnings = validate_config(config)
    assert isinstance(warnings, list)


def test_validate_config_invalid_page_category():
    """Test that validate_config handles invalid PAGE_CATEGORY."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "PAGE_CATEGORY": "not-a-list",  # Invalid type
    }

    with pytest.raises(ConfigValidationError, match="PAGE_CATEGORY must be a list"):
        validate_config(config)


def test_validate_config_invalid_page_category_items():
    """Test that validate_config handles invalid PAGE_CATEGORY items."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "PAGE_CATEGORY": ["not-an-int"],  # Invalid items
    }

    with pytest.raises(
        ConfigValidationError, match="PAGE_CATEGORY must contain only integers"
    ):
        validate_config(config)


def test_validate_config_valid_page_category():
    """Test that validate_config accepts valid PAGE_CATEGORY."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "PAGE_CATEGORY": [1, 2, 3],
    }

    # Should not raise an exception
    warnings = validate_config(config)
    assert isinstance(warnings, list)


def test_validate_config_nullcache_in_production():
    """Test that validate_config warns about NullCache in production."""
    # Temporarily set environment
    old_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "production"

    try:
        config = {
            "SECRET_KEY": "a-valid-secret-key",
            "CACHE_TYPE": "NullCache",  # Should warn in production
        }

        warnings = validate_config(config)
        assert any("NullCache" in warning for warning in warnings)
    finally:
        # Restore environment
        if old_env is not None:
            os.environ["FLASK_ENV"] = old_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]


def test_validate_required_configs_all_present():
    """Test that validate_required_configs passes when all required configs are present."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "REQUIRED_CONFIG": "value",
    }

    # Should not raise an exception
    validate_required_configs(
        config, ["SECRET_KEY", "SQLALCHEMY_DATABASE_URI", "REQUIRED_CONFIG"]
    )


def test_validate_required_configs_missing():
    """Test that validate_required_configs raises an error when configs are missing."""
    config = {
        "SECRET_KEY": "a-valid-secret-key",
    }

    with pytest.raises(
        ConfigValidationError, match="Missing required configuration keys"
    ):
        validate_required_configs(
            config, ["SECRET_KEY", "SQLALCHEMY_DATABASE_URI", "REQUIRED_CONFIG"]
        )


def test_validate_environment_specific_configs_development_debug():
    """Test that validate_environment_specific_configs handles development environment."""
    # Temporarily set environment
    old_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "development"

    try:
        config = {
            "DEBUG": True,
        }

        warnings = validate_environment_specific_configs(config)
        # No warnings expected for development environment with debug
        assert isinstance(warnings, list)
    finally:
        # Restore environment
        if old_env is not None:
            os.environ["FLASK_ENV"] = old_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]


def test_validate_environment_specific_configs_production_debug():
    """Test that validate_environment_specific_configs warns about debug in production."""
    # Temporarily set environment
    old_env = os.environ.get("FLASK_ENV")
    os.environ["FLASK_ENV"] = "production"

    try:
        config = {
            "DEBUG": True,
        }

        warnings = validate_environment_specific_configs(config)
        assert any("DEBUG mode is enabled" in warning for warning in warnings)
    finally:
        # Restore environment
        if old_env is not None:
            os.environ["FLASK_ENV"] = old_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]
