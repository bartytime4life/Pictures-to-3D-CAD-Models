"""Identifiability/counterexamples, not a camera calibration certificate."""

import json
import math
from dataclasses import asdict, replace

import numpy as np
import pytest

from backend.psf_calibration import (
    covariance_from_edge_fits,
    covariance_from_edge_spreads,
    plan_edge_orientation,
)


def normals(angles):
    return np.column_stack([np.cos(angles), np.sin(angles)])


def spreads(n, matrix):
    return np.einsum("ij,jk,ik->i", n, matrix, n)


@pytest.mark.parametrize("rotation", [0.0, 0.17, 0.7, 2.2])
def test_balanced_design_recovers_covariance_in_rotation_invariant_coordinates(rotation):
    n = normals(np.array([0.0, math.pi / 3, 2 * math.pi / 3]) + rotation)
    truth = np.array([[3.0, 1.2], [1.2, 1.0]])
    result = covariance_from_edge_spreads(n, spreads(n, truth))
    np.testing.assert_allclose(result.covariance, truth, rtol=2e-15, atol=3e-15)
    assert result.rank == result.geometric_rank == 3
    assert result.condition == pytest.approx(math.sqrt(2))
    assert result.positive_definite and result.numerically_supported
    assert result.nullspace == ()
    assert not result.gaussian_model_validated and not result.physically_calibrated
    json.dumps(asdict(result), allow_nan=False)


def test_rectangle_spreads_leave_cross_covariance_unidentified_despite_spd_candidate():
    n = [[1, 0], [-1, 0], [0, 1], [0, -1]]
    result = covariance_from_edge_spreads(n, [2, 2, 3, 3])
    assert result.rank == 2 and result.condition is None and result.covariance is None
    assert result.positive_definite
    np.testing.assert_allclose(result.candidate, [[2, 0], [0, 3]], atol=1e-15)
    assert len(result.nullspace) == 1
    # Construct two distinct SPD optics that this whole target cannot distinguish.
    for cross in [-1.8, 1.8]:
        matrix = [[2, cross], [cross, 3]]
        assert np.min(np.linalg.eigvalsh(matrix)) > 0
        np.testing.assert_allclose(spreads(np.array(n), matrix), [2, 2, 3, 3])


def test_oblique_direction_identifies_cross_term_without_changing_diagonal_data():
    q = math.sqrt(0.5)
    result = covariance_from_edge_spreads([[1, 0], [0, 1], [q, q]], [2, 3, 3.25])
    np.testing.assert_allclose(result.covariance, [[2, 0.75], [0.75, 3]], atol=3e-15)


def test_small_positive_spread_error_can_make_full_rank_candidate_indefinite():
    c, d = 39999 / 40001, 400 / 40001
    n = np.array([[1.0, 0.0], [c, d], [c, -d]])
    truth = np.diag([1.0, 0.5])
    v = spreads(n, truth)
    v[0] += 1e-4
    assert np.all(v > 0)
    result = covariance_from_edge_spreads(n, v)
    assert result.rank == 3 and result.condition > 10_000
    assert result.covariance is None and result.positive_definite is False
    assert result.candidate[1][1] == pytest.approx(0.5 - c * c / (d * d) * 1e-4, abs=3e-11)
    assert result.eigenvalues[0] < -0.49  # No eigenvalue clipping conceals the failure.


@pytest.mark.parametrize("scale", [1.0, 1e-200, 1e200])
def test_weighted_repeats_and_variance_units_preserve_known_solution(scale):
    q = math.sqrt(0.5)
    result = covariance_from_edge_spreads(
        [[1, 0], [1, 0], [0, 1], [q, q]],
        np.array([1.0, 3.0, 2.0, 1.7]) * scale,
        variance_std=np.array([1.0, 2.0, 1.0, 1.0]) * scale,
    )
    np.testing.assert_allclose(np.array(result.covariance) / scale, [[1.4, 0], [0, 2]], atol=3e-15)
    assert result.weighted_residual_l2 == pytest.approx(math.sqrt(0.8))
    assert result.maximum_standardized_residual == pytest.approx(0.8)
    assert result.numerically_supported
    json.dumps(asdict(result), allow_nan=False)


