"""Service layer for Icon entities."""

from blog.repos.icon import IconRepository
from blog.domain.icon import Icon


class IconServiceError(Exception):
    """Base exception for IconService errors."""

    pass


class IconNotFoundError(IconServiceError):
    """Raised when an icon is not found."""

    pass


class IconCreationError(IconServiceError):
    """Raised when an icon cannot be created."""

    pass


class IconUpdateError(IconServiceError):
    """Raised when an icon cannot be updated."""

    pass


class IconService:
    """Service layer for Icon entities."""

    def __init__(self, icon_repository: IconRepository):
        self.icon_repository = icon_repository

    def get_icon_orm_by_id(self, icon_id: int):
        """Get an icon ORM model by its ID. Used for specific use cases requiring ORM models."""
        return self.icon_repository.get_icon_orm_by_id(icon_id)

    def get_all_icons_orm(self) -> list:
        """Get all icons as ORM models. Used for specific use cases requiring ORM models."""
        return self.icon_repository.get_all_icons_orm()

    def get_icon_by_id(self, icon_id: int) -> Icon | None:
        return self.icon_repository.get_by_id(icon_id)

    def get_icon_by_title(self, title: str) -> Icon | None:
        return self.icon_repository.get_by_title(title)

    def get_all_icons(self) -> list[Icon]:
        return self.icon_repository.get_all()

    def create_icon(self, icon: Icon) -> Icon:
        try:
            return self.icon_repository.create(icon)
        except Exception as e:
            # Re-raise as a more specific exception for the service layer
            raise IconCreationError(f"Failed to create icon: {str(e)}") from e

    def update_icon(self, icon: Icon) -> Icon:
        try:
            return self.icon_repository.update(icon)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise IconUpdateError(f"Failed to update icon: {str(e)}") from e

    def delete_icon(self, icon_id: int) -> bool:
        try:
            return self.icon_repository.delete(icon_id)
        except Exception:
            # Return False to indicate failure
            return False
