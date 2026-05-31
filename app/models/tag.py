from typing import TYPE_CHECKING, override

from sqlalchemy.orm import Mapped, relationship

from app.infrastructure.database import get_posts_tags_table, get_tags_table
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


class Tag(Base):
    __table__ = get_tags_table(Base.metadata)

    id: Mapped[int]
    title: Mapped[str | None]
    alias: Mapped[str | None]

    posts: Mapped[list["Post"]] = relationship(
        "Post",
        secondary=get_posts_tags_table(Base.metadata),
        back_populates="tags",
    )

    @override
    def __str__(self) -> str:
        return f"{self.title}"
