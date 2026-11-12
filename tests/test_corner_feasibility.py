"""Independent development regressions for conditional corner-set enclosures.

The erfc/Legendre oracle below is ordinary floating-point quadrature, not a
certified primitive or physical error bound. Exact boundary and set-coverage
checks separately exercise the inference contract without trusting that oracle.
"""

import math
from dataclasses import is_dataclass
from decimal import ROUND_UP, Decimal, localcontext
from fractions import Fraction

import numpy as np
import pytest

from backend import corner_feasibility as corner
from backend.decimal_bounds import Interval


def oracle_level(point, sigma, radius, *, order=96):
    """Integrate the missing circular corner by a separate angular parameter.

    x=r*(1-cos(theta)), h=r*(1-sin(theta)) removes the square-root
    endpoint. Uses stdlib erfc, NumPy quadrature nodes, and no production CDF,
    rectangle-mass, geometry, rendering, or fitting functions.
    """
    px, py = map(float, point)
    sx, sy = map(float, sigma)
    radius = float(radius)

    def cdf(value):
        return .5 * math.erfc(-value / math.sqrt(2))

    wedge = cdf(px / sx) * cdf(py / sy)
    if radius == 0:
        return wedge
    nodes, weights = np.polynomial.legendre.leggauss(order)
    terms = []
    for node, weight in zip(nodes, weights):
        theta = (float(node) + 1) * math.pi / 4
        x = radius * (1 - math.cos(theta))
        height = radius * (1 - math.sin(theta))
        density = math.exp(-.5 * ((x - px) / sx) ** 2) / (sx * math.sqrt(2 * math.pi))
        vertical = cdf((height - py) / sy) - cdf(-py / sy)
        terms.append(float(weight) * math.pi / 4 * radius * math.sin(theta) * density * vertical)
    return wedge - math.fsum(terms)


def config(**changes):
    raw = {
        "format": "pictures-to-cad-corner-feasibility",
        "version": 1,
        "coordinate_unit": "px",
        "points": [["0", "0"]],
        "blur_sigma": ["0.5", "1.5"],
        "level_intervals": [["0.1", "0.2"]],
        "radius_domain": ["0", "4"],
        "radius_resolution": "0.125",
        "max_boxes": 31,
        "cells": 8,
    }
    return {**raw, **changes}


def intervals(result, key):
    return [(Fraction(Decimal(a)), Fraction(Decimal(b))) for a, b in result[key]]


def in_union(result, key, value):
    value = Fraction(value)
    return any(a <= value <= b for a, b in intervals(result, key))


def assert_leaf_cover(result, domain):
    """Every prior radius survives in one terminal leaf category, without gaps."""
    low, high = map(Fraction, domain)
    leaves = sorted(intervals(result, "accepted") + intervals(result, "unknown")
                    + intervals(result, "excluded"))
    assert leaves
    assert leaves[0][0] == low and leaves[-1][1] == high
    end = low
    for a, b in leaves:
        assert low <= a <= b <= high
        assert a <= end
        end = max(end, b)
    assert end == high
    assert result["coverage_complete"] is True


@pytest.mark.parametrize("point,sigma,radius", [
    (("0", "0"), ("1", "1"), "0"),
    ((".5", ".5"), (".5", "1.5"), "2.25"),
    ((".5", "1.5"), (".5", "1.5"), "2.25"),
    (("1.5", ".5"), (".5", "1.5"), "2.25"),
    (("-.4", "1.7"), (".8", "1.2"), "1.3"),
    (("2", "2"), ("1.5", ".5"), "4"),
])
def test_probability_covers_contain_independent_continuum_values(point, sigma, radius):
    coarse = oracle_level(point, sigma, radius, order=48)
    reference = oracle_level(point, sigma, radius, order=96)
    assert abs(coarse - reference) < 5e-13  # Observed numerical agreement only.
    bounded = corner.level_bounds(point, sigma, radius, cells=32)
    assert 0 <= bounded.lo <= bounded.hi <= 1
    assert float(bounded.lo) - 2e-13 <= reference <= float(bounded.hi) + 2e-13


def test_zero_radius_apex_is_exactly_one_quarter():
    for sigma in (("1", "1"), (".5", "1.5"), (".000001", "1000000")):
        assert corner.level_bounds(("0", "0"), sigma, "0", cells=1) == Interval.point(".25")


def test_spatial_refinement_tightens_the_probability_cover():
    point, sigma, radius = (".5", ".5"), (".5", "1.5"), "2.25"
    coarse = corner.level_bounds(point, sigma, radius, cells=4)
    fine = corner.level_bounds(point, sigma, radius, cells=32)
    assert coarse.lo < fine.lo < fine.hi < coarse.hi


