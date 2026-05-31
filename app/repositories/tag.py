from typing import override

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.tag import Tag as TagDomain
from app.models.post import Post as PostORM
from app.models.tag import Tag as TagORM
from app.repositories.base import BaseRepository


class TagRepository(BaseRepository[TagDomain, int]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def get_by_id(self, id: int) -> TagDomain | None:
        stmt = sa.select(TagORM).where(TagORM.id == id)
        tag_orm = await self.session.scalar(stmt)
        return self._to_domain(tag_orm) if tag_orm else None

    async def get_by_alias(self, alias: str) -> TagDomain | None:
        stmt = sa.select(TagORM).where(TagORM.alias == alias)
        tag_orm = await self.session.scalar(stmt)
        return self._to_domain(tag_orm) if tag_orm else None

    @override
    async def get_all(self) -> list[TagDomain]:
        stmt = sa.select(TagORM)
        result = await self.session.scalars(stmt)
        return [self._to_domain(t) for t in result.all()]

    async def get_tags_with_posts(self) -> list[TagDomain]:
        stmt = sa.select(TagORM).options(selectinload(TagORM.posts))
        result = await self.session.scalars(stmt)
        return [self._to_domain(t) for t in result.unique().all()]

    async def get_tags_for_post(self, post_id: int) -> list[TagDomain]:
        stmt = sa.select(TagORM).join(TagORM.posts).where(PostORM.id == post_id)
        result = await self.session.scalars(stmt)
        return [self._to_domain(t) for t in result.all()]

    @override
    async def create(self, entity: TagDomain) -> TagDomain:
        tag_orm = TagORM()
        tag_orm.title = entity.title
        tag_orm.alias = entity.alias
        self.session.add(tag_orm)
        await self.session.flush()
        entity.id = tag_orm.id
        return entity

    @override
    async def update(self, entity: TagDomain) -> TagDomain:
        stmt = sa.select(TagORM).where(TagORM.id == entity.id)
        tag_orm = await self.session.scalar(stmt)
        if not tag_orm:
            raise ValueError(f"Tag with id {entity.id} not found")
        tag_orm.title = entity.title
        tag_orm.alias = entity.alias
        await self.session.flush()
        return entity

    @override
    async def delete(self, id: int) -> bool:
        stmt = sa.select(TagORM).where(TagORM.id == id)
        tag_orm = await self.session.scalar(stmt)
        if tag_orm:
            await self.session.delete(tag_orm)
            return True
        return False

    def _to_domain(self, t: TagORM) -> TagDomain:
        return TagDomain(id=t.id, title=t.title or "", alias=t.alias or "")
