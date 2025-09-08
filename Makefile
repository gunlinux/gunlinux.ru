VERSION = 0.0.7


all: check


lint: ruff-lint ruff-lint-format-check lint-types

ruff-lint:
	uvx ruff check .

ruff-lint-format-check:
	uvx ruff format .
	uvx ruff format --check .

lint-types:
	uv run pyright .


test:
	FLASK_ENV=testing FLASK_APP=blog uv run pytest


test-coverage:
	FLASK_ENV=testing FLASK_APP=blog uv run pytest --cov=blog --cov-report xml

check: lint test

run:
	uv run flask db upgrade
	uv run flask run --host="0.0.0.0" --debug 

docker-build:
	docker build . --tag="gunlinux:$(VERSION)"

docker:
	-docker stop gunlinux
	-docker rm gunlinux
	docker run --rm -d --name gunlinux -v /home/loki/projects/gunlinux.ru/tmp:/app/tmp -p 5000:5000 gunlinux:$(VERSION)

docker-shell:
	docker run --rm -it --entrypoint="" gunlinux:$(VERSION) sh 

docker-test:
	docker build --target test-image -t gunlinux:$(VERSION)-test .
