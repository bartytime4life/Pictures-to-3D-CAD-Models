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
surfaces an edge lies between. Two colours can differ clearly in the saved photo yet
have the same luminance (pure green on light grey); the edge is then measured on the
channels that do differ (mix_weights).
"""

import cv2
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


def surface_light(pixels):
    """Median linear-light RGB of a surface's 8-bit sRGB pixels (N x 3)."""
    return np.median(_LINEAR[pixels], axis=0).astype(np.float64)


def saved_contrast(a, b, weights):
    """How far apart two surfaces' light (linear RGB) lies in a mix, in saved grey
    levels: the scale contrast limits are stated on."""
    w = np.asarray(weights, np.float64)
    return float(abs(encoded_from_linear(w @ a) - encoded_from_linear(w @ b)))


def mix_weights(a, b, floor=40.0):
    """Channel weights for measuring the edge between two surfaces of linear RGB `a`
    and `b`.

    Luminance is kept while it separates them by at least `floor` saved grey levels:
    it carries the photo's finest detail. Below that, each channel is weighted by its
    own difference, taking only the channels that differ in the more strongly differing
    direction so that the weights stay non-negative, and that mix is used if it
    separates the surfaces better. Weights sum to 1.
    """
    luminance = saved_contrast(a, b, LUMINANCE)
    if luminance >= floor:
        return LUMINANCE
    difference = np.asarray(a, np.float64) - np.asarray(b, np.float64)
    up, down = np.maximum(difference, 0), np.maximum(-difference, 0)
    chosen = up if up @ up >= down @ down else down
    if chosen.sum() <= 0:
        return LUMINANCE
    weights = tuple(float(v) for v in chosen / chosen.sum())
    return weights if saved_contrast(a, b, weights) > luminance else LUMINANCE


def reduce_in_linear_light(rgb, scale):
    """Shrink an 8-bit sRGB photo by `scale` (below 1) and return 8-bit sRGB.

    Each output pixel is the exact area average of the linear light it covers, so an
    edge's half-level keeps its place. Averaging saved values instead would mix tones
    on the wrong scale and move edges, the error this module exists to avoid.
    """
    height, width = rgb.shape[:2]
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    out = np.empty((size[1], size[0], 3), np.uint8)
    for channel in range(3):
        light = cv2.resize(_LINEAR[rgb[..., channel]], size, interpolation=cv2.INTER_AREA)
        out[..., channel] = np.clip(np.rint(encoded_from_linear(light)), 0, 255)
    return out
