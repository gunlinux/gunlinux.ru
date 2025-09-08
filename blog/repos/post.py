"""Repository for Post entities."""

import sqlalchemy as sa
from typing import Any, List, Optional

from blog.extensions import db
from blog.post.models import Post as PostORM
from blog.tags.models import Tag as TagORM
from blog.domain.post import Post as PostDomain
from blog.domain.user import User as UserDomain
from blog.domain.category import Category as CategoryDomain
from blog.domain.tag import Tag as TagDomain
from blog.repos.base import BaseRepository


class PostRepository(BaseRepository[PostDomain, int]):
    """Repository for Post entities."""

    def __init__(self, session: Any = None):
        self.session = session or db.session

    def get_post_with_relationships(self, post_id: int) -> PostDomain | None:
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

    def get_by_id(self, id: int) -> Optional[PostDomain]:
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

    def get_all(self) -> List[PostDomain]:
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

    def get_page_posts(self, page_category_ids: list[int]) -> list[PostDomain]:
        stmt = sa.select(PostORM).where(PostORM.category_id.in_(page_category_ids))
        posts_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(post_orm) for post_orm in posts_orm]

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

        # Handle tags relationship if provided
        if entity.tags:
            # Find existing Tag ORM models based on the domain Tag models
            tag_ids = [tag.id for tag in entity.tags if tag.id is not None]
            if tag_ids:
                stmt = sa.select(TagORM).where(TagORM.id.in_(tag_ids))
                existing_tags = list(self.session.scalars(stmt).all())
                post_orm.tags = existing_tags

        self.session.add(post_orm)
        self.session.flush()  # Get the ID without committing
        entity.id = post_orm.id
        return entity

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

    def delete(self, id: int) -> bool:
        stmt = sa.select(PostORM).where(PostORM.id == id)
        post_orm = self.session.scalar(stmt)
        if post_orm:
            self.session.delete(post_orm)
            return True
        return False

    def _to_domain_model(self, post_orm: PostORM) -> PostDomain:
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
