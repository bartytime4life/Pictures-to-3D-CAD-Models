"""Source support of assembled geometry, using independently specified boundaries."""

import math

import cv2
import numpy as np
import pytest
import shapely
from fastapi.testclient import TestClient
from shapely.geometry import Polygon, box

from backend import app as api
from backend import edges, fitting, reference
from backend.tracing import trace_image
from tests import synthetic as S


def cap(radius, degrees, count=100):
    angle = np.linspace(-math.radians(degrees) / 2, math.radians(degrees) / 2, count)
    arc = radius * np.column_stack([np.cos(angle), np.sin(angle)])
    return np.vstack([arc, np.linspace(arc[-1], arc[0], count)[1:-1]])


@pytest.mark.parametrize("radius,degrees", [(100.0, 20.0), (300.0, 10.0)])
@pytest.mark.parametrize("turn,reverse,start", [(0, False, 0), (37, True, 42), (103, False, 117)])
def test_cap_keeps_its_boundary_dimensions_and_area(radius, degrees, turn, reverse, start):
    points = cap(radius, degrees)
    angle = math.radians(turn)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    points = np.roll(points[::-1] if reverse else points, start, axis=0) @ rotation.T + [151, -287]
    source = Polygon(points)
    prims = fitting.fit_ring(points, tol=0.3, min_line=4.0)
    segs, _ = reference._segments_for(points, prims, tolerance_px=0.2)
    described = Polygon(fitting.sample_segments(segs, 0.01))
    assert described.is_valid
    assert shapely.hausdorff_distance(described.boundary, source.boundary, densify=0.1) <= 0.2 + 1e-9
    assert np.max(np.abs(np.asarray(described.bounds) - source.bounds)) <= 0.2 + 1e-9
    assert abs(described.area - source.area) <= source.length * 0.2


@pytest.mark.parametrize("sides", [3, 4, 6])
def test_vertices_on_a_circle_do_not_turn_a_sparse_polygon_into_a_disc(sides):
    angle = np.arange(sides) * 2 * math.pi / sides
    points = 30 * np.column_stack([np.cos(angle), np.sin(angle)])
    prims = fitting.fit_ring(points, 0.15, 4.0)
    segs, _ = reference._segments_for(points, prims, 0.03)
    polygon = Polygon(fitting.sample_segments(segs, 0.01))
    assert math.isclose(polygon.area, Polygon(points).area, rel_tol=1e-10)
    assert all(seg[0] == "line" for seg in segs)


@pytest.mark.parametrize("stretch,reverse", [(1.0, False), (1.0, True), (1.02, True)])
def test_dense_circles_and_slightly_out_of_round_holes_keep_their_circle(stretch, reverse):
    angle = np.linspace(0, 2 * math.pi, 1000, endpoint=False)
    points = np.column_stack([30 * stretch * np.cos(angle), 30 * np.sin(angle)]) + [-81, 234]
    points = points[::-1] if reverse else points
    (circle,) = fitting.fit_ring(points, 0.15, 4.0)
    assert circle.kind == "circle"
    assert 30 - 1e-8 <= circle.data["r"] <= 30.31


def test_support_recomputes_deviation_after_blur_and_radius_equalisation():
    angle = np.linspace(0, 2 * math.pi, 1000, endpoint=False)
    unit = np.column_stack([np.cos(angle), np.sin(angle)])
    points = 6 * unit
    prims = fitting.fit_ring(points, 0.03, 1.0)
    fitting.correct_blur(prims, 2.0)
    assert prims[0].max_abs < 1e-10  # Stored pre-correction residual is obsolete.
    assert fitting.supported_fit(points, prims, 0.03)
    rings = [fitting.fit_ring(r * unit, 0.03, 1.0) for r in (30, 30.8)]
    fitting.equalise_radii(rings)
    assert all(fitting.supported_fit(r * unit, ring, 0.03) for r, ring in zip((30, 30.8), rings))


def test_support_sampling_limit_retains_the_source_instead_of_coarsening(monkeypatch):
    angle = np.linspace(0, 2 * math.pi, 1000, endpoint=False)
    points = 30 * np.column_stack([np.cos(angle), np.sin(angle)])
    prims = fitting.fit_ring(points, 0.15, 4.0)
    monkeypatch.setattr(fitting, "MAX_SUPPORT_SAMPLES", 8)
    assert not fitting.supported_fit(points, prims, 0.15)


def test_missing_subpixel_profiles_use_complete_coverage_without_changing_the_fit():
    angle = np.linspace(0, 2 * math.pi, 1000, endpoint=False)
    support = 30 * np.column_stack([np.cos(angle), np.sin(angle)])
    measured = support[(angle < 1) | (angle > 2.5)]
    # Without coverage evidence, the gap closes as a straight chord and a whole
    # circle is unsupported. The complete classified boundary supplies that evidence.
    assert fitting.fit_ring(measured, 0.15, 4.0) is None
    (circle,) = fitting.fit_ring(measured, 0.15, 4.0, support_points=support)
    assert circle.kind == "circle" and abs(circle.data["r"] - 30) < 1e-10


