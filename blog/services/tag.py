"""Service layer for Tag entities."""

from typing import List, Optional
from blog.repos.tag import TagRepository
from blog.domain.tag import Tag


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
        except Exception:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False
