"""Signed-angle, coordinate-frame and resource contracts; no physical qualification.

The analytic control integrates a finite vertical chord independently. Coordinate
identities concern a supplied fixed Gaussian model. Monkeypatched failures isolate
accounting and exception contracts, rather than establish numerical accuracy.
"""

import json
import math
from dataclasses import FrozenInstanceError, asdict

import numpy as np
import pytest

from backend import finite_centre_fit as centre_fit
from backend import finite_normal as normal
from backend import finite_shape as finite


def configuration(**overrides):
    options = {
        "pixels_xy": np.array([[16, 16], [17, 19], [19, 16], [13, 16]]),
        "radius": 4.0,
        "chord_fraction": 0.25,
        "centre": np.array([16.5, 16.5]),
        "normal": np.array([0.8, 0.6]),
        "sensor_shape": (64, 64),
        "homography": np.eye(3),
        "psf_covariance": np.array([[1.2, 0.25], [0.25, 0.8]]),
        "probability_tolerance": 1e-10,
    }
    options.update(overrides)
    return options


def evaluate(**overrides):
    return normal.circular_segment_normal_derivative(**configuration(**overrides))


def assert_result_contract(result, queries, *, tolerance=1e-10, panels=4096, work=2_000_000):
    for field in (
        result.derivatives,
        result.statuses,
        result.estimated_errors,
        result.query_methods,
        result.query_evaluations,
        result.query_panels,
    ):
        assert isinstance(field, tuple) and len(field) == queries
    assert result.evaluations == sum(result.query_evaluations) <= work
    assert result.panels == sum(result.query_panels)
    assert all(0 <= value <= panels for value in result.query_panels)
    assert all(value >= 0 for value in result.query_evaluations)
    assert 0 < result.chart_margin <= 1
    assert result.method == "finite_chord_shape"
    assert result.quadrature_certified is False
    for value, status, error in zip(
        result.derivatives, result.statuses, result.estimated_errors, strict=True
    ):
        if status == "resolved":
            assert math.isfinite(value)
            assert math.isfinite(error) and 0 <= error <= tolerance
        else:
            assert status in {"work_limit", "numerical"}
            assert value is None and error is None
    # Unknowns stay null; signed derivatives need no probability-range repair.
    assert json.loads(json.dumps(asdict(result), allow_nan=False))["statuses"] == list(
        result.statuses
    )


def resolved_values(result, queries=4):
    assert_result_contract(result, queries)
    assert result.statuses == ("resolved",) * queries
    return np.array(result.derivatives)


