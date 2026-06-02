import logging

from app.domain.category import Category
from app.repositories.category import CategoryRepository

logger = logging.getLogger(__name__)


class CategoryServiceError(Exception):
    pass


class CategoryNotFoundError(CategoryServiceError):
    pass


class CategoryCreationError(CategoryServiceError):
    pass


class CategoryUpdateError(CategoryServiceError):
    pass


class CategoryService:
    def __init__(self, category_repository: CategoryRepository) -> None:
        self.category_repository = category_repository

    async def get_category_by_alias(self, alias: str) -> Category | None:
        return await self.category_repository.get_by_alias(alias)

    async def create_category(self, category: Category) -> Category:
        try:
            return await self.category_repository.create(category)
        except Exception as e:
            logger.error("Failed to create category: %s", str(e), exc_info=True)
            raise CategoryCreationError(f"Failed to create category: {str(e)}") from e
