"""Authentication adapter for Flask-Login integration.

This module provides the authentication layer for the Flask-Login integration.
It serves as the bridge between the domain-driven service layer and Flask-Login's
requirements for ORM-based user models.

Authentication Flow
===================

1. User Login (blog/user/views.py::login)
   - User submits credentials via login form
   - View calls auth_adapter.authenticate_and_login(name, password)
   - Adapter authenticates via service layer (domain model)
   - Adapter retrieves ORM model for Flask-Login compatibility
   - Adapter returns FlaskLoginUser instance
   - View calls flask_login.login_user() with the FlaskLoginUser

2. Session Management (Flask-Login internal)
   - Flask-Login stores user ID in session
   - On subsequent requests, Flask-Login loads the user

3. User Loading (this module::load_user)
   - Flask-Login calls @login_manager.user_loader callback
   - This callback (defined below) calls auth_adapter.load_user(user_id)
   - Adapter retrieves user via service layer (domain model)
   - Adapter retrieves ORM model for Flask-Login compatibility
   - Adapter returns FlaskLoginUser instance
   - Flask-Login sets current_user

Architecture
============

The adapter pattern is used here to maintain separation of concerns:

- Domain Layer (blog/domain/): Pure Python models, business logic
- Service Layer (blog/services/): Business operations on domain models
- Adapter Layer (blog/auth/adapter.py): Converts between domain and ORM for Flask-Login
- ORM Layer (blog/user/models.py): SQLAlchemy models for database persistence

Why Only One user_loader?
=========================

Flask-Login uses a single callback function to load users. If multiple functions
are decorated with @login_manager.user_loader, only the LAST one registered will
be used. This can lead to unpredictable behavior depending on import order.

Therefore, the user_loader is defined ONLY in this module (blog/auth/adapter.py),
which is the correct location following the adapter pattern. Other modules
(like blog/user/views.py) should NOT define their own user_loader.

Example::

    # CORRECT: user_loader in auth/adapter.py (this file)
    @login_manager.user_loader
    def load_user(user_id: str):
        return auth_adapter.load_user(int(user_id))

    # INCORRECT: duplicate user_loader in user/views.py (removed)
    # This would cause race conditions and unpredictable behavior

"""

from flask_login import UserMixin

from blog.adapters.factory import ORMAdapterFactory
from blog.extensions import login_manager
from blog.services.factory import ServiceFactory
from blog.user.models import User as UserORM


class FlaskLoginUser(UserORM, UserMixin):
    """Extended User ORM model that includes Flask-Login's UserMixin.

    This class is used specifically for Flask-Login compatibility.
    It inherits from both the User ORM model and Flask-Login's UserMixin.
    """

    pass


class AuthenticationAdapter:
    """Adapter for handling authentication with Flask-Login.

    This adapter handles the conversion between domain models and ORM models
    specifically for Flask-Login integration, keeping the service layer clean.
    """

    def __init__(self):
        self.user_service = ServiceFactory.create_user_service()
        self.orm_adapter = ORMAdapterFactory.create_orm_adapter()

    def load_user(self, user_id: int) -> FlaskLoginUser | None:
        """Load user by ID for Flask-Login.

        Args:
            user_id: The ID of the user to load

        Returns:
            FlaskLoginUser instance if user exists, None otherwise
        """
        # First check if user exists using the service layer (domain model)
        user_domain = self.user_service.get_user_by_id(user_id)
        if not user_domain:
            return None

        # Get the ORM model for Flask-Login compatibility using the ORM adapter
        user_orm = self.orm_adapter.get_user_orm_by_id(user_id)
        if not user_orm:
            return None

        # Return a FlaskLoginUser instance
        return self._to_flask_login_user(user_orm)

    def authenticate_and_login(self, name: str, password: str) -> FlaskLoginUser | None:
        """Authenticate user and return FlaskLoginUser instance for login.

        Args:
            name: The username
            password: The password

        Returns:
            FlaskLoginUser instance if authentication successful, None otherwise
        """
        # Authenticate using the service layer (domain model)
        user_domain = self.user_service.authenticate_user(name, password)
        if not user_domain:
            return None

        # Get the ORM model for Flask-Login compatibility using the ORM adapter
        user_orm = self.orm_adapter.get_user_orm_by_name(name)
        if not user_orm:
            return None

        # Return a FlaskLoginUser instance
        return self._to_flask_login_user(user_orm)

    def _to_flask_login_user(self, user_orm: UserORM) -> FlaskLoginUser:
        """Convert User ORM model to FlaskLoginUser.

        Args:
            user_orm: The User ORM model

        Returns:
            FlaskLoginUser instance
        """
        # Create a FlaskLoginUser instance with the same attributes
        flask_login_user = FlaskLoginUser()
        flask_login_user.id = user_orm.id
        flask_login_user.name = user_orm.name
        flask_login_user.password = user_orm.password
        flask_login_user.authenticated = user_orm.authenticated
        flask_login_user.createdon = user_orm.createdon
        return flask_login_user


# Initialize the authentication adapter
auth_adapter = AuthenticationAdapter()


@login_manager.user_loader
def load_user(user_id: str) -> FlaskLoginUser | None:
    """Load user by ID for Flask-Login.

    This function uses the authentication adapter to handle the Flask-Login
    integration while keeping the service layer clean.

    Args:
        user_id: The user ID as a string (from Flask-Login session)

    Returns:
        FlaskLoginUser instance if user exists, None otherwise
    """
    try:
        return auth_adapter.load_user(int(user_id))
    except (ValueError, TypeError):
        # Return None for invalid user IDs (e.g., session tampering)
        return None
