# Tasks — Rust migration (status 2026-08-23)

> Working checklist extracted from `plan.md`. All implementation tasks are
> **complete**; the only remaining items are the **operator-executed
> production cutover** (Stage 8) — everything is prepared, the live switch is
> deliberately manual.
>
> **Legend:** ✅ done · 📋 prepared, operator executes · ⬜ pending

## Overall status

- **111 Rust tests** passing across features (98 default: domain 11 ·
  repositories 10 · web lib 11 · admin 10 · auth 8 · basics 8 · services 21 ·
  tags 3 · views 16; +10 Postgres parity; +3 browser E2E). fmt + clippy clean.
- Parity vs Python: **18/19 status MATCH**; remaining DIFFs documented
  (admin root / `/admin/login` markup — Thread B — and a whitespace-only
  `/md/` raw-HTML blank line).
- Python app removed; README/CLAUDE rewritten; contract doc created.
- ⚠️ `origin/master` is Flask-era (`a808b26`), local `master` ahead 18 — the
  cutover push jumps prod straight to the Rust build (see `deploy/CUTOVER.md`).

## Stage 0 — Contract

- [x] **T1** `MIGRATION_CONTRACT.md` — created (routes, status codes, bodies,
      htmx matrix, schema, auth + ambiguities section).
- [x] **T2** Contract freeze — pinned by the contract doc + route suites +
      final parity run.
- [x] **T3** Stale docs — rewritten (`README.md`, `CLAUDE.md`, `deploy.sh`).

## Stage 3 — Persistence

- [x] **T4** Postgres parity suite — `postgres-parity` feature (testcontainers
      / `TEST_DATABASE_URL`), shared suite bodies, CI job. Exposed + fixed a
      real `page IS NOT $1` divergence.
- [x] **T5** Stage 3 acceptance — SQLite **and** Postgres runtime-verified.

## Stage 4 — Services

- [x] **T6** Service tests — 21 tests in `web/tests/test_services.rs`
      (in-memory fake repos).
- [x] **T7** Stage 4 acceptance — standalone service suite green.

## Stage 7 — Frontend

- [x] **T8** htmx end-to-end — real headless-Chrome tests (`test_browser.rs`,
      chromiumoxide): load + click swaps asserted on `htmx:afterSwap`,
      dual-mode consistency, push-URL. Feature-gated + CI job.
- [x] **T9** Stage 7 acceptance — browser parity automated.

## Stage 8 — Deploy & cutover (prepared; operator executes)

- [x] **T10** CI swap — `deploy.yaml` now triggers on the Rust workflow (must
      ship together with the cutover commit).
- [x] **T11** `deploy.sh` rewritten for Rust (docker build path — no cargo on
      server; installs `gunlinux-ru`, swaps off legacy unit).
- [x] **T12** systemd unit — `deploy/gunlinux-ru.service` (EnvironmentFile,
      hardening, distinct name for rollback).
- [ ] **T13** DB cutover (backup → baseline stamp → smoke) — 📋 runbook in
      `deploy/CUTOVER.md`; **not executed**.
- [ ] **T14** Rollback rehearsal — 📋 documented (git revert, legacy unit,
      pg_restore); **not rehearsed**.
- [ ] **T15** Stage 8 acceptance — **pending operator execution** of the
      runbook (preflight facts recorded in `deploy/CUTOVER.md`).

## Stage 9 — Parity, cleanup & docs

- [x] **T16** Parity run — `scripts/parity/` harness + `results.md`; 404 JSON
      body and `/md/` fenced-code output fixed to match Python byte-for-byte.
- [x] **T17** Python removed — `app/` (except `app/static/` — webpack +
      uploads), `migrations/`, `pyproject.toml`, `uv.lock`, `main.py`,
      `entrypoint.sh`, `Dockerfile`, `tests/`, Python Makefile targets, CI.
- [x] **T18** `README.md` + `CLAUDE.md` rewritten for the Rust app.
- [x] **T19** Stage 9 acceptance — Python gone, docs accurate, parity green.

## Cross-cutting

- [x] **T20** Thread A (platform-independent tests) — Postgres half done;
      service-tests half done; SQLite half was already done.
- [x] **T21** DoD sweep — plan.md §6 updated: 4/5 ✅, deploy/cutover 🟡
      (prepared, operator-executed).

---

## Notes

- Feature-gated suites keep the default `cargo test` compile graph unchanged
  (test-only deps are optional **regular** dependencies — cargo rejects
  `optional = true` in `[dev-dependencies]`).
- `scripts/parity/` is archived (requires the removed Python app); its
  `results.md` is the golden reference.
- Operator cutover entry point: `deploy/CUTOVER.md` (backup → build/install →
  baseline stamp → smoke → rollback; one nginx `/static/` repoint).
