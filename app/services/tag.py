import logging

from app.domain.tag import Tag
from app.repositories.tag import TagRepository

logger = logging.getLogger(__name__)


class TagServiceError(Exception):
    pass


class TagNotFoundError(TagServiceError):
    pass


class TagCreationError(TagServiceError):
    pass


class TagUpdateError(TagServiceError):
    pass


class TagService:
    def __init__(self, tag_repository: TagRepository) -> None:
        self.tag_repository = tag_repository

    async def get_tag_by_alias(self, alias: str) -> Tag | None:
        return await self.tag_repository.get_by_alias(alias)

    async def get_all_tags(self) -> list[Tag]:
        return await self.tag_repository.get_all()

    async def create_tag(self, tag: Tag) -> Tag:
        try:
            return await self.tag_repository.create(tag)
        except Exception as e:
            logger.error("Failed to create tag: %s", str(e), exc_info=True)
            raise TagCreationError(f"Failed to create tag: {str(e)}") from e
