#!/bin/sh

echo "run migrations"
uv run alembic upgrade head

exec uv run gunicorn -c uvicorn.py
