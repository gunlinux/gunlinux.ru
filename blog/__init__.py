"""[summary]."""

import os
import logging
import sqlalchemy as sa

from flask import Flask
from dotenv import load_dotenv

from blog.admin import create_admin
from blog.config import config
from blog.extensions import db, cache, migrate, admin_ext, login_manager
from blog.post.views import post
from blog.tags.views import tagsb
from blog.user.views import user_blueprint
from blog.user.models import User


load_dotenv()
logger = logging.getLogger(__name__)


def create_admin_user(app):
    blog_admin = os.environ.get('BLOG_ADMIN')
    blog_password = os.environ.get('BLOG_PASSWORD')
    if not blog_admin or not blog_password:
        print('there is no admin')
        return
    with app.app_context():
        row = db.session.execute(sa.select(User).where(User.name == blog_admin)).first()
        if row:
            print('found user reseting pass')
            user = row[0]
            user.set_password(blog_password)
            db.session.add(user)
            db.session.commit()
            return
        print('new user')
        user = User()
        user.name = blog_admin
        user.set_password(blog_password)
        db.session.add(user)
        db.session.commit()


def configure_extensions(app):
    """Configures the extensions."""
    db.init_app(app)
    admin_ext.init_app(app)
    cache.init_app(app)
    migrate.init_app(app=app, db=db)
    login_manager.init_app(app=app)
    login_manager.login_view = 'userb.index'


def create_app():
    app = Flask(__name__)
    env = os.environ.get('FLASK_ENV', 'development')
    logger.debug('current FLASK_ENV %s', env)
    app.config.from_object(config.get(env))
    configure_extensions(app)
    if not app.config['TESTING']:
        create_admin(admin_ext)
    app.register_blueprint(post)
    app.register_blueprint(tagsb)
    app.register_blueprint(user_blueprint)
    create_admin_user(app)
    return app
