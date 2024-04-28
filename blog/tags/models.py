from typing import List, TYPE_CHECKING

from sqlalchemy import ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from blog.extensions import db

if TYPE_CHECKING:
    from blog.post.models import Post


posts_tags = Table(
    'posts_tags',
    db.Model.metadata,
    Column("post_id", ForeignKey("posts.id")),
    Column("tag_id", ForeignKey("tags.id")),
)


class Tag(db.Model):
    """orm model for blog post."""

    __tablename__ = 'tags'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    alias: Mapped[str] = mapped_column(unique=True)
    posts: Mapped[List["Post"]] = relationship(secondary=posts_tags,
                                               back_populates="tags")

    def __str__(self):
        return f'{self.title}'
