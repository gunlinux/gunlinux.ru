## Why

The app silently falls back to a **publicly-known default `SECRET_KEY`**
(`"hard-to-guess-string-change-in-production"`, `web/src/settings.rs:30`) on
any settings-loading error or missing env value. That key signs the admin JWT,
the session cookie HMAC, and the analytics IP-hash salt. If production ever
boots with it (missing/typo'd `.env` entry, or any unrelated config error
tripping the all-or-nothing deserialize fallback), anyone can forge an admin
session cookie and take over the panel — full CRUD over posts, users, content,
plus retroactive de-anonymization of stored IP hashes. Today the only signal is
a startup warning line, and `deploy.sh` never checks for `SECRET_KEY` at all.

## What Changes

- The `server` binary **refuses to start** when `SECRET_KEY` is unset or equals
  the known default — the failure is loud, immediate, and tells the operator
  exactly what to set, instead of booting with a forgeable key.
- The all-or-nothing settings fallback stays for non-secret fields, but the
  secret is validated separately so one bad env value can no longer silently
  reset it.
- `.github/deploy.sh` gains a guard: the deploy **fails** when the host `.env`
  lacks `SECRET_KEY` (mirroring the existing `DATABASE_URL` check).
- Local dev `.env` and the env docs (`rust/README.md`, AGENTS.md config
  section) are updated to require `SECRET_KEY`, so a fresh checkout fails fast
  instead of running with the default.
- **BREAKING (operational):** servers without a configured `SECRET_KEY` no
  longer boot — including local dev until the `.env` is updated.

## Capabilities

### New Capabilities

- `admin-auth`: hardening of admin authentication — the server must not start
  with an unset or default signing key, and the deployment pipeline must not
  ship one. Covers the fail-fast startup contract and the deploy guard.

### Modified Capabilities

<!-- None: this repo has no existing specs (openspec/specs is empty). -->

## Impact

- `rust/crates/web/src/settings.rs` — secret validation (default constant
  exposed for comparison; `load_settings` or a new check).
- `rust/crates/server/src/main.rs` — startup bail with a clear message.
- `.github/deploy.sh` — SECRET_KEY presence guard before the service swap.
- Repo `.env` (gitignored, local dev) and host `.env` (prod) — must set
  `SECRET_KEY`.
- Docs: `rust/README.md` / `AGENTS.md` config section note the requirement.
- Non-goals (documented, not part of this change): splitting the analytics
  salt into its own `ANALYTICS_SALT` env (rotation story); checking the JWT
  `sub` against the `users` table on admin requests (the forged-`sub` hole).
