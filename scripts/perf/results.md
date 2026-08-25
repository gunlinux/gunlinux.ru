# Performance results — k6 load test (`make perf`)

Run with `make perf` (default profile: warm-up 10s @10 VUs → peak 30s @50 VUs →
cool-down 10s; thresholds encode the SLO — `p(95) < 500ms` HTTP,
`p(95) < 300ms` page fragment + markdown preview, `checks > 99%`).

Target: dev server (`rust/target/debug/server`) on `localhost:8000`, serving
real content from the dev PostgreSQL (`db.test`). The load-test script harvests
live post/tag aliases from the homepage, mixes full-page HTML + htmx fragment
requests, and hammers `POST /md/`.

| Run (2026-08-25) | Cache backend | HTTP p(95) | page_full p(95) | page_fragment p(95) | md_render p(95) | req/s | checks |
|---|---|---|---|---|---|---|---|
| baseline (before Redis work) | moka, fixed 50s TTL, unversioned keys | 5.55 ms | 1.31 ms | 1.24 ms | 1.68 ms | 67.9 | 100% |
| with smart invalidation | moka (memory fallback) | 5.32 ms | 2.89 ms | 3.00 ms | 1.60 ms | 67.9 | 100% |
| with smart invalidation | Redis (Valkey 8.1, `redis://:…@127.0.0.1:6379`) | 9.96 ms | 10.83 ms | 8.85 ms | 3.39 ms | 66.9 | 100% |
| **no cache at all** (`CACHE_DISABLED=1`) | — (every request fully renders) | 8.71 ms | 9.28 ms | 7.69 ms | 1.74 ms | 67.8 | 100% |

All runs pass every threshold (`make perf` exits 0).

## What the cache is worth

On this box (server, DB and Redis all on localhost, small pages, one
instance):

| Backend | HTTP p(95) | vs cacheless |
|---|---|---|
| memory (moka) | 5.32 ms | **1.6× faster** |
| cacheless | 8.71 ms | 1× |
| Redis (Valkey) | 9.96 ms | 1.1× **slower** |

- **Memory cache wins**: hits skip the render entirely, leaving only the
  ~0.5 ms version query. Cacheless pays a full render per request.
- **Redis ≈ cacheless here** — a cache *hit* costs a `GET` of a JSON string
  (~3–5× the page size: `Vec<u8>` bodies serialize as byte arrays) plus
  serde_json decode, which on localhost costs about as much as just
  re-rendering. The Redis backend's real value is a *shared* cache across
  multiple app instances (and keeping render CPU off the app under load), not
  raw latency on a single box. A binary storage format (raw bytes or
  bincode) would bring hits down to ~memory-cache cost.
- **Why the version query is in every run**: content-fresh keys
  (`blog:v{max-update}:…`) require one cheap
  `MAX(COALESCE(update_date, createdon, publishedon))` per request; a
  new/edited post invalidates all cached pages instantly, no timer wait.
- Stale content-version keys are bounded by a 600 s safety-net TTL (memory:
  moka `max_capacity` 4096; Redis: `SETEX`). Admin writes still clear the
  whole `blog:*` namespace (covers deletes, tags, icons, categories).
- All three backends sit far under the SLO (500 ms HTTP / 300 ms fragments);
  the bottleneck everywhere is the local DB round-trip, not the cache.
