"""Replay conditional PSF covariance controls using independently rendered edges.

Required --output NEW_JSON must be fresh before imports/rendering/analysis.
All source means use stdlib erfc, never the production edge probability helper.
The optional finite-D reference uses the pinned independent positive area oracle.
No physical images, automatic calibration, or production trace is involved.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import platform
import sys
import time
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/psf-calibration-v1.json"
RUNNER = Path(__file__).resolve()
AREA_ORACLE = ROOT / "studies/verification/finite-shape-oracle-v1.py"
SOURCES = (
    "backend/__init__.py",
    "backend/psf_calibration.py",
    "backend/edge_spread.py",
    "backend/profile_observations.py",
    "backend/raw_source_fit.py",
    "backend/finite_shape.py",
    "backend/fitting.py",
    "backend/circular_joins.py",
    "backend/sheet.py",
    "backend/tone.py",
    "studies/verification/finite-shape-oracle-v1.py",
    "studies/psf-calibration-v1.json",
    "studies/verification/psf-calibration-v1.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def load_plan():
    plan = json.loads(PLAN.read_text())
    if plan.get("format") != "pictures-to-cad-psf-calibration-plan" or plan.get("version") != 1:
        raise ValueError("unsupported PSF study plan")
    names = [c["name"] for c in plan["cases"]]
    if not 1 <= len(names) <= 16 or len(set(names)) != len(names):
        raise ValueError("the fixed small plan needs 1..16 unique cases")
    return plan


def phi_cdf(value):
    return math.erfc(-float(value) / math.sqrt(2)) / 2


def normals(config):
    return [
        [math.cos(math.radians(a)), math.sin(math.radians(a))] for a in config["angles_degrees"]
    ]


def directional_variance(normal, matrix):
    x, y = normal
    return x * x * matrix[0][0] + 2 * x * y * matrix[0][1] + y * y * matrix[1][1]


def pixels(config):
    import numpy as np

    anchor = np.floor(config["anchor"]).astype(int)
    return anchor + np.array(
        [[x, y] for y in config["pixel_offsets"] for x in config["pixel_offsets"]], dtype=int
    )


def edge_means(config, normal, xy, *, order=None):
    """Independent stationary raw half-plane mean and optional detector averaging."""
    import numpy as np

    points = np.asarray(xy, float) + 0.5
    anchor = np.asarray(config["anchor"])
    normal = np.asarray(normal)
    sigma = math.sqrt(directional_variance(normal, config["covariance"]))
    source = config.get("source", "gaussian")

    def probability(at):
        z = ((at - anchor) @ normal - config["offset"]) / sigma
        if source == "mixture":
            return sum(
                weight * np.array([phi_cdf(v / math.sqrt(scale)) for v in z])
                for weight, scale in config["mixture"]
            )
        if source == "probit_response":
            z = config["response_a"] * z + config["response_b"]
        result = np.array([phi_cdf(v) for v in z])
        return result ** config["gamma"] if source == "gamma" else result

    if source == "aperture":
        nodes, weights = np.polynomial.legendre.leggauss(order)
        p = np.zeros(len(points))
        for i, x in enumerate(nodes):
            for j, y in enumerate(nodes):
                p += weights[i] * weights[j] / 4 * probability(points + [x / 2, y / 2])
    else:
        p = probability(points)
    low, high = config["levels"]
    return low + (high - low) * p


def source_second_moment(config):
    """Supplied optical/source PSF moment, before detector aperture or response."""
    import numpy as np

    scale = (
        sum(w * factor for w, factor in config["mixture"])
        if config.get("source") == "mixture"
        else 1.0
    )
    return np.asarray(config["covariance"], float) * scale


def norm_matrix_difference(first, second):
    if first is None or second is None:
        return None
    return math.sqrt(
        sum((float(a) - float(b)) ** 2 for ar, br in zip(first, second) for a, b in zip(ar, br))
    )


def fit_one(config, normal, xy, values, fit, noise_type, *, matrix=None, std=1.0):
    import numpy as np

    matrix = np.eye(len(xy)) if matrix is None else matrix
    noise = noise_type.factor(matrix, std)
    result = fit(
        xy,
        values,
        noise,
        sensor_shape=config["sensor_shape"],
        normal=normal,
        anchor=config["anchor"],
        offset_bounds=config["offset_bounds"],
        sigma_bounds=config["sigma_bounds"],
        grid_points=config["grid_points"],
        refinement_iterations=config["refinement_iterations"],
        max_basins=config["max_basins"],
        max_evaluations=config["max_evaluations"],
    )
    return result


def result_checks(result, config):
    return {
        "complete_grid_retained": len(result.grid)
        == len(result.grid_statuses)
        == config["grid_points"] ** 2,
        "work_caps_respected": result.evaluations <= config["max_evaluations"]
        and result.work <= 100_000_000,
        "no_global_certificate": not result.global_search_certified,
        "represented_candidate_available": result.best is not None,
    }


def finite_holdout(config, plan, covariance):
    import numpy as np

    if sha(AREA_ORACLE) != plan["finite_D"]["oracle_sha256"]:
        raise ValueError("independent finite-D oracle pin changed")
    spec = importlib.util.spec_from_file_location("psf_independent_area", AREA_ORACLE)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    from backend.finite_shape import finite_shape_probabilities

    d = plan["finite_D"]
    cx, cy = d["centre"]
    radius, fraction = d["radius"], d["fraction"]
    shape = {
        "kind": "disk_segment",
        "center": [0.0, 0.0],
        "radius": radius,
        "chord": radius * fraction,
    }
    transform = np.array([[1.0, 0.0, cx], [0.0, 1.0, cy], [0.0, 0.0, 1.0]])
    xy = np.asarray(d["pixels"], int)
    settings = {"tail_multipliers": d["tail_multipliers"]}
    components = config.get("mixture", [[1.0, 1.0]])
    references = []
    for order in d["oracle_orders"]:
        probabilities = []
        for point in xy + 0.5:
            probabilities.append(
                sum(
                    weight
                    * oracle._shape_reference(
                        shape,
                        point,
                        transform,
                        np.asarray(config["covariance"]) * scale,
                        order,
                        settings,
                        "slice",
                    )[0]
                    for weight, scale in components
                )
            )
        references.append(np.asarray(probabilities))
    top = np.array([cx + radius * fraction, cy + radius * math.sqrt(1 - fraction * fraction)])
    bottom = np.array([top[0], 2 * cy - top[1]])
    ring = [("arc", top, np.array([cx - radius, cy]), bottom), ("line", bottom, top)]
    prediction = finite_shape_probabilities(
        xy,
        [ring],
        sensor_shape=config["sensor_shape"],
        homography=np.eye(3),
        psf_covariance=covariance,
    )
    if any(v is None for v in prediction.probabilities):
        raise ValueError("finite-D model prediction was unresolved")
    contrast = abs(config["levels"][1] - config["levels"][0])
    return {
        "pixels_xy": xy.tolist(),
        "truth_probabilities": references[-1].tolist(),
        "model_probabilities": list(prediction.probabilities),
        "oracle_order_max_level_delta": float(np.max(np.abs(references[1] - references[0])))
        * contrast,
        "max_level_error": float(
            np.max(np.abs(np.asarray(prediction.probabilities) - references[-1]))
        )
        * contrast,
        "model_statuses": list(prediction.statuses),
        "quadrature_certified": False,
        "inverse_shape_recovery": False,
    }


def edge_case(case, config, plan, fit, noise_type, reconstruct, aggregate):
    import numpy as np

    xy = pixels(config)
    ns = normals(config)
    entries, variances, fits, checks = [], [], [], {}
    for index, n in enumerate(ns):
        order = case.get("aperture_orders", [None, None])
        values = edge_means(config, n, xy, order=order[-1])
        delta = 0.0
        if config.get("source") == "aperture":
            delta = float(np.max(np.abs(values - edge_means(config, n, xy, order=order[0]))))
            checks[f"aperture_order_{index}"] = delta <= case["oracle_max_level_delta"]
        result = fit_one(config, n, xy, values, fit, noise_type)
        fits.append(result)
        checks.update({f"edge_{index}_{k}": v for k, v in result_checks(result, config).items()})
        row = {
            "normal": n,
            "pixels_xy": xy.tolist(),
            "values": values.tolist(),
            "aperture_order_max_level_delta": delta,
            "fit": asdict(result),
        }
        source_sigma = math.sqrt(directional_variance(n, source_second_moment(config)))
        expected_sigma, expected_offset = source_sigma, config["offset"]
        if config.get("source") == "probit_response":
            expected_sigma /= config["response_a"]
            expected_offset -= config["response_b"] * expected_sigma
        if result.best is not None:
            variances.append(result.best.sigma**2)
            row["supplied_source_RMS_sigma"] = source_sigma
            row["conditional_expected_sigma"] = expected_sigma
            row["conditional_expected_offset"] = expected_offset
            row["sigma_error_to_conditional_target"] = abs(result.best.sigma - expected_sigma)
            row["offset_error_to_conditional_target"] = abs(result.best.offset - expected_offset)
            if case.get("matched") or case.get("alias_targets"):
                checks[f"edge_{index}_sigma_target"] = (
                    row["sigma_error_to_conditional_target"]
                    <= plan["matched_targets"]["sigma_error_px"]
                )
                checks[f"edge_{index}_offset_target"] = (
                    row["offset_error_to_conditional_target"]
                    <= plan["matched_targets"]["offset_error_px"]
                )
        entries.append(row)
    estimate = aggregate(ns, fits)
    covariance = estimate.reconstruction
    record = {
        "source": config.get("source"),
        "edges": entries,
        "covariance": asdict(covariance) if covariance else None,
        "fit_aggregation": asdict(estimate),
        "checks": checks,
    }
    checks["every_planned_edge_retained"] = len(estimate.edge_statuses) == len(ns)
    checks["unresolved_edges_never_silently_pooled"] = (
        estimate.all_edges_resolved or estimate.reconstruction is None
    )
    if case.get("matched") or case.get("alias_targets"):
        checks["matched_edges_resolved_before_pooling"] = estimate.all_edges_resolved
    if covariance is not None:
        checks["no_shape_or_physical_certificate"] = (
            not covariance.gaussian_model_validated and not covariance.physically_calibrated
        )
        record["supplied_source_second_moment"] = source_second_moment(config).tolist()
        record["covariance_error_to_supplied_source_second_moment"] = norm_matrix_difference(
            covariance.candidate, source_second_moment(config)
        )
        if case.get("matched") or case.get("alias_targets"):
            expected = np.asarray(config["covariance"])
            if config.get("source") == "probit_response":
                expected = expected / config["response_a"] ** 2
            record["conditional_covariance_target"] = expected.tolist()
            checks["identified_SPD_covariance_available"] = covariance.covariance is not None
            checks["conditional_covariance_target"] = (
                norm_matrix_difference(covariance.covariance, expected) is not None
                and norm_matrix_difference(covariance.covariance, expected)
                <= plan["matched_targets"]["covariance_frobenius_error_px2"]
            )
            if case.get("alias_targets"):
                checks["exact_response_hides_wrong_physical_covariance"] = (
                    record["covariance_error_to_supplied_source_second_moment"] > 0.1
                )
        if case.get("finite_D") and covariance.covariance is not None:
            record["finite_D_holdout"] = finite_holdout(config, plan, covariance.covariance)
            checks["independent_finite_D_order_agreement"] = (
                record["finite_D_holdout"]["oracle_order_max_level_delta"]
                <= plan["matched_targets"]["finite_D_oracle_order_delta"]
            )
            if case.get("matched"):
                checks["matched_finite_D_target"] = (
                    record["finite_D_holdout"]["max_level_error"]
                    <= plan["matched_targets"]["finite_D_max_level_error"]
                )
        if "fourth_direction" in case and covariance.covariance is not None:
            n = [
                math.cos(math.radians(case["fourth_direction"])),
                math.sin(math.radians(case["fourth_direction"])),
            ]
            truth = edge_means(config, n, xy)
            prediction_config = config | {"covariance": covariance.covariance}
            prediction = edge_means(prediction_config, n, xy)
            error = float(np.max(np.abs(prediction - truth)))
            record["heldout_fourth_direction"] = {"normal": n, "max_level_error": error}
            checks["matched_fourth_direction_target"] = (
                error <= plan["matched_targets"]["heldout_profile_max_level_error"]
            )
    if config.get("source") == "mixture":
        # A distinct exact-summary countercontrol: homogeneous mixture ESFs have
        # direction-independent standardized quartiles. These are not widths
        # exported from any incomplete Gaussian optimizer above.
        lo, hi = 0.0, 40.0
        for _ in range(120):
            mid = (lo + hi) / 2
            cdf = sum(w * phi_cdf(mid / math.sqrt(scale)) for w, scale in config["mixture"])
            if cdf < 0.75:
                lo = mid
            else:
                hi = mid
        scale_equivalent = ((lo + hi) / 2 / 0.6744897501960817) ** 2
        equivalent = np.asarray(config["covariance"]) * scale_equivalent
        spread = reconstruct(ns, [directional_variance(n, equivalent) for n in ns])
        record["independent_quartile_summary_countercontrol"] = {
            "gaussian_equivalent_covariance": asdict(spread),
            "supplied_mixture_second_moment": (
                np.asarray(config["covariance"]) * sum(w * scale for w, scale in config["mixture"])
            ).tolist(),
            "origin": "independent standardized mixture quartile; not pooled optimizer candidates",
        }
        checks["nonGaussian_quartiles_admit_SPD_quadratic_summary"] = spread.covariance is not None
        checks["summary_differs_from_supplied_source_second_moment"] = (
            norm_matrix_difference(
                spread.covariance,
                record["independent_quartile_summary_countercontrol"][
                    "supplied_mixture_second_moment"
                ],
            )
            > 0.1
        )
        record["quartile_model_finite_D_holdout"] = finite_holdout(config, plan, spread.covariance)
        checks["quartile_countercontrol_area_order_agreement"] = (
            record["quartile_model_finite_D_holdout"]["oracle_order_max_level_delta"]
            <= plan["matched_targets"]["finite_D_oracle_order_delta"]
        )
    return record


def fraction_solve(matrix, target):
    work = [list(row) + [value] for row, value in zip(matrix, target)]
    for column in range(3):
        pivot = next(i for i in range(column, 3) if work[i][column])
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [v / scale for v in work[column]]
        for i in range(3):
            if i != column:
                scale = work[i][column]
                work[i] = [a - scale * b for a, b in zip(work[i], work[column])]
    return [row[-1] for row in work]


def algebra_case(case, reconstruct, planner):
    import numpy as np

    kind, checks = case["kind"], {}
    if kind == "rectangle":
        ns, values = [[1.0, 0.0], [0.0, 1.0]], [2.25, 1.21]
        result = reconstruct(ns, values)
        aliases = [[[2.25, off], [off, 1.21]] for off in (-0.6, 0.6)]
        checks = {
            "rank_two": result.rank == 2,
            "no_identified_covariance": result.covariance is None,
            "one_missing_mode": len(result.nullspace) == 1,
            "two_distinct_SPD_truths_same_spreads": all(
                a[0][0] * a[1][1] > a[0][1] ** 2
                and all(abs(directional_variance(n, a) - v) < 1e-14 for n, v in zip(ns, values))
                for a in aliases
            ),
        }
        return {"result": asdict(result), "independent_aliases": aliases, "checks": checks}
    if kind == "nearparallel":
        c, d = Fraction(case["c"]), Fraction(case["d"])
        perturb = Fraction(case["centre_variance_perturbation"])
        values = [Fraction(2) + perturb, 2 * c * c + d * d / 2, 2 * c * c + d * d / 2]
        ns = [[1.0, 0.0], [float(c), float(d)], [float(c), -float(d)]]
        expected = [
            [float(Fraction(2) + perturb), 0.0],
            [0.0, float(Fraction(1, 2) - c * c / (d * d) * perturb)],
        ]
        result = reconstruct(ns, list(map(float, values)))
        checks = {
            "rank_three": result.rank == 3,
            "positive_spreads": all(v > 0 for v in values),
            "indefinite_unclipped": result.positive_definite is False and result.covariance is None,
            "independent_closed_form": norm_matrix_difference(result.candidate, expected) < 1e-7,
            "ill_condition_visible": result.condition > 10000,
        }
        return {
            "result": asdict(result),
            "independent_expected": expected,
            "exact_observed_variances": [str(v) for v in values],
            "checks": checks,
        }
    if kind == "weighted":
        ns = [
            [Fraction(1), Fraction(0)],
            [Fraction(0), Fraction(1)],
            [Fraction(3, 5), Fraction(4, 5)],
            [Fraction(4, 5), Fraction(3, 5)],
        ]
        truth = [[Fraction(9, 4), Fraction(3, 5)], [Fraction(3, 5), Fraction(121, 100)]]
        values = [
            x * x * truth[0][0] + 2 * x * y * truth[0][1] + y * y * truth[1][1] for x, y in ns
        ]
        values[2] += Fraction(3, 1000)
        values[3] -= Fraction(5, 1000)
        std = list(map(Fraction, ["0.2", "0.5", "0.3", "0.7"]))
        rows = [[x * x, 2 * x * y, y * y] for x, y in ns]
        gram = [
            [sum(row[a] * row[b] / s**2 for row, s in zip(rows, std)) for b in range(3)]
            for a in range(3)
        ]
        target = [sum(row[a] * v / s**2 for row, v, s in zip(rows, values, std)) for a in range(3)]
        beta = fraction_solve(gram, target)
        expected = [[float(beta[0]), float(beta[1])], [float(beta[1]), float(beta[2])]]
        results = []
        for scale in case["unit_scales"]:
            result = reconstruct(
                np.asarray(ns, float),
                np.asarray(values, float),
                variance_std=np.asarray(std, float) * scale,
            )
            results.append(asdict(result))
            checks[f"exact_Fraction_WLS_units_{scale}"] = (
                norm_matrix_difference(result.candidate, expected) < 1e-11
            )
        return {
            "results": results,
            "exact_coefficients_xx_xy_yy": list(map(str, beta)),
            "checks": checks,
        }
    if kind == "planner":
        result = planner([[1.0, 0.0], [0.0, 1.0]])
        n = [[math.cos(a), math.sin(a)] for a in (0, math.pi / 3, 2 * math.pi / 3)]
        balanced = reconstruct(n, [directional_variance(v, [[2.25, 0.6], [0.6, 1.21]]) for v in n])
        checks = {
            "rank_gain": result.rank_before == 2 and result.rank_after == 3,
            "best_added_angle_45_degrees": abs(result.angle_rad - math.pi / 4) < 1e-12,
            "balanced_global_condition_lower_bound_attained": abs(
                balanced.geometric_condition - math.sqrt(2)
            )
            < 1e-12,
            "finite_planner_no_continuous_or_physical_certificate": not result.continuous_optimality_certified
            and not result.physical_capture_qualified,
        }
        return {"planner": asdict(result), "balanced": asdict(balanced), "checks": checks}
    raise ValueError("unknown algebra case")


def evaluate(case, plan):
    import numpy as np

    from backend.edge_spread import fit_edge_spread
    from backend.profile_observations import PixelNoise
    from backend.psf_calibration import (
        covariance_from_edge_fits,
        covariance_from_edge_spreads,
        plan_edge_orientation,
    )

    config = plan["defaults"] | case
    if case["kind"] == "edges":
        result = edge_case(
            case,
            config,
            plan,
            fit_edge_spread,
            PixelNoise,
            covariance_from_edge_spreads,
            covariance_from_edge_fits,
        )
    elif case["kind"] in {"rectangle", "nearparallel", "weighted", "planner"}:
        result = algebra_case(case, covariance_from_edge_spreads, plan_edge_orientation)
    elif case["kind"] in {"constant", "budget"}:
        xy = pixels(config)
        n = normals(config)[0]
        values = (
            np.full(len(xy), case["constant"])
            if case["kind"] == "constant"
            else edge_means(config, n, xy)
        )
        fit = fit_one(config, n, xy, values, fit_edge_spread, PixelNoise)
        checks = result_checks(fit, config)
        if case["kind"] == "constant":
            checks["flat_tied_unidentified"] = fit.flat and fit.tied and fit.rank_deficient
        else:
            checks["grid_retained_on_exhaustion"] = fit.work_exhausted and fit.unrefined_basins > 0
        estimate = covariance_from_edge_fits([n], [fit])
        checks["unresolved_aggregation_withheld"] = (
            estimate.reconstruction is None and not estimate.all_edges_resolved
        )
        result = {"fit": asdict(fit), "fit_aggregation": asdict(estimate), "checks": checks}
    elif case["kind"] == "noise_controls":
        xy = pixels(config)
        ns = normals(config)
        rng = np.random.default_rng(case["seed"])
        std = np.linspace(*case["input_std_range"], len(xy))
        results = []
        checks = {}
        by_operator = {k: [] for k in ["identity", "duplicate", "units-small", "units-large"]}
        for i, n in enumerate(ns):
            values = edge_means(config, n, xy) + rng.normal(size=len(xy)) * std
            group = []
            for name, scale, mat in [
                ("identity", 1.0, None),
                ("duplicate", 1.0, np.vstack([np.eye(len(xy))] * 2)),
                ("units-small", case["unit_scales"][0], None),
                ("units-large", case["unit_scales"][1], None),
            ]:
                fit = fit_one(
                    config, n, xy, values, fit_edge_spread, PixelNoise, matrix=mat, std=std * scale
                )
                group.append({"operator": name, "fit": asdict(fit)})
                checks.update(
                    {f"edge_{i}_{name}_{k}": v for k, v in result_checks(fit, config).items()}
                )
                by_operator[name].append(fit)
            reference = group[0]["fit"]["best"]
            for other in group[1:]:
                best = other["fit"]["best"]
                checks[f"edge_{i}_invariance_{other['operator']}"] = (
                    best is not None
                    and max(
                        abs(best["offset"] - reference["offset"]),
                        abs(best["sigma"] - reference["sigma"]),
                    )
                    <= case["parameter_invariance_max"]
                )
            results.append(
                {"normal": n, "values": values.tolist(), "input_std": std.tolist(), "fits": group}
            )
        estimates = {
            name: asdict(covariance_from_edge_fits(ns, fits)) for name, fits in by_operator.items()
        }
        for name, estimate in estimates.items():
            checks["all_planned_edges_retained_" + name] = len(estimate["edge_statuses"]) == len(ns)
            checks["unresolved_never_pooled_" + name] = (
                estimate["all_edges_resolved"] or estimate["reconstruction"] is None
            )
            first, second = (
                estimate["directional_variances"],
                estimates["identity"]["directional_variances"],
            )
            checks["same_directional_variances_" + name] = (
                all(a is not None and b is not None for a, b in zip(first, second))
                and math.hypot(*(a - b for a, b in zip(first, second)))
                <= case["directional_variance_invariance_max"]
            )
        result = {
            "edges": results,
            "fit_aggregations": estimates,
            "checks": checks,
            "covariance_means_have_inferred_uncertainty": False,
        }
    else:
        raise ValueError("unknown fixed study case")
    return {"name": case["name"], "input": case, **result, "passed": all(result["checks"].values())}


def run(plan=None):
    started = time.monotonic()
    before = hashes()
    plan = load_plan() if plan is None else plan
    sys.path.insert(0, str(ROOT))
    rows = []
    for case in plan["cases"]:
        start = time.monotonic()
        try:
            row = evaluate(case, plan)
            json.dumps(row, allow_nan=False)
        except Exception as error:  # noqa: BLE001 - preserve each case and continue every later case
            row = {
                "name": case["name"],
                "input": case,
                "passed": False,
                "execution_failure": f"{type(error).__name__}: {error}",
                "checks": {},
            }
        rows.append(row | {"seconds": time.monotonic() - start})
    after = hashes()
    return {
        "format": "pictures-to-cad-psf-calibration-replay",
        "version": 1,
        "plan": plan,
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "cases": rows,
        "passed": before == after and all(r["passed"] for r in rows),
        "summary": {
            "declared_cases": len(plan["cases"]),
            "retained_cases": len(rows),
            "checks": sum(len(r["checks"]) for r in rows),
            "failed_cases": sum(not r["passed"] for r in rows),
            "execution_failures": sum("execution_failure" in r for r in rows),
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": importlib.import_module("numpy").__version__,
            "seconds": time.monotonic() - started,
        },
        "development_history": {
            "initial_report_sha256": "8fe97210f42f6f409ff98b5ffd2a7a3eb354a8b7bca6d72014de572ded5d1b82",
            "initial_report_retained_locally": True,
            "correction": "The initial mixture label compared its Gaussian-equivalent covariance to base-component Sigma0. The final report uses the supplied mixture second moment 3.4*Sigma0 and names that reference explicitly. Independent source means, fitted candidates, finite-D predictions, plan and numerical pass targets are unchanged.",
        },
        "limitations": plan["limitations"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="fresh JSON report; existing paths/symlinks refused",
    )
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("output must be fresh")
    if args.output.suffix.lower() != ".json" or not args.output.parent.is_dir():
        parser.error("output must be .json in an existing directory")
    report = run()
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    with args.output.open("x") as output:
        output.write(encoded)
    print(encoded, end="")
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
