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

    async def get_icon_by_id(self, icon_id: int) -> Icon | None:
        return await self.icon_repository.get_by_id(icon_id)

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

    async def update_icon(self, icon: Icon) -> Icon:
        try:
            return await self.icon_repository.update(icon)
        except ValueError as e:
            logger.error("Failed to update icon: %s", str(e), exc_info=True)
            raise IconServiceError(f"Failed to update icon: {str(e)}") from e

    async def delete_icon(self, icon_id: int) -> bool:
        try:
            return await self.icon_repository.delete(icon_id)
        except Exception as e:
            logger.error("Failed to delete icon %s: %s", icon_id, str(e), exc_info=True)
            return False
