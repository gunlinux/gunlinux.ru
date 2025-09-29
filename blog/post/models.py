from datetime import datetime
from typing import TYPE_CHECKING, override

import markdown
from sqlalchemy.orm import Mapped, relationship

from blog.extensions import db
from blog.infrastructure.database import get_posts_table, get_posts_tags_table

if TYPE_CHECKING:
    from blog.category.models import Category
    from blog.user.models import User
    from blog.tags.models import Tag


MARKDOWN_EXTENSIONS = ["markdown.extensions.fenced_code"]


class Post(db.Model):
    """orm model for blog post."""

    __table__ = get_posts_table(db.metadata)

    # Type annotations for table columns
    id: Mapped[int]
    pagetitle: Mapped[str]
    alias: Mapped[str]
    content: Mapped[str | None]
    createdon: Mapped[datetime | None]
    publishedon: Mapped[datetime | None]
    category_id: Mapped[int | None]
    user_id: Mapped[int | None]

    user: Mapped["User"] = relationship("User", back_populates="posts")
    category: Mapped["Category"] = relationship("Category", back_populates="posts")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=get_posts_tags_table(db.metadata), back_populates="posts"
    )

    @property
    def markdown(self):
        return markdown.markdown(self.content or "", extensions=MARKDOWN_EXTENSIONS)

    @override
    def __str__(self):
        return f"{self.pagetitle}"


class Icon(db.Model):
    """orm model for icons."""

    __tablename__ = "icons"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    title: Mapped[str] = db.Column(db.String(255), nullable=False, unique=True)
    url: Mapped[str] = db.Column(db.String(255), nullable=False, unique=True)
    content: Mapped[str | None] = db.Column(db.Text)

    @override
    def __str__(self):
        return f"{self.id} {self.title}"
