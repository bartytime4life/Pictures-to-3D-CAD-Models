"""Replay independently specified tapered/parallel boundaries through real exports.

Requires fresh --output JSON and --artifacts directory. --source-root optionally
selects another local checkout for a baseline replay. Every declared row is kept,
including construction/export failures. This checks digital synthetic geometry,
not an image capture, physical tolerance, or an independent CAD kernel.
"""

import argparse
import hashlib
import importlib
import itertools
import json
import math
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cadquery as cq
import ezdxf
import numpy as np
import shapely
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[2]
MM_PER_PX = 0.2
THICKNESS_MM = 4.0
GEOMETRY_TOLERANCE_PX = 0.05
SOURCE_STEP_PX = 0.15


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(root):
    paths = [*sorted((root / "backend").glob("*.py")), root / "pyproject.toml", root / "uv.lock"]
    return {str(p.relative_to(root)): sha(p) for p in paths}


def git_state(root):
    def call(*args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, timeout=10
        ).strip()

    try:
        return {
            "revision": call("rev-parse", "HEAD"),
            "dirty_files": call("status", "--porcelain", "--untracked-files=all").splitlines(),
        }
    except (OSError, subprocess.SubprocessError):
        return {"revision": None, "dirty_files": None, "reason": "Git metadata unavailable"}


def exact_cap(length, degrees=89.0):
    """Literal radius-10 arc, its exact tangent sides, and a vertical back."""
    r, beta = 10.0, math.radians(degrees)
    lower = np.array([r * math.cos(beta), -r * math.sin(beta)])
    upper = lower * [1, -1]
    back_y = r * math.sin(beta) + math.cos(beta) / math.sin(beta) * (length + lower[0])
    back_top, back_bottom = np.array([-length, back_y]), np.array([-length, -back_y])
    return [
        ("arc", np.zeros(2), r, -beta, 2 * beta),
        ("line", upper, back_top),
        ("line", back_top, back_bottom),
        ("line", back_bottom, lower),
    ]


def exact_capsule(equal=False):
    """Convex hull of two exact discs, using their analytic common tangents."""
    r1, r2, distance = 20.0, 20.0 if equal else 24.0, 160.0
    alpha = math.asin((r2 - r1) / distance)
    top, bottom = math.pi / 2 + alpha, 3 * math.pi / 2 - alpha
    c1, c2 = np.zeros(2), np.array([distance, 0.0])

    def at(c, r, a):
        return c + r * np.array([math.cos(a), math.sin(a)])

    return [
        ("arc", c1, r1, top, bottom - top),
        ("line", at(c1, r1, bottom), at(c2, r2, bottom)),
        ("arc", c2, r2, bottom, top + 2 * math.pi - bottom),
        ("line", at(c2, r2, top), at(c1, r1, top)),
    ]


def truth_geometry(segments):
    """Green integral and exact cardinal extrema of the declared primitives."""
    area_twice, points, arcs, sample_error = 0.0, [], [], 0.0
    for s in segments:
        if s[0] == "line":
            _, a, b = s
            area_twice += float(a[0] * b[1] - a[1] * b[0])
            points.extend((a, b))
        else:
            _, c, r, a, sweep = s
            end = a + sweep
            area_twice += r * r * sweep + r * c[0] * (math.sin(end) - math.sin(a))
            area_twice -= r * c[1] * (math.cos(end) - math.cos(a))
            angles = [a, end]
            angles += [
                k * math.pi / 2
                for k in range(math.ceil(a / (math.pi / 2)), math.floor(end / (math.pi / 2)) + 1)
            ]
            points.extend(c + r * np.array([math.cos(t), math.sin(t)]) for t in angles)
            arcs.append({"center": c.tolist(), "radius": r})
            n = max(2, math.ceil(r * sweep / SOURCE_STEP_PX))
            sample_error = max(sample_error, r * (1 - math.cos(sweep / (2 * n))))
    points = np.asarray(points)
    return {
        "area_px2": abs(area_twice / 2),
        "bounds_px": [*points.min(axis=0), *points.max(axis=0)],
        "arcs": arcs,
        "source_chord_error_px": sample_error,
    }


def transformed(segments, degrees):
    angle = math.radians(degrees)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    shift = np.array([71.0, -43.0]) if degrees else np.zeros(2)
    result = []
    for s in segments:
        if s[0] == "line":
            result.append(("line", rotation @ s[1] + shift, rotation @ s[2] + shift))
        else:
            result.append(("arc", rotation @ s[1] + shift, s[2], s[3] + angle, s[4]))
    return result


