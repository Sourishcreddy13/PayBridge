#!/usr/bin/env bash
set -euo pipefail
if rg -n --glob '*.py' 'logger\.\w*\([^\n]*(account_number|ifsc|payer_name)' src/paybridge; then
  echo "ERROR: unmasked PII candidate found in logger arguments." >&2
  exit 1
fi
if rg -n --glob '*.py' 'print\([^\n]*(account_number|ifsc|payer_name)' src/paybridge; then
  echo "ERROR: unmasked PII candidate found in print output." >&2
  exit 1
fi
