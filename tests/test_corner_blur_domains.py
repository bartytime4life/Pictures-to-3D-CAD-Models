"""Independent regressions for shared radius/blur parameter-set inference.

The erfc/Legendre calculation is an ordinary numerical development oracle, not
a certified probability bound. Exact quarter-probability and rational box-cover
checks exercise separate analytic and set-accounting properties.
"""

import itertools
import math
from decimal import ROUND_UP, Decimal, localcontext
from fractions import Fraction
from functools import lru_cache

import numpy as np
import pytest

from backend import corner_blur_domains as joint
from backend import corner_feasibility as fixed
from backend.decimal_bounds import Interval


@lru_cache(maxsize=2)
def quadrature(order):
    return np.polynomial.legendre.leggauss(order)


def oracle_level(point, sigma, radius, *, order=96):
    """Separate continuum cutout integral; no production CDF or mass routine."""
    px, py = map(float, point)
    sx, sy = map(float, sigma)
    radius = float(radius)

    def cdf(value):
        return .5 * math.erfc(-value / math.sqrt(2))

    wedge = cdf(px / sx) * cdf(py / sy)
    if radius == 0:
        return wedge
    nodes, weights = quadrature(order)
    terms = []
    for node, weight in zip(nodes, weights):
        theta = (float(node) + 1) * math.pi / 4
        x = radius * (1 - math.cos(theta))
        height = radius * (1 - math.sin(theta))
        density = math.exp(-.5 * ((x - px) / sx) ** 2) / (sx * math.sqrt(2 * math.pi))
        vertical = cdf((height - py) / sy) - cdf(-py / sy)
        terms.append(float(weight) * math.pi / 4 * radius * math.sin(theta) * density * vertical)
    return wedge - math.fsum(terms)


def oracle_mass(a, b, mean, sigma):
    """Stable erfc differences for independent Gaussian strip-mass checks."""
    low, high = ((float(value) - float(mean)) / float(sigma) for value in (a, b))
    if low >= 0:
        return .5 * (math.erfc(low / math.sqrt(2)) - math.erfc(high / math.sqrt(2)))
    return .5 * (math.erfc(-high / math.sqrt(2)) - math.erfc(-low / math.sqrt(2)))


def config(**changes):
    return {
        "format": "pictures-to-cad-corner-feasibility", "version": 2,
        "coordinate_unit": "px", "points": [["0", "0"]],
        "blur_sigma_intervals": [[".5", "1.5"], ["1", "2"]],
        "level_intervals": [[".1", ".2"]], "radius_domain": ["0", "4"],
        "radius_resolution": ".125", "blur_resolution": [".125", ".125"],
        "max_boxes": 31, "cells": 8, **changes,
    }


def rational_interval(pair):
    return tuple(Fraction(Decimal(value)) for value in pair)


def radius_sets(result, key):
    return [rational_interval(pair) for pair in result[key]]


def parameter_boxes(result, category):
    return [tuple(rational_interval(axis) for axis in box)
            for box in result["parameter_boxes"][category]]


def contains(box, point):
    return all(low <= Fraction(value) <= high for (low, high), value in zip(box, point))


def projection(boxes):
    merged = []
    for low, high in sorted(box[0] for box in boxes):
        if merged and low <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def assert_joint_coverage(result, raw):
    """Exact intrinsic volume and nonoverlapping interiors prove finite coverage.

    All leaves are closed and inside the prior. A finite closed union missing
    a prior point would miss positive relative volume. Singleton axes are
    checked for containment but omitted from intrinsic-volume products.
    """
    assert result["parameter_order"] == ["radius", "sigma_x", "sigma_y"]
    assert "excluded" not in result  # Excluded nuisance projections are unsound.
    domain = tuple(rational_interval(axis) for axis in
                   [raw["radius_domain"], *raw["blur_sigma_intervals"]])
    active = [i for i, (low, high) in enumerate(domain) if low < high]
    groups = {category: parameter_boxes(result, category)
              for category in ("accepted", "unknown", "excluded")}
    leaves = list(itertools.chain.from_iterable(groups.values()))
    assert leaves
    for box in leaves:
        assert len(box) == 3
        for (low, high), (prior_low, prior_high) in zip(box, domain):
            assert prior_low <= low <= high <= prior_high
    for left, right in itertools.combinations(leaves, 2):
        assert not all(max(left[i][0], right[i][0]) < min(left[i][1], right[i][1])
                       for i in active)
    prior_volume = math.prod(domain[i][1] - domain[i][0] for i in active)
    leaf_volume = sum(math.prod(box[i][1] - box[i][0] for i in active) for box in leaves)
    assert leaf_volume == prior_volume
    assert result["coverage_complete"] is True
    assert radius_sets(result, "inner") == projection(groups["accepted"])
    assert radius_sets(result, "outer") == projection(groups["accepted"] + groups["unknown"])


