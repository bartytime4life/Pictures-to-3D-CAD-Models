"""The paper's light round a part: a fitted model of its soft shadow.

A part on a sheet shades the paper next to it. For a part thin beside the light's
distance, the light a point of paper loses is the part's footprint F convolved with a
kernel K set by the light (its direction, size and spread):

    L(x) = P(x) - (K * F)(x),

with P the paper's unshaded light, smooth across the sheet. The edge search
(sheet.half_level_search) needs L within a few blur widths of each edge, where the
part's own blurred step hides it. A line fitted to each profile beyond 2.5 sigma and
extrapolated inward misses the light's curvature there; K, fitted once to all the paper
round the part, carries the shadow's shape to every edge.

`fit_paper_light` fits P as a quadratic and K >= 0 on a grid of nodes (bilinear tents)
to the photo's linear light on paper cells beyond 2.5 sigma from the classified part,
with the photo's blur applied to the model. The step's own blurred tail on those cells
is removed first. K's smoothness prior is chosen by how well a fit to the farther paper
predicts the band nearest the edges, the band the model is used to reach, and the model
is returned only if that prediction is within ADEQUATE_FRACTION of the paper's light:
a shadow with an edge sharper than the node grid can describe is left to the line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

CELL_MM = 0.5  # the fit's working grid
NODE_CELLS = 2  # kernel node spacing in cells (about 1.1 mm)
RADIUS_MM = 9.0  # kernel reach
BAND_MM = 15.0  # paper used, out from the part
NEAR_MM = 1.5  # width of the held-out band nearest the edges
PRIORS = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)  # candidate smoothness weights
RIDGE = 1e-3
ADEQUATE_FRACTION = 0.02
BORDER_MM = 3.0  # as edges.BORDER_MM: the sheet's margin, never paper data
MIN_CELLS = 400


@dataclass
class PaperLight:
    """Predicted paper light on the rectified grid: `sharp` before the photo's blur, as
    the edge model needs it, and `blurred` after it, as the profiles see it."""

    sharp: np.ndarray
    blurred: np.ndarray
    info: dict = field(default_factory=dict)


def fit_paper_light(g, mask, ppm, sigma, covariance=None):
    """Fit the paper's light round the classified part (`mask`, rectified) in the
    linear-light image `g`. `sigma` is the edge blur in px, or `covariance` its 2 x 2
    covariance (px^2) when it differs by direction. Returns a PaperLight, with
    info["used"] False and no images when the model is not adequate or the paper is too
    scarce to fit it; the caller then keeps the per-profile line."""
    H, W = g.shape
    f = max(1, round(CELL_MM * ppm))
    h, w = H // f, W // f
    spread = float(np.sqrt(np.linalg.eigvalsh(covariance).max())) if covariance is not None else float(sigma)
    info = {"used": False}
    if spread <= 0 or h < 8 or w < 8:
        return PaperLight(None, None, info)
    gw = g[: h * f, : w * f].reshape(h, f, w, f).mean((1, 3)).astype(np.float64)
    material = (mask > 0).astype(np.float32)
    Fw = material[: h * f, : w * f].reshape(h, f, w, f).mean((1, 3)).astype(np.float64)
    # Distance (px) from each paper pixel to the part, and per cell its least.
    dist = cv2.distanceTransform((mask == 0).astype(np.uint8), cv2.DIST_L2, 5)
    border = int(BORDER_MM * ppm + 4 * spread) + 2
    dist[:border, :] = dist[-border:, :] = 0
    dist[:, :border] = dist[:, -border:] = 0
    distw = dist[: h * f, : w * f].reshape(h, f, w, f).min((1, 3))

    nc = NODE_CELLS
    tent1 = 1 - np.abs(np.arange(-nc + 1, nc)) / nc
    base = cv2.filter2D(Fw, -1, np.outer(tent1, tent1), borderType=cv2.BORDER_CONSTANT)
    based = _blur(base, spread, covariance, f)
    reach = math.ceil(RADIUS_MM * ppm / f / nc)
    offsets = [(i * nc, j * nc) for i in range(-reach, reach + 1) for j in range(-reach, reach + 1)]
    pad = reach * nc + 1
    padded_blur = np.pad(based, pad)
    n = 2 * reach + 1
    smooth = _laplacian(n)
    rows, cols = np.mgrid[0:h, 0:w]
    u_grid, v_grid = (cols + 0.5 - w / 2) / w, (rows + 0.5 - h / 2) / h
    checker = ((rows + cols) % 2) == 0  # neighbouring cells share pixels' noise

    def cells(near_px):
        return np.nonzero((distw >= near_px) & (distw <= BAND_MM * ppm) & checker)

    def design(yy, xx):
        kernel = np.column_stack([padded_blur[yy - dy + pad, xx - dx + pad] for dy, dx in offsets])
        u, v = u_grid[yy, xx], v_grid[yy, xx]
        return np.hstack([np.column_stack([np.ones_like(u), u, v, u * u, u * v, v * v]), -kernel])

    def solve(normal, rhs, prior):
        scale = np.trace(normal[6:, 6:]) / (n * n)
        matrix = normal.copy()
        matrix[6:, 6:] += prior * scale * smooth / 20 + RIDGE * scale * np.eye(n * n)
        free = np.ones(len(rhs), bool)
        theta = np.zeros(len(rhs))
        for _ in range(60):  # active set: kernel nodes held at zero where they would go negative
            theta = np.zeros(len(rhs))
            index = np.flatnonzero(free)
            theta[index] = _spd_solve(matrix[np.ix_(index, index)], rhs[index])
            negative = free & (np.arange(len(theta)) >= 6) & (theta < 0)
            if not negative.any():
                break
            free &= ~negative
        return theta

    def fit(yy, xx, values, choose):
        A = design(yy, xx)
        near = distw[yy, xx] < (2.5 * spread + 1.5) + NEAR_MM * ppm
        far = ~near
        normal_far, rhs_far = A[far].T @ A[far], A[far].T @ values[far]
        normal = normal_far + A[near].T @ A[near]
        rhs = rhs_far + A[near].T @ values[near]
        errors = {}
        if choose and near.sum() >= 50 and far.sum() >= MIN_CELLS:
            for prior in PRIORS:
                theta = solve(normal_far, rhs_far, prior)
                errors[prior] = float(np.mean((A[near] @ theta - values[near]) ** 2))
        prior = min(errors, key=errors.get) if errors else 1.0
        theta = solve(normal, rhs, prior)
        rms = float(np.sqrt(np.mean((A @ theta - values) ** 2)))
        return theta, prior, rms, errors

    def images(theta):
        # sum_j k_j base(x - offset_j) is a convolution; cv2.filter2D correlates, so
        # each node goes at the mirrored place of a kernel centred on the anchor.
        kernel = np.zeros((2 * reach * nc + 1,) * 2)
        for k, (dy, dx) in zip(theta[6:], offsets):
            kernel[reach * nc - dy, reach * nc - dx] = k
        sharp = cv2.filter2D(base, -1, kernel, borderType=cv2.BORDER_CONSTANT)
        blurred = cv2.filter2D(based, -1, kernel, borderType=cv2.BORDER_CONSTANT)
        c = theta[:6]
        paper = c[0] + c[1] * u_grid + c[2] * v_grid + c[3] * u_grid**2 + c[4] * u_grid * v_grid + c[5] * v_grid**2
        return paper, sharp, blurred

    yy, xx = cells(3.5 * spread + 1.5)
    if len(yy) < MIN_CELLS:
        return PaperLight(None, None, info)
    theta, _, _, _ = fit(yy, xx, gw[yy, xx], choose=False)
    # The step's own blurred tail on the paper, (A - L) (G * F), with A the part's level
    # and L the paper's light at the edge from that first fit; then the fit from 2.5 sigma.
    paper, sharp, _ = images(theta)
    inside = Fw > 0.999
    part_level = float(np.median(gw[inside])) if inside.any() else 0.0
    tail = (part_level - (paper - sharp)) * _blur(Fw, spread, covariance, f)
    yy, xx = cells(2.5 * spread + 1.5)
    theta, prior, rms, errors = fit(yy, xx, gw[yy, xx] - tail[yy, xx], choose=True)
    paper, sharp, blurred = images(theta)
    paper_level = float(np.median(paper[Fw == 0])) if (Fw == 0).any() else 1.0
    near_mse = min(errors.values()) if errors else rms**2
    excess = math.sqrt(max(0.0, near_mse - rms**2)) / max(paper_level, 1.0)
    depth = float((sharp[Fw == 0] / max(paper_level, 1.0)).max()) if (Fw == 0).any() else 0.0
    info.update(prior=prior, cells=len(yy), rms=rms, excess=excess, depth=depth)
    if excess > ADEQUATE_FRACTION:
        return PaperLight(None, None, info)
    info["used"] = True
    # Up to the rectified grid: cell (i, j) covers pixels [j f, (j + 1) f), as
    # cv2.resize's centre alignment assumes.
    return PaperLight(_upsample(paper - sharp, f, H, W), _upsample(paper - blurred, f, H, W), info)


def _upsample(image, f, H, W):
    h, w = image.shape
    out = cv2.resize(image.astype(np.float32), (w * f, h * f), interpolation=cv2.INTER_CUBIC)
    return np.pad(out, ((0, H - h * f), (0, W - w * f)), mode="edge")


def _blur(image, sigma, covariance, f):
    """The photo's Gaussian blur (px, or its covariance) applied on the working grid of
    f px cells."""
    cov = np.asarray(covariance, float) if covariance is not None else np.eye(2) * sigma**2
    cov = cov / (f * f)
    if math.sqrt(np.linalg.eigvalsh(cov).max()) < 0.3:
        return image.copy()
    r = math.ceil(4 * math.sqrt(np.linalg.eigvalsh(cov).max())) + 1
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1].astype(float)
    inv = np.linalg.inv(cov)
    kernel = np.exp(-0.5 * (inv[0, 0] * xx * xx + 2 * inv[0, 1] * xx * yy + inv[1, 1] * yy * yy))
    return cv2.filter2D(image, -1, kernel / kernel.sum(), borderType=cv2.BORDER_CONSTANT)


def _laplacian(n):
    """L^T L for the five-point Laplacian on an n x n node grid, zero beyond it."""
    lap = np.zeros((n * n, n * n))
    for a in range(n):
        for b in range(n):
            r = a * n + b
            lap[r, r] = -4
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if 0 <= a + da < n and 0 <= b + db < n:
                    lap[r, (a + da) * n + b + db] = 1
    return lap.T @ lap


def _spd_solve(matrix, rhs):
    """Solve M x = b for symmetric positive definite M by Cholesky and substitution.
    LAPACK's general solver can take a second on a few hundred unknowns under a
    threaded OpenBLAS; this takes milliseconds."""
    lower = np.linalg.cholesky(matrix)
    n = len(rhs)
    y = np.empty(n)
    for i in range(n):
        y[i] = (rhs[i] - lower[i, :i] @ y[:i]) / lower[i, i]
    x = np.empty(n)
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - lower[i + 1 :, i] @ x[i + 1 :]) / lower[i, i]
    return x
