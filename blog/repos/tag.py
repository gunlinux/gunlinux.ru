"""Repository for Tag entities."""

import sqlalchemy as sa
from typing import Any

from blog.extensions import db
from blog.tags.models import Tag as TagORM
from blog.domain.tag import Tag as TagDomain
from blog.domain.post import Post as PostDomain


class TagRepository:
    """Repository for Tag entities."""

    def __init__(self, session: Any = None):
        self.session = session or db.session

    def get_tag_orm_with_relationships(self, tag_id: int) -> TagORM | None:
        stmt = (
            sa.select(TagORM)
            .where(TagORM.id == tag_id)
            .options(sa.orm.joinedload(TagORM.posts))
        )
        return self.session.scalar(stmt)

    def get_by_id(self, tag_id: int) -> TagDomain | None:
        stmt = sa.select(TagORM).where(TagORM.id == tag_id)
        tag_orm = self.session.scalar(stmt)
        if tag_orm:
            return self._to_domain_model(tag_orm)
        return None

    def get_by_alias(self, alias: str) -> TagDomain | None:
        stmt = sa.select(TagORM).where(TagORM.alias == alias)
        tag_orm = self.session.scalar(stmt)
        if tag_orm:
            return self._to_domain_model(tag_orm)
        return None

    def get_all(self) -> list[TagDomain]:
        stmt = sa.select(TagORM)
        tags_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(tag_orm) for tag_orm in tags_orm]

    def get_tags_with_posts(self) -> list[TagDomain]:
        stmt = sa.select(TagORM).options(sa.orm.joinedload(TagORM.posts))
        tags_orm = list(self.session.scalars(stmt).unique().all())
        return [self._to_domain_model(tag_orm) for tag_orm in tags_orm]

    def create(self, tag: TagDomain) -> TagDomain:
        tag_orm = TagORM()
        tag_orm.title = tag.title
        tag_orm.alias = tag.alias
        self.session.add(tag_orm)
        self.session.flush()  # Get the ID without committing
        tag.id = tag_orm.id
        return tag

    def update(self, tag: TagDomain) -> TagDomain:
        stmt = sa.select(TagORM).where(TagORM.id == tag.id)
        tag_orm = self.session.scalar(stmt)
        if not tag_orm:
            raise ValueError(f"Tag with id {tag.id} not found")

        tag_orm.title = tag.title
        tag_orm.alias = tag.alias
        self.session.flush()
        return tag

    def delete(self, tag_id: int) -> bool:
        stmt = sa.select(TagORM).where(TagORM.id == tag_id)
        tag_orm = self.session.scalar(stmt)
        if tag_orm:
            self.session.delete(tag_orm)
            return True
        return False

    def _to_domain_model(self, tag_orm: TagORM) -> TagDomain:
        # Convert related posts if they exist
        posts = None
        if tag_orm.posts:
            posts = [
                PostDomain(
                    id=post_orm.id,
                    pagetitle=post_orm.pagetitle or "",
                    alias=post_orm.alias or "",
                    content=post_orm.content or "",
                    createdon=post_orm.createdon,
                    publishedon=post_orm.publishedon,
                    category_id=post_orm.category_id,
                    user_id=post_orm.user_id,
                    user=None,  # Avoid circular references
                    category=None,  # Avoid circular references
                    tags=None,  # Avoid circular references
                )
                for post_orm in tag_orm.posts
            ]

        return TagDomain(
            id=tag_orm.id,
            title=tag_orm.title or "",
            alias=tag_orm.alias or "",
            posts=posts,
        )
