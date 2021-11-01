lint:
	./venv/bin/flake8	pro app.py

pytest:
	FLASK_ENV=testing FLASK_APP=pro python3 -m pytest

test-coverage:
	FLASK_ENV=testing FLASK_APP=pro python3 -m pytest --cov=pro --cov-report xml

check: lint pytest


