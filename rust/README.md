# gunlinux.ru — Rust server

Rust (axum) port of the gunlinux.ru blog, built as a cargo workspace under
`rust/`. See `plan.md` (repo root) for the staged migration strategy; the
Python/FastAPI app at the repo root remains the live deploy until cutover
(stage 8).

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
cargo test --workspace              # currently the domain unit tests
cargo fmt --check
cargo clippy --workspace -- -D warnings
```

(Equivalent `make rust-check` / `rust-test` / `rust-build` / `rust-run` targets
exist in the root Makefile.)

## Run locally

```sh
cd rust
DATABASE_URL="sqlite://tmp/dev.db" \
SECRET_KEY="change-me" \
STATIC_DIR="../app/static" \
cargo run -p server
```

The server binds `0.0.0.0:8000`.

## Environment variables

| Variable             | Default                        | Purpose                                              |
|----------------------|--------------------------------|------------------------------------------------------|
| `DATABASE_URL`       | `sqlite:///app/tmp/prod.db?mode=rwc` | SQLx connection string (SQLite or PostgreSQL); absolute sqlite paths need 3 slashes + `?mode=rwc` |
| `SECRET_KEY`         | *(dev default in code)*        | Signs JWT tokens / session cookies                   |
| `STATIC_DIR`         | `/app/static`                  | Directory served at `/static`                        |
| `YANDEX_METRIKA`     | `76938046`                     | Yandex.Metrika counter id (footer snippet)           |
| `YANDEX_VERIFICATION`| *(empty)*                      | Yandex site-verification meta tag content            |
| `JWT_ALGORITHM`      | `HS256`                        | JWT signing algorithm                                |
| `JWT_EXPIRE_MINUTES` | `1440`                         | JWT lifetime in minutes                              |

A `.env` file in the working directory is also loaded (via `dotenvy`).

## Static assets

CSS is built by the existing webpack pipeline — it is **not** compiled by
cargo. Run it from the repo root:

```sh
make css-build          # = npm install && npx webpack --mode production
```

The output goes to `app/static/dist` (e.g. `css/bundle.css`). The server serves
`STATIC_DIR` at runtime, so point it at `app/static` (the default) and the
webpack `dist/` subdirectory is picked up automatically.

- **Docker image:** the build context must already contain the webpack output —
  run `make css-build` before `docker build`. CI/deploy pipelines must build
  CSS before invoking the Docker build.
- **Local runs:** run `make css-build` once, or point `STATIC_DIR` at a
  directory that already contains a prebuilt `dist/`.

## Docker

Build from the repo root (context needs both `rust/` and `app/`):

```sh
docker build -f rust/Dockerfile -t gunlinux-rust:0.2.0 .
docker run --rm -p 8000:8000 \
  -v "$PWD/tmp:/app/tmp" \
  gunlinux-rust:0.2.0
```

The image is self-contained: multi-stage (builder compiles `server` in
release, runtime is `debian:bookworm-slim` with just the binary + `app/static`),
runs as the non-root `appuser`, listens on `0.0.0.0:8000`, and defaults to a
SQLite database at `/app/tmp/prod.db` (mount a volume at `/app/tmp` to
persist it).
