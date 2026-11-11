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


def linear_luminance(rgb):
    """Linear-light luminance (float32, 0-255 scale) of an 8-bit sRGB photo, with the
    Rec. 709 weights of linear sRGB."""
    return (
        0.2126 * _LINEAR[rgb[..., 0]]
        + 0.7152 * _LINEAR[rgb[..., 1]]
        + 0.0722 * _LINEAR[rgb[..., 2]]
    )
