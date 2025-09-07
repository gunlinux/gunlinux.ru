# blog/tags/models.py
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from blog.extensions import db
from blog.infrastructure.database import get_tags_table, get_posts_tags_table

if TYPE_CHECKING:
    from blog.post.models import Post


class Tag(db.Model):
    """orm model for blog tag."""

    __table__ = get_tags_table(db.metadata)

    # Type annotations for table columns
    id: Mapped[int]
    title: Mapped[str | None]
    alias: Mapped[str | None]

    posts: Mapped[list["Post"]] = relationship(
        "Post", secondary=get_posts_tags_table(db.metadata), back_populates="tags"
    )

    def __str__(self):
        return f"{self.title}"
