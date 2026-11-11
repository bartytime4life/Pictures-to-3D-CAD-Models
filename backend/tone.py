"""A photo's tone curve: saved values <-> linear light.

A lens and sensor blur the scene in linear light. The camera then saves every value
through a transfer curve (sRGB's, IEC 61966-2-1: close to a 2.2 gamma), which bends a
blurred edge's profile. The half-level of an edge blurred by a symmetric point-spread
function lies on the edge only in linear light. Taken on saved values it sits inside
the darker side: by about half a blur sigma for a dark part on white paper, 0.13 mm
per edge in the rendered test photos. Sub-pixel measurements therefore use linear
light; see docs/reference-sheet.md.

Linear values keep the saved values' 0-255 scale, so 0 and 255 map to themselves.

Photos are decoded as sRGB. Display P3 shares its curve and Adobe RGB's 2.2 gamma is
close. The primaries do not matter here: any fixed mix of linear channels keeps an
edge's half-level in place. A camera's own tone mapping on top of the standard curve
is not known from the file and is not undone.

That freedom also chooses the mix. Luminance is used when it separates the two
sides of a boundary all along it. Two colours can differ clearly in the saved photo yet
have the same luminance (pure green on light grey); the boundary is then measured on
the channels that do differ (choose_mix).
"""

import numpy as np


def _floating(values):
    array = np.asarray(values)
    return array if array.dtype.kind == "f" else array.astype(np.float64)


def linear_from_encoded(values):
    """Saved sRGB values (0-255) to linear light on the same scale."""
    v = _floating(values) / 255
    return 255 * np.where(
        v <= 0.04045, v / 12.92, ((np.maximum(v, 0.04045) + 0.055) / 1.055) ** 2.4
    )


def encoded_from_linear(values):
    """Linear light (0-255 scale) to saved sRGB values; negative light saves as 0."""
    v = np.maximum(_floating(values), 0) / 255
    return 255 * np.where(
        v <= 0.0031308, 12.92 * v, 1.055 * np.maximum(v, 0.0031308) ** (1 / 2.4) - 0.055
    )


_LINEAR = linear_from_encoded(np.arange(256)).astype(np.float32)


# Rec. 709 luminance weights of linear sRGB.
LUMINANCE = (0.2126, 0.7152, 0.0722)


def linear_mix(rgb, weights=LUMINANCE):
    """A fixed mix of an 8-bit sRGB photo's linear-light channels (float32, 0-255
    scale); luminance by default. `weights` are non-negative and sum to 1."""
    out = np.zeros(rgb.shape[:2], np.float32)
    for channel, weight in enumerate(weights):
        if weight:
            out += np.float32(weight) * _LINEAR[rgb[..., channel]]
    return out


def linear_luminance(rgb):
    """Linear-light luminance (float32, 0-255 scale) of an 8-bit sRGB photo."""
    return linear_mix(rgb, LUMINANCE)


def light_at(rgb, points):
    """Linear-light RGB (N x 3) of an 8-bit sRGB image at points (x, y), each read from
    the pixel that contains it; points outside the image read its nearest edge pixel."""
    h, w = rgb.shape[:2]
    x = np.clip(np.floor(points[:, 0]).astype(np.int64), 0, w - 1)
    y = np.clip(np.floor(points[:, 1]).astype(np.int64), 0, h - 1)
    return _LINEAR[rgb[y, x]].astype(np.float64)


def saved_contrast(a, b, weights):
    """How far apart the light on two sides (linear RGB, one row or N rows) lies in a
    mix, in saved grey levels: the scale contrast limits are stated on."""
    w = np.asarray(weights, np.float64)
    return np.abs(
        encoded_from_linear(np.asarray(a, np.float64) @ w)
        - encoded_from_linear(np.asarray(b, np.float64) @ w)
    )


def difference_mix(a, b):
    """Each channel weighted by its own difference between two colours (linear RGB),
    taking only the channels that differ in the more strongly differing direction so
    that the weights stay non-negative. Returns None for equal colours."""
    difference = np.asarray(a, np.float64) - np.asarray(b, np.float64)
    up, down = np.maximum(difference, 0), np.maximum(-difference, 0)
    chosen = up if up @ up >= down @ down else down
    if chosen.sum() <= 0:
        return None
    return tuple(float(v) for v in chosen / chosen.sum())


# A boundary is measurable where its two sides differ by 12 saved grey levels
# (sheet.half_level_search); twice that is taken as adequate everywhere.
ADEQUATE_CONTRAST = 24.0


def choose_mix(side_a, side_b):
    """Channel weights for measuring a boundary, from the linear RGB on its two sides
    at N points along it (N x 3 each). Weights are non-negative and sum to 1.

    A mix is judged by the contrast it leaves at the boundary's weakest stretch: the
    5th percentile over the points. Luminance is kept while that is adequate, because
    it carries the photo's finest detail and every boundary is then measurable in it.
    Otherwise the candidate with the best weakest stretch is used if it beats
    luminance: the mix weighted by each channel's difference between the two sides'
    typical colours, an even mix, or one channel alone. Judging by the weakest stretch
    keeps a part of two colours from losing the boundary of its smaller colour.
    """

    def weakest(weights):
        return float(np.percentile(saved_contrast(side_a, side_b, weights), 5))

    luminance = weakest(LUMINANCE)
    if luminance >= ADEQUATE_CONTRAST:
        return LUMINANCE
    difference = difference_mix(np.median(side_a, axis=0), np.median(side_b, axis=0))
    candidates = [difference] if difference else []
    candidates += [(1 / 3, 1 / 3, 1 / 3), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    best = max(candidates, key=weakest)
    return best if weakest(best) > luminance else LUMINANCE
