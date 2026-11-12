"""Exact circle/tangent observations must survive near-parallel cap refinement.

No blur, renderer or physical error model is used. The independent fixture is a
known circle sector, its exact tangent lines and one back edge. Arc circumcircles,
area and bounds are checked independently from the emitted three points.
"""

import copy
import math

import numpy as np
import pytest
from shapely.geometry import Polygon

from backend import fitting, reference


def tapered_cap(length=200.0, radius=10.0, half_angle_deg=1.0, step=0.2):
    epsilon = math.radians(half_angle_deg)
    start, sweep = -math.pi / 2 + epsilon, math.pi - 2 * epsilon
    a = radius * np.array([math.cos(start), math.sin(start)])
    b = radius * np.array([math.cos(start + sweep), math.sin(start + sweep)])
    lo = np.array([-length, -length * math.tan(epsilon) - radius / math.cos(epsilon)])
    hi = np.array([-length, length * math.tan(epsilon) + radius / math.cos(epsilon)])

    def line(p, q):
        return np.linspace(p, q, max(2, math.ceil(np.linalg.norm(q - p) / step)), endpoint=False)

    n = math.ceil(radius * sweep / step)
    angle = start + np.arange(n) * sweep / n
    points = np.vstack(
        (
            line(lo, a),
            radius * np.column_stack((np.cos(angle), np.sin(angle))),
            line(b, hi),
            line(hi, lo),
        )
    )
    cross = lambda p, q: float(p[0] * q[1] - p[1] * q[0])
    area = (cross(lo, a) + radius**2 * sweep + cross(b, hi) + cross(hi, lo)) / 2
    return points, {
        "start": start,
        "sweep": sweep,
        "vertices": np.array([lo, a, b, hi]),
        "radius": radius,
        "area": area,
        "source_sagitta": radius * (1 - math.cos(sweep / (2 * n))),
    }


def initial_fit(points, *, snap=True):
    prims = fitting.fit_ring(points, tol=0.05, min_line=5)
    assert prims is not None
    assert [p.kind for p in prims].count("arc") == 1
    if snap:
        fitting.snap_axes([prims])
    fitting.refit_lines(points, prims, margin=0)
    return prims


def final_fit(points, prims):
    fitting.fit_fillets(points, prims, tol=0.05, sigma=0)
    fitting.correct_blur(prims, 0)
    fitting.equalise_radii([prims])
    segments, analytic = reference._segments_for(points, prims, 0.05)
    assert analytic, "an exact supported circle must not silently become a polyline"
    assert [s[0] for s in segments].count("arc") == 1
    assert [s[0] for s in segments].count("line") == 3
    assert Polygon(fitting.sample_segments(segments, 0.001)).is_valid
    return segments


def circumcircle(segment):
    """Independent linear-equation circle, not fitting.arc_geometry."""
    a, mid, b = map(np.asarray, segment[1:])
    centre = np.linalg.solve(
        2 * np.vstack((mid - a, b - a)), np.array([mid @ mid - a @ a, b @ b - a @ a])
    )
    radius = float(np.linalg.norm(a - centre))
    angles = [math.atan2(p[1] - centre[1], p[0] - centre[0]) for p in (a, mid, b)]
    ccw = (angles[2] - angles[0]) % (2 * math.pi)
    sweep = ccw if (angles[1] - angles[0]) % (2 * math.pi) < ccw else ccw - 2 * math.pi
    return centre, radius, angles[0], sweep


def exact_segment_area(segments):
    twice_area = 0.0
    for segment in segments:
        a, b = np.asarray(segment[1]), np.asarray(segment[-1])
        if segment[0] == "line":
            twice_area += float(a[0] * b[1] - a[1] * b[0])
        else:
            centre, radius, _, sweep = circumcircle(segment)
            twice_area += radius**2 * sweep + centre[0] * (b[1] - a[1]) - centre[1] * (b[0] - a[0])
    return abs(twice_area) / 2


def exact_bounds(segments):
    extrema = []
    for segment in segments:
        extrema.extend((np.asarray(segment[1]), np.asarray(segment[-1])))
        if segment[0] == "arc":
            centre, radius, start, sweep = circumcircle(segment)
            for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
                travelled = (
                    (angle - start) % (2 * math.pi)
                    if sweep > 0
                    else (start - angle) % (2 * math.pi)
                )
                if travelled <= abs(sweep) + 1e-12:
                    extrema.append(centre + radius * np.array([math.cos(angle), math.sin(angle)]))
    xy = np.asarray(extrema)
    return np.r_[xy.min(axis=0), xy.max(axis=0)]


