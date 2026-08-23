# Migration to Rust — Plan

> Goal: port `gunlinux.ru` (FastAPI personal blog) to Rust without changing the
> public behavior (routes, status codes, HTML/htmx output, DB schema, admin UX).
> Grouped by stages; two cross-cutting threads run through every stage:
> **platform-independent tests** and a **repository pattern for all models**.

---

## 1. Current state (verified against code, not docs)

> ⚠️ `CLAUDE.md`, `README.md` and `deploy.sh` are stale — they reference Flask,
> `fasthx`, `repositories/protocols.py`, `domain/exceptions.py`, `validate_alias`
> and `flask db upgrade`, none of which exist in the current code. Treat the code
> below as the single source of truth.

**Stack:** Python 3.12 · FastAPI · granian (ASGI) · SQLAlchemy 2 (async) · Alembic ·
bcrypt · python-jose (JWT) · pydantic-settings · sqladmin · Jinja2 + htmx ·
fastapi-cache2 (in-memory) · markdown · webpack/npm (CSS only).

**Schema (6 tables):** `users`, `posts`, `categories`, `tags`, `posts_tags` (m2m),
`icons`. Prod is PostgreSQL; tests use in-memory SQLite.

**Routes:** `GET /`, `/posts`, `/hx/pages`, `/hx/icons`, `/robots.txt`,
`/sitemap.xml`, `/rss.xml`, `POST /md/`, catch-all `GET /{alias}`, `/tags`,
`/tags/{alias}`, `/admin` (sqladmin), `/static`.

**Layers:** `api → services → repositories → models`, with `domain` dataclasses
crossing layer boundaries. Admin (sqladmin) **bypasses** the repository/service
layers and mutates ORM models directly.

**Tests:** pytest + pytest-asyncio + httpx `ASGITransport` against in-memory SQLite.

**CI/CD:** `.github/workflows/code-quality.yaml` (ruff, basedpyright, pytest) +
`deploy.yaml` (SSH → systemd restart).

---

## 2. Target architecture (Rust)

Same strict layering, translated to idiomatic Rust:

```
route (axum handlers) → service (structs) → repository (async traits) → entity (SeaORM)
                             ↑ domain (serde structs, pure logic) crosses boundaries
```

- **Async runtime:** Tokio.
- **Web framework:** Axum + tower + tower-http (static files, sessions).
- **ORM/DB:** SeaORM (closest 1:1 to SQLAlchemy; async, relations, migrations).
  SQLx sits underneath and is used directly for the pool + test harness.
- **Templating:** Minijinja (Jinja2-compatible syntax → existing templates port
  nearly verbatim; keeps htmx dual-mode rendering).
- **Config:** `config` (or `figment`) + `dotenvy` + `serde` — replaces
  pydantic-settings.
- **Password hashing:** `bcrypt` — **must stay bcrypt** to keep verifying existing
  user hashes.
- **JWT:** `jsonwebtoken` (replaces python-jose).
- **Markdown:** `comrak` (CommonMark/GFM) + `scraper`/`html2text` for teaser
  text extraction (replaces python-markdown + regex strip).
- **Cache:** `moka` (in-memory TTL + namespace invalidation).
- **Errors:** `thiserror` for domain/repo errors, `anyhow` only at binary boundaries.
- **Logging:** `tracing` + `tracing-subscriber`.
- **Frontend:** **unchanged.** Keep the existing webpack/npm CSS pipeline and serve
  its output as static files. This removes a large chunk of scope.

### Python → Rust mapping

| Python | Rust |
|---|---|
| FastAPI + granian | Axum (+ tower-http) on Tokio |
| SQLAlchemy async | SeaORM entities + relations |
| Alembic | SeaORM migrations |
| `repositories/base.py` ABC | `Repository` async trait |
| pydantic-settings | `config`/`figment` + serde |
| Jinja2 | Minijinja |
| bcrypt | `bcrypt` crate |
| python-jose | `jsonwebtoken` |
| markdown | `comrak` |
| fastapi-cache2 InMemoryBackend | `moka` |
| sqladmin | custom admin built on repository traits |
| pytest + httpx ASGITransport | `#[tokio::test]` + `tower::ServiceExt`/`axum-test` |
| in-memory SQLite tests | `sqlx::SqlitePool` (+ Postgres via testcontainers) |

---

## 3. Cross-cutting threads

### Thread A — Platform-independent tests (the "smart plan")

"Platform-independent" here means **database-platform-independent**: one test suite
written against the repository *traits*, runnable against SQLite (fast, CI) **and**
Postgres (parity, opt-in) without rewriting the tests.

Strategy:

1. **Test against traits, not engines.** Every service/route test depends on a
   repository trait, never a concrete SeaORM/sqlx type. Swap the backend by swapping
   the pool/impl behind the trait.
2. **SQLite as the default.** Use `sqlx::SqlitePool` (in-memory or temp file) for the
   fast, self-contained suite — mirrors today's `sqlite+aiosqlite:///:memory:`.
