"""Repository for Tag entities."""

import sqlalchemy as sa
from typing import Any, List, Optional

from blog.extensions import db
from blog.tags.models import Tag as TagORM
from blog.domain.tag import Tag as TagDomain
from blog.repos.base import BaseRepository


class TagRepository(BaseRepository[TagDomain, int]):
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

    def get_by_id(self, id: int) -> Optional[TagDomain]:
        stmt = sa.select(TagORM).where(TagORM.id == id)
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

    def get_all(self) -> List[TagDomain]:
        stmt = sa.select(TagORM)
        tags_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(tag_orm) for tag_orm in tags_orm]

    def get_tags_with_posts(self) -> list[TagDomain]:
        """Get all tags with their posts loaded.

        Note: This method loads relationships but doesn't include them in the domain model
        since we've removed relationship fields to avoid circular dependencies.
        """
        stmt = sa.select(TagORM).options(sa.orm.joinedload(TagORM.posts))
        tags_orm = list(self.session.scalars(stmt).unique().all())
        return [self._to_domain_model(tag_orm) for tag_orm in tags_orm]

    def get_tags_for_post(self, post_id: int) -> List[TagDomain]:
        """Get all tags associated with a specific post."""
        from blog.post.models import Post as PostORM

        stmt = sa.select(TagORM).join(TagORM.posts).where(PostORM.id == post_id)
        tags_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(tag_orm) for tag_orm in tags_orm]

    def create(self, entity: TagDomain) -> TagDomain:
        tag_orm = TagORM()
        tag_orm.title = entity.title
        tag_orm.alias = entity.alias
        self.session.add(tag_orm)
        self.session.flush()  # Get the ID without committing
        entity.id = tag_orm.id
        return entity

    def update(self, entity: TagDomain) -> TagDomain:
        stmt = sa.select(TagORM).where(TagORM.id == entity.id)
        tag_orm = self.session.scalar(stmt)
        if not tag_orm:
            raise ValueError(f"Tag with id {entity.id} not found")

        tag_orm.title = entity.title
        tag_orm.alias = entity.alias
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        stmt = sa.select(TagORM).where(TagORM.id == id)
        tag_orm = self.session.scalar(stmt)
        if tag_orm:
            self.session.delete(tag_orm)
            return True
        return False

    def _to_domain_model(self, tag_orm: TagORM) -> TagDomain:
        return TagDomain(
            id=tag_orm.id,
            title=tag_orm.title or "",
            alias=tag_orm.alias or "",
        )