def assert_truth(points, prims, segments, truth, *, turn=0, translation=(0, 0)):
    (primitive,) = [p for p in prims if p.kind == "arc"]
    (arc,) = [s for s in segments if s[0] == "arc"]
    centre, radius, _, sweep = circumcircle(arc)
    np.testing.assert_allclose(centre, translation, rtol=0, atol=2e-8)
    assert radius == pytest.approx(truth["radius"], rel=0, abs=2e-8)
    np.testing.assert_allclose(primitive.data["c"], centre, rtol=0, atol=2e-8)
    assert primitive.data["r"] == pytest.approx(radius, rel=0, abs=2e-8)
    assert abs(sweep) == pytest.approx(truth["sweep"], rel=0, abs=2e-9)
    for p in (arc[1], arc[3]):
        assert np.linalg.norm(np.asarray(p) - centre) == pytest.approx(
            primitive.data["r"], abs=2e-8
        )
    assert exact_segment_area(segments) == pytest.approx(truth["area"], rel=0, abs=2e-6)
    theta = math.radians(turn)
    rotation = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
    candidates = list(truth["vertices"] @ rotation.T + translation)
    for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        if (angle - theta - truth["start"]) % (2 * math.pi) <= truth["sweep"]:
            candidates.append(
                np.asarray(translation)
                + truth["radius"] * np.array([math.cos(angle), math.sin(angle)])
            )
    candidates = np.asarray(candidates)
    np.testing.assert_allclose(
        exact_bounds(segments),
        np.r_[candidates.min(axis=0), candidates.max(axis=0)],
        rtol=0,
        atol=3e-8,
    )
    sampled = Polygon(fitting.sample_segments(segments, 0.001))
    # Both polylines approximate the independently specified circle. Use their
    # actual chord sagitta bound, including sample_segments'180-chord cap.
    count = min(180, max(2, math.ceil(abs(sweep) / (2 * math.acos(1 - 0.001 / radius)))))
    sampling = radius * (1 - math.cos(abs(sweep) / (2 * count)))
    assert (
        sampled.boundary.hausdorff_distance(Polygon(points).boundary)
        <= truth["source_sagitta"] + sampling + 1e-7
    )


@pytest.mark.parametrize("length", [50, 100, 200, 400])
def test_actual_fitting_chain_preserves_fixed_circle_when_tangent_side_length_changes(length):
    points, truth = tapered_cap(length)
    prims = initial_fit(points)
    segments = final_fit(points, prims)
    assert_truth(points, prims, segments, truth)
    (arc,) = [p for p in prims if p.kind == "arc"]
    assert not arc.data.get("end_cap"), "actual nonparallel tangents are not a constant-width slot"


@pytest.mark.parametrize("turn,reverse,start", [(37, False, 0), (19, True, 17), (91, True, 83)])
def test_rigid_motion_winding_and_cyclic_start_preserve_the_known_cap(turn, reverse, start):
    points, truth = tapered_cap()
    theta = math.radians(turn)
    rotation = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
    translation = (71, -43)
    points = np.roll(points[::-1] if reverse else points, start, axis=0) @ rotation.T + translation
    prims = initial_fit(points)
    assert_truth(points, prims, final_fit(points, prims), truth, turn=turn, translation=translation)


@pytest.mark.parametrize("shift", [-100, 0, 100])
def test_equivalent_line_anchors_do_not_change_direct_fillet_geometry(shift):
    points, truth = tapered_cap()
    prims = initial_fit(points)
    k = next(i for i, p in enumerate(prims) if p.kind == "arc")
    line = prims[(k + 1) % len(prims)]
    line.data["c"] = np.asarray(line.data["c"]) + shift * np.asarray(line.data["d"])
    # This is exactly the SAME line, not changed input observations or a new fit.
    segments = final_fit(points, prims)
    assert_truth(points, prims, segments, truth)


@pytest.mark.parametrize("half_angle", [0.01, 0.1, 0.4, 2, 3])
def test_direct_nearparallel_control_uses_general_tangency_not_axis_design_intent(half_angle):
    points, truth = tapered_cap(half_angle_deg=half_angle)
    # Below .6deg per side, snap_axes deliberately changes the taper to parallel.
    # Bypass only that design choice to verify real nonparallel tangent geometry.
    prims = initial_fit(points, snap=False)
    segments = final_fit(points, prims)
    assert_truth(points, prims, segments, truth)


