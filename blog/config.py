"""config module."""

from os import environ, path

basedir = path.abspath(path.dirname(__file__))


class Config(object):
    CACHE_TYPE: str = "NullCache"
    PORT: str = environ.get("PORT") or "5555"
    SECRET_KEY: str = environ.get("SECRET_KEY") or "hard to guess string"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False
    YANDEX_VERIFICATION: str | None = environ.get("YANDEX_VERIFICATION", None)
    YANDEX_METRIKA: str = environ.get("YANDEX_METRIKA", "76938046")

    PAGE_CATEGORY: list[int] = [
        int(c) for c in environ.get("PAGE_CATEGORY", "0").split(",")
    ]


class DevelopmentConfig(Config):
    DEBUG: bool = True
    default_db_uri: str = f"sqlite:///{path.join(basedir, '../tmp/dev.db')}"
    SQLALCHEMY_DATABASE_URI: str = environ.get(
        "SQLALCHEMY_DATABASE_URI", default_db_uri
    )


class TestingConfig(Config):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    PAGE_CATEGORY: list[int] = [
        1,
    ]


class ProductionConfig(Config):
    DEBUG: bool = False
    default_db_uri: str = f"sqlite:///{path.join(basedir, '../tmp/prod.db')}"
    SQLALCHEMY_DATABASE_URI: str = environ.get(
        "SQLALCHEMY_DATABASE_URI", default_db_uri
    )
    CACHE_TYPE: str = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT: int = 300


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
