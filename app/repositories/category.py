from typing import override

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.category import Category as CategoryDomain
from app.models.category import Category as CategoryORM
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[CategoryDomain, int]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def get_by_id(self, id: int) -> CategoryDomain | None:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == id)
        category_orm = await self.session.scalar(stmt)
        return self._to_domain(category_orm) if category_orm else None

    async def get_by_alias(self, alias: str) -> CategoryDomain | None:
        stmt = sa.select(CategoryORM).where(CategoryORM.alias == alias)
        category_orm = await self.session.scalar(stmt)
        return self._to_domain(category_orm) if category_orm else None

    @override
    async def get_all(self) -> list[CategoryDomain]:
        stmt = sa.select(CategoryORM)
        result = await self.session.scalars(stmt)
        return [self._to_domain(c) for c in result.all()]

    @override
    async def create(self, entity: CategoryDomain) -> CategoryDomain:
        category_orm = CategoryORM()
        category_orm.title = entity.title
        category_orm.alias = entity.alias
        category_orm.page = entity.page
        if entity.template is not None:
            category_orm.template = entity.template
        self.session.add(category_orm)
        await self.session.flush()
        entity.id = category_orm.id
        return entity

    @override
    async def update(self, entity: CategoryDomain) -> CategoryDomain:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == entity.id)
        category_orm = await self.session.scalar(stmt)
        if not category_orm:
            raise ValueError(f"Category with id {entity.id} not found")
        category_orm.title = entity.title
        category_orm.alias = entity.alias
        if entity.template is not None:
            category_orm.template = entity.template
        await self.session.flush()
        return entity

    @override
    async def delete(self, id: int) -> bool:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == id)
        category_orm = await self.session.scalar(stmt)
        if category_orm:
            await self.session.delete(category_orm)
            return True
        return False

    def _to_domain(self, c: CategoryORM) -> CategoryDomain:
        return CategoryDomain(
            id=c.id,
            title=c.title or "",
            alias=c.alias or "",
            template=c.template,
            page=c.page,
        )
