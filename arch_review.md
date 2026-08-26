# Architecture Review — gunlinux.ru (Rust/axum)

**Date:** 2026-08-26
**Lens:** Clean Architecture (Uncle Bob: entities → use cases → interface
adapters → frameworks; the Dependency Rule — source-code dependencies point
*inward*, toward the domain).
**Scope:** `rust/` Cargo workspace (`domain`, `persistence`, `web`, `server`),
the htmx dual-mode rendering model, the admin panel, auth, caching, and the
deployment wiring.

---

## 1. Executive summary

The project is **structurally closer to Clean Architecture than most Rust web
apps**, and the expensive parts are already right:

- The **domain crate is a true inner core** — pure types and logic, zero I/O,
  zero framework types.
- The **repository traits are a genuine port seam**: `web` depends only on
  `Arc<dyn …Repository>` trait objects; `persistence` implements them.
  `web`'s `Cargo.toml` literally cannot import `persistence`/SeaORM — the
  Dependency Rule for the two outer layers is enforced by the build system,
  not just convention.
- **Persistence is an adapter** with explicit `to_domain` mappers; SeaORM
  models never escape it.
- **The composition root is where it belongs** — `server` reads
  `DATABASE_URL`, runs migrations, and constructs `AppState`.

The gaps are **not** in the layering; they are in the *middle* of the onion:

1. **There is no application (use-case) layer.** Orchestration lives inside
   axum handlers in the `web` crate (`routes.rs`, `admin.rs`). The `services`
   module is a deliberate set of pass-through stubs, so business rules that
   exist today (nav-page resolution, year grouping, cache-key semantics,
   admin form-translation) are glued to the web framework.
2. **Domain entities are persistence-shaped**, not domain-shaped — `id:
   Option<i32>`, foreign keys, and a cache-versioning field (`update_date`)
   are all in the inner core. This is a pragmatic tradeoff, not a violation,
   but it weakens the "domain independent of data concerns" property.
3. A handful of **small leaks and drifts**: settings accessed via a global
   `OnceLock` instead of the injected `AppState.settings`, cache-versioning
   query on the `PostRepository` port, an outdated cache description in
   `README.md`, and no CI guard that the dependency edges stay clean.

None of these block the current feature set; they matter the moment the app
grows beyond its current ~7k lines. Section 7 prioritizes remediation.

**Verdict: conformance is ~85%.** The dependency rule holds everywhere that
matters; the missing 15% is use-case encapsulation and domain purity, not
layer violations.

---

