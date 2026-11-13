#!/usr/bin/env python3
"""Independent smooth source-cell sensitivity controls; no rounded-chain inverse."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import traceback
from fractions import Fraction
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = "studies/finite-cell-sensitivity-v1.json"
ORDER = ("centre_x", "centre_y", "radius", "fraction", "normal_angle")
SETTINGS = {
    "fd_step": 1e-4,
    "area_orders": [64, 96],
    "area_propagated_order_limit": 2e-6,
    "fd_step_delta_limit": 2e-5,
    "candidate_fd_absolute": 3e-6,
    "candidate_fd_relative": 2e-6,
    "boundary_orders": [32, 64],
    "boundary_order_limit": 1e-10,
    "candidate_boundary_absolute": 2e-9,
    "candidate_boundary_relative": 2e-9,
    "invariant_absolute": 2e-8,
    "invariant_relative": 2e-8,
}


def canonical_normal(normal):
    """Freeze the mean API's represented canonical normal ONCE."""
    length = math.hypot(*normal)
    return tuple(float(x) / length for x in normal)


def regular_cases():
    """Fixed 18 regular cells, declared before recovery/derivative evaluation."""
    rows = []
    radii = (0.4, 1.0, 2.7, 1.0, 2.7, 0.4)
    angles = (0.0, 37.0, 127.0, 251.0, 90.0, 213.0)
    fractions = (-0.25, 0.0, 0.25, 0.8, -0.4, 0.17)
    for kind in ("arc", "chord", "joint"):
        for index, (radius, angle, fraction) in enumerate(
            zip(radii, angles, fractions, strict=True)
        ):
            radians = math.radians(angle)
            normal = (math.cos(radians), math.sin(radians))
            if index == 4:
                normal = (0.6, 0.8)
            if index == 5:
                normal = (-0.6, -0.8)
            nx, ny = canonical_normal(normal)
            tx, ty = -ny, nx
            centre = (0.125 + 0.03125 * index, -0.25 + 0.015625 * index)
            if kind == "arc":
                # Opposite the chord; no truth-derived optimizer is involved.
                offset = (-0.95 * nx + 0.07 * tx, -0.95 * ny + 0.07 * ty)
                pitch = 0.4 * radius
            elif kind == "chord":
                offset = ((fraction + 0.03) * nx + 0.13 * tx, (fraction + 0.03) * ny + 0.13 * ty)
                pitch = 0.2 * radius
            else:
                half = math.sqrt((1 - fraction) * (1 + fraction))
                offset = (
                    (fraction + 0.03) * nx + (half + 0.02) * tx,
                    (fraction + 0.03) * ny + (half + 0.02) * ty,
                )
                pitch = 0.35 * radius
            rows.append(
                {
                    "name": f"{kind}-{index}",
                    "kind": kind,
                    "centre": centre,
                    "radius": radius,
                    "fraction": fraction,
                    "normal": normal,
                    "shape": (1, 1),
                    "origin": tuple(centre[j] + radius * offset[j] for j in (0, 1)),
                    "pitch": pitch,
                }
            )
    return rows


