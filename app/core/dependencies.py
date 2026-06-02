from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.session import get_db
from app.repositories.icon import IconRepository
from app.repositories.post import PostRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.services.icon import IconService
from app.services.post import PostService
from app.services.tag import TagService
from app.services.user import UserService

DB = Annotated[AsyncSession, Depends(get_db)]


def get_post_service(db: DB) -> PostService:
    return PostService(PostRepository(db))


def get_tag_service(db: DB) -> TagService:
    return TagService(TagRepository(db))


def get_user_service(db: DB) -> UserService:
    return UserService(UserRepository(db))


def get_icon_service(db: DB) -> IconService:
    return IconService(IconRepository(db))


PostServiceDep = Annotated[PostService, Depends(get_post_service)]
TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
IconServiceDep = Annotated[IconService, Depends(get_icon_service)]
