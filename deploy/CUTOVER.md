# Production cutover — gunlinux.ru Python → Rust

Runbook for plan.md Stage 8 (tasks T10–T15). The **operator** executes the
cutover themselves; this document is the ordered, copy-pasteable procedure.
Nothing here runs automatically except the deploy script at Phase 2 — and that
one you run on purpose.

> All server facts below were verified read-only on 2026-08-23 (SSH inspection,
> no mutations). Anything you must fill in at cutover time is written as
> `<PLACEHOLDER>`.

---

## 0. What ships in the cutover commit

One commit on `master` containing **all** of:

| File | Role |
|---|---|
| `.github/deploy.sh` | Rewritten: builds the Rust binary (docker), installs the unit, swaps services |
| `.github/workflows/deploy.yaml` | Trigger swap: deploy fires on **"Rust"** workflow success, not "Python Code quality" |
| `deploy/gunlinux-ru.service` | systemd unit for the Rust binary (distinct name → legacy unit stays for rollback) |
| `deploy/CUTOVER.md` | This runbook |
| `rust/` (workspace) + the existing rust CI | Already on master; the baseline migration stamps on first start |

**Critical coupling:** `.github/deploy.sh` and the `deploy.yaml` trigger swap
MUST land in the same commit. Until that commit is on `origin/master`, any
master push would run the new deploy.sh against the still-Python server.
`deploy.sh` guards against this (it refuses to run if `rust/` or
`deploy/gunlinux-ru.service` are missing from the checkout), but do not rely
on the guard alone.

---

## 1. Key facts (verified 2026-08-23)

- **SSH:** `ssh gunlinux` (HostName gunlinux.ru, User loki, Port 187).
- **Repo on server:** `/home/loki/www/gunlinux.ru` — git remote
  `git@github.com:gunlinux/gunlinux.org.git`. Currently at `a808b26`
  (pre-FastAPI Flask era — the FastAPI rewrite was never deployed; prod runs
  the original Flask app). **`origin/master` still points at `a808b26`** until
  you push the cutover commit.
- **Legacy unit `gunlinux.ru`** (Python/gunicorn): User/Group `loki`,
  WorkingDirectory = repo, ExecStart `uv run gunicorn -c gunicorn.py`
  (binds `0.0.0.0:5000`), inline env, `Restart=always`, **no hardening**.
  Its unit file will be left installed for rollback.
- **New unit `gunlinux-ru`:** binary `/usr/local/bin/gunlinux-ru`,
  `BIND_ADDR=127.0.0.1:5000` (nginx expects the app on 5000 — no proxy change
  needed), `EnvironmentFile=/home/loki/www/gunlinux.ru/.env`.
- **Env file:** `/home/loki/www/gunlinux.ru/.env` (164 B, **untracked +
  gitignored → survives `git reset --hard`**). Keys today:
  `PAGE_CATEGORY`, `SQLALCHEMY_DATABASE_URI`, `SECRET_KEY`. The Rust binary
  reads **`DATABASE_URL`** (not the Flask name) — `deploy.sh` adds it
  automatically (same DSN value, secret never leaves the host).
  `PAGE_CATEGORY` is legacy and ignored by the Rust app.
- **Postgres:** docker container **`db`** (`postgres:18.4`),
  `127.0.0.1:5433 -> 5432`, database and user both **`gunlinux`**.
  `docker exec db pg_dump -U gunlinux -d gunlinux -Fc` works **without a
  password** (trust auth on the unix socket) — verified, dump ≈ 27 KB.
- **Build path:** **no cargo on the server**, **docker 29.4.2 present** and
  usable without sudo (loki is in the `docker` group). Binary is built with
  `docker build -f rust/Dockerfile` and extracted from the runtime stage at
  `/app/server`.
- **nginx vhost:** `/etc/nginx/sites-available/gunlinux.ru` (linked from
  sites-enabled). `/` → `127.0.0.1:5000`; `/admin/` → `127.0.0.1:5000` with an
  **IP allowlist** (72.56.74.60/32, 88.201.246.167/32); `/static/` and
  `/static/upload/` are served **from disk** by nginx (root
  `/home/loki/www/gunlinux.ru/blog`). Other vhosts on this host (twitch, bs,
  photo, ts, pay, gate, sl, asd27.ru, wg, default) are untouched.
