"""Independent elementary areas and finite-source grid invariants.

No synthetic renderer, Gaussian operator or production contour generator is used.
These tests qualify the declared area model, not a camera or acquisition inverse.
"""

import math
from itertools import pairwise

import numpy as np
import pytest

from backend import finite_aperture as aperture


def area(bounds, *, centre=(0, 0), radius=1, fraction=1, normal=(1, 0)):
    return aperture.segment_rectangle_area(centre, radius, fraction, normal, bounds)


def segment_area(radius, fraction):
    return radius**2 * (
        math.pi - math.acos(fraction) + fraction * math.sqrt((1 - fraction) * (1 + fraction))
    )


def positive_slice_area(bounds, *, centre, radius, fraction, normal, order):
    """Independent positive vertical-slice integral, with known breakpoints.

    x=Cx+R*sin(theta) removes the disk endpoint square root. The rectangle,
    chord/rectangle and chord/circle intersections split every change of active
    vertical bound. Panels span at most pi/32; only then is a fixed GL rule used.
    No Green edge integral, exact-predicate helper or rasterizer is called.
    """
    cx, cy = centre
    nx, ny = normal
    length = math.hypot(nx, ny)
    nx, ny = nx / length, ny / length
    x0, y0, x1, y1 = bounds
    lo, hi = max(x0, cx - radius), min(x1, cx + radius)
    if ny == 0:
        cut = cx + radius * fraction / nx
        if nx > 0:
            hi = min(hi, cut)
        else:
            lo = max(lo, cut)
    if lo >= hi:
        return 0.0
    cuts = [lo, hi]
    for y in (y0, y1):
        offset = y - cy
        if abs(offset) < radius:
            reach = math.sqrt((radius - abs(offset)) * (radius + abs(offset)))
            cuts.extend((cx - reach, cx + reach))
        if nx != 0:
            cuts.append(cx + (radius * fraction - ny * offset) / nx)
    half = math.sqrt((1 - fraction) * (1 + fraction))
    cuts.extend(
        (cx + radius * (fraction * nx - half * ny), cx + radius * (fraction * nx + half * ny))
    )
    angles = sorted(
        {math.asin(max(-1.0, min(1.0, (x - cx) / radius))) for x in cuts if lo <= x <= hi}
    )
    nodes, weights = np.polynomial.legendre.leggauss(order)
    pieces = []
    for left, right in pairwise(angles):
        panels = max(1, math.ceil((right - left) / (math.pi / 32)))
        for panel in range(panels):
            a = left + (right - left) * panel / panels
            b = left + (right - left) * (panel + 1) / panels
            midpoint, width = (a + b) / 2, (b - a) / 2
            terms = []
            for node, weight in zip(nodes, weights, strict=True):
                theta = midpoint + width * float(node)
                x = cx + radius * math.sin(theta)
                reach = radius * math.cos(theta)
                lower, upper = max(y0, cy - reach), min(y1, cy + reach)
                if ny != 0:
                    chord = cy + (radius * fraction - nx * (x - cx)) / ny
                    if ny > 0:
                        upper = min(upper, chord)
                    else:
                        lower = max(lower, chord)
                terms.append(float(weight) * max(0.0, upper - lower) * reach)
            pieces.append(width * math.fsum(terms))
    return math.fsum(pieces)


@pytest.mark.parametrize("bounds", [(0, 0, 2, 2), (-2, 0, 0, 2), (-2, -2, 0, 0), (0, -2, 2, 0)])
def test_quarter_disk(bounds):
    assert area(bounds) == pytest.approx(math.pi / 4, abs=3e-15)


def test_half_disk_and_chord_rectangle():
    assert area((-2, -2, 2, 2), fraction=0) == pytest.approx(math.pi / 2, abs=4e-15)
    assert area((-1, -1, 1, 1), radius=10, fraction=0) == 2


def test_disk_inside_pixel_and_pixel_inside_disk():
    assert area((-1, -1, 1, 1), centre=(0.125, -0.25), radius=0.25) == pytest.approx(
        math.pi / 16, abs=2e-15
    )
    assert area((-0.25, -0.5, 0.25, 0.5), radius=2) == 0.5


@pytest.mark.parametrize("fraction", [-1, -0.8, -0.4, 0, 0.25, 0.8, 1])
def test_complete_segment_matches_elementary_area(fraction):
    actual = area(
        (-4, -5, 6, 4), centre=(1.25, -0.75), radius=2.7, fraction=fraction, normal=(0.6, 0.8)
    )
    assert actual == pytest.approx(segment_area(2.7, fraction), abs=3e-13)


