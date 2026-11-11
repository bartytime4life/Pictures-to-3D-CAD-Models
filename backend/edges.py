"""Part segmentation and sub-pixel boundaries on a rectified (millimetre) image.

Pipeline: flatten illumination and classify part against sheet; take the part's pixel
contours; move every boundary point to the local half-level crossing (two passes, the
second with windows centred on the edge); measure edge blur; optionally undo the
parallax of a thick part's top face. All coordinates are rectified pixels, where pixel
i spans [i, i + 1].

Two images are used. The part is classified on the photo's saved values, the scale its
thresholds are stated in. Boundary positions, edge blur and the wall model are measured
in linear light (backend.tone), where blur and partial coverage mix tones linearly.
"""

from __future__ import annotations

import cv2
import numpy as np
from shapely.geometry import Point, Polygon

from . import tone
from .sheet import half_level_search, sample_bilinear
from .tone import encoded_from_linear

BORDER_MM = 3.0  # sheet margin excluded from the part search
TINY_AREA_MM2 = 0.1  # boundary regions below this are under the trace resolution


class EdgeError(ValueError):
    """A recoverable segmentation failure whose message is suitable for the user."""


def _poly_surface(values, sample_mask, degree, step=6):
    ys, xs = np.nonzero(sample_mask[::step, ::step])
    ys, xs = ys * step, xs * step
    samples = values[ys, xs].astype(np.float64)
    h, w = values.shape

    def basis(u, v):
        return np.column_stack(
            [u**i * v**j for i in range(degree + 1) for j in range(degree + 1 - i)]
        )

    u, v = xs / w - 0.5, ys / h - 0.5
    keep = np.ones(len(samples), bool)
    for _ in range(3):  # robust refit: drop texture and stray marks
        coef, *_ = np.linalg.lstsq(basis(u[keep], v[keep]), samples[keep], rcond=None)
        residual = samples - basis(u, v) @ coef
        spread = 1.4826 * np.median(np.abs(residual[keep])) + 1e-6
        keep = np.abs(residual) < 3 * spread
    # Evaluate sum_ij c_ij u^i v^j as outer products: one image-sized buffer instead of a
    # pixels x terms basis matrix (720 MB at the 12 MP rectification limit).
    u_axis = np.arange(w) / w - 0.5
    v_axis = np.arange(h) / h - 0.5
    surface = np.zeros((h, w), np.float64)
    terms = [(i, j) for i in range(degree + 1) for j in range(degree + 1 - i)]
    for (i, j), c in zip(terms, coef):
        surface += c * np.outer(v_axis**j, u_axis**i)
    return surface


