#!/usr/bin/env bash
# Architecture guard — machine-checks the workspace crate matrix.
#
# The Dependency Rule (AGENTS.md, arch_review.md §4.5) requires:
#   - domain depends on nothing in-workspace (it is the inner core);
#   - application depends only on domain (the use-case layer);
#   - web depends only on domain + application — persistence/sea-orm must
#     never appear in web/Cargo.toml, in any dependency position (the build
#     system is what enforces the seam);
#   - server is the ONLY crate that joins persistence and web.
#
# Run locally: make check-arch · CI: the `arch` job in
# .github/workflows/rust-ci.yaml.

set -euo pipefail

cd "$(dirname "$0")/../rust/crates"

fail() { echo "architecture check FAILED: $*" >&2; exit 1; }

# 1. The web seam: no persistence/sea-orm in any dependency position
#    (dependencies, dev-dependencies, features).
if grep -nE '^[[:space:]]*(persistence|sea-orm)[[:space:]]*=' web/Cargo.toml; then
  fail "web/Cargo.toml must not depend on persistence or sea-orm"
fi

# 2. domain is the inner core: no in-workspace (path) dependencies.
if grep -nE '^[[:space:]]*path[[:space:]]*=' domain/Cargo.toml; then
  fail "domain/Cargo.toml must not depend on workspace crates (path = ...)"
fi

# 3. application is the use-case layer: depends only on domain (its only
#    allowed path dependency) and never on persistence/web.
if grep -nE '^[[:space:]]*(persistence|web|sea-orm)[[:space:]]*=' application/Cargo.toml; then
  fail "application/Cargo.toml must not depend on persistence/web/sea-orm"
fi

# 4. Only server may join persistence and web.
for crate in domain application persistence web server; do
  has_persistence=$(grep -cE '^[[:space:]]*persistence[[:space:]]*=' "$crate/Cargo.toml" || true)
  has_web=$(grep -cE '^[[:space:]]*web[[:space:]]*=' "$crate/Cargo.toml" || true)
  if [ "$crate" = server ]; then
    [ "$has_persistence" -ge 1 ] || fail "server must depend on persistence"
    [ "$has_web" -ge 1 ] || fail "server must depend on web"
  else
    [ "$has_persistence" -eq 0 ] || fail "$crate must not depend on persistence"
    [ "$has_web" -eq 0 ] || fail "$crate must not depend on web"
  fi
done

echo "architecture check OK"
