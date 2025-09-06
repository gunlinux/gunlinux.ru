"""Service layer for Category entities."""

from typing import List, Optional
from blog.repos.category import CategoryRepository
from blog.domain.category import Category
from blog.category.models import Category as CategoryORM
from blog.extensions import db
import sqlalchemy as sa


class CategoryServiceError(Exception):
    """Base exception for CategoryService errors."""
    pass


class CategoryService:
    """Service layer for Category entities."""

    def __init__(self, category_repository: CategoryRepository):
        self.category_repository = category_repository

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Get a category by its ID."""
        return self.category_repository.get_by_id(category_id)

    def get_category_by_alias(self, alias: str) -> Optional[Category]:
        """Get a category by its alias."""
        return self.category_repository.get_by_alias(alias)

    def get_all_categories(self) -> List[Category]:
        """Get all categories."""
        return self.category_repository.get_all()

    def get_categories_with_posts(self) -> List[Category]:
        """Get all categories with their posts."""
        return self.category_repository.get_categories_with_posts()

    def create_category(self, category: Category) -> Category:
        """Create a new category."""
        try:
            return self.category_repository.create(category)
        except Exception as e:
            # Re-raise as a more specific exception for the service layer
            raise CategoryServiceError(f"Failed to create category: {str(e)}") from e

    def update_category(self, category: Category) -> Category:
        """Update an existing category."""
        try:
            return self.category_repository.update(category)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise CategoryServiceError(f"Failed to update category: {str(e)}") from e

    def delete_category(self, category_id: int) -> bool:
        """Delete a category by its ID."""
        try:
            return self.category_repository.delete(category_id)
        except Exception as e:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False

    def get_category_by_id_orm(self, category_id: int) -> Optional[CategoryORM]:
        """Get a category by its ID as ORM model (for compatibility with views)."""
        domain_category = self.get_category_by_id(category_id)
        if domain_category:
            return self._to_orm_model(domain_category)
        return None

    def _to_orm_model(self, category: Category) -> CategoryORM:
        """Convert domain model to ORM model by loading from database."""
        if category.id:
            # Load the full ORM model from database to get relationships
            stmt = sa.select(CategoryORM).where(CategoryORM.id == category.id)
            category_orm = db.session.scalar(stmt)
            if category_orm:
                return category_orm

        # If we can't load from database, create a new instance
        category_orm = CategoryORM()
        category_orm.id = category.id or 0
        category_orm.title = category.title
        category_orm.alias = category.alias
        category_orm.template = category.template
        return category_orm