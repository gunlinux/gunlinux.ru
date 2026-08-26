# AGENTS.md

Guidance for AI coding assistants working in this repository.

## Project

`gunlinux.ru` is a personal blog written in **Rust** (axum). Server-rendered
HTML over **htmx** (dual-mode: full page vs fragment based on the `HX-Request`
header), a custom admin panel built on repository traits, **PostgreSQL
everywhere** (SQLite support was removed from the workspace). The original
implementation was replaced in a staged rewrite; only the Rust workspace
remains. Behavioral contracts that the rewrite preserved are pinned by the
test suites — treat them as frozen.

## Commands

All through the Makefile (see `rust/README.md` for details):

- `make check` — full gate: `cargo fmt --check` + `clippy -D warnings` +
  `cargo test --workspace` (run before considering work done; the persistence
  suite needs Docker or `TEST_DATABASE_URL` — PostgreSQL only).
- `make css-build` — esbuild CSS build (output `app/static/dist`).
- `make rust-run` — `cargo run -p server` (reads `DATABASE_URL`, required,
  `postgres://` URL from env or repo `.env`).
- Feature-gated suites: `cargo test -p web --features browser-tests --test
  test_browser` (needs Chrome; downloads one on demand).

## Workspace layout & layering (critical)

`rust/` is a Cargo workspace: `domain`, `application`, `persistence`, `web`,
`server`.

```
route (axum handlers) → use case (application) → repository trait (domain) → impl (SeaORM)
                             ↑ domain (serde structs, pure logic) crosses boundaries
```

- **`domain`** — pure types + logic (Post/Category/Tag/User/Icon, markdown
  rendering, teaser, is_page, year grouping, bcrypt, repository **traits**).
  It is a **FROZEN contract**: do not change public APIs without care. It must
  never depend on persistence/web.
- **`application`** — use cases over the repository traits (read path:
  `nav_pages`, `posts_by_year`, `resolve_post_view`; admin writes: form →
  entity translation, validation). No HTTP types, no drivers — depends only on
  `domain`. `web` translates between HTTP and these functions.
- **`persistence`** — SeaORM entities, the baseline migration
  (`m20260101_000001_create_schema`), and the concrete repository impls.
  Backend is PostgreSQL (`sqlx-postgres`); repos are backend-agnostic over
  `DatabaseConnection`.
- **`web`** — the axum app. **MUST NOT depend on `persistence`**: data access
  happens only through `Arc<dyn ...Repository>` trait objects in `AppState`
  (see `web/src/app.rs`). Handlers are thin HTTP translators over the
  `application` use cases. Tests fake the traits with in-memory repos.
- **`server`** — the wiring binary: reads `DATABASE_URL` itself, connects,
  applies `Migrator::up`, builds `AppState`, serves.

There is deliberately no pass-through service layer: thin reads go straight
to the repository traits (via `WebError: From<RepoError>`); rules live in
`application`. Do not reintroduce wrapper structs that add nothing; do not let
SeaORM/entity types leak above the repository line.

## Key invariants (pinned by tests)

- **Route ordering:** the catch-all `GET /{alias}` is registered LAST so
  `/tags`, `/admin`, `/static` are never shadowed. Preserve this.
- **htmx dual-mode:** `HX-Request` header present → render the `*.htmx`
  fragment, else the full `*.html` page. Cache keys are htmx-aware.
- **Cache:** dual backend — Redis when `REDIS_URL` is set (`.env`), in-memory
  moka otherwise (connect failure falls back with a warning). Keys are
  content-versioned (`blog:v{max-update}:{uri}:{hx}`, version from
  `MAX(COALESCE(update_date, createdon, publishedon))`), so new/edited posts
  invalidate cached pages instantly; 600s TTL is only a safety net. Admin
  writes clear the
  namespace. `/sitemap.xml`, `/tags*`, `POST /md/` are NOT cached.
- **404 body:** every 404 returns the pinned `{"detail":"Not Found"}`
  with `application/json` (contract-pinned; `routes::not_found()`).
- **`POST /md/`:** uses `domain::post::render_markdown_preview`
  (fenced blocks render as inline `<code>` in a `<p>`, language tag first).
  Post **pages** use `render_markdown` (comrak with fenced code). Do not
  unify them — the preview contract depends on the split. No CSRF by design
  (no side effects); do not add state-changing cookie-authed POSTs without
  CSRF.
- **Auth:** JWT (HS256, `{sub, exp}`) wrapped in a signed `session` cookie
  (`base64url(json).hex(hmac)`). Passwords are **bcrypt** — existing prod
  hashes must keep verifying; do not switch to argon2 without a re-hash
  migration.
- **Admin:** custom, on repository traits (the pre-rewrite admin bypassed the
  layers; this must not return). Driven by `AdminModel`
  descriptors (5 models); `User.password` is form-excluded (blank keeps the
  hash). Registered at both `/admin` and `/admin/` (bare `/admin` → 302 login
  is a deliberate, documented improvement over the previous 404). Every write
  invalidates the cache.
- **Markdown drift:** known risk — the two renderers (`render_markdown` vs
  `render_markdown_preview`) are pinned by the test suites.
- **Known faithful quirks (do NOT "fix" them — they reproduce the
  pre-rewrite reference behavior, pinned by tests):** drafts leak into
  `/tags/{alias}` listings; `users.authenticated` is never enforced at login;
  some queries have no ORDER BY (DB-dependent order, only published listings
  pin `publishedon DESC`).

## Testing conventions

- Web tests: in-memory fake repos driving the axum router with
  `tower::ServiceExt` (see `rust/crates/web/tests/common/` for the app
  builder + seed helpers); no database required.
- `persistence` runs one suite body (`tests/common/suite.rs`) against scratch
  PostgreSQL 16 databases — provisioned per test, dropped after
  (`tests/common/postgres.rs`). Postgres is resolved from `TEST_DATABASE_URL`
  when set (CI service container), otherwise via a testcontainers
  `postgres:16` container, so `make check` needs Docker (or
  `TEST_DATABASE_URL`) locally.
- Browser tests use chromiumoxide + the system Chrome (or a downloaded
  build); they assert on real htmx `afterSwap` events, never sleeps.
- Feature flags must keep the default `cargo test` compile graph unchanged —
  add new test-only deps as **optional regular dependencies** gated by the
  feature (cargo rejects `optional = true` in `[dev-dependencies]`).

## Configuration (env / `.env`)

`web/src/settings.rs` (config + dotenvy, cached in a `OnceLock`): `ENV`,
`SECRET_KEY`, `YANDEX_VERIFICATION`, `JWT_ALGORITHM`,
`JWT_EXPIRE_MINUTES`. Server: `DATABASE_URL` (required — no default;
`postgres://` URL), `BIND_ADDR` (default `0.0.0.0:8000`), `STATIC_DIR`
(default `app/static`), `RUST_LOG` (default `info`). `database_url` in
settings is informational only — `server` owns the real connection.

## Deployment

- `rust/Dockerfile` (multi-stage; templates are embedded via `include_dir!`,
  static assets copied from `app/static` — `make css-build` must run first).
  Alpine builder → fully static musl binary → tiny `alpine` runtime image.
- **Deploys are automated:** pushing to `master` runs the `Rust` quality-gate
  workflow (fmt, clippy, test incl. postgres suite, browser-e2e); on success the
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
