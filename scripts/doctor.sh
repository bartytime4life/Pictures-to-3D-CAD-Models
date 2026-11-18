#!/usr/bin/env bash
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
if [[ -x .venv/bin/python ]]; then
  PICAD_DOCTOR_PYTHON=.venv/bin/python
elif [[ -n "${PICAD_PYTHON:-}" ]]; then
  PICAD_DOCTOR_PYTHON="$PICAD_PYTHON"
else
  PICAD_DOCTOR_PYTHON="$(command -v python3.12 || command -v python3 || true)"
fi
if [[ -z "$PICAD_DOCTOR_PYTHON" ]] || ! "$PICAD_DOCTOR_PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
  echo 'The setup check needs Python 3.10+. Install Python 3.12, then run ./scripts/setup.sh.' >&2
  exit 1
fi
exec "$PICAD_DOCTOR_PYTHON" -B scripts/doctor.py "$@"
