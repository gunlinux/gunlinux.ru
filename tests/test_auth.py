"""Unit tests for the authentication adapter."""

import pytest
import os

from blog import create_app
from blog.extensions import db
from blog.domain.user import User as UserDomain
from blog.auth.adapter import AuthenticationAdapter
from blog.user.models import User as UserORM
from blog.services.factory import ServiceFactory


@pytest.fixture()
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def auth_adapter(app):
    """Create an AuthenticationAdapter instance for testing."""
    return AuthenticationAdapter()


@pytest.fixture()
def user_service(app):
    """Create a UserService instance for testing."""
    return ServiceFactory.create_user_service()


class TestAuthenticationAdapter:
    """Test cases for AuthenticationAdapter."""

    def test_load_user_existing_user(self, app, auth_adapter, user_service):
        """Test loading an existing user by ID."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user_domain)

            # Set the password properly
            user_orm = db.session.get(UserORM, created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Load the user using the adapter
            loaded_user = auth_adapter.load_user(created_user.id)

            # Verify the user was loaded correctly
            assert loaded_user is not None
            assert loaded_user.id == created_user.id
            assert loaded_user.name == "testuser"

    def test_load_user_nonexistent_user(self, app, auth_adapter):
        """Test loading a nonexistent user by ID."""
        with app.app_context():
            # Try to load a user that doesn't exist
            loaded_user = auth_adapter.load_user(99999)

            # Verify None is returned
            assert loaded_user is None

    def test_authenticate_and_login_valid_credentials(
        self, app, auth_adapter, user_service
    ):
        """Test authenticating with valid credentials."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user_domain)

            # Set the password properly
            user_orm = db.session.get(UserORM, created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Authenticate the user using the adapter
            authenticated_user = auth_adapter.authenticate_and_login(
                "testuser", "testpassword"
            )

            # Verify the user was authenticated correctly
            assert authenticated_user is not None
            assert authenticated_user.id == created_user.id
            assert authenticated_user.name == "testuser"

    def test_authenticate_and_login_invalid_credentials(
        self, app, auth_adapter, user_service
    ):
        """Test authenticating with invalid credentials."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user_domain)

            # Set the password properly
            user_orm = db.session.get(UserORM, created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Try to authenticate with wrong password
            authenticated_user = auth_adapter.authenticate_and_login(
                "testuser", "wrongpassword"
            )

            # Verify None is returned
            assert authenticated_user is None

    def test_authenticate_and_login_nonexistent_user(self, app, auth_adapter):
        """Test authenticating a nonexistent user."""
        with app.app_context():
            # Try to authenticate a user that doesn't exist
            authenticated_user = auth_adapter.authenticate_and_login(
                "nonexistent", "password"
            )

            # Verify None is returned
            assert authenticated_user is None

    def test_to_flask_login_user_conversion(self, app, auth_adapter, user_service):
        """Test converting User ORM model to FlaskLoginUser."""
        with app.app_context():
            # Create a user first
            user_domain = UserDomain(name="testuser", password="testpassword")
            created_user = user_service.create_user(user_domain)

            # Set the password properly
            user_orm = db.session.get(UserORM, created_user.id)
            if user_orm:
                user_orm.set_password("testpassword")
                db.session.commit()

            # Get the ORM model directly from the database
            user_orm = db.session.get(UserORM, created_user.id)
            assert user_orm is not None

            # Convert to FlaskLoginUser
            flask_login_user = auth_adapter._to_flask_login_user(user_orm)

            # Verify the conversion was correct
            assert flask_login_user.id == user_orm.id
            assert flask_login_user.name == user_orm.name
            assert flask_login_user.password == user_orm.password
            assert flask_login_user.authenticated == user_orm.authenticated
