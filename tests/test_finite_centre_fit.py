"""Independent numerical/optimizer contracts; not camera or physical qualification."""

import itertools
import json
import math
from dataclasses import asdict

import numpy as np
import pytest

from backend import finite_centre_fit as fit
from backend import finite_shape as finite


def configuration():
    pixels = np.array([[5, 7], [8, 11], [12, 8], [13, 14], [17, 9], [20, 15]])
    return pixels, {
        "sensor_shape": (32, 32),
        "homography": np.eye(3),
        "psf_covariance": np.array([[1.0, 0.3], [0.3, 2.0]]),
        "centre_bounds": ((12.0, 14.0), (11.0, 13.0)),
        "radius_bounds": (5.0, 7.0),
        "chord_fraction_bounds": (-0.2, 0.4),
        "refinement_iterations": 0,
    }


def probabilities(pixels, parameters, h, covariance, normal):
    ring = fit.circular_segment_ring(
        parameters[2], parameters[3], centre=parameters[:2], normal=normal
    )
    result = finite.finite_shape_probabilities(
        pixels,
        [ring],
        sensor_shape=(64, 64),
        homography=h,
        psf_covariance=covariance,
        probability_tolerance=1e-10,
    )
    assert set(result.statuses) == {"resolved"}
    return np.array(result.probabilities)


@pytest.mark.parametrize("fraction", [-0.65, 0.0, 0.6])
@pytest.mark.parametrize(
    "h",
    [
        np.eye(3),
        np.array([[1.1, 0.1, -2], [0.05, 0.9, 2], [0.002, -0.001, 1]]),
        np.array([[-1.0, 0.1, 40], [0, 1.0, 0], [0, 0, 1.0]]),
    ],
)
def test_boundary_shape_derivatives_match_independent_parameter_differences(fraction, h):
    pixels = np.array([[10, 13], [14, 10], [18, 14], [12, 17]])
    parameters = np.array([14.37, 14.81, 6.4, fraction])
    normal = np.array([math.cos(0.37), math.sin(0.37)])
    covariance = np.array([[1.1, 0.4], [0.4, 2.3]])
    actual = fit.circular_segment_jacobian(
        pixels,
        parameters[2],
        parameters[3],
        centre=parameters[:2],
        normal=normal,
        sensor_shape=(64, 64),
        homography=h,
        psf_covariance=covariance,
        probability_tolerance=1e-10,
    )
    assert set(actual.statuses) == {"resolved"}
    assert actual.method == "boundary_shape" and not actual.quadrature_certified
    for step in (2e-4, 1e-4):
        expected = np.column_stack(
            [
                (
                    probabilities(pixels, parameters + step * axis, h, covariance, normal)
                    - probabilities(pixels, parameters - step * axis, h, covariance, normal)
                )
                / (2 * step)
                for axis in np.eye(4)
            ]
        )
        np.testing.assert_allclose(actual.jacobian, expected, rtol=3e-6, atol=2e-8)


def independent_box_fit(a, target, bounds):
    """Enumerate nine faces, using scalar/2x2 closed forms independent of SVD."""
    options = []
    for state in itertools.product((None, *bounds), repeat=2):
        beta = np.array([0.0 if value is None else value for value in state])
        free = [i for i, value in enumerate(state) if value is None]
        rhs = target - a @ beta
        if len(free) == 2:
            gram, b = a.T @ a, a.T @ rhs
            determinant = gram[0, 0] * gram[1, 1] - gram[0, 1] ** 2
            beta = np.array(
                [
                    (gram[1, 1] * b[0] - gram[0, 1] * b[1]) / determinant,
                    (gram[0, 0] * b[1] - gram[0, 1] * b[0]) / determinant,
                ]
            )
        elif len(free) == 1:
            i = free[0]
            beta[i] = (a[:, i] @ rhs) / (a[:, i] @ a[:, i])
        if np.all((beta >= bounds[0]) & (beta <= bounds[1])):
            r = target - a @ beta
            options.append((r @ r, beta, r))
    return min(options, key=lambda item: item[0])