def test_radius_box_encloses_independent_values_across_the_whole_box():
    point, sigma = (".5", ".5"), (".5", "1.5")
    box = corner.radius_box_bounds(point, sigma, Interval("1", "4"), cells=32)
    for radius in np.linspace(1, 4, 17):
        reference = oracle_level(point, sigma, radius)
        assert float(box.lo) - 2e-13 <= reference <= float(box.hi) + 2e-13
    small = corner.level_bounds(point, sigma, "1", cells=32)
    large = corner.level_bounds(point, sigma, "4", cells=32)
    assert large.hi < small.lo


def test_axis_swap_preserves_the_probability_despite_different_rectangle_covers():
    original = corner.level_bounds((".4", "1.3"), (".5", "1.5"), "2.25", cells=32)
    swapped = corner.level_bounds(("1.3", ".4"), ("1.5", ".5"), "2.25", cells=32)
    # Cover widths depend on the partition direction, so equality is not required.
    assert max(original.lo, swapped.lo) <= min(original.hi, swapped.hi)
    assert abs(oracle_level((.4, 1.3), (.5, 1.5), 2.25)
               - oracle_level((1.3, .4), (1.5, .5), 2.25)) < 5e-13


def test_common_scaling_preserves_dimensionless_probability_bounds():
    original = corner.level_bounds((".4", "1.3"), (".5", "1.5"), "2.25", cells=16)
    scaled = corner.level_bounds(("4", "13"), ("5", "15"), "22.5", cells=16)
    for a, b in ((original.lo, scaled.lo), (original.hi, scaled.hi)):
        assert abs(Fraction(a) - Fraction(b)) < Fraction(1, 10**45)


def test_all_admissible_levels_accept_the_entire_prior_without_search():
    raw = config(level_intervals=[["0", "1"]], max_boxes=1, cells=1)
    result = corner.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert intervals(result, "inner") == [(Fraction(0), Fraction(4))]
    assert intervals(result, "outer") == [(Fraction(0), Fraction(4))]
    assert result["unknown"] == result["excluded"] == []
    assert result["classification_complete"] is True
    assert result["budget_exhausted"] is False
    assert result["prior_ceiling_reached"] is True
    assert result["boxes_evaluated"] == 1
    assert_leaf_cover(result, (0, 4))


def test_apex_levels_above_one_quarter_reject_every_nonnegative_radius():
    result = corner.analyze(config(level_intervals=[[".26", ".30"]], max_boxes=1))
    assert result["status"] == "conditional_incompatible"
    assert result["inner"] == result["outer"] == result["unknown"] == []
    assert intervals(result, "excluded") == [(Fraction(0), Fraction(4))]
    assert result["classification_complete"] is True
    assert result["prior_ceiling_reached"] is False
    assert_leaf_cover(result, (0, 4))


def test_sharp_singleton_accepts_closed_exact_level_contact():
    result = corner.analyze(config(radius_domain=["0", "0"], level_intervals=[[".25", ".25"]]))
    assert result["status"] == "conditional_compatible"
    assert intervals(result, "inner") == [(Fraction(0), Fraction(0))]
    assert intervals(result, "outer") == [(Fraction(0), Fraction(0))]
    assert result["excluded"] == []
    assert result["classification_complete"] is True
    assert_leaf_cover(result, (0, 0))


def test_closed_boundary_sharp_witness_is_never_discarded():
    result = corner.analyze(config(level_intervals=[[".25", ".25"]], max_boxes=7))
    assert result["status"] != "conditional_incompatible"
    assert in_union(result, "outer", 0)
    assert not in_union(result, "excluded", 0)
    assert_leaf_cover(result, (0, 4))


def test_known_rounded_radius_is_retained_and_accepted_boxes_agree_with_independent_model():
    points = [[".5", ".5"], ["1.5", ".5"]]
    sigma, radius = [".5", "1.5"], Decimal("2.25")
    centers = [Decimal(str(oracle_level(point, sigma, radius))) for point in points]
    levels = [[str(center - Decimal(".05")), str(center + Decimal(".05"))] for center in centers]
    result = corner.analyze(config(points=points, blur_sigma=sigma, level_intervals=levels,
                                   cells=16, max_boxes=31))
    assert result["status"] == "conditional_compatible"
    assert result["inner"]
    assert in_union(result, "outer", radius)
    assert not in_union(result, "excluded", radius)
    assert not in_union(result, "outer", 0)
    assert not in_union(result, "outer", 4)
    for a, b in intervals(result, "accepted"):
        midpoint = float((a + b) / 2)
        for point, (low, high) in zip(points, levels):
            probability = oracle_level(point, sigma, midpoint)
            assert float(low) - 2e-13 <= probability <= float(high) + 2e-13
    assert_leaf_cover(result, (0, 4))


