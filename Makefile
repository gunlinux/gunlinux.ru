VERSION = 0.2.0


all: check


lint: ruff-lint ruff-lint-format-check lint-types

ruff-lint:
	uvx ruff check .

ruff-lint-format-check:
	uvx ruff format .
	uvx ruff format --check .

lint-types:
	uv run basedpyright .


test:
	uv run pytest

test-dev:
	uv run pytest -vv -s

test-coverage:
	uv run pytest --cov=app --cov-report xml

check: lint test

css-build:
	npm install
	npx webpack --mode production

run:
	uv run alembic upgrade head
	npx webpack --mode production
	uv run uvicorn main:app --host 0.0.0.0 --reload

create-admin:
	uv run python scripts/create_admin.py

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
