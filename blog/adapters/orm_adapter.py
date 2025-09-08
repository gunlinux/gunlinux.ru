"""Adapters for handling ORM model exposure in special cases.

This module provides adapters that handle the conversion between domain models and ORM models
for special cases where ORM models need to be exposed directly, keeping the service layer clean.
"""

import sqlalchemy as sa
from typing import List, Optional

from blog.extensions import db
from blog.post.models import Post as PostORM, Icon as IconORM
from blog.category.models import Category as CategoryORM
from blog.tags.models import Tag as TagORM
from blog.user.models import User as UserORM


class ORMAdapter:
    """Adapter for handling ORM model exposure in special cases."""

    def __init__(self):
        self.session = db.session

    # Icon ORM adapters
    def get_icon_orm_by_id(self, icon_id: int) -> Optional[IconORM]:
        """Get an icon ORM model by its ID.
        
        Args:
            icon_id: The ID of the icon to retrieve
            
        Returns:
            IconORM instance if found, None otherwise
        """
        stmt = sa.select(IconORM).where(IconORM.id == icon_id)
        return self.session.scalar(stmt)

    def get_all_icons_orm(self) -> List[IconORM]:
        """Get all icons as ORM models.
        
        Returns:
            List of IconORM instances
        """
        stmt = sa.select(IconORM)
        return list(self.session.scalars(stmt).all())

    # Category ORM adapters
    def get_category_orm_with_relationships(self, category_id: int) -> Optional[CategoryORM]:
        """Get a category ORM model with its relationships loaded.
        
        Args:
            category_id: The ID of the category to retrieve
            
        Returns:
            CategoryORM instance with relationships loaded if found, None otherwise
        """
        stmt = (
            sa.select(CategoryORM)
            .where(CategoryORM.id == category_id)
            .options(sa.orm.joinedload(CategoryORM.posts))
        )
        return self.session.scalar(stmt)

    # Tag ORM adapters
    def get_tag_orm_with_relationships(self, tag_id: int) -> Optional[TagORM]:
        """Get a tag ORM model with its relationships loaded.
        
        Args:
            tag_id: The ID of the tag to retrieve
            
        Returns:
            TagORM instance with relationships loaded if found, None otherwise
        """
        stmt = (
            sa.select(TagORM)
            .where(TagORM.id == tag_id)
            .options(sa.orm.joinedload(TagORM.posts))
        )
        return self.session.scalar(stmt)

    # User ORM adapters (for Flask-Login)
    def get_user_orm_by_id(self, user_id: int) -> Optional[UserORM]:
        """Get a user ORM model by its ID.
        
        Args:
            user_id: The ID of the user to retrieve
            
        Returns:
            UserORM instance if found, None otherwise
        """
        stmt = sa.select(UserORM).where(UserORM.id == user_id)
        return self.session.scalar(stmt)

    def get_user_orm_by_name(self, name: str) -> Optional[UserORM]:
        """Get a user ORM model by its name.
        
        Args:
            name: The name of the user to retrieve
            
        Returns:
            UserORM instance if found, None otherwise
        """
        stmt = sa.select(UserORM).where(UserORM.name == name)
        return self.session.scalar(stmt)