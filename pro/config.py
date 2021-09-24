"""config module."""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    """[summary].

    Args:
        object ([type]): [description]
    """
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    PORT = os.environ.get('PORT') or '5555'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    DEBUG = False 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False


class DevelopmentConfig(Config):
    """[summary].

    Args:
        Config ([type]): [description]
    """

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
        os.path.join(basedir, '../tmp/dev.db')


class TestingConfig(Config):
    """[summary].

    Args:
        Config ([type]): [description]
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + \
        os.path.join(basedir, '../tmp/test.db')


class ProductionConfig(Config):
    """[summary].

    Args:
        Config ([type]): [description]
    """

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '../tmp/data.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
