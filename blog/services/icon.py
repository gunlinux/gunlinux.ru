"""Service layer for Icon entities."""

from typing import List, Optional
from blog.repos.icon import IconRepository
from blog.domain.icon import Icon


class IconServiceError(Exception):
    """Base exception for IconService errors."""

    pass


class IconService:
    """Service layer for Icon entities."""

    def __init__(self, icon_repository: IconRepository):
        self.icon_repository = icon_repository

    def get_icon_orm_by_id(self, icon_id: int):
        """Get an icon ORM model by its ID. Used for specific use cases requiring ORM models."""
        return self.icon_repository.get_icon_orm_by_id(icon_id)

    def get_all_icons_orm(self) -> List:
        """Get all icons as ORM models. Used for specific use cases requiring ORM models."""
        return self.icon_repository.get_all_icons_orm()

    def get_icon_by_id(self, icon_id: int) -> Optional[Icon]:
        """Get an icon by its ID."""
        return self.icon_repository.get_by_id(icon_id)

    def get_icon_by_title(self, title: str) -> Optional[Icon]:
        """Get an icon by its title."""
        return self.icon_repository.get_by_title(title)

    def get_all_icons(self) -> List[Icon]:
        """Get all icons."""
        return self.icon_repository.get_all()

    def create_icon(self, icon: Icon) -> Icon:
        """Create a new icon."""
        try:
            return self.icon_repository.create(icon)
        except Exception as e:
            # Re-raise as a more specific exception for the service layer
            raise IconServiceError(f"Failed to create icon: {str(e)}") from e

    def update_icon(self, icon: Icon) -> Icon:
        """Update an existing icon."""
        try:
            return self.icon_repository.update(icon)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise IconServiceError(f"Failed to update icon: {str(e)}") from e

    def delete_icon(self, icon_id: int) -> bool:
        """Delete an icon by its ID."""
        try:
            return self.icon_repository.delete(icon_id)
        except Exception:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False