@pytest.mark.parametrize("source_levels", [(50, 180), (-25, 180), (50, 290), (-150, 500)])
def test_full_fixed_active_face_variable_projection_matches_profiled_residual(source_levels):
    p = np.linspace(0.05, 0.95, 13)
    a = np.column_stack((1 - p, p))
    dp = np.column_stack((np.sin(p), np.cos(3 * p), p**2, np.exp(-p)))
    target = a @ source_levels + np.random.default_rng(27).normal(0, 0.2, len(p))
    expected_cost, expected_beta, _ = independent_box_fit(a, target, (0.0, 255.0))
    cost, beta, _, _ = fit._box_fit(a, target, (0.0, 255.0))
    assert cost == pytest.approx(expected_cost, rel=2e-12, abs=1e-9)
    np.testing.assert_allclose(beta, expected_beta, rtol=0, atol=1e-10)
    full, mean = fit._projected_jacobians(a, dp, beta, target, (0.0, 255.0))
    epsilon = 1e-6
    expected_jacobian = np.column_stack(
        [
            (
                independent_box_fit(
                    np.column_stack((1 - p - epsilon * column, p + epsilon * column)),
                    target,
                    (0.0, 255.0),
                )[2]
                - independent_box_fit(
                    np.column_stack((1 - p + epsilon * column, p - epsilon * column)),
                    target,
                    (0.0, 255.0),
                )[2]
            )
            / (2 * epsilon)
            for column in dp.T
        ]
    )
    np.testing.assert_allclose(full, expected_jacobian, rtol=2e-5, atol=2e-6)
    if np.any((beta > 0) & (beta < 255)):
        assert np.linalg.norm(full + mean) > 1e-5  # residual-dependent GP term is exercised
    else:
        np.testing.assert_array_equal(full, -mean)  # no free nuisance parameter


def fake_forward(monkeypatch, *, error=0.0, callback=None):
    def forward(pixels, *args, **kwargs):
        if callback:
            callback()
        p = np.linspace(0.1, 0.9, len(pixels))
        return finite.FiniteShapeResult(
            tuple(p), ("resolved",) * len(p), (error,) * len(p), (0.0,) * len(p), 2, 1, 1.0, False
        )

    monkeypatch.setattr(fit, "circular_segment_probabilities", forward)


def fake_derivative(monkeypatch):
    def derivative(pixels, *args, **kwargs):
        dp = np.random.default_rng(31).normal(size=(len(pixels), 4))
        return fit.ShapeJacobian(
            tuple(map(tuple, dp)), ("resolved",) * len(pixels), (0.0,) * len(pixels), 2, 1
        )

    monkeypatch.setattr(fit, "circular_segment_jacobian", derivative)


def test_information_rank_does_not_come_from_projector_roundoff(monkeypatch):
    pixels, config = configuration()
    fake_forward(monkeypatch)
    fake_derivative(monkeypatch)
    transform = np.eye(len(pixels))[:2]
    result = fit.fit_circular_segment(
        pixels, np.linspace(60.0, 180.0, len(pixels)), residual_transform=transform, **config
    )
    assert result.residual_rank == 2 and not result.full_source_metric
    assert result.best.design_rank == 2
    assert result.geometry_rank == 0  # two free levels exhaust both retained modes
    assert result.rank_deficient


def test_zero_contrast_has_no_mean_information_even_with_noisy_residual():
    p = np.linspace(0.1, 0.9, 8)
    a = np.column_stack((1 - p, p))
    dp = np.random.default_rng(18).normal(size=(8, 4))
    full, mean = fit._projected_jacobians(
        a,
        dp,
        np.array([70.0, 70.0]),
        np.array([69.0, 72.0, 70.0, 74.0, 68.0, 71.0, 70.0, 72.0]),
        (0.0, 255.0),
    )
    assert np.linalg.norm(full) > 0
    np.testing.assert_array_equal(mean, np.zeros_like(mean))


def test_derivative_failure_retains_complete_grid_and_unknown_rank(monkeypatch):
    pixels, config = configuration()
    fake_forward(monkeypatch)

    def fail(*args, **kwargs):
        raise ArithmeticError("injected derivative numerical failure")

    monkeypatch.setattr(fit, "circular_segment_jacobian", fail)
    result = fit.fit_circular_segment(pixels, np.linspace(60.0, 180.0, len(pixels)), **config)
    assert len(result.grid) == len(result.grid_statuses) == 81
    assert result.best is not None and result.geometry_rank is None
    assert result.numerically_unsupported
    json.dumps(asdict(result), allow_nan=False)


