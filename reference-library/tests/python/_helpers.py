"""Shared test setup: make the reference-library root importable and locate files."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXAMPLES = ROOT / "examples"
TEMPLATES = ROOT / "templates"
GOLDEN = EXAMPLES / "calculation-results.json"
from cadkit import scad as _scad  # noqa: E402

HAS_OPENSCAD = _scad.find_openscad() is not None
