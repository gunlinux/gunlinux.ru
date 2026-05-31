from typing import TYPE_CHECKING, override

from sqlalchemy.orm import Mapped, relationship

from app.infrastructure.database import get_categories_table
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


class Category(Base):
    __table__ = get_categories_table(Base.metadata)

    id: Mapped[int]
    title: Mapped[str | None]
    alias: Mapped[str | None]
    template: Mapped[str | None]
    page: Mapped[bool | None]

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="category")

    @override
    def __str__(self) -> str:
        return f"{self.title}"
