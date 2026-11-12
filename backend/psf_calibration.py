"""Conditional Gaussian covariance reconstruction and edge-orientation planning.

Input spreads must concern a common working-image PSF and known straight-edge
normals. This is not the production rectified-rise diagnostic, a Gaussian-model
test, or physical calibration. No eigenvalue clipping fills missing information.
"""

import math
from dataclasses import dataclass

import numpy as np

_EPS = np.finfo(float).eps
_ROOT2 = math.sqrt(2)
MAX_EDGES = 128


def _normals(normals, *, empty=False):
    shape = np.shape(normals)
    if empty and shape in ((0,), (0, 2)):
        return np.empty((0, 2))
    if len(shape) != 2 or shape[1] != 2 or not 1 <= shape[0] <= MAX_EDGES:
        raise ValueError("supply 1..128 unit source-edge normal pairs")
    if any(isinstance(v, (bool, np.bool_)) for pair in normals for v in pair):
        raise ValueError("edge normals must be numerical unit vectors")
    n = np.asarray(normals, dtype=float)
    lengths = np.hypot(n[:, 0], n[:, 1])
    if not np.isfinite(n).all() or np.any(np.abs(lengths - 1) > 64 * _EPS):
        raise ValueError("edge normals must be finite unit vectors")
    return n / lengths[:, None]


def _std(values, size):
    if values is None:
        return np.ones(size)
    if np.shape(values) not in ((), (size,)):
        raise ValueError("supply one positive variance standard deviation or one per edge")
    if isinstance(values, (bool, np.bool_)) or (
        np.shape(values) == (size,) and any(isinstance(v, (bool, np.bool_)) for v in values)
    ):
        raise ValueError("variance standard deviations must be numerical")
    std = np.broadcast_to(np.asarray(values, dtype=float), (size,)).copy()
    if not np.isfinite(std).all() or np.any(std <= 0):
        raise ValueError("variance standard deviations must be positive and finite")
    return std


def _design(normals):
    x, y = normals.T
    return np.column_stack((x * x, _ROOT2 * x * y, y * y))


def _spectrum(matrix):
    if len(matrix) == 0:
        return np.empty((0, 0)), np.array([]), np.eye(3), 0, 0.0, None
    u, s, vt = np.linalg.svd(matrix, full_matrices=True)
    cutoff = float(_EPS * max(matrix.shape) * s[0])
    rank = int(np.sum(s > cutoff))
    condition = float(s[0] / s[2]) if rank == 3 else None
    return u, s, vt, rank, cutoff, condition


def _tuple_rows(matrix):
    return tuple(tuple(float(v) for v in row) for row in matrix)


@dataclass(frozen=True)
class CovarianceReconstruction:
    covariance: tuple | None
    candidate: tuple | None
    normals: tuple
    observed_variances: tuple
    fitted_variances: tuple
    variance_residuals: tuple
    variance_std: tuple
    rank: int
    geometric_rank: int
    condition: float | None
    geometric_condition: float | None
    rank_cutoff: float
    nullspace: tuple
    eigenvalues: tuple | None
    positive_definite: bool | None
    weighted_residual_l2: float | None
    maximum_standardized_residual: float | None
    numerically_supported: bool
    gaussian_model_validated: bool = False
    physically_calibrated: bool = False


