# Parity harness — gunlinux.ru Python (FastAPI) vs Rust (axum)

> **⚠️ Archived.** This harness requires the Python app, which Stage 9 removed
> (plan.md T17) — it cannot be re-run. Kept as a historical record; the golden
> comparison lives in `results.md`.

Side-by-side behavioral comparison of the legacy Python app and the Rust
rewrite, run against **two scratch SQLite databases seeded with identical
data** (plan.md Task T16, first half / Stage 9 parity). The harness starts
both apps, runs the route matrix from plan.md §1 against each, and reports a
PASS/DIFF table. It finds divergences — it does **not** fix them.

## Layout

```
scripts/parity/
├── parity.sh      # orchestrator: DBs -> seed -> start both apps -> compare -> cleanup
├── seed.sql       # identical seed applied to both DBs (fixed IDs, RFC3339 timestamps)
├── compare.py     # route matrix + normalization + diff (stdlib only)
├── README.md      # this file
├── results.md     # actual comparison results from the latest run
└── tmp/           # scratch DBs, app logs, per-route response snapshots (git-ignored)
```

## How to run

```bash
./scripts/parity/parity.sh
```

What happens (see `parity.sh` for details):

1. **Python DB** — `alembic upgrade head` (schema) then `seed.sql`, into
   `tmp/python.db`.
2. **Python app** on **127.0.0.1:8100** — `uv run uvicorn main:app --port 8100`
   (ASGI equivalent of the Makefile's granian line; single worker avoids the
   known multi-worker cache bug).
3. **Rust app** on **127.0.0.1:8101** — `cargo build -p server` then
   `target/debug/server` with `DATABASE_URL`, `BIND_ADDR=127.0.0.1:8101`,
   `STATIC_DIR` (repo `app/static`). Migrations apply on startup, then
   `seed.sql` is applied. If `cargo build` fails (e.g. the workspace is
   mid-edit), the harness falls back to an existing `target/debug/server`
   binary and warns.
4. **Compare** — `compare.py` runs the route matrix against both apps, compares
   status code + normalized body, prints the table, and saves per-route raw and
   normalized bodies to `tmp/out/`.
5. **Cleanup** — both processes are killed; `tmp/` (DBs, logs, snapshots) is
   kept for investigation.

Re-running re-creates both DBs from scratch, so results are reproducible.

## Safety

- **No production/remote database is ever touched.** Both apps run against
  scratch SQLite files under `tmp/`. The repo `.env` has no `DATABASE_URL`
  (it sets `SQLALCHEMY_DATABASE_URI`, which neither app reads); the harness
  sets `DATABASE_URL` explicitly for both processes.
- **Ports 8000/8001 (user dev servers) are untouched.** The harness uses
  8100/8101 and refuses to start if those are already bound.
- No application code (Python or Rust) is modified by the harness.

## What is compared

Routes (from plan.md §1, plus extras):

| Route | Notes |
|---|---|
| `GET /`, `/posts`, `/hx/pages`, `/hx/icons` | cached public pages / htmx fragments |
| `GET /robots.txt` | exact text |
| `GET /sitemap.xml`, `/rss.xml` | XML feeds |
| `POST /md/` | markdown preview (urlencoded `data=`) |
| `GET /tags`, `/tags/{alias}` | tag cloud + tag view |
| `GET /{alias}` | `hello-world`, `about-page`, `draft-post` (404), `nonexistent-xyz` (404) |
| `GET /admin`, `/admin/`, `/admin/login` | auth redirect + login page |
| `GET /static/dist/css/bundle.css` | static asset |

Per route the harness records: **status code**, **normalized body**, and a
**raw body** (normalization = strip dynamic RSS channel dates, collapse
whitespace for HTML/XML/JSON; raw = only the dynamic-date strip). This
distinguishes semantic differences from pure-whitespace ones (e.g.
`<pre><code>` block line endings).

## Seed data

`seed.sql` covers the parity-relevant surface:

- 2 categories (one regular, one `page=1` so `is_page` posts exist);
- 2 tags + 3 `posts_tags` links;
- 1 user with a real bcrypt hash (`parity-admin-pass`);
- 5 posts: published-with-category, draft (unpublished), page post, and two
  uncategorized published posts (feed/sitemap + long-teaser truncation);
  content deliberately includes fenced code, raw/inline HTML, links with `&`,
  Cyrillic, and a pagetitle containing `&` (escaping check).

Fixed IDs and RFC3339 timestamps (`2026-01-15T12:00:00+00:00`) guarantee both
apps read byte-identical rows and render identical dates.

## Extending the route matrix

Edit the `ROUTES` list at the top of `compare.py`. Each entry is
`(method, path, body, kind, note)` where `kind` selects normalization:
`html`/`xml`/`rss`/`json` collapse whitespace (and `rss` strips the dynamic
channel dates), `text` is compared byte-for-byte, `css` collapses whitespace.
Add a seed row in `seed.sql` for any new content-dependent route. Re-run
`parity.sh`; per-route snapshots land in `tmp/out/`.

## Interpreting results

- **STATUS DIFF** — the two apps disagree on the HTTP status code (real
  divergence or auth-gating difference).
- **BODY(norm) DIFF** — normalized bodies differ (semantic difference).
- **BODY(raw) DIFF with norm MATCH** — only whitespace differs (e.g.
  markdown blank-line placement), semantically equivalent.
