"""Conditional synthetic source means, not physical optical qualification."""

import json
import math
from dataclasses import asdict
from statistics import NormalDist

import numpy as np
import pytest

from backend import edge_spread as spread
from backend.profile_observations import PixelNoise


def scene(*, offset=0.237, sigma=1.37, levels=(31.0, 207.0)):
    pixels = np.array([(x, y) for x in (15, 17, 19, 21, 23, 25) for y in (17, 20, 23)])
    normal = np.array([0.8, 0.6])
    anchor = np.array([20.3, 19.7])
    # Independent standard-library CDF, with explicit pixel-centre coordinates.
    p = np.array(
        [NormalDist().cdf((float(normal @ (q + 0.5 - anchor)) - offset) / sigma) for q in pixels]
    )
    values = levels[0] * (1 - p) + levels[1] * p
    settings = {
        "sensor_shape": (48, 48),
        "normal": normal,
        "anchor": anchor,
        "offset_bounds": (-1.0, 1.0),
        "sigma_bounds": (0.7, 2.3),
        "grid_points": 3,
    }
    return pixels, values, settings


def run(pixels, values, settings, *, noise=None, **changes):
    if noise is None:
        noise = PixelNoise.factor(np.eye(len(pixels)), 1.0)
    return spread.fit_edge_spread(pixels, values, noise, **{**settings, **changes})


@pytest.fixture(scope="module")
def recovered():
    pixels, values, settings = scene()
    return pixels, values, settings, run(pixels, values, settings)


def test_joint_offgrid_offset_width_and_shared_levels_recover_known_means(recovered):
    pixels, _, _, result = recovered
    assert result.best is not None
    assert abs(result.best.offset - 0.237) < 2e-7
    assert abs(result.best.sigma - 1.37) < 2e-7
    np.testing.assert_allclose(result.best.levels, [31.0, 207.0], atol=2e-6, rtol=0)
    assert result.best.cost < 1e-10
    assert result.geometry_rank == 2 and result.geometry_condition >= 1
    assert not result.flat and not result.rank_deficient and not result.endpoint
    assert not result.work_exhausted and not result.numerically_unsupported
    assert result.projection_rank == result.raw_pixel_count == len(pixels)
    assert result.raw_residual_l2 < 1e-5
    assert result.omitted_source_residual_l2 < 1e-10
    assert result.global_search_certified is False


def test_complete_grid_endpoints_logwidth_and_native_json_flags(recovered):
    _, _, settings, result = recovered
    assert result.grid_shape == (3, 3)
    assert result.grid_statuses == ("resolved",) * 9
    assert len(result.grid) == 9
    assert {c.offset for c in result.grid} == {-1.0, 0.0, 1.0}
    widths = [c.sigma for c in result.grid[:3]]
    assert widths[0] == settings["sigma_bounds"][0]
    assert widths[-1] == settings["sigma_bounds"][1]
    assert widths[1] == pytest.approx(math.sqrt(0.7 * 2.3), rel=2e-15)
    for candidate in (*result.grid, *result.candidates):
        assert 0 <= candidate.cost_lower_guard <= candidate.cost <= candidate.cost_upper_guard
        assert all(0 <= v <= 255 for v in candidate.levels)
    for name in (
        "flat",
        "tied",
        "endpoint",
        "rank_deficient",
        "work_exhausted",
        "numerically_unsupported",
        "refinement_limited",
        "global_search_certified",
    ):
        assert type(getattr(result, name)) is bool
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("scale", [1e-6, 1e6])
def test_common_noise_unit_change_preserves_fit_and_cost_scaling(recovered, scale):
    pixels, values, settings, reference = recovered
    result = run(pixels, values, settings, noise=PixelNoise.factor(np.eye(len(pixels)), scale))
    assert abs(result.best.offset - reference.best.offset) < 2e-7
    assert abs(result.best.sigma - reference.best.sigma) < 2e-7
    # Compare a nonzero grid cost, avoiding ratios of two near-zero fitted residuals.
    assert result.grid[0].cost * scale**2 == pytest.approx(reference.grid[0].cost, rel=2e-12)
    assert result.comparison_tolerance * scale**2 == pytest.approx(
        reference.comparison_tolerance, rel=2e-12
    )


