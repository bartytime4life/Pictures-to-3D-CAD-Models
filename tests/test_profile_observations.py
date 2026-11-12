"""Independent invariants for known linear samples, not physical camera acceptance."""

import cv2
import numpy as np
import pytest

from backend import profile_observations as observations
from backend import sheet


def test_keys_operator_matches_actual_sampler_including_replicated_borders():
    image = np.random.default_rng(4).normal(size=(9, 13))
    x = np.array([-3., -.4, .2, 4.1, 12.4, 25.])
    y = np.array([2.3, -.2, 8.9, 3.7, -5., 19.])
    op = observations.keys_profile(image.shape, x, y)
    assert np.max(np.abs(op.sample(image) - sheet.sample_keys(image, x, y))) < 8e-15
    assert np.max(np.abs(op.matrix.sum(axis=1) - 1)) < 8e-15
    assert np.any(op.matrix < 0)
    assert np.all(np.any(op.matrix != 0, axis=0))
    assert not op.matrix.flags.writeable and not op.pixels_xy.flags.writeable


def test_integer_samples_and_duplicate_border_taps_have_one_source_noise():
    op = observations.keys_profile((1, 1), np.array([-4., -.3, .7, 3.]), np.zeros(4))
    assert np.array_equal(op.pixels_xy, [[0, 0]])
    assert np.max(np.abs(op.matrix - 1)) < 5e-15
    noise = observations.PixelNoise.factor(op.matrix, 2.)
    assert noise.rank == 1
    # Four repeated measurements of the same noisy pixel still have variance four.
    direction = noise.whiten(np.ones(4))
    assert float(direction @ direction) == pytest.approx(.25)


@pytest.mark.parametrize("shape", [(1, 1), (1, 8), (8, 1), (9, 13)])
@pytest.mark.parametrize("border,opencv", [("reflect101", cv2.BORDER_REFLECT_101),
                                        ("replicate", cv2.BORDER_REPLICATE)])
def test_filter_composition_matches_actual_filter_and_keys_at_borders(shape, border, opencv):
    image = np.random.default_rng(9).normal(size=shape)
    x = np.array([-.4, .2, 1.7, 4.1, shape[1] + .3])
    y = np.array([-.8, .3, 2.5, 3.7, shape[0] + .9])
    kernel = np.array([[.1, -.2, .3], [.05, .5, .15], [.4, .2, -.5]])
    op = observations.keys_profile(shape, x, y)
    composed = op.after_filter(kernel, border=border)
    actual = sheet.sample_keys(cv2.filter2D(image, -1, kernel, borderType=opencv), x, y)
    assert np.max(np.abs(composed.sample(image) - actual)) < 5e-15


def test_explicit_gaussian_composition_matches_actual_automatic_kernel():
    image = np.random.default_rng(19).normal(size=(16, 32))
    support = np.arange(-3, 4)
    kernel = np.exp(-.5 * (support / .7)**2)
    kernel /= kernel.sum()
    x, y = np.linspace(-1, 32, 17), np.linspace(-2, 17, 17)
    composed = observations.keys_profile(image.shape, x, y).after_filter(np.outer(kernel, kernel), border="reflect101")
    actual = sheet.sample_keys(cv2.GaussianBlur(image, (0, 0), .7), x, y)
    assert np.max(np.abs(composed.sample(image) - actual)) < 5e-15


def test_filter_work_budget_precedes_expansion(monkeypatch):
    op = observations.keys_profile((8, 8), np.zeros(3), np.ones(3))
    monkeypatch.setattr(observations, "MAX_FILTER_WORK", 1)
    with pytest.raises(ValueError, match="work limits"):
        op.after_filter(np.ones((3, 3)), border="reflect101")


@pytest.mark.parametrize("kernel,border", [(np.ones((2, 3)), "reflect101"),
                                         (np.ones((17, 1)), "reflect101"),
                                         (np.ones((3, 3)), "unknown"),
                                         (np.array([[np.inf]]), "replicate")])
def test_unsupported_filter_is_refused(kernel, border):
    op = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    with pytest.raises(ValueError):
        op.after_filter(kernel, border=border)


@pytest.mark.parametrize("repeats", [1, 2, 8])
def test_duplicates_preserve_gls_fit_information_and_cost(repeats):
    raw_design = np.column_stack((np.ones(5), [-2., -1., 0., 1., 3.]))
    values = np.array([2., 2.9, 4.2, 5., 7.1])
    std = np.array([1., 2., .5, 1.3, .8])
    raw_whitened = raw_design / std[:, None]
    expected = np.linalg.lstsq(raw_whitened, values / std, rcond=None)[0]
    matrix = np.repeat(np.eye(5), repeats, axis=0)
    noise = observations.PixelNoise.factor(matrix, std)
    fit = noise.fit_source(raw_design, matrix @ values)
    assert noise.rank == 5 and fit["residual_degrees_of_freedom"] == 3
    assert np.max(np.abs(fit["coefficients"] - expected)) < 2e-14
    residual = (values - raw_design @ expected) / std
    assert fit["squared_whitened_residual"] == pytest.approx(float(residual @ residual))
    w_design = noise.whiten(matrix @ raw_design)
    assert np.max(np.abs(w_design.T @ w_design - raw_whitened.T @ raw_whitened)) < 4e-14


