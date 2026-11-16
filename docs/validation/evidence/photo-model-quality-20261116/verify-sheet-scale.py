"""Compare historical axis assignment with current code on one rendered plate.

Run from the repository root with its Python environment. Only the historical
homography function is replayed; all other current tracing code stays fixed.
Outputs are synthetic observations, not real-camera accuracy or uncertainty.
"""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from backend import sheet, tracing
from tests import synthetic

BASELINE = "9337800037f66bcef601c1e49171ac7144c960c4"
source = subprocess.check_output(
    ["git", "-C", str(ROOT), "show", f"{BASELINE}:backend/sheet.py"], text=True
)
node = next(node for node in ast.parse(source).body
            if isinstance(node, ast.FunctionDef) and node.name == "homography")
old_function_source = ast.get_source_segment(source, node)
namespace = dict(vars(sheet))
exec(compile(old_function_source, "historical-homography", "exec"), namespace)  # noqa: S102 - pinned local Git source
old_homography = namespace["homography"]
current_homography = sheet.homography
settings = {"tilt": (50.0, 10.0, 0.0), "k1": 0.0, "shadow": 0.0, "gradient": 0.0,
            "noise": 0.0, "dither": 0.0, "quality": None}
data, _ = synthetic.render(**settings)
results = {}
try:
    for name, function in (("before", old_homography), ("after", current_homography)):
        if name == "before":
            def historical(found, k1, size, sheet_mm, **_):
                return old_homography(found, k1, size, sheet_mm)
            sheet.homography = historical
        else:
            sheet.homography = function
        trace = tracing.trace_image(data, reference="a4", snap=False)
        profile = trace["profile"]
        points = np.asarray(profile["outer"]) * profile["reference"]["mm_per_px"]
        _, lengths, _ = cv2.minAreaRect(points.astype(np.float32))
        results[name] = {"outside_dimensions_mm": sorted(map(float, lengths), reverse=True),
                         "warnings": trace["warnings"]}
finally:
    sheet.homography = current_homography
assert max(abs(np.asarray(results["after"]["outside_dimensions_mm"]) - [120, 70])) < 0.15
assert results["before"]["outside_dimensions_mm"][0] > 160
assert any("physical direction was resolved" in note for note in results["after"]["warnings"])
inputs = [Path(__file__).resolve(), ROOT / "backend/sheet.py", ROOT / "backend/reference.py",
          ROOT / "backend/calibration_bounds.py", ROOT / "tests/synthetic.py"]
print(json.dumps({
    "kind": "executed-controlled-historical-axis-function-replay",
    "method": "Only homography is replaced; other tracing code is current for both runs",
    "historical_function_revision": BASELINE,
    "historical_function_sha256": hashlib.sha256(old_function_source.encode()).hexdigest(),
    "inputs": [{"path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in inputs],
    "image_sha256": hashlib.sha256(data).hexdigest(), "render_settings": settings,
    "ground_truth_outside_dimensions_mm": [120, 70], "results": results,
    "runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "opencv": cv2.__version__},
    "physical_accuracy_validated": False,
}, indent=2, allow_nan=False))
