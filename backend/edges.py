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

import itertools
import math

import cv2
import numpy as np
from shapely.geometry import Point, Polygon

from . import shadow, tone
from .fitting import fit_circle
from .sheet import half_level_search, sample_bilinear, sample_keys
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


DIRECTIONAL_RATIO = 1.15  # principal blur spreads further apart are traced by direction
LIGHT_ROUNDS = 2  # shadow fits, each with the footprint of the rings the last one placed


def _paper_light_variation(light, points, normals, t, step, paper_side, spread):
    """How the paper's own uneven light shows in each profile: the shadow model's light
    before the blur (shadow.PaperLight.sharp) less its value at the point, kept on the
    paper side of the point only (`paper_side`, +1 or -1 per point: the side of t the
    paper lies on) and blurred along t by each point's `spread` (Simpson's rule over
    5 standard deviations each way).

    Across a straight edge with material level A and paper light L, a Gaussian blur
    makes A + (L(0) - A) Phi(t / sigma) + int_{x > 0} (L(x) - L(0)) phi_sigma(t - x) dx;
    the last term is this one, so subtracting it leaves the clean step. A constant
    offset of the light makes (L(0) - A) Phi(t / sigma) instead and leaves the width as
    it was, so only the light's variation matters."""
    spread = np.broadcast_to(np.asarray(spread, float), (len(points),))
    side = np.broadcast_to(np.asarray(paper_side, float), (len(points),))
    m = math.ceil(5 * float(spread.max()) / step) + 1
    ext = t[0] + (np.arange(len(t) + 2 * m) - m) * step
    ex = points[:, None, 0] + ext[None, :] * normals[:, None, 0] - 0.5
    ey = points[:, None, 1] + ext[None, :] * normals[:, None, 1] - 0.5
    sharp = sample_bilinear(light.sharp, ex, ey)
    at_point = sample_bilinear(light.sharp, points[:, :1] - 0.5, points[:, 1:] - 0.5)
    delta = np.where(ext[None, :] * side[:, None] > 0, sharp - at_point, 0.0)
    z = np.linspace(-5.0, 5.0, 21)
    simpson = np.full(21, 2.0)
    simpson[1::2] = 4.0
    simpson[[0, -1]] = 1.0
    wz = simpson * (z[1] - z[0]) / 3 * np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    rows = np.arange(len(points))[:, None]
    columns = m + np.arange(len(t))[None, :]
    out = np.zeros((len(points), len(t)))
    for zk, wk in zip(z, wz):
        position = columns - (spread * zk / step)[:, None]
        i0 = np.clip(np.floor(position).astype(int), 0, delta.shape[1] - 2)
        frac = position - i0
        out += wk * (delta[rows, i0] * (1 - frac) + delta[rows, i0 + 1] * frac)
    return out


def _edge_widths(g, points, normals, half=8.0, step=0.125, single_step=False, light=None, paper_side=None):
    """Each profile's Gaussian-equivalent blur, its 25-75 % rise distance over 1.349, on
    a linear-light image; NaN where the profile has under 20 saved grey levels of
    contrast. `half` may be one value or one per point. With `single_step`, also NaN
    where the profile is not one clean step: where, normalised to rise from its low end
    to its high one, it falls back by more than 10 % of the step after its peak or
    before its trough, or overshoots either end by 15 %. Such a profile reaches another
    edge (across a thin hole or at a sharp corner), and its width is not this edge's.

    Profiles are read by Keys cubic sampling. Bilinear sampling blurs what it reads by
    a variance of f (1 - f) at sub-pixel phase f, 1/6 px^2 on average: on exactly
    blurred straight edges it measured sigma 2.2-4.2 % high at 1.6 px and up to 8.4 % at
    1.2 px, where cubic sampling is within 0.6 % and 2.3 %.

    With the shadow model's `light` (shadow.PaperLight) and `paper_side` (per point),
    the paper's own light variation is removed from each profile first
    (_paper_light_variation, blurred by half / 5, the window's expected width). A soft
    shadow darkens the paper towards the edge, and its slow rise read as blur: a
    rendered 3 px blur measured 3.88 px without a shadow and 4.17 px beside a 25 % one.
    """
    half = np.broadcast_to(np.asarray(half, float), (len(points),))
    reach = float(half.max())
    t = np.arange(-reach, reach + step / 2, step)
    sx = points[:, None, 0] + t[None, :] * normals[:, None, 0] - 0.5
    sy = points[:, None, 1] + t[None, :] * normals[:, None, 1] - 0.5
    profile = sample_keys(g, sx, sy)
    if light is not None and paper_side is not None:
        profile = profile - _paper_light_variation(light, points, normals, t, step, paper_side, half / 5)
    widths = np.full(len(points), np.nan)
    for i, (row, h) in enumerate(zip(profile, half)):
        inside = np.abs(t) <= h + step / 2
        row, ti = row[inside], t[inside]
        k = int(0.15 * len(ti))
        lo, hi = np.median(row[:k]), np.median(row[-k:])
        if abs(encoded_from_linear(hi) - encoded_from_linear(lo)) < 20:
            continue
        f = (row - lo) / (hi - lo)
        if f[-1] < f[0]:
            f = f[::-1]
        if single_step and (f.max() - f[-1] > 0.1 or f[0] - f.min() > 0.1 or f.max() > 1.15 or f.min() < -0.15):
            continue
        rising = np.maximum.accumulate(f)
        widths[i] = (np.interp(0.75, rising, ti) - np.interp(0.25, rising, ti)) / 1.349
    return widths


