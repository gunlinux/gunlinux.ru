"""Repository for Post entities."""

import sqlalchemy as sa
from typing import Any

from blog.extensions import db
from blog.post.models import Post as PostORM
from blog.tags.models import Tag as TagORM
from blog.domain.post import Post as PostDomain
from blog.domain.user import User as UserDomain
from blog.domain.category import Category as CategoryDomain
from blog.domain.tag import Tag as TagDomain


class PostRepository:
    """Repository for Post entities."""

    def __init__(self, session: Any = None):
        self.session = session or db.session

    def get_post_with_relationships(self, post_id: int) -> PostDomain | None:
        """Get a post domain model with all its relationships loaded."""
        stmt = (
            sa.select(PostORM)
            .where(PostORM.id == post_id)
            .options(
                sa.orm.joinedload(PostORM.user),
                sa.orm.joinedload(PostORM.category),
                sa.orm.joinedload(PostORM.tags),
            )
        )
        post_orm = self.session.scalar(stmt)
        if post_orm:
            return self._to_domain_model(post_orm)
        return None

    def get_by_id(self, post_id: int) -> PostDomain | None:
        """Get a post by its ID."""
        stmt = sa.select(PostORM).where(PostORM.id == post_id)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            return self._to_domain_model(post_orm)
        return None

    def get_by_alias(self, alias: str) -> PostDomain | None:
        """Get a post by its alias."""
        stmt = sa.select(PostORM).where(PostORM.alias == alias)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            return self._to_domain_model(post_orm)
        return None

    def get_all(self) -> list[PostDomain]:
        """Get all posts."""
        stmt = sa.select(PostORM)
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def get_published_posts(self) -> list[PostDomain]:
        """Get all published posts ordered by published date."""
        stmt = (
            sa.select(PostORM)
            .where(
                PostORM.publishedon.isnot(None),
                PostORM.category_id.is_(None),
            )
            .order_by(PostORM.publishedon.desc())
        )
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def get_page_posts(self, page_category_ids: list[int]) -> list[PostDomain]:
        """Get posts that are pages (in specific categories)."""
        stmt = sa.select(PostORM).where(PostORM.category_id.in_(page_category_ids))
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def create(self, post: PostDomain) -> PostDomain:
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

        # Handle tags relationship if provided
        if post.tags:
            # Find existing Tag ORM models based on the domain Tag models
            tag_ids = [tag.id for tag in post.tags if tag.id is not None]
            if tag_ids:
                stmt = sa.select(TagORM).where(TagORM.id.in_(tag_ids))
                existing_tags = list(self.session.scalars(stmt).all())
                post_orm.tags = existing_tags

        self.session.add(post_orm)
        self.session.flush()  # Get the ID without committing
        post.id = post_orm.id
        return post

    def update(self, post: PostDomain) -> PostDomain:
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

    def _to_domain_model(self, post_orm: PostORM) -> PostDomain:
        """Convert ORM model to domain model."""
        # Convert related user if it exists
        user = None
        if post_orm.user:
            user = UserDomain(
                id=post_orm.user.id,
                name=post_orm.user.name or "",
                password=post_orm.user.password or "",
                authenticated=bool(post_orm.user.authenticated)
                if post_orm.user.authenticated is not None
                else False,
                createdon=post_orm.user.createdon,
                posts=None,  # Avoid circular references
            )

        # Convert related category if it exists
        category = None
        if post_orm.category:
            category = CategoryDomain(
                id=post_orm.category.id,
                title=post_orm.category.title or "",
                alias=post_orm.category.alias or "",
                template=post_orm.category.template,
                posts=None,  # Avoid circular references
            )

        # Convert related tags if they exist
        tags = None
        if post_orm.tags:
            tags = [
                TagDomain(
                    id=tag_orm.id,
                    title=tag_orm.title or "",
                    alias=tag_orm.alias or "",
                    posts=None,  # Avoid circular references
                )
                for tag_orm in post_orm.tags
            ]

        return PostDomain(
            id=post_orm.id,
            pagetitle=post_orm.pagetitle or "",
            alias=post_orm.alias or "",
            content=post_orm.content or "",
            createdon=post_orm.createdon,
            publishedon=post_orm.publishedon,
            category_id=post_orm.category_id,
            user_id=post_orm.user_id,
            user=user,
            category=category,
            tags=tags,
        )
