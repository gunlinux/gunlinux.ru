"""Unit tests for the authentication adapter."""

import pytest

from blog.extensions import db
from blog.domain.user import User as UserDomain
from blog.auth.adapter import AuthenticationAdapter
from blog.repos.user import UserRepository
from blog.user.models import User as UserORM
from blog.services.factory import ServiceFactory


@pytest.fixture()
def auth_adapter(admin_app):
    """Create an AuthenticationAdapter instance for testing."""
    return AuthenticationAdapter()


@pytest.fixture()
def user_service(admin_app):
    """Create a UserService instance for testing."""
    return ServiceFactory.create_user_service()


@pytest.fixture()
def temp_user(admin_app, auth_adapter, user_service):
    """Create a UserService instance for testing."""
    # Create a user first
    user_domain = UserDomain(name="testuser", password="testpassword")

    with admin_app.app_context():
        created_user = user_service.create_user(user_domain)
        user_service.authenticate_user("testuser", "testpassword")

        # Set the password properly
        user_orm = db.session.get(UserORM, created_user.id)
        if user_orm:
            user_orm.set_password("testpassword")
            db.session.commit()

        # Load the user using the adapter
        loaded_user = auth_adapter.load_user(created_user.id)
        assert loaded_user is not None

        return user_orm


@pytest.fixture()
def user_repository(client_admin):
    """Create an IconRepository instance for testing."""
    return UserRepository(db.session)


"""Test cases for AuthenticationAdapter."""


@pytest.fixture()
def authenticated_client(client_admin, temp_user):
    """Create a client that is logged in as the test user."""
    # First, get the login page to extract CSRF token
    login_page_response = client_admin.get("/login")
    content = login_page_response.get_data(as_text=True)

    # Extract the CSRF token using regex
    import re

    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', content)
    csrf_token = csrf_match.group(1) if csrf_match else ""

    # Log in the user using the proper login endpoint with CSRF token
    login_response = client_admin.post(
        "/login",
        data={"name": "testuser", "password": "testpassword", "csrf_token": csrf_token},
        follow_redirects=True,
    )

    # Verify that login was successful
    assert login_response.status_code == 200

    yield client_admin


def test_admin_view(authenticated_client, user_repository):
    """Test that admin views are accessible to authenticated users."""
    # Access the admin page - it should be accessible to authenticated users
    rv = authenticated_client.get("/admin/")
    assert rv.status_code == 200

    links = (
        "admin_user",
        "admin_post",
        "admin_category",
        "admin_tag",
        "admin_icon",
    )
    # check is user auth
    # juser = user_repository.get_by_id(1)
    # assert user is not None

    for link in links:
        url = f"/admin/{link}/"
        rv = authenticated_client.get(url)
        assert rv.status_code == 200

        url = f"/admin/{link}/new/"
        rv = authenticated_client.get(url)
        assert rv.status_code == 200
    rv = authenticated_client.get("/admin/myfileadmin/")
    assert rv.status_code == 200