def edge_sigma(g, points, normals, half=8.0, step=0.125, light=None, paper_side=None, start=None):
    """Gaussian-equivalent edge blur: the median of the profiles' (_edge_widths, with the
    shadow model's `light` and `paper_side` when given).

    Each profile's plateaus are read at the ends of its window, which must reach well
    beyond the blur: a 3 px blur read 11 % narrow in a +-8 px window (2.2 sigma), and
    1.7 % at 2 px. The window is therefore widened to 5 sigma and the blur measured
    again, twice; up to 1.6 px the first window already reaches that far. With `start`,
    a blur at least this one measured before (with the shadow in), one window of 5 times
    it already reaches far enough.
    """
    if start:
        widths = _edge_widths(g, points, normals, max(half, 5 * start), step, light=light, paper_side=paper_side)
        widths = widths[np.isfinite(widths)]
        return float(np.median(widths)) if len(widths) else 0.0
    sigma = 0.0
    for _ in range(3):
        widths = _edge_widths(g, points, normals, max(half, 5 * sigma), step, light=light, paper_side=paper_side)
        widths = widths[np.isfinite(widths)]
        if not len(widths):
            return 0.0
        previous, sigma = sigma, float(np.median(widths))
        if 5 * sigma <= half or abs(sigma - previous) < 1e-3 * sigma:
            break
    return sigma


DIRECTION_BINS = 6  # of 30 degrees, modulo 180, for the blur covariance's support
MIN_PER_BIN = 15  # clean profiles a direction bin needs to count
ADEQUATE_FIT = 0.1  # largest systematic relative variance residual of a direction bin


def edge_covariance(g, points, normals, sigma, step=0.125, min_ratio=None, light=None, paper_side=None, start=None):
    """The blur's 2 x 2 covariance, from edge widths across many directions, or None.

    A Gaussian blur of covariance S spreads an edge with unit normal n by sigma_n^2 =
    n' S n, so each profile's width (_edge_widths) gives one linear equation in
    (S_xx, S_xy, S_yy). Each profile's window reaches 5 times its expected sigma_n (at
    least 8 px); a fixed window cuts a wide blur's plateaus short and reads it narrow.
    Only clean single steps take part: a thin hole whose far side fell inside the
    windows read as a blur 2.5 times wider one way on an evenly blurred photo.

    The fit must be supported in several directions, not just numerically possible.
    The profiles are grouped by normal direction into DIRECTION_BINS bins (modulo 180
    degrees), and a bin counts with MIN_PER_BIN clean profiles. Three unknowns need three
    such bins and a numerical rank-three covariance design: opposite normals can
    straddle a bin boundary through floating angle rounding without adding information.
    A part with edges in two directions (a rectangle, whose corners add only a
    few, often unclean profiles) cannot separate the cross term from the rest. Each
    counted bin weighs the same in the least squares: a part's long straight edges
    give two bins most of the profiles, and an unweighted fit follows them and pushes
    its misfit into the others (one read 11.5 % off on a rendered photo, 7 % weighted).
    Profiles more than 3 robust standard deviations off are trimmed twice. The model
    must explain every counted bin, judged one by one, so that a dominant edge direction
    cannot hide a minority one's disagreement in a pooled statistic. One profile's width is
    only good to a few per cent, so a bin's median absolute residual is mostly noise;
    a wrong model instead shifts the whole bin. A bin whose median relative variance
    residual (signed) is beyond both ADEQUATE_FIT and three standard errors of that
    median means the blur is not one Gaussian covariance (a disk, a motion streak, a blur
    that varies across the photo), and None is returned, as it is without three bins, 30
    profiles or a positive-definite result.

    With `min_ratio`, the fit stops after its first pass when that pass's principal
    spreads are under 0.95 min_ratio apart: its windows suit the isotropic guess and
    read a wide direction narrow, so the final pass would not reach min_ratio either.

    `light` and `paper_side` remove a soft shadow's light from the profiles first, as in
    _edge_widths. With `start`, a covariance measured before with the shadow in, only
    the final pass runs, its windows sized by `start`.
    """
    if len(points) < 30 or sigma <= 0:
        return None
    c, s = normals[:, 0], normals[:, 1]
    design = np.column_stack([c * c, 2 * c * s, s * s])
    direction = np.floor((np.degrees(np.arctan2(s, c)) % 180.0) / (180.0 / DIRECTION_BINS)).astype(int) % DIRECTION_BINS
    cov = np.array([[sigma**2, 0.0], [0.0, sigma**2]]) if start is None else np.asarray(start, float)
    for final in ((False, True) if start is None else (True,)):
        expected = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", normals, cov, normals), 1e-6))
        widths = _edge_widths(
            g, points, normals, np.maximum(8.0, 5 * expected), step, single_step=True, light=light, paper_side=paper_side
        )
        ok = np.isfinite(widths)
        counts = np.bincount(direction[ok], minlength=DIRECTION_BINS)
        counted = counts >= MIN_PER_BIN
        if ok.sum() < 30 or counted.sum() < 3:
            return None
        ok &= counted[direction]
        for _ in range(3):
            weight = 1.0 / np.sqrt(np.maximum(np.bincount(direction[ok], minlength=DIRECTION_BINS), 1))[direction]
            fit, _, rank, _ = np.linalg.lstsq(design[ok] * weight[ok, None], widths[ok] ** 2 * weight[ok], rcond=None)
            if rank < 3:
                return None
            residual = np.where(ok, design @ fit - widths**2, np.inf)
            # A robust spread, floored at 1 % of the squared widths, so that exact data
            # are not trimmed to nothing.
            spread = max(
                1.4826 * float(np.median(np.abs(residual[ok] - np.median(residual[ok])))),
                0.01 * float(np.median(widths[ok] ** 2)),
            )
            trimmed = ok & (np.abs(residual) <= 3 * spread)
            if trimmed.sum() < 30 or (np.bincount(direction[trimmed], minlength=DIRECTION_BINS) >= MIN_PER_BIN).sum() < 3:
                break
            ok = trimmed
        cov = np.array([[fit[0], fit[1]], [fit[1], fit[2]]])
        if np.linalg.eigvalsh(cov).min() <= 0:
            return None
        if not final:
            # The first pass's windows suit the isotropic guess and cut a wide
            # direction short; only the final pass, with windows sized by its fit, is
            # judged.
            low, high = np.linalg.eigvalsh(cov)
            if min_ratio is not None and high < (0.95 * min_ratio) ** 2 * low:
                return None
            continue
        model = np.einsum("ij,jk,ik->i", normals, cov, normals)
        relative = (widths**2 - model) / model
        for b in np.flatnonzero(counted):
            r = relative[np.isfinite(widths) & (direction == b)]
            middle = float(np.median(r))
            # The standard error of a median: 1.253 standard deviations over sqrt(n),
            # the deviation taken robustly as 1.4826 median absolute deviations.
            error = 1.253 * 1.4826 * float(np.median(np.abs(r - middle))) / math.sqrt(len(r))
            if abs(middle) > max(ADEQUATE_FIT, 3 * error):
                return None
    return cov


