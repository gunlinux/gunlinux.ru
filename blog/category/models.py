"""SqlAlchemy models."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from blog.extensions import db

if TYPE_CHECKING:
    from blog.post.models import Post


class Category(db.Model):
    """orm model for blog post."""

    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(default="")
    alias: Mapped[str] = mapped_column(unique=True)
    posts: Mapped[list["Post"]] = relationship()
    template: Mapped[str | None] = mapped_column(nullable=True)

    def __str__(self):
        return f"Category(id={self.id}, title={self.title}, template={self.template})"
