#!/bin/bash
# =============================================================================
# gunlinux.ru — deploy the Rust container image from Docker Hub.
#
# Runs ON the server, invoked by .github/workflows/deploy.yaml over SSH with
# DEPLOY_TAG=<commit short SHA> exported. The image is built and pushed in CI
# (public repo gunlinuxloki/gunlinux.ru — no docker login needed here); this
# script pulls that exact tag, installs the systemd unit with the tag baked
# in, and restarts the service. Idempotent: safe to re-run.
#
# Replaces the pre-cutover script that built the binary on the server; the
# server no longer needs a Rust toolchain or a local docker build.
# =============================================================================
set -euo pipefail

REPO_DIR="/home/loki/www/gunlinux.ru"
BRANCH="master"
IMAGE="gunlinuxloki/gunlinux.ru"
OLD_UNIT="gunlinux.ru"   # legacy Python/gunicorn unit (file kept for rollback)
NEW_UNIT="gunlinux-ru"

cd "$REPO_DIR" || exit 1

# The server's git remote historically pointed at the wrong repo
# (gunlinux.org); enforce the real one so `git fetch` always pulls this repo.
git remote set-url origin git@github.com:gunlinux/gunlinux.ru.git

# --- 1. Pull the deployed commit ----------------------------------------------
git fetch --all
git reset --hard "origin/$BRANCH"

# Guard: refuse to run if the checkout lacks the deploy artifacts (protects
# against running this script against a pre-cutover master).
if [ ! -f rust/Cargo.toml ] || [ ! -f deploy/gunlinux-ru.service ]; then
    echo "ERROR: origin/$BRANCH lacks rust/ or deploy/gunlinux-ru.service — refusing to deploy." >&2
    exit 1
fi

# --- 2. Ensure .env exposes DATABASE_URL --------------------------------------
# The legacy .env carries the DSN under SQLALCHEMY_DATABASE_URI (Flask
# naming); the Rust binary reads DATABASE_URL. Same value, different key —
# the secret stays on the host, never in this repo. Docker's --env-file (in
# the unit) feeds both into the container; unknown keys are ignored by the
# Rust settings loader.
if ! grep -q '^DATABASE_URL=' .env; then
    DSN="$(grep '^SQLALCHEMY_DATABASE_URI=' .env | cut -d= -f2-)"
    if [ -n "$DSN" ]; then
        printf '\nDATABASE_URL=%s\n' "$DSN" >> .env
        echo "Added DATABASE_URL to .env (copied from SQLALCHEMY_DATABASE_URI)."
    else
        echo "WARNING: no SQLALCHEMY_DATABASE_URI in .env — set DATABASE_URL manually before starting gunlinux-ru." >&2
    fi
fi

# --- 3. Install the unit with the commit-hash tag baked in --------------------
TAG="${DEPLOY_TAG:?DEPLOY_TAG is required (commit short SHA)}"
sed -e "s|@IMAGE_TAG@|$TAG|g" deploy/gunlinux-ru.service \
    | sudo tee "/etc/systemd/system/$NEW_UNIT.service" >/dev/null
sudo systemctl daemon-reload

# --- 4. Swap services ---------------------------------------------------------
# Stop+disable the legacy Python app (`|| true`: idempotent — fine if it is
# already stopped/disabled on a re-run).
sudo systemctl disable --now "$OLD_UNIT" || true
sudo systemctl enable --now "$NEW_UNIT"

echo "Deployment completed: $IMAGE:$TAG"
echo "Next: run the smoke test and acceptance checks in deploy/CUTOVER.md"
