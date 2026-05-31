from typing import override

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.icon import Icon as IconDomain
from app.models.post import Icon as IconORM
from app.repositories.base import BaseRepository


class IconRepository(BaseRepository[IconDomain, int]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def get_by_id(self, id: int) -> IconDomain | None:
        stmt = sa.select(IconORM).where(IconORM.id == id)
        icon_orm = await self.session.scalar(stmt)
        return self._to_domain(icon_orm) if icon_orm else None

    async def get_by_title(self, title: str) -> IconDomain | None:
        stmt = sa.select(IconORM).where(IconORM.title == title)
        icon_orm = await self.session.scalar(stmt)
        return self._to_domain(icon_orm) if icon_orm else None

    @override
    async def get_all(self) -> list[IconDomain]:
        stmt = sa.select(IconORM)
        result = await self.session.scalars(stmt)
        return [self._to_domain(i) for i in result.all()]

    @override
    async def create(self, entity: IconDomain) -> IconDomain:
        icon_orm = IconORM()
        icon_orm.title = entity.title
        icon_orm.url = entity.url
        if entity.content is not None:
            icon_orm.content = entity.content
        self.session.add(icon_orm)
        await self.session.flush()
        entity.id = icon_orm.id
        return entity

    @override
    async def update(self, entity: IconDomain) -> IconDomain:
        stmt = sa.select(IconORM).where(IconORM.id == entity.id)
        icon_orm = await self.session.scalar(stmt)
        if not icon_orm:
            raise ValueError(f"Icon with id {entity.id} not found")
        icon_orm.title = entity.title
        icon_orm.url = entity.url
        if entity.content is not None:
            icon_orm.content = entity.content
        await self.session.flush()
        return entity

    @override
    async def delete(self, id: int) -> bool:
        stmt = sa.select(IconORM).where(IconORM.id == id)
        icon_orm = await self.session.scalar(stmt)
        if icon_orm:
            await self.session.delete(icon_orm)
            return True
        return False

    def _to_domain(self, i: IconORM) -> IconDomain:
        return IconDomain(id=i.id, title=i.title, url=i.url, content=i.content)
