# gunlinux.ru — Frozen Migration Contract (golden reference)

> **Status:** frozen 2026-08-23 (plan.md Stage 0 deliverable T1+T2, created post-hoc
> from the completed Rust implementation). This document is the reference that the
> Python-vs-Rust parity run (plan.md Stage 9) checks the ported app against.
>
> **Source of truth:** the Rust code under `rust/` (which was itself ported 1:1 from
> the Python app). Where this document and any other doc (`README.md`, `CLAUDE.md`,
> `deploy.sh` are known-stale) disagree, **this document + the Rust code win**.
> Each claim cites its source file. Nothing in this contract was invented: behavior
> that is ambiguous in the code is stated as the code does it and collected in
> §8 ("Ambiguities & implicit behavior").
>
> **How to verify parity:** for each section, run the Rust app and check every
> status code, content-type, body marker and fragment below; run the SQLite
> `cargo test` suite in `rust/crates/web/tests/*` against both apps; compare
> DB rows after the same sequence of writes.

---

## 1. HTTP routes

Sources: `rust/crates/web/src/app.rs` (registration), `rust/crates/web/src/routes.rs`
(handlers), `rust/crates/web/tests/*` (pinned assertions).

Content-type constants used throughout (`routes.rs`):
`text/html; charset=utf-8`, `text/plain; charset=utf-8`, `application/xml`,
`application/rss+xml`. Error responses (`WebError` → `IntoResponse`, `routes.rs`):
404 `WebError::NotFound`, 409 `WebError::Conflict`, 500 `WebError::Internal`,
body = the error message string.

### 1.1 Public routes (12)

| # | Method | Path | Success | Errors | Content-Type | Cached? | Key body markers / notes |
|---|--------|------|---------|--------|--------------|---------|--------------------------|
| 1 | GET | `/` | 200 | — | text/html; charset=utf-8 | yes, htmx-aware key | Renders `index.html` (full page, **no htmx variant — always full**). Title contains `Неразумный перфекционизм`. Contains `<div id="posts" class="posts">`. On load it `hx-get="/posts"` into `.page__content` (see §2). |
| 2 | GET | `/posts` | 200 | — | text/html; charset=utf-8 | yes, htmx-aware key | Dual-mode: full → `posts.html`, `HX-Request` present → `posts.htmx`. **Both are bare listings — no `<!DOCTYPE>`.** Markers: class `postGroup`, `postGroup__title`, `minipost`, `minipost__title`, `minipost__date` (date formatted `%B %d, %Y`). |
| 3 | GET | `/hx/pages` | 200 | — | text/html; charset=utf-8 | yes, htmx-aware key | Always fragment `pages.htmx` (nav page links, class `nav__link`). No `<!DOCTYPE>`. |
| 4 | GET | `/hx/icons` | 200 | — | text/html; charset=utf-8 | yes, htmx-aware key | Always fragment `icons/icons.htmx` (footer icon links: `href`, `title`, `aria-label`, `{{icon.content|safe}}`). No `<!DOCTYPE>`. |
| 5 | GET | `/robots.txt` | 200 | — | text/plain; charset=utf-8 | yes, static key | **Exact body** (asserted byte-for-byte in `test_basics`): `\nUser-agent: *\nCrawl-delay: 2\nDisallow: /tags/*\nHost: gunlinux.ru\n` (leading newline). |
| 6 | GET | `/sitemap.xml` | 200 | — | application/xml (exact, no charset) | **NOT cached** | Body: `<?xml version="1.0" encoding="UTF-8"?>` + `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">` + one `<url><loc>/{alias}</loc></url>` per page (first, `get_page_posts`) then per published post (`get_published_posts`) + `</urlset>`. `loc` is **relative** (`/alias`). |
| 7 | GET | `/rss.xml` | 200 | — | application/rss+xml (exact, no charset) | yes, static key | Rendered `rss.xml` template; items from `get_published_posts()`; `<description>` = teaser of raw content; `<pubDate>`/`<lastBuildDate>` = current time UTC formatted `%a, %d %b %Y %H:%M:%S %z` → `+0000`; item `<link>` = `https://gunlinux.ru/{alias}`. |
| 8 | POST | `/md/` | 200 | — | application/json | **NOT cached** | **No auth, no CSRF, no side effects** (by design, documented in plan.md §5.8). Accepts `application/x-www-form-urlencoded` and `multipart/form-data`; reads field `data` (EasyMDE client sends urlencoded; multipart also supported). Body capped at 2 MiB. Response JSON: `{"data": "<rendered html>"}`. |
| 9 | GET | `/tags`, `/tags/` | 200 | — | text/html; charset=utf-8 | **NOT cached** | Dual-mode: full → `tags.html` (extends layout, `<h3 class="page__title">Tags</h3>`); htmx → `tags.htmx`. Both iterate `minipost`/`minipost__title`. |
| 10 | GET | `/tags/{alias}` | 200 | 404 unknown tag | text/html; charset=utf-8 | **NOT cached** | Full → `tag.html` (extends layout, includes `posts.htmx`); htmx → `posts.htmx`. Fragment shows `Посты с тэгом: {{tag.title}}`. |
| 11 | GET | `/static/*` | 200 | 404 for missing file | per file | — | `tower-http ServeDir` over `app/static` (see §6). A missing file returns 404 **from ServeDir** and must not fall through to the catch-all. |
| 12 | GET | `/{alias}` | 200 | 404 | text/html; charset=utf-8 | yes, htmx-aware key | **Catch-all; must be registered LAST** (§7.1). 404 when the post does not exist **or** when it is neither published (`publishedon IS NOT NULL`) nor a page (`is_page`). Full → `post.html` (extends layout, `<!DOCTYPE>`); htmx → `post.htmx` (no `<!DOCTYPE>`). Markers: `post__title`, `post__date`, `post__tags` (`tags__item`), `post__body` (contains `{{post.markdown|safe}}`). |

