# blog/tags/models.py
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from blog.extensions import db
from blog.tags.association import posts_tags

if TYPE_CHECKING:
    from blog.post.models import Post


class Tag(db.Model):
    """orm model for blog post."""

    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    alias: Mapped[str] = mapped_column(unique=True)
    posts: Mapped[list["Post"]] = relationship(
        secondary=posts_tags, back_populates="tags"
    )

    def __str__(self):
        return f"{self.title}"