def test_residual_transform_and_forward_error_use_same_snapshot(monkeypatch):
    pixels, config = configuration()
    transform = np.diag(np.linspace(1.0, 2.0, len(pixels)))
    expected_error = 255 * math.hypot(*(transform @ np.full(len(pixels), 1e-5)))
    fake_forward(monkeypatch, error=1e-5, callback=lambda: transform.fill(0))
    fake_derivative(monkeypatch)
    result = fit.fit_circular_segment(
        pixels, np.linspace(60.0, 180.0, len(pixels)), residual_transform=transform, **config
    )
    assert result.grid[0].forward_residual_error_estimate == pytest.approx(expected_error)


@pytest.mark.parametrize("tolerance", [True, float("nan"), 0.0, 0.1])
def test_invalid_tolerance_is_input_error_not_81_numerical_unknowns(monkeypatch, tolerance):
    pixels, config = configuration()

    def unexpected(*args, **kwargs):
        pytest.fail("input validation must precede every forward call")

    monkeypatch.setattr(fit, "circular_segment_probabilities", unexpected)
    with pytest.raises(ValueError, match="probability_tolerance"):
        fit.fit_circular_segment(
            pixels, np.ones(len(pixels)), probability_tolerance=tolerance, **config
        )


def test_forward_work_exhaustion_keeps_all_grid_cells_and_strict_json():
    pixels, config = configuration()
    result = fit.fit_circular_segment(pixels, np.ones(len(pixels)), forward_work_limit=1, **config)
    assert result.best is None and result.geometry_rank is None
    assert len(result.grid) == 81 and set(result.grid_statuses) == {"work_limit"}
    assert result.work_exhausted and result.evaluations == 1
    assert result.forward_evaluations <= 1
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("factor", [1e-6, 1.0, 1e6])
def test_equivalent_vector_and_matrix_weights_have_same_numerical_rank(monkeypatch, factor):
    pixels, config = configuration()
    fake_forward(monkeypatch)
    fake_derivative(monkeypatch)
    weights = factor * np.array([1.0, 1e-20, 1e-20, 1e-20, 1e-20, 1e-20])
    rows = [
        fit.fit_circular_segment(
            pixels, np.linspace(60.0, 180.0, len(pixels)), residual_transform=t, **config
        )
        for t in (weights, np.diag(weights))
    ]
    assert [r.residual_rank for r in rows] == [1, 1]
    assert all(not r.full_source_metric and r.geometry_rank == 0 for r in rows)
    assert rows[0].best.cost == pytest.approx(rows[1].best.cost, abs=1e-30)


@pytest.mark.parametrize("large_value,expected", [(1e200, 1e200), (1e308, None)])
def test_discarded_source_residual_remains_visible_without_corrupting_fit(
    monkeypatch, large_value, expected
):
    pixels, config = configuration()
    fake_forward(monkeypatch)
    values = np.full(len(pixels), large_value)
    values[0] = 0
    result = fit.fit_circular_segment(
        pixels, values, residual_transform=np.eye(len(pixels))[:1], **config
    )
    assert result.best is not None and result.best.cost == 0
    assert result.transformed_residual_l2 == 0
    if expected is None:
        assert result.raw_residual_l2 is None and result.numerically_unsupported
    else:
        assert result.raw_residual_l2 == pytest.approx(math.sqrt(len(pixels) - 1) * expected)
    json.dumps(asdict(result), allow_nan=False)


def test_a_complete_coarse_grid_does_not_invent_a_budget_starved_geometry_rank(monkeypatch):
    pixels, config = configuration()
    fake_forward(monkeypatch)
    result = fit.fit_circular_segment(
        pixels, np.linspace(60.0, 180.0, len(pixels)), forward_work_limit=2 * 81, **config
    )
    assert result.best is not None and all(c is not None for c in result.grid)
    assert result.forward_evaluations == 162 and result.work_exhausted
    assert result.geometry_rank is None and result.derivative_calls == 0
    assert result.grid_shape == (3, 3, 3, 3)
    assert result.endpoint and result.tied  # every represented coarse geometry ties
    assert not result.global_search_certified