def segment(gray, ppm, part_lighter=False):
    """Classify the part on the sheet; returns (mask uint8, notes).

    `gray` is the rectified photo as saved (0-255), not linear light. Both the sheet and
    the part get a smooth fitted brightness surface, so a gradient, vignetting or a soft
    shadow does not move the classification threshold. Only the largest part region is
    kept. The mask only starts the sub-pixel search (subpixel_rings).
    """
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), 0.7)
    work = 255 - g if part_lighter else g  # the part is the darker class in `work`
    h, w = g.shape
    border = max(2, int(BORDER_MM * ppm))
    inner = np.zeros((h, w), bool)
    inner[border:-border, border:-border] = True
    _, initial = cv2.threshold(
        np.clip(work, 0, 255).astype(np.uint8), 0, 1, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    initial = initial.astype(bool) & inner
    if initial.sum() < 64:
        raise EdgeError("No part was found on the reference sheet. Check the foreground setting.")
    away = int(4 * ppm) | 1
    kernel = np.ones((away, away), np.uint8)
    part_core = cv2.erode(initial.astype(np.uint8), kernel).astype(bool)
    sheet_core = ~cv2.dilate(initial.astype(np.uint8), kernel).astype(bool) & inner
    if sheet_core.sum() < 500:
        raise EdgeError(
            "The part covers almost the whole sheet. Use a larger sheet so paper shows around the part."
        )
    sheet_level = _poly_surface(work, sheet_core, degree=3)
    part_level = (
        _poly_surface(work, part_core, degree=1)
        if part_core.sum() > 500
        else np.full_like(sheet_level, float(work[initial].mean()))
    )
    if float(np.median(sheet_level - part_level)) < 15:
        raise EdgeError(
            "The part and the sheet are too similar in brightness. Use a sheet that contrasts with the part."
        )
    normalized = (sheet_level - work) / np.maximum(sheet_level - part_level, 1.0)
    normalized[~inner] = 0
    mask = (normalized > 0.5).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count < 2:
        raise EdgeError("No part was found on the reference sheet. Check the foreground setting.")
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = 1 + int(np.argmax(areas))
    notes = []
    others = int(np.sum(areas > max(64, 0.01 * areas.max()))) - 1
    if others:
        notes.append(
            f"Found {others + 1} separate regions on the sheet. Only the largest is traced; remove other objects if this is the wrong part."
        )
    mask = (labels == largest).astype(np.uint8)
    x, y, bw, bh = cv2.boundingRect(mask)
    if x <= border or y <= border or x + bw >= w - border or y + bh >= h - border:
        raise EdgeError(
            "The part reaches the edge of the reference sheet. Place it with a clear margin of sheet all round."
        )
    return mask, notes


def measurement_weights(rectified, mask, ppm):
    """Channel weights (tone.mix_weights) for measuring the part's boundary, from the
    part's interior and the sheet at least 2 mm clear of it. `rectified` is the
    rectified photo in 8-bit sRGB and `mask` the classified part."""
    near = 2 * max(1, int(ppm)) + 1
    part = cv2.erode(mask, np.ones((near, near), np.uint8)) > 0
    if part.sum() < 50:
        part = mask > 0
    clear = 2 * max(1, int(2 * ppm)) + 1
    sheet = cv2.dilate(mask, np.ones((clear, clear), np.uint8)) == 0
    border = max(2, int(BORDER_MM * ppm))
    sheet[:border] = sheet[-border:] = False
    sheet[:, :border] = sheet[:, -border:] = False
    if part.sum() < 8 or sheet.sum() < 50:
        return tone.LUMINANCE
    step = max(1, int(part.sum()) // 20000), max(1, int(sheet.sum()) // 20000)
    return tone.mix_weights(
        tone.surface_light(rectified[part][:: step[0]]),
        tone.surface_light(rectified[sheet][:: step[1]]),
    )


def ring_normals(ring, sigma=2.0):
    """Smoothed closed ring and its unit normals (orientation not normalised)."""
    n = len(ring)
    k = int(3 * sigma) | 1
    padded = np.concatenate([ring[-k:], ring, ring[:k]])
    smooth = np.column_stack(
        [
            cv2.GaussianBlur(padded[:, i : i + 1].astype(np.float64), (1, 2 * k + 1), sigma).ravel()
            for i in range(2)
        ]
    )[k : k + n]
    tangent = np.roll(smooth, -1, axis=0) - np.roll(smooth, 1, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-12
    return smooth, np.column_stack([-tangent[:, 1], tangent[:, 0]])


def edge_sigma(g, points, normals, half=8.0, step=0.125):
    """Gaussian-equivalent edge blur from the 25-75 % rise distance (1.349 sigma), on a
    linear-light image; profiles under 20 saved grey levels of contrast are skipped."""
    t = np.arange(-half, half + step / 2, step)
    sx = points[:, None, 0] + t[None, :] * normals[:, None, 0] - 0.5
    sy = points[:, None, 1] + t[None, :] * normals[:, None, 1] - 0.5
    profile = sample_bilinear(g, sx, sy)
    k = int(0.15 * len(t))
    low, high = np.median(profile[:, :k], axis=1), np.median(profile[:, -k:], axis=1)
    widths = []
    for row, lo, hi in zip(profile, low, high):
        if abs(encoded_from_linear(hi) - encoded_from_linear(lo)) < 20:
            continue
        f = (row - lo) / (hi - lo)
        if f[-1] < f[0]:
            f = f[::-1]
        rising = np.maximum.accumulate(f)
        widths.append(np.interp(0.75, rising, t) - np.interp(0.25, rising, t))
    return float(np.median(widths) / 1.349) if widths else 0.0


def subpixel_rings(mask, g, ppm):
    """Outer boundary and holes of the mask at the local half-level, sub-pixel.

    `g` is the lightly smoothed rectified photo in linear light.
    Returns (rings, sigma_px, tiny) where rings is a list of {"outer": bool, "points"}.
    Pass 1 starts from boundary-pixel centres, about half a pixel inside one side, so its
    level windows are asymmetric; pass 2 re-centres each point with windows beyond
    3.5 sigma on both sides of the measured edge blur.
    """
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    hierarchy = hierarchy[0]
    roots = [i for i, node in enumerate(hierarchy) if node[3] == -1]
    outer_index = max(roots, key=lambda i: cv2.contourArea(contours[i]))
    tiny_px = TINY_AREA_MM2 * ppm * ppm
    first, tiny = [], 0
    for i, contour in enumerate(contours):
        if i != outer_index and hierarchy[i][3] != outer_index:
            continue
        if i != outer_index and cv2.contourArea(contour) < max(tiny_px, 9):
            tiny += 1
            continue
        ring = contour.reshape(-1, 2).astype(np.float64) + 0.5
        if len(ring) < 8:
            tiny += 1
            continue
        smooth, normals = ring_normals(ring)
        moved, keep = half_level_search(g, smooth, normals, half=4.0)
        if keep.sum() < 8:
            tiny += 1
            continue
        first.append((i == outer_index, moved[keep]))
    outer = next(points for is_outer, points in first if is_outer)
    _, normals = ring_normals(outer)
    sigma = edge_sigma(g, outer[::4], normals[::4])
    half = max(4.0, 3.5 * sigma)
    rings = []
    for is_outer, points in first:
        _, normals = ring_normals(points)
        moved, keep = half_level_search(g, points, normals, half=half)
        if keep.sum() < 8:
            if is_outer:
                raise EdgeError("The part's outline is not clear enough to trace. Improve the contrast.")
            tiny += 1
            continue
        rings.append({"outer": is_outer, "points": moved[keep]})
    return rings, sigma, tiny


def material_normals(points, is_outer):
    """Unit normals pointing out of the material: outward on the outer boundary, into
    the hole on a hole boundary."""
    _, normals = ring_normals(points)
    polygon = Polygon(points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    stride = max(1, len(points) // 50)
    reach = min(2.0, 0.1 * float(np.ptp(points, axis=0).min()))
    probes = points[::stride] + reach * normals[::stride]
    inward = np.mean([polygon.contains(Point(p)) for p in probes]) > 0.5
    return -normals if is_outer == inward else normals


def correct_thickness(points, normals, nadir, height, thickness):
    """Undo the top-face parallax of a vertical-walled part of known thickness.

    From a camera `height` above the plane, a face at `thickness` projects onto the
    plane enlarged by height / (height - thickness) about the nadir. A silhouette point
    whose material-outward normal faces away from the nadir is formed by the top edge
    and is scaled back; one that faces the nadir is formed by the bottom edge.
    `points`, `nadir`, `height` and `thickness` share one unit.
    """
    relative = points - nadir
    top = np.einsum("ij,ij->i", normals, relative) > 0
    corrected = points.copy()
    corrected[top] = nadir + relative[top] * (height - thickness) / height
    return corrected, top


def normal_cdf(z):
    """Standard normal CDF via Abramowitz & Stegun 7.1.26 (|error| < 1.5e-7), vectorised."""
    x = np.abs(z) / np.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    erf = 1.0 - poly * np.exp(-x * x)
    return 0.5 * (1.0 + np.sign(z) * erf)


def two_step_refine(g, points, normals, band, sigma, wall_tone=None, step=0.125):
    """Locate an edge that has a narrow wall band on its material side.

    `g` holds linear light, in which the model below is exact for flat tones.
    Where a thick part's bottom edge forms the silhouette, the visible side wall lies
    between the bottom edge (t = 0, the edge sought) and the top edge (t = -w) along the
    material-outward normal t. A single mid-level crossing is biased into the material
    by up to 0.2 sigma when w is 1-3 sigma. The profile is modelled as a blurred two-step
        I(t) = C (1 - P1) + B (P1 - P2) + A P2,
        P1 = Phi((t + w - e) / sigma),  P2 = Phi((t - e) / sigma),
    linear in the tones A (sheet), B (wall) and C (top face) for a given edge offset e.
    For each candidate e the tones follow by least squares (variable projection); the
    residual minimum is refined by a parabola.

    As w -> 0 the wall term tends to (B - C)(w / sigma) phi, which is indistinguishable
    from a shift of e, so B and e are confounded. Pass `wall_tone` (estimated where the
    band is widest) to fix B and keep narrow-band fits well-posed. `band` holds each
    point's predicted w in image pixels. Returns (moved points, fitted wall tones).
    """
    if len(points) == 0:
        return points, np.empty(0)
    t = np.arange(-(float(band.max()) + 4 * sigma), 4 * sigma + step / 2, step)
    sx = points[:, None, 0] + t[None, :] * normals[:, None, 0] - 0.5
    sy = points[:, None, 1] + t[None, :] * normals[:, None, 1] - 0.5
    y = sample_bilinear(g, sx, sy)
    candidates = np.arange(-0.6, 0.8 + 1e-9, 0.02) * sigma
    residuals = np.empty((len(points), len(candidates)))
    walls = np.empty((len(points), len(candidates)))
    for k, e in enumerate(candidates):
        p1 = normal_cdf((t[None, :] + band[:, None] - e) / sigma)
        p2 = np.broadcast_to(normal_cdf((t[None, :] - e) / sigma), p1.shape)
        if wall_tone is None:
            basis = np.stack([1 - p1, p1 - p2, p2], axis=2)
            target = y
        else:
            basis = np.stack([1 - p1, p2], axis=2)
            target = y - wall_tone * (p1 - p2)
        size = basis.shape[2]
        gram = np.einsum("nti,ntj->nij", basis, basis) + 1e-9 * np.eye(size)
        rhs = np.einsum("nti,nt->ni", basis, target)
        tones = np.linalg.solve(gram, rhs[..., None])[..., 0]
        residuals[:, k] = np.einsum("nt,nt->n", target, target) - np.einsum("ni,ni->n", tones, rhs)
        walls[:, k] = tones[:, 1] if wall_tone is None else wall_tone
    best = np.clip(np.argmin(residuals, axis=1), 1, len(candidates) - 2)
    rows = np.arange(len(points))
    r0, r1, r2 = residuals[rows, best - 1], residuals[rows, best], residuals[rows, best + 1]
    denominator = r0 - 2 * r1 + r2
    shift = np.where(denominator > 0, 0.5 * (r0 - r2) / np.where(denominator > 0, denominator, 1), 0)
    offset = candidates[best] + np.clip(shift, -1, 1) * (candidates[1] - candidates[0])
    return points + offset[:, None] * normals, walls[rows, best]
