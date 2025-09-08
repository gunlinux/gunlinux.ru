"""Service layer for Tag entities."""

from blog.repos.tag import TagRepository
from blog.domain.tag import Tag


class TagServiceError(Exception):
    """Base exception for TagService errors."""

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
            # Re-raise as a more specific exception for the service layer
            raise TagServiceError(f"Failed to create tag: {str(e)}") from e

    def update_tag(self, tag: Tag) -> Tag:
        try:
            return self.tag_repository.update(tag)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise TagServiceError(f"Failed to update tag: {str(e)}") from e

    def delete_tag(self, tag_id: int) -> bool:
        try:
            return self.tag_repository.delete(tag_id)
        except Exception:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False