def edge_widths_by_direction(g, points, normals, sigma, step=0.125, light=None, paper_side=None, start=None):
    """Each direction bin's blur width (px, its clean profiles' median), NaN where a bin
    has fewer than MIN_PER_BIN clean single-step profiles, each bin's count of clean
    profiles and its normals' mean direction (radians, modulo pi); None without two
    measured bins.

    When the blur is not measured as a covariance (edge_covariance: a part whose edges
    face two ways, or a blur that one Gaussian covariance does not explain), each
    direction's width across its edges is still measured directly. As there, the
    windows reach 5 times the expected width (at least 8 px): a first pass at 5 sigma,
    then one at 5 times each bin's own width. `light` and `paper_side` remove a soft
    shadow's light from the profiles first, as in _edge_widths. With `start`, bin widths
    measured before with the shadow in, one pass at 5 times them runs.
    """
    if len(points) < 2 * MIN_PER_BIN or sigma <= 0:
        return None
    angle = np.degrees(np.arctan2(normals[:, 1], normals[:, 0])) % 180.0
    direction = np.floor(angle / (180.0 / DIRECTION_BINS)).astype(int) % DIRECTION_BINS
    expected = np.full(len(points), float(sigma))
    if start is not None:
        expected = np.where(np.isfinite(start[direction]), start[direction], expected)
    medians = np.full(DIRECTION_BINS, np.nan)
    for _ in range(2 if start is None else 1):
        widths = _edge_widths(
            g, points, normals, np.maximum(8.0, 5 * expected), step, single_step=True, light=light, paper_side=paper_side
        )
        ok = np.isfinite(widths)
        counts = np.bincount(direction[ok], minlength=DIRECTION_BINS)
        medians = np.array([
            float(np.median(widths[ok & (direction == b)])) if counts[b] >= MIN_PER_BIN else np.nan
            for b in range(DIRECTION_BINS)
        ])
        if np.isfinite(medians).sum() < 2:
            return None
        expected = np.where(np.isfinite(medians[direction]), medians[direction], expected)
    # Normals are directions modulo pi: their mean is half the doubled angles' mean.
    doubled = np.exp(2j * np.radians(angle))
    means = np.array([
        float(np.angle(doubled[ok & (direction == b)].mean()) / 2) % math.pi if counts[b] else np.nan
        for b in range(DIRECTION_BINS)
    ])
    return medians, counts, means


def _spread_by_direction(normals, medians):
    """Each normal's width from its own direction bin, or the angularly nearest bin
    that was measured (edge_widths_by_direction)."""
    centres = (np.arange(DIRECTION_BINS) + 0.5) * (180.0 / DIRECTION_BINS)
    measured = np.flatnonzero(np.isfinite(medians))
    angle = np.degrees(np.arctan2(normals[:, 1], normals[:, 0])) % 180.0
    gap = np.abs(angle[:, None] - centres[measured][None, :])
    gap = np.minimum(gap, 180.0 - gap)
    return medians[measured][np.argmin(gap, axis=1)]


def _covariance_from_directions(medians, counts, means):
    """A positive-definite covariance whose spread across the two best-supported
    measured direction bins equals their widths, for the shadow model's blur when no
    covariance is fitted, or None. Aligned with the first bin's normal n1:
    S = w1^2 n1 n1' + beta n1p n1p', where n1p is n1 turned a quarter, and
    n2' S n2 = w2^2 gives beta = (w2^2 - w1^2 cos^2 t) / sin^2 t, t being the angle
    between the bins' mean normals. The cross term in that frame is not measured and is
    taken as 0."""
    measured = np.flatnonzero(np.isfinite(medians))
    if len(measured) < 2:
        return None
    first, second = measured[np.argsort(-counts[measured], kind="stable")[:2]]
    angles = means[[first, second]]
    t = angles[1] - angles[0]
    if abs(math.sin(t)) < 0.3:
        return None
    w1, w2 = medians[first], medians[second]
    beta = (w2**2 - w1**2 * math.cos(t) ** 2) / math.sin(t) ** 2
    if beta <= 0:
        return None
    n1 = np.array([math.cos(angles[0]), math.sin(angles[0])])
    n1p = np.array([-n1[1], n1[0]])
    return w1**2 * np.outer(n1, n1) + beta * np.outer(n1p, n1p)


def _paper_side_of(mask, points, normals, spread):
    """+1 where the classified mask is paper `3 spread` along each normal, else -1: the
    side of t the paper lies on."""
    probe = np.rint(points + 3 * np.asarray(spread, float).reshape(-1, 1) * normals - 0.5).astype(int)
    probe = np.clip(probe, 0, np.array(mask.shape[::-1]) - 1)
    return np.where(mask[probe[:, 1], probe[:, 0]] == 0, 1, -1)