@pytest.mark.parametrize("snap", [False, True])
def test_genuine_parallel_constant_width_cap_is_preserved(snap):
    points, truth = tapered_cap(half_angle_deg=0)
    original = initial_fit(points, snap=snap)
    for shift in (-100, 0, 100):
        prims = copy.deepcopy(original)
        k = next(i for i, p in enumerate(prims) if p.kind == "arc")
        line = prims[(k + 1) % len(prims)]
        line.data["c"] = np.asarray(line.data["c"]) + shift * np.asarray(line.data["d"])
        segments = final_fit(points, prims)
        assert_truth(points, prims, segments, truth)
        assert next(p for p in prims if p.kind == "arc").data.get("end_cap")


def test_repeated_radius_updates_keep_the_referenced_centre_on_both_tangencies():
    points, truth = tapered_cap()
    prims = initial_fit(points)
    final_fit(points, prims)
    k = next(i for i, p in enumerate(prims) if p.kind == "arc")
    arc = prims[k]
    lines = (prims[k - 1], prims[(k + 1) % len(prims)])
    normals = np.array([[-p.data["d"][1], p.data["d"][0]] for p in lines])
    offsets = np.array([n @ p.data["c"] for n, p in zip(normals, lines)])
    signs = np.sign(normals @ np.asarray(arc.data["c"]) - offsets)
    for radius in (10.001, 9.999, 10.0):
        arc.data["r"] = radius
        fitting.place_fillets(prims)
        expected = np.linalg.solve(normals, offsets + signs * radius)
        np.testing.assert_allclose(arc.data["c"], expected, rtol=0, atol=2e-10)
        (segment,) = [s for s in fitting.segments(prims) if s[0] == "arc"]
        centre, emitted_radius, _, sweep = circumcircle(segment)
        np.testing.assert_allclose(centre, expected, rtol=0, atol=2e-10)
        assert emitted_radius == pytest.approx(radius, abs=2e-10)
        assert abs(sweep) == pytest.approx(truth["sweep"], abs=2e-10)


def test_unresolvable_radius_coordinate_retains_free_geometry_and_warns():
    half_angle = 1e-12
    points, truth = tapered_cap(half_angle_deg=half_angle)
    prims = initial_fit(points, snap=False)
    arc = next(p for p in prims if p.kind == "arc")
    original_centre, original_radius = tuple(arc.data["c"]), arc.data["r"]
    # For these exact tangents |dC/dr|=1/sin(epsilon). A single radius ulp moves
    # its constrained centre farther than the supplied fit tolerance.
    assert math.ulp(original_radius) / math.sin(math.radians(half_angle)) > 0.05
    segments = final_fit(points, prims)
    assert arc.data["r"] == original_radius and tuple(arc.data["c"]) == original_centre
    assert arc.data.get("r_sd") == math.inf
    assert "fillet" not in arc.data and not arc.data.get("end_cap")
    assert any("could not settle" in note for note in fitting.undetermined_radii([prims], 0))
    assert_truth(points, prims, segments, truth)


def test_nearparallel_iteration_stops_on_geometric_motion_not_small_radius_step():
    # Independent translated circle and exact tangent lines. A representable tiny
    # radius-seed error corresponds to an O(1) centre displacement on this bisector.
    # Stopping at |dr|<1e-10 leaves about .0496px error, greater than the .03px fit
    # tolerance; this stage must iterate on the represented geometric movement.
    theta, radius = 1e-10, 10.0
    half = theta / 2
    centre = np.array([400.0, 20.0])
    directions = (
        np.array([math.cos(half), math.sin(half)]),
        np.array([-math.cos(half), math.sin(half)]),
    )
    normals = [np.array([-d[1], d[0]]) for d in directions]
    anchors = (
        centre + radius * normals[0] - 200 * directions[0],
        centre + radius * normals[1] + 200 * directions[1],
    )
    angles = np.linspace(math.pi / 2 + half, -math.pi / 2 - half, 501)
    points = centre + radius * np.column_stack((np.cos(angles), np.sin(angles)))
    arc = fitting.Primitive(
        "arc",
        {"c": tuple(centre), "r": radius + 0.75 * theta, "mid": tuple(centre + [radius, 0])},
        0.0,
        0.0,
        (0, len(points) - 1),
    )
    lines = [
        fitting.Primitive("line", {"c": c, "d": d}, 0.0, 0.0) for c, d in zip(anchors, directions)
    ]
    fitting.fit_fillets(points, [lines[0], arc, lines[1]], tol=0.03, sigma=0)
    np.testing.assert_allclose(arc.data["c"], centre, rtol=0, atol=1e-7)
    assert arc.data["r"] == pytest.approx(radius, rel=0, abs=1e-7)
    assert arc.max_abs < 1e-7 and arc.rms < 1e-7
    assert "fillet" in arc.data and not arc.data.get("end_cap")