- **Static:** the live site and the Rust templates both use
  `/static/dist/css/bundle.css`. After cutover the tracked `blog/` tree
  disappears, so the `/static/` nginx root must be repointed to `app/` —
  see Phase 4 (the one nginx edit of the whole cutover).
- **Legacy uploads:** `/home/loki/www/gunlinux.ru/blog/static/upload` (28 MB,
  untracked **and** ignored → survives git reset) keeps being served by
  nginx's `/static/upload/` + `@static_fallback` locations. No action needed.
- **Backups dir:** `/home/loki/backups` **does not exist yet** — Phase 1
  creates it.
- **Passwordless sudo** for loki is available (used by deploy.sh and the
  legacy workflow).

---

## 2. Phase 0 — Preflight

```bash
# From your laptop, in the repo root:

# 0.1 Local tree is the cutover state; note anything unexpected.
git status --short

# 0.2 Confirm what origin/master currently is (must still be a808b26 or
#     whatever was there before the cutover push — sanity check).
git ls-remote origin master

# 0.3 Server reachable, docker + postgres container up.
ssh gunlinux 'echo ok; docker ps --format "{{.Names}} {{.Image}} {{.Status}}" | grep -E "db"'

# 0.4 Backups dir + disk space (creates the dir — first mutation of the cutover).
ssh gunlinux 'mkdir -p /home/loki/backups && df -h /home/loki/backups'

# 0.5 Read the DSN with the password MASKED (confirms DATABASE_URL source
#     and the real db name/port without leaking the secret).
ssh gunlinux 'grep "^SQLALCHEMY_DATABASE_URI=" /home/loki/www/gunlinux.ru/.env | sed -E "s#(://[^:]+:)[^@]+@#\1***@#"' 
#     -> expect: postgresql://gunlinux:***@127.0.0.1:5433/gunlinux

# 0.6 Snapshot current public output for later parity/drift checks.
#     (rss/sitemap should come out IDENTICAL after cutover; / and /posts may
#     differ slightly — comrak vs python-markdown, see §9.)
mkdir -p /tmp/precutover
for p in / /posts /rss.xml /sitemap.xml /robots.txt; do
  curl -s "https://gunlinux.ru$p" | sha256sum | sed "s#-#$p#" >> /tmp/precutover/sha256.txt
done
cat /tmp/precutover/sha256.txt
```

**Operator judgement:** the server repo has uncommitted local modifications
(`blog/config.py`, `blog/templates/layout.html`, `blog/templates/post.html`,
`package-lock.json`). `deploy.sh`'s `git reset --hard` discards them — this is
pre-existing deploy behavior, and the Python tree is being replaced at
cutover, so it is expected. Confirm you don't need anything from those files
(e.g. a prod config not present in git). The **database is untouched** by git
operations.

---

## 3. Phase 1 — Backup (database)

```bash
# On the server. Writes a timestamped custom-format dump; no password needed.
ssh gunlinux '
  mkdir -p /home/loki/backups
  DUMP=/home/loki/backups/gunlinux_pre_rust_cutover_$(date +%Y%m%d_%H%M%S).dump
  docker exec db pg_dump -U gunlinux -d gunlinux -Fc > "$DUMP"
  echo "wrote: $DUMP"
  ls -lh /home/loki/backups/
'
# Note the exact dump filename — you need it for rollback (§8). Example:
#   gunlinux_pre_rust_cutover_20260823_201500.dump

# Verify the dump is a valid archive (list some of its contents).
ssh gunlinux 'docker exec -i db pg_restore --list < /home/loki/backups/gunlinux_pre_rust_cutover_<TS>.dump | head -25'
#     -> expect a table list: public.categories, public.icons, public.posts,
#        public.posts_tags, public.tags, public.users, (+ indexes, FKs)
```

DB name is `gunlinux` on port 5433 (from the server, §1). If for any reason
the trust auth fails, fall back to password auth:

```bash
ssh gunlinux '
  PGPASSWORD=$(grep "^SQLALCHEMY_DATABASE_URI=" .env | sed -E "s#.*://[^:]+:([^@]+)@.*#\1#")
  docker exec -e PGPASSWORD="$PGPASSWORD" db pg_dump -h 127.0.0.1 -U gunlinux -d gunlinux -Fc \
    > /home/loki/backups/gunlinux_pre_rust_cutover_$(date +%Y%m%d_%H%M%S).dump
'
```

