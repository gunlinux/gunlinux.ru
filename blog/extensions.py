"""[summary]."""
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from flask_markdown import Markdown
from flask_caching import Cache
from flask_migrate import Migrate

db = SQLAlchemy()
admin_ext = Admin(base_template='admin/index.html', template_mode='bootstrap3')
md = Markdown()
cache = Cache()
migrate = Migrate()
