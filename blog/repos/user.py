"""Repository for User entities."""

import sqlalchemy as sa
from typing import Any, List, Optional

from blog.extensions import db
from blog.user.models import User as UserORM
from blog.domain.user import User as UserDomain
from blog.repos.base import BaseRepository


class UserRepository(BaseRepository[UserDomain, int]):
    """Repository for User entities."""

    def __init__(self, session: Any = None):
        self.session = session or db.session

    def get_by_id(self, id: int) -> Optional[UserDomain]:
        stmt = sa.select(UserORM).where(UserORM.id == id)
        user_orm = self.session.scalar(stmt)
        if user_orm:
            return self._to_domain_model(user_orm)
        return None

    def get_by_name(self, name: str) -> UserDomain | None:
        stmt = sa.select(UserORM).where(UserORM.name == name)
        user_orm = self.session.scalar(stmt)
        if user_orm:
            return self._to_domain_model(user_orm)
        return None

    def get_all(self) -> List[UserDomain]:
        stmt = sa.select(UserORM)
        users_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(user_orm) for user_orm in users_orm]

    def get_users_with_posts(self) -> list[UserDomain]:
        """Get all users with their posts loaded.

        Note: This method loads relationships but doesn't include them in the domain model
        since we've removed relationship fields to avoid circular dependencies.
        """
        stmt = sa.select(UserORM).options(sa.orm.joinedload(UserORM.posts))
        users_orm = self.session.scalars(stmt).unique().all()
        return [self._to_domain_model(user_orm) for user_orm in users_orm]

    def create(self, entity: UserDomain) -> UserDomain:
        user_orm = UserORM()
        user_orm.name = entity.name
        user_orm.password = entity.password
        # Handle the case where authenticated might be None
        user_orm.authenticated = (
            entity.authenticated if entity.authenticated is not None else False
        )
        # Handle datetime field that might be None
        if entity.createdon is not None:
            user_orm.createdon = entity.createdon
        self.session.add(user_orm)
        self.session.flush()  # Get the ID without committing
        entity.id = user_orm.id
        return entity

    def update(self, entity: UserDomain) -> UserDomain:
        stmt = sa.select(UserORM).where(UserORM.id == entity.id)
        user_orm = self.session.scalar(stmt)
        if not user_orm:
            raise ValueError(f"User with id {entity.id} not found")

        user_orm.name = entity.name
        user_orm.password = entity.password
        # Handle the case where authenticated might be None
        user_orm.authenticated = (
            entity.authenticated if entity.authenticated is not None else False
        )
        # Handle datetime field that might be None
        if entity.createdon is not None:
            user_orm.createdon = entity.createdon
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        stmt = sa.select(UserORM).where(UserORM.id == id)
        user_orm = self.session.scalar(stmt)
        if user_orm:
            self.session.delete(user_orm)
            return True
        return False

    def authenticate(self, name: str, password: str) -> UserDomain | None:
        stmt = sa.select(UserORM).where(UserORM.name == name)
        user_orm = self.session.scalar(stmt)
        if user_orm and user_orm.check_password(password):
            return self._to_domain_model(user_orm)
        return None

    def _to_domain_model(self, user_orm: UserORM) -> UserDomain:
        return UserDomain(
            id=user_orm.id,
            name=user_orm.name or "",
            password=user_orm.password or "",
            authenticated=bool(user_orm.authenticated)
            if user_orm.authenticated is not None
            else False,
            createdon=user_orm.createdon,
        )
