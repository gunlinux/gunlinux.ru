"""SqlAlchemy models."""

from datetime import datetime
from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from blog.extensions import db
from blog.infrastructure.database import get_users_table

if TYPE_CHECKING:
    from blog.post.models import Post


class User(UserMixin, db.Model):
    """SqlAlchemy model for users."""

    __table__ = get_users_table(db.metadata)

    # Type annotations for table columns
    id: Mapped[int]
    name: Mapped[str]
    password: Mapped[str | None]
    authenticated: Mapped[int | None]
    createdon: Mapped[datetime | None]

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user")

    def __init__(self, **kwargs):
        """Initialize a new User instance."""
        super().__init__(**kwargs)
        # Set default createdon if not provided
        if self.createdon is None:
            self.createdon = datetime.now()

    def set_password(self, password: str) -> None:
        """Set password hash."""
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password hash."""
        return check_password_hash(self.password or "", password)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name}"
