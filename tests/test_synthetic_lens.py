"""Independent synthetic-camera numerics, not qualification of a real lens."""

import math
from decimal import Decimal, localcontext

import numpy as np
import pytest

from backend import sheet
from tests import synthetic as S


def decimal_root(radius, k1, k2):
    """High-precision scalar sign bracket, independent of the cubic identities.

    Inputs below originate at ru <= 1; every tested polynomial is strictly
    increasing over [0, 1.01]. Decimal preserves the exact binary input floats.
    """
    with localcontext() as context:
        context.prec = 70
        target, a, b = map(Decimal.from_float, (float(radius), k1, k2))
        lo, hi = Decimal(0), Decimal("1.01")
        assert hi + a * hi**3 + b * hi**5 >= target
        for _ in range(240):
            mid = (lo + hi) / 2
            if mid + a * mid**3 + b * mid**5 < target:
                lo = mid
            else:
                hi = mid
        return float((lo + hi) / 2)


@pytest.mark.parametrize(
    "k1,k2",
    [
        (-0.25, 0.0), (-0.12, 0.0), (-1e-12, 0.0), (0.0, 0.0),
        (1e-12, 0.0), (0.06, 0.0), (0.25, 0.0),
        (-0.2, 0.08), (0.06, -0.02), (0.0, 0.12), (0.25, 0.1), (-0.1, -0.02),
    ],
)
def test_radial_inverse_agrees_with_high_precision_sign_brackets(k1, k2):
    radii = np.r_[0.0, 2.0**-32, 0.03, 0.125, 0.5, 0.875, 1.0,
                  np.random.default_rng(193).uniform(0, 1, 12)]
    observed = radii + k1 * radii**3 + k2 * radii**5
    expected = np.array([decimal_root(float(r), k1, k2) for r in observed])
    actual = S._radial_inverse(observed, k1, k2)
    np.testing.assert_allclose(actual, expected, rtol=3e-15, atol=3e-16)
    assert actual[0] == 0.0


@pytest.mark.parametrize("k1,k2", [(-0.12, 0.0), (0.0, 0.0), (0.25, 0.0), (-0.2, 0.08)])
def test_independent_grid_inverts_known_forward_rays_in_pixel_coordinates(k1, k2):
    size = (4000, 3000)
    centre = np.array(size) / 2
    scale = math.hypot(*size) / 2
    radius, angle = np.meshgrid(np.linspace(0, 1, 31), np.linspace(0, 2 * np.pi, 57))
    ideal = np.stack([np.cos(angle), np.sin(angle)], axis=-1) * radius[..., None]
    factor = 1 + k1 * radius**2 + k2 * radius**4
    observed = centre + scale * ideal * factor[..., None]
    u, v = S.undistort_grid(observed[..., 0], observed[..., 1], k1, size, k2)
    actual = np.stack([u, v], axis=-1)
    np.testing.assert_allclose(actual, centre + scale * ideal, rtol=0, atol=5e-12)


@pytest.mark.parametrize("k1,k2", [(-0.25, 0.0), (0.0, -0.25)])
def test_renderer_refuses_a_radial_fold_before_the_sensor_edge(k1, k2):
    with pytest.raises(ValueError, match="folds before"):
        S._radial_inverse(np.array([0.0, 0.5, 1.0]), k1, k2)


def test_lens_rendering_does_not_call_the_production_inverse(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Renderer reused production lens inversion")

    monkeypatch.setattr(sheet, "undistort_radius", forbidden)
    image, truth = S.render(size=(800, 600), ppm=4, k1=-0.04, k2=0.06,
                            shadow=0, gradient=0, noise=0, quality=100)
    assert image[:2] == b"\xff\xd8"
    assert truth["k1"] == -0.04 and truth["k2"] == 0.06
