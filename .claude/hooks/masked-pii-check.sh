#!/usr/bin/env bash
# Raw account numbers, IFSC codes and names must never reach logs or stdout.
set -euo pipefail
ROOT="src/paybridge"
[ -d "$ROOT" ] || { echo "ERROR: $ROOT not found; run from the repository root." >&2; exit 2; }
PII='account_number|ifsc|payer_name|beneficiary_name'
if grep -rnE --include='*.py' "(logger\.[a-z]+|log_event|logging\.[a-z]+)\(.*($PII)" "$ROOT"; then
  echo "ERROR: unmasked PII candidate found in logging arguments." >&2
  exit 1
fi
if grep -rnE --include='*.py' "print\(.*($PII)" "$ROOT"; then
  echo "ERROR: unmasked PII candidate found in print output." >&2
  exit 1
fi
