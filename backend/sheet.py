"""Reference-sheet geometry: detection, lens distortion, rectification and camera pose.

A sheet of known size lying in the part's plane supplies three things a single photo
otherwise lacks: millimetre scale, the plane-to-image homography (perspective), and
enough straight edges to estimate radial lens distortion. The homography also fixes the
camera's position relative to the plane, which the edge stage uses to undo the parallax
of a part's top face.

Coordinates: photo pixel i spans [i, i + 1] (its centre is i + 0.5), the repository
convention. Plane coordinates are millimetres on the sheet, x along its top edge and y
down its left edge, origin at its top-left corner as seen in the photo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from . import tone
from .tone import encoded_from_linear

# Paper presets in millimetres (ISO 216 A4 and ANSI Letter), short side first.
SHEETS = {"a4": (210.0, 297.0), "letter": (215.9, 279.4)}
MAX_RECTIFIED_PIXELS = 12_000_000
PPM_RANGE = (4.0, 12.0)  # rectified pixels per millimetre
K1_RANGE = (-0.25, 0.25)
# A phone's main camera is typically about 24-28 mm (35 mm equivalent).
DEFAULT_FOCAL_35MM = 26.0


class SheetError(ValueError):
    """A recoverable reference-sheet failure whose message is suitable for the user."""


@dataclass
class Sheet:
    corners: np.ndarray  # 4x2 photo px (distorted), order: top-left, top-right, bottom-right, bottom-left
    sides: list  # four arrays of edge points (distorted photo px), same order as the corners
    polarity: int  # +1 for a sheet brighter than its surroundings, -1 for darker


def line_tls(points):
    """Total-least-squares line: (centroid, unit direction, rms residual)."""
    centre = points.mean(axis=0)
    _, _, vt = np.linalg.svd(points - centre, full_matrices=False)
    direction = vt[0]
    normal = np.array([-direction[1], direction[0]])
    residual = (points - centre) @ normal
    return centre, direction, float(np.sqrt(np.mean(residual * residual)))


def intersect(c1, d1, c2, d2):
    t = np.linalg.solve(np.array([d1, -d2]).T, np.asarray(c2) - np.asarray(c1))
    return np.asarray(c1) + t[0] * np.asarray(d1)


def sample_bilinear(image, x, y):
    """Bilinear samples of a 2-D float image at continuous index coordinates (x, y),
    in float64, with edge replication.

    cv2.remap would be faster, but it quantises interpolation positions to 1/32 pixel
    (INTER_TAB_SIZE), up to 0.016 px of error, which is larger than the edge
    localisation it serves.
    """
    h, w = image.shape
    x = np.clip(x, 0, w - 1)
    y = np.clip(y, 0, h - 1)
    x0 = np.minimum(np.floor(x).astype(np.int64), w - 2)
    y0 = np.minimum(np.floor(y).astype(np.int64), h - 2)
    fx, fy = x - x0, y - y0
    img = image.astype(np.float64, copy=False)
    top = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    bottom = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return top * (1 - fy) + bottom * fy


def half_level_search(
    gray,
    points,
    normals,
    half,
    step=0.125,
    min_contrast=12.0,
    sigma=None,
    ring_smoothing=0.0,
    paper_side=None,
    paper_light=None,
    paper_extent=None,
):
    """Move each point along its normal to the crossing of its local mid-level.

    `gray` holds linear light (backend.tone). The level is the mean of the median
    intensities at both ends of the sampled profile, so it follows uneven light and
    shadow. For a straight edge blurred by any symmetric point-spread function the
    crossing is unbiased whatever the blur width; that holds in linear light only.
    Profiles whose ends differ by less than `min_contrast` saved grey levels are
    dropped: the limit is stated on the saved scale, where a photo's noise is roughly
    even across tones. Returns the moved points and a keep mask.

    With the edge blur `sigma` given, each end is instead a sloped plateau: a soft
    shadow brightens the paper away from an edge, and the end medians then put the
    level too far out. The profile is sampled out to 5 sigma, the step's own Gaussian
    tail is removed, and a line is fitted to each end beyond 2.5 sigma from the centre,
    A(t) and B(t). A Gaussian-blurred step between two linear plateaus, with slopes a1
    and b1 at its edge e, has the value (A(e) + B(e)) / 2 + (b1 - a1) sigma / sqrt(2 pi)
    there, so the crossing of the profile with that level, as a function of t, is the
    edge itself, flat ends included. Extrapolated lines are
    noisier than medians, while a shadow's slope changes slowly along an edge: with
    `ring_smoothing` (points in order round a closed ring), the correction from the
    median level's crossing to the sloped level's is smoothed along the ring with a
    Gaussian of that many points before it is applied, except for its first harmonic
    round the ring, which is kept where it is significant (_smooth_along_ring): that
    harmonic is how a shadow moves a hole's centre. `paper_side` (+1 or -1 per point:
    the side of t the paper lies on) confines the slope to the paper: a shadow is cast
    there, while the material side can hold a thick part's narrow side wall, whose own
    blurred step would read as a slope; that side keeps its end median.

    `sigma` may be one value or one per point: under a directional blur each edge has
    its own spread across it (edges.edge_covariance).

    `paper_light` (shadow.PaperLight, with `paper_side`) replaces the paper's line by
    the fitted shadow model plus a line: B(t) = L(p + t n) + r0 + r1 t, with r0 and r1
    fitted to the profile minus the model's blurred light over the same window, so a
    model without a shadow leaves the line method as it was. The level is then the
    blurred step's exact value at its edge, A / 2 + int_0^inf B(t +- u) phi_sigma(u) du
    (_modelled_level), for any curvature of B.

    `paper_extent` (px per point, with `sigma` and `paper_side`; inf where none) is how
    far the paper runs along the normal before material starts again: across a narrow
    opening the profile's paper end reaches the opening's far edge, whose blurred step
    reads as a darker paper and moves the edge into the opening. The paper end is then
    read only up to 2.5 sigma short of that edge; where that leaves nothing beyond the
    step's own 2.5 sigma, it is the median at the opening's middle, flat.
    """
    # edges.edge_sigma returns 0 when no profile has the contrast to measure the blur;
    # the median-level search then stands.
    if sigma is not None:
        sigma = np.broadcast_to(np.asarray(sigma, float), (len(points),))
    sloped = sigma is not None and bool(np.all(sigma > 0))
    reach = max(half, 5 * float(sigma.max())) if sloped else half
    t = np.arange(-reach, reach + step / 2, step)
    sx = points[:, None, 0] + t[None, :] * normals[:, None, 0] - 0.5
    sy = points[:, None, 1] + t[None, :] * normals[:, None, 1] - 0.5
    profile = sample_bilinear(gray, sx, sy)
    inner = np.abs(t) <= half + step / 2
    k = max(2, round(0.15 * inner.sum()))
    low = np.median(profile[:, inner][:, :k], axis=1)
    high = np.median(profile[:, inner][:, -k:], axis=1)
    narrow = None
    if sloped and paper_extent is not None and paper_side is not None:
        extent = np.asarray(paper_extent, float)
        paper_high = np.asarray(paper_side) > 0
        # The paper end's samples: within the opening, 2.5 sigma short of its far edge.
        along = np.where(paper_high[:, None], t[None, :], -t[None, :])
        clear = (along >= 2.5 * sigma[:, None]) & (along <= (extent - 2.5 * sigma)[:, None])
        middle = np.abs(along - (extent / 2)[:, None]) <= np.maximum(0.25 * sigma, step)[:, None]
        cut = np.isfinite(extent) & (extent - 2.5 * sigma < reach)
        tight = cut & (clear.sum(axis=1) < 4)
        narrow = np.where(tight[:, None], middle, clear) & cut[:, None]
        # An opening too narrow to hold even its middle keeps the full window.
        cut &= narrow.any(axis=1)
        tight &= cut
        narrow &= cut[:, None]
        paper_end = np.full(len(points), np.nan)
        if cut.any():
            paper_end[cut] = np.nanmedian(np.where(narrow[cut], profile[cut], np.nan), axis=1)
        high = np.where(cut & paper_high, paper_end, high)
        low = np.where(cut & ~paper_high, paper_end, low)
    if not sloped:
        level_t = np.repeat(((low + high) / 2)[:, None], len(t), axis=1)
    else:
        # Beyond 2.5 sigma, with the step's own blurred tail (high - low) Q(|t| / sigma)
        # removed first: it is under 0.6 % of the contrast there, but a line fitted to
        # one side alone would read it as a slope.
        within = np.abs(t)[None, :] <= reach + step / 2
        lo_end = (t[None, :] <= -2.5 * sigma[:, None]) & within
        hi_end = (t[None, :] >= 2.5 * sigma[:, None]) & within
        if narrow is not None:
            cut_high = cut & paper_high
            cut_low = cut & ~paper_high
            hi_end = np.where(cut_high[:, None], narrow, hi_end)
            lo_end = np.where(cut_low[:, None], narrow, lo_end)
        tail = (high - low)[:, None] * _upper_tail(np.abs(t)[None, :] / sigma[:, None])
        flattened = np.where(t[None, :] < 0, profile - tail, profile + tail)

        def line(mask):
            weight = mask.astype(float)
            count = weight.sum(axis=1)
            xm = (weight * t[None, :]).sum(axis=1) / count
            ym = (weight * flattened).sum(axis=1) / count
            dx = (t[None, :] - xm[:, None]) * weight
            slope = (dx * (flattened - ym[:, None])).sum(axis=1) / (dx * dx).sum(axis=1)
            return ym - slope * xm, slope

        a0, a1 = line(lo_end)
        b0, b1 = line(hi_end)
        if narrow is not None and tight.any():
            # The opening's middle alone: too short for a slope, so its median, flat.
            middle_level = np.full(len(points), np.nan)
            middle_level[tight] = np.nanmedian(np.where(narrow[tight], flattened[tight], np.nan), axis=1)
            flat_high, flat_low = tight & paper_high, tight & ~paper_high
            b0, b1 = np.where(flat_high, middle_level, b0), np.where(flat_high, 0.0, b1)
            a0, a1 = np.where(flat_low, middle_level, a0), np.where(flat_low, 0.0, a1)
        if paper_side is not None:
            # The material side keeps a flat level, the median of its end.
            material_low = np.asarray(paper_side) > 0
            a_flat = np.nanmedian(np.where(lo_end, flattened, np.nan), axis=1)
            b_flat = np.nanmedian(np.where(hi_end, flattened, np.nan), axis=1)
            a0, a1 = np.where(material_low, a_flat, a0), np.where(material_low, 0.0, a1)
            b0, b1 = np.where(material_low, b0, b_flat), np.where(material_low, b1, 0.0)
        level_t = (a0 + b0)[:, None] / 2 + ((a1 + b1)[:, None] / 2) * t[None, :]
        level_t += ((b1 - a1) * sigma / math.sqrt(2 * math.pi))[:, None]
        if paper_light is not None and paper_side is not None:
            material_low = np.asarray(paper_side) > 0
            level_t = _modelled_level(
                paper_light, points, normals, t, step, sigma, flattened,
                material_low, np.where(material_low, a0, b0), np.where(material_low[:, None], hi_end, lo_end),
                inner, level_t,
            )
    sign = np.sign(high - low)[:, None]
    keep = np.abs(encoded_from_linear(high) - encoded_from_linear(low)) >= min_contrast
    searched = inner[1:] & inner[:-1]
    centre = len(t) // 2

    def crossing(level):
        """Offset along each normal of the profile's crossing with `level` (per sample)."""
        above = (profile - level) * sign > 0
        offset = np.full(len(points), np.nan)
        for i in np.nonzero(keep)[0]:
            crossings = np.nonzero((above[i, 1:] != above[i, :-1]) & searched)[0]
            if len(crossings) == 0:
                continue
            j = crossings[np.argmin(np.abs(crossings - centre))]
            p0, p1 = profile[i, j] - level[i, j], profile[i, j + 1] - level[i, j + 1]
            offset[i] = t[j] + (p0 / (p0 - p1) if p0 != p1 else 0.5) * step
        return offset

    offset = crossing(np.repeat(((low + high) / 2)[:, None], len(t), axis=1))
    if sloped:
        correction = crossing(level_t) - offset
        if ring_smoothing > 0:
            correction = _smooth_along_ring(correction, ring_smoothing, points)
        offset = offset + correction
    keep &= np.isfinite(offset)
    moved = points.astype(np.float64).copy()
    moved[keep] += offset[keep, None] * normals[keep]
    return moved, keep


