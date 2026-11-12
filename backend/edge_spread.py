"""Conditional straight-edge offset and Gaussian width in fixed source pixels.

Pixel centres are indices + .5 in the supplied working-photo frame. A shared
two-level mean is fitted before a fixed PixelNoise source projection. The search
uses offset and log(width), retaining its complete grid and represented basins.
This is an engineering local fit, not optical calibration, a physical confidence
interval, or a certificate that no narrower unrepresented minimum exists.
"""

import math
from dataclasses import dataclass, replace

import numpy as np

from .profile_observations import PixelNoise
from .raw_source_fit import _box_fit, _integer, _pixels, _shape

MAX_WORK = 100_000_000
_EPS = float(np.finfo(float).eps)
_ERFC = np.frompyfunc(math.erfc, 1, 1)


@dataclass(frozen=True)
class EdgeSpreadCandidate:
    offset: float
    sigma: float
    levels: tuple[float, float]
    cost: float
    cost_lower_guard: float
    cost_upper_guard: float
    design_rank: int
    maximum_projected_residual: float
    kind: str


@dataclass(frozen=True)
class EdgeSpreadFit:
    best: EdgeSpreadCandidate | None
    candidates: tuple[EdgeSpreadCandidate, ...]
    grid: tuple[EdgeSpreadCandidate | None, ...]
    grid_statuses: tuple[str, ...]
    grid_shape: tuple[int, int]
    evaluations: int
    work: int
    projection_rank: int
    raw_pixel_count: int
    comparison_tolerance: float | None
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
    refinement_limited: bool = False
    global_search_certified: bool = False


def _no_bools(value):
    return not any(isinstance(v, (bool, np.bool_)) for v in np.asarray(value, dtype=object).flat)


def _bounds(value, name, low, high):
    if np.shape(value) != (2,) or not _no_bools(value):
        raise ValueError(f"{name} needs two finite increasing endpoints")
    a, b = map(float, value)
    if not (math.isfinite(a) and math.isfinite(b) and low <= a < b <= high):
        raise ValueError(f"{name} must lie in [{low}, {high}]")
    if math.nextafter(a, b) >= b:
        raise ValueError(f"{name} must contain a representable interior point")
    return a, b


def _cdf_pdf(z):
    """erfc CDF and analytic derivatives, including the infinite-tail limit."""
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        probability = _ERFC(-z / math.sqrt(2)).astype(float) / 2
        density = np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
        width_derivative = np.zeros_like(z)
        np.multiply(-z, density, out=width_derivative, where=density != 0)
    return probability, density, width_derivative


