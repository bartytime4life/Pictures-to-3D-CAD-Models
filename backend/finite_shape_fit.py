"""Conditional source-intensity fitting of one finite circular segment.

The fixed pose, lens-free homography, point sampling, Gaussian covariance and
noise factor are supplied, never inferred from the saved profile's blur summary.
Radius and chord fraction are jointly searched; shared bounded background and
material levels are profiled at each geometry. All coarse grid cells and every
represented basin/face remain visible. Local refinement is not a global search
certificate, geometry acceptance or physical camera/print qualification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .finite_shape import _integer, finite_shape_probabilities
from .profile_observations import PixelNoise
from .raw_source_fit import _box_fit

_EPS = np.finfo(float).eps


def circular_segment_ring(radius, chord_fraction, *, centre=(0.0, 0.0), normal=(1.0, 0.0)):
    """Canonical boundary of disc(C,R) intersect {n dot (x-C) <= R*f}."""
    if isinstance(radius, (bool, np.bool_)) or isinstance(chord_fraction, (bool, np.bool_)):
        raise TypeError("radius and chord_fraction must be real numbers")
    radius, fraction = float(radius), float(chord_fraction)
    if not (math.isfinite(radius) and 1e-3 <= radius <= 1e6):
        raise ValueError("radius must be finite in [1e-3, 1e6]")
    if not (math.isfinite(fraction) and -0.999 <= fraction <= 0.999):
        raise ValueError("chord_fraction must be finite in [-.999, .999]")
    centre, normal = np.asarray(centre, dtype=float), np.asarray(normal, dtype=float)
    if (
        centre.shape != (2,)
        or normal.shape != (2,)
        or not np.isfinite(centre).all()
        or not np.isfinite(normal).all()
        or np.max(np.abs(centre)) > 1e9
        or abs(math.hypot(*normal) - 1) > 64 * _EPS
    ):
        raise ValueError("supply a bounded centre and a unit chord normal")
    tangent = np.array([-normal[1], normal[0]])
    half = radius * math.sqrt((1 - fraction) * (1 + fraction))
    chord = centre + radius * fraction * normal
    start, end, middle = chord + half * tangent, chord - half * tangent, centre - radius * normal
    return [("arc", tuple(start), tuple(middle), tuple(end)), ("line", tuple(end), tuple(start))]


@dataclass(frozen=True)
class CircularSegmentCandidate:
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


@dataclass(frozen=True)
class CircularSegmentFit:
    best: CircularSegmentCandidate | None
    candidates: tuple[CircularSegmentCandidate, ...]
    grid: tuple[CircularSegmentCandidate | None, ...]
    grid_statuses: tuple[str, ...]
    grid_shape: tuple[int, int]
    evaluations: int
    forward_evaluations: int
    forward_panels: int
    projection_rank: int
    raw_pixel_count: int
    flat: bool
    tied: bool
    endpoint: bool
    rank_deficient: bool
    geometry_rank: int | None
    geometry_condition: float | None
    unrefined_basins: int
    work_exhausted: bool
    numerically_unsupported: bool
    raw_residual_l2: float | None
    retained_residual_l2: float | None
    omitted_source_residual_l2: float | None
    global_search_certified: bool = False
    pose_fitted: bool = False
    psf_fitted: bool = False
    refinement_limited: bool = False


def _bounds(values, name, low, high):
    if np.shape(values) != (2,):
        raise ValueError(f"{name} needs two increasing finite endpoints")
    a, b = map(float, values)
    if not (math.isfinite(a) and math.isfinite(b) and low <= a < b <= high):
        raise ValueError(f"{name} must lie in [{low}, {high}]")
    if math.nextafter(a, b) >= b:
        raise ValueError(f"{name} must contain a representable interior point")
    return a, b


def fit_circular_segment(
    pixels_xy,
    raw_values,
    noise,
    *,
    sensor_shape,
    homography,
    psf_covariance,
    radius_bounds,
    chord_fraction_bounds,
    centre=(0.0, 0.0),
    normal=(1.0, 0.0),
    level_bounds=(0.0, 255.0),
    grid_points=5,
    refinement_iterations=32,
    max_basins=8,
    max_evaluations=512,
    forward_work_limit=20_000_000,
    probability_tolerance=1e-8,
):
    """Fit actual intensities under a declared fixed-pose finite-shape model.

    The rectangular search domain is (R, h/R), not (R,h). It always describes a
    valid circular segment. Geometry observations and metric are fixed for every
    candidate. PixelNoise.whiten_source retains its supplied source subspace;
    it is an all-pixel objective only if all source modes are retained.

    The numerical forward error is propagated through bounded contrast and the
    supplied noise scaling, separately from observation/model discrepancy.
    Those are estimates, so cost guards do not certify feasibility or confidence.
    No generic correct_blur is applied: blur already belongs in the mean.
    """
    if not isinstance(noise, PixelNoise):
        raise TypeError("noise must be a supplied PixelNoise factor")
    count, rank = noise.matrix.shape[1], noise.rank
    if (
        not 1 <= count <= 2048
        or not 1 <= rank <= min(noise.matrix.shape)
        or noise.right.shape != (rank, count)
        or noise.input_std.shape != (count,)
        or np.shape(pixels_xy) != (count, 2)
        or np.shape(raw_values) != (count,)
        or not np.isfinite(noise.right).all()
        or not np.isfinite(noise.input_std).all()
        or np.any(noise.input_std <= 0)
    ):
        raise ValueError("source pixels, values and supplied noise factor must agree")
    radii = _bounds(radius_bounds, "radius_bounds", 1e-3, 1e6)
    fractions = _bounds(chord_fraction_bounds, "chord_fraction_bounds", -0.999, 0.999)
    levels = _bounds(level_bounds, "level_bounds", -1e6, 1e6)
    grid_points = _integer(grid_points, 3, 11, "grid_points")
    refinement_iterations = _integer(refinement_iterations, 0, 64, "refinement_iterations")
    max_basins = _integer(max_basins, 0, 16, "max_basins")
    max_evaluations = _integer(max_evaluations, grid_points**2, 4096, "max_evaluations")
    forward_work_limit = _integer(forward_work_limit, 1, 100_000_000, "forward_work_limit")
    values = np.asarray(raw_values, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("source values must be finite")
    # S(f) is nested in f, and the projective denominator is affine in R
    # for each v in S(f_max). Check both extreme R shapes, on the same chart,
    # to cover the whole (R,f) box rather than only its lowest corner.
    charts = []
    for radius in radii:
        ring = circular_segment_ring(radius, fractions[1], centre=centre, normal=normal)
        charts.append(
            finite_shape_probabilities(
                pixels_xy,
                [ring],
                sensor_shape=sensor_shape,
                homography=homography,
                psf_covariance=psf_covariance,
                probability_tolerance=probability_tolerance,
                max_evaluations=1,
            ).reflected
        )
    if charts[0] != charts[1]:
        raise ValueError("the geometry domain crosses the projective horizon")
    target = noise.whiten_source(values)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        energy = float(target @ target)
    if not math.isfinite(energy) or (energy == 0 and np.any(target != 0)):
        raise ValueError("source target is numerically unsupported")
    arithmetic = float(256 * _EPS * energy)
    cache, source_means = {}, {}
    attempts, work, panels = 0, 0, 0
    exhausted, unsupported = False, False

    def evaluate(radius, fraction, kind):
        nonlocal attempts, work, panels, exhausted, unsupported
        key = float(radius), float(fraction)
        if key in cache:
            candidate, status = cache[key]
            return (replace(candidate, kind=kind) if candidate else None), status
        if attempts >= max_evaluations or work >= forward_work_limit:
            exhausted = True
            return None, "work_limit"
        attempts += 1
        try:
            ring = circular_segment_ring(*key, centre=centre, normal=normal)
            forward = finite_shape_probabilities(
                pixels_xy,
                [ring],
                sensor_shape=sensor_shape,
                homography=homography,
                psf_covariance=psf_covariance,
                probability_tolerance=probability_tolerance,
                max_evaluations=min(2_000_000, forward_work_limit - work),
            )
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            unsupported = True
            cache[key] = None, "numerical"
            return None, "numerical"
        work += forward.evaluations
        panels += forward.panels
        if any(status != "resolved" for status in forward.statuses):
            status = "work_limit" if "work_limit" in forward.statuses else "numerical"
            exhausted |= status == "work_limit"
            unsupported |= status != "work_limit"
            cache[key] = None, status
            return None, status
        probability = np.asarray(forward.probabilities)
        try:
            design = noise.whiten_source(np.column_stack((1 - probability, probability)))
            cost, coefficients, design_rank, maximum = _box_fit(design, target, levels)
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            unsupported = True
            cache[key] = None, "numerical"
            return None, "numerical"
        # right has orthonormal rows: ||right @ v|| <= ||v||. Use the maximum
        # allowed contrast, not only fitted contrast, to guard variable projection.
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            scaled_error = np.asarray(forward.estimated_errors) / noise.input_std
        error = (levels[1] - levels[0]) * math.hypot(*scaled_error)
        norm = math.sqrt(cost)
        upper = norm + error
        # Retain a numerical unknown when the requested squared-cost units
        # cannot represent the guard. Never emit infinity/NaN or underflow a
        # nonzero guard/residual into an exact zero-cost claim.
        if (
            not math.isfinite(error)
            or upper > math.sqrt(np.finfo(float).max)
            or (upper != 0 and upper * upper == 0)
            or (cost == 0 and maximum != 0)
        ):
            unsupported = True
            cache[key] = None, "numerical"
            return None, "numerical"
        upper_cost = upper * upper + arithmetic
        if not math.isfinite(upper_cost):
            unsupported = True
            cache[key] = None, "numerical"
            return None, "numerical"
        candidate = CircularSegmentCandidate(
            *key,
            key[0] * key[1],
            tuple(map(float, coefficients)),
            cost,
            max(0.0, (max(0.0, norm - error)) ** 2 - arithmetic),
            upper_cost,
            design_rank,
            maximum,
            error,
            kind,
        )
        cache[key] = candidate, "resolved"
        source_means[key] = probability, design
        return candidate, "resolved"

    low = np.array([radii[0], fractions[0]])
    high = np.array([radii[1], fractions[1]])
    span = high - low

    def derivative_columns(current):
        """Domain-scaled mean derivatives with only FREE levels projected out.

        This is an approximate variable-projection GN direction, not the full
        residual-dependent Golub-Pereyra Jacobian. Actual-cost backtracking below
        refits the bounded levels and decides every accepted step.
        """
        nonlocal unsupported
        position = np.array([current.radius, current.chord_fraction])
        contrast = current.levels[1] - current.levels[0]
        columns = []
        for k in range(2):
            left, right = position.copy(), position.copy()
            left[k] = max(low[k], position[k] - 1e-4 * span[k])
            right[k] = min(high[k], position[k] + 1e-4 * span[k])
            if left[k] == right[k]:
                unsupported = True
                return None
            a, _ = evaluate(*left, "derivative")
            b, _ = evaluate(*right, "derivative")
            if a is None or b is None:
                return None
            dp = source_means[tuple(right)][0] - source_means[tuple(left)][0]
            dp *= span[k] / (right[k] - left[k])
            columns.append(noise.whiten_source(dp) * contrast)
        jacobian = np.column_stack(columns)
        _, design = source_means[tuple(position)]
        fitted = np.asarray(current.levels)
        guard = 256 * _EPS * max(abs(fitted))
        free = (fitted > levels[0] + guard) & (fitted < levels[1] - guard)
        if np.any(free):
            nuisance = design[:, free]
            jacobian -= nuisance @ np.linalg.lstsq(nuisance, jacobian, rcond=None)[0]
        if not np.isfinite(jacobian).all():
            unsupported = True
            return None
        return jacobian

    axes = [np.linspace(*domain, grid_points) for domain in (radii, fractions)]
    grid, statuses = [], []
    for radius in axes[0]:
        for fraction in axes[1]:
            item, status = evaluate(radius, fraction, "grid")
            grid.append(item)
            statuses.append(status)
    numeric = [c for c in grid if c is not None]
    if not numeric:
        return CircularSegmentFit(
            None,
            (),
            tuple(grid),
            tuple(statuses),
            (grid_points, grid_points),
            attempts,
            work,
            panels,
            rank,
            count,
            False,
            False,
            False,
            False,
            None,
            None,
            0,
            exhausted,
            unsupported,
            None,
            None,
            None,
        )
    flat = bool(
        len(numeric) == len(grid)
        and max(c.cost for c in numeric) - min(c.cost for c in numeric) <= arithmetic
    )
    seeds, candidates = [], []
    for i in range(grid_points):
        for j in range(grid_points):
            candidate = grid[i * grid_points + j]
            if candidate is None:
                continue
            neighbours = [
                grid[a * grid_points + b]
                for a in range(max(0, i - 1), min(grid_points, i + 2))
                for b in range(max(0, j - 1), min(grid_points, j + 2))
                if (a, b) != (i, j)
            ]
            local = all(c is None or candidate.cost <= c.cost + arithmetic for c in neighbours)
            if i in (0, grid_points - 1) or j in (0, grid_points - 1) or local:
                candidates.append(replace(candidate, kind="grid_basin" if local else "domain_face"))
            if local:
                seeds.append(candidate)
    seeds.sort(key=lambda c: c.cost)
    refined_basins, refinement_limited = 0, False
    if not flat and refinement_iterations:
        for seed in seeds[:max_basins]:
            if exhausted:
                break
            current = seed
            converged = False
            for _ in range(refinement_iterations):
                jacobian = derivative_columns(current)
                if jacobian is None:
                    break
                scale = float(np.max(np.abs(jacobian)))
                if scale == 0:
                    converged = True
                    break
                _, design = source_means[current.radius, current.chord_fraction]
                residual = target - design @ np.asarray(current.levels)
                step = np.linalg.lstsq(
                    np.vstack((jacobian / scale, 1e-4 * np.eye(2))),
                    np.r_[residual / scale, 0.0, 0.0],
                    rcond=None,
                )[0]
                largest = float(np.max(np.abs(step)))
                if largest > 0.25:
                    step *= 0.25 / largest
                position = np.array([current.radius, current.chord_fraction])
                feasible_step = (np.clip(position + span * step, low, high) - position) / span
                if float(np.max(np.abs(feasible_step))) < 1e-8:
                    converged = True
                    break
                accepted = False
                for power in range(12):
                    point = np.clip(position + (2.0**-power) * span * step, low, high)
                    candidate, _ = evaluate(*point, "refinement")
                    improvement = 64 * _EPS * max(current.cost, _EPS * energy)
                    if candidate is not None and candidate.cost < current.cost - improvement:
                        current, accepted = candidate, True
                        break
                    if exhausted:
                        break
                if not accepted or exhausted:
                    break
            refined_basins += int(converged)
            refinement_limited |= not converged
            candidates.append(replace(current, kind="refined_basin"))
            if exhausted:
                break
    unrefined = len(seeds) - refined_basins
    # Keep distinct represented candidates; the complete grid is never removed.
    candidates = list({(c.radius, c.chord_fraction): c for c in candidates}.values())
    best = min([*candidates, *numeric], key=lambda c: c.cost)
    same_basin = np.array([radii[1] - radii[0], fractions[1] - fractions[0]]) * 1e-5
    competitors = [
        c
        for c in candidates
        if abs(c.radius - best.radius) > same_basin[0]
        or abs(c.chord_fraction - best.chord_fraction) > same_basin[1]
    ]
    tied = any(c.cost_lower_guard <= best.cost_upper_guard for c in competitors)
    endpoint = any(
        min(abs(value - low), abs(value - high)) <= 64 * _EPS * max(1.0, high - low)
        for value, (low, high) in zip((best.radius, best.chord_fraction), (radii, fractions))
    )
    probability, _ = source_means[best.radius, best.chord_fraction]
    predicted = best.levels[0] * (1 - probability) + best.levels[1] * probability
    residual = values - predicted
    scaled = residual / noise.input_std
    retained = noise.right @ scaled
    omitted = scaled - noise.right.T @ retained
    residual_norms = []
    for component in (scaled, retained, omitted):
        value = math.hypot(*component)
        if not math.isfinite(value):
            unsupported = True
            value = None
        residual_norms.append(value)
    geometry_rank, condition = None, None
    if abs(best.levels[1] - best.levels[0]) <= 256 * _EPS * max(map(abs, best.levels)):
        geometry_rank = 0
        jacobian = None
    else:
        jacobian = derivative_columns(best)
    if jacobian is not None:
        singular = np.linalg.svd(jacobian, compute_uv=False)
        cutoff = 256 * _EPS * max(jacobian.shape) * singular[0]
        geometry_rank = int(np.count_nonzero(singular > cutoff))
        condition = float(singular[0] / singular[-1]) if geometry_rank == 2 else None
    return CircularSegmentFit(
        best,
        tuple(sorted(candidates, key=lambda c: c.cost)),
        tuple(grid),
        tuple(statuses),
        (grid_points, grid_points),
        attempts,
        work,
        panels,
        rank,
        count,
        flat,
        tied,
        endpoint,
        bool(best.design_rank < 2 or (geometry_rank is not None and geometry_rank < 2)),
        geometry_rank,
        condition,
        unrefined,
        exhausted,
        unsupported,
        *residual_norms,
        refinement_limited=bool(refinement_limited),
    )
