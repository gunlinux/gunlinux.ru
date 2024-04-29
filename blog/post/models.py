"""SqlAlchemy models."""
from typing import TYPE_CHECKING, List
import datetime
import markdown
from blog.extensions import db
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from blog.tags.models import posts_tags


if TYPE_CHECKING:
    from blog.category.models import Category
    from blog.tags.models import Tag
    from blog.user.models import User


class Post(db.Model):
    """orm model for blog post."""

    __tablename__ = 'posts'
    id: Mapped[int] = mapped_column(primary_key=True)
    pagetitle: Mapped[str]
    alias: Mapped[str] = mapped_column(nullable=False, unique=True)
    content: Mapped[str] = mapped_column(type_=db.Text)
    createdon: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    publishedon: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        nullable=True,
    )
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    user: Mapped["User"] = relationship(back_populates="posts")
    category: Mapped["Category"] = relationship(back_populates="posts")
    tags: Mapped[List["Tag"]] = relationship(secondary=posts_tags, back_populates="posts")

    @property
    def markdown(self):
        return markdown.markdown(self.content)

    def __str__(self):
        return f'{self.pagetitle}'
