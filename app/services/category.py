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

    async def get_category_by_id(self, category_id: int) -> Category | None:
        return await self.category_repository.get_by_id(category_id)

    async def get_category_by_alias(self, alias: str) -> Category | None:
        return await self.category_repository.get_by_alias(alias)

    async def get_all_categories(self) -> list[Category]:
        return await self.category_repository.get_all()

    async def create_category(self, category: Category) -> Category:
        try:
            return await self.category_repository.create(category)
        except Exception as e:
            logger.error("Failed to create category: %s", str(e), exc_info=True)
            raise CategoryCreationError(f"Failed to create category: {str(e)}") from e

    async def update_category(self, category: Category) -> Category:
        try:
            return await self.category_repository.update(category)
        except ValueError as e:
            logger.error("Failed to update category: %s", str(e), exc_info=True)
            raise CategoryUpdateError(f"Failed to update category: {str(e)}") from e

    async def delete_category(self, category_id: int) -> bool:
        try:
            return await self.category_repository.delete(category_id)
        except Exception as e:
            logger.error(
                "Failed to delete category %s: %s", category_id, str(e), exc_info=True
            )
            return False