def test_a_real_unmeasured_closing_edge_is_not_paid_for_by_candidate_mismatch():
    angle = np.linspace(math.pi / 4, 7 * math.pi / 4, 451)
    measured = 100 * np.column_stack([np.cos(angle), np.sin(angle)])
    support = np.vstack([measured, np.linspace(measured[-1], measured[0], 201)[1:-1]])
    prims = fitting.fit_ring(measured, 0.3, 4.0, support_points=support)
    assert prims is None or [p.kind for p in prims] != ["circle"]
    full_angle = np.linspace(0, 2 * math.pi, 1000, endpoint=False)
    full = 100 * np.column_stack([np.cos(full_angle), np.sin(full_angle)])
    (circle,) = fitting.fit_ring(measured, 0.3, 4.0, support_points=full)
    assert circle.kind == "circle" and abs(circle.data["r"] - 100) < 1e-10


def test_independently_measured_localization_allowance_does_not_change_the_circle():
    angle = np.linspace(0, 2 * math.pi, 1000, endpoint=False)
    unit = np.column_stack([np.cos(angle), np.sin(angle)])
    measured, support = 30 * unit, 29.2 * unit
    assert fitting.fit_ring(measured, 0.15, 4, support_points=support) is None
    (circle,) = fitting.fit_ring(measured, 0.15, 4, support_points=support, support_error=0.8)
    assert circle.kind == "circle" and abs(circle.data["r"] - 30) < 1e-10


def test_complete_support_indices_survive_the_subpixel_rejection_passes(monkeypatch):
    """The ring keeps the first pass's support, indexed through the final pass's keep;
    the final pass starts where the provisional one crossed, and from the first pass's
    point where it found no crossing (edges.subpixel_rings)."""
    mask = np.zeros((100, 100), np.uint8)
    cv2.circle(mask, (50, 50), 30, 1, -1)
    calls = []

    def search(image, points, normals, **kwargs):
        index = np.arange(len(points))
        keep = index % 3 != 1 if not calls else index % 4 != 2
        moved = points + [0.25, -0.75]
        calls.append((points.copy(), moved, keep))
        return moved, keep

    monkeypatch.setattr(edges, "half_level_search", search)
    monkeypatch.setattr(edges, "edge_sigma", lambda *args: 1.0)
    (ring,), _, _ = edges.subpixel_rings(mask, mask.astype(np.float32), ppm=4)
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    expected_support = contours[0].reshape(-1, 2).astype(np.float64) + 0.5
    first, provisional, *_, final = calls
    assert np.array_equal(ring["support"], expected_support)
    assert np.array_equal(ring["support_indices"], np.flatnonzero(first[2])[final[2]])
    assert np.array_equal(ring["points"], final[1][final[2]])
    assert np.array_equal(final[0], np.where(provisional[2][:, None], provisional[1], provisional[0]))


def test_rendered_cap_hole_survives_trace_and_actual_cad_build(monkeypatch, tmp_path):
    points = cap(100, 20, 1001)
    points[:, 0] -= (points[:, 0].min() + points[:, 0].max()) / 2
    hole = Polygon(points)
    part = Polygon(box(-60, -35, 60, 35).exterior, [hole.exterior])
    monkeypatch.setattr(S, "part_local", lambda: part)
    photo, _ = S.render(
        tilt=(0, 0, 4), k1=0, thickness=0, shadow=0, gradient=0, noise=0, quality=100
    )
    result = trace_image(photo, reference="a4", snap=True)
    profile = result["profile"]
    assert len(profile["holes"]) == 1
    mm = profile["reference"]["mm_per_px"]
    traced_hole = Polygon(np.asarray(profile["holes"][0]) * mm)
    # Sharp tips are blurred and are not recovered exactly. Check the preserved hole
    # independently by area and size, without treating this synthetic render as fit proof.
    assert abs(traced_hole.area - hole.area) < 0.5
    sides = sorted(cv2.minAreaRect(np.asarray(traced_hole.exterior.coords, np.float32))[1])
    assert 1 < sides[0] < 3 and 30 < sides[1] < 36
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    with TestClient(api.app) as client:
        response = client.post("/api/build", json={
            "profile": profile, "width_mm": result["bounds"]["width"] * mm,
            "thickness_mm": 4, "name": "Circular-segment aperture", "design": {},
        })
    assert response.status_code == 200, response.text
    built = response.json()
    assert built["hole_count"] == 1
    assert abs(built["dimensions"]["width"] - 120) < 0.05
    assert abs(built["dimensions"]["height"] - 70) < 0.05
    assert math.isclose(built["volume_mm3"], part.area * 4, rel_tol=0.002)
