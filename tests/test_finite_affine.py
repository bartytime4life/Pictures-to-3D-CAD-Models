"""Independent means and work contracts; no optimizer or physical qualification."""

import hashlib
import json
import math
import sys
import types
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from backend import finite_affine as batch
from backend import finite_centre_fit as centre_fit
from backend import finite_shape as scalar
from backend import fitting


def options(**changes):
    result = {"sensor_shape": (80, 80), "homography": np.eye(3), "psf_covariance": np.eye(2)}
    result.update(changes)
    return result


def rectangle(a, b, reverse=False):
    x0, y0 = a
    x1, y1 = b
    points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if reverse:
        points.reverse()
    return [("line", p, q) for p, q in zip(points, points[1:] + points[:1])]


def phi(z):
    return 0.5 * math.erfc(-z / math.sqrt(2))


def independent_disk(point, centre, radius, covariance, order):
    """Positive conditional-X|Y area integral; no Green/production calls."""
    nodes, weights = np.polynomial.legendre.leggauss(order)
    angle = math.pi / 2 * nodes
    y = centre[1] + radius * np.sin(angle)
    halfwidth = radius * np.cos(angle)
    variance = covariance[1, 1]
    mean = point[0] + covariance[0, 1] / variance * (y - point[1])
    sd = math.sqrt(covariance[0, 0] - covariance[0, 1] ** 2 / variance)
    mass = np.array(
        [
            phi((hi - m) / sd) - phi((lo - m) / sd)
            for hi, lo, m in zip(centre[0] + halfwidth, centre[0] - halfwidth, mean)
        ]
    )
    density = np.exp(-((y - point[1]) ** 2) / (2 * variance)) / math.sqrt(math.tau * variance)
    return math.pi / 2 * math.fsum(weights * radius * np.cos(angle) * density * mass)


@pytest.mark.parametrize("reverse", [False, True])
def test_rectangle_matches_independent_product_cdf_including_boundary(reverse):
    pixels = np.array([[10, 12], [4, 8], [27, 24], [35, 40]])
    low, high = (4.5, 8.5), (27.5, 24.5)
    covariance = np.diag([0.64, 2.25])
    result = batch.finite_shape_probabilities(
        pixels, [rectangle(low, high, reverse)], **options(psf_covariance=covariance)
    )
    expected = [
        math.prod(
            phi((b - p) / s) - phi((a - p) / s)
            for a, b, p, s in zip(low, high, pixel + 0.5, (0.8, 1.5))
        )
        for pixel in pixels
    ]
    assert result.statuses == ("resolved",) * len(pixels)
    np.testing.assert_allclose(result.probabilities, expected, rtol=0, atol=2e-10)
    assert result.diagnostics.batched_queries == len(pixels)


@pytest.mark.parametrize(
    "matrix",
    [
        np.array([[1.0, 0, 0], [0, 1, 0], [0, 0, 1]]),
        np.array([[0.9, 0.2, 15], [-0.1, 1.1, 9], [0, 0, 1]]),
        np.array([[-1.0, 0.2, 50], [0.1, 1.1, 9], [0, 0, 1]]),
    ],
)
def test_affine_disk_matches_independent_positive_area_at_two_orders(matrix):
    centre = np.array([10.37, 12.81])
    radius = 4.3
    covariance = np.array([[0.6, 0.2], [0.2, 1.4]])
    pixels = np.array([[10, 12], [23, 31], [30, 25]])
    result = batch.finite_shape_probabilities(
        pixels,
        [[("circle", centre, radius)]],
        **options(homography=matrix, psf_covariance=covariance),
    )
    inverse = np.linalg.inv(matrix[:2, :2])
    plane_covariance = inverse @ covariance @ inverse.T
    expected = []
    for pixel in pixels:
        point = inverse @ (pixel + 0.5 - matrix[:2, 2])
        low = independent_disk(point, centre, radius, plane_covariance, 128)
        high = independent_disk(point, centre, radius, plane_covariance, 256)
        assert abs(low - high) < 3e-11
        expected.append(high)
    assert result.statuses == ("resolved",) * len(pixels)
    np.testing.assert_allclose(result.probabilities, expected, rtol=0, atol=2e-10)
    assert result.reflected == (np.linalg.det(matrix) < 0)


