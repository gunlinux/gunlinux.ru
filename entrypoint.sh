#!/bin/sh

echo "run migrations"

uv run alembic -c migrations/alembic.ini upgrade head

exec uv run granian main:app --interface asgi --host 0.0.0.0 --port 8000 --workers 4
