# AGENTS.md

Guidance for AI coding assistants working in this repository.

## Project

`gunlinux.ru` is a personal blog written in **Rust** (axum). Server-rendered
HTML over **htmx** (dual-mode: full page vs fragment based on the `HX-Request`
header), a custom admin panel built on repository traits, PostgreSQL in
production, SQLite in dev/tests. The Python/FastAPI implementation was
migrated to Rust in a staged rewrite; the Python code is **removed** (Stage 9
complete). Key documents:

- [`plan.md`](plan.md) — the migration plan (history, stages, risks, DoD).
- [`MIGRATION_CONTRACT.md`](MIGRATION_CONTRACT.md) — the **frozen HTTP/htmx/
  DB/admin contract**; read it before changing any public behavior.
- [`TASKS.md`](TASKS.md) — remaining work (Stages 8–9 leftovers).
- [`scripts/parity/results.md`](scripts/parity/results.md) — final Python-vs-
  Rust parity comparison and the documented deviations.

## Commands

All through the Makefile (see `rust/README.md` for details):

- `make check` — full gate: `cargo fmt --check` + `clippy -D warnings` +
  `cargo test --workspace` (run before considering work done).
- `make css-build` — esbuild CSS build (output `app/static/dist`).
- `make rust-run` — `cargo run -p server` (reads `DATABASE_URL`; sqlite URLs
  need `?mode=rwc`).
- Feature-gated suites: `cargo test -p persistence --features postgres-parity`
  (needs Docker or `TEST_DATABASE_URL`) and `cargo test -p web --features
  browser-tests --test test_browser` (needs Chrome; downloads one on demand).

## Workspace layout & layering (critical)

`rust/` is a Cargo workspace: `domain`, `persistence`, `web`, `server`.

```
route (axum handlers) → service (structs) → repository (async traits) → entity (SeaORM)
                             ↑ domain (serde structs, pure logic) crosses boundaries
```

- **`domain`** — pure types + logic (Post/Category/Tag/User/Icon, markdown
  rendering, teaser, is_page, bcrypt, repository **traits**). It is a
  **FROZEN contract**: do not change public APIs without care. It must never
  depend on persistence/web.
- **`persistence`** — SeaORM entities, the baseline migration
  (`m20260101_000001_create_schema`), and the concrete repository impls.
  Repos are backend-agnostic over `DatabaseConnection` (both `sqlx-sqlite`
  and `sqlx-postgres` always enabled).
- **`web`** — the axum app. **MUST NOT depend on `persistence`**: data access
  happens only through `Arc<dyn ...Repository>` trait objects in `AppState`
  (see `web/src/app.rs`). Tests fake the traits with in-memory repos.
- **`server`** — the wiring binary: reads `DATABASE_URL` itself, connects,
  applies `Migrator::up`, builds `AppState`, serves.

Services (`web/src/services.rs`) are deliberately thin pass-throughs — the
seam where orchestration lands when it appears. Do not reflexively add
pass-through methods; do not let SeaORM/entity types leak above the repository
line.

## Key invariants (pinned by tests + MIGRATION_CONTRACT.md)

- **Route ordering:** the catch-all `GET /{alias}` is registered LAST so
  `/tags`, `/admin`, `/static` are never shadowed. Preserve this.
- **htmx dual-mode:** `HX-Request` header present → render the `*.htmx`
  fragment, else the full `*.html` page. Cache keys are htmx-aware.
- **Cache:** moka, 50s TTL, `"blog"` namespace. Admin writes clear the
  namespace. `/sitemap.xml`, `/tags*`, `POST /md/` are NOT cached.
- **404 body:** every 404 returns FastAPI's exact `{"detail":"Not Found"}`
  with `application/json` (parity-pinned; `routes::not_found()`).
