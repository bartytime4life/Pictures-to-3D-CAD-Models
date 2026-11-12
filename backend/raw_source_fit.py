"""Developer-only plane-edge fitting in a declared retained raw source space.

For fixed H, a unit plane normal and a supplied SPD raw Gaussian PSF, the exact
half-plane probability is evaluated before digital resampling. Both observations
and nuisance columns use PixelNoise.whiten_source; no small sampled singular mode
is inverted. This is a conditional finite numerical search, not calibrated camera
confidence, a continuous global certificate or accepted production geometry.
"""

import math
from dataclasses import dataclass, replace

import numpy as np

from .profile_observations import PixelNoise

MAX_RAW_PIXELS = 2048
MAX_GRID_POINTS = 513
MAX_EVALUATIONS = 4096
MAX_WORK = 100_000_000
_EPS = np.finfo(float).eps
_ERFC = np.frompyfunc(math.erfc, 1, 1)


@dataclass(frozen=True)
class OffsetCandidate:
    offset: float
    levels: tuple[float, float]
    cost: float
    design_rank: int
    kind: str
    bracket: tuple[float, float]
    maximum_projected_residual: float


@dataclass(frozen=True)
class EdgeOffsetResult:
    """Numerical candidates only; best is never an automatic geometry acceptance.

    candidates includes both endpoints and every represented interior minimum,
    including unrefined grid/plateau candidates when a work budget is exhausted.
    An unobserved narrower basin is not excluded by this finite search.
    """

    best: OffsetCandidate
    candidates: tuple[OffsetCandidate, ...]
    grid_offsets: tuple[float, ...]
    grid_costs: tuple[float, ...]
    evaluations: int
    work: int
    projection_rank: int
    raw_pixel_count: int
    comparison_tolerance: float
    flat: bool
    plateau: bool
    tied: bool
    endpoint: bool
    rank_deficient: bool
    work_exhausted: bool
    numerically_unsupported: bool
    raw_residual_l2: float | None
    raw_residual_maximum: float | None
    retained_residual_l2: float | None
    omitted_source_residual_l2: float | None
    global_search_certified: bool = False


def _integer(value, low, high, label):
    if (
        isinstance(value, (bool, np.bool_))
        or not isinstance(value, (int, np.integer))
        or not low <= value <= high
    ):
        raise ValueError(f"{label} must be an integer in [{low}, {high}]")
    return int(value)


def _shape(shape):
    if np.shape(shape) != (2,):
        raise ValueError("sensor_shape needs height and width")
    return tuple(_integer(v, 1, 10**9, "sensor dimension") for v in shape)


def _pixels(pixels_xy, sensor_shape, *, count=None):
    shape = np.shape(pixels_xy)
    if (
        len(shape) != 2
        or shape[1] != 2
        or not 1 <= shape[0] <= MAX_RAW_PIXELS
        or (count is not None and shape[0] != count)
    ):
        raise ValueError("supply 1-2048 unique raw pixels in the noise column order")
    pixels = np.asarray(pixels_xy)
    if not np.issubdtype(pixels.dtype, np.integer) or np.issubdtype(pixels.dtype, np.bool_):
        raise ValueError("raw pixel indices must be integers")
    height, width = sensor_shape
    if np.any(pixels < 0) or np.any(pixels[:, 0] >= width) or np.any(pixels[:, 1] >= height):
        raise ValueError("raw pixels lie outside the declared sensor")
    if len(np.unique(pixels, axis=0)) != len(pixels):
        raise ValueError("raw pixels must be unique")
    return pixels.astype(float) + 0.5


def _bounds(values, label, *, coordinate=False):
    if np.shape(values) != (2,):
        raise ValueError(f"{label} needs two ordered finite endpoints")
    low, high = (float(v) for v in values)
    if not (math.isfinite(low) and math.isfinite(high) and low < high):
        raise ValueError(f"{label} needs two ordered finite endpoints")
    if coordinate and max(abs(low), abs(high)) > 10**9:
        raise ValueError(f"{label} exceeds the coordinate limit")
    return low, high


@dataclass(frozen=True)
class _Geometry:
    line: np.ndarray
    rate: np.ndarray
    cholesky: np.ndarray

    def probability(self, pixels, offset):
        line = self.line + offset * self.rate
        width = math.hypot(*(self.cholesky.T @ line[:2]))
        if not math.isfinite(width) or width <= 0:
            raise ValueError("candidate raw line has unsupported Gaussian width")
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            z = (pixels @ line[:2] + line[2]) / width
        if np.isnan(z).any():
            raise ValueError("candidate raw probability is not numerical")
        return 0.5 * np.asarray(_ERFC(-z / math.sqrt(2)), dtype=float)