def test_underflowed_weights_are_refused_instead_of_dropping_rows():
    with pytest.raises(ValueError, match="weights"):
        covariance_from_edge_spreads([[1, 0], [0, 1]], [1, 1], variance_std=[1e-300, 1e300])


def test_unrepresentable_residual_units_keep_candidate_but_not_false_zero_diagnostics():
    result = covariance_from_edge_spreads(
        [[1, 0], [0, 1], [0.6, 0.8], [0.8, 0.6]],
        [1e-100, 2e-100, 1.6e-100, 1.4e-100],
        variance_std=1e300,
    )
    assert result.rank == 3 and result.covariance is not None
    assert any(v != 0 for v in result.variance_residuals)
    assert result.numerically_supported is False
    assert result.weighted_residual_l2 is None and result.maximum_standardized_residual is None
    json.dumps(asdict(result), allow_nan=False)


def test_zero_variance_is_not_an_spd_covariance():
    result = covariance_from_edge_spreads(normals([0.0, 1.0, 2.0]), [0, 0, 0])
    assert result.rank == 3 and result.positive_definite is False and result.covariance is None
    assert result.weighted_residual_l2 == 0


@pytest.fixture(scope="module")
def resolved_spread_fit():
    from backend.edge_spread import fit_edge_spread
    from backend.profile_observations import PixelNoise

    pixels = np.array([[x, y] for x in range(8, 24) for y in [9, 10]])
    z = (pixels[:, 0] + 0.5 - 16.13) / 1.37
    values = 180 - 140 * np.array([0.5 * math.erfc(-t / math.sqrt(2)) for t in z])
    result = fit_edge_spread(
        pixels,
        values,
        PixelNoise.factor(np.eye(len(pixels)), 1.0),
        sensor_shape=(32, 32),
        normal=(1.0, 0.0),
        anchor=(16.0, 10.0),
        offset_bounds=(-0.4, 0.5),
        sigma_bounds=(0.8, 2.0),
        grid_points=3,
    )
    assert result.best is not None and result.geometry_rank == 2
    return result


def test_fit_pooling_keeps_resolved_widths_but_never_claims_physical_calibration(
    resolved_spread_fit,
):
    n = normals([0.0, math.pi / 3, 2 * math.pi / 3])
    result = covariance_from_edge_fits(n, [resolved_spread_fit] * 3)
    assert result.all_edges_resolved and result.reconstruction is not None
    np.testing.assert_allclose(result.reconstruction.covariance, np.eye(2) * 1.37**2, atol=1e-8)
    assert not result.physically_calibrated and not result.gaussian_model_validated


@pytest.mark.parametrize(
    "flag",
    [
        "flat",
        "tied",
        "endpoint",
        "rank_deficient",
        "work_exhausted",
        "numerically_unsupported",
        "refinement_limited",
    ],
)
def test_fit_pooling_withholds_every_planned_row_if_one_is_unresolved(resolved_spread_fit, flag):
    fits = [resolved_spread_fit, replace(resolved_spread_fit, **{flag: True}), resolved_spread_fit]
    result = covariance_from_edge_fits(normals([0.0, 1.0, 2.0]), fits)
    assert not result.all_edges_resolved and result.reconstruction is None
    assert len(result.directional_variances) == len(result.edge_statuses) == 3
    assert flag in result.edge_statuses[1]
    assert result.edge_statuses[0] == result.edge_statuses[2] == ()


@pytest.mark.parametrize(
    "bad_normals,bad_variances,kwargs",
    [
        ([], [], {}),
        ([[2, 0]], [1], {}),
        ([[True, 0]], [1], {}),
        ([[1, 0]], [-1], {}),
        ([[1, 0]], [float("inf")], {}),
        ([[1, 0]], [True], {}),
        ([[1, 0]], [1], {"variance_std": 0}),
        ([[1, 0]], [1], {"variance_std": True}),
    ],
)
def test_invalid_calibration_summaries_are_explicitly_refused(bad_normals, bad_variances, kwargs):
    with pytest.raises(ValueError):
        covariance_from_edge_spreads(bad_normals, bad_variances, **kwargs)


