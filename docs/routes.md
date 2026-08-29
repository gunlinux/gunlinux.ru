# Routes

All HTTP routes of the Rust (axum) blog app. Source of truth:
`rust/crates/web/src/app.rs` (router assembly) and
`rust/crates/web/src/admin.rs` (admin router).

## Router structure

The router is assembled in `app::build_app_with_static` in this order:

1. Public routes (`/`, `/posts`, `/hx/icons`, `/robots.txt`, `/sitemap.xml`,
   `/rss.xml`, `/md/`, `/tags*`).
2. `nest_service("/static", ServeDir)` — static files from `STATIC_DIR`
   (default `app/static`).
3. `merge(admin::router())` — all `/admin*` routes.
4. **Catch-all `GET /{alias}` last** — the ordering constraint is critical:
   `/tags`, `/admin` and `/static` must never be shadowed by it.

Two global layers wrap everything:

- `analytics::track_visit` — records one `page_views` row per full-page HTML
  load (GET, `Accept: text/html`, no `HX-Request`, excludes `/static`,
  `/admin` and machine endpoints). Best-effort: failures are logged, never
  fail the request. Runs BEFORE the response cache so cache hits are counted
  exactly once.
- `tower_http::trace::TraceLayer` — HTTP request/response tracing.

## Conventions

- **htmx dual-mode:** if the `HX-Request` header is present, the `*.htmx`
  fragment template is rendered; otherwise the full `*.html` page. Cache keys
  are htmx-aware.
- **Caching:** cached GET routes use the response cache (Redis when
  `REDIS_URL` is set, in-memory moka otherwise). Keys carry a content version
  from `MAX(update_date, createdon, publishedon)` so new/edited posts
  invalidate instantly. Only `200` responses are cached. Admin writes clear
  the whole namespace. `/sitemap.xml`, `/tags*` and `POST /md/` are NOT
  cached.
- **404:** missing posts, tags and admin models return the pinned
  `{"detail":"Not Found"}` body with `application/json`
  (`routes::not_found()`).
- **Auth:** admin routes require a valid JWT (HS256, `{sub, exp}`) wrapped in
  the signed `session` cookie. Unauthenticated requests get a `302` redirect
  to `/admin/login`.

## Public routes

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/` | `routes::index` | Index page: posts grouped by year, server-rendered into `index.html`. Cached (htmx-aware key, no htmx variant exists). |
| GET | `/posts` | `routes::posts` | Full post listing; `posts.html` or `posts.htmx` fragment. Cached. |
| GET | `/hx/icons` | `routes::icons_hx` | Footer icons fragment (`icons/icons.htmx`) for htmx swaps. Cached. |
| GET | `/robots.txt` | `routes::robots` | Fixed robots body (`text/plain`). Cached with a static key. |
| GET | `/sitemap.xml` | `routes::sitemap` | Relative `<loc>/alias</loc>` entries for pages then published posts. NOT cached. |
| GET | `/rss.xml` | `routes::rss` | RSS feed from published posts, rendered from `rss.xml` template (`application/rss+xml`). Cached with a static key. |
| POST | `/md/` | `routes::getmd` | Markdown → HTML preview helper for the admin editor. Accepts urlencoded `data` (EasyMDE) and `multipart/form-data`. Public, no auth, no CSRF (no side effects). Uses `render_markdown_preview` (fenced blocks render as inline `<code>`). Returns `{"data": "<html>"}`. NOT cached. |
| GET | `/tags` | `routes::tags_index` | Tag cloud; `tags.html` or `tags.htmx`. NOT cached. |
| GET | `/tags/` | `routes::tags_index` | Same as `/tags` (trailing slash). |
| GET | `/tags/{alias}` | `routes::tag_view` | Posts for one tag (`tag.html` or `posts.htmx`). Unknown tag → 404. NOT cached. |
| GET | `/static/*` | `ServeDir` | Static assets from `STATIC_DIR` (e.g. `app/static`). Registered via `nest_service`. |
| GET | `/{alias}` | `routes::post_view` | **Catch-all (registered LAST):** post or page view; `post.html` or `post.htmx`. Missing or non-published, non-page alias → 404. Cached (htmx-aware key). |

## Admin routes

Auth: every handler below checks the `session` cookie and `302`-redirects to
`/admin/login` when absent/invalid (except the login routes themselves).
`{model}` must be one of `post`, `category`, `tag`, `user`, `icon` — anything
else → 404. Every successful write clears the cache namespace.

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/admin` | `admin::dashboard` | Dashboard: entity counts + total views. |
| GET | `/admin/` | `admin::dashboard` | Same as `/admin` (trailing slash). |
| GET | `/admin/login` | `admin::login_get` | Login form (`admin/login.html`). |
| POST | `/admin/login` | `admin::login_post` | Authenticates form fields `username` + `password` (bcrypt). Success: sets the `session` cookie and redirects to `/admin`; failure: re-renders the form with "Invalid username or password". |
| GET | `/admin/logout` | `admin::logout` | Clears the `session` cookie, redirects to `/admin/login`. |
| GET | `/admin/stats` | `admin::stats` | Visit analytics: totals, unique visitors, 14-day daily chart, top referrer sources and top landing pages (30-day window). |
| GET | `/admin/{model}` | `admin::list` | List rows, paginated (25/page). Query params: `search` (searchable columns), `sort` (sortable column), `dir=desc`, `page`. htmx requests swap only `admin/list_table.html`; others render `admin/list.html`. |
| GET | `/admin/{model}/` | `admin::list` | Same as `/admin/{model}` (trailing slash). |
| GET | `/admin/{model}/create` | `admin::create_form` | Empty create form (`admin/form.html`). |
| POST | `/admin/{model}/create` | `admin::create` | Creates the row from the form; `303` redirect to `/admin/{model}/`. Validation errors re-render the form with the submitted values. |
| GET | `/admin/{model}/{id}/edit` | `admin::edit_form` | Edit form pre-filled from the row; unknown id → 404. |
| POST | `/admin/{model}/{id}/edit` | `admin::edit` | Updates the row from the form; `303` redirect to `/admin/{model}/`. Validation errors re-render the form. |
| GET | `/admin/{model}/{id}/delete` | `admin::delete` | Deletes the row (GET-triggered delete), redirects to `/admin/{model}/`. |
| POST | `/admin/{model}/{id}/delete` | `admin::delete` | Deletes the row, redirects to `/admin/{model}/`. |

Admin model details (`admin::AdminModel` descriptors):

| slug | name (plural) | columns | searchable | sortable | form-excluded |
|------|---------------|---------|------------|----------|---------------|
| `post` | Post (Posts) | id, pagetitle, alias, publishedon, category_id | pagetitle, alias | id, publishedon | — |
| `category` | Category (Categories) | id, title, alias, page | title, alias | id, title | — |
| `tag` | Tag (Tags) | id, title, alias | title, alias | id, title | — |
| `user` | User (Users) | id, name, createdon | name | id, name | password |
| `icon` | Icon (Icons) | id, title, url | title | id, title | — |

`User.password` is excluded from the form: a blank password keeps the existing
hash.

## Error responses

- **404:** `{"detail":"Not Found"}` with `application/json` — produced by
  `routes::not_found()` for unknown post aliases, unknown tags and unknown
  admin models/ids.
- **409 Conflict:** from `WebError::Conflict` (e.g. duplicate alias on
  admin create/edit).
- **500:** from `WebError::Internal`.
