"""Circle-consistent assembly from independent circular-segment observations.

These are fitting/export regressions on analytic synthetic geometry. They do not
qualify a camera, blur approximation, endpoint-error model or physical part.
"""

import copy
import math
import re
from xml.etree import ElementTree as ET

import cadquery as cq
import ezdxf
import numpy as np
import pytest
from shapely.geometry import Polygon

from backend import drawing, fitting, reference
from backend.models import Profile
from backend.worker import extrude_fitted, write_fitted_dxf


def circular_segment(radius=10.0, chord=6.0, *, reverse=False, start=0, angle=0, shift=(0, 0)):
    """Right portion of a circle cut by x=chord, with independent ordered samples."""
    beta = math.acos(chord / radius)
    arc_angle = np.linspace(-beta, beta, 501)
    arc = radius * np.column_stack([np.cos(arc_angle), np.sin(arc_angle)])
    chord_points = np.linspace(arc[-1], arc[0], 201)[1:-1]
    points = np.vstack([arc, chord_points])
    theta = math.radians(angle)
    rotation = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
    points = np.roll(points[::-1] if reverse else points, start, axis=0) @ rotation.T + shift
    return points, (-1 if reverse else 1) * 2 * beta


def fit_segment(points):
    prims = fitting.fit_ring(points, tol=0.03, min_line=1)
    assert prims is not None, "a supported exact circular segment must remain analytic"
    assert sorted(p.kind for p in prims) == ["arc", "line"]
    return prims


def independent_arc(segment):
    """Circumcircle from translated 2x2 equations, without production arc_geometry."""
    start, middle, end = (np.asarray(p) for p in segment[1:])
    u, v = middle - start, end - start
    local_centre = np.linalg.solve(2 * np.vstack([u, v]), [u @ u, v @ v])
    centre = start + local_centre
    radius = float(np.linalg.norm(local_centre))
    first, witness, last = (math.atan2(*(p - centre)[::-1]) for p in (start, middle, end))
    ccw = (last - first) % (2 * math.pi)
    sweep = ccw if (witness - first) % (2 * math.pi) < ccw else ccw - 2 * math.pi
    return centre, radius, first, sweep


def independent_area(segments):
    # Translate before cross products so the oracle itself does not lose area
    # accuracy through subtraction of large squared world coordinates.
    origin = np.asarray(segments[0][1])
    twice = 0.0
    for segment in segments:
        start, end = (np.asarray(p) - origin for p in (segment[1], segment[-1]))
        twice += float(start[0] * end[1] - start[1] * end[0])
        if segment[0] == "arc":
            _, radius, _, sweep = independent_arc(segment)
            twice += radius**2 * (sweep - math.sin(sweep))
    return abs(twice) / 2


def assert_circle_and_closure(prims, segments, centre, radius, sweep=None):
    assert len(segments) == len(prims)
    for current, following in zip(segments, segments[1:] + segments[:1]):
        np.testing.assert_array_equal(current[-1], following[1])
    for primitive, segment in zip(prims, segments):
        if primitive.kind != "arc":
            continue
        actual_centre, actual_radius, _, actual_sweep = independent_arc(segment)
        np.testing.assert_allclose(actual_centre, centre, rtol=0, atol=2e-8)
        assert actual_radius == pytest.approx(radius, rel=0, abs=2e-8)
        np.testing.assert_allclose(actual_centre, primitive.data["c"], rtol=0, atol=2e-8)
        assert actual_radius == pytest.approx(primitive.data["r"], rel=0, abs=2e-8)
        np.testing.assert_allclose(
            np.linalg.norm(np.asarray(segment[1:]) - centre, axis=1), radius, rtol=0, atol=2e-8
        )
        if sweep is not None:
            assert actual_sweep == pytest.approx(sweep, rel=0, abs=2e-9)