## 2. The architecture, mapped onto the onion

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRAMEWORKS & DRIVERS        axum · tokio · tower-http · minijinja    │
│                             sea-orm/sqlx (postgres) · moka · redis   │
│                             comrak · bcrypt · jsonwebtoken           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ INTERFACE ADAPTERS                                             │  │
│  │  web crate: routes.rs, admin.rs, auth.rs, cache.rs,            │  │
│  │             analytics.rs, templates.rs, services.rs,           │  │
│  │             settings.rs, app.rs (AppState, Router assembly)    │  │
│  │  persistence crate: entities/, repositories/*, migrator/       │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │ USE CASES (application layer)                            │  │  │
│  │  │  ⚠ ABSENT as its own layer — currently spread across     │  │  │
│  │  │  routes.rs + admin.rs handlers (see §4.2)                │  │  │
│  │  │  ┌────────────────────────────────────────────────────┐  │  │  │
│  │  │  │ ENTITIES (domain crate)                            │  │  │  │
│  │  │  │  Post Tag Category User Icon Visit                  │  │  │  │
│  │  │  │  post.rs (markdown ×2, teaser) · security.rs        │  │  │  │
│  │  │  │  repositories.rs (ports) · error.rs (RepoError)     │  │  │  │
│  │  │  └────────────────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  COMPOSITION ROOT: server crate (main.rs) — DATABASE_URL, Migrator, │
│  AppState wiring, BIND_ADDR                                         │
└─────────────────────────────────────────────────────────────────────┘
```

Dependency edges (from `Cargo.toml`, verified):

| Crate | Depends on | Own deps of note |
|---|---|---|
| `domain` | — (nothing in-workspace) | serde, chrono, comrak, bcrypt, thiserror, async-trait — all pure, no I/O |
| `persistence` | `domain` | sea-orm (sqlx-postgres), sea-orm-migration |
| `web` | `domain` only | axum, minijinja, moka, redis, jsonwebtoken, hmac, tower-http… |
| `server` | `domain` + `persistence` + `web` | anyhow, tokio, tracing |

The Dependency Rule holds: every arrow points inward. `web` has **no**
`persistence`/`sea-orm` dependency declared — it is structurally impossible
for a SeaORM entity or driver type to appear above the repository line
(AGENTS.md's "MUST NOT depend on persistence" is enforced by cargo, which is
the strongest form of that rule).

---

## 3. What is genuinely right (keep, do not "fix")

### 3.1 The port seam (`domain/src/repositories.rs`, `domain/src/error.rs`)

The generic `Repository<T, Id>` plus per-entity traits (`PostRepository`,
`TagRepository`, …) are textbook ports. `RepoError` is domain-owned, so
`persistence` maps driver errors inward (`translate_err` →
`RepoError::Conflict/Db/NotFound`) and no SeaORM type can cross the boundary.
This is the single most valuable architectural property in the repo — it is
what lets `web/tests` run the whole app against in-memory fakes with zero DB
(and zero mocking framework), and it is what lets the admin panel be written
once against `AdminStore` trait objects.

### 3.2 Persistence as an adapter, with explicit mapping

Every repository impl has a `to_domain(...)` mapper (`post_repository.rs`,
`user_repository.rs`, …) that converts SeaORM models into domain structs.
Column-level quirks (nullable BOOLEAN, no server defaults) are documented at
the entity/migration, not leaked upward. The test suite runs the *real*
Postgres adapter against scratch databases (`persistence/tests/repositories.rs`
via testcontainers / `TEST_DATABASE_URL`) — this is the correct way to test an
adapter: real driver, real schema, no mocks.

### 3.3 Composition root (`server/src/main.rs`)

Reads `DATABASE_URL` itself, connects, runs `Migrator::up` (migrations are a
deployment concern — correct placement), builds `AppState` with concrete
repos, serves. `web` stays ignorant of *how* the repos are built. This is
exactly what Clean Architecture asks of the outermost layer.

### 3.4 Framework details contained at the edges

- **htmx dual-mode** (`routes.rs`, `templates.rs`): the `HX-Request`
  decision and fragment-vs-full rendering is an adapter concern, handled
  where it belongs; cache keys are htmx-aware.
- **Cache** (`cache.rs`): Redis-vs-moka is hidden behind one `Cache` struct
  with a *content-versioned* key scheme (`blog:v{max-update}:{uri}:{hx}`) —
  freshness comes from the domain's `update_date`, so admin writes
  invalidate instantly and the 600 s TTL is only a safety net. Good design.
- **Admin** (`admin.rs`): built on repository traits via `AdminStore`
  descriptors; deliberately no ORM bypass (this was the pre-rewrite failure
  mode). Form → domain translation happens inside `AdminStore` impls.

### 3.5 The frozen domain contract + test posture

`domain` is documented as a frozen contract, and the tests pin the preserved
behaviors (404 body, `/md/` preview output, route ordering, admin index
redirection). The three test tiers — domain unit tests, web tests on in-memory
fakes, persistence tests on real scratch Postgres, plus opt-in browser e2e on
real htmx `afterSwap` events — give the architecture the safety net it needs
to be changed at all.

---

## 4. Findings

Severity: 🔴 high · 🟠 medium · 🟡 low · ⚪ informational.

### 4.1 🟠 The use-case layer does not exist as a layer

**Where:** `web/src/routes.rs` (413 lines), `web/src/admin.rs` (1202 lines),
`web/src/services.rs` (171 lines).

**What:** `services.rs` is 100% pass-through (`get_post_by_alias` =
`repo.get_by_alias`). All actual orchestration lives in axum handlers:

- `routes.rs::nav_pages` — resolves nav pages + htmx-vs-full decision;
- `templates.rs::group_posts_by_year` — pure grouping logic that *should*
  be domain/application but sits in the template module;
- `routes.rs::with_cache` + key builders — cache orchestration;
- `admin.rs` — form → entity translation, validation errors, store dispatch.

**Why it matters:** use cases cannot be exercised without an axum `Router` and
`HeaderMap`. The moment a second entry point appears (CLI import, API client,
a scheduled job), the logic must be extracted or duplicated. It also means
`WebError` (HTTP-flavored) is the only error type the "application" knows.

**What to do (when it matters):** extract an `application` crate (or a
`use_cases` module inside `domain` — many small Rust projects do this) holding
interactors like `PublishPost`, `RenderPostPage`, `ResolveNav`. Each takes
repository trait objects + plain inputs and returns domain results; `routes.rs`
becomes a thin translator (HTTP → use case → HTTP). This is the biggest single
item on the roadmap and the one with the best payoff-per-risk.

**Counterpoint (documented decision):** AGENTS.md explicitly calls services
"the seam where orchestration lands when it appears — do not reflexively add
pass-through methods." The pass-throughs are *intentional stubs*, and the
app is a personal blog with one rendering path. Extracting use cases now
would be speculative abstraction; extract when the second consumer or the
first non-trivial rule appears. ⚪ This tradeoff is acceptable — record it in
`AGENTS.md` so the decision stays conscious.

### 4.2 🟠 Domain entities are persistence/query-shaped

**Where:** `domain/src/post.rs` (`Post`), `repositories.rs`
(`latest_update`), `domain/src/user.rs`, `visit.rs`.

**What:**

- `Post.id: Option<i32>` — identity belongs to persistence; a domain entity
  that is "created" then gains an id is really a DTO for a database row.
- `Post.update_date` — added *for cache content versioning*; an
  infrastructure concern is now a field of the inner-core entity, and
  `Post::new()` writes it (`Some(Utc::now())`).
- `Post.category_id`, `user_id` — raw foreign keys; and `is_page` only
  becomes meaningful when a *category is joined in* (the persistence layer
  computes it in `to_domain`). The entity is shaped like a query result, not
  an aggregate.
- `PostRepository::latest_update` — the cache's version query sits on the
  port. The port now knows about caching.

**Why it matters:** domain types can no longer be reasoned about in
isolation ("a post is content + publication state"); they encode storage
layout. If the app ever needs a second storage backend or a decoupled read
model (e.g. a search index), the entity shape fights the requirement.

**What to do:** the pragmatic middle ground — split *identity/meta* from
*content*: keep `Post` as-is for the wire/DB shape (it is the contract) but
stop adding new infrastructure fields to it; introduce a separate domain
value (`PostDraft`, `PublishedPost`) for rules that don't need ids; move
`latest_update` off the repository port into a `ContentVersion`/`CacheKey`
helper in `web` that queries via the existing `PostRepository` methods.
🟡 Low urgency: the entity is stable and tests pin it — treat the split as a
"when we add the next field" trigger, not a refactor sprint.

### 4.3 🟡 Settings: global `OnceLock` vs injected `AppState.settings`

**Where:** `web/src/settings.rs` (`get_settings()` global), `auth.rs`,
`cache.rs`, `analytics.rs` (call the global), `app.rs` (`AppState.settings`).

**What:** two mechanisms coexist: `AppState.settings: Arc<Settings>` (the
clean, injected form, built by the composition root) and `settings::get_settings()` (a process-wide `OnceLock` that reads env + `.env` directly). `auth.rs` and `cache.rs` use the global, not the injected value.

**Why it matters:** tests that want to vary `SECRET_KEY` or JWT expiry must
race against a process-global instead of constructing an `AppState`; the
global also makes `web` self-configuring, which blurs the composition-root
boundary.

**What to do:** route all settings reads through `AppState.settings`
(`auth` functions take `&Settings`; `Cache::connect` already takes the URL —
pass `settings.redis_url` at construction). The global can remain as a thin
convenience for the handful of non-state call sites, but the injected form
should be primary. Small, mechanical, low risk — good first cleanup.

### 4.4 🟡 Documentation drift on the cache — *fixed in this pass*

**Where:** `README.md` "Cache: moka (in-memory TTL, 50s …)".

**What:** code says `TTL_SECS = 600` with dual Redis/moka backends and
content-versioned keys (AGENTS.md is correct). README's description was
stale. **Resolved 2026-08-26**: the bullet now matches the implementation.

### 4.5 🟡 No guard that the dependency edges stay clean

**Where:** `.github/workflows/rust-ci.yaml`.

**What:** the rule "web must not depend on persistence" is currently
enforced by `Cargo.toml` (the dependency simply isn't declared) — good — but
nothing *checks* it. A future `cargo add persistence -p web` or a
`dev-dependency` addition would silently widen the seam. `server` is the only
crate that should know both `persistence` and `web`.

**What to do:** cheap and effective — a CI step running
`cargo machete` (unused-dependency lint) plus a 3-line check that
`web/Cargo.toml` contains no `persistence`/`sea-orm` entry. Alternatively a
tiny `xtask`/script asserting the crate matrix. 30 minutes of work, makes the
architecture's most important invariant machine-checked.

### 4.6 🟡 Redis cache wire format is unversioned

**Where:** `web/src/cache.rs` (`WireEntry`).

**What:** `WireEntry { status, body, content_type }` serialized into Redis.
If the entry shape ever changes (new field, different serde), stale entries
from the previous deploy fail to deserialize — verified that this degrades
to a cache **miss** (`cache.rs:149–150`: `serde_json::from_str(&raw?).ok()?`
→ `None`), so the failure mode is safe today.

**What to do:** keep the miss-on-bad-entry behavior (it is already correct);
optionally prefix keys with a wire-format version
(`blog:v{version}:w1:…`) so schema changes orphan old entries *explicitly*,
the same trick the content version already uses — only if the entry shape is
expected to change.

### 4.7 🟡 `web` is one large crate with mixed responsibilities

**Where:** `web/src/*` — routes, admin, auth, cache, analytics, templates,
settings, services, app assembly.

**What:** 8 modules, two of them large (`admin.rs` ~1200 lines, `routes.rs`
~410). All are interface adapters, so this is *not* a layering violation, but
it concentrates every HTTP concern in one compile unit.

**What to do:** nothing now. If the app grows (new API surface, second
frontend), split by *adapter* — `web-admin`, `web-cache`, `web-templates` as
crates — before splitting by layer. ⚪ Watch, don't act.

### 4.8 🟡 `README.md` architecture section is aspirational

The README still describes the pre-Redis, single-backend cache and omits the
analytics/visit pipeline and the AdminStore model. It was partially refreshed
during the Python-trace cleanup (2026-08-26); the cache bullet (§4.4) is the
remaining drift. Keep README in sync when the cache or admin story changes.

### 4.9 ⚪ Faithful quirks are architectural debt, deliberately

Drafts leaking into `/tags/{alias}`, `users.authenticated` never enforced,
order-less queries — these are documented, test-pinned behaviors inherited
from the pre-rewrite app. From a clean-architecture standpoint they are the
*frozen contract* (AGENTS.md lists them as "do NOT fix"). Correct call:
behavioral compatibility is more valuable than theoretical purity for a live
blog with existing content. Revisit only if the contract is ever allowed to
break.

---

## 5. Conformance checklist

| Clean Architecture principle | Status | Evidence / gap |
|---|---|---|
| Inner core is framework-free | ✅ | `domain` deps: serde/chrono/comrak/bcrypt only; no axum/sea-orm/tokio I/O |
| Dependency Rule (arrows inward) | ✅ | Cargo graph verified; `web` cannot reach `persistence` |
| Ports/adapters (repositories) | ✅ | Traits in `domain`, impls in `persistence`, fakes in `web/tests` |
| Adapter maps driver types inward | ✅ | `to_domain` mappers; `RepoError` owns error translation |
| Use cases independent of framework | ⚠️ | Orchestration in axum handlers; `services` are pass-through stubs (§4.1) |
| Domain entities free of persistence shape | ⚠️ | `id: Option`, FK fields, `update_date` versioning in `Post` (§4.2) |
| Composition root at the edge | ✅ | `server` wires everything |
| Framework details at the edge | ✅ | htmx, cache backends, templates, JWT all confined to `web` |
| Config injected, not global | ⚠️ | `AppState.settings` exists but global `get_settings()` is used in places (§4.3) |
| Dependency edges machine-checked | ⚠️ | Cargo enforces structure; no CI assertion (§4.5) |

---

## 6. Verification of claims

- Dependency edges: read from `rust/crates/*/Cargo.toml` (2026-08-26).
- Test posture: `make check` green on this revision — fmt, clippy
  `-D warnings`, full workspace tests including the Postgres persistence
  suite (`tests/repositories.rs`, 11 tests) and all web suites
  (admin 18, services 21, views 16, auth 8, basics 9, tags 3, analytics 7).
- Code references: `domain/src/…`, `persistence/src/…`, `web/src/…`,
  `server/src/main.rs` as of commit `43bf129` + the Python-trace cleanup.

---

## 7. Recommendations, prioritized

**Do now (small, mechanical, high value):**
1. ~~Fix `README.md` cache bullet~~ — done in this pass (4.4).
2. Redis `WireEntry` miss-on-bad-entry is already correct (verified) — no
   action needed unless the wire format is expected to change (4.6).
3. Prefer `AppState.settings` at new call sites; convert `auth.rs`/`cache.rs`
   to take `&Settings` (4.3).

**Next growth trigger (do when the second consumer or first non-trivial
rule appears):**
4. Extract an `application`/use-case layer; make `routes.rs`/`admin.rs` thin
   HTTP translators (4.1).
5. Stop adding infrastructure fields to domain entities; introduce
   domain value types (`PostDraft`, `PublishedPost`) when the next field
   arrives; move `latest_update` off the port (4.2).

**Cheap insurance (one CI job):**
6. Assert the crate matrix (`web` has no `persistence` dep; only `server`
   joins them) — `cargo machete` + a 3-line grep check (4.5).

**Explicitly NOT recommended:**
- Splitting `web` into per-layer crates now (4.7).
- "Fixing" the faithful quirks (4.9) — they are the contract.
- Introducing an entity/DTO split for all six models — the current unified
  shape is the frozen contract and the mapping cost is not justified at this
  size.

---

## 8. Bottom line

The architecture already delivers the two outcomes Clean Architecture exists
for: **the domain is independently testable** (it is — pure functions, unit
tests, zero I/O) and **the storage/UI details can be swapped without touching
business rules** (they can — repo traits + in-memory fakes + real-adapter
tests prove it). The missing middle — a true use-case layer — is the only
structural gap, and it is correctly parked behind a documented decision until
the app needs it. Keep the dependency graph as clean as it is today, fix the
small drifts, and the architecture will stay "clean enough" at this project's
scale for a long time.