def test_normal_reversal_and_translated_frame_preserve_same_means(recovered):
    pixels, values, settings, reference = recovered
    reversed_result = run(pixels, values, settings, normal=-settings["normal"])
    assert reversed_result.best.offset == pytest.approx(-reference.best.offset, abs=2e-7)
    assert reversed_result.best.sigma == pytest.approx(reference.best.sigma, abs=2e-7)
    np.testing.assert_allclose(reversed_result.best.levels, reference.best.levels[::-1], atol=2e-6)
    shift = np.array([7, -3])
    translated = run(pixels + shift, values, settings, anchor=settings["anchor"] + shift)
    assert translated.best.offset == pytest.approx(reference.best.offset, abs=2e-7)
    assert translated.best.sigma == pytest.approx(reference.best.sigma, abs=2e-7)


@pytest.mark.parametrize("level", [0.0, 70.0])
def test_constant_source_is_flat_and_tied_without_identified_width(level):
    pixels, _, settings = scene()
    result = run(pixels, np.full(len(pixels), level), settings)
    assert result.best is not None
    assert result.flat and result.tied and result.rank_deficient
    assert result.geometry_rank == 0 and result.geometry_condition is None
    assert result.unrefined_basins == 9
    assert result.best.cost < 1e-20
    json.dumps(asdict(result), allow_nan=False)


def test_equal_normal_coordinates_alias_width_and_offset():
    pixels = np.array([(10, y) for y in range(6, 18)])
    settings = {
        "sensor_shape": (32, 32),
        "normal": (1.0, 0.0),
        "anchor": (10.5, 12.0),
        "offset_bounds": (-1.0, 1.0),
        "sigma_bounds": (0.5, 2.0),
        "grid_points": 3,
    }
    result = run(pixels, np.full(len(pixels), 70.0), settings)
    assert result.flat and result.tied and result.rank_deficient
    assert result.best.design_rank == 1
    assert result.geometry_rank is None or result.geometry_rank < 2


def test_nuisance_projection_roundoff_does_not_invent_two_geometry_directions():
    pixels = np.array([(10, y) for y in range(6, 18)])
    # Every true derivative is a multiple of the same brightness column, even
    # after this nontrivial retained source projection. Both geometry ranks are0.
    noise = PixelNoise.factor(np.random.default_rng(0).normal(size=(5, len(pixels))), 1.0)
    result = spread.fit_edge_spread(
        pixels,
        np.full(len(pixels), 70.0),
        noise,
        sensor_shape=(32, 32),
        normal=(1.0, 0.0),
        anchor=(10.5, 12.0),
        offset_bounds=(-1.0, 1.0),
        sigma_bounds=(0.5, 2.0),
        grid_points=3,
    )
    assert result.flat and result.tied and result.best.design_rank == 1
    assert result.geometry_rank == 0 and result.geometry_condition is None
    assert result.rank_deficient


def _independent_box_fit(probability, values, bounds):
    a = np.column_stack((1 - probability, probability))
    unconstrained = np.linalg.lstsq(a, values, rcond=None)[0]
    candidates = []
    if np.all((unconstrained >= bounds[0]) & (unconstrained <= bounds[1])):
        candidates.append(unconstrained)
    for fixed, free in ((0, 1), (1, 0)):
        for bound in bounds:
            v = values - a[:, fixed] * bound
            denominator = float(a[:, free] @ a[:, free])
            other = bounds[0] if denominator == 0 else float(a[:, free] @ v) / denominator
            pair = np.zeros(2)
            pair[fixed], pair[free] = bound, np.clip(other, *bounds)
            candidates.append(pair)
    return min(candidates, key=lambda x: float(np.sum((a @ x - values) ** 2)))


