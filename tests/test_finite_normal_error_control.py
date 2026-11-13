"""V2 normalization/frontier regressions under supplied numerical hypotheses.

The compressed-map reference integrates an elementary exponential independently
of both production and archived quadrature. Injected panels test coverage, error
aggregation and charged work; their values are not Gaussian accuracy evidence.
"""

import itertools
import json
import math
from dataclasses import asdict
from fractions import Fraction

import numpy as np
import pytest

from backend import finite_normal as normal
from backend import finite_shape as finite

EPS = np.finfo(float).eps
POOL_TOLERANCE = 2.0**-30


def exact_determinant(matrix):
    """Leibniz expansion of the exact binary floats, independent of LU/cofactors."""
    rows = [[Fraction(float(value)) for value in row] for row in matrix]
    result = Fraction(0)
    for permutation in itertools.permutations(range(3)):
        inversions = sum(permutation[i] > permutation[j] for i in range(3) for j in range(i + 1, 3))
        product = math.prod(rows[row][column] for row, column in enumerate(permutation))
        result += (-1 if inversions % 2 else 1) * product
    return result


def compressed_map(delta):
    c = 1.0 - 2.0**-16
    return np.array([[1.0, c / 2, 0.5], [0.0, c / 2 + delta, 0.5], [0.0, c, 1.0]])


def compressed_reference(matrix):
    """Exact input d=b-c/2, then an expm1-stable elementary chord integral.

    On x=0 the mapped x equals .5 and y-.5=d*s/(1+c*s). The derivative is
    [exp(-d²/(2(1+c)²))-exp(-d²/(2(1-c)²))]/(2*pi*abs(d)). This controls
    represented operational inputs; it does not calibrate a physical PSF.
    """
    c = Fraction(float(matrix[2, 1]))
    d = Fraction(float(matrix[1, 1])) - c / 2
    near = -(float(d / (1 + c)) ** 2) / 2
    far = -(float(d / (1 - c)) ** 2) / 2
    value = math.exp(near) * -math.expm1(far - near) / (math.tau * float(abs(d)))
    # Explicit engineering allowance for this finite elementary reference.
    return value, 128 * EPS * abs(value)


def evaluate(**overrides):
    options = {
        "pixels_xy": [[0, 0]],
        "radius": 1.0,
        "chord_fraction": 0.0,
        "centre": (0.0, 0.0),
        "normal": (1.0, 0.0),
        "sensor_shape": (3, 3),
        "homography": np.eye(3),
        "psf_covariance": np.eye(2),
        "probability_tolerance": 1e-10,
        "max_panels": 4096,
        "max_evaluations": 2_000_000,
    }
    options.update(overrides)
    return normal.circular_segment_normal_derivative(**options)


def check_result(result, *, tolerance, panels, work):
    assert result.evaluations == sum(result.query_evaluations) <= work
    assert result.panels == sum(result.query_panels)
    assert len(result.derivatives) == len(result.statuses) == len(result.query_methods)
    assert all(0 <= value <= panels for value in result.query_panels)
    for value, error, status in zip(
        result.derivatives, result.estimated_errors, result.statuses, strict=True
    ):
        if status == "resolved":
            assert math.isfinite(value) and math.isfinite(error)
            assert 0 <= error <= tolerance
        else:
            assert status in {"work_limit", "numerical"}
            assert value is None and error is None
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("reflected", [False, True])
@pytest.mark.parametrize("scale", [2.0**-200, 1.0, 2.0**200])
def test_exact_operational_normalization_does_not_depend_on_platform_lu(
    monkeypatch, reflected, scale
):
    matrix = compressed_map(1e-6)
    if reflected:
        matrix = np.array([[-1, 0, 1], [0, 1, 0], [0, 0, 1]]) @ matrix
    matrix *= scale
    inverse = np.array([[1.5, 0.0], [-0.3, 0.8]])
    expected = exact_determinant(matrix)

    def forbidden(*args, **kwargs):
        raise AssertionError("normalizer used a floating LU determinant")

    monkeypatch.setattr(np.linalg, "det", forbidden)
    actual = normal._normalizer(matrix, inverse)
    assert actual.determinant == expected
    assert actual.reflected is (expected < 0)
    assert math.isfinite(actual.log_error) and 0 <= actual.log_error < 1
    inverse_product = Fraction(float(inverse[0, 0])) * Fraction(float(inverse[1, 1]))
    density = abs(expected) * inverse_product
    # Independent rational log expression; its own cancellation is allowed for.
    log_density = math.log(density.numerator) - math.log(density.denominator)
    expected_flux = log_density - math.log(math.tau)
    expected_moment = log_density - math.log(math.sqrt(math.tau))
    allowance = actual.log_error + 128 * EPS * max(1.0, abs(log_density))
    assert abs(actual.log_flux - expected_flux) <= allowance
    assert abs(actual.log_moment - expected_moment) <= allowance


