#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
.venv/bin/python -m pytest -q
npm run build
npm run test:e2e
