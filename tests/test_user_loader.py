"""Tests for Flask-Login user_loader functionality.

This module tests that the user_loader is properly configured
and that user loading works correctly for Flask-Login integration.
"""

import os

import pytest

from blog import create_app
from blog.domain.user import User as UserDomain
from blog.extensions import db, login_manager
from blog.services.factory import ServiceFactory
from blog.user.models import User as UserORM


@pytest.fixture()
def app():
    """Create application for testing."""
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def user_service(app):
    """Create a UserService instance for testing."""
    return ServiceFactory.create_user_service()


class TestUserLoader:
    """Test cases for Flask-Login user_loader functionality."""

    def test_user_loader_function_exists(self, app):
        """Test that user_loader function is registered with login_manager."""
        with app.app_context():
            # Verify that login_manager has a user_loader function registered
            assert login_manager._user_callback is not None, (
                "user_loader function should be registered with login_manager"
            )

    def test_user_loader_loads_existing_user(self, app, user_service):
        """Test that user_loader correctly loads an existing user."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user_domain)

            # Set the password properly
            user_orm = db.session.get(UserORM, created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Call the user_loader function directly
            # The user_loader expects a string ID
            loaded_user = login_manager._user_callback(str(created_user.id))

            # Verify the user was loaded correctly
            assert loaded_user is not None, "User should be loaded successfully"
            assert loaded_user.id == created_user.id
            assert loaded_user.name == "testuser"
            # Verify Flask-Login UserMixin methods work
            assert loaded_user.is_authenticated is True

    def test_user_loader_returns_none_for_nonexistent_user(self, app):
        """Test that user_loader returns None for a nonexistent user."""
        with app.app_context():
            # Try to load a user that doesn't exist
            loaded_user = login_manager._user_callback("99999")

            # Verify None is returned
            assert loaded_user is None

    def test_user_loader_returns_none_for_invalid_id(self, app):
        """Test that user_loader returns None for an invalid ID.

        The user_loader should handle invalid IDs gracefully and return None,
        not raise an exception. This is important for security to prevent
        errors during session tampering attacks.
        """
        with app.app_context():
            # Try to load a user with invalid ID
            # The user_loader should handle invalid IDs gracefully
            loaded_user = login_manager._user_callback("invalid")
            # Should return None, not raise an exception
            assert loaded_user is None, (
                "user_loader should return None for invalid ID, not raise exception"
            )

    def test_user_loader_returns_none_for_empty_string_id(self, app):
        """Test that user_loader returns None for an empty string ID."""
        with app.app_context():
            loaded_user = login_manager._user_callback("")
            assert loaded_user is None, (
                "user_loader should return None for empty string ID"
            )

    def test_user_loader_returns_none_for_float_string_id(self, app):
        """Test that user_loader returns None for a float string ID."""
        with app.app_context():
            loaded_user = login_manager._user_callback("123.45")
            assert loaded_user is None, (
                "user_loader should return None for float string ID"
            )

    def test_user_loader_returns_none_for_negative_id_string(self, app):
        """Test that user_loader returns None for a negative ID string."""
        with app.app_context():
            loaded_user = login_manager._user_callback("-1")
            # Negative IDs should return None (no such user exists)
            assert loaded_user is None

    def test_only_one_user_loader_registered(self, app, user_service):
        """Test that only one user_loader is registered.

        This test ensures we don't have duplicate user_loader decorators,
        which would cause unpredictable behavior.
        """
        with app.app_context():
            # The _user_callback should be set only once
            # If multiple decorators are used, the last one wins
            # We verify this by checking the callback is from auth.adapter

            # Load a test user to verify the callback works
            user_domain = UserDomain(name="testuser2", password="testpassword")
            created_user = user_service.create_user(user_domain)

            user_orm = db.session.get(UserORM, created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            loaded_user = login_manager._user_callback(str(created_user.id))
            assert loaded_user is not None
            # Verify it's using the auth_adapter's load_user method
            # by checking the returned type is FlaskLoginUser
            from blog.auth.adapter import FlaskLoginUser

            assert isinstance(loaded_user, FlaskLoginUser), (
                "user_loader should return FlaskLoginUser instance from auth.adapter"
            )
