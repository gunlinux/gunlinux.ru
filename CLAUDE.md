# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run tests
make test          # uv run pytest
make test-dev      # verbose with stdout

# Lint and type check
make lint          # ruff check + ruff format check + basedpyright
make check         # lint + test (run before committing)

# Run a single test file (pytest runs with --cov on app by default, see pyproject.toml)
uv run pytest tests/test_views.py -vv -s

# Dev server (runs alembic upgrade + webpack build first, then uvicorn --reload)
make run

# Create an admin user interactively
make create-admin  # uv run python scripts/create_admin.py

# Build CSS only
make css-build     # npm install && npx webpack --mode production

# Docker (build runs `make check` in the test stage)
make docker-build  # docker build . --tag gunlinux:<VERSION>
make docker        # stop/rm/run the container on :5000
```

## Architecture

This is a FastAPI blog application with domain-driven design. Data flows through **three distinct representations** of each entity — keep them in sync when adding fields:

1. **`app/infrastructure/database.py`** — SQLAlchemy Core `Table` definitions built via `get_*_table(metadata)` factory functions, all bound to a single shared `MetaData` / `Base.metadata`. This is the physical schema.
2. **`app/models/`** — SQLAlchemy ORM `DeclarativeBase` classes (`Base` in `models/base.py`). Each ORM class sets `__table__ = get_*_table(Base.metadata)` and adds `relationship()`s plus derived properties (the ORM `Post.markdown_html`). Used by repositories, sqladmin, and alembic autogenerate. NOTE: templates render **domain** objects, so they use the domain `Post.markdown` (rendered HTML) and `Post.teaser` (plain-text excerpt), not the ORM's `markdown_html`.
3. **`app/domain/`** — Pure Python dataclasses with no framework dependencies (`Post`, `Tag`, `User`, `Category`, `Icon`). Canonical representations passed around services and routes.

**`app/infrastructure/session.py`** — Async engine, `AsyncSessionLocal` sessionmaker, and the `get_db` FastAPI dependency (commits only when the request actually wrote — tracked via an `after_flush` event — rolls back on exception).

**`app/repositories/`** — Repository pattern with `BaseRepository[T, ID]` ABC. Each repo runs async SQLAlchemy queries against the **ORM models** and maps results to **domain dataclasses** via a private `_to_domain`. Session is injected via FastAPI `Depends(get_db)`.

**`app/services/`** — Business logic layer that operates on domain models via repos. Created via dependency functions in `app/core/dependencies.py`.

**`app/api/`** — FastAPI routers (`posts.py`, `tags.py`) that replace Flask blueprints. Routes use `Depends` for service injection. `posts.py` owns the catch-all `GET /{alias}`, which is why prefixed routers are registered first and the tags index is exposed at both `/tags` and `/tags/`.

**`app/auth/`** — JWT helpers (`jwt.py`, `security.py`) used by the sqladmin authentication backend, which stores the token in the server-side session.

**`app/admin/`** — sqladmin views replacing Flask-Admin. `PostAdmin` uses custom Jinja2 templates (`app/templates/sqladmin/post_edit.html`, `post_create.html`) with EasyMDE markdown editor.

**`app/core/`** — Application factory (`application.py`), pydantic-settings config (`settings.py`), FastAPI dependency factories (`dependencies.py`), caching (`cache.py`).

## HTMX templates

Routes check for the `HX-Request` header and render `.htmx` templates for partial page updates (e.g., `post.htmx` vs `post.html`). HTMX template files live in `app/templates/`.

## Frontend

CSS source is at `app/static/src/styles.css`, compiled by webpack to `app/static/dist/css/bundle.css`. Fonts are copied to `app/static/dist/fonts/`. The `make run` target builds CSS automatically.

## Config and environment

`DATABASE_URL` env var overrides the default SQLite path. Default dev DB: `tmp/dev.db`. Copy `.env.example` → `.env` for local overrides.

Production runs through `entrypoint.sh` (the Docker `ENTRYPOINT`): it runs `alembic upgrade head` then launches `gunicorn -c gunicorn.conf.py` with the `uvicorn.workers.UvicornWorker` worker class. Server config lives in `gunicorn.conf.py` (binds `0.0.0.0:5000`, `wsgi_app = "main:app"` — `wsgi_app` is gunicorn's own config key and is correct for the ASGI worker). The file must NOT be named `uvicorn.py`: a root-level `uvicorn.py` shadows the installed `uvicorn` package whenever the cwd is on `sys.path`.

## Database migrations

```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

Migrations live in `migrations/versions/`. The app runs `alembic upgrade head` automatically on `make run`.
