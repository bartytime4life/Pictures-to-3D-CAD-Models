"""Conditional finite-material fitting from independently integrated observations.

The fixed pose, point detector, constant levels and isotropic Gaussian used here
are declared synthetic assumptions. These regressions do not qualify real camera
noise, PSFs, response curves, physical recovery or global identifiability.
"""

import json
import math
from dataclasses import asdict

import numpy as np
import pytest

from backend import finite_shape_fit as fitting
from backend.profile_observations import PixelNoise
from tests.test_finite_shape import d_mass


def observations(radius=7.37, fraction=0.273, *, levels=(31.0, 207.0)):
    """Positive area slices, without the product forward model or shape helper."""
    centre = np.array([20.3, 20.1])
    pixels = np.array([(x, y) for x in (12, 17, 21, 24) for y in (13, 18, 23, 27)])
    sigma = 1.1
    first = np.array(
        [d_mass(p + 0.5, centre, radius, radius * fraction, sigma, 24) for p in pixels]
    )
    means = np.array(
        [d_mass(p + 0.5, centre, radius, radius * fraction, sigma, 48) for p in pixels]
    )
    assert np.max(np.abs(first - means)) < 2e-12
    values = levels[0] * (1 - means) + levels[1] * means
    settings = {
        "sensor_shape": (48, 48),
        "homography": np.eye(3),
        "psf_covariance": np.eye(2) * sigma**2,
        "centre": centre,
        "radius_bounds": (6.8, 8.1),
        "chord_fraction_bounds": (0.1, 0.45),
    }
    return pixels, values, settings


def run(pixels, values, settings, *, noise=None, **changes):
    supplied = {**settings, **changes}
    return fitting.fit_circular_segment(
        pixels,
        values,
        PixelNoise.factor(np.eye(len(pixels)), 1.0) if noise is None else noise,
        **supplied,
    )


@pytest.fixture(scope="module")
def off_grid():
    pixels, values, settings = observations()
    result = run(pixels, values, settings, grid_points=3, max_basins=2, max_evaluations=256)
    return pixels, values, settings, result


def test_off_grid_radius_chord_and_unknown_shared_levels_recover_independent_truth(off_grid):
    pixels, _, _, result = off_grid
    best = result.best
    assert best is not None
    assert abs(best.radius - 7.37) < 2e-4
    assert abs(best.chord_fraction - 0.273) < 5e-5
    assert abs(best.chord_offset - 7.37 * 0.273) < 5e-4
    np.testing.assert_allclose(best.levels, [31.0, 207.0], atol=0.003, rtol=0)
    assert best.cost < 1e-6
    assert best.design_rank == 2
    assert result.geometry_rank == 2 and result.geometry_condition >= 1
    assert not result.flat and not result.endpoint and not result.rank_deficient
    assert not result.work_exhausted and not result.numerically_unsupported
    assert result.raw_pixel_count == result.projection_rank == len(pixels)
    assert result.raw_residual_l2 < 0.002
    assert result.omitted_source_residual_l2 < 1e-10


def test_complete_grid_cost_guards_and_local_scope_are_json_serializable(off_grid):
    _, _, _, result = off_grid
    assert result.grid_shape == (3, 3)
    assert len(result.grid) == len(result.grid_statuses) == 9
    assert result.grid_statuses == ("resolved",) * 9
    assert all(row is not None for row in result.grid)
    assert len({(row.radius, row.chord_fraction) for row in result.grid}) == 9
    for row in (*result.grid, *result.candidates):
        assert 0 <= row.cost_lower_guard <= row.cost <= row.cost_upper_guard
        assert row.chord_offset == row.radius * row.chord_fraction
        assert row.forward_residual_error_estimate >= 0
    assert result.global_search_certified is False
    assert result.pose_fitted is False and result.psf_fitted is False
    encoded = json.loads(json.dumps(asdict(result), allow_nan=False))
    for flag in (
        "flat",
        "tied",
        "endpoint",
        "rank_deficient",
        "work_exhausted",
        "numerically_unsupported",
        "global_search_certified",
        "pose_fitted",
        "psf_fitted",
    ):
        assert type(getattr(result, flag)) is bool
        assert type(encoded[flag]) is bool


