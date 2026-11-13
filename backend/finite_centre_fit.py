"""Local finite-material intensity fitting with unknown centre, radius and chord.

The fixed pixel ROI, chord normal, homography, Gaussian covariance and residual
transform are caller-supplied hypotheses. The transform is a deterministic metric
or linear statistic, not calibrated noise. Two bounded constant levels are shared
by every observation. No response, illumination gradient, pose or PSF is inferred.

The forward operator uses finite_shape's Green kernel, with shared-panel batch
evaluation for exactly affine maps and scalar fallback otherwise. The geometry
and bounded variable-projection search extend finite_shape_fit at c9daa2a; unlike
that fixed-centre prototype, all four (Cx,Cy,R,f) coordinates are fitted here.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, replace

import numpy as np

from . import finite_affine as affine
from . import finite_shape as finite

_EPS = np.finfo(float).eps
PARAMETER_ORDER = ("centre_x", "centre_y", "radius", "chord_fraction")


def _array(value, shape, name):
    if np.shape(value) != shape or np.iscomplexobj(value):
        raise ValueError(f"{name} must have shape {shape}")
    if any(isinstance(v, (bool, np.bool_)) for v in np.asarray(value, dtype=object).flat):
        raise ValueError(f"{name} must contain real numbers, not booleans")
    result = np.asarray(value, dtype=float)
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def _bounds(value, name, low, high):
    result = _array(value, (2,), name)
    a, b = map(float, result)
    if not low <= a < b <= high or math.nextafter(a, b) >= b:
        raise ValueError(
            f"{name} needs increasing bounds in [{low}, {high}] with an interior float"
        )
    return a, b


def _pixels(pixels_xy, sensor_shape):
    if np.shape(sensor_shape) != (2,):
        raise ValueError("sensor_shape needs height and width")
    height, width = (finite._integer(v, 1, 10**9, "sensor dimension") for v in sensor_shape)
    pixels = np.asarray(pixels_xy)
    if (
        pixels.ndim != 2
        or pixels.shape[1] != 2
        or not 1 <= len(pixels) <= 2048
        or pixels.dtype.kind not in "iu"
        or any(isinstance(v, (bool, np.bool_)) for v in np.asarray(pixels_xy, dtype=object).flat)
        or len(np.unique(pixels, axis=0)) != len(pixels)
        or np.any(pixels < 0)
        or np.any(pixels[:, 0] >= width)
        or np.any(pixels[:, 1] >= height)
    ):
        raise ValueError("supply 1..2048 unique in-frame integer pixel pairs")
    return pixels.copy(), (height, width)


def _normal(value):
    result = _array(value, (2,), "normal")
    length = math.hypot(*result)
    if abs(length - 1) > 64 * _EPS:
        raise ValueError("supply a fixed unit chord normal")
    return result / length


def circular_segment_ring(radius, chord_fraction, *, centre=(0.0, 0.0), normal=(1.0, 0.0)):
    """Boundary of disc(C,R) intersect {n dot (x-C) <= R*f}; no inferred joins."""
    centre, normal = _array(centre, (2,), "centre"), _normal(normal)
    radius, fraction = _array([radius, chord_fraction], (2,), "radius/fraction")
    if np.max(np.abs(centre)) > 1e9 or not 1e-3 <= radius <= 1e6 or not -0.999 <= fraction <= 0.999:
        raise ValueError("unsupported circular-segment geometry")
    tangent = np.array([-normal[1], normal[0]])
    half = radius * math.sqrt((1 - fraction) * (1 + fraction))
    chord = centre + radius * fraction * normal
    start, end = chord + half * tangent, chord - half * tangent
    middle = centre - radius * normal
    return [("arc", tuple(start), tuple(middle), tuple(end)), ("line", tuple(end), tuple(start))]


def _segment_geometry(radius, fraction, centre, normal, homography, covariance):
    centre = _array(centre, (2,), "centre")
    radius, fraction = _array([radius, fraction], (2,), "radius/fraction")
    if np.max(np.abs(centre)) > 1e9 or not 1e-3 <= radius <= 1e6 or not -0.999 <= fraction <= 0.999:
        raise ValueError("unsupported circular-segment geometry")
    angle = math.atan2(normal[1], normal[0]) + math.acos(fraction)
    sweep = math.tau - 2 * math.acos(fraction)
    start = radius * np.array([math.cos(angle), math.sin(angle)])
    end = radius * np.array([math.cos(angle + sweep), math.sin(angle + sweep)])
    curves = [
        finite._Curve(np.zeros(2), None, radius, angle, sweep, 1.0),
        finite._Curve(end, start - end, 0.0, 0.0, 0.0, 1.0),
    ]
    return finite._geometry_curves(curves, centre, homography, covariance)


def _controls(probability_tolerance, max_panels, max_evaluations):
    tolerance = float(_array([probability_tolerance], (1,), "probability_tolerance")[0])
    if not 1e-12 <= tolerance <= 1e-3:
        raise ValueError("probability_tolerance must lie in [1e-12, 1e-3]")
    panels = finite._integer(max_panels, 1, finite.MAX_PANELS, "max_panels")
    work = finite._integer(max_evaluations, 1, finite.MAX_EVALUATIONS, "max_evaluations")
    return tolerance, panels, work


def circular_segment_probabilities(
    pixels_xy,
    radius,
    chord_fraction,
    *,
    centre,
    normal=(1.0, 0.0),
    sensor_shape,
    homography,
    psf_covariance,
    probability_tolerance=1e-8,
    max_panels=4096,
    max_evaluations=2_000_000,
):
    """Finite D probabilities for the ACTUAL parameters, not a rounded 3-point circle.

    Fixed integer-pixel centres and all finite_shape numerical/status semantics
    apply. Exactly affine maps share curve panels across queries; every attempted
    query-node remains charged and unsupported paths use the scalar evaluator.
    """
    pixels, _ = _pixels(pixels_xy, sensor_shape)
    normal = _normal(normal)
    homography = _array(homography, (3, 3), "homography").copy()
    covariance = _array(psf_covariance, (2, 2), "psf_covariance").copy()
    controls = _controls(probability_tolerance, max_panels, max_evaluations)
    geometry = _segment_geometry(radius, chord_fraction, centre, normal, homography, covariance)
    # Classify the supplied snapshot, before homogeneous normalization can
    # underflow a nonzero perspective coefficient. The scalar path owns all
    # projective cases, even when their represented perspective is very small.
    if np.all(homography[2, :2] == 0):
        result = affine._probabilities(pixels, geometry, *controls)
        # Keep this existing API's result type and serialized schema stable.
        # Batch-specific diagnostics remain available through finite_affine.
        return finite.FiniteShapeResult(
            result.probabilities,
            result.statuses,
            result.estimated_errors,
            result.tail_bounds,
            result.evaluations,
            result.panels,
            result.chart_margin,
            result.reflected,
            result.topology_validated,
            result.quadrature_certified,
        )
    return finite._probabilities(pixels, geometry, *controls)


@dataclass(frozen=True)
class ShapeJacobian:
    jacobian: tuple[tuple[float, float, float, float] | None, ...]
    statuses: tuple[str, ...]
    estimated_errors: tuple[float | None, ...]
    evaluations: int
    panels: int
    method: str = "boundary_shape"
    quadrature_certified: bool = False


def _jacobian_one(
    point,
    curves,
    origin,
    h,
    inverse,
    centre,
    radius,
    fraction,
    normal,
    tolerance,
    max_panels,
    evaluations_left,
):
    """Reynolds boundary derivative; the moving corner has zero area measure."""
    matrix = inverse @ (h[:2] - point[:, None] * h[2])
    density_factor = abs(float(np.linalg.det(inverse))) / math.tau
    map_determinant = abs(float(np.linalg.det(h)))
    pending = [(curve, 0.0, 1.0) for curve in reversed(curves)]
    values, errors, panels, evaluations = [], [], 0, 0
    leaf = tolerance / (2 * max_panels)

    def quadrature(curve, start, end, order):
        nodes, weights = finite._RULES[order]
        half = (end - start) / 2
        ts = (start + end) / 2 + half * nodes
        q, velocity = curve.at(ts)
        w = q @ h[2, :2] + h[2, 2]
        # Reuse this rule's curve samples while retaining _at's complete finite
        # guard, including its mapped velocity even though only u enters density.
        u = (q @ matrix[:, :2].T + matrix[:, 2]) / w[:, None]
        mapped_velocity = (velocity @ matrix[:, :2].T - u * (velocity @ h[2, :2])[:, None]) / w[
            :, None
        ]
        if not np.isfinite(u).all() or not np.isfinite(mapped_velocity).all():
            raise ArithmeticError("nonfinite transformed curve")
        density = density_factor * np.exp(-np.sum(u * u, axis=1) / 2)
        speed = np.hypot(velocity[:, 0], velocity[:, 1])
        if curve.delta is None:
            outward = (q - (centre - origin)) / radius
            motion = np.column_stack((outward, np.ones(len(q)), np.zeros(len(q))))
        else:
            motion = np.tile([*normal, fraction, radius], (len(q), 1))
        factor = density * map_determinant / w**3 * speed * weights * half
        terms = factor[:, None] * motion
        if not np.isfinite(terms).all():
            raise ArithmeticError("unsupported shape derivative")
        return np.sum(terms, axis=0), float(np.sum(np.abs(terms)))

    while pending:
        if panels >= max_panels or evaluations + 2 > evaluations_left:
            return None, "work_limit", None, evaluations, panels
        curve, start, end = pending.pop()
        panels += 1
        evaluations += 2
        try:
            distance, length = finite._panel(curve, matrix, h[2], start, end)
            wlo, _ = curve.range(h[2], start, end)
            speed = (
                math.hypot(*curve.delta)
                if curve.delta is not None
                else curve.radius * abs(curve.sweep)
            )
            maximum_motion = 1.0 if curve.delta is None else max(1.0, radius)
            bound = (
                density_factor
                * math.exp(-(distance**2) / 2)
                * map_determinant
                / wlo**3
                * speed
                * (end - start)
                * maximum_motion
            )
            if not math.isfinite(bound):
                raise ArithmeticError("unsupported derivative bound")
            if bound <= leaf:
                values.append(np.zeros(4))
                errors.append(bound)
                continue
            if length <= 0.5:
                if evaluations + 36 > evaluations_left:
                    return None, "work_limit", None, evaluations, panels
                evaluations += 36
                low, _ = quadrature(curve, start, end, 12)
                high, absolute = quadrature(curve, start, end, 24)
                error = float(np.max(np.abs(high - low))) + 64 * _EPS * absolute
                if error <= leaf:
                    values.append(high)
                    errors.append(error)
                    continue
        except (ArithmeticError, FloatingPointError, OverflowError):
            return None, "numerical", None, evaluations, panels
        mid = (start + end) / 2
        if mid in (start, end):
            return None, "numerical", None, evaluations, panels
        pending.extend(((curve, mid, end), (curve, start, mid)))
    result = np.sum(values, axis=0)
    error = math.fsum(errors) + 64 * _EPS * float(np.sum(np.abs(values)))
    if not np.isfinite(result).all() or not math.isfinite(error):
        return None, "numerical", None, evaluations, panels
    return tuple(map(float, result)), "resolved", error, evaluations, panels


def circular_segment_jacobian(
    pixels_xy,
    radius,
    chord_fraction,
    *,
    centre,
    normal=(1.0, 0.0),
    sensor_shape,
    homography,
    psf_covariance,
    probability_tolerance=1e-8,
    max_panels=4096,
    max_evaluations=2_000_000,
):
    """Probability derivatives in (Cx,Cy,R,f), under supplied fixed optics.

    Independent from differentiating the quadrature program. Adaptive Gaussian
    boundary integration has engineering error estimates, not certified bounds.
    There is no unreported numerical-derivative fallback.
    """
    pixels, _ = _pixels(pixels_xy, sensor_shape)
    normal = _normal(normal)
    homography = _array(homography, (3, 3), "homography").copy()
    covariance = _array(psf_covariance, (2, 2), "psf_covariance").copy()
    curves, h, inverse, _, _ = _segment_geometry(
        radius, chord_fraction, centre, normal, homography, covariance
    )
    origin = np.asarray(centre, dtype=float)
    tolerance, max_panels, limit = _controls(probability_tolerance, max_panels, max_evaluations)
    jacobian, statuses, errors = [], [], []
    work, panels = 0, 0
    for point in pixels.astype(float) + 0.5:
        value, status, error, used, count = _jacobian_one(
            point,
            curves,
            origin,
            h,
            inverse,
            np.asarray(centre),
            float(radius),
            float(chord_fraction),
            normal,
            tolerance,
            max_panels,
            limit - work,
        )
        jacobian.append(value)
        statuses.append(status)
        errors.append(error)
        work += used
        panels += count
    return ShapeJacobian(tuple(jacobian), tuple(statuses), tuple(errors), work, panels)


# Active-face enumeration is adapted from raw_source_fit._box_fit (701aa91).
# Direct SVD solves are used even on one-free-level faces; no normal equations.
def _box_fit(design, target, bounds):
    if not np.isfinite(design).all() or not np.isfinite(target).all():
        raise ValueError("bounded intensity fit requires finite arrays")
    levels, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    options = [levels] if np.all((levels >= bounds[0]) & (levels <= bounds[1])) else []
    for fixed, free in ((0, 1), (1, 0)):
        for bound in bounds:
            with np.errstate(over="ignore", invalid="ignore"):
                rhs = target - bound * design[:, fixed]
            if not np.isfinite(rhs).all():
                continue
            value = np.linalg.lstsq(design[:, free, None], rhs, rcond=None)[0][0]
            item = np.empty(2)
            item[fixed], item[free] = bound, np.clip(value, *bounds)
            options.append(item)
    best = None
    for levels in options:
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            residual = target - design @ levels
            cost = float(residual @ residual)
        if not np.isfinite(levels).all() or not math.isfinite(cost):
            continue
        maximum = float(np.max(np.abs(residual)))
        if cost == 0 and maximum != 0:
            continue
        if best is None or cost < best[0]:
            best = cost, levels, int(rank), maximum
    if best is None:
        raise ValueError("bounded intensity fit is numerically unsupported")
    return best


def _projected_jacobians(design, probability_derivative, levels, target, bounds):
    """Full fixed-active-face GP residual Jacobian and projected MEAN Jacobian.

    r=y-A beta. The second term -A_F^{+T}(A'_F)^T r is needed in the
    residual derivative; it must not create information in the mean Jacobian.
    """
    residual = target - design @ levels
    contrast = levels[1] - levels[0]
    mean = probability_derivative * contrast
    scale = max(map(abs, levels))
    guard = 256 * _EPS * scale
    free = (levels > bounds[0] + guard) & (levels < bounds[1] - guard)
    full = -mean.copy()
    if np.any(free):
        u, singular, vt = np.linalg.svd(design[:, free], full_matrices=False)
        cutoff = _EPS * max(design[:, free].shape) * singular[0]
        retained = singular > cutoff
        basis = u[:, retained]
        mean -= basis @ (basis.T @ mean)
        full = -mean.copy()
        # A' columns are [-dp,+dp], restricted to the free-level face.
        signs = np.array([-1.0, 1.0])[free]
        dtr = signs[:, None] * (probability_derivative.T @ residual)[None, :]
        full -= basis @ ((vt[retained] @ dtr) / singular[retained, None])
    return full, mean


@dataclass(frozen=True)
class CentreCandidate:
    centre: tuple[float, float]
    radius: float
    chord_fraction: float
    chord_offset: float
    levels: tuple[float, float]
    cost: float
    cost_lower_guard: float
    cost_upper_guard: float
    design_rank: int
    maximum_projected_residual: float
    forward_residual_error_estimate: float
    kind: str

    @property
    def parameters(self):
        return (*self.centre, self.radius, self.chord_fraction)


@dataclass(frozen=True)
class CentreFit:
    best: CentreCandidate | None
    candidates: tuple[CentreCandidate, ...]
    grid: tuple[CentreCandidate | None, ...]
    grid_statuses: tuple[str, ...]
    grid_shape: tuple[int, int, int, int]
    basins: tuple[dict, ...]
    evaluations: int
    forward_evaluations: int
    forward_panels: int
    derivative_calls: int
    residual_rank: int
    observation_count: int
    full_source_metric: bool
    flat: bool
    tied: bool
    endpoint: bool
    rank_deficient: bool
    geometry_rank: int | None
    geometry_condition: float | None
    unrefined_basins: int
    refinement_limited: bool
    work_exhausted: bool
    numerically_unsupported: bool
    raw_residual_l2: float | None
    transformed_residual_l2: float | None
    global_search_certified: bool = False
    psf_fitted: bool = False
    normal_fitted: bool = False
    derivative_method: str = "boundary_shape/full_fixed_face_variable_projection"


def _transform(value, count, max_evaluations):
    if value is None:
        return lambda x: x, lambda x: x, count
    shape = np.shape(value)
    if shape == (count,):
        weights = _array(value, shape, "residual_transform").copy()
        if np.any(weights < 0):
            raise ValueError("diagonal residual weights must be nonnegative")
        cutoff = _EPS * count * float(np.max(weights))
        rank = int(np.count_nonzero(weights > cutoff))
        return (
            lambda x: weights[:, None] * x if x.ndim == 2 else weights * x,
            lambda x: weights * x,
            rank,
        )
    if (
        len(shape) != 2
        or shape[1] != count
        or not 1 <= shape[0] <= 2048
        or shape[0] * count > 500_000
        or shape[0] * count * max_evaluations > 100_000_000
    ):
        raise ValueError("residual transform exceeds shape/work limits")
    matrix = _array(value, shape, "residual_transform").copy()
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.count_nonzero(singular > _EPS * max(shape) * singular[0]))
    absolute = np.abs(matrix)
    return lambda x: matrix @ x, lambda x: absolute @ x, rank


def fit_circular_segment(
    pixels_xy,
    raw_values,
    *,
    sensor_shape,
    homography,
    psf_covariance,
    centre_bounds,
    radius_bounds,
    chord_fraction_bounds,
    normal=(1.0, 0.0),
    level_bounds=(0.0, 255.0),
    residual_transform=None,
    grid_points=3,
    refinement_iterations=32,
    max_basins=8,
    max_evaluations=512,
    forward_work_limit=20_000_000,
    probability_tolerance=1e-8,
):
    """Bounded local centre/radius/chord fitting from ONE fixed integer-pixel ROI.

    Every coarse grid result and represented basin is retained. Bounds are supplied
    by the caller, not inferred from truth. A successful local solve does not certify
    all minima, response/PSF adequacy, topology, physical dimensions or uncertainty.
    The covariance and H use the observation frame of these pixels; an empirical
    rectified covariance is not a raw-camera PSF. Constant levels only.
    """
    pixels, sensor_shape = _pixels(pixels_xy, sensor_shape)
    values = _array(raw_values, (len(pixels),), "raw_values").copy()
    normal = _normal(normal)
    homography = _array(homography, (3, 3), "homography").copy()
    psf_covariance = _array(psf_covariance, (2, 2), "psf_covariance").copy()
    probability_tolerance = float(_array([probability_tolerance], (1,), "probability_tolerance")[0])
    if not 1e-12 <= probability_tolerance <= 1e-3:
        raise ValueError("probability_tolerance must lie in [1e-12, 1e-3]")
    if np.shape(centre_bounds) != (2, 2):
        raise ValueError("centre_bounds needs x/y pairs")
    domains = [_bounds(centre_bounds[k], f"centre_bounds[{k}]", -1e9, 1e9) for k in range(2)]
    domains += [
        _bounds(radius_bounds, "radius_bounds", 1e-3, 1e6),
        _bounds(chord_fraction_bounds, "chord_fraction_bounds", -0.999, 0.999),
    ]
    levels = _bounds(level_bounds, "level_bounds", -1e6, 1e6)
    grid_points = finite._integer(grid_points, 3, 5, "grid_points")
    refinement_iterations = finite._integer(refinement_iterations, 0, 64, "refinement_iterations")
    max_basins = finite._integer(max_basins, 0, 16, "max_basins")
    max_evaluations = finite._integer(max_evaluations, grid_points**4, 4096, "max_evaluations")
    forward_work_limit = finite._integer(forward_work_limit, 1, 100_000_000, "forward_work_limit")
    # C+R*S(f) is affine in C and positive R for fixed s. S(f) is nested
    # in f. Same-chart extreme-centre/R shapes at f_max cover the whole box.
    reflected = []
    for cx, cy, radius in itertools.product(*domains[:3]):
        reflected.append(
            _segment_geometry(radius, domains[3][1], (cx, cy), normal, homography, psf_covariance)[
                -1
            ]
        )
    if len(set(reflected)) != 1:
        raise ValueError("the geometry domain crosses a projective horizon")
    apply, error_apply, residual_rank = _transform(residual_transform, len(pixels), max_evaluations)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        target = apply(values)
        energy = float(target @ target)
    if (
        not np.isfinite(target).all()
        or not math.isfinite(energy)
        or (energy == 0 and np.any(target != 0))
    ):
        raise ValueError("transformed target is numerically unsupported")
    arithmetic = 256 * _EPS * energy
    low, high = np.array(domains)[:, 0], np.array(domains)[:, 1]
    span = high - low
    cache, means, jacobians = {}, {}, {}
    attempts = work = panels = derivative_calls = 0
    exhausted = unsupported = False

    def evaluate(position, kind):
        nonlocal attempts, work, panels, exhausted, unsupported
        key = tuple(map(float, position))
        if key in cache:
            item, status = cache[key]
            return (replace(item, kind=kind) if item else None), status
        if exhausted or attempts >= max_evaluations or work >= forward_work_limit:
            exhausted = True
            return None, "work_limit"
        attempts += 1
        try:
            result = circular_segment_probabilities(
                pixels,
                key[2],
                key[3],
                centre=key[:2],
                normal=normal,
                sensor_shape=sensor_shape,
                homography=homography,
                psf_covariance=psf_covariance,
                probability_tolerance=probability_tolerance,
                max_evaluations=min(2_000_000, forward_work_limit - work),
            )
            work += result.evaluations
            panels += result.panels
            if any(status != "resolved" for status in result.statuses):
                status = "work_limit" if "work_limit" in result.statuses else "numerical"
                exhausted |= status == "work_limit"
                unsupported |= status == "numerical"
                cache[key] = None, status
                return None, status
            p = np.asarray(result.probabilities)
            with np.errstate(over="ignore", invalid="ignore"):
                design = apply(np.column_stack((1 - p, p)))
            cost, coefficients, rank, maximum = _box_fit(design, target, levels)
            # Bound the supplied linear transform by |T| through its action on
            # nonnegative forward errors. Diagonal weights and identity are exact;
            # for a general signed T use its absolute matrix explicitly.
            errors = np.asarray(result.estimated_errors)
            with np.errstate(over="ignore", invalid="ignore"):
                projected_error = error_apply(errors)
            error = (levels[1] - levels[0]) * math.hypot(*projected_error)
            norm = math.sqrt(cost)
            upper = norm + error
            if (
                not math.isfinite(upper)
                or upper > math.sqrt(np.finfo(float).max)
                or (upper != 0 and upper * upper == 0)
            ):
                raise ValueError("unrepresentable forward/cost guard")
            upper_cost = upper * upper + arithmetic
            if not math.isfinite(upper_cost):
                raise ValueError("unrepresentable upper cost")
            item = CentreCandidate(
                key[:2],
                key[2],
                key[3],
                key[2] * key[3],
                tuple(map(float, coefficients)),
                cost,
                max(0.0, max(0.0, norm - error) ** 2 - arithmetic),
                upper_cost,
                rank,
                maximum,
                error,
                kind,
            )
        except (ValueError, ArithmeticError, np.linalg.LinAlgError):
            unsupported = True
            cache[key] = None, "numerical"
            return None, "numerical"
        means[key] = p, design
        cache[key] = item, "resolved"
        return item, "resolved"

    def derivatives(candidate):
        nonlocal work, panels, derivative_calls, exhausted, unsupported
        key = candidate.parameters
        if key in jacobians:
            return jacobians[key]
        if exhausted or work >= forward_work_limit:
            exhausted = True
            return None
        derivative_calls += 1
        try:
            result = circular_segment_jacobian(
                pixels,
                key[2],
                key[3],
                centre=key[:2],
                normal=normal,
                sensor_shape=sensor_shape,
                homography=homography,
                psf_covariance=psf_covariance,
                probability_tolerance=probability_tolerance,
                max_evaluations=min(finite.MAX_EVALUATIONS, forward_work_limit - work),
            )
        except (ValueError, ArithmeticError, np.linalg.LinAlgError):
            unsupported = True
            return None
        work += result.evaluations
        panels += result.panels
        if any(status != "resolved" for status in result.statuses):
            exhausted |= "work_limit" in result.statuses
            unsupported |= any(
                status not in ("resolved", "work_limit") for status in result.statuses
            )
            return None
        try:
            dp = apply(np.asarray(result.jacobian))
            with np.errstate(over="ignore", invalid="ignore"):
                full, mean = _projected_jacobians(
                    means[key][1], dp, np.asarray(candidate.levels), target, levels
                )
            if not np.isfinite(full).all() or not np.isfinite(mean).all():
                raise ValueError("unsupported projected derivative")
        except (ValueError, ArithmeticError, np.linalg.LinAlgError):
            unsupported = True
            return None
        # Projector cancellation must not manufacture information. Compare the
        # projected mean to its unprojected arithmetic scale, and retain the
        # residual-subspace dimension left after fitting FREE brightness levels.
        contrast = candidate.levels[1] - candidate.levels[0]
        reference = dp * contrast * span
        beta = np.asarray(candidate.levels)
        guard = 256 * _EPS * max(map(abs, beta))
        free = (beta > levels[0] + guard) & (beta < levels[1] - guard)
        free_rank = int(np.linalg.matrix_rank(means[key][1][:, free])) if np.any(free) else 0
        mean_error = (
            abs(contrast)
            * math.hypot(*error_apply(np.asarray(result.estimated_errors)))
            * math.hypot(*span)
        )
        if not math.isfinite(mean_error):
            unsupported = True
            return None
        jacobians[key] = (
            full * span,
            mean * span,
            float(np.linalg.norm(reference, 2)),
            free_rank,
            mean_error,
        )
        return jacobians[key]

    axes = [np.linspace(*domain, grid_points) for domain in domains]
    grid, statuses = [], []
    for position in itertools.product(*axes):
        item, status = evaluate(position, "grid")
        grid.append(item)
        statuses.append(status)
    numeric = [item for item in grid if item is not None]
    flat = bool(
        len(numeric) == len(grid)
        and max((c.cost for c in numeric), default=0) - min((c.cost for c in numeric), default=0)
        <= arithmetic
    )
    candidates, basins, seeds = list(numeric), [], []
    shape = (grid_points,) * 4
    for index in itertools.product(range(grid_points), repeat=4):
        item = grid[np.ravel_multi_index(index, shape)]
        if item is None:
            continue
        neighbours = [
            grid[np.ravel_multi_index(other, shape)]
            for other in itertools.product(
                *(range(max(0, k - 1), min(grid_points, k + 2)) for k in index)
            )
            if other != index
        ]
        if all(c is None or item.cost <= c.cost + arithmetic for c in neighbours):
            seeds.append(item)
    seeds.sort(key=lambda c: c.cost)
    converged_count = 0
    if not flat and refinement_iterations:
        for seed in seeds[:max_basins]:
            current, reason, iterations = seed, "iteration_limit", 0
            for iteration in range(refinement_iterations):
                iterations = iteration + 1
                derivative = derivatives(current)
                if derivative is None:
                    reason = "work_limit" if exhausted else "numerical"
                    break
                full = derivative[0]
                key = current.parameters
                residual = target - means[key][1] @ np.asarray(current.levels)
                scale = float(np.max(np.abs(full)))
                if scale == 0:
                    reason = "parameter_resolution"
                    break
                step = np.linalg.lstsq(
                    np.vstack((full / scale, 1e-4 * np.eye(4))),
                    np.r_[-residual / scale, np.zeros(4)],
                    rcond=None,
                )[0]
                if not np.isfinite(step).all():
                    unsupported, reason = True, "numerical"
                    break
                largest = float(np.max(np.abs(step)))
                if largest > 0.25:
                    step *= 0.25 / largest
                position = np.asarray(key)
                proposal = np.clip(position + span * step, low, high)
                if np.max(np.abs((proposal - position) / span)) < 1e-8:
                    reason = "parameter_resolution"
                    break  # retain CURRENT iterate before any cost trial
                accepted = False
                for power in range(12):
                    point = np.clip(position + 2.0**-power * span * step, low, high)
                    candidate, _ = evaluate(point, "refined_basin")
                    improvement = 64 * _EPS * max(current.cost, _EPS * energy)
                    if candidate is not None and candidate.cost < current.cost - improvement:
                        current, accepted = candidate, True
                        break
                    if exhausted:
                        break
                if not accepted:
                    reason = "work_limit" if exhausted else "no_descent"
                    break
            candidates.append(replace(current, kind="refined_basin"))
            basins.append(
                {
                    "seed_parameters": list(seed.parameters),
                    "parameters": list(current.parameters),
                    "status": reason,
                    "iterations": iterations,
                }
            )
            converged_count += reason == "parameter_resolution"
            if exhausted:
                break
    best = min(candidates, key=lambda c: c.cost) if candidates else None
    rank, condition, raw_norm, transformed_norm = None, None, None, None
    endpoint = tied = False
    if best is not None:
        position = np.asarray(best.parameters)
        endpoint = bool(
            np.any(np.minimum(abs(position - low), abs(position - high)) <= 64 * _EPS * span)
        )
        tied = any(
            np.max(np.abs((np.asarray(c.parameters) - position) / span)) > 1e-5
            and c.cost_lower_guard <= best.cost_upper_guard
            for c in candidates
        )
        if abs(best.levels[0] - best.levels[1]) <= 256 * _EPS * max(map(abs, best.levels)):
            rank = 0
        else:
            derivative = derivatives(best)
            if derivative is not None:
                singular = np.linalg.svd(derivative[1], compute_uv=False)
                cutoff = max(
                    derivative[4],
                    256 * _EPS * max(derivative[1].shape) * max(singular[0], derivative[2]),
                )
                rank = min(
                    int(np.count_nonzero(singular > cutoff)), max(0, residual_rank - derivative[3])
                )
                condition = float(singular[0] / singular[-1]) if rank == 4 else None
        predicted = means[best.parameters][1] @ np.asarray(best.levels)
        p = means[best.parameters][0]
        raw_residual = values - (best.levels[0] * (1 - p) + best.levels[1] * p)
        norms = [math.hypot(*raw_residual), math.hypot(*(target - predicted))]
        for i, value in enumerate(norms):
            if not math.isfinite(value):
                norms[i] = None
                unsupported = True
        raw_norm, transformed_norm = norms
    unrefined = len(seeds) - converged_count
    return CentreFit(
        best,
        tuple(candidates),
        tuple(grid),
        tuple(statuses),
        shape,
        tuple(basins),
        attempts,
        work,
        panels,
        derivative_calls,
        residual_rank,
        len(pixels),
        residual_rank == len(pixels),
        flat,
        bool(tied),
        endpoint,
        bool(best is not None and (best.design_rank < 2 or (rank is not None and rank < 4))),
        rank,
        condition,
        unrefined,
        bool(unrefined and not flat),
        exhausted,
        unsupported,
        raw_norm,
        transformed_norm,
    )
