[![Rust](https://github.com/gunlinux/gunlinux.ru/actions/workflows/rust-ci.yaml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/rust-ci.yaml)
[![Deploy](https://github.com/gunlinux/gunlinux.ru/actions/workflows/deploy.yaml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/deploy.yaml)

# gunlinux.ru

Personal blog, rewritten in **Rust** (axum). Server-rendered HTML with **htmx**
for progressive enhancement, a repository-trait admin panel, **PostgreSQL
everywhere** (SQLite support was removed from the workspace).

The original implementation was replaced in a staged rewrite; the Rust
workspace is the only implementation that ships. Behavioral contracts
preserved from the rewrite are pinned by the test suites.

## Repository layout

```
rust/                Cargo workspace — the application
  crates/domain/       Pure types + logic (serde structs, markdown, teaser, bcrypt,
                       repository traits). FROZEN contract — do not change public APIs.
  crates/persistence/  SeaORM entities, baseline migration, repository trait impls
  crates/web/          Axum app: routes, services, templates (Minijinja), admin, auth
  crates/server/       Wiring binary: reads DATABASE_URL, applies migrations, serves
app/static/          esbuild output + sources (CSS/img/upload) — served at /static
deploy/              systemd unit + production cutover runbook (CUTOVER.md)
.github/workflows/   rust-ci.yaml (fmt/clippy/test incl. postgres suite/browser-e2e), deploy.yaml
```

## Architecture

```
route (axum handlers) → service (structs) → repository (async traits) → entity (SeaORM)
                             ↑ domain (serde structs, pure logic) crosses boundaries
```

- **Web:** Axum + tower-http (static files) on Tokio.
- **ORM/DB:** SeaORM (SQLx underneath); PostgreSQL only.
- **Templates:** Minijinja — 16 templates; htmx dual-mode
  rendering (full page vs fragment based on the `HX-Request` header).
- **Auth:** JWT in a signed `session` cookie; bcrypt password hashes (existing
  hashes keep verifying — do not switch to argon2 without a re-hash migration).
- **Cache:** dual backend — Redis when `REDIS_URL` is set, in-memory moka
  otherwise. Keys are content-versioned (`blog:v{max-update}:{uri}:{hx}`) so
  new/edited posts invalidate cached pages instantly; the 600 s TTL is only a
  safety net. Admin writes clear the namespace.
- **Markdown:** comrak for post pages; `POST /md/` uses the legacy preview
  renderer (fenced blocks render as inline `<code>` in a `<p>`, language tag
  first — pinned by the domain tests).
- **Frontend:** esbuild CSS pipeline (single dep); output served from
  `app/static/dist`.

## Requirements

- Rust **1.96** (pinned in CI; rustfmt output is version-sensitive)
- Node + npm (only for `make css-build`)
- Docker (required for the persistence test suite via testcontainers, or set
  `TEST_DATABASE_URL` to a Postgres instance)

## Quick start

```sh
make css-build                                  # esbuild CSS (app/static/dist)
cd rust
DATABASE_URL='postgres://postgres:postgres@localhost:5432/gunlinux' cargo run -p server
# or: make rust-run
```

Notes:

- `DATABASE_URL` is **required** and must be a `postgres://` URL — the server
  has no embedded-DB fallback.
- The server applies the baseline migration on startup; the production
  cutover *stamps* it rather than re-running schema creation.

## Configuration (env vars / `.env`)

| Var | Default | Used by |
|---|---|---|
| `DATABASE_URL` | *(required)* | server (DB connection, `postgres://`) |
| `BIND_ADDR` | `0.0.0.0:8000` | server (listen address) |
| `STATIC_DIR` | `app/static` | web (static file root) |
| `SECRET_KEY` | dev-only default | web (session cookie signing) |
| `ENV` | `development` | web settings |
| `YANDEX_VERIFICATION` | — | web settings (search-console meta tag) |
| `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` | `HS256` / `1440` | web auth |
| `RUST_LOG` | `info` | tracing |

## Testing

```sh
make check                        # fmt + clippy + full workspace tests
cd rust && cargo test --workspace # web tests (in-memory fakes) + persistence suite (scratch Postgres 16)
```

Feature-gated suites (default `cargo test` never compiles them):

- `cargo test -p web --features browser-tests --test test_browser` — real
  headless-Chrome htmx swap tests (needs a browser; downloads one on demand).

The persistence suite provisions per-test scratch PostgreSQL 16 databases —
via testcontainers locally (needs Docker), or the CI `postgres:16` service
container when `TEST_DATABASE_URL` is set.

## Deployment

- Image: `docker build -f rust/Dockerfile -t gunlinux-rust .` (multi-stage;
  Alpine musl static build — requires `app/static/dist` from `make css-build`).
- Deploy script: `.github/deploy.sh` (builds the image on the server, installs
  the systemd unit `gunlinux-ru`, swaps off the legacy service).
- **Production cutover:** follow [`deploy/CUTOVER.md`](deploy/CUTOVER.md)
  (backup → build/install → baseline stamp → smoke → rollback). The cutover
  commit ships the deploy script + CI trigger swap together.

## Database

6 tables: `users`, `posts`, `categories`, `tags`, `posts_tags` (m2m), `icons`.
Three SeaORM migrations: the non-destructive baseline
`m20260101_000001_create_schema` (`CREATE TABLE IF NOT EXISTS`) plus two
additive follow-ups (`posts.update_date`, `page_views`).

## Behavioral contract

Routes, status codes, bodies, schema and auth behavior are pinned by the
test suites (`rust/crates/web/tests/`, `rust/crates/persistence/tests/`,
`rust/crates/domain/src/`) — treat them as frozen. Deliberate deviations from
the pre-rewrite behavior (e.g. bare `/admin` → 302 login, JSON 404 body) are
documented in `AGENTS.md`.
