import logging

from app.domain.icon import Icon
from app.repositories.icon import IconRepository

logger = logging.getLogger(__name__)


class IconServiceError(Exception):
    pass


class IconNotFoundError(IconServiceError):
    pass


class IconCreationError(IconServiceError):
    pass


class IconService:
    def __init__(self, icon_repository: IconRepository) -> None:
        self.icon_repository = icon_repository

    async def get_icon_by_title(self, title: str) -> Icon | None:
        return await self.icon_repository.get_by_title(title)

    async def get_all_icons(self) -> list[Icon]:
        return await self.icon_repository.get_all()

    async def create_icon(self, icon: Icon) -> Icon:
        try:
            return await self.icon_repository.create(icon)
        except Exception as e:
            logger.error("Failed to create icon: %s", str(e), exc_info=True)
            raise IconCreationError(f"Failed to create icon: {str(e)}") from e
