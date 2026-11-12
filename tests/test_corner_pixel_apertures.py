"""Independent numerical and set-accounting checks for known pixel apertures.

The erfc/Legendre oracle averages point probabilities directly over each
uniform axis and integrates the circular cutout in angle. It does not use the
production Gaussian antiderivative, CDF, renderer, or probability covers. Two
quadrature orders are development convergence checks, not certified error or
physical-accuracy bounds. Exact symmetry and rational joint-box accounting
exercise separate analytic and set-inclusion properties.
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


def oracle_level(aperture, sigma, radius, *, angular_order=96, aperture_order=32):
    """Normalized product-aperture mean via independent numerical integrals."""
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


def converged_level(aperture, sigma, radius):
    coarse = oracle_level(aperture, sigma, radius, angular_order=64, aperture_order=24)
    fine = oracle_level(aperture, sigma, radius, angular_order=128, aperture_order=48)
    assert abs(coarse - fine) < 2e-12
    return fine


def config(**changes):
    return {
        "format": "pictures-to-cad-corner-feasibility", "version": 3,
        "coordinate_unit": "px", "pixel_apertures": [[["0", "1"], ["0", "1"]]],
        "blur_sigma_intervals": [[".5", "1.5"], ["1", "2"]],
        "level_intervals": [[".1", ".2"]], "radius_domain": ["0", "4"],
        "radius_resolution": ".125", "blur_resolution": [".125", ".125"],
        "max_boxes": 31, "cells": 8, **changes,
    }


def dirac(point):
    return [[value, value] for value in point]


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
    """Exact intrinsic volume, containment, disjoint interiors and projection."""
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


@pytest.mark.parametrize("aperture", [
    [["0", "1"], ["0", "1"]],
    [["-.8", ".2"], [".3", "1.7"]],
    [["1.5", "2.5"], ["1.5", "2.5"]],
])
@pytest.mark.parametrize("radius", ["0", "1.25", "2.25"])
def test_bounds_cover_independent_uniform_means_at_interior_blurs(aperture, radius):
    bounded = pixels.aperture_level_bounds(aperture, [[".5", "1.1"], [".9", "1.7"]],
                                          radius, cells=16)
    assert 0 <= bounded.lo <= bounded.hi <= 1
    for sigma in itertools.product((.5, .7, 1.1), (.9, 1.2, 1.7)):
        reference = converged_level(aperture, sigma, radius)
        assert float(bounded.lo) - 2e-12 <= reference <= float(bounded.hi) + 2e-12


def test_symmetric_rectangles_have_exact_sharp_quarter_for_every_blur():
    aperture = [["-2", "2"], ["-.3", ".3"]]
    domains = [Interval(".000001", "1000000"), Interval(".000001", "1000000")]
    assert pixels.aperture_level_bounds(aperture, domains, "0", cells=1) == Interval.point(".25")
    raw = config(pixel_apertures=[aperture], radius_domain=["0", "0"],
                 level_intervals=[[".25", ".25"]], max_boxes=1, cells=1)
    result = pixels.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert result["classification_complete"] is True
    assert_joint_coverage(result, raw)


def test_nonunit_apertures_are_normalized_means_not_total_flux():
    aperture = [["-.5", "2.5"], [".2", "1.7"]]
    sigma, radius = (".7", "1.2"), "1.75"
    whole = converged_level(aperture, sigma, radius)
    left = converged_level([["-.5", ".5"], aperture[1]], sigma, radius)
    right = converged_level([[".5", "2.5"], aperture[1]], sigma, radius)
    assert abs(whole - (left + 2 * right) / 3) < 2e-12
    bounded = pixels.aperture_level_bounds(aperture, [[s, s] for s in sigma], radius, cells=64)
    assert float(bounded.lo) <= whole <= float(bounded.hi)
    # Its area is 4.5, so total flux is not the probability returned here.
    assert 4.5 * whole > float(bounded.hi)


@pytest.mark.parametrize("aperture", [
    [[".4", ".4"], ["-.2", "1.5"]],
    [["-.3", "1.2"], [".7", ".7"]],
])
def test_one_dirac_axis_keeps_the_other_axis_uniform(aperture):
    for radius in ("0", "2.25"):
        bounded = pixels.aperture_level_bounds(aperture, [[".5", ".5"], ["1.5", "1.5"]],
                                              radius, cells=64)
        reference = converged_level(aperture, (.5, 1.5), radius)
        assert float(bounded.lo) - 2e-12 <= reference <= float(bounded.hi) + 2e-12


@pytest.mark.parametrize("radius", ["0", "2.25"])
def test_two_dirac_axes_preserve_exact_version_two_bounds_and_analysis(radius):
    point, domains = (".4", "1.3"), [[".5", ".9"], ["1.1", "1.6"]]
    actual = pixels.aperture_level_bounds(dirac(point), domains, radius, cells=16)
    assert actual == point_model.parameter_level_bounds(point, domains, radius, cells=16)
    raw = config(pixel_apertures=[dirac(point)])
    old = {key: value for key, value in raw.items() if key != "pixel_apertures"}
    old.update(version=2, points=[list(point)])
    result, expected = pixels.analyze(raw), point_model.analyze(old)
    for key in expected.keys() - {"version", "assumptions"}:
        assert result[key] == expected[key]
    assert_joint_coverage(result, raw)


def test_shrinking_apertures_approach_the_point_without_changing_measure_at_finite_width():
    point = [[".4", ".4"], ["1.3", "1.3"]]
    small = [[".39999", ".40001"], ["1.29999", "1.30001"]]
    sigma, domains = (.5, 1.5), [[".5", ".5"], ["1.5", "1.5"]]
    reference = converged_level(point, sigma, 2.25)
    assert abs(converged_level(small, sigma, 2.25) - reference) < 1e-9
    original = pixels.aperture_level_bounds(point, domains, "2.25", cells=32)
    actual = pixels.aperture_level_bounds(small, domains, "2.25", cells=32)
    assert abs(float(original.lo - actual.lo)) < 1e-4
    assert abs(float(original.hi - actual.hi)) < 1e-4
    assert float(actual.lo) <= reference <= float(actual.hi)


def test_common_scaling_and_axis_swap_preserve_the_normalized_mean():
    aperture, domains = [["-.2", "1"], [".4", "1.8"]], [[".5", ".9"], ["1.1", "1.6"]]
    original = pixels.aperture_level_bounds(aperture, domains, "2.25", cells=16)
    scaled = pixels.aperture_level_bounds([["-2", "10"], ["4", "18"]],
                                         [["5", "9"], ["11", "16"]], "22.5", cells=16)
    for left, right in ((original.lo, scaled.lo), (original.hi, scaled.hi)):
        assert abs(Fraction(left) - Fraction(right)) < Fraction(1, 10**45)
    swapped = pixels.aperture_level_bounds(aperture[::-1], domains[::-1], "2.25", cells=16)
    assert max(original.lo, swapped.lo) <= min(original.hi, swapped.hi)
    assert abs(converged_level(aperture, (.7, 1.3), 2.25)
               - converged_level(aperture[::-1], (1.3, .7), 2.25)) < 2e-12


def test_known_interior_joint_truth_is_kept_with_three_uniform_observations():
    truth = (Decimal("2.25"), Decimal(".65"), Decimal("1.35"))
    apertures = [[["0", "1"], ["0", "1"]], [["1", "2"], ["0", "1"]],
                 [["0", "1"], ["1", "2"]]]
    centers = [Decimal(str(converged_level(a, truth[1:], truth[0]))) for a in apertures]
    bands = [[str(c - Decimal(".08")), str(c + Decimal(".08"))] for c in centers]
    raw = config(pixel_apertures=apertures, level_intervals=bands, radius_domain=["1.5", "3"],
                 blur_sigma_intervals=[[".5", ".9"], ["1.1", "1.6"]], cells=8, max_boxes=31)
    result = pixels.analyze(raw)
    kept = parameter_boxes(result, "accepted") + parameter_boxes(result, "unknown")
    assert any(contains(box, truth) for box in kept)
    assert not any(contains(box, truth) for box in parameter_boxes(result, "excluded"))
    for box in parameter_boxes(result, "accepted"):
        middle = [float((low + high) / 2) for low, high in box]
        for aperture, (low, high) in zip(apertures, bands):
            reference = converged_level(aperture, middle[1:], middle[0])
            assert float(low) <= reference <= float(high)
    assert_joint_coverage(result, raw)


# Frozen read-only development examples: the old point model is conditional on
# exact point observations, so its exclusions are not a soundness defect. These
# known uniform means deliberately use different observation assumptions.
FOOTPRINT_CASES = [
    pytest.param([".5", ".5"], "0", ["1", "1"],
                 [[".99", "1.01"], [".99", "1.01"]],
                 "0.46836666344571026", False, id="sharp-pixel-point-model-excludes"),
    pytest.param([".5", ".5"], "2.25", [".5", "1.5"],
                 [[".495", ".505"], ["1.485", "1.515"]],
                 "0.3525378979734415", True, id="rounded-pixel-point-model-retains-control"),
    pytest.param(["2", "2"], "2.25", [".5", "1.5"],
                 [[".495", ".505"], ["1.485", "1.515"]],
                 "0.894977011010492", False, id="rounded-pixel-point-model-excludes"),
]


@pytest.mark.parametrize("point,radius,sigma,domains,mean,old_retains", FOOTPRINT_CASES)
def test_known_pixel_footprints_retain_truth_and_preserve_point_model_controls(
        point, radius, sigma, domains, mean, old_retains):
    aperture = [[str(Decimal(p) - Decimal(".5")), str(Decimal(p) + Decimal(".5"))] for p in point]
    reference = converged_level(aperture, sigma, radius)
    assert abs(reference - float(mean)) < 2e-12
    center = converged_level(dirac(point), sigma, radius)
    assert center - reference > .006
    band = [[str(Decimal(mean) - Decimal(".00001")), str(Decimal(mean) + Decimal(".00001"))]]
    raw = config(pixel_apertures=[aperture], blur_sigma_intervals=domains,
                 level_intervals=band, radius_domain=["0", str(max(Decimal(2), 2 * Decimal(radius)))],
                 radius_resolution=".025", blur_resolution=[".005", ".005"], cells=32, max_boxes=127)
    old = {key: value for key, value in raw.items() if key != "pixel_apertures"}
    old.update(version=2, points=[point])
    original, actual = point_model.analyze(old), pixels.analyze(raw)
    truth = (Decimal(radius), *map(Decimal, sigma))
    assert any(low <= Fraction(truth[0]) <= high for low, high in radius_sets(original, "outer")) is old_retains
    assert any(contains(box, truth) for box in parameter_boxes(actual, "accepted")
               + parameter_boxes(actual, "unknown"))
    assert not any(contains(box, truth) for box in parameter_boxes(actual, "excluded"))
    assert_joint_coverage(original, raw)
    assert_joint_coverage(actual, raw)


def test_exact_center_observation_control_retains_its_true_radius():
    point, sigma, radius = [".5", ".5"], [".5", "1.5"], "2.25"
    center = Decimal(str(converged_level(dirac(point), sigma, radius)))
    raw = config(pixel_apertures=[dirac(point)], blur_sigma_intervals=[[s, s] for s in sigma],
                 level_intervals=[[str(center - Decimal(".00001")), str(center + Decimal(".00001"))]],
                 radius_domain=["0", "4.5"], radius_resolution=".025", cells=32, max_boxes=127)
    result = pixels.analyze(raw)
    assert any(low <= Fraction(Decimal(radius)) <= high for low, high in radius_sets(result, "outer"))
    assert_joint_coverage(result, raw)


def test_three_observations_require_one_common_blur_pair_even_when_individually_feasible():
    points = [["0", "1"], ["1", "0"], ["1", "1"]]
    apertures = [dirac(p) for p in points]
    raw = config(pixel_apertures=apertures, radius_domain=["0", "0"],
                 blur_sigma_intervals=[["1", "2"], ["1", "2"]],
                 level_intervals=[[".420", ".421"], [".420", ".421"], [".478", ".479"]],
                 blur_resolution=[".001", ".001"], cells=1, max_boxes=127)
    resolutions = [["1", ".001"], [".001", "1"], [".001", ".001"]]
    for aperture, level, resolution, sigma in zip(apertures, raw["level_intervals"], resolutions,
                                                  [(1, 1), (1, 1), (2, 2)]):
        assert float(level[0]) < converged_level(aperture, sigma, 0) < float(level[1])
        single = pixels.analyze({**raw, "pixel_apertures": [aperture], "level_intervals": [level],
                                 "blur_resolution": resolution})
        assert single["status"] == "conditional_compatible"
    result = pixels.analyze(raw)
    assert result["status"] == "conditional_incompatible"
    assert result["outer"] == []
    assert_joint_coverage(result, raw)


def test_positive_width_apertures_also_require_a_common_blur_witness():
    apertures = [[["-.5", ".5"], [".5", "1.5"]],
                 [[".5", "1.5"], ["-.5", ".5"]],
                 [[".5", "1.5"], [".5", "1.5"]]]
    # Frozen bands around distinct known blur witnesses, not fitted from output.
    bands = [["0.41525511818064925", "0.41625511818064925"],
             ["0.41525511818064925", "0.41625511818064925"],
             ["0.47510945265347526", "0.47610945265347526"]]
    raw = config(pixel_apertures=apertures, level_intervals=bands, radius_domain=["0", "0"],
                 blur_sigma_intervals=[["1", "2"], ["1", "2"]],
                 blur_resolution=[".001", ".001"], cells=1, max_boxes=127)
    for aperture, band, sigma in zip(apertures, bands, [("1", "1"), ("1", "1"), ("2", "2")]):
        reference = converged_level(aperture, sigma, 0)
        assert float(band[0]) < reference < float(band[1])
        witness = pixels.analyze({**raw, "pixel_apertures": [aperture], "level_intervals": [band],
                                  "blur_sigma_intervals": [[s, s] for s in sigma]})
        assert witness["status"] == "conditional_compatible"
    # Over the full blur domain the third single-observation search can exhaust
    # its budget. Its known witness must still survive; no unknown is a rejection.
    single_raw = {**raw, "pixel_apertures": [apertures[2]], "level_intervals": [bands[2]]}
    single = pixels.analyze(single_raw)
    assert single["status"] in ("unknown", "conditional_compatible")
    assert any(contains(box, (0, 2, 2)) for box in parameter_boxes(single, "accepted")
               + parameter_boxes(single, "unknown"))
    assert_joint_coverage(single, single_raw)
    result = pixels.analyze(raw)
    assert result["status"] == "conditional_incompatible"
    assert result["classification_complete"] is True
    assert result["outer"] == []
    assert_joint_coverage(result, raw)


def test_rejected_blur_boxes_cannot_remove_a_radius_with_another_valid_blur():
    raw = config(pixel_apertures=[dirac(["1", "0"])], radius_domain=["0", "0"],
                 blur_sigma_intervals=[["1", "3"], ["1", "1"]],
                 level_intervals=[[".39", ".41"]], blur_resolution=[".01", ".01"], cells=1, max_boxes=63)
    result = pixels.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert result["parameter_boxes"]["accepted"] and result["parameter_boxes"]["excluded"]
    assert radius_sets(result, "outer") == radius_sets(result, "inner") == [(Fraction(0), Fraction(0))]
    assert_joint_coverage(result, raw)


def test_all_levels_accept_the_whole_joint_prior_without_search():
    raw = config(level_intervals=[["0", "1"]], cells=1, max_boxes=1)
    result = pixels.analyze(raw)
    assert result["status"] == "conditional_compatible"
    assert result["classification_complete"] is True
    assert result["budget_exhausted"] is False
    assert result["boxes_evaluated"] == 1
    assert_joint_coverage(result, raw)


def test_work_budget_retains_every_queued_joint_box():
    raw = config(level_intervals=[[".3", ".4"]], cells=1, max_boxes=1)
    result = pixels.analyze(raw)
    assert result["status"] == "unknown"
    assert result["budget_exhausted"] is True
    assert result["boxes_evaluated"] == 1
    assert len(result["parameter_boxes"]["unknown"]) == 2
    assert result["unknown_reason_counts"]["work_budget"] == 2
    assert radius_sets(result, "outer") == [(Fraction(0), Fraction(4))]
    assert_joint_coverage(result, raw)


def test_numerical_enclosure_failure_retains_the_entire_prior(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ArithmeticError("independent injected aperture enclosure failure")

    monkeypatch.setattr(pixels, "_level_bounds", unavailable)
    raw = config()
    result = pixels.analyze(raw)
    assert result["status"] == "unknown"
    assert result["parameter_boxes"]["accepted"] == result["parameter_boxes"]["excluded"] == []
    assert result["unknown_reason_counts"] == {"numerical_enclosure": 1}
    assert_joint_coverage(result, raw)


def test_coarse_tail_probability_is_unknown_rather_than_exact_zero():
    raw = config(pixel_apertures=[[["-101", "-100"], ["-101", "-100"]]],
                 radius_domain=["0", "0"], blur_sigma_intervals=[["1", "2"], ["1", "2"]],
                 level_intervals=[["0", "0"]], blur_resolution=["1", "1"], cells=1)
    result = pixels.analyze(raw)
    assert result["status"] == "unknown"
    assert result["parameter_boxes"]["accepted"] == result["parameter_boxes"]["excluded"] == []
    assert_joint_coverage(result, raw)


def test_forty_digit_external_inputs_allow_more_precise_internal_midpoints():
    raw = config(pixel_apertures=[[["0.1234567890123456789012345678901234567890", ".5"], [".5", "1"]]],
                 radius_domain=["1.234567890123456789012345678901234567890",
                                "3.876543210987654321098765432109876543211"],
                 level_intervals=[[".20", ".24"]], cells=2, max_boxes=7,
                 radius_resolution=".01", blur_resolution=[".01", ".01"])
    result = pixels.analyze(raw)
    assert result["boxes_evaluated"] > 1
    assert_joint_coverage(result, raw)


def test_global_decimal_context_cannot_change_bounds_or_analysis():
    args = ([["-.2", "1"], [".4", "1.8"]], [[".5", ".9"], ["1.1", "1.6"]], "2.25")
    raw = config(cells=2, max_boxes=7)
    expected_level = pixels.aperture_level_bounds(*args, cells=8)
    expected_analysis = pixels.analyze(raw)
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_UP
        context.Emax, context.Emin = 2, -2
        for signal in context.traps:
            context.traps[signal] = True
        assert pixels.aperture_level_bounds(*args, cells=8) == expected_level
        assert pixels.analyze(raw) == expected_analysis


@pytest.mark.parametrize("change", [
    {"version": 2}, {"version": True}, {"points": [["0", "0"]]},
    {"point_boxes": [[["0", "1"], ["0", "1"]]]}, {"pixel_apertures": []},
    {"pixel_apertures": [[["0", "1"]]]}, {"pixel_apertures": [[["1", "0"], ["0", "1"]]]},
    {"pixel_apertures": [[["0", "1", "2"], ["0", "1"]]]},
    {"pixel_apertures": [[[0, "1"], ["0", "1"]]]},
    {"pixel_apertures": [[[.0, "1"], ["0", "1"]]]},
    {"pixel_apertures": [[[True, "1"], ["0", "1"]]]},
    {"pixel_apertures": [[["NaN", "1"], ["0", "1"]]]},
    {"pixel_apertures": [[["-Infinity", "1"], ["0", "1"]]]},
    {"pixel_apertures": [[["0", "1000001"], ["0", "1"]]]},
    {"pixel_apertures": [[["1e-13", "1"], ["0", "1"]]]},
    {"pixel_apertures": [[["0.12345678901234567890123456789012345678901", "1"], ["0", "1"]]]},
    {"pixel_apertures": [[["0", "1"], ["0", "1"]]] * 17},
    {"blur_sigma_intervals": [["0", "1"], ["1", "2"]]},
    {"blur_sigma_intervals": [["1e-7", "1"], ["1", "2"]]},
    {"blur_sigma_intervals": [["1", "1000001"], ["1", "2"]]},
    {"blur_sigma_intervals": [[1, "2"], ["1", "2"]]},
    {"blur_resolution": ["0", ".1"]}, {"blur_resolution": [".1"]},
    {"radius_domain": [0, "4"]}, {"radius_domain": ["4", "0"]},
    {"radius_resolution": "0"}, {"level_intervals": [[0, "1"]]},
    {"level_intervals": [["-.1", "1"]]}, {"level_intervals": []},
    {"max_boxes": True}, {"max_boxes": 513}, {"cells": True}, {"cells": 257},
    {"coordinate_unit": "inch"}, {"unknown_field": "refuse"},
])
def test_schema_refuses_invalid_apertures_and_implicit_inputs(change):
    with pytest.raises((ValueError, TypeError)):
        pixels.analyze(config(**change))


def test_all_fields_and_the_two_endpoint_resource_bound_are_required():
    for missing in config():
        raw = config()
        del raw[missing]
        with pytest.raises(ValueError):
            pixels.analyze(raw)
    with pytest.raises(ValueError, match="work limit"):
        pixels.analyze(config(pixel_apertures=[[["0", "1"], ["0", "1"]]] * 8,
                              level_intervals=[["0", "1"]] * 8, cells=64, max_boxes=65))


@pytest.mark.parametrize("aperture", [
    [[.0, "1"], ["0", "1"]], [["1", "0"], ["0", "1"]],
    [["0", "1000001"], ["0", "1"]], [["0", "1"]],
])
def test_public_bounds_refuse_malformed_apertures(aperture):
    with pytest.raises((ValueError, TypeError)):
        pixels.aperture_level_bounds(aperture, [["1", "1"], ["1", "1"]], "0")
