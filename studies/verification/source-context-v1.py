"""Replay private source capture through the actual trace and conditional fitter.

The digital comparison uses the full existing image pipeline, not its sampling
matrix. The finite fixture independently rasterizes area coverage, Gaussian blurs
it, and quantizes through sRGB. That is intentionally not the point-detector
Gaussian model: the row checks a finite engineering tolerance, never exact model
equivalence or a physical camera. No source image or pixel values are saved.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/source-context-v1.json"


def hashes():
    paths = sorted((ROOT / "backend").glob("*.py"))
    paths.extend([PLAN, Path(__file__), ROOT / "tests/synthetic.py"])
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def fixture(case):
    import cv2
    import numpy as np
    from PIL import Image
    from shapely.geometry import Point, box

    from tests import synthetic as s

    if case["kind"] == "camera":
        return s.render(size=(1200, 900), **case.get("render", {}))[0]
    if case["kind"] == "colour":
        return s.colour_photo((120, 120, 120), (220, 220, 220), (0, 255, 0), ppm=4)
    # Independent polygon-area renderer, not finite_shape or its ring helper.
    ppm, margin, sigma = 4, 40, 1.5
    c, r, f = case["centre"], case["radius"], case["fraction"]
    shape = (int((297 + 2 * margin) * ppm), int((210 + 2 * margin) * ppm))
    circle = Point(c).buffer(r, quad_segs=2048)
    part = circle.intersection(box(c[0] - 2 * r, c[1] - 2 * r, c[0] + r * f, c[1] + 2 * r))
    # The coverage helper's scene index is centred at x0+i/ppm. The rendered
    # working photo instead uses geometric pixel centres i+.5, including paper.
    coverage = s.coverage(part, ppm, -margin + 0.5 / ppm, -margin + 0.5 / ppm, shape)
    sheet = np.zeros(shape)
    sheet[margin * ppm : (margin + 297) * ppm, margin * ppm : (margin + 210) * ppm] = 1
    table, paper, material = s.srgb_to_linear(np.array([70.0, 230.0, 40.0]))
    light = table * (1 - sheet) + paper * sheet
    light = light * (1 - coverage) + material * coverage
    encoded = s.linear_to_srgb(cv2.GaussianBlur(light, (0, 0), sigma))
    rgb = np.repeat(np.rint(encoded).clip(0, 255).astype(np.uint8)[..., None], 3, axis=2)
    output = io.BytesIO()
    Image.fromarray(rgb).save(output, "PNG")
    return output.getvalue()


def fit_control(case, context, result):
    import numpy as np

    from backend.finite_shape import finite_shape_probabilities
    from backend.finite_shape_fit import circular_segment_ring

    centre = np.asarray(case["centre"])
    radius, fraction = case["radius"], case["fraction"]
    angle = math.acos(fraction)
    arcs = np.linspace(angle + 0.12, 2 * math.pi - angle - 0.12, 6)
    directions = np.column_stack([np.cos(arcs), np.sin(arcs)])
    arc = centre + radius * directions
    chord = np.column_stack(
        [
            np.full(6, centre[0] + radius * fraction),
            centre[1] + np.linspace(-0.8, 0.8, 6) * radius * math.sqrt(1 - fraction**2),
        ]
    )
    boundary = np.vstack([arc, chord])
    normals = np.vstack([directions, np.tile([1, 0], (6, 1))])
    points = (
        boundary[:, None, :] + normals[:, None, :] * np.array([-3.0, 0.0, 3.0])[None, :, None] / 4
    )
    pixels = np.floor((points.reshape(-1, 2) + 40) * 4).astype(int)
    observation = context.source_pixels(pixels, profile=result["profile"])
    before = context.metadata()["profile_sha256"]
    fit = context.fit_circular_segment(
        observation,
        profile=result["profile"],
        input_std=1.0,
        psf_covariance=np.eye(2) * 1.5**2,
        centre=centre,
        radius_bounds=(19.8, 20.5),
        chord_fraction_bounds=(0.22, 0.31),
        grid_points=3,
        max_basins=2,
        refinement_iterations=24,
        max_evaluations=128,
        forward_work_limit=20_000_000,
    )
    best = fit.best
    if best is None:
        raise ValueError("finite-shape control found no represented candidate")
    heldout_angles = np.linspace(angle + 0.2, 2 * math.pi - angle - 0.2, 10)
    heldout_points = centre + radius * np.column_stack(
        [np.cos(heldout_angles), np.sin(heldout_angles)]
    )
    heldout_pixels = np.floor((heldout_points + 40) * 4).astype(int)
    heldout = context.source_pixels(heldout_pixels, profile=result["profile"])
    probability = finite_shape_probabilities(
        heldout_pixels,
        [circular_segment_ring(best.radius, best.chord_fraction, centre=centre)],
        psf_covariance=np.eye(2) * 1.5**2,
        **context.point_gaussian_geometry(profile=result["profile"]),
    )
    if any(v is None for v in probability.probabilities):
        raise ValueError("heldout source prediction was unresolved")
    mean = best.levels[0] + (best.levels[1] - best.levels[0]) * np.asarray(
        probability.probabilities
    )
    radius_error = abs(best.radius - radius)
    fraction_error = abs(best.chord_fraction - fraction)
    heldout_error = float(np.max(np.abs(mean - heldout.raw_values)))
    context.assert_profile(result["profile"])
    return {
        "passed": radius_error <= case["radius_error_max_mm"]
        and fraction_error <= case["fraction_error_max"]
        and heldout_error <= case["heldout_max_level_error"]
        and context.metadata()["profile_sha256"] == before,
        "radius_error_mm": radius_error,
        "fraction_error": fraction_error,
        "heldout_max_level_error": heldout_error,
        "fit": asdict(fit),
        "caveat": "area rasterization, finite-support digital blur, quantization and estimated pose differ from a point-detector forward model; not physical qualification",
    }


def evaluate(case, tolerance):
    import numpy as np

    from backend import sheet, tracing
    from backend.source_context import trace_with_source

    data = fixture(case)
    retained = {}
    original = sheet.rectify_gray

    def spy(field, *args, **kwargs):
        retained["field"] = field.copy()
        output = original(field, *args, **kwargs)
        retained["rectified"] = output.copy()
        return output

    import cv2

    limit = case.get("working_pixels", tracing.WORKING_PIXELS)
    with patch.object(sheet, "rectify_gray", spy), patch.object(tracing, "WORKING_PIXELS", limit):
        result, context = trace_with_source(data, reference="a4", **case.get("trace", {}))
    if context is None:
        raise ValueError("no source context published")
    profile = result["profile"]
    outline = np.asarray(profile["outer"])
    points = outline[np.linspace(0, len(outline) - 1, 4).astype(int)]
    observation = context.observe_display(points, profile=profile)
    plane = context.display_to_plane(points, profile=profile)
    xy = plane * context.metadata()["rectified_ppm"] - 0.5
    pipeline = sheet.sample_keys(
        cv2.GaussianBlur(retained["rectified"], (0, 0), 0.7), xy[:, 0], xy[:, 1]
    )
    delta = float(np.max(np.abs(pipeline - observation.samples)))
    m = context.metadata()
    try:
        context.point_gaussian_geometry(profile=profile)
    except ValueError as exc:
        guard = str(exc)
    else:
        guard = None
    expected_guard = m["lens_k1"] != 0 or m["reduction"]["applied"] or m["thickness_mm"] != 0
    report = {
        "passed": np.array_equal(context.working_field, retained["field"])
        and delta <= tolerance
        and bool(guard) == expected_guard,
        "exact_prewarp_field_match": bool(np.array_equal(context.working_field, retained["field"])),
        "float64_operator_vs_float32_pipeline_max_level_error": delta,
        "source_columns": len(observation.pixels_xy),
        "operator_rows": len(observation.matrix),
        "input_sha256": m["input_sha256"],
        "working_field_sha256": m["working_field_sha256"],
        "working_shape": m["working_field_shape"],
        "channel_weights": m["channel_weights"],
        "lens_k1": m["lens_k1"],
        "reduced": m["reduction"]["applied"],
        "model_refusal": guard,
    }
    if case["kind"] == "fit":
        report["conditional_fit"] = fit_control(case, context, result)
        report["passed"] = report["passed"] and report["conditional_fit"]["passed"]
    report["passed"] = bool(report["passed"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="new local JSON report; existing paths refused"
    )
    args = parser.parse_args()
    # Validate destination before importing the numerical/trace code or rendering.
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("output must be a new file in an existing directory")
    plan = json.loads(PLAN.read_text())
    if plan["format"] != "pictures-to-cad-source-context-plan" or plan["version"] != 1:
        parser.error("unsupported plan")
    sys.path.insert(0, str(ROOT))
    before = hashes()
    rows = []
    for case in plan["cases"]:
        start = time.monotonic()
        try:
            row = {"name": case["name"], **evaluate(case, plan["replay_max_level_error"])}
        except Exception as exc:  # noqa: BLE001 - retain failures and execute every later case
            row = {"name": case["name"], "passed": False, "error": f"{type(exc).__name__}: {exc}"}
        rows.append({**row, "runtime_seconds": time.monotonic() - start})
    after = hashes()
    report = {
        "format": "pictures-to-cad-source-context-replay",
        "version": 1,
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "cases": rows,
        "passed": before == after and all(r["passed"] for r in rows),
    }
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    with args.output.open("x") as output:
        output.write(encoded)
    print(encoded, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
