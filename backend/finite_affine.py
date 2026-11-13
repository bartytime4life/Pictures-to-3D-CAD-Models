"""Opt-in shared-panel affine evaluation of the existing radial Green kernel.

The public fixed-integer observation and numerical status contracts are those
of finite_shape. Affine means EXACTLY zero represented
projective coefficients. Local analytic curves and per-query translations are
retained; this is not a polygon approximation or a different physical model.

Work is charged in the same boundary/query-node units as finite_shape: two
endpoints per attempted panel and 12+24 nodes for a near-panel rule pair. Sharing
curve geometry does not discount those query operations. Complete batches are
preflighted at their worst-case work, and failed batch work is charged before
scalar fallback. The workspace limit bounds declared NumPy batch arrays and a
conservative temporary allowance, not Python/process RSS or caller-owned input.
Quadrature errors/float guards remain engineering estimates, not certificates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import finite_shape as finite

DEFAULT_MEMORY_LIMIT = 16 * 1024 * 1024
MAX_MEMORY_LIMIT = 256 * 1024 * 1024
_EPS = np.finfo(float).eps
_TAU = math.tau


@dataclass(frozen=True)
class AffineDiagnostics:
    affine: bool
    batched_queries: int
    fallback_queries: int
    batch_evaluations: int
    fallback_evaluations: int
    batch_panels: int
    fallback_panels: int
    discarded_batch_queries: int
    workspace_peak_bytes: int
    memory_limit_bytes: int
    fallback_reasons: tuple[str, ...]
    work_unit: str = "boundary/query-node evaluations, including attempted/discarded work"


@dataclass(frozen=True)
class AffineShapeResult(finite.FiniteShapeResult):
    diagnostics: AffineDiagnostics | None = None


def _workspace(panel_count, query_count):
    # Three dense panel contribution arrays; query counters/coordinates/masks;
    # one pair of rules/endpoints/range temporaries. 8 KiB/query deliberately
    # exceeds the simultaneously live <=24-node arrays and indexing copies.
    return 8192 + query_count * (24 * panel_count + 8192)


def _partition(curves, linear, denominator, max_panels):
    plans = []
    for curve in curves:
        speed = math.hypot(*(curve.rate(np.r_[row, 0.0]) for row in linear)) / denominator
        if not math.isfinite(speed) or speed > 0.5 * max_panels:
            return None
        count = max(1, math.ceil(2 * speed * (1 + 64 * _EPS)))
        if len(plans) + count > max_panels:
            return None
        for i in range(count):
            start, end = i / count, (i + 1) / count
            length = (end - start) * speed
            if length > 0.5:
                return None
            plans.append((curve, start, end, length))
    return plans


def _ranges(curve, linear, constants, denominator, start, end):
    """Whole-panel affine covers, including EACH query's constant in the pad."""
    bounds = []
    for axis, row in enumerate(linear):
        constant = float(row @ curve.centre) + constants[:, axis]
        scale = float(abs(row) @ abs(curve.centre)) + abs(constants[:, axis])
        if curve.delta is not None:
            rate = float(row @ curve.delta)
            values = np.column_stack((constant + start * rate, constant + end * rate))
            scale += abs(rate)
        else:
            a, b = curve.angle + curve.sweep * start, curve.angle + curve.sweep * end
            lo, hi = sorted((a, b))
            angles = [a, b]
            phase = math.atan2(row[1], row[0])
            first = math.ceil((lo - phase) / math.pi)
            for k in range(first, first + 4):
                t = phase + k * math.pi
                if lo <= t <= hi:
                    angles.append(t)
            shifts = curve.radius * np.array(
                [row[0] * math.cos(t) + row[1] * math.sin(t) for t in angles]
            )
            values = constant[:, None] + shifts
            scale += curve.radius * math.hypot(*row)
        pad = 64 * _EPS * np.maximum(1.0, scale)
        low = np.nextafter((values.min(axis=1) - pad) / denominator, -math.inf)
        high = np.nextafter((values.max(axis=1) + pad) / denominator, math.inf)
        bounds.append(np.maximum(np.maximum(low, -high), 0.0))
    return np.hypot(*bounds)


def _coordinates(curve, linear, constants, denominator, t):
    q, derivative = curve.at(t)
    # The per-query constant was formed BEFORE whitening, so a large world
    # translation is not subtracted from a separately whitened world centre.
    u = (q @ linear.T + constants[:, None, :]) / denominator
    velocity = derivative @ linear.T / denominator
    if not np.isfinite(u).all() or not np.isfinite(velocity).all():
        raise ArithmeticError("nonfinite affine curve")
    return u, velocity