@pytest.mark.parametrize("delta", [1e-6, 1e-4])
@pytest.mark.parametrize("reflected", [False, True])
@pytest.mark.parametrize("homogeneous_scale", [1.0, -8.0])
def test_archived_compressed_limits_against_independent_elementary_reference(
    delta, reflected, homogeneous_scale
):
    matrix = compressed_map(delta)
    expected, reference_allowance = compressed_reference(matrix)
    if reflected:
        matrix = np.array([[-1, 0, 1], [0, 1, 0], [0, 0, 1]]) @ matrix
    result = evaluate(homography=matrix * homogeneous_scale)
    check_result(result, tolerance=1e-10, panels=4096, work=2_000_000)
    assert result.statuses == ("resolved",)
    difference = abs(result.derivatives[0] - expected)
    assert difference <= result.estimated_errors[0] + reference_allowance
    assert difference <= 1e-10 + reference_allowance
    assert result.reflected is reflected
    assert result.query_methods[0].startswith("projective_closed_form")
    if delta == 1e-4:
        # V1 retained this query as unknown at these SAME tolerance/work caps.
        assert result.panels <= 4096 and result.evaluations <= 2_000_000


def injected_frontier(monkeypatch, panel_values, *, guards_pass=True):
    """Inject abstract embedded rules while retaining the actual frontier/accounting."""
    trace = {"panels": [], "rules": [], "normalizers": []}

    def discard(*args, **kwargs):
        raise ArithmeticError("controlled analytic discard")

    def panel(curve, matrix, denominator, start, end):
        trace["panels"].append((start, end))
        return 0.0, 0.125 if guards_pass else 1.0

    def endpoints(curve, matrix, denominator, locations):
        return np.zeros((len(locations), 2)), np.zeros((len(locations), 2))

    def quadrature(*args, **kwargs):
        start, end, order = args[-3:]
        trace["rules"].append((start, end, order))
        trace["normalizers"].append(kwargs["normalizer"])
        return panel_values(start, end, order)

    monkeypatch.setattr(normal, "_closed_form", discard)
    monkeypatch.setattr(finite, "_panel", panel)
    monkeypatch.setattr(finite, "_at", endpoints)
    monkeypatch.setattr(normal, "_quadrature", quadrature)
    return trace


def assert_charged(result, trace):
    # One discarded analytic attempt, then every attempted endpoint/rule unit.
    assert result.evaluations == 2 + 2 * len(trace["panels"]) + sum(
        order for _, _, order in trace["rules"]
    )
    assert result.panels == 1 + len(trace["panels"])


def pooling_values(start, end, order):
    if (start, end) == (0.0, 1.0):
        high, error = 20.0, 2 * POOL_TOLERANCE
    elif (start, end) == (0.0, 0.5):
        high, error = 0.5, 0.75 * POOL_TOLERANCE
    elif (start, end) == (0.5, 1.0):
        high, error = 0.25, 0.125 * POOL_TOLERANCE
    else:
        raise AssertionError("global pooling unnecessarily refined accepted children")
    return (high - error if order == 12 else high), abs(high)