def test_annulus_keeps_far_angular_winding_and_hole_role():
    centre = (25.5, 25.5)
    result = batch.finite_shape_probabilities(
        [[25, 25], [45, 25]], [[("circle", centre, 12)], [("circle", centre, 2)]], **options()
    )
    assert result.statuses == ("resolved", "resolved")
    expected = math.exp(-2) - math.exp(-72)
    assert abs(result.probabilities[0] - expected) < 2e-10
    assert abs(result.probabilities[1]) < 2e-10
    assert result.tail_bounds[1] > 0  # Gaussian tail not replaced by exact zero.
    assert result.diagnostics.batched_queries == 2


def test_complex_line_arc_outer_and_disjoint_holes_match_existing_kernel():
    radius, fraction = 13.0, 0.3
    centre = np.array([25.5, 25.5])
    h = radius * math.sqrt(1 - fraction * fraction)
    a, b = tuple(centre + (radius * fraction, h)), tuple(centre + (radius * fraction, -h))
    outer = [("arc", a, tuple(centre - (radius, 0)), b), ("line", b, a)]
    rings = [outer, [("circle", (20.0, 25.5), 1.1)], rectangle((25, 22), (26, 23), True)]
    pixels = np.array([[12, 25], [20, 25], [25, 22], [29, 25], [25, 40]])
    kwargs = options(psf_covariance=np.array([[1, 0.4], [0.4, 2]]))
    actual = batch.finite_shape_probabilities(pixels, rings, **kwargs)
    expected = scalar.finite_shape_probabilities(pixels, rings, **kwargs)
    assert actual.statuses == expected.statuses == ("resolved",) * len(pixels)
    np.testing.assert_allclose(actual.probabilities, expected.probabilities, rtol=0, atol=2e-9)


@pytest.mark.parametrize("scale", [1.0, -7.0, 1e80])
def test_homogeneous_scale_and_large_crop_translation_preserve_means(scale):
    # Same LOCAL analytic disk at tiny radius and huge world centre. Query
    # constants must cancel before whitening, rather than subtract large whites.
    pixels = np.array([[50, 50], [51, 50]])
    centre = np.array([1e6 + 0.501, 1e6 + 0.5])
    matrix = np.array([[1, 0, -1e6 + 50], [0, 1, -1e6 + 50], [0, 0, 1.0]])
    kwargs = options(homography=matrix * scale, psf_covariance=np.diag([1e-10, 4e-10]))
    actual = batch.finite_shape_probabilities(pixels, [[("circle", centre, 0.001)]], **kwargs)
    old = scalar.finite_shape_probabilities(pixels, [[("circle", centre, 0.001)]], **kwargs)
    assert actual.statuses == old.statuses
    np.testing.assert_allclose(actual.probabilities, old.probabilities, rtol=0, atol=2e-9)


def test_giant_boundary_layer_uses_adaptive_fallback_and_independent_area():
    result = batch.finite_shape_probabilities(
        [[10000, 10000]],
        [[("circle", (0.5, 10000.5), 10000)]],
        **options(sensor_shape=(20010, 20010)),
    )
    nodes, weights = np.polynomial.legendre.leggauss(64)
    y = 12 * nodes
    # At the rightmost boundary, stable x_upper-R=-y²/(R+sqrt(R²-y²)).
    upper = -y * y / (10000 + np.sqrt(10000**2 - y * y))
    expected = 12 * math.fsum(
        weights * np.exp(-y * y / 2) / math.sqrt(math.tau) * np.array([phi(x) for x in upper])
    )
    assert result.statuses == ("resolved",)
    assert abs(result.probabilities[0] - expected) < 2e-10
    assert result.diagnostics.fallback_queries == 1
    assert result.diagnostics.batch_evaluations == 0
    assert result.diagnostics.fallback_reasons == ("partition_limit",)


def test_zero_green_coefficient_limit_has_no_eager_divide_warning():
    nodes = scalar._RULES[12][0]
    t = 0.5 + nodes[0] / 2
    curve = scalar._Curve(np.array([0.5 - t, 0.5]), np.array([1.0, 0.0]), 0, 0, 0, 1)
    value, absolute = batch._rule(curve, np.eye(2), np.array([[-0.5, -0.5]]), 1.0, 0, 1, 12)
    assert value[0] == 0 and absolute[0] == 0