def sample_truth(segments):
    points = []
    for s in segments:
        if s[0] == "line":
            n = max(2, math.ceil(float(np.linalg.norm(s[2] - s[1])) / SOURCE_STEP_PX))
            points.extend(np.linspace(s[1], s[2], n, endpoint=False))
        else:
            _, c, r, start, sweep = s
            n = max(2, math.ceil(r * sweep / SOURCE_STEP_PX))
            t = np.linspace(start, start + sweep, n, endpoint=False)
            points.extend(c + r * np.column_stack([np.cos(t), np.sin(t)]))
    return np.asarray(points)


def circumcircle(a, mid, b):
    """Independent 2x2 circumcentre; does not call production arc_geometry."""
    matrix = 2 * np.asarray([mid - a, b - a])
    center = np.linalg.solve(matrix, np.asarray([mid @ mid - a @ a, b @ b - a @ a]))
    return center, float(np.linalg.norm(a - center))


def metadata(prims):
    return [
        {
            "kind": p.kind,
            "rms": p.rms,
            "max_abs": p.max_abs,
            "radius_px": p.data.get("r"),
            "center_px": p.data.get("c"),
            "end_cap": bool(p.data.get("end_cap")),
            "fillet": "fillet" in p.data,
        }
        for p in prims
    ]