3. **Postgres parity behind a feature flag.** Gate the same suite on a `postgres`
   feature using `testcontainers` (or a `TEST_DATABASE_URL`). CI runs SQLite on every
   push; Postgres parity runs nightly/on-demand. This catches SQLite↔Postgres
   divergences (types, `page` bool, `DateTime(timezone=True)`) that the current
   Python suite never exercised.
4. **Recreate the existing test categories** 1:1 so behavior is pinned during the
   port (see Stage 2/3/5/6 for which tests land where):
   - domain unit tests (markdown, teaser, bcrypt) — pure, no IO;
   - repository CRUD/finder tests — via trait, both backends;
   - service tests — via trait with a test repository;
   - route/integration tests — full axum app + SQLite pool;
   - auth/JWT roundtrip tests — pure.

### Thread B — Repository pattern for all models (incl. admin)

The current sqladmin **bypasses** the service/repository/domain layers and mutates
ORM models directly. The Rust rebuild will **not** replicate that: the admin is a
normal client of the same repository layer every other path uses.

Concrete shape:

```rust
#[async_trait]
pub trait Repository<T, Id>: Send + Sync {
    async fn get_by_id(&self, id: Id) -> Result<Option<T>, RepoError>;
    async fn get_all(&self) -> Result<Vec<T>, RepoError>;
    async fn create(&self, entity: T) -> Result<T, RepoError>;
    async fn update(&self, entity: T) -> Result<T, RepoError>;
    async fn delete(&self, id: Id) -> Result<bool, RepoError>;
}
```

Plus one finder trait per model (`PostRepository: Repository<Post, i32>` with
`get_by_alias`, `get_published_posts`, `get_posts_by_tag`, `get_tags_for_post`, …),
so services and admin both depend on the narrow trait, not the concrete SeaORM repo.

For the admin, add a thin `AdminModel` descriptor alongside each model:

```rust
struct AdminModel {
    entity: &'static str,          // "Post"
    searchable: &'static [&'static str],  // ["pagetitle", "alias"]
    sortable:   &'static [&'static str],  // ["id", "publishedon"]
    excluded:   &'static [&'static str],  // ["password"] for User
}
```

…so the admin CRUD UI (list/create/edit/delete) is **generic** over
`(Repository, AdminModel)` and drives all five models through the same code path —
this is what replaces sqladmin's per-`ModelView` classes.

---

## 4. Stages

> **Status legend:** ✅ done · 🟡 partial (note) · ⬜ pending
>
> **Overall status (2026-08-23):** the rewrite core (Stages 1–7) is complete and
> verified — 72 Rust tests passing, fmt + clippy clean, live smoke test green.
> **Stages 8–9 remain**: production cutover and parity/cleanup. Partials: no
> golden contract file, no Postgres parity suite, no dedicated service tests.

### Stage 0 — Recon & contract freeze (no code) — 🟡 Partial
- **Freeze the HTTP contract** 🟡 — instead of a golden snapshot file, the
  contract is pinned by the ported route suites (`test_basics`/`test_views`/
  `test_tags` assert status codes + key bodies) and a live smoke test.
- **Inventory** ✅ — schema (6 tables), routes (12), templates (16), Alembic
  revisions (16) all documented in this plan.
- **Fix/ignore stale docs** 🟡 — identified as stale (`CLAUDE.md`, `README.md`,
  `deploy.sh`), left untouched; rewrite deferred to Stage 9.
- **Decide & record stack** ✅ — Axum + SeaORM + Minijinja + moka, confirmed by
  the working implementation.
- **Deliverable `MIGRATION_CONTRACT.md`** ⬜ — not created.

### Stage 1 — Workspace scaffold & CI — ✅
- Cargo workspace ✅ — `rust/` with `domain` / `persistence` / `web` / `server`.
- CI ✅ — `.github/workflows/rust-ci.yaml` (`cargo fmt --check`, `clippy -D
  warnings`, `cargo test`).
- Config + `tracing` + `.env` ✅ — `web::settings` (config + dotenvy), tracing
  init in `server`.
- `Dockerfile` ✅ — `rust/Dockerfile` multi-stage, validated with a real build.
- **Acceptance** ✅ — exceeded (full app, not just a hello-world).

### Stage 2 — Domain layer (pure Rust, no IO) — ✅
- Serde structs ✅ — `Post`, `Category`, `Tag`, `User`, `Icon`.
- Pure logic ✅ — markdown (`comrak`), `teaser`, `is_page`, bcrypt hash/verify,
  `createdon` defaulting. (No alias-validation exists in the real Python code —
  stale-docs artifact, nothing to port.)
- **First platform-independent tests** ✅ — 8 unit tests (no DB, no HTTP).
- **Acceptance** ✅ — pass on any OS, zero external services.

### Stage 3 — Persistence: entities, migrations, repository traits — 🟡
- SeaORM entities + relations (6 tables) ✅ — exact column/nullability match.
- **Repository traits for all models** (Thread B) + impls ✅ — SQLite verified;
  Postgres feature-flagged impls compile.
- **Migrations** ✅ — baseline `m20260101_000001_create_schema` (stamp on the
  existing DB is part of Stage 8 cutover).
