"""Independent source geometry and ambiguity controls, not camera qualification."""

import math

import numpy as np
import pytest

from backend import raw_source_fit as fitting
from backend.profile_observations import PixelNoise


def oracle(pixels, offset, h, anchor, normal, covariance):
    """Render by crossing forward-projected line points, independently of H^-T."""
    tangent = np.array([-normal[1], normal[0]])
    point = anchor + offset * normal
    plane = np.array([point - 3 * tangent, point + 3 * tangent, point + 0.1 * normal])
    homogeneous = np.column_stack((plane, np.ones(3))) @ h.T
    photo = homogeneous[:, :2] / homogeneous[:, 2, None]
    line = np.cross(np.r_[photo[0], 1.0], np.r_[photo[1], 1.0])
    if line @ np.r_[photo[2], 1.0] < 0:
        line = -line
    width = math.sqrt(float(line[:2] @ covariance @ line[:2]))
    z = ((pixels + 0.5) @ line[:2] + line[2]) / width
    return np.array([0.5 * math.erfc(-v / math.sqrt(2)) for v in z])


def fixture(*, std=1.0, matrix=None, sigma=1.3, levels=(80.0, 200.0)):
    pixels = np.column_stack((np.arange(23, 43), np.full(20, 31)))
    h = np.array([[1.1, 0.15, 2.3], [-0.05, 0.9, 3.1], [0.001, -0.001, 1.0]])
    normal, anchor = np.array([1.0, 0.0]), np.array([27.3, 31.2])
    covariance = np.diag([sigma**2, (1.1 * sigma) ** 2])
    truth = 0.13719
    p = oracle(pixels, truth, h, anchor, normal, covariance)
    values = levels[0] * (1 - p) + levels[1] * p
    noise = PixelNoise.factor(np.eye(20) if matrix is None else matrix, std)
    arguments = {
        "sensor_shape": (64, 64),
        "homography": h,
        "anchor": anchor,
        "normal": normal,
        "psf_covariance": covariance,
        "offset_bounds": (-0.6, 0.6),
        "grid_points": 31,
        "refinement_iterations": 32,
    }
    return pixels, values, noise, arguments, truth


@pytest.mark.parametrize("scale", [1.0, -1.0, 1e-80, -1e80])
def test_anisotropic_probability_has_correct_physical_side_under_h_scale(scale):
    pixels, _, _, args, truth = fixture()
    covariance = np.array([[2.0, 0.45], [0.45, 0.8]])
    h, anchor, normal = args["homography"], args["anchor"], args["normal"]
    expected = oracle(pixels, truth, h, anchor, normal, covariance)
    actual = fitting.plane_edge_probabilities(
        pixels,
        truth,
        sensor_shape=(64, 64),
        homography=scale * h,
        anchor=anchor,
        normal=normal,
        psf_covariance=covariance,
    )
    assert np.max(np.abs(actual - expected)) < 2e-14


def test_off_grid_source_fit_profiles_two_unknown_levels():
    pixels, values, noise, args, truth = fixture(std=np.linspace(0.6, 1.4, 20))
    result = fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    assert abs(result.best.offset - truth) < 2e-8
    assert np.max(np.abs(np.array(result.best.levels) - [80, 200])) < 2e-6
    assert not any(
        (
            result.flat,
            result.plateau,
            result.tied,
            result.endpoint,
            result.rank_deficient,
            result.work_exhausted,
            result.numerically_unsupported,
        )
    )
    assert result.global_search_certified is False
    assert len(result.grid_offsets) == len(result.grid_costs) == 31
    assert {c.kind for c in result.candidates} == {"endpoint", "refined_minimum"}
    assert result.raw_residual_l2 < 2e-6
    assert result.work <= 50_000_000


@pytest.mark.parametrize("levels", [(0.0, 255.0), (255.0, 0.0)])
def test_active_level_bound_faces_preserve_extreme_contrast(levels):
    pixels, values, noise, args, truth = fixture(levels=levels)
    result = fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    assert abs(result.best.offset - truth) < 2e-8
    assert all(0 <= level <= 255 for level in result.best.levels)
    assert max(abs(a - b) for a, b in zip(result.best.levels, levels)) < 2e-6


@pytest.mark.parametrize("value", [0.0, 128.0])
def test_constant_source_is_flat_even_with_rank_two_level_design(value):
    pixels, values, noise, args, _ = fixture()
    result = fitting.fit_plane_edge_offset(pixels, np.full_like(values, value), noise, **args)
    assert result.flat and result.plateau and result.tied
    assert len(result.candidates) >= 3
    assert all(cost <= result.best.cost + result.comparison_tolerance for cost in result.grid_costs)


def test_saturated_narrow_psf_retains_partial_plateau_and_ties():
    pixels, values, noise, args, _ = fixture(sigma=1e-4)
    result = fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    assert result.tied and result.plateau
    assert (
        sum(cost <= result.best.cost + result.comparison_tolerance for cost in result.grid_costs)
        > 2
    )
    assert any(c.kind == "plateau_grid" for c in result.candidates)


