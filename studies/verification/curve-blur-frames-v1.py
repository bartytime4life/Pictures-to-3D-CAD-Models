#!/usr/bin/env python3
"""Replay the frozen conditional blur-frame study; requires --output NEW_JSON.

Source observations come from finite Gaussian area probabilities, independently
of production curvature formulas. The area-slice method is adapted from the
separate frozen finite-shape oracle identified in the plan, not from a production
forward evaluator. No analysis or production imports precede output validation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/curve-blur-frames-v1.json"
RUNNER = Path(__file__).resolve()
ERFC = np.frompyfunc(math.erfc, 1, 1)
GL = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = (
        "backend/__init__.py",
        "backend/fitting.py",
        "backend/reference.py",
        "backend/edges.py",
        "backend/sheet.py",
        "backend/tone.py",
        "uv.lock",
        str(PLAN.relative_to(ROOT)),
        str(RUNNER.relative_to(ROOT)),
    )
    return {path: digest(ROOT / path) for path in paths}


def legendre(order):
    if order not in GL:
        GL[order] = np.polynomial.legendre.leggauss(order)
    return GL[order]


def normal_mass(low, high):
    low, high = np.broadcast_arrays(np.asarray(low, float), np.asarray(high, float))
    root = math.sqrt(2)
    left = 0.5 * np.asarray(ERFC(-high / root), float) - 0.5 * np.asarray(ERFC(-low / root), float)
    right = 0.5 * np.asarray(ERFC(low / root), float) - 0.5 * np.asarray(ERFC(high / root), float)
    return np.where(low >= 0, right, left)


def disk_slice_probability(
    radius, mean, covariance, order, multipliers, *, center_x=0.0, chord=None
):
    """Conditional-Y area integral with x=cx-R*cos(theta), not a boundary integral."""
    left, right = center_x - radius, center_x + (radius if chord is None else chord)
    sx = math.sqrt(covariance[0, 0])
    beta = covariance[1, 0] / covariance[0, 0]
    conditional = math.sqrt(covariance[1, 1] - covariance[1, 0] ** 2 / covariance[0, 0])
    cuts = [left, right, center_x]
    for multiplier in multipliers:
        cuts.append(mean[0] + multiplier * sx)
        intercept = mean[1] + beta * (center_x - mean[0]) + multiplier * conditional
        aa = 1 + beta * beta
        extent = radius * math.sqrt(aa)
        discriminant = (extent - abs(intercept)) * (extent + abs(intercept))
        if discriminant >= 0:
            root = math.sqrt(discriminant)
            cuts.extend(center_x + (-beta * intercept + sign * root) / aa for sign in (-1, 1))
    cuts = sorted({left, right, *(value for value in cuts if left < value < right)})
    angles = np.arccos(np.clip((center_x - np.asarray(cuts)) / radius, -1, 1))
    nodes, weights = legendre(order)
    half = np.diff(angles) / 2
    theta = (angles[:-1, None] + angles[1:, None]) / 2 + half[:, None] * nodes
    x = center_x - radius * np.cos(theta)
    height = radius * np.sin(theta)
    conditional_mean = mean[1] + beta * (x - mean[0])
    mass = normal_mass(
        (-height - conditional_mean) / conditional, (height - conditional_mean) / conditional
    )
    density = np.exp(-0.5 * ((x - mean[0]) / sx) ** 2) / (sx * math.sqrt(2 * math.pi))
    return math.fsum((density * mass * radius * np.sin(theta) * half[:, None] * weights).ravel())


def rectangle_probability(half_core, radius, mean, covariance, order, multipliers):
    if half_core == 0:
        return 0.0
    sx = math.sqrt(covariance[0, 0])
    sy = math.sqrt(covariance[1, 1])
    if covariance[0, 1] == covariance[1, 0] == 0:
        return float(normal_mass((-half_core - mean[0]) / sx, (half_core - mean[0]) / sx)) * float(
            normal_mass((-radius - mean[1]) / sy, (radius - mean[1]) / sy)
        )
    cuts = sorted(
        {
            -half_core,
            half_core,
            *(mean[0] + k * sx for k in multipliers if -half_core < mean[0] + k * sx < half_core),
        }
    )
    nodes, weights = legendre(order)
    half = np.diff(cuts) / 2
    x = (np.asarray(cuts[:-1]) + np.asarray(cuts[1:]))[:, None] / 2 + half[:, None] * nodes
    conditional_mean = mean[1] + covariance[1, 0] / covariance[0, 0] * (x - mean[0])
    sd = math.sqrt(covariance[1, 1] - covariance[1, 0] ** 2 / covariance[0, 0])
    mass = normal_mass((-radius - conditional_mean) / sd, (radius - conditional_mean) / sd)
    density = np.exp(-0.5 * ((x - mean[0]) / sx) ** 2) / (sx * math.sqrt(2 * math.pi))
    return math.fsum((mass * density * half[:, None] * weights).ravel())


def finite_probability(shape, radius, half_core, mean, covariance, order, multipliers):
    """A finite capsule is exactly a rectangle and two disjoint half-disks."""
    mean = np.asarray(mean, float)
    covariance = np.asarray(covariance, float)
    if shape == "disk":
        return disk_slice_probability(radius, mean, covariance, order, multipliers)
    if shape != "capsule":
        raise ValueError("unknown source shape")
    reflected = np.array([-mean[0], mean[1]])
    reflection = np.diag([-1.0, 1.0])
    return math.fsum(
        [
            rectangle_probability(half_core, radius, mean, covariance, order, multipliers),
            disk_slice_probability(
                radius, mean, covariance, order, multipliers, center_x=-half_core, chord=0.0
            ),
            disk_slice_probability(
                radius,
                reflected,
                reflection @ covariance @ reflection,
                order,
                multipliers,
                center_x=-half_core,
                chord=0.0,
            ),
        ]
    )


def rotation(degrees):
    angle = math.radians(degrees)
    return np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])


def build_source(shape, model, plan):
    geometry = plan["geometry"]
    radius, core = geometry["radius"], geometry["capsule_core_half_length"]
    covariance = np.asarray(plan["blur"][model], float)
    settings = plan["oracle"]
    multipliers = settings["gaussian_breakpoints"]
    order = settings["orders"][0]

    def probability(point, at_order=order):
        return finite_probability(shape, radius, core, point, covariance, at_order, multipliers)

    if shape == "disk":
        angles = np.linspace(0, 2 * math.pi, geometry["circle_points"], endpoint=False)
        normals = np.column_stack([np.cos(angles), np.sin(angles)])
        anchors = np.zeros_like(normals)
        spans = {}
    else:
        line_n, arc_n = geometry["capsule_line_points"], geometry["capsule_arc_points"]
        bottom = np.column_stack([np.linspace(-core, core, line_n), np.zeros(line_n)])
        top = np.column_stack([np.linspace(core, -core, line_n), np.zeros(line_n)])
        right_angle = np.linspace(-math.pi / 2, math.pi / 2, arc_n)
        left_angle = np.linspace(math.pi / 2, 3 * math.pi / 2, arc_n)
        anchors = np.vstack(
            [
                bottom,
                np.tile([core, 0], (arc_n - 1, 1)),
                top[1:],
                np.tile([-core, 0], (arc_n - 2, 1)),
            ]
        )
        normals = np.vstack(
            [
                np.tile([0, -1], (line_n, 1)),
                np.column_stack([np.cos(right_angle[1:]), np.sin(right_angle[1:])]),
                np.tile([0, 1], (line_n - 1, 1)),
                np.column_stack([np.cos(left_angle[1:-1]), np.sin(left_angle[1:-1])]),
            ]
        )
        spans = {
            "bottom": [0, line_n - 1],
            "right": [line_n - 1, line_n + arc_n - 2],
            "top": [line_n + arc_n - 2, 2 * line_n + arc_n - 3],
            "left": [2 * line_n + arc_n - 3, 0],
        }
    points = []
    outer = radius + 12 * math.sqrt(float(np.linalg.eigvalsh(covariance)[-1]))
    for anchor, normal in zip(anchors, normals, strict=True):
        if probability(anchor) <= 0.5 or probability(anchor + outer * normal) >= 0.5:
            raise ArithmeticError("declared half-level root bracket is unavailable")
        lo, hi = 0.0, outer
        for _ in range(settings["bisection_iterations"]):
            mid = (lo + hi) / 2
            if probability(anchor + mid * normal) > 0.5:
                lo = mid
            else:
                hi = mid
        points.append(anchor + (lo + hi) * normal / 2)
    points = np.asarray(points)
    low = np.array([probability(point, settings["orders"][0]) for point in points])
    high = np.array([probability(point, settings["orders"][1]) for point in points])
    return {
        "id": f"{shape}-{model}",
        "shape": shape,
        "blur_model": model,
        "covariance": covariance,
        "points": points,
        "spans": spans,
        "point_count": len(points),
        "oracle_order_delta": float(np.max(np.abs(low - high))),
        "oracle_halflevel_error": float(np.max(np.abs(high - 0.5))),
    }


def self_controls(plan):
    settings = plan["oracle"]
    multipliers = settings["gaussian_breakpoints"]
    order = settings["orders"][1]
    scalar = np.asarray(plan["blur"]["scalar"], float)
    aniso = np.asarray(plan["blur"]["anisotropic"], float)
    rows = []
    for name, radius in (("isotropic_disk_center", 12.0), ("isotropic_small_disk_center", 1.0)):
        value = finite_probability("disk", radius, 0, [0, 0], scalar, order, multipliers)
        expected = -math.expm1(-radius * radius / (2 * scalar[0, 0]))
        rows.append(
            {
                "id": name,
                "value": value,
                "expected": expected,
                "error": abs(value - expected),
                "passed": abs(value - expected) <= 1e-8,
            }
        )
    point = [11.8, 1.0]
    disk = finite_probability("disk", 12, 0, point, aniso, order, multipliers)
    capsule = finite_probability("capsule", 12, 0, point, aniso, order, multipliers)
    rows.append(
        {
            "id": "zero_core_capsule_is_disk",
            "error": abs(disk - capsule),
            "passed": abs(disk - capsule) <= 1e-8,
        }
    )
    left = finite_probability("capsule", 12, 60, [-71.8, 1], aniso, order, multipliers)
    right = finite_probability("capsule", 12, 60, [71.8, 1], aniso, order, multipliers)
    rows.append(
        {
            "id": "capsule_reflection",
            "error": abs(left - right),
            "passed": abs(left - right) <= 1e-8,
        }
    )
    return rows


def curve(primitive):
    return {
        "kind": primitive.kind,
        "center": list(primitive.data["c"]),
        "radius": float(primitive.data["r"]),
        "blur_frame_mixed": bool(primitive.data.get("blur_frame_mixed")),
        "blur_unresolved": bool(primitive.data.get("blur_unresolved")),
        "end_cap": bool(primitive.data.get("end_cap")),
    }


def primitive_arc(points, span, fitting):
    segment = fitting.span_points(points, *span)
    cx, cy, radius, rms, worst = fitting.fit_circle(segment)
    return fitting.Primitive(
        "arc",
        {"c": (cx, cy), "r": radius, "mid": tuple(segment[len(segment) // 2])},
        rms,
        worst,
        tuple(span),
    )


def capsule_primitives(points, source, turn, fitting, *, trimmed=None):
    spans = source["spans"]
    axis = rotation(turn) @ np.array([1.0, 0.0])
    bottom_span, top_span = spans["bottom"], spans["top"]
    bottom_c = np.mean(fitting.span_points(points, *bottom_span), axis=0)
    top_c = np.mean(fitting.span_points(points, *top_span), axis=0)
    right_span = spans["right"] if trimmed is None else trimmed
    bottom_metadata = bottom_span if trimmed is None else [bottom_span[0], trimmed[0]]
    top_metadata = top_span if trimmed is None else [trimmed[1], top_span[1]]
    return [
        fitting.Primitive("line", {"c": bottom_c, "d": axis}, 0.0, 0.0, tuple(bottom_metadata)),
        primitive_arc(points, right_span, fitting),
        fitting.Primitive("line", {"c": top_c, "d": -axis}, 0.0, 0.0, tuple(top_metadata)),
        primitive_arc(points, spans["left"], fitting),
    ]


def fit_shape(shape, points, scales, source, model, turn, plan, fitting):
    base_covariance = np.asarray(plan["blur"][model], float)
    sigma = float(np.linalg.det(base_covariance) ** 0.25)
    covariance = (
        rotation(turn) @ base_covariance @ rotation(turn).T if model == "anisotropic" else None
    )
    if shape == "circle":
        prims = fitting.fit_ring(points, 0.15 * sigma, 5.0)
        if not prims or len(prims) != 1 or prims[0].kind != "circle":
            raise ArithmeticError("declared full-circle source was not eligible as one circle")
    elif shape == "wrapping_free_arc":
        prims = [primitive_arc(points, plan["geometry"]["wrapping_free_arc_span"], fitting)]
    else:
        prims = capsule_primitives(points, source, turn, fitting)
        spread = (
            sigma if covariance is None else math.sqrt(float(np.linalg.eigvalsh(covariance)[-1]))
        )
        fitting.refit_lines(points, prims, margin=3 * spread, blur_scales=scales)
        fitting.fit_fillets(points, prims, 0.03, sigma, covariance, blur_scales=scales)
        if len(prims) != 4 or not all(prims[index].data.get("end_cap") for index in (1, 3)):
            raise ArithmeticError(
                "declared parallel caps did not retain their constrained cap model"
            )
    fitting.correct_blur(prims, sigma, blur_scales=scales)
    return [curve(p) for p in prims if p.kind in ("circle", "arc")]


def mapped_points(points, turn, canonical_nadir, alpha, plan, edges):
    matrix = rotation(turn)
    shift = np.asarray(plan["geometry"]["translation"], float)
    world = points @ matrix.T + shift
    nadir = matrix @ np.asarray(canonical_nadir, float) + shift
    height = plan["geometry"]["height"]
    thickness = height * (1 - alpha)
    local_alpha = (height - thickness) / height
    normals = edges.material_normals(world, True)
    mapped, top = edges.correct_thickness(world, normals, nadir, height, thickness)
    scales = np.where(top, local_alpha, 1.0)
    expected = nadir + scales[:, None] * (world - nadir)
    return world, mapped, scales, top, nadir, float(np.max(np.abs(mapped - expected)))


def truth_error(geometry, shape, alpha, turn, nadir, plan):
    matrix = rotation(turn)
    shift = np.asarray(plan["geometry"]["translation"], float)
    radius = plan["geometry"]["radius"]
    core = plan["geometry"]["capsule_core_half_length"]
    centers = [[0, 0]] if shape != "capsule" else [[core, 0], [-core, 0]]
    errors = []
    for output, center in zip(geometry, centers, strict=True):
        original = matrix @ np.asarray(center) + shift
        target = nadir + alpha * (original - nadir)
        errors.append(
            {
                "radius_error": output["radius"] - alpha * radius,
                "center_error": float(np.linalg.norm(np.asarray(output["center"]) - target)),
            }
        )
    return errors


def evaluate_uniform(config, bank, plan, fitting, edges):
    shape, model, turn, alpha = (
        config[key] for key in ("shape", "blur_model", "rotation_degrees", "alpha")
    )
    source = bank[("capsule" if shape == "capsule" else "disk", model)]
    if "error" in source:
        raise ArithmeticError(source["error"])
    world, mapped, scales, top, nadir, map_error = mapped_points(
        source["points"], turn, [0, 0], alpha, plan, edges
    )
    baseline = fit_shape(shape, world, np.ones(len(world)), source, model, turn, plan, fitting)
    result = fit_shape(shape, mapped, scales, source, model, turn, plan, fitting)
    errors = []
    for base, output in zip(baseline, result, strict=True):
        target = nadir + alpha * (np.asarray(base["center"]) - nadir)
        errors.extend(
            [
                abs(output["radius"] - alpha * base["radius"]),
                float(np.linalg.norm(np.asarray(output["center"]) - target)),
            ]
        )
    error = max(errors)
    criteria = plan["criteria"]
    checks = [
        {"name": "actual_uniform_top_map", "passed": bool(top.all())},
        {
            "name": "pointwise_homothety",
            "passed": map_error <= criteria["point_map_pixels"],
            "error": map_error,
        },
        {
            "name": "uniform_frame_commutation",
            "passed": error <= criteria["frame_commutation_pixels"],
            "maximum_error": error,
        },
        {
            "name": "uniform_not_mixed_or_unresolved",
            "passed": not any(p["blur_frame_mixed"] or p["blur_unresolved"] for p in result),
        },
    ]
    return {
        "input": config,
        "lane": "uniform",
        "baseline_geometry": baseline,
        "mapped_geometry": result,
        "frame_commutation_error": error,
        "source_finite_model_errors": truth_error(baseline, shape, 1, turn, nadir, plan),
        "mapped_finite_model_errors": truth_error(result, shape, alpha, turn, nadir, plan),
        "checks": checks,
    }


def radius_series(radius, sigma):
    return radius + sigma * sigma / (2 * radius) - sigma**4 / (24 * radius**3)


def evaluate_separate(config, bank, plan, fitting, edges):
    name, model = config["case"], config["blur_model"]
    settings = plan["separate_controls"]
    turn, alpha = settings["rotation_degrees"], settings["alpha"]
    source = bank[("capsule" if name == "mixed_cap_neighbor_support" else "disk", model)]
    if "error" in source:
        raise ArithmeticError(source["error"])
    canonical_nadir = (
        settings["capsule_external_nadir"]
        if name == "mixed_cap_neighbor_support"
        else settings["circle_external_nadir"]
    )
    _, mapped, scales, _, _, map_error = mapped_points(
        source["points"], turn, canonical_nadir, alpha, plan, edges
    )
    covariance = np.asarray(plan["blur"][model], float)
    sigma = float(np.linalg.det(covariance) ** 0.25)
    checks = [
        {
            "name": "actual_piecewise_map",
            "passed": map_error <= plan["criteria"]["point_map_pixels"],
        },
        {"name": "whole_ring_is_mixed", "passed": len(np.unique(scales)) == 2},
    ]
    if name == "mixed_cap_neighbor_support":
        trimmed = settings["trimmed_right_arc_span"]
        own = fitting.span_points(scales, *trimmed)
        full = fitting.span_points(scales, source["spans"]["bottom"][0], source["spans"]["top"][1])
        prims = capsule_primitives(mapped, source, turn, fitting, trimmed=trimmed)
        legacy = copy.deepcopy(prims)
        matrix = rotation(turn)
        cov = matrix @ covariance @ matrix.T if model == "anisotropic" else None
        fitting.fit_fillets(mapped, legacy, 0.03, sigma, cov)
        fitting.fit_fillets(mapped, prims, 0.03, sigma, cov, blur_scales=scales)
        output, old = curve(prims[1]), curve(legacy[1])
        delta = max(
            abs(output["radius"] - old["radius"]),
            float(np.linalg.norm(np.asarray(output["center"]) - old["center"])),
        )
        checks.extend(
            [
                {
                    "name": "own_arc_uniform_but_neighbor_support_mixed",
                    "passed": bool(np.all(own == own[0]) and len(np.unique(full)) == 2),
                },
                {
                    "name": "mixed_cap_is_explicit_legacy_approximation",
                    "passed": output["blur_frame_mixed"]
                    and not output["blur_unresolved"]
                    and output["end_cap"],
                },
                {
                    "name": "mixed_cap_preserves_declared_legacy_lane",
                    "passed": delta <= plan["criteria"]["frame_commutation_pixels"],
                    "geometry_delta": delta,
                },
            ]
        )
        payload = {
            "mapped_geometry": output,
            "legacy_geometry": old,
            "own_support_scales": np.unique(own).tolist(),
            "whole_neighbor_support_scales": np.unique(full).tolist(),
            "line_refitting": "omitted in this direct consumer contract to isolate cap context selection",
        }
    else:
        if name == "mixed_circle_actual":
            cx, cy, radius, rms, worst = fitting.fit_circle(mapped)
            primitive = fitting.Primitive("circle", {"c": (cx, cy), "r": radius}, rms, worst)
            support = scales
        else:
            span = (
                plan["geometry"]["wrapping_free_arc_span"]
                if name == "uniform_wrapping_arc_mixed_outside"
                else settings["mixed_free_arc_span"]
            )
            primitive = primitive_arc(mapped, span, fitting)
            support = fitting.span_points(scales, *span)
        before = float(primitive.data["r"])
        expected_mixed = name != "uniform_wrapping_arc_mixed_outside"
        common = float(support[0]) if np.all(support == support[0]) else None
        local_sigma = sigma if common is None else common * sigma
        fitting.correct_blur([primitive], sigma, blur_scales=scales)
        output = curve(primitive)
        expected = radius_series(before, local_sigma)
        checks.extend(
            [
                {
                    "name": "declared_support_quantifier",
                    "passed": (common is None) if expected_mixed else common == 1.0,
                },
                {
                    "name": "explicit_mixed_marker",
                    "passed": output["blur_frame_mixed"] == expected_mixed
                    and not output["blur_unresolved"],
                },
                {
                    "name": "declared_series_lane",
                    "passed": abs(output["radius"] - expected)
                    <= plan["criteria"]["frame_commutation_pixels"],
                    "error": abs(output["radius"] - expected),
                },
            ]
        )
        payload = {
            "mapped_geometry": output,
            "own_support_scales": np.unique(support).tolist(),
            "radius_before": before,
            "declared_series_radius": expected,
        }
    return {
        "input": config,
        "lane": "support_policy",
        "scope": "Direct consumer on actual piecewise-mapped points; not a whole-trace eligibility or physical inference certificate.",
        **payload,
        "checks": checks,
    }


def evaluate_no_halflevel(config, plan):
    covariance = np.asarray(plan["blur"][config["blur_model"]], float)
    settings = plan["oracle"]
    values = [
        finite_probability(
            "disk", config["radius"], 0, [0, 0], covariance, order, settings["gaussian_breakpoints"]
        )
        for order in settings["orders"]
    ]
    return {
        "input": config,
        "lane": "adverse_no_halflevel",
        "center_probabilities": values,
        "observations_generated": False,
        "checks": [
            {"name": "no_center_halflevel_mass", "passed": max(values) < 0.5},
            {
                "name": "order_agreement",
                "passed": abs(values[0] - values[1]) <= plan["criteria"]["oracle_order_delta"],
            },
        ],
    }


def evaluate_case(config, bank, plan, fitting, edges):
    if config["lane"] == "uniform":
        return evaluate_uniform(config, bank, plan, fitting, edges)
    if config["lane"] == "support_policy":
        return evaluate_separate(config, bank, plan, fitting, edges)
    return evaluate_no_halflevel(config, plan)


def configurations(plan):
    configs = []
    matrix = plan["uniform_matrix"]
    for shape in matrix["shapes"]:
        for model in matrix["blur_models"]:
            for turn in matrix["rotations_degrees"]:
                for alpha in matrix["alphas"]:
                    configs.append(
                        {
                            "id": f"uniform-{shape}-{model}-rot{turn}-a{alpha}",
                            "lane": "uniform",
                            "shape": shape,
                            "blur_model": model,
                            "rotation_degrees": turn,
                            "alpha": alpha,
                        }
                    )
    settings = plan["separate_controls"]
    for case in settings["cases"]:
        for model in settings["blur_models"]:
            configs.append(
                {
                    "id": f"{case}-{model}",
                    "lane": "support_policy",
                    "case": case,
                    "blur_model": model,
                    "rotation_degrees": settings["rotation_degrees"],
                    "alpha": settings["alpha"],
                }
            )
    adverse = plan["adverse_no_halflevel"]
    for model in adverse["blur_models"]:
        configs.append(
            {
                "id": f"no-halflevel-{model}",
                "lane": "adverse_no_halflevel",
                "blur_model": model,
                "radius": adverse["radius"],
            }
        )
    if len(configs) != 46 or len({c["id"] for c in configs}) != 46:
        raise ValueError("the frozen matrix must retain all 46 unique rows")
    return configs


def run_study():
    sys.path.insert(0, str(ROOT))
    from backend import edges, fitting

    plan = json.loads(PLAN.read_text())
    before = source_hashes()
    started = time.perf_counter()
    controls = self_controls(plan)
    bank = {}
    source_rows = []
    for shape in ("disk", "capsule"):
        for model in plan["uniform_matrix"]["blur_models"]:
            try:
                source = build_source(shape, model, plan)
                bank[(shape, model)] = source
                record = {
                    key: value.tolist() if isinstance(value, np.ndarray) else value
                    for key, value in source.items()
                }
                record["checks"] = [
                    {
                        "name": "source_order_agreement",
                        "passed": source["oracle_order_delta"]
                        <= plan["criteria"]["oracle_order_delta"],
                    },
                    {
                        "name": "source_halflevel",
                        "passed": source["oracle_halflevel_error"]
                        <= plan["criteria"]["oracle_halflevel_error"],
                    },
                ]
                source_rows.append(record)
            except Exception as exc:  # noqa: BLE001 - retain failures and all dependent cases.
                error = f"{type(exc).__name__}: {exc}"
                bank[(shape, model)] = {"error": error}
                source_rows.append(
                    {"id": f"{shape}-{model}", "execution_failure": error, "checks": []}
                )
    rows = []
    for config in configurations(plan):
        row_start = time.perf_counter()
        try:
            row = evaluate_case(config, bank, plan, fitting, edges)
            row["status"] = "passed" if all(c["passed"] for c in row["checks"]) else "failed"
        except Exception as exc:  # noqa: BLE001 - every predeclared later row still runs.
            row = {
                "input": config,
                "status": "execution_failure",
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "checks": [],
            }
        row["id"] = config["id"]
        row["runtime_seconds"] = time.perf_counter() - row_start
        rows.append(row)
    after = source_hashes()
    checks = (
        controls
        + [c for source in source_rows for c in source["checks"]]
        + [c for row in rows for c in row["checks"]]
    )
    failures = sum("execution_failure" in source for source in source_rows) + sum(
        row["status"] == "execution_failure" for row in rows
    )
    return {
        "format": "pictures-to-cad-curve-blur-frames-result",
        "version": 1,
        "scope": plan["scope"],
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "oracle_controls": controls,
        "sources": source_rows,
        "cases": rows,
        "limitations": plan["limitations"],
        "summary": {
            "cases": len(rows),
            "checks": len(checks),
            "failed_checks": sum(not c["passed"] for c in checks),
            "execution_failures": failures,
            "all_passed": before == after and failures == 0 and all(c["passed"] for c in checks),
        },
        "runtime_seconds": time.perf_counter() - started,
    }


def fresh_output(value):
    path = Path(value)
    if path.suffix.lower() != ".json":
        raise ValueError("--output must name a .json file")
    if path.exists() or path.is_symlink():
        raise ValueError("--output must not exist, including dangling symlinks")
    if not path.parent.is_dir():
        raise ValueError("the output parent directory must already exist")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="new JSON file in an existing directory")
    args = parser.parse_args(argv)
    try:
        output = fresh_output(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    report = run_study()
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(encoded)
    sys.stdout.write(encoded)
    return 0 if report["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