@pytest.mark.parametrize("fraction", [-0.6, 0.0, 0.6])
def test_minor_half_and_major_truth_grid_is_kept_without_automatic_blur_correction(fraction):
    pixels, values, settings = observations(7.37, fraction, levels=(201.0, 37.0))
    result = run(
        pixels,
        values,
        settings,
        radius_bounds=(7.0, 7.74),
        chord_fraction_bounds=(fraction - 0.08, fraction + 0.08),
        grid_points=3,
        refinement_iterations=0,
        max_basins=0,
        max_evaluations=32,
    )
    assert result.best is not None
    assert result.best.radius == pytest.approx(7.37, abs=2e-14)
    assert result.best.chord_fraction == pytest.approx(fraction, abs=2e-15)
    np.testing.assert_allclose(result.best.levels, [201.0, 37.0], atol=2e-6, rtol=0)
    assert result.best.cost < 1e-9
    assert not result.endpoint
    assert result.unrefined_basins >= 1
    assert result.global_search_certified is False


def test_constant_zero_levels_are_flat_tied_and_geometry_rank_zero():
    pixels, _, settings = observations()
    pixels = pixels[[0, 5, 10, 15]]
    result = run(pixels, np.zeros(4), settings, grid_points=3, max_evaluations=32)
    assert result.best is not None and result.best.cost == 0
    assert result.flat and result.tied and result.rank_deficient
    assert result.geometry_rank == 0 and result.geometry_condition is None
    assert result.best.levels == (0.0, 0.0)
    assert result.raw_residual_l2 == result.retained_residual_l2 == 0
    assert result.unrefined_basins == 9


def test_discarded_source_changes_are_visible_even_when_retained_fit_is_exact():
    pixels, values, settings = observations()
    changed = values.copy()
    changed[10:] += 30.0
    noise = PixelNoise.factor(np.eye(len(pixels))[:10], 1.0)
    result = run(
        pixels,
        changed,
        settings,
        noise=noise,
        radius_bounds=(7.0, 7.74),
        chord_fraction_bounds=(0.193, 0.353),
        grid_points=3,
        refinement_iterations=0,
        max_basins=0,
        max_evaluations=32,
    )
    assert result.best is not None
    assert result.projection_rank == 10 and result.raw_pixel_count == 16
    assert result.best.cost < 1e-9
    assert result.retained_residual_l2 < 1e-5
    assert result.omitted_source_residual_l2 > 70
    assert result.raw_residual_l2 > 70
    assert result.raw_residual_l2**2 == pytest.approx(
        result.retained_residual_l2**2 + result.omitted_source_residual_l2**2,
        rel=2e-12,
        abs=1e-10,
    )


def test_single_retained_mode_does_not_identify_two_levels_or_geometry():
    pixels, values, settings = observations()
    pixels, values = pixels[:4], values[:4]
    result = run(
        pixels,
        values,
        settings,
        noise=PixelNoise.factor(np.ones((1, 4)), 1.0),
        grid_points=3,
        max_evaluations=32,
    )
    assert result.best is not None
    assert result.projection_rank == 1
    assert result.best.design_rank == 1
    assert result.flat and result.tied and result.rank_deficient
    assert result.geometry_rank < 2


def test_forward_budget_retains_all_unknown_grid_cells_and_no_fabricated_best():
    pixels, values, settings = observations()
    result = run(pixels, values, settings, grid_points=3, forward_work_limit=1, max_evaluations=9)
    assert result.grid_shape == (3, 3)
    assert len(result.grid) == len(result.grid_statuses) == 9
    assert result.grid == (None,) * 9
    assert result.grid_statuses == ("work_limit",) * 9
    assert result.best is None and result.candidates == ()
    assert result.work_exhausted and result.forward_evaluations <= 1
    assert result.raw_residual_l2 is None
    json.dumps(asdict(result), allow_nan=False)


