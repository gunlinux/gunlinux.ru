"""SqlAlchemy models."""
from typing import TYPE_CHECKING, List
import datetime
from blog.extensions import db
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


if TYPE_CHECKING:
    from blog.post.models import Post 


class User(db.Model):
    """orm model for users."""

    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    createdon: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    posts: Mapped[List["Post"]] = relationship()

    def __str__(self):
        return f'{self.name}'