@pytest.mark.parametrize("point", [(".4", "1.3"), ("-.3", ".8"), ("1.8", ".2")])
def test_blur_domain_bounds_cover_independent_interior_probabilities(point):
    domains = [[".5", "1.1"], [".9", "1.7"]]
    for radius in ("0", "1.25", "2.25"):
        bounded = joint.parameter_level_bounds(point, domains, radius, cells=16)
        assert 0 <= bounded.lo <= bounded.hi <= 1
        for sigma in itertools.product((.5, .7, 1.1), (.9, 1.2, 1.7)):
            coarse = oracle_level(point, sigma, radius, order=48)
            reference = oracle_level(point, sigma, radius, order=96)
            assert abs(coarse - reference) < 5e-13
            assert float(bounded.lo) - 2e-13 <= reference <= float(bounded.hi) + 2e-13


def test_exact_apex_quarter_holds_for_every_positive_blur_in_the_domain():
    domains = [Interval(".000001", "1000000"), Interval(".000001", "1000000")]
    assert joint.parameter_level_bounds(("0", "0"), domains, "0", cells=1) == Interval.point(".25")
    raw = config(radius_domain=["0", "0"], blur_sigma_intervals=[["1", "2"], ["1", "3"]],
                 level_intervals=[[".25", ".25"]], max_boxes=1, cells=1)
    result = joint.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert result["classification_complete"] is True
    assert radius_sets(result, "inner") == [(Fraction(0), Fraction(0))]
    assert_joint_coverage(result, raw)


def test_levels_above_apex_quarter_exclude_every_radius_and_blur():
    raw = config(level_intervals=[[".26", ".30"]], max_boxes=1)
    result = joint.analyze(raw)
    assert result["status"] == "conditional_incompatible"
    assert result["inner"] == result["outer"] == []
    assert result["parameter_boxes"]["accepted"] == result["parameter_boxes"]["unknown"] == []
    assert_joint_coverage(result, raw)


@pytest.mark.parametrize("radius,point", [("0", (".3", ".7")), ("2.25", (".5", ".5"))])
def test_singleton_blur_probability_domains_agree_exactly_with_version_one(radius, point):
    sigma = (".5", "1.5")
    actual = joint.parameter_level_bounds(point, [[s, s] for s in sigma], radius, cells=16)
    assert actual == fixed.level_bounds(point, sigma, radius, cells=16)


def test_singleton_blur_analysis_agrees_with_version_one_radius_sets():
    raw = config(blur_sigma_intervals=[[".5", ".5"], ["1.5", "1.5"]])
    first = {key: value for key, value in raw.items()
             if key not in ("blur_sigma_intervals", "blur_resolution")}
    first.update(version=1, blur_sigma=[".5", "1.5"])
    expected, actual = fixed.analyze(first), joint.analyze(raw)
    for key in ("status", "inner", "outer", "classification_complete", "budget_exhausted",
                "boxes_evaluated", "prior_ceiling_reached"):
        assert actual[key] == expected[key]
    assert_joint_coverage(actual, raw)