Route registration order (`app.rs`): `/`, `/posts`, `/hx/pages`, `/hx/icons`,
`/robots.txt`, `/sitemap.xml`, `/rss.xml`, `/md/`, `/tags`, `/tags/`,
`/tags/{alias}`, `nest_service("/static")`, admin router, then `/{alias}` **last**.

Pinned by tests (`test_basics`, `test_views`, `test_tags`):
- `GET /nonexistent-alias-xyz` → 404.
- `GET /tags` and `GET /tags/` → 200 (catch-all must not swallow `/tags`).
- `GET /static/dist/css/bundle.css` → 404 by default (bundle not built) with body **not** containing `postGroup`.
- Draft (unpublished, not a page) post view → 404.
- `POST /md/` with `data=%23+Title` → 200, JSON `data` contains `Title`; multipart `# Multi` → JSON `data` contains `<h1>Multi</h1>`.
- rss.xml: contains first-paragraph teaser text, must **not** contain the second paragraph.

### 1.2 Admin routes (auth-gated)

Sources: `rust/crates/web/src/admin.rs` (`router()`, handlers), `test_auth.rs`, `test_admin.rs`.

Auth gate: every handler except login/logout checks the signed `session` cookie;
unauthenticated → **302 Found** with `Location: /admin/login`. Unknown model slug
after auth → 404 (`/admin/nope/` with a valid cookie → 404).

| Method | Path | Success | Errors / notes |
|--------|------|---------|----------------|
| GET | `/admin` | 200 dashboard (lists the 5 models by plural name, e.g. `Posts`) | 302 → `/admin/login` when unauthenticated |
| GET | `/admin/login` | 200 login form | |
| POST | `/admin/login` | 303 See Other → `/admin` + `Set-Cookie: session=…` | failure → 200 re-render with body marker `Invalid username or password` |
| GET | `/admin/logout` | 302 Found → `/admin/login` + `Set-Cookie: session=; … Max-Age=0` | no auth required |
| GET | `/admin/{model}` and `/admin/{model}/` | 200 list (search/sort table) | 302 unauth; 404 unknown model |
| GET | `/admin/{model}/create` | 200 create form | 302 unauth |
| POST | `/admin/{model}/create` | 303 → `/admin/{slug}/` (cache cleared) | repo error → 200 re-render form with error text + preserved values; `NotFound` → 404 |
| GET | `/admin/{model}/{id}/edit` | 200 edit form | 302 unauth; 404 missing row |
| POST | `/admin/{model}/{id}/edit` | 303 → `/admin/{slug}/` (cache cleared) | error → 200 re-render; 404 |
| POST **and** GET | `/admin/{model}/{id}/delete` | 303 → `/admin/{slug}/` (cache cleared) | **result `Ok(false)` (row already gone) is ignored — still 303 + cache clear** |

