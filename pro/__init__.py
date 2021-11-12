"""[summary]."""

import unittest

import click
from flask import Flask
from flask.cli import with_appcontext


from pro.admin import create_admin
from pro.config import config
from pro.extensions import admin_ext, db, md, cache
from pro.post.views import post


@click.command('dbinit')
@with_appcontext
def cli_dbinit():
    db.create_all()


@click.command('test')
def cli_test():
    """Run the unit tests."""
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


def configure_extensions(app):
    """Configures the extensions."""
    db.init_app(app)
    admin_ext.init_app(app)
    md(app)
    cache.init_app(app)


def create_app():
    app = Flask(__name__)
    app.config.from_object(config[app.config['ENV']])
    configure_extensions(app)
    app.cli.add_command(cli_dbinit)
    app.cli.add_command(cli_test)
    if not app.config['TESTING']:
        create_admin(admin_ext)
    app.register_blueprint(post)

    return app
