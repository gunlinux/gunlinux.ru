import logging

from app.domain.user import User
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class UserServiceError(Exception):
    pass


class UserNotFoundError(UserServiceError):
    pass


class UserCreationError(UserServiceError):
    pass


class UserUpdateError(UserServiceError):
    pass


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self.user_repository.get_by_id(user_id)

    async def get_user_by_name(self, name: str) -> User | None:
        return await self.user_repository.get_by_name(name)

    async def get_all_users(self) -> list[User]:
        return await self.user_repository.get_all()

    async def authenticate_user(self, name: str, password: str) -> User | None:
        return await self.user_repository.authenticate(name, password)

    async def create_user(self, user: User) -> User:
        try:
            return await self.user_repository.create(user)
        except Exception as e:
            logger.error("Failed to create user: %s", str(e), exc_info=True)
            raise UserCreationError(f"Failed to create user: {str(e)}") from e

    async def update_user(self, user: User) -> User:
        try:
            return await self.user_repository.update(user)
        except ValueError as e:
            logger.error("Failed to update user: %s", str(e), exc_info=True)
            raise UserUpdateError(f"Failed to update user: {str(e)}") from e

    async def delete_user(self, user_id: int) -> bool:
        try:
            return await self.user_repository.delete(user_id)
        except Exception as e:
            logger.error("Failed to delete user %s: %s", user_id, str(e), exc_info=True)
            return False
