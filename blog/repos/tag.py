"""Repository for Tag entities."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from blog.extensions import db
from blog.tags.models import Tag as TagORM
from blog.domain.tag import Tag


class TagRepository:
    """Repository for Tag entities."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def get_by_id(self, tag_id: int) -> Tag | None:
        """Get a tag by its ID."""
        stmt = sa.select(TagORM).where(TagORM.id == tag_id)
        tag_orm = self.session.scalar(stmt)
        if tag_orm:
            return self._to_domain_model(tag_orm)
        return None

    def get_by_alias(self, alias: str) -> Tag | None:
        """Get a tag by its alias."""
        stmt = sa.select(TagORM).where(TagORM.alias == alias)
        tag_orm = self.session.scalar(stmt)
        if tag_orm:
            return self._to_domain_model(tag_orm)
        return None

    def get_all(self) -> list[Tag]:
        """Get all tags."""
        stmt = sa.select(TagORM)
        tags_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(tag_orm) for tag_orm in tags_orm]

    def get_tags_with_posts(self) -> list[Tag]:
        """Get all tags with their posts."""
        stmt = sa.select(TagORM).options(sa.orm.joinedload(TagORM.posts))
        tags_orm = self.session.scalars(stmt).unique().all()
        return [self._to_domain_model(tag_orm) for tag_orm in tags_orm]

    def create(self, tag: Tag) -> Tag:
        """Create a new tag."""
        tag_orm = TagORM()
        tag_orm.title = tag.title
        tag_orm.alias = tag.alias
        self.session.add(tag_orm)
        self.session.flush()  # Get the ID without committing
        tag.id = tag_orm.id
        return tag

    def update(self, tag: Tag) -> Tag:
        """Update an existing tag."""
        stmt = sa.select(TagORM).where(TagORM.id == tag.id)
        tag_orm = self.session.scalar(stmt)
        if not tag_orm:
            raise ValueError(f"Tag with id {tag.id} not found")

        tag_orm.title = tag.title
        tag_orm.alias = tag.alias
        self.session.flush()
        return tag

    def delete(self, tag_id: int) -> bool:
        """Delete a tag by its ID."""
        stmt = sa.select(TagORM).where(TagORM.id == tag_id)
        tag_orm = self.session.scalar(stmt)
        if tag_orm:
            self.session.delete(tag_orm)
            return True
        return False

    def _to_domain_model(self, tag_orm: TagORM) -> Tag:
        """Convert ORM model to domain model."""
        return Tag(
            id=tag_orm.id,
            title=tag_orm.title,
            alias=tag_orm.alias,
        )
