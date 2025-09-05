"""SqlAlchemy models."""

import datetime
from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash

from blog.extensions import db, login_manager
from blog.infrastructure.database import get_users_table

if TYPE_CHECKING:
    from blog.post.models import Post


@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class User(UserMixin, db.Model):
    """orm model for users."""

    __table__ = get_users_table(db.metadata)
    
    posts = relationship("Post", back_populates="user")

    def is_authenticated(self):  # pyright: ignore[ reportIncompatibleMethodOverride]
        return self.authenticated

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __str__(self):
        return f"{self.name}"
