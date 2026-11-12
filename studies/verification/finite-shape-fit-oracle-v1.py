"""Replay independently rendered finite circular-segment inverse controls.

Supply required --output NEW_JSON. Rendering and held-out predictions use the
frozen independent area/slice oracle, never the production forward evaluator.
Known pose/PSF and fixed pixel support are supplied experimental assumptions.
Matched numerical reconstruction targets are not physical accuracy guarantees.
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
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-shape-fit-v1.json"
FORWARD_ORACLE = ROOT / "studies/verification/finite-shape-oracle-v1.py"
SOURCE_PATHS = (
    "backend/__init__.py",
    "backend/finite_shape_fit.py",
    "backend/finite_shape.py",
    "backend/raw_source_fit.py",
    "backend/profile_observations.py",
    "backend/fitting.py",
    "backend/circular_joins.py",
    "backend/sheet.py",
    "backend/tone.py",
    "studies/verification/finite-shape-oracle-v1.py",
    "studies/verification/finite-shape-fit-oracle-v1.py",
    "studies/finite-shape-fit-v1.json",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return {name: sha(ROOT / name) for name in SOURCE_PATHS}


def load_plan():
    plan = json.loads(PLAN.read_text())
    if plan.get("format") != "pictures-to-cad-finite-shape-fit-plan" or plan.get("version") != 1:
        raise ValueError("unsupported finite-shape inverse plan")
    if not 1 <= len(plan["cases"]) <= 64:
        raise ValueError("the fixed small plan needs 1-64 cases")
    names = [c["name"] for c in plan["cases"]]
    if len(names) != len(set(names)):
        raise ValueError("case names must be unique")
    return plan


def load_forward_oracle(plan):
    if sha(FORWARD_ORACLE) != plan["forward_oracle_sha256"]:
        raise ValueError("independent forward-oracle pin changed; review before a new run")
    spec = importlib.util.spec_from_file_location(
        "_independent_finite_shape_area_oracle", FORWARD_ORACLE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def covariance(config, prefix=""):
    name = prefix + "covariance"
    if name in config:
        return np.asarray(config[name], float)
    return np.eye(2) * config.get(prefix + "sigma", config["sigma"]) ** 2


def pose(config):
    angle = math.radians(config["normal_degrees"])
    normal = np.array([math.cos(angle), math.sin(angle)])
    transform = np.array(
        [
            [normal[0], -normal[1], config["centre"][0]],
            [normal[1], normal[0], config["centre"][1]],
            [0.0, 0.0, 1.0],
        ]
    )
    return normal, np.asarray(config["homography"], float) @ transform


def pixels(config, plan, kind):
    _, transform = pose(config)
    raw_centre = transform @ [0.0, 0.0, 1.0]
    anchor = np.floor(raw_centre[:2] / raw_centre[2]).astype(int)
    if kind == "training" and "training_offsets" in config:
        offsets = config["training_offsets"]
    else:
        grid = plan[kind + "_grid"]
        offsets = [[x, y] for y in grid["y_offsets"] for x in grid["x_offsets"]]
    result = anchor + np.asarray(offsets, int)
    if len(np.unique(result, axis=0)) != len(result):
        raise ValueError("independent pixel support must be unique")
    height, width = config["sensor_shape"]
    if np.any(result < 0) or np.any(result >= [width, height]):
        raise ValueError("fixed study pixels leave the declared sensor")
    return result


def shape(radius, fraction):
    return {
        "kind": "disk_segment",
        "center": [0.0, 0.0],
        "radius": radius,
        "chord": radius * fraction,
    }


def point_probabilities(oracle, points, radius, fraction, transform, psf, order, settings, lane):
    return np.array(
        [
            oracle._shape_reference(
                shape(radius, fraction), point, transform, psf, order, settings, lane
            )[0]
            for point in points
        ]
    )


def gradient_field(oracle, points, config, transform, psf, order, settings):
    """Bounded affine material levels using independent Gaussian first moments.

    This source lives only inside the FINITE material. Outside it the background
    is constant. No unbounded illumination extrapolation or production model is
    used; the chosen slopes keep every material level in [0,255].
    """
    radius, fraction = config["radius"], config["fraction"]
    geometry = shape(radius, fraction)
    background, material = config["levels"]
    gx, gy = config["gradient"]
    if (
        not 0
        <= material - radius * math.hypot(gx, gy)
        <= material + radius * math.hypot(gx, gy)
        <= 255
    ):
        raise ValueError("gradient source levels are not globally bounded on the disk")
    nodes, weights = np.polynomial.legendre.leggauss(order)
    values = []
    for point in points:
        mean, pulled = oracle.affine_pullback(point, transform, psf)
        cuts = oracle._slice_cuts(geometry, mean, pulled, settings["tail_multipliers"])
        theta = np.array([math.acos(max(-1.0, min(1.0, -x / radius))) for x in cuts])
        half = np.diff(theta) / 2
        angles = (theta[:-1] + theta[1:])[:, None] / 2 + half[:, None] * nodes
        x, height = -radius * np.cos(angles), radius * np.sin(angles)
        variance = pulled[0, 0]
        sd = math.sqrt(pulled[1, 1] - pulled[1, 0] ** 2 / variance)
        my = mean[1] + pulled[1, 0] / variance * (x - mean[0])
        lower, upper = (-height - my) / sd, (height - my) / sd
        mass = oracle.normal_mass(lower, upper)
        phi = lambda z: np.exp(-z * z / 2) / math.sqrt(2 * math.pi)
        first_y = my * mass + sd * (phi(lower) - phi(upper))
        density = np.exp(-((x - mean[0]) ** 2) / (2 * variance)) / math.sqrt(2 * math.pi * variance)
        jacobian = radius * np.sin(angles) * half[:, None] * weights
        material_contrast_mass = (material - background + gx * x) * mass + gy * first_y
        values.append(background + math.fsum((density * jacobian * material_contrast_mass).ravel()))
    return np.asarray(values)


def field(oracle, points, config, order, settings, aperture_order=None):
    """Render supplied synthetic raw intensities without a production probability."""
    _, transform = pose(config)
    psf = covariance(config)
    source = config.get("source", "point")
    if source == "constant":
        return np.full(len(points), config["constant"], float)
    if source == "material_gradient":
        return gradient_field(oracle, points, config, transform, psf, order, settings)
    if source == "pixel_mean":
        nodes, weights = np.polynomial.legendre.leggauss(aperture_order)
        probability = np.zeros(len(points))
        for i, x in enumerate(nodes):
            for j, y in enumerate(nodes):
                probability += (
                    weights[i]
                    * weights[j]
                    / 4
                    * point_probabilities(
                        oracle,
                        points + [x / 2, y / 2],
                        config["radius"],
                        config["fraction"],
                        transform,
                        psf,
                        order,
                        settings,
                        config.get("oracle", "slice"),
                    )
                )
    elif source == "gaussian_mixture":
        components = config["mixture"]
        if (
            any(c["weight"] <= 0 for c in components)
            or abs(sum(c["weight"] for c in components) - 1) > 1e-15
        ):
            raise ValueError("the independent PSF mixture must be positive and normalized")
        probability = sum(
            c["weight"]
            * point_probabilities(
                oracle,
                points,
                config["radius"],
                config["fraction"],
                transform,
                np.asarray(c["covariance"], float),
                order,
                settings,
                config.get("oracle", "slice"),
            )
            for c in components
        )
    else:
        probability = point_probabilities(
            oracle,
            points,
            config["radius"],
            config["fraction"],
            transform,
            psf,
            order,
            settings,
            config.get("oracle", "slice"),
        )
    if source == "power_response":
        probability = np.maximum(probability, 0) ** config["gamma"]
    background, material = config["levels"]
    return background + (material - background) * probability


def independent_observations(oracle, xy, config, settings):
    points = np.asarray(xy, float) + 0.5
    orders = (
        settings["area_orders"]
        if config.get("oracle") == "plane_area"
        else settings["slice_orders"]
    )
    aperture = config.get("aperture_orders", [None, None])
    previous = field(oracle, points, config, orders[0], settings, aperture[0])
    values = field(oracle, points, config, orders[1], settings, aperture[1])
    return values, float(np.max(np.abs(values - previous)))


def boundary(radius, fraction, settings):
    beta = math.acos(fraction)
    angles = np.linspace(beta, math.tau - beta, settings["boundary_arc_samples"])
    arc = radius * np.column_stack((np.cos(angles), np.sin(angles)))
    chord = np.linspace(arc[-1], arc[0], settings["boundary_chord_samples"])
    return np.vstack((arc, chord))


def boundary_distance(points, radius, fraction):
    """Exact point-to-analytic-boundary distance, evaluated at supplied samples."""
    height, chord = radius * math.sqrt(1 - fraction * fraction), radius * fraction
    radial = np.linalg.norm(points, axis=1)
    projected_x = np.divide(
        radius * points[:, 0], radial, out=np.zeros_like(radial), where=radial > 0
    )
    distance_to_circle = np.abs(radial - radius)
    endpoints = np.array([[chord, height], [chord, -height]])
    distance_to_ends = np.min(
        np.linalg.norm(points[:, None, :] - endpoints[None, :, :], axis=2), axis=1
    )
    distance_to_arc = np.where(
        (projected_x <= chord) & (radial > 0), distance_to_circle, distance_to_ends
    )
    distance_to_arc = np.where(radial == 0, radius, distance_to_arc)
    distance_to_line = np.hypot(points[:, 0] - chord, np.maximum(np.abs(points[:, 1]) - height, 0))
    return np.minimum(distance_to_arc, distance_to_line)


def geometry_errors(best, config, settings):
    truth_radius, truth_fraction = config["radius"], config["fraction"]
    old = boundary(truth_radius, truth_fraction, settings)
    new = boundary(best.radius, best.chord_fraction, settings)
    discrepancy = max(
        float(boundary_distance(old, best.radius, best.chord_fraction).max()),
        float(boundary_distance(new, truth_radius, truth_fraction).max()),
    )
    return {
        "radius_absolute": abs(best.radius - truth_radius),
        "fraction_absolute": abs(best.chord_fraction - truth_fraction),
        "chord_absolute": abs(best.chord_offset - truth_radius * truth_fraction),
        "sampled_boundary_distance": discrepancy,
        "circle_boundary_hausdorff_exact": abs(best.radius - truth_radius),
        "complete_boundary_distance_certified": False,
    }


def evaluate(case, plan, oracle, fit, noise_type):
    started = time.perf_counter()
    config = plan["defaults"] | case
    normal, transform = pose(config)
    training, heldout = pixels(config, plan, "training"), pixels(config, plan, "heldout")
    values, training_delta = independent_observations(oracle, training, config, plan["oracle"])
    heldout_truth, heldout_delta = independent_observations(oracle, heldout, config, plan["oracle"])
    if "observed_values" in config:
        values = np.asarray(config["observed_values"], float)
        if values.shape != (len(training),):
            raise ValueError("declared observation override does not match fixed support")
    selected = np.arange(len(training))
    if config.get("projection") == "even_pixels":
        selected = selected[::2]
    matrix = np.eye(len(training))[selected]
    standard_deviations = np.full(len(training), config["noise_scale"])
    if config.get("source") == "omitted_texture":
        omitted = sorted(set(range(len(training))) - set(selected))
        values[omitted] += config["texture_amplitude"] * np.where(
            np.arange(len(omitted)) % 2, -1, 1
        )
    noise = noise_type.factor(matrix, standard_deviations)
    psf = (
        covariance(config, "fit_")
        if "fit_sigma" in config or "fit_covariance" in config
        else covariance(config)
    )
    options = {
        key: config[key]
        for key in (
            "sensor_shape",
            "homography",
            "centre",
            "level_bounds",
            "grid_points",
            "refinement_iterations",
            "max_basins",
            "max_evaluations",
            "forward_work_limit",
            "probability_tolerance",
        )
    }
    options.update(
        normal=normal,
        psf_covariance=psf,
        radius_bounds=config["radius_bounds"],
        chord_fraction_bounds=config["fraction_bounds"],
    )
    result = fit(training, values, noise, **options)
    row = {
        "name": case["name"],
        "lane": case["lane"],
        "input": config,
        "execution": "executed",
        "result": asdict(result),
        "observations": {
            "pixels_xy": training.tolist(),
            "values": values.tolist(),
            "input_standard_deviations": standard_deviations.tolist(),
            "retained_source_indices": selected.tolist(),
            "independent_order_delta": training_delta,
            "declared_observation_override": "observed_values" in config,
            "geometry_truth_applies": config.get("source") != "constant"
            and "observed_values" not in config,
        },
        "heldout": {
            "pixels_xy": heldout.tolist(),
            "truth": heldout_truth.tolist(),
            "independent_order_delta": heldout_delta,
        },
        "checks": {},
    }
    checks = row["checks"]
    checks["independent_truth_order_agreement"] = (
        max(training_delta, heldout_delta) <= plan["oracle"]["maximum_level_order_delta"]
    )
    checks["complete_coarse_grid_retained"] = (
        len(result.grid) == len(result.grid_statuses) == config["grid_points"] ** 2
    )
    checks["declared_work_limits_respected"] = (
        result.evaluations <= config["max_evaluations"]
        and result.forward_evaluations <= config["forward_work_limit"]
    )
    checks["no_global_pose_PSF_or_physical_claim"] = (
        not result.global_search_certified and not result.pose_fitted and not result.psf_fitted
    )
    checks["represented_candidate_available"] = result.best is not None
    if result.best is not None:
        best = result.best
        errors = geometry_errors(best, config, plan["oracle"])
        row["geometry_errors"] = errors
        settings = plan["oracle"]
        order = (
            settings["area_orders"][-1]
            if config.get("oracle") == "plane_area"
            else settings["slice_orders"][-1]
        )
        train_probability = point_probabilities(
            oracle,
            training.astype(float) + 0.5,
            best.radius,
            best.chord_fraction,
            transform,
            psf,
            order,
            settings,
            config.get("oracle", "slice"),
        )
        heldout_probability = point_probabilities(
            oracle,
            heldout.astype(float) + 0.5,
            best.radius,
            best.chord_fraction,
            transform,
            psf,
            order,
            settings,
            config.get("oracle", "slice"),
        )
        background, material = best.levels
        train_prediction = background + (material - background) * train_probability
        heldout_prediction = background + (material - background) * heldout_probability
        row["heldout"].update(
            prediction=heldout_prediction.tolist(),
            maximum_error=float(np.max(np.abs(heldout_prediction - heldout_truth))),
        )
        residual = (values - train_prediction) / standard_deviations
        independent_cost = float(residual[selected] @ residual[selected])
        row["independent_objective"] = {
            "cost": independent_cost,
            "difference_from_reported": independent_cost - best.cost,
            "within_engineering_cost_guards": bool(
                best.cost_lower_guard <= independent_cost <= best.cost_upper_guard
            ),
        }
        total, retained, omitted = (
            result.raw_residual_l2,
            result.retained_residual_l2,
            result.omitted_source_residual_l2,
        )
        if None not in (total, retained, omitted):
            scale = total * total + retained * retained + omitted * omitted
            checks["standardized_residual_split"] = (
                abs(total * total - retained * retained - omitted * omitted) <= 1e-10 * scale
            )
        if case["lane"] in {"matched", "unit_control"}:
            criteria = plan["matched_criteria"]
            for key in (
                "radius_absolute",
                "fraction_absolute",
                "chord_absolute",
                "sampled_boundary_distance",
            ):
                checks["matched_" + key] = errors[key] <= criteria[key]
            checks["matched_heldout_prediction"] = (
                row["heldout"]["maximum_error"] <= criteria["heldout_level_maximum"]
            )
    expected = config.get("expected")
    if expected == "flat":
        checks["exact_constant_alias_retained"] = result.flat and (
            result.tied or result.rank_deficient
        )
    elif expected == "rank_deficient":
        checks["structural_insufficiency_retained"] = result.rank_deficient
    elif expected == "represented_ambiguity":
        checks["practical_chord_ambiguity_retained"] = (
            result.tied or result.rank_deficient or result.unrefined_basins > 0
        )
    elif expected == "endpoint":
        checks["prior_boundary_flag_retained"] = result.endpoint
    elif expected == "work_limit":
        checks["budget_exhaustion_retains_coarse_grid"] = (
            result.work_exhausted and result.unrefined_basins > 0
        )
    elif expected == "unrefined":
        checks["unrefined_basins_remain_visible"] = result.unrefined_basins > 0
    elif expected == "omitted_mismatch":
        checks["omitted_model_mismatch_visible"] = (
            result.omitted_source_residual_l2 is not None and result.omitted_source_residual_l2 > 10
        )
    elif expected == "active_levels_improve":
        coarse = [candidate.cost for candidate in result.grid if candidate is not None]
        checks["active_levels_retained"] = result.best is not None and np.allclose(
            result.best.levels, config["level_bounds"], rtol=0, atol=1e-10
        )
        checks["free_only_projection_improves_coarse_cost"] = (
            result.best is not None
            and bool(coarse)
            and result.best.cost < min(coarse) - 1e-12 * min(coarse)
        )
        checks["independent_active_profiled_objective"] = row.get("independent_objective", {}).get(
            "within_engineering_cost_guards", False
        )
    row["passed"] = all(checks.values())
    row["seconds"] = time.perf_counter() - started
    return row


def run(plan=None, fit=None):
    started = time.perf_counter()
    before = hashes()
    plan = load_plan() if plan is None else plan
    oracle = load_forward_oracle(plan)
    sys.path.insert(0, str(ROOT))
    noise_module = importlib.import_module("backend.profile_observations")
    if fit is None:
        fit_module = importlib.import_module("backend.finite_shape_fit")
        if Path(fit_module.__file__).resolve() != ROOT / "backend/finite_shape_fit.py":
            raise ValueError("fitter import does not match selected checkout")
        fit = fit_module.fit_circular_segment
    rows = []
    for index, case in enumerate(plan["cases"]):
        try:
            row = evaluate(case, plan, oracle, fit, noise_module.PixelNoise)
            json.dumps(row, allow_nan=False)
        except Exception as error:  # noqa: BLE001 - retain every planned inverse failure and continue
            row = {
                "name": case["name"],
                "lane": case["lane"],
                "input": case,
                "execution": "execution_failure",
                "error": f"{type(error).__name__}: {error}",
                "checks": {},
                "passed": False,
            }
        rows.append({"index": index, **row})
    by_name = {row["name"]: row for row in rows}
    units = []
    reference = by_name.get("matched-R9.37-f0", {})
    for name in ("noise-units-small", "noise-units-large"):
        other = by_name.get(name, {})
        if (
            "result" in reference
            and "result" in other
            and reference["result"]["best"]
            and other["result"]["best"]
        ):
            first, second = reference["result"], other["result"]
            same_flags = all(
                first[key] == second[key]
                for key in ("flat", "tied", "endpoint", "rank_deficient", "geometry_rank")
            )
            same_geometry = (
                abs(first["best"]["radius"] - second["best"]["radius"])
                <= plan["matched_criteria"]["radius_absolute"]
                and abs(first["best"]["chord_fraction"] - second["best"]["chord_fraction"])
                <= plan["matched_criteria"]["fraction_absolute"]
            )
            units.append(
                {
                    "case": name,
                    "same_ambiguity_flags": same_flags,
                    "same_geometry_within_predeclared_numerical_targets": same_geometry,
                    "passed": same_flags and same_geometry,
                }
            )
        else:
            units.append(
                {"case": name, "passed": False, "reason": "required paired case unavailable"}
            )
    after = hashes()
    failures = sum(not row["passed"] for row in rows)
    return {
        "format": "pictures-to-cad-finite-shape-inverse-oracle",
        "version": 1,
        "verification": "passed"
        if before == after and not failures and all(x["passed"] for x in units)
        else "failed",
        "plan": plan,
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
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
            "matched_rows": sum(row["lane"] == "matched" for row in rows),
            "checks": sum(len(row["checks"]) for row in rows) + len(units),
            "unit_control_failures": sum(not x["passed"] for x in units),
        },
        "unit_controls": units,
        "rows": rows,
        "limits": plan["limitations"]
        + [
            "Complete-boundary discrepancy samples independently specified source arcs/chords and uses analytic point-to-boundary distances. It is not a certified continuous Hausdorff enclosure.",
            "Held-out pixel predictions and objective recomputation use the independent area/slice oracle. Quadrature agreement and engineering cost guards are not formal interval or physical-confidence certificates.",
            "Adverse-source rows retain geometry shifts and held-out errors without requiring improvement. Tiny matched-model errors do not establish robustness to those failures or identify a real camera model.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="fresh .json report; existing paths and symlinks refused",
    )
    args = parser.parse_args(argv)
    output = args.output
    if output.exists() or output.is_symlink():
        parser.error("--output must be fresh")
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