def grid_cases():
    rows = []
    for index, (centre, radius, fraction, angle, shape, origin, pitch) in enumerate(
        (
            ((0.23, -0.19), 2.7, -0.4, 37.0, (15, 15), (-3.5, -3.5), 0.5),
            ((-0.13, 0.21), 1.4, 0.25, 127.0, (12, 12), (-2.0, -2.0), 0.4),
            ((0.125, -0.25), 0.7, -0.7, None, (13, 13), (-1.5, -1.5), 0.25),
            ((-0.2, 0.14), 1.9, 0.8, 251.0, (15, 15), (-2.6, -2.6), 0.4),
        )
    ):
        normal = (
            (0.6, 0.8)
            if angle is None
            else (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
        )
        rows.append(
            {
                "name": f"grid-{index}",
                "centre": centre,
                "radius": radius,
                "fraction": fraction,
                "normal": normal,
                "shape": shape,
                "origin": origin,
                "pitch": pitch,
            }
        )
    return rows


def special_cases():
    return [
        {
            "name": "coincident-left",
            "centre": (0.0, 0.0),
            "radius": 2.0,
            "fraction": 0.0,
            "normal": (1.0, 0.0),
            "shape": (1, 1),
            "origin": (0.5, 0.0),
            "pitch": 1.0,
            "expected": "nondifferentiable",
        },
        {
            "name": "coincident-bottom",
            "centre": (0.0, 0.0),
            "radius": 2.0,
            "fraction": 0.0,
            "normal": (0.0, 1.0),
            "shape": (1, 1),
            "origin": (0.0, 0.5),
            "pitch": 1.0,
            "expected": "nondifferentiable",
        },
        {
            "name": "near-coincidence-inside",
            "centre": (0.0, 0.0),
            "radius": 2.0,
            "fraction": 0.0,
            "normal": (1.0, 0.0),
            "shape": (1, 1),
            "origin": (0.5 - 1e-8, 0.0),
            "pitch": 1.0,
            "expected": "resolved_or_unresolved",
        },
        {
            "name": "near-coincidence-outside",
            "centre": (0.0, 0.0),
            "radius": 2.0,
            "fraction": 0.0,
            "normal": (1.0, 0.0),
            "shape": (1, 1),
            "origin": (0.5 + 1e-8, 0.0),
            "pitch": 1.0,
            "expected": "resolved_or_unresolved",
        },
        {
            "name": "isolated-circle-tangent",
            "centre": (0.0, 0.0),
            "radius": 1.0,
            "fraction": 0.5,
            "normal": (-1.0, 0.0),
            "shape": (1, 1),
            "origin": (1.5, 0.0),
            "pitch": 1.0,
            "expected": "resolved_zero_or_unresolved",
        },
        {
            "name": "isolated-chord-corner",
            "centre": (0.0, 0.0),
            "radius": 2.0,
            "fraction": 0.0,
            "normal": (0.6, 0.8),
            "shape": (1, 1),
            "origin": (0.5, 0.5),
            "pitch": 1.0,
            "expected": "resolved_zero_or_unresolved",
        },
        {
            "name": "fraction-minus-one",
            "centre": (0.0, 0.0),
            "radius": 1.0,
            "fraction": -1.0,
            "normal": (0.6, 0.8),
            "shape": (1, 1),
            "origin": (0.1, 0.2),
            "pitch": 1.0,
            "expected": "parameter_endpoint",
        },
        {
            "name": "fraction-plus-one",
            "centre": (0.0, 0.0),
            "radius": 1.0,
            "fraction": 1.0,
            "normal": (-0.6, -0.8),
            "shape": (1, 1),
            "origin": (0.1, 0.2),
            "pitch": 1.0,
            "expected": "parameter_endpoint",
        },
        {
            "name": "large-world-small-cell",
            "centre": (1e8 + 0.125, -1e8 - 0.25),
            "radius": 0.001,
            "fraction": 0.17,
            "normal": (0.6, 0.8),
            "shape": (1, 1),
            "origin": (1e8 + 0.125 - 0.00095, -1e8 - 0.25 + 0.00007),
            "pitch": 1e-5,
            "expected": "resolved_or_unresolved",
        },
        {
            "name": "multiple-circle-spans",
            "centre": (0.0, 0.0),
            "radius": 1.0,
            "fraction": 0.8,
            "normal": (1.0, 0.0),
            "shape": (1, 1),
            "origin": (0.0, 0.0),
            "pitch": 1.8,
            "expected": "resolved_with_boundary",
        },
        {
            "name": "budget-before-cellwork",
            "centre": (0.125, -0.25),
            "radius": 1.0,
            "fraction": 0.17,
            "normal": (0.6, 0.8),
            "shape": (2, 2),
            "origin": (0.0, 0.0),
            "pitch": 0.5,
            "max_work": 3,
            "expected": "work_limit",
        },
    ]


@lru_cache(maxsize=4)
def rule(order):
    import numpy as np

    nodes, weights = np.polynomial.legendre.leggauss(order)
    return tuple(map(float, nodes)), tuple(map(float, weights))


def cell_bounds(case, row=0, col=0):
    step = Fraction(case["pitch"])
    cx = Fraction(case["origin"][0]) + col * step
    cy = Fraction(case["origin"][1]) + row * step
    return (cx - step / 2, cy - step / 2, cx + step / 2, cy + step / 2)


def local_bounds(bounds, centre):
    # Subtraction precedes conversion; large-world small cells stay distinct.
    return tuple(
        float(Fraction(value) - Fraction(centre[axis]))
        for value, axis in zip(bounds, (0, 1, 0, 1), strict=True)
    )


def positive_slice_area(bounds, *, centre, radius, fraction, stored_normal, angle=0.0, order=96):
    """Independent positive vertical area integral; no Green/production helpers.

    The represented canonical m is frozen before perturbations. Theta rotates m;
    neither theta nor f perturbations are renormalized by the API's input path.
    """
    mx, my = stored_normal
    cosine, sine = math.cos(angle), math.sin(angle)
    mx, my = cosine * mx - sine * my, sine * mx + cosine * my
    length = math.hypot(mx, my)
    g = fraction / length
    x0, y0, x1, y1 = local_bounds(bounds, centre)
    if g <= -1:
        return 0.0
    lo, hi = max(x0, -radius), min(x1, radius)
    if my == 0:
        cut = radius * fraction / mx
        if mx > 0:
            hi = min(hi, cut)
        else:
            lo = max(lo, cut)
    if lo >= hi:
        return 0.0
    cuts = [lo, hi]
    for y in (y0, y1):
        if abs(y) < radius:
            reach = math.sqrt((radius - abs(y)) * (radius + abs(y)))
            cuts.extend((-reach, reach))
        if mx != 0:
            cuts.append((radius * fraction - my * y) / mx)
    if -1 < g < 1:
        ux, uy = mx / length, my / length
        half = math.sqrt((1 - g) * (1 + g))
        cuts.extend((radius * (g * ux - half * uy), radius * (g * ux + half * uy)))
    angles = sorted({math.asin(max(-1.0, min(1.0, x / radius))) for x in cuts if lo <= x <= hi})
    nodes, weights = rule(order)
    pieces = []
    for left, right in pairwise(angles):
        panels = max(1, math.ceil((right - left) / (math.pi / 32)))
        for panel in range(panels):
            a = left + (right - left) * panel / panels
            b = left + (right - left) * (panel + 1) / panels
            mid, halfwidth = (a + b) / 2, (b - a) / 2
            terms = []
            for node, weight in zip(nodes, weights, strict=True):
                parameter = mid + halfwidth * node
                x, reach = radius * math.sin(parameter), radius * math.cos(parameter)
                lower, upper = max(y0, -reach), min(y1, reach)
                if my != 0:
                    chord = (radius * fraction - mx * x) / my
                    if my > 0:
                        upper = min(upper, chord)
                    else:
                        lower = max(lower, chord)
                terms.append(weight * max(0.0, upper - lower) * reach)
            pieces.append(halfwidth * math.fsum(terms))
    return math.fsum(pieces)


def boundary_quadrature(bounds, *, centre, radius, fraction, stored_normal, order=64):
    """Independent arc/chord flux quadrature, not endpoint antiderivatives."""
    mx, my = stored_normal
    length = math.hypot(mx, my)
    ux, uy = mx / length, my / length
    tx, ty = -uy, ux
    g = fraction / length
    x0, y0, x1, y1 = local_bounds(bounds, centre)
    cuts = {0.0, math.tau}
    for value in (x0 / radius, x1 / radius):
        if -1 < value < 1:
            alpha = math.acos(value)
            cuts.update((alpha, math.tau - alpha))
    for value in (y0 / radius, y1 / radius):
        if -1 < value < 1:
            alpha = math.asin(value)
            cuts.update((alpha % math.tau, (math.pi - alpha) % math.tau))
    if -1 < g < 1:
        alpha, direction = math.acos(g), math.atan2(uy, ux)
        cuts.update(((direction - alpha) % math.tau, (direction + alpha) % math.tau))
    nodes, weights = rule(order)
    terms = [[] for _ in ORDER]
    for a, b in pairwise(sorted(cuts)):
        mid = (a + b) / 2
        vx, vy = math.cos(mid), math.sin(mid)
        if not (
            x0 <= radius * vx <= x1 and y0 <= radius * vy <= y1 and mx * vx + my * vy <= fraction
        ):
            continue
        half = (b - a) / 2
        for node, weight in zip(nodes, weights, strict=True):
            angle = mid + half * node
            factor = radius * half * weight
            for column, velocity in enumerate((math.cos(angle), math.sin(angle), 1.0, 0.0, 0.0)):
                terms[column].append(factor * velocity)
    if -1 < g < 1:
        reach = radius * math.sqrt((1 - g) * (1 + g))
        lower, upper = -reach, reach
        for start, tangent, low, high in (
            (radius * g * ux, tx, x0, x1),
            (radius * g * uy, ty, y0, y1),
        ):
            if tangent == 0:
                if not low <= start <= high:
                    lower, upper = 1.0, 0.0
            else:
                ends = sorted(((low - start) / tangent, (high - start) / tangent))
                lower, upper = max(lower, ends[0]), min(upper, ends[1])
        if lower < upper:
            mid, half = (lower + upper) / 2, (upper - lower) / 2
            for node, weight in zip(nodes, weights, strict=True):
                s = mid + half * node
                for column, velocity in enumerate((ux, uy, g, radius / length, -s)):
                    terms[column].append(half * weight * velocity)
    return tuple(math.fsum(column) for column in terms)


def reference_checks(case, candidate_jacobian):
    """Retain all raw area orders/steps; estimated order guards are not proofs."""
    pitch = case["pitch"]
    scales = (pitch, pitch, pitch, 1.0, 1.0)
    area = pitch * pitch
    bounds = cell_bounds(case)
    normal = canonical_normal(case["normal"])
    boundary_vectors = {
        order: boundary_quadrature(
            bounds,
            centre=case["centre"],
            radius=case["radius"],
            fraction=case["fraction"],
            stored_normal=normal,
            order=order,
        )
        for order in SETTINGS["boundary_orders"]
    }
    checks = []
    for column, scale in enumerate(scales):
        orders = {}
        for order in SETTINGS["area_orders"]:
            steps = {}
            for divisor in (1, 2):
                h = SETTINGS["fd_step"] / divisor
                values = []
                for sign in (-1, 1):
                    centre, radius, fraction, angle = (
                        list(case["centre"]),
                        case["radius"],
                        case["fraction"],
                        0.0,
                    )
                    if column < 2:
                        centre[column] = Fraction(centre[column]) + Fraction(sign * h * scale)
                    elif column == 2:
                        radius += sign * h * scale
                    elif column == 3:
                        fraction += sign * h
                    else:
                        angle = sign * h
                    values.append(
                        positive_slice_area(
                            bounds,
                            centre=centre,
                            radius=radius,
                            fraction=fraction,
                            stored_normal=normal,
                            angle=angle,
                            order=order,
                        )
                    )
                steps[str(divisor)] = {
                    "minus_area": values[0],
                    "plus_area": values[1],
                    "scaled_derivative": (values[1] - values[0]) / (2 * h * area),
                }
            orders[str(order)] = steps
        low, high = orders["64"], orders["96"]
        propagated = max(
            (
                abs(high[str(divisor)]["plus_area"] - low[str(divisor)]["plus_area"])
                + abs(high[str(divisor)]["minus_area"] - low[str(divisor)]["minus_area"])
            )
            / (2 * (SETTINGS["fd_step"] / divisor) * area)
            for divisor in (1, 2)
        )
        coarse, fine = high["1"]["scaled_derivative"], high["2"]["scaled_derivative"]
        richardson = (4 * fine - coarse) / 3
        raw_actual = float(candidate_jacobian[column])
        actual = raw_actual * scale if math.isfinite(raw_actual) else None
        boundary = {
            str(order): boundary_vectors[order][column] * scale / area
            for order in SETTINGS["boundary_orders"]
        }
        boundary_delta = abs(boundary["64"] - boundary["32"])
        fd_limit = SETTINGS["candidate_fd_absolute"] + SETTINGS["candidate_fd_relative"] * abs(
            richardson
        )
        boundary_limit = SETTINGS["candidate_boundary_absolute"] + SETTINGS[
            "candidate_boundary_relative"
        ] * abs(boundary["64"])
        flags = {
            "area_order": propagated <= SETTINGS["area_propagated_order_limit"],
            "step": abs(fine - coarse) <= SETTINGS["fd_step_delta_limit"],
            "candidate_fd": actual is not None and abs(actual - richardson) <= fd_limit,
            "boundary_order": boundary_delta <= SETTINGS["boundary_order_limit"],
            "candidate_boundary": actual is not None
            and abs(actual - boundary["64"]) <= boundary_limit,
        }
        checks.append(
            {
                "parameter": ORDER[column],
                "scale": scale,
                "candidate_scaled": actual,
                "raw_area_orders": orders,
                "noncancelling_area_order_error": propagated,
                "step_delta": abs(fine - coarse),
                "richardson": richardson,
                "fd_limit": fd_limit,
                "boundary_orders": boundary,
                "boundary_order_delta": boundary_delta,
                "boundary_limit": boundary_limit,
                "flags": flags,
                "passed": all(flags.values()),
            }
        )
    return {
        "stored_normal": normal,
        "stored_normal_squared_exact": str(sum((Fraction(x) ** 2 for x in normal), Fraction())),
        "columns": checks,
        "passed": all(x["passed"] for x in checks),
    }


def candidate_record(result, case):
    import numpy as np

    shape = tuple(case["shape"])
    if (
        any(
            array.dtype != np.dtype("float64")
            for array in (result.coverage, result.jacobian, result.estimated_absolute_error)
        )
        or result.error_estimate_is_certified is not False
    ):
        raise ValueError("candidate dtype/error-qualification contract is malformed")
    if (
        result.coverage.shape != shape
        or result.jacobian.shape != (*shape, 5)
        or result.estimated_absolute_error.shape != (*shape, 5)
        or tuple(result.parameter_order) != ORDER
    ):
        raise ValueError("candidate result shapes/parameter order are malformed")
    if len(result.statuses) != math.prod(shape):
        raise ValueError("candidate result status census is malformed")
    known = {"resolved", "nondifferentiable", "parameter_endpoint", "unresolved", "work_limit"}
    cells = []
    for index, status in enumerate(result.statuses):
        if status not in known:
            raise ValueError("unknown candidate status")
        jacobian = result.jacobian.reshape(-1, 5)[index]
        errors = result.estimated_absolute_error.reshape(-1, 5)[index]
        if status == "resolved" and not np.isfinite(jacobian).all():
            raise ValueError("nonfinite resolved derivative")
        if status != "resolved" and not np.isnan(jacobian).all():
            raise ValueError("unknown derivative is not withheld")
        if status == "resolved" and not (np.isfinite(errors).all() and (errors >= 0).all()):
            raise ValueError("invalid resolved error estimate")
        if status != "resolved" and not np.isnan(errors).all():
            raise ValueError("unknown derivative error is not withheld")
        coverage = float(result.coverage.flat[index])
        if not (math.isnan(coverage) and status != "resolved") and not (
            math.isfinite(coverage) and 0 <= coverage <= 1
        ):
            raise ValueError("invalid candidate coverage")
        cells.append(
            {
                "status": status,
                "coverage": None if math.isnan(coverage) else coverage,
                "jacobian": [float(x) for x in jacobian] if status == "resolved" else None,
                "estimated_absolute_error": [float(x) for x in errors]
                if status == "resolved"
                else None,
            }
        )
    for key in ("required_work", "performed_work", "numeric_workspace_bound_bytes"):
        value = getattr(result, key)
        if type(value) is not int or value < 0:
            raise ValueError(f"invalid candidate {key}")
    if (
        result.required_work != math.prod(shape)
        or not 0 <= result.performed_work <= result.required_work
    ):
        raise ValueError("invalid candidate cell-work accounting")
    return {
        "cells": cells,
        "input_sha256": result.input_sha256,
        "required_work": result.required_work,
        "performed_work": result.performed_work,
        "numeric_workspace_bound_bytes": result.numeric_workspace_bound_bytes,
        "shape": shape,
        "parameter_order": ORDER,
    }


def options(case):
    return {
        key: case[key]
        for key in ("centre", "radius", "fraction", "normal", "shape", "origin", "pitch")
    }


def special_pass(case, record):
    statuses = [cell["status"] for cell in record["cells"]]
    expected = case["expected"]
    if expected == "work_limit":
        return all(status == expected for status in statuses) and record["performed_work"] == 0
    if expected in {"nondifferentiable", "parameter_endpoint"}:
        return all(status == expected for status in statuses)
    if expected == "resolved_with_boundary":
        return all(status == "resolved" for status in statuses)
    if not all(status in {"resolved", "unresolved"} for status in statuses):
        return False
    if expected == "resolved_zero_or_unresolved":
        return all(
            cell["jacobian"] is None or max(map(abs, cell["jacobian"])) <= 2e-9
            for cell in record["cells"]
        )
    return True


def full_grid_expectation(case):
    mx, my = canonical_normal(case["normal"])
    length = math.hypot(mx, my)
    g, radius = case["fraction"] / length, case["radius"]
    area = radius**2 * (math.acos(-g) + g * math.sqrt((1 - g) * (1 + g)))
    return area, (
        0.0,
        0.0,
        2 * area / radius,
        2 * radius**2 * math.sqrt((1 - g) * (1 + g)) / length,
        0.0,
    )


def special_boundary_check(case, result):
    """Accuracy for resolved near-contact/large-coordinate specials, not FD."""
    normal = canonical_normal(case["normal"])
    scales = (case["pitch"],) * 3 + (1.0, 1.0)
    orders = {
        order: boundary_quadrature(
            cell_bounds(case),
            centre=case["centre"],
            radius=case["radius"],
            fraction=case["fraction"],
            stored_normal=normal,
            order=order,
        )
        for order in SETTINGS["boundary_orders"]
    }
    rows = []
    for column, scale in enumerate(scales):
        low, high = (
            orders[order][column] * scale / case["pitch"] ** 2
            for order in SETTINGS["boundary_orders"]
        )
        raw = float(result.jacobian[0, 0, column])
        actual = raw * scale if math.isfinite(raw) else None
        limit = SETTINGS["candidate_boundary_absolute"] + SETTINGS[
            "candidate_boundary_relative"
        ] * abs(high)
        rows.append(
            {
                "parameter": ORDER[column],
                "candidate_scaled": actual,
                "boundary_low": low,
                "boundary_high": high,
                "limit": limit,
                "passed": actual is not None
                and abs(high - low) <= SETTINGS["boundary_order_limit"]
                and abs(actual - high) <= limit,
            }
        )
    # Unknown remains a retained allowed event/precision outcome, never an
    # accuracy pass or an invented zero. Reference values are still retained.
    resolved = result.statuses == ("resolved",)
    return {
        "columns": rows,
        "accuracy_qualified": resolved and all(row["passed"] for row in rows),
        "unknown_retained": not resolved,
        "passed": not resolved or all(row["passed"] for row in rows),
    }


def invariant_checks(case, baseline, call):
    """Frame and partition identities; actual candidate results retained per call."""
    import numpy as np

    h, w = case["shape"]
    cx, cy = case["centre"]
    ox, oy = case["origin"]
    nx, ny = case["normal"]
    pitch = case["pitch"]
    variants = [
        (
            "translation",
            {**case, "centre": (cx + 1024, cy - 2048), "origin": (ox + 1024, oy - 2048)},
        ),
        (
            "rotation90",
            {
                **case,
                "centre": (-cy, cx),
                "normal": (-ny, nx),
                "shape": (w, h),
                "origin": (-oy - (h - 1) * pitch, ox),
            },
        ),
        (
            "reflection",
            {
                **case,
                "centre": (-cx, cy),
                "normal": (-nx, ny),
                "origin": (-ox - (w - 1) * pitch, oy),
            },
        ),
        (
            "scale2",
            {
                **case,
                "centre": (2 * cx, 2 * cy),
                "radius": 2 * case["radius"],
                "origin": (2 * ox, 2 * oy),
                "pitch": 2 * pitch,
            },
        ),
        (
            "subdivision",
            {
                **case,
                "shape": (2 * h, 2 * w),
                "origin": (ox - pitch / 4, oy - pitch / 4),
                "pitch": pitch / 2,
            },
        ),
        ("complement", {**case, "normal": (-nx, -ny), "fraction": -case["fraction"]}),
    ]
    if case["name"] == "grid-2":
        variants.append(
            (
                "large_translation",
                {**case, "centre": (cx + 1e8, cy - 1e8), "origin": (ox + 1e8, oy - 1e8)},
            )
        )
    rows = []
    for kind, variant in variants:
        try:
            result = call(**options(variant))
            record = candidate_record(result, variant)
            target_coverage = baseline.coverage.copy()
            target_jacobian = baseline.jacobian.copy()
            actual_coverage, actual_jacobian = result.coverage, result.jacobian
            if kind == "rotation90":
                target_coverage = np.rot90(target_coverage, -1)
                target_jacobian = np.rot90(target_jacobian, -1).copy()
                target_jacobian[..., 0], target_jacobian[..., 1] = (
                    -target_jacobian[..., 1].copy(),
                    target_jacobian[..., 0].copy(),
                )
            elif kind == "reflection":
                target_coverage = target_coverage[:, ::-1]
                target_jacobian = target_jacobian[:, ::-1].copy()
                target_jacobian[..., 0] *= -1
                target_jacobian[..., 4] *= -1
            elif kind == "scale2":
                target_jacobian[..., :3] /= 2
            elif kind == "subdivision":
                actual_coverage = actual_coverage.reshape(h, 2, w, 2).mean(axis=(1, 3))
                actual_jacobian = actual_jacobian.reshape(h, 2, w, 2, 5).mean(axis=(1, 3))
            elif kind == "complement":
                # Independent full-disk flux per clipped cell; production endpoints
                # are deliberately withheld and are not invoked as a disk oracle.
                disk_coverage = np.empty((h, w), dtype=float)
                disk_jacobian = np.empty((h, w, 5), dtype=float)
                for i in range(h):
                    for j in range(w):
                        bounds = cell_bounds(case, i, j)
                        disk_coverage[i, j] = (
                            positive_slice_area(
                                bounds,
                                centre=case["centre"],
                                radius=case["radius"],
                                fraction=1.0,
                                stored_normal=(1.0, 0.0),
                                order=96,
                            )
                            / pitch**2
                        )
                        disk_jacobian[i, j] = (
                            np.asarray(
                                boundary_quadrature(
                                    bounds,
                                    centre=case["centre"],
                                    radius=case["radius"],
                                    fraction=1.0,
                                    stored_normal=(1.0, 0.0),
                                    order=64,
                                )
                            )
                            / pitch**2
                        )
                actual_coverage = actual_coverage + baseline.coverage
                actual_jacobian = actual_jacobian.copy()
                actual_jacobian[..., :3] += baseline.jacobian[..., :3]
                # f changes sign under complement; theta does not.
                actual_jacobian[..., 3] -= baseline.jacobian[..., 3]
                actual_jacobian[..., 4] += baseline.jacobian[..., 4]
                target_coverage, target_jacobian = disk_coverage, disk_jacobian
            coverage_delta = (
                float(np.max(np.abs(actual_coverage - target_coverage)))
                if np.isfinite(actual_coverage).all() and np.isfinite(target_coverage).all()
                else None
            )
            errors = np.abs(actual_jacobian - target_jacobian)
            limits = SETTINGS["invariant_absolute"] + SETTINGS["invariant_relative"] * np.abs(
                target_jacobian
            )
            passed = (
                all(status == "resolved" for status in result.statuses)
                and bool(np.all(errors <= limits))
                and coverage_delta is not None
                and coverage_delta <= SETTINGS["invariant_absolute"]
            )
            rows.append(
                {
                    "kind": kind,
                    "case": variant,
                    "candidate": record,
                    "coverage_max_delta": coverage_delta,
                    "jacobian_max_delta": [
                        float(np.max(errors[..., k])) if np.isfinite(errors[..., k]).all() else None
                        for k in range(5)
                    ],
                    "passed": bool(passed),
                }
            )
        except Exception as error:  # noqa: BLE001 -- retain every later frame/partition call.
            rows.append(
                {
                    "kind": kind,
                    "case": variant,
                    "status": "execution_failure",
                    "passed": False,
                    "error": {
                        "type": type(error).__name__,
                        "message": str(error),
                        "traceback": traceback.format_exc(),
                    },
                }
            )
    return {"rows": rows, "passed": all(row["passed"] for row in rows)}


def strict_safe(value):
    if isinstance(value, dict):
        return {str(key): strict_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [strict_safe(item) for item in value]
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise TypeError("unsafe or nonfinite diagnostic payload")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    out = args.output_dir.absolute()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():
        parser.error("output directory must be fresh with an existing parent")
    paths = (
        PLAN,
        "backend/__init__.py",
        "backend/finite_aperture.py",
        "backend/finite_aperture_sensitivity.py",
        "backend/finite_acquisition.py",
        "backend/finite_acquisition_linear.py",
        "tests/test_finite_aperture_sensitivity.py",
        "tests/test_finite_acquisition_linear.py",
        "tests/test_finite_acquisition_sensitivity.py",
        "studies/verification/finite-cell-sensitivity-v1.py",
    )
    before = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for path in paths:
        if (
            hashlib.sha256(
                subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
            ).hexdigest()
            != before[path]
        ):
            parser.error(f"governing source is not committed: {path}")
    plan = json.loads((ROOT / PLAN).read_text())
    out.mkdir()
    cases = (
        [("regular", case) for case in regular_cases()]
        + [("grid", case) for case in grid_cases()]
        + [("special", case) for case in special_cases()]
    )
    rows = [
        {"family": family, "case": case, "status": "not_attempted", "passed": False}
        for family, case in cases
    ]
    report = {
        "format": "finite-cell-sensitivity-study-v1",
        "source_commit": commit,
        "source_before": before,
        "source_after": {},
        "source_unchanged": False,
        "plan_sha256": before[PLAN],
        "plan": plan,
        "settings": SETTINGS,
        "rows": rows,
        "errors": [],
        "passed": False,
        "scope": "Smooth geometric area family around the stored canonicalized normal; no rounded acquisition derivative, inverse optimizer, renderer or camera qualification.",
    }
    try:
        if (
            plan["settings"] != SETTINGS
            or plan["population"]["regular_cells"] != len(regular_cases())
            or plan["population"]["whole_grids"] != len(grid_cases())
            or plan["population"]["special_cases"] != len(special_cases())
        ):
            raise ValueError("frozen plan settings/population differ from the runner")
        sys.path.insert(0, str(ROOT))
        import numpy as np

        from backend.finite_aperture_sensitivity import segment_cell_sensitivity

        report["versions"] = {"python": sys.version, "numpy": np.__version__}
        report["api_calls"] = {"attempted": 0, "returned": 0}

        def call(**kwargs):
            report["api_calls"]["attempted"] += 1
            value = segment_cell_sensitivity(**kwargs)
            report["api_calls"]["returned"] += 1
            return value

        for row, (family, case) in zip(rows, cases, strict=True):
            print(f"starting {family} {case['name']}", file=sys.stderr, flush=True)
            try:
                result = call(
                    **options(case),
                    **({"max_work": case["max_work"]} if "max_work" in case else {}),
                )
                record = candidate_record(result, case)
                row["candidate"] = record
                if family == "regular":
                    reference = reference_checks(case, result.jacobian[0, 0])
                    row["independent_reference"] = reference
                    passed = (
                        all(x["status"] == "resolved" for x in record["cells"])
                        and reference["passed"]
                    )
                elif family == "grid":
                    expected_area, expected_jacobian = full_grid_expectation(case)
                    area = (
                        math.fsum(float(x) for x in result.coverage.flat) * case["pitch"] ** 2
                        if np.isfinite(result.coverage).all()
                        else None
                    )
                    summed = tuple(
                        math.fsum(float(x) for x in result.jacobian[..., column].flat)
                        * case["pitch"] ** 2
                        if np.isfinite(result.jacobian[..., column]).all()
                        else None
                        for column in range(5)
                    )
                    flags = [
                        actual is not None
                        and abs(actual - expected)
                        <= SETTINGS["invariant_absolute"]
                        + SETTINGS["invariant_relative"] * abs(expected)
                        for actual, expected in zip(summed, expected_jacobian, strict=True)
                    ]
                    area_flag = area is not None and abs(area - expected_area) <= SETTINGS[
                        "invariant_absolute"
                    ] + SETTINGS["invariant_relative"] * abs(expected_area)
                    row["whole_grid"] = {
                        "area": area,
                        "expected_area": expected_area,
                        "summed_jacobian": summed,
                        "expected_jacobian": expected_jacobian,
                        "flags": flags,
                        "area_passed": area_flag,
                    }
                    row["invariants"] = invariant_checks(case, result, call)
                    passed = (
                        all(x["status"] == "resolved" for x in record["cells"])
                        and all(flags)
                        and area_flag
                        and row["invariants"]["passed"]
                    )
                else:
                    passed = special_pass(case, record)
                    if case["expected"] == "resolved_with_boundary":
                        reference = reference_checks(case, result.jacobian[0, 0])
                        row["independent_reference"] = reference
                        passed = passed and reference["passed"]
                    elif case["expected"] == "resolved_or_unresolved":
                        row["independent_boundary"] = special_boundary_check(case, result)
                        passed = passed and row["independent_boundary"]["passed"]
                row.update(status="evaluated", passed=bool(passed))
                strict_safe(row)
            except Exception as error:  # noqa: BLE001 -- retain the complete fixed population.
                # Preserve completed safe scientific stages. A malformed field
                # is explicitly withheld, never converted to a fake float.
                for key, value in list(row.items()):
                    try:
                        strict_safe(value)
                    except (TypeError, ValueError):
                        row[key] = {"withheld": True, "reason": "unsafe diagnostic payload"}
                row.update(
                    status="execution_failure",
                    passed=False,
                    error={
                        "type": type(error).__name__,
                        "message": str(error),
                        "traceback": traceback.format_exc(),
                    },
                )
    except Exception as error:  # noqa: BLE001 -- known census survives bootstrap failure.
        report["errors"].append(
            {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            }
        )
    finally:
        for path in paths:
            try:
                report["source_after"][path] = hashlib.sha256(
                    (ROOT / path).read_bytes()
                ).hexdigest()
            except OSError as error:
                report["source_after"][path] = None
                report["errors"].append(
                    {
                        "stage": "source_after",
                        "path": path,
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                )
        report["source_unchanged"] = before == report["source_after"]
        report["passed"] = bool(
            not report["errors"]
            and report["source_unchanged"]
            and all(row["passed"] for row in rows)
        )
        report["summary"] = {
            family: {
                "total": sum(row["family"] == family for row in rows),
                "passed": sum(row["family"] == family and row["passed"] for row in rows),
            }
            for family in ("regular", "grid", "special")
        }
        records = [
            row["candidate"]
            for row in rows
            if isinstance(row.get("candidate"), dict) and "cells" in row["candidate"]
        ]
        records += [
            variant["candidate"]
            for row in rows
            for variant in row.get("invariants", {}).get("rows", [])
            if "candidate" in variant
        ]
        report["candidate_status_census"] = {
            status: sum(cell["status"] == status for record in records for cell in record["cells"])
            for status in (
                "resolved",
                "nondifferentiable",
                "parameter_endpoint",
                "unresolved",
                "work_limit",
            )
        }
        report["candidate_record_work"] = {
            key: sum(record[key] for record in records)
            for key in ("required_work", "performed_work")
        }
        with (out / "report.json").open("x") as stream:
            json.dump(strict_safe(report), stream, allow_nan=False, indent=2, sort_keys=True)
            stream.write("\n")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "summary": report["summary"],
                "output": str(out / "report.json"),
            },
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
