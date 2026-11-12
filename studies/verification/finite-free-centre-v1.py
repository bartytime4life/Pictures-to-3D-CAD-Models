#!/usr/bin/env python3
"""Replay a prospective, conditional finite-D intensity/pose experiment.

Required --output NEW_JSON is checked before production imports or analysis.
The positive-area conic slice oracle never calls the production Green kernel.
All source pixels use geometric centres (integer index + .5). This is a
developer experiment, not optical calibration or automatic geometry acceptance.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import platform
import sys
import time
from dataclasses import asdict
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/finite-free-centre-v1.json"
RUNNER = Path(__file__).resolve()
ERFC = np.frompyfunc(math.erfc, 1, 1)
RULES = {}
SOURCES = (
    "backend/__init__.py",
    "backend/finite_shape.py",
    "backend/finite_centre_fit.py",
    "backend/fitting.py",
    "backend/circular_joins.py",
    "backend/reference.py",
    "backend/edges.py",
    "backend/sheet.py",
    "backend/tone.py",
    "uv.lock",
    "studies/finite-free-centre-v1.json",
    "studies/verification/finite-free-centre-v1.py",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashes():
    return {name: sha(ROOT / name) for name in SOURCES}


def rule(order):
    if order not in RULES:
        RULES[order] = np.polynomial.legendre.leggauss(order)
    return RULES[order]


def normal_mass(low, high):
    low, high = np.broadcast_arrays(np.asarray(low, float), np.asarray(high, float))
    root = math.sqrt(2)
    left = 0.5 * np.asarray(ERFC(-high / root), float) - 0.5 * np.asarray(ERFC(-low / root), float)
    right = 0.5 * np.asarray(ERFC(low / root), float) - 0.5 * np.asarray(ERFC(high / root), float)
    return np.where(low >= 0, right, left)


def mapped(points, matrix):
    points = np.asarray(points, float)
    hom = np.column_stack((points, np.ones(len(points)))) @ np.asarray(matrix).T
    if np.any(hom[:, 2] == 0):
        raise ValueError("independent map reaches a horizon")
    return hom[:, :2] / hom[:, 2, None]


def map_jacobian(point, matrix):
    h = np.asarray(matrix, float)
    p = h @ np.r_[point, 1.0]
    return (h[:2, :2] * p[2] - p[:2, None] * h[2, :2]) / p[2] ** 2


def normal(config):
    angle = math.radians(config["normal_degrees"])
    return np.array([math.cos(angle), math.sin(angle)])


def conic(config, *, hole=False):
    """Projected disk ellipse and chord half-plane, independently of arc tuples.

    These planned H maps keep the ENTIRE disk in one chart. General finite-D
    shapes whose discarded disk crosses a horizon are outside this oracle.
    """
    centre = np.asarray(config["centre"], float)
    radius = float(config["radius"])
    if hole:
        centre = centre + config["hole_offset"]
        radius = config["hole_radius"]
    h = np.asarray(config["homography"], float)
    inverse = np.linalg.inv(h)
    denominator = float(h[2, :2] @ centre + h[2, 2])
    if abs(denominator) <= radius * math.hypot(*h[2, :2]):
        raise ValueError("independent complete-disk oracle crosses a horizon")
    quadratic = np.eye(3)
    quadratic[:2, 2] = quadratic[2, :2] = -centre
    quadratic[2, 2] = float(centre @ centre) - radius**2
    q = inverse.T @ quadratic @ inverse
    q = (q + q.T) / 2
    origin = -np.linalg.solve(q[:2, :2], q[:2, 2])
    scale = -float(np.r_[origin, 1.0] @ q @ np.r_[origin, 1.0])
    ellipse = q[:2, :2] / scale
    if np.linalg.eigvalsh(ellipse)[0] <= 0:
        raise ValueError("independent projected disk is not a bounded ellipse")
    spread = np.linalg.inv(ellipse)
    chord, endpoints = None, []
    if not hole:
        n = normal(config)
        f = config["fraction"]
        chord = inverse.T @ np.r_[n, -n @ centre - radius * f]
        raw_centre = mapped([centre], h)[0]
        chart = float(inverse[2] @ np.r_[raw_centre, 1.0])
        chord *= math.copysign(1.0, chart)
        tangent = np.array([-n[1], n[0]])
        delta = radius * math.sqrt((1 - f) * (1 + f)) * tangent
        endpoints = mapped([centre + radius * f * n + delta, centre + radius * f * n - delta], h)[
            :, 1
        ].tolist()
    return origin, ellipse, spread, chord, endpoints


def roots(a, b, c):
    if a == 0:
        return [] if b == 0 else [-c / b]
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return []
    q = -0.5 * (b + math.copysign(math.sqrt(discriminant), b))
    return [-b / (2 * a)] if q == 0 else [q / a, c / q]


def area_one(point, geometry, covariance, order, multipliers):
    """Positive Gaussian area and raw-coordinate first moments by vertical slices."""
    origin, ellipse, spread, chord, endpoints = geometry
    px, py = point
    sy = math.sqrt(covariance[1, 1])
    beta = covariance[0, 1] / covariance[1, 1]
    conditional = math.sqrt(covariance[0, 0] - covariance[0, 1] ** 2 / covariance[1, 1])
    half_y = math.sqrt(spread[1, 1])
    lower, upper = origin[1] - half_y, origin[1] + half_y
    cuts = [lower, upper, origin[1], *endpoints]
    e00, e01, e11 = ellipse[0, 0], ellipse[0, 1], ellipse[1, 1]
    for k in multipliers:
        cuts.append(py + k * sy)
        intercept = px - beta * py + k * conditional - origin[0]
        aa = e00 * beta**2 + 2 * e01 * beta + e11
        bb = (
            2 * e00 * beta * intercept
            + 2 * e01 * (intercept - beta * origin[1])
            - 2 * e11 * origin[1]
        )
        cc = e00 * intercept**2 - 2 * e01 * intercept * origin[1] + e11 * origin[1] ** 2 - 1
        cuts.extend(roots(aa, bb, cc))
        if chord is not None:
            divisor = chord[0] * beta + chord[1]
            if divisor != 0:
                cuts.append(-(chord[0] * (px - beta * py + k * conditional) + chord[2]) / divisor)
    cuts = sorted({lower, upper, *(x for x in cuts if lower < x < upper)})
    angles = np.arccos(np.clip((origin[1] - np.asarray(cuts)) / half_y, -1.0, 1.0))
    nodes, weights = rule(order)
    half = np.diff(angles) / 2
    theta = (angles[:-1, None] + angles[1:, None]) / 2 + half[:, None] * nodes
    y = origin[1] - half_y * np.cos(theta)
    dy = y - origin[1]
    middle_x = origin[0] - e01 / e00 * dy
    half_x = np.sqrt(np.maximum(0.0, (1 - (e11 - e01**2 / e00) * dy**2) / e00))
    lo, hi = middle_x - half_x, middle_x + half_x
    valid = np.ones_like(y, dtype=bool)
    if chord is not None:
        if chord[0] > 0:
            hi = np.minimum(hi, -(chord[1] * y + chord[2]) / chord[0])
        elif chord[0] < 0:
            lo = np.maximum(lo, -(chord[1] * y + chord[2]) / chord[0])
        else:
            valid &= chord[1] * y + chord[2] <= 0
    valid &= hi > lo
    mean_x = px + beta * (y - py)
    zlo, zhi = (lo - mean_x) / conditional, (hi - mean_x) / conditional
    mass = np.where(valid, normal_mass(zlo, zhi), 0.0)
    phi = lambda z: np.exp(-z * z / 2) / math.sqrt(2 * math.pi)
    first_x = np.where(valid, mean_x * mass + conditional * (phi(zlo) - phi(zhi)), 0.0)
    density = np.exp(-0.5 * ((y - py) / sy) ** 2) / (sy * math.sqrt(2 * math.pi))
    factor = density * half_y * np.sin(theta) * half[:, None] * weights
    return np.array(
        [
            math.fsum((factor * mass).ravel()),
            math.fsum((factor * first_x).ravel()),
            math.fsum((factor * y * mass).ravel()),
        ]
    )


def independent_means(points, config, order, plan, *, aperture_order=None):
    covariance = np.asarray(config["covariance"], float)
    geometry = conic(config)
    multipliers = plan["oracle"]["tail_breakpoints"]
    source = config.get("source", "point")
    if source == "constant":
        return np.full(len(points), config["constant"], float)
    if source == "pixel_mean" and aperture_order is not None:
        nodes, weights = rule(aperture_order)
        result = np.zeros(len(points))
        altered = {**config, "source": "point"}
        for x, wx in zip(nodes, weights, strict=True):
            for y, wy in zip(nodes, weights, strict=True):
                result += (
                    wx
                    * wy
                    / 4
                    * independent_means(np.asarray(points) + [x / 2, y / 2], altered, order, plan)
                )
        return result
    values = np.array([area_one(p, geometry, covariance, order, multipliers) for p in points])
    probability = values[:, 0]
    if source == "hole":
        probability -= np.array(
            [
                area_one(p, conic(config, hole=True), covariance, order, multipliers)[0]
                for p in points
            ]
        )
    if source == "nonlinear":
        probability = probability ** config["power"]
    background, material = config["levels"]
    result = background + (material - background) * probability
    if source == "material_gradient":
        centre = mapped([config["centre"]], config["homography"])[0]
        result += (values[:, 1:] - values[:, :1] * centre) @ np.asarray(config["gradient"])
    if source == "overshoot":
        result += config["overshoot"] * np.sign(probability - 0.5)
    return result


def spread_select(items, count):
    if len(items) < count:
        raise ValueError(f"observed stratum has {len(items)} pixels; needs {count}")
    indices = np.rint(np.linspace(0, len(items) - 1, count)).astype(int)
    return np.asarray(items)[indices]


def observed_seed_roi(field, config, plan):
    """Frozen study-only observation policy; intentionally takes no true geometry."""
    height, width = field.shape
    border = np.r_[field[0], field[-1], field[1:-1, 0], field[1:-1, -1]]
    background = float(np.median(border))
    bright = config["levels"][1] > config["levels"][0]  # declared polarity only
    material = float(np.percentile(field, 99.8 if bright else 0.2))
    contrast = material - background
    if abs(contrast) < plan["seed_and_roi"]["minimum_observed_contrast"]:
        raise ValueError("observed contrast below12; seed ineligible")
    u = (field - background) / contrast
    level = config["seed_level"]
    points = []
    for y in range(height):
        for x in range(width - 1):
            a, b = u[y, x] - level, u[y, x + 1] - level
            if a * b < 0:
                points.append((x + 0.5 - a / (b - a), y + 0.5))
            if a == 0:
                points.append((x + 0.5, y + 0.5))
    for y in range(height - 1):
        for x in range(width):
            a, b = u[y, x] - level, u[y + 1, x] - level
            if a * b < 0:
                points.append((x + 0.5, y + 0.5 - a / (b - a)))
            if a == 0:
                points.append((x + 0.5, y + 0.5))
    points.extend((float(x) + 0.5, float(y) + 0.5) for y, x in np.argwhere(u == level))
    contour = np.array(sorted(set(points)), float)
    if len(contour) < 8:
        raise ValueError("observed contour has fewer than8 crossings")
    h = np.asarray(config["homography"], float)
    plane = mapped(contour, np.linalg.inv(h))
    n = normal(config)
    projection = plane @ n
    support = plane[projection <= np.percentile(projection, 65)]
    if len(support) < 6:
        raise ValueError("observed circular support has fewer than6 crossings")
    origin = np.mean(support, axis=0)
    local = support - origin
    offset, _, rank, _ = np.linalg.lstsq(
        2 * local,
        np.sum(local * local, axis=1) - np.mean(np.sum(local * local, axis=1)),
        rcond=None,
    )
    if rank != 2:
        raise ValueError("observed circle seed rank deficient")
    centre = origin + offset
    raw_radius = math.sqrt(float(np.mean(np.sum(local * local, axis=1)) + offset @ offset))
    extent = float(np.max(np.ptp(plane, axis=0)))
    radius = float(np.clip(raw_radius, 0.05, 4 * extent))
    fraction = float(np.clip((np.percentile(projection, 97) - n @ centre) / radius, -0.9, 0.9))
    sigma = math.sqrt(
        float(np.linalg.eigvalsh(config.get("fit_covariance", config["covariance"]))[-1])
    )
    corners = [
        [x, y]
        for x in (contour[:, 0].min(), contour[:, 0].max())
        for y in (contour[:, 1].min(), contour[:, 1].max())
    ]
    blur_plane = sigma * max(np.linalg.norm(map_jacobian(p, np.linalg.inv(h)), 2) for p in corners)
    pad = max(0.5 * radius, 3 * blur_plane)
    bounds = {
        "centre_bounds": [[float(c - pad), float(c + pad)] for c in centre],
        "radius_bounds": [max(0.05, 0.25 * radius), max(2 * radius, extent)],
        "chord_fraction_bounds": [max(-0.98, fraction - 0.45), min(0.98, fraction + 0.45)],
    }
    mask = np.argwhere(u >= level)
    if not len(mask):
        raise ValueError("observed threshold mask empty")
    margin = math.ceil(3 * sigma)
    ymin, xmin = np.maximum(mask.min(axis=0) - margin, 0)
    ymax, xmax = np.minimum(mask.max(axis=0) + margin, [height - 1, width - 1])
    roi = [(x, y) for y in range(int(ymin), int(ymax) + 1) for x in range(int(xmin), int(xmax) + 1)]
    centroid = mask[:, ::-1].mean(axis=0) + 0.5
    edge = [p for p in roi if 0.15 < u[p[1], p[0]] < 0.85]
    edge.sort(
        key=lambda p: (
            math.atan2(p[1] + 0.5 - centroid[1], p[0] + 0.5 - centroid[0]),
            math.hypot(p[0] + 0.5 - centroid[0], p[1] + 0.5 - centroid[1]),
            p[1],
            p[0],
        )
    )
    strata = [
        spread_select(edge, 32),
        spread_select([p for p in roi if u[p[1], p[0]] >= 0.9], 12),
        spread_select([p for p in roi if u[p[1], p[0]] <= 0.1], 12),
    ]
    training, heldout = [], []
    for group_index, group in enumerate(strata):
        period = 4 if group_index == 0 else 3
        for i, p in enumerate(group):
            (heldout if i % period == period - 1 else training).append(p.tolist())
    if len(training) != 40 or len(heldout) != 16:
        raise ValueError("fixed observed stratum split must yield40training/16heldout")
    training = np.asarray(training, int)
    edge_training = training[:24].copy()
    if "training_crop" in config:
        training = training[training[:, 0] <= config["training_crop"]["x_max"]]
    if config.get("training_mode") == "contour_only":
        training = edge_training
    return {
        "background_estimate": background,
        "material_estimate": material,
        "observed_contrast": contrast,
        "contour": contour.tolist(),
        "plane_contour": plane.tolist(),
        "seed_centre": centre.tolist(),
        "seed_radius": radius,
        "unclipped_seed_radius": raw_radius,
        "seed_fraction": fraction,
        "observed_extent": extent,
        "blur_plane": blur_plane,
        "bounds": bounds,
        "roi_bounds_xy": [int(xmin), int(ymin), int(xmax), int(ymax)],
        "training_pixels": training.tolist(),
        "heldout_pixels": heldout,
    }


def boundary(config, parameters, count=1025):
    cx, cy, r, f = parameters
    n = normal(config)
    t = np.array([-n[1], n[0]])
    angles = np.linspace(math.acos(f), 2 * math.pi - math.acos(f), count)
    arc = np.array([cx, cy]) + r * (np.cos(angles)[:, None] * n + np.sin(angles)[:, None] * t)
    chord = np.linspace(arc[-1], arc[0], 65)[1:]
    return mapped(np.vstack((arc, chord)), config["homography"])


def geometry_metrics(config, best):
    from shapely.geometry import LineString

    fitted = [*best.centre, best.radius, best.chord_fraction]
    truth = [*config["centre"], config["radius"], config["fraction"]]
    scale = float(np.linalg.norm(map_jacobian(config["centre"], config["homography"]), 2))
    return {
        "centre_error_observation_px": float(
            np.linalg.norm(
                mapped([best.centre], config["homography"])[0]
                - mapped([config["centre"]], config["homography"])[0]
            )
        ),
        "radius_error_times_local_H_operator_norm_px": abs(best.radius - config["radius"]) * scale,
        "fraction_error": abs(best.chord_fraction - config["fraction"]),
        "mapped_boundary_polyline_hausdorff_px": float(
            LineString(boundary(config, fitted)).hausdorff_distance(
                LineString(boundary(config, truth))
            )
        ),
        "boundary_distance_scope": "Dense1025arc/65chord polyline diagnostic, not a certified Hausdorff bound.",
    }


def run_case(case, plan, core):
    start = time.perf_counter()
    config = {**copy.deepcopy(plan["base"]), **copy.deepcopy(case)}
    h, w = config["sensor_shape"]
    pixels = np.array([(x, y) for y in range(h) for x in range(w)], int)
    detector = independent_means(
        pixels + 0.5,
        config,
        plan["oracle"]["detector_order"],
        plan,
        aperture_order=plan["oracle"]["aperture_orders"][0],
    ).reshape(h, w)
    row = {"name": case["name"], "lane": case["lane"], "config": config}
    try:
        observed = observed_seed_roi(detector, config, plan)
    except ValueError as error:
        return {
            **row,
            "status": "observed_seed_ineligible",
            "reason": str(error),
            "matched_targets_passed": False if case["lane"] == "matched" else None,
            "runtime_seconds": time.perf_counter() - start,
        }
    row["observed"] = observed
    train = np.asarray(observed["training_pixels"], int)
    held = np.asarray(observed["heldout_pixels"], int)
    allpixels = np.vstack((train, held))
    low, high = plan["oracle"]["orders"]
    aperture_low, aperture_high = plan["oracle"]["aperture_orders"]
    a = independent_means(allpixels + 0.5, config, low, plan, aperture_order=aperture_low)
    y = independent_means(allpixels + 0.5, config, high, plan, aperture_order=aperture_high)
    delta = float(np.max(np.abs(a - y)))
    row["oracle"] = {
        "level_order_delta": delta,
        "passed": delta <= plan["oracle"]["maximum_level_order_delta"],
        "orders": [low, high],
        "aperture_orders": [aperture_low, aperture_high]
        if config["source"] == "pixel_mean"
        else None,
    }
    settings = {**plan["fit_settings"], **config.get("fit_settings", {})}
    settings["level_bounds"] = tuple(settings["level_bounds"])
    arguments = {
        "sensor_shape": config["sensor_shape"],
        "homography": config["homography"],
        "normal": normal(config),
        "psf_covariance": config.get("fit_covariance", config["covariance"]),
        **observed["bounds"],
        **settings,
    }
    original = core.circular_segment_probabilities
    injected_calls = 0

    def first_error(*args, **kwargs):
        nonlocal injected_calls
        injected_calls += 1
        if injected_calls == 1:
            raise ValueError("planned first-forward numerical failure")
        return original(*args, **kwargs)

    try:
        if config.get("injection") == "first_forward_value_error":
            core.circular_segment_probabilities = first_error
        fitted = core.fit_circular_segment(train, y[: len(train)], **arguments)
    finally:
        core.circular_segment_probabilities = original
    row.update(
        status="fit_completed",
        fit=asdict(fitted),
        injected_forward_calls=injected_calls,
        observed_values_training=y[: len(train)].tolist(),
        observed_values_heldout=y[len(train) :].tolist(),
    )
    truth = [*config["centre"], config["radius"], config["fraction"]]
    bounds = [
        *observed["bounds"]["centre_bounds"],
        observed["bounds"]["radius_bounds"],
        observed["bounds"]["chord_fraction_bounds"],
    ]
    row["truth_in_observed_domain"] = all(
        lo <= v <= hi for v, (lo, hi) in zip(truth, bounds, strict=True)
    )
    if fitted.best is not None:
        row["geometry"] = geometry_metrics(config, fitted.best)
        predicted_config = {
            **config,
            "source": "point",
            "centre": list(fitted.best.centre),
            "radius": fitted.best.radius,
            "fraction": fitted.best.chord_fraction,
            "levels": list(fitted.best.levels),
            "covariance": arguments["psf_covariance"],
        }
        prediction = independent_means(held + 0.5, predicted_config, high, plan)
        row["heldout_level_max_error"] = float(np.max(np.abs(prediction - y[len(train) :])))
        targets = plan["matched_targets"]
        row["matched_completion_passed"] = not (
            fitted.work_exhausted
            or fitted.refinement_limited
            or fitted.unrefined_basins
            or fitted.numerically_unsupported
        )
        row["matched_targets_passed"] = bool(
            all(
                row["geometry"][key] <= targets[key]
                for key in (
                    "centre_error_observation_px",
                    "radius_error_times_local_H_operator_norm_px",
                    "fraction_error",
                )
            )
            and row["heldout_level_max_error"] <= targets["heldout_level_max_error"]
            and row["oracle"]["passed"]
            and row["matched_completion_passed"]
        )
    else:
        row["matched_targets_passed"] = False
    if case["lane"] != "matched":
        row["matched_targets_passed"] = None
    row["runtime_seconds"] = time.perf_counter() - start
    return row


def decimal_box_fit(design, target, bounds):
    """Independent two-column face oracle using90-digit scalar Gram arithmetic."""
    with localcontext() as context:
        context.prec = 90
        a = [[Decimal.from_float(float(v)) for v in row] for row in design]
        z = [Decimal.from_float(float(v)) for v in target]
        lo, hi = (Decimal.from_float(float(x)) for x in bounds)
        gram = [[sum(row[i] * row[j] for row in a) for j in range(2)] for i in range(2)]
        rhs = [sum(row[i] * v for row, v in zip(a, z, strict=True)) for i in range(2)]
        options = []
        determinant = gram[0][0] * gram[1][1] - gram[0][1] ** 2
        if determinant > 0:
            options.append(
                [
                    (rhs[0] * gram[1][1] - rhs[1] * gram[0][1]) / determinant,
                    (rhs[1] * gram[0][0] - rhs[0] * gram[0][1]) / determinant,
                ]
            )
        for fixed, free in ((0, 1), (1, 0)):
            for bound in (lo, hi):
                value = (
                    lo
                    if gram[free][free] == 0
                    else (rhs[free] - bound * gram[free][fixed]) / gram[free][free]
                )
                item = [lo, lo]
                item[fixed] = bound
                item[free] = min(hi, max(lo, value))
                options.append(item)
        candidates = []
        for coefficients in options:
            if all(lo <= v <= hi for v in coefficients):
                residual = [
                    v - sum(x * c for x, c in zip(row, coefficients, strict=True))
                    for row, v in zip(a, z, strict=True)
                ]
                candidates.append((sum(v * v for v in residual), coefficients))
        return np.array(list(map(float, min(candidates, key=lambda x: x[0])[1])))


def oracle_controls(plan):
    """Closed Gaussian disk/half-disk answers before any production comparison."""
    config = copy.deepcopy(plan["base"])
    config.update(
        radius=2.0, fraction=0.0, covariance=[[1.21, 0.0], [0.0, 1.21]], levels=[0.0, 1.0]
    )
    expected = 0.5 * (-math.expm1(-(2.0**2) / (2 * 1.21)))
    rows = []
    for name, angle, h in (
        ("half-disk-axis", 0.0, np.eye(3)),
        ("half-disk-rotated-normal", 37.0, np.eye(3)),
        ("half-disk-negative-H", 37.0, -7 * np.eye(3)),
        (
            "half-disk-reflection",
            37.0,
            np.array([[-1.0, 0.0, 64.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        ),
    ):
        altered = {**config, "normal_degrees": angle, "homography": h.tolist()}
        point = mapped([altered["centre"]], h)
        values = [
            float(independent_means(point, altered, order, plan)[0])
            for order in plan["oracle"]["orders"]
        ]
        error = max(abs(value - expected) for value in values)
        rows.append(
            {
                "name": name,
                "values": values,
                "expected": expected,
                "maximum_absolute_error": error,
                "passed": error <= 1e-11,
            }
        )
    return {
        "checks": rows,
        "all_passed": all(r["passed"] for r in rows),
        "scope": "Closed centred isotropic half-disk Gaussian masses, including H sign and reflection; no production mean is called.",
    }


def derivative_controls(plan, core):
    """Independent area finite differences, full fixed-face residuals, mean ranks."""
    config = copy.deepcopy(plan["base"])
    config.update(
        covariance=[[3.0, 1.1], [1.1, 1.7]],
        normal_degrees=37.0,
        homography=[[1.0, 0.12, -1.0], [0.02, 1.03, -1.0], [0.0012, -0.0007, 1.0]],
    )
    pixels = np.array(
        [[20, 29], [22, 24], [25, 22], [30, 20], [35, 23], [36, 28], [34, 34], [28, 38]], int
    )
    parameters = np.r_[config["centre"], config["radius"], config["fraction"]]
    order = plan["oracle"]["orders"][1]

    def probabilities(p):
        altered = {
            **config,
            "centre": p[:2].tolist(),
            "radius": float(p[2]),
            "fraction": float(p[3]),
            "levels": [0.0, 1.0],
        }
        return independent_means(pixels + 0.5, altered, order, plan)

    analytic = core.circular_segment_jacobian(
        pixels,
        config["radius"],
        config["fraction"],
        centre=config["centre"],
        normal=normal(config),
        sensor_shape=config["sensor_shape"],
        homography=config["homography"],
        psf_covariance=config["covariance"],
    )
    rows = []
    if all(status == "resolved" for status in analytic.statuses):
        jac = np.asarray(analytic.jacobian)
        for step in plan["independent_checks"]["derivative_targets"]["parameter_steps"]:
            numeric = np.column_stack(
                [
                    (
                        probabilities(parameters + axis * step)
                        - probabilities(parameters - axis * step)
                    )
                    / (2 * step)
                    for axis in np.eye(4)
                ]
            )
            error = float(np.max(np.abs(numeric - jac) / (1 + np.abs(numeric))))
            rows.append(
                {
                    "name": f"area-shape-derivative-{step}",
                    "maximum_scaled_error": error,
                    "passed": error <= 5e-5,
                }
            )
        p = probabilities(parameters)
        design = np.column_stack((1 - p, p))

        def independent_profile(at, target, bounds):
            prob = probabilities(at)
            a = np.column_stack((1 - prob, prob))
            coef = decimal_box_fit(a, target, bounds)
            return target - a @ coef

        for name, levels, delta, bounds in (
            ("interior", [37.0, 211.0], 0.07, (0.0, 255.0)),
            ("both-active", [0.0, 255.0], 0.2, (0.0, 255.0)),
        ):
            target = design @ levels + delta * np.sign(p - 0.5)
            coefficients = decimal_box_fit(design, target, bounds)
            full, mean = core._projected_jacobians(design, jac, coefficients, target, bounds)
            for step in plan["independent_checks"]["derivative_targets"]["parameter_steps"]:
                numeric = np.column_stack(
                    [
                        (
                            independent_profile(parameters + axis * step, target, bounds)
                            - independent_profile(parameters - axis * step, target, bounds)
                        )
                        / (2 * step)
                        for axis in np.eye(4)
                    ]
                )
                error = float(np.max(np.abs(numeric - full) / (1 + np.abs(numeric))))
                rows.append(
                    {
                        "name": f"profiled-residual-{name}-{step}",
                        "coefficients": coefficients.tolist(),
                        "maximum_scaled_error": error,
                        "passed": error <= 2e-4,
                    }
                )
            rows.append(
                {
                    "name": f"mean-jacobian-rank-{name}",
                    "rank": int(np.linalg.matrix_rank(mean)),
                    "passed": bool(np.linalg.matrix_rank(mean) <= 4),
                }
            )
            complemented = core._projected_jacobians(
                design, jac, 255 - coefficients, 255 - target, bounds
            )
            error = float(
                max(
                    np.max(np.abs(complemented[0] + full) / (1 + np.abs(full))),
                    np.max(np.abs(complemented[1] + mean) / (1 + np.abs(mean))),
                )
            )
            rows.append(
                {
                    "name": f"complement-fixed-face-{name}",
                    "maximum_scaled_error": error,
                    "passed": error <= 2e-4,
                }
            )
            for scale in (1e-6, 1e6):
                scaled = core._projected_jacobians(
                    design * scale, jac * scale, coefficients, target * scale, bounds
                )
                error = float(
                    max(
                        np.max(np.abs(scaled[0] / scale - full) / (1 + np.abs(full))),
                        np.max(np.abs(scaled[1] / scale - mean) / (1 + np.abs(mean))),
                    )
                )
                rows.append(
                    {
                        "name": f"residual-metric-scale-{name}-{scale}",
                        "maximum_scaled_error": error,
                        "passed": error <= 2e-4,
                    }
                )
        # Three retained measurements minus two free nuisance levels admit at most
        # ONE local mean-information direction, even if residual-dependent J grows.
        selected = [0, 3, 6]
        a = design[selected]
        dp = jac[selected]
        target = a @ np.array([37.0, 211.0]) + np.array([0.03, -0.04, 0.08])
        coefficients = decimal_box_fit(a, target, (0.0, 255.0))
        full, mean = core._projected_jacobians(a, dp, coefficients, target, (0.0, 255.0))
        singular = np.linalg.svd(mean, compute_uv=False)
        rank = int(np.count_nonzero(singular > 1e-10 * max(1.0, singular[0])))
        rows.append(
            {
                "name": "projected-mean-rank-ceiling",
                "mean_rank": rank,
                "full_residual_rank": int(np.linalg.matrix_rank(full)),
                "passed": rank <= 1,
            }
        )
        rotation = np.array([[0.0, -1.0], [1.0, 0.0]])
        frame = np.array([[0.0, -1.0, 64.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
        for name, query, h, covariance in (
            (
                "negative-homogeneous-H",
                pixels,
                -7 * np.asarray(config["homography"]),
                config["covariance"],
            ),
            (
                "large-homogeneous-H",
                pixels,
                1e12 * np.asarray(config["homography"]),
                config["covariance"],
            ),
            (
                "quarterturn-observation-frame",
                np.column_stack((63 - pixels[:, 1], pixels[:, 0])),
                frame @ np.asarray(config["homography"]),
                rotation @ np.asarray(config["covariance"]) @ rotation.T,
            ),
            ("pixel-permutation", pixels[::-1], config["homography"], config["covariance"]),
        ):
            value = core.circular_segment_jacobian(
                query,
                config["radius"],
                config["fraction"],
                centre=config["centre"],
                normal=normal(config),
                sensor_shape=config["sensor_shape"],
                homography=h,
                psf_covariance=covariance,
            )
            expected = jac[::-1] if name == "pixel-permutation" else jac
            available = all(s == "resolved" for s in value.statuses)
            error = (
                float(
                    np.max(np.abs(np.asarray(value.jacobian) - expected) / (1 + np.abs(expected)))
                )
                if available
                else None
            )
            rows.append(
                {
                    "name": name,
                    "maximum_scaled_error": error,
                    "passed": bool(available and error <= 5e-5),
                }
            )
    else:
        rows.append(
            {
                "name": "shape-derivative-available",
                "statuses": list(analytic.statuses),
                "passed": False,
            }
        )
    return {
        "checks": rows,
        "all_passed": all(row["passed"] for row in rows),
        "scope": "Area-oracle finite differences and Decimal face solves; numerical checks, not certified derivatives or Fisher/noise calibration.",
    }


def run_study(plan, *, core=None):
    start = time.perf_counter()
    before = hashes()
    if core is None:
        sys.path.insert(0, str(ROOT))
        core = importlib.import_module("backend.finite_centre_fit")
    closed_oracle = oracle_controls(plan)
    rows = []
    for case in plan["cases"]:
        try:
            row = run_case(case, plan, core)
            json.dumps(row, allow_nan=False)  # a bad row cannot destroy later outcomes
        except Exception as error:  # noqa: BLE001 - retain each planned scene's execution failure
            row = {
                "name": case["name"],
                "lane": case["lane"],
                "status": "execution_failure",
                "error_type": type(error).__name__,
                "error": str(error),
                "matched_targets_passed": False if case["lane"] == "matched" else None,
            }
        rows.append(row)
        print(
            json.dumps(
                {"case": row["name"], "status": row["status"], "completed": len(rows)},
                allow_nan=False,
            ),
            file=sys.stderr,
            flush=True,
        )
    try:
        derivatives = derivative_controls(plan, core)
    except Exception as error:  # noqa: BLE001 - retained, explicitly failed control lane
        derivatives = {
            "all_passed": False,
            "checks": [],
            "error_type": type(error).__name__,
            "error": str(error),
        }
    after = hashes()
    matched = [r for r in rows if r["lane"] == "matched"]
    oracle = [r["oracle"] for r in rows if "oracle" in r]
    summary = {
        "planned_cases": len(plan["cases"]),
        "retained_cases": len(rows),
        "execution_failures": sum(r["status"] == "execution_failure" for r in rows),
        "observed_seed_ineligible": sum(r["status"] == "observed_seed_ineligible" for r in rows),
        "matched_cases": len(matched),
        "matched_target_passes": sum(r["matched_targets_passed"] for r in matched),
        "all_matched_targets_passed": all(r["matched_targets_passed"] for r in matched),
        "available_oracle_rows": len(oracle),
        "all_available_oracle_orders_passed": all(r["passed"] for r in oracle),
        "derivative_checks_passed": derivatives["all_passed"],
        "closed_oracle_checks_passed": closed_oracle["all_passed"],
    }
    return {
        "format": "pictures-to-cad-finite-free-centre-study",
        "version": 1,
        "scope": plan["scope"],
        "plan": plan,
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "cases": rows,
        "derivative_controls": derivatives,
        "closed_oracle_controls": closed_oracle,
        "summary": summary,
        "runtime_seconds": time.perf_counter() - start,
    }


def validate_output(path):
    path = Path(path)
    if (
        path.suffix.lower() != ".json"
        or not path.parent.is_dir()
        or path.exists()
        or path.is_symlink()
    ):
        raise ValueError("--output needs a fresh .json path in an existing directory")
    return path


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(arguments)
    try:
        output = validate_output(args.output)
        plan = json.loads(PLAN.read_text())
        result = run_study(plan)
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        with output.open("x") as stream:
            stream.write(encoded)
        print(encoded, end="")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    summary = result["summary"]
    return (
        0
        if (
            result["source_unchanged"]
            and summary["execution_failures"] == 0
            and summary["all_matched_targets_passed"]
            and summary["all_available_oracle_orders_passed"]
            and summary["derivative_checks_passed"]
            and summary["closed_oracle_checks_passed"]
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
