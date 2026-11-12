"""Independently replay finite-shape Gaussian raw-point controls.

No production imports or analysis run before a required fresh --output path is
validated. Expectations use area integrals, not the production Green boundary
formula. Slice breakpoints target Gaussian tails and circle intersections with
conditional-y Gaussian locations, including giant-radius narrow boundary layers.
Quadrature-order agreement is a numerical cross-check, never a certified bound.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-shape-source-v1.json"
ERFC = np.frompyfunc(math.erfc, 1, 1)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    # Bind the evaluator and its local import closure, rather than unrelated new
    # backend research files that another team member may develop concurrently.
    implementation = (
        "backend/__init__.py",
        "backend/finite_shape.py",
        "backend/fitting.py",
        "backend/circular_joins.py",
        "backend/sheet.py",
        "backend/tone.py",
    )
    return {name: digest(ROOT / name) for name in implementation} | {
        str(RUNNER.relative_to(ROOT)): digest(RUNNER),
        str(PLAN.relative_to(ROOT)): digest(PLAN),
    }


def load_plan():
    plan = json.loads(PLAN.read_text())
    if plan.get("format") != "pictures-to-cad-finite-shape-source-plan" or plan.get("version") != 1:
        raise ValueError("unsupported independent finite-shape plan")
    cases = plan.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        raise ValueError("the small fixed plan needs 1-64 declared cases")
    names = [case["name"] for case in cases]
    if len(names) != len(set(names)):
        raise ValueError("plan case names must be unique")
    return plan


def normal_mass(low, high):
    """Stable normal interval mass, including positive and negative tails."""
    low, high = np.broadcast_arrays(np.asarray(low, float), np.asarray(high, float))
    root = math.sqrt(2)
    left = 0.5 * np.asarray(ERFC(-high / root), float)
    left -= 0.5 * np.asarray(ERFC(-low / root), float)
    right = 0.5 * np.asarray(ERFC(low / root), float)
    right -= 0.5 * np.asarray(ERFC(high / root), float)
    return np.where(low >= 0, right, left)


def _covariance(case):
    if "covariance" in case:
        return np.asarray(case["covariance"], float)
    return np.eye(2) * case.get("sigma", 1.0) ** 2


def _point(shape, x, y):
    return tuple(np.asarray(shape["center"], float) + [x, y])


def ring_for(shape):
    """Independent explicit canonical geometry; no fitter or join solver."""
    if shape["kind"] == "rectangle":
        (left, right), (bottom, top) = shape["bounds"]
        corners = [(left, bottom), (right, bottom), (right, top), (left, top)]
        return [("line", a, b) for a, b in zip(corners, corners[1:] + corners[:1])]
    radius = shape["radius"]
    if shape["kind"] == "disk":
        return [("circle", tuple(shape["center"]), radius)]
    if shape["kind"] != "disk_segment":
        raise ValueError("unsupported plan shape")
    chord = shape["chord"]
    height = math.sqrt((radius - chord) * (radius + chord))
    top, bottom = _point(shape, chord, height), _point(shape, chord, -height)
    return [("arc", top, _point(shape, -radius, 0), bottom), ("line", bottom, top)]


def rings_for(case):
    shape = case["shape"]
    rings = [ring_for(shape)]
    if "hole" in shape:
        rings.append(ring_for(shape["hole"]))
    if case.get("reverse"):
        rings = [
            [
                (segment[0], *reversed(segment[1:])) if segment[0] != "circle" else segment
                for segment in reversed(ring)
            ]
            for ring in rings
        ]
    shift = case.get("cyclic_shift", 0)
    if shift:
        rings = [ring[shift:] + ring[:shift] for ring in rings]
    return rings


def affine_pullback(point, homography, covariance):
    """An affine image of a Gaussian has this exact mathematical pullback."""
    h = np.asarray(homography, float)
    h = h / h[2, 2]
    if np.any(h[2, :2] != 0):
        raise ValueError("the slice oracle requires an affine map")
    inverse = np.linalg.inv(h[:2, :2])
    return inverse @ (point - h[:2, 2]), inverse @ covariance @ inverse.T


def _slice_cuts(shape, mean, covariance, multipliers):
    radius = shape["radius"]
    cx, cy = shape["center"]
    left = cx - radius
    right = cx + shape.get("chord", radius)
    sx = math.sqrt(covariance[0, 0])
    beta = covariance[1, 0] / covariance[0, 0]
    conditional = math.sqrt(covariance[1, 1] - covariance[1, 0] ** 2 / covariance[0, 0])
    cuts = [left, right, cx]
    for multiplier in multipliers:
        cuts.append(mean[0] + multiplier * sx)
        # Circle intersection with y=mu_y(x)+k*s_cond. This catches the much
        # narrower curvature layer at a giant circle's tangent point.
        intercept = mean[1] + beta * (cx - mean[0]) - cy + multiplier * conditional
        aa = 1 + beta * beta
        extent = radius * math.sqrt(aa)
        discriminant = (extent - abs(intercept)) * (extent + abs(intercept))
        if discriminant >= 0:
            root = math.sqrt(discriminant)
            cuts.extend(cx + (-beta * intercept + sign * root) / aa for sign in (-1, 1))
    return sorted({left, right, *(value for value in cuts if left < value < right)})


def slice_probability(shape, mean, covariance, order, multipliers):
    """Conditional-normal vertical slices, separately targeted in x and y.

    x=cx-R*cos(theta) removes the square-root endpoint. The production radial
    Green formula, its quadrature, arc decoder and coordinate covers are unused.
    """
    radius = shape["radius"]
    cx, cy = shape["center"]
    cuts = _slice_cuts(shape, mean, covariance, multipliers)
    angles = [math.acos(max(-1.0, min(1.0, (cx - x) / radius))) for x in cuts]
    nodes, weights = np.polynomial.legendre.leggauss(order)
    low, high = np.asarray(angles[:-1]), np.asarray(angles[1:])
    half = (high - low) / 2
    theta = (high + low)[:, None] / 2 + half[:, None] * nodes
    x = cx - radius * np.cos(theta)
    height = radius * np.sin(theta)
    variance = covariance[0, 0]
    conditional_mean = mean[1] + covariance[1, 0] / variance * (x - mean[0])
    conditional_sd = math.sqrt(covariance[1, 1] - covariance[1, 0] ** 2 / variance)
    mass = normal_mass(
        (cy - height - conditional_mean) / conditional_sd,
        (cy + height - conditional_mean) / conditional_sd,
    )
    density = np.exp(-0.5 * ((x - mean[0]) ** 2 / variance)) / math.sqrt(2 * math.pi * variance)
    terms = density * mass * radius * np.sin(theta) * half[:, None] * weights
    return math.fsum(terms.ravel()), len(angles) - 1


def rectangle_probability(shape, mean, covariance, order, multipliers):
    (left, right), (bottom, top) = shape["bounds"]
    sx, sy = math.sqrt(covariance[0, 0]), math.sqrt(covariance[1, 1])
    if covariance[0, 1] == covariance[1, 0] == 0:
        return float(normal_mass((left - mean[0]) / sx, (right - mean[0]) / sx)) * float(
            normal_mass((bottom - mean[1]) / sy, (top - mean[1]) / sy)
        ), 0
    cuts = sorted(
        {left, right, *(mean[0] + k * sx for k in multipliers if left < mean[0] + k * sx < right)}
    )
    nodes, weights = np.polynomial.legendre.leggauss(order)
    halves = np.diff(cuts) / 2
    x = (np.asarray(cuts[:-1]) + np.asarray(cuts[1:]))[:, None] / 2 + halves[:, None] * nodes
    conditional_mean = mean[1] + covariance[1, 0] / covariance[0, 0] * (x - mean[0])
    sd = math.sqrt(covariance[1, 1] - covariance[1, 0] ** 2 / covariance[0, 0])
    mass = normal_mass((bottom - conditional_mean) / sd, (top - conditional_mean) / sd)
    density = np.exp(-0.5 * ((x - mean[0]) / sx) ** 2) / (sx * math.sqrt(2 * math.pi))
    return math.fsum((mass * density * halves[:, None] * weights).ravel()), len(cuts) - 1


def area_probability(shape, point, homography, covariance, order):
    """Independent plane-area change of variables for moderate projective cases.

    The source disk slice is parameterized by theta and normalized height. The
    density is evaluated in RAW coordinates and includes |det DH|. A Gaussian
    is never pulled through a projective map as another Gaussian.
    """
    radius = shape["radius"]
    centre = np.asarray(shape["center"])
    theta_max = math.acos(-shape.get("chord", radius) / radius)
    nodes, weights = np.polynomial.legendre.leggauss(order)
    theta_edges, vertical_edges = np.linspace(0, theta_max, 9), np.linspace(-1, 1, 5)
    thalf, vhalf = np.diff(theta_edges) / 2, np.diff(vertical_edges) / 2
    theta = (theta_edges[:-1, None] + theta_edges[1:, None]) / 2 + thalf[:, None] * nodes
    vertical = (vertical_edges[:-1, None] + vertical_edges[1:, None]) / 2 + vhalf[:, None] * nodes
    tt, vv = theta.ravel()[:, None], vertical.ravel()[None, :]
    x = np.broadcast_to(centre[0] - radius * np.cos(tt), (tt.size, vv.size))
    y = centre[1] + radius * np.sin(tt) * vv
    homogeneous = np.stack([x, y, np.ones_like(x)], axis=-1)
    h = np.asarray(homography, float)
    h = h / np.max(np.abs(h))
    mapped = homogeneous @ h.T
    denominator = mapped[..., 2]
    raw = mapped[..., :2] / denominator[..., None]
    inverse = np.linalg.inv(covariance)
    delta = raw - point
    exponent = np.einsum("...i,ij,...j->...", delta, inverse, delta)
    density = np.exp(-exponent / 2) / (2 * math.pi * math.sqrt(np.linalg.det(covariance)))
    jacobian = abs(np.linalg.det(h)) / abs(denominator) ** 3
    plane_jacobian = radius**2 * np.sin(tt) ** 2
    tw = (thalf[:, None] * weights).ravel()
    vw = (vhalf[:, None] * weights).ravel()
    return math.fsum(
        (density * jacobian * plane_jacobian * tw[:, None] * vw[None, :]).ravel()
    ), tt.size * vv.size


def _shape_reference(shape, point, homography, covariance, order, settings, lane):
    if lane == "plane_area":
        value, count = area_probability(shape, point, homography, covariance, order)
    else:
        mean, pulled = affine_pullback(point, homography, covariance)
        if lane == "centered_disk":
            if not np.allclose(mean, shape["center"], rtol=0, atol=1e-12) or not np.array_equal(
                pulled, np.eye(2) * pulled[0, 0]
            ):
                raise ValueError("exact centered-disk oracle requires its declared symmetry")
            value, count = -math.expm1(-(shape["radius"] ** 2) / (2 * pulled[0, 0])), 0
        elif shape["kind"] == "rectangle":
            value, count = rectangle_probability(
                shape, mean, pulled, order, settings["tail_multipliers"]
            )
        else:
            value, count = slice_probability(
                shape, mean, pulled, order, settings["tail_multipliers"]
            )
    if "hole" in shape:
        hole, used = _shape_reference(
            shape["hole"], point, homography, covariance, order, settings, lane
        )
        value, count = value - hole, count + used
    return value, count


def reference_values(case, defaults, settings):
    homography = case.get("homography", defaults["homography"])
    covariance = _covariance(case)
    lane = case.get("oracle", "slice")
    orders = settings["area_orders"] if lane == "plane_area" else settings["slice_orders"]
    rows, counts = [], []
    for order in orders:
        result, used = [], []
        for point in np.asarray(case["pixels"], float) + 0.5:
            value, count = _shape_reference(
                case["shape"], point, homography, covariance, order, settings, lane
            )
            result.append(value)
            used.append(count)
        rows.append(result)
        counts.append(used)
    return {
        "method": lane,
        "orders": orders,
        "values": rows[-1],
        "previous_order_values": rows[0],
        "maximum_order_delta": max(abs(a - b) for a, b in zip(*rows)),
        "targeted_intervals_or_area_nodes": counts,
        "certified": False,
    }


def evaluate(case, plan, analyze):
    defaults, settings = plan["defaults"], plan["oracle"]
    kwargs = {key: case.get(key, value) for key, value in defaults.items()}
    kwargs["psf_covariance"] = _covariance(case)
    row = {"name": case["name"], "input": case, "execution": "executed", "checks": {}}
    expected = case.get("expected", "resolved")
    try:
        result = analyze(case["pixels"], rings_for(case), **kwargs)
    except ValueError as error:
        if expected != "refused":
            raise
        row.update(status="refused", refusal=f"ValueError: {error}", passed=True)
        row["checks"]["invalid_input_refused"] = True
        return row
    row["result"] = asdict(result)
    checks = row["checks"]
    checks["all_queries_retained"] = (
        len(result.probabilities) == len(case["pixels"]) == len(result.statuses)
    )
    checks["evaluation_budget_respected"] = 0 <= result.evaluations <= kwargs["max_evaluations"]
    checks["panel_budget_respected"] = (
        0 <= result.panels <= kwargs["max_panels"] * len(case["pixels"])
    )
    checks["no_formal_or_topology_claim"] = (
        result.topology_validated is False and result.quadrature_certified is False
    )
    if expected == "unresolved":
        checks["budget_keeps_unresolved_query"] = any(p is None for p in result.probabilities)
        row["status"] = "unresolved"
    elif expected == "refused":
        checks["invalid_input_refused"] = False
        row["status"] = "unexpected_acceptance"
    else:
        reference = reference_values(case, defaults, settings)
        row["reference"] = reference
        checks["independent_order_agreement"] = (
            reference["maximum_order_delta"] <= settings["reference_order_tolerance"]
        )
        checks["resolved_forward_targets"] = all(p is not None for p in result.probabilities)
        comparisons = [
            abs(p - q) if p is not None else None
            for p, q in zip(result.probabilities, reference["values"])
        ]
        row["absolute_differences"] = comparisons
        checks["independent_probability_agreement"] = all(
            difference is not None and difference <= settings["absolute_comparison_tolerance"]
            for difference in comparisons
        )
        row["status"] = "resolved" if checks["resolved_forward_targets"] else "unresolved"
    row["passed"] = all(checks.values())
    return row


def run(plan=None, analyze=None):
    started = time.perf_counter()
    before = source_hashes()
    plan = load_plan() if plan is None else plan
    setup_error = None
    if analyze is None:
        try:
            sys.path.insert(0, str(ROOT))
            module = importlib.import_module("backend.finite_shape")
            if Path(module.__file__).resolve() != ROOT / "backend/finite_shape.py":
                raise ValueError("finite-shape implementation loaded outside the selected source")
            analyze = module.finite_shape_probabilities
        except Exception as error:  # noqa: BLE001 - retain all declared rows on setup failure
            setup_error = f"{type(error).__name__}: {error}"
    rows = []
    for index, case in enumerate(plan["cases"]):
        try:
            if setup_error:
                raise RuntimeError(setup_error)
            row = evaluate(case, plan, analyze)
            # A nonserializable/nonfinite row is an execution failure, retained
            # here rather than causing the complete census to disappear at save.
            json.dumps(row, allow_nan=False)
        except Exception as error:  # noqa: BLE001 - one failure must not omit later cases
            row = {
                "name": case["name"],
                "input": case,
                "execution": "execution_failure",
                "error": f"{type(error).__name__}: {error}",
                "checks": {},
                "passed": False,
            }
        rows.append({"index": index, **row})
    after = source_hashes()
    unchanged = before == after
    failures = sum(not row["passed"] for row in rows)
    differences = [x for row in rows for x in row.get("absolute_differences", []) if x is not None]
    deltas = [row["reference"]["maximum_order_delta"] for row in rows if "reference" in row]
    return {
        "format": "pictures-to-cad-finite-shape-independent-oracle",
        "version": 1,
        "verification": "passed" if unchanged and not failures else "failed",
        "source_before": before,
        "source_after": after,
        "source_unchanged": unchanged,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "seconds": time.perf_counter() - started,
        },
        "summary": {
            "declared_rows": len(plan["cases"]),
            "retained_rows": len(rows),
            "failed_rows": failures,
            "execution_failures": sum(row["execution"] == "execution_failure" for row in rows),
            "checks": sum(len(row["checks"]) for row in rows),
            "maximum_probability_difference": max(differences, default=None),
            "maximum_reference_order_delta": max(deltas, default=None),
        },
        "rows": rows,
        "limits": [
            "The mathematical model is a supplied finite material, fixed lens-free homography, stationary raw Gaussian PSF and point detector. No camera calibration, optical adequacy or physical CAD acceptance is inferred.",
            "The reference uses separate conditional-normal slice/area integrals, targeted breakpoints, standard-library erfc and numerical quadrature. Order agreement is not a rigorous integration certificate.",
            "Nonidentity affine controls pull the Gaussian back exactly; projective controls integrate the RAW Gaussian times the projective area Jacobian instead of assuming a Gaussian plane field.",
            "Complete geometry, including off-sensor material, contributes before point sampling. No implicit sensor clipping, pixel-aperture averaging, response curve, wall, segmentation or downstream resampling is included.",
            "Expected work-limit and invalid-input outcomes remain in the report. Finite case agreement is not a convergence guarantee for arbitrary supplied curves.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new .json report; existing files and symlinks refused",
    )
    args = parser.parse_args(argv)
    output = args.output
    if output.exists() or output.is_symlink():
        parser.error("--output must be a fresh destination")
    if output.suffix.lower() != ".json":
        parser.error("--output must have a .json suffix")
    ancestor = output.parent
    while not ancestor.exists() and not ancestor.is_symlink():
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        parser.error("--output parent must be a directory or creatable beneath one")
    report = run()
    rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    except OSError as error:
        parser.error(f"cannot save fresh report: {error}")
    print(rendered, end="")
    return int(report["verification"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
