# Production deployment — gunlinux.ru (Rust container)

How the Rust (axum) app ships to production. The deploy is **automated**:
pushing to `master` runs the "Rust" quality gate; when it passes, the
"Deploy to Server" workflow builds the Docker image, pushes it to
**Docker Hub** tagged with the commit short SHA (plus `latest`), then runs
`.github/deploy.sh` on the server over SSH. This document is the runbook for
what happens around that automation and how to roll back.

> Server facts below were verified read-only on 2026-08-23 and re-verified on
> 2026-08-24: SSH `gunlinux` (HostName gunlinux.ru, User loki, **Port 187**),
> repo `/home/loki/www/gunlinux.ru`, Postgres container `db` on
> `127.0.0.1:5433` (**restart policy `unless-stopped`; if it is ever down,
> `docker start db`**), legacy Python unit `gunlinux.ru` (file kept for
> rollback). The server's git remote was pointing at the wrong repo
> (`gunlinux.org`) and is fixed by deploy.sh on every run.

---

## Topology after cutover

```
GitHub push to master
  └─ "Rust" workflow (fmt, clippy, tests, postgres-parity, browser-e2e)
      └─ on success: "Deploy to Server" workflow
          ├─ make css-build
          ├─ docker build (rust/Dockerfile, multi-stage) → push
          │    gunlinuxloki/gunlinux.ru:<sha7>  +  :latest   (public image)
          └─ ssh loki@gunlinux.ru:187 → bash .github/deploy.sh
               ├─ git fetch + reset --hard origin/master   (guard: rust/ + deploy/ present)
               ├─ append DATABASE_URL to .env if missing   (Flask-name → Rust-name)
               ├─ unquote .env values                      (docker --env-file keeps quotes)
               ├─ extract app/static/dist from the image   (server has no npm; nginx serves from disk)
               ├─ install deploy/gunlinux-ru.service with @IMAGE_TAG@ = <sha7>
               ├─ systemctl disable --now gunlinux.ru       (legacy, file kept)
               └─ systemctl enable --now gunlinux-ru        (docker run --network host)

nginx vhost gunlinux.ru
  ├─ /  and  /admin/  →  proxy_pass http://127.0.0.1:5000   (container, --network host)
  └─ /static/         →  served from disk: root .../app     (the ONE operator edit)
```

Key properties:

- **Image is public** — the server pulls without registry credentials.
- **Container runs with `--network host`** — `BIND_ADDR=127.0.0.1:5000`
  matches what nginx already expects, and `127.0.0.1:5433` reaches the
  Postgres container exactly as before. No proxy change.
- **Env stays on the host** — `.env` (`DATABASE_URL`, `SECRET_KEY`, ...) is
  fed into the container via docker `--env-file`; it is gitignored and
  survives `git reset --hard`.
- **The baseline migration is non-destructive** — `CREATE TABLE IF NOT EXISTS`
  only; on the existing prod DB it stamps `seaql_migrations` on first start
  and touches no data.

---

## Phase 0 — Preflight (before any deploy)

```bash
# Server reachable, docker + Postgres up.
ssh gunlinux 'echo ok; docker ps --format "{{.Names}} {{.Status}}" | grep "^db"'

# Backups dir.
ssh gunlinux 'mkdir -p /home/loki/backups && df -h /home/loki/backups'

# Secrets present on GitHub (repo settings → Secrets and variables → Actions):
#   DOCKERHUB_USERNAME  — Docker Hub account that owns the gunlinux namespace
#   DOCKERHUB_TOKEN     — Docker Hub access token (Account Settings → Security)
#   PRIVATE_KEY_SSH     — SSH key for loki@gunlinux.ru (already present)
```

## Phase 1 — Database backup (mandatory before any deploy)

```bash
ssh gunlinux '
  DUMP=/home/loki/backups/gunlinux_pre_deploy_$(date +%Y%m%d_%H%M%S).dump
  docker exec db pg_dump -U gunlinux -d gunlinux -Fc > "$DUMP"
  echo "wrote: $DUMP"; ls -lh /home/loki/backups/
'
# Note the exact filename — you need it for rollback.
```

## Phase 2 — Deploy

Push to master and let the pipeline run (or run `.github/deploy.sh` manually
with `DEPLOY_TAG=<sha7>` exported — idempotent, same end state):

```bash
git push origin master
# Watch in GitHub Actions: "Rust" → "Deploy to Server".
```

`deploy.sh` prints `Deployment completed: gunlinuxloki/gunlinux.ru:<sha7>`.

## Phase 3 — Verify the swap and the migration baseline

```bash
ssh gunlinux 'systemctl status gunlinux-ru --no-pager -l | head -12'
ssh gunlinux 'systemctl status gunlinux.ru --no-pager | head -4'
#     -> gunlinux-ru: active (running); gunlinux.ru: inactive (dead), disabled
ssh gunlinux 'journalctl -u gunlinux-ru | grep "migrations applied"'
ssh gunlinux 'docker exec db psql -U gunlinux -d gunlinux -tAc "SELECT version FROM seaql_migrations;"'
#     -> exactly: m20260101_000001_create_schema
```

**If the unit crash-loops** (`Restart=on-failure`): stop it and read the logs —

