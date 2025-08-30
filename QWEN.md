# Qwen Code - Project Context for gunlinux.ru

## Project Information
- **Name**: gunlinux.ru (Flask Blog Application)
- **Root Directory**: /home/loki/projects/aidame/gunlinux.ru
- **Date**: Saturday, August 30, 2025
- **OS**: linux

## Project Analysis

### Framework & Core Technologies
- **Web Framework**: Flask
- **Database**: SQLAlchemy (with PostgreSQL via `psycopg2-binary`)
- **Authentication**: Flask-Login
- **Admin Interface**: Flask-Admin
- **Migrations**: Flask-Migrate (Alembic)
- **Caching**: Flask-Caching
- **Sitemap Generation**: Flask-Sitemap
- **Asynchronous Server**: Gunicorn with Gevent workers
- **Containerization**: Docker

## Setup Commands

### Development Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd gunlinux.ru

# Create a virtual environment (using 'uv' for speed)
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
uv sync

# Set environment variables (create a .env file based on config.example.sh)
cp config.example.sh .env
# Edit .env to set your database URL, secrets, etc.

# Initialize and run database migrations
FLASK_APP=blog uv run flask db upgrade

# Run the application in debug mode
make run
# Or directly:
# uv run flask run --host="0.0.0.0" --debug
```

## Code Quality & Testing

### Tools Identified for Code Quality
Based on `pyproject.toml`, `Makefile`, and `.pre-commit-config.yaml`:
- **Linting & Formatting**: `ruff` (used for both linting and formatting)
- **Type Checking**: `pyright` (preferred), `mypy` (also configured)
- **Pre-commit Hooks**: `pre-commit` with `flake8` (currently configured hook)

### Running Tests
- **Test Framework**: `pytest`
- **Command to run tests and linters**:
  ```bash
  # Run all checks (linting, formatting, type checking, tests)
  make check

  # Run only tests
  make test

  # Run tests with coverage report
  make test-coverage
  ```

## Best Development Practices for this Project

1.  **Follow PEP 8**: Adhere to the standard Python style guide for code readability.
2.  **Use Type Hints**: Leverage `pyright` or `mypy` for static type checking to catch errors early.
3.  **Write Tests**: Use `pytest` to write comprehensive unit and integration tests. Aim for high code coverage (this project uses pytest-cov).
4.  **Lint and Format**: Use `ruff` (`make lint`) to ensure consistent code style. This project uses `ruff format` for formatting and `ruff check` for linting.
5.  **Pre-commit Hooks**: Install and use `pre-commit` (`pre-commit install`) to automate linting and other checks before commits.
6.  **Dependency Management**: Use `uv` for fast dependency management. Keep `requirements.txt` and `dev.txt` up-to-date. Prefer pinned versions for reproducible builds.
7.  **Environment Variables**: Use environment variables for configuration (secrets, database URLs) via `python-dotenv`. Never commit secrets.
8.  **Database Migrations**: Use `Flask-Migrate` (Alembic) for database schema changes. Always create and review migration scripts.
9.  **Dockerization**: The `Dockerfile` and `entrypoint.sh` handle containerization. Ensure the image is built and tested regularly (`make docker-build`, `make docker-test`).
10. **Documentation**: Keep `README.md` updated with setup, usage, and contribution guidelines.
11. **Secure Coding**: Follow security best practices, especially for web applications (e.g., input validation, preventing injection attacks, CSRF protection via Flask-WTF).

## Architecture Overview

This is a Flask-based web application structured as a blog. The project uses a modular approach, organizing code into different modules within the `blog/` directory.

### Core Components

- **Entry Point**:
    - `app.py`: The main WSGI application entry point. It imports and calls `create_app` from the `blog` package.
- **Application Factory (`blog/__init__.py`)**:
    - `create_app()`: The Flask application factory function. It initializes the app, loads configuration based on `FLASK_ENV`, configures extensions, registers blueprints, and sets up the admin interface.
    - `configure_extensions()`: Initializes all Flask extensions (SQLAlchemy, Flask-Admin, Flask-Caching, Flask-Migrate, Flask-Login, Flask-Sitemap) with the app instance.
- **Configuration**:
    - `blog/config.py`: Defines configuration classes for different environments (Development, Testing, Production) using environment variables.
    - `.env` (not in repo, but used): File for local environment variables, loaded by `python-dotenv`.
    - `gunicorn.py`: Configuration file for the Gunicorn WSGI server used in production.
- **Extensions (`blog/extensions.py`)**:
    - Centralizes the instantiation of Flask extensions (db, admin, cache, migrate, login_manager, flask_sitemap) to avoid circular imports.
- **Modular Blueprints**:
    - `blog/post/`: Contains models, views, and potentially templates related to blog posts.
    - `blog/tags/`: Contains models, views, and association tables for post tags.
    - `blog/category/`: Contains models for post categories.
    - `blog/user/`: Contains models, views, forms, and authentication logic for users.
    - `blog/admin/`: Contains logic for setting up the Flask-Admin interface.
- **Dependencies**:
    - `pyproject.toml`: Modern Python project configuration, defining dependencies and build system. It uses `hatchling` as the build backend.
- **Deployment**:
    - `Dockerfile`, `.dockerignore`: Define a multi-stage Docker image for the application and a separate test image.
    - `entrypoint.sh`: The script executed when the Docker container starts. It waits for the database, runs migrations, and then starts Gunicorn.
    - `Makefile`: Contains common development tasks (`make run`, `make check`, `make test`, `make docker-build`, `make docker`).
- **Infrastructure/CI**:
    - `.github/workflows/`: Contains GitHub Actions workflows for continuous integration (running tests, linting).
    - `.pre-commit-config.yaml`: Configures git pre-commit hooks (currently uses `flake8`; could be updated to use `ruff`).
- **Data**:
    - `migrations/`: Database migration scripts managed by Flask-Migrate (Alembic).
