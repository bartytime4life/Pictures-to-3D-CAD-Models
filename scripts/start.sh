#!/usr/bin/env bash
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
if [[ ! -x .venv/bin/python || ! -f frontend/dist/index.html ]]; then
  echo 'Run ./scripts/setup.sh first to install dependencies and build the interface.' >&2
  exit 1
fi
exec .venv/bin/python -m uvicorn backend.app:app --host "${PICAD_HOST:-127.0.0.1}" --port "${PICAD_PORT:-8000}"