- **`POST /md/`:** uses `domain::post::render_markdown_preview`
  (python-markdown-compatible: fenced blocks render as inline `<code>` in a
  `<p>`, language tag first). Post **pages** use `render_markdown` (comrak
  with fenced code). Do not unify them — the parity contract depends on the
  split. No CSRF by design (no side effects); do not add state-changing
  cookie-authed POSTs without CSRF.
- **Auth:** JWT (HS256, `{sub, exp}`) wrapped in a signed `session` cookie
  (`base64url(json).hex(hmac)`). Passwords are **bcrypt** — existing prod
  hashes must keep verifying; do not switch to argon2 without a re-hash
  migration.
- **Admin:** custom, on repository traits (Thread B — the old sqladmin
  bypassed the layers; this must not return). Driven by `AdminModel`
  descriptors (5 models); `User.password` is form-excluded (blank keeps the
  hash). Registered at both `/admin` and `/admin/` (bare `/admin` → 302 login
  is a deliberate, documented improvement over the Python 404). Every write
  invalidates the cache.
- **Markdown drift / SQLite↔Postgres divergence:** known risks (§5 of
  plan.md) — the postgres-parity suite and MIGRATION_CONTRACT.md guard them.
- **Known faithful quirks (do NOT "fix" them — they match the Python
  reference):** drafts leak into `/tags/{alias}` listings; `users.authenticated`
  is never enforced at login; some queries have no ORDER BY (DB-dependent
  order, only published listings pin `publishedon DESC`).

## Testing conventions

- Default suite: SQLite scratch DBs (temp files, `?mode=rwc`), `#[tokio::test]`
  with `tower::ServiceExt` against the axum router (see `rust/crates/web/tests/
  common/` for the app builder + seed helpers).
- `persistence` shares one suite body between SQLite and Postgres
  (`tests/common/suite.rs`); the Postgres side provisions a scratch DB per
  test and drops it after. `TEST_DATABASE_URL` skips testcontainers.
- Browser tests use chromiumoxide + the system Chrome (or a downloaded
  build); they assert on real htmx `afterSwap` events, never sleeps.
- Feature flags must keep the default `cargo test` compile graph unchanged —
  add new test-only deps as **optional regular dependencies** gated by the
  feature (cargo rejects `optional = true` in `[dev-dependencies]`).

## Configuration (env / `.env`)

`web/src/settings.rs` (config + dotenvy, cached in a `OnceLock`): `ENV`,
`SECRET_KEY`, `YANDEX_VERIFICATION`, `JWT_ALGORITHM`,
`JWT_EXPIRE_MINUTES`. Server: `DATABASE_URL` (default `sqlite://./tmp/dev.db`),
`BIND_ADDR` (default `0.0.0.0:8000`), `STATIC_DIR` (default `app/static`),
`RUST_LOG` (default `info`). `database_url` in settings is informational only —
`server` owns the real connection.

## Deployment

- `rust/Dockerfile` (multi-stage; templates are embedded via `include_dir!`,
  static assets copied from `app/static` — `make css-build` must run first).
- **Deploys are automated:** pushing to `master` runs the `Rust` quality-gate
  workflow (fmt, clippy, test, postgres-parity, browser-e2e); on success the
  `Deploy to Server` workflow builds the image, pushes it to the **public**
  Docker Hub repo `gunlinuxloki/gunlinux.ru` tagged with the commit short SHA
  (+ `latest`), and runs `.github/deploy.sh` on the server over SSH
  (`loki@gunlinux.ru:187`). Secrets required: `DOCKERHUB_USERNAME`,
  `DOCKERHUB_TOKEN`, `PRIVATE_KEY_SSH`.
- The server runs the container with `--network host` via the systemd unit
  `deploy/gunlinux-ru.service` (legacy Python unit `gunlinux.ru` is kept for
  rollback); env comes from the host `.env` via docker `--env-file`.
  `deploy/CUTOVER.md` is the runbook (backup, smoke tests, nginx `/static`
  root edit, rollback).
- Do not push to `origin/master` without the user asking — every master push
  deploys to production.
