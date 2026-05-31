# Flask → FastAPI Migration Review (REVIEW_01)

Branch: `refastapi` · Date: 2026-05-31

Suite status at review time: **32 tests pass**, `make lint` clean (ruff + basedpyright, 0 errors).
The green suite hides several real migration problems documented below.

---

## 🔴 Critical — production won't start

**`entrypoint.sh` calls a file that no longer exists.**

```sh
exec uv run gunicorn -c gunicorn.py   # file was renamed to uvicorn.py
```

`gunicorn.py` → `uvicorn.py` was renamed in this branch (`git diff master..refastapi`
shows `gunicorn.py => uvicorn.py`), but the Docker `ENTRYPOINT` still references the old
name. The container crashes on boot. CLAUDE.md already flags this, but it's still unfixed.
Tests never exercise the entrypoint, so the suite stays green.

**Fix:** point `entrypoint.sh` at `uvicorn.py`.

---

## 🔴 Significant — the `/auth` login flow is broken & dead

There are **two disconnected auth systems**, and the custom one does not work.

- `app/api/auth.py` `/auth/login` validates the user, sets an `access_token` **cookie**,
  then redirects to `/admin`.
- `/admin` is guarded by sqladmin's `AdminAuth.authenticate` (`app/admin/__init__.py:39`),
  which reads `request.session.get(COOKIE_NAME)` — the **server-side session**, not the cookie.

So a successful `/auth/login` sets a cookie nothing reads and bounces the user straight
back to `/admin/login`. The working admin login is sqladmin's own `/admin/login`; the
`/auth/*` router is a half-migrated Flask login that connects to nothing.

Corroborating: `get_current_user` / `CurrentUser` (`app/auth/dependencies.py`) — the
cookie-based dependency — is **referenced by zero routes** (grep confirms). It is entirely
dead code.

The auth tests only cover *invalid* login and logout, never the success → admin path —
exactly the broken part — so the suite stays green.

**Fix:** either wire `/auth/login` into the admin session, or remove the dead `/auth`
router + `get_current_user`/`CurrentUser` code.

---

## 🟠 Security — hardcoded admin session secret

`app/admin/__init__.py:107`:

```python
authentication_backend = AdminAuth(secret_key="admin-secret-fallback")
```

sqladmin uses this to sign admin session cookies. It's a hardcoded constant (and ignores
`settings.secret_key`), so anyone who knows it can forge an admin session.

**Fix:** use `get_settings().secret_key`.

---

## 🟡 Minor

- **Catch-all routing:** `GET /{alias}` lives in `posts_router`, which is `include_router`'d
  first. A request to `/tags` (no trailing slash) is swallowed as `alias="tags"` instead of
  redirecting to `/tags/`, and every unknown single-segment path triggers a DB lookup before
  404ing. Low risk since the other routers are prefixed, but worth ordering the catch-all last.
- **`get_db` commits on every request** including read-only GETs (`yield` → `commit()`).
  Harmless but unnecessary write traffic.

---

## Priority

The two that actually break behavior are **#1 (entrypoint)** and **#2 (auth)**.
**#3 (admin secret)** is a one-line security fix.
