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

All runs pass every threshold (`make perf` exits 0).

## Notes

- **Baseline** was captured before the cache rework: cache hits served from
  moka with zero DB round-trips. After the rework every request pays one cheap
  `MAX(COALESCE(update_date, createdon, publishedon))` query — the price of
  content-fresh caching (new/edited posts invalidate all cached pages
  instantly, no timer wait).
- **Memory fallback ≈ baseline** (5.32 vs 5.55 ms p(95)): the version query
  is absorbed by the local network; page renders are ~1.6 ms slower (full page
  p(95) 2.89 vs 1.31 ms) because the version lookup runs before every render.
- **Redis adds ~4.6 ms p(95)** over the memory fallback: connection-manager
  GET + JSON decode + set on miss. Still ~50× under the SLO.
- Stale content-version keys are bounded by a 600 s safety-net TTL (memory:
  moka `max_capacity` 4096; Redis: `SETEX`). Admin writes still clear the
  whole `blog:*` namespace (covers deletes, tags, icons, categories).
- SLO headroom is enormous in both backends; the bottleneck is the DB
  connection round-trip, not the cache backend.
