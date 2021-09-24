"""[summary]."""
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from flaskext.markdown import Markdown
from flask_caching import Cache

db = SQLAlchemy()
admin_ext = Admin(base_template='admin/index.html', template_mode='bootstrap3')
md = Markdown
cache = Cache()