@pytest.mark.parametrize("chord", [-6.0, 0.0, 6.0])
def test_actual_fit_ring_recovers_minor_half_and_major_circular_segments(chord):
    points, sweep = circular_segment(chord=chord)
    prims = fit_segment(points)
    segments, analytic = reference._segments_for(points, prims, 0.03)
    assert analytic
    assert_circle_and_closure(prims, segments, (0, 0), 10, sweep)
    expected_area = 100 * math.acos(chord / 10) - chord * math.sqrt(100 - chord**2)
    assert independent_area(segments) == pytest.approx(expected_area, rel=0, abs=2e-8)
    line = next(segment for segment in segments if segment[0] == "line")
    np.testing.assert_allclose(np.asarray(line[1:])[:, 0], chord, rtol=0, atol=1e-9)
    assert math.dist(*line[1:]) == pytest.approx(2 * math.sqrt(100 - chord**2), abs=1e-8)
    for p in prims:
        np.testing.assert_array_equal(p.data["source_ends"], points[list(p.span)])
    arc = next(p for p in prims if p.kind == "arc")
    assert math.copysign(1, arc.data["source_sweep"]) == math.copysign(1, sweep)


@pytest.mark.parametrize("chord", [-6.0, 0.0, 6.0])
@pytest.mark.parametrize("angle,reverse,start", [(37, False, 17), (-19, True, 83), (90, True, 1)])
def test_rigid_motion_winding_and_cyclic_source_start_preserve_circle(chord, angle, reverse, start):
    shift = (71, -43)
    points, sweep = circular_segment(
        chord=chord, angle=angle, reverse=reverse, start=start, shift=shift
    )
    prims = fit_segment(points)
    assert_circle_and_closure(prims, fitting.segments(prims), shift, 10, sweep)


@pytest.mark.parametrize("chord", [-6.0, 0.0, 6.0])
def test_free_radius_blur_update_preserves_actual_circle_and_rejoins_unchanged_chord(chord):
    points, _ = circular_segment(chord=chord)
    prims = fit_segment(points)
    source = [copy.deepcopy(p.data["source_ends"]) for p in prims]
    fitting.correct_blur(prims, sigma=1.5)
    radius = next(p.data["r"] for p in prims if p.kind == "arc")
    assert radius > 10
    segments = fitting.segments(prims)
    assert_circle_and_closure(prims, segments, (0, 0), radius, 2 * math.acos(chord / radius))
    for p, ends in zip(prims, source):
        np.testing.assert_array_equal(p.data["source_ends"], ends)
    expected_area = radius**2 * math.acos(chord / radius) - chord * math.sqrt(radius**2 - chord**2)
    assert independent_area(segments) == pytest.approx(expected_area, rel=0, abs=2e-8)


def test_equalisation_rejoins_both_transverse_source_arcs_at_the_declared_mean_radius():
    rings = [fit_segment(circular_segment(radius=radius, chord=6)[0]) for radius in (9.9, 10.1)]
    old_ends = [[copy.deepcopy(p.data["source_ends"]) for p in ring] for ring in rings]
    notes = fitting.equalise_radii(rings)
    assert len(notes) == 1
    for prims, sources in zip(rings, old_ends):
        assert_circle_and_closure(prims, fitting.segments(prims), (0, 0), 10, 2 * math.acos(0.6))
        for p, ends in zip(prims, sources):
            np.testing.assert_array_equal(p.data["source_ends"], ends)


@pytest.mark.parametrize("anchor_shift", [-100000.0, 0.0, 100000.0])
@pytest.mark.parametrize("sign", [-1, 1])
def test_equivalent_line_anchor_and_tls_direction_sign_do_not_change_ordered_join(
    anchor_shift, sign
):
    prims = fit_segment(circular_segment(chord=-6)[0])
    expected = fitting.segments(prims)
    line = next(p for p in prims if p.kind == "line")
    line.data["c"] = np.asarray(line.data["c"]) + anchor_shift * np.asarray(line.data["d"])
    line.data["d"] = sign * np.asarray(line.data["d"])
    actual = fitting.segments(prims)
    for a, b in zip(actual, expected):
        assert a[0] == b[0]
        np.testing.assert_allclose(a[1:], b[1:], rtol=0, atol=2e-8)


def explicit_tangent_corner(radius=5.0):
    # Legacy radius-zero constraint: C(r)=(5,5)-r(1,1). Its two exact tangencies
    # and interior witness specify a quarter even without source_* metadata.
    arc = fitting.Primitive(
        "arc",
        {
            "c": (0.0, 0.0),
            "r": radius,
            "mid": (5 / math.sqrt(2), 5 / math.sqrt(2)),
            "fillet": ((5.0, 5.0), (-1.0, -1.0)),
        },
        0.0,
        0.0,
    )
    return [
        fitting.Primitive("line", {"c": (5.0, 0.0), "d": (0.0, -1.0)}, 0.0, 0.0),
        arc,
        fitting.Primitive("line", {"c": (0.0, 5.0), "d": (1.0, 0.0)}, 0.0, 0.0),
    ]