@pytest.mark.parametrize("fraction", [-0.7, 0, 0.2, 0.8])
@pytest.mark.parametrize("normal", [(1, 0), (0.6, 0.8), (-0.8, 0.6)])
def test_complement_partitions_the_same_clipped_disk(fraction, normal):
    bounds = (-0.8, -0.7, 0.9, 0.6)
    left = area(bounds, fraction=fraction, normal=normal)
    right = area(bounds, fraction=-fraction, normal=tuple(-x for x in normal))
    assert left + right == pytest.approx(area(bounds), abs=2e-14)


def test_partition_of_rectangle_is_additive():
    settings = {"centre": (0.25, -0.125), "radius": 1.25, "fraction": 0.2, "normal": (0.6, 0.8)}
    whole = area((-2, -2, 2, 2), **settings)
    pieces = [
        area((x, y, x + 0.5, y + 0.5), **settings)
        for y in np.arange(-2, 2, 0.5)
        for x in np.arange(-2, 2, 0.5)
    ]
    assert math.fsum(pieces) == pytest.approx(whole, abs=3e-14)


def test_local_translation_does_not_change_circle_arithmetic():
    base = area(
        (-0.75, -0.5, 0.5, 1), centre=(0.25, -0.125), radius=1.25, fraction=0.25, normal=(0.6, 0.8)
    )
    translated = area(
        (1023.25, -2048.5, 1024.5, -2047),
        centre=(1024.25, -2048.125),
        radius=1.25,
        fraction=0.25,
        normal=(0.6, 0.8),
    )
    assert translated == base


def test_reflection_and_axis_swap_preserve_area():
    settings = {"centre": (0.25, -0.125), "radius": 1.25, "fraction": 0.25, "normal": (0.6, 0.8)}
    original = area((-0.75, -0.5, 0.5, 1), **settings)
    reflected = area(
        (-0.5, -0.5, 0.75, 1),
        centre=(-0.25, -0.125),
        radius=1.25,
        fraction=0.25,
        normal=(-0.6, 0.8),
    )
    swapped = area(
        (-0.5, -0.75, 1, 0.5), centre=(-0.125, 0.25), radius=1.25, fraction=0.25, normal=(0.8, 0.6)
    )
    assert reflected == pytest.approx(original, abs=1e-14)
    assert swapped == pytest.approx(original, abs=1e-14)


def test_tangent_and_root_endpoint_contacts_have_no_spurious_area():
    assert area((1, -0.5, 2, 0.5)) == 0
    assert area((-2, -0.5, -1, 0.5)) == 0
    assert area((-0.5, 1, 0.5, 2)) == 0
    assert area((0, 0, 1, 1)) == pytest.approx(math.pi / 4, abs=3e-15)
    assert area((-1, -1, 1, 1), fraction=-1) == 0


def test_near_tangency_is_bounded_without_a_false_full_cell():
    left = math.nextafter(1.0, 0.0)
    actual = area((left, -0.5, 2, 0.5))
    assert 0 <= actual <= 1 - left


def test_rotated_grid_coverage_sums_to_the_elementary_segment_area():
    angle = math.radians(37)
    values = aperture.segment_cell_coverage(
        centre=(0.23, -0.19),
        radius=2.7,
        fraction=-0.4,
        normal=(math.cos(angle), math.sin(angle)),
        shape=(13, 13),
        origin=(-3, -3),
        pitch=0.5,
    )
    assert values.dtype == np.float64
    assert np.isfinite(values).all() and ((0 <= values) & (values <= 1)).all()
    assert math.fsum(map(float, values.flat)) * 0.25 == pytest.approx(
        segment_area(2.7, -0.4), abs=2e-12
    )


def test_grid_uses_origin_as_cell_centre_and_exact_local_offsets():
    options = {
        "centre": (0.25, -0.125),
        "radius": 0.7,
        "fraction": 0.2,
        "normal": (0.6, 0.8),
        "shape": (8, 9),
        "origin": (-0.25, -0.5),
        "pitch": 0.125,
    }
    baseline = aperture.segment_cell_coverage(**options)
    shifted = aperture.segment_cell_coverage(
        **{**options, "centre": (1e8 + 0.25, -1e8 - 0.125), "origin": (1e8 - 0.25, -1e8 - 0.5)}
    )
    np.testing.assert_array_equal(shifted, baseline)
    expected = (
        area(
            (-0.3125, -0.5625, -0.1875, -0.4375),
            centre=options["centre"],
            radius=0.7,
            fraction=0.2,
            normal=(0.6, 0.8),
        )
        / 0.125**2
    )
    assert baseline[0, 0] == pytest.approx(expected, abs=2e-15)


