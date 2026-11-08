#!/usr/bin/env bash
set -euo pipefail
PICAD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PICAD_ROOT"
command -v python3 >/dev/null || { echo 'Install Python 3.10+ before setting up the reference library.' >&2; exit 1; }
command -v node >/dev/null || { echo 'Install Node.js 20+ before setting up the reference library.' >&2; exit 1; }
command -v npm >/dev/null || { echo 'Install npm before setting up the reference library.' >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 10), "The reference library requires Python 3.10+."'
node -e 'if(Number(process.versions.node.split(".")[0])<20){console.error("The reference library requires Node.js 20+.");process.exit(1)}'
export npm_config_cache="$PICAD_ROOT/.cache/npm"
export PIP_CACHE_DIR="$PICAD_ROOT/.cache/pip"
python3 -m venv reference-library/.venv
reference-library/.venv/bin/python -m pip install --disable-pip-version-check -r reference-library/requirements.txt
npm --prefix reference-library ci --no-fund --no-audit
echo 'Reference library setup complete. Run make test-library from the repository root.'
echo 'PDF rebuilds need DejaVu fonts; browser checks need Chromium; plate rendering needs OpenSCAD.'
