#!/usr/bin/env python
# -*- coding: utf-8 -*-
from config import config
from flask import Flask
from pro.extensions import toolbar, db, admin_ext
from flask_markdown import markdown
from pro.post.views import post
from pro.admin import create_admin


def configure_extensions(app):
    """Configures the extensions."""
    db.init_app(app)
    admin_ext.init_app(app)
    toolbar.init_app(app)
    markdown(app)


def configure_blueprints(app):
    app.register_blueprint(post)


def create_app(config_name):
    """ Flask app builder. """
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    configure_extensions(app)
    configure_blueprints(app)
    if not app.config['TESTING']:
        create_admin(admin_ext)
    return app