def run_case(case, backend, directory):
    fitting, reference, models, worker, drawing = backend
    row = {"case": case[0], "checks": [], "errors": [], "artifacts": {}}

    def check(name, passed, **evidence):
        row["checks"].append({"name": name, "passed": bool(passed), **evidence})

    def artifact(path):
        row["artifacts"][path.name] = {"sha256": sha(path), "bytes": path.stat().st_size}

    segments = transformed(case[1], case[2])
    truth = truth_geometry(segments)
    points = sample_truth(segments)
    if case[3]:
        points = np.roll(points[::-1], 17, axis=0)
    row.update(truth=truth, transform_degrees=case[2], reversed=case[3])
    tolerance = 0.03 / MM_PER_PX  # Actual reference.py sigma=0 tolerance at five px/mm.
    extent_mm = float(np.ptp(points, axis=0).max()) * MM_PER_PX
    min_line = min(max(0.025 * extent_mm, 1.0), 3.0) / MM_PER_PX
    row["fitting_settings"] = {"tolerance_px": tolerance, "min_line_px": min_line, "sigma_px": 0}
    try:
        prims = fitting.fit_ring(points, tolerance, min_line)
        check("initial_analytic_fit", prims is not None)
        if prims is None:
            return row
        row["initial_metadata"] = metadata(prims)
        notes, _ = fitting.snap_axes([prims])
        fitting.refit_lines(points, prims, margin=0)
        fitting.fit_fillets(points, prims, tolerance, 0)
        fitting.correct_blur(prims, 0)
        notes.extend(fitting.equalise_radii([prims], scale=MM_PER_PX, unit="mm"))
        notes.extend(fitting.undetermined_radii([prims], 0, scale=MM_PER_PX, unit="mm"))
        row.update(final_metadata=metadata(prims), notes=notes)
        actual = fitting.segments(prims)
        sampled = fitting.sample_segments(actual, 0.001)
        distance = float(
            shapely.hausdorff_distance(
                Polygon(points).boundary, Polygon(sampled).boundary, densify=0.25
            )
        )
        check(
            "source_boundary_preserved",
            distance <= GEOMETRY_TOLERANCE_PX,
            hausdorff_px=distance,
            tolerance_px=GEOMETRY_TOLERANCE_PX,
        )
        radius_errors = []
        for p, s in zip(prims, actual):
            if p.kind == "arc":
                _, radius = circumcircle(*map(np.asarray, s[1:]))
                radius_errors.append(abs(radius - p.data["r"]))
        check(
            "stored_and_emitted_arc_radii_agree",
            bool(radius_errors) and max(radius_errors) < 1e-6,
            absolute_errors_px=radius_errors,
        )
        mm = [(s[0], *(np.asarray(p) * MM_PER_PX for p in s[1:])) for s in actual]
        polygon = Polygon(sampled * MM_PER_PX)
        transform = reference._Transform(np.eye(2), np.zeros(2), np.zeros(2), MM_PER_PX)
        described = reference._to_model(actual, transform)
        profile = models.Profile(
            outer=(sampled * MM_PER_PX).tolist(), primitives={"outer": described, "holes": []}
        )
        check("actual_profile_validation", True)
        profile_path = directory / "profile.json"
        profile_path.write_text(profile.model_dump_json(indent=2) + "\n")
        artifact(profile_path)
    except Exception as error:  # noqa: BLE001 -- retain fitting/kernel failures in the complete census.
        row["errors"].append(
            {"stage": "fitting_profile", "error": f"{type(error).__name__}: {error}"}
        )
        return row

    expected_bounds = np.asarray(truth["bounds_px"]) * MM_PER_PX
    expected_size = expected_bounds[2:] - expected_bounds[:2]
    expected_area = truth["area_px2"] * MM_PER_PX**2
    dimension_tolerance = GEOMETRY_TOLERANCE_PX * MM_PER_PX
    # A tolerance-width boundary strip: a digital regression allowance, not metrology.
    area_tolerance = dimension_tolerance * Polygon(points * MM_PER_PX).length
    try:
        solid, area = worker.extrude_fitted([mm], THICKNESS_MM, polygon)
        path = directory / "model.step"
        cq.exporters.export(solid, str(path))
        artifact(path)
        restored = cq.importers.importStep(str(path)).val()
        measured = worker.dimensions_of(restored)
        delta = np.asarray([measured["width"], measured["height"]]) - expected_size
        check(
            "step_dimensions_match_truth",
            max(abs(delta)) <= dimension_tolerance,
            errors_mm=delta.tolist(),
            tolerance_mm=dimension_tolerance,
        )
        check(
            "step_volume_matches_truth",
            abs(restored.Volume() - expected_area * THICKNESS_MM) <= area_tolerance * THICKNESS_MM,
            volume_mm3=restored.Volume(),
            expected_mm3=expected_area * THICKNESS_MM,
            tolerance_mm3=area_tolerance * THICKNESS_MM,
        )
        check("cad_valid_single_solid", restored.isValid() and len(restored.Solids()) == 1)
        row["cad_area_mm2"] = area
    except Exception as error:  # noqa: BLE001 -- a STEP failure must not hide DXF/SVG results.
        row["errors"].append({"stage": "cad_step", "error": f"{type(error).__name__}: {error}"})
    try:
        path = directory / "profile.dxf"
        worker.write_fitted_dxf(path, [mm])
        artifact(path)
        document = ezdxf.readfile(path)
        arcs = list(document.modelspace().query("ARC"))
        expected = truth["arcs"]
        check(
            "dxf_units_and_arc_count",
            document.units == ezdxf.units.MM and len(arcs) == len(expected),
            arc_count=len(arcs),
            expected_arc_count=len(expected),
        )
        if len(arcs) == len(expected):
            assignments = []
            for permutation in itertools.permutations(range(len(arcs))):
                errors = [
                    (
                        float(
                            np.linalg.norm(
                                np.asarray(arcs[j].dxf.center)[:2] / MM_PER_PX - t["center"]
                            )
                        ),
                        abs(arcs[j].dxf.radius / MM_PER_PX - t["radius"]),
                    )
                    for t, j in zip(expected, permutation)
                ]
                assignments.append((sum(sum(pair) for pair in errors), permutation, errors))
            _, _, errors = min(assignments)
            check(
                "dxf_arc_centers_and_radii_match_truth",
                max(max(pair) for pair in errors) <= GEOMETRY_TOLERANCE_PX,
                center_radius_errors_px=errors,
                tolerance_px=GEOMETRY_TOLERANCE_PX,
            )
    except Exception as error:  # noqa: BLE001 -- retain parser/kernel failures and continue.
        row["errors"].append({"stage": "dxf", "error": f"{type(error).__name__}: {error}"})
    try:
        path = directory / "profile.svg"
        text = drawing.svg(drawing.fitted_loops([mm]), case[0])
        path.write_text(text)
        artifact(path)
        svg = ET.fromstring(text)
        dimensions = np.asarray(
            [
                float(svg.attrib[k].removesuffix("mm")) - 2 * drawing.SVG_MARGIN
                for k in ("width", "height")
            ]
        )
        radii = [float(v) / MM_PER_PX for v in re.findall(r"\bA ([\d.eE+\-]+) ", text)]
        check(
            "svg_dimensions_match_truth",
            max(abs(dimensions - expected_size)) <= dimension_tolerance,
            errors_mm=(dimensions - expected_size).tolist(),
            tolerance_mm=dimension_tolerance,
        )
        radius_error = max(
            (min(abs(r - t["radius"]) for t in truth["arcs"]) for r in radii), default=math.inf
        )
        check(
            "svg_arc_radii_match_truth",
            bool(radii) and radius_error <= GEOMETRY_TOLERANCE_PX,
            maximum_radius_error_px=radius_error if math.isfinite(radius_error) else None,
        )
    except Exception as error:  # noqa: BLE001 -- retain malformed export failures and continue.
        row["errors"].append({"stage": "svg", "error": f"{type(error).__name__}: {error}"})
    return row


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path, default=ROOT, help="local checkout supplying backend modules"
    )
    parser.add_argument("--output", type=Path, required=True, help="fresh full JSON report")
    parser.add_argument(
        "--artifacts",
        type=Path,
        required=True,
        help="fresh directory for actual Profile/STEP/DXF/SVG files",
    )
    args = parser.parse_args(arguments)
    source = args.source_root.resolve()
    if (
        args.output.exists()
        or args.output.is_symlink()
        or args.artifacts.exists()
        or args.artifacts.is_symlink()
    ):
        parser.error("output/artifact paths must be fresh; preserve the earlier run")
    if not (source / "backend/fitting.py").is_file():
        parser.error("source-root must contain the Pictures-to-CAD backend")
    before, runner_before = source_hashes(source), sha(Path(__file__))
    sys.path.insert(0, str(source))
    backend = [
        importlib.import_module("backend." + name)
        for name in ("fitting", "reference", "models", "worker", "drawing")
    ]
    if any(Path(module.__file__).resolve().parent != source / "backend" for module in backend):
        parser.error("backend imports did not resolve to the selected source checkout")
    cases = [
        (f"tapered_cap_L{length}", exact_cap(length), 0, False) for length in (50, 100, 200, 400)
    ]
    cases += [
        ("tapered_cap_L200_rotated_reversed", exact_cap(200), 37, True),
        ("unequal_circle_capsule", exact_capsule(), 0, False),
        ("unequal_circle_capsule_rotated_reversed", exact_capsule(), 37, True),
        ("parallel_cap_L50", exact_cap(50, 90), 0, False),
        ("parallel_cap_L200", exact_cap(200, 90), 0, False),
        ("parallel_equal_circle_capsule", exact_capsule(True), 0, False),
        ("parallel_equal_circle_capsule_rotated_reversed", exact_capsule(True), 37, True),
    ]
    args.artifacts.mkdir(parents=True)
    rows = []
    for index, case in enumerate(cases):
        directory = args.artifacts / case[0]
        directory.mkdir()
        try:
            row = run_case(case, backend, directory)
        except Exception as error:  # noqa: BLE001 -- every declared row survives unexpected failure.
            row = {
                "case": case[0],
                "checks": [],
                "errors": [{"stage": "row", "error": f"{type(error).__name__}: {error}"}],
                "artifacts": {},
            }
        row["index"] = index
        row["passed"] = (
            bool(row["checks"]) and not row["errors"] and all(c["passed"] for c in row["checks"])
        )
        rows.append(row)
    after, runner_after = source_hashes(source), sha(Path(__file__))
    stable = before == after and runner_before == runner_after
    report = {
        "format": "pictures-to-cad-tapered-cap-export-regression",
        "version": 1,
        "source_root": str(source),
        "git": git_state(source),
        "source_sha256_before": before,
        "source_sha256_after": after,
        "runner_sha256_before": runner_before,
        "runner_sha256_after": runner_after,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "shapely": shapely.__version__,
            "cadquery": cq.__version__,
            "ezdxf": ezdxf.__version__,
        },
        "artifact_directory": str(args.artifacts.resolve()),
        "settings": {
            "source_step_px": SOURCE_STEP_PX,
            "mm_per_px": MM_PER_PX,
            "geometry_tolerance_px": GEOMETRY_TOLERANCE_PX,
            "thickness_mm": THICKNESS_MM,
        },
        "rows": rows,
        "summary": {
            "expected_rows": len(cases),
            "retained_rows": len(rows),
            "passed_rows": sum(r["passed"] for r in rows),
            "failed_rows": sum(not r["passed"] for r in rows),
            "source_stable": stable,
        },
        "limits": [
            "Exact synthetic tangent geometry, sigma zero; not a rendered/full-photo accuracy study.",
            "Profile/CAD/STEP use the actual production classes and OCC kernel; STEP readback is not an independent CAD kernel.",
            "Truth uses analytic circle/tangent geometry, Green integrals and cardinal extrema; source chord error is recorded.",
            "A numerical geometry tolerance is a digital regression allowance, not a physical error bound.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(clean(report), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "summary": report["summary"]}))
    return 0 if stable and all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
