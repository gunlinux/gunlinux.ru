"""config module."""
from os import path, environ


basedir = path.abspath(path.dirname(__file__))


class Config(object):

    CACHE_TYPE = "NullCache"
    PORT = environ.get("PORT") or "5555"
    SECRET_KEY = environ.get("SECRET_KEY") or "hard to guess string"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False


class DevelopmentConfig(Config):

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{path.join(basedir, "../tmp/dev.db")}'


class TestingConfig(Config):

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):

    SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI", None)
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
