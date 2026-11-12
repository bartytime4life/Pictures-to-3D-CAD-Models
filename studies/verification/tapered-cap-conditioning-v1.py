"""Independent synthetic conditioning controls for tangent-circle cap refinement.

Use --output NEW_JSON. A fixed 54-case census specifies exact circle samples and
analytic tangent lines independently of production fitting. It compares the
current implementation with one in-memory legacy radius-only stopping rule.
This is float64 fitting-stage numerical evidence, not physical photo accuracy.
"""

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend/fitting.py"
SOURCE_PATHS = (Path(__file__).resolve(), SOURCE, ROOT / "backend/sheet.py")
TOLERANCE = 0.03
ANGLES = (math.radians(2), 1e-4, 1e-6, 1e-8, 1e-9, 1e-10, 1e-11, 1e-12, 1e-13)
TRANSLATIONS = ((400.0, 20.0), (100000.0, -100000.0))
FRAMES = ((False, 0.0), (True, 0.0), (False, 0.37))
CURRENT_STOP = "if abs(r - previous_r) * max(1.0, float(np.linalg.norm(v))) < 1e-10:"
LEGACY_STOP = "if abs(step) < 1e-10:"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def hashes():
    return {str(path.relative_to(ROOT)): sha256(path.read_bytes()) for path in SOURCE_PATHS}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def legacy_module(raw):
    """One explicit source-bound ablation; all other current code is unchanged."""
    source = raw.decode()
    head, tail = source.split("def fit_fillets(", 1)
    require(tail.count(CURRENT_STOP) == 1, "expected exactly one current stopping predicate")
    altered = head + "def fit_fillets(" + tail.replace(CURRENT_STOP, LEGACY_STOP, 1)
    module = types.ModuleType("backend._tapered_cap_conditioning_legacy")
    module.__package__ = "backend"
    sys.modules[module.__name__] = module
    exec(compile(altered, str(SOURCE) + "[legacy stopping ablation]", "exec"), module.__dict__)  # noqa: S102 - source-bound single-predicate control
    return module, sha256(altered.encode())


def geometry(theta, centre, reverse_direction, rotation):
    """Known R10 circle and tangents; no production geometry fitting is used."""
    half = theta / 2
    centre = np.asarray(centre, dtype=float)
    radius = 10.0
    first = np.array([math.cos(half), math.sin(half)])
    second = np.array([-math.cos(half), math.sin(half)])
    normals = np.array([[-first[1], first[0]], [-second[1], second[0]]])
    anchors = np.array(
        [centre + radius * normals[0] - 200 * first, centre + radius * normals[1] + 200 * second]
    )
    angle = np.linspace(math.pi / 2 + half, -math.pi / 2 - half, 501)
    points = centre + radius * np.column_stack([np.cos(angle), np.sin(angle)])
    turn = np.array(
        [[math.cos(rotation), -math.sin(rotation)], [math.sin(rotation), math.cos(rotation)]]
    )
    centre, points, anchors, first, second = (
        item @ turn.T for item in (centre, points, anchors, first, second)
    )
    if reverse_direction:
        second = -second
    return centre, points, anchors, first, second, radius + 0.75 * theta