def _measure_blur(g, outline, outline_normals, sampled, light=None, mask=None, before=None):
    """The edge blur for subpixel_rings: (sigma, covariance or None, per-direction widths
    or None, the shadow model's covariance or None, the raw estimates). `outline` and its
    normals give the one sigma; `sampled`, [(points, normals)] per ring, the directional
    measurements. With the shadow model's `light` (and the `mask`, whose paper side
    tells each profile's paper side), every width is read with the paper's light
    variation removed (_edge_widths), starting from `before`, the raw estimates of the
    measurement with the shadow in: its wider blur sizes windows that still reach 5
    times the narrower one, so the passes that widen them are not repeated."""
    before = before or {}
    sigma_guess = before.get("sigma")
    sides = {}
    if light is not None:
        sides["outline"] = _paper_side_of(mask, outline, outline_normals, np.full(len(outline), sigma_guess))
        sides["rings"] = np.concatenate([
            _paper_side_of(mask, p, n, np.full(len(p), sigma_guess)) for p, n in sampled
        ])
    # Without a light the calls stay as they were (tests stand in for edge_sigma).
    on_outline = {"light": light, "paper_side": sides["outline"]} if sides else {}
    with_light = {"light": light, "paper_side": sides["rings"]} if sides else {}
    sigma = edge_sigma(g, outline, outline_normals, **on_outline, **({"start": sigma_guess} if sides else {}))
    raw = {"sigma": sigma}
    all_points = np.vstack([p for p, _ in sampled])
    all_normals = np.vstack([n for _, n in sampled])
    # A blur that differs by direction spreads each edge by its own sigma_n, measured
    # over every ring's edges (edge_covariance); the outline alone may face few ways.
    covariance = edge_covariance(
        g, all_points, all_normals, sigma, min_ratio=DIRECTIONAL_RATIO, **with_light,
        **({"start": before["covariance"]} if sides and before.get("covariance") is not None else {}),
    )
    raw["covariance"] = covariance
    if covariance is not None:
        # Rendered photos tilted up to 22 degrees fit principal spreads 1.00-1.05 apart
        # (foreshortening); a shaken camera's 1.3-2.5. Below DIRECTIONAL_RATIO the one
        # measured sigma stands, as it was validated.
        low, high = np.linalg.eigvalsh(covariance)
        if high < DIRECTIONAL_RATIO**2 * low:
            covariance = None
    if covariance is not None:
        # The returned sigma serves the curvature corrections. Blur draws a curved edge
        # of radius R in by the median of w_n + w_t^2 / (2R), with w_n, w_t the blur's
        # components across and along the edge: to first order the variance of w_t
        # given w_n = 0, det(S) / (n' S n), over 2R. Round a circle that averages
        # sqrt(det S) / (2R), since the mean of 1 / (n' S n) over directions is
        # 1 / sqrt(det S). The isotropic equivalent is therefore det(S)^(1/4), the
        # geometric mean of the principal spreads, not their quadratic mean.
        sigma = float(np.linalg.det(covariance) ** 0.25)
    by_direction = None
    model_covariance = covariance
    if covariance is None:
        # Without a covariance each direction's width is still measured directly; where
        # the directions differ as a shaken camera's do, each edge is searched with its
        # own. A sharp-cornered rectangle under 3 x 1 px turned 30 degrees, whose two
        # edge directions cannot fit a covariance, read its short sides' blur as 3.56 px
        # and was traced with the median 1.95 px: its paper windows lay inside the
        # step's own tail, and the outline read 0.45 mm short between its fitted lines.
        measured = edge_widths_by_direction(
            g, all_points, all_normals, sigma, **with_light,
            **({"start": before["medians"]} if sides and before.get("medians") is not None else {}),
        )
        raw["medians"] = None if measured is None else measured[0]
        if measured is not None and np.nanmax(measured[0]) > DIRECTIONAL_RATIO * np.nanmin(measured[0]):
            by_direction = measured[0]
            # The shadow model blurs its kernel and the step's own tail as the photo
            # does; with one width it read the wider edges' tail as shadow beside them.
            model_covariance = _covariance_from_directions(*measured)
    return sigma, covariance, by_direction, model_covariance, raw


def _accumulate_edge(acc, x0, y0, x1, y1):
    """Add one directed edge's signed area to a row accumulator (a polygon rasteriser's
    accumulation buffer): after a cumulative sum along each row, every cell holds the
    exact signed area of its pixel square [i, i + 1] x [j, j + 1] inside the polygon.
    The same method as the test renderer's exact coverage (tests/synthetic.py)."""
    if y0 == y1:
        return
    sign = 1.0
    if y0 > y1:
        x0, y0, x1, y1, sign = x1, y1, x0, y0, -1.0
    dxdy = (x1 - x0) / (y1 - y0)
    rows = acc.shape[0]
    first, last = max(0, math.floor(y0)), min(rows, math.ceil(y1))
    x = x0 + dxdy * (max(y0, first) - y0)
    for y in range(first, last):
        dy = min(y + 1.0, y1) - max(float(y), y0)
        x_next = x + dxdy * dy
        d = dy * sign
        lo, hi = (x, x_next) if x < x_next else (x_next, x)
        lo_floor = math.floor(lo)
        i0, i1 = lo_floor, math.ceil(hi)
        if i1 <= i0 + 1:
            # Within one cell: the area right of the edge's mean position stays in it.
            mid = 0.5 * (x + x_next) - lo_floor
            acc[y, i0] += d * (1.0 - mid)
            acc[y, i0 + 1] += d * mid
        else:
            inv = 1.0 / (hi - lo)
            f0 = lo - lo_floor
            a0 = 0.5 * inv * (1.0 - f0) ** 2
            f1 = hi - math.ceil(hi) + 1.0
            am = 0.5 * inv * f1 * f1
            acc[y, i0] += d * a0
            if i1 == i0 + 2:
                acc[y, i0 + 1] += d * (1.0 - a0 - am)
            else:
                a1 = inv * (1.5 - f0)
                acc[y, i0 + 1] += d * (a1 - a0)
                acc[y, i0 + 2 : i1 - 1] += d * inv
                a2 = a1 + (i1 - i0 - 3) * inv
                acc[y, i1 - 1] += d * (1.0 - a2 - am)
            acc[y, i1] += d * am
        x = x_next


