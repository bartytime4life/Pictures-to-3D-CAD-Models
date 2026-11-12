"""Coordinate-change invariants, separate from finite-camera model accuracy.

An arbitrary observed contour and every length-valued input must give the same
geometric result after a known homothety. These checks exercise actual fitting
stages, not a second implementation of the radius correction.
"""

import copy
import math

import numpy as np
import pytest
import shapely
from shapely.geometry import LineString

from backend import edges, fitting


@pytest.mark.parametrize("scale", [1.0, 0.8, 0.6])
def test_actual_circle_fit_and_top_face_map_transport_the_radius_correction(scale):
    angles = np.linspace(0, 2 * math.pi, 128, endpoint=False)
    normals = np.column_stack([np.cos(angles), np.sin(angles)])
    centre = np.array([30.0, 40.0])
    points = centre + 6 * normals
    original = fitting.fit_ring(points, 0.2, 3.0)
    assert original is not None and [p.kind for p in original] == ["circle"]
    fitting.correct_blur(original, 2.0)
    mapped, top = edges.correct_thickness(points, normals, centre, 100.0, 100 * (1 - scale))
    assert top.all()
    transported = fitting.fit_ring(mapped, 0.2 * scale, 3.0 * scale)
    untransported = copy.deepcopy(transported)
    fitting.correct_blur(transported, 2.0, blur_scales=np.where(top, scale, 1.0))
    fitting.correct_blur(untransported, 2.0)
    np.testing.assert_allclose(transported[0].data["c"], centre, atol=1e-11)
    expected = scale * original[0].data["r"]
    assert transported[0].data["r"] == pytest.approx(expected, abs=1e-11)
    if scale == 0.8:
        assert untransported[0].data["r"] - expected > 0.14
    assert not transported[0].data.get("blur_frame_mixed")


def test_free_arc_uses_its_wrapping_support_rather_than_other_ring_points():
    original = [fitting.Primitive("arc", {"c": (0.0, 0.0), "r": 10.0}, 0, 0, (6, 1))]
    mapped = [fitting.Primitive("arc", {"c": (0.0, 0.0), "r": 6.0}, 0, 0, (6, 1))]
    scales = np.array([0.6, 0.6, 1.0, 1.0, 1.0, 1.0, 0.6, 0.6])
    fitting.correct_blur(original, 2.0)
    fitting.correct_blur(mapped, 2.0, blur_scales=scales)
    assert mapped[0].data["r"] == pytest.approx(0.6 * original[0].data["r"], abs=1e-12)
    assert not mapped[0].data.get("blur_frame_mixed")


def test_mixed_free_curve_retains_the_explicit_legacy_approximation_without_averaging():
    legacy = [fitting.Primitive("arc", {"c": (0.0, 0.0), "r": 6.0}, 0, 0, (6, 2))]
    mixed = copy.deepcopy(legacy)
    fitting.correct_blur(legacy, 2.0)
    fitting.correct_blur(mixed, 2.0, blur_scales=[0.6, 0.6, 1, 1, 1, 1, 0.6, 0.6])
    assert mixed[0].data["r"] == legacy[0].data["r"]
    assert mixed[0].data["blur_frame_mixed"]
    assert not mixed[0].data.get("blur_modelled")
    assert "r_sd" not in mixed[0].data and "sharp_bound" not in mixed[0].data


def capsule_points(angle=0.0):
    outline = LineString([(-20.0, 0.0), (20.0, 0.0)]).buffer(12.0, quad_segs=64).exterior
    points = np.asarray(shapely.segmentize(outline, 0.4).coords)[:-1]
    rotate = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    return points @ rotate.T, rotate


def capsule_chain(points, sigma, covariance, *, scale=1.0, scales=None):
    prims = fitting.fit_ring(points, 0.2 * scale, 3.0 * scale)
    assert prims is not None
    fitting.refit_lines(points, prims, margin=3 * sigma, blur_scales=scales)
    fitting.fit_fillets(points, prims, 0.2 * scale, sigma, covariance, blur_scales=scales)
    fitting.correct_blur(prims, sigma, blur_scales=scales)
    return prims