def test_bounded_brightness_faces_are_refitted_with_actual_cost_descent():
    pixels, values, settings = scene(levels=(-40.0, 300.0))
    result = run(pixels, values, settings)
    assert result.best is not None
    assert result.best.cost < min(c.cost for c in result.grid)
    assert any(v in (0.0, 255.0) for v in result.best.levels)
    best = result.best
    p = np.array(
        [
            NormalDist().cdf(
                (float(settings["normal"] @ (q + 0.5 - settings["anchor"])) - best.offset)
                / best.sigma
            )
            for q in pixels
        ]
    )
    expected = _independent_box_fit(p, values, (0.0, 255.0))
    np.testing.assert_allclose(best.levels, expected, atol=2e-10, rtol=0)
    assert best.cost == pytest.approx(
        float(np.sum(((1 - p) * best.levels[0] + p * best.levels[1] - values) ** 2)), rel=2e-13
    )


def test_projection_uses_same_raw_rows_and_exposes_discarded_source_information():
    pixels, values, settings = scene()
    matrix = np.eye(len(pixels))[:10]
    std = np.linspace(1.0, 2.0, len(pixels))
    noise = PixelNoise.factor(matrix, std)
    changed = values.copy()
    changed[10:] += 40.0
    result = run(pixels, changed, settings, noise=noise)
    assert abs(result.best.offset - 0.237) < 2e-7 and abs(result.best.sigma - 1.37) < 2e-7
    assert result.best.cost < 1e-10
    assert result.raw_residual_l2 > 50 and result.omitted_source_residual_l2 > 50
    assert result.retained_residual_l2 < 1e-5
    assert result.raw_residual_l2**2 == pytest.approx(
        result.retained_residual_l2**2 + result.omitted_source_residual_l2**2, rel=2e-13
    )
    assert result.projection_rank == 10 and result.raw_pixel_count == len(pixels)


def test_source_column_permutation_requires_matching_pixels_values_and_noise(recovered):
    pixels, values, settings, reference = recovered
    permutation = np.random.default_rng(13).permutation(len(pixels))
    matrix = np.eye(len(pixels))[:, permutation]
    noise = PixelNoise.factor(matrix, np.ones(len(pixels)))
    result = run(pixels[permutation], values[permutation], settings, noise=noise)
    assert result.best.offset == pytest.approx(reference.best.offset, abs=2e-7)
    assert result.best.sigma == pytest.approx(reference.best.sigma, abs=2e-7)


def test_geometry_evaluation_cap_retains_every_grid_slot_and_unfinished_basin():
    pixels, values, settings = scene()
    result = run(pixels, values, settings, max_evaluations=9)
    assert result.best is not None and result.work_exhausted
    assert result.evaluations == 9 and len(result.grid) == 9
    assert result.grid_statuses == ("resolved",) * 9
    assert result.unrefined_basins >= 1 and result.refinement_limited
    assert result.global_search_certified is False


def test_projection_work_cap_retains_pending_grid_slots_and_unknown_local_rank(monkeypatch):
    pixels, values, settings = scene()
    # Exactly one forward evaluation, with no derivative projection budget left.
    rank = len(pixels)
    monkeypatch.setattr(spread, "MAX_WORK", len(pixels) * (2 * rank + 1) + 64 * rank)
    result = run(pixels, values, settings)
    assert result.best is not None and result.work_exhausted
    assert result.evaluations == 1
    assert result.grid_statuses[0] == "resolved"
    assert result.grid_statuses[1:] == ("work_limit",) * 8
    assert result.geometry_rank is None and result.geometry_condition is None
    assert len(result.grid) == 9 and result.unrefined_basins >= 1
    json.dumps(asdict(result), allow_nan=False)


def test_no_refinement_retains_faces_and_exact_domain_endpoint():
    pixels, values, settings = scene(offset=1.0, sigma=2.3)
    result = run(pixels, values, settings, refinement_iterations=0)
    assert result.best.offset == 1.0 and result.best.sigma == 2.3
    assert result.endpoint and result.unrefined_basins >= 1
    assert len(result.candidates) >= 8 and len(result.grid) == 9


def test_infinite_standardized_tail_derivatives_have_their_zero_limits():
    p, density, derivative = spread._cdf_pdf(np.array([-np.inf, -1e300, 0.0, 1e300, np.inf]))
    np.testing.assert_array_equal(p, [0.0, 0.0, 0.5, 1.0, 1.0])
    np.testing.assert_array_equal(derivative, [0.0, 0.0, 0.0, 0.0, 0.0])
    assert density[2] == pytest.approx(1 / math.sqrt(2 * math.pi))
    assert np.isfinite(p).all() and np.isfinite(derivative).all()


