lint:
	flake8	pro app.py

pytest:
	FLASK_ENV=testing FLASK_APP=pro pytest

test-coverage:
	( \
    source venv/bin/activate; \
		FLASK_ENV=testing FLASK_APP=pro pytest --cov=pro --cov-report xml\
	)

check: lint pytest


