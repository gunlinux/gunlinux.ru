from datetime import datetime
from typing import TYPE_CHECKING, override

import bcrypt as _bcrypt
from sqlalchemy.orm import Mapped, relationship

from app.infrastructure.database import get_users_table
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# Exposed for tests that need to pre-hash passwords
pwd_context = type(
    "_PwdContext",
    (),
    {"hash": staticmethod(_hash), "verify": staticmethod(_verify)},
)()


class User(Base):
    __table__ = get_users_table(Base.metadata)

    id: Mapped[int]
    name: Mapped[str]
    password: Mapped[str | None]
    authenticated: Mapped[int | None]
    createdon: Mapped[datetime | None]

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user")

    def set_password(self, password: str) -> None:
        self.password = _hash(password)

    def check_password(self, password: str) -> bool:
        return _verify(password, self.password or "")

    @override
    def __str__(self) -> str:
        return f"{self.name}"
