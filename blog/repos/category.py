"""Repository for Category entities."""

import sqlalchemy as sa
from typing import Any

from blog.extensions import db
from blog.category.models import Category as CategoryORM
from blog.domain.category import Category as CategoryDomain
from blog.domain.post import Post as PostDomain


class CategoryRepository:
    """Repository for Category entities."""

    def __init__(self, session: Any = None):
        self.session = session or db.session

    def get_category_orm_with_relationships(
        self, category_id: int
    ) -> CategoryORM | None:
        stmt = (
            sa.select(CategoryORM)
            .where(CategoryORM.id == category_id)
            .options(sa.orm.joinedload(CategoryORM.posts))
        )
        return self.session.scalar(stmt)

    def get_by_id(self, category_id: int) -> CategoryDomain | None:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == category_id)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            return self._to_domain_model(category_orm)
        return None

    def get_by_alias(self, alias: str) -> CategoryDomain | None:
        stmt = sa.select(CategoryORM).where(CategoryORM.alias == alias)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            return self._to_domain_model(category_orm)
        return None

    def get_all(self) -> list[CategoryDomain]:
        stmt = sa.select(CategoryORM)
        categories_orm = list(self.session.scalars(stmt).all())
        return [self._to_domain_model(category_orm) for category_orm in categories_orm]

    def get_categories_with_posts(self) -> list[CategoryDomain]:
        stmt = sa.select(CategoryORM).options(sa.orm.joinedload(CategoryORM.posts))
        categories_orm = list(self.session.scalars(stmt).unique().all())
        return [self._to_domain_model(category_orm) for category_orm in categories_orm]

    def create(self, category: CategoryDomain) -> CategoryDomain:
        category_orm = CategoryORM()
        category_orm.title = category.title
        category_orm.alias = category.alias
        # Handle the case where template might be None
        if category.template is not None:
            category_orm.template = category.template
        self.session.add(category_orm)
        self.session.flush()  # Get the ID without committing
        category.id = category_orm.id
        return category

    def update(self, category: CategoryDomain) -> CategoryDomain:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == category.id)
        category_orm = self.session.scalar(stmt)
        if not category_orm:
            raise ValueError(f"Category with id {category.id} not found")

        category_orm.title = category.title
        category_orm.alias = category.alias
        # Handle the case where template might be None
        if category.template is not None:
            category_orm.template = category.template
        self.session.flush()
        return category

    def delete(self, category_id: int) -> bool:
        stmt = sa.select(CategoryORM).where(CategoryORM.id == category_id)
        category_orm = self.session.scalar(stmt)
        if category_orm:
            self.session.delete(category_orm)
            return True
        return False

    def _to_domain_model(self, category_orm: CategoryORM) -> CategoryDomain:
        # Convert related posts if they exist
        posts = None
        if category_orm.posts:
            posts = [
                PostDomain(
                    id=post_orm.id,
                    pagetitle=post_orm.pagetitle or "",
                    alias=post_orm.alias or "",
                    content=post_orm.content or "",
                    createdon=post_orm.createdon,
                    publishedon=post_orm.publishedon,
                    category_id=post_orm.category_id,
                    user_id=post_orm.user_id,
                    user=None,  # Avoid circular references
                    category=None,  # Avoid circular references
                    tags=None,  # Avoid circular references
                )
                for post_orm in category_orm.posts
            ]

        return CategoryDomain(
            id=category_orm.id,
            title=category_orm.title or "",
            alias=category_orm.alias or "",
            template=category_orm.template,
            posts=posts,
        )
