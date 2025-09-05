"""SqlAlchemy models."""

from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from blog.extensions import db
from blog.infrastructure.database import get_users_table

if TYPE_CHECKING:
    pass


class User(UserMixin, db.Model):
    """SqlAlchemy model for users."""

    __table__ = get_users_table(db.metadata)

    posts = relationship("Post", back_populates="user")

    def set_password(self, password: str) -> None:
        """Set password hash."""
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password hash."""
        return check_password_hash(self.password or "", password)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.name}"