@pytest.mark.parametrize("radius", [5.0, 5.25])
def test_legacy_explicit_tangent_constraints_keep_unique_exact_joins(radius):
    prims = explicit_tangent_corner(radius)
    fitting.place_fillets(prims)
    assert_circle_and_closure(
        prims, fitting.segments(prims), (5 - radius, 5 - radius), radius, math.pi / 2
    )


def expanded_tangent_major():
    corner, start, end = (5.0, -5.0), (5.0, 0.0), (0.0, -5.0)
    return [
        fitting.Primitive(
            "line", {"c": start, "d": (0.0, 1.0), "source_ends": (corner, start)}, 0.0, 0.0
        ),
        fitting.Primitive(
            "arc",
            {
                "c": (0.0, 0.0),
                "r": 5.394666666666667,
                "mid": (-5 / math.sqrt(2), 5 / math.sqrt(2)),
                "source_ends": (start, end),
                "source_sweep": 1.5 * math.pi,
            },
            0.0,
            0.0,
        ),
        fitting.Primitive(
            "line", {"c": end, "d": (1.0, 0.0), "source_ends": (end, corner)}, 0.0, 0.0
        ),
    ]


def test_expanded_free_tangencies_retain_equal_cost_major_arc_ambiguity():
    from backend.circular_joins import JoinConstructionError, assemble

    prims = expanded_tangent_major()
    original_radius = prims[1].data["r"]
    with pytest.raises(JoinConstructionError) as error:
        assemble(prims)
    assert error.value.reason == "ambiguous"
    assert prims[1].data["r"] == original_radius
    assert prims[1].data["c"] == (0.0, 0.0)


@pytest.mark.parametrize("sweep_degrees", [90, 120])
@pytest.mark.parametrize("rotation,shift", [(0, (0, 0)), (37, (400, 20))])
def test_actual_closed_tangent_fit_does_not_export_a_different_circle_after_radius_edit(
    sweep_degrees, rotation, shift
):
    from backend.circular_joins import JoinConstructionError

    # A complete valid source outline: one exact R10 arc closed by its two
    # tangents. Requesting nonzero blur on unblurred geometry deliberately tests
    # representation, not physical radius recovery. The old line-foot assembler
    # emitted R9.74099 while its quarter-arc metadata said R10.11229.
    half = math.radians(sweep_degrees) / 2
    angles = np.linspace(-half, half, 201)
    arc = 10 * np.column_stack([np.cos(angles), np.sin(angles)])
    apex = np.array([10 / math.cos(half), 0])
    points = np.vstack(
        [arc, np.linspace(arc[-1], apex, 101)[1:], np.linspace(apex, arc[0], 101)[1:-1]]
    )
    theta = math.radians(rotation)
    turn = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
    points = points @ turn.T + shift
    assert Polygon(points).is_valid
    prims = fitting.fit_ring(points, 0.03, 1)
    assert prims is not None and sorted(p.kind for p in prims) == ["arc", "line", "line"]
    fitting.correct_blur(prims, 1.5)
    with pytest.raises(JoinConstructionError) as error:
        fitting.segments(prims)
    assert error.value.reason == "ambiguous"
    notices = []
    segments, analytic = reference._segments_for(points, prims, 0.03, notices)
    assert not analytic and all(segment[0] == "line" for segment in segments)
    assert Polygon(np.array([segment[1] for segment in segments])).is_valid
    assert len(notices) == 1 and "more than one possible fitted join" in notices[0]


def disjoint_circle_candidate():
    points, _ = circular_segment(radius=12, chord=11)
    prims = fit_segment(points)
    arc = next(p for p in prims if p.kind == "arc")
    arc.data["r"] = 10.0
    return points, prims


def test_no_intersection_is_typed_and_final_reference_assembly_preserves_source_fallback():
    from backend.circular_joins import JoinConstructionError, assemble

    points, prims = disjoint_circle_candidate()
    with pytest.raises(JoinConstructionError) as error:
        assemble(prims)
    assert error.value.reason == "no_intersection"
    segments, analytic = reference._segments_for(points, prims, 0.03)
    assert not analytic
    assert all(segment[0] == "line" for segment in segments)
    assert Polygon(np.array([segment[1] for segment in segments])).is_valid
    assert next(p.data["r"] for p in prims if p.kind == "arc") == 10.0


