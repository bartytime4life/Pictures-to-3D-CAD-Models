#!/usr/bin/env bash
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo 'The app Python environment is missing. Run ./scripts/setup.sh first.' >&2
  echo 'Use ./scripts/doctor.sh to inspect setup without changing anything.' >&2
  exit 1
fi
if [[ ! -f frontend/dist/index.html ]]; then
  echo 'The app interface is not built. Run npm run build, or ./scripts/setup.sh for first-time setup.' >&2
  echo 'Use ./scripts/doctor.sh to inspect setup without changing anything.' >&2
  exit 1
fi
PICAD_START_HOST="${PICAD_HOST:-127.0.0.1}"
PICAD_START_PORT="${PICAD_PORT:-8000}"
if [[ "$PICAD_START_HOST" == 127.0.0.1 || "$PICAD_START_HOST" == localhost ]]; then
  echo "Open http://$PICAD_START_HOST:$PICAD_START_PORT after the server reports startup complete."
else
  echo "The app will listen on $PICAD_START_HOST:$PICAD_START_PORT. Use this host's supported browser or port forwarding."
fi
echo 'Keep this terminal open. Press Ctrl+C to stop the app.'
exec .venv/bin/python -m uvicorn backend.app:app --host "${PICAD_HOST:-127.0.0.1}" --port "${PICAD_PORT:-8000}"
