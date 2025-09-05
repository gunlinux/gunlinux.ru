# blog/posts/models.py
import typing
from typing import TYPE_CHECKING

import markdown
from sqlalchemy.orm import relationship

from blog.extensions import db
from blog.infrastructure.database import get_posts_table, get_posts_tags_table

if TYPE_CHECKING:
    pass


MARKDOWN_EXTENSIONS = ["markdown.extensions.fenced_code"]


class Post(db.Model):
    """orm model for blog post."""

    __table__ = get_posts_table(db.metadata)

    user = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    tags = relationship(
        "Tag", secondary=get_posts_tags_table(db.metadata), back_populates="posts"
    )

    @property
    def markdown(self):
        return markdown.markdown(self.content, extensions=MARKDOWN_EXTENSIONS)

    @typing.override
    def __str__(self):
        return f"{self.pagetitle}"


class Icon(db.Model):
    """orm model for icons."""

    __tablename__ = "icons"  # pyright: ignore[reportUnannotatedClassAttribute]

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, unique=True)
    url = db.Column(db.String(255), nullable=False, unique=True)
    content = db.Column(db.Text)

    def __str__(self):
        return f"{self.id} {self.title}"
