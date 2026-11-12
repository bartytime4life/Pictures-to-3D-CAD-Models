"""Known fixed coordinate maps, source sharing and actual resampling composition."""

import cv2
import numpy as np
import pytest

from backend import profile_observations as observations
from backend import sheet


def explicit_map(matrix, k1, source_shape, gx, gy):
    """Independent scalar homogeneous and normalized radial coordinate calculation."""
    height, width = source_shape
    result = []
    radius2 = (width * width + height * height) / 4
    for x, y in zip(gx, gy):
        value = matrix @ np.array([x, y, 1.])
        u, v = value[:2] / value[2]
        dx, dy = u - width / 2, v - height / 2
        gain = 1 + k1 * (dx * dx + dy * dy) / radius2
        result.append([width / 2 + gain * dx - .5, height / 2 + gain * dy - .5])
    return np.asarray(result).T


@pytest.mark.parametrize("shape", [(1, 1), (1, 17), (13, 1), (13, 17)])
def test_arbitrary_fixed_keys_warp_matches_actual_two_stage_sampling(shape):
    image = np.random.default_rng(9).normal(size=shape)
    target = (7, 9)
    x, y = np.array([-.8, .3, 2.7, 8.1, 13.]), np.array([-.3, .2, 3.1, 6.7, 8.])
    final = observations.keys_profile(target, x, y)
    yy, xx = np.mgrid[:target[0], :target[1]]

    def mapping(x, y):
        return 1.2 * x + .07 * y**2 - .37, .8 * y + .03 * x**2 + .23

    mx, my = mapping(xx, yy)
    expected = sheet.sample_keys(sheet.sample_keys(image, mx, my), x, y)
    sx, sy = mapping(*final.pixels_xy.T)
    composed = final.after_warp(shape, sx, sy)
    assert np.max(np.abs(composed.sample(image) - expected)) < 8e-15
    assert composed.image_shape == shape
    assert np.max(np.abs(composed.matrix.sum(axis=1) - 1)) < 1e-14


@pytest.mark.parametrize("k1", [-.13, 0., .09])
@pytest.mark.parametrize("scale", [1., -3.])
def test_rectification_map_has_correct_centres_units_radial_scale_and_homogeneous_sign(k1, scale):
    shape, target, ppm = (18, 31), (9, 15), 1.5
    plane = (target[1] / ppm, target[0] / ppm)
    h = scale * np.array([[1.3, .17, 3.37], [-.08, .9, 4.21], [.003, -.004, 1.]])
    image = np.random.default_rng(11).normal(size=shape)
    final = observations.keys_profile(target, np.array([-.2, 2.3, 7.1, 14.7]), np.array([-.7, 1.2, 4.3, 9.]))
    gx, gy = (final.pixels_xy + .5).T / ppm
    x, y = explicit_map(h, k1, shape, gx, gy)
    expected = final.matrix @ sheet.sample_keys(image, x, y)
    actual = final.after_rectification(shape, h, k1, plane, ppm).sample(image)
    assert np.max(np.abs(actual - expected)) < 2e-14


def test_reflection_is_on_the_rectified_grid_before_warp_and_differs_from_raw_filtering():
    shape, target = (19, 29), (11, 17)
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    source = np.sin(.7 * xx + .3 * yy)
    h = np.array([[1.4, .2, 2.37], [-.1, .7, 1.21], [.005, -.003, 1.]])
    t = np.linspace(-2, 2, 17)
    x, y = .2 + .8 * t, .1 + .6 * t
    final = observations.keys_profile(target, x, y)
    one = np.array([.2, .6, .2])
    kernel = np.outer(one, one)
    yy, xx = np.mgrid[:target[0], :target[1]]
    mx, my = explicit_map(h, .07, shape, xx.ravel() + .5, yy.ravel() + .5)
    rectified = sheet.sample_keys(source, mx.reshape(target), my.reshape(target))
    expected = sheet.sample_keys(cv2.filter2D(rectified, -1, kernel, borderType=cv2.BORDER_REFLECT_101), x, y)
    correct = final.after_filter(kernel, border="reflect101").after_rectification(shape, h, .07, target[::-1], 1.)
    wrong = final.after_rectification(shape, h, .07, target[::-1], 1.).after_filter(kernel, border="reflect101")
    assert np.max(np.abs(correct.sample(source) - expected)) < 2e-14
    assert np.max(np.abs(wrong.sample(source) - expected)) > .01


def test_warp_duplicate_pixels_share_one_noise_source():
    final = observations.keys_profile((8, 8), np.linspace(1, 5, 9), np.full(9, 3.))
    warped = final.after_warp((10, 10), np.zeros(len(final.pixels_xy)), np.zeros(len(final.pixels_xy)))
    assert np.array_equal(warped.pixels_xy, [[0, 0]])
    noise = observations.PixelNoise.factor(warped.matrix, 1.)
    assert noise.rank == 1
    assert float(np.linalg.norm(noise.whiten(np.ones(9)))) == pytest.approx(1.)


@pytest.mark.parametrize("rectification", [False, True])
def test_zero_functional_stays_zero_through_warp(rectification):
    final = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    zero = final.after_filter(np.zeros((1, 1)), border="reflect101")
    if rectification:
        result = zero.after_rectification((3, 4), np.eye(3), 0., (2., 2.), 1.)
    else:
        result = zero.after_warp((3, 4), np.zeros(0), np.zeros(0))
    assert result.image_shape == (3, 4)
    assert result.pixels_xy.shape == (0, 2)
    assert np.array_equal(result.sample(np.ones((3, 4))), [0.])
    with pytest.raises(ValueError):
        observations.PixelNoise.factor(result.matrix, 1.)


@pytest.mark.parametrize("field,value", [("k1", np.nan), ("k1", np.inf), ("ppm", 0.), ("ppm", np.inf)])
def test_invalid_rectification_parameters_are_refused(field, value):
    final = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    kwargs = {"source_shape": (3, 3), "matrix": np.eye(3), "k1": 0., "plane_size": (2., 2.), "ppm": 1.}
    kwargs[field] = value
    with pytest.raises(ValueError):
        final.after_rectification(**kwargs)


def test_rectification_output_shape_is_part_of_the_operator():
    final = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    with pytest.raises(ValueError, match="output shape"):
        final.after_rectification((3, 3), np.eye(3), 0., (2., 2.), 2.)


def test_projective_horizon_is_refused_before_keys_evaluation(monkeypatch):
    final = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    monkeypatch.setattr(observations, "_keys", lambda *args: pytest.fail("nonfinite map reached kernel"))
    h = np.eye(3)
    h[2] = 0
    with pytest.raises(ValueError, match="finite and bounded"):
        final.after_rectification((3, 3), h, 0., (2., 2.), 1.)


def test_warp_work_limit_precedes_tap_expansion(monkeypatch):
    final = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    monkeypatch.setattr(observations, "MAX_WARP_WORK", 1)
    monkeypatch.setattr(observations, "_keys", lambda *args: pytest.fail("oversized warp reached kernel"))
    with pytest.raises(ValueError, match="work limits"):
        final.after_warp((3, 3), np.zeros(len(final.pixels_xy)), np.zeros(len(final.pixels_xy)))


def test_warp_coordinates_bind_every_intermediate_pixel():
    final = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    with pytest.raises(ValueError, match="one pair"):
        final.after_warp((3, 3), np.zeros(2), np.zeros(2))
