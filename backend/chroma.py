"""Edges in a photo whose colour is stored at half resolution.

A JPEG or HEIC keeps its luma Y' (for a JPEG 0.299 R' + 0.587 G' + 0.114 B' of the saved
values; for an HEIC by its colour matrix, luma_weights) at full
resolution, and its colour, Cb and Cr, usually at half resolution in each direction
(4:2:0). The linear light the trace measures mixes the two through the sRGB curve, and
at a coloured part's edge the half-resolution colour moves it: on exactly blurred plates
with noise a green part on a grey card read its sides 0.044-0.066 px into the part, an
orange one up to 0.018 px, and a grey one within 0.003 px (docs/reference-sheet.md, §3,
**JPEG's colour**).

Near an edge between the part's colour A and the paper's B, each pixel's linear colour
is a blend (1 - a) A + a B, and its full-resolution luma alone fixes a. `rebuild` puts
the measured light back together from that, within a band round the classified part:
the part's light is read beyond the band, and the paper's is the fitted shadow model's,
so a soft shadow beside the part is followed. The light within about two blur widths of
a shadowed edge cannot be measured from one photo, and there the paper's light would be
the model's guess; the caller therefore rebuilds only where the fitted shadow is shallow.
"""

from __future__ import annotations

import cv2
import numpy as np

from .tone import encoded_from_linear

LUMA_601 = np.array([0.299, 0.587, 0.114])  # JPEG's (JFIF's) luma of saved R'G'B'
# Luma's red and blue weights (Kr, Kb) by an HEIF's nclx matrix_coefficients (ITU-T
# H.273): 1 BT.709, 4 FCC, 5 and 6 BT.601, 7 SMPTE 240M, 9 BT.2020 non-constant
# luminance. libheif takes 2 (unspecified) as BT.601: a file so marked decodes exactly
# as one marked 6. The others (identity, YCgCo, constant-luminance and ICtCp) have no
# such luma, and nothing is rebuilt for them.
MATRIX_LUMA = {1: (0.2126, 0.0722), 2: (0.299, 0.114), 4: (0.30, 0.11), 5: (0.299, 0.114), 6: (0.299, 0.114), 7: (0.212, 0.087), 9: (0.2627, 0.0593)}
BAND_SIGMAS = 5.5  # rebuilt within this many blur widths, plus 2 px, of the part's boundary
FIELD_PX = 6.0  # smoothing of the part's light, read beyond the band
MIN_LUMA_CONTRAST = 20.0  # saved levels of luma between the two colours, to solve the blend
MIN_HUE = 0.1  # chromaticities closer than this are one hue: nothing to rebuild
BISECTIONS = 6
NEWTON_STEPS = 4


def luma_weights(matrix_coefficients):
    """The luma weights (Kr, Kg, Kb) of an nclx matrix_coefficients, or None."""
    pair = MATRIX_LUMA.get(matrix_coefficients)
    return None if pair is None else (pair[0], 1.0 - pair[0] - pair[1], pair[1])


def luma(rgb, weights=LUMA_601):
    """The photo's luma Y' on the saved scale, float64. The decoder's R'G'B' are its
    Y'CbCr through the inverse of the matrix whose weights these are, so with the same
    weights this is its stored luma, at full resolution, whatever its range."""
    return np.asarray(rgb, np.float64) @ np.asarray(weights, np.float64)


def chromaticity(linear_rgb, weights):
    """A linear colour scaled so that its mix with `weights` is 1."""
    colour = np.asarray(linear_rgb, np.float64)
    return colour / float(colour @ np.asarray(weights, np.float64))


def different_hues(part, paper):
    """Whether two chromaticities differ enough for the colour's resolution to matter."""
    return bool(np.max(np.abs(np.asarray(part) - np.asarray(paper))) >= MIN_HUE)


def _luma_and_slope(blend, part, paper, weights=LUMA_601):
    """The luma of (1 - a) part + a paper and its derivative with respect to a."""
    raw = (1 - blend)[:, None] * part + blend[:, None] * paper
    colour = np.clip(raw, 0, None)
    v = colour / 255
    # The sRGB curve's slope, on the 0-255 scale both ways; nothing where light clips.
    slope = np.where(v <= 0.0031308, 12.92, (1.055 / 2.4) * np.maximum(v, 0.0031308) ** (1 / 2.4 - 1))
    slope = np.where(raw > 0, slope, 0.0)
    weights = np.asarray(weights, np.float64)
    return encoded_from_linear(colour) @ weights, (slope * (paper - part)) @ weights


