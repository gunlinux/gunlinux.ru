"""SqlAlchemy models."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import relationship

from blog.extensions import db
from blog.infrastructure.database import get_categories_table

if TYPE_CHECKING:
    from blog.post.models import Post


class Category(db.Model):
    """orm model for blog post."""

    __table__ = get_categories_table(db.metadata)
    
    posts = relationship("Post", back_populates="category")

    def __str__(self):
        return f"Category(id={self.id}, title={self.title}, template={self.template})"