@pytest.mark.parametrize("scale", [0.6, 0.8])
@pytest.mark.parametrize("angle,directional", [(0.0, False), (0.0, True), (0.61, True)])
def test_actual_full_capsule_chain_commutes_in_scalar_and_directional_frames(scale, angle, directional):
    # The specified contour need not be an exact Gaussian half-level contour:
    # coordinate equivariance must hold even when the physical model is mismatched.
    points, rotate = capsule_points(angle)
    covariance = rotate @ np.diag([1.0, 4.0]) @ rotate.T if directional else None
    sigma = math.sqrt(2.0) if directional else 2.0
    original = capsule_chain(points, sigma, covariance)
    mapped = capsule_chain(points * scale, sigma, covariance, scale=scale,
                           scales=np.full(len(points), scale))
    original_caps = sorted((p for p in original if p.data.get("end_cap")), key=lambda p: p.data["c"][0])
    mapped_caps = sorted((p for p in mapped if p.data.get("end_cap")), key=lambda p: p.data["c"][0])
    assert len(original_caps) == len(mapped_caps) == 2
    for before, after in zip(original_caps, mapped_caps):
        np.testing.assert_allclose(after.data["c"], np.asarray(before.data["c"]) * scale, atol=2e-9)
        assert after.data["r"] == pytest.approx(before.data["r"] * scale, abs=2e-10)
        assert not after.data.get("blur_frame_mixed")


def test_mixed_cap_is_marked_approximate_without_a_radius_confidence_claim():
    points, _ = capsule_points()
    scales = np.where(points[:, 1] > 0, 0.8, 1.0)
    prims = capsule_chain(points, 2.0, np.diag([1.0, 4.0]), scales=scales)
    caps = [p for p in prims if p.data.get("end_cap")]
    assert len(caps) == 2 and all(p.data.get("blur_frame_mixed") for p in caps)
    assert all(not p.data.get("blur_modelled") and "r_sd" not in p.data for p in caps)


def test_unsupported_covariance_does_not_enter_the_parallel_cap_solver():
    points, _ = capsule_points()
    prims = capsule_chain(points, 2.0, np.ones((2, 2)))
    arcs = [p for p in prims if p.kind == "arc"]
    assert len(arcs) == 2
    assert all(p.data.get("blur_unresolved") for p in arcs)
    assert not any(p.data.get("end_cap") for p in arcs)


def test_line_refit_exclusion_window_uses_the_mapped_length_unit():
    x = np.linspace(0.0, 20.0, 81)
    points = np.column_stack([x, 0.015 * (x - 8) ** 2])
    prims = [
        fitting.Primitive("arc", {"c": (3.0, 0.0)}, 0, 0),
        fitting.Primitive("line", {"c": (10.0, 0.0), "d": (1.0, 0.0)}, 0, 0, (0, 80)),
        fitting.Primitive("arc", {"c": (17.0, 0.0)}, 0, 0),
    ]
    mapped = copy.deepcopy(prims)
    scale = 0.6
    for p in mapped:
        p.data["c"] = tuple(np.asarray(p.data["c"]) * scale)
    fitting.refit_lines(points, prims, margin=3.0)
    fitting.refit_lines(points * scale, mapped, margin=3.0, blur_scales=np.full(len(points), scale))
    np.testing.assert_allclose(mapped[1].data["c"], np.asarray(prims[1].data["c"]) * scale, atol=1e-12)
    np.testing.assert_allclose(mapped[1].data["d"], prims[1].data["d"], atol=1e-12)
    assert mapped[1].rms == pytest.approx(prims[1].rms * scale, abs=1e-12)


