"""Optical effects of real cameras in the test renderer (synthetic.render): veiling glare,
lateral chromatic aberration and sharpening, and what each does to an edge."""

import math

import cv2
import numpy as np

from backend import sheet
from tests import synthetic as S


def test_veiling_glare_spreads_light_by_its_long_tailed_kernel():
    """The veil of a point of light falls off as (r^2 + a^2)^-1.5, and light the kernel
    carries beyond the frame is lost from the photo."""
    image = np.zeros((401, 401), np.float32)
    image[200, 200] = 1.0
    a = 5.0
    veil = S._veil(image, a)
    assert abs(veil[200, 220] / veil[200, 200] - (a * a / (400 + a * a)) ** 1.5) < 0.01 * (a * a / (400 + a * a)) ** 1.5
    assert abs(veil[180, 200] - veil[200, 220]) < 1e-6 * veil[200, 200]
    assert 0.97 < float(veil.sum()) < 1


def test_lateral_chromatic_aberration_moves_red_out_and_blue_in_at_the_corners():
    """Red is magnified and blue shrunk about the image centre, each by the given shift
    at the image's corners, so a point between the centre and a corner moves in
    proportion to its distance."""
    size = (400, 300)
    red, green, blue = S._chromatic_scales(1.5, size)
    assert green == 1.0
    half_diagonal = math.hypot(*size) / 2
    assert abs((red - 1) * half_diagonal - 1.5) < 1e-12 and abs((1 - blue) * half_diagonal - 1.5) < 1e-12
    image = np.zeros((300, 400), np.float32)
    image[260, 350] = 1.0
    image = cv2.GaussianBlur(image, (0, 0), 2.0)

    def centroid(img):
        yy, xx = np.mgrid[0 : img.shape[0], 0 : img.shape[1]] + 0.5
        return np.array([(img * xx).sum(), (img * yy).sum()]) / img.sum()

    moved = centroid(S._magnify(image, red)) - centroid(image)
    expected = (red - 1) * (centroid(image) - np.array([200.0, 150.0]))
    assert np.linalg.norm(moved - expected) < 0.01


def test_sharpening_saved_values_moves_the_half_level_into_the_dark_side():
    """An unsharp mask is linear in the values it is given. A phone sharpens its saved,
    gamma-encoded values, so in linear light the bright side's overshoot is expanded and
    the dark side's compressed, and the half-level crossing of a straight edge blurred
    1.6 px moves 0.065 px towards the dark side (0.207 px with amount 1.2 and a 1.5 px
    radius). The same mask on linear light leaves it in place."""
    t = np.arange(200, dtype=np.float64) + 0.5
    dark, bright = S.srgb_to_linear(np.array([48.0]))[0], S.srgb_to_linear(np.array([236.0]))[0]
    edge = 100.3
    erf = np.vectorize(math.erf)
    row = dark + (bright - dark) * 0.5 * (1 + erf((t - edge) / (1.6 * math.sqrt(2))))
    linear = np.tile(row, (64, 1)).astype(np.float32)

    def sharpened(image, amount, radius):
        return image + amount * (image - cv2.GaussianBlur(image, (0, 0), radius))

    def crossing(image):
        points = np.column_stack([np.full(32, 100.0), np.linspace(16, 48, 32)])
        normals = np.tile([1.0, 0.0], (32, 1))
        moved, keep = sheet.half_level_search(image, points, normals, half=8.0)
        return float(moved[keep, 0].mean()) - edge

    plain = crossing(linear)  # bilinear sampling's own 0.006 px at this phase
    assert abs(crossing(sharpened(linear, 0.6, 1.0)) - plain) < 0.002
    saved = S.linear_to_srgb(linear).astype(np.float32)
    for (amount, radius), shift in (((0.6, 1.0), -0.065), ((1.2, 1.5), -0.207)):
        moved = crossing(S.srgb_to_linear(np.clip(sharpened(saved, amount, radius), 0, 255)).astype(np.float32))
        assert abs(moved - plain - shift) < 0.01


def test_veiling_glare_is_fitted_from_the_part_and_taken_out():
    """A dark disc on bright paper, blurred 1.6 px, with 10 % of its light scattered by
    the renderer's kernel of a = 20 px (synthetic._veil, built in space, not from the
    tracer's transform). edges._glare_fit reads g and a from the disc's own light, and
    edges._deglare takes out over 90 % of the glare beside the edge. Without glare the
    fitted fraction stays far below the 1 % the trace would correct."""
    from backend import edges

    yy, xx = np.mgrid[0:480, 0:480] + 0.5
    disc = (np.hypot(xx - 240, yy - 240) < 140).astype(np.float32)
    clean = cv2.GaussianBlur((200.0 - 190.0 * disc).astype(np.float32), (0, 0), 1.6)
    glared = (0.9 * clean + 0.1 * S._veil(clean, 20.0)).astype(np.float32)
    fit = edges._glare_fit(glared, disc.astype(np.uint8), 1.6, 5.0)
    assert abs(fit["g"] - 0.1) < 0.01 and abs(fit["a"] / 20.0 - 1) < 0.1 and fit["gain"] > 0.9
    near = np.abs(np.hypot(xx - 240, yy - 240) - 140) < 10
    before = float(np.abs(glared - clean)[near].max())
    assert float(np.abs(edges._deglare(glared, fit, 1.6) - clean)[near].max()) < 0.1 * before
    assert abs(edges._glare_fit(clean, disc.astype(np.uint8), 1.6, 5.0)["g"]) < 0.001
