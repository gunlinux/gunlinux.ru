"""Service layer for User entities."""

import logging
from blog.repos.user import UserRepository
from blog.domain.user import User


logger = logging.getLogger(__name__)


class UserServiceError(Exception):
    """Base exception for UserService errors."""

    pass


class UserNotFoundError(UserServiceError):
    """Raised when a user is not found."""

    pass


class UserCreationError(UserServiceError):
    """Raised when a user cannot be created."""

    pass


class UserUpdateError(UserServiceError):
    """Raised when a user cannot be updated."""

    pass


class UserService:
    """Service layer for User entities."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.user_repository.get_by_id(user_id)

    def get_user_by_name(self, name: str) -> User | None:
        return self.user_repository.get_by_name(name)

    def get_all_users(self) -> list[User]:
        return self.user_repository.get_all()

    def get_users_with_posts(self) -> list[User]:
        return self.user_repository.get_users_with_posts()

    def create_user(self, user: User) -> User:
        try:
            return self.user_repository.create(user)
        except Exception as e:
            # Log the error with details
            logger.error(f"Failed to create user: {str(e)}", exc_info=True)
            # Re-raise as a more specific exception for the service layer
            raise UserCreationError(f"Failed to create user: {str(e)}") from e

    def update_user(self, user: User) -> User:
        try:
            return self.user_repository.update(user)
        except ValueError as e:
            # Log the error with details
            logger.error(f"Failed to update user: {str(e)}", exc_info=True)
            # Re-raise as a more specific exception for the service layer
            raise UserUpdateError(f"Failed to update user: {str(e)}") from e

    def delete_user(self, user_id: int) -> bool:
        try:
            return self.user_repository.delete(user_id)
        except Exception as e:
            # Log the error with details
            logger.error(f"Failed to delete user with id {user_id}: {str(e)}", exc_info=True)
            # Return False to indicate failure
            return False

    def authenticate_user(self, name: str, password: str) -> User | None:
        return self.user_repository.authenticate(name, password)