```bash
ssh gunlinux 'sudo systemctl stop gunlinux-ru && journalctl -u gunlinux-ru -n 50 --no-pager'
```

Likely causes: `DATABASE_URL` missing in `.env` (deploy.sh prints a warning),
`docker pull` failing (network), or a schema divergence during the baseline.

## Phase 4 — nginx: repoint `/static/` root to `app/` (one-time operator edit)

nginx serves `/static/` from disk. Before cutover it pointed at the Flask-era
`blog/` tree (which git removed); the Rust app ships the same bundle in
`app/static`, so the root inside the `location ^~ /static/ {` block changes:

```bash
ssh gunlinux 'sudo cp /etc/nginx/sites-available/gunlinux.ru /home/loki/backups/nginx.gunlinux.ru.bak.$(date +%Y%m%d_%H%M%S)'
ssh gunlinux 'sudo sed -i "/location \^~ \/static\/ {/,/}/ s#root /home/loki/www/gunlinux.ru/blog;#root /home/loki/www/gunlinux.ru/app;#" /etc/nginx/sites-available/gunlinux.ru'
ssh gunlinux 'sudo nginx -t && sudo systemctl reload nginx'
```

`/static/upload/` and `@static_fallback` intentionally stay on
`blog/static/upload` (legacy uploads, untracked + ignored → survive git ops).

## Phase 5 — Smoke test

Run inside an SSH session on the server (`ssh gunlinux`), so localhost checks
bypass the nginx IP allowlist on `/admin/`:

```bash
B=http://127.0.0.1:5000
# Route sweep — expect all 200
for p in / /posts /hx/icons /robots.txt /sitemap.xml /rss.xml /tags /tags/; do
  printf '%-12s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' "$B$p")"
done
# Markdown helper
curl -s -X POST -d 'data=**hello**' "$B/md/"   # {"data":"<p><strong>hello</strong></p>"}
# Real alias + negative
curl -s -o /dev/null -w 'post: %{http_code}\n' "$B/<REAL_POST_ALIAS>"          # 200
curl -s -o /dev/null -w '404:  %{http_code}\n' "$B/this-alias-does-not-exist"   # 404
# Admin login with a REAL account (bcrypt must verify) + write/read/delete round-trip:
curl -s -o /dev/null -w 'login: %{http_code}\n' -c /tmp/ck -d 'username=<U>&password=<P>' "$B/admin/login"   # 302
curl -s -o /dev/null -w 'admin: %{http_code}\n' -b /tmp/ck "$B/admin"                                        # 200
# Public checks through nginx (from your laptop)
for p in / /posts /robots.txt /sitemap.xml /rss.xml /static/dist/css/bundle.css; do
  printf '%-32s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' "https://gunlinux.ru$p")"
done
curl -s -o /dev/null -w 'legacy upload: %{http_code}\n' https://gunlinux.ru/static/upload/song.mp3   # 200
```

## Phase 6 — Rollback

```bash
# 1. Back to the previous image (unit pins <sha7>; restart with an older tag):
ssh gunlinux 'cd /home/loki/www/gunlinux.ru && git fetch --all && git reset --hard <PREV_SHA> && DEPLOY_TAG=<PREV_SHA7> bash .github/deploy.sh'

# 2. If the app itself is broken and you need the Python app back:
ssh gunlinux 'sudo systemctl stop gunlinux-ru && sudo systemctl disable gunlinux-ru && sudo systemctl enable --now gunlinux.ru'

# 3. Restore the pre-cutover nginx config (Phase 4 backup file).
ssh gunlinux 'sudo cp /home/loki/backups/nginx.gunlinux.ru.bak.<TS> /etc/nginx/sites-available/gunlinux.ru && sudo nginx -t && sudo systemctl reload nginx'

# 4. Restore the DB ONLY if a deploy wrote bad data (baseline is
#    non-destructive; the smoke test cleans up after itself).
ssh gunlinux 'docker exec -i db pg_restore -U gunlinux -d gunlinux --clean --if-exists < /home/loki/backups/gunlinux_pre_deploy_<TS>.dump'
```

## Known risks that bear on deploy

1. **bcrypt hashes are preserved** — the Rust app verifies existing user
   hashes; the §5 login is the end-to-end proof.
2. **Markdown drift** — the two renderers (comrak for post pages, the
   legacy preview renderer for `/md/`) differ slightly (raw-HTML
   pass-through, fenced code). The output contract is pinned by the test
   suites; judge any drift on `/` and `/posts` acceptable.
3. **Postgres-only** — SQLite support was removed; the persistence suite runs
   against scratch PostgreSQL 16 databases (testcontainers or
   `TEST_DATABASE_URL`), pinning the schema and repository behavior.
4. **Route ordering** — the catch-all `GET /{alias}` is registered last
   (never shadows `/tags`, `/admin`, `/static`); pinned by route tests.
5. **`.env` parsing** — docker `--env-file` parses `KEY=VALUE` lines with
   comments/quotes like dotenv; the current `.env` values parse cleanly. If
   you ever add a value with `#`, spaces, or quotes, re-check the unit.
6. **First-start timing** — between `systemctl disable --now gunlinux.ru` and
   `enable --now gunlinux-ru` nginx returns 502 for a few seconds. Expected.
