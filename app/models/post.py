from datetime import datetime
from typing import TYPE_CHECKING, override

from sqlalchemy.orm import Mapped, relationship

from app.infrastructure.database import (
    get_icons_table,
    get_posts_table,
    get_posts_tags_table,
)
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.tag import Tag
    from app.models.user import User

MARKDOWN_EXTENSIONS = ["markdown.extensions.fenced_code"]


class Post(Base):
    __table__ = get_posts_table(Base.metadata)

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
        "Tag",
        secondary=get_posts_tags_table(Base.metadata),
        back_populates="posts",
    )

    @override
    def __str__(self) -> str:
        return f"{self.pagetitle}"


class Icon(Base):
    __table__ = get_icons_table(Base.metadata)

    id: Mapped[int]
    title: Mapped[str]
    url: Mapped[str]
    content: Mapped[str | None]

    @override
    def __str__(self) -> str:
        return f"{self.id} {self.title}"
