"""Independent crossing localization regressions for sampled linear-light profiles.

Exact Fraction calculations refer to the piecewise-linear function of the
supplied binary samples. They do not assert an optical or physical edge bound.
Unresolved level contacts remain missing measurements, not arbitrary locations.
"""

import math
from fractions import Fraction

import numpy as np
import pytest

from backend import sheet


def nearest(t, residual, searched=None):
    t, residual = np.asarray(t, dtype=float), np.asarray(residual, dtype=float)
    if searched is None:
        searched = np.ones(len(t) - 1, dtype=bool)
    return sheet._nearest_profile_crossing(t, residual, np.asarray(searched, dtype=bool))


def fraction_root(t0, t1, r0, r1):
    a, b, p, q = (Fraction(float(x)) for x in (t0, t1, r0, r1))
    return (a * q - b * p) / (q - p)


def exact_strict_roots(t, residual, searched):
    """Separate oracle for nonzero finite samples; no production interpolation."""
    return [fraction_root(t[i], t[i + 1], residual[i], residual[i + 1])
            for i, enabled in enumerate(searched)
            if enabled and ((residual[i] < 0 < residual[i + 1])
                            or (residual[i + 1] < 0 < residual[i]))]


def profile_image(changes):
    row = np.r_[np.zeros(16), np.full(17, 200.)]
    for index, value in changes.items():
        row[index] = value
    return np.tile(row, (4, 1))


def locate_image(image, direction):
    point = np.array([[16.5, 1.]])
    with np.errstate(invalid="ignore", over="ignore"):
        moved, keep = sheet.half_level_search(image, point, np.array([[direction, 0.]]), half=4.)
    return moved, keep, point


def test_actual_default_sampler_selects_the_closest_physical_crossing_in_both_directions():
    image = profile_image({15: 199., 16: 99., 17: 109.})
    # End medians are0 and200. Pixel-centre linear segments give exact local
    # roots -1/100 and1/10, plus the farther root100/199-2. The old left-index
    # ranking chose +.1 for normal+ and-.01 for normal-.
    roots = [Fraction(-1, 100), Fraction(1, 10), Fraction(100, 199) - 2]
    expected = min(roots, key=abs)
    assert expected == Fraction(-1, 100)
    for direction in (-1, 1):
        moved, keep, point = locate_image(image, direction)
        assert keep.tolist() == [True]
        assert abs(float(moved[0, 0] - point[0, 0]) - float(expected)) < 3e-14
        assert moved[0, 1] == point[0, 1]


@pytest.mark.parametrize("changes", [
    {15: 115., 16: 99., 17: 115.},  # Equal isolated roots at+/-.0625.
    {15: 120., 16: 100., 17: 120.},  # Nearest tangent contact, farther crossing.
    {15: 100., 16: 100., 17: 100.},  # A whole interval at the target level.
])
def test_actual_ambiguous_profile_is_rejected_and_input_point_is_unchanged(changes):
    image = profile_image(changes)
    for direction in (-1, 1):
        moved, keep, point = locate_image(image, direction)
        assert keep.tolist() == [False]
        np.testing.assert_array_equal(moved, point)
        np.testing.assert_array_equal(point, [[16.5, 1.]])


def test_actual_nonfinite_profile_cannot_become_a_verified_edge_after_normal_reversal():
    image = profile_image({14: 0., 15: -np.inf, 16: 101., 17: 200.})
    for direction in (-1, 1):
        moved, keep, point = locate_image(image, direction)
        assert keep.tolist() == [False]
        np.testing.assert_array_equal(moved, point)


def test_rejected_profiles_do_not_move_or_discard_independent_resolved_points():
    resolved = profile_image({15: 199., 16: 99., 17: 109.})
    ambiguous = profile_image({15: 115., 16: 99., 17: 115.})
    image = np.vstack([resolved, ambiguous])
    points = np.array([[16.5, 1.], [16.5, 6.]])
    saved = points.copy()
    moved, keep = sheet.half_level_search(image, points, np.array([[1., 0.], [1., 0.]]), half=4.)
    assert keep.tolist() == [True, False]
    assert abs(float(moved[0, 0]) - 16.49) < 3e-14
    np.testing.assert_array_equal(moved[1], saved[1])
    np.testing.assert_array_equal(points, saved)


@pytest.mark.parametrize("t,residual,expected", [
    ([-1, 1], [-1, 1], 0.),
    ([-1, 0, 1], [-1, 0, 1], 0.),
    ([-1, 0, 1], [1, 0, -1], 0.),
    ([-2, -1, 0, 1], [-2, 0, 1, 2], -1.),
    ([0, 1, 2], [-2, -1, 3], 1.25),
    ([-3, -.5, 2], [-2, -1, 4], 0.),
])
def test_verified_single_crossing_or_isolated_zero_is_localized_once(t, residual, expected):
    assert nearest(t, residual) == pytest.approx(expected, abs=1e-15)


@pytest.mark.parametrize("t,residual", [
    ([-1, 0, 1], [1, -1, 1]),  # Equally near strict crossings.
    ([-2, -1, 0, 1, 2], [-1, 1, 0, 1, 1]),  # Tangent nearest; do not jump farther.
    ([-3, -2, -1, 0, 1, 2, 3], [-1, -1, 0, 0, 1, 1, 1]),
    ([-2, -1, 0, 1, 2, 3], [-1, -1, -1, 0, 0, 1]),
    ([-2, -1, 0, 1, 2], [1, 0, 1, 0, -1]),  # Tangent ties a verified zero.
    ([-1, 0, 1], [0, 1, 2]),  # Closed search boundary lacks both sides.
    ([-1, 0, 1], [-2, -1, 0]),
    ([-1, 0, 1], [0, 0, 0]),
    ([-1, 0, 1], [1, 1, 1]),
])
def test_nearest_unresolved_contact_or_distinct_tie_has_no_localization(t, residual):
    assert math.isnan(nearest(t, residual))


