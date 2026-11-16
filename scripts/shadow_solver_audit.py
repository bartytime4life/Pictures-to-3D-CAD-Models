"""Replay paired shadow fits with the former deletion solve and the KKT repair.

Run from the repository root: .venv/bin/python -m scripts.shadow_solver_audit OUTPUT
The existing synthetic scene is shared to isolate the solver; this is development
regression evidence, not an independent camera or physical-accuracy benchmark.
"""

import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

from backend import shadow
from tests.test_fidelity_math import _shadowed_scene, _side_errors


def deleted_only(matrix, rhs, unbounded=0, **kwargs):
    free = np.ones(len(rhs), bool)
    for _ in range(60):
        x = np.zeros(len(rhs))
        indices = np.flatnonzero(free)
        x[indices] = shadow._spd_solve(matrix[np.ix_(indices, indices)], rhs[indices])
        negative = free & (np.arange(len(rhs)) >= unbounded) & (x < 0)
        if not negative.any():
            break
        free[negative] = False
    return x


def replay():
    current = shadow._nonnegative_solve
    rows = []
    for shift, width, depth, ppm, sigma in [
        ((1.6, 1.9), 2.2, 0.3, 4., 3.), ((0, 0), 2.2, 0.3, 4., 3.),
        ((3, -2), 4, 0.4, 4., 3.), ((0, 0), 0.8, 0.3, 4., 3.),
        ((1.6, 1.9), 2.2, 0, 4., 3.), ((1.6, 1.9), 2.2, 0, 5.4, 4.),
    ]:
        image, mask, ppm, sigma = _shadowed_scene(shift, width, depth, ppm=ppm, sigma=sigma)
        row = {"shift_mm": shift, "shadow_width_mm": width, "shadow_depth": depth, "ppm": ppm, "sigma_px": sigma}
        for name, solver in (("deleted_only", deleted_only), ("kkt_repair", current)):
            diagnostics = []

            def measured(matrix, rhs, unbounded=0, _solver=solver, _diagnostics=diagnostics):
                x = _solver(matrix, rhs, unbounded)
                gradient = matrix @ x - rhs
                units = np.sqrt(np.diag(matrix))
                dual_scale = max(float(np.max(np.abs(rhs / units))), 1e-300)
                _diagnostics.append({
                    "negative_node": bool(np.any(x[unbounded:] < 0)),
                    "relative_dual_violation": float(max(0, -np.min(gradient[unbounded:] / units[unbounded:])) / dual_scale),
                })
                return x

            started = time.monotonic()
            with patch.object(shadow, "_nonnegative_solve", measured):
                light = shadow.fit_paper_light(image, mask, ppm, sigma)
            result = {
                "seconds": time.monotonic() - started, "light": light.info,
                "solves": len(diagnostics),
                "maximum_relative_dual_violation": max(d["relative_dual_violation"] for d in diagnostics),
                "negative_node": any(d["negative_node"] for d in diagnostics),
            }
            if light.info["used"]:
                result["side_errors_px"] = _side_errors(image, ppm, sigma, light)
            row[name] = result
        rows.append(row)
    return {
        "scope": "same synthetic inputs, fixed model and settings, solver substitution only",
        "sources_sha256": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ("backend/shadow.py", "backend/sheet.py", "tests/test_fidelity_math.py", "tests/synthetic.py", "scripts/shadow_solver_audit.py")
        },
        "cases": rows,
    }


if __name__ == "__main__":
    output = Path(sys.argv[1])
    report = replay()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {len(report['cases'])} paired cases to {output}")
