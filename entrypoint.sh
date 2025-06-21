#!/bin/sh

echo "wait until database started"
#while ! nc -z $DB_HOST $DB_PORT; do sleep 1; done

#source /app/venv/bin/activate
echo "run migrates"
FLASK_APP=blog uv run flask db upgrade

exec uv run gunicorn -c gunicorn.py # "$@"
