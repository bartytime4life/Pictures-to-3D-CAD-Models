#!/usr/bin/env bash
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
# Find Python 3.12 without assuming it is `python3`: PICAD_PYTHON if set, else the first
# of python3.12 and python3 that really is 3.12 (pyenv, distribution, and Homebrew layouts).
is_python312() { "$1" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' >/dev/null 2>&1; }
if [[ -n "${PICAD_PYTHON:-}" ]]; then
  PICAD_PY="$PICAD_PYTHON"
  is_python312 "$PICAD_PY" || { echo "PICAD_PYTHON=$PICAD_PY is not a working Python 3.12." >&2; exit 1; }
else
  PICAD_PY=''
  for candidate in python3.12 python3; do
    found="$(command -v "$candidate" || true)"
    if [[ -n "$found" ]] && is_python312 "$found"; then PICAD_PY="$found"; break; fi
  done
  [[ -n "$PICAD_PY" ]] || {
    echo 'Python 3.12 is required for the tested CAD binary dependencies, and neither python3.12 nor python3 is 3.12.' >&2
    echo 'Install Python 3.12, or set PICAD_PYTHON=/path/to/python3.12 and run setup again.' >&2
    exit 1
  }
fi
command -v npm >/dev/null || { echo 'Install Node.js 24 LTS before running setup.' >&2; exit 1; }
node -e 'const [major,minor]=process.versions.node.split(".").map(Number); if(major<22||(major===22&&minor<12)){console.error("Node.js 22.12+ is required; Node 24 is recommended.");process.exit(1)}'
echo "Using Python 3.12 at $PICAD_PY"
export UV_CACHE_DIR="$PICAD_ROOT/.cache/uv"
export UV_SYSTEM_CERTS=true
export npm_config_cache="$PICAD_ROOT/.cache/npm"
if command -v uv >/dev/null; then
  PICAD_UV="$(command -v uv)"
else
  "$PICAD_PY" -m venv .local/uv-bootstrap
  .local/uv-bootstrap/bin/python -m pip install --disable-pip-version-check 'uv==0.13.5'
  PICAD_UV="$PICAD_ROOT/.local/uv-bootstrap/bin/uv"
fi
"$PICAD_UV" sync --frozen --python "$PICAD_PY"
npm ci --no-fund --no-audit
npm run build
echo 'Setup complete. Run ./scripts/start.sh, or ./scripts/dev.sh for development.'