- **Recreate repository tests** ✅ — 10 tests on temp-file SQLite; **Postgres
  parity via testcontainers** ⬜ not implemented.
- **Acceptance** 🟡 — SQLite green; Postgres backend unverified.

### Stage 4 — Services — 🟡
- Services over repository traits ✅ — all five in `web/src/services.rs`.
- `thiserror` error types ✅ — `WebError` (NotFound/Conflict/Internal); no
  `Validation` variant (nothing to validate in the real code).
- **Recreate service tests** (port `test_services.py`) ⬜ — no dedicated suite;
  services are exercised indirectly through the route tests with fake repos.
- **Acceptance** 🟡 — green via routes, no standalone service suite.

### Stage 5 — HTTP layer (Axum) — ✅
- App factory + route ordering ✅ — catch-all `/{alias}` registered last.
- All routes + Minijinja + htmx dual-mode ✅ — 12 routes, 16 templates ported.
- moka cache + admin invalidation ✅.
- **Recreate route/integration tests** ✅ — `test_basics`/`test_views`/
  `test_tags` via `tower::ServiceExt`; live smoke test on all routes passed.
- **Acceptance** ✅ — contract enforced by tests + live HTTP verification.

### Stage 6 — Auth + admin panel (repository-pattern based) — ✅
- JWT + signed session cookie + bcrypt ✅.
- **Custom admin on repository traits** (Thread B) ✅ — `AdminModel` descriptors
  for all 5 models, generic CRUD, `User.password` excluded, cache cleared on
  every write.
- `test_auth` ✅ (8 tests) + admin CRUD tests ✅ (7 tests, writes go through
  the repo traits).
- **Acceptance** ✅.

### Stage 7 — Frontend & static integration — 🟡
- webpack kept, `app/static` served via tower-http ✅ — `bundle.css` 200.
- htmx end-to-end 🟡 — fragments verified at HTTP level (`/hx/pages`,
  `/hx/icons`); no browser-level swap automation.
- **Acceptance** 🟡 — route-level verified; browser parity not automated.

### Stage 8 — Deploy & cutover — ⬜
- `Dockerfile` ✅ finalized + build-validated; `.github/workflows` replacement
  and `deploy.sh` stale-Flask fix ⬜ (Rust CI added alongside, not swapped).
- systemd unit for the Rust binary ⬜.
- **DB cutover** (backup → baseline stamp → smoke test) ⬜.
- **Rollback plan** 📝 documented in §5 but not rehearsed.
- **Acceptance** ⬜ — deploy not yet pointed at prod.

### Stage 9 — Parity, cleanup & docs — ⬜
- Side-by-side parity run (old Python vs new Rust, golden outputs) ⬜.
- Remove Python (`app/`, `migrations/`, `pyproject.toml`, `uv.lock`, Makefile
  targets) ⬜.
- Rewrite `README.md` + `CLAUDE.md` (currently wrong) ⬜.
- **Acceptance** ⬜.

---

## 5. Risks & gotchas

1. **Stale docs** (`README.md`, `CLAUDE.md`, `deploy.sh`) describe a different
   architecture — do not trust them for any decision.
2. **bcrypt compatibility** — existing user hashes must keep verifying; do not switch
   to argon2 without a re-hash migration.
3. **Markdown drift** — `comrak`/`pulldown-cmark` render slightly differently from
   python-markdown (e.g. raw-HTML pass-through, `fenced_code`). Golden-output parity
   tests in Stage 9 are the guard.
4. **SQLite↔Postgres divergence** — `page` bool, `DateTime(timezone=True)`,
   integer `authenticated`. The Postgres parity suite (Thread A) is the fix.
5. **Route ordering** — catch-all `GET /{alias}` must stay last, or `/tags`, `/admin`,
   `/static` get shadowed.
6. **Cache single-worker constraint** — today's `InMemoryBackend` breaks invalidation
   under `--workers 4` (already inconsistent in `entrypoint.sh`/`Makefile`). Rust +
   axum is single-process, so one `moka` cache is shared — this bug disappears.
7. **Migrations** — 16 Alembic revisions must collapse into one baseline; stamping
   (not re-running) is critical to avoid touching prod data.
8. **`POST /md/` has no CSRF** (documented as acceptable: no side effects). Preserve
   that status; don't add state-changing cookie-authed POSTs without CSRF.

---

## 6. Definition of done

- All 6 tables, all routes, and admin CRUD behave identically to the frozen
  contract — 🟡 routes + admin verified by tests/smoke; full golden-output
  parity vs Python pending Stage 9.
- Repository trait is the **only** data-access seam, used by routes, services,
  **and** admin — ✅ (the admin no longer bypasses the layer, unlike sqladmin).
- One test suite runs on SQLite (CI, every push) and Postgres (parity, opt-in)
  — 🟡 SQLite done; Postgres parity suite not implemented yet.
- CI is Rust-native (`fmt`, `clippy`, `test`); deploy path is correct and
  rollbackable — 🟡 CI done; deploy/cutover (Stage 8) pending.
- Python code and stale docs are removed or rewritten — ⬜ (Stage 9).
