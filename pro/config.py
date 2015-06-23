import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    PORT = os.environ.get('PORT')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    DEBUG = True
    SERVER_NAME = os.environ.get('SERVER_NAME')
    EXTRA_DEBUG = bool(os.environ.get('EXTRA_DEBUG'))
    DEBUG_TB_ENABLED = EXTRA_DEBUG
    DEBUG_TB_PROFILER_ENABLED = EXTRA_DEBUG
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '../tmp/data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '../tmp/data-test.sqlite')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '../data.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
