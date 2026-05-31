from typing import override

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import User as UserDomain
from app.models.user import User as UserORM
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserDomain, int]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def get_by_id(self, id: int) -> UserDomain | None:
        stmt = sa.select(UserORM).where(UserORM.id == id)
        user_orm = await self.session.scalar(stmt)
        return self._to_domain(user_orm) if user_orm else None

    async def get_by_name(self, name: str) -> UserDomain | None:
        stmt = sa.select(UserORM).where(UserORM.name == name)
        user_orm = await self.session.scalar(stmt)
        return self._to_domain(user_orm) if user_orm else None

    @override
    async def get_all(self) -> list[UserDomain]:
        stmt = sa.select(UserORM)
        result = await self.session.scalars(stmt)
        return [self._to_domain(u) for u in result.all()]

    async def authenticate(self, name: str, password: str) -> UserDomain | None:
        stmt = sa.select(UserORM).where(UserORM.name == name)
        user_orm = await self.session.scalar(stmt)
        if user_orm and user_orm.check_password(password):
            return self._to_domain(user_orm)
        return None

    @override
    async def create(self, entity: UserDomain) -> UserDomain:
        user_orm = UserORM()
        user_orm.name = entity.name
        user_orm.password = entity.password
        user_orm.authenticated = int(entity.authenticated)
        if entity.createdon is not None:
            user_orm.createdon = entity.createdon
        self.session.add(user_orm)
        await self.session.flush()
        entity.id = user_orm.id
        return entity

    @override
    async def update(self, entity: UserDomain) -> UserDomain:
        stmt = sa.select(UserORM).where(UserORM.id == entity.id)
        user_orm = await self.session.scalar(stmt)
        if not user_orm:
            raise ValueError(f"User with id {entity.id} not found")
        user_orm.name = entity.name
        user_orm.password = entity.password
        user_orm.authenticated = int(entity.authenticated)
        if entity.createdon is not None:
            user_orm.createdon = entity.createdon
        await self.session.flush()
        return entity

    @override
    async def delete(self, id: int) -> bool:
        stmt = sa.select(UserORM).where(UserORM.id == id)
        user_orm = await self.session.scalar(stmt)
        if user_orm:
            await self.session.delete(user_orm)
            return True
        return False

    def _to_domain(self, u: UserORM) -> UserDomain:
        return UserDomain(
            id=u.id,
            name=u.name or "",
            password=u.password or "",
            authenticated=bool(u.authenticated)
            if u.authenticated is not None
            else False,
            createdon=u.createdon,
        )
