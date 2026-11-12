"""Conditional Gaussian controls with independent CDF/positive-area observations."""

import copy
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from backend import fitting


def rotation(degrees):
    angle = math.radians(degrees)
    return np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])


def independent_study():
    path = Path(__file__).resolve().parents[1] / "studies/verification/corner-anisotropy-v1.py"
    spec = importlib.util.spec_from_file_location("corner_area_oracle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def matched_corner():
    oracle = independent_study()
    import json

    plan = json.loads(oracle.PLAN.read_text())
    case = next(row for row in plan["cases"] if row["id"] == "right-axis-anisotropy")
    return oracle.half_level_points(case, plan["oracle"]), oracle.geometry(case), case


@pytest.mark.parametrize("turn", [0, 19, 77, 143])
@pytest.mark.parametrize("spreads", [(0.6, 2.0), (2.0, 0.6), (0.4, 4.0)])
def test_sharp_quadrant_matches_independent_separable_cdfs_after_rotation(turn, spreads):
    points = np.random.default_rng(18).uniform(-5, 5, (31, 2))
    std = np.array(spreads)
    expected = np.prod([
        [0.5 * math.erfc(float(v) / s / math.sqrt(2)) for v in points[:, axis]]
        for axis, s in enumerate(std)
    ], axis=0)
    rotate = rotation(turn)
    covariance = rotate @ np.diag(std**2) @ rotate.T
    actual = fitting.corner_level(points @ rotate.T + [27, -14], [27, -14], 0,
                                  math.radians(turn), math.pi / 2, 1,
                                  covariance=covariance)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=6e-8)


@pytest.mark.parametrize("sweep", [30, 60, 90, 120, 150])
def test_correlated_sharp_vertex_matches_exact_gaussian_orthant_probability(sweep):
    covariance = np.array([[0.8, 0.5], [0.5, 3.0]])
    half = math.radians(sweep) / 2
    normals = np.array([[math.cos(half), -math.sin(half)], [math.cos(half), math.sin(half)]])
    rho = float(normals[0] @ covariance @ normals[1]) / math.sqrt(
        float(normals[0] @ covariance @ normals[0]) * float(normals[1] @ covariance @ normals[1])
    )
    expected = 0.25 + math.asin(rho) / (2 * math.pi)
    actual = fitting.corner_level([[0, 0]], [0, 0], 0, -half, 2 * half, 1,
                                  covariance=covariance)
    assert actual[0] == pytest.approx(expected, abs=6e-8)


@pytest.mark.parametrize("radius", [0, 0.6, 4, 40])
def test_supplied_isotropic_covariance_preserves_scalar_forward_model(radius):
    points = np.random.default_rng(11).uniform(-5, 5, (31, 2))
    sigma = 1.4
    old = fitting.corner_level(points, [0, 0], radius, -.7, 1.4, sigma)
    supplied = fitting.corner_level(points, [0, 0], radius, -.7, 1.4, sigma,
                                    covariance=np.eye(2) * sigma**2)
    np.testing.assert_allclose(supplied, old, rtol=0, atol=6e-8)


@pytest.mark.parametrize("scale,turn,reflect", [(1, 37, False), (.3, 73, True), (4, -29, False)])
def test_rounded_corner_agrees_with_independent_positive_area_under_frame_changes(matched_corner, scale, turn, reflect):
    points, geo, case = matched_corner
    transform = rotation(turn) @ np.diag([scale, -scale if reflect else scale])
    covariance = transform @ geo["covariance"] @ transform.T
    half = math.pi / 4
    start = math.radians(turn) - half
    actual = fitting.corner_level(points @ transform.T + [13, 21], [13, 21], case["radius"] * scale,
                                  start, 2 * half, geo["sigma"] * scale, covariance=covariance)
    np.testing.assert_allclose(actual, .5, rtol=0, atol=6e-8)


def test_known_radius_is_recovered_where_scalar_model_is_biased(matched_corner):
    points, geo, case = matched_corner
    args = (points, geo["lines"], geo["v"], geo["inward"], case["radius"], geo["sigma"], 0, 1)
    scalar = fitting._exact_fillet(*args)
    directional = fitting._exact_fillet(*args, covariance=geo["covariance"])
    assert scalar is not None and scalar[0] - case["radius"] > .5
    assert directional is not None
    assert directional[0] == pytest.approx(case["radius"], abs=5e-5)
    assert directional[2] < 1e-6
    assert directional[4] is None


