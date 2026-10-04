#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
exec python -m uvicorn paybridge.main:app --host 127.0.0.1 --port "${PORT:-8000}"