def test_incompatible_observations_at_the_same_point_have_no_radius():
    result = corner.analyze(config(points=[["0", "0"], ["0", "0"]],
                                   level_intervals=[["0", ".10"], [".20", ".30"]],
                                   cells=8, max_boxes=31))
    assert result["status"] == "conditional_incompatible"
    assert result["outer"] == result["inner"] == result["unknown"] == []
    assert_leaf_cover(result, (0, 4))


def test_work_exhaustion_preserves_all_unclassified_radii():
    result = corner.analyze(config(max_boxes=1, cells=1, radius_resolution=".001"))
    assert result["status"] == "unknown"
    assert result["budget_exhausted"] is True
    assert result["boxes_evaluated"] == 1
    assert result["classification_complete"] is False
    assert result["unknown"]
    assert intervals(result, "outer") == [(Fraction(0), Fraction(4))]
    assert_leaf_cover(result, (0, 4))


def test_coarse_gaussian_tails_remain_unknown_instead_of_claiming_exact_zero():
    result = corner.analyze(config(points=[["-100", "-100"]], blur_sigma=["1", "1"],
                                   radius_domain=["0", "0"], level_intervals=[["0", "0"]]))
    assert result["status"] == "unknown"
    assert result["inner"] == result["excluded"] == []
    assert in_union(result, "outer", 0)
    assert result["classification_complete"] is False
    assert_leaf_cover(result, (0, 0))


def test_numerical_failure_retains_the_radius_box_as_unknown(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ArithmeticError("independent injected enclosure failure")

    monkeypatch.setattr(corner, "_level_bounds", unavailable)
    result = corner.analyze(config())
    assert result["status"] == "unknown"
    assert result["inner"] == result["excluded"] == []
    assert result["unknown_reason_counts"]["numerical_enclosure"] >= 1
    assert intervals(result, "outer") == [(Fraction(0), Fraction(4))]
    assert_leaf_cover(result, (0, 4))


def test_model_enclosures_ignore_hostile_global_decimal_context():
    args = ((".4", "1.3"), (".5", "1.5"), "2.25")
    expected = corner.level_bounds(*args, cells=8)
    expected_analysis = corner.analyze(config(max_boxes=7, cells=2))
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_UP
        context.Emax, context.Emin = 2, -2
        for signal in context.traps:
            context.traps[signal] = True
        assert corner.level_bounds(*args, cells=8) == expected
        assert corner.analyze(config(max_boxes=7, cells=2)) == expected_analysis


def test_forty_digit_inputs_can_subdivide_beyond_the_external_input_precision_limit():
    raw = config(
        points=[["0.1234567890123456789012345678901234567890", ".5"]],
        radius_domain=["1.234567890123456789012345678901234567890",
                       "3.876543210987654321098765432109876543211"],
        level_intervals=[[".20", ".24"]], radius_resolution=".01",
        cells=4, max_boxes=7,
    )
    result = corner.analyze(raw)
    assert result["boxes_evaluated"] > 1
    assert_leaf_cover(result, map(Decimal, raw["radius_domain"]))


def test_parse_config_returns_a_dataclass_without_mutating_input():
    raw = config()
    before = repr(raw)
    assert is_dataclass(corner.parse_config(raw))
    assert repr(raw) == before


@pytest.mark.parametrize("change", [
    {"format": "another-format"}, {"version": 2}, {"coordinate_unit": "inch"},
    {"extra": "not admitted"}, {"points": []}, {"points": [["0", "0"]] * 17},
    {"points": [["0"]]}, {"level_intervals": []},
    {"level_intervals": [[".3", ".2"]]}, {"level_intervals": [["-.1", ".5"]]},
    {"level_intervals": [["0", "1.1"]]}, {"blur_sigma": ["0", "1"]},
    {"blur_sigma": ["-1", "1"]}, {"blur_sigma": ["1e-7", "1"]},
    {"blur_sigma": ["1000001", "1"]}, {"radius_domain": ["2", "1"]},
    {"radius_domain": ["-1", "2"]}, {"radius_resolution": "0"},
    {"radius_resolution": "-1"}, {"max_boxes": 0}, {"max_boxes": 513},
    {"cells": 0}, {"cells": 257}, {"points": [["NaN", "0"]]},
    {"points": [["Infinity", "0"]]}, {"points": [["1e13", "0"]]},
    {"points": [["1e-13", "0"]]},
    {"points": [["0.12345678901234567890123456789012345678901", "0"]]},
])
def test_malformed_or_out_of_scope_configuration_is_rejected(change):
    with pytest.raises((ValueError, TypeError)):
        corner.parse_config(config(**change))


def test_required_fields_and_aggregate_work_limit_are_enforced():
    raw = config()
    del raw["cells"]
    with pytest.raises((ValueError, TypeError)):
        corner.parse_config(raw)
    with pytest.raises((ValueError, TypeError)):
        corner.parse_config(config(points=[["0", "0"]] * 16,
                                   level_intervals=[["0", "1"]] * 16,
                                   cells=256, max_boxes=512))
