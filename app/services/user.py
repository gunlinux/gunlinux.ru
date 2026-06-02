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

    async def authenticate_user(self, name: str, password: str) -> User | None:
        return await self.user_repository.authenticate(name, password)

    async def create_user(self, user: User) -> User:
        try:
            return await self.user_repository.create(user)
        except Exception as e:
            logger.error("Failed to create user: %s", str(e), exc_info=True)
            raise UserCreationError(f"Failed to create user: {str(e)}") from e
