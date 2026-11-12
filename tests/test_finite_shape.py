"""Independent finite Gaussian means, not optical or topology qualification.

Positive area/slice integrals below do not use the production boundary-flux
formula. Agreement between their two quadrature orders is a development
cross-check, not a certified enclosure of numerical or physical error.
"""

import math
from itertools import pairwise

import numpy as np
import pytest

from backend import finite_shape


def cdf(value):
    return 0.5 * math.erfc(-float(value) / math.sqrt(2))


def rectangle(x0, y0, x1, y1):
    points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [("line", a, b) for a, b in zip(points, points[1:] + points[:1])]


def reverse(ring):
    return [(s[0], s[-1], *s[2:-1], s[1]) if s[0] != "circle" else s for s in reversed(ring)]


def evaluate(pixels, rings, **kwargs):
    settings = {
        "sensor_shape": (64, 64),
        "homography": np.eye(3),
        "psf_covariance": np.eye(2),
    }
    settings.update(kwargs)
    return finite_shape.finite_shape_probabilities(np.asarray(pixels), rings, **settings)


def resolved(result):
    assert result.statuses == ("resolved",) * len(result.probabilities)
    values = np.asarray(result.probabilities, dtype=float)
    assert np.isfinite(values).all()
    assert len(result.estimated_errors) == len(values) == len(result.tail_bounds)
    assert all(e is not None and math.isfinite(e) and e >= 0 for e in result.estimated_errors)
    for value, error in zip(values, result.estimated_errors):
        assert -error <= value <= 1 + error  # Unclipped roundoff is intentionally visible.
    assert all(math.isfinite(e) and e >= 0 for e in result.tail_bounds)
    assert result.topology_validated is False
    assert result.quadrature_certified is False
    assert result.chart_margin > 0 and math.isfinite(result.chart_margin)
    return values


def rectangle_mass(point, bounds, sigma):
    x0, y0, x1, y1 = bounds
    px, py = point
    sx, sy = sigma
    return (cdf((x1 - px) / sx) - cdf((x0 - px) / sx)) * (cdf((y1 - py) / sy) - cdf((y0 - py) / sy))


def gauss_integral(function, cuts, order):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    total = []
    for a, b in pairwise(cuts):
        xs = (a + b) / 2 + (b - a) * nodes / 2
        total.append((b - a) / 2 * math.fsum(w * function(x) for x, w in zip(xs, weights)))
    return math.fsum(total)


def polygon_mass(point, vertices, covariance, order):
    """Independent positive vertical slices with the Gaussian conditional in y."""
    px, py = point
    sx = math.sqrt(covariance[0, 0])
    conditional_sigma = math.sqrt(covariance[1, 1] - covariance[0, 1] ** 2 / covariance[0, 0])
    lo, hi = min(p[0] for p in vertices), max(p[0] for p in vertices)
    candidates = [lo, hi, *(p[0] for p in vertices), *(px + k * sx for k in range(-12, 13))]
    cuts = sorted({v for v in candidates if lo <= v <= hi})

    def integrand(x):
        crossings = []
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            if min(a[0], b[0]) < x < max(a[0], b[0]):
                crossings.append(a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0]))
        assert len(crossings) == 2
        low, high = min(crossings), max(crossings)
        mean = py + covariance[0, 1] / covariance[0, 0] * (x - px)
        mass = cdf((high - mean) / conditional_sigma) - cdf((low - mean) / conditional_sigma)
        return math.exp(-0.5 * ((x - px) / sx) ** 2) / (sx * math.sqrt(2 * math.pi)) * mass

    return gauss_integral(integrand, cuts, order)


