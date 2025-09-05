"""Repository for User entities."""

from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from blog.extensions import db
from blog.user.models import User as UserORM
from blog.domain.user import User


class UserRepository:
    """Repository for User entities."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by its ID."""
        stmt = sa.select(UserORM).where(UserORM.id == user_id)
        user_orm = self.session.scalar(stmt)
        if user_orm:
            return self._to_domain_model(user_orm)
        return None

    def get_by_name(self, name: str) -> Optional[User]:
        """Get a user by their name."""
        stmt = sa.select(UserORM).where(UserORM.name == name)
        user_orm = self.session.scalar(stmt)
        if user_orm:
            return self._to_domain_model(user_orm)
        return None

    def get_all(self) -> List[User]:
        """Get all users."""
        stmt = sa.select(UserORM)
        users_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(user_orm) for user_orm in users_orm]

    def get_users_with_posts(self) -> List[User]:
        """Get all users with their posts."""
        stmt = sa.select(UserORM).options(sa.orm.joinedload(UserORM.posts))
        users_orm = self.session.scalars(stmt).unique().all()
        return [self._to_domain_model(user_orm) for user_orm in users_orm]

    def create(self, user: User) -> User:
        """Create a new user."""
        user_orm = UserORM(
            name=user.name,
            password=user.password,
            authenticated=user.authenticated,
            createdon=user.createdon,
        )
        self.session.add(user_orm)
        self.session.flush()  # Get the ID without committing
        user.id = user_orm.id
        return user

    def update(self, user: User) -> User:
        """Update an existing user."""
        stmt = sa.select(UserORM).where(UserORM.id == user.id)
        user_orm = self.session.scalar(stmt)
        if not user_orm:
            raise ValueError(f"User with id {user.id} not found")

        user_orm.name = user.name
        user_orm.password = user.password
        user_orm.authenticated = user.authenticated
        user_orm.createdon = user.createdon
        self.session.flush()
        return user

    def delete(self, user_id: int) -> bool:
        """Delete a user by its ID."""
        stmt = sa.select(UserORM).where(UserORM.id == user_id)
        user_orm = self.session.scalar(stmt)
        if user_orm:
            self.session.delete(user_orm)
            return True
        return False

    def authenticate(self, name: str, password: str) -> Optional[User]:
        """Authenticate a user by name and password."""
        stmt = sa.select(UserORM).where(UserORM.name == name)
        user_orm = self.session.scalar(stmt)
        if user_orm and user_orm.check_password(password):
            return self._to_domain_model(user_orm)
        return None

    def _to_domain_model(self, user_orm: UserORM) -> User:
        """Convert ORM model to domain model."""
        return User(
            id=user_orm.id,
            name=user_orm.name,
            password=user_orm.password,
            authenticated=user_orm.authenticated,
            createdon=user_orm.createdon,
        )
