"""Blog application initialization."""

import logging
import os

from dotenv import load_dotenv
from flask import Flask

from blog.admin import create_admin
from blog.config import config
from blog.config_validator import validate_config, ConfigValidationError
from blog.extensions import admin_ext, cache, db, login_manager, migrate, flask_sitemap
from blog.post.views import post
from blog.tags.views import tags
from blog.user.views import user

load_dotenv()
logger = logging.getLogger(__name__)


def configure_extensions(app: Flask) -> None:
    """Configures the extensions."""
    db.init_app(app)
    admin_ext.init_app(app)
    cache.init_app(app)
    migrate.init_app(app=app, db=db)
    login_manager.init_app(app=app)
    login_manager.login_view = "user.login"
    flask_sitemap.init_app(app)


def register_commands(app: Flask) -> None:
    """Register custom CLI commands."""
    from blog.commands import init_app

    init_app(app)


def validate_application_config(app: Flask) -> None:
    """Validate the application configuration at startup.

    Args:
        app: The Flask application instance

    Raises:
        ConfigValidationError: If configuration validation fails
    """
    try:
        # Validate the configuration
        warnings = validate_config(app.config)

        # Log any warnings
        for warning in warnings:
            logger.warning("Configuration warning: %s", warning)

        logger.info("Application configuration validated successfully")

    except ConfigValidationError as e:
        logger.error("Configuration validation failed: %s", str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error during configuration validation: %s", str(e))
        raise ConfigValidationError(f"Configuration validation failed: {str(e)}") from e


def create_app(init_admin: bool = False) -> Flask:
    app = Flask(__name__)
    env = os.environ.get("FLASK_ENV", "development")
    logger.debug("current FLASK_ENV %s", env)
    app.config.from_object(config.get(env))

    # Validate configuration at startup
    validate_application_config(app)

    configure_extensions(app)
    if init_admin or env != "testing":
        create_admin(admin_ext)
    app.register_blueprint(post)
    app.register_blueprint(tags)
    app.register_blueprint(user)

    # Register CLI commands
    register_commands(app)

    return app
