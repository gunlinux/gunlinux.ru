"""Service layer for User entities."""

from typing import List, Optional
from blog.repos.user import UserRepository
from blog.domain.user import User
from blog.user.models import User as UserORM
from blog.extensions import db
import sqlalchemy as sa


class UserServiceError(Exception):
    """Base exception for UserService errors."""
    pass


class UserService:
    """Service layer for User entities."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by its ID."""
        return self.user_repository.get_by_id(user_id)

    def get_user_by_name(self, name: str) -> Optional[User]:
        """Get a user by their name."""
        return self.user_repository.get_by_name(name)

    def get_all_users(self) -> List[User]:
        """Get all users."""
        return self.user_repository.get_all()

    def get_users_with_posts(self) -> List[User]:
        """Get all users with their posts."""
        return self.user_repository.get_users_with_posts()

    def create_user(self, user: User) -> User:
        """Create a new user."""
        try:
            return self.user_repository.create(user)
        except Exception as e:
            # Re-raise as a more specific exception for the service layer
            raise UserServiceError(f"Failed to create user: {str(e)}") from e

    def update_user(self, user: User) -> User:
        """Update an existing user."""
        try:
            return self.user_repository.update(user)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise UserServiceError(f"Failed to update user: {str(e)}") from e

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by its ID."""
        try:
            return self.user_repository.delete(user_id)
        except Exception as e:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False

    def authenticate_user(self, name: str, password: str) -> Optional[User]:
        """Authenticate a user by name and password."""
        return self.user_repository.authenticate(name, password)

    def get_user_by_id_orm(self, user_id: int) -> Optional[UserORM]:
        """Get a user by its ID as ORM model (for compatibility with views)."""
        domain_user = self.get_user_by_id(user_id)
        if domain_user:
            return self._to_orm_model(domain_user)
        return None

    def get_user_by_name_orm(self, name: str) -> Optional[UserORM]:
        """Get a user by their name as ORM model (for compatibility with views)."""
        domain_user = self.get_user_by_name(name)
        if domain_user:
            return self._to_orm_model(domain_user)
        return None

    def _to_orm_model(self, user: User) -> UserORM:
        """Convert domain model to ORM model by loading from database."""
        if user.id:
            # Load the full ORM model from database to get relationships
            stmt = sa.select(UserORM).where(UserORM.id == user.id)
            user_orm = db.session.scalar(stmt)
            if user_orm:
                return user_orm

        # If we can't load from database, create a new instance
        user_orm = UserORM()
        user_orm.id = user.id or 0
        user_orm.name = user.name
        user_orm.password = user.password
        user_orm.authenticated = user.authenticated
        user_orm.createdon = user.createdon
        return user_orm