def test_safe_low_geometry_does_not_hide_an_unsafe_upper_projective_domain(monkeypatch):
    pixels, config = configuration()
    config["homography"] = np.array([[1.0, 0, 0], [0, 1.0, 0], [1.0, 0, -16.0]])

    def unexpected(*args, **kwargs):
        pytest.fail("whole-domain chart validation must precede measurements")

    monkeypatch.setattr(fit, "circular_segment_probabilities", unexpected)
    with pytest.raises(ValueError, match="horizon"):
        fit.fit_circular_segment(pixels, np.ones(len(pixels)), **config)


@pytest.mark.parametrize(
    "change",
    [
        {"centre_bounds": ((12.0, math.nextafter(12.0, 13.0)), (11.0, 13.0))},
        {"radius_bounds": (6.0, math.nextafter(6.0, 7.0))},
        {"chord_fraction_bounds": (0.1, math.nextafter(0.1, 1.0))},
        {"radius_bounds": (True, 7.0)},
        {"normal": (1.0, 1.0)},
        {"normal": (True, 0)},
        {"max_evaluations": 80},
        {"max_evaluations": True},
        {"grid_points": 6},
        {"refinement_iterations": True},
        {"forward_work_limit": 0},
        {"homography": [[True, 0, 0], [0, 1, 0], [0, 0, 1]]},
        {"psf_covariance": [[1.0, 2.0], [2.0, 1.0]]},
        {"psf_covariance": [[1.0, 0.1], [0, 1.0]]},
        {"residual_transform": [True] * 6},
        {"residual_transform": [-1.0] * 6},
        {"residual_transform": np.ones((2, 5))},
        {"level_bounds": (1.0, 1.0)},
    ],
)
def test_invalid_settings_are_refused_before_forward_work(monkeypatch, change):
    pixels, config = configuration()
    config.update(change)

    def unexpected(*args, **kwargs):
        pytest.fail("invalid input must not enter the numerical forward operator")

    monkeypatch.setattr(fit, "circular_segment_probabilities", unexpected)
    with pytest.raises((ValueError, TypeError)):
        fit.fit_circular_segment(pixels, np.ones(len(pixels)), **config)


@pytest.mark.parametrize(
    "pixels",
    [
        [[True, 1], [2, 3]],
        [[1.0, 2.0], [3.0, 4.0]],
        [[1, 2], [1, 2]],
        [[-1, 2], [1, 2]],
        [[1, 32]],
        [],
        [[1, 2, 3]],
    ],
)
def test_source_pixel_validation_has_no_rounding_or_clipping(pixels):
    _, config = configuration()
    with pytest.raises(ValueError, match="pixel"):
        fit.fit_circular_segment(pixels, np.ones(len(pixels)), **config)


@pytest.mark.parametrize("fraction", [-0.6, 0.0, 0.6])
def test_internal_direct_parameters_preserve_ordinary_public_ring_predictions(fraction):
    pixels = np.array([[10, 13], [14, 10], [18, 14], [12, 17]])
    centre = (14.37, 14.81)
    h = np.array([[1.1, 0.1, -2], [0.05, 0.9, 2], [0.002, -0.001, 1.0]])
    covariance = np.array([[1.1, 0.4], [0.4, 2.3]])
    normal = np.array([math.cos(0.37), math.sin(0.37)])
    old = probabilities(pixels, np.array([*centre, 6.4, fraction]), h, covariance, normal)
    direct = fit.circular_segment_probabilities(
        pixels,
        6.4,
        fraction,
        centre=centre,
        normal=normal,
        sensor_shape=(64, 64),
        homography=h,
        psf_covariance=covariance,
        probability_tolerance=1e-10,
    )
    assert set(direct.statuses) == {"resolved"}
    np.testing.assert_allclose(direct.probabilities, old, atol=2e-12, rtol=0)


