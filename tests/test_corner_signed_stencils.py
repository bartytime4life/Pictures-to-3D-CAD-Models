"""Independent regressions for known signed sampling functionals.

The erfc/Legendre oracle directly averages point responses over each aperture
and integrates the circular cutout in angle. It does not use production CDFs,
Gaussian antiderivatives, renderers, or probability covers. Convergence at two
orders is a development check, not a certified or physical error bound. Separate
component enclosures certify the frozen nonmonotonicity example, and exact
rational arithmetic checks joint-box coverage and existential projections.
"""

import itertools
import math
from decimal import ROUND_UP, Decimal, localcontext
from fractions import Fraction
from functools import lru_cache

import numpy as np
import pytest

from backend import corner_blur_domains as point_model
from backend import corner_pixel_apertures as pixels
from backend import corner_signed_stencils as signed
from backend import sheet
from backend.decimal_bounds import Interval


@lru_cache(maxsize=8)
def quadrature(order):
    return np.polynomial.legendre.leggauss(order)


def uniform_axis(axis, order):
    low, high = map(float, axis)
    if low == high:
        return [(low, 1.)]
    nodes, weights = quadrature(order)
    return [((low + high) / 2 + (high - low) * float(node) / 2, float(weight) / 2)
            for node, weight in zip(nodes, weights)]


def oracle_aperture(aperture, sigma, radius, *, angular_order=96, aperture_order=32):
    sx, sy = map(float, sigma)
    radius = float(radius)
    xs, ys = (uniform_axis(axis, aperture_order) for axis in aperture)

    def cdf(value):
        return .5 * math.erfc(-value / math.sqrt(2))

    wedge = (math.fsum(weight * cdf(x / sx) for x, weight in xs)
             * math.fsum(weight * cdf(y / sy) for y, weight in ys))
    if radius == 0:
        return wedge
    nodes, weights = quadrature(angular_order)
    terms = []
    for node, weight in zip(nodes, weights):
        theta = (float(node) + 1) * math.pi / 4
        x, height = radius * (1 - math.cos(theta)), radius * (1 - math.sin(theta))
        density = math.fsum(w * math.exp(-.5 * ((x - p) / sx) ** 2)
                            / (sx * math.sqrt(2 * math.pi)) for p, w in xs)
        vertical = math.fsum(w * (cdf((height - p) / sy) - cdf(-p / sy)) for p, w in ys)
        terms.append(float(weight) * math.pi / 4 * radius * math.sin(theta) * density * vertical)
    return wedge - math.fsum(terms)


def oracle_stencil(stencil, sigma, radius, *, angular_order=128, aperture_order=48):
    return math.fsum(float(term["weight"]) * oracle_aperture(
        term["pixel_aperture"], sigma, radius,
        angular_order=angular_order, aperture_order=aperture_order) for term in stencil)


def converged_stencil(stencil, sigma, radius):
    coarse = oracle_stencil(stencil, sigma, radius, angular_order=64, aperture_order=24)
    fine = oracle_stencil(stencil, sigma, radius, angular_order=128, aperture_order=48)
    assert abs(coarse - fine) < 2e-12
    return fine


def term(weight, aperture=None):
    return {"weight": weight, "pixel_aperture": aperture or [["0", "1"], ["0", "1"]]}


def dirac(x, y):
    return [[x, x], [y, y]]


def keys_four(y=".5"):
    return [term(w, [[str(Decimal(x) - Decimal(".5")), str(Decimal(x) + Decimal(".5"))],
                     [str(Decimal(y) - Decimal(".5")), str(Decimal(y) + Decimal(".5"))]])
            for x, w in zip((1, 2, 3, 4), ("-.0625", ".5625", ".5625", "-.0625"))]


def keys_sixteen():
    q = [Fraction(-1, 16), Fraction(9, 16), Fraction(9, 16), Fraction(-1, 16)]
    # Every product is dyadic, so these decimal strings are exact.
    return [term(str(Decimal((wx * wy).numerator) / Decimal((wx * wy).denominator)),
                 dirac(str(x), str(y)))
            for (x, wx), (y, wy) in itertools.product(zip((-1, 0, 1, 2), q), repeat=2)]