def _modelled_level(light, points, normals, t, step, sigma, flattened, paper_high, material, window, inner, level_t):
    """The level with the paper's light from the shadow model (shadow.PaperLight).

    B(t) = L(p + t n) + r0 + r1 t on the paper side, with L the model's light before the
    blur and r0 + r1 t the line through the profile minus the model's blurred light over
    the paper window. The blurred step from the material's flat level A to B has, at its
    edge, A / 2 + int_0^inf B(t + u) phi(u) du (paper on the high side; t - u on the low):
    that is the level, computed by Simpson's rule on u = sigma z, z in [0, 5]. Only the
    searched samples (`inner`) are replaced."""
    m = math.ceil((5 * float(sigma.max()) + 2 * step) / step)
    ext = t[0] + (np.arange(len(t) + 2 * m) - m) * step
    ex = points[:, None, 0] + ext[None, :] * normals[:, None, 0] - 0.5
    ey = points[:, None, 1] + ext[None, :] * normals[:, None, 1] - 0.5
    sharp = sample_bilinear(light.sharp, ex, ey)
    blurred = sample_bilinear(light.blurred, ex[:, m : m + len(t)], ey[:, m : m + len(t)])
    residual = flattened - blurred
    weight = window.astype(float)
    count = weight.sum(axis=1)
    tm = (weight * t[None, :]).sum(axis=1) / count
    rm = (weight * residual).sum(axis=1) / count
    dx = (t[None, :] - tm[:, None]) * weight
    r1 = (dx * (residual - rm[:, None])).sum(axis=1) / (dx * dx).sum(axis=1)
    r0 = rm - r1 * tm
    z = np.linspace(0.0, 5.0, 21)
    simpson = np.full(21, 2.0)
    simpson[1::2] = 4.0
    simpson[[0, -1]] = 1.0
    wz = simpson * (z[1] - z[0]) / 3 * np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    columns = np.flatnonzero(inner)
    direction = np.where(paper_high, 1.0, -1.0)
    rows = np.arange(len(points))[:, None]
    integral = np.zeros((len(points), len(columns)))
    for zk, wk in zip(z, wz):
        position = m + columns[None, :] + (direction * sigma * zk / step)[:, None]
        i0 = np.clip(np.floor(position).astype(int), 0, sharp.shape[1] - 2)
        frac = position - i0
        integral += wk * (sharp[rows, i0] * (1 - frac) + sharp[rows, i0 + 1] * frac)
    out = level_t.copy()
    out[:, columns] = (
        material[:, None] / 2
        + integral
        + (r0[:, None] + r1[:, None] * t[None, columns]) / 2
        + (direction * r1 * sigma / math.sqrt(2 * math.pi))[:, None]
    )
    return out