def test_free_near_contact_is_unknown_rather_than_silently_normalized_to_tangent():
    from backend.circular_joins import JoinConstructionError, assemble

    prims = expanded_tangent_major()
    prims[1].data["r"] = math.nextafter(5.0, math.inf)
    with pytest.raises(JoinConstructionError) as error:
        assemble(prims)
    assert error.value.reason == "near_contact"


def test_small_pre_correction_tangent_miss_is_kept_as_candidate_not_falsely_exported():
    # Independently specified nominally tangent edge observations with a .05px
    # radius/line gap. Source bridges close the sampled ring; no optical claim.
    radius = 9.95
    arc_angle = np.linspace(-math.pi / 2, math.pi / 2, 501)
    arc = radius * np.column_stack([np.cos(arc_angle), np.sin(arc_angle)])
    points = np.vstack(
        [
            np.linspace((-100, -10), (0, -10), 401, endpoint=False),
            [[0, -10]],
            arc,
            [[0, 10]],
            np.linspace((0, 10), (-100, 10), 401, endpoint=False),
            np.linspace((-100, 10), (-100, -10), 81, endpoint=False),
        ]
    )
    prims = fitting.fit_ring(points, tol=0.15, min_line=2)
    assert prims is not None, "initial support eligibility must allow correction to run"
    assert any(p.kind == "arc" for p in prims)
    _, analytic = reference._segments_for(points, prims, 0.15)
    assert not analytic, "an eligibility proxy is not circle-consistent final geometry"


@pytest.mark.parametrize("chord", [-6.0, 6.0])
def test_corrected_free_arc_keeps_its_circle_in_cad_step_dxf_and_svg(chord, tmp_path):
    points, _ = circular_segment(chord=chord)
    prims = fit_segment(points)
    fitting.correct_blur(prims, 1.5)
    radius = next(p.data["r"] for p in prims if p.kind == "arc")
    segments = fitting.segments(prims)
    reviewed, _ = circular_segment(radius=radius, chord=chord)
    profile = Profile(
        outer=reviewed.tolist(),
        primitives={
            "outer": [
                {
                    "kind": segment[0],
                    "start": list(segment[1]),
                    "end": list(segment[-1]),
                    **({"mid": list(segment[2])} if segment[0] == "arc" else {}),
                }
                for segment in segments
            ],
            "holes": [],
        },
    )
    assert profile.primitives is not None
    shape, area = extrude_fitted([segments], 3.0, Polygon(reviewed))
    expected_area = radius**2 * math.acos(chord / radius) - chord * math.sqrt(radius**2 - chord**2)
    assert area == pytest.approx(expected_area, rel=1e-10)
    assert shape.Volume() == pytest.approx(3 * expected_area, rel=1e-10)
    circle_edges = [edge for edge in shape.Edges() if edge.geomType() == "CIRCLE"]
    assert len(circle_edges) == 2
    for edge in circle_edges:
        assert edge.radius() == pytest.approx(radius, abs=2e-8)
    path = tmp_path / "corrected.dxf"
    write_fitted_dxf(path, [segments])
    (entity,) = list(ezdxf.readfile(path).modelspace().query("ARC"))
    assert entity.dxf.radius == pytest.approx(radius, rel=0, abs=2e-8)
    np.testing.assert_allclose(tuple(entity.dxf.center)[:2], (0, 0), rtol=0, atol=2e-8)

    step_path = tmp_path / "corrected.step"
    cq.exporters.export(shape, str(step_path))
    restored = cq.importers.importStep(str(step_path)).val()
    assert restored.isValid() and len(restored.Solids()) == 1
    assert restored.Volume() == pytest.approx(3 * expected_area, rel=1e-10)
    restored_circles = [edge for edge in restored.Edges() if edge.geomType() == "CIRCLE"]
    assert len(restored_circles) == 2
    for edge in restored_circles:
        assert edge.radius() == pytest.approx(radius, abs=2e-8)
        np.testing.assert_allclose(edge.arcCenter().toTuple()[:2], (0, 0), rtol=0, atol=2e-8)
    y_extent = 2 * (radius if chord < 0 else math.sqrt(radius**2 - chord**2))
    bounds = restored.BoundingBox()
    np.testing.assert_allclose(
        (bounds.xlen, bounds.ylen, bounds.zlen), (radius - chord, y_extent, 3), rtol=0, atol=1e-6
    )

    svg_path = tmp_path / "corrected.svg"
    svg_path.write_text(
        drawing.svg(drawing.fitted_loops([segments]), "Synthetic corrected arc"), encoding="utf-8"
    )
    svg = ET.parse(svg_path).getroot()  # Fixed synthetic output from the local serializer.
    dimensions = [float(svg.attrib[key].removesuffix("mm")) for key in ("width", "height")]
    np.testing.assert_allclose(
        np.array(dimensions) - 2 * drawing.SVG_MARGIN, (radius - chord, y_extent), rtol=0, atol=1e-5
    )
    np.testing.assert_allclose(
        list(map(float, svg.attrib["viewBox"].split())), (0, 0, *dimensions), rtol=0, atol=1e-10
    )
    paths = svg.findall(".//{http://www.w3.org/2000/svg}path")
    assert len(paths) == 1
    arcs = re.findall(r"\bA ([^ ]+) ([^ ]+) 0 0 ([01]) ([^ ]+) ([^ ]+)", paths[0].attrib["d"])
    assert arcs
    svg_centre = np.array([-chord + drawing.SVG_MARGIN, y_extent / 2 + drawing.SVG_MARGIN])
    for rx, ry, sweep_flag, x, y in arcs:
        assert float(rx) == float(ry)
        assert float(rx) == pytest.approx(radius, rel=0, abs=1e-5)
        assert sweep_flag == "0", "the model CCW arc flips into SVG's y-down frame"
        assert np.linalg.norm(np.array([float(x), float(y)]) - svg_centre) == pytest.approx(
            radius, rel=0, abs=1e-5
        )