def test_axis_swap_and_common_scaling_preserve_parameter_probability_bounds():
    point, domains, radius = (".4", "1.3"), [[".5", ".9"], ["1.1", "1.6"]], "2.25"
    original = joint.parameter_level_bounds(point, domains, radius, cells=16)
    swapped = joint.parameter_level_bounds(point[::-1], domains[::-1], radius, cells=16)
    assert max(original.lo, swapped.lo) <= min(original.hi, swapped.hi)
    scaled = joint.parameter_level_bounds(("4", "13"), [["5", "9"], ["11", "16"]], "22.5", cells=16)
    for a, b in ((original.lo, scaled.lo), (original.hi, scaled.hi)):
        assert abs(Fraction(a) - Fraction(b)) < Fraction(1, 10**45)


def test_known_interior_radius_and_blur_are_not_excluded():
    truth = (Decimal("2.25"), Decimal(".65"), Decimal("1.35"))
    points = [[".5", ".5"], ["1.5", ".5"], [".5", "1.5"]]
    centers = [Decimal(str(oracle_level(point, truth[1:], truth[0]))) for point in points]
    bands = [[str(center - Decimal(".08")), str(center + Decimal(".08"))] for center in centers]
    raw = config(points=points, radius_domain=["1.5", "3"],
                 blur_sigma_intervals=[[".5", ".9"], ["1.1", "1.6"]],
                 level_intervals=bands, cells=8, max_boxes=31)
    result = joint.analyze(raw)
    kept = parameter_boxes(result, "accepted") + parameter_boxes(result, "unknown")
    assert any(contains(box, truth) for box in kept)
    assert not any(contains(box, truth) for box in parameter_boxes(result, "excluded"))
    assert any(low <= Fraction(truth[0]) <= high for low, high in radius_sets(result, "outer"))
    for box in parameter_boxes(result, "accepted"):
        middle = [float((low + high) / 2) for low, high in box]
        for point, (low, high) in zip(points, bands):
            reference = oracle_level(point, middle[1:], middle[0])
            assert float(low) - 2e-13 <= reference <= float(high) + 2e-13
    assert_joint_coverage(result, raw)


def test_rejected_blur_boxes_do_not_exclude_a_compatible_radius_projection():
    raw = config(points=[["1", "0"]], radius_domain=["0", "0"],
                 blur_sigma_intervals=[["1", "3"], ["1", "1"]],
                 level_intervals=[[".39", ".41"]], blur_resolution=[".01", ".01"],
                 cells=1, max_boxes=63)
    result = joint.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert result["parameter_boxes"]["accepted"] and result["parameter_boxes"]["excluded"]
    assert any(box[0] == (Fraction(0), Fraction(0)) for box in parameter_boxes(result, "excluded"))
    assert radius_sets(result, "outer") == radius_sets(result, "inner") == [(Fraction(0), Fraction(0))]
    assert_joint_coverage(result, raw)


def test_individually_feasible_levels_can_have_no_common_sigma_x():
    raw = config(points=[["1", "0"], ["2", "0"]], radius_domain=["0", "0"],
                 blur_sigma_intervals=[["1", "3"], ["1", "1"]],
                 level_intervals=[[".39", ".41"], [".39", ".41"]],
                 blur_resolution=[".01", ".01"], cells=1, max_boxes=63)
    for point, level in zip(raw["points"], raw["level_intervals"]):
        assert joint.analyze({**raw, "points": [point], "level_intervals": [level]})["status"] == "conditional_compatible"
    result = joint.analyze(raw)
    assert result["status"] == "conditional_incompatible"
    assert result["outer"] == []
    assert_joint_coverage(result, raw)


def test_three_observations_require_one_common_pair_of_blur_sigmas():
    raw = config(points=[["0", "1"], ["1", "0"], ["1", "1"]],
                 radius_domain=["0", "0"], blur_sigma_intervals=[["1", "2"], ["1", "2"]],
                 level_intervals=[[".420", ".421"], [".420", ".421"], [".478", ".479"]],
                 blur_resolution=[".001", ".001"], cells=1, max_boxes=127)
    # The first two depend only on one sigma. Avoid subdividing an irrelevant
    # sigma for those individual existence controls; joint inference keeps both.
    resolutions = [["1", ".001"], [".001", "1"], [".001", ".001"]]
    witnesses = [(1, 1), (1, 1), (2, 2)]
    for point, level, resolution, sigma in zip(raw["points"], raw["level_intervals"], resolutions, witnesses):
        assert float(level[0]) < oracle_level(point, sigma, 0) < float(level[1])
        single = joint.analyze({**raw, "points": [point], "level_intervals": [level],
                                "blur_resolution": resolution})
        assert single["status"] == "conditional_compatible"
    result = joint.analyze(raw)
    assert result["status"] == "conditional_incompatible"
    assert result["classification_complete"] is True
    assert result["outer"] == []
    assert_joint_coverage(result, raw)