`{model}` accepts singular and plural (`post`|`posts`, `category`|`categories`,
`tag`|`tags`, `user`|`users`, `icon`|`icons`). Login success redirect is `303
SEE_OTHER`; the unauthenticated redirect and logout redirect are `302 FOUND`.
Pinned by tests: create/edit/delete return 303 and invalidate the `"blog"` cache
(a pre-warmed listing shows the new/changed/deleted state on next GET).

---

## 2. HTMX contract

Sources: `rust/crates/web/src/routes.rs`, `rust/crates/web/templates/*`.

### 2.1 Dual-mode rendering rule

A route renders the **fragment** template instead of the full page **iff the
request carries the `HX-Request` header** (any value; only presence is checked —
`is_htmx_request()` in `routes.rs`). Full pages are `<!DOCTYPE>` documents that
`{% extends "layout.html" %}`; fragments are bare markup with no doctype.

Affected routes: `/posts`, `/tags`+`/tags/`, `/tags/{alias}`, `/{alias}`.
`/hx/pages` and `/hx/icons` are fragment-only by construction; `/` is full-only.

| Route | Full template | Fragment template |
|-------|---------------|-------------------|
| `/posts` | `posts.html` (bare, **no layout**, no doctype) | `posts.htmx` |
| `/tags`, `/tags/` | `tags.html` (extends layout) | `tags.htmx` |
| `/tags/{alias}` | `tag.html` (extends layout, `{% include 'posts.htmx' %}`) | `posts.htmx` (with `tag` context) |
| `/{alias}` | `post.html` (extends layout) | `post.htmx` |

### 2.2 Fragments and their swap targets (who swaps what)

| Fragment endpoint | Fragment template | `hx-get` trigger site | `hx-target` | `hx-swap` |
|---|---|---|---|---|
| `/posts` | `posts.htmx` | `index.html`: `<div hx-swap="posts" hx-get="/posts" hx-trigger="load" hx-target=".page__content">` | `.page__content` | `posts` (non-standard — see §8.2) |
| `/{alias}` | `post.htmx` | every `minipost__title` link in `posts.html`/`posts.htmx` (`hx-trigger="click"`, `hx-push-url="true"`); the header logo in `layout.html` (`hx-get="/posts"`); each page link in `pages.htmx`; and **`post.html` itself** (`hx-trigger="load"` re-fetches the same post) | `.page__content` | `posts` |
| `/hx/pages` | `pages.htmx` | `layout.html`: `<div hx-swap="innerHTML" hx-get="/hx/pages" hx-trigger="load" hx-target=".pages_nav">` | `.pages_nav` | `innerHTML` |
| `/hx/icons` | `icons/icons.htmx` | `footer.html`: `<div hx-swap="innerHTML" hx-get="/hx/icons" hx-trigger="load" hx-target=".footer__links">` | `.footer__links` | `innerHTML` |
| `/tags` | `tags.htmx` | `layout.html` nav link: `hx-get="/tags" hx-trigger="click" hx-target=".page__content"` (href `/tags/`; **no** `hx-push-url`) | `.page__content` | default |
| `/tags/{alias}` | `posts.htmx` | tag links in `post.html`/`post.htmx` (`hx-get="/tags/{alias}" hx-trigger="click" hx-target=".page__content"`; `post.htmx` also sets `hx-push-url="true"`, `post.html` does not) and tag links in `tags.htmx` (`hx-push-url="true"`) | `.page__content` | default |

