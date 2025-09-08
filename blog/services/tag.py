"""Service layer for Tag entities."""

import logging
from blog.repos.tag import TagRepository
from blog.domain.tag import Tag


logger = logging.getLogger(__name__)


class TagServiceError(Exception):
    """Base exception for TagService errors."""

    pass


class TagNotFoundError(TagServiceError):
    """Raised when a tag is not found."""

    pass


class TagCreationError(TagServiceError):
    """Raised when a tag cannot be created."""

    pass


class TagUpdateError(TagServiceError):
    """Raised when a tag cannot be updated."""

    pass


class TagService:
    """Service layer for Tag entities."""

    def __init__(self, tag_repository: TagRepository):
        self.tag_repository = tag_repository

    def get_tag_by_id(self, tag_id: int) -> Tag | None:
        return self.tag_repository.get_by_id(tag_id)

    def get_tag_by_alias(self, alias: str) -> Tag | None:
        return self.tag_repository.get_by_alias(alias)

    def get_all_tags(self) -> list[Tag]:
        return self.tag_repository.get_all()

    def get_tags_with_posts(self) -> list[Tag]:
        return self.tag_repository.get_tags_with_posts()

    def create_tag(self, tag: Tag) -> Tag:
        try:
            return self.tag_repository.create(tag)
        except Exception as e:
            # Log the error with details
            logger.error(f"Failed to create tag: {str(e)}", exc_info=True)
            # Re-raise as a more specific exception for the service layer
            raise TagCreationError(f"Failed to create tag: {str(e)}") from e

    def update_tag(self, tag: Tag) -> Tag:
        try:
            return self.tag_repository.update(tag)
        except ValueError as e:
            # Log the error with details
            logger.error(f"Failed to update tag: {str(e)}", exc_info=True)
            # Re-raise as a more specific exception for the service layer
            raise TagUpdateError(f"Failed to update tag: {str(e)}") from e

    def delete_tag(self, tag_id: int) -> bool:
        try:
            return self.tag_repository.delete(tag_id)
        except Exception as e:
            # Log the error with details
            logger.error(f"Failed to delete tag with id {tag_id}: {str(e)}", exc_info=True)
            # Return False to indicate failure
            return False
