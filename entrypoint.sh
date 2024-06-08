#!/bin/sh

echo "wait until database started"
while ! nc -z $DB_HOST $DB_PORT; do sleep 1; done

source /app/venv/bin/activate
echo "run migrates"
cd /app
FLASK_APP=blog /app/venv/bin/flask db upgrade
