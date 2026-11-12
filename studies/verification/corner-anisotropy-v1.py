#!/usr/bin/env python3
"""Independent conditional Gaussian corner study; no production renderer as truth.

Execution requires --output NEW_JSON. The known infinite corner is x <= g(y):
g(y)=sqrt(r*r-y*y) on |y|<=r*sin(h), else (r-|y|*sin(h))/cos(h).
The source probability integrates the conditional X CDF over standardized Y.
Finite standardized tails have an analytic omitted-probability bound; GL order
agreement is a numerical audit, not a certified quadrature enclosure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/corner-anisotropy-v1.json"
ERFC = np.frompyfunc(math.erfc, 1, 1)
_LEGENDRE: dict[int, tuple[np.ndarray, np.ndarray]] = {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(fitting: Any) -> dict[str, str]:
    paths = {
        "runner": Path(__file__).resolve(),
        "plan": PLAN,
        "fitting": Path(fitting.__file__).resolve(),
        "sheet": ROOT / "backend/sheet.py",
        "tone": ROOT / "backend/tone.py",
        "requirements_lock": ROOT / "uv.lock",
    }
    return {name: sha256(path) for name, path in paths.items()}


def cdf(z: np.ndarray) -> np.ndarray:
    return 0.5 * ERFC(-np.asarray(z) / math.sqrt(2.0)).astype(np.float64)


def boundary_x(y: np.ndarray, radius: float, half_sweep: float) -> np.ndarray:
    s, c = math.sin(half_sweep), math.cos(half_sweep)
    y = np.asarray(y, dtype=np.float64)
    arc = np.sqrt(np.maximum(0.0, radius * radius - y * y))
    tangent = (radius - np.abs(y) * s) / c
    return np.where(np.abs(y) <= radius * s, arc, tangent)


def corner_probability(
    points: np.ndarray,
    radius: float,
    sweep: float,
    covariance: np.ndarray,
    *,
    order: int = 16,
    limit: float = 12.0,
    panel_width: float = 0.5,
) -> np.ndarray:
    """Independent raw-point probability in canonical coordinates, centre=(0,0).

    Input covariance is SPD in squared coordinate units. The uncomputed Y tails
    contribute at most erfc(limit/sqrt(2)), since the conditional CDF is in [0,1].
    """
    points = np.atleast_2d(np.asarray(points, dtype=np.float64))
    covariance = np.asarray(covariance, dtype=np.float64)
    sigma_y = math.sqrt(float(covariance[1, 1]))
    conditional_sigma = math.sqrt(float(np.linalg.det(covariance) / covariance[1, 1]))
    conditional_slope = float(covariance[0, 1] / sigma_y)
    if order not in _LEGENDRE:
        _LEGENDRE[order] = np.polynomial.legendre.leggauss(order)
    nodes, weights = _LEGENDRE[order]
    grid = np.linspace(-limit, limit, math.ceil(2 * limit / panel_width) + 1)
    tangent_y = radius * math.sin(sweep / 2)
    cuts = np.clip(
        (np.array([-tangent_y, tangent_y])[None] - points[:, 1, None]) / sigma_y,
        -limit,
        limit,
    )
    bounds = np.sort(
        np.concatenate([np.broadcast_to(grid, (len(points), len(grid))), cuts], axis=1),
        axis=1,
    )
    a, b = bounds[:, :-1, None], bounds[:, 1:, None]
    t = (a + b) / 2 + (b - a) * nodes / 2
    weight = (b - a) * weights / 2
    y = points[:, 1, None, None] + sigma_y * t
    gx = boundary_x(y, radius, sweep / 2)
    z = (gx - points[:, 0, None, None] - conditional_slope * t) / conditional_sigma
    density = np.exp(-0.5 * t * t) / math.sqrt(2 * math.pi)
    return np.sum(cdf(z) * density * weight, axis=(1, 2))


def half_level_points(case: dict[str, Any], oracle: dict[str, Any]) -> np.ndarray:
    radius = float(case["radius"])
    sweep = math.radians(case["sweep_degrees"])
    covariance = np.array(case["covariance"], dtype=np.float64)
    sy = math.sqrt(float(covariance[1, 1]))
    tangent_y = radius * math.sin(sweep / 2)
    if radius:
        arc_y = radius * np.sin(np.linspace(-sweep / 2, sweep / 2, oracle["arc_y_samples"]))
    else:
        arc_y = np.linspace(-2 * sy, 2 * sy, oracle["arc_y_samples"])
    extra = sy * np.linspace(0.5, oracle["line_extent_sigma_y"], oracle["line_samples_per_side"])
    ys = np.unique(np.r_[arc_y, -tangent_y - extra, tangent_y + extra])
    boundary = boundary_x(ys, radius, sweep / 2)
    reach = 16 * math.sqrt(float(covariance[0, 0]))
    lo, hi = boundary - reach, boundary + reach

    def evaluate(xs: np.ndarray) -> np.ndarray:
        return corner_probability(
            np.column_stack([xs, ys]),
            radius,
            sweep,
            covariance,
            order=oracle["orders"][0],
            limit=oracle["standardized_y_limit"],
            panel_width=oracle["maximum_panel_width"],
        )

    if not ((evaluate(lo) > 0.5).all() and (evaluate(hi) < 0.5).all()):
        raise ArithmeticError("Declared finite x brackets do not enclose every half-level crossing")
    for _ in range(oracle["bisection_iterations"]):
        mid = (lo + hi) / 2
        inside = evaluate(mid) > 0.5
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    return np.column_stack([(lo + hi) / 2, ys])


def geometry(case: dict[str, Any]) -> dict[str, Any]:
    radius = float(case["radius"])
    half = math.radians(case["sweep_degrees"]) / 2
    turn = math.radians(case["rotation_degrees"])
    rotation = np.array([[math.cos(turn), -math.sin(turn)], [math.sin(turn), math.cos(turn)]])
    covariance = np.array(case["covariance"], dtype=np.float64)
    c, s = math.cos(half), math.sin(half)
    apex = np.array([radius / c, 0.0])
    tangent_points = (np.array([radius * c, -radius * s]), np.array([radius * c, radius * s]))
    directions = (np.array([s, c]), np.array([-s, c]))
    inward = (np.array([-c, s]), np.array([-c, -s]))
    return {
        "rotation": rotation,
        "apex": apex,
        "v": rotation @ np.array([-1 / c, 0.0]),
        "lines": tuple((rotation @ p, rotation @ d) for p, d in zip(tangent_points, directions)),
        "inward": tuple(rotation @ n for n in inward),
        "covariance": rotation @ covariance @ rotation.T,
        "sigma": float(np.linalg.det(covariance) ** 0.25),
    }


def clean(value: Any, *, path: str = "", nonfinite: list[str] | None = None) -> Any:
    if nonfinite is None:
        nonfinite = []
    if isinstance(value, dict):
        return {str(k): clean(v, path=f"{path}.{k}", nonfinite=nonfinite) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v, path=f"{path}[{i}]", nonfinite=nonfinite) for i, v in enumerate(value)]
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            nonfinite.append(path)
            return None
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def evaluate_case(
    case: dict[str, Any], plan: dict[str, Any], fitting: Any, models: tuple[str, ...]
) -> dict[str, Any]:
    started = time.perf_counter()
    points = half_level_points(case, plan["oracle"])
    geo = geometry(case)
    radius = float(case["radius"])
    sweep = math.radians(case["sweep_degrees"])
    covariance = np.array(case["covariance"], dtype=np.float64)
    means = [
        corner_probability(points, radius, sweep, covariance, order=order)
        for order in plan["oracle"]["orders"]
    ]
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: Any, **evidence: Any) -> None:
        checks.append({"name": name, "passed": bool(condition), **evidence})

    delta = float(np.max(np.abs(means[0] - means[1])))
    half_error = float(np.max(np.abs(means[1] - 0.5)))
    check(
        "independent_gl16_gl32",
        delta <= plan["criteria"]["quadrature_order_delta"],
        maximum_delta=delta,
    )
    check(
        "independent_half_level",
        half_error <= plan["criteria"]["half_level_error"],
        maximum_error=half_error,
    )
    global_points = points @ geo["rotation"].T
    fits: dict[str, Any] = {}
    start_radius = max(radius, 0.5 * geo["sigma"])
    for model in models:
        kwargs = {} if model == "scalar" else {"covariance": geo["covariance"]}
        lane: dict[str, Any] = {}
        try:
            at_truth = fitting.corner_level(
                global_points,
                [0.0, 0.0],
                radius,
                math.radians(case["rotation_degrees"]) - sweep / 2,
                sweep,
                geo["sigma"],
                **kwargs,
            )
            lane["model_level_error_at_true_geometry"] = float(np.max(np.abs(at_truth - 0.5)))
            result = fitting._exact_fillet(
                global_points,
                geo["lines"],
                geo["v"],
                geo["inward"],
                start_radius,
                geo["sigma"],
                0.0,
                1.0,
                **kwargs,
            )
            lane["returned_none"] = result is None
            if result is not None:
                r, sd, rms, max_abs, bound = result
                centre = geo["apex"] + r * np.array([-1 / math.cos(sweep / 2), 0.0])
                independent_at_fit = corner_probability(
                    points - centre, r, sweep, covariance, order=plan["oracle"]["orders"][1]
                )
                lane.update(
                    radius=r,
                    radius_error=r - radius,
                    radius_sd=sd,
                    normal_rms=rms,
                    normal_max_abs=max_abs,
                    sharp_bound=bound,
                    centre_error=float(np.linalg.norm(centre)),
                    independent_level_error_at_fitted_geometry=float(
                        np.max(np.abs(independent_at_fit - 0.5))
                    ),
                )
            if model == "scalar" and np.array_equal(covariance, np.eye(2) * covariance[0, 0]):
                error = None if result is None else abs(result[0] - radius)
                check(
                    "isotropic_scalar_radius",
                    error is not None
                    and error <= plan["criteria"]["isotropic_scalar_radius_error"],
                    error=error,
                )
            if model == "covariance" and case["id"] in plan["criteria"]["covariance_radius_cases"]:
                error = None if result is None else abs(result[0] - radius)
                check(
                    "covariance_known_radius",
                    error is not None
                    and error <= plan["criteria"]["covariance_resolved_radius_error"],
                    error=error,
                )
        except Exception as exc:  # noqa: BLE001 - retain every declared lane's failure.
            lane = {"execution_failure": {"type": type(exc).__name__, "message": str(exc)}}
            check(f"{model}_execution", False)
        nonfinite: list[str] = []
        fits[model] = clean(lane, nonfinite=nonfinite)
        fits[model]["nonfinite_fields"] = nonfinite
    return {
        "id": case["id"],
        "status": "passed" if all(c["passed"] for c in checks) else "failed",
        "input": case,
        "sigma_scalar": geo["sigma"],
        "start_radius": start_radius,
        "point_count": len(points),
        "points_canonical": points.tolist(),
        "tangent_apex_canonical": geo["apex"].tolist(),
        "oracle": {
            "order_delta": delta,
            "half_level_error": half_error,
            "omitted_y_probability_bound": math.erfc(
                plan["oracle"]["standardized_y_limit"] / math.sqrt(2)
            ),
        },
        "fits": fits,
        "checks": checks,
        "runtime_seconds": time.perf_counter() - started,
    }


def run_study(fitting: Any, *, model: str = "both") -> dict[str, Any]:
    """Explicit callable entry point for source-pinned baseline and failure audits."""
    plan = json.loads(PLAN.read_text())
    models = ("scalar", "covariance") if model == "both" else (model,)
    before = source_hashes(fitting)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for case in plan["cases"]:
        try:
            rows.append(evaluate_case(case, plan, fitting, models))
        except Exception as exc:  # noqa: BLE001 - later predeclared cases still execute.
            rows.append(
                {
                    "id": case["id"],
                    "input": case,
                    "status": "execution_failure",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            )
    after = source_hashes(fitting)
    checks = [check for row in rows for check in row.get("checks", [])]
    return {
        "format": "pictures-to-cad-corner-anisotropy-result",
        "version": 1,
        "scope": plan["scope"],
        "model": model,
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "assumptions": [
            "Known infinite convex tangent/arc corner, SPD Gaussian covariance, working-pixel point observations.",
            "Oracle uses conditional scalar integration, independent of production angular radial integration.",
            "Known true radius is the declared numerical seed except sharp/small radii seeded at half scalar sigma.",
            "GL16/32 convergence and floating probability comparisons are engineering evidence, not rigorous enclosures.",
            "Complemented materials have identical half-level points; no polarity-specific intensity fitting is performed.",
            "Line refitting, segmentation, finite boundaries, sampling, camera response and physical calibration are excluded.",
            "Returned radius_sd and sharp_bound are production conditional model diagnostics, not oracle-certified uncertainty.",
        ],
        "summary": {
            "cases": len(rows),
            "checks": len(checks),
            "failed_checks": sum(not c["passed"] for c in checks),
            "execution_failures": sum(
                r["status"] == "execution_failure"
                or any("execution_failure" in f for f in r.get("fits", {}).values())
                for r in rows
            ),
            "all_passed": before == after and all(r["status"] == "passed" for r in rows),
        },
        "cases": rows,
        "runtime_seconds": time.perf_counter() - started,
    }


def fresh_output(value: str) -> Path:
    path = Path(value)
    if path.suffix.lower() != ".json":
        raise ValueError("--output must name a .json file")
    if path.exists() or path.is_symlink():
        raise ValueError("--output must not exist (including symlinks)")
    if not path.parent.is_dir():
        raise ValueError("--output parent directory must already exist")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="new JSON file in an existing directory")
    parser.add_argument("--model", choices=("scalar", "covariance", "both"), default="both")
    args = parser.parse_args(argv)
    try:
        output = fresh_output(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    sys.path.insert(0, str(ROOT))
    from backend import fitting

    report = run_study(fitting, model=args.model)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    sys.stdout.write(encoded)
    return 0 if report["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