def _upper_tail(z):
    """Upper standard normal tail Q(z), vectorised (Abramowitz & Stegun 7.1.26, absolute
    error below 1e-7)."""
    x = np.asarray(z, dtype=np.float64) / math.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * np.abs(x))
    erfc = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))) * np.exp(-x * x)
    return np.where(x >= 0, 0.5 * erfc, 1.0 - 0.5 * erfc)


RING_SECTORS = 8  # contiguous sectors of a ring for the jackknife in _smooth_along_ring
SIGNIFICANT_DIPOLE = 3.0  # standard errors


def _smooth_along_ring(values, scale, points=None):
    """Gaussian smoothing (standard deviation `scale` samples) of values in order round a
    closed ring, over the finite ones; non-finite values stay non-finite. The values'
    first harmonic round the ring is kept, shrunk only by its uncertainty.

    A Gaussian of s samples keeps a ring of N samples' first harmonic by exp(-(2 pi s /
    N)^2 / 2), and a ring of fewer than 6 s samples was given its mean alone. For the
    slope correction of a hole that harmonic is the centre's shift: on a 6 mm hole of 99
    samples a soft shadow's whole effect on its centre was dropped, and a blur of 3 px
    with a 25 % shadow put the holes 0.027 mm out of position. The harmonic is therefore
    fitted (by least squares in arc length round `points`, the ring's positions, or in
    sample order without them) and kept with the gain max(0, 1 - k^2 V / |d|^2), where d
    is its amplitude, V the variance of that estimate by a jackknife over RING_SECTORS
    contiguous sectors (neighbouring profiles share pixels, so their noise is
    correlated), and k = SIGNIFICANT_DIPOLE: a harmonic within k standard errors of zero
    is noise and is dropped, as before. Only the rest is smoothed.
    """
    ok = np.isfinite(values)
    n = len(values)
    if ok.sum() >= 4 * RING_SECTORS:
        if points is None:
            theta = 2 * math.pi * np.arange(n) / n
        else:
            step = np.linalg.norm(np.diff(points, axis=0, append=points[:1]), axis=1)
            theta = 2 * math.pi * np.concatenate([[0.0], np.cumsum(step[:-1])]) / step.sum()
        design = np.column_stack([np.ones(n), np.cos(theta), np.sin(theta)])
        coef = np.linalg.lstsq(design[ok], values[ok], rcond=None)[0]
        sector = np.minimum((theta * RING_SECTORS / (2 * math.pi)).astype(int), RING_SECTORS - 1)
        left_out = np.array([
            np.linalg.lstsq(design[ok & (sector != b)], values[ok & (sector != b)], rcond=None)[0][1:]
            for b in range(RING_SECTORS)
        ])
        variance = (RING_SECTORS - 1) / RING_SECTORS * float(((left_out - left_out.mean(0)) ** 2).sum())
        amplitude2 = float((coef[1:] ** 2).sum())
        gain = max(0.0, 1 - SIGNIFICANT_DIPOLE**2 * variance / amplitude2) if amplitude2 > 0 else 0.0
        if gain > 0:
            dipole = gain * (design[:, 1:] @ coef[1:])
            out = _gaussian_along_ring(values - dipole, scale) + dipole
            out[~ok] = np.nan
            return out
    return _gaussian_along_ring(values, scale)


