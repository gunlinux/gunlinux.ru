import logging
from blog.repos.post import PostRepository
from blog.domain.post import Post


logger = logging.getLogger(__name__)


class PostServiceError(Exception):
    """Base exception for PostService errors."""

    pass


class PostService:
    """Service layer for Post entities."""

    def __init__(self, post_repository: PostRepository):
        self.post_repository = post_repository

    def get_post_by_id(self, post_id: int) -> Post | None:
        return self.post_repository.get_by_id(post_id)

    def get_post_by_alias(self, alias: str) -> Post | None:
        return self.post_repository.get_by_alias(alias)

    def get_all_posts(self) -> list[Post]:
        return self.post_repository.get_all()

    def get_published_posts(self) -> list[Post]:
        return self.post_repository.get_published_posts()

    def get_page_posts(self, page_category_ids: list[int]) -> list[Post]:
        return self.post_repository.get_page_posts(page_category_ids)

    def create_post(self, post: Post) -> Post:
        try:
            return self.post_repository.create(post)
        except Exception as e:
            # Re-raise as a more specific exception for the service layer
            raise PostServiceError(f"Failed to create post: {str(e)}") from e

    def update_post(self, post: Post) -> Post:
        try:
            return self.post_repository.update(post)
        except ValueError as e:
            # Re-raise as a more specific exception for the service layer
            raise PostServiceError(f"Failed to update post: {str(e)}") from e

    def delete_post(self, post_id: int) -> bool:
        try:
            return self.post_repository.delete(post_id)
        except Exception as e:
            # Log the error with details
            logger.error(
                f"Failed to delete post with id {post_id}: {str(e)}", exc_info=True
            )
            # Re-raise as a more specific exception for the service layer
            raise PostServiceError(
                f"Failed to delete post with id {post_id}: {str(e)}"
            ) from e
