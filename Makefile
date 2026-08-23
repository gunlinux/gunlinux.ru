VERSION = 0.2.0

# Frontend assets (webpack CSS build; output served from app/static/dist).
css-build:
	npm install
	npx webpack --mode production

# ---------------------------------------------------------------------------
# Rust — the deployed service (rust/ workspace: domain, persistence, web,
# server). The Python/FastAPI app was removed in Stage 9 (see plan.md).
# ---------------------------------------------------------------------------

RUST_DIR := rust

check:
	cd $(RUST_DIR) && cargo fmt --check && cargo clippy --workspace -- -D warnings && cargo test --workspace

rust-check:
	cd $(RUST_DIR) && cargo fmt --check && cargo clippy --workspace -- -D warnings

rust-test:
	cd $(RUST_DIR) && cargo test --workspace

rust-build:
	cd $(RUST_DIR) && cargo build --release -p server

rust-run:
	cd $(RUST_DIR) && cargo run -p server

rust-docker:
	docker build -f rust/Dockerfile -t gunlinux-rust:$(VERSION) .
