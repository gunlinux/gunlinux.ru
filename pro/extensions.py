from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_debugtoolbar import DebugToolbarExtension


db = SQLAlchemy()
admin_ext = Admin(base_template='admin/index.html', template_mode='bootstrap3')
toolbar = DebugToolbarExtension()