def measure(module, config):
    centre, points, anchors, first, second, old_radius = geometry(**config)
    normals = np.array([[-first[1], first[0]], [-second[1], second[0]]])
    signs = np.array([-1.0, 1.0 if config["reverse_direction"] else -1.0])
    directions = np.array([first, second])
    for direction in directions:
        require(abs(np.linalg.norm(direction) - 1) < 5e-16, "nonunit fixture direction")
    require(
        np.max(np.abs(np.linalg.norm(points - centre, axis=1) - 10)) < 5e-11,
        "independent circle observations lost their specified radius",
    )
    tangent_error = float(np.max(np.abs(np.sum(normals * (centre - anchors), axis=1) - 10 * signs)))
    require(tangent_error < 5e-11, "independent line/circle tangency lost in input representation")
    mid = centre + 10 * np.array([math.cos(config["rotation"]), math.sin(config["rotation"])])
    arc = module.Primitive(
        "arc", {"c": tuple(centre), "r": old_radius, "mid": tuple(mid)}, 0.0, 0.0, (0, 500)
    )
    prims = [
        module.Primitive("line", {"c": anchors[0], "d": first}, 0.0, 0.0),
        arc,
        module.Primitive("line", {"c": anchors[1], "d": second}, 0.0, 0.0),
    ]
    module.fit_fillets(points, prims, TOLERANCE, 0.0)
    # Compare BOTH algebraic constructions on the same represented tangent data.
    # These are diagnostics, not an exact-arithmetic oracle for input rounding.
    apex = module.intersect(anchors[0], first, anchors[1], second)
    old_v = (
        module.intersect(
            anchors[0] + signs[0] * normals[0], first, anchors[1] + signs[1] * normals[1], second
        )
        - apex
    )
    direct_v = np.linalg.solve(normals, signs)
    distances = np.sum(normals * (centre - anchors), axis=1)
    direct_centre = centre + np.linalg.solve(normals, 10 * signs - distances)
    result_centre = np.asarray(arc.data["c"])
    require(np.isfinite(result_centre).all(), "nonfinite fitted centre")
    require(math.isfinite(arc.data["r"]) and math.isfinite(arc.rms), "nonfinite fit result")
    return {
        "radius_origin": old_radius,
        "radius": arc.data["r"],
        "centre": list(result_centre),
        "centre_error_from_analytic": float(np.linalg.norm(result_centre - centre)),
        "rms": arc.rms,
        "maximum_residual": arc.max_abs,
        "constrained": "fillet" in arc.data,
        "end_cap": bool(arc.data.get("end_cap", False)),
        "unresolved_radius_note": math.isinf(arc.data.get("r_sd", 0.0)),
        "radius_ulp_times_v_norm": math.ulp(old_radius) * float(np.linalg.norm(direct_v)),
        "fixture_tangency_representation_error": tangent_error,
        "old_apex_subtraction_true_radius_centre_error": float(
            np.linalg.norm(apex + 10 * old_v - centre)
        ),
        "direct_solve_true_radius_centre_error": float(np.linalg.norm(direct_centre - centre)),
    }


