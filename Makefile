VERSION = 0.2.0

# Frontend assets (esbuild CSS build; output served from app/static/dist).
css-build:
	npm install
	npm run build

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
	cd $(RUST_DIR) && STATIC_DIR=../app/static cargo run -p server

rust-docker:
	docker build -f rust/Dockerfile -t gunlinux-rust:$(VERSION) .

# ---------------------------------------------------------------------------
# Performance / load testing (k6 — https://k6.io; scripts in scripts/perf/).
# Requires: brew install k6
# ---------------------------------------------------------------------------

PERF_BASE_URL ?= http://localhost:8000

perf:
	BASE_URL=$(PERF_BASE_URL) k6 run scripts/perf/load-test.js

perf-smoke:
	BASE_URL=$(PERF_BASE_URL) k6 run --stage 2s:2,10s:10,3s:0 scripts/perf/load-test.js
