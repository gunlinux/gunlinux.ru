## Context

See proposal.md — Why for the motivation. Current state that shapes the
approach:

- `web/src/settings.rs` merges env + `.env` into one `Settings` struct; any
  deserialize error falls back to `Settings::default()` (all-or-nothing) with
  a startup warning. `Settings::default().secret_key` is the public constant
  `"hard-to-guess-string-change-in-production"`.
- The same key signs the admin JWT, the session-cookie HMAC, and the analytics
  IP-hash salt (`auth.rs`, `analytics.rs`).
- `server/src/main.rs` is the only place with startup authority; `load_settings`
  is shared with tests, which construct `Settings::default()` directly and must
  stay unaffected.
- `.github/deploy.sh` guards `DATABASE_URL` (with a warning, not a hard fail)
  and normalizes quoted `KEY="value"` lines, but never checks `SECRET_KEY`.
- The local (gitignored) repo `.env` currently has no `SECRET_KEY` — dev runs
  with the default key today. `ENV` is dead config (loaded, never read), so
  gating behavior on it is unreliable.

## Goals / Non-Goals

**Goals:**
- The server process refuses to start when `SECRET_KEY` is unset or equals the
  known default (spec: `admin-auth`), covering the all-or-nothing fallback
  (any config error now yields the default → fail-fast).
- `deploy.sh` fails the deploy when the host `.env` lacks `SECRET_KEY`.
- `SECRET_KEY` becomes a documented requirement (dev `.env`, README, AGENTS.md).

**Non-Goals:**
- Splitting the analytics salt into a separate `ANALYTICS_SALT` (rotation story —
  noted in proposal.md, tracked separately).
- Checking the JWT `sub` against the `users` table (the forged-`sub` hole).
- CSRF/Secure-cookie work (S1–S3 in REV.md — separate changes).

## Decisions

**D1. Fail-fast lives in `server/src/main.rs`, not in `load_settings`.**
After `get_settings()`, bail via `anyhow::Context` when
`settings.secret_key == Settings::default().secret_key`, with a message naming
`SECRET_KEY` and the fix. Rationale: the server binary owns startup policy; the
web crate is shared with tests and has no authority to kill the process.
Alternative considered (panic inside `load_settings`) rejected for that reason.
This also means the spec's "unrelated settings error" scenario is covered for
free: the fallback produces the default secret, and the main.rs check then
fails startup.

**D2. Not gated on `ENV`.** `ENV` is dead config — gating on it would make the
guard depend on a second setting the operator must remember, recreating the
silent-failure mode. Fail-fast unconditionally; dev `.env` gets a real key
(one line). The known-default constant stays in `Settings::default()` so tests
keep working; the check compares against it.

**D3. Deploy guard is a hard fail, after quote normalization.** In
`deploy.sh`, after the existing `sed` quote-strip step, add
`grep -q '^SECRET_KEY=' .env || { echo ERROR...; exit 1; }`. Hard fail (not a
warning like the `DATABASE_URL` case) per spec — an insecure boot is worse than
a failed deploy. Positioned before the service swap, so a failure leaves the
running unit untouched.

**D4. Comparison via the default-constant, not "is non-empty".** Checking only
"non-empty" would still permit the known string (copy-paste from docs/tests).
Comparing against `Settings::default().secret_key` catches exactly the
dangerous cases while allowing any real random value.

## Risks / Trade-offs

- [Fresh dev checkout without `.env` now fails to boot] → Error message names
  the fix; README/AGENTS.md document the required line; the `.env` is one line.
- [The guard depends on the constant staying in sync with the default] → The
  comparison uses `Settings::default()` itself, so they cannot drift.
- [Prod host `.env` may lack `SECRET_KEY` today → next deploy fails] → That is
  the intended behavior; the operator adds the key, and the failing deploy
  leaves the old service running (rollback is a no-op).
- [Operator deliberately sets the default string as their key] → Startup fails
  with an explanatory message; no way to tell intent from a typo, failing is
  the safe side.

## Migration Plan

1. Land code: main.rs check + deploy.sh guard + docs.
2. Update local repo `.env` with a `SECRET_KEY` (dev) — required before the new
   binary boots locally.
3. Operator adds `SECRET_KEY` to the prod host `.env` before the next deploy.
4. Deploy: guard fails loudly until present; no change to the service swap
   path. Rollback of the guard = revert the commit; nothing in prod state
   changes from a failed deploy.