def _gaussian_along_ring(values, scale):
    """Gaussian smoothing (standard deviation `scale` samples) of values in order round a
    closed ring, over the finite ones; a ring of fewer than 6 `scale` finite values is
    given their mean. Non-finite values stay non-finite."""
    ok = np.isfinite(values)
    v = values[ok]
    if len(v) < 6 * scale:
        out = values.copy()
        out[ok] = v.mean() if len(v) else v
        return out
    radius = int(3 * scale)
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / scale) ** 2)
    kernel /= kernel.sum()
    padded = np.concatenate([v[-radius:], v, v[:radius]])
    out = values.copy()
    out[ok] = np.convolve(padded, kernel, mode="valid")
    return out


def _quad(gray_small, polarity):
    work = gray_small if polarity > 0 else 255 - gray_small
    _, mask = cv2.threshold(work, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < 0.05 * gray_small.size or area > 0.97 * gray_small.size:
        return None
    hull = cv2.convexHull(contour)
    quad = cv2.approxPolyDP(hull, 0.02 * cv2.arcLength(hull, True), True).reshape(-1, 2)
    if len(quad) != 4 or not cv2.isContourConvex(quad.reshape(-1, 1, 2)):
        return None
    # The sheet must not run off the photo: a clipped edge would be a false side.
    h, w = gray_small.shape
    if quad[:, 0].min() <= 2 or quad[:, 1].min() <= 2 or quad[:, 0].max() >= w - 3 or quad[:, 1].max() >= h - 3:
        return None
    # A sheet carries a part: something contrasting must lie well inside it. Without this
    # a plain dark rectangle on a light background would pass as a dark sheet.
    inside = np.zeros_like(mask)
    cv2.fillConvexPoly(inside, quad.astype(np.int32), 255)
    inside = cv2.erode(inside, np.ones((9, 9), np.uint8))
    region = inside > 0
    if region.sum() < 100 or np.mean(mask[region] == 0) < 0.003:
        return None
    return quad.astype(np.float64)


def _edge_mix(rgb, quad, small_shape):
    """Channel weights (tone.choose_mix) for the sheet's edges, from the light just
    inside and just outside each side. `quad` is in the coordinates of the reduced
    image of `small_shape`."""
    h, w = small_shape
    small = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
    reach = max(6.0, 0.01 * max(h, w))
    inside, outside = [], []
    for i in range(4):
        a, b = quad[i], quad[(i + 1) % 4]
        length = float(np.linalg.norm(b - a))
        if length < 4 * reach:
            return tone.LUMINANCE
        points = a[None] + np.linspace(0.06, 0.94, max(20, int(length / 4)))[:, None] * (b - a)[None]
        normal = np.array([-(b - a)[1], (b - a)[0]]) / length
        inside.append(tone.light_at(small, points + reach * normal))
        outside.append(tone.light_at(small, points - reach * normal))
    return tone.choose_mix(np.vstack(inside), np.vstack(outside))


def find_sheet(gray, rgb=None):
    """Locate the reference sheet and sub-pixel points along its four edges.

    `gray` is the full-resolution photo as saved, uint8; the sheet is found on it.
    `rgb` is the same photo in colour; the sub-pixel edge points are measured on a
    linear-light mix of its channels (luminance, unless the sheet and the surface
    under it differ mainly in colour). Without it, `gray` is taken as linear light.
    Tries a sheet brighter than its surroundings first, then a darker one.
    """
    h, w = gray.shape
    scale = 1000 / max(h, w)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (5, 5), 0)
    for polarity in (1, -1):
        quad = _quad(small, polarity)
        if quad is not None:
            break
    else:
        raise SheetError(
            "No reference sheet was found. Show the whole sheet, with all four corners and a "
            "contrasting surface around it, or choose No reference."
        )
    measured = gray if rgb is None else tone.linear_mix(rgb, _edge_mix(rgb, quad, small.shape))
    quad /= scale
    sums, diffs = quad.sum(1), np.diff(quad, axis=1).ravel()
    quad = np.array([quad[np.argmin(sums)], quad[np.argmin(diffs)], quad[np.argmax(sums)], quad[np.argmax(diffs)]])
    gray_f = cv2.GaussianBlur(measured.astype(np.float32), (0, 0), 1.0)
    sides = []
    for i in range(4):
        a, b = quad[i], quad[(i + 1) % 4]
        length = float(np.linalg.norm(b - a))
        ts = np.linspace(0.06, 0.94, max(40, int(length / 3)))  # clear of the corners
        points = a[None] + ts[:, None] * (b - a)[None]
        d = (b - a) / length
        normals = np.tile([-d[1], d[0]], (len(points), 1))
        moved, keep = half_level_search(gray_f, points, normals, half=14.0, step=0.25)
        # Distortion bows a real edge off the corner-to-corner chord, which can put one
        # level window on the transition. Re-centre on the first crossings and search again.
        moved, keep2 = half_level_search(gray_f, moved[keep], normals[keep], half=10.0, step=0.25)
        side = moved[keep2]
        if len(side) < 20:
            raise SheetError(
                "The reference sheet's edges are not clear enough. Use a sheet that contrasts with the surface under it."
            )
        sides.append(side)
    return Sheet(corners=quad, sides=sides, polarity=polarity)