def _footprint(rings, shape):
    """The part's exact coverage of each pixel, from traced rings [(is_outer, points)]:
    each ring's edges add their signed area to a row accumulator, outer rings turning
    one way and holes the other (_accumulate_edge). Pixel i spans [i, i + 1], as the
    rings' coordinates do. Filling a supersampled grid instead (cv2.fillPoly, 4 x)
    counted boundary sub-pixels as inside and put every edge 0.15 px outward, and the
    fitted shadow read the misplaced step tail as a 1.4-1.9 % shadow."""
    H, W = shape
    acc = np.zeros((H, W + 2), np.float64)
    for is_outer, points in rings:
        if len(points) < 3:
            continue
        p = np.asarray(points, np.float64)
        x, y = p[:, 0], p[:, 1]
        area = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
        if (area > 0) != is_outer:
            p = p[::-1]
        closed = np.vstack([p, p[:1]])
        for (ax, ay), (bx, by) in itertools.pairwise(closed):
            _accumulate_edge(acc, min(max(ax, 0.0), W), ay, min(max(bx, 0.0), W), by)
    # Outer rings and holes turn opposite ways, so their signed areas cancel in holes.
    return np.clip(np.abs(np.cumsum(acc, axis=1)[:, :W]), 0.0, 1.0).astype(np.float32)


def _alone(mask, points, normals, reach):
    """True where the classified mask changes only once along each normal within
    +-reach (px, per point): the edge is the only one a window that long sees."""
    reach = np.broadcast_to(np.asarray(reach, float), (len(points),))
    t = np.arange(-1.0, 1.0 + 1e-9, 1 / 32)[None, :] * reach[:, None]
    xs = np.clip(np.rint(points[:, None, 0] + t * normals[:, None, 0] - 0.5).astype(int), 0, mask.shape[1] - 1)
    ys = np.clip(np.rint(points[:, None, 1] + t * normals[:, None, 1] - 0.5).astype(int), 0, mask.shape[0] - 1)
    inside = mask[ys, xs] > 0
    return np.count_nonzero(inside[:, 1:] != inside[:, :-1], axis=1) <= 1


EDGE_RISE_MM = 2.0  # how far beyond the fit's start the shadow's rise is read
# The part's rise towards its outline (_part_rise) from which the trace reports veiling
# glare. On rendered photos under 1 and 3 px blurs, three seeds each, it read -0.33 to
# +0.07 % of the contrast without glare (with shadows, contact shadows, a 4 mm part or
# sharpening); with 10 % of the light scattered 0.70-1.73 %, and with 3 % 0.24-0.33 %.
GLARE_RISE = 0.005


def _edge_rise(light, mask, points, normals, sigma, ppm):
    """How much the fitted paper light still rises outward where the fit starts, round
    the outline: (L(d + EDGE_RISE_MM) - L(d)) / L(d + EDGE_RISE_MM) at each point, d being
    the fit's start (shadow.TRACED_FIT). Within d the shadow cannot be measured; a light
    still rising at d is a shadow deepening towards the edge, and one that does so all
    round is cast from every side, deepest at the edge. Returns its median, and per
    eighth of the outward direction its median: the largest (edge_rise_top), and the
    smallest over the largest (edge_rise_balance), near 1 for a rise all round and near
    0 for one on some sides only."""
    side = _paper_side_of(mask, points, normals, np.full(len(points), sigma))
    out = normals * side[:, None]
    d = shadow.TRACED_FIT[1] * sigma + 1.5
    far = d + EDGE_RISE_MM * ppm
    near_l = sample_bilinear(light.sharp, points[:, 0] + d * out[:, 0] - 0.5, points[:, 1] + d * out[:, 1] - 0.5)
    far_l = sample_bilinear(light.sharp, points[:, 0] + far * out[:, 0] - 0.5, points[:, 1] + far * out[:, 1] - 0.5)
    rise = (far_l - near_l) / np.maximum(far_l, 1e-9)
    eighth = np.floor(np.arctan2(out[:, 1], out[:, 0]) / (np.pi / 4)).astype(int) % 8
    medians = [float(np.median(rise[eighth == k])) for k in range(8) if np.count_nonzero(eighth == k) >= 5]
    top = max(medians) if medians else 0.0
    return {
        "edge_rise": float(np.median(rise)), "edge_rise_top": top,
        "edge_rise_balance": min(medians) / top if top > 0 else 0.0,
    }


def _part_rise(g, mask, points, normals, sigma, ppm):
    """How much the part's own light rises towards its outline, as a share of the
    paper-part contrast: the median round the outline of (G(-d) - G(-d - EDGE_RISE_MM)) /
    (paper - part), less the blurred step's own tail there, Q(d / sigma); G is the photo's
    light, d the shadow fit's start, and -d lies in the part. Veiling glare, light the
    lens scatters from the bright paper, brightens the part beside it; a shadow on the
    paper does not, and a thick part's brighter wall lies on one side of it only."""
    side = _paper_side_of(mask, points, normals, np.full(len(points), sigma))
    out = normals * side[:, None]
    d = shadow.TRACED_FIT[1] * sigma + 1.5
    far = d + EDGE_RISE_MM * ppm

    def at(distance):
        return sample_bilinear(g, points[:, 0] + distance * out[:, 0] - 0.5, points[:, 1] + distance * out[:, 1] - 0.5)

    part_far, paper = at(-far), at(far + EDGE_RISE_MM * ppm)
    rise = (at(-d) - part_far) / np.maximum(paper - part_far, 1e-9)
    return float(np.median(rise)) - 0.5 * math.erfc(d / sigma / math.sqrt(2))


GLARE_GAIN = 0.25  # share of the part's own light variation the veil must explain
GLARE_RANGE = (0.01, 0.3)  # fractions of the light scattered that are corrected
GLARE_MAX_MM = 40.0  # widest veil spread tried
GLARE_CELLS = 4e5  # most cells the glare fit uses