def blend_from_luma(y, part, paper, lo=-0.5, hi=1.5, weights=LUMA_601):
    """The blend a of (1 - a) part + a paper (linear RGB, one row per pixel) whose luma
    is `y`. The luma is monotone in a when the two colours' lumas differ, and a may
    leave [0, 1] by noise, so the bracket reaches beyond it. BISECTIONS halvings, then
    Newton steps kept within the bracket: the result is within 1e-7 of the root."""
    part, paper = np.atleast_2d(part), np.atleast_2d(paper)
    rising = _luma_and_slope(np.ones(len(y)), part, paper, weights)[0] > _luma_and_slope(np.zeros(len(y)), part, paper, weights)[0]
    low, high = np.full(len(y), lo), np.full(len(y), hi)
    for _ in range(BISECTIONS):
        mid = (low + high) / 2
        above = (_luma_and_slope(mid, part, paper, weights)[0] > y) == rising
        high, low = np.where(above, mid, high), np.where(above, low, mid)
    blend = (low + high) / 2
    for _ in range(NEWTON_STEPS):
        value, slope = _luma_and_slope(blend, part, paper, weights)
        step = np.where(np.abs(slope) > 1e-9, (value - y) / np.where(np.abs(slope) > 1e-9, slope, 1.0), 0.0)
        blend = np.clip(blend - step, low, high)
    return blend


def _extended(values, support):
    """`values` read where `support` (0 or 1) is set, smoothed over FIELD_PX and carried
    out from there: a band's paper side lies up to twice its width from the part's
    interior, where a FIELD_PX Gaussian's weight vanishes. Each pixel takes the finest
    of FIELD_PX, 8 FIELD_PX and the median whose weight there is not negligible."""
    out = np.full(values.shape, float(np.median(values[support > 0])))
    h, w = values.shape
    for scale, shrink in ((8 * FIELD_PX, 8), (FIELD_PX, 1)):
        # The coarse field on a grid 8 times coarser: it varies over 8 FIELD_PX.
        small = (max(1, w // shrink), max(1, h // shrink))
        sup = cv2.resize(support, small, interpolation=cv2.INTER_AREA) if shrink > 1 else support
        val = cv2.resize(values * support, small, interpolation=cv2.INTER_AREA) if shrink > 1 else values * support
        weight = cv2.GaussianBlur(sup, (0, 0), scale / shrink)
        level = cv2.GaussianBlur(val, (0, 0), scale / shrink) / np.maximum(weight, 1e-12)
        if shrink > 1:
            weight = cv2.resize(weight, (w, h), interpolation=cv2.INTER_LINEAR)
            level = cv2.resize(level, (w, h), interpolation=cv2.INTER_LINEAR)
        out = np.where(weight > 1e-3, level, out)
    return out


def rebuild(g, y, mask, sigma, part, paper, weights, paper_level, luma_weights=LUMA_601):
    """The measured light `g` (the rectified linear mix, before its smoothing) rebuilt
    from the rectified luma `y` within BAND_SIGMAS sigma + 2 px of the classified part
    `mask`, or None when the two colours' lumas are too close to solve the blend.

    `part` and `paper` are the two sides' chromaticities (chromaticity), and
    `paper_level` the paper's light on the grid (the shadow model's, shadow.PaperLight's
    `blurred`), and `luma_weights` the photo's luma (luma_weights; JPEG's by default). The part's light is read from `g` beyond the band and smoothed over
    FIELD_PX (_extended). Outside the band `g` is kept: there the colour's resolution
    does not matter."""
    inside = mask > 0
    d_in = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    d_out = cv2.distanceTransform((~inside).astype(np.uint8), cv2.DIST_L2, 5)
    band_px = BAND_SIGMAS * float(sigma) + 2.0
    far = (inside & (d_in > band_px)).astype(np.float64)
    if not far.any():
        return None
    part_level = _extended(np.asarray(g, np.float64), far)
    band = np.minimum(d_in, d_out) <= band_px
    a = part_level[band][:, None] * np.asarray(part, np.float64)
    b = np.asarray(paper_level, np.float64)[band][:, None] * np.asarray(paper, np.float64)
    lw = np.asarray(luma_weights, np.float64)
    gap = np.median(np.abs(encoded_from_linear(np.clip(b, 0, None)) @ lw - encoded_from_linear(np.clip(a, 0, None)) @ lw))
    if gap < MIN_LUMA_CONTRAST:
        return None
    blend = blend_from_luma(np.asarray(y, np.float64)[band], a, b, weights=lw)
    out = np.asarray(g, np.float64).copy()
    out[band] = ((1 - blend)[:, None] * a + blend[:, None] * b) @ np.asarray(weights, np.float64)
    return out.astype(np.float32)
