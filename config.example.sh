#!/bin/bash
# Example configuration script for the gunlinux.ru blog application
# Copy this file to config.sh and modify as needed

# Secret key for Flask sessions and CSRF protection
# Generate a strong random key for production
export SECRET_KEY="change-this-to-a-strong-random-string-in-production"

# Database configuration
# SQLite (development)
export SQLALCHEMY_DATABASE_URI="sqlite:///tmp/dev.db"

# For PostgreSQL:
# export SQLALCHEMY_DATABASE_URI="postgresql://username:password@localhost/database_name"

# For MySQL:
# export SQLALCHEMY_DATABASE_URI="mysql://username:password@localhost/database_name"

# Application environment
# Options: development, testing, production
export FLASK_ENV="development"

# Web server port
export PORT="5555"

# Yandex verification code (optional)
# export YANDEX_VERIFICATION="your-yandex-verification-code"

# Yandex Metrika ID (optional)
# export YANDEX_METRIKA="your-yandex-metrika-id"

# Cache configuration (optional)
# export CACHE_TYPE="SimpleCache"
# export CACHE_DEFAULT_TIMEOUT="300"
