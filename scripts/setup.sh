#!/usr/bin/env bash
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
command -v python3 >/dev/null || { echo 'Install Python 3.12 before running setup.' >&2; exit 1; }
command -v npm >/dev/null || { echo 'Install Node.js 24 LTS before running setup.' >&2; exit 1; }
node -e 'const [major,minor]=process.versions.node.split(".").map(Number); if(major<22||(major===22&&minor<12)){console.error("Node.js 22.12+ is required; Node 24 is recommended.");process.exit(1)}'
python3 -c 'import sys; assert sys.version_info[:2] == (3,12), "Python 3.12 is required for the tested CAD binary dependencies."'
export UV_CACHE_DIR="$PICAD_ROOT/.cache/uv"
export UV_SYSTEM_CERTS=true
export npm_config_cache="$PICAD_ROOT/.cache/npm"
if command -v uv >/dev/null; then
  PICAD_UV="$(command -v uv)"
else
  python3 -m venv .local/uv-bootstrap
  .local/uv-bootstrap/bin/python -m pip install --disable-pip-version-check 'uv==0.13.5'
  PICAD_UV="$PICAD_ROOT/.local/uv-bootstrap/bin/uv"
fi
"$PICAD_UV" sync --frozen --python "$(command -v python3)"
npm ci --no-fund --no-audit
npm run build
echo 'Setup complete. Run ./scripts/start.sh, or ./scripts/dev.sh for development.'
