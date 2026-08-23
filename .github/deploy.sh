#!/bin/bash
# =============================================================================
# gunlinux.ru — Rust (axum) production deploy
#
#   *** CUTOVER SCRIPT — only safe to run at cutover; must ship in the same
#       commit as the deploy.yaml trigger swap (workflow_run
#       "Python Code quality" -> "Rust"). ***
#
#   Before the cutover commit is on origin/master this script must NOT run:
#   it would deploy the Rust binary and unit onto the still-Python server and
#   break production. .github/deploy.sh now refuses to run if the checkout
#   lacks the cutover artifacts (rust/ and deploy/gunlinux-ru.service).
#
# Build path (server inspection, read-only): cargo is NOT installed on the
# server; docker IS (loki is in the `docker` group — no sudo needed for docker
# itself). So the release binary is built with
#   docker build -f rust/Dockerfile
# (multi-stage, BuildKit) and extracted from the runtime stage at /app/server.
# Templates are embedded at build time; the webpack CSS bundle (app/static)
# is copied into the image, so `make css-build` MUST run first.
#
# What this script does:
#   1. git fetch + reset --hard origin/master  (the cutover commit must be there)
#   2. make css-build                           (webpack CSS, still app/static)
#   3. docker build the Rust release binary, install to /usr/local/bin/gunlinux-ru
#   4. ensure .env exposes DATABASE_URL (the legacy file uses the Flask name
#      SQLALCHEMY_DATABASE_URI; the Rust binary reads DATABASE_URL)
#   5. install deploy/gunlinux-ru.service, daemon-reload
#   6. stop+disable the legacy Python unit `gunlinux.ru` (unit file KEPT for
#      rollback) and enable+start the new unit `gunlinux-ru`
#
# NOT done here (see deploy/CUTOVER.md): the nginx /static root change and the
# DB backup/baseline verification are operator steps around this script.
# =============================================================================
set -euo pipefail

REPO_DIR="/home/loki/www/gunlinux.ru"
BRANCH="master"
BINARY_DEST="/usr/local/bin/gunlinux-ru"
DOCKER_IMAGE="gunlinux-ru:cutover"
OLD_UNIT="gunlinux.ru"     # legacy Python/gunicorn unit (file kept for rollback)
NEW_UNIT="gunlinux-ru"     # new Rust unit

cd "$REPO_DIR" || exit 1

# --- 1. Pull the cutover commit ------------------------------------------------
git fetch --all
git reset --hard origin/$BRANCH

# Refuse to proceed if origin/master is not the cutover commit (no rust/ or
# deploy/ artifacts). This is the guard behind the CUTOVER SCRIPT warning.
if [ ! -f rust/Cargo.toml ] || [ ! -f deploy/gunlinux-ru.service ]; then
    echo "ERROR: origin/$BRANCH is not the cutover commit (rust/ or deploy/ missing). Aborting — do not run this script before cutover." >&2
    exit 1
fi

# --- 2. CSS bundle (webpack) ----------------------------------------------------
# The image COPYs app/static, so the bundle must exist before docker build.
make css-build

# --- 3. Build the Rust release binary via docker and install it -----------------
docker build -f rust/Dockerfile -t "$DOCKER_IMAGE" .

# Extract /app/server from the runtime stage image and install it on the host.
TMP_BIN="$(mktemp)"
cid="$(docker create "$DOCKER_IMAGE")"
docker cp "$cid:/app/server" "$TMP_BIN"
docker rm "$cid" >/dev/null
sudo install -m 0755 "$TMP_BIN" "$BINARY_DEST"
rm -f "$TMP_BIN"

# --- 4. Ensure the server-side .env exposes DATABASE_URL for the Rust binary ----
# The legacy .env carries the DSN under SQLALCHEMY_DATABASE_URI (Flask naming).
# The Rust binary reads DATABASE_URL (sqlx accepts both postgres:// and
# postgresql:// schemes). Same value, different key name — secret stays on the
# host, never in this repo.
if ! grep -q '^DATABASE_URL=' .env; then
    DSN="$(grep '^SQLALCHEMY_DATABASE_URI=' .env | cut -d= -f2-)"
    if [ -n "$DSN" ]; then
        printf '\nDATABASE_URL=%s\n' "$DSN" >> .env
        echo "Added DATABASE_URL to .env (copied from SQLALCHEMY_DATABASE_URI)."
    else
        echo "WARNING: no SQLALCHEMY_DATABASE_URI found in .env — set DATABASE_URL manually before starting gunlinux-ru." >&2
    fi
fi

# --- 5. Install the unit and swap services --------------------------------------
sudo install -m 0644 deploy/gunlinux-ru.service /etc/systemd/system/gunlinux-ru.service
sudo systemctl daemon-reload

# Stop+disable the legacy Python app. `|| true`: idempotent — fine if it is
# already stopped/disabled (or if a later re-run finds it missing).
sudo systemctl disable --now "$OLD_UNIT" || true
sudo systemctl enable --now "$NEW_UNIT"

echo "Deployment completed successfully."
echo "Next: run the smoke test and acceptance checks in deploy/CUTOVER.md"