def _geometry(sensor_shape, homography, anchor, normal, psf_covariance, offset_bounds):
    if (
        np.shape(homography) != (3, 3)
        or np.shape(anchor) != (2,)
        or np.shape(normal) != (2,)
        or np.shape(psf_covariance) != (2, 2)
    ):
        raise ValueError("supply a 3x3 H, 2-D anchor/unit normal and 2x2 PSF covariance")
    h = np.asarray(homography, dtype=float).copy()
    anchor, normal = np.asarray(anchor, dtype=float), np.asarray(normal, dtype=float)
    covariance = np.asarray(psf_covariance, dtype=float)
    if (
        not all(np.isfinite(v).all() for v in (h, anchor, normal, covariance))
        or np.max(np.abs(anchor)) > 10**9
    ):
        raise ValueError("geometry must be finite and anchor coordinates bounded")
    length = math.hypot(*normal)
    if not math.isfinite(length) or abs(length - 1) > 64 * _EPS:
        raise ValueError("plane normal must be a unit vector")
    normal = normal / length
    if not np.array_equal(covariance, covariance.T):
        raise ValueError("raw PSF covariance must be symmetric positive definite")
    try:
        cholesky = np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError as exc:
        raise ValueError("raw PSF covariance must be symmetric positive definite") from exc
    scale = float(np.max(np.abs(h)))
    if scale == 0:
        raise ValueError("homography must be invertible")
    h /= scale
    anchor_h = np.r_[anchor, 1.0]
    anchor_denominator = float(h[2] @ anchor_h)
    if anchor_denominator == 0 or not math.isfinite(anchor_denominator):
        raise ValueError("plane anchor lies on an unsupported projective horizon")
    if anchor_denominator < 0:
        h = -h
    try:
        inverse = np.linalg.inv(h)
        line = np.linalg.solve(h.T, np.r_[normal, -normal @ anchor])
        rate = np.linalg.solve(h.T, [0.0, 0.0, -1.0])
    except np.linalg.LinAlgError as exc:
        raise ValueError("homography must be invertible") from exc
    if not all(np.isfinite(v).all() for v in (inverse, line, rate)):
        raise ValueError("homography inversion is numerically unsupported")
    height, width = sensor_shape
    corners = np.array(
        [[0.0, 0.0, 1.0], [width, 0.0, 1.0], [0.0, height, 1.0], [width, height, 1.0]]
    )
    chart = corners @ inverse[2]
    if not np.isfinite(chart).all() or np.any(chart <= 0):
        raise ValueError("declared sensor crosses the positive inverse projective chart")
    low, high = offset_bounds
    if any(float(h[2] @ np.r_[anchor + e * normal, 1.0]) <= 0 for e in (low, high)):
        raise ValueError("offset interval leaves the positive plane projective chart")
    common_scale = max(float(np.max(np.abs(line))), float(np.max(np.abs(rate))))
    line, rate = line / common_scale, rate / common_scale
    a, b = cholesky.T @ line[:2], cholesky.T @ rate[:2]
    bscale = float(np.max(np.abs(b)))
    vertex = low
    if bscale:
        direction = b / bscale
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            stationary = float(-(a @ direction) / (bscale * (direction @ direction)))
        vertex = min(high, max(low, stationary))
    widths = [math.hypot(*(a + e * b)) for e in (low, vertex, high)]
    if not all(math.isfinite(w) and w > 0 for w in widths):
        raise ValueError(
            "offset interval contains an unsupported line at infinity or zero PSF width"
        )
    return _Geometry(line, rate, cholesky)


def plane_edge_probabilities(
    pixels_xy, offset, *, sensor_shape, homography, anchor, normal, psf_covariance
):
    """Raw point-sensor half-plane means under supplied anisotropic Gaussian blur.

    H maps plane coordinates to raw pixel-edge coordinates; raw pixel centres are
    indices+.5. H and negative/scaled H define the same physical side. The declared
    sensor must occupy one positive inverse projective chart. A half-plane extension
    under this PSF is an assumed source model, not inferred optical calibration.
    """
    shape = _shape(sensor_shape)
    offset = float(offset)
    if not math.isfinite(offset) or abs(offset) > 10**9:
        raise ValueError("offset must be finite and bounded")
    pixels = _pixels(pixels_xy, shape)
    geometry = _geometry(shape, homography, anchor, normal, psf_covariance, (offset, offset))
    return geometry.probability(pixels, offset)


