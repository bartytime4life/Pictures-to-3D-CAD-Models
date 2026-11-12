"""Finite-material Gaussian means at declared working-image pixel centres.

This developer operator integrates the whole supplied material, including holes,
before resampling. Geometry, projective map and spatially constant Gaussian PSF
are supplied hypotheses. It neither estimates camera calibration nor changes a
trace. The caller supplies simple analytic rings with contained, disjoint holes;
closure/orientation checks here do not certify their exact analytic topology.

After Cholesky whitening, Gaussian mass is the radial Green flux
    integral [-expm1(-s/2)/s] * cross(u, du) / (2*pi), s = dot(u,u).
The removable coefficient at s=0 is 1/2. Far panels retain angular winding and
bound only the omitted Gaussian remainder. Near panels must first resolve a
bounded whitened travel distance; quadrature agreement alone cannot accept a
missed narrow feature. Float geometry guards and embedded-rule errors remain
engineering estimates, not certified integration or physical uncertainty.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from backend.fitting import arc_geometry

MAX_POINTS = 2048
MAX_SEGMENTS = 128
MAX_PANELS = 8192
MAX_EVALUATIONS = 20_000_000
_EPS = np.finfo(float).eps
_TAU = math.tau
_RULES = {order: np.polynomial.legendre.leggauss(order) for order in (12, 24)}


@dataclass(frozen=True)
class FiniteShapeResult:
    probabilities: tuple[float | None, ...]
    statuses: tuple[str, ...]
    estimated_errors: tuple[float | None, ...]
    tail_bounds: tuple[float, ...]
    evaluations: int
    panels: int
    chart_margin: float
    reflected: bool
    topology_validated: bool = False
    quadrature_certified: bool = False


def _integer(value, low, high, name):
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, (int, np.integer))
        or not low <= value <= high
    ):
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    return int(value)


def _array(value, shape, name, *, limit=1e12):
    if np.shape(value) != shape or np.iscomplexobj(value):
        raise ValueError(f"{name} must have shape {shape}")
    result = np.asarray(value, dtype=float)
    if not np.isfinite(result).all() or np.max(np.abs(result)) > limit:
        raise ValueError(f"{name} must be finite and bounded")
    return result


def _point(value):
    return _array(value, (2,), "boundary point")


@dataclass(frozen=True)
class _Curve:
    centre: np.ndarray
    delta: np.ndarray | None
    radius: float
    angle: float
    sweep: float
    sign: float

    def at(self, t):
        t = np.atleast_1d(t)
        if self.delta is not None:
            q = self.centre + t[:, None] * self.delta
            derivative = np.broadcast_to(self.delta, q.shape)
        else:
            angle = self.angle + self.sweep * t
            q = self.centre + self.radius * np.column_stack((np.cos(angle), np.sin(angle)))
            derivative = self.radius * self.sweep * np.column_stack((-np.sin(angle), np.cos(angle)))
        return q, derivative

    def range(self, row, start, end):
        """Engineering outward cover of a linear functional on the ENTIRE panel."""
        constant = float(row[:2] @ self.centre + row[2])
        if self.delta is not None:
            rate = float(row[:2] @ self.delta)
            values = (constant + start * rate, constant + end * rate)
            scale = abs(row[:2]) @ abs(self.centre) + abs(row[2]) + abs(rate)
        else:
            a, b = self.angle + self.sweep * start, self.angle + self.sweep * end
            angles = [a, b]
            lo, hi = sorted((a, b))
            phase = math.atan2(row[1], row[0])
            first = math.ceil((lo - phase) / math.pi)
            for k in range(first, first + 4):
                angle = phase + k * math.pi
                if lo <= angle <= hi:
                    angles.append(angle)
            values = [
                constant + self.radius * (row[0] * math.cos(t) + row[1] * math.sin(t))
                for t in angles
            ]
            scale = abs(row[:2]) @ abs(self.centre) + abs(row[2])
            scale += self.radius * math.hypot(*row[:2])
        pad = 64 * _EPS * max(1.0, float(scale))
        return math.nextafter(min(values) - pad, -math.inf), math.nextafter(
            max(values) + pad, math.inf
        )

    def rate(self, row):
        if self.delta is not None:
            return abs(float(row[:2] @ self.delta)) * (1 + 32 * _EPS)
        return self.radius * abs(self.sweep) * math.hypot(*row[:2]) * (1 + 32 * _EPS)


def _boundary(rings):
    if not isinstance(rings, (tuple, list)) or not 1 <= len(rings) <= 33:
        raise ValueError("supply one outer ring and at most 32 holes")
    if any(not isinstance(r, (tuple, list)) or not r for r in rings):
        raise ValueError("boundary rings must be nonempty sequences")
    if sum(map(len, rings)) > MAX_SEGMENTS:
        raise ValueError("finite boundary exceeds 128 analytic segments")
    first = rings[0][0]
    if not isinstance(first, (tuple, list)) or len(first) < 2:
        raise ValueError("use canonical line/arc/circle tuples")
    origin = _point(first[1]).copy()
    curves = []
    for ring_index, ring in enumerate(rings):
        local, ends, area_terms = [], [], []
        for segment in ring:
            if not isinstance(segment, (tuple, list)) or not segment:
                raise ValueError("use canonical line/arc/circle tuples")
            kind = segment[0]
            if kind == "circle":
                if len(ring) != 1 or len(segment) != 3:
                    raise ValueError("a circle must describe a whole ring alone")
                centre = _point(segment[1]) - origin
                radius = float(segment[2])
                if isinstance(segment[2], (bool, np.bool_)) or not 0 < radius <= 1e9:
                    raise ValueError("circle radius must be finite, positive and bounded")
                local.append(_Curve(centre, None, radius, 0.0, _TAU, 1.0))
                area_terms.append(math.pi * radius**2)
                continue
            if kind not in {"line", "arc"} or len(segment) != (3 if kind == "line" else 4):
                raise ValueError("use canonical line/arc/circle tuples")
            points = [_point(p) - origin for p in segment[1:]]
            a, b = points[0], points[-1]
            if np.array_equal(a, b):
                raise ValueError("a segment cannot have coincident endpoints")
            ends.append((a, b))
            area_terms.append(float(a[0] * b[1] - a[1] * b[0]) / 2)
            if kind == "line":
                local.append(_Curve(a, b - a, 0.0, 0.0, 0.0, 1.0))
            else:
                centre, radius, angle, sweep = arc_geometry(*points)
                if not (math.isfinite(radius) and 0 < radius <= 1e9 and 0 < abs(sweep) < _TAU):
                    raise ValueError("arc is not numerically supported")
                local.append(_Curve(np.asarray(centre), None, radius, angle, sweep, 1.0))
                area_terms.append(radius**2 * (sweep - math.sin(sweep)) / 2)
        if ends and any(not np.array_equal(a[1], b[0]) for a, b in zip(ends, ends[1:] + ends[:1])):
            raise ValueError("analytic rings must close exactly without invented joins")
        area = math.fsum(area_terms)
        guard = 128 * _EPS * max(1.0, math.fsum(map(abs, area_terms)))
        if abs(area) <= guard:
            raise ValueError("ring orientation is numerically unresolved")
        sign = (1 if ring_index == 0 else -1) * math.copysign(1, area)
        curves.extend(_Curve(c.centre, c.delta, c.radius, c.angle, c.sweep, sign) for c in local)
    return curves, origin


def _geometry(rings, homography, psf_covariance):
    curves, origin = _boundary(rings)
    h = _array(homography, (3, 3), "homography", limit=math.inf).copy()
    scale = float(np.max(np.abs(h)))
    if scale == 0:
        raise ValueError("homography must be invertible")
    h /= scale
    singular = np.linalg.svd(h, compute_uv=False)
    if singular[-1] <= 64 * _EPS * singular[0]:
        raise ValueError("homography is numerically singular")
    h[:, 2] += h[:, :2] @ origin
    ranges = [curve.range(h[2], 0, 1) for curve in curves]
    if max(high for _, high in ranges) < 0:
        h = -h
        ranges = [(-high, -low) for low, high in ranges]
    low, high = min(a for a, _ in ranges), max(b for _, b in ranges)
    if not math.isfinite(low) or low <= 0 or not math.isfinite(high):
        raise ValueError("finite shape crosses or cannot resolve a projective horizon")
    covariance = _array(psf_covariance, (2, 2), "PSF covariance")
    if not np.array_equal(covariance, covariance.T):
        raise ValueError("PSF covariance must be symmetric positive definite")
    try:
        factor = np.linalg.cholesky(covariance)
        inverse = np.linalg.solve(factor, np.eye(2))
    except np.linalg.LinAlgError as exc:
        raise ValueError("PSF covariance must be symmetric positive definite") from exc
    if (
        not np.isfinite(inverse).all()
        or np.max(np.abs(inverse)) > 1e12
        or np.linalg.cond(factor) > 1e8
    ):
        raise ValueError("PSF covariance is numerically unsupported")
    reflected = bool(np.linalg.det(h) < 0)
    return curves, h, inverse, low / max(high, np.finfo(float).tiny), reflected


def _panel(curve, matrix, denominator, start, end):
    wlo, whi = curve.range(denominator, start, end)
    if wlo <= 0:
        raise ArithmeticError("unresolved panel chart")
    bounds, rates = [], []
    wrate = curve.rate(denominator)
    for row in matrix:
        nlo, nhi = curve.range(row, start, end)
        ratios = (nlo / wlo, nlo / whi, nhi / wlo, nhi / whi)
        lo, hi = min(ratios), max(ratios)
        bounds.append((lo, hi))
        rates.append((curve.rate(row) + max(abs(lo), abs(hi)) * wrate) / wlo)
    distance = math.hypot(*(max(lo, -hi, 0.0) for lo, hi in bounds))
    length = (end - start) * math.hypot(*rates)
    if not all(math.isfinite(v) for v in (distance, length)):
        raise ArithmeticError("unsupported panel scale")
    return distance, length


def _at(curve, matrix, denominator, t):
    q, derivative = curve.at(t)
    w, rate = q @ denominator[:2] + denominator[2], derivative @ denominator[:2]
    u = (q @ matrix[:, :2].T + matrix[:, 2]) / w[:, None]
    velocity = (derivative @ matrix[:, :2].T - u * rate[:, None]) / w[:, None]
    if not np.isfinite(u).all() or not np.isfinite(velocity).all():
        raise ArithmeticError("nonfinite transformed curve")
    return u, velocity


def _quadrature(curve, matrix, denominator, start, end, order):
    nodes, weights = _RULES[order]
    half = (end - start) / 2
    u, velocity = _at(curve, matrix, denominator, (start + end) / 2 + half * nodes)
    squared = np.sum(u * u, axis=1)
    coefficient = np.full_like(squared, 0.5)
    nonzero = squared > 0
    coefficient[nonzero] = -np.expm1(-squared[nonzero] / 2) / squared[nonzero]
    flux = coefficient * (u[:, 0] * velocity[:, 1] - u[:, 1] * velocity[:, 0])
    terms = half * weights * flux / _TAU
    return math.fsum(terms), math.fsum(abs(terms))


def _one(point, curves, h, inverse, tolerance, max_panels, evaluations_left):
    matrix = inverse @ (h[:2] - point[:, None] * h[2])
    pending = [(curve, 0.0, 1.0) for curve in reversed(curves)]
    values, errors, tails = [], [], []
    panels, evaluations = 0, 0
    leaf_tolerance = tolerance / (2 * max_panels)
    while pending:
        if panels >= max_panels or evaluations + 2 > evaluations_left:
            return None, "work_limit", None, math.fsum(tails), evaluations, panels
        curve, start, end = pending.pop()
        panels += 1
        evaluations += 2
        try:
            distance, length = _panel(curve, matrix, h[2], start, end)
            endpoints, _ = _at(curve, matrix, h[2], [start, end])
        except (ArithmeticError, FloatingPointError):
            return None, "numerical", None, math.fsum(tails), evaluations, panels
        if distance > 0:
            a, b = endpoints
            angle = math.atan2(a[0] * b[1] - a[1] * b[0], float(a @ b))
            # A whole-panel box excludes the origin, hence stays in one open
            # half-plane: principal endpoint angle is its complete angular turn.
            exponent = -(distance * distance) / 2
            tail = (math.exp(exponent) if exponent > -745 else 5e-324) * length / distance / _TAU
            roundoff = 64 * _EPS * (abs(angle) + min(length / distance, 1e12)) / _TAU
            if tail + roundoff <= leaf_tolerance:
                values.append(curve.sign * angle / _TAU)
                errors.append(tail + roundoff)
                tails.append(tail)
                continue
        if length <= 0.5:
            if evaluations + 36 > evaluations_left:
                return None, "work_limit", None, math.fsum(tails), evaluations, panels
            evaluations += 36
            try:
                low, _ = _quadrature(curve, matrix, h[2], start, end, 12)
                high, absolute = _quadrature(curve, matrix, h[2], start, end, 24)
            except (ArithmeticError, FloatingPointError):
                return None, "numerical", None, math.fsum(tails), evaluations, panels
            error = abs(high - low) + 64 * _EPS * absolute
            if error <= leaf_tolerance:
                values.append(curve.sign * high)
                errors.append(error)
                continue
        mid = (start + end) / 2
        if mid in (start, end):
            return None, "numerical", None, math.fsum(tails), evaluations, panels
        pending.extend(((curve, mid, end), (curve, start, mid)))
    value, error = math.fsum(values), math.fsum(errors)
    error += 64 * _EPS * math.fsum(map(abs, values))
    if not (math.isfinite(value) and math.isfinite(error)):
        return None, "numerical", None, math.fsum(tails), evaluations, panels
    if value < -error or value > 1 + error:
        return None, "invalid_winding", error, math.fsum(tails), evaluations, panels
    return value, "resolved", error, math.fsum(tails), evaluations, panels


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
):
    """Numerical means for a supplied valid finite material, never accepted CAD.

    pixels_xy are unique integer working-image indices; observations are at +.5.
    The complete finite shape is projected before Gaussian integration, without
    sensor clipping. This assumes a lens-free supplied homography, point detector,
    constant levels and constant supplied raw-coordinate covariance. Unsupported
    optics, aperture, radiometry, pose error and visible walls need other models.

    Every query is retained. Input errors raise ValueError; exhausted/numerically
    unresolved queries return None with a status. No probability is silently
    clipped. Numerical estimates are not formal bounds or physical confidence.
    """
    if np.shape(sensor_shape) != (2,):
        raise ValueError("sensor_shape needs height and width")
    height, width = (_integer(v, 1, 10**9, "sensor dimension") for v in sensor_shape)
    shape = np.shape(pixels_xy)
    if len(shape) != 2 or shape[1] != 2 or not 1 <= shape[0] <= MAX_POINTS:
        raise ValueError("supply 1-2048 unique integer working-image pixel indices")
    pixels = np.asarray(pixels_xy)
    if not np.issubdtype(pixels.dtype, np.integer) or np.issubdtype(pixels.dtype, np.bool_):
        raise ValueError("pixel indices must be integers")
    if np.any(pixels < 0) or np.any(pixels[:, 0] >= width) or np.any(pixels[:, 1] >= height):
        raise ValueError("pixels lie outside the declared working image")
    if len(np.unique(pixels, axis=0)) != len(pixels):
        raise ValueError("pixel indices must be unique")
    if isinstance(probability_tolerance, (bool, np.bool_)) or not (
        math.isfinite(probability_tolerance) and 1e-12 <= probability_tolerance <= 1e-3
    ):
        raise ValueError("probability_tolerance must be finite in [1e-12, 1e-3]")
    max_panels = _integer(max_panels, 1, MAX_PANELS, "max_panels")
    max_evaluations = _integer(max_evaluations, 1, MAX_EVALUATIONS, "max_evaluations")
    curves, h, inverse, margin, reflected = _geometry(rings, homography, psf_covariance)
    if reflected:
        curves = [_Curve(c.centre, c.delta, c.radius, c.angle, c.sweep, -c.sign) for c in curves]
    probabilities, statuses, errors, tails = [], [], [], []
    evaluations, panels = 0, 0
    for point in pixels.astype(float) + 0.5:
        value, status, error, tail, used, count = _one(
            point,
            curves,
            h,
            inverse,
            probability_tolerance,
            max_panels,
            max_evaluations - evaluations,
        )
        probabilities.append(value)
        statuses.append(status)
        errors.append(error)
        tails.append(tail)
        evaluations += used
        panels += count
    return FiniteShapeResult(
        tuple(probabilities),
        tuple(statuses),
        tuple(errors),
        tuple(tails),
        evaluations,
        panels,
        margin,
        reflected,
    )
