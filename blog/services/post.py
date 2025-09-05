"""Service layer for Post entities."""

from typing import List, Optional
from blog.repos.post import PostRepository
from blog.domain.post import Post
from blog.post.models import Post as PostORM
from blog.extensions import db
import sqlalchemy as sa


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

    def get_published_posts_orm(self) -> List[PostORM]:
        """Get all published posts as ORM models (for compatibility with views)."""
        domain_posts = self.get_published_posts()
        return [self._to_orm_model(post) for post in domain_posts]

    def get_post_by_alias_orm(self, alias: str) -> Optional[PostORM]:
        """Get a post by its alias as ORM model (for compatibility with views)."""
        domain_post = self.get_post_by_alias(alias)
        if domain_post:
            return self._to_orm_model(domain_post)
        return None

    def _to_orm_model(self, post: Post) -> PostORM:
        """Convert domain model to ORM model by loading from database."""
        if post.id:
            # Load the full ORM model from database to get relationships
            stmt = sa.select(PostORM).where(PostORM.id == post.id)
            post_orm = db.session.scalar(stmt)
            if post_orm:
                return post_orm

        # If we can't load from database, create a new instance
        post_orm = PostORM()
        post_orm.id = post.id or 0
        post_orm.pagetitle = post.pagetitle
        post_orm.alias = post.alias
        post_orm.content = post.content
        post_orm.createdon = post.createdon
        post_orm.publishedon = post.publishedon
        post_orm.category_id = post.category_id
        post_orm.user_id = post.user_id
        return post_orm
