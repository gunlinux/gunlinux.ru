"""Repository for Post entities."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from blog.extensions import db
from blog.post.models import Post as PostORM
from blog.domain.post import Post


class PostRepository:
    """Repository for Post entities."""

    def __init__(self, session: Session | None = None):
        self.session = session or db.session

    def get_by_id(self, post_id: int) -> Post | None:
        """Get a post by its ID."""
        stmt = sa.select(PostORM).where(PostORM.id == post_id)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            return self._to_domain_model(post_orm)
        return None

    def get_by_alias(self, alias: str) -> Post | None:
        """Get a post by its alias."""
        stmt = sa.select(PostORM).where(PostORM.alias == alias)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            return self._to_domain_model(post_orm)
        return None

    def get_all(self) -> list[Post]:
        """Get all posts."""
        stmt = sa.select(PostORM)
        posts_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def get_published_posts(self) -> list[Post]:
        """Get all published posts ordered by published date."""
        stmt = (
            sa.select(PostORM)
            .where(
                PostORM.publishedon.isnot(None),
                PostORM.category_id.is_(None),
            )
            .order_by(PostORM.publishedon.desc())
        )
        posts_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def get_page_posts(self, page_category_ids: list[int]) -> list[Post]:
        """Get posts that are pages (in specific categories)."""
        stmt = sa.select(PostORM).where(PostORM.category_id.in_(page_category_ids))
        posts_orm = self.session.scalars(stmt).all()
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def create(self, post: Post) -> Post:
        """Create a new post."""
        post_orm = PostORM()
        post_orm.pagetitle = post.pagetitle
        post_orm.alias = post.alias
        post_orm.content = post.content
        # Handle datetime fields that might be None
        if post.createdon is not None:
            post_orm.createdon = post.createdon
        if post.publishedon is not None:
            post_orm.publishedon = post.publishedon
        if post.category_id is not None:
            post_orm.category_id = post.category_id
        if post.user_id is not None:
            post_orm.user_id = post.user_id
        self.session.add(post_orm)
        self.session.flush()  # Get the ID without committing
        post.id = post_orm.id
        return post

    def update(self, post: Post) -> Post:
        """Update an existing post."""
        stmt = sa.select(PostORM).where(PostORM.id == post.id)
        post_orm = self.session.scalar(stmt)
        if not post_orm:
            raise ValueError(f"Post with id {post.id} not found")

        post_orm.pagetitle = post.pagetitle
        post_orm.alias = post.alias
        post_orm.content = post.content
        # Handle datetime fields that might be None
        if post.createdon is not None:
            post_orm.createdon = post.createdon
        if post.publishedon is not None:
            post_orm.publishedon = post.publishedon
        if post.category_id is not None:
            post_orm.category_id = post.category_id
        if post.user_id is not None:
            post_orm.user_id = post.user_id
        self.session.flush()
        return post

    def delete(self, post_id: int) -> bool:
        """Delete a post by its ID."""
        stmt = sa.select(PostORM).where(PostORM.id == post_id)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            self.session.delete(post_orm)
            return True
        return False

    def _to_domain_model(self, post_orm: PostORM) -> Post:
        """Convert ORM model to domain model."""
        return Post(
            id=post_orm.id,
            pagetitle=post_orm.pagetitle,
            alias=post_orm.alias,
            content=post_orm.content,
            createdon=post_orm.createdon,
            publishedon=post_orm.publishedon,
            category_id=post_orm.category_id,
            user_id=post_orm.user_id,
        )