@pytest.mark.parametrize("t,residual", [
    ([-3, -2, -1, 0, 1, 2, 3], [0, -2, -2, -.25, 1, 1, 1]),
    ([-2, -1, 0, 1, 2, 3, 4], [-2, -2, -.25, 1, 1, 0, 1]),
    ([-2, -1, 0, 1, 2, 3, 4], [-2, -2, -.25, 1, 0, 0, 1]),
])
def test_farther_boundary_tangent_or_plateau_does_not_hide_a_closer_verified_root(t, residual):
    assert nearest(t, residual) == pytest.approx(.2, abs=1e-15)


def test_distances_use_original_binary_samples_instead_of_rounded_float_interpolants():
    t = np.array([-2., -1., 0., 1., 2.])
    residual = np.array([-1., 1., -1., np.nextafter(1., math.inf), 1.])
    roots = exact_strict_roots(t, residual, np.ones(4, dtype=bool))
    expected = min(roots, key=abs)
    assert 0 < expected < Fraction(1, 2)
    # The naive denominator rounds to2, erasing the tiny strict ordering.
    assert residual[2] / (residual[2] - residual[3]) == .5
    actual = nearest(t, residual)
    assert actual > 0  # An arbitrary tolerance would reject this distinct minimum.
    assert abs(actual - float(expected)) <= math.ulp(.5)
    mirrored = nearest(-t[::-1], residual[::-1])
    assert mirrored < 0
    assert abs(actual + mirrored) <= math.ulp(.5)


@pytest.mark.parametrize("tiny", [1e-20, -1e-20])
def test_tiny_root_next_to_a_sample_node_survives_interpolation_and_mirroring(tiny):
    t = np.array([-.125, 0., .125])
    residual = np.array([-1., tiny, 1.])
    roots = exact_strict_roots(t, residual, np.ones(2, dtype=bool))
    assert len(roots) == 1
    expected = float(roots[0])
    assert expected != 0
    assert abs(expected) == pytest.approx(1.25e-21, rel=2e-15, abs=0)
    actual = nearest(t, residual)
    mirrored = nearest(-t[::-1], residual[::-1])
    # Computing the tiny barycentric weight as1-minus-the-large-weight rounds
    # it to0. Relative checks against the original binary-rational root expose
    # that cancellation; an ordinary pixel-scale absolute tolerance would not.
    assert actual != 0 and mirrored != 0
    assert actual == pytest.approx(expected, rel=2e-15, abs=0)
    assert mirrored == pytest.approx(-expected, rel=2e-15, abs=0)


@pytest.mark.parametrize("values", [[-1e308, 1e308], [1e308, -1e308],
                                    [-np.nextafter(0., 1.), np.nextafter(0., 1.)]])
def test_single_crossing_interpolation_avoids_overflow_and_sign_product_underflow(values):
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        assert nearest([-1, 1], values) == 0


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_nonfinite_values_at_any_searched_node_reject_the_profile(invalid):
    residual = [-2., -1., -.25, 1., invalid]
    assert math.isnan(nearest([-2, -1, 0, 1, 2], residual))
    t = [-2., -1., 0., 1., invalid]
    assert math.isnan(nearest(t, [-2, -1, -.25, 1, 2]))


def test_unsearched_nodes_and_segments_do_not_supply_roots_or_confirm_zero_contacts():
    assert math.isnan(nearest([-1, 1], [-1, 1], [False]))
    assert math.isnan(nearest([-1, 0, 1], [-1, 0, 1], [False, True]))
    # The first two samples participate in no searched segment. Their invalid
    # residuals are irrelevant to the finite root in the actual search region.
    assert nearest([-2, -1, 0, 1, 2], [np.nan, np.inf, -.25, 1, 2],
                   [False, False, True, True]) == pytest.approx(.2, abs=1e-15)


def test_adding_farther_verified_roots_preserves_the_nearest_one():
    original = nearest([-1, 0, 1], [-1, -1, 9])
    extended = nearest([-10, -9, -1, 0, 1, 9, 10], [-1, 1, -1, -1, 9, -1, 1])
    assert original == pytest.approx(.1, abs=1e-15)
    assert extended == pytest.approx(original, abs=1e-15)


def test_exact_strict_root_oracle_matches_random_profiles_and_mirror_contrast_scaling():
    rng = np.random.default_rng(20261112)
    t = np.arange(-4., 5.)
    for _ in range(128):
        residual = rng.integers(1, 1000, size=len(t)).astype(float)
        residual *= rng.choice([-1., 1.], size=len(t))
        searched = rng.random(len(t) - 1) > .15
        roots = exact_strict_roots(t, residual, searched)
        if not roots:
            assert math.isnan(nearest(t, residual, searched))
            continue
        distance = min(map(abs, roots))
        closest = [root for root in roots if abs(root) == distance]
        expected = None if len(closest) != 1 else float(closest[0])
        for scale in (.25, -1., 8.):
            actual = nearest(t, residual * scale, searched)
            mirror = nearest(-t[::-1], residual[::-1] * scale, searched[::-1])
            if expected is None:
                assert math.isnan(actual) and math.isnan(mirror)
            else:
                assert math.isfinite(actual) and math.isfinite(mirror)
                assert actual == pytest.approx(expected, abs=2e-15)
                assert mirror == pytest.approx(-expected, abs=2e-15)
