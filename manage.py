#!/usr/bin/env python
import os
from pro import create_app, db
from pro.postb.models import Post

from flask_script import Manager, Shell

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)


def make_shell_context():
    return dict(app=app, db=db, Post=Post)
manager.add_command("shell", Shell(make_context=make_shell_context))


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


@manager.command
def list_routes():
    for rule in app.url_map.iter_rules():
        print(rule)


@manager.command
def dbinit():
    db.create_all()


if __name__ == '__main__':
    manager.run()
