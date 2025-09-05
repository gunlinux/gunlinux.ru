"""Service layer for Post entities."""

from typing import List, Optional
from blog.repos.post import PostRepository
from blog.domain.post import Post


class PostService:
    """Service layer for Post entities."""

    def __init__(self, post_repository: PostRepository):
        self.post_repository = post_repository

    def get_post_by_id(self, post_id: int) -> Optional[Post]:
        """Get a post by its ID."""
        return self.post_repository.get_by_id(post_id)

    def get_post_by_alias(self, alias: str) -> Optional[Post]:
        """Get a post by its alias."""
        return self.post_repository.get_by_alias(alias)

    def get_all_posts(self) -> List[Post]:
        """Get all posts."""
        return self.post_repository.get_all()

    def get_published_posts(self) -> List[Post]:
        """Get all published posts."""
        return self.post_repository.get_published_posts()

    def get_page_posts(self, page_category_ids: List[int]) -> List[Post]:
        """Get posts that are pages (in specific categories)."""
        return self.post_repository.get_page_posts(page_category_ids)

    def create_post(self, post: Post) -> Post:
        """Create a new post."""
        return self.post_repository.create(post)

    def update_post(self, post: Post) -> Post:
        """Update an existing post."""
        return self.post_repository.update(post)

    def delete_post(self, post_id: int) -> bool:
        """Delete a post by its ID."""
        return self.post_repository.delete(post_id)