@pytest.mark.parametrize("budget", [1, 2, 39, 120, 1000])
def test_small_budget_preflight_fallback_preserves_complete_ordered_old_result(budget):
    pixels = [[20, 20], [20, 10], [31, 20]]
    rings = [[("circle", (20.5, 20.5), 10)]]
    kwargs = options(max_evaluations=budget)
    result = batch.finite_shape_probabilities(pixels, rings, **kwargs)
    old = scalar.finite_shape_probabilities(pixels, rings, **kwargs)
    assert result.probabilities == old.probabilities and result.statuses == old.statuses
    assert result.estimated_errors == old.estimated_errors
    assert result.tail_bounds == old.tail_bounds
    assert result.evaluations == old.evaluations <= budget
    assert result.panels == old.panels
    assert result.diagnostics.batch_evaluations == 0
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("panels", [1, 8, 32])
def test_per_query_panel_limit_is_not_bypassed_by_vectorization(panels):
    result = batch.finite_shape_probabilities(
        [[20, 10], [31, 20]], [[("circle", (20.5, 20.5), 10)]], **options(max_panels=panels)
    )
    assert result.diagnostics.batch_panels == 0
    assert result.panels <= 2 * panels and len(result.statuses) == 2


def test_nonzero_perspective_is_never_approximated_as_affine():
    matrix = np.array([[1, 0, 0], [0, 1, 0], [1e-12, 0, 1]])
    rings = [[("circle", (20.5, 20.5), 10)]]
    kwargs = options(homography=matrix)
    result = batch.finite_shape_probabilities([[20, 10], [31, 20]], rings, **kwargs)
    old = scalar.finite_shape_probabilities([[20, 10], [31, 20]], rings, **kwargs)
    assert not result.diagnostics.affine
    assert result.diagnostics.batch_evaluations == 0
    assert result.probabilities == old.probabilities
    assert result.evaluations == old.evaluations


def test_workspace_limit_is_preflighted_and_fallback_work_remains_visible():
    rings = [[("circle", (20.5, 20.5), 10)]]
    small = batch.finite_shape_probabilities(
        [[20, 10], [31, 20]], rings, **options(memory_limit_bytes=1)
    )
    assert small.diagnostics.workspace_peak_bytes == 0
    assert small.diagnostics.fallback_queries == 2
    assert small.evaluations == small.diagnostics.fallback_evaluations
    bounded = batch.finite_shape_probabilities(
        [[20, 10], [31, 20]], rings, **options(memory_limit_bytes=24000)
    )
    assert bounded.diagnostics.workspace_peak_bytes <= 24000
    assert bounded.statuses == ("resolved", "resolved")


