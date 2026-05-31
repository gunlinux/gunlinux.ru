import logging

from app.domain.post import Post
from app.domain.tag import Tag
from app.repositories.post import PostRepository

logger = logging.getLogger(__name__)


class PostServiceError(Exception):
    pass


class PostNotFoundError(PostServiceError):
    pass


class PostCreationError(PostServiceError):
    pass


class PostUpdateError(PostServiceError):
    pass


class PostService:
    def __init__(self, post_repository: PostRepository) -> None:
        self.post_repository = post_repository

    async def get_post_by_id(self, post_id: int) -> Post | None:
        return await self.post_repository.get_by_id(post_id)

    async def get_post_by_alias(self, alias: str) -> Post | None:
        return await self.post_repository.get_by_alias(alias)

    async def get_all_posts(self) -> list[Post]:
        return await self.post_repository.get_all()

    async def get_published_posts(self) -> list[Post]:
        return await self.post_repository.get_published_posts()

    async def get_all_published_content(self) -> list[Post]:
        return await self.post_repository.get_all_published_content()

    async def get_page_posts(self) -> list[Post]:
        return await self.post_repository.get_page_posts()

    async def get_posts_by_tag(self, tag_id: int) -> list[Post]:
        return await self.post_repository.get_posts_by_tag(tag_id)

    async def get_tags_for_post(self, post_id: int) -> list[Tag]:
        return await self.post_repository.get_tags_for_post(post_id)

    async def create_post(self, post: Post) -> Post:
        try:
            return await self.post_repository.create(post)
        except Exception as e:
            logger.error("Failed to create post: %s", str(e), exc_info=True)
            raise PostCreationError(f"Failed to create post: {str(e)}") from e

    async def update_post(self, post: Post) -> Post:
        try:
            return await self.post_repository.update(post)
        except ValueError as e:
            logger.error("Failed to update post: %s", str(e), exc_info=True)
            raise PostUpdateError(f"Failed to update post: {str(e)}") from e

    async def delete_post(self, post_id: int) -> bool:
        try:
            return await self.post_repository.delete(post_id)
        except Exception as e:
            logger.error("Failed to delete post %s: %s", post_id, str(e), exc_info=True)
            raise PostNotFoundError(f"Failed to delete post: {str(e)}") from e
