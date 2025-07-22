"""[summary]."""

import logging
import os

from dotenv import load_dotenv
from flask import Flask

from blog.admin import create_admin
from blog.config import config
from blog.extensions import admin_ext, cache, db, login_manager, migrate, flask_sitemap
from blog.post.views import post
from blog.tags.views import tagsb
from blog.user.views import user_blueprint

load_dotenv()
logger = logging.getLogger(__name__)


def configure_extensions(app):
    """Configures the extensions."""
    db.init_app(app)
    admin_ext.init_app(app)
    cache.init_app(app)
    migrate.init_app(app=app, db=db)
    login_manager.init_app(app=app)
    login_manager.login_view = "userb.index"  # type: ignore
    flask_sitemap.init_app(app)


def create_app():
    app = Flask(__name__)
    env = os.environ.get("FLASK_ENV", "development")
    logger.debug("current FLASK_ENV %s", env)
    app.config.from_object(config.get(env))
    configure_extensions(app)
    if not app.config["TESTING"]:
        create_admin(admin_ext)
    app.register_blueprint(post)
    app.register_blueprint(tagsb)
    app.register_blueprint(user_blueprint)
    return app
