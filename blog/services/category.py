"""Service layer for Category entities."""

from blog.repos.category import CategoryRepository
from blog.domain.category import Category


class CategoryServiceError(Exception):
    """Base exception for CategoryService errors."""

    pass


class CategoryService:
    """Service layer for Category entities."""

    def __init__(self, category_repository: CategoryRepository):
        self.category_repository = category_repository

    def get_category_by_id(self, category_id: int) -> Category | None:
        """Get a category by its ID."""
        return self.category_repository.get_by_id(category_id)

    def get_category_by_alias(self, alias: str) -> Category | None:
        """Get a category by its alias."""
        return self.category_repository.get_by_alias(alias)

    def get_all_categories(self) -> list[Category]:
        """Get all categories."""
        return self.category_repository.get_all()

    def get_categories_with_posts(self) -> list[Category]:
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
        except Exception:
            # Log the error and return False to indicate failure
            # In a real application, you might want to log this
            return False
