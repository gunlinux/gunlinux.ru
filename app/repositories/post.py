from typing import override

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.post import Post as PostDomain
from app.domain.tag import Tag as TagDomain
from app.models.category import Category as CategoryORM
from app.models.post import Post as PostORM
from app.models.tag import Tag as TagORM
from app.repositories.base import BaseRepository


class PostRepository(BaseRepository[PostDomain, int]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def get_by_id(self, id: int) -> PostDomain | None:
        stmt = (
            sa.select(PostORM)
            .where(PostORM.id == id)
            .options(selectinload(PostORM.category))
        )
        post_orm = await self.session.scalar(stmt)
        return self._to_domain(post_orm) if post_orm else None

    async def get_by_alias(self, alias: str) -> PostDomain | None:
        stmt = (
            sa.select(PostORM)
            .where(PostORM.alias == alias)
            .options(selectinload(PostORM.category))
        )
        post_orm = await self.session.scalar(stmt)
        return self._to_domain(post_orm) if post_orm else None

    @override
    async def get_all(self) -> list[PostDomain]:
        stmt = sa.select(PostORM).options(selectinload(PostORM.category))
        result = await self.session.scalars(stmt)
        return [self._to_domain(p) for p in result.all()]

    async def get_published_posts(self) -> list[PostDomain]:
        stmt = (
            sa.select(PostORM)
            .where(PostORM.publishedon.isnot(None), PostORM.category_id.is_(None))
            .options(selectinload(PostORM.category))
            .order_by(PostORM.publishedon.desc())
        )
        result = await self.session.scalars(stmt)
        return [self._to_domain(p) for p in result.all()]

    async def get_all_published_content(self) -> list[PostDomain]:
        stmt = (
            sa.select(PostORM)
            .join(CategoryORM, PostORM.category_id == CategoryORM.id, isouter=True)
            .where(PostORM.publishedon.isnot(None))
            .where(CategoryORM.page.isnot(True))
            .options(selectinload(PostORM.category))
            .order_by(PostORM.publishedon.desc())
        )
        result = await self.session.scalars(stmt)
        return [self._to_domain(p) for p in result.all()]

    async def get_page_posts(self) -> list[PostDomain]:
        stmt = (
            sa.select(PostORM)
            .join(CategoryORM, PostORM.category_id == CategoryORM.id)
            .where(CategoryORM.page.is_(True))
            .options(selectinload(PostORM.category))
        )
        result = await self.session.scalars(stmt)
        return [self._to_domain(p) for p in result.all()]

    async def get_posts_by_tag(self, tag_id: int) -> list[PostDomain]:
        stmt = (
            sa.select(PostORM)
            .join(PostORM.tags)
            .where(TagORM.id == tag_id)
            .options(selectinload(PostORM.category))
        )
        result = await self.session.scalars(stmt)
        return [self._to_domain(p) for p in result.all()]

    async def get_tags_for_post(self, post_id: int) -> list[TagDomain]:
        stmt = sa.select(TagORM).join(TagORM.posts).where(PostORM.id == post_id)
        result = await self.session.scalars(stmt)
        return [
            TagDomain(id=t.id, title=t.title or "", alias=t.alias or "")
            for t in result.all()
        ]

    @override
    async def create(self, entity: PostDomain) -> PostDomain:
        post_orm = PostORM()
        post_orm.pagetitle = entity.pagetitle
        post_orm.alias = entity.alias
        post_orm.content = entity.content
        if entity.createdon is not None:
            post_orm.createdon = entity.createdon
        if entity.publishedon is not None:
            post_orm.publishedon = entity.publishedon
        if entity.category_id is not None:
            post_orm.category_id = entity.category_id
        if entity.user_id is not None:
            post_orm.user_id = entity.user_id
        self.session.add(post_orm)
        await self.session.flush()
        entity.id = post_orm.id
        return entity

    @override
    async def update(self, entity: PostDomain) -> PostDomain:
        stmt = sa.select(PostORM).where(PostORM.id == entity.id)
        post_orm = await self.session.scalar(stmt)
        if not post_orm:
            raise ValueError(f"Post with id {entity.id} not found")
        post_orm.pagetitle = entity.pagetitle
        post_orm.alias = entity.alias
        post_orm.content = entity.content
        if entity.createdon is not None:
            post_orm.createdon = entity.createdon
        if entity.publishedon is not None:
            post_orm.publishedon = entity.publishedon
        if entity.category_id is not None:
            post_orm.category_id = entity.category_id
        if entity.user_id is not None:
            post_orm.user_id = entity.user_id
        await self.session.flush()
        return entity

    @override
    async def delete(self, id: int) -> bool:
        stmt = sa.select(PostORM).where(PostORM.id == id)
        post_orm = await self.session.scalar(stmt)
        if not post_orm:
            raise ValueError(f"Post not found {id}")
        await self.session.delete(post_orm)
        return True

    def _to_domain(self, p: PostORM) -> PostDomain:
        return PostDomain(
            id=p.id,
            pagetitle=p.pagetitle or "",
            alias=p.alias or "",
            content=p.content or "",
            createdon=p.createdon,
            publishedon=p.publishedon,
            category_id=p.category_id,
            is_page=bool(p.category.page) if p.category_id and p.category else False,
            user_id=p.user_id,
        )
