"""Service layer for Tag entities."""

from typing import List, Optional
from blog.repos.tag import TagRepository
from blog.domain.tag import Tag
from blog.tags.models import Tag as TagORM
from blog.extensions import db
import sqlalchemy as sa


class TagServiceError(Exception):
    """Base exception for TagService errors."""
    pass


class TagService:
    """Service layer for Tag entities."""

    def __init__(self, tag_repository: TagRepository):
        self.tag_repository = tag_repository

    def get_tag_by_id(self, tag_id: int) -> Optional[Tag]:
        """Get a tag by its ID."""
        return self.tag_repository.get_by_id(tag_id)

    def get_tag_by_alias(self, alias: str) -> Optional[Tag]:
        """Get a tag by its alias."""
        return self.tag_repository.get_by_alias(alias)

    def get_all_tags(self) -> List[Tag]:
        """Get all tags."""
        return self.tag_repository.get_all()

    def get_tags_with_posts(self) -> List[Tag]:
        """Get all tags with their posts."""
        return self.tag_repository.get_tags_with_posts()

    def create_tag(self, tag: Tag) -> Tag:
        """Create a new tag."""
        try:
            return self.tag_repository.create(tag)
        except Exception as e:
            # Re-raise as a more specific exception for the service layer
            raise TagServiceError(f"Failed to create tag: {str(e)}") from e

    def update_tag(self, tag: Tag) -> Tag:
        """Update an existing tag."""
        try:
            return self.tag_repository.update(tag)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise TagServiceError(f"Failed to update tag: {str(e)}") from e

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag by its ID."""
        try:
            return self.tag_repository.delete(tag_id)
        except Exception as e:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False

    def get_tag_by_alias_orm(self, alias: str) -> Optional[TagORM]:
        """Get a tag by its alias as ORM model (for compatibility with views)."""
        domain_tag = self.get_tag_by_alias(alias)
        if domain_tag:
            return self._to_orm_model(domain_tag)
        return None

    def get_all_tags_orm(self) -> List[TagORM]:
        """Get all tags as ORM models (for compatibility with views)."""
        domain_tags = self.get_all_tags()
        return [self._to_orm_model(tag) for tag in domain_tags]

    def _to_orm_model(self, tag: Tag) -> TagORM:
        """Convert domain model to ORM model by loading from database."""
        if tag.id:
            # Load the full ORM model from database to get relationships
            stmt = sa.select(TagORM).where(TagORM.id == tag.id)
            tag_orm = db.session.scalar(stmt)
            if tag_orm:
                return tag_orm

        # If we can't load from database, create a new instance
        tag_orm = TagORM()
        tag_orm.id = tag.id or 0
        tag_orm.title = tag.title
        tag_orm.alias = tag.alias
        return tag_orm