"""Repository for Icon entities."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from blog.extensions import db
from blog.post.models import Icon as IconORM
from blog.domain.icon import Icon


class IconRepository:
    """Repository for Icon entities."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def get_by_id(self, icon_id: int) -> Icon | None:
        """Get an icon by its ID."""
        stmt = sa.select(IconORM).where(IconORM.id == icon_id)
        icon_orm = self.session.scalar(stmt)
        if icon_orm:
            return self._to_domain_model(icon_orm)
        return None

    def get_by_title(self, title: str) -> Icon | None:
        """Get an icon by its title."""
        stmt = sa.select(IconORM).where(IconORM.title == title)
        icon_orm = self.session.scalar(stmt)
        if icon_orm:
            return self._to_domain_model(icon_orm)
        return None

    def get_all(self) -> list[Icon]:
        """Get all icons."""
        stmt = sa.select(IconORM)
        icons_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(icon_orm) for icon_orm in icons_orm]

    def create(self, icon: Icon) -> Icon:
        """Create a new icon."""
        icon_orm = IconORM()
        icon_orm.title = icon.title
        icon_orm.url = icon.url
        if icon.content is not None:
            icon_orm.content = icon.content
        self.session.add(icon_orm)
        self.session.flush()  # Get the ID without committing
        icon.id = icon_orm.id
        return icon

    def update(self, icon: Icon) -> Icon:
        """Update an existing icon."""
        stmt = sa.select(IconORM).where(IconORM.id == icon.id)
        icon_orm = self.session.scalar(stmt)
        if not icon_orm:
            raise ValueError(f"Icon with id {icon.id} not found")

        icon_orm.title = icon.title
        icon_orm.url = icon.url
        if icon.content is not None:
            icon_orm.content = icon.content
        self.session.flush()
        return icon

    def delete(self, icon_id: int) -> bool:
        """Delete an icon by its ID."""
        stmt = sa.select(IconORM).where(IconORM.id == icon_id)
        icon_orm = self.session.scalar(stmt)
        if icon_orm:
            self.session.delete(icon_orm)
            return True
        return False

    def _to_domain_model(self, icon_orm: IconORM) -> Icon:
        """Convert ORM model to domain model."""
        return Icon(
            id=icon_orm.id,
            title=icon_orm.title,
            url=icon_orm.url,
            content=icon_orm.content,
        )