def test_global_traversal_can_require_the_root_farther_from_both_source_endpoints():
    from backend.circular_joins import assemble

    original_radius, radius, corner_y = 5.25, 5.375, -1.75
    old_start = (5.0, -math.sqrt(original_radius**2 - 25))
    old_end = (-math.sqrt(original_radius**2 - corner_y**2), corner_y)
    corner = (5.0, corner_y)
    first_angle, last_angle = (math.atan2(p[1], p[0]) for p in (old_start, old_end))
    source_sweep = (last_angle - first_angle) % (2 * math.pi)
    prims = [
        fitting.Primitive(
            "line",
            {"c": (5.0, 0.0), "d": (0.0, 1.0), "source_ends": (corner, old_start)},
            0.0,
            0.0,
        ),
        fitting.Primitive(
            "arc",
            {
                "c": (0.0, 0.0),
                "r": radius,
                "mid": (-original_radius / math.sqrt(2), original_radius / math.sqrt(2)),
                "source_ends": (old_start, old_end),
                "source_sweep": source_sweep,
            },
            0.0,
            0.0,
        ),
        fitting.Primitive(
            "line",
            {"c": (0.0, corner_y), "d": (1.0, 0.0), "source_ends": (old_end, corner)},
            0.0,
            0.0,
        ),
    ]
    reach = math.sqrt(radius**2 - 25)
    nearest, feasible = (5.0, -reach), (5.0, reach)
    assert math.dist(nearest, old_start) < math.dist(feasible, old_start)
    assert nearest[1] < corner_y < old_start[1] < feasible[1]
    segments = assemble(prims)
    # The closer root reverses the source line. A local nearest-root rule is
    # wrong even though its endpoint score is strictly better at this join.
    np.testing.assert_allclose(segments[0][-1], feasible, rtol=0, atol=1e-12)
    np.testing.assert_allclose(
        segments[-1][1], (-math.sqrt(radius**2 - corner_y**2), corner_y), rtol=0, atol=1e-12
    )
    assert_circle_and_closure(prims, segments, (0, 0), radius)