def run():
    started = time.perf_counter()
    before = hashes()
    raw = SOURCE.read_bytes()
    sys.path.insert(0, str(ROOT))
    from backend import fitting

    legacy, legacy_hash = legacy_module(raw)
    rows = []
    for theta in ANGLES:
        for centre in TRANSLATIONS:
            for reverse, rotation in FRAMES:
                config = {
                    "theta": theta,
                    "centre": list(centre),
                    "reverse_direction": reverse,
                    "rotation": rotation,
                }
                methods = {}
                for name, module in (("current", fitting), ("legacy_radius_stop", legacy)):
                    try:
                        methods[name] = {
                            "verification": "executed",
                            "measurement": measure(module, config),
                        }
                    except Exception as error:  # noqa: BLE001 - retain every declared method failure
                        methods[name] = {
                            "verification": "failed",
                            "error": f"{type(error).__name__}: {error}",
                        }
                rows.append({"index": len(rows), "config": config, "methods": methods})
    checks = []

    def check(name, condition):
        checks.append({"name": name, "verification": "passed" if condition else "failed"})

    executed = [
        row
        for row in rows
        if all(value["verification"] == "executed" for value in row["methods"].values())
    ]
    current = [row["methods"]["current"]["measurement"] for row in executed]
    historical = [row["methods"]["legacy_radius_stop"]["measurement"] for row in executed]
    check("all_54_case_pairs_retained_and_executed", len(rows) == len(executed) == 54)
    check(
        "no_nonparallel_fixture_forced_into_constant_width_branch",
        all(not item["end_cap"] for item in current),
    )
    check(
        "all_current_centre_errors_within_declared_fit_tolerance",
        all(item["centre_error_from_analytic"] < TOLERANCE for item in current),
    )
    check(
        "current_controls_include_retained_unresolved_geometry",
        any(not item["constrained"] and item["unresolved_radius_note"] for item in current),
    )
    decisive = next(
        row
        for row in rows
        if row["config"]
        == {"theta": 1e-10, "centre": [400.0, 20.0], "reverse_direction": False, "rotation": 0.0}
    )
    if decisive in executed:
        check(
            "legacy_small_radius_step_causes_material_centre_error",
            decisive["methods"]["legacy_radius_stop"]["measurement"]["centre_error_from_analytic"]
            > TOLERANCE,
        )
        check(
            "spatial_step_resolves_decisive_exact_circle",
            decisive["methods"]["current"]["measurement"]["centre_error_from_analytic"] < 1e-7,
        )
    else:
        check("legacy_small_radius_step_causes_material_centre_error", False)
        check("spatial_step_resolves_decisive_exact_circle", False)
    after = hashes()
    check(
        "source_unchanged_during_census",
        before == after and sha256(raw) == before["backend/fitting.py"],
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    failures = sum(
        value["verification"] == "failed" for row in rows for value in row["methods"].values()
    )
    failed_checks = sum(check["verification"] == "failed" for check in checks)
    return {
        "format": "pictures-to-cad-tapered-cap-conditioning",
        "version": 1,
        "verification": "failed" if failures or failed_checks else "passed",
        "source_sha256_before": before,
        "source_sha256_after": after,
        "head": revision.stdout.strip() if revision.returncode == 0 else None,
        "in_memory_control": {
            "base_source_sha256": sha256(raw),
            "altered_source_sha256": legacy_hash,
            "replacement_from": CURRENT_STOP,
            "replacement_to": LEGACY_STOP,
            "all_other_source_preserved": True,
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "seconds": time.perf_counter() - started,
        },
        "population": {
            "cases": 54,
            "methods_per_case": 2,
            "angles": list(ANGLES),
            "translations": list(TRANSLATIONS),
            "frames": list(FRAMES),
        },
        "settings": {
            "true_radius": 10.0,
            "old_radius": "10+0.75*theta",
            "arc_points": 501,
            "line_anchor_distance": 200.0,
            "tolerance": TOLERANCE,
            "sigma": 0.0,
        },
        "summary": {
            "retained_case_pairs": len(rows),
            "executed_case_pairs": len(executed),
            "method_execution_failures": failures,
            "checks": len(checks),
            "failed_checks": failed_checks,
            "current_maximum_centre_error": max(
                (item["centre_error_from_analytic"] for item in current), default=None
            ),
            "legacy_maximum_centre_error": max(
                (item["centre_error_from_analytic"] for item in historical), default=None
            ),
            "current_constrained_cases": sum(item["constrained"] for item in current),
            "current_retained_cases": sum(not item["constrained"] for item in current),
        },
        "checks": checks,
        "rows": rows,
        "limits": [
            "This fixed development census includes previously inspected controls; it is not a new holdout or a physical-photo benchmark.",
            "The direct synthetic fitting-stage controls use exact analytic circles/tangents before float64 representation; extreme-angle translated inputs retain finite representation and dot-product error.",
            "The legacy control changes only the current stopping predicate in memory. It does not reconstruct every historical implementation change or isolate the 5-degree branch defect.",
            "Retained free arcs and radius-ulp checks are numerical safeguards. Twenty Gauss-Newton iterations are not a certified global minimum or a physical uncertainty bound.",
            "The independent analytic centre comparison and tangent construction do not use production circle fitting, rendering, blurring or photo tracing. Production intersect is used only for the explicitly labeled old-apex diagnostic.",
        ],
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new .json report; existing files/symlinks refused",
    )
    args = parser.parse_args(arguments)
    if args.output.exists() or args.output.is_symlink():
        parser.error("output already exists; preserve it and choose a fresh destination")
    if args.output.suffix.lower() != ".json":
        parser.error("output must have a .json suffix")
    try:
        report = run()
    except (OSError, ValueError, TypeError, AssertionError, ImportError) as error:
        parser.error(f"conditioning census setup failed: {error}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "verification": report["verification"],
                "summary": report["summary"],
                "runtime": report["runtime"],
            },
            indent=2,
        )
    )
    return int(report["verification"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