htmx library: `https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js`
(in `layout.html`). Full-page `post.html` additionally loads highlight.js
(`github-dark.min.css`, `highlight.min.js`, `hljs.highlightAll()`).

Pinned by tests: `/hx/pages` and `/hx/icons` → 200 with no `<!DOCTYPE>`;
`GET /posts` with and without `HX-Request` both → no doctype, both contain
`postGroup`; `/{alias}` with `HX-Request` → no doctype; `GET /tags/htmx` full
contains `<!DOCTYPE>` and `Посты с тэгом: Htmx`; `GET /tags` with `HX-Request`
→ fragment contains `Linux`.

---

## 3. DB schema (6 tables)

Source: `rust/crates/persistence/src/migrator/m20260101_000001_create_schema.rs`
(baseline migration, mirrors `app/infrastructure/database.py`), entities in
`rust/crates/persistence/src/entities/*`.

Notes that apply to all tables:
- `INTEGER PRIMARY KEY AUTOINCREMENT` on every `id`.
- Timestamps are timezone-aware: Postgres `TIMESTAMPTZ`; SQLite stores ISO-8601
  text (`timestamp_with_time_zone_text`, TEXT affinity).
- All foreign keys have **NO ACTION** referential action (SQLAlchemy default) —
  including delete.
- **No server-side defaults anywhere.** Python applies defaults client-side
  (`createdon`, `authenticated=0`, `categories.page=False`); the repository
  always writes explicit values. The migration encodes the *column* definitions
  exactly (nullable, no DEFAULT).
- The single baseline migration is `m20260101_000001_create_schema` (the 16
  Alembic revisions collapse into it). Production cutover **stamps**, never
  re-runs it (§7.9).

### users
| Column | Type | Null | Default | Constraints |
|--------|------|------|---------|-------------|
| id | INTEGER | no | auto | PK, auto-increment |
| name | VARCHAR(50) | no | — | — |
| password | VARCHAR(255) | yes | — | bcrypt hash when set; domain maps NULL → `""` |
| authenticated | INTEGER | yes | none (client default 0) | 0/1 semantics; `bool(a) if a is not None else False` in domain; repository writes a value on every insert/update |
| createdon | TIMESTAMPTZ | yes | — | client-defaulted to now |

### categories
| Column | Type | Null | Default | Constraints |
|--------|------|------|---------|-------------|
| id | INTEGER | no | auto | PK |
| title | VARCHAR(255) | yes | — | NULL → `""` in domain |
| alias | VARCHAR(255) | yes | — | **UNIQUE** (unique key, nullable) |
| template | VARCHAR(255) | yes | — | |
| page | BOOLEAN | yes | none (client default False) | `TRUE` marks the category's posts as pages; `NULL`/`FALSE` = not a page |

### posts
| Column | Type | Null | Default | Constraints |
|--------|------|------|---------|-------------|
| id | INTEGER | no | auto | PK |
| pagetitle | VARCHAR(255) | no | — | |
| alias | VARCHAR(255) | no | — | **UNIQUE** |
| content | TEXT | yes | — | NULL → `""` in domain |
| createdon | TIMESTAMPTZ | yes | — | client-defaulted to now |
| publishedon | TIMESTAMPTZ | yes | — | `NULL` = draft; `NOT NULL` = published |
| category_id | INTEGER | yes | — | FK → `categories.id` (`fk-posts-category_id`, NO ACTION) |
| user_id | INTEGER | yes | — | FK → `users.id` (`fk-posts-user_id`, NO ACTION) |

### tags
| Column | Type | Null | Default | Constraints |
|--------|------|------|---------|-------------|
| id | INTEGER | no | auto | PK |
| title | VARCHAR(255) | yes | — | |
| alias | VARCHAR(255) | yes | — | **UNIQUE** (nullable) |

### posts_tags (m2m join)
| Column | Type | Null | Constraints |
|--------|------|------|-------------|
| post_id | INTEGER | no | part of composite PK `pk-posts_tags`; FK → `posts.id` (NO ACTION) |
| tag_id | INTEGER | no | part of composite PK; FK → `tags.id` (NO ACTION) |