def test_noise_unit_scaling_preserves_fit_and_ambiguity():
    pixels, values, _, args, _ = fixture()
    rows = [
        fitting.fit_plane_edge_offset(pixels, values, PixelNoise.factor(np.eye(20), scale), **args)
        for scale in (1.0, 1e-6, 1e6)
    ]
    for row in rows[1:]:
        assert abs(row.best.offset - rows[0].best.offset) < 3e-8
        assert max(abs(a - b) for a, b in zip(row.best.levels, rows[0].best.levels)) < 3e-6
        assert (row.flat, row.plateau, row.tied, row.endpoint, row.rank_deficient) == (
            rows[0].flat,
            rows[0].plateau,
            rows[0].tied,
            rows[0].endpoint,
            rows[0].rank_deficient,
        )


def test_joint_raw_column_permutation_preserves_declared_projection():
    rng = np.random.default_rng(88)
    matrix = rng.normal(size=(12, 20))
    std = np.linspace(0.5, 1.5, 20)
    pixels, values, noise, args, _ = fixture(matrix=matrix, std=std)
    expected = fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    permutation = rng.permutation(20)
    changed = PixelNoise.factor(matrix[:, permutation], std[permutation])
    actual = fitting.fit_plane_edge_offset(
        pixels[permutation], values[permutation], changed, **args
    )
    assert abs(actual.best.offset - expected.best.offset) < 3e-8
    assert actual.best.cost == pytest.approx(expected.best.cost, abs=1e-17)


def test_available_omitted_source_residual_is_not_hidden_by_low_projected_cost():
    pixels, values, _, args, _ = fixture()
    matrix = np.eye(20)[:10]
    noise = PixelNoise.factor(matrix, 1.0)
    values[10:] += 30
    result = fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    assert result.best.cost < 1e-10
    assert result.omitted_source_residual_l2 > 90
    assert result.raw_residual_l2 > 90
    assert result.retained_residual_l2 < 1e-5
    assert result.raw_residual_l2**2 == pytest.approx(
        result.retained_residual_l2**2 + result.omitted_source_residual_l2**2, rel=1e-12
    )


def test_projection_with_one_mode_is_explicitly_rank_deficient():
    pixels, values, _, args, _ = fixture()
    noise = PixelNoise.factor(np.ones((1, 20)), 1.0)
    result = fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    assert result.rank_deficient


def test_search_endpoint_and_refinement_budget_are_retained():
    pixels, values, noise, args, _ = fixture()
    args["offset_bounds"] = (-0.1, 0.1)
    endpoint = fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    assert endpoint.endpoint and endpoint.best.offset == 0.1
    args["offset_bounds"] = (-0.6, 0.6)
    limited = fitting.fit_plane_edge_offset(pixels, values, noise, max_evaluations=31, **args)
    assert limited.work_exhausted and limited.evaluations == 31
    assert len(limited.grid_costs) == 31
    assert any(c.kind == "unfinished_minimum" for c in limited.candidates)
    assert sum(c.kind == "endpoint" for c in limited.candidates) == 2


def test_work_refusal_precedes_target_projection(monkeypatch):
    pixels, values, noise, args, _ = fixture()
    monkeypatch.setattr(
        PixelNoise, "whiten_source", lambda *args: pytest.fail("exceeded budget projected inputs")
    )
    with pytest.raises(ValueError, match="work limit"):
        fitting.fit_plane_edge_offset(pixels, values, noise, work_limit=1, **args)


@pytest.mark.parametrize(
    "change",
    [
        {"normal": (2.0, 0.0)},
        {"psf_covariance": [[1.0, 0.2], [0.1, 1.0]]},
        {"psf_covariance": [[1.0, 0.0], [0.0, 0.0]]},
        {"homography": np.zeros((3, 3))},
        {"offset_bounds": (-np.inf, 1.0)},
        {"grid_points": True},
    ],
)
def test_invalid_geometry_and_search_inputs_are_refused(change):
    pixels, values, noise, args, _ = fixture()
    args.update(change)
    with pytest.raises(ValueError):
        fitting.fit_plane_edge_offset(pixels, values, noise, **args)


def test_sensor_chart_and_duplicate_pixel_refusals():
    pixels, values, noise, args, _ = fixture()
    args["homography"] = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.03, 0.0, 1.0]])
    with pytest.raises(ValueError, match="inverse projective chart"):
        fitting.fit_plane_edge_offset(pixels, values, noise, **args)
    args["homography"] = np.eye(3)
    pixels[1] = pixels[0]
    with pytest.raises(ValueError, match="unique"):
        fitting.fit_plane_edge_offset(pixels, values, noise, **args)


def test_partial_refinement_budget_keeps_a_newly_evaluated_better_candidate():
    pixels, _, noise, args, _ = fixture()
    p = oracle(
        pixels, 0.11, args["homography"], args["anchor"], args["normal"], args["psf_covariance"]
    )
    result = fitting.fit_plane_edge_offset(pixels, 80 + 120 * p, noise, max_evaluations=32, **args)
    assert result.work_exhausted and result.evaluations == 32
    assert result.best.cost < min(result.grid_costs)
    assert result.best.kind == "unfinished_minimum"
    assert result.best.bracket[0] <= result.best.offset <= result.best.bracket[1]