def test_geometry_budget_keeps_all_grid_faces_and_marks_missing_refinement():
    pixels, values, settings = observations()
    result = run(pixels, values, settings, grid_points=3, max_evaluations=9)
    assert len(result.grid) == len(result.grid_statuses) == 9
    assert all(row is not None for row in result.grid)
    assert result.best is not None
    assert result.evaluations == 9 and result.work_exhausted
    assert result.unrefined_basins >= 1
    faces = {
        (r.radius, r.chord_fraction)
        for r in result.grid
        if (
            r.radius in settings["radius_bounds"]
            or r.chord_fraction in settings["chord_fraction_bounds"]
        )
    }
    assert faces <= {(r.radius, r.chord_fraction) for r in result.candidates}


def test_true_parameter_on_radius_face_is_retained_and_flagged_as_endpoint():
    pixels, values, settings = observations(7.0, 0.273)
    result = run(
        pixels,
        values,
        settings,
        radius_bounds=(7.0, 7.74),
        chord_fraction_bounds=(0.193, 0.353),
        grid_points=3,
        refinement_iterations=0,
        max_basins=0,
        max_evaluations=32,
    )
    assert result.best is not None and result.endpoint
    assert result.best.radius == 7.0
    assert result.best.chord_fraction == pytest.approx(0.273, abs=2e-15)
    assert result.best.cost < 1e-9


@pytest.mark.parametrize("fraction", [-0.6, 0.0, 0.6])
@pytest.mark.parametrize("normal", [(1.0, 0.0), (0.0, -1.0)])
def test_ring_generator_preserves_true_circle_chord_and_finite_segment_area(fraction, normal):
    radius, centre = 7.37, np.array([20.3, 20.1])
    ring = fitting.circular_segment_ring(radius, fraction, centre=centre, normal=normal)
    assert [s[0] for s in ring] == ["arc", "line"]
    start, middle, end = map(np.asarray, ring[0][1:])
    assert ring[0][-1] == ring[1][1] and ring[1][-1] == ring[0][1]
    local = np.vstack((middle - start, end - start))
    offset = np.linalg.solve(2 * local, np.sum(local * local, axis=1))
    np.testing.assert_allclose(start + offset, centre, atol=2e-13, rtol=0)
    assert np.linalg.norm(offset) == pytest.approx(radius, abs=2e-13)
    assert np.dot(start - centre, normal) == pytest.approx(radius * fraction, abs=2e-13)
    a, m, b = [math.atan2(*(p - centre)[::-1]) for p in (start, middle, end)]
    sweep = (b - a) % math.tau
    assert 0 < (m - a) % math.tau < sweep
    for angle in np.linspace(a, a + sweep, 101):
        point = radius * np.array([math.cos(angle), math.sin(angle)])
        assert point @ normal <= radius * fraction + 2e-13
    area = radius**2 * (sweep - math.sin(sweep)) / 2
    expected = radius**2 * (math.acos(-fraction) + fraction * math.sqrt(1 - fraction**2))
    assert area == pytest.approx(expected, rel=2e-14)


@pytest.mark.parametrize(
    "changes",
    [
        {"radius_bounds": (8.1, 6.8)},
        {"radius_bounds": (7.0, 7.0)},
        {"radius_bounds": (0, 7)},
        {"radius_bounds": (7, math.inf)},
        {"chord_fraction_bounds": (-1, 0)},
        {"chord_fraction_bounds": (0.2, 0.2)},
        {"chord_fraction_bounds": (0.2, 1)},
        {"level_bounds": (255, 0)},
        {"centre": (math.nan, 20)},
        {"normal": (2, 0)},
        {"grid_points": True},
        {"grid_points": 2},
        {"grid_points": 3.0},
        {"max_evaluations": 8, "grid_points": 3},
        {"refinement_iterations": -1},
        {"max_basins": -1},
        {"forward_work_limit": 0},
        {"probability_tolerance": 0},
    ],
)
def test_invalid_domains_and_work_settings_are_refused_before_fitting(changes):
    pixels, values, settings = observations()
    with pytest.raises((ValueError, TypeError)):
        run(pixels, values, settings, **changes)


