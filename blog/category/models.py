# blog/category/models.py
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from blog.extensions import db
from blog.infrastructure.database import get_categories_table

if TYPE_CHECKING:
    from blog.post.models import Post


class Category(db.Model):
    """orm model for blog category."""

    __table__ = get_categories_table(db.metadata)

    # Type annotations for table columns
    id: Mapped[int]
    title: Mapped[str | None]
    alias: Mapped[str | None]
    template: Mapped[str | None]

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="category")

    def __str__(self):
        return f"{self.title}"
