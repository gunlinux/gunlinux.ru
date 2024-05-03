"""SqlAlchemy models."""
from typing import TYPE_CHECKING, List
import datetime
from blog.extensions import db, login_manager
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


if TYPE_CHECKING:
    from blog.post.models import Post


@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class User(UserMixin, db.Model):
    """orm model for users."""

    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    password: Mapped[str]
    authenticated: Mapped[bool] = mapped_column(default=False, nullable=True)
    createdon: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    posts: Mapped[List["Post"]] = relationship()

    def is_authenticated(self):  # pyright: ignore[ reportIncompatibleMethodOverride]
        return self.authenticated

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __str__(self):
        return f'{self.name}'