def _glare_cell(shape, sigma):
    """The glare fit's cell (px): about the blur, which the veil's spread is at least
    twice, and no more than GLARE_CELLS cells over the image."""
    return max(1, round(float(sigma)), math.ceil(math.sqrt(shape[0] * shape[1] / GLARE_CELLS)))


def _glare_veil(cells, f, scale):
    """A function a -> the veiling-glare spread of `cells` (an image averaged over f x f
    px cells) by the kernel a / (2 pi (r^2 + a^2)^1.5), a in px, whose Fourier transform
    is exp(-2 pi a |xi|): the Poisson kernel's. Zero-padded, so light outside the image
    adds none. With `scale` = g, the veil of the image before the glare instead,
    K * I with O = (1 - g) I + g K * I, whose transform is K O / (1 - g + g K)."""
    h, w = cells.shape
    H, W = cv2.getOptimalDFTSize(2 * h), cv2.getOptimalDFTSize(2 * w)
    padded = np.zeros((H, W))
    padded[:h, :w] = cells
    spectrum = np.fft.rfft2(padded)
    rho = np.hypot(np.fft.fftfreq(H)[:, None], np.fft.rfftfreq(W)[None, :])

    def veil(a):
        k = np.exp(-2 * np.pi * (a / f) * rho)
        if scale:
            k = k / (1 - scale + scale * k)
        return np.fft.irfft2(spectrum * k, s=(H, W))[:h, :w]

    return veil


def _glare_fit(g, mask, sigma, ppm):
    """Veiling glare, light the lens scatters, fitted to the part's own light: O = (1 - g)
    I + g K * I with K the Poisson kernel of spread a (`_glare_veil`), I the image before
    the glare and O the photo. Inside the part, beyond 4 sigma + 1 px of its outline where
    the edges' own blur has died away, I is the part's light, taken as a plane, and O is
    the plane plus g K * O to first order: linear in g for each a. a is tried from 2
    sigma, below which the glare cannot be told from the blur, in quarter octaves to
    GLARE_MAX_MM. Returns {"g", "a" (px), "gain"}, gain being the share of the plane's
    residual the veil explains, or None with too little of the part to fit."""
    f = _glare_cell(g.shape, sigma)
    h, w = g.shape[0] // f, g.shape[1] // f
    cells = g[: h * f, : w * f].reshape(h, f, w, f).mean((1, 3)).astype(np.float64)
    inside = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
    depth = inside[: h * f, : w * f].reshape(h, f, w, f).min((1, 3))
    use = depth >= 4 * sigma + 1
    border = int(BORDER_MM * ppm / f) + 1
    use[:border] = use[-border:] = False
    use[:, :border] = use[:, -border:] = False
    yy, xx = np.nonzero(use)
    if len(yy) < 200:
        return None
    obs = cells[yy, xx]
    plane = np.column_stack([np.ones(len(yy)), (xx - w / 2) / w, (yy - h / 2) / h])
    base = float(np.sum((plane @ np.linalg.lstsq(plane, obs, rcond=None)[0] - obs) ** 2))
    if base <= 0:
        return None
    veil = _glare_veil(cells, f, 0.0)

    def trial(a):
        design = np.column_stack([plane, veil(a)[yy, xx]])
        coef, *_ = np.linalg.lstsq(design, obs, rcond=None)
        return float(np.sum((design @ coef - obs) ** 2)), float(coef[3])

    tried = {}
    a = 2 * sigma
    while a <= GLARE_MAX_MM * ppm:  # octaves, then quarter octaves round the best
        tried[a] = trial(a)
        a *= 2
    best = min(tried, key=lambda k: tried[k][0])
    for step in (-0.75, -0.5, -0.25, 0.25, 0.5, 0.75):
        a = best * 2**step
        if 2 * sigma <= a <= GLARE_MAX_MM * ppm:
            tried[a] = trial(a)
    best = min(tried, key=lambda k: tried[k][0])
    near = [next((k for k in tried if abs(k / (best * 2**step) - 1) < 1e-6), None) for step in (-0.25, 0.25)]
    if None not in near:  # a parabola in log a through the three
        r0, r1, r2 = tried[near[0]][0], tried[best][0], tried[near[1]][0]
        if r0 + r2 > 2 * r1:
            a = best * 2 ** (0.125 * (r0 - r2) / (r0 + r2 - 2 * r1))
            tried[a] = trial(a)
            best = min(tried, key=lambda k: tried[k][0])
    rss, fraction = tried[best]
    return {"g": fraction, "a": best, "gain": 1 - rss / base}


def _deglare(g, fit, sigma):
    """The image before the glare `fit` (_glare_fit): I = (O - g K * I) / (1 - g), K * I
    computed exactly from O on the cells and brought back to every pixel."""
    f = _glare_cell(g.shape, sigma)
    H, W = g.shape
    h, w = H // f, W // f
    cells = g[: h * f, : w * f].reshape(h, f, w, f).mean((1, 3)).astype(np.float64)
    before = _glare_veil(cells, f, fit["g"])(fit["a"])
    up = cv2.resize(before.astype(np.float32), (w * f, h * f), interpolation=cv2.INTER_CUBIC)
    up = np.pad(up, ((0, H - h * f), (0, W - w * f)), mode="edge")
    return ((g - fit["g"] * up) / (1 - fit["g"])).astype(g.dtype)