def test_global_error_pooling_replaces_parent_only_after_both_children(monkeypatch):
    trace = injected_frontier(monkeypatch, pooling_values)
    result = evaluate(probability_tolerance=POOL_TOLERANCE, max_panels=4, max_evaluations=116)
    check_result(result, tolerance=POOL_TOLERANCE, panels=4, work=116)
    assert result.statuses == ("resolved",)
    assert result.derivatives == (0.75,)  # Parent value20 must have been removed.
    assert 0.875 * POOL_TOLERANCE <= result.estimated_errors[0] <= POOL_TOLERANCE
    assert set(trace["panels"]) == {(0.0, 1.0), (0.0, 0.5), (0.5, 1.0)}
    assert len(trace["rules"]) == 6
    assert_charged(result, trace)


@pytest.mark.parametrize("max_panels,max_work", [(3, 116), (4, 78), (4, 115)])
def test_interrupted_child_replacement_never_reports_a_partial_integral(
    monkeypatch, max_panels, max_work
):
    trace = injected_frontier(monkeypatch, pooling_values)
    result = evaluate(
        probability_tolerance=POOL_TOLERANCE,
        max_panels=max_panels,
        max_evaluations=max_work,
    )
    check_result(result, tolerance=POOL_TOLERANCE, panels=max_panels, work=max_work)
    assert result.statuses == ("work_limit",)
    assert result.derivatives == (None,) and result.estimated_errors == (None,)
    assert (0.0, 1.0) in trace["panels"]
    assert len(trace["panels"]) >= 2
    assert_charged(result, trace)


@pytest.mark.parametrize("large_order", [12, 24])
def test_roundoff_floor_from_either_rule_cannot_be_erased_by_a_zero_integral(
    monkeypatch, large_order
):
    def cancellation(start, end, order):
        return 0.0, 1e6 if order == large_order else 0.0

    trace = injected_frontier(monkeypatch, cancellation)
    result = evaluate(max_panels=8, max_evaluations=268)
    check_result(result, tolerance=1e-10, panels=8, work=268)
    assert result.statuses[0] in {"work_limit", "numerical"}
    assert result.derivatives == (None,)
    assert_charged(result, trace)


def test_opposite_signed_leaves_do_not_cancel_absolute_error(monkeypatch):
    def cancellation(start, end, order):
        if (start, end) == (0.0, 1.0):
            return (2 * POOL_TOLERANCE if order == 12 else 0.0), 2e6
        value = 1e6 if end <= 0.5 else -1e6
        return value, abs(value)

    trace = injected_frontier(monkeypatch, cancellation)
    result = evaluate(probability_tolerance=POOL_TOLERANCE, max_panels=4, max_evaluations=116)
    check_result(result, tolerance=POOL_TOLERANCE, panels=4, work=116)
    assert result.statuses[0] in {"work_limit", "numerical"}
    assert result.derivatives == (None,) and result.estimated_errors == (None,)
    assert {(0.0, 0.5), (0.5, 1.0)}.issubset(trace["panels"])
    assert_charged(result, trace)


@pytest.mark.parametrize(
    "values,errors",
    [
        ([1e16, 1.0, -1e16], [0.0, 0.0, 0.0]),
        ([1.0, 2.0**-53], [0.0, 0.0]),
        ([0.0, 0.0], [1.0, 2.0**-53]),
        ([1e6, -1e6], [2.0**-40, 2.0**-42]),
        ([0.0, 0.0], [POOL_TOLERANCE, 2.0**-100]),
    ],
)
def test_frontier_reduction_includes_exact_value_rounding_and_outward_error_sum(values, errors):
    leaves = [
        normal._Leaf(float(i), float(i + 1), value, error, abs(value))
        for i, (value, error) in enumerate(zip(values, errors, strict=True))
    ]
    actual_value, actual_error = normal._frontier_total(leaves)
    assert actual_value == math.fsum(values)
    exact_value = sum((Fraction(value) for value in values), Fraction(0))
    exact_error = sum((Fraction(error) for error in errors), Fraction(0))
    exact_total = exact_error + abs(Fraction(actual_value) - exact_value)
    assert Fraction(actual_error) >= exact_total
    # The adjacent lower float is insufficient: no arbitrary extra floor is used.
    assert Fraction(math.nextafter(actual_error, -math.inf)) < exact_total
    assert math.isfinite(actual_error) and actual_error >= 0


