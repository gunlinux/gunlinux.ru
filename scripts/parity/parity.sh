#!/usr/bin/env bash
# ============================================================================
# gunlinux.ru side-by-side parity harness (plan.md Task T16, first half).
#
# Starts the Python (FastAPI) app and the Rust (axum) app against TWO scratch
# SQLite databases seeded with identical data, then runs the route matrix from
# plan.md §1 against both and diffs status + normalized bodies.
#
#   * Python app: port 8100  (uv run uvicorn main:app)
#   * Rust app:   port 8101  (cargo-built rust/crates/server binary)
#   * Scratch DBs: scripts/parity/tmp/python.db and rust.db
#   * NO production/remote database is ever touched.
#
# Usage:  ./parity.sh            (from anywhere; paths are resolved internally)
# ============================================================================
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
RUST_DIR="$ROOT/rust"
TMP="$DIR/tmp"
OUT="$TMP/out"

PY_DB="$TMP/python.db"
RS_DB="$TMP/rust.db"
PY_PORT=8100
RS_PORT=8101
PY_URL="http://127.0.0.1:$PY_PORT"
RS_URL="http://127.0.0.1:$RS_PORT"

mkdir -p "$TMP" "$OUT"
# Fresh artifacts each run (stale files from earlier matrix shapes confuse).
rm -rf "$OUT"
mkdir -p "$OUT"

# --- refuse to run over a live server on our ports -------------------------
for p in "$PY_PORT" "$RS_PORT"; do
  if lsof -iTCP:$p -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    echo "ERROR: port $p is already in use (user dev servers are on 8000/8001; harness uses 8100/8101)." >&2
    exit 1
  fi
done

# --- scratch DBs -----------------------------------------------------------
rm -f "$PY_DB" "$RS_DB"

PY_PID=""
RS_PID=""
cleanup() {
  set +e
  if [ -n "$PY_PID" ]; then kill "$PY_PID" 2>/dev/null; fi
  if [ -n "$RS_PID" ]; then kill "$RS_PID" 2>/dev/null; fi
  wait "$PY_PID" 2>/dev/null
  wait "$RS_PID" 2>/dev/null
  set -e
}
trap cleanup EXIT

wait_for() {
  local url="$1" name="$2" tries="$3"
  local i=0
  while [ "$i" -lt "$tries" ]; do
    if curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null | grep -qE '^[0-9]+$'; then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  echo "ERROR: $name never became ready at $url (log: $TMP/$name.log)" >&2
  return 1
}

# --- 1. Python: schema via Alembic, then seed ------------------------------
echo "==> [1/5] creating + seeding Python DB ($PY_DB)"
cd "$ROOT"
DATABASE_URL="sqlite+aiosqlite:///$PY_DB" uv run alembic -c migrations/alembic.ini upgrade head >"$TMP/alembic.log" 2>&1
sqlite3 -cmd ".timeout 5000" "$PY_DB" < "$DIR/seed.sql"
echo "     python db seeded: $(sqlite3 "$PY_DB" 'SELECT count(*) FROM posts;') posts"

# --- 2. Start the Python app on 8100 ---------------------------------------
echo "==> [2/5] starting Python app on :$PY_PORT"
(
  cd "$ROOT"
  DATABASE_URL="sqlite+aiosqlite:///$PY_DB" uv run uvicorn main:app --host 127.0.0.1 --port "$PY_PORT" --log-level warning
) >"$TMP/python.log" 2>&1 &
PY_PID=$!
wait_for "$PY_URL/robots.txt" python 60 || exit 1

# --- 3. Rust: build, start (applies migrations on startup), seed -----------
echo "==> [3/5] building + starting Rust app on :$RS_PORT"
# sqlx only auto-creates a SQLite file for `?mode=rwc` URLs; the server's
# default relies on the file already existing (tmp/dev.db). Pre-create the
# scratch file so the unmodified server binary can open it.
: > "$RS_DB"
(
  cd "$RUST_DIR"
  if ! cargo build -p server --quiet 2>"$TMP/cargo-build.log"; then
    if [ -x target/debug/server ]; then
      echo "     warning: 'cargo build -p server' failed (see $TMP/cargo-build.log); using existing target/debug/server" >&2
    else
      echo "ERROR: cargo build failed and no existing target/debug/server binary" >&2
      cat "$TMP/cargo-build.log" >&2
      exit 1
    fi
  fi
)
(
  cd "$RUST_DIR"
  DATABASE_URL="sqlite:///$RS_DB" BIND_ADDR="127.0.0.1:$RS_PORT" STATIC_DIR="$ROOT/app/static" \
    RUST_LOG=warn ./target/debug/server
) >"$TMP/rust.log" 2>&1 &
RS_PID=$!
wait_for "$RS_URL/robots.txt" rust 120 || exit 1

echo "     seeding rust db: $RS_DB"
sqlite3 -cmd ".timeout 5000" "$RS_DB" < "$DIR/seed.sql"
echo "     rust db seeded:  $(sqlite3 "$RS_DB" 'SELECT count(*) FROM posts;') posts"

# --- 4. Run the route matrix and diff --------------------------------------
echo "==> [4/5] running route matrix ($PY_URL vs $RS_URL)"
python3 "$DIR/compare.py" "$PY_URL" "$RS_URL" "$OUT"

# --- 5. Cleanup -------------------------------------------------------------
echo "==> [5/5] stopping apps (DBs + artifacts kept under $TMP)"
kill "$PY_PID" 2>/dev/null || true
kill "$RS_PID" 2>/dev/null || true
wait "$PY_PID" 2>/dev/null || true
wait "$RS_PID" 2>/dev/null || true
PY_PID=""
RS_PID=""
echo "     done."
