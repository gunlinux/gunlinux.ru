#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_debugtoolbar import DebugToolbarExtension
from flask_markdown import markdown

from config import config


db = SQLAlchemy()
flask_admin = Admin(
    base_template='admin/index.html',
    template_mode='bootstrap3')
toolbar = DebugToolbarExtension()


def create_app(config_name):
    """ Flask app builder. """
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    db.init_app(app)
    flask_admin.init_app(app)
    toolbar.init_app(app)
    markdown(app)
    from .postb import postb as posts_blueprint
    app.register_blueprint(posts_blueprint)
    import admin

    return app