@pytest.mark.parametrize(
    "values,errors", [([1e308, 1e308], [0.0, 0.0]), ([0.0, 0.0], [1e308, 1e308])]
)
def test_unrepresentable_final_value_or_error_is_not_a_finite_success(values, errors):
    leaves = [
        normal._Leaf(float(i), float(i + 1), value, error, abs(value))
        for i, (value, error) in enumerate(zip(values, errors, strict=True))
    ]
    with pytest.raises(ArithmeticError):
        normal._frontier_total(leaves)


def test_error_sum_just_above_tolerance_cannot_round_down_to_a_resolved_flag(monkeypatch):
    def above_tolerance(start, end, order):
        if (start, end) == (0.0, 1.0):
            error = 2 * POOL_TOLERANCE
        elif (start, end) == (0.0, 0.5):
            error = POOL_TOLERANCE
        elif (start, end) == (0.5, 1.0):
            error = 2.0**-100
        else:
            raise AssertionError("test requested work past its declared frontier")
        return (-error if order == 12 else 0.0), 0.0

    trace = injected_frontier(monkeypatch, above_tolerance)
    result = evaluate(probability_tolerance=POOL_TOLERANCE, max_panels=4, max_evaluations=116)
    check_result(result, tolerance=POOL_TOLERANCE, panels=4, work=116)
    assert result.statuses == ("work_limit",)
    assert result.derivatives == (None,) and result.estimated_errors == (None,)
    assert_charged(result, trace)