---

## 4. Phase 2 — Push the cutover commit, then deploy

### 4a. Push (from your laptop, repo root)

```bash
git add .github/deploy.sh .github/workflows/deploy.yaml deploy/
git commit -m "cutover: ship Rust deploy (systemd unit, deploy.sh, workflow trigger swap)"
git push origin master
```

**What happens next — choose one path, not both:**

- **Path A — let CI deploy (recommended).** Pushing triggers the "Rust"
  workflow; when it passes on master, `deploy.yaml` fires and runs
  `deploy.sh` on the server automatically. Watch it in the GitHub Actions tab
  (workflow "Deploy to Server").
- **Path B — deploy manually (CI unavailable):**
  ```bash
  ssh gunlinux 'cd /home/loki/www/gunlinux.ru && git fetch --all && git reset --hard origin/master && bash .github/deploy.sh'
  ```

`deploy.sh` (idempotent) performs, in order: `git fetch`+`reset --hard
origin/master` (guarded: aborts if the cutover artifacts are absent) →
`make css-build` (webpack; npm install may take minutes and can touch
package-lock.json — pre-existing behavior) → `docker build -f rust/Dockerfile`
→ extract `/app/server` from the runtime image and install to
`/usr/local/bin/gunlinux-ru` → append `DATABASE_URL=…` to `.env` if missing →
install `deploy/gunlinux-ru.service` → `daemon-reload` →
`systemctl disable --now gunlinux.ru` (legacy, file kept) →
`systemctl enable --now gunlinux-ru`.

### 4b. Verify the swap

```bash
ssh gunlinux 'systemctl status gunlinux-ru --no-pager -l | head -15'
ssh gunlinux 'systemctl status gunlinux.ru --no-pager | head -5'
#     -> gunlinux-ru: active (running); gunlinux.ru: inactive (dead), disabled
ssh gunlinux 'sudo systemctl list-unit-files gunlinux.ru gunlinux-ru'
#     -> both unit FILES present (gunlinux.ru kept for rollback); only
#        gunlinux-ru is enabled
```

---

## 5. Phase 3 — Migration baseline stamping (automatic; verify)

The Rust binary runs the migrator **on startup**:
`rust/crates/server/src/main.rs` calls `Migrator::up(&db, None)` and logs
`migrations applied`. There is **no separate stamp step** — the first start
after backup stamps the baseline.

What that first start does (read before relying on it —
`rust/crates/persistence/src/migrator/m20260101_000001_create_schema.rs`):

- The 16 Alembic revisions of the Python era are collapsed into **one**
  baseline migration.
- The baseline creates the 6 tables (`users`, `categories`, `posts`, `tags`,
  `posts_tags`, `icons`) **all with `IF NOT EXISTS`**, with columns/FKs
  matching `app/infrastructure/database.py` (nullable `users.authenticated`
  integer, nullable `categories.page` boolean, `TIMESTAMPTZ` datetimes,
  composite `posts_tags` PK, FKs with NO ACTION).
- On the existing prod DB every `CREATE TABLE IF NOT EXISTS` is a **no-op** —
  **no DROP, no ALTER, no data changes, no destructive effects**. SeaORM then
  records the applied version in its own `seaql_migrations` table (a new,
  harmless table; the Python-era `alembic_version` table is left untouched).

Verify:

```bash
ssh gunlinux 'journalctl -u gunlinux-ru | grep "migrations applied"'   # expect the log line
ssh gunlinux 'docker exec db psql -U gunlinux -d gunlinux -c "SELECT version FROM seaql_migrations;"'
#     -> expect exactly: m20260101_000001_create_schema
```

**If the unit crash-loops instead** (`Restart=on-failure` retries forever):
stop it while diagnosing —

```bash
ssh gunlinux 'sudo systemctl stop gunlinux-ru && journalctl -u gunlinux-ru -n 100 --no-pager'
```

Most likely causes, in order: `DATABASE_URL` missing or wrong in `.env`
(deploy.sh prints a warning in that case), `.env` unreadable, or a schema
divergence surfacing during the baseline (see §10 risk notes; the admin
write/read smoke test in §7 is the end-to-end check).

---

## 6. Phase 4 — nginx: repoint `/static/` to `app/` (operator step)

