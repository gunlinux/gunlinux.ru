"""Repository for Icon entities."""

import sqlalchemy as sa
from typing import Any, List, Optional

from blog.extensions import db
from blog.post.models import Icon as IconORM
from blog.domain.icon import Icon
from blog.repos.base import BaseRepository


class IconRepository(BaseRepository[Icon, int]):
    """Repository for Icon entities."""

    def __init__(self, session: Any = None):
        self.session = session or db.session

    def get_icon_orm_by_id(self, icon_id: int) -> IconORM | None:
        """Get an icon ORM model by its ID. Used for specific use cases requiring ORM models."""
        stmt = sa.select(IconORM).where(IconORM.id == icon_id)
        return self.session.scalar(stmt)

    def get_all_icons_orm(self) -> list[IconORM]:
        """Get all icons as ORM models. Used for specific use cases requiring ORM models."""
        stmt = sa.select(IconORM)
        return list(self.session.scalars(stmt).all())

    def get_by_id(self, id: int) -> Optional[Icon]:
        stmt = sa.select(IconORM).where(IconORM.id == id)
        icon_orm = self.session.scalar(stmt)
        if icon_orm:
            return self._to_domain_model(icon_orm)
        return None

    def get_by_title(self, title: str) -> Icon | None:
        stmt = sa.select(IconORM).where(IconORM.title == title)
        icon_orm = self.session.scalar(stmt)
        if icon_orm:
            return self._to_domain_model(icon_orm)
        return None

    def get_all(self) -> List[Icon]:
        stmt = sa.select(IconORM)
        icons_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(icon_orm) for icon_orm in icons_orm]

    def create(self, entity: Icon) -> Icon:
        icon_orm = IconORM()
        icon_orm.title = entity.title
        icon_orm.url = entity.url
        if entity.content is not None:
            icon_orm.content = entity.content
        self.session.add(icon_orm)
        self.session.flush()  # Get the ID without committing
        entity.id = icon_orm.id
        return entity

    def update(self, entity: Icon) -> Icon:
        stmt = sa.select(IconORM).where(IconORM.id == entity.id)
        icon_orm = self.session.scalar(stmt)
        if not icon_orm:
            raise ValueError(f"Icon with id {entity.id} not found")

        icon_orm.title = entity.title
        icon_orm.url = entity.url
        if entity.content is not None:
            icon_orm.content = entity.content
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        stmt = sa.select(IconORM).where(IconORM.id == id)
        icon_orm = self.session.scalar(stmt)
        if icon_orm:
            self.session.delete(icon_orm)
            return True
        return False

    def _to_domain_model(self, icon_orm: IconORM) -> Icon:
        return Icon(
            id=icon_orm.id,
            title=icon_orm.title,
            url=icon_orm.url,
            content=icon_orm.content,
        )