def covariance_from_edge_spreads(normals, variances, *, variance_std=None):
    """Fit v_i=n_i.T Sigma n_i in orthonormal Frobenius coordinates.

    Variances and variance_std have working-pixel-squared units. The optional
    diagonal weighting is a supplied hypothesis, not uncertainty inferred from a
    width optimizer. Rank uses an explicit floating SVD cutoff; condition is in
    rotation-invariant Frobenius coordinates. Every supplied row is retained.

    candidate is the minimum-Frobenius-norm unconstrained WLS solution. covariance
    is returned only for numerical rank three and a numerically SPD candidate.
    A rank-two SPD candidate is still not identified. Indefinite results are not
    clipped into plausible optics. Small residuals do not validate Gaussian shape.
    """
    normals = _normals(normals)
    size = len(normals)
    if np.shape(variances) != (size,) or any(isinstance(v, (bool, np.bool_)) for v in variances):
        raise ValueError("supply one nonnegative finite directional variance per edge")
    values = np.asarray(variances, dtype=float)
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("directional variances must be nonnegative and finite")
    std = _std(variance_std, size)
    weights = np.min(std) / std
    if np.any(weights == 0):
        raise ValueError("relative variance weights are numerically unsupported")
    design = _design(normals)
    _, _, _, geometric_rank, _, geometric_condition = _spectrum(design)
    u, s, vt, rank, cutoff, condition = _spectrum(weights[:, None] * design)
    # Keep scaling out of the SVD solve and avoid arbitrary variance-unit floors.
    scale = float(np.max(values)) or 1.0
    beta = vt[:rank].T @ ((u[:, :rank].T @ (weights * (values / scale))) / s[:rank])
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        fitted = (design @ beta) * scale
        coefficients = beta * scale
        matrix = np.array(
            [
                [coefficients[0], coefficients[1] / _ROOT2],
                [coefficients[1] / _ROOT2, coefficients[2]],
            ]
        )
        residual = fitted - values
        standardized = residual / std
    nullspace = []
    for row in vt[rank:]:
        row = row.copy()
        if row[np.argmax(np.abs(row))] < 0:
            row = -row
        nullspace.append(row)
    finite = np.isfinite(matrix).all() and np.isfinite(fitted).all() and np.isfinite(residual).all()
    # Underflow must not turn a nonzero parameter into an apparently exact zero.
    finite = bool(finite and not np.any((beta != 0) & (coefficients == 0)))
    candidate = _tuple_rows(matrix) if finite else None
    eigenvalues = None
    spd = None
    if finite:
        matrix_scale = float(np.max(np.abs(matrix)))
        with np.errstate(over="ignore", invalid="ignore"):
            eigen = (
                np.linalg.eigvalsh(matrix / matrix_scale) * matrix_scale
                if matrix_scale
                else np.zeros(2)
            )
        if np.isfinite(eigen).all():
            eigenvalues = tuple(float(v) for v in eigen)
            spd = bool(eigen[0] > 64 * _EPS * np.max(np.abs(eigen)))
        else:
            finite = False
    parameter_supported = finite
    norm = math.hypot(*standardized)
    maximum = float(np.max(np.abs(standardized)))
    diagnostic_supported = (
        math.isfinite(norm)
        and math.isfinite(maximum)
        and not np.any((residual != 0) & (standardized == 0))
    )
    finite = bool(parameter_supported and diagnostic_supported)
    return CovarianceReconstruction(
        candidate if rank == 3 and spd and parameter_supported else None,
        candidate,
        _tuple_rows(normals),
        tuple(float(v) for v in values),
        tuple(float(v) if math.isfinite(v) else None for v in fitted),
        tuple(float(v) if math.isfinite(v) else None for v in residual),
        tuple(float(v) for v in std),
        rank,
        geometric_rank,
        condition,
        geometric_condition,
        cutoff,
        _tuple_rows(nullspace),
        eigenvalues,
        spd,
        norm if diagnostic_supported else None,
        maximum if diagnostic_supported else None,
        bool(finite),
    )


@dataclass(frozen=True)
class EdgeOrientationPlan:
    angle_rad: float
    normal: tuple
    rank_before: int
    rank_after: int
    condition_after: float | None
    log_pseudovolume_after: float
    candidates_considered: int
    continuous_optimality_certified: bool = False
    physical_capture_qualified: bool = False


@dataclass(frozen=True)
class GaussianPsfEstimate:
    reconstruction: CovarianceReconstruction | None
    edge_statuses: tuple
    directional_variances: tuple
    geometric_rank: int
    geometric_condition: float | None
    all_edges_resolved: bool
    gaussian_model_validated: bool = False
    physically_calibrated: bool = False