def test_complete_coverage_with_unresolved_panels_is_not_a_zero_error_result(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unresolved geometric guard entered quadrature")

    trace = injected_frontier(monkeypatch, forbidden, guards_pass=False)
    result = evaluate(max_panels=4, max_evaluations=100)
    check_result(result, tolerance=1e-10, panels=4, work=100)
    assert result.statuses == ("work_limit",)
    assert result.derivatives == (None,)
    assert trace["rules"] == []
    assert_charged(result, trace)


@pytest.mark.parametrize("invalid", [-1.0, math.nan, math.inf])
@pytest.mark.parametrize("invalid_order", [12, 24])
def test_nonfinite_or_negative_absolute_rule_data_cannot_create_a_resolved_flag(
    monkeypatch, invalid, invalid_order
):
    def bad_absolute(start, end, order):
        return 0.0, invalid if order == invalid_order else 0.0

    trace = injected_frontier(monkeypatch, bad_absolute)
    result = evaluate(max_panels=2, max_evaluations=40)
    check_result(result, tolerance=1e-10, panels=2, work=40)
    assert result.statuses == ("numerical",)
    assert result.derivatives == (None,)
    assert_charged(result, trace)


def test_one_shared_exact_normalizer_is_reused_through_closed_discard_and_all_rules(monkeypatch):
    original = normal._normalizer
    built = []

    def spy(*args, **kwargs):
        result = original(*args, **kwargs)
        built.append(result)
        return result

    monkeypatch.setattr(normal, "_normalizer", spy)
    trace = injected_frontier(monkeypatch, pooling_values)
    result = evaluate(probability_tolerance=POOL_TOLERANCE, max_panels=4, max_evaluations=116)
    assert result.statuses == ("resolved",)
    assert len(built) == 1
    assert trace["normalizers"] and all(item is built[0] for item in trace["normalizers"])
    assert_charged(result, trace)


def test_global_refinement_order_and_work_are_repeatable_for_equal_priorities(monkeypatch):
    def equal_error(start, end, order):
        return (0.0 if order == 12 else 2 * POOL_TOLERANCE), 1.0

    trace = injected_frontier(monkeypatch, equal_error)
    first = evaluate(probability_tolerance=POOL_TOLERANCE, max_panels=6, max_evaluations=192)
    first_panels, first_rules = list(trace["panels"]), list(trace["rules"])
    trace["panels"].clear()
    trace["rules"].clear()
    second = evaluate(probability_tolerance=POOL_TOLERANCE, max_panels=6, max_evaluations=192)
    assert first == second
    assert first.statuses == ("work_limit",)
    assert trace["panels"] == first_panels and trace["rules"] == first_rules
    assert_charged(second, trace)


@pytest.mark.parametrize(
    "inverse",
    [
        # Frozen solver-only addendum: its tiny upper entry is an actual float.
        [[10.0, 5.551115123125805e-17], [-54.99999999999997, 4.999999999999997]],
        # Well-separated algebra control: dropping the upper term visibly biases density.
        [[1.5, 0.25], [-0.3, 0.8]],
    ],
)
def test_full_represented_inverse_determinant_retains_off_diagonal_terms(monkeypatch, inverse):
    inverse = np.array(inverse)
    saved = inverse.copy()
    a, b, c, d = (Fraction(float(value)) for value in inverse.flat)
    expected = a * d - b * c
    assert expected > 0 and expected != a * d
    log_arguments = []
    original = normal._fraction_log

    def capture_exact_log(value):
        log_arguments.append(value)
        return original(value)

    def forbidden(*args, **kwargs):
        raise AssertionError("represented inverse normalizer used an LU determinant")

    monkeypatch.setattr(normal, "_fraction_log", capture_exact_log)
    monkeypatch.setattr(np.linalg, "det", forbidden)
    actual = normal._normalizer(np.eye(3), inverse)
    assert expected in log_arguments  # Exact off-diagonal term survives to normalization.
    np.testing.assert_array_equal(inverse, saved)
    logarithm = math.log(expected.numerator) - math.log(expected.denominator)
    allowance = actual.log_error + 128 * EPS * max(1.0, abs(logarithm))
    assert abs(actual.log_flux - (logarithm - math.log(math.tau))) <= allowance
    assert abs(actual.log_moment - (logarithm - math.log(math.sqrt(math.tau)))) <= allowance


def test_supported_covariance_with_general_solve_roundoff_resolves_all_queries(monkeypatch):
    # Literal input from frozen inverse addendum5703d6fa; no nominal L*L.T replacement.
    covariance = np.array(
        [[0.010000000000000002, 0.11000000000000001], [0.11000000000000001, 1.2500000000000002]]
    )
    expected_inverse = np.linalg.solve(np.linalg.cholesky(covariance), np.eye(2))
    original = normal._normalizer
    captured = []

    def retain_actual_inverse(h, inverse):
        np.testing.assert_array_equal(inverse, expected_inverse)
        before = inverse.copy()
        result = original(h, inverse)
        np.testing.assert_array_equal(inverse, before)
        captured.append(before)
        return result

    monkeypatch.setattr(normal, "_normalizer", retain_actual_inverse)
    result = evaluate(
        pixels_xy=[[16, 16], [17, 19], [19, 16], [13, 16]],
        radius=4.0,
        chord_fraction=0.25,
        centre=(16.5, 16.5),
        normal=(0.8, 0.6),
        sensor_shape=(64, 64),
        psf_covariance=covariance,
    )
    check_result(result, tolerance=1e-10, panels=4096, work=2_000_000)
    assert result.statuses == ("resolved",) * 4
    assert any(abs(value) > 1e-8 for value in result.derivatives)
    assert len(captured) == 1  # Same represented whitening for every query/fallback.


@pytest.mark.parametrize(
    "inverse",
    [
        [[1.0, 2.0], [2.0, 1.0]],
        [[1.0, 1.0], [1.0, 1.0]],
        [[1.0, math.nan], [0.0, 1.0]],
    ],
)
def test_general_inverse_correction_does_not_admit_nonpositive_or_nonfinite_density(inverse):
    with pytest.raises(ArithmeticError):
        normal._normalizer(np.eye(3), np.array(inverse))