Today nginx serves `/static/` from disk at `root /home/loki/www/gunlinux.ru/blog`
(the Flask-era layout). After `git reset --hard origin/master` the tracked
`blog/` tree (including `blog/static/dist`) is gone, so `/static/dist/css/bundle.css`
would 404. The Rust app serves the same URL from `app/static`, but nginx
intercepts `/static/` first — so repoint the root.

```bash
# Back up the live config (needed for rollback, §8).
ssh gunlinux 'sudo cp /etc/nginx/sites-available/gunlinux.ru /home/loki/backups/nginx.gunlinux.ru.bak.$(date +%Y%m%d_%H%M%S)'

# Only the `location ^~ /static/ {` block changes root blog -> app.
# `/static/upload/` and `@static_fallback` intentionally stay on blog/static/upload.
ssh gunlinux 'sudo sed -i "/location \^~ \/static\/ {/,/}/ s#root /home/loki/www/gunlinux.ru/blog;#root /home/loki/www/gunlinux.ru/app;#" /etc/nginx/sites-available/gunlinux.ru'

# Validate + reload (only this site's config is affected).
ssh gunlinux 'sudo nginx -t && sudo systemctl reload nginx'

# Verify the diff is exactly ONE root line:
ssh gunlinux 'diff <(cat /home/loki/backups/nginx.gunlinux.ru.bak.* | tail -n +1) /etc/nginx/sites-available/gunlinux.ru'
#     -> expect a single-line change: blog -> app inside the /static/ block
```

**Operator judgement:** this edit touches a shared multi-vhost nginx. If you
are not comfortable with the sed, edit the file by hand in
`/etc/nginx/sites-available/gunlinux.ru` — the only change is the `root` line
inside the `location ^~ /static/ {` block.

---

## 7. Phase 5 — Smoke test

Run these **inside an SSH session on the server** (`ssh gunlinux`), so the
localhost checks bypass the nginx IP allowlist on `/admin/`.

### 7.1 Route sweep (localhost, direct)

```bash
B=http://127.0.0.1:5000
for p in / /posts /hx/pages /hx/icons /robots.txt /sitemap.xml /rss.xml /tags /tags/; do
  printf '%-12s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' "$B$p")"
done
# expect: every line ends in 200
```

### 7.2 POST /md/ (markdown helper — public, no auth, no CSRF by design)

```bash
curl -s -X POST -d 'data=**hello**' http://127.0.0.1:5000/md/
# expect: 200 + JSON, e.g. {"data":"<p><strong>hello</strong></p>"}
```

### 7.3 Alias routes (real + nonexistent)

```bash
# pick a real post alias from the index page
curl -s http://127.0.0.1:5000/ | grep -oE 'href="/[a-z0-9-]{3,}"' | sort -u | head -8
curl -s -o /dev/null -w 'post: %{http_code}\n' http://127.0.0.1:5000/<POST_ALIAS>
# pick a real tag alias from the /tags page
curl -s http://127.0.0.1:5000/tags | grep -oE 'href="/tags/[a-z0-9-]+"' | sort -u | head -8
curl -s -o /dev/null -w 'tag: %{http_code}\n' http://127.0.0.1:5000/tags/<TAG_ALIAS>
# negatives
curl -s -o /dev/null -w '404 post: %{http_code}\n' http://127.0.0.1:5000/this-alias-does-not-exist-xyz
curl -s -o /dev/null -w '404 tag: %{http_code}\n' http://127.0.0.1:5000/tags/this-alias-does-not-exist-xyz
# expect: 200 / 200 / 404 / 404
```

### 7.4 Admin + DB write/read sanity (bcrypt login → write → read → delete)

```bash
B=http://127.0.0.1:5000
CJ=/tmp/cutover-cookies.txt; rm -f "$CJ"
curl -s -o /dev/null -w 'admin unauthed: %{http_code}\n' "$B/admin"        # 302 -> /admin/login
curl -s -o /dev/null -w 'login page:    %{http_code}\n' "$B/admin/login"   # 200
# login with a REAL existing user (bcrypt hash from the prod DB must verify)
curl -s -c "$CJ" -o /dev/null -w 'login POST:    %{http_code}\n' \
  -d 'username=<ADMIN_USERNAME>&password=<ADMIN_PASSWORD>' "$B/admin/login" # 302 + Set-Cookie: session
curl -s -b "$CJ" -o /dev/null -w 'admin authed:  %{http_code}\n' "$B/admin" # 200

# write: create a throwaway post through the admin CRUD
TS=$(date +%s)
curl -s -b "$CJ" -o /dev/null -w 'create: %{http_code}\n' \
  -d "pagetitle=CUTOVER TEST $TS&alias=cutover-test-$TS&content=# cutover sanity" \
  "$B/admin/post/create"                                                    # 302 -> /admin/post/
# read: the post is in Postgres and rendered by the app
curl -s -o /dev/null -w 'read:  %{http_code}\n' "$B/cutover-test-$TS"       # 200
# find its id straight from Postgres (docker exec runs directly on the server)
ID=$(docker exec db psql -U gunlinux -d gunlinux -tAc "SELECT id FROM posts WHERE alias='cutover-test-$TS';" | tr -d ' ')
echo "test post id=$ID"
# delete it and confirm it is gone
curl -s -b "$CJ" -o /dev/null -w 'delete: %{http_code}\n' -X POST "$B/admin/post/$ID/delete"  # 302
curl -s -o /dev/null -w 'gone:   %{http_code}\n' "$B/cutover-test-$TS"     # 404
```

If login fails, the first thing to check is `SECRET_KEY`/`.env` parsing
(`journalctl -u gunlinux-ru`) — the smoke test is the end-to-end guard for
systemd `EnvironmentFile` vs dotenv value parsing (§10).

### 7.5 Public checks through nginx

```bash
for p in / /posts /robots.txt /sitemap.xml /rss.xml /static/dist/css/bundle.css; do
  printf '%-32s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' "https://gunlinux.ru$p")"
done
# expect: all 200 (bundle.css proves the Phase 4 nginx change)
curl -s -o /dev/null -w '/admin (public): %{http_code}\n' https://gunlinux.ru/admin
# expect: 403 unless your source IP is on the nginx allowlist — 403 is the
#         allowlist working as intended
curl -s -o /dev/null -w 'legacy upload:  %{http_code}\n' https://gunlinux.ru/static/upload/song.mp3
# expect: 200 — legacy uploads still served from blog/static/upload
```

---

## 8. Phase 6 — Acceptance checklist (plan.md Stage 8 + §6)

- [ ] Cutover commit (deploy.sh + deploy.yaml trigger swap + deploy/) is on `origin/master`; `git ls-remote origin master` == the cutover SHA.
- [ ] `deploy.yaml` triggers on **"Rust"** only (viewed on GitHub: the "Deploy to Server" run followed the "Rust" workflow run).
- [ ] Backup dump exists in `/home/loki/backups/` and `pg_restore --list` shows the 6 tables; filename noted for rollback.
- [ ] `gunlinux-ru` unit installed, enabled, `active (running)`; legacy `gunlinux.ru` stopped + disabled but its unit file still present.
- [ ] `journalctl -u gunlinux-ru` shows `migrations applied`; `seaql_migrations` contains `m20260101_000001_create_schema`.
- [ ] Baseline migration confirmed non-destructive (all `CREATE TABLE IF NOT EXISTS`, no drops/alters/data changes) — §5.
- [ ] Smoke tests §7.1–§7.5 all green (routes 200/302/404 as marked, bundle.css 200 publicly, legacy upload 200).
- [ ] Admin login works with an existing account (bcrypt hash preserved) and the write→read→delete post round-trip passed (DB sanity).
- [ ] `rss.xml` / `sitemap.xml` byte-identical to the Phase 0 snapshot; `/` and `/posts` diffed for markdown drift (§9) and the drift judged acceptable.
- [ ] Rollback procedure (§9) is understood and the backup + nginx backup files are confirmed present.

---

## 9. Phase 7 — Rollback

Revert in this order (copy-pasteable). `<PRE_CUTOVER_SHA>` = `a808b26` (or
whatever `origin/master` was before the cutover push); `<TS>` = the dump
timestamp from Phase 1 / the nginx backup timestamp from Phase 4.

```bash
# 1. Bring the legacy Python app back up (its unit file is still installed).
ssh gunlinux 'sudo systemctl stop gunlinux-ru && sudo systemctl disable gunlinux-ru && sudo systemctl enable --now gunlinux.ru'

# 2. Revert the code on the server to the pre-cutover master.
ssh gunlinux 'cd /home/loki/www/gunlinux.ru && git fetch --all && git reset --hard <PRE_CUTOVER_SHA>'

# 3. Restore the pre-cutover nginx config (reverts the /static/ root change).
ssh gunlinux 'sudo cp /home/loki/backups/nginx.gunlinux.ru.bak.<TS> /etc/nginx/sites-available/gunlinux.ru && sudo nginx -t && sudo systemctl reload nginx'

# 4. Verify the Python app serves again.
curl -sI https://gunlinux.ru/ | head -1                                  # 200
curl -sI https://gunlinux.ru/static/dist/css/bundle.css | head -1        # 200 (nginx back on blog/)

# 5. Restore the DB from the dump ONLY if the smoke test wrote bad data or
#    the baseline touched something. The baseline is non-destructive and the
#    §7.4 test cleans up after itself, so a restore is normally NOT needed.
ssh gunlinux 'docker exec -i db pg_restore -U gunlinux -d gunlinux --clean --if-exists < /home/loki/backups/gunlinux_pre_rust_cutover_<TS>.dump'
```

Also on your laptop: to stop future master pushes from re-running the cutover
deploy, push a revert of the cutover commit (`git revert <CUTOVER_SHA>`), or
keep `origin/master` at the pre-cutover commit until the next deploy is
intentional.

**Risk notes (plan.md §5) that bear on rollback:**

1. **bcrypt hashes are preserved** — the Rust app uses the `bcrypt` crate, so
   existing user hashes verify without re-hashing (proven by the §7.4 login).
   Rollback to the Python app is equally unaffected: hashes are untouched.
2. **Markdown drift** — `comrak` renders slightly differently from
   python-markdown (raw-HTML pass-through, fenced_code). Golden-output parity
   is a Stage 9 deliverable; for cutover, diff `/` and `/posts` against the
   Phase 0 snapshot and judge the differences acceptable.
3. **SQLite↔Postgres divergence** — `page` bool, `DateTime(timezone=True)`,
   integer `authenticated`. The Postgres parity suite is not implemented
   (Stage 3 partial). The §7.4 admin round-trip exercises `posts` end-to-end;
   if you want extra assurance, run a column diff of each table against the
   baseline migration before starting the unit.
4. **Route ordering** — the catch-all `GET /{alias}` is registered last in
   `web/src/app.rs` (never shadows `/tags`, `/admin`, `/static`) — enforced
   by the ported route tests.
5. **Migrations** — 16 Alembic revisions collapsed into one baseline;
   stamping (not re-running schema creation) is exactly what the auto-migrate
   does on first start (§5). No destructive changes.
6. **Cache single-worker bug** — gone: axum is single-process, one moka cache.
7. **`POST /md/` has no CSRF** — preserved by design (no side effects).

---

## 10. Notes & operator judgement items

- **CI vs manual deploy (Phase 2):** do one or the other, not both. If both
  run, `deploy.sh` is idempotent — the second run just rebuilds and restarts
  (wasted build time, same end state).
- **`deploy.yaml` "test secrests" step** echoes `secrets.USERNAME` into CI
  logs — pre-existing, unrelated to this cutover, but worth cleaning up in a
  later commit.
- **`.env` parsing edge:** systemd `EnvironmentFile` parsing is not
  byte-identical to dotenv parsing (comments `#`, quoting). The values in the
  current `.env` (`SECRET_KEY`, the DSN) parse cleanly under both, and the
  §7.4 login is the end-to-end proof. If you ever add a value with `#`,
  spaces, or quotes to `.env`, re-check the unit (`systemctl cat gunlinux-ru`)
  — and note the binary also self-loads `.env` via dotenvy, so the 
  `EnvironmentFile` is belt-and-braces, not load-bearing.
- **First-start timing:** between `systemctl disable --now gunlinux.ru` and
  `enable --now gunlinux-ru` the site has no app on port 5000 — nginx returns
  502 for a few seconds. Expected.
- **`make css-build` runs `npm install`** — can take minutes and may rewrite
  `package-lock.json` if it is out of sync with `package.json` (pre-existing
  behavior; the server already had a locally-modified `package-lock.json`).
- **If anything here is stale at cutover time** (repo moved, unit changed),
  trust the live server, not this document — and update the runbook.
