"""Service layer for Category entities."""

import logging
from blog.repos.category import CategoryRepository
from blog.domain.category import Category


logger = logging.getLogger(__name__)


class CategoryServiceError(Exception):
    """Base exception for CategoryService errors."""

    pass


class CategoryNotFoundError(CategoryServiceError):
    """Raised when a category is not found."""

    pass


class CategoryCreationError(CategoryServiceError):
    """Raised when a category cannot be created."""

    pass


class CategoryUpdateError(CategoryServiceError):
    """Raised when a category cannot be updated."""

    pass


class CategoryService:
    """Service layer for Category entities."""

    def __init__(self, category_repository: CategoryRepository):
        self.category_repository = category_repository

    def get_category_by_id(self, category_id: int) -> Category | None:
        return self.category_repository.get_by_id(category_id)

    def get_category_by_alias(self, alias: str) -> Category | None:
        return self.category_repository.get_by_alias(alias)

    def get_all_categories(self) -> list[Category]:
        return self.category_repository.get_all()

    def get_categories_with_posts(self) -> list[Category]:
        return self.category_repository.get_categories_with_posts()

    def create_category(self, category: Category) -> Category:
        try:
            return self.category_repository.create(category)
        except Exception as e:
            # Log the error with details
            logger.error(f"Failed to create category: {str(e)}", exc_info=True)
            # Re-raise as a more specific exception for the service layer
            raise CategoryCreationError(f"Failed to create category: {str(e)}") from e

    def update_category(self, category: Category) -> Category:
        try:
            return self.category_repository.update(category)
        except ValueError as e:
            # Log the error with details
            logger.error(f"Failed to update category: {str(e)}", exc_info=True)
            # Re-raise as a more specific exception for the service layer
            raise CategoryUpdateError(f"Failed to update category: {str(e)}") from e

    def delete_category(self, category_id: int) -> bool:
        try:
            return self.category_repository.delete(category_id)
        except Exception as e:
            # Log the error with details
            logger.error(f"Failed to delete category with id {category_id}: {str(e)}", exc_info=True)
            # Return False to indicate failure
            return False
