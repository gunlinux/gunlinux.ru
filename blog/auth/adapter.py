"""Authentication adapter for Flask-Login integration."""

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
def load_user(user_id):
    """Load user by ID for Flask-Login.

    This function uses the authentication adapter to handle the Flask-Login
    integration while keeping the service layer clean.
    """
    return auth_adapter.load_user(int(user_id))
