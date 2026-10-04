#!/usr/bin/env bash
set -euo pipefail
if rg -n --glob '*.py' "float\(|: *float\b|-> *float\b|\bfloat\(" src/paybridge; then
  echo "ERROR: floating-point arithmetic is forbidden in payment production code." >&2
  exit 1
fi
rg -n --glob '*.py' "Decimal" src/paybridge/domain >/dev/null
