#!/usr/bin/env bash
set -euo pipefail
if rg -n --glob '*.py' 'execute\([^\n]*(UPDATE|DELETE)' src/paybridge/infrastructure/repositories.py src/paybridge/infrastructure/rail_attempt_repository.py src/paybridge/infrastructure/read_models.py; then
  echo "ERROR: immutable persistence paths must not issue UPDATE/DELETE." >&2
  exit 1
fi
