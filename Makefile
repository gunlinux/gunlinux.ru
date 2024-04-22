all: check

lint:
	flake8 blog app.py

pytest:
	FLASK_ENV=testing FLASK_APP=pro pytest

test-coverage:
	( \
    . venv/bin/activate;\
		FLASK_ENV=testing FLASK_APP=blog pytest --cov=blog --cov-report xml\
	)

check: lint pytest


