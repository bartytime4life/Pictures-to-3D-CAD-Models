#!/usr/bin/env bash
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
[[ -x .venv/bin/python && -d node_modules ]] || { echo 'Run ./scripts/setup.sh first.' >&2; exit 1; }
.venv/bin/python - <<'PY'
import socket
for port in (8000, 4173):
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', port))
        except OSError:
            raise SystemExit(f'Port {port} is already in use. Stop the existing service first.')
PY
PICAD_API_PID=''
PICAD_WEB_PID=''
cleanup() {
  [[ -z "$PICAD_WEB_PID" ]] || kill "$PICAD_WEB_PID" 2>/dev/null || true
  [[ -z "$PICAD_API_PID" ]] || kill "$PICAD_API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload &
PICAD_API_PID=$!
./node_modules/.bin/vite frontend --config frontend/vite.config.ts --host "${PICAD_DEV_HOST:-127.0.0.1}" --port 4173 --strictPort &
PICAD_WEB_PID=$!
wait -n "$PICAD_API_PID" "$PICAD_WEB_PID"