def test_different_row_spaces_can_have_different_information():
    first = observations.PixelNoise.factor([[1., 0.]], 1.)
    second = observations.PixelNoise.factor(np.eye(2), 1.)
    derivative = np.array([0., 1.])
    assert float(np.linalg.norm(first.whiten(first.matrix @ derivative))) == 0
    assert float(np.linalg.norm(second.whiten(second.matrix @ derivative))) == 1


def test_pseudoinverse_cannot_hide_a_residual_outside_sampling_support():
    noise = observations.PixelNoise.factor([[1.], [1.]], 1.)
    result = noise.residual(np.array([1., -1.]), np.zeros(2))
    assert result["squared_whitened_residual"] < 1e-30
    assert result["outside_support_l2"] == pytest.approx(np.sqrt(2))
    assert not result["within_retained_support_tolerance"]
    with pytest.raises(ValueError, match="outside the retained"):
        noise.fit_source([[1.]], [1., -1.])


def test_whitened_operator_has_identity_covariance_and_declared_raw_projection():
    matrix = np.array([[1., -.2], [.4, .8], [-.3, 1.2]])
    std = np.array([.7, 1.3])
    noise = observations.PixelNoise.factor(matrix, std)
    whitened = noise.whiten(matrix * std)
    assert np.max(np.abs(whitened @ whitened.T - np.eye(2))) < 2e-15
    assert np.max(np.abs(whitened - noise.right)) < 1e-15
    source = np.array([3., 5.])
    assert np.max(np.abs(noise.whiten(matrix @ source) - noise.whiten_source(source))) < 2e-15


def test_rank_and_truncation_are_retained_without_invented_information():
    matrix = np.diag([1., 1e-18])
    noise = observations.PixelNoise.factor(matrix, 1.)
    assert noise.rank == 1
    assert noise.discarded_largest == 1e-18
    assert noise.cutoff > noise.discarded_largest
    fit = noise.fit_source(np.eye(2), [2., 0.])
    assert fit["design_rank"] == 1
    assert fit["residual_degrees_of_freedom"] == 0
    assert np.array_equal(fit["coefficients"], [2., 0.])


@pytest.mark.parametrize("std", [0., -1., np.nan, np.inf, [1., 0.], [1.]])
def test_invalid_input_noise_is_refused(std):
    with pytest.raises(ValueError):
        observations.PixelNoise.factor(np.eye(2), std)


@pytest.mark.parametrize("matrix", [[], [[np.nan]], [[np.inf]], [[0.]], [1., 2.]])
def test_invalid_or_zero_rank_matrix_is_refused(matrix):
    with pytest.raises(ValueError):
        observations.PixelNoise.factor(matrix, 1.)


def test_factor_budget_is_checked_before_svd(monkeypatch):
    monkeypatch.setattr(observations, "MAX_FACTOR_WORK", 1)
    monkeypatch.setattr(np.linalg, "svd", lambda *a, **kw: pytest.fail("exceeded cap reached SVD"))
    with pytest.raises(ValueError, match="work limit"):
        observations.PixelNoise.factor(np.eye(2), 1.)


def test_coordinate_cap_precedes_kernel_and_dense_allocation(monkeypatch):
    monkeypatch.setattr(observations, "_keys", lambda *a: pytest.fail("oversized request reached kernel"))
    with pytest.raises(ValueError, match="bounded nonempty"):
        observations.keys_profile((2, 2), np.zeros(513), np.zeros(513))


@pytest.mark.parametrize("x,y", [(np.array([np.nan]), np.zeros(1)), (np.zeros(1), np.array([np.inf])),
                                (np.array([1e30]), np.zeros(1)), (np.zeros(2), np.zeros(1))])
def test_invalid_sampling_coordinates_are_refused(x, y):
    with pytest.raises(ValueError):
        observations.keys_profile((2, 2), x, y)


def test_shape_is_part_of_the_sampling_geometry():
    op = observations.keys_profile((2, 2), np.zeros(1), np.zeros(1))
    with pytest.raises(ValueError, match="geometry"):
        op.sample(np.zeros((3, 3)))


def test_residual_metrics_never_return_successful_nonfinite_values():
    noise = observations.PixelNoise.factor(np.eye(2), 1.)
    with pytest.raises(ValueError, match="overflow"):
        noise.residual(np.array([1e308, 1e308]), np.zeros(2))


def test_matrix_allocation_cap_precedes_svd(monkeypatch):
    monkeypatch.setattr(observations, "MAX_MATRIX_CELLS", 1)
    with pytest.raises(ValueError, match="allocation limits"):
        observations.PixelNoise.factor(np.eye(2), 1.)