def corner_primitives(points, geo, radius=4):
    n = len(points)
    arc = fitting.Primitive("arc", {"c": (0., 0.), "r": radius, "mid": (radius, 0.)}, 0, 0, (8, n - 9))
    line1 = fitting.Primitive("line", {"c": tuple(geo["lines"][0][0]), "d": tuple(geo["lines"][0][1])}, 0, 0, (0, 8))
    line2 = fitting.Primitive("line", {"c": tuple(geo["lines"][1][0]), "d": tuple(geo["lines"][1][1])}, 0, 0, (n - 9, n - 1))
    return [line1, arc, line2]


def test_actual_constrained_fit_uses_supplied_covariance_and_preserves_tangency(matched_corner):
    points, geo, _ = matched_corner
    prims = corner_primitives(points, geo)
    fitting.fit_fillets(points, prims, .05, geo["sigma"], geo["covariance"])
    arc = next(p for p in prims if p.kind == "arc")
    assert not arc.data.get("blur_unresolved")
    assert arc.data["r"] == pytest.approx(4, abs=5e-5)
    before = arc.data["r"]
    fitting.correct_blur(prims, geo["sigma"])
    assert arc.data["r"] == before
    for c, d in geo["lines"]:
        n = np.array([-d[1], d[0]])
        assert abs((np.asarray(arc.data["c"]) - c) @ n) == pytest.approx(4, abs=5e-5)


def test_unresolved_covariant_integral_never_becomes_a_scalar_radius_or_sharp_bound(matched_corner, monkeypatch):
    points, geo, _ = matched_corner
    prims = corner_primitives(points, geo)
    before = copy.deepcopy(prims[1].data)
    original = fitting.corner_level

    def unresolved(*args, **kwargs):
        if kwargs.get("covariance") is not None:
            raise ValueError("independent injected quadrature refusal")
        return original(*args, **kwargs)

    monkeypatch.setattr(fitting, "corner_level", unresolved)
    fitting.fit_fillets(points, prims, .05, geo["sigma"], geo["covariance"])
    assert len(prims) == 3
    arc = prims[1]
    assert arc.data["blur_unresolved"] and math.isinf(arc.data["r_sd"])
    fitting.correct_blur(prims, geo["sigma"])
    assert arc.data["r"] == before["r"] and arc.data["c"] == before["c"]
    assert all("sharp_bound" not in p.data and not p.data.get("sharp") for p in prims)


@pytest.mark.parametrize("covariance", [
    [[1, 100], [0, 1]], [[1, 2], [2, 1]], [[0, 0], [0, 1]],
    [[1, float("nan")], [0, 1]], [[1, 0], [0, 1e-18]], [1, 2],
])
def test_unsupported_covariance_is_explicit(covariance):
    with pytest.raises(ValueError, match="covariance"):
        fitting.corner_level([[0, 0]], [0, 0], 1, 0, math.pi / 2, 1, covariance=covariance)


def test_covariant_work_exhaustion_is_explicit():
    with pytest.raises(ValueError, match="work limit"):
        fitting.corner_level(np.zeros((4096, 2)), [0, 0], 1, 0, math.pi / 2, 1,
                             covariance=np.diag([.36, 4]))


@pytest.mark.parametrize("spreads", [(.4, 4), (.2, 4)])
def test_stronger_rounded_anisotropy_agrees_with_independent_higher_order_area(spreads):
    oracle = independent_study()
    points = np.random.default_rng(19).uniform(-4, 4, (15, 2))
    covariance = np.diag(np.array(spreads)**2)
    lower = oracle.corner_probability(points, 4, math.pi / 2, covariance, order=64, panel_width=.125)
    higher = oracle.corner_probability(points, 4, math.pi / 2, covariance, order=128, panel_width=.125)
    np.testing.assert_allclose(lower, higher, rtol=0, atol=1e-9)
    actual = fitting.corner_level(points, [0, 0], 4, -math.pi / 4, math.pi / 2, 1,
                                  covariance=covariance)
    np.testing.assert_allclose(actual, higher, rtol=0, atol=6e-8)


def test_unresolved_strong_anisotropy_is_refused_instead_of_silently_accepted():
    points = np.random.default_rng(19).uniform(-4, 4, (15, 2))
    with pytest.raises(ValueError, match="work limit"):
        fitting.corner_level(points, [0, 0], 4, -math.pi / 4, math.pi / 2, 1,
                             covariance=np.diag([.01**2, 4**2]))


def test_finite_sharp_bound_requires_an_actual_crossing_bracket(matched_corner):
    points, geo, _ = matched_corner
    # With this explicitly huge positional allowance the finite radius search never
    # brackets a distinguishable corner. Its endpoint cannot become a finite bound.
    actual = fitting._exact_fillet(points, geo["lines"], geo["v"], geo["inward"], 4,
                                   geo["sigma"], 1000, 1, covariance=geo["covariance"])
    assert actual is None
