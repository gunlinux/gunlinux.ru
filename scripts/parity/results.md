# Parity results — Python vs Rust, 2026-08-23 (final, post parity-fixes)

Run via `./scripts/parity/parity.sh` against scratch SQLite DBs seeded from
`seed.sql` (5 posts incl. draft + page post, 2 categories, 2 tags, 3
posts_tags links, 1 user, 2 icons). Python: uvicorn `main:app` on :8100.
Rust: `target/debug/server` on :8101 (`DATABASE_URL`, `BIND_ADDR`, `STATIC_DIR`
envs; migrations applied on startup). 19 routes compared — status code +
normalized body, plus a whitespace-sensitive raw body.

This run is **after** the parity fixes (2026-08-23): 404 bodies now emit
FastAPI's JSON `{"detail":"Not Found"}`, `POST /md/` uses a python-markdown-
compatible renderer (`domain::post::render_markdown_preview`), and the admin
index is registered at both `/admin` and `/admin/`.

## Route-by-route comparison (final)

| # | Route | PY | RS | STATUS | BODY(norm) | BODY(raw) |
|---|---|---|---|---|---|---|
| 1 | `GET /` | 200 | 200 | MATCH | MATCH | MATCH |
| 2 | `GET /posts` | 200 | 200 | MATCH | MATCH | MATCH |
| 3 | `GET /hx/pages` | 200 | 200 | MATCH | MATCH | MATCH |
| 4 | `GET /hx/icons` | 200 | 200 | MATCH | MATCH | MATCH |
| 5 | `GET /robots.txt` | 200 | 200 | MATCH | MATCH | MATCH |
| 6 | `GET /sitemap.xml` | 200 | 200 | MATCH | MATCH | MATCH |
| 7 | `GET /rss.xml` | 200 | 200 | MATCH | MATCH | MATCH¹ |
| 8 | `POST /md/` | 200 | 200 | MATCH | **DIFF**² | **DIFF**² |
| 9 | `GET /tags` | 200 | 200 | MATCH | MATCH | MATCH |
| 10 | `GET /tags/rust` | 200 | 200 | MATCH | MATCH | MATCH |
| 11 | `GET /hello-world` | 200 | 200 | MATCH | MATCH | DIFF³ |
| 12 | `GET /about-page` | 200 | 200 | MATCH | MATCH | DIFF³ |
| 13 | `GET /draft-post` | 404 | 404 | MATCH | MATCH | MATCH |
| 14 | `GET /admin` | **404** | **302** | **DIFF**⁴ | DIFF | DIFF |
| 15 | `GET /admin/` | 302 | 302 | MATCH | MATCH | MATCH |
| 16 | `GET /admin/login` | 200 | 200 | MATCH | **DIFF**⁵ | **DIFF**⁵ |
| 17 | `GET /static/dist/css/bundle.css` | 200 | 200 | MATCH | MATCH | MATCH |
| 18 | `GET /nonexistent-xyz` | 404 | 404 | MATCH | MATCH | MATCH |
| 19 | `GET /tags/nonexistent-xyz` | 404 | 404 | MATCH | MATCH | MATCH |

¹ Channel `pubDate`/`lastBuildDate` are `datetime.now()`-based and stripped by
the normalizer. All per-item dates and teasers matched exactly.
² Only residual `/md/` difference: python-markdown keeps the blank line after a
raw-HTML block before a list (`</div>\n\n<ul>`), CommonMark collapses it
(`</div>\n<ul>`). Whitespace-only, documented in MIGRATION_CONTRACT.md.
³ Whitespace-only blank-line placement in page markdown rendering.
⁴ Bare `/admin`: Python's sqladmin index lives at `/admin/`, so bare `/admin`
falls to the catch-all 404; Rust serves the dashboard at `/admin` → 302
login. Deliberate Thread-B deviation (more useful URL), documented.
⁵ Admin login markup differs completely — expected (sqladmin vs the custom
repository-based admin, Thread B), not part of the frozen public contract.

**Summary: 19 routes — 18 status MATCH, 1 documented DIFF (`/admin` bare);
16 normalized-body MATCH, 3 DIFF (all documented deviations: `/md/` blank
line, `/admin` root, `/admin/login` markup); 14 raw-body MATCH, 5 DIFF
(whitespace-only + the same three).**

## Fixed since the first run (2026-08-23)

1. **404 bodies** — Rust now returns FastAPI's exact `{"detail":"Not Found"}`
   with `application/json` (Starlette compact separators) for the catch-all,
   draft-post and unknown-tag 404s. Was: empty body.
2. **`POST /md/`** — new `render_markdown_preview` (comrak with the same
   options as pages, then fenced `<pre><code>` blocks converted back to
   python-markdown's inline `<p><code>lang\ncontent</code></p>` form, with
   comrak's `&quot;` unescaped and trailing newline trimmed). The sample
   fence now matches byte-for-byte. Only residual: the raw-HTML blank line.
3. **`/admin/`** — trailing-slash route registered → 302 to login, matching
   Python's `/admin/` behavior. (Rust keeps bare `/admin` → 302 as a
   documented improvement over Python's 404.)

## Checks that passed (no drift)

- HTML escaping (pagetitle with `&` — `.html` autoescaped, `.htmx` raw) —
  identical on both sides.
- Fenced code, raw HTML pass-through, links with `&`, inline code, Cyrillic —
  identical on post pages.
- `/sitemap.xml` identical (pages then published posts, same ordering).
- Teaser truncation identical (char-based, ≤301 chars, `…` suffix).
- RSS per-item `pubDate`s + teasers byte-identical.
- `/static/dist/css/bundle.css` byte-identical.
- All 404 status codes + bodies identical.

## Known deviations (documented in MIGRATION_CONTRACT.md)

- Bare `/admin` (404 py / 302 rs) — deliberate Thread-B admin improvement.
- `/admin/login` markup — custom admin vs sqladmin (Thread B).
- `/md/` blank line after raw-HTML blocks — python-markdown vs CommonMark
  whitespace quirk.
- RSS channel-date format: Python naive (no `%z`), Rust `+0000` — run-specific
  anyway.
- Admin CRUD + htmx dual-mode routes are covered by the Rust test suite
  (`test_admin`, `test_auth`, `test_browser`) rather than the live matrix —
  auth-gated and browser-executed respectively.

## Environment notes

- The earlier blocker (optional dev-dependencies breaking `cargo build`) is
  resolved — both `postgres-parity` and `browser-tests` now use optional
  regular dependencies behind features.
- Rust server's plain `sqlite:///…` URL cannot create a missing DB file (sqlx
  needs `?mode=rwc`); the harness pre-creates the scratch file.
- Both apps default to SQLite and the repo `.env` does not set
  `DATABASE_URL`, so no production/remote DB is involved at any point.

Artifacts from this run: `scripts/parity/tmp/{python,rust}.db`,
`tmp/*.log`, `tmp/out/` (per-route `.py.raw/.rs.raw/.py.norm/.rs.norm`
snapshots), `tmp/out/summary.txt`.

**Note:** the harness requires the Python app (`main:app` + `.venv`); once
Stage 9 removes the Python codebase (plan.md T17), this harness is archived
as a historical record — the golden outputs above are the frozen reference.
