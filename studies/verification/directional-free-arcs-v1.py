"""Conditional developer free-arc model comparison; not a production/raw API.

The generator is a conditional-area integral. The finite comparator reuses the
separate research lineage's private radial-flux kernel at continuous rectified
points, H=I, and rectified covariance. No integer pixels or source samples are
invented. All local fit outcomes and material-mismatch controls are retained.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FORWARD = HERE / "finite-shape-flux-v1.py"
PLAN_PATH = ROOT / "studies/directional-free-arcs-v1.json"
ORACLE_PATH = HERE / "curve-blur-frames-v1.py"
ORIGINAL_FORWARD_SHA256 = "07e0a2bb0d03b7e4f12f4a9b0675b3f7598d54587d746c07c502ea83623d29d8"
VENDORED_FORWARD_SHA256 = "e6c8962a896ab60f4e0e335f1d17ed5694c85597dc7fff58565b3e770d4d7b00"
PLAN_SHA256 = "ab666455689d2e915674eb775b72c991bb305188c0354e987f9ed91fe3f1c600"
ORACLE_SHA256 = "86b89e6f5b5ef09ee43f575c108923170ab7c97ea4fbd190246385ce91814625"
MULT = [-12, -8, -4, -2, -1, 0, 1, 2, 4, 8, 12]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def hashes():
    paths = [
        Path(__file__),
        PLAN_PATH,
        FORWARD,
        ROOT / "backend/__init__.py",
        ROOT / "backend/fitting.py",
        ROOT / "backend/circular_joins.py",
        ROOT / "backend/sheet.py",
        ROOT / "backend/tone.py",
        ORACLE_PATH,
        ROOT / "uv.lock",
    ]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def source(case):
    radius, covariance = case["radius"], np.array(case["covariance"], float)
    core, chord = case.get("capsule_core"), case.get("chord")
    anchor = np.array([core or 0.0, 0.0])
    level = case.get("level", 0.5)

    def probability(q, order):
        if core is not None:
            return oracle.finite_probability("capsule", radius, core, q, covariance, order, MULT)
        return oracle.disk_slice_probability(radius, q, covariance, order, MULT, chord=chord)

    center_mass = probability(anchor, 64)
    if center_mass <= level:
        return {"available": False, "center_mass": center_mass, "level": level}
    degrees = np.linspace(
        case["angle"] - case["sweep"] / 2,
        case["angle"] + case["sweep"] / 2,
        case.get("points", PLAN["settings"]["points"]),
    )
    directions = np.column_stack([np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees))])
    points = []
    for normal in directions:
        lo, hi = 0.0, radius + 12 * math.sqrt(np.linalg.eigvalsh(covariance)[-1])
        if probability(anchor + hi * normal, 64) >= level:
            raise ArithmeticError("unavailable declared root bracket")
        for _ in range(PLAN["settings"]["root_iterations"]):
            middle = (lo + hi) / 2
            if probability(anchor + middle * normal, 32) > level:
                lo = middle
            else:
                hi = middle
        points.append(anchor + (lo + hi) / 2 * normal)
    points = np.array(points)
    low = np.array([probability(p, 32) for p in points])
    high = np.array([probability(p, 64) for p in points])
    delta = np.zeros(len(points))
    if "perturbation" in case:
        delta = np.random.default_rng(case["seed"]).uniform(
            -case["perturbation"], case["perturbation"], len(points)
        )
        points = points + delta[:, None] * directions
    turn = oracle.rotation(case.get("rotation", 0))
    transported = turn @ covariance @ turn.T
    asymmetry = float(np.max(np.abs(transported - transported.T)))
    symmetry_guard = 64 * np.finfo(float).eps * float(np.max(np.abs(transported)))
    if asymmetry > symmetry_guard:
        raise ArithmeticError("rotation produced more than roundoff-scale covariance asymmetry")
    # The exact transported covariance is symmetric. Canonicalize its float
    # representation for the frozen kernel's exact-symmetry input contract.
    # This is neither a covariance estimate nor an average of local PSFs.
    symmetric = (transported + transported.T) / 2
    return {
        "available": True,
        "points": points @ turn.T,
        "truth_center": anchor @ turn.T,
        "covariance": symmetric,
        "raw_rotated_covariance": transported.tolist(),
        "canonical_rotated_covariance": symmetric.tolist(),
        "covariance_rotation_asymmetry": asymmetry,
        "covariance_symmetry_guard": symmetry_guard,
        "covariance_maximum_representation_change": float(np.max(np.abs(symmetric - transported))),
        "covariance_symmetrization": "Arithmetic-scale Q Sigma Q^T representation only",
        "center_mass": center_mass,
        "order_delta": float(np.max(np.abs(high - low))),
        "level_residual": float(np.max(np.abs(high - level))),
        "point_perturbations": delta.tolist(),
    }


def flux(points, params, covariance):
    cx, cy, radius = params
    curves, h, inverse, _, reflected = finite._geometry(
        [[("circle", (cx, cy), radius)]], np.eye(3), covariance
    )
    if reflected:
        raise AssertionError("identity chart cannot reflect")
    values, errors, count = [], [], 0
    for point in points:
        value, status, error, _, used, _ = finite._one(
            point, curves, h, inverse, PLAN["settings"]["flux_tolerance"], 4096, 2_000_000
        )
        if status != "resolved":
            raise ArithmeticError(f"finite private kernel unresolved: {status}")
        values.append(value)
        errors.append(error)
        count += used
    return np.array(values), max(errors), count


def flux_derivative(points, params, covariance, order=1024):
    # Reynolds derivative of disk mass: R integral density(q-C-Ru)*(u_x,u_y,1)dtheta.
    theta = np.arange(order) * (2 * math.pi / order)
    u = np.column_stack([np.cos(theta), np.sin(theta)])
    residual = points[:, None, :] - np.array(params[:2]) - params[2] * u
    exponent = np.einsum("nki,ij,nkj->nk", residual, np.linalg.inv(covariance), residual)
    density = np.exp(-exponent / 2) / (2 * math.pi * math.sqrt(np.linalg.det(covariance)))
    return params[2] * (2 * math.pi / order) * density @ np.column_stack([u, np.ones(order)])


def asymptotic(points, params, covariance, third):
    delta = points - params[:2]
    rho = np.linalg.norm(delta, axis=1)
    n = delta / np.maximum(rho[:, None], 1e-100)
    t = np.column_stack([-n[:, 1], n[:, 0]])
    a = np.einsum("ni,ij,nj->n", n, covariance, n)
    b = np.einsum("ni,ij,nj->n", t, covariance, t)
    c = np.einsum("ni,ij,nj->n", n, covariance, t)
    v = np.linalg.det(covariance) / a
    shift = v / (2 * params[2])
    if third:
        shift += v * v * (3 / 8 - b / (6 * a) + 17 * c * c / (12 * a * a)) / params[2] ** 3
    return rho - params[2] + shift


def fit(points, covariance, start, radius, method):
    evaluations, forward_evaluations = 0, 0
    max_error = 0.0

    def evaluate(p, jac=False):
        nonlocal evaluations, forward_evaluations, max_error
        if evaluations >= PLAN["settings"]["evaluations"]:
            raise TimeoutError("declared fit evaluation cap")
        evaluations += 1
        if method == "finite":
            value, error, count = flux(points, p, covariance)
            forward_evaluations += count
            max_error = max(max_error, error)
            return value - 0.5, flux_derivative(points, p, covariance) if jac else None
        value = asymptotic(points, p, covariance, method == "third")
        if not jac:
            return value, None
        step = 1e-5 * max(1.0, radius)
        matrix = np.column_stack(
            [
                (
                    asymptotic(points, p + np.eye(3)[j] * step, covariance, method == "third")
                    - asymptotic(points, p - np.eye(3)[j] * step, covariance, method == "third")
                )
                / (2 * step)
                for j in range(3)
            ]
        )
        return value, matrix

    p = np.array(start)
    lower = np.r_[start[:2] - radius, 0.1 * radius]
    upper = np.r_[start[:2] + radius, 3 * radius]
    history, reason = [], "iteration_limit"
    for iteration in range(PLAN["settings"]["iterations"]):
        residual, jac = evaluate(p, True)
        cost = float(residual @ residual)
        history.append({"iteration": iteration, "cost": cost, "parameters": p.tolist()})
        if cost < 1e-23:
            reason = "numerical_zero"
            break
        step, _, _, _ = np.linalg.lstsq(jac, -residual, rcond=1e-12)
        length = np.linalg.norm(step)
        if length > radius:
            step *= radius / length
        accepted = False
        for power in range(16):
            trial = np.clip(p + step * 2.0 ** (-power), lower, upper)
            r_trial, _ = evaluate(trial)
            if r_trial @ r_trial < cost:
                accepted = True
                movement = np.linalg.norm(trial - p)
                p = trial
                break
        if not accepted:
            reason = "no_strict_local_decrease"
            break
        if movement < 1e-10:
            reason = "small_parameter_step"
            break
    residual, jac = evaluate(p, True)
    _, singular, vt = np.linalg.svd(jac, full_matrices=False)
    values, error, _ = flux(points, p, covariance)
    derivative = flux_derivative(points, p, covariance)
    grad_norm = np.linalg.norm(derivative[:, :2], axis=1)
    normal_residual = (values - 0.5) / np.maximum(grad_norm, 1e-100)
    result = {
        "parameters": p.tolist(),
        "cost": float(residual @ residual),
        "reason": reason,
        "iterations": len(history),
        "evaluations": evaluations,
        "forward_evaluations": forward_evaluations,
        "forward_evaluations_scope": "Fit-objective calls only; final residual, derivative-check and alternative diagnostics are excluded.",
        "maximum_forward_error_estimate": max_error,
        "final_forward_error_estimate": error,
        "singular_values": singular.tolist(),
        "condition": float(singular[0] / singular[-1]),
        "rank": int(np.sum(singular > 1e-12 * singular[0])),
        "history": history,
        "finite_disk_level_rms": float(np.sqrt(np.mean((values - 0.5) ** 2))),
        "finite_disk_normalized_residual_max": float(np.max(np.abs(normal_residual))),
        "derivative_order_delta": float(
            np.max(np.abs(derivative - flux_derivative(points, p, covariance, 512)))
        ),
    }
    if method == "finite":
        selected = points[[0, len(points) // 2, -1]]
        analytic = flux_derivative(selected, p, covariance)
        derivative_checks = []
        for fraction in (1e-4, 1e-5):
            delta = fraction * radius
            numerical = []
            for axis in np.eye(3):
                high, _, _ = flux(selected, p + delta * axis, covariance)
                low, _, _ = flux(selected, p - delta * axis, covariance)
                numerical.append((high - low) / (2 * delta))
            derivative_checks.append(
                {
                    "parameter_step": delta,
                    "max_absolute_difference": float(
                        np.max(np.abs(np.column_stack(numerical) - analytic))
                    ),
                }
            )
        result["derivative_central_difference_checks"] = derivative_checks
        alternatives = []
        for sign in (-1, 1):
            trial = p + sign * 0.1 * vt[-1]
            value, _, _ = flux(points, trial, covariance)
            alternatives.append(
                {
                    "parameters": trial.tolist(),
                    "parameter_distance": 0.1,
                    "maximum_level_change": float(np.max(np.abs(value - values))),
                    "maximum_linear_normal_change": float(
                        np.max(np.abs(value - values) / np.maximum(grad_norm, 1e-100))
                    ),
                }
            )
        result["least_sensitive_alternatives"] = alternatives
    return result


def evaluate_case(case):
    row = {"input": case}
    generated = globals()["source"](case)
    row["source"] = {
        k: v for k, v in generated.items() if k not in {"points", "truth_center", "covariance"}
    }
    if not generated["available"]:
        row["status"] = "no_level_set"
        return row
    points, covariance, truth = (
        generated["points"],
        generated["covariance"],
        generated["truth_center"],
    )
    row["points"] = points.tolist()
    cx, cy, r, rms, worst = fitting.fit_circle(points)
    baseline = np.array(
        [cx, cy, fitting.blur_corrected_radius(r, np.linalg.det(covariance) ** 0.25)]
    )
    row["observed_circle"] = {"parameters": [cx, cy, r], "rms": rms, "maximum_residual": worst}
    row["current_scalar"] = {
        "parameters": baseline.tolist(),
        "radius_error": float(baseline[2] - case["radius"]),
        "center_error": float(np.linalg.norm(baseline[:2] - truth)),
    }
    row["fits"] = {}
    for method in ("leading", "finite", "third"):
        try:
            result = fit(points, covariance, baseline, case["radius"], method)
            p = np.array(result["parameters"])
            result["radius_error"] = float(p[2] - case["radius"])
            result["center_error"] = float(np.linalg.norm(p[:2] - truth))
            if method == "finite" and case["lane"] == "matched_disk":
                result["matched_recovery_passed"] = (
                    max(abs(result["radius_error"]), result["center_error"])
                    <= PLAN["settings"]["matched_geometry_target_pixels"]
                )
            row["fits"][method] = result
        except Exception as exc:  # noqa: BLE001 - retain every predeclared outcome
            row["fits"][method] = {
                "execution_failure": {"type": type(exc).__name__, "message": str(exc)}
            }
    row["status"] = "retained"
    return row


def run_study():
    global PLAN, fitting, oracle, finite
    before = hashes()
    assert before[str(PLAN_PATH.relative_to(ROOT))] == PLAN_SHA256, "frozen original plan changed"
    assert before[str(ORACLE_PATH.relative_to(ROOT))] == ORACLE_SHA256, (
        "independent source oracle changed"
    )
    assert before[str(FORWARD.relative_to(ROOT))] == VENDORED_FORWARD_SHA256, (
        "vendored forward changed"
    )
    restored = FORWARD.read_bytes().replace(
        b"from backend.fitting import arc_geometry\n", b"from .fitting import arc_geometry\n"
    )
    assert hashlib.sha256(restored).hexdigest() == ORIGINAL_FORWARD_SHA256, (
        "vendor differs beyond import"
    )
    PLAN = json.loads(PLAN_PATH.read_text())
    sys.path.insert(0, str(ROOT))
    from backend import fitting

    oracle = load("directional_arc_area_oracle", ORACLE_PATH)
    finite = load("directional_arc_finite_flux", FORWARD)
    started = time.perf_counter()
    rows = []
    for case in PLAN["cases"]:
        row_start = time.perf_counter()
        try:
            row = evaluate_case(case)
        except Exception as exc:  # noqa: BLE001 - retain every predeclared outcome
            row = {
                "input": case,
                "status": "execution_failure",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        row["runtime_seconds"] = time.perf_counter() - row_start
        rows.append(row)
    after = hashes()
    matched = [
        row["fits"]["finite"]
        for row in rows
        if row["input"]["lane"] == "matched_disk" and "fits" in row and "finite" in row["fits"]
    ]
    failures = sum(row["status"] == "execution_failure" for row in rows) + sum(
        "execution_failure" in fit for row in rows for fit in row.get("fits", {}).values()
    )
    generated = [row["source"] for row in rows if row.get("source", {}).get("available")]
    oracle_failures = sum(
        source["order_delta"] > PLAN["settings"]["oracle_order_delta"] for source in generated
    )
    return {
        "format": "pictures-to-cad-directional-free-arcs-study",
        "version": 1,
        "scope": __doc__,
        "provenance": {
            "original_plan_frozen_before_first_ignored_execution": True,
            "original_ignored_plan_sha256": PLAN_SHA256,
            "tracked_plan_promoted_utc": "2026-11-12 20:49:08 UTC",
            "promotion_preceded_completed_ignored_comparison": True,
            "forward_origin": "backend/finite_shape.py in separate finite-shape research lineage at c9daa2a",
            "original_forward_sha256": ORIGINAL_FORWARD_SHA256,
            "vendored_forward_sha256": VENDORED_FORWARD_SHA256,
            "vendor_change": "Only relative fitting import changed to backend.fitting.arc_geometry.",
            "initial_ignored_rotation_failure": "Q Sigma Q^T float asymmetry of one ULP violated the old kernel's exact symmetry contract. Initial result is retained locally; the portable adapter records and symmetrizes only arithmetic-scale rotation asymmetry, without changing cases or recovery criteria.",
        },
        "limitations": [
            "The finite comparator assumes a whole disk, known stationary rectified Gaussian covariance and true half-level; a circular boundary span alone does not establish the material hypothesis.",
            "Continuous rectified queries use a private study kernel with identity homography. No integer-pixel raw-source API or measured raw optical PSF is invoked.",
            "Only stored centre/radius are compared. No closed-ring join, emitted CAD, image segmentation or physical geometry is accepted.",
            "Local bounded iterations retain stopping reasons and do not certify all minima, global identification or uncertainty.",
            "Probability divided by spatial gradient is a first-order normal residual diagnostic, not an exact closest-boundary distance.",
            "Quadrature-order and derivative agreement are numerical controls, not certified enclosures.",
        ],
        "plan": PLAN,
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "cases": rows,
        "runtime_seconds": time.perf_counter() - started,
        "summary": {
            "cases": len(rows),
            "execution_failures": failures,
            "oracle_generated_rows": len(generated),
            "oracle_order_delta_limit": PLAN["settings"]["oracle_order_delta"],
            "oracle_failed_rows": oracle_failures,
            "all_available_oracle_orders_passed": oracle_failures == 0,
            "matched_cases": len(matched),
            "matched_finite_recovery_passes": sum(
                fit.get("matched_recovery_passed", False) for fit in matched
            ),
            "all_matched_finite_recovered": len(matched) == 10
            and all(fit.get("matched_recovery_passed", False) for fit in matched),
        },
    }


def fresh_output(value):
    path = Path(value)
    if path.suffix != ".json" or not path.parent.is_dir() or path.exists() or path.is_symlink():
        raise ValueError("output must be a NEW .json path in an existing directory")
    return path


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, help="NEW JSON file; existing paths and symlinks refused"
    )
    args = parser.parse_args(argv)
    try:
        output = fresh_output(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    result = run_study()
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    with output.open("x") as stream:
        stream.write(encoded)
    print(encoded, end="")
    return (
        0
        if (
            result["source_unchanged"]
            and result["summary"]["execution_failures"] == 0
            and result["summary"]["all_available_oracle_orders_passed"]
            and result["summary"]["all_matched_finite_recovered"]
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
