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
from .fitting import fit_circle
from .sheet import half_level_search, sample_keys
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
    """Channel weights (tone.choose_mix) for measuring the part's boundary, from the
    light 1 mm to either side of it along the outline and every hole. `rectified` is
    the rectified photo in 8-bit sRGB and `mask` the classified part."""
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    reach = max(4.0, ppm)
    one_side, other_side = [], []
    for contour in contours:
        if len(contour) < 8:
            continue
        smooth, normals = ring_normals(contour.reshape(-1, 2).astype(np.float64) + 0.5)
        step = max(1, len(smooth) // 2000)
        one_side.append(tone.light_at(rectified, smooth[::step] + reach * normals[::step]))
        other_side.append(tone.light_at(rectified, smooth[::step] - reach * normals[::step]))
    if not one_side:
        return tone.LUMINANCE
    return tone.choose_mix(np.vstack(one_side), np.vstack(other_side))


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
    linear-light image; profiles under 20 saved grey levels of contrast are skipped.

    Profiles are read by Keys cubic sampling. Bilinear sampling blurs what it reads by
    a variance of f (1 - f) at sub-pixel phase f, 1/6 px^2 on average: on exactly
    blurred straight edges it measured sigma 2.2-4.2 % high at 1.6 px and up to 8.4 % at
    1.2 px, where cubic sampling is within 0.6 % and 2.3 %."""
    t = np.arange(-half, half + step / 2, step)
    sx = points[:, None, 0] + t[None, :] * normals[:, None, 0] - 0.5
    sy = points[:, None, 1] + t[None, :] * normals[:, None, 1] - 0.5
    profile = sample_keys(g, sx, sy)
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
    3.5 sigma on both sides of the measured edge blur. Pass 2 also takes the paper side's
    brightness slope into the level (sheet.half_level_search with sigma), smoothed along
    the ring over 20 points, so a soft shadow beside an edge does not push it outward.
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
        # Keep the complete classified boundary as coverage evidence. Rejected
        # sub-pixel profiles are missing measurements, not observed straight chords.
        first.append((i == outer_index, moved[keep], ring, np.flatnonzero(keep)))
    outer = next((points for is_outer, points, _, _ in first if is_outer), None)
    if outer is None:
        raise EdgeError(
            "The part's outline is not clear enough to measure. Retake the photo in focus "
            "with stronger contrast between the part and the sheet."
        )
    _, normals = ring_normals(outer)
    sigma = edge_sigma(g, outer[::4], normals[::4])
    half = max(4.0, 3.5 * sigma)
    rings = []
    for is_outer, points, support, indices in first:
        _, normals = ring_normals(points)
        # Which side of each point the paper is on, from the classified mask 3 sigma out.
        probe = np.rint(points + 3 * sigma * normals - 0.5).astype(int)
        probe = np.clip(probe, 0, np.array(mask.shape[::-1]) - 1)
        paper_side = np.where(mask[probe[:, 1], probe[:, 0]] == 0, 1, -1)
        moved, keep = half_level_search(
            g, points, normals, half=half, sigma=sigma, ring_smoothing=20.0, paper_side=paper_side
        )
        if keep.sum() < 8:
            if is_outer:
                raise EdgeError("The part's outline is not clear enough to trace. Improve the contrast.")
            tiny += 1
            continue
        rings.append({
            "outer": is_outer, "points": moved[keep], "support": support,
            "support_indices": indices[keep],
        })
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


def roundness_focal(holes, pose_at, thickness, diagonal, gate, lo=10.0, hi=200.0, steps=49):
    """The focal length at which a thick part's holes are round after the parallax
    correction, or None.

    A hole's silhouette is formed by the top edge where its material normal faces away
    from the nadir and by the bottom edge where it faces it (correct_thickness), so only
    part of it is scaled back by (D - t) / D. With a wrong camera height D, that part
    lands off the true circle by t |p - N| (1/D_true - 1/D) and the corrected hole is
    stretched along the direction from the nadir. Its roundness therefore measures D,
    which the sheet alone does not fix in a nearly frontal view. For each candidate
    focal length the camera is posed from the sheet (`pose_at(focal_px)`), every hole is
    corrected and fitted as a circle, and the total squared residual of the holes that
    are round at some candidate is least at the true focal length.

    `holes` holds each hole's points (mm) before the parallax correction, with the edges
    that show a narrow wall already refined, and their material normals. `gate` is the
    circle tolerance in mm (a hole is round where its RMS is under max(gate, 1 % of its
    radius)). Focal lengths run from `lo` to `hi` mm (35 mm equivalent) on a geometric
    grid, then on a finer grid round the least total, refined by a parabola in log focal
    length. Returns (focal_px, holes used), or None when no hole is round, or the least
    total lies at an end of the grid or is not under half of both ends.
    """
    holes = [(p, n) for p, n in holes if len(p) >= 20]
    if not holes:
        return None
    per_mm = diagonal / np.hypot(36.0, 24.0)

    def residuals(f35, chosen):
        camera = pose_at(f35 * per_mm)
        if thickness >= 0.5 * camera["height_mm"]:
            return None
        out = []
        for points, normals in chosen:
            corrected, _ = correct_thickness(points, normals, camera["nadir_mm"], camera["height_mm"], thickness)
            _, _, radius, rms, _ = fit_circle(corrected)
            out.append((rms, radius))
        return np.array(out)

    grid = np.geomspace(lo, hi, steps)
    table = [residuals(f, holes) for f in grid]
    valid = np.array([t is not None for t in table])
    if valid.sum() < 3:
        return None
    grid = grid[valid]
    table = np.array([t for t in table if t is not None])  # (focal, hole, (rms, radius))
    counts = np.array([len(p) for p, _ in holes], float)
    rms, radius = table[:, :, 0], table[:, :, 1]
    best = rms.argmin(axis=0)
    round_ = rms[best, np.arange(len(holes))] < np.maximum(gate, 0.01 * radius[best, np.arange(len(holes))])
    if not round_.any():
        return None
    keep = [h for h, ok in zip(holes, round_) if ok]
    weights = counts[round_]
    totals = (rms[:, round_] ** 2 * weights).sum(axis=1)
    k = int(np.argmin(totals))
    if k in (0, len(grid) - 1) or totals[k] > 0.5 * min(totals[0], totals[-1]):
        return None
    fine = np.geomspace(grid[k - 1], grid[k + 1], 9)
    rows = [residuals(f, keep) for f in fine[1:-1]]
    if any(r is None for r in rows):
        return None
    inner = (np.array([r[:, 0] for r in rows]) ** 2 * weights).sum(axis=1)
    values = np.concatenate([[totals[k - 1]], inner, [totals[k + 1]]])
    j = int(np.clip(np.argmin(values), 1, len(fine) - 2))
    r0, r1, r2 = values[j - 1], values[j], values[j + 1]
    denominator = r0 - 2 * r1 + r2
    shift = float(np.clip(0.5 * (r0 - r2) / denominator, -1, 1)) if denominator > 0 else 0.0
    step = np.log(fine[1] / fine[0])
    return float(fine[j] * np.exp(shift * step) * per_mm), int(round_.sum())


def normal_cdf(z):
    """Standard normal CDF via Abramowitz & Stegun 7.1.26 (|error| < 1.5e-7), vectorised."""
    x = np.abs(z) / np.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    erf = 1.0 - poly * np.exp(-x * x)
    return 0.5 * (1.0 + np.sign(z) * erf)


def pooled_wall_tone(g, points, normals, band, sigma, steps=17, sample=160):
    """One wall tone shared by many narrow wall bands, or None.

    Where no band is wide enough (2.5 sigma) for a free two-step fit, each narrow band
    on its own confounds the wall tone with the edge offset (two_step_refine). One tone
    for the whole part is still identifiable from many bands of 1-3.5 sigma: for each
    candidate tone every point's edge offset is fitted with that tone fixed, and the
    total residual is least at the true tone. The total is evaluated on a grid over the
    image's light, from black to its 99.5th percentile, then on a finer grid around its
    least value, whose minimum is refined by a parabola. Each evaluation is cheap: for a
    given edge offset a point's residual is a quadratic in the tone, whose coefficients
    are found once (_wall_tone_parabolas). At most `sample` points, spread evenly, take
    part. A minimum at an end of the grid, or one not well below both ends, means the
    tone is not determined.

    Only bands of at least sigma take part. Below that a wall differs from an edge
    shift only at second order in w / sigma, so on noise-free profiles with bands under
    0.4 sigma the 0.3-level error of cubic sampling alone made a false minimum (a tone of
    186 for 15, moving edges by 0.18 sigma), and with any noise the minimum is flat.
    """
    keep = band >= sigma
    points, normals, band = points[keep], normals[keep], band[keep]
    if len(points) < 30:
        return None
    if len(points) > sample:
        pick = np.linspace(0, len(points) - 1, sample).round().astype(int)
        points, normals, band = points[pick], normals[pick], band[pick]
    _, c0, c1, c2 = _wall_tone_parabolas(g, points, normals, band, sigma)

    def total(tone):
        return _refined_minimum(c0 + (c1 + c2 * tone) * tone)[2].sum()

    coarse = np.linspace(0.0, float(np.percentile(g, 99.5)), steps)
    totals = np.array([total(tone) for tone in coarse])
    k = int(np.argmin(totals))
    if k in (0, steps - 1) or totals[k] > 0.8 * min(totals[0], totals[-1]):
        return None
    grid = np.linspace(coarse[k - 1], coarse[k + 1], 9)
    totals = np.array([totals[k - 1], *(total(tone) for tone in grid[1:-1]), totals[k + 1]])
    k = int(np.clip(np.argmin(totals), 1, len(grid) - 2))
    r0, r1, r2 = totals[k - 1], totals[k], totals[k + 1]
    denominator = r0 - 2 * r1 + r2
    shift = 0.5 * (r0 - r2) / denominator if denominator > 0 else 0.0
    return float(grid[k] + np.clip(shift, -1, 1) * (grid[1] - grid[0]))


def _wall_tone_parabolas(g, points, normals, band, sigma, step=0.125):
    """The two-step model's residual as a function of the wall tone B, for each point
    and each candidate edge offset e (two_step_refine).

    With e fixed the model is linear in the tones, so with A and C fitted for each B
    the residual sum of squares is exactly c0 + c1 B + c2 B^2. With u = 1 - P1,
    v = P1 - P2, w = P2, profile y, G the Gram matrix of (u, w) and r_a = (u.a, w.a):
        c0 = y.y - r_y' G^-1 r_y,   c1 = -2 (v.y - r_v' G^-1 r_y),   c2 = v.v - r_v' G^-1 r_v,
    where c2 >= 0 is what is left of v after projecting out u and w. Returns
    (candidates, c0, c1, c2), each coefficient of shape (points, candidates).
    """
    t = np.arange(-(float(band.max()) + 4 * sigma), 4 * sigma + step / 2, step)
    sx = points[:, None, 0] + t[None, :] * normals[:, None, 0] - 0.5
    sy = points[:, None, 1] + t[None, :] * normals[:, None, 1] - 0.5
    y = sample_keys(g, sx, sy)
    yy = np.einsum("nt,nt->n", y, y)
    candidates = np.arange(-0.6, 0.8 + 1e-9, 0.02) * sigma
    c0, c1, c2 = (np.empty((len(points), len(candidates))) for _ in range(3))
    for k, e in enumerate(candidates):
        p1 = normal_cdf((t[None, :] + band[:, None] - e) / sigma)
        p2 = normal_cdf((t - e) / sigma)
        u, v = 1 - p1, p1 - p2[None, :]
        gram = ((u * u).sum(1), u @ p2, p2 @ p2)
        ry, rv = ((u * y).sum(1), y @ p2), ((u * v).sum(1), v @ p2)
        c0[:, k] = yy - _inverse_form(gram, ry, ry)
        c1[:, k] = -2 * ((v * y).sum(1) - _inverse_form(gram, rv, ry))
        c2[:, k] = (v * v).sum(1) - _inverse_form(gram, rv, rv)
    return candidates, c0, c1, c2


def _inverse_form(gram, a, b):
    """a' G^-1 b for 2-vectors a, b and the symmetric 2 x 2 G = [[guu, guw], [guw, gww]],
    each entry an array over points."""
    guu, guw, gww = gram
    return (gww * a[0] * b[0] - guw * (a[0] * b[1] + a[1] * b[0]) + guu * a[1] * b[1]) / (guu * gww - guw * guw)


def _refined_minimum(residuals):
    """Per row of residuals over the candidate offsets: the index of the least value
    (kept off the ends), the parabola's vertex shift from it in grid steps (within
    one), and the parabola's least value where its vertex lies within the bracket,
    never below zero, which a sum of squares cannot be."""
    best = np.clip(np.argmin(residuals, axis=1), 1, residuals.shape[1] - 2)
    rows = np.arange(len(residuals))
    r0, r1, r2 = residuals[rows, best - 1], residuals[rows, best], residuals[rows, best + 1]
    denominator = r0 - 2 * r1 + r2
    safe = np.where(denominator > 0, denominator, 1)
    shift = np.where(denominator > 0, 0.5 * (r0 - r2) / safe, 0)
    inside = (denominator > 0) & (np.abs(shift) <= 1)
    least = np.maximum(r1 - np.where(inside, 0.125 * (r0 - r2) ** 2 / safe, 0), 0.0)
    return best, np.clip(shift, -1, 1), least


def two_step_refine(g, points, normals, band, sigma, wall_tone=None, step=0.125, with_residuals=False):
    """Locate an edge that has a narrow wall band on its material side.

    `g` holds linear light, in which the model below is exact for flat tones.
    Where a thick part's bottom edge forms the silhouette, the visible side wall lies
    between the bottom edge (t = 0, the edge sought) and the top edge (t = -w) along the
    material-outward normal t. A single mid-level crossing is biased into the material
    by up to 0.2 sigma when w is 1-3 sigma. The profile is modelled as a blurred two-step
        I(t) = C (1 - P1) + B (P1 - P2) + A P2,
        P1 = Phi((t + w - e) / sigma),  P2 = Phi((t - e) / sigma),
    linear in the tones A (sheet), B (wall) and C (top face) for a given edge offset e.
    For each candidate e the tones follow by least squares (variable projection), here
    through the residual's exact quadratic in B (_wall_tone_parabolas): a free fit takes
    its vertex, a fixed tone its value. The residual minimum over e is refined by a
    parabola. Profiles are read by Keys cubic sampling: the fit uses every sample, so
    bilinear sampling's error at the shoulders of a blurred edge (up to 2.1 grey levels
    in 200 at sigma = 1.7 px, against 0.33) would bias it.

    As w -> 0 the wall term tends to (B - C)(w / sigma) phi, which is indistinguishable
    from a shift of e, so B and e are confounded. Pass `wall_tone` (estimated where the
    band is widest) to fix B and keep narrow-band fits well-posed. `band` holds each
    point's predicted w in image pixels. Returns (moved points, fitted wall tones), and
    with `with_residuals` also each point's least residual sum of squares.
    """
    if len(points) == 0:
        return (points, np.empty(0), np.empty(0)) if with_residuals else (points, np.empty(0))
    candidates, c0, c1, c2 = _wall_tone_parabolas(g, points, normals, band, sigma, step)
    if wall_tone is None:
        curvature = c2 + 1e-9  # a band too narrow to see leaves c2 at zero
        walls = -c1 / (2 * curvature)
        residuals = c0 - c1 * c1 / (4 * curvature)
    else:
        walls = np.full(c0.shape, float(wall_tone))
        residuals = c0 + (c1 + c2 * wall_tone) * wall_tone
    best, shift, least = _refined_minimum(residuals)
    offset = candidates[best] + shift * (candidates[1] - candidates[0])
    moved = points + offset[:, None] * normals
    rows = np.arange(len(points))
    if with_residuals:
        return moved, walls[rows, best], least
    return moved, walls[rows, best]
