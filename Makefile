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
	uv run alembic -c migrations/alembic.ini upgrade head
	npx webpack --mode production
	uv run granian --interface asgi --access-log --workers 4 --workers-kill-timeout 1 main:app
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

# ---------------------------------------------------------------------------
# Rust (migration) — the Python targets above are the LEGACY path and stay
# untouched until the Rust cutover (see plan.md, stage 8). The rust-* targets
# operate on the `rust/` workspace.
# ---------------------------------------------------------------------------

RUST_DIR := rust

rust-check:
	cd $(RUST_DIR) && cargo fmt --check && cargo clippy --workspace -- -D warnings

rust-test:
	cd $(RUST_DIR) && cargo test --workspace

rust-build:
	cd $(RUST_DIR) && cargo build --release -p server

rust-run:
	cd $(RUST_DIR) && cargo run -p server