@pytest.mark.parametrize("std", [1e-300, 1e300])
def test_extreme_noise_units_retain_numerical_unknowns_instead_of_false_zero_rss(std):
    pixels, values, settings = scene()
    noise = PixelNoise.factor(np.eye(len(pixels)), std)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        result = run(pixels, values, settings, noise=noise, max_evaluations=9)
    assert result.best is None and result.numerically_unsupported
    assert result.grid == (None,) * 9 and result.grid_statuses == ("numerical",) * 9
    assert not result.flat and result.geometry_rank is None
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("value,count,expected", [(1e200, 2, 1e200), (1e308, 5, None)])
def test_large_discarded_norms_do_not_destroy_a_finite_projected_fit(value, count, expected):
    pixels = np.array([(12 + i, 13 + i) for i in range(count)])
    values = np.array([0.0] + [value] * (count - 1))
    noise = PixelNoise.factor(np.eye(count)[:1], 1.0)
    settings = {
        "sensor_shape": (48, 48),
        "normal": (1.0, 0.0),
        "anchor": (20.0, 20.0),
        "offset_bounds": (-1.0, 1.0),
        "sigma_bounds": (0.7, 2.3),
        "grid_points": 3,
    }
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        result = run(pixels, values, settings, noise=noise, refinement_iterations=0)
    assert result.best is not None and result.best.cost == 0.0
    assert result.retained_residual_l2 == 0.0
    if expected is None:
        assert result.raw_residual_l2 is None and result.omitted_source_residual_l2 is None
        assert result.numerically_unsupported
    else:
        assert result.raw_residual_l2 == pytest.approx(expected)
        assert result.omitted_source_residual_l2 == pytest.approx(expected)
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize(
    "changes",
    [
        {"normal": (2.0, 0.0)},
        {"normal": (math.nan, 1.0)},
        {"normal": (True, 0.0)},
        {"anchor": (math.inf, 0.0)},
        {"anchor": (0.0, 1e10)},
        {"anchor": (False, 0.0)},
        {"offset_bounds": (1.0, 1.0)},
        {"offset_bounds": (-math.inf, 1.0)},
        {"offset_bounds": (0.0, math.nextafter(0.0, 1.0))},
        {"offset_bounds": (False, 1.0)},
        {"sigma_bounds": (0.0, 1.0)},
        {"sigma_bounds": (0.1, 1001.0)},
        {"sigma_bounds": (1.0, math.nextafter(1.0, 2.0))},
        {"level_bounds": (255.0, 0.0)},
        {"grid_points": True},
        {"grid_points": 12},
        {"grid_points": 5.0},
        {"max_basins": False},
        {"max_evaluations": 8},
        {"refinement_iterations": -1},
        {"sensor_shape": (True, 48)},
    ],
)
def test_invalid_numeric_domains_and_budgets_are_refused(changes):
    pixels, values, settings = scene()
    with pytest.raises((ValueError, TypeError)):
        run(pixels, values, settings, **changes)


@pytest.mark.parametrize(
    "pixels", [[[True, 1]], [[1.0, 2.0]], [[1, -1]], [[48, 1]], [[1, 2], [1, 2]]]
)
def test_invalid_source_indices_are_refused(pixels):
    count = len(pixels)
    with pytest.raises(ValueError):
        spread.fit_edge_spread(
            pixels,
            np.zeros(count),
            PixelNoise.factor(np.eye(count), 1.0),
            sensor_shape=(48, 48),
            normal=(1.0, 0.0),
            anchor=(20.0, 20.0),
            offset_bounds=(-1.0, 1.0),
            sigma_bounds=(0.7, 2.3),
        )


def test_nonfinite_source_values_and_mismatched_noise_column_count_are_refused():
    pixels, values, settings = scene()
    invalid = values.copy()
    invalid[0] = math.nan
    with pytest.raises(ValueError, match="finite"):
        run(pixels, invalid, settings)
    with pytest.raises(ValueError, match="agree"):
        run(pixels, values, settings, noise=PixelNoise.factor(np.eye(len(pixels) - 1), 1.0))
