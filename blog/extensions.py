"""[summary]."""
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_migrate import Migrate

db = SQLAlchemy()
admin_ext = Admin(base_template='admin/index.html', template_mode='bootstrap3')
cache = Cache()
migrate = Migrate()
