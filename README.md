[![Code quality](https://github.com/gunlinux/gunlinux.ru/actions/workflows/code-quality.yaml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/code-quality.yaml)
[![Deploy](https://github.com/gunlinux/gunlinux.ru/actions/workflows/deploy.yaml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/deploy.yaml)

# gunlinux.ru

Personal blog. **FastAPI** application (a rewrite of an older Flask app) served via
[granian](https://github.com/emmett-framework/granian) as `main:app`. Tooling is
[`uv`](https://docs.astral.sh/uv/) for Python and `npm`/webpack for CSS/JS. Requires Python 3.10+.

## Install

```bash
# Python deps (uv reads pyproject.toml / uv.lock)
$ uv sync

# CSS/JS assets
$ make css-build   # npm install + webpack production build

# Database schema
$ uv run alembic -c migrations/alembic.ini upgrade head

# Create an admin user for /admin
$ make create-admin
```

## Configuration

Settings are loaded from `.env` via `pydantic-settings` (see `app/core/settings.py`).
Key variables — override the dev defaults in production:

- `DATABASE_URL` — async driver URL, e.g. `sqlite+aiosqlite:///./tmp/dev.db` or
  `postgresql+asyncpg://user:pass@host/db`
- `SECRET_KEY` — used to sign JWTs / session cookies
- `JWT_*` — JWT algorithm / expiry settings

## Run

```bash
$ make run   # runs migrations, builds CSS, then serves main:app via granian on :8000
```

## Develop

```bash
$ make check     # full gate: ruff lint + format check + basedpyright + pytest
$ make lint      # lint and type-check only
$ make test      # pytest (--cov=app); make test-dev for verbose

# run a single test
$ uv run pytest tests/test_posts.py::test_name
```

## Deploy

The multi-stage `Dockerfile` runs `make check` in a `test-image` stage (the build fails on
lint/type/test errors), then ships a slim runtime stage. `entrypoint.sh` applies alembic
migrations and launches granian on port 8000.

```bash
$ make docker-build
$ make docker
```

## Contribution

Run the full gate before opening a PR:

```bash
$ make check
```