def d_mass(point, centre, radius, chord, sigma, order):
    """Positive slice integral of disc(R) intersect x <= centre.x + chord."""
    px, py = np.asarray(point) - centre
    end = math.acos(-chord / radius)
    cuts = {0.0, end}
    for k in range(-12, 13):
        x = px + k * sigma
        if -radius < x < chord:
            cuts.add(math.acos(-x / radius))

    def integrand(theta):
        x, y = -radius * math.cos(theta), radius * math.sin(theta)
        density = math.exp(-0.5 * ((x - px) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
        return density * (cdf((y - py) / sigma) - cdf((-y - py) / sigma)) * y

    return gauss_integral(integrand, sorted(cuts), order)


@pytest.mark.parametrize("sigma", [(1.0, 1.0), (0.35, 2.3)])
@pytest.mark.parametrize("backwards", [False, True])
def test_rectangle_matches_separable_gaussian_and_normalizes_supplied_winding(sigma, backwards):
    bounds = (10.2, 11.7, 19.4, 22.1)
    ring = rectangle(*bounds)
    pixels = np.array([[10, 12], [14, 16], [19, 22], [9, 18], [23, 25]])
    result = evaluate(
        pixels, [reverse(ring) if backwards else ring], psf_covariance=np.diag(np.square(sigma))
    )
    expected = [rectangle_mass(p + 0.5, bounds, sigma) for p in pixels]
    np.testing.assert_allclose(resolved(result), expected, atol=2e-8, rtol=0)


def test_two_disjoint_holes_are_subtracted_by_role_without_clipping_to_sensor():
    outer = (-3.0, -4.0, 13.0, 14.0)
    holes = [(2.0, 3.0, 5.0, 6.0), (8.0, 8.0, 11.0, 11.0)]
    sigma = (0.8, 1.4)
    pixels = np.array([[0, 0], [3, 4], [9, 9], [6, 7], [13, 7]])
    rings = [reverse(rectangle(*outer)), *(rectangle(*h) for h in holes)]
    expected = [
        rectangle_mass(p + 0.5, outer, sigma)
        - sum(rectangle_mass(p + 0.5, h, sigma) for h in holes)
        for p in pixels
    ]
    result = evaluate(
        pixels, rings, sensor_shape=(16, 16), psf_covariance=np.diag(np.square(sigma))
    )
    np.testing.assert_allclose(resolved(result), expected, atol=2e-8, rtol=0)


@pytest.mark.parametrize("radius,sigma", [(0.2, 1.0), (1.0, 1.0), (3.0, 1.3), (20.0, 0.01)])
def test_centred_disk_matches_exact_radial_area_probability(radius, sigma):
    result = evaluate(
        [[20, 20]], [[("circle", (20.5, 20.5), radius)]], psf_covariance=np.eye(2) * sigma**2
    )
    expected = -math.expm1(-(radius**2) / (2 * sigma**2))
    assert resolved(result)[0] == pytest.approx(expected, abs=2e-8)


@pytest.mark.parametrize(
    "inner,outer,sigma", [(0.3, 1.0, 1.0), (1.5, 3.0, 1.0), (10.0, 20.0, 0.01)]
)
def test_centred_annulus_keeps_hole_winding_even_when_all_boundaries_are_far(inner, outer, sigma):
    rings = [[("circle", (20.5, 20.5), outer)], [("circle", (20.5, 20.5), inner)]]
    result = evaluate([[20, 20]], rings, psf_covariance=np.eye(2) * sigma**2)
    expected = math.exp(-(inner**2) / (2 * sigma**2)) - math.exp(-(outer**2) / (2 * sigma**2))
    assert resolved(result)[0] == pytest.approx(expected, abs=2e-8)


@pytest.mark.parametrize("chord", [-6.0, 0.0, 6.0])
def test_finite_minor_half_and_major_d_match_independent_positive_slices(chord):
    centre, radius, sigma = np.array([15.5, 15.5]), 10.0, 1.3
    height = math.sqrt(radius**2 - chord**2)
    top, bottom = centre + [chord, height], centre + [chord, -height]
    ring = [("arc", top, centre + [-radius, 0.0], bottom), ("line", bottom, top)]
    pixels = np.array([[8, 15], [15, 15], [21, 15], [15, 20]])
    first = [d_mass(p + 0.5, centre, radius, chord, sigma, 24) for p in pixels]
    expected = [d_mass(p + 0.5, centre, radius, chord, sigma, 48) for p in pixels]
    assert max(abs(a - b) for a, b in zip(first, expected)) < 2e-12
    result = evaluate(pixels, [ring], psf_covariance=np.eye(2) * sigma**2)
    np.testing.assert_allclose(resolved(result), expected, atol=3e-8, rtol=0)
    opposite = evaluate(pixels, [reverse(ring)], psf_covariance=np.eye(2) * sigma**2)
    np.testing.assert_allclose(resolved(opposite), expected, atol=3e-8, rtol=0)


@pytest.mark.parametrize("scale", [1.0, -1.0, 1e-80, -1e80])
def test_projective_correlated_gaussian_matches_independent_area_slices_and_h_scale(scale):
    bounds = (-2.0, -1.0, 3.0, 2.0)
    ring = rectangle(*bounds)
    h = np.array([[2.0, 0.3, 14.2], [-0.1, 1.6, 12.1], [0.03, -0.02, 1.0]])
    covariance = np.array([[0.9, 0.4], [0.4, 1.7]])
    homogeneous = np.array([[*s[1], 1.0] for s in ring]) @ h.T
    vertices = (homogeneous[:, :2] / homogeneous[:, 2, None]).tolist()
    pixels = np.array([[13, 12], [17, 13], [10, 11], [18, 10]])
    first = [polygon_mass(p + 0.5, vertices, covariance, 24) for p in pixels]
    expected = [polygon_mass(p + 0.5, vertices, covariance, 48) for p in pixels]
    assert max(abs(a - b) for a, b in zip(first, expected)) < 3e-13
    result = evaluate(pixels, [ring], homography=scale * h, psf_covariance=covariance)
    np.testing.assert_allclose(resolved(result), expected, atol=3e-8, rtol=0)
    assert result.reflected is False


def test_reflection_and_quarter_turn_preserve_means_with_raw_covariance_transport():
    ring = rectangle(10.2, 11.7, 19.4, 22.1)
    pixels = np.array([[10, 12], [14, 16], [19, 22], [9, 18]])
    covariance = np.array([[0.9, 0.4], [0.4, 1.7]])
    expected = resolved(evaluate(pixels, [ring], psf_covariance=covariance))
    for transform in (
        np.array([[0.0, -1.0, 64.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]),
        np.array([[-1.0, 0.0, 64.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
    ):
        rotation = transform[:2, :2]
        moved_pixels = np.rint((pixels + 0.5) @ rotation.T + transform[:2, 2] - 0.5).astype(int)
        result = evaluate(
            moved_pixels,
            [ring],
            homography=transform,
            psf_covariance=rotation @ covariance @ rotation.T,
        )
        np.testing.assert_allclose(resolved(result), expected, atol=3e-8, rtol=0)
        assert result.reflected is bool(np.linalg.det(rotation) < 0)


def test_compact_forward_chart_does_not_require_whole_sensor_inverse_chart():
    ring = rectangle(0.0, 0.0, 1.0, 1.0)
    h = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.1, 0.0, 1.0]])
    homogeneous = np.array([[*s[1], 1.0] for s in ring]) @ h.T
    vertices = (homogeneous[:, :2] / homogeneous[:, 2, None]).tolist()
    covariance = np.eye(2) * 0.4**2
    expected = polygon_mass((0.5, 0.5), vertices, covariance, 48)
    # The sensor extends past raw x=10, its inverse horizon; the object does not.
    result = evaluate(
        [[0, 0]], [ring], sensor_shape=(20, 20), homography=h, psf_covariance=covariance
    )
    assert resolved(result)[0] == pytest.approx(expected, abs=3e-8)


def test_large_radius_boundary_peak_is_not_missed_between_fixed_angle_nodes():
    radius = 10_000.0

    def oracle(order):
        def integrand(y):
            root = math.sqrt(radius**2 - y**2)
            distance = y**2 / (radius + root)
            x_mass = cdf(-distance) - cdf(-radius - root)
            return math.exp(-(y**2) / 2) / math.sqrt(2 * math.pi) * x_mass

        return gauss_integral(integrand, np.arange(-12, 13, 2), order)

    first, expected = oracle(24), oracle(48)
    assert abs(first - expected) < 3e-14
    assert 0.49997 < expected < 0.5  # Curvature remains visible; half-plane is wrong.
    ring = [("circle", (radius + 0.5, radius + 0.5), radius)]
    result = evaluate([[20_000, 10_000]], [ring], sensor_shape=(20_002, 20_002))
    assert resolved(result)[0] == pytest.approx(expected, abs=3e-8)


def test_whole_major_arc_horizon_is_checked_even_with_positive_endpoint_denominators():
    radius, chord = 10.0, 6.0
    height = math.sqrt(radius**2 - chord**2)
    ring = [
        ("arc", (chord, height), (-radius, 0.0), (chord, -height)),
        ("line", (chord, -height), (chord, height)),
    ]
    h = np.array([[1.0, 0.0, 20.0], [0.0, 1.0, 20.0], [0.2, 0.0, 1.0]])
    assert all(h[2] @ [*s[1], 1.0] > 0 for s in ring)
    with pytest.raises(ValueError, match="chart|horizon|denominator"):
        evaluate([[20, 20]], [ring], homography=h)


def test_budget_exhaustion_retains_every_query_and_never_returns_false_resolved_values():
    pixels = [[30, 20], [20, 20], [20, 30], [0, 0]]
    result = evaluate(pixels, [[("circle", (20.5, 20.5), 10.0)]], max_panels=1, max_evaluations=1)
    assert len(result.probabilities) == len(result.statuses) == len(pixels)
    assert len(result.estimated_errors) == len(result.tail_bounds) == len(pixels)
    assert "work_limit" in result.statuses
    assert set(result.statuses) <= {"resolved", "work_limit", "numerical", "invalid_winding"}
    assert result.evaluations <= 1
    for value, status in zip(result.probabilities, result.statuses):
        assert (value is not None) is (status == "resolved")
        if value is not None:
            assert math.isfinite(value)


def test_numerical_failure_retains_queries_without_erasing_work_already_performed(monkeypatch):
    actual_at = finite_shape._at
    actual_quadrature = finite_shape._quadrature
    evaluated, quadratures = 0, 0

    def counted_at(*args):
        nonlocal evaluated
        result = actual_at(*args)
        evaluated += np.size(args[-1])
        return result

    def fail_after_completed_work(*args):
        nonlocal quadratures
        quadratures += 1
        if quadratures == 3:
            raise ArithmeticError("independent injected arithmetic failure after completed panels")
        return actual_quadrature(*args)

    monkeypatch.setattr(finite_shape, "_at", counted_at)
    monkeypatch.setattr(finite_shape, "_quadrature", fail_after_completed_work)
    result = evaluate([[22, 20], [20, 20]], [[("circle", (20.5, 20.5), 2.0)]], max_evaluations=128)
    assert len(result.probabilities) == len(result.statuses) == 2
    assert result.statuses[0] == "numerical" and result.probabilities[0] is None
    assert evaluated > 36  # The failure happened after a completed quadrature pair.
    assert evaluated <= result.evaluations <= 128


def test_invalid_negative_winding_mass_is_reported_instead_of_clipped_to_zero():
    # Deliberately violate the supplied disjoint-hole assumption. This control
    # tests a detected invalid mass, not a promise to detect every invalid topology.
    rings = [[("circle", (20.5, 20.5), radius)] for radius in (3.0, 2.5, 2.5)]
    result = evaluate([[20, 20]], rings)
    assert result.statuses == ("invalid_winding",)
    assert result.probabilities == (None,)


@pytest.mark.parametrize(
    "pixels",
    [
        [],
        [[1.0, 2.0]],
        [[True, False]],
        [[1, 2], [1, 2]],
        [[-1, 0]],
        [[64, 1]],
        [[1, 64]],
        [[1, 2, 3]],
    ],
)
def test_invalid_raw_pixel_rows_are_refused(pixels):
    with pytest.raises((ValueError, TypeError)):
        evaluate(pixels, [rectangle(10, 10, 20, 20)])


@pytest.mark.parametrize(
    "settings",
    [
        {"sensor_shape": (0, 10)},
        {"sensor_shape": (10.0, 10)},
        {"sensor_shape": (True, 10)},
        {"homography": np.zeros((3, 3))},
        {"homography": np.eye(2)},
        {"homography": np.eye(3) * math.nan},
        {"psf_covariance": [[1, 0.1], [0, 1]]},
        {"psf_covariance": [[1, 2], [2, 1]]},
        {"psf_covariance": np.zeros((2, 2))},
        {"psf_covariance": np.diag([math.inf, math.inf])},
        {"probability_tolerance": 0},
        {"probability_tolerance": math.nan},
        {"max_panels": 0},
        {"max_panels": True},
        {"max_evaluations": 0},
    ],
)
def test_invalid_geometry_and_numerical_settings_are_refused(settings):
    with pytest.raises((ValueError, TypeError)):
        evaluate([[12, 12]], [rectangle(10, 10, 20, 20)], **settings)


@pytest.mark.parametrize(
    "rings",
    [
        [],
        [[]],
        [[("circle", (10, 10), 0)]],
        [[("circle", (10, 10), -1)]],
        [[("circle", (math.nan, 10), 1)]],
        [[("bezier", (0, 0), (1, 1))]],
        [[("line", (0, 0), (1, 0)), ("line", (1.1, 0), (0, 0))]],
        [[("arc", (0, 0), (1, 0), (2, 0)), ("line", (2, 0), (0, 0))]],
    ],
)
def test_empty_unclosed_and_unrepresentable_supplied_boundaries_are_refused(rings):
    with pytest.raises((ValueError, TypeError)):
        evaluate([[12, 12]], rings)


def test_declared_shape_and_query_resource_caps_are_enforced():
    angles = np.arange(129) * math.tau / 129
    vertices = [(20 + math.cos(t), 20 + math.sin(t)) for t in angles]
    ring = [("line", a, b) for a, b in zip(vertices, vertices[1:] + vertices[:1])]
    cases = [
        (np.array([[12, 12]]), [ring]),
        (np.array([[12, 12]]), [[("circle", (20, 20), 10)]] * 34),
        (
            np.column_stack((np.arange(2049) % 64, np.arange(2049) // 64)),
            [rectangle(10, 10, 20, 20)],
        ),
    ]
    for pixels, rings in cases:
        with pytest.raises((ValueError, TypeError)):
            evaluate(pixels, rings)