def test_invalid_source_shapes_nonfinite_data_and_noise_types_are_refused():
    pixels, values, settings = observations()
    noise = PixelNoise.factor(np.eye(len(pixels)), 1.0)
    cases = [
        (pixels, values[:-1], noise),
        (pixels[:-1], values, noise),
        (pixels.astype(float), values, noise),
        (pixels, values * math.nan, noise),
        (pixels, values, object()),
    ]
    for points, observed, supplied_noise in cases:
        with pytest.raises((ValueError, TypeError)):
            fitting.fit_circular_segment(points, observed, supplied_noise, **settings)


@pytest.mark.parametrize("standard_deviation", [1e-6, 1e6])
def test_common_noise_unit_rescaling_preserves_off_grid_geometry_and_decisions(
    off_grid, standard_deviation
):
    pixels, values, settings, baseline = off_grid
    result = run(
        pixels,
        values,
        settings,
        noise=PixelNoise.factor(np.eye(len(pixels)), standard_deviation),
        grid_points=3,
        max_basins=2,
        max_evaluations=256,
    )
    assert result.best is not None and baseline.best is not None
    assert abs(result.best.radius - baseline.best.radius) < 6e-6
    assert abs(result.best.chord_fraction - baseline.best.chord_fraction) < 2e-6
    np.testing.assert_allclose(result.best.levels, baseline.best.levels, atol=5e-4, rtol=0)
    for field in (
        "flat",
        "tied",
        "endpoint",
        "rank_deficient",
        "geometry_rank",
        "work_exhausted",
        "numerically_unsupported",
    ):
        assert getattr(result, field) == getattr(baseline, field), field
    for original, scaled in zip(baseline.grid, result.grid):
        assert original is not None and scaled is not None
        assert scaled.cost * standard_deviation**2 == pytest.approx(
            original.cost, rel=2e-11, abs=1e-8
        )


def test_nonunit_noise_residual_norms_share_one_standardized_orthogonal_split():
    pixels, values, settings = observations()
    deviations = np.linspace(0.5, 2.0, len(pixels))
    changed = values.copy()
    changed[10:] += 30.0
    noise = PixelNoise.factor(np.eye(len(pixels))[:10], deviations)
    result = run(
        pixels,
        changed,
        settings,
        noise=noise,
        radius_bounds=(7.0, 7.74),
        chord_fraction_bounds=(0.193, 0.353),
        grid_points=3,
        refinement_iterations=0,
        max_basins=0,
        max_evaluations=32,
    )
    assert result.best is not None
    expected = np.linalg.norm((changed - values) / deviations)
    assert result.raw_residual_l2 == pytest.approx(expected, rel=1e-6)
    assert result.retained_residual_l2 < 1e-5
    assert result.omitted_source_residual_l2 == pytest.approx(expected, rel=1e-6)
    assert result.raw_residual_l2**2 == pytest.approx(
        result.retained_residual_l2**2 + result.omitted_source_residual_l2**2,
        rel=2e-12,
        abs=1e-10,
    )
    assert result.retained_residual_l2**2 == pytest.approx(result.best.cost, abs=1e-12)


def test_safe_low_corner_does_not_hide_an_unsafe_upper_projective_domain(monkeypatch):
    pixels, values, settings = observations()
    # The entire leftmost disc point belongs to every represented segment.
    # min denominator = 1 - .14 R: +.048 at R6.8, but -.134 at R8.1.
    assert 1 - 0.14 * settings["radius_bounds"][0] > 0
    assert 1 - 0.14 * settings["radius_bounds"][1] < 0
    homography = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.14, 0.0, 1 - 0.14 * settings["centre"][0]],
        ]
    )
    original = fitting.finite_shape_probabilities
    forward_limits = []

    def recorded_forward(*args, **kwargs):
        forward_limits.append(kwargs.get("max_evaluations"))
        return original(*args, **kwargs)

    monkeypatch.setattr(fitting, "finite_shape_probabilities", recorded_forward)
    with pytest.raises(ValueError, match="horizon|chart|denominator"):
        run(pixels, values, settings, homography=homography, grid_points=3)
    # Validation may use the forward parser with a one-evaluation allowance;
    # it must refuse this whole domain before starting data-fitting evaluations.
    assert all(limit == 1 for limit in forward_limits)


