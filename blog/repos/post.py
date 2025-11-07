"""Repository for Post entities."""

import sqlalchemy as sa
from typing import Any, override

from blog.extensions import db
from blog.post.models import Post as PostORM
from blog.tags.models import Tag as TagORM
from blog.domain.post import Post as PostDomain
from blog.domain.tag import Tag as TagDomain
from blog.repos.base import BaseRepository


class PostRepository(BaseRepository[PostDomain, int]):
    """Repository for Post entities."""

    def __init__(self, session: Any = None):  # pyright: ignore[reportExplicitAny]
        self.session = session or db.session

    def get_post_with_relationships(self, post_id: int) -> PostDomain | None:
        """Get a post by ID with its relationships loaded.

        Note: This method loads relationships but doesn't include them in the domain model
        since we've removed relationship fields to avoid circular dependencies.
        """
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

    def get_tags_for_post(self, post_id: int) -> list[TagDomain]:
        """Get all tags associated with a specific post."""
        stmt = sa.select(TagORM).join(TagORM.posts).where(PostORM.id == post_id)
        tags_orm = list(self.session.scalars(stmt).all())
        return [self._tag_to_domain_model(tag_orm) for tag_orm in tags_orm]

    def get_posts_by_tag(self, tag_id: int) -> list[PostDomain]:
        """Get all posts associated with a specific tag."""
        stmt = sa.select(PostORM).join(PostORM.tags).where(TagORM.id == tag_id)
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def _tag_to_domain_model(self, tag_orm: TagORM) -> TagDomain:
        """Convert Tag ORM model to Tag domain model."""
        return TagDomain(
            id=tag_orm.id,
            title=tag_orm.title or "",
            alias=tag_orm.alias or "",
        )

    @override
    def get_by_id(self, id: int) -> PostDomain | None:
        stmt = sa.select(PostORM).where(PostORM.id == id)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            return self._to_domain_model(post_orm)
        return None

    def get_by_alias(self, alias: str) -> PostDomain | None:
        stmt = sa.select(PostORM).where(PostORM.alias == alias)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            return self._to_domain_model(post_orm)
        return None

    @override
    def get_all(self) -> list[PostDomain]:
        stmt = sa.select(PostORM)
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def get_published_posts(self) -> list[PostDomain]:
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

    def get_all_published_content(self) -> list[PostDomain]:
        """Get all published content including posts and pages."""
        stmt = (
            sa.select(PostORM)
            .where(PostORM.publishedon.isnot(None))
            .where(PostORM.category_id.isnot(1))
            .order_by(PostORM.publishedon.desc())
        )
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    def get_page_posts(self, page_category_ids: list[int]) -> list[PostDomain]:
        stmt = sa.select(PostORM).where(PostORM.category_id.in_(page_category_ids))
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

    @override
    def create(self, entity: PostDomain) -> PostDomain:
        post_orm = PostORM()
        post_orm.pagetitle = entity.pagetitle
        post_orm.alias = entity.alias
        post_orm.content = entity.content
        # Handle datetime fields that might be None
        if entity.createdon is not None:
            post_orm.createdon = entity.createdon
        if entity.publishedon is not None:
            post_orm.publishedon = entity.publishedon
        if entity.category_id is not None:
            post_orm.category_id = entity.category_id
        if entity.user_id is not None:
            post_orm.user_id = entity.user_id

        self.session.add(post_orm)
        self.session.flush()  # Get the ID without committing
        entity.id = post_orm.id
        return entity

    @override
    def update(self, entity: PostDomain) -> PostDomain:
        stmt = sa.select(PostORM).where(PostORM.id == entity.id)
        post_orm = self.session.scalar(stmt)
        if not post_orm:
            raise ValueError(f"Post with id {entity.id} not found")

        post_orm.pagetitle = entity.pagetitle
        post_orm.alias = entity.alias
        post_orm.content = entity.content
        # Handle datetime fields that might be None
        if entity.createdon is not None:
            post_orm.createdon = entity.createdon
        if entity.publishedon is not None:
            post_orm.publishedon = entity.publishedon
        if entity.category_id is not None:
            post_orm.category_id = entity.category_id
        if entity.user_id is not None:
            post_orm.user_id = entity.user_id
        self.session.flush()
        return entity

    @override
    def delete(self, id: int) -> bool:
        stmt = sa.select(PostORM).where(PostORM.id == id)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            self.session.delete(post_orm)
            return True
        raise ValueError(f"Post not found {id}")

    def _to_domain_model(self, post_orm: PostORM) -> PostDomain:
        return PostDomain(
            id=post_orm.id,
            pagetitle=post_orm.pagetitle or "",
            alias=post_orm.alias or "",
            content=post_orm.content or "",
            createdon=post_orm.createdon,
            publishedon=post_orm.publishedon,
            category_id=post_orm.category_id,
            user_id=post_orm.user_id,
        )