@pytest.mark.parametrize("clearance,unresolved", [(1e-13, True), (1e-8, False)])
def test_interior_witness_must_clear_the_propagated_join_position_error(clearance, unresolved):
    from backend.circular_joins import JoinConstructionError, assemble

    prims = fit_segment(circular_segment(chord=6)[0])
    arc = next(p for p in prims if p.kind == "arc")
    angle = -math.acos(0.6) + clearance
    # Strictly interior in exact geometry. The smaller positive clearance is
    # below the sampler-independent engineering error on the constructed join.
    arc.data["mid"] = (10 * math.cos(angle), 10 * math.sin(angle))
    if unresolved:
        with pytest.raises(JoinConstructionError) as error:
            assemble(prims)
        assert error.value.reason == "numerical"
    else:
        assert_circle_and_closure(prims, assemble(prims), (0, 0), 10, 2 * math.acos(0.6))


def nearparallel_contact_fixture():
    theta, radius = 1e-10, 10.0
    half = theta / 2
    first = np.array([math.cos(half), math.sin(half)])
    second = np.array([-math.cos(half), math.sin(half)])
    normal_first = np.array([-first[1], first[0]])
    normal_second = np.array([-second[1], second[0]])
    top, bottom = radius * normal_first, radius * normal_second
    back_top, back_bottom = top - 400 * first, bottom + 400 * second
    angle = np.linspace(math.pi / 2 + half, -math.pi / 2 - half, 501)
    points = radius * np.column_stack([np.cos(angle), np.sin(angle)])
    prims = [
        fitting.Primitive(
            "line", {"c": top - 200 * first, "d": first, "source_ends": (back_top, top)}, 0.0, 0.0
        ),
        fitting.Primitive(
            "arc",
            {
                "c": (0.0, 0.0),
                "r": radius,
                "mid": (radius, 0.0),
                "source_ends": (top, bottom),
                "source_sweep": -math.pi - theta,
            },
            0.0,
            0.0,
            (0, 500),
        ),
        fitting.Primitive(
            "line",
            {"c": bottom + 200 * second, "d": second, "source_ends": (bottom, back_bottom)},
            0.0,
            0.0,
        ),
        fitting.Primitive(
            "line",
            {
                "c": (back_top + back_bottom) / 2,
                "d": (0.0, 1.0),
                "source_ends": (back_bottom, back_top),
            },
            0.0,
            0.0,
        ),
    ]
    return points, prims, normal_first


def test_only_an_explicit_design_contact_can_normalize_a_roundoff_tangency():
    from backend.circular_joins import JoinConstructionError, assemble

    _points, prims, _ = nearparallel_contact_fixture()
    arc = prims[1]
    # No design-intent operation yet: a free near-contact remains unresolved.
    with pytest.raises(JoinConstructionError) as error:
        assemble(prims)
    assert error.value.reason == "near_contact"
    # Exercise the assembler's explicit design-intent contract, not the separate
    # research-lineage tapered-cap fitter absent from this main-based change.
    arc.data["tangent_contact"] = True
    assert arc.data["c"] == (0.0, 0.0) and arc.data["r"] == 10.0
    assert_circle_and_closure(prims, assemble(prims), (0, 0), 10, -math.pi - 1e-10)


def test_explicit_design_contact_cannot_hide_a_line_miss_outside_roundoff():
    from backend.circular_joins import JoinConstructionError, assemble

    _points, prims, normal = nearparallel_contact_fixture()
    arc = prims[1]
    # The tiny line displacement is still larger than the declared arithmetic
    # contact guard. Even explicit intent cannot manufacture an intersection.
    prims[0].data["c"] = np.asarray(prims[0].data["c"]) + 1e-11 * normal
    arc.data["tangent_contact"] = True
    with pytest.raises(JoinConstructionError) as error:
        assemble(prims)
    assert error.value.reason == "no_intersection"
    assert arc.data["c"] == (0.0, 0.0) and arc.data["r"] == 10.0