def test_failed_batch_is_charged_before_real_scalar_fallback(monkeypatch):
    original = batch._rule
    calls = []

    def first_failure(*args, **kwargs):
        calls.append(args[-1])
        if len(calls) == 1:
            raise ArithmeticError("injected rule failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(batch, "_rule", first_failure)
    result = batch.finite_shape_probabilities(
        [[30, 20], [30, 21]], [[("circle", (20.5, 20.5), 10)]], **options()
    )
    assert result.statuses == ("resolved", "resolved")
    assert result.diagnostics.fallback_queries == 2
    assert result.diagnostics.batch_evaluations == 2 * 38
    assert result.diagnostics.batch_panels == 2
    assert (
        result.evaluations
        == result.diagnostics.batch_evaluations + result.diagnostics.fallback_evaluations
    )
    assert result.panels == result.diagnostics.batch_panels + result.diagnostics.fallback_panels
    assert result.diagnostics.discarded_batch_queries == 2
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize(
    "changes",
    [
        {"memory_limit_bytes": True},
        {"memory_limit_bytes": 0},
        {"max_evaluations": True},
        {"probability_tolerance": False},
        {"psf_covariance": [[1, 2], [2, 1]]},
    ],
)
def test_invalid_controls_or_covariance_are_refused(changes):
    kwargs = options()
    kwargs.update(changes)
    with pytest.raises(ValueError):
        batch.finite_shape_probabilities([[20, 20]], [[("circle", (20.5, 20.5), 10)]], **kwargs)


@pytest.mark.parametrize("pixels", [[[True, 20]], [[20.0, 20.0]], [[20, 20], [20, 20]], [[80, 20]]])
def test_fixed_integer_observation_contract_is_preserved(pixels):
    with pytest.raises(ValueError):
        batch.finite_shape_probabilities(pixels, [[("circle", (20.5, 20.5), 10)]], **options())


@pytest.fixture(scope="module")
def original_centre_api():
    """Saved pre-dispatch API AND kernel, isolated from current dispatch hooks."""
    package = "backend._affine_original_contract"
    names = (
        package,
        package + ".fitting",
        package + ".finite_shape",
        package + ".finite_centre_fit",
    )
    assert all(name not in sys.modules for name in names)
    namespace = types.ModuleType(package)
    namespace.__path__ = []
    sys.modules[package] = namespace
    sys.modules[package + ".fitting"] = fitting
    fixtures = Path(__file__).resolve().parents[1] / "studies/fixtures/finite-affine-batch-v1"
    try:
        expected_hashes = {
            "finite_shape": "9102f9e19127ce3666d2bf8744b0356bcc923060f2b142c8a2cbd50a363f5380",
            "finite_centre_fit": "e2019bcc8b5813c0957967b469baf44bbdd784f50855418852c2686cc48b9ab4",
        }
        for stem in ("finite_shape", "finite_centre_fit"):
            path = fixtures / ("original-" + stem.replace("_", "-") + ".py.txt")
            module = types.ModuleType(package + "." + stem)
            module.__package__, module.__file__ = package, str(path)
            sys.modules[module.__name__] = module
            source = path.read_bytes()
            assert hashlib.sha256(source).hexdigest() == expected_hashes[stem]
            exec(compile(source, str(path), "exec"), module.__dict__)  # noqa: S102 - hash-pinned original test fixture
        yield module
    finally:
        for name in reversed(names):
            sys.modules.pop(name, None)


def independent_segment(point, centre, radius, fraction, covariance, order):
    """Positive area of disc intersect x<=Cx+Rf, conditional on Y.

    Split at the actual circle/chord integration transitions; this oracle has
    no Green flux, shape derivatives or production segmentation dependency.
    """
    nodes, weights = np.polynomial.legendre.leggauss(order)
    transition = math.acos(abs(fraction))
    cuts = [-math.pi / 2, -transition, transition, math.pi / 2]
    variance = covariance[1, 1]
    sd = math.sqrt(covariance[0, 0] - covariance[0, 1] ** 2 / variance)
    contributions = []
    for start, end in pairwise(cuts):
        angle = (start + end) / 2 + (end - start) / 2 * nodes
        y = centre[1] + radius * np.sin(angle)
        width = radius * np.cos(angle)
        lower = centre[0] - width
        upper = np.minimum(centre[0] + width, centre[0] + radius * fraction)
        mean = point[0] + covariance[0, 1] / variance * (y - point[1])
        mass = np.array(
            [
                max(0.0, phi((hi - m) / sd) - phi((lo - m) / sd))
                for hi, lo, m in zip(upper, lower, mean)
            ]
        )
        density = np.exp(-((y - point[1]) ** 2) / (2 * variance)) / math.sqrt(math.tau * variance)
        contributions.append(
            (end - start) / 2 * math.fsum(weights * radius * np.cos(angle) * density * mass)
        )
    return math.fsum(contributions)


@pytest.mark.parametrize(
    "matrix",
    [
        np.eye(3),
        np.array([[-1.0, 0.2, 45], [0.1, 1.1, -3], [0, 0, 1.0]]),
    ],
)
def test_public_parametric_d_uses_batch_but_keeps_base_schema_and_independent_means(
    monkeypatch, matrix
):
    centre, radius, fraction = np.array([20.37, 19.81]), 6.4, 0.27
    covariance = np.array([[1.1, 0.4], [0.4, 2.3]])
    pixels = np.array([[17, 15], [20, 19], [22, 21], [26, 20]])
    observed_dispatch = []
    original = batch._probabilities

    def spy(*args, **kwargs):
        result = original(*args, **kwargs)
        observed_dispatch.append(result.diagnostics)
        return result

    monkeypatch.setattr(batch, "_probabilities", spy)
    actual = centre_fit.circular_segment_probabilities(
        pixels,
        radius,
        fraction,
        centre=centre,
        **options(homography=matrix, psf_covariance=covariance),
    )
    assert len(observed_dispatch) == 1
    assert observed_dispatch[0].batched_queries == len(pixels)
    assert type(actual) is scalar.FiniteShapeResult
    assert set(asdict(actual)) == {
        "probabilities",
        "statuses",
        "estimated_errors",
        "tail_bounds",
        "evaluations",
        "panels",
        "chart_margin",
        "reflected",
        "topology_validated",
        "quadrature_certified",
    }
    assert not hasattr(actual, "diagnostics")
    assert actual.statuses == ("resolved",) * len(pixels)
    inverse = np.linalg.inv(matrix[:2, :2])
    plane_covariance = inverse @ covariance @ inverse.T
    expected = []
    for pixel in pixels:
        point = inverse @ (pixel + 0.5 - matrix[:2, 2])
        low = independent_segment(point, centre, radius, fraction, plane_covariance, 64)
        high = independent_segment(point, centre, radius, fraction, plane_covariance, 128)
        assert abs(low - high) < 2e-11
        expected.append(high)
    np.testing.assert_allclose(actual.probabilities, expected, rtol=0, atol=2e-10)
    json.dumps(asdict(actual), allow_nan=False)


@pytest.mark.parametrize(
    "perspective,homogeneous_scale", [(1e-3, 1.0), (1e-12, 1.0), (1e-320, 1e12)]
)
def test_public_d_raw_nonzero_perspective_never_dispatches_even_if_normalization_underflows(
    monkeypatch, original_centre_api, perspective, homogeneous_scale
):
    matrix = np.eye(3) * homogeneous_scale
    matrix[2, 0] = perspective
    assert matrix[2, 0] != 0
    if perspective == 1e-320:
        with np.errstate(under="ignore"):
            assert (matrix / np.max(abs(matrix)))[2, 0] == 0

    def forbidden(*args, **kwargs):
        raise AssertionError("raw nonzero projective map entered affine evaluator")

    monkeypatch.setattr(batch, "_probabilities", forbidden)
    kwargs = options(homography=matrix, psf_covariance=[[1.1, 0.4], [0.4, 2.3]])
    parameters = {"centre": (20.37, 19.81), "normal": (1.0, 0.0)}
    pixels = [[17, 15], [20, 19], [22, 21], [26, 20]]
    actual = centre_fit.circular_segment_probabilities(pixels, 6.4, 0.27, **parameters, **kwargs)
    original = original_centre_api.circular_segment_probabilities(
        pixels, 6.4, 0.27, **parameters, **kwargs
    )
    assert asdict(actual) == asdict(original)


@pytest.mark.parametrize("budget", [1, 2, 39])
def test_public_d_low_total_work_keeps_every_query_and_never_fabricates_completion(budget):
    pixels = [[17, 15], [20, 19], [22, 21], [26, 20]]
    actual = centre_fit.circular_segment_probabilities(
        pixels, 6.4, 0.27, centre=(20.37, 19.81), **options(max_evaluations=budget)
    )
    assert type(actual) is scalar.FiniteShapeResult
    assert actual.statuses == ("work_limit",) * len(pixels)
    assert actual.probabilities == (None,) * len(pixels)
    assert actual.estimated_errors == (None,) * len(pixels)
    assert actual.evaluations <= budget
    assert not actual.quadrature_certified and not actual.topology_validated
    json.dumps(asdict(actual), allow_nan=False)


@pytest.mark.parametrize("homogeneous_scale", [1e8, 1e12])
def test_public_ring_raw_perspective_underflow_still_uses_exact_original_fallback(
    monkeypatch, original_centre_api, homogeneous_scale
):
    matrix = np.eye(3) * homogeneous_scale
    matrix[2, 0] = 1e-320
    with np.errstate(under="ignore"):
        assert (matrix / np.max(abs(matrix)))[2, 0] == 0

    def forbidden(*args, **kwargs):
        raise AssertionError("raw nonzero perspective entered shared affine panels")

    monkeypatch.setattr(batch, "_batch", forbidden)
    pixels = [[20, 10], [31, 20]]
    rings = [[("circle", (20.5, 20.5), 10)]]
    kwargs = options(homography=matrix)
    actual = batch.finite_shape_probabilities(pixels, rings, **kwargs)
    original = original_centre_api.finite.finite_shape_probabilities(pixels, rings, **kwargs)
    assert not actual.diagnostics.affine and actual.diagnostics.batch_evaluations == 0
    assert actual.diagnostics.fallback_queries == len(pixels)
    public_payload = asdict(actual)
    public_payload.pop("diagnostics")
    assert public_payload == asdict(original)
