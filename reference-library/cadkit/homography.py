"""Planar homography from point correspondences (pure Python).

``fit`` uses the normalized direct linear transform: both point sets are
translated to their centroid and scaled to a mean distance of sqrt(2)
(Hartley normalization), the 2n x 9 system is formed, and the solution is the
eigenvector of ``A^T A`` with the smallest eigenvalue, found with a cyclic
Jacobi eigen-solver. The result is denormalized and scaled so ``H[2][2] == 1``.

Points are ``(u, v)`` image pixels mapped to ``(x, y)`` plane coordinates,
typically millimetres. ``jacobian`` and ``local_scale`` give the local
millimetres-per-pixel factors at an image point (handbook section 5).
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Sequence

Point = Sequence[float]
Matrix = list[list[float]]

FOUR_POINT_WARNING = (
    "Exactly four point pairs: the homography reproduces them exactly, so residuals are zero "
    "by construction and are not accuracy evidence. Add well-distributed control points and "
    "reserve an independent check length."
)
NEAR_COLLINEAR_AREA = 0.05  # in normalized coordinates (mean distance sqrt(2))
COLLINEAR_AREA = 1e-9


def _sum(values) -> float:
    """Plain left-to-right float addition.

    Python 3.12+ makes ``sum()`` of floats use compensated summation, which
    changes results on ill-conditioned point sets between Python versions and
    away from the browser twin (assets/js/cadcalc.js adds left to right). Using
    one explicit order keeps every Python version and the JavaScript identical.
    """
    total = 0.0
    for v in values:
        total += v
    return total


def _points(name: str, pts: Sequence[Point]) -> list[tuple[float, float]]:
    out = []
    for p in pts:
        if len(p) != 2:
            raise ValueError(f"{name} points must be (x, y) pairs")
        x, y = float(p[0]), float(p[1])
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError(f"{name} points must be finite")
        out.append((x, y))
    return out


def _normalizer(pts: list[tuple[float, float]]) -> tuple[Matrix, list[tuple[float, float]]]:
    n = len(pts)
    cx = _sum(p[0] for p in pts) / n
    cy = _sum(p[1] for p in pts) / n
    mean_dist = _sum(math.hypot(p[0] - cx, p[1] - cy) for p in pts) / n
    if mean_dist == 0:
        raise ValueError("points are all identical")
    s = math.sqrt(2.0) / mean_dist
    T = [[s, 0.0, -s * cx], [0.0, s, -s * cy], [0.0, 0.0, 1.0]]
    return T, [((p[0] - cx) * s, (p[1] - cy) * s) for p in pts]


def _spread_ratio(pts: list[tuple[float, float]]) -> float:
    """Ratio of the smaller to larger principal variance (0 for collinear points)."""
    n = len(pts)
    cx = _sum(p[0] for p in pts) / n
    cy = _sum(p[1] for p in pts) / n
    sxx = _sum((p[0] - cx) ** 2 for p in pts) / n
    syy = _sum((p[1] - cy) ** 2 for p in pts) / n
    sxy = _sum((p[0] - cx) * (p[1] - cy) for p in pts) / n
    tr, det = sxx + syy, sxx * syy - sxy * sxy
    disc = math.sqrt(max(tr * tr / 4.0 - det, 0.0))
    big, small = tr / 2.0 + disc, tr / 2.0 - disc
    return 0.0 if big <= 0 else max(small, 0.0) / big


def _min_triangle_area(pts: list[tuple[float, float]]) -> float:
    best = math.inf
    for a, b, c in combinations(pts, 3):
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2.0
        best = min(best, area)
    return best


def jacobi_eigen(matrix: Matrix, tol: float = 1e-15, max_sweeps: int = 100) -> tuple[list[float], Matrix]:
    """Eigenvalues and eigenvectors (as columns) of a real symmetric matrix."""
    n = len(matrix)
    a = [list(map(float, row)) for row in matrix]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    scale = math.sqrt(_sum(a[i][j] ** 2 for i in range(n) for j in range(n))) or 1.0
    for _ in range(max_sweeps):
        off = math.sqrt(_sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j))
        if off <= tol * scale:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if apq == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * apq)
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p] = c * vkp - s * vkq
                    v[k][q] = s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def _matmul(a: Matrix, b: Matrix) -> Matrix:
    return [[_sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _inverse_similarity(T: Matrix) -> Matrix:
    s, tx, ty = T[0][0], T[0][2], T[1][2]
    return [[1.0 / s, 0.0, -tx / s], [0.0, 1.0 / s, -ty / s], [0.0, 0.0, 1.0]]


def _validate(src: list, dst: list) -> None:
    if len(src) != len(dst):
        raise ValueError("src and dst must have the same number of points")
    if len(src) < 4:
        raise ValueError("a homography needs at least four point pairs")
    for name, pts in (("src", src), ("dst", dst)):
        if len(set(pts)) != len(pts):
            raise ValueError(f"{name} contains duplicate points")
        if _spread_ratio(pts) < 1e-12:
            raise ValueError(f"{name} points are collinear; a homography is undefined")


def fit(src: Sequence[Point], dst: Sequence[Point]) -> Matrix:
    """Fit ``H`` with ``dst ~ H src``; returns a 3 x 3 list with ``H[2][2] == 1``."""
    src_p, dst_p = _points("src", src), _points("dst", dst)
    _validate(src_p, dst_p)
    t_src, ns = _normalizer(src_p)
    t_dst, nd = _normalizer(dst_p)
    if len(src_p) == 4:
        for name, pts in (("src", ns), ("dst", nd)):
            if _min_triangle_area(pts) < COLLINEAR_AREA:
                raise ValueError(f"three {name} points are collinear; four points cannot define a homography")
    rows = []
    for (u, v), (x, y) in zip(ns, nd):
        rows.append([-u, -v, -1.0, 0.0, 0.0, 0.0, x * u, x * v, x])
        rows.append([0.0, 0.0, 0.0, -u, -v, -1.0, y * u, y * v, y])
    ata = [[_sum(r[i] * r[j] for r in rows) for j in range(9)] for i in range(9)]
    values, vectors = jacobi_eigen(ata)
    order = sorted(range(9), key=lambda i: values[i])
    largest = max(abs(values[order[-1]]), 1e-300)
    if values[order[1]] / largest < 1e-12:
        raise ValueError("degenerate point configuration: the homography is not unique")
    h = [vectors[k][order[0]] for k in range(9)]
    hn = [h[0:3], h[3:6], h[6:9]]
    H = _matmul(_matmul(_inverse_similarity(t_dst), hn), t_src)
    if abs(H[2][2]) < 1e-12:
        raise ValueError("H[2][2] is zero: the mapping sends the image origin to infinity")
    return [[value / H[2][2] for value in row] for row in H]


def apply(H: Matrix, pt: Point) -> tuple[float, float]:
    u, v = float(pt[0]), float(pt[1])
    w = H[2][0] * u + H[2][1] * v + H[2][2]
    if abs(w) < 1e-15:
        raise ValueError("point maps to infinity")
    return (
        (H[0][0] * u + H[0][1] * v + H[0][2]) / w,
        (H[1][0] * u + H[1][1] * v + H[1][2]) / w,
    )


def residuals(H: Matrix, src: Sequence[Point], dst: Sequence[Point]) -> tuple[list[float], float]:
    """Euclidean residuals in ``dst`` units and their root-mean-square."""
    res = []
    for s, d in zip(src, dst):
        x, y = apply(H, s)
        res.append(math.hypot(x - float(d[0]), y - float(d[1])))
    rms = math.sqrt(_sum(r * r for r in res) / len(res)) if res else 0.0
    return res, rms


def jacobian(H: Matrix, pt: Point) -> list[list[float]]:
    """``[[dx/du, dx/dv], [dy/du, dy/dv]]`` of the mapping at ``pt``."""
    u, v = float(pt[0]), float(pt[1])
    a = H[0][0] * u + H[0][1] * v + H[0][2]
    b = H[1][0] * u + H[1][1] * v + H[1][2]
    w = H[2][0] * u + H[2][1] * v + H[2][2]
    if abs(w) < 1e-15:
        raise ValueError("point maps to infinity")
    w2 = w * w
    return [
        [(H[0][0] * w - a * H[2][0]) / w2, (H[0][1] * w - a * H[2][1]) / w2],
        [(H[1][0] * w - b * H[2][0]) / w2, (H[1][1] * w - b * H[2][1]) / w2],
    ]


def local_scale(H: Matrix, pt: Point) -> tuple[float, float]:
    """Plane units per pixel along the image u and v directions at ``pt``."""
    J = jacobian(H, pt)
    return math.hypot(J[0][0], J[1][0]), math.hypot(J[0][1], J[1][1])


def fit_report(src: Sequence[Point], dst: Sequence[Point], at: Point | None = None) -> dict:
    """Fit, residual summary, optional local scale, and warnings."""
    src_p, dst_p = _points("src", src), _points("dst", dst)
    H = fit(src_p, dst_p)
    res, rms = residuals(H, src_p, dst_p)
    warnings = []
    if len(src_p) == 4:
        warnings.append(FOUR_POINT_WARNING)
    _, ns = _normalizer(src_p)
    # Check the count first: the triangle scan is cubic in the number of points.
    if len(src_p) <= 6 and _min_triangle_area(ns) < NEAR_COLLINEAR_AREA:
        warnings.append("Some image points are nearly collinear; the estimate is fragile.")
    if _spread_ratio(src_p) < 0.05:
        warnings.append("Control points occupy a narrow region; avoid extrapolating beyond it.")
    report = {
        "H": H,
        "points": len(src_p),
        "residuals": res,
        "rms_residual": rms,
        "max_residual": max(res),
        "warnings": warnings,
    }
    if at is not None:
        sx, sy = local_scale(H, at)
        report["at"] = [float(at[0]), float(at[1])]
        report["mapped"] = list(apply(H, at))
        report["jacobian"] = jacobian(H, at)
        report["local_scale_u"] = sx
        report["local_scale_v"] = sy
        report["local_anisotropy_percent"] = (max(sx, sy) / min(sx, sy) - 1.0) * 100.0
    return report