@pytest.mark.parametrize("centre", [(0, 0), (100000, 100000), (999000, 998000)])
@pytest.mark.parametrize("sweep_degrees", [10, 120])
def test_large_coordinate_arc_geometry_and_actual_dxf_svg_keep_the_local_circle(
    centre, sweep_degrees, tmp_path
):
    # All coordinates remain within Profile's existing +/-1e6 bound. With the
    # former world-square formula the translated10deg case exported R11.99920.
    angles = np.radians([17, 17 + sweep_degrees / 2, 17 + sweep_degrees])
    points = np.asarray(centre) + 12 * np.column_stack([np.cos(angles), np.sin(angles)])
    arc = ("arc", *points)
    expected_centre, expected_radius, _, _ = independent_arc(arc)
    actual_centre, actual_radius, _, _ = fitting.arc_geometry(*points)
    np.testing.assert_allclose(actual_centre, expected_centre, rtol=0, atol=3e-8)
    assert actual_radius == pytest.approx(expected_radius, rel=0, abs=3e-8)
    segments = [arc, ("line", points[-1], points[0])]
    path = tmp_path / "translated.dxf"
    write_fitted_dxf(path, [segments])
    (entity,) = list(ezdxf.readfile(path).modelspace().query("ARC"))
    np.testing.assert_allclose(tuple(entity.dxf.center)[:2], expected_centre, rtol=0, atol=3e-8)
    assert entity.dxf.radius == pytest.approx(expected_radius, rel=0, abs=3e-8)
    svg_path = tmp_path / "translated.svg"
    svg_path.write_text(drawing.svg(drawing.fitted_loops([segments]), "Synthetic translated arc"))
    svg = ET.parse(svg_path).getroot()
    paths = svg.findall(".//{http://www.w3.org/2000/svg}path")
    assert len(paths) == 1
    radii = re.findall(r"\bA ([^ ]+) ([^ ]+) ", paths[0].attrib["d"])
    assert radii
    for rx, ry in radii:
        assert float(rx) == float(ry)
        assert float(rx) == pytest.approx(expected_radius, rel=0, abs=1e-5)


@pytest.mark.parametrize("sigma", [0.0, 2.0])
@pytest.mark.parametrize("cluster_radians", [0.005, 0.1])
def test_actual_nonuniform_capsule_keeps_its_original_angular_witness_after_cap_fit(
    sigma, cluster_radians
):
    # A source-index midpoint need not be the angular tip when accepted samples
    # are nonuniform. The sparse-angle control formerly moved the centre beyond
    # the old midpoint and made canonical assembly refuse an otherwise valid cap.
    right_angles = np.r_[
        np.linspace(-math.pi / 2, -math.pi / 2 + cluster_radians, 301),
        np.linspace(-math.pi / 2 + cluster_radians, math.pi / 2, 81)[1:],
    ]
    left_angles = np.linspace(math.pi / 2, 3 * math.pi / 2, 301)
    right = np.column_stack([30 + 10 * np.cos(right_angles), 10 * np.sin(right_angles)])
    left = np.column_stack([-30 + 10 * np.cos(left_angles), 10 * np.sin(left_angles)])
    points = np.vstack(
        [
            right,
            np.linspace(right[-1], left[0], 101)[1:-1],
            left,
            np.linspace(left[-1], right[0], 101)[1:-1],
        ]
    )
    assert Polygon(points).is_valid
    prims = fitting.fit_ring(points, 0.03, 1)
    assert prims is not None and sorted(p.kind for p in prims) == ["arc", "arc", "line", "line"]
    before = {id(p): copy.deepcopy(p.data) for p in prims if p.kind == "arc"}
    # The sigma2 request on exact unblurred geometry is deliberately mismatched:
    # this verifies representation and witness transport, not optical recovery.
    fitting.fit_fillets(points, prims, 0.03, sigma)
    for p in prims:
        if p.kind != "arc":
            continue
        old = before[id(p)]
        old_direction = np.asarray(old["mid"]) - np.asarray(old["c"])
        new_direction = np.asarray(p.data["mid"]) - np.asarray(p.data["c"])
        np.testing.assert_allclose(
            new_direction / np.linalg.norm(new_direction),
            old_direction / np.linalg.norm(old_direction),
            rtol=0,
            atol=2e-13,
        )
        assert np.linalg.norm(new_direction) == pytest.approx(p.data["r"], abs=2e-12)
        np.testing.assert_array_equal(p.data["source_ends"], old["source_ends"])
        assert p.data["source_sweep"] == old["source_sweep"]
    segments = fitting.segments(prims)
    assert Polygon(fitting.sample_segments(segments, 0.001)).is_valid
    for primitive, segment in zip(prims, segments):
        if primitive.kind == "arc":
            centre, radius, _, _ = independent_arc(segment)
            np.testing.assert_allclose(centre, primitive.data["c"], rtol=0, atol=2e-8)
            assert radius == pytest.approx(primitive.data["r"], abs=2e-8)
