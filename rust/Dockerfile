# syntax=docker/dockerfile:1
#
# Multi-stage build for the Rust server (axum port of gunlinux.ru).
#
# Build from the REPO ROOT so the context contains both `rust/` and `app/`:
#
#   docker build -f rust/Dockerfile -t gunlinux-rust:0.2.0 .
#
# The esbuild output (`app/static/dist`) must exist before building — run
# `make css-build` first (see rust/README.md). Templates are embedded into the
# binary at build time, so any template files the `web` crate embeds with
# include_dir! must live inside `rust/crates/` (they travel via `COPY rust/crates/`).

# ---------------------------------------------------------------- builder --
FROM rust:1.96-slim AS builder

WORKDIR /build

# C compiler needed to compile the bundled SQLite (libsqlite3-sys "bundled",
# pulled in via sea-orm's sqlx-sqlite feature — no system libsqlite3 needed).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Cache-friendly dependency layer: copy manifests + lockfile first and build
# against stub sources, so the (large) dependency tree compiles once and is
# reused as a Docker layer when only crate sources change.
COPY rust/Cargo.toml rust/Cargo.lock ./
COPY rust/crates/domain/Cargo.toml crates/domain/Cargo.toml
COPY rust/crates/persistence/Cargo.toml crates/persistence/Cargo.toml
COPY rust/crates/web/Cargo.toml crates/web/Cargo.toml
COPY rust/crates/server/Cargo.toml crates/server/Cargo.toml

RUN mkdir -p crates/domain/src crates/persistence/src crates/web/src crates/server/src \
    && touch crates/domain/src/lib.rs crates/persistence/src/lib.rs crates/web/src/lib.rs \
    && printf 'fn main() {}\n' > crates/server/src/main.rs \
    && cargo build --release -p server \
    && rm -rf crates/domain/src crates/persistence/src crates/web/src crates/server/src

# Real sources — only the workspace crates recompile at this point.
# `touch` forces newer mtimes than the stub build above: Docker COPY preserves
# the context files' (possibly older) mtimes, which would make cargo's
# fingerprint check skip the recompile and ship the stub binary.
COPY rust/crates/ crates/
RUN find crates -type f -name '*.rs' -exec touch {} + \
    && cargo build --release -p server \
    && cp target/release/server /build/server

# ---------------------------------------------------------------- runtime --
FROM debian:bookworm-slim AS runtime

# ca-certificates: harmless to include (outbound HTTPS not used server-side
# today, but keeps the image safe for future external fetches).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Non-root user, mirroring the Python Dockerfile (UID 10000).
ARG UID=10000
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# Static assets (CSS/JS/fonts/images). `app/static/dist` is the esbuild output
# directory; copying it here keeps the image self-contained.
COPY app/static /app/static

COPY --from=builder /build/server /app/server

ENV DATABASE_URL=sqlite:///app/tmp/prod.db?mode=rwc
ENV STATIC_DIR=/app/static

# SQLite database directory (a volume mounted at /app/tmp in production
# shadows this). Chown so the non-root user can write it.
RUN mkdir -p /app/tmp \
    && chown -R appuser:appuser /app

EXPOSE 8000

USER appuser

CMD ["./server"]
