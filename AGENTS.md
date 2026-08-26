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

All through the Makefile (see `rust/README.md` for details). The toolchain is
pinned to Rust **1.96** (CI + Dockerfile); rustfmt output is version-sensitive,
so match it locally.

- `make check` — full gate: `cargo fmt --check` + `clippy -D warnings` +
  `cargo test --workspace` (run before considering work done; the persistence
  suite needs Docker or `TEST_DATABASE_URL` — PostgreSQL only).
- `make check-arch` — machine-checks the crate-matrix Dependency Rule via
  `scripts/check-architecture.sh` (also the `arch` job in CI).
- `make css-build` — esbuild CSS build (output `app/static/dist`, gitignored;
  required before `cargo test`, Docker builds, and any deploy).
- `make rust-run` — `cargo run -p server` (reads `DATABASE_URL`, required,
  `postgres://` URL from env or repo `.env`). `make rust-check` / `rust-test` /
  `rust-build` / `rust-docker` are the individual steps.
- Feature-gated suites: `cargo test -p web --features browser-tests --test
  test_browser` (needs Chrome; downloads one on demand).
- Load tests: `make perf` / `make perf-smoke` (k6 scripts in `scripts/perf/`).

## Workspace layout & layering (critical)

`rust/` is a Cargo workspace: `domain`, `application`, `persistence`, `web`,
`server`.

```
route (axum handlers) → use case (application) → repository trait (domain) → impl (SeaORM)
                             ↑ domain (serde structs, pure logic) crosses boundaries
```

- **`domain`** — pure types + logic (Post/Category/Tag/User/Icon/Visit,
  markdown rendering, teaser, is_page, year grouping, bcrypt, repository
  **traits**). It is a **FROZEN contract**: do not change public APIs without
  care. It must never depend on persistence/web.
- **`application`** — use cases over the repository traits (read path:
  `nav_pages`, `posts_by_year`, `resolve_post_view`; admin writes: form →
  entity translation, validation). No HTTP types, no drivers — depends only on
  `domain`. `web` translates between HTTP and these functions.
- **`persistence`** — SeaORM entities, migrations (non-destructive baseline
  `m20260101_000001_create_schema` plus two additive follow-ups:
  `m20260825_000002_add_post_update_date`, `m20260825_000003_create_page_views`),
  and the concrete repository impls. Backend is PostgreSQL (`sqlx-postgres`);
  repos are backend-agnostic over `DatabaseConnection`.
- **`web`** — the axum app. **MUST NOT depend on `persistence`**: data access
  happens only through `Arc<dyn ...Repository>` trait objects in `AppState`
  (see `web/src/app.rs` — posts/tags/users/categories/icons/visits). Handlers
  are thin HTTP translators over the `application` use cases. Tests fake the
  traits with in-memory repos.
- **`server`** — the wiring binary: reads `DATABASE_URL` itself, connects,
  applies `Migrator::up`, builds `AppState`, serves.

### The Dependency Rule (machine-enforced)

`scripts/check-architecture.sh` (`make check-arch`, CI `arch` job) enforces:

1. `domain` has no in-workspace (path) dependencies;
2. `application` depends only on `domain`;
3. `web` must not depend on `persistence` or `sea-orm` in any position
   (dependencies, dev-dependencies, features);
4. only `server` may depend on both `persistence` and `web`.

There is deliberately no pass-through service layer: thin reads go straight
to the repository traits (via `WebError: From<RepoError>`); rules live in
`application`. Do not reintroduce wrapper structs that add nothing; do not let
SeaORM/entity types leak above the repository line. **If you add a workspace
crate, update the arch script's rules AND the Dockerfile's manifest-stub
layer** (see Deployment) or both gates fail.

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
  writes clear the namespace. `/sitemap.xml`, `/tags*`, `POST /md/` are NOT
  cached.
- **Analytics:** the `analytics::track_visit` middleware records one row per
  full-page HTML load into `page_views` (normalized referrer host, landing
  path, salted SHA-256 of the client IP — raw IPs are never stored). htmx
  fragment swaps and non-`text/html` requests are excluded. Best-effort: a
  failed insert is logged, never fails the request. Runs BEFORE the response
  cache so cache hits are counted exactly once.
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
  descriptors (5 models: post/category/tag/user/icon); `User.password` is
  form-excluded (blank keeps the hash). Registered at both `/admin` and
  `/admin/` (bare `/admin` → 302 login is a deliberate, documented improvement
  over the previous 404). Every write invalidates the cache.
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
`SECRET_KEY`, `YANDEX_VERIFICATION`, `REDIS_URL` (cache backend), `JWT_ALGORITHM`,
`JWT_EXPIRE_MINUTES`. Server: `DATABASE_URL` (required — no default;
`postgres://` URL), `BIND_ADDR` (default `0.0.0.0:8000`), `STATIC_DIR`
(default `app/static`), `RUST_LOG` (default `info`). `database_url` in
settings is informational only — `server` owns the real connection. The repo
`.env` is gitignored and loaded by dotenvy.

## Deployment

- `rust/Dockerfile` (multi-stage; templates are embedded via `include_dir!`,
  static assets copied from `app/static` — `make css-build` must run first).
  Alpine builder → fully static musl binary → tiny `alpine` runtime image.
  The builder stubs each workspace crate's manifest for layer caching (COPY
  manifest + mkdir/touch stub sources): **every workspace crate must be listed
  there**, or the stub `cargo build` fails to resolve the workspace.
- **Deploys are automated:** pushing to `master` runs the `Rust` quality-gate
  workflow (fmt, clippy, arch guard, test incl. postgres suite, browser-e2e);
  on success the `Deploy to Server` workflow builds the image, pushes it to
  the **public** Docker Hub repo `gunlinuxloki/gunlinux.ru` tagged with the
  commit short SHA (+ `latest`), and runs `.github/deploy.sh` on the server
  over SSH (`loki@gunlinux.ru:187`). Secrets required: `DOCKERHUB_USERNAME`,
  `DOCKERHUB_TOKEN`, `PRIVATE_KEY_SSH`.
- The server runs the container with `--network host` via the systemd unit
  `deploy/gunlinux-ru.service` (legacy Python unit `gunlinux.ru` is kept for
  rollback); env comes from the host `.env` via docker `--env-file`.
  `deploy/CUTOVER.md` is the runbook (backup, smoke tests, nginx `/static`
  root edit, rollback).
- `app/static/dist` is gitignored build output — CI builds CSS before tests
  and before the Docker build; the image `COPY`s it in.
- Do not push to `origin/master` without the user asking — every master push
  deploys to production.