@pytest.mark.parametrize("axis", ["radius_bounds", "chord_fraction_bounds"])
def test_adjacent_float_parameter_bounds_cannot_claim_a_resolved_search_grid(axis):
    pixels, values, settings = observations()
    lower = 7.0 if axis == "radius_bounds" else 0.273
    upper = math.nextafter(lower, math.inf)
    assert lower < upper
    with pytest.raises(ValueError):
        run(pixels, values, settings, **{axis: (lower, upper)}, grid_points=3)


def test_exhausted_geometry_diagnostic_remains_unknown_instead_of_rank_zero():
    pixels, values, settings = observations()
    result = run(
        pixels,
        values,
        settings,
        grid_points=3,
        max_evaluations=9,
        refinement_iterations=0,
        max_basins=0,
    )
    assert result.best is not None and result.best.design_rank == 2
    assert result.work_exhausted and result.evaluations == 9
    assert result.geometry_rank is None
    assert result.geometry_condition is None
    assert len(result.grid) == 9 and all(row is not None for row in result.grid)


@pytest.mark.parametrize("standard_deviation", [1e-300, 1e300])
def test_unrepresentable_noise_error_costs_retain_numerical_unknowns_and_strict_json(
    standard_deviation,
):
    _, _, settings = observations()
    pixels, values = np.array([[12, 13], [17, 18]]), np.zeros(2)
    noise = PixelNoise.factor(np.eye(2), standard_deviation)
    # A zero target must not hide overflow/underflow in the model-error norm or
    # squared cost guard and turn unsupported arithmetic into a flat-fit claim.
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        result = run(
            pixels,
            values,
            settings,
            noise=noise,
            grid_points=3,
            max_evaluations=9,
            refinement_iterations=0,
            max_basins=0,
        )
    assert result.grid_shape == (3, 3)
    assert len(result.grid) == len(result.grid_statuses) == 9
    assert result.grid == (None,) * 9
    assert result.grid_statuses == ("numerical",) * 9
    assert result.best is None and result.candidates == ()
    assert result.numerically_unsupported and not result.flat
    assert result.geometry_rank is None and result.geometry_condition is None
    assert result.raw_residual_l2 is None
    assert result.retained_residual_l2 is None and result.omitted_source_residual_l2 is None
    json.dumps(asdict(result), allow_nan=False)


def test_large_representable_omitted_source_norm_uses_stable_arithmetic():
    _, _, settings = observations()
    pixels, values = np.array([[12, 13], [17, 18]]), np.array([0.0, 1e200])
    noise = PixelNoise.factor([[1.0, 0.0]], 1.0)
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        result = run(
            pixels,
            values,
            settings,
            noise=noise,
            grid_points=3,
            refinement_iterations=0,
            max_basins=0,
            max_evaluations=9,
        )
    assert result.best is not None and result.best.cost == 0
    assert len(result.grid) == 9 and all(row is not None for row in result.grid)
    assert result.raw_residual_l2 == pytest.approx(1e200, rel=2e-15)
    assert result.omitted_source_residual_l2 == pytest.approx(1e200, rel=2e-15)
    assert result.retained_residual_l2 == 0
    json.dumps(asdict(result), allow_nan=False)


def test_unrepresentable_omitted_norm_is_nullable_without_losing_finite_projected_fit():
    _, _, settings = observations()
    pixels = np.array([[12, 13], [17, 18], [21, 23], [24, 27], [20, 20]])
    values = np.array([0.0, 1e308, 1e308, 1e308, 1e308])
    noise = PixelNoise.factor([[1.0, 0.0, 0.0, 0.0, 0.0]], 1.0)
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        result = run(
            pixels,
            values,
            settings,
            noise=noise,
            grid_points=3,
            refinement_iterations=0,
            max_basins=0,
            max_evaluations=9,
        )
    assert result.best is not None and result.best.cost == 0
    assert len(result.grid) == 9 and all(row is not None for row in result.grid)
    assert result.raw_residual_l2 is None and result.omitted_source_residual_l2 is None
    assert result.retained_residual_l2 == 0
    assert result.numerically_unsupported is True
    json.dumps(asdict(result), allow_nan=False)
