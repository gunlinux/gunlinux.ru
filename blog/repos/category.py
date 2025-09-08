"""Repository for Category entities."""

import sqlalchemy as sa
from typing import Any, List, Optional

from blog.extensions import db
from blog.category.models import Category as CategoryORM
from blog.domain.category import Category as CategoryDomain
from blog.repos.base import BaseRepository


class CategoryRepository(BaseRepository[CategoryDomain, int]):
    """Repository for Category entities."""

    def __init__(self, session: Any = None):
        self.session = session or db.session

    def get_category_orm_with_relationships(
        self, category_id: int
    ) -> CategoryORM | None:
        stmt = (
            sa.select(CategoryORM)
            .where(CategoryORM.id == category_id)
            .options(sa.orm.joinedload(CategoryORM.posts))
        )
        return self.session.scalar(stmt)

    def get_by_id(self, id: int) -> Optional[CategoryDomain]:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == id)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            return self._to_domain_model(category_orm)
        return None

    def get_by_alias(self, alias: str) -> CategoryDomain | None:
        stmt = sa.select(CategoryORM).where(CategoryORM.alias == alias)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            return self._to_domain_model(category_orm)
        return None

    def get_all(self) -> List[CategoryDomain]:
        stmt = sa.select(CategoryORM)
        categories_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(category_orm) for category_orm in categories_orm]

    def get_categories_with_posts(self) -> list[CategoryDomain]:
        """Get all categories with their posts loaded.

        Note: This method loads relationships but doesn't include them in the domain model
        since we've removed relationship fields to avoid circular dependencies.
        """
        stmt = sa.select(CategoryORM).options(sa.orm.joinedload(CategoryORM.posts))
        categories_orm = list(self.session.scalars(stmt).unique().all())
        return [self._to_domain_model(category_orm) for category_orm in categories_orm]

    def create(self, entity: CategoryDomain) -> CategoryDomain:
        category_orm = CategoryORM()
        category_orm.title = entity.title
        category_orm.alias = entity.alias
        # Handle the case where template might be None
        if entity.template is not None:
            category_orm.template = entity.template
        self.session.add(category_orm)
        self.session.flush()  # Get the ID without committing
        entity.id = category_orm.id
        return entity

    def update(self, entity: CategoryDomain) -> CategoryDomain:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == entity.id)
        category_orm = self.session.scalar(stmt)
        if not category_orm:
            raise ValueError(f"Category with id {entity.id} not found")

        category_orm.title = entity.title
        category_orm.alias = entity.alias
        # Handle the case where template might be None
        if entity.template is not None:
            category_orm.template = entity.template
        self.session.flush()
        return entity

    def delete(self, id: int) -> bool:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == id)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            self.session.delete(category_orm)
            return True
        return False

    def _to_domain_model(self, category_orm: CategoryORM) -> CategoryDomain:
        return CategoryDomain(
            id=category_orm.id,
            title=category_orm.title or "",
            alias=category_orm.alias or "",
            template=category_orm.template,
        )
