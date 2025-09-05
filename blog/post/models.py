# blog/posts/models.py
import datetime
import typing
from typing import TYPE_CHECKING

import markdown
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from blog.extensions import db
from blog.tags.association import posts_tags

if TYPE_CHECKING:
    from blog.category.models import Category
    from blog.tags.models import Tag
    from blog.user.models import User


MARKDOWN_EXTENSIONS = ["markdown.extensions.fenced_code"]


class Post(db.Model):
    """orm model for blog post."""

    __tablename__ = "posts"  # pyright: ignore[reportUnannotatedClassAttribute]

    id: Mapped[int] = mapped_column(primary_key=True)
    pagetitle: Mapped[str] = mapped_column(nullable=False, unique=False)
    alias: Mapped[str] = mapped_column(nullable=False, unique=True)
    content: Mapped[str] = mapped_column(type_=Text)
    createdon: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    publishedon: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User"] = relationship(back_populates="posts")
    category: Mapped["Category"] = relationship(back_populates="posts")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=posts_tags, back_populates="posts"
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

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False, unique=True)

    url: Mapped[str] = mapped_column(nullable=False, unique=True)
    content: Mapped[str] = mapped_column(type_=Text)

    @typing.override
    def __str__(self):
        return f"{self.id} {self.title}"
