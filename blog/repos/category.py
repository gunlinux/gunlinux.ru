"""Repository for Category entities."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from blog.extensions import db
from blog.category.models import Category as CategoryORM
from blog.domain.category import Category


class CategoryRepository:
    """Repository for Category entities."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def get_by_id(self, category_id: int) -> Category | None:
        """Get a category by its ID."""
        stmt = sa.select(CategoryORM).where(CategoryORM.id == category_id)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            return self._to_domain_model(category_orm)
        return None

    def get_by_alias(self, alias: str) -> Category | None:
        """Get a category by its alias."""
        stmt = sa.select(CategoryORM).where(CategoryORM.alias == alias)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            return self._to_domain_model(category_orm)
        return None

    def get_all(self) -> list[Category]:
        """Get all categories."""
        stmt = sa.select(CategoryORM)
        categories_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(category_orm) for category_orm in categories_orm]

    def get_categories_with_posts(self) -> list[Category]:
        """Get all categories with their posts."""
        stmt = sa.select(CategoryORM).options(sa.orm.joinedload(CategoryORM.posts))
        categories_orm = self.session.scalars(stmt).unique().all()
        return [self._to_domain_model(category_orm) for category_orm in categories_orm]

    def create(self, category: Category) -> Category:
        """Create a new category."""
        category_orm = CategoryORM()
        category_orm.title = category.title
        category_orm.alias = category.alias
        # Handle the case where template might be None
        if category.template is not None:
            category_orm.template = category.template
        self.session.add(category_orm)
        self.session.flush()  # Get the ID without committing
        category.id = category_orm.id
        return category

    def update(self, category: Category) -> Category:
        """Update an existing category."""
        stmt = sa.select(CategoryORM).where(CategoryORM.id == category.id)
        category_orm = self.session.scalar(stmt)
        if not category_orm:
            raise ValueError(f"Category with id {category.id} not found")

        category_orm.title = category.title
        category_orm.alias = category.alias
        # Handle the case where template might be None
        if category.template is not None:
            category_orm.template = category.template
        self.session.flush()
        return category

    def delete(self, category_id: int) -> bool:
        """Delete a category by its ID."""
        stmt = sa.select(CategoryORM).where(CategoryORM.id == category_id)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            self.session.delete(category_orm)
            return True
        return False

    def _to_domain_model(self, category_orm: CategoryORM) -> Category:
        """Convert ORM model to domain model."""
        return Category(
            id=category_orm.id,
            title=category_orm.title,
            alias=category_orm.alias,
            template=category_orm.template,
        )
