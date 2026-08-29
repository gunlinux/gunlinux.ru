# gunlinux.ru — Rust server

Rust (axum) implementation of the gunlinux.ru blog, built as a cargo workspace
under `rust/`. Deployment and rollback are covered in `deploy/CUTOVER.md` (repo
root).

## Workspace layout

| Crate          | Role                                                        |
|----------------|-------------------------------------------------------------|
| `crates/domain` | Serde structs + pure logic (markdown, teaser, bcrypt, traits) |
| `crates/persistence` | SeaORM entities, migrations, pools, repository impls      |
| `crates/web`   | Axum application: routes, templates, auth, admin, caching   |
| `crates/server` | Binary that wires everything and serves HTTP on `0.0.0.0:8000` |

## Prerequisites

- Rust toolchain **1.96** (`rustup default 1.96.0` or a matching `rust:1.96`
  image). The CI workflow pins the same version.
- Static assets (see below).

## Build

```sh
cd rust
cargo build --release -p server     # binary: rust/target/release/server
```

## Test & lint

```sh
cd rust
cargo test --workspace              # web tests (in-memory fakes) + persistence suite (scratch Postgres 16; needs Docker or TEST_DATABASE_URL)
cargo fmt --check
cargo clippy --workspace -- -D warnings
```

(Equivalent `make rust-check` / `rust-test` / `rust-build` / `rust-run` targets
exist in the root Makefile.)

## Run locally

```sh
cd rust
DATABASE_URL="postgres://postgres:postgres@localhost:5432/gunlinux" \
SECRET_KEY="change-me" \
STATIC_DIR="../app/static" \
cargo run -p server
```

The server binds `0.0.0.0:8000`. `DATABASE_URL` is **required** (PostgreSQL
only — SQLite support was removed) and is usually supplied by the repo `.env`
(`postgres://...`); the migrations run against it on startup.

## Environment variables

| Variable             | Default                        | Purpose                                              |
|----------------------|--------------------------------|------------------------------------------------------|
| `DATABASE_URL`       | *(required — no default)*      | PostgreSQL connection string (`postgres://...`)      |
| `SECRET_KEY`         | *(required — no default; server refuses to start without a non-default value)* | Signs JWT tokens / session cookies                   |
| `STATIC_DIR`         | `app/static` (code); `/app/static` (Docker image) | Directory served at `/static`                        |
| `YANDEX_VERIFICATION`| *(empty)*                      | Yandex site-verification meta tag content            |
| `REDIS_URL`          | *(unset)*                     | Response-cache backend: Redis/Valkey URL when set (e.g. `redis://:pass@127.0.0.1:6379`); in-memory cache otherwise |
| `JWT_ALGORITHM`      | `HS256`                        | JWT signing algorithm                                |
| `JWT_EXPIRE_MINUTES` | `1440`                         | JWT lifetime in minutes                              |

A `.env` file in the working directory is also loaded (via `dotenvy`).

## Static assets

CSS is built with esbuild — it is **not** compiled by cargo. Run it from the
repo root:

```sh
make css-build          # = npm install && npm run build (esbuild)
```

The output goes to `app/static/dist` (e.g. `css/bundle.css`). The server serves
`STATIC_DIR` at runtime, so point it at `app/static` (the default) and the
esbuild `dist/` subdirectory is picked up automatically.

- **Docker image:** the build context must already contain the esbuild output —
  run `make css-build` before `docker build`. CI/deploy pipelines must build
  CSS before invoking the Docker build.
- **Local runs:** run `make css-build` once, or point `STATIC_DIR` at a
  directory that already contains a prebuilt `dist/`.

## Docker

Build from the repo root (context needs both `rust/` and `app/`):

```sh
docker build -f rust/Dockerfile -t gunlinux-rust:0.2.0 .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL="postgres://postgres:postgres@host.docker.internal:5432/gunlinux" \
  gunlinux-rust:0.2.0
```

The image is self-contained: multi-stage (Alpine builder compiles `server`
with the musl target into a **fully static binary**, runtime is a tiny
`alpine` image with just the binary + `app/static`), runs as the non-root
`appuser`, and listens on `0.0.0.0:8000`. `DATABASE_URL` (PostgreSQL) is
required at runtime — production feeds it via docker `--env-file`.