def undistort_radius(rd, k1, iterations=64):
    """Invert the radial cubic on the increasing branch containing the camera centre.

    With negative k1, its maximum distorted radius is 2/(3 sqrt(-3 k1)); a
    sensor radius beyond it has no central-camera inverse. Safeguarded Newton
    steps stay in the physical branch, with bisection for an inadmissible step.
    Near the turning point, input rounding and image noise are still amplified.
    """
    rd = np.asarray(rd, dtype=np.float64)
    if not math.isfinite(k1) or not np.isfinite(rd).all() or (rd < 0).any():
        raise SheetError("The radial lens model needs finite, nonnegative image radii.")
    if k1 == 0:
        return rd.copy()
    if k1 < 0:
        scale = math.sqrt(-3 * k1)
        if np.any(rd > 2 / (3 * scale)):
            raise SheetError("The radial lens model has no central-camera inverse at this image radius.")
        upper = np.full_like(rd, 1 / scale)
    else:
        upper = rd.copy()
    lower = np.zeros_like(rd)
    ru = rd.copy()
    for _ in range(iterations):
        residual = ru * (1 + k1 * ru * ru) - rd
        lower = np.where(residual < 0, ru, lower)
        upper = np.where(residual > 0, ru, upper)
        derivative = 1 + 3 * k1 * ru * ru
        step = np.divide(residual, derivative, out=np.full_like(ru, np.nan), where=derivative > 0)
        proposed = ru - step
        admissible = np.isfinite(proposed) & ((residual == 0) | ((proposed > lower) & (proposed < upper)))
        moved = np.where(admissible, proposed, lower + (upper - lower) / 2)
        converged = np.abs(moved - ru) <= 4 * np.finfo(float).eps * np.maximum(1, np.abs(ru))
        ru = moved
        if converged.all():
            return ru
    raise SheetError("The radial lens model could not be inverted at numerical precision.")