def test_all_levels_accept_the_complete_joint_prior_without_search():
    raw = config(level_intervals=[["0", "1"]], max_boxes=1, cells=1)
    result = joint.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert result["classification_complete"] is True
    assert result["budget_exhausted"] is False
    assert result["boxes_evaluated"] == 1
    assert_joint_coverage(result, raw)


def test_work_exhaustion_keeps_every_queued_parameter_box():
    raw = config(cells=1, max_boxes=1)
    result = joint.analyze(raw)
    assert result["status"] == "unknown"
    assert result["budget_exhausted"] is True
    assert result["boxes_evaluated"] == 1
    assert result["classification_complete"] is False
    assert len(result["parameter_boxes"]["unknown"]) == 2
    assert radius_sets(result, "outer") == [(Fraction(0), Fraction(4))]
    assert_joint_coverage(result, raw)


def test_numerical_failure_keeps_the_complete_joint_box_unknown(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ArithmeticError("independent injected enclosure failure")

    monkeypatch.setattr(fixed, "_level_bounds_with_sigma", unavailable)
    raw = config()
    result = joint.analyze(raw)
    assert result["status"] == "unknown"
    assert result["unknown_reason_counts"]["numerical_enclosure"] >= 1
    assert result["parameter_boxes"]["accepted"] == result["parameter_boxes"]["excluded"] == []
    assert_joint_coverage(result, raw)


def test_coarse_gaussian_tail_bounds_do_not_turn_into_exact_zero():
    raw = config(points=[["-100", "-100"]], blur_sigma_intervals=[["1", "2"], ["1", "2"]],
                 radius_domain=["0", "0"], level_intervals=[["0", "0"]],
                 blur_resolution=["1", "1"], cells=1)
    result = joint.analyze(raw)
    assert result["status"] == "unknown"
    assert result["parameter_boxes"]["accepted"] == result["parameter_boxes"]["excluded"] == []
    assert result["unknown_reason_counts"]["parameter_resolution"] == 1
    assert_joint_coverage(result, raw)


def test_forty_digit_external_inputs_allow_more_precise_internal_subdivision():
    raw = config(points=[["0.1234567890123456789012345678901234567890", ".5"]],
                 radius_domain=["1.234567890123456789012345678901234567890",
                                "3.876543210987654321098765432109876543211"],
                 level_intervals=[[".20", ".24"]], cells=2, max_boxes=7,
                 radius_resolution=".01", blur_resolution=[".01", ".01"])
    result = joint.analyze(raw)
    assert result["boxes_evaluated"] > 1
    assert_joint_coverage(result, raw)


def test_joint_model_and_analysis_ignore_hostile_global_decimal_context():
    args = ((".4", "1.3"), [[".5", ".9"], ["1.1", "1.6"]], "2.25")
    raw = config(cells=2, max_boxes=7)
    expected_level = joint.parameter_level_bounds(*args, cells=8)
    expected_analysis = joint.analyze(raw)
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_UP
        context.Emax, context.Emin = 2, -2
        for signal in context.traps:
            context.traps[signal] = True
        assert joint.parameter_level_bounds(*args, cells=8) == expected_level
        assert joint.analyze(raw) == expected_analysis


@pytest.mark.parametrize("a,b,mean,domain,sigmas", [
    ("-.4", "1.3", ".2", (".3", "1.5"), (.3, .6, .9, 1.5)),
    ("1", "2", "0", (".25", "4"), (.25, .7, 1.47, 2.3, 4)),
    ("-2", "-1", "0", (".25", "4"), (.25, .7, 1.47, 2.3, 4)),
    ("20", "20.1", "0", ("1", "1.01"), (1, 1.002, 1.005, 1.01)),
])
def test_strip_mass_intersection_contains_independent_values_for_every_sampled_sigma(a, b, mean, domain, sigmas):
    bounded = joint._x_mass(Decimal(a), Decimal(b), Interval.point(mean), Interval(*domain))
    assert 0 <= bounded.lo <= bounded.hi <= 1
    for sigma in sigmas:
        reference = oracle_mass(a, b, mean, sigma)
        # Relative numerical tolerance keeps the far-tail control meaningful.
        assert reference > 0
        assert float(bounded.lo) <= reference * (1 + 3e-12)
        assert float(bounded.hi) >= reference * (1 - 3e-12)


def test_strip_mass_maximum_can_be_inside_the_sigma_domain():
    low_sigma, high_sigma = .25, 4
    interior_sigma = math.sqrt(3 / (2 * math.log(2)))
    interior_mass = oracle_mass(1, 2, 0, interior_sigma)
    endpoint_max = max(oracle_mass(1, 2, 0, sigma) for sigma in (low_sigma, high_sigma))
    assert interior_mass > 1.5 * endpoint_max
    bounded = joint._x_mass(Decimal(1), Decimal(2), Interval.point(0), Interval(".25", "4"))
    assert float(bounded.hi) >= interior_mass * (1 - 3e-12)


def test_density_cover_controls_strip_mass_when_both_cdf_arguments_are_in_coarse_tails():
    a, b, mean, sigma = Decimal(20), Decimal("20.1"), Interval.point(0), Interval("1", "1.01")
    cdf_only = fixed._mass(Interval.point(a), Interval.point(b), mean, sigma)
    bounded = joint._x_mass(a, b, mean, sigma)
    assert cdf_only.hi > Decimal("1e-16")
    assert 0 < bounded.lo <= bounded.hi < Decimal("1e-70")
    assert bounded.lo >= cdf_only.lo and bounded.hi < cdf_only.hi


@pytest.mark.parametrize("change", [
    {"version": 1}, {"version": True}, {"blur_sigma": ["1", "1"]},
    {"blur_sigma_intervals": [["1", "2"]]},
    {"blur_sigma_intervals": [["2", "1"], ["1", "2"]]},
    {"blur_sigma_intervals": [["0", "1"], ["1", "2"]]},
    {"blur_sigma_intervals": [["1e-7", "1"], ["1", "2"]]},
    {"blur_sigma_intervals": [["1", "1000001"], ["1", "2"]]},
    {"blur_sigma_intervals": [["NaN", "1"], ["1", "2"]]},
    {"blur_sigma_intervals": [[1, "2"], ["1", "2"]]},
    {"blur_sigma_intervals": [[1.0, "2"], ["1", "2"]]},
    {"blur_resolution": ["0", ".1"]}, {"blur_resolution": ["-.1", ".1"]},
    {"blur_resolution": [".1"]}, {"blur_resolution": [.1, ".1"]},
    {"blur_resolution": ["1e-13", ".1"]},
    {"blur_resolution": ["1000001", ".1"]},
    {"points": [[0, "0"]]}, {"radius_domain": [0, "4"]},
    {"level_intervals": [[0, "1"]]}, {"max_boxes": True}, {"cells": True},
    {"coordinate_unit": "inch"}, {"unknown_field": "refuse"},
])
def test_joint_schema_refuses_invalid_or_implicit_input(change):
    with pytest.raises((ValueError, TypeError)):
        joint.analyze(config(**change))


def test_every_v2_field_and_the_two_endpoint_work_bound_are_required():
    for missing in ("blur_sigma_intervals", "blur_resolution", "radius_resolution", "cells"):
        raw = config()
        del raw[missing]
        with pytest.raises(ValueError):
            joint.analyze(raw)
    # This satisfies v1's cells*points*(boxes+1) bound but violates v2's
    # two endpoint evaluations per joint box bound.
    with pytest.raises(ValueError, match="work limit"):
        joint.analyze(config(points=[["0", "0"]] * 8,
                             level_intervals=[["0", "1"]] * 8,
                             cells=64, max_boxes=65))