@pytest.mark.parametrize("scales", [[], [[0.8]], [0.0], [-0.8], [math.nan], [math.inf]])
def test_invalid_blur_scale_context_is_refused_before_radius_change(scales):
    prims = [fitting.Primitive("circle", {"c": (0.0, 0.0), "r": 6.0}, 0, 0)]
    with pytest.raises(ValueError, match="blur scales"):
        fitting.correct_blur(prims, 2.0, blur_scales=scales)
    assert prims[0].data["r"] == 6.0


def test_point_context_must_match_the_actual_measurement_array():
    points, _ = capsule_points()
    prims = fitting.fit_ring(points, 0.2, 3.0)
    with pytest.raises(ValueError, match="bound to every point"):
        fitting.fit_fillets(points, prims, 0.2, 2.0, blur_scales=[0.8])
    with pytest.raises(ValueError, match="bound to every point"):
        fitting.refit_lines(points, prims, margin=6.0, blur_scales=[0.8])


def scalar_corner():
    from tests.test_anisotropic_corners import corner_primitives, independent_study

    oracle = independent_study()
    case = {"radius": 4, "sweep_degrees": 90, "covariance": [[1.44, 0], [0, 1.44]],
            "rotation_degrees": 0, "complement": False}
    geometry = oracle.geometry(case)
    import json

    plan = json.loads(oracle.PLAN.read_text())
    points = oracle.half_level_points(case, plan["oracle"])
    prims = corner_primitives(points, geometry)
    scales = np.ones(len(points))
    scales[0] = 0.8
    return points, prims, scales


def test_mixed_scalar_corner_retains_legacy_geometry_but_not_radius_confidence():
    points, prims, scales = scalar_corner()
    legacy = copy.deepcopy(prims)
    fitting.fit_fillets(points, legacy, 0.2, 1.2)
    fitting.correct_blur(legacy, 1.2)
    fitting.fit_fillets(points, prims, 0.2, 1.2, blur_scales=scales)
    fitting.correct_blur(prims, 1.2, blur_scales=scales)
    assert len(prims) == len(legacy) == 3
    assert prims[1].data["blur_frame_mixed"] and math.isinf(prims[1].data["r_sd"])
    assert not prims[1].data.get("blur_unresolved")
    assert prims[1].data["r"] == legacy[1].data["r"]
    np.testing.assert_array_equal(prims[1].data["c"], legacy[1].data["c"])
    assert all(not p.data.get("sharp") and "sharp_bound" not in p.data for p in prims)


@pytest.mark.parametrize("radius", [0.0, -1.0, math.nan, math.inf])
def test_unusable_mixed_scalar_model_radius_retains_positive_geometric_arc(radius, monkeypatch):
    points, prims, scales = scalar_corner()
    before = copy.deepcopy(prims[1].data)
    monkeypatch.setattr(fitting, "_exact_fillet", lambda *a, **kw: (radius, 0.01, 0, 0, 5))
    fitting.fit_fillets(points, prims, 0.2, 1.2, blur_scales=scales)
    fitting.correct_blur(prims, 1.2, blur_scales=scales)
    assert len(prims) == 3
    assert prims[1].data["blur_frame_mixed"] and prims[1].data["blur_correction_withheld"]
    assert math.isinf(prims[1].data["r_sd"])
    assert prims[1].data["r"] == before["r"]
    np.testing.assert_array_equal(prims[1].data["c"], before["c"])
    assert not prims[1].data.get("blur_modelled") and "fillet" not in prims[1].data
    assert all(not p.data.get("sharp") and "sharp_bound" not in p.data for p in prims)


def test_mixed_scalar_corner_cannot_publish_stationary_model_sharp_bound(monkeypatch):
    points, prims, scales = scalar_corner()
    monkeypatch.setattr(fitting, "_exact_fillet", lambda *a, **kw: (4.0, 0.01, 0, 0, 5))
    fitting.fit_fillets(points, prims, 0.2, 1.2, blur_scales=scales)
    assert len(prims) == 3 and prims[1].data["r"] == 4.0
    assert math.isinf(prims[1].data["r_sd"])
    assert all(not p.data.get("sharp") and "sharp_bound" not in p.data for p in prims)