def subpixel_rings(mask, g, ppm, shadow_free_blur=True, remove_glare=True):
    """Outer boundary and holes of the mask at the local half-level, sub-pixel.

    `g` is the lightly smoothed rectified photo in linear light.
    Returns (rings, sigma_px, tiny) where rings is a list of {"outer": bool, "points"}.
    Pass 1 starts from boundary-pixel centres, about half a pixel inside one side, so its
    level windows are asymmetric; pass 2 re-centres each point with windows beyond
    3.5 sigma on both sides of the measured edge blur. Pass 2 also takes the paper side's
    brightness slope into the level (sheet.half_level_search with sigma), smoothed along
    the ring over 20 points, so a soft shadow beside an edge does not push it outward;
    where a shadow model fitted to all the paper round the part is adequate
    (shadow.fit_paper_light), the paper's light follows that model's curvature too.
    Pass 2 runs twice: a provisional search with the line alone, whose rings give the
    shadow model its footprint, and the final one from those rings, since its windows
    are anchored where it starts.
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
    sampled = [(points[::2], ring_normals(points)[1][::2]) for _, points, _, _ in first]
    sigma, covariance, by_direction, model_covariance, raw = _measure_blur(g, outer[::4], normals[::4], sampled)
    # Veiling glare brightens the part beside the bright paper and dims the paper beside
    # it, moving edges into the part; it widens the measured blur too. Where the part's
    # own light shows it (_glare_fit), it is taken out of the image and the blur measured
    # again. Not for a part traced with a thickness, whose walls are brighter than its top.
    glare = _glare_fit(g, mask, sigma, ppm) if remove_glare and sigma > 0 else None
    corrected = (
        glare is not None and glare["gain"] >= GLARE_GAIN and GLARE_RANGE[0] <= glare["g"] <= GLARE_RANGE[1]
    )
    if corrected:
        g = _deglare(g, glare, sigma)
        sigma, covariance, by_direction, model_covariance, raw = _measure_blur(g, outer[::4], normals[::4], sampled)
    # The paper's light round the part, fitted once as a soft shadow (shadow.py): the
    # second pass places each edge against it where it is adequate. A shadow beside the
    # edges also widens their measured blur: its light rises slowly away from them, and a
    # rendered 3 px blur read 3.88 px without a shadow and 4.17 px beside a 25 % one.
    # Where the model is used and finds a shadow worth reporting (NOTICEABLE_DEPTH), the
    # blur is therefore measured again with the model's light removed from every profile
    # (_edge_widths) and the light fitted again with it. A shallower one is mostly the
    # classified mask's own offset from the edges, read as shadow (up to 2.3 % on exactly
    # blurred scenes), and taking it out read the blur up to 0.6 % narrow.
    def spreads(normals):
        if covariance is not None:
            return np.sqrt(np.einsum("ij,jk,ik->i", normals, covariance, normals))
        if by_direction is not None:
            return _spread_by_direction(normals, by_direction)
        return np.full(len(normals), sigma)

    def second_pass(start, normals, light):
        spread = spreads(normals)
        # Which side of each point the paper is on, from the classified mask 3 sigma out.
        search = {
            "half": max(4.0, 3.5 * float(spread.max())), "sigma": spread, "ring_smoothing": 20.0,
            "paper_side": _paper_side_of(mask, start, normals, spread), "paper_light": light,
        }
        moved, keep = half_level_search(g, start, normals, **search)
        return moved, keep, spread

    # The second pass's windows, its step-tail removal and its median-level start are
    # anchored where it starts, so its result depends on that start. Pass 1 starts from
    # the classified mask, cut at the midpoint of saved values, a third of sigma into
    # the dark side, and its 4 px windows recover that only in part: on exactly blurred
    # plates the sides read 0.049 px into the material at a 3.85 px blur. A provisional
    # second pass with the line alone therefore places every ring near its edge, and the
    # final one starts there: 0.0015 px. The provisional rings also give the shadow model
    # its footprint (_footprint, shadow.TRACED_FIT): from the mask's pixels its fitted
    # kernel read the step's own tail as a 0.7 % shadow.
    # Starting again converges only where the profile sees this edge alone. Across a
    # thin hole or at a sharp corner it reaches another, whose step its paper line reads
    # as a slope, and each start reads a different level: a circular-segment hole 10 px
    # across moved 0.3 px into itself on one restart and 0.4 px on the next. There the
    # final pass starts from pass 1, as it did before.
    starts, alone = [], []
    for _, points, _, _ in first:
        _, across = ring_normals(points)
        moved, keep, spread = second_pass(points, across, None)
        # The profile reaches 5 sigma (sheet.half_level_search), and its paper line is
        # fitted out there; another edge's step reaches 2.5 sigma towards it.
        reach = max(4.0, 3.5 * float(spread.max()), 5 * float(spread.max())) + 2.5 * spread
        lone = _alone(mask, points, across, reach)
        alone.append(lone)
        starts.append((np.where((keep & lone)[:, None], moved, points), across))
    # Under a shadow the line puts the provisional rings outward, and so the footprint;
    # the light is then fitted again from the rings it placed (LIGHT_ROUNDS).
    for round_ in range(LIGHT_ROUNDS):
        footprint = _footprint([(is_outer, start) for (is_outer, _, _, _), (start, _) in zip(first, starts)], mask.shape)
        light = shadow.fit_paper_light(g, mask, ppm, sigma, model_covariance, footprint)
        # `shadow_free_blur` False keeps the width with the shadow in: a part traced with a
        # thickness, whose wall model and piecewise thickness map were validated with it
        # (docs/reference-sheet.md, Limits).
        if (
            round_ == 0 and shadow_free_blur and light.info["used"]
            and light.info.get("depth", 0.0) >= shadow.NOTICEABLE_DEPTH and sigma > 0
        ):
            sigma, covariance, by_direction, model_covariance, _ = _measure_blur(
                g, outer[::4], normals[::4], sampled, light, mask, raw
            )
            light = shadow.fit_paper_light(g, mask, ppm, sigma, model_covariance, footprint)
        paper_light = light if light.info["used"] else None
        final = [second_pass(start, across, paper_light) for start, across in starts]
        if paper_light is None:
            break
        if round_ + 1 < LIGHT_ROUNDS:
            starts = [
                (np.where((keep & lone)[:, None], moved, points), across)
                for (_, points, _, _), (moved, keep, _), (_, across), lone in zip(first, final, starts, alone)
            ]
    o = next(i for i, ring in enumerate(first) if ring[0])
    outline, across = final[o][0][final[o][1]], starts[o][1][final[o][1]]
    if paper_light is not None:
        light.info.update(_edge_rise(paper_light, mask, outline, across, sigma, ppm))
    if sigma > 0:
        light.info["part_rise"] = _part_rise(g, mask, outline, across, sigma, ppm)
    if corrected:
        light.info.update(glare=glare["g"], glare_mm=glare["a"] / ppm)
    rings = []
    for (is_outer, _, support, indices), (moved, keep, spread) in zip(first, final):
        if keep.sum() < 8:
            if is_outer:
                raise EdgeError("The part's outline is not clear enough to trace. Improve the contrast.")
            tiny += 1
            continue
        rings.append({
            "outer": is_outer, "points": moved[keep], "support": support,
            "support_indices": indices[keep], "sigma_n": spread[keep], "covariance": covariance,
            "paper_light": light.info,
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


def correct_silhouette(points, normals, nadir, height, thickness, is_outer):
    """correct_thickness for one traced ring, with the wall's vertical edges taken out.

    The photo's silhouette S of a vertical-walled part P is the union of P (bottom
    edge) and its image h(P) (top edge, enlarged about the nadir by D / (D - t)), and
    the part is P = S ∩ h⁻¹(S) wherever each ray from the nadir crosses it in one
    interval (one each side, for a hole). Where support switches between the edges
    the ray is tangent to the outline, and the silhouette runs straight along it from
    the bottom edge's tangent point P to the top edge's h(P): the wall's vertical edge
    seen from the camera, (D / (D - t) - 1) |P - N| long. Its points face neither way,
    and either correction leaves them on that ray, beyond P (bottom) or short of it
    (top), so the corrected outline went out along the ray and back; with noise in the
    normals the two kinds alternated and it crossed itself.

    Each point therefore keeps the candidate that lies on S ∩ h⁻¹(S): its bottom
    candidate (the point) where it lies in h⁻¹(S), its top candidate where it lies in S.
    Where both do the normal decides, as in correct_thickness; the points of the wall's
    vertical edges lie in neither and are dropped. `points` are one ring's silhouette
    points in order, `normals` their material normals. Returns (corrected, top, keep),
    each over all the points; only `keep`'s are on the corrected outline.
    """
    corrected, top = correct_thickness(points, normals, nadir, height, thickness)
    if len(points) < 3:
        return corrected, top, np.ones(len(points), bool)
    import shapely

    ring = Polygon(points)
    if not ring.is_valid:
        ring = ring.buffer(0)
    ratio = height / (height - thickness)
    # The bottom candidate (the point itself) is in h⁻¹(S) where h of it is in S; the
    # top candidate is in S where it is. One on S's boundary, within roundoff, counts as
    # in it: at a tangent point that bounds no wall's edge the other candidate lies
    # exactly there. A wall's edge lies s² / 2r outside the outline s along it, so only
    # its points within about 3 µm of its ends pass (r = 20 mm, coordinates to 200 mm).
    tolerance = 1e-9 * (1.0 + float(np.abs(points).max()))

    def in_material(candidates):
        # A hole's material lies outside its ring.
        inside = shapely.contains_xy(ring, candidates[:, 0], candidates[:, 1])
        ok = inside if is_outer else ~inside
        if (~ok).any():
            ok[~ok] = shapely.distance(ring.boundary, shapely.points(candidates[~ok])) <= tolerance
        return ok

    lowered = nadir + (points - nadir) / ratio
    bottom_ok = in_material(nadir + (points - nadir) * ratio)
    top_ok = in_material(lowered)
    chosen = np.where(bottom_ok != top_ok, top_ok, top)
    corrected = np.where(chosen[:, None], lowered, points)
    return corrected, chosen, bottom_ok | top_ok


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
    sigma = np.broadcast_to(np.asarray(sigma, float), (len(points),))
    keep = band >= sigma
    points, normals, band, sigma = points[keep], normals[keep], band[keep], sigma[keep]
    if len(points) < 30:
        return None
    if len(points) > sample:
        pick = np.linspace(0, len(points) - 1, sample).round().astype(int)
        points, normals, band, sigma = points[pick], normals[pick], band[pick], sigma[pick]
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
    where c2 >= 0 is what is left of v after projecting out u and w. `sigma` may be one
    value or one per point (the edge's own spread across it under a directional blur).
    Returns (candidates, c0, c1, c2), each of shape (points, candidates); the candidate
    offsets are the same multiples of each point's sigma.
    """
    sigma = np.broadcast_to(np.asarray(sigma, float), (len(points),))
    t = np.arange(-(float(band.max()) + 4 * float(sigma.max())), 4 * float(sigma.max()) + step / 2, step)
    sx = points[:, None, 0] + t[None, :] * normals[:, None, 0] - 0.5
    sy = points[:, None, 1] + t[None, :] * normals[:, None, 1] - 0.5
    y = sample_keys(g, sx, sy)
    yy = np.einsum("nt,nt->n", y, y)
    candidates = np.arange(-0.6, 0.8 + 1e-9, 0.02)[None, :] * sigma[:, None]
    c0, c1, c2 = (np.empty(candidates.shape) for _ in range(3))
    for k in range(candidates.shape[1]):
        e, s = candidates[:, k, None], sigma[:, None]
        p1 = normal_cdf((t[None, :] + band[:, None] - e) / s)
        p2 = normal_cdf((t[None, :] - e) / s)
        u, v = 1 - p1, p1 - p2
        gram = ((u * u).sum(1), (u * p2).sum(1), (p2 * p2).sum(1))
        ry, rv = ((u * y).sum(1), (y * p2).sum(1)), ((u * v).sum(1), (v * p2).sum(1))
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
    rows = np.arange(len(points))
    offset = candidates[rows, best] + shift * (candidates[:, 1] - candidates[:, 0])
    moved = points + offset[:, None] * normals
    if with_residuals:
        return moved, walls[rows, best], least
    return moved, walls[rows, best]