def undistort_points(points, k1, size):
    """Invert x_d = x_u (1 + k1 r_u^2), r normalised by the image half-diagonal."""
    w, h = size
    cx, cy, s = w / 2, h / 2, math.hypot(w, h) / 2
    xd, yd = (points[:, 0] - cx) / s, (points[:, 1] - cy) / s
    rd = np.hypot(xd, yd)
    ru = undistort_radius(rd, k1)
    factor = np.divide(ru, rd, out=np.ones_like(rd), where=rd > 0)
    return np.column_stack([cx + xd * factor * s, cy + yd * factor * s])


def straightness(sides, k1, size):
    total, count = 0.0, 0
    for side in sides:
        _, _, rms = line_tls(undistort_points(side, k1, size))
        total += rms * rms * len(side)
        count += len(side)
    return math.sqrt(total / count)


def estimate_k1(sheet, size):
    """Golden-section search for the radial coefficient that straightens the sheet edges.

    Returns (k1, rms before, rms after) with residuals in photo pixels. Four edges
    near the image centre constrain k1 weakly; the residual improvement shows how much
    the correction mattered.
    """
    g = (math.sqrt(5) - 1) / 2
    a, b = K1_RANGE
    # A trial lens must invert every reference observation on its central branch.
    # Include detected corners as well as the measured interior edge samples.
    observed = np.vstack([sheet.corners, *sheet.sides])
    radius = np.max(np.linalg.norm((observed - np.array(size) / 2) / (math.hypot(*size) / 2), axis=1))
    if radius > 0:
        a = max(a, math.nextafter(-4 / (27 * radius * radius), math.inf))
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = straightness(sheet.sides, c, size), straightness(sheet.sides, d, size)
    for _ in range(60):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = straightness(sheet.sides, c, size)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = straightness(sheet.sides, d, size)
    k1 = (a + b) / 2
    before = straightness(sheet.sides, 0.0, size)
    after = straightness(sheet.sides, k1, size)
    # Keep a correction only when it clearly straightens the edges.
    if after > 0.8 * before or abs(k1) < 1e-4:
        return 0.0, before, before
    return k1, before, after


def homography(sheet, k1, size, sheet_mm):
    """Plane millimetres -> undistorted photo pixels, from the four fitted sheet edges.

    The longer pair of opposite sides is matched to the sheet's long dimension.
    """
    lines = []
    for side in sheet.sides:
        centre, direction, _ = line_tls(undistort_points(side, k1, size))
        lines.append((centre, direction))
    corners = np.array([intersect(*lines[i - 1], *lines[i]) for i in range(4)])
    horizontal = np.linalg.norm(corners[1] - corners[0]) + np.linalg.norm(corners[2] - corners[3])
    vertical = np.linalg.norm(corners[3] - corners[0]) + np.linalg.norm(corners[2] - corners[1])
    short, long = sorted(sheet_mm)
    width, height = (short, long) if vertical > horizontal else (long, short)
    plane = np.array([[0, 0], [width, 0], [width, height], [0, height]], np.float64)
    matrix, _ = cv2.findHomography(plane, corners, 0)
    if matrix is None or not np.all(np.isfinite(matrix)):
        raise SheetError("The reference sheet's corners could not be resolved. Retake the photo.")
    return matrix / matrix[2, 2], (width, height), corners