def fit_edge_spread(
    pixels_xy,
    raw_values,
    noise,
    *,
    sensor_shape,
    normal,
    anchor,
    offset_bounds,
    sigma_bounds,
    level_bounds=(0.0, 255.0),
    grid_points=5,
    refinement_iterations=32,
    max_basins=8,
    max_evaluations=512,
):
    """Fit one fixed-frame half-plane under a supplied independent-source noise model.

    Material probability is Phi((n dot (pixel+.5-anchor)-offset)/sigma).
    Target, brightness columns, and analytic derivatives use whiten_source with
    the same retained modes. Only free brightness columns are projected from
    the approximate variable-projection GN direction; every accepted step refits
    bounded levels and decreases actual represented cost. No full residual-
    dependent variable-projection Jacobian or global optimum is claimed.

    The arithmetic cost guard is relative to target energy, without a unit floor.
    Unrepresentable squared-cost units retain numerical unknowns, not zero costs.
    MAX_WORK bounds declared dense projection work, separately from the geometry
    evaluation limit. All coarse grid slots remain visible on either exhaustion.
    Residual norms are standardized by the supplied source deviations; omitted
    source directions are reported separately from the retained objective.
    """
    if not isinstance(noise, PixelNoise):
        raise TypeError("noise must be a supplied PixelNoise factor")
    shape = _shape(sensor_shape)
    if (
        len(np.shape(pixels_xy)) != 2
        or np.shape(pixels_xy)[1] != 2
        or not 1 <= np.shape(pixels_xy)[0] <= 2048
    ):
        raise ValueError("supply 1..2048 raw pixel pairs")
    if not _no_bools(pixels_xy):
        raise ValueError("raw pixel indices must be integers, not booleans")
    # raw_source_fit's validator returns geometric centres, already indices+.5.
    centres = _pixels(pixels_xy, shape)
    count, rank = len(centres), noise.rank
    if (
        noise.matrix.ndim != 2
        or noise.matrix.shape[1] != count
        or not 1 <= rank <= min(noise.matrix.shape)
        or noise.right.shape != (rank, count)
        or noise.input_std.shape != (count,)
        or not np.isfinite(noise.right).all()
        or not np.isfinite(noise.input_std).all()
        or np.any(noise.input_std <= 0)
        or np.shape(raw_values) != (count,)
        or not _no_bools(raw_values)
    ):
        raise ValueError("source pixels, values and supplied noise factor must agree")
    values = np.array(raw_values, dtype=float, copy=True)
    if not np.isfinite(values).all():
        raise ValueError("source values must be finite")
    if np.shape(normal) != (2,) or np.shape(anchor) != (2,):
        raise ValueError("supply a unit normal and bounded anchor")
    if not _no_bools(normal) or not _no_bools(anchor):
        raise ValueError("supply a unit normal and bounded anchor, not booleans")
    normal, anchor = np.asarray(normal), np.asarray(anchor)
    if (
        normal.shape != (2,)
        or anchor.shape != (2,)
        or not _no_bools(normal)
        or not _no_bools(anchor)
    ):
        raise ValueError("supply a unit normal and bounded anchor")
    normal, anchor = normal.astype(float), anchor.astype(float)
    if (
        not np.isfinite(normal).all()
        or not np.isfinite(anchor).all()
        or np.max(np.abs(anchor)) > 1e9
        or abs(math.hypot(*normal) - 1) > 64 * _EPS
    ):
        raise ValueError("supply a unit normal and finite anchor bounded by 1e9")
    normal /= math.hypot(*normal)
    offsets = _bounds(offset_bounds, "offset_bounds", -1e9, 1e9)
    widths = _bounds(sigma_bounds, "sigma_bounds", 1e-3, 1e3)
    levels = _bounds(level_bounds, "level_bounds", -1e6, 1e6)
    log_widths = _bounds(tuple(map(math.log, widths)), "log sigma domain", -8, 8)
    grid_points = _integer(grid_points, 3, 11, "grid_points")
    refinement_iterations = _integer(refinement_iterations, 0, 64, "refinement_iterations")
    max_basins = _integer(max_basins, 0, 16, "max_basins")
    max_evaluations = _integer(max_evaluations, grid_points**2, 4096, "max_evaluations")
    low, high = np.array([offsets[0], log_widths[0]]), np.array([offsets[1], log_widths[1]])
    span = high - low
    distances = (centres - anchor) @ normal
    attempts, work = 0, 0
    exhausted, unsupported = False, False
    cache, means, positions, derivative_scales = {}, {}, {}, {}
    try:
        target = noise.whiten_source(values)
        norm = math.hypot(*target)
        energy = norm * norm
        arithmetic = 256 * _EPS * energy
        target_valid = (
            math.isfinite(energy)
            and not (norm != 0 and energy == 0)
            and not (energy != 0 and arithmetic == 0)
        )
    except (ValueError, FloatingPointError):
        target, energy, arithmetic, target_valid = None, 0.0, 0.0, False
    if not target_valid:
        unsupported = True

    def charge(amount):
        nonlocal work, exhausted
        if work + amount > MAX_WORK:
            exhausted = True
            return False
        work += amount
        return True

    def evaluate(position, kind):
        nonlocal attempts, exhausted, unsupported
        key = tuple(map(float, position))
        if key in cache:
            item, status = cache[key]
            return (replace(item, kind=kind) if item is not None else None), status
        if attempts >= max_evaluations or not charge(count * (2 * rank + 1) + 64 * rank):
            exhausted = True
            return None, "work_limit"
        attempts += 1
        if not target_valid:
            cache[key] = None, "numerical"
            return None, "numerical"
        sigma = (
            widths[0]
            if key[1] == low[1]
            else (widths[1] if key[1] == high[1] else math.exp(key[1]))
        )
        try:
            with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
                z = (distances - key[0]) / sigma
                probability, density, dw = _cdf_pdf(z)
                design = noise.whiten_source(np.column_stack((1 - probability, probability)))
                cost, coefficients, design_rank, maximum = _box_fit(design, target, levels)
            upper = cost + arithmetic
            if (
                not math.isfinite(upper)
                or not math.isfinite(maximum)
                or (cost == 0 and maximum != 0)
            ):
                raise ValueError("source squared-cost units are numerically unsupported")
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            unsupported = True
            cache[key] = None, "numerical"
            return None, "numerical"
        item = EdgeSpreadCandidate(
            key[0],
            sigma,
            tuple(map(float, coefficients)),
            cost,
            max(0.0, cost - arithmetic),
            upper,
            design_rank,
            maximum,
            kind,
        )
        cache[key] = item, "resolved"
        means[key] = probability, density, dw, design
        positions[item.offset, item.sigma] = key
        return item, "resolved"

    def derivatives(current):
        nonlocal unsupported
        key = positions[current.offset, current.sigma]
        _, density, dw, design = means[key]
        contrast = current.levels[1] - current.levels[0]
        if contrast == 0:
            derivative_scales[key] = 0.0
            return np.zeros((rank, 2))
        if not charge(2 * count * rank + 64 * rank):
            return None
        try:
            with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
                source = np.column_stack((-density / current.sigma * span[0], dw * span[1]))
                jacobian = noise.whiten_source(source) * contrast
                reference_scale = math.hypot(*jacobian.ravel())
                if not math.isfinite(reference_scale):
                    raise ValueError("derivative norm is numerically unsupported")
                fitted = np.asarray(current.levels)
                guard = 256 * _EPS * max(map(abs, fitted))
                free = (fitted > levels[0] + guard) & (fitted < levels[1] - guard)
                if np.any(free):
                    nuisance = design[:, free]
                    jacobian -= nuisance @ np.linalg.lstsq(nuisance, jacobian, rcond=None)[0]
            if not np.isfinite(jacobian).all():
                raise ValueError("derivative units are numerically unsupported")
            derivative_scales[key] = reference_scale
            return jacobian
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            unsupported = True
            return None

    grid, statuses = [], []
    axes = [np.linspace(a, b, grid_points) for a, b in zip(low, high)]
    for x in axes[0]:
        for y in axes[1]:
            item, status = evaluate((x, y), "grid")
            grid.append(item)
            statuses.append(status)
    numeric = [c for c in grid if c is not None]
    if not numeric:
        return EdgeSpreadFit(
            None,
            (),
            tuple(grid),
            tuple(statuses),
            (grid_points, grid_points),
            attempts,
            work,
            rank,
            count,
            arithmetic if target_valid else None,
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
            item = grid[i * grid_points + j]
            if item is None:
                continue
            neighbours = [
                grid[a * grid_points + b]
                for a in range(max(0, i - 1), min(grid_points, i + 2))
                for b in range(max(0, j - 1), min(grid_points, j + 2))
                if (a, b) != (i, j)
            ]
            local = all(c is None or item.cost <= c.cost + arithmetic for c in neighbours)
            if local or i in (0, grid_points - 1) or j in (0, grid_points - 1):
                candidates.append(replace(item, kind="grid_basin" if local else "domain_face"))
            if local:
                seeds.append(item)
    seeds.sort(key=lambda c: c.cost)
    refined, limited = 0, False
    if not flat and refinement_iterations:
        for seed in seeds[:max_basins]:
            if exhausted:
                break
            current, converged = seed, False
            for _ in range(refinement_iterations):
                jacobian = derivatives(current)
                if jacobian is None:
                    break
                scale = float(np.max(np.abs(jacobian)))
                if scale == 0:
                    converged = True
                    break
                _, _, _, design = means[positions[current.offset, current.sigma]]
                with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
                    residual = (target - design @ np.asarray(current.levels)) / scale
                if not np.isfinite(residual).all():
                    unsupported = True
                    break
                try:
                    step = np.linalg.lstsq(
                        np.vstack((jacobian / scale, 1e-6 * np.eye(2))),
                        np.r_[residual, 0.0, 0.0],
                        rcond=None,
                    )[0]
                except np.linalg.LinAlgError:
                    unsupported = True
                    break
                if not np.isfinite(step).all():
                    unsupported = True
                    break
                largest = float(np.max(np.abs(step)))
                if largest > 0.25:
                    step *= 0.25 / largest
                position = np.asarray(positions[current.offset, current.sigma])
                feasible = (np.clip(position + span * step, low, high) - position) / span
                if float(np.max(np.abs(feasible))) < 1e-9:
                    converged = True
                    break
                accepted = False
                for power in range(12):
                    point = np.clip(position + (2.0**-power) * span * step, low, high)
                    item, _ = evaluate(point, "refinement")
                    improvement = 64 * _EPS * max(current.cost, _EPS * energy)
                    if item is not None and item.cost < current.cost - improvement:
                        current, accepted = item, True
                        break
                    if exhausted:
                        break
                if not accepted or exhausted:
                    break
            refined += int(converged)
            limited |= not converged
            candidates.append(replace(current, kind="refined_basin"))
    candidates = list({(c.offset, c.sigma): c for c in candidates}.values())
    best = min([*numeric, *candidates], key=lambda c: c.cost)
    best_position = np.asarray(positions[best.offset, best.sigma])
    competitors = [
        c
        for c in candidates
        if np.max(np.abs((np.asarray(positions[c.offset, c.sigma]) - best_position) / span)) > 1e-5
    ]
    tied = bool(any(c.cost_lower_guard <= best.cost_upper_guard for c in competitors))
    endpoint = bool(
        np.any(
            np.minimum(np.abs(best_position - low), np.abs(best_position - high))
            <= 64 * _EPS * span
        )
    )
    probability = means[positions[best.offset, best.sigma]][0]
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        predicted = best.levels[0] * (1 - probability) + best.levels[1] * probability
        scaled = (values - predicted) / noise.input_std
        retained = noise.right @ scaled
        omitted = scaled - noise.right.T @ retained
    norms = []
    for value in (scaled, retained, omitted):
        norm = math.hypot(*value)
        if not math.isfinite(norm):
            unsupported = True
            norm = None
        norms.append(norm)
    geometry_rank, condition = None, None
    if abs(best.levels[1] - best.levels[0]) <= 256 * _EPS * max(map(abs, best.levels)):
        geometry_rank = 0
    else:
        jacobian = derivatives(best)
        if jacobian is not None:
            try:
                singular = np.linalg.svd(jacobian, compute_uv=False)
                # Projection can leave only roundoff from an exactly nuisance-
                # confounded derivative. Its own tiny residual is not a valid
                # reference scale for claiming new geometry directions.
                reference_scale = derivative_scales[positions[best.offset, best.sigma]]
                cutoff = 256 * _EPS * max(jacobian.shape) * max(singular[0], reference_scale)
                geometry_rank = int(np.count_nonzero(singular > cutoff))
                condition = float(singular[0] / singular[-1]) if geometry_rank == 2 else None
            except np.linalg.LinAlgError:
                unsupported = True
    return EdgeSpreadFit(
        best,
        tuple(sorted(candidates, key=lambda c: c.cost)),
        tuple(grid),
        tuple(statuses),
        (grid_points, grid_points),
        attempts,
        work,
        rank,
        count,
        arithmetic,
        flat,
        tied,
        endpoint,
        bool(best.design_rank < 2 or (geometry_rank is not None and geometry_rank < 2)),
        geometry_rank,
        condition,
        len(seeds) - refined,
        exhausted,
        unsupported,
        *norms,
        refinement_limited=bool(limited),
    )