def test_planner_adds_oblique_normal_to_rectangle_without_claiming_capture_optimality():
    plan = plan_edge_orientation([[1, 0], [0, 1]])
    assert plan.angle_rad == pytest.approx(math.pi / 4)
    assert plan.rank_before == 2 and plan.rank_after == 3
    assert plan.candidates_considered == 720
    assert not plan.continuous_optimality_certified and not plan.physical_capture_qualified
    json.dumps(asdict(plan), allow_nan=False)


def test_planner_handles_first_edge_and_fixed_nonuniform_candidate_set():
    first = plan_edge_orientation([])
    assert first.angle_rad == 0 and first.rank_before == 0 and first.rank_after == 1
    third = plan_edge_orientation([[1, 0], [0, 1]], candidate_angles=[1.6, 0.5, math.pi / 4])
    assert third.angle_rad == pytest.approx(math.pi / 4)
    assert third.candidates_considered == 3


@pytest.mark.parametrize("angles", [[], [math.pi], [-1], [float("nan")], [True]])
def test_planner_refuses_invalid_candidates(angles):
    with pytest.raises(ValueError):
        plan_edge_orientation([[1, 0]], candidate_angles=angles)


@pytest.fixture(scope="module")
def context_fixture():
    from shapely.geometry import box

    from backend.source_context import trace_with_source
    from tests import synthetic as s

    data = s._flat_photo(
        (120, 120, 120), (220, 220, 220), [(box(70, 110, 140, 180), (40, 40, 40))], 4.0, 1.5
    )
    return trace_with_source(data, reference="a4")


def test_context_bridge_fits_actual_captured_edge_without_calibration_or_geometry_mutation(
    context_fixture,
):
    result, context = context_fixture
    profile = result["profile"]
    before = json.dumps(profile, sort_keys=True)
    pixels = [[x, y] for y in [575, 625, 675] for x in range(434, 448)]
    observation = context.source_pixels(pixels, profile=profile)
    fit = context.fit_edge_spread(
        observation,
        profile=profile,
        input_std=1.0,
        normal=(1.0, 0.0),
        anchor=(440.5, 625.0),
        offset_bounds=(-1.0, 1.0),
        sigma_bounds=(1.0, 2.0),
        grid_points=3,
        max_evaluations=64,
        max_basins=2,
        refinement_iterations=16,
    )
    assert fit.best is not None and math.isfinite(fit.best.cost)
    assert 1 < fit.best.sigma < 2  # A digital fixture check, not exact optical recovery.
    assert json.dumps(profile, sort_keys=True) == before
    assert context.metadata()["psf_calibrated"] is False
    assert context.metadata()["noise_calibrated"] is False
    json.dumps(asdict(fit), allow_nan=False)
    altered = replace(observation, raw_values=np.zeros_like(observation.raw_values))
    with pytest.raises(ValueError, match="values differ"):
        context.fit_edge_spread(altered, profile=profile, input_std=1.0)


def test_context_bridge_reuses_source_and_model_guards_before_dispatch(
    context_fixture, monkeypatch
):
    from backend import edge_spread

    result, context = context_fixture
    profile = result["profile"]
    observation = context.source_pixels([[440, 625], [441, 625]], profile=profile)
    seen = {}

    def inspect_dispatch(pixels, values, noise, **kwargs):
        seen.update(pixels=pixels, values=values, noise=noise, kwargs=kwargs)
        return "checked"

    monkeypatch.setattr(edge_spread, "fit_edge_spread", inspect_dispatch)
    assert (
        context.fit_edge_spread(
            observation, profile=profile, input_std=2.0, normal=(1, 0), anchor=(440.5, 625)
        )
        == "checked"
    )
    np.testing.assert_array_equal(seen["values"], observation.raw_values)
    assert not seen["values"].flags.writeable
    assert seen["kwargs"]["sensor_shape"] == context.working_field.shape
    metadata = context.metadata()
    metadata["lens_k1"] = 0.01
    unsupported = replace(context, _record_json=json.dumps(metadata))
    with pytest.raises(ValueError, match="lens distortion"):
        unsupported.fit_edge_spread(observation, profile=profile, input_std=2.0)