Composite primary key `(post_id, tag_id)`; no surrogate `id` column. The Python
table declared no PK; SeaORM requires one, so the composite PK was chosen — it
also prevents duplicate links.

### icons
| Column | Type | Null | Default | Constraints |
|--------|------|------|---------|-------------|
| id | INTEGER | no | auto | PK |
| title | VARCHAR(255) | no | — | **UNIQUE** |
| url | VARCHAR(255) | no | — | **UNIQUE** |
| content | TEXT | yes | — | HTML/SVG snippet rendered `|safe` |

Down migration drops in reverse dependency order: posts_tags, icons, tags, posts,
categories, users.

Repository write semantics (`post_repository.rs`): on create/update, optional
fields are only written when `Some` (a `None` leaves the existing DB value /
NULL); `content` is always written (NULL → stored as empty string). Deletes
return `Ok(true)` if a row was affected, `Ok(false)` otherwise.

---

## 4. Auth contract

Sources: `rust/crates/web/src/auth.rs`, `rust/crates/web/src/admin.rs`,
`rust/crates/domain/src/security.rs`, `test_auth.rs`.

### 4.1 Session cookie
- Name: **`session`** (Starlette default).
- Value format: `base64url(json) + "." + hex(hmac_sha256(base64url(json), secret_key))`
  where `json` = `{"access_token": "<jwt>"}` (the JWT lives under the
  `access_token` key, matching the Python app's Starlette session).
- Signature check is constant-time; any tamper/malformed/unknown-secret cookie
  yields no session → treated as unauthenticated (302 to login). Verified by
  `test_session_cookie_is_tamper_evident`.
- Login `Set-Cookie`: `session=<value>; Path=/; HttpOnly; SameSite=lax; Max-Age=1209600`
  (14 days).
- Logout `Set-Cookie`: `session=; Path=/; HttpOnly; SameSite=lax; Max-Age=0`
  (asserted: starts with `session=;` and contains `Max-Age=0`).

### 4.2 JWT
- Algorithm HS256, signed with `settings.secret_key`.
- Claims: `{sub: <user name>, exp: now + jwt_expire_minutes * 60}`.
- `decode_token` returns `None` on **any** error (bad signature, expired,
  malformed) — mirrors python-jose's catch-all.
- Defaults (`settings.rs`, overridable via env / `.env`): `secret_key =
  "hard-to-guess-string-change-in-production"`, `jwt_expire_minutes = 1440`,
  `jwt_algorithm = "HS256"`.

### 4.3 Password hashing (bcrypt)
- New hashes: `bcrypt::hash(plain, bcrypt::DEFAULT_COST)` (cost 12).
- Verification: `bcrypt::verify`; **any** error (malformed hash, empty) → `false`,
  never panics. The cost is read from the stored hash, so **existing production
  hashes must keep verifying without re-hashing** — bcrypt must never be swapped
  for another scheme without a re-hash migration (plan.md §5.2).
- Login (`UserRepository::authenticate`): find user by `name`, then
  `verify_password(password, stored_hash)`; unknown name or mismatch → `None`.

---

## 5. Admin contract

Sources: `rust/crates/web/src/admin.rs` (handlers, `AdminModel` descriptors,
`AdminStore` impls), `rust/crates/web/templates/admin/*`, `test_admin.rs`.

### 5.1 Design
- Generic CRUD driven by one `AdminModel` descriptor + one `AdminStore` per
  entity; all writes go through the **repository traits** (no ORM bypass — this
  is the deliberate difference from the Python sqladmin).
- Every successful create/edit/delete calls `cache.clear_namespace("blog")`
  which invalidates the whole (single-namespace) response cache.
- Login is `UserService::authenticate_user` + JWT in the signed session cookie.
  **No throttling/rate-limiting** (the Python in-process throttle was intentionally
  not ported; Rust runs single-process).

### 5.2 The 5 AdminModel descriptors
| Model | slug | List columns | searchable | sortable | form_excluded |
|-------|------|--------------|------------|----------|---------------|
| Post | `post` | `id, pagetitle, alias, publishedon, category_id` | `pagetitle, alias` | `id, publishedon` | — |
| Category | `category` | `id, title, alias, page` | — | — | — |
| Tag | `tag` | `id, title, alias` | — | — | — |
| User | `user` | `id, name, createdon` | — | — | **`password`** |
| Icon | `icon` | `id, title, url` | — | — | — |

Registration order on the dashboard: Post, Category, Tag, User, Icon.

### 5.3 Form fields per model (create form; edit hides `form_excluded`)
| Model | Fields (input kind) |
|-------|---------------------|
| Post | `pagetitle` (text), `alias` (text), `content` (textarea), `publishedon` (text), `category_id` (text), `is_page` (checkbox) |
| Category | `title` (text), `alias` (text), `template` (text), `page` (checkbox) |
| Tag | `title` (text), `alias` (text) |
| User | `name` (text), `password` (text), `authenticated` (checkbox) |
| Icon | `title` (text), `url` (text), `content` (textarea) |

Checkbox semantics: present in the form data as `on` → true; absent/other → false
(`POST …&page=on` → `category.page = true`; `authenticated=` → false).

### 5.4 CRUD behavior details
- **Post create:** `createdon = now`, `user_id = None`, `category_id` parsed as
  `i32` (empty/invalid → `None`), `publishedon` parsed by `parse_datetime_field`
  (RFC3339 `2026-01-01T12:00:00Z` or naive `YYYY-MM-DDTHH:MM[:SS]` assumed UTC;
  empty → `None`; **unparseable → silently `None`**), `is_page` from checkbox.
- **Post edit:** same, but `createdon` and `user_id` are preserved from the
  existing row.
- **Category:** `template` empty string → `None`; `page` checkbox → `Some(true)`
  else `None`.
- **User create:** password **always bcrypt-hashed** (test asserts stored value
  starts with `$2` and verifies).
- **User edit:** the `password` field is not rendered (`test_admin_edit_form_hides_password`
  asserts no `name="password"` in the edit form); a blank password in the submit
  keeps the stored hash unchanged; a non-blank value is re-hashed.
- **Icon:** empty `content` → `None`.
- **List:** `?search=` = case-insensitive substring over `searchable` fields;
  `?sort=` honored only for `sortable` fields, otherwise sorted by `id`
  ascending. Delete button is a POST form with JS `confirm()`.
- **Errors:** `WebError::NotFound` → plain 404; any other error re-renders the
  form (200) with the error text and the submitted values preserved
  (`render_form_error`).

---

## 6. Static assets

Sources: `rust/crates/web/src/app.rs`, `webpack.config.js`.

- `/static` is served by `tower_http::services::ServeDir` from
  `app/static` (repo root), overridable via the `STATIC_DIR` env var.
- `app/static/dist/css/bundle.css` is the webpack output (`npm run build`;
  `MiniCssExtractPlugin` → `css/bundle.css`). **After a build, `GET
  /static/dist/css/bundle.css` must return 200.** It is the stylesheet referenced
  by `layout.html` and every admin template.
- `app/static/img/favicon.ico` is referenced by `layout.html`.
- Static sources live under `app/static/src/` (component CSS) with fonts in
  `app/static/fonts/` and `css/admin.css` for admin styling.
- Missing files under `/static` → 404 from ServeDir (must not be shadowed by the
  `/{alias}` catch-all).

---

## 7. Cross-cutting invariants

1. **Route ordering:** `/static`, `/tags`, `/admin` are registered **before** the
   catch-all `GET /{alias}`, which is registered last so it never shadows them
   (`app.rs`; pinned by `test_catch_all_does_not_shadow_tags_or_static` and
   `test_tags_index_without_slash`).
2. **Cache:** one shared in-process `moka` cache (single-process server), TTL
   **50 s**, namespace `"blog"` (`cache.rs`). Only **200** responses are cached
   (non-200 pass through uncached). Keys: htmx-aware routes →
   `blog:{path_and_query}:{HX-Request header value}` (`path_and_query` includes
   the query string); static-key routes (`/robots.txt`, `/rss.xml`) →
   `blog:{path_and_query}:`. **Not cached:** `/sitemap.xml`, `/tags*`, `POST
   /md/`, all admin routes. Cache invalidation = `invalidate_all()` on the
   single namespace, triggered by every admin write.
3. **`is_page` derivation:** derived from the post's category, never stored on
   the post: `is_page = category_id IS NOT NULL AND category.page IS TRUE`
   (domain `Post.is_page`, computed in `post_repository::to_domain` via
   `bool(category.page)`).
4. **Published vs pages vs listing:**
   - `get_published_posts` (RSS, sitemap): `publishedon IS NOT NULL AND
     category_id IS NULL`, ordered `publishedon DESC`.
   - `get_all_published_content` (`/posts`): `publishedon IS NOT NULL AND
     NOT (category.page IS TRUE)` (null-safe — uncategorized posts included),
     ordered `publishedon DESC`.
   - `get_page_posts` (`/hx/pages`, sitemap pages): inner-join categories where
     `page IS TRUE`, **no ORDER BY** (see §8.1).
   - `get_posts_by_tag` (`/tags/{alias}`): posts linked via `posts_tags`,
     **no ORDER BY** and **no published filter** — drafts linked to a tag
     appear in the tag listing (their direct `/alias` URL still 404s; see
     §8.1).
   - `get_tags_for_post`: tags linked via `posts_tags`, **no ORDER BY**.
   - `/{alias}` visibility: published OR page; anything else → 404.
5. **Teaser truncation** (RSS `<description>`, `Post::teaser`): first paragraph
   = text before the first `\n\n` (split, then trimmed); if > 300 characters
   (Unicode chars), truncate to 300, strip trailing whitespace, append `…`
   (ellipsis). Operates on **raw content** — no markdown rendering or HTML
   stripping. Pinned: teaser ≤ 301 chars and ends with `…` for 500-char input;
   RSS body excludes the second paragraph.
6. **Markdown rendering** (`domain::post::render_markdown`): `comrak` with all
   GFM extensions **disabled** (strikethrough, table, tasklist, autolink,
   tagfilter, superscript, footnotes, description_lists = false),
   `render.unsafe_ = true` (**raw HTML passes through unsanitized** — admin
   content is trusted), `hardbreaks = false`. Intended to match python-markdown
   with only the `fenced_code` extension (test: `# Hello` → `<h1>Hello</h1>`,
   fenced code → `<pre><code>`).
7. **RSS feed shape** (`rss.xml` template): `rss version="2.0"`; channel title
   `gunlinux`, link `http://gunlinux.ru`, description `gunlinux blog abour`
   (typo preserved verbatim), language `ru-ru`, `generator` `gunlinux.ru`;
   `<pubDate>` and `<lastBuildDate>` = now, `%a, %d %b %Y %H:%M:%S %z`; one
   `<item>` per published post with `<title>` = pagetitle, `<link>` =
   `https://gunlinux.ru/{alias}`, `<description>` = teaser.
8. **Sitemap shape:** pages first then published posts; relative `<loc>`; exact
   content-type `application/xml`; not cached.
9. **Migrations:** one baseline (`m20260101_000001_create_schema`); prod
   cutover stamps, never re-runs. The server binary applies `Migrator::up` at
   startup (SQLite dev DB only).
10. **Templates:** Minijinja with `UndefinedBehavior::Chainable` (loops over
    undefined render nothing — e.g. footer `icons` filled only by htmx); filters
    `strftime` (supported directives `%a %b %B %d %Y %H %M %S %z`; `%z` always
    renders `+0000`) and `teaser`; global `settings` exposes
    `yandex_verification` (optional) and `yandex_metrika` (default `76938046`);
    Yandex.Metrika snippet conditionally included in `footer.html`.
11. **Post listing grouping** (`group_posts_by_year`): posts grouped by
    publication year, years descending; posts keep repository order within a
    year (already `publishedon DESC` for published routes).
12. **Domain null-coercions:** `posts.content` NULL → `""`; `users.password`
    NULL → `""`; `users.authenticated` NULL → false (non-zero integer → true);
    `categories.title/alias` and `tags.title/alias` NULL → `""`.

---

## 8. Ambiguities & implicit behavior (not pinned by any test)

These are behaviors the code has that no test asserts and no spec states. A
parity check should be aware of them; do not "fix" them without a documented
reason.

1. **Unspecified ordering:** `get_page_posts` (`/hx/pages`, sitemap pages),
   `get_posts_by_tag`, `get_tags_for_post`, `get_all_tags` (`/tags`) and
   `Repository::get_all` have **no ORDER BY** — result order is
   database-dependent (rowid/insertion order in SQLite). Only
   `get_published_posts` / `get_all_published_content` pin `publishedon DESC`.
   Related: `get_posts_by_tag` has no published filter, so a **draft linked to
   a tag is listed on `/tags/{alias}`** yet 404s when its own `/alias` is
   requested (pinned by the in-progress `test_services.rs`, not by the shipped
   route tests).
2. **`hx-swap="posts"`:** a non-standard htmx swap value appearing on the header
   logo, minipost links, page links and the index/post load-divs. htmx treats an
   unknown swap as `innerHTML`. Preserved verbatim from the Python templates.
3. **Dead templates:** `templates/sqladmin/post_create.html` and
   `post_edit.html` are vendored leftovers that `{% extends %}` non-existent
   bases (`sqladmin/create.html`/`edit.html`). They are registered with Minijinja
   (parse succeeds) but never rendered by any handler; rendering one would error.
4. **`/` cache-key quirk:** the index handler always renders the full page but
   uses the htmx-aware cache key, so `GET /` with and without `HX-Request` occupy
   separate cache entries with identical bodies.
5. **`post.html` self-load:** the full post page renders the article and then
   `hx-get="/{alias}"` on `load` replaces `.page__content` with the fragment —
   the article is re-rendered via htmx immediately after load.
6. **Delete of a missing row:** the admin delete handler ignores the
   repository's `Ok(false)` and still redirects 303 and clears the cache.
7. **No login throttling:** the Python in-process login throttle was
   intentionally not ported (single-process Rust). Login is also not protected
   by CSRF (the whole admin is cookie-authenticated; plan.md §5.8 documents the
   no-CSRF position for `POST /md/` only).
8. **`users.authenticated` is not enforced:** login checks only name + bcrypt.
   A user with `authenticated = 0`/`false` can still log in. The flag is
   stored and shown in admin forms but consulted nowhere.
9. **`publishedon` parse failure:** an invalid (non-RFC3339, non-naive)
   datetime in the admin post form silently becomes `None` (draft) instead of a
   form error.
10. **`robots.txt` leading newline:** the exact body starts with `\n` (see §1.1
    #5) — byte-for-byte comparison must preserve it.
11. **Route `GET /md/` mismatch:** only `POST /md/` is registered; a `GET /md/`
    hits the catch-all `/{alias}` and returns 404 (missing post).
12. **Tag/aliases with trailing slash:** `/tags/{alias}` does not accept a
    trailing slash; `/tags/` is a distinct route from `/tags`.

---

## Appendix — files that pin this contract

- `plan.md` §1 (Python inventory), §2 (target architecture), §5 (risks).
- `rust/crates/web/src/app.rs` — router assembly + route ordering + static dir.
- `rust/crates/web/src/routes.rs` — all public handlers, status codes, cache keys.
- `rust/crates/web/src/admin.rs` — admin routes, `AdminModel` descriptors, CRUD,
  cache invalidation.
- `rust/crates/web/src/auth.rs` — session cookie + JWT.
- `rust/crates/domain/src/security.rs` — bcrypt.
- `rust/crates/domain/src/post.rs` — markdown (comrak), teaser.
- `rust/crates/domain/src/repositories.rs` — repository trait contract.
- `rust/crates/persistence/src/migrator/m20260101_000001_create_schema.rs` — DDL.
- `rust/crates/persistence/src/repositories/*.rs` — query semantics (filters,
  ordering, `is_page` derivation, write semantics).
- `rust/crates/web/templates/**` — dual-mode and htmx attribute inventory.
- `rust/crates/web/tests/*` — pinned status codes and body markers.