def _rule(curve, linear, constants, denominator, start, end, order):
    nodes, weights = finite._RULES[order]
    half = (end - start) / 2
    u, velocity = _coordinates(
        curve, linear, constants, denominator, (start + end) / 2 + half * nodes
    )
    squared = np.sum(u * u, axis=2)
    coefficient = np.full_like(squared, 0.5)
    nonzero = squared > 0
    coefficient[nonzero] = -np.expm1(-squared[nonzero] / 2) / squared[nonzero]
    flux = coefficient * (u[:, :, 0] * velocity[:, 1] - u[:, :, 1] * velocity[:, 0])
    terms = half * weights * flux / _TAU
    # Match the scalar kernel's cancellation-sensitive rule summation.
    return (
        np.array([math.fsum(row) for row in terms]),
        np.array([math.fsum(abs(row)) for row in terms]),
    )


def _batch(points, curves, plans, h, inverse, tolerance, max_panels):
    count, size = len(points), len(plans)
    values, errors, tails = (np.zeros((count, size)) for _ in range(3))
    used = np.zeros(count, dtype=np.int64)
    panels = np.zeros(count, dtype=np.int64)
    valid = np.ones(count, dtype=bool)
    denominator = float(h[2, 2])
    linear = inverse @ h[:2, :2]
    constants = (h[:2, 2] - points * denominator) @ inverse.T
    leaf = tolerance / (2 * max_panels)
    for j, (curve, start, end, length) in enumerate(plans):
        indices = np.flatnonzero(valid)
        if not len(indices):
            break
        c = constants[indices]
        used[indices] += 2
        panels[indices] += 1
        try:
            distance = _ranges(curve, linear, c, denominator, start, end)
            endpoints, _ = _coordinates(curve, linear, c, denominator, [start, end])
            if not np.isfinite(distance).all():
                raise ArithmeticError("nonfinite affine panel cover")
            far = distance > 0
            far_indices = np.flatnonzero(far)
            accepted = np.zeros(len(indices), dtype=bool)
            if len(far_indices):
                a, b = endpoints[far_indices, 0], endpoints[far_indices, 1]
                angle = np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], np.sum(a * b, axis=1))
                d = distance[far_indices]
                exponent = -d * d / 2
                exponential = np.full(len(d), 5e-324)
                representable = exponent > -745
                exponential[representable] = np.exp(exponent[representable])
                tail = exponential * length / d / _TAU
                error = tail + 64 * _EPS * (abs(angle) + np.minimum(length / d, 1e12)) / _TAU
                okay = error <= leaf
                accepted[far_indices[okay]] = True
                dest = indices[far_indices[okay]]
                values[dest, j] = curve.sign * angle[okay] / _TAU
                errors[dest, j], tails[dest, j] = error[okay], tail[okay]
            near = np.flatnonzero(~accepted)
            if len(near):
                dest = indices[near]
                used[dest] += 36
                low, _ = _rule(curve, linear, c[near], denominator, start, end, 12)
                high, absolute = _rule(curve, linear, c[near], denominator, start, end, 24)
                error = abs(high - low) + 64 * _EPS * absolute
                okay = np.isfinite(high) & np.isfinite(error) & (error <= leaf)
                values[dest[okay], j] = curve.sign * high[okay]
                errors[dest[okay], j] = error[okay]
                valid[dest[~okay]] = False
        except (ArithmeticError, FloatingPointError, OverflowError):
            valid[indices] = False
    results = []
    for i in range(count):
        if not valid[i]:
            results.append(None)
            continue
        value, error, tail = math.fsum(values[i]), math.fsum(errors[i]), math.fsum(tails[i])
        error += 64 * _EPS * math.fsum(abs(values[i]))
        if not all(math.isfinite(x) for x in (value, error, tail)):
            results.append(None)
        else:
            status = "invalid_winding" if value < -error or value > 1 + error else "resolved"
            results.append((value if status == "resolved" else None, status, error, tail))
    return results, used, panels


