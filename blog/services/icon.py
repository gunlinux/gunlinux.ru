"""Service layer for Icon entities."""

from typing import List, Optional
from blog.repos.icon import IconRepository
from blog.domain.icon import Icon
from blog.post.models import Icon as IconORM
from blog.extensions import db
import sqlalchemy as sa


class IconServiceError(Exception):
    """Base exception for IconService errors."""
    pass


class IconService:
    """Service layer for Icon entities."""

    def __init__(self, icon_repository: IconRepository):
        self.icon_repository = icon_repository

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
        except Exception as e:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False

    def get_all_icons_orm(self) -> List[IconORM]:
        """Get all icons as ORM models (for compatibility with views)."""
        domain_icons = self.get_all_icons()
        return [self._to_orm_model(icon) for icon in domain_icons]

    def _to_orm_model(self, icon: Icon) -> IconORM:
        """Convert domain model to ORM model by loading from database."""
        if icon.id:
            # Load the full ORM model from database
            stmt = sa.select(IconORM).where(IconORM.id == icon.id)
            icon_orm = db.session.scalar(stmt)
            if icon_orm:
                return icon_orm

        # If we can't load from database, create a new instance
        icon_orm = IconORM()
        icon_orm.id = icon.id or 0
        icon_orm.title = icon.title
        icon_orm.url = icon.url
        icon_orm.content = icon.content
        return icon_orm