"""Service layer for User entities."""

from blog.repos.user import UserRepository
from blog.domain.user import User


class UserServiceError(Exception):
    """Base exception for UserService errors."""

    pass


class UserService:
    """Service layer for User entities."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.user_repository.get_by_id(user_id)

    def get_user_orm_by_id(self, user_id: int):
        """Get a user ORM model by its ID. Used for Flask-Login compatibility."""
        return self.user_repository.get_user_orm_by_id(user_id)

    def get_user_orm_by_name(self, name: str):
        """Get a user ORM model by their name. Used for Flask-Login compatibility."""
        return self.user_repository.get_user_orm_by_name(name)

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
            # Re-raise as a more specific exception for the service layer
            raise UserServiceError(f"Failed to create user: {str(e)}") from e

    def update_user(self, user: User) -> User:
        try:
            return self.user_repository.update(user)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise UserServiceError(f"Failed to update user: {str(e)}") from e

    def delete_user(self, user_id: int) -> bool:
        try:
            return self.user_repository.delete(user_id)
        except Exception:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False

    def authenticate_user(self, name: str, password: str) -> User | None:
        return self.user_repository.authenticate(name, password)
