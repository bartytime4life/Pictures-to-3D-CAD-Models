"""Central-camera domain and independent high-precision radial inverse oracles."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pytest

from backend import sheet


def high_precision_root(radius, coefficient):
    with localcontext() as context:
        context.prec = 80
        target, k = Decimal.from_float(radius), Decimal.from_float(coefficient)
        lo = Decimal(0)
        hi = 1 / (-3 * k).sqrt() if k < 0 else max(Decimal(1), target)
        assert hi + k * hi**3 >= target
        for _ in range(260):
            mid = (lo + hi) / 2
            if mid + k * mid**3 < target:
                lo = mid
            else:
                hi = mid
        return float((lo + hi) / 2)


@pytest.mark.parametrize("coefficient", [-0.25, -0.12])
@pytest.mark.parametrize("gap", [1e-4, 1e-8, 1e-10])
def test_inverse_converges_on_the_central_branch_near_its_turn(coefficient, gap):
    maximum = 2 / (3 * math.sqrt(-3 * coefficient))
    radii = np.array([0.0, 0.1, 0.5, maximum * (1 - gap)])
    expected = np.array([high_precision_root(float(r), coefficient) for r in radii])
    actual = sheet.undistort_radius(radii, coefficient)
    derivative = 1 + 3 * coefficient * expected**2
    # Inverse sensitivity amplifies float evaluation error near the fold.
    allowance = 64 * np.finfo(float).eps * np.maximum(1, expected) / derivative
    assert np.all(np.abs(actual - expected) <= allowance)
    assert np.all(1 + 3 * coefficient * actual**2 > 0)
    np.testing.assert_allclose(actual + coefficient * actual**3, radii, rtol=0, atol=3e-15)


@pytest.mark.parametrize("radius", [0.8, 0.9, 1.0])
def test_inverse_refuses_a_sensor_radius_without_a_central_camera_root(radius):
    with pytest.raises(sheet.SheetError, match="radial lens"):
        sheet.undistort_radius(np.array([0.0, 0.5, radius]), -0.25)


def test_pixel_inverse_refuses_an_impossible_corner_instead_of_returning_positions():
    with pytest.raises(sheet.SheetError, match="radial lens"):
        sheet.undistort_points(np.array([[4000.0, 3000.0]]), -0.25, (4000, 3000))


def test_plumb_line_search_uses_only_admissible_lenses_for_its_observations(monkeypatch):
    size = (4000, 3000)
    centre = np.array(size) / 2
    diagonal = math.hypot(*size) / 2
    # A near-corner quadrilateral of straight edges, specified in ideal coordinates.
    # Independent forward projection keeps every observed point inside the sensor.
    ideal = np.array([[0.3, 0.1], [0.9, 0.5], [1.04, 0.78], [0.5, 0.5]])
    true_k = -0.14

    def photograph(points):
        squared = np.sum(points**2, axis=1)
        return centre + diagonal * points * (1 + true_k * squared[:, None])

    corners = photograph(ideal)
    sides = []
    for a, b in zip(ideal, np.roll(ideal, -1, axis=0)):
        sides.append(photograph(a + np.linspace(0.06, 0.94, 300)[:, None] * (b - a)))
    observations = np.vstack([corners, *sides])
    assert (observations >= 0).all() and (observations <= size).all()
    real_inverse = sheet.undistort_radius
    calls = []

    def check_inverse(rd, k1, *args, **kwargs):
        ru = real_inverse(rd, k1, *args, **kwargs)
        assert np.all(ru >= 0) and np.all(1 + 3 * k1 * ru**2 > 0)
        np.testing.assert_allclose(ru + k1 * ru**3, rd, rtol=0, atol=2e-14)
        calls.append(k1)
        return ru

    monkeypatch.setattr(sheet, "undistort_radius", check_inverse)
    coefficient, before, after = sheet.estimate_k1(sheet.Sheet(corners, sides, 1), size)
    assert calls
    assert abs(coefficient - true_k) < 1e-6
    assert after < 1e-7 < before
