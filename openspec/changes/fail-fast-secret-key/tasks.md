## 1. Server fail-fast

- [x] 1.1 Extract the default-secret check as a small testable helper in `server/src/main.rs` (or `web/src/settings.rs`) and add unit tests: unset secret, default-constant secret, and a custom secret — verify `cargo test -p server` (and `-p web` if placed there) passes
- [x] 1.2 Wire the check into startup: after `get_settings()`, bail with an `anyhow` error naming `SECRET_KEY` and the fix when the secret is unset or equals `Settings::default().secret_key` — verify `DATABASE_URL` set + no `SECRET_KEY` env exits non-zero with the message, and a custom `SECRET_KEY` boots and serves on the bound port

## 2. Deploy guard

- [x] 2.1 Add a hard-fail `SECRET_KEY` guard to `.github/deploy.sh` (after the quote-normalization `sed` step, before the service swap): missing `^SECRET_KEY=` line in the host `.env` → error + `exit 1` — verify with a scratch `.env` (with and without the line) that the guard passes/fails as intended and a failure leaves the service untouched

## 3. Docs and env

- [x] 3.1 Add a strong random `SECRET_KEY` to the local repo `.env` (gitignored, never committed) — verify the dev server boots with the key and `git status` shows `.env` still ignored
- [x] 3.2 Document `SECRET_KEY` as required in `rust/README.md` and the AGENTS.md configuration section (env list, no default in production) — verify the docs render the requirement in both files
- [ ] 3.3 Add `SECRET_KEY` to the production host `.env` (operator-executed on the server, not from this repo) — verify the next deploy's guard step passes

## 4. Verification

- [x] 4.1 Run `make check` (fmt + clippy + workspace tests) green with the changes
- [x] 4.2 End-to-end smoke: start the server without `SECRET_KEY` → exits with the error; with the local `.env` key → serves `/` and `/admin/login` — verify both behaviors
