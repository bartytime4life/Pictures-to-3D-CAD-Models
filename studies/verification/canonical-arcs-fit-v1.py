"""Six actual-fit circular-segment controls for canonical final assembly.

Use --output NEW_JSON; --source-root selects a local backend checkout. The fixed
R10/h=-6,0,6 observations are EXACT UNBLURRED GEOMETRY. Applying requested sigma
1.5 is deliberately mismatched and tests representation only, never optical
recovery, physical accuracy or physical uniqueness. No server or CAD export runs.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
RADIUS = 10.0
CHORDS = (-6.0, 0.0, 6.0)
SIGMAS = (0.0, 1.5)
TOLERANCE = 0.03
MIN_LINE = 1.0
CIRCLE_TOLERANCE = 2e-8
AREA_TOLERANCE = 2e-7
ARC_SAMPLES = 501
CHORD_SAMPLES = 201
VALIDITY_ARC_CHORDS = 2048


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(source_root):
    return {
        str(path.relative_to(source_root)): digest(path)
        for path in sorted((source_root / "backend").glob("*.py"))
    }


def git_state(source_root):
    result = {}
    for name, arguments in (
        ("revision", ("rev-parse", "HEAD")),
        ("tree", ("rev-parse", "HEAD^{tree}")),
        ("branch", ("branch", "--show-current")),
        ("status", ("status", "--porcelain", "--untracked-files=all")),
    ):
        try:
            process = subprocess.run(
                ["git", "-C", str(source_root), *arguments],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            result[name] = process.stdout.strip() if process.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            result[name] = None
    return result


def fixture(chord):
    beta = math.acos(chord / RADIUS)
    angle = np.linspace(-beta, beta, ARC_SAMPLES)
    arc = RADIUS * np.column_stack([np.cos(angle), np.sin(angle)])
    closing_chord = np.linspace(arc[-1], arc[0], CHORD_SAMPLES)[1:-1]
    return np.vstack([arc, closing_chord])


def circumcircle(segment):
    """Independent translated linear equations; no production arc_geometry."""
    start, middle, end = (np.asarray(point, dtype=float) for point in segment[1:])
    first, second = middle - start, end - start
    local = np.linalg.solve(2 * np.vstack([first, second]), [first @ first, second @ second])
    centre = start + local
    radius = float(np.linalg.norm(local))
    angle, witness, last = (
        math.atan2((point - centre)[1], (point - centre)[0]) for point in (start, middle, end)
    )
    ccw = (last - angle) % (2 * math.pi)
    sweep = ccw if (witness - angle) % (2 * math.pi) < ccw else ccw - 2 * math.pi
    if not np.isfinite(centre).all() or not math.isfinite(radius) or radius <= 0:
        raise ValueError("nonfinite/degenerate independent circumcircle")
    return centre, radius, angle, sweep


def boundary_measurements(segments):
    """Analytic segment-area formula and a separately sampled validity check."""
    if not segments or any(segment[0] not in {"line", "arc"} for segment in segments):
        raise ValueError("expected a nonempty line/three-point-arc boundary")
    origin = np.asarray(segments[0][1], dtype=float)
    twice_area, closure_error = 0.0, 0.0
    sampled, arcs = [], []
    for segment, following in zip(segments, segments[1:] + segments[:1]):
        start, end = np.asarray(segment[1]), np.asarray(segment[-1])
        closure_error = max(closure_error, math.dist(end, following[1]))
        a, b = start - origin, end - origin
        twice_area += float(a[0] * b[1] - a[1] * b[0])
        if segment[0] == "line":
            sampled.append(start)
            continue
        centre, radius, angle, sweep = circumcircle(segment)
        twice_area += radius**2 * (sweep - math.sin(sweep))
        at = angle + np.arange(VALIDITY_ARC_CHORDS) * sweep / VALIDITY_ARC_CHORDS
        sampled.extend(centre + radius * np.column_stack([np.cos(at), np.sin(at)]))
        arcs.append({"centre": centre.tolist(), "radius": radius, "sweep": sweep})
    polygon = Polygon(np.asarray(sampled))
    return {
        "closure_error": closure_error,
        "closed": closure_error <= CIRCLE_TOLERANCE,
        "sampled_polygon_valid": bool(polygon.is_valid and polygon.area > 0),
        "sampled_polygon_area": float(polygon.area),
        "segment_integral_area": abs(twice_area) / 2,
        "arcs": arcs,
    }


def expected_geometry(chord, sigma):
    # This deliberately supplied radius update is the recorded series operation,
    # not the physical truth of the unblurred input observations when sigma > 0.
    radius = RADIUS + sigma**2 / (2 * RADIUS) - sigma**4 / (24 * RADIUS**3)
    beta = math.acos(chord / radius)
    return {
        "centre": [0.0, 0.0],
        "radius_after_requested_update": radius,
        "sweep": 2 * beta,
        "closed_formula_area": radius**2 * beta - chord * math.sqrt(radius**2 - chord**2),
    }


def evaluate(fitting, reference, chord, sigma):
    points = fixture(chord)
    row = {
        "chord": chord,
        "requested_sigma": sigma,
        "observation_geometry": "exact_unblurred_circle_segment",
        "deliberately_mismatched_blur_request": sigma > 0,
        "expected_representation": expected_geometry(chord, sigma),
        "execution": "executed",
        "checks": {},
    }
    prims = fitting.fit_ring(points, TOLERANCE, MIN_LINE)
    initial = prims is not None
    row["initial_fit"] = {
        "analytic_candidate": initial,
        "kinds": [p.kind for p in prims] if initial else [],
    }
    if initial:
        fitting.correct_blur(prims, sigma)
    segments, analytic = reference._segments_for(points, prims, TOLERANCE)
    row["final_analytic"] = bool(analytic)
    row["final_kinds"] = [segment[0] for segment in segments]
    measurements = boundary_measurements(segments)
    row["measurements"] = measurements
    stored = [p for p in (prims or []) if p.kind == "arc"]
    row["stored_arcs_after_update"] = [
        {"centre": list(p.data["c"]), "radius": float(p.data["r"])} for p in stored
    ]
    observed = measurements["arcs"]
    checks = row["checks"]
    checks["actual_fit_reaches_one_arc_and_one_line"] = bool(
        initial and sorted(p.kind for p in prims) == ["arc", "line"]
    )
    checks["final_boundary_is_analytic"] = bool(analytic)
    checks["represented_boundary_is_closed"] = measurements["closed"]
    checks["sampled_final_polygon_is_valid"] = measurements["sampled_polygon_valid"]
    one_arc = analytic and len(stored) == len(observed) == 1
    checks["one_emitted_arc_matches_stored_circle"] = bool(
        one_arc
        and math.dist(observed[0]["centre"], stored[0].data["c"]) <= CIRCLE_TOLERANCE
        and abs(observed[0]["radius"] - stored[0].data["r"]) <= CIRCLE_TOLERANCE
    )
    expected = row["expected_representation"]
    checks["emitted_circle_matches_supplied_radius_update"] = bool(
        one_arc
        and math.dist(observed[0]["centre"], expected["centre"]) <= CIRCLE_TOLERANCE
        and abs(observed[0]["radius"] - expected["radius_after_requested_update"])
        <= CIRCLE_TOLERANCE
    )
    checks["oriented_sweep_matches_transverse_intersections"] = bool(
        one_arc and abs(observed[0]["sweep"] - expected["sweep"]) <= CIRCLE_TOLERANCE
    )
    checks["analytic_area_matches_closed_formula"] = bool(
        analytic
        and abs(measurements["segment_integral_area"] - expected["closed_formula_area"])
        <= AREA_TOLERANCE
    )
    row["passed"] = all(checks.values())
    return row


def run(source_root):
    started = time.perf_counter()
    before, runner_before = source_hashes(source_root), digest(RUNNER)
    git_before = git_state(source_root)
    modules, setup_error = {}, None
    try:
        sys.path.insert(0, str(source_root))
        fitting = importlib.import_module("backend.fitting")
        reference = importlib.import_module("backend.reference")
        for name, module in list(sys.modules.items()):
            if (name == "backend" or name.startswith("backend.")) and getattr(
                module, "__file__", None
            ):
                path = Path(module.__file__).resolve()
                if not path.is_relative_to(source_root / "backend"):
                    raise ValueError(f"{name} loaded outside the selected backend root")
                modules[name] = str(path)
    except Exception as error:  # noqa: BLE001 - a failed setup still retains all six declared rows
        setup_error = f"{type(error).__name__}: {error}"
    rows = []
    for chord in CHORDS:
        for sigma in SIGMAS:
            try:
                if setup_error is not None:
                    raise RuntimeError(setup_error)
                row = evaluate(fitting, reference, chord, sigma)
            except Exception as error:  # noqa: BLE001 - retain failed rows and continue the complete census
                row = {
                    "chord": chord,
                    "requested_sigma": sigma,
                    "execution": "failed",
                    "error": f"{type(error).__name__}: {error}",
                    "passed": False,
                    "checks": {},
                }
            rows.append({"index": len(rows), **row})
    after, runner_after = source_hashes(source_root), digest(RUNNER)
    source_unchanged = before == after and runner_before == runner_after
    errors = sum(row["execution"] == "failed" for row in rows)
    failed = sum(not row["passed"] for row in rows)
    return {
        "format": "pictures-to-cad-canonical-arcs-actual-fit",
        "version": 1,
        "verification": "passed" if failed == 0 and source_unchanged else "failed",
        "source_root": str(source_root),
        "runner": str(RUNNER),
        "runner_sha256_before": runner_before,
        "runner_sha256_after": runner_after,
        "source_sha256_before": before,
        "source_sha256_after": after,
        "source_unchanged": source_unchanged,
        "loaded_backend_modules": modules,
        "git_before": git_before,
        "git_after": git_state(source_root),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "shapely": shapely.__version__,
            "seconds": time.perf_counter() - started,
        },
        "settings": {
            "true_input_radius": RADIUS,
            "chords": list(CHORDS),
            "requested_sigmas": list(SIGMAS),
            "fit_tolerance": TOLERANCE,
            "minimum_line": MIN_LINE,
            "circle_samples": ARC_SAMPLES,
            "closing_chord_samples_including_endpoints": CHORD_SAMPLES,
            "validity_chords_per_arc": VALIDITY_ARC_CHORDS,
            "circle_comparison_tolerance": CIRCLE_TOLERANCE,
            "analytic_area_comparison_tolerance": AREA_TOLERANCE,
        },
        "summary": {
            "declared_rows": 6,
            "retained_rows": len(rows),
            "executed_rows": len(rows) - errors,
            "execution_errors": errors,
            "initial_analytic_candidates": sum(
                row.get("initial_fit", {}).get("analytic_candidate", False) for row in rows
            ),
            "final_analytic_boundaries": sum(row.get("final_analytic", False) for row in rows),
            "passed_rows": len(rows) - failed,
            "failed_target_rows": failed,
            "failed_row_checks": sum(not value for row in rows for value in row["checks"].values()),
        },
        "rows": rows,
        "limits": [
            "Six fixed development cases exercise actual fit_ring, correct_blur and reference._segments_for; they do not execute the full photo tracer or qualify its optics.",
            "Every source curve is exact unblurred R10 geometry. Requested sigma1.5 is deliberately mismatched; its radius/area expectation checks the requested representation operation, not recovery of a physically true circle.",
            "Baseline polyline outcomes are retained failed analytic-target checks, not execution errors. An exit1 baseline report is expected when the earlier source cannot reach these analytic D-shapes.",
            "Circle reconstruction and closed-form segment area are independent of production arc_geometry. Polygon validity uses a declared finite chord sampling and is not a formal analytic simplicity proof.",
            "This comparison omits CAD exports and physical fit. The separate new regression tests cover actual STEP/DXF/SVG geometry; a source hash or a valid polygon is not physical acceptance.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new .json report; existing files and symlinks refused",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=ROOT,
        help="local checkout supplying backend source; default is this repository",
    )
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("--output must be a fresh destination")
    if args.output.suffix.lower() != ".json":
        parser.error("--output must have a .json suffix")
    ancestor = args.output.parent
    while not ancestor.exists() and not ancestor.is_symlink():
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        parser.error("--output parent must be a directory or creatable beneath one")
    source_root = args.source_root.resolve()
    if not all(
        (source_root / "backend" / name).is_file() for name in ("fitting.py", "reference.py")
    ):
        parser.error("--source-root must contain backend/fitting.py and backend/reference.py")
    report = run(source_root)
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except OSError as error:
        parser.error(f"cannot save fresh report: {error}")
    print(
        json.dumps(
            {
                "verification": report["verification"],
                "summary": report["summary"],
                "seconds": report["runtime"]["seconds"],
            },
            indent=2,
        )
    )
    return int(report["verification"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