def independent_axis_d_mass(q, radius, fraction, sigma, order):
    """Positive conditional-X Gaussian area integral in LOCAL coordinates."""
    nodes, weights = np.polynomial.legendre.leggauss(order)
    total = 0.0
    for left in range(-12, 12):
        for node, weight in zip(nodes, weights):
            t = left + (node + 1) / 2
            y = q[1] + sigma * t
            if abs(y) >= radius:
                continue
            extent = math.sqrt((radius - y) * (radius + y))
            lower, upper = -extent, min(extent, radius * fraction)
            if lower >= upper:
                continue
            mass = 0.5 * (
                math.erfc((lower - q[0]) / (sigma * math.sqrt(2)))
                - math.erfc((upper - q[0]) / (sigma * math.sqrt(2)))
            )
            total += weight / 2 * math.exp(-t * t / 2) / math.sqrt(2 * math.pi) * mass
    return total


@pytest.mark.parametrize("translation", [0, 999998, 999999998])
def test_tiny_shape_at_large_translation_keeps_actual_parameter_means_and_derivatives(translation):
    pixels = np.array([[translation, translation]])
    centre = np.array([translation + 0.501, translation + 0.5])
    radius, fraction, sigma = 0.001, 0.99, 1e-5
    relative = pixels[0].astype(float) + 0.5 - centre
    expected = independent_axis_d_mass(relative, radius, fraction, sigma, 64)
    assert abs(expected - independent_axis_d_mass(relative, radius, fraction, sigma, 32)) < 1e-12
    controls = {
        "centre": centre,
        "sensor_shape": (10**9, 10**9),
        "homography": np.eye(3),
        "psf_covariance": np.eye(2) * sigma**2,
        "probability_tolerance": 1e-10,
    }
    direct = fit.circular_segment_probabilities(pixels, radius, fraction, **controls)
    assert direct.statuses == ("resolved",)
    assert direct.probabilities[0] == pytest.approx(expected, abs=2e-10)
    derivative = fit.circular_segment_jacobian(pixels, radius, fraction, **controls)
    # The ~4e4/px derivative has an absolute arithmetic floor above 1e-10;
    # retain this stricter unresolved query rather than enlarging its budget.
    assert derivative.statuses == ("work_limit",)
    controls["probability_tolerance"] = 1e-8  # unchanged API default, absolute derivative units
    derivative = fit.circular_segment_jacobian(pixels, radius, fraction, **controls)
    assert derivative.statuses == ("resolved",)
    step = sigma * 1e-4
    # Differentiate the independent LOCAL area integral, avoiding cancellation
    # from trying to add sub-ULP increments to a large world-coordinate centre.
    expected_dx = (
        independent_axis_d_mass(relative - [step, 0], radius, fraction, sigma, 64)
        - independent_axis_d_mass(relative + [step, 0], radius, fraction, sigma, 64)
    ) / (2 * step)
    assert derivative.jacobian[0][0] == pytest.approx(expected_dx, rel=2e-7, abs=2e-5)


@pytest.mark.parametrize(
    "homography", [np.eye(3), np.array([[-1.0, 0.1, 40], [0, 1.0, 0], [0.001, 0, 1.0]])]
)
def test_public_kernel_refactor_preserves_frozen_ring_results(monkeypatch, homography):
    import hashlib
    import importlib.util
    import sys
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "studies/verification/finite-shape-flux-v1.py"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "e6c8962a896ab60f4e0e335f1d17ed5694c85597dc7fff58565b3e770d4d7b00"
    )
    spec = importlib.util.spec_from_file_location("frozen_shape_parity", path)
    old = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, old)
    spec.loader.exec_module(old)
    pixels = np.array([[10, 13], [14, 10], [18, 14], [12, 17]])
    rings = [
        fit.circular_segment_ring(8.0, 0.6, centre=(14.0, 14.0)),
        [("circle", (12.0, 14.0), 0.75)],
    ]
    options = {
        "sensor_shape": (64, 64),
        "homography": homography,
        "psf_covariance": np.array([[1.1, 0.4], [0.4, 2.3]]),
    }
    assert asdict(finite.finite_shape_probabilities(pixels, rings, **options)) == asdict(
        old.finite_shape_probabilities(pixels, rings, **options)
    )