def covariance_from_edge_fits(normals, fits, *, variance_std=None):
    """Keep every planned edge; withhold pooling if any search is unresolved.

    This is numerical readiness for a conditional reconstruction, not acceptance
    of the target, Gaussian shape, noise, geometry, response or physical optics.
    The caller must bind fits from the same declared stationary source PSF.
    """
    from .edge_spread import EdgeSpreadFit

    n = _normals(normals)
    if len(fits) != len(n) or any(not isinstance(f, EdgeSpreadFit) for f in fits):
        raise ValueError("supply one edge-spread fit per declared normal")
    std = _std(variance_std, len(n))
    _, _, _, rank, _, condition = _spectrum(_design(n))
    statuses, variances = [], []
    for fit in fits:
        reasons = [
            name
            for name in (
                "flat",
                "tied",
                "endpoint",
                "rank_deficient",
                "work_exhausted",
                "numerically_unsupported",
                "refinement_limited",
            )
            if getattr(fit, name)
        ]
        if fit.unrefined_basins:
            reasons.append("unrefined_basins")
        if fit.geometry_rank != 2:
            reasons.append("geometry_rank_unavailable_or_deficient")
        if fit.best is None:
            reasons.append("no_resolved_candidate")
            variances.append(None)
        else:
            sigma = fit.best.sigma
            if not math.isfinite(sigma) or not 1e-3 <= sigma <= 1e3:
                raise ValueError("edge fit contains an unsupported Gaussian width")
            variances.append(float(sigma * sigma))
        statuses.append(tuple(reasons))
    complete = not any(statuses)
    reconstruction = (
        covariance_from_edge_spreads(n, variances, variance_std=std) if complete else None
    )
    return GaussianPsfEstimate(
        reconstruction, tuple(statuses), tuple(variances), rank, condition, complete
    )


def plan_edge_orientation(normals, *, variance_std=None, candidate_angles=None, candidate_std=1.0):
    """Greedy finite-grid rank/D-optimal planning for variance measurements.

    First maximize numerical rank, then sum(log singular values), with a scale-
    aware tie and smallest angle for deterministic reporting. The supplied error
    weights concern variance summaries. This does not model pixel-phase sampling,
    finite target support, unknown edge normals, or spatially varying optics.
    """
    normals = _normals(normals, empty=True)
    if len(normals) >= MAX_EDGES:
        raise ValueError("orientation planning allows at most 127 existing edges")
    std = _std(variance_std, len(normals))
    new_std = float(_std(candidate_std, 1)[0])
    if candidate_angles is None:
        angles = np.linspace(0.0, math.pi, 720, endpoint=False)
    else:
        if (
            len(np.shape(candidate_angles)) != 1
            or not 1 <= len(candidate_angles) <= 4096
            or any(isinstance(v, (bool, np.bool_)) for v in candidate_angles)
        ):
            raise ValueError("supply 1..4096 numerical candidate angles")
        angles = np.asarray(candidate_angles, dtype=float)
        if not np.isfinite(angles).all() or np.any(angles < 0) or np.any(angles >= math.pi):
            raise ValueError("candidate angles must be finite radians in [0,pi)")
        angles = np.unique(angles)
    all_std = np.r_[std, new_std]
    weights = np.min(all_std) / all_std
    if np.any(weights == 0):
        raise ValueError("relative planning weights are numerically unsupported")
    base = _design(normals) * weights[:-1, None]
    _, _, _, rank_before, _, _ = _spectrum(base)
    best = None
    for angle in angles:
        n = np.array([[math.cos(angle), math.sin(angle)]])
        design = np.vstack([base, _design(n) * weights[-1]])
        _, s, _, rank, _, condition = _spectrum(design)
        score = math.fsum(math.log(float(v)) for v in s[:rank])
        tolerance = 64 * _EPS * max(1.0, abs(score), abs(best[0]) if best else 0.0)
        if best is None or rank > best[1] or (rank == best[1] and score > best[0] + tolerance):
            best = score, rank, float(angle), tuple(float(v) for v in n[0]), condition
    score, rank, angle, normal, condition = best
    return EdgeOrientationPlan(angle, normal, rank_before, rank, condition, score, len(angles))
