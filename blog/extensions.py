"""[summary]."""

from flask_admin import Admin
from flask_caching import Cache
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
admin_ext = Admin(base_template="admin/index.html", template_mode="bootstrap3")
cache = Cache()
migrate = Migrate()
login_manager: LoginManager = LoginManager()
