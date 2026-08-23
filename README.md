[![Rust](https://github.com/gunlinux/gunlinux.ru/actions/workflows/rust-ci.yaml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/rust-ci.yaml)
[![Deploy](https://github.com/gunlinux/gunlinux.ru/actions/workflows/deploy.yaml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/deploy.yaml)

# gunlinux.ru

Personal blog, rewritten in **Rust** (axum). Server-rendered HTML with **htmx**
for progressive enhancement, a repository-trait admin panel, PostgreSQL in
production (SQLite in dev/tests).

The original FastAPI/Python implementation was migrated to Rust in a staged
rewrite — see [`plan.md`](plan.md) for the migration plan and
[`MIGRATION_CONTRACT.md`](MIGRATION_CONTRACT.md) for the frozen HTTP/DB/admin
contract. [`TASKS.md`](TASKS.md) tracks the remaining work.

## Repository layout

```
rust/                Cargo workspace — the application
  crates/domain/       Pure types + logic (serde structs, markdown, teaser, bcrypt,
                       repository traits). FROZEN contract — do not change public APIs.
  crates/persistence/  SeaORM entities, baseline migration, repository trait impls
  crates/web/          Axum app: routes, services, templates (Minijinja), admin, auth
  crates/server/       Wiring binary: reads DATABASE_URL, applies migrations, serves
app/static/          webpack output + sources (CSS/fonts/img/upload) — served at /static
deploy/              systemd unit + production cutover runbook (CUTOVER.md)
scripts/parity/      Python-vs-Rust parity harness (archived; golden results in results.md)
.github/workflows/   rust-ci.yaml (fmt/clippy/test/postgres-parity/browser-e2e), deploy.yaml
```

## Architecture

```
route (axum handlers) → service (structs) → repository (async traits) → entity (SeaORM)
                             ↑ domain (serde structs, pure logic) crosses boundaries
```

- **Web:** Axum + tower-http (static files) on Tokio.
- **ORM/DB:** SeaORM (SQLx underneath); PostgreSQL in prod, SQLite in dev/tests.
- **Templates:** Minijinja — 16 templates ported from Jinja2; htmx dual-mode
  rendering (full page vs fragment based on the `HX-Request` header).
- **Auth:** JWT in a signed `session` cookie; bcrypt password hashes (existing
  hashes keep verifying — do not switch to argon2 without a re-hash migration).
- **Cache:** moka (in-memory TTL, 50s, `"blog"` namespace); admin writes
  invalidate it. Single-process, so no cross-worker staleness.
- **Markdown:** comrak for post pages; `POST /md/` uses a python-markdown-
  compatible preview renderer (see MIGRATION_CONTRACT.md for the residual
  differences).
- **Frontend:** unchanged webpack/npm CSS pipeline; output served from
  `app/static/dist`.

## Requirements

- Rust **1.96** (pinned in CI; rustfmt output is version-sensitive)
- Node + npm (only for `make css-build`)
- Docker (optional — Postgres parity tests via testcontainers)

## Quick start

```sh
make css-build                                  # webpack CSS (app/static/dist)
cd rust
DATABASE_URL='sqlite:///tmp/gunlinux-dev.db?mode=rwc' cargo run -p server
# or: make rust-run
```

Notes:

- `sqlite://` URLs need `?mode=rwc` — sqlx cannot create a missing file.
- The server applies the baseline migration on startup (also on PostgreSQL;
  the production cutover *stamps* it rather than re-running schema creation).
- The dev default `sqlite://./tmp/dev.db` only works because the file exists.

## Configuration (env vars / `.env`)

| Var | Default | Used by |
|---|---|---|
| `DATABASE_URL` | `sqlite://./tmp/dev.db` | server (DB connection) |
| `BIND_ADDR` | `0.0.0.0:8000` | server (listen address) |
| `STATIC_DIR` | `app/static` | web (static file root) |
| `SECRET_KEY` | dev-only default | web (session cookie signing) |
| `ENV` | `development` | web settings |
| `YANDEX_VERIFICATION` / `YANDEX_METRIKA` | — / `76938046` | templates |
| `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` | `HS256` / `1440` | web auth |
| `RUST_LOG` | `info` | tracing |

## Testing

```sh
make check                        # fmt + clippy + full workspace tests
cd rust && cargo test --workspace # default suite (SQLite)
```

Feature-gated suites (default `cargo test` never compiles them):

- `cargo test -p persistence --features postgres-parity` — the same repository
  suite against real PostgreSQL (testcontainers locally, or set
  `TEST_DATABASE_URL` for CI). Catches SQLite↔Postgres divergence.
- `cargo test -p web --features browser-tests --test test_browser` — real
  headless-Chrome htmx swap tests (needs a browser; downloads one on demand).

## Deployment

- Image: `docker build -f rust/Dockerfile -t gunlinux-rust .` (multi-stage;
  requires `app/static/dist` from `make css-build`).
- Deploy script: `.github/deploy.sh` (builds the image on the server, installs
  the systemd unit `gunlinux-ru`, swaps off the legacy service).
- **Production cutover:** follow [`deploy/CUTOVER.md`](deploy/CUTOVER.md)
  (backup → build/install → baseline stamp → smoke → rollback). The cutover
  commit ships the deploy script + CI trigger swap together.

## Database

6 tables: `users`, `posts`, `categories`, `tags`, `posts_tags` (m2m), `icons`.
Single SeaORM baseline migration `m20260101_000001_create_schema` (the 16
Alembic revisions it replaces); `CREATE TABLE IF NOT EXISTS` — non-destructive.

## Contract & parity

- [`MIGRATION_CONTRACT.md`](MIGRATION_CONTRACT.md) — the frozen HTTP/htmx/DB/
  admin contract (routes, status codes, bodies, schema, auth).
- [`scripts/parity/results.md`](scripts/parity/results.md) — final Python-vs-
  Rust comparison: 18/19 status MATCH (one documented admin-root deviation),
  16/19 normalized-body MATCH (remaining DIFFs are documented Thread-B admin
  differences and a whitespace-only markdown quirk).