def project(matrix, points):
    p = np.c_[points, np.ones(len(points))] @ matrix.T
    return p[:, :2] / p[:, 2:]


def native_ppm(matrix, plane_size):
    """Photo pixels per millimetre at the sheet centre (geometric mean of both axes)."""
    w, h = plane_size
    c = np.array([[w / 2, h / 2], [w / 2 + 1, h / 2], [w / 2, h / 2 + 1]])
    p = project(matrix, c)
    return math.sqrt(np.linalg.norm(p[1] - p[0]) * np.linalg.norm(p[2] - p[0]))


def choose_ppm(matrix, plane_size):
    native = native_ppm(matrix, plane_size)
    ppm = min(max(1.25 * native, PPM_RANGE[0]), PPM_RANGE[1])
    w, h = plane_size
    return min(ppm, math.sqrt(MAX_RECTIFIED_PIXELS / (w * h))), native


def rectify(rgb, matrix, k1, plane_size, ppm):
    """One resampling of the photo onto a millimetre grid, through perspective and lens,
    for display (cv2.remap: fast, but positions quantised to 1/32 pixel; measurements
    use rectify_gray).

    Output pixel (i, j) is centred on plane ((i + 0.5) / ppm, (j + 0.5) / ppm).
    """
    w, h = plane_size
    cols, rows = round(w * ppm), round(h * ppm)
    gx, gy = np.meshgrid((np.arange(cols) + 0.5) / ppm, (np.arange(rows) + 0.5) / ppm)
    ph, pw = rgb.shape[:2]
    u, v = plane_to_photo(matrix, k1, (pw, ph), gx, gy)
    map_x = (u - 0.5).astype(np.float32)
    map_y = (v - 0.5).astype(np.float32)
    return cv2.remap(rgb, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _keys(t, a=-0.5):
    """Keys cubic-convolution kernel (a = -0.5): interpolates, and reproduces
    quadratics exactly."""
    t = np.abs(t)
    near = t <= 1
    far = (t > 1) & (t < 2)
    out = np.zeros_like(t)
    out[near] = ((a + 2) * t[near] - (a + 3)) * t[near] ** 2 + 1
    out[far] = ((a * t[far] - 5 * a) * t[far] + 8 * a) * t[far] - 4 * a
    return out


def plane_to_photo(matrix, k1, size, gx, gy):
    """Distorted photo coordinates (continuous, pixel i spans [i, i + 1]) of plane points."""
    den = matrix[2, 0] * gx + matrix[2, 1] * gy + matrix[2, 2]
    iu = (matrix[0, 0] * gx + matrix[0, 1] * gy + matrix[0, 2]) / den
    iv = (matrix[1, 0] * gx + matrix[1, 1] * gy + matrix[1, 2]) / den
    pw, ph = size
    cx, cy, s = pw / 2, ph / 2, math.hypot(pw, ph) / 2
    x, y = (iu - cx) / s, (iv - cy) / s
    f = 1 + k1 * (x * x + y * y)
    return cx + x * f * s, cy + y * f * s


def rectify_gray(gray, matrix, k1, plane_size, ppm, block_rows=192):
    """The measurement image: an exact float64 cubic resampling of a grey photo onto the
    millimetre grid (same geometry as rectify). Unlike cv2.remap, which quantises
    positions to 1/32 pixel and moved content by up to 0.09 px in tests, this has no
    positional quantisation: a linear intensity ramp is reproduced exactly."""
    h, w = gray.shape
    width, height = plane_size
    cols, rows = round(width * ppm), round(height * ppm)
    image = gray.astype(np.float64)
    out = np.empty((rows, cols), np.float32)
    xs = (np.arange(cols) + 0.5) / ppm
    for top in range(0, rows, block_rows):
        ys = (np.arange(top, min(rows, top + block_rows)) + 0.5) / ppm
        gx, gy = np.meshgrid(xs, ys)
        u, v = plane_to_photo(matrix, k1, (w, h), gx, gy)
        out[top : top + len(ys)] = sample_keys(image, u - 0.5, v - 0.5)  # index coordinates
    return out


def sample_keys(image, x, y):
    """Keys cubic samples of a 2-D image at continuous index coordinates (x, y), in
    float64, with edge replication. Its error on smooth content is third order in the
    pixel pitch, where bilinear sampling's is second order: on an edge blurred to
    sigma = 1.7 px with 200 grey levels of contrast, bilinear values are off by up to
    2.1 levels at the shoulders, this by 0.33."""
    h, w = image.shape
    img = image.astype(np.float64, copy=False)
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    acc = np.zeros(np.shape(x))
    for j in range(-1, 3):
        wy = _keys(fy - j)
        yy = np.clip(y0 + j, 0, h - 1)
        row = np.zeros(np.shape(x))
        for i in range(-1, 3):
            row += _keys(fx - i) * img[yy, np.clip(x0 + i, 0, w - 1)]
        acc += wy * row
    return acc


def orthogonal_focal(matrix, size):
    """Focal length from the orthogonality of the rotation's first two columns alone.

    Scaling the plane's x or y axis (a wrong sheet aspect ratio) scales a column of the
    homography and cannot change whether the two columns are orthogonal, so this
    estimate does not depend on the stated sheet size. Returns None when the view gives
    no usable constraint (perspective about only one axis, or a frontal view).
    """
    w, h = size
    shifted = np.array([[1, 0, -w / 2], [0, 1, -h / 2], [0, 0, 1.0]]) @ matrix
    (h11, h12, _), (h21, h22, _), (h31, h32, _) = shifted
    a, b = h11 * h12 + h21 * h22, h31 * h32
    if abs(a) < 1e-12 or -b / a <= 0:
        return None
    focal = 1 / math.sqrt(-b / a)
    diagonal = math.hypot(w, h)
    return focal if 0.3 * diagonal <= focal <= 5 * diagonal else None


def aspect_ratio_check(matrix, size, focal):
    """Measured / stated sheet aspect ratio (width / height) implied by the homography.

    With metric plane coordinates the rotation's first two columns have equal norms,
    so their ratio in K^-1 H is (true aspect) / (stated aspect). In a frontal view the
    ratio hardly depends on the focal length, so the check holds for any view.
    """
    w, h = size
    shifted = np.array([[1, 0, -w / 2], [0, 1, -h / 2], [0, 0, 1.0]]) @ matrix
    m = np.diag([1 / focal, 1 / focal, 1.0]) @ shifted
    return float(np.linalg.norm(m[:, 0]) / np.linalg.norm(m[:, 1]))


def camera_pose(matrix, size, exif_focal_35mm=None, focal_px=None):
    """Focal length, camera centre and height above the plane from the homography.

    Assumes square pixels, zero skew and the principal point at the image centre. The
    focal length follows from the two orthonormality constraints on the rotation's
    first columns. Each constraint gives its own estimate; when they disagree (a nearly
    frontal view, or a cropped photo) the EXIF 35 mm-equivalent focal length is used,
    else a typical phone value. `focal_px` imposes a focal length found otherwise
    (edges.roundness_focal). Returns a dict; `focal_source` says which was used.
    """
    w, h = size
    diagonal = math.hypot(w, h)
    shifted = np.array([[1, 0, -w / 2], [0, 1, -h / 2], [0, 0, 1.0]]) @ matrix
    (h11, h12, _), (h21, h22, _), (h31, h32, _) = shifted
    a1, b1 = h11 * h12 + h21 * h22, h31 * h32
    a2, b2 = h11**2 + h21**2 - h12**2 - h22**2, h31**2 - h32**2
    estimates = []
    for a, b in ((a1, b1), (a2, b2)):
        if abs(a) > 1e-12 and -b / a > 0:
            estimates.append(1 / math.sqrt(-b / a))
    focal, source = (float(focal_px), "given") if focal_px else (None, None)
    if focal is None and len(estimates) == 2:
        u = -(a1 * b1 + a2 * b2) / (a1 * a1 + a2 * a2)
        if u > 0:
            candidate = 1 / math.sqrt(u)
            spread = abs(estimates[0] - estimates[1]) / candidate
            if spread < 0.15 and 0.3 * diagonal <= candidate <= 5 * diagonal:
                focal, source = candidate, "sheet"
    if focal is None and exif_focal_35mm and 5 <= exif_focal_35mm <= 600:
        focal, source = exif_focal_35mm / math.hypot(36, 24) * diagonal, "exif"
    if focal is None:
        focal, source = DEFAULT_FOCAL_35MM / math.hypot(36, 24) * diagonal, "assumed"
    m = np.diag([1 / focal, 1 / focal, 1.0]) @ shifted
    lam = 2 / (np.linalg.norm(m[:, 0]) + np.linalg.norm(m[:, 1]))
    r1, r2, t = lam * m[:, 0], lam * m[:, 1], lam * m[:, 2]
    if t[2] < 0:
        r1, r2, t = -r1, -r2, -t
    u_, _, vt = np.linalg.svd(np.column_stack([r1, r2, np.cross(r1, r2)]))
    rotation = u_ @ vt
    centre = -rotation.T @ t
    return {
        "focal_px": float(focal),
        "focal_source": source,
        "centre_mm": centre,
        "nadir_mm": centre[:2].copy(),
        "height_mm": float(abs(centre[2])),
    }