def config(**changes):
    return {
        "format": "pictures-to-cad-corner-feasibility", "version": 4,
        "coordinate_unit": "px", "sampling_stencils": [[term("1")]],
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
    assert result["parameter_order"] == ["radius", "sigma_x", "sigma_y"]
    assert "excluded" not in result
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
    assert sum(math.prod(box[i][1] - box[i][0] for i in active) for box in leaves) == math.prod(
        domain[i][1] - domain[i][0] for i in active)
    assert result["coverage_complete"] is True
    assert radius_sets(result, "inner") == projection(groups["accepted"])
    assert radius_sets(result, "outer") == projection(groups["accepted"] + groups["unknown"])


@pytest.mark.parametrize("stencil", [
    [term("-2", [["-.8", ".2"], [".3", "1.7"]])],
    [term("1.25"), term("-.75", [["1", "2"], ["-.5", ".5"]])],
    keys_four(),
])
def test_whole_radius_box_contains_independent_interior_blur_and_radius_values(stencil):
    bounded = signed.stencil_box_bounds(stencil, [[".5", "1.1"], [".9", "1.7"]],
                                        Interval("0", "3"), cells=16)
    for sigma in itertools.product((.5, .7, 1.1), (.9, 1.2, 1.7)):
        for radius in (0, .75, 1.5, 2.25, 3):
            reference = converged_stencil(stencil, sigma, radius)
            assert float(bounded.lo) - 2e-12 <= reference <= float(bounded.hi) + 2e-12


def test_actual_four_tap_keys_response_is_not_monotone_in_radius():
    stencil, sigma = keys_four(), [[".5", ".5"], [".5", ".5"]]
    values = [converged_stencil(stencil, (.5, .5), radius) for radius in (0, 1.5, 6)]
    assert values == pytest.approx([.8067734193179003, .8093927742160953, .1792737951018984], abs=2e-12)
    assert values[1] > max(values[0], values[2]) + .0026
    # Separate outward component covers certify strict separation too. These
    # component checks are distinct from the ordinary numerical oracle above.
    enclosures = []
    for radius in ("0", "1.5", "6"):
        total = Interval.point(0)
        for item in stencil:
            component = pixels.aperture_level_bounds(item["pixel_aperture"], sigma, radius, cells=256)
            total = total + Decimal(item["weight"]) * component
        enclosures.append(total)
    assert enclosures[1].lo > max(enclosures[0].hi, enclosures[2].hi) + Decimal(".0025")
    bounded = signed.stencil_box_bounds(stencil, sigma, Interval("0", "6"), cells=256)
    assert bounded.lo <= enclosures[1].lo <= enclosures[1].hi <= bounded.hi
    assert float(bounded.lo) <= values[1] <= float(bounded.hi)


def test_dyadic_keys_weights_reproduce_the_actual_float64_sampler():
    stencil = keys_four()
    for radius in (0, 1.5, 6):
        components = [oracle_aperture(item["pixel_aperture"], (.5, .5), radius,
                                      angular_order=256, aperture_order=96) for item in stencil]
        image = np.tile(np.array(components, dtype=np.float64), (3, 1))
        sampled = sheet.sample_keys(image, np.array([1.5]), np.array([1.]))
        expected = math.fsum(float(item["weight"]) * value for item, value in zip(stencil, components))
        assert sampled.dtype == np.float64
        assert abs(float(sampled[0]) - expected) < 2e-15
    # Edge replication clips TAP indices; it does not clamp the requested
    # coordinate or the result. At x=-.5 the coalesced weights are(17,-1)/16.
    edge = np.tile(np.array([0., 1.]), (3, 1))
    assert sheet.sample_keys(edge, np.array([-.5, 1.5]), np.array([1., 1.])).tolist() == [-.0625, 1.0625]


def test_frozen_signed_pixel_truth_survives_while_different_point_and_pixel_models_exclude_it():
    band = [[".8093827742160953", ".8094027742160953"]]
    raw = config(sampling_stencils=[keys_four()], blur_sigma_intervals=[[".5", ".5"], [".5", ".5"]],
                 level_intervals=band, radius_domain=["0", "6"], radius_resolution=".025",
                 blur_resolution=[".01", ".01"], cells=64, max_boxes=127)
    result = signed.analyze(raw)
    truth = (Fraction(3, 2), Fraction(1, 2), Fraction(1, 2))
    assert any(contains(box, truth) for box in parameter_boxes(result, "accepted")
               + parameter_boxes(result, "unknown"))
    assert not any(contains(box, truth) for box in parameter_boxes(result, "excluded"))
    assert_joint_coverage(result, raw)
    # These conditional models are valid for other observation assumptions.
    # Supplying the signed output as their observation is deliberately mismatched.
    old = {key: value for key, value in raw.items() if key != "sampling_stencils"}
    old.update(version=3, pixel_apertures=[[["2", "3"], ["0", "1"]]], cells=128, max_boxes=255)
    pixel_result = pixels.analyze(old)
    assert pixel_result["status"] == "conditional_incompatible"
    assert pixel_result["outer"] == []
    del old["pixel_apertures"]
    old.update(version=2, points=[["2.5", ".5"]])
    point_result = point_model.analyze(old)
    assert point_result["status"] == "unknown"
    assert point_result["inner"] == []
    assert not any(low <= truth[0] <= high for low, high in radius_sets(point_result, "outer"))


def test_sixteen_tap_signed_response_can_be_negative_and_cannot_be_probability_clipped():
    stencil = keys_sixteen()
    expected = [.5883398485737167, -.00685831396251]
    for radius, reference in zip((0, 6), expected):
        actual = converged_stencil(stencil, (.5, .5), radius)
        finer = oracle_stencil(stencil, (.5, .5), radius, angular_order=256, aperture_order=96)
        assert abs(actual - finer) < 2e-12
        assert abs(actual - reference) < 2e-12
        bounded = signed.stencil_box_bounds(stencil, [[".5", ".5"], [".5", ".5"]],
                                            Interval.point(str(radius)), cells=128)
        assert float(bounded.lo) <= actual <= float(bounded.hi)
    assert bounded.hi < 0


def test_negative_weights_reverse_whole_component_intervals():
    aperture, domains = [["0", "1"], ["0", "1"]], [[".5", ".9"], ["1.1", "1.6"]]
    low_radius = pixels.aperture_level_bounds(aperture, domains, "0", cells=32)
    high_radius = pixels.aperture_level_bounds(aperture, domains, "3", cells=32)
    component = Interval(high_radius.lo, low_radius.hi)
    actual = signed.stencil_box_bounds([term("-2", aperture)], domains, Interval("0", "3"), cells=32)
    assert actual == -2 * component
    for radius in (0, 1, 2, 3):
        reference = converged_stencil([term("-2", aperture)], (.7, 1.3), radius)
        assert float(actual.lo) <= reference <= float(actual.hi)


@pytest.mark.parametrize("weight", ["2", "-2"])
def test_arbitrary_gains_can_produce_levels_outside_the_probability_range(weight):
    stencil = [term(weight, dirac("1", "1"))]
    value = converged_stencil(stencil, (1, 1), 0)
    assert value > 1 if Decimal(weight) > 0 else value < 0
    bounded = signed.stencil_box_bounds(stencil, [["1", "1"], ["1", "1"]], Interval.point(0), cells=1)
    # The ordinary erfc value is not a 60-digit enclosure oracle; even a sharp
    # quadrant differs from the Decimal reference by a binary rounding unit.
    assert float(bounded.lo) - 2e-12 <= value <= float(bounded.hi) + 2e-12
    band = [[str(Decimal(str(value)) - Decimal(".00001")), str(Decimal(str(value)) + Decimal(".00001"))]]
    raw = config(sampling_stencils=[stencil], blur_sigma_intervals=[["1", "1"], ["1", "1"]],
                 radius_domain=["0", "0"], level_intervals=band, max_boxes=1, cells=1)
    result = signed.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert_joint_coverage(result, raw)


def test_known_signed_range_contains_the_box_and_metadata_are_exact():
    stencil = [term("1.25"), term("-.75", dirac("1", "1"))]
    bounded = signed.stencil_box_bounds(stencil, [[".000001", "1000000"]] * 2,
                                        Interval("0", "1000000"), cells=1)
    assert Decimal("-.75") <= bounded.lo <= bounded.hi <= Decimal("1.25")
    raw = config(sampling_stencils=[stencil], level_intervals=[["-.75", "1.25"]], max_boxes=1, cells=1)
    result = signed.analyze(raw)
    assert result["status"] == "conditional_compatible"
    summary = result["stencil_summaries"][0]
    assert {key: Fraction(Decimal(summary[key])) for key in
            ("weight_sum", "negative_sum", "positive_sum", "l1")} == {
                "weight_sum": Fraction(1, 2), "negative_sum": Fraction(-3, 4),
                "positive_sum": Fraction(5, 4), "l1": Fraction(2)}
    assert summary["constant_preserving"] is False
    assert summary["terms"] == summary["nonzero_terms"] == 2
    assert_joint_coverage(result, raw)


def test_duplicate_opposite_terms_retain_their_zero_truth_without_implicit_normalization():
    stencil = [term("1"), term("-1")]
    bounded = signed.stencil_box_bounds(stencil, [[".5", "1.5"], ["1", "2"]], Interval("0", "4"), cells=8)
    assert bounded.lo <= 0 <= bounded.hi
    raw = config(sampling_stencils=[stencil], level_intervals=[["0", "0"]], cells=1, max_boxes=1)
    result = signed.analyze(raw)
    assert result["status"] in ("unknown", "conditional_compatible")
    assert result["outer"] == [["0", "4"]]
    summary = result["stencil_summaries"][0]
    assert Decimal(summary["weight_sum"]) == 0
    assert Decimal(summary["l1"]) == 2
    assert summary["constant_preserving"] is False
    assert_joint_coverage(result, raw)


def test_all_zero_stencils_are_exact_zero_without_evaluating_apertures(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ArithmeticError("a zero coefficient must not request a model evaluation")

    monkeypatch.setattr(pixels, "_level_bounds", unavailable)
    stencil = [term("0"), term("-0.0", dirac("-100", "100"))]
    assert signed.stencil_box_bounds(stencil, [["1", "2"]] * 2, Interval("0", "4"), cells=256) == Interval.point(0)
    raw = config(sampling_stencils=[stencil], level_intervals=[["0", "0"]], cells=256, max_boxes=512)
    result = signed.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert result["classification_complete"] is True
    assert result["stencil_summaries"][0]["nonzero_terms"] == 0
    assert_joint_coverage(result, raw)
    incompatible = signed.analyze({**raw, "level_intervals": [[".01", ".02"]]})
    assert incompatible["status"] == "conditional_incompatible"


@pytest.mark.parametrize("aperture", [[["0", "1"], ["0", "1"]], dirac(".4", "1.3")])
def test_positive_unit_stencils_preserve_exact_version_three_bounds_and_analysis(aperture):
    domains = [[".5", ".9"], ["1.1", "1.6"]]
    for radius in ("0", "2.25"):
        assert signed.stencil_box_bounds([term("1", aperture)], domains, Interval.point(radius), cells=16) == (
            pixels.aperture_level_bounds(aperture, domains, radius, cells=16))
    raw = config(sampling_stencils=[[term("1", aperture)]])
    old = {key: value for key, value in raw.items() if key != "sampling_stencils"}
    old.update(version=3, pixel_apertures=[aperture])
    actual, expected = signed.analyze(raw), pixels.analyze(old)
    for key in ("status", "inner", "outer", "parameter_boxes", "parameter_order", "parameter_domain",
                "coverage_complete", "classification_complete", "boxes_evaluated", "budget_exhausted",
                "unknown_reason_counts", "prior_ceiling_reached"):
        assert actual[key] == expected[key]
    assert_joint_coverage(actual, raw)


def test_one_common_blur_pair_must_explain_every_negative_observation():
    stencils = [[term("-1", dirac(x, y))] for x, y in [("0", "1"), ("1", "0"), ("1", "1")]]
    raw = config(sampling_stencils=stencils, radius_domain=["0", "0"],
                 blur_sigma_intervals=[["1", "2"], ["1", "2"]],
                 level_intervals=[["-.421", "-.420"], ["-.421", "-.420"], ["-.479", "-.478"]],
                 blur_resolution=[".001", ".001"], cells=1, max_boxes=127)
    resolutions = [["1", ".001"], [".001", "1"], [".001", ".001"]]
    for stencil, level, resolution, sigma in zip(stencils, raw["level_intervals"], resolutions,
                                                [(1, 1), (1, 1), (2, 2)]):
        assert float(level[0]) < converged_stencil(stencil, sigma, 0) < float(level[1])
        single = signed.analyze({**raw, "sampling_stencils": [stencil], "level_intervals": [level],
                                 "blur_resolution": resolution})
        assert single["status"] == "conditional_compatible"
    result = signed.analyze(raw)
    assert result["status"] == "conditional_incompatible"
    assert result["outer"] == []
    assert_joint_coverage(result, raw)


def test_interior_common_radius_and_blur_truth_survives_three_signed_stencils():
    truth = (Decimal("1.5"), Decimal(".55"), Decimal(".65"))
    stencils = [keys_four(y) for y in (".5", "1.5", "2.5")]
    centers = [Decimal(str(converged_stencil(s, truth[1:], truth[0]))) for s in stencils]
    bands = [[str(c - Decimal(".03")), str(c + Decimal(".03"))] for c in centers]
    raw = config(sampling_stencils=stencils, level_intervals=bands, radius_domain=["1", "2"],
                 blur_sigma_intervals=[[".5", ".6"], [".6", ".7"]], cells=8, max_boxes=31)
    result = signed.analyze(raw)
    kept = parameter_boxes(result, "accepted") + parameter_boxes(result, "unknown")
    assert any(contains(box, truth) for box in kept)
    assert not any(contains(box, truth) for box in parameter_boxes(result, "excluded"))
    for box in parameter_boxes(result, "accepted"):
        middle = [float((low + high) / 2) for low, high in box]
        for stencil, (low, high) in zip(stencils, bands):
            reference = converged_stencil(stencil, middle[1:], middle[0])
            assert float(low) <= reference <= float(high)
    assert_joint_coverage(result, raw)


def test_work_exhaustion_retains_every_queued_joint_box():
    raw = config(sampling_stencils=[keys_four()], level_intervals=[[".8", ".81"]], cells=1, max_boxes=1)
    result = signed.analyze(raw)
    assert result["status"] == "unknown"
    assert result["budget_exhausted"] is True
    assert result["boxes_evaluated"] == 1
    assert len(result["parameter_boxes"]["unknown"]) == 2
    assert radius_sets(result, "outer") == [(Fraction(0), Fraction(4))]
    assert_joint_coverage(result, raw)


def test_failed_component_enclosure_retains_the_whole_joint_prior(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ArithmeticError("independent injected component enclosure failure")

    monkeypatch.setattr(pixels, "_level_bounds", unavailable)
    raw = config(sampling_stencils=[keys_four()])
    result = signed.analyze(raw)
    assert result["status"] == "unknown"
    assert result["unknown_reason_counts"] == {"numerical_enclosure": 1}
    assert result["parameter_boxes"]["accepted"] == result["parameter_boxes"]["excluded"] == []
    assert_joint_coverage(result, raw)


def test_l1_and_constant_preservation_use_exact_sums_even_under_hostile_context():
    near_two = "2.000000000000000000000000000000000000001"
    below_two = "-1.999999999999999999999999999999999999999"
    valid = config(sampling_stencils=[[term(near_two), term(below_two)]],
                   level_intervals=[["-4", "4"]], cells=1, max_boxes=1)
    almost_one = {**valid, "sampling_stencils": [[term(near_two), term("-1")]]}
    invalid = {**valid, "sampling_stencils": [[term(near_two), term("-2")]]}
    expected = signed.analyze(valid)
    expected_almost = signed.analyze(almost_one)
    summary = expected["stencil_summaries"][0]
    assert Fraction(Decimal(summary["l1"])) == 4
    assert Fraction(Decimal(summary["weight_sum"])) == Fraction(2, 10**39)
    assert expected_almost["stencil_summaries"][0]["constant_preserving"] is False
    exact_one = signed.analyze({**valid, "sampling_stencils": [[term("2"), term("-1")]]})
    assert exact_one["stencil_summaries"][0]["constant_preserving"] is True
    with pytest.raises(ValueError):
        signed.analyze(invalid)
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_UP
        context.Emax, context.Emin = 2, -2
        for signal in context.traps:
            context.traps[signal] = True
        assert signed.analyze(valid) == expected
        assert signed.analyze(almost_one) == expected_almost
        with pytest.raises(ValueError):
            signed.analyze(invalid)


def test_forty_digit_geometry_and_hostile_context_do_not_change_internal_partitioning():
    aperture = [["0.1234567890123456789012345678901234567890", ".5"], [".5", "1"]]
    stencil = [term("1.25", aperture), term("-.25", dirac("1", "1"))]
    raw = config(sampling_stencils=[stencil],
                 radius_domain=["1.234567890123456789012345678901234567890",
                                "3.876543210987654321098765432109876543211"],
                 radius_resolution=".01", blur_resolution=[".01", ".01"],
                 level_intervals=[[".20", ".24"]], cells=2, max_boxes=7)
    domains, radius = [[".5", ".9"], ["1.1", "1.6"]], Interval("0", "3")
    expected_level = signed.stencil_box_bounds(stencil, domains, radius, cells=8)
    expected = signed.analyze(raw)
    assert expected["boxes_evaluated"] > 1
    assert_joint_coverage(expected, raw)
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_UP
        context.Emax, context.Emin = 2, -2
        for signal in context.traps:
            context.traps[signal] = True
        assert signed.stencil_box_bounds(stencil, domains, radius, cells=8) == expected_level
        assert signed.analyze(raw) == expected


@pytest.mark.parametrize("change", [
    {"version": 3}, {"version": True}, {"points": [["0", "0"]]},
    {"pixel_apertures": [[["0", "1"], ["0", "1"]]]}, {"sampling_stencils": []},
    {"sampling_stencils": [[]]}, {"sampling_stencils": [term("1")]},
    {"sampling_stencils": [[{"weight": "1"}]]},
    {"sampling_stencils": [[{"pixel_aperture": [["0", "1"], ["0", "1"]]}]]},
    {"sampling_stencils": [[{**term("1"), "unknown": "refuse"}]]},
    {"sampling_stencils": [[term(1)]]}, {"sampling_stencils": [[term(1.)]]},
    {"sampling_stencils": [[term(True)]]}, {"sampling_stencils": [[term("NaN")]]},
    {"sampling_stencils": [[term("Infinity")]]}, {"sampling_stencils": [[term("1e-13")]]},
    {"sampling_stencils": [[term("4.000000000001")]]},
    {"sampling_stencils": [[term("1", [["1", "0"], ["0", "1"]])]]},
    {"sampling_stencils": [[term("1", [[0, "1"], ["0", "1"]])]]},
    {"sampling_stencils": [[term("1", [["0", "1000001"], ["0", "1"]])]]},
    {"sampling_stencils": [[term("0")]] * 17}, {"sampling_stencils": [[term("0")] * 257]},
    {"blur_sigma_intervals": [["0", "1"], ["1", "2"]]},
    {"blur_sigma_intervals": [["1e-7", "1"], ["1", "2"]]},
    {"blur_resolution": ["0", ".1"]}, {"radius_domain": ["4", "0"]},
    {"radius_resolution": "0"}, {"level_intervals": [["-4.000000000001", "0"]]},
    {"level_intervals": [["0", "4.000000000001"]]}, {"level_intervals": [[0, "1"]]},
    {"max_boxes": True}, {"max_boxes": 513}, {"cells": True}, {"cells": 257},
    {"coordinate_unit": "inch"}, {"unknown_field": "refuse"},
])
def test_strict_schema_refuses_implicit_or_out_of_domain_inputs(change):
    with pytest.raises((ValueError, TypeError)):
        signed.analyze(config(**change))


def test_all_fields_and_aggregate_nonzero_term_work_limit_are_required():
    for missing in config():
        raw = config()
        del raw[missing]
        with pytest.raises(ValueError):
            signed.analyze(raw)
    # 256 nonzero terms at1/64 each have exact L1=4. Their aggregate work
    # hits the allowed limit at128cells and crosses it at129cells.
    raw = config(sampling_stencils=[[term(".015625")] * 256], max_boxes=1, cells=128)
    signed.parse_config(raw)
    with pytest.raises(ValueError, match="work limit"):
        signed.parse_config({**raw, "cells": 129})
    across = config(sampling_stencils=[[term(".015625")] * 128] * 2,
                    level_intervals=[["0", "1"]] * 2, max_boxes=1, cells=129)
    with pytest.raises(ValueError, match="work limit"):
        signed.parse_config(across)
    # Zero terms count toward the finite input-size cap, but require no model
    # evaluations and therefore do not consume the nonzero-term work allowance.
    zeros = config(sampling_stencils=[[term("0")] * 256] * 16, level_intervals=[["0", "0"]] * 16,
                   cells=256, max_boxes=512)
    result = signed.analyze(zeros)
    assert result["status"] == "conditional_compatible"
    assert_joint_coverage(result, zeros)


def test_two_stage_keys_composition_exercises_the_raw_256_term_work_boundary():
    q = [Fraction(-1, 16), Fraction(9, 16), Fraction(9, 16), Fraction(-1, 16)]
    stencil = []
    for (i, wi), (j, wj), (k, wk), (ell, well) in itertools.product(zip((-1, 0, 1, 2), q), repeat=4):
        weight = wi * wj * wk * well
        stencil.append(term(str(Decimal(weight.numerator) / Decimal(weight.denominator)),
                            dirac(str(i + k), str(j + ell))))
    assert len(stencil) == 256
    # At radius0 the oracle reduces to independent erfc values at point samples;
    # no cutout quadrature or production evaluator enters this reference value.
    reference = converged_stencil(stencil, (.5, .5), 0)
    center = Decimal(str(reference))
    raw = config(sampling_stencils=[stencil], radius_domain=["0", "0"],
                 blur_sigma_intervals=[[".5", ".5"], [".5", ".5"]],
                 level_intervals=[[str(center - Decimal(".00000001")), str(center + Decimal(".00000001"))]],
                 cells=8, max_boxes=16)
    result = signed.analyze(raw)
    assert result["status"] == "conditional_compatible"
    summary = result["stencil_summaries"][0]
    assert summary["terms"] == summary["nonzero_terms"] == 256
    assert Fraction(Decimal(summary["weight_sum"])) == 1
    assert Fraction(Decimal(summary["l1"])) == Fraction(625, 256)
    assert result["aperture_evaluations"] == 49
    assert_joint_coverage(result, raw)
    with pytest.raises(ValueError, match="work limit"):
        signed.analyze({**raw, "max_boxes": 17})


@pytest.mark.parametrize("stencil", [[], [term(True)], [term(1.)], [term("NaN")],
                                           [term("4.000000000001")], [{**term("1"), "other": "refuse"}]])
def test_public_bounds_refuse_malformed_stencils(stencil):
    with pytest.raises((ValueError, TypeError)):
        signed.stencil_box_bounds(stencil, [["1", "1"], ["1", "1"]], Interval("0", "1"))