def _box_fit(design, target, bounds):
    """Exact two-level box-LS active faces, using direct SVD least squares."""
    low, high = bounds
    levels, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if np.all((levels >= low) & (levels <= high)):
        candidates = [levels]
    else:
        candidates = []
        for fixed, free in ((0, 1), (1, 0)):
            denominator = float(design[:, free] @ design[:, free])
            if not math.isfinite(denominator):
                raise ValueError("bounded level fit is numerically unsupported")
            for bound in bounds:
                value = (
                    low
                    if denominator == 0
                    else float(design[:, free] @ (target - bound * design[:, fixed]) / denominator)
                )
                item = np.empty(2)
                item[fixed], item[free] = bound, min(high, max(low, value))
                candidates.append(item)
    best = None
    for levels in candidates:
        residual = target - design @ levels
        cost = float(residual @ residual)
        if not math.isfinite(cost) or not np.isfinite(levels).all():
            raise ValueError("source-space least squares is numerically unsupported")
        item = (cost, levels, int(rank), float(np.max(np.abs(residual))))
        if best is None or item[0] < best[0]:
            best = item
    return best


class _BudgetExhausted(Exception):
    pass


def fit_plane_edge_offset(
    pixels_xy,
    raw_values,
    noise,
    *,
    sensor_shape,
    homography,
    anchor,
    normal,
    psf_covariance,
    offset_bounds,
    level_bounds=(0.0, 255.0),
    grid_points=65,
    refinement_iterations=40,
    max_basins=16,
    max_evaluations=4096,
    work_limit=50_000_000,
):
    """Fit two bounded levels and a finite-search plane offset in retained source space.

    pixels_xy and raw_values MUST use exactly noise.matrix's unique raw column order.
    noise must come from PixelNoise.factor with supplied positive input deviations.
    This fits V.T D^-1 g. It equals retained processed-profile GLS only for the same
    fixed linear operator, raw covariance and modes, before quantization/arithmetic
    discrepancy. It is not an all-raw-pixel objective unless all raw modes are kept.

    Work units conservatively include dense projection and small direct linear fits;
    they are resource accounting, not a whole-photo time bound. The complete grid
    and residual diagnostics must fit the budget before any large input conversion.
    Refinement exhaustion retains every represented grid basin and both endpoints.
    Cost comparison is relative to target energy, preserving supplied noise units;
    its floating arithmetic guard is not a physical acceptance threshold.
    """
    if not isinstance(noise, PixelNoise):
        raise TypeError("noise must be a supplied PixelNoise factor")
    nshape = np.shape(noise.matrix)
    if len(nshape) != 2 or not 1 <= nshape[0] <= 512 or not 1 <= nshape[1] <= MAX_RAW_PIXELS:
        raise ValueError("noise factor dimensions exceed the supported limits")
    count, rank = nshape[1], noise.rank
    if (
        not 1 <= rank <= min(nshape)
        or np.shape(noise.right) != (rank, count)
        or np.shape(noise.input_std) != (count,)
    ):
        raise ValueError("noise factor shapes are inconsistent")
    if np.shape(pixels_xy) != (count, 2) or np.shape(raw_values) != (count,):
        raise ValueError("unique pixels and values must match noise matrix columns")
    grid_points = _integer(grid_points, 3, MAX_GRID_POINTS, "grid_points")
    refinement_iterations = _integer(refinement_iterations, 0, 64, "refinement_iterations")
    max_basins = _integer(max_basins, 0, 32, "max_basins")
    max_evaluations = _integer(max_evaluations, grid_points, MAX_EVALUATIONS, "max_evaluations")
    work_limit = _integer(work_limit, 1, MAX_WORK, "work_limit")
    per_evaluation = 4 * rank * count + 512 * rank + 128 * count + 1024
    preparation_work = 2 * rank * count + 64 * count
    diagnostic_work = 4 * rank * count + 64 * count
    if preparation_work + diagnostic_work + grid_points * per_evaluation > work_limit:
        raise ValueError("full grid and diagnostics exceed source-fit work limit")
    shape = _shape(sensor_shape)
    pixels = _pixels(pixels_xy, shape, count=count)
    values = np.asarray(raw_values, dtype=float)
    if (
        not np.isfinite(values).all()
        or not np.isfinite(noise.right).all()
        or not np.isfinite(noise.input_std).all()
        or np.any(noise.input_std <= 0)
    ):
        raise ValueError(
            "raw values and supplied noise factor must be finite with positive deviations"
        )
    offset_bounds = _bounds(offset_bounds, "offset_bounds", coordinate=True)
    level_bounds = _bounds(level_bounds, "level_bounds", coordinate=True)
    geometry = _geometry(shape, homography, anchor, normal, psf_covariance, offset_bounds)
    target = noise.whiten_source(values)
    energy = float(target @ target)
    if not math.isfinite(energy):
        raise ValueError("source target energy is numerically unsupported")
    tolerance = 256 * _EPS * energy
    used_work, attempts, cache = preparation_work, 0, {}

    def evaluate(offset):
        nonlocal used_work, attempts
        offset = float(offset)
        if offset in cache:
            return cache[offset]
        if attempts >= max_evaluations or used_work + per_evaluation + diagnostic_work > work_limit:
            raise _BudgetExhausted
        used_work += per_evaluation
        attempts += 1
        probability = geometry.probability(pixels, offset)
        design = noise.whiten_source(np.column_stack((1 - probability, probability)))
        cost, levels, design_rank, maximum = _box_fit(design, target, level_bounds)
        row = OffsetCandidate(
            offset,
            tuple(float(v) for v in levels),
            cost,
            design_rank,
            "evaluation",
            (offset, offset),
            maximum,
        )
        cache[offset] = row
        return row

    grid_offsets = np.linspace(*offset_bounds, grid_points)
    grid = [evaluate(offset) for offset in grid_offsets]
    costs = np.array([row.cost for row in grid])
    candidates = [replace(grid[0], kind="endpoint"), replace(grid[-1], kind="endpoint")]
    interior = [
        i
        for i in range(1, grid_points - 1)
        if costs[i] <= costs[i - 1] + tolerance and costs[i] <= costs[i + 1] + tolerance
    ]
    runs = []
    for index in interior:
        if runs and index == runs[-1][-1] + 1:
            runs[-1].append(index)
        else:
            runs.append([index])
    work_exhausted, unsupported, refined = False, False, 0
    for run in runs:
        if len(run) > 1:
            candidates.extend(
                replace(
                    grid[i],
                    kind="plateau_grid",
                    bracket=(float(grid_offsets[run[0] - 1]), float(grid_offsets[run[-1] + 1])),
                )
                for i in run
            )
            continue
        index = run[0]
        left, right = float(grid_offsets[index - 1]), float(grid_offsets[index + 1])
        fallback = replace(grid[index], kind="grid_minimum", bracket=(left, right))
        if refined >= max_basins or work_exhausted or unsupported:
            work_exhausted = work_exhausted or not unsupported
            candidates.append(fallback)
            continue
        refined += 1
        local = [grid[index], grid[index - 1], grid[index + 1]]
        try:
            phi = (math.sqrt(5) - 1) / 2
            c, d = right - phi * (right - left), left + phi * (right - left)
            fc = evaluate(c)
            local.append(fc)
            fd = evaluate(d)
            local.append(fd)
            for _ in range(refinement_iterations):
                if fc.cost <= fd.cost:
                    right, d, fd = d, c, fc
                    c = right - phi * (right - left)
                    fc = evaluate(c)
                    local.append(fc)
                else:
                    left, c, fc = c, d, fd
                    d = left + phi * (right - left)
                    fd = evaluate(d)
                    local.append(fd)
            winner = min(local, key=lambda row: row.cost)
            candidates.append(
                replace(
                    winner,
                    kind="refined_minimum",
                    bracket=(min(left, winner.offset), max(right, winner.offset)),
                )
            )
        except _BudgetExhausted:
            work_exhausted = True
            winner = min(local, key=lambda row: row.cost)
            candidates.append(replace(winner, kind="unfinished_minimum", bracket=fallback.bracket))
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            unsupported = True
            candidates.append(fallback)
    candidates.sort(key=lambda row: row.offset)
    best = min(candidates, key=lambda row: row.cost)
    near_grid = costs <= best.cost + tolerance
    equivalent = [row for row in candidates if row.cost <= best.cost + tolerance]
    flat = bool(float(costs.max() - costs.min()) <= tolerance)
    plateau = bool(np.any(near_grid[:-1] & near_grid[1:]))
    tied = bool(len({row.offset for row in equivalent}) > 1 or np.count_nonzero(near_grid) > 1)
    endpoint = bool(any(row.kind == "endpoint" for row in equivalent))
    raw_l2 = raw_maximum = retained_l2 = omitted_l2 = None
    try:
        probability = geometry.probability(pixels, best.offset)
        prediction = np.column_stack((1 - probability, probability)) @ best.levels
        standardized = (values - prediction) / noise.input_std
        retained = noise.right @ standardized
        omitted = standardized - noise.right.T @ retained
        raw_l2, raw_maximum = math.hypot(*standardized), float(np.max(np.abs(standardized)))
        retained_l2, omitted_l2 = math.hypot(*retained), math.hypot(*omitted)
        if not all(math.isfinite(v) for v in (raw_l2, raw_maximum, retained_l2, omitted_l2)):
            raise ValueError("residual diagnostics overflow")
    except (ValueError, FloatingPointError):
        unsupported = True
        raw_l2 = raw_maximum = retained_l2 = omitted_l2 = None
    used_work += diagnostic_work
    return EdgeOffsetResult(
        best,
        tuple(candidates),
        tuple(float(v) for v in grid_offsets),
        tuple(float(v) for v in costs),
        attempts,
        used_work,
        rank,
        count,
        tolerance,
        flat,
        plateau,
        tied,
        endpoint,
        best.design_rank < 2,
        work_exhausted,
        unsupported,
        raw_l2,
        raw_maximum,
        retained_l2,
        omitted_l2,
    )