@pytest.mark.parametrize(
    "name,value",
    [
        ("pixels_xy", []),
        ("pixels_xy", [[2, 3], [2, 3]]),
        ("pixels_xy", [[2.0, 3.0]]),
        ("pixels_xy", [[True, 3]]),
        ("pixels_xy", [[-1, 3]]),
        ("pixels_xy", [[64, 3]]),
        ("pixels_xy", [[3, 64]]),
        ("pixels_xy", [[i % 64, i // 64] for i in range(2049)]),
        ("sensor_shape", (64,)),
        ("sensor_shape", (True, 64)),
        ("sensor_shape", (64, 64.0)),
        ("sensor_shape", (0, 64)),
        ("normal", [0.0, 0.0]),
        ("normal", [2.0, 0.0]),
        ("normal", [1.0, 0.0, 0.0]),
        ("normal", [True, 0.0]),
        ("normal", [math.nan, 0.0]),
        ("normal", [1.0 + 128 * np.finfo(float).eps, 0.0]),
        ("radius", 0.0),
        ("radius", 0.0009),
        ("radius", 1_000_001.0),
        ("radius", True),
        ("radius", math.inf),
        ("chord_fraction", -1.0),
        ("chord_fraction", 1.0),
        ("chord_fraction", False),
        ("chord_fraction", math.nan),
        ("centre", [0.0]),
        ("centre", [1_000_000_001.0, 0.0]),
        ("centre", [0.0, math.inf]),
        ("homography", np.zeros((3, 3))),
        ("homography", np.diag([1.0, 1.0, 0.0])),
        ("homography", np.eye(2)),
        ("homography", [[1, 0, 0], [0, 1, 0], [0, math.nan, 1]]),
        ("psf_covariance", [[1.0, 0.1], [0.0, 1.0]]),
        ("psf_covariance", [[1.0, 1.0], [1.0, 1.0]]),
        ("psf_covariance", [[1.0, 2.0], [2.0, 1.0]]),
        ("psf_covariance", np.diag([1e-20, 1.0])),
        ("psf_covariance", np.eye(2) * 1e-26),
        ("probability_tolerance", 0.0),
        ("probability_tolerance", 1e-13),
        ("probability_tolerance", 0.01),
        ("probability_tolerance", math.nan),
        ("probability_tolerance", True),
        ("max_panels", 0),
        ("max_panels", 1.5),
        ("max_panels", True),
        ("max_panels", finite.MAX_PANELS + 1),
        ("max_evaluations", 0),
        ("max_evaluations", 1.5),
        ("max_evaluations", True),
        ("max_evaluations", finite.MAX_EVALUATIONS + 1),
    ],
)
def test_invalid_supplied_inputs_are_refused_before_query_evaluation(monkeypatch, name, value):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid input reached query evaluation")

    monkeypatch.setattr(normal, "_closed_form", forbidden)
    with pytest.raises(ValueError):
        evaluate(**{name: value})


def test_maximum_valid_query_population_is_retained_under_a_small_global_budget():
    pixels = np.array([[x, y] for y in range(32) for x in range(64)])
    result = evaluate(pixels_xy=pixels, max_evaluations=2)
    assert_result_contract(result, 2048, work=2)
    assert result.query_evaluations == (2,) + (0,) * 2047
    assert result.query_panels == (1,) + (0,) * 2047
    assert result.statuses[1:] == ("work_limit",) * 2047
    assert result.query_methods[1:] == ("not_attempted",) * 2047


def test_whole_segment_horizon_is_checked_even_when_its_chord_is_safe(monkeypatch):
    # x<=0 half-disc: the chord x=0 has w=1, while the curved edge crosses x=-.5.
    def forbidden(*args, **kwargs):
        raise AssertionError("whole-D horizon was not checked")

    monkeypatch.setattr(normal, "_closed_form", forbidden)
    with pytest.raises(ValueError, match="horizon"):
        evaluate(
            pixels_xy=[[10, 10]],
            centre=(0.0, 0.0),
            radius=1.0,
            chord_fraction=0.0,
            normal=(1.0, 0.0),
            homography=[[1, 0, 10], [0, 1, 10], [2, 0, 1]],
        )


def test_valid_whole_segment_chart_does_not_require_the_disc_centre_to_be_inside_it():
    # The material has x<=-.5, so w=-x-.25 is positive everywhere on it.
    # C=(0,0) lies outside that material, with w(C)=-.25, and is not a chart test.
    result = evaluate(
        pixels_xy=[[2, 2], [3, 4]],
        centre=(0.0, 0.0),
        radius=1.0,
        chord_fraction=-0.5,
        normal=(1.0, 0.0),
        homography=[[1, 0, 2], [0, 1, 2], [-1, 0, -0.25]],
        psf_covariance=np.eye(2),
    )
    resolved_values(result, 2)
    assert result.chart_margin == pytest.approx(1 / 3, rel=1e-13)
    assert all(method.startswith("projective_closed_form") for method in result.query_methods)


def vertical_chord_derivative(dx, dy, radius, sigma):
    """Integrate -s times an isotropic Gaussian on the finite chord x=0.

    With z=(s-dy)/sigma, its first moment is dy*mass+sigma*(phi(lo)-phi(hi)).
    This is an analytic supplied-model control, not an optical calibration.
    """
    lo, hi = (-radius - dy) / sigma, (radius - dy) / sigma
    mass = (math.erf(hi / math.sqrt(2)) - math.erf(lo / math.sqrt(2))) / 2
    phi_lo = math.exp(-lo * lo / 2) / math.sqrt(math.tau)
    phi_hi = math.exp(-hi * hi / 2) / math.sqrt(math.tau)
    moment = dy * mass + sigma * (phi_lo - phi_hi)
    return -math.exp(-((dx / sigma) ** 2) / 2) * moment / (math.sqrt(math.tau) * sigma)


def test_signed_per_radian_control_is_not_clamped_to_a_probability():
    pixels = np.array([[10, 19], [10, 1], [10, 10]])
    result = evaluate(
        pixels_xy=pixels,
        centre=(10.5, 10.5),
        radius=10.0,
        chord_fraction=0.0,
        normal=(1.0, 0.0),
        psf_covariance=np.eye(2) * 0.04,
    )
    actual = resolved_values(result, 3)
    expected = [vertical_chord_derivative(0.0, y, 10.0, 0.2) for y in (9.0, -9.0, 0.0)]
    np.testing.assert_allclose(actual, expected, rtol=2e-11, atol=2e-10)
    assert actual[0] < -1 and actual[1] > 1
    assert actual[0] == pytest.approx(-actual[1], abs=2e-10)
    assert abs(actual[2]) <= 1e-12


@pytest.mark.parametrize("projective", [False, True])
def test_half_disc_normal_negation_gives_the_opposite_derivative(projective):
    h = np.eye(3)
    if projective:
        h[2, :2] = (0.001, -0.0005)
    first = evaluate(chord_fraction=0.0, homography=h)
    second = evaluate(chord_fraction=0.0, normal=(-0.8, -0.6), homography=h)
    np.testing.assert_allclose(
        resolved_values(first), -resolved_values(second), rtol=2e-9, atol=2e-10
    )


@pytest.mark.parametrize("scale", [2.0**-200, -1.0, 2.0**200])
def test_homogeneous_map_scale_preserves_values_chart_and_orientation(scale):
    h = np.array([[1.0, 0.1, 2.0], [-0.05, 1.1, 3.0], [0.001, -0.0005, 1.0]])
    expected = evaluate(homography=h)
    actual = evaluate(homography=h * scale)
    np.testing.assert_allclose(
        resolved_values(actual), resolved_values(expected), rtol=2e-9, atol=2e-10
    )
    assert actual.chart_margin == pytest.approx(expected.chart_margin, rel=1e-13)
    assert actual.reflected is expected.reflected


def test_raw_nonzero_perspective_is_not_reclassified_after_normalization_underflows():
    h = np.eye(3) * 1e8
    h[2, 0] = 1e-320
    actual = evaluate(homography=h)
    expected = evaluate()
    np.testing.assert_allclose(
        resolved_values(actual), resolved_values(expected), rtol=2e-9, atol=2e-10
    )
    assert all(method.startswith("projective_closed_form") for method in actual.query_methods)
    assert all(method.startswith("affine_closed_form") for method in expected.query_methods)


@pytest.mark.parametrize("projective", [False, True])
@pytest.mark.parametrize(
    "transform", ["crop", "reflection", "rotation", "source_scale", "sensor_scale"]
)
def test_source_and_observation_coordinate_changes_preserve_angle_units(projective, transform):
    options = configuration()
    if projective:
        options["homography"][2, :2] = (0.001, -0.0005)
    expected = normal.circular_segment_normal_derivative(**options)
    options = {
        key: value.copy() if isinstance(value, np.ndarray) else value
        for key, value in options.items()
    }
    pixels, h, covariance = (
        options["pixels_xy"],
        options["homography"],
        options["psf_covariance"],
    )
    reflected = False
    if transform == "crop":
        offset = np.array([5, 6])
        options["pixels_xy"] = pixels - offset
        options["sensor_shape"] = (58, 59)
        options["homography"] = np.array([[1, 0, -5], [0, 1, -6], [0, 0, 1]]) @ h
    elif transform in {"reflection", "rotation"}:
        if transform == "reflection":
            matrix = np.array([[-1, 0, 64], [0, 1, 0], [0, 0, 1]])
            options["pixels_xy"] = np.column_stack((63 - pixels[:, 0], pixels[:, 1]))
            reflected = True
        else:
            matrix = np.array([[0, -1, 64], [1, 0, 0], [0, 0, 1]])
            options["pixels_xy"] = np.column_stack((63 - pixels[:, 1], pixels[:, 0]))
        options["homography"] = matrix @ h
        options["psf_covariance"] = matrix[:2, :2] @ covariance @ matrix[:2, :2].T
    elif transform == "source_scale":
        options["centre"] *= 3
        options["radius"] *= 3
        options["homography"] = h @ np.diag([1 / 3, 1 / 3, 1])
        # Sigma remains in observation-pixel units, not source length units.
    else:
        options["pixels_xy"] = 3 * pixels + 1  # pixel centres become 3*(i+.5).
        options["sensor_shape"] = (192, 192)
        options["homography"] = np.diag([3, 3, 1]) @ h
        options["psf_covariance"] = 9 * covariance
    actual = normal.circular_segment_normal_derivative(**options)
    np.testing.assert_allclose(
        resolved_values(actual), resolved_values(expected), rtol=2e-9, atol=2e-10
    )
    assert actual.reflected is (expected.reflected != reflected)


def test_input_arrays_are_snapshotted_before_any_query_callback(monkeypatch):
    options = configuration()
    expected = normal.circular_segment_normal_derivative(**options)
    original = normal._closed_form
    calls = 0

    def mutate_caller_arrays(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            options["pixels_xy"][:] = 0
            options["centre"][:] = math.nan
            options["normal"][:] = 0
            options["homography"][:] = math.nan
            options["psf_covariance"][:] = math.nan
        return original(*args, **kwargs)

    monkeypatch.setattr(normal, "_closed_form", mutate_caller_arrays)
    actual = normal.circular_segment_normal_derivative(**options)
    assert calls == 4
    assert actual == expected
    with pytest.raises(FrozenInstanceError):
        actual.evaluations = 0
    with pytest.raises(TypeError):
        actual.derivatives[0] = 0.0


def short_chord_options(**overrides):
    """An actual smooth one-panel quadrature case, independent of fault injection."""
    return configuration(
        **{
            "pixels_xy": np.array([[16, 17]]),
            "radius": 0.01,
            "chord_fraction": 0.0,
            "normal": (1.0, 0.0),
            "psf_covariance": np.eye(2),
            **overrides,
        }
    )


def force_analytic_discard(monkeypatch):
    def discard(*args, **kwargs):
        raise ArithmeticError("declared numerical discard")

    monkeypatch.setattr(normal, "_closed_form", discard)


@pytest.mark.parametrize("limit", [1, 2, 3])
def test_analytic_attempt_cost_and_global_query_order(limit):
    result = evaluate(max_evaluations=limit)
    assert_result_contract(result, 4, work=limit)
    if limit == 1:
        assert result.statuses == ("work_limit",) * 4
        assert result.query_methods == ("not_attempted",) * 4
        assert result.query_evaluations == (0, 0, 0, 0)
    else:
        assert result.statuses == ("resolved", "work_limit", "work_limit", "work_limit")
        assert result.query_evaluations == (2, 0, 0, 0)
        assert result.query_panels == (1, 0, 0, 0)


@pytest.mark.parametrize(
    "panels,work,expected_work,expected_panels,status",
    [
        (1, 40, 2, 1, "work_limit"),
        (2, 2, 2, 1, "work_limit"),
        (2, 3, 2, 1, "work_limit"),
        (2, 4, 4, 2, "work_limit"),
        (2, 39, 4, 2, "work_limit"),
        (2, 40, 40, 2, "resolved"),
    ],
)
def test_discarded_analytic_work_is_charged_before_real_fallback(
    monkeypatch, panels, work, expected_work, expected_panels, status
):
    force_analytic_discard(monkeypatch)
    result = normal.circular_segment_normal_derivative(
        **short_chord_options(max_panels=panels, max_evaluations=work)
    )
    assert_result_contract(result, 1, panels=panels, work=work)
    assert result.statuses == (status,)
    assert result.evaluations == expected_work
    assert result.panels == expected_panels
    assert result.query_methods == ("affine_closed_form_then_chord_quadrature",)


def test_panel_limit_is_per_query_while_evaluation_limit_is_batch_global(monkeypatch):
    force_analytic_discard(monkeypatch)
    result = normal.circular_segment_normal_derivative(
        **short_chord_options(
            pixels_xy=np.array([[16, 17], [16, 15], [16, 18]]),
            max_panels=2,
            max_evaluations=80,
        )
    )
    assert_result_contract(result, 3, panels=2, work=80)
    assert result.statuses == ("resolved", "resolved", "work_limit")
    assert result.query_evaluations == (40, 40, 0)
    assert result.query_panels == (2, 2, 0)
    assert result.panels == 4


def test_far_tail_discard_still_charges_analytic_and_fallback_endpoint_work(monkeypatch):
    force_analytic_discard(monkeypatch)
    result = normal.circular_segment_normal_derivative(
        **short_chord_options(pixels_xy=[[63, 63]], max_panels=2, max_evaluations=4)
    )
    assert_result_contract(result, 1, panels=2, work=4)
    assert result.statuses == ("resolved",)
    assert result.derivatives == (0.0,)
    assert result.evaluations == 4 and result.panels == 2


def test_unresolved_first_query_does_not_blanket_withhold_later_affordable_query(monkeypatch):
    original = normal._closed_form
    calls = 0

    def first_discard(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ArithmeticError("first query needs unsupported fallback")
        return original(*args, **kwargs)

    monkeypatch.setattr(normal, "_closed_form", first_discard)
    result = evaluate(pixels_xy=[[16, 17], [17, 19]], max_panels=1, max_evaluations=4)
    assert_result_contract(result, 2, panels=1, work=4)
    assert result.statuses == ("work_limit", "resolved")
    assert result.derivatives[0] is None and math.isfinite(result.derivatives[1])
    assert result.query_evaluations == (2, 2)
    assert result.query_panels == (1, 1)


@pytest.mark.parametrize("failing_order,expected_work", [(12, 16), (24, 40)])
def test_attempted_quadrature_nodes_remain_charged_on_numerical_failure(
    monkeypatch, failing_order, expected_work
):
    force_analytic_discard(monkeypatch)
    original = normal._quadrature
    orders = []

    def fail_at_order(*args, **kwargs):
        order = args[-1]
        orders.append(order)
        if order == failing_order:
            raise ArithmeticError("unrepresentable quadrature term")
        return original(*args, **kwargs)

    monkeypatch.setattr(normal, "_quadrature", fail_at_order)
    result = normal.circular_segment_normal_derivative(
        **short_chord_options(max_panels=2, max_evaluations=40)
    )
    assert_result_contract(result, 1, panels=2, work=40)
    assert result.statuses == ("numerical",)
    assert result.evaluations == expected_work and result.panels == 2
    assert orders == ([12] if failing_order == 12 else [12, 24])


@pytest.mark.parametrize("exception", [TypeError, ValueError])
@pytest.mark.parametrize("stage", ["closed_form", "panel", "quadrature"])
def test_unexpected_internal_errors_propagate_instead_of_becoming_unknown(
    monkeypatch, exception, stage
):
    def unexpected(*args, **kwargs):
        raise exception("unexpected sentinel")

    if stage == "closed_form":
        monkeypatch.setattr(normal, "_closed_form", unexpected)
    else:
        force_analytic_discard(monkeypatch)
        if stage == "panel":
            monkeypatch.setattr(finite, "_panel", unexpected)
        else:
            monkeypatch.setattr(normal, "_quadrature", unexpected)
    with pytest.raises(exception, match="unexpected sentinel"):
        normal.circular_segment_normal_derivative(
            **short_chord_options(max_panels=2, max_evaluations=40)
        )


def test_new_operator_keeps_existing_mean_and_four_column_jacobian_contracts():
    options = configuration(pixels_xy=[[16, 17]], radius=1.5)
    before_mean = centre_fit.circular_segment_probabilities(**options)
    before_jacobian = centre_fit.circular_segment_jacobian(**options)
    result = normal.circular_segment_normal_derivative(**options)
    assert_result_contract(result, 1)
    assert centre_fit.circular_segment_probabilities(**options) == before_mean
    assert centre_fit.circular_segment_jacobian(**options) == before_jacobian
    assert type(before_mean) is finite.FiniteShapeResult
    assert set(asdict(before_mean)) == {
        "probabilities",
        "statuses",
        "estimated_errors",
        "tail_bounds",
        "evaluations",
        "panels",
        "chart_margin",
        "reflected",
        "topology_validated",
        "quadrature_certified",
    }
    assert type(before_jacobian) is centre_fit.ShapeJacobian
    assert set(asdict(before_jacobian)) == {
        "jacobian",
        "statuses",
        "estimated_errors",
        "evaluations",
        "panels",
        "method",
        "quadrature_certified",
    }
    assert before_jacobian.statuses == ("resolved",)
    assert all(len(row) == 4 for row in before_jacobian.jacobian)
    assert centre_fit.PARAMETER_ORDER == ("centre_x", "centre_y", "radius", "chord_fraction")