def _probabilities(
    pixels,
    geometry,
    probability_tolerance,
    max_panels,
    max_evaluations,
    *,
    memory_limit_bytes=DEFAULT_MEMORY_LIMIT,
    affine_allowed=True,
):
    """Validated queries/local curves; caller retains raw-homography eligibility."""
    memory = finite._integer(memory_limit_bytes, 1, MAX_MEMORY_LIMIT, "memory_limit_bytes")
    curves, h, inverse, margin, reflected = geometry
    if reflected:
        curves = [
            finite._Curve(c.centre, c.delta, c.radius, c.angle, c.sweep, -c.sign) for c in curves
        ]
    affine = bool(affine_allowed and np.all(h[2, :2] == 0))
    plans = _partition(curves, inverse @ h[:2, :2], float(h[2, 2]), max_panels) if affine else None
    values, statuses, errors, tails = [], [], [], []
    batch_work = fallback_work = batch_panels = fallback_panels = 0
    batched_queries = fallback_queries = discarded = peak = 0
    reasons = []
    index = 0
    while index < len(pixels):
        remaining = max_evaluations - batch_work - fallback_work
        group = 0
        if plans is not None:
            by_memory = max(0, (memory - 8192) // (24 * len(plans) + 8192))
            by_work = remaining // (38 * len(plans))
            group = min(len(pixels) - index, by_memory, by_work)
        if group:
            points = pixels[index : index + group].astype(float) + 0.5
            peak = max(peak, _workspace(len(plans), group))
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                result, work, counts = _batch(
                    points, curves, plans, h, inverse, probability_tolerance, max_panels
                )
            batch_work += int(np.sum(work))
            batch_panels += int(np.sum(counts))
        else:
            group = 1
            result, work, counts = [None], [0], [0]
            reason = (
                "nonaffine"
                if not affine
                else "partition_limit"
                if plans is None
                else "workspace_or_work_preflight"
            )
            if reason not in reasons:
                reasons.append(reason)
        for local in range(group):
            item = result[local]
            remaining = max_evaluations - batch_work - fallback_work
            # Do not report a precomputed later query resolved after global work
            # exhaustion at an earlier fallback. Its spent batch work stays charged.
            if (
                remaining < 2
                and item is not None
                and any(s == "work_limit" for s in statuses[-local:] if local)
            ):
                discarded += 1
                item = (None, "work_limit", None, 0.0)
            if item is None:
                fallback_queries += 1
                if work[local]:
                    discarded += 1
                    if "batch_numerical_or_rule" not in reasons:
                        reasons.append("batch_numerical_or_rule")
                value, status, error, tail, used, count = finite._one(
                    pixels[index + local].astype(float) + 0.5,
                    curves,
                    h,
                    inverse,
                    probability_tolerance,
                    max(0, max_panels - int(counts[local])),
                    remaining,
                )
                fallback_work += used
                fallback_panels += count
                item = value, status, error, tail
            else:
                batched_queries += 1
            value, status, error, tail = item
            values.append(value)
            statuses.append(status)
            errors.append(error)
            tails.append(tail)
        index += group
    diagnostics = AffineDiagnostics(
        affine,
        batched_queries,
        fallback_queries,
        batch_work,
        fallback_work,
        batch_panels,
        fallback_panels,
        discarded,
        peak,
        memory,
        tuple(reasons),
    )
    return AffineShapeResult(
        tuple(values),
        tuple(statuses),
        tuple(errors),
        tuple(tails),
        batch_work + fallback_work,
        batch_panels + fallback_panels,
        margin,
        reflected,
        diagnostics=diagnostics,
    )


def finite_shape_probabilities(
    pixels_xy,
    rings,
    *,
    sensor_shape,
    homography,
    psf_covariance,
    probability_tolerance=1e-8,
    max_panels=4096,
    max_evaluations=2_000_000,
    memory_limit_bytes=DEFAULT_MEMORY_LIMIT,
):
    """Opt-in affine batch evaluation; nonaffine/small-budget paths use old _one.

    Integer queries are at +.5, and the complete material is integrated without
    sensor clipping. Probability values are never clamped. See finite_shape for
    the unchanged conditional Gaussian, topology and non-certification limits.
    """
    if np.shape(sensor_shape) != (2,):
        raise ValueError("sensor_shape needs height and width")
    height, width = (finite._integer(v, 1, 10**9, "sensor dimension") for v in sensor_shape)
    pixels = np.asarray(pixels_xy)
    if (
        pixels.ndim != 2
        or pixels.shape[1] != 2
        or not 1 <= len(pixels) <= finite.MAX_POINTS
        or pixels.dtype.kind not in "iu"
        or any(isinstance(v, (bool, np.bool_)) for v in np.asarray(pixels_xy, dtype=object).flat)
        or len(np.unique(pixels, axis=0)) != len(pixels)
        or np.any(pixels < 0)
        or np.any(pixels[:, 0] >= width)
        or np.any(pixels[:, 1] >= height)
    ):
        raise ValueError("supply 1..2048 unique in-frame integer pixel pairs")
    if isinstance(probability_tolerance, (bool, np.bool_)) or not (
        math.isfinite(probability_tolerance) and 1e-12 <= probability_tolerance <= 1e-3
    ):
        raise ValueError("probability_tolerance must be finite in [1e-12, 1e-3]")
    panels = finite._integer(max_panels, 1, finite.MAX_PANELS, "max_panels")
    work = finite._integer(max_evaluations, 1, finite.MAX_EVALUATIONS, "max_evaluations")
    homography = finite._array(homography, (3, 3), "homography", limit=math.inf).copy()
    geometry = finite._geometry(rings, homography, psf_covariance)
    return _probabilities(
        pixels.copy(),
        geometry,
        probability_tolerance,
        panels,
        work,
        memory_limit_bytes=memory_limit_bytes,
        affine_allowed=bool(np.all(homography[2, :2] == 0)),
    )
