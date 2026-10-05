#!/usr/bin/env bash
# Money must be fixed-point Decimal. Floats are rejected anywhere under src/paybridge unless the
# line is explicitly marked as non-monetary (e.g. a wall-clock sleep duration):
#     sleep(float(delay))  # non-monetary: wall-clock seconds
set -euo pipefail
ROOT="src/paybridge"
[ -d "$ROOT" ] || { echo "ERROR: $ROOT not found; run from the repository root." >&2; exit 2; }

violations="$(grep -rnE --include='*.py' 'float\(|:[[:space:]]*float\b|->[[:space:]]*float\b' "$ROOT" \
  | grep -v '# non-monetary:' || true)"
if [ -n "$violations" ]; then
  echo "$violations"
  echo "ERROR: floating-point values are forbidden in payment code (mark true non-money uses with '# non-monetary: <why>')." >&2
  exit 1
fi
grep -rq --include='*.py' 'Decimal' "$ROOT/domain" || { echo "ERROR: domain layer lost its Decimal money type." >&2; exit 1; }
