#!/usr/bin/env bash
# Persistence code must be append-only: no UPDATE/DELETE statements outside migrations.
set -euo pipefail
ROOT="src/paybridge/infrastructure"
[ -d "$ROOT" ] || { echo "ERROR: $ROOT not found; run from the repository root." >&2; exit 2; }
if grep -rnE --include='*.py' "(execute|executemany|executescript)\(.*\b(UPDATE|DELETE)\b" "$ROOT"; then
  echo "ERROR: immutable persistence paths must not issue UPDATE/DELETE." >&2
  exit 1
fi