@pytest.mark.parametrize(
    "bounds,settings",
    [
        ((0.3, 0.2, 1.2, 1.1), {"centre": (0, 0), "radius": 1, "fraction": 1, "normal": (1, 0)}),
        (
            (-1.25, -0.5, 0.75, 0.5),
            {"centre": (0, 0), "radius": 1, "fraction": 0, "normal": (0, 1)},
        ),
        (
            (-2.5, -1.5, -1.5, -0.5),
            {
                "centre": (0.23, -0.19),
                "radius": 2.7,
                "fraction": -0.4,
                "normal": (math.cos(math.radians(37)), math.sin(math.radians(37))),
            },
        ),
        (
            (-0.3, -2.4, 0.7, -1.4),
            {
                "centre": (0.23, -0.19),
                "radius": 2.7,
                "fraction": -0.4,
                "normal": (math.cos(math.radians(37)), math.sin(math.radians(37))),
            },
        ),
        (
            (-0.3, -0.6, 0.4, 0.1),
            {
                "centre": (0.125, -0.25),
                "radius": 0.4,
                "fraction": 0.17,
                "normal": (math.cos(math.radians(127)), math.sin(math.radians(127))),
            },
        ),
        (
            (-17, -0.25, -16, 0.75),
            {
                "centre": (0.37, 0.29),
                "radius": 17.3,
                "fraction": 0.91,
                "normal": (math.cos(math.radians(31)), math.sin(math.radians(31))),
            },
        ),
    ],
)
def test_independent_positive_area_orders_and_green_agree(bounds, settings):
    low = positive_slice_area(bounds, **settings, order=48)
    high = positive_slice_area(bounds, **settings, order=96)
    assert abs(low - high) <= 1e-11
    assert abs(area(bounds, **settings) - high) <= 2e-11


@pytest.mark.parametrize(
    "name,value",
    [
        ("centre", (True, 0)),
        ("centre", (math.nan, 0)),
        ("radius", True),
        ("radius", 0),
        ("radius", math.inf),
        ("radius", 1e-7),
        ("fraction", math.nan),
        ("fraction", 1.01),
        ("normal", (0, 0)),
        ("normal", (2, 0)),
        ("normal", (True, 0)),
        ("normal", (1 + 128 * np.finfo(float).eps, 0)),
    ],
)
def test_invalid_geometry_refused(name, value):
    settings = {"centre": (0, 0), "radius": 1, "fraction": 0.2, "normal": (1, 0)}
    settings[name] = value
    with pytest.raises(ValueError):
        aperture.segment_rectangle_area(**settings, bounds=(-1, -1, 1, 1))


def test_numeric_conversion_overflow_is_a_typed_input_refusal():
    with pytest.raises(ValueError):
        area((-1, -1, 1, 1), radius=10**400)
    with np.errstate(over="ignore"):
        large = np.longdouble(np.finfo(np.longdouble).max)
    with pytest.raises(ValueError):
        area((-1, -1, 1, 1), radius=large)


@pytest.mark.parametrize(
    "bounds",
    [(0, 0, 0, 1), (1, 0, 0, 1), (0, 1, 1, 0), (0, 0, math.inf, 1), (0, 0, True, 1), (0, 0, 1)],
)
def test_invalid_rectangle_refused(bounds):
    with pytest.raises(ValueError):
        area(bounds)


@pytest.mark.parametrize(
    "name,value",
    [
        ("shape", (True, 2)),
        ("shape", (2.0, 2)),
        ("shape", (0, 2)),
        ("shape", (2,)),
        ("pitch", 0),
        ("pitch", True),
        ("pitch", math.nan),
        ("origin", (math.inf, 0)),
    ],
)
def test_invalid_grid_refused(name, value):
    options = {
        "centre": (0, 0),
        "radius": 1,
        "fraction": 0.2,
        "normal": (1, 0),
        "shape": (2, 2),
        "origin": (0, 0),
        "pitch": 1,
    }
    options[name] = value
    with pytest.raises(ValueError):
        aperture.segment_cell_coverage(**options)


def test_cell_cap_is_checked_before_output_allocation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("output allocation occurred before cell-cap refusal")

    monkeypatch.setattr(aperture.np, "empty", forbidden)
    with pytest.raises(ValueError, match="65536"):
        aperture.segment_cell_coverage(
            centre=(0, 0),
            radius=1,
            fraction=0.2,
            normal=(1, 0),
            shape=(257, 256),
            origin=(0, 0),
            pitch=1,
        )
