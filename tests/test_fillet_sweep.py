"""Arc branch preservation after constrained centres/radii move."""

import math
import statistics

import cadquery as cq
import ezdxf
import numpy as np
import pytest
from shapely.geometry import Polygon, box

from backend import fitting, reference
from backend.models import Profile, ring_polygon
from backend.worker import dimensions_of, extrude_fitted, write_fitted_dxf


def blurred_sharp_rectangle(sigma_x=3.0, sigma_y=1.5, step=0.6):
    """Independent half-level of separable Gaussian blur on a 600x350px rectangle.

    Near a true sharp corner Phi(dx/sigma_x)*Phi(dy/sigma_y)=1/2. NormalDist
    inversion supplies observations without production corner_level or a renderer.
    Opposite edges are hundreds of blur widths away; their Gaussian tails round
    to zero at float64 precision. Anisotropy remains a deliberately wrong model
    for the scalar fitter: this test only requires consistent arc assembly.
    """
    normal = statistics.NormalDist()
    depth = np.linspace(7.0, normal.inv_cdf(math.sqrt(0.5)), 500)
    other = np.array([normal.inv_cdf(0.5 / normal.cdf(v)) for v in depth])
    half = np.column_stack([depth, other])
    corner = np.vstack([half, half[-2::-1, ::-1]])
    outline = []
    for sx, sy, swap in ((1, 1, True), (-1, 1, False), (-1, -1, True), (1, -1, False)):
        q = corner[:, ::-1] if swap else corner
        outline.extend(
            np.column_stack([sx * (300 - sigma_x * q[:, 0]), sy * (175 - sigma_y * q[:, 1])])
        )
    xy = np.array(outline + outline[:1])
    along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    at = np.arange(0, along[-1] - step / 2, step)
    return np.column_stack([np.interp(at, along, xy[:, 0]), np.interp(at, along, xy[:, 1])])


def transformed(points, turn, reverse, start):
    angle = math.radians(turn)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    return np.roll(points[::-1] if reverse else points, start, axis=0) @ rotation.T + [71, -43]


def fit_chain(points, sigma):
    """The actual reference fitting order, including post-fit radius equalisation."""
    ppm = 5.0
    tol = max(0.03, 0.15 * sigma / ppm) * ppm
    min_line = min(max(0.025 * float(np.ptp(points, axis=0).max()) / ppm, 1.0), 3.0) * ppm
    prims = fitting.fit_ring(points, tol, min_line)
    assert prims is not None
    fitting.snap_axes([prims])
    fitting.refit_lines(points, prims, margin=3 * sigma)
    fitting.fit_fillets(points, prims, tol, sigma)
    fitting.correct_blur(prims, sigma)
    fitting.equalise_radii([prims])
    return prims


@pytest.mark.parametrize(
    "turn,reverse,start", [(0, False, 0), (37, False, 0), (0, True, 0), (19, True, 17)]
)
def test_refined_quarter_fillets_do_not_switch_to_the_major_complement(turn, reverse, start):
    points = transformed(blurred_sharp_rectangle(), turn, reverse, start)
    prims = fit_chain(points, 1.5)
    assert [p.kind for p in prims].count("arc") == 4
    for primitive, segment in zip(prims, fitting.segments(prims)):
        if primitive.kind != "arc":
            continue
        centre = np.asarray(primitive.data["c"])
        # Adjacent exact perpendicular lines define a quarter-circle. Its midpoint
        # follows the SUM of the endpoint radial directions, not their opposite.
        a, mid, b = (np.asarray(p) - centre for p in segment[1:])
        bisector = a / np.linalg.norm(a) + b / np.linalg.norm(b)
        expected_mid = primitive.data["r"] * bisector / np.linalg.norm(bisector)
        np.testing.assert_allclose(mid, expected_mid, rtol=0, atol=1e-8)
        assert abs(a @ b) < 1e-8
    # The anisotropic-to-scalar mismatch still produces uncertain fillet radii;
    # branch repair must not silently remove those model-dependent warnings.
    assert any("does not determine" in note for note in fitting.undetermined_radii([prims], 1.5))


@pytest.mark.parametrize("turn,reverse,start", [(0, False, 0), (37, True, 17)])
def test_inside_and_outside_quarters_keep_their_winding(turn, reverse, start):
    plate = box(0, 0, 120, 90).difference(box(60, 45, 130, 100))
    rounded = plate.buffer(8, quad_segs=256).buffer(-16, quad_segs=256).buffer(8, quad_segs=256)
    boundary = rounded.exterior
    samples = np.arange(0, boundary.length, 0.2)
    points = np.array([boundary.interpolate(s).coords[0] for s in samples])
    points = transformed(points, turn, reverse, start)
    prims = fit_chain(points, 0)
    arcs = [s for s in fitting.segments(prims) if s[0] == "arc"]
    assert len(arcs) == 6
    sweeps = [fitting.arc_geometry(*s[1:])[-1] for s in arcs]
    assert sum(s > 0 for s in sweeps) in (1, 5)
    assert sum(s < 0 for s in sweeps) in (1, 5)
    np.testing.assert_allclose(np.abs(sweeps), math.pi / 2, rtol=0, atol=1e-8)
    result = Polygon(fitting.sample_segments(fitting.segments(prims), 0.001))
    assert result.is_valid
    assert result.boundary.hausdorff_distance(Polygon(points).boundary) < 0.03


def major_arc_ring(radius=30.0):
    angle = np.linspace(0, 1.5 * math.pi, 700)
    arc = radius * np.column_stack([np.cos(angle), np.sin(angle)])
    corner = [radius, -radius]
    return np.vstack(
        [arc, np.linspace(arc[-1], corner, 151)[1:], np.linspace(corner, arc[0], 151)[1:-1]]
    )


@pytest.mark.parametrize("turn,reverse,start", [(0, False, 0), (37, True, 17)])
def test_genuine_tangent_joined_major_arc_is_preserved(turn, reverse, start, tmp_path):
    points = transformed(major_arc_ring(), turn, reverse, start)
    prims = fit_chain(points, 0)
    arcs = [s for s in fitting.segments(prims) if s[0] == "arc"]
    assert len(arcs) == 1
    # This arc is tagged as a constraint by fit_fillets too: fixing all such arcs
    # to the minor sector would destroy a valid three-quarter-circle boundary.
    assert any("fillet" in p.data for p in prims)
    assert abs(fitting.arc_geometry(*arcs[0][1:])[-1]) == pytest.approx(1.5 * math.pi, abs=1e-10)
    segs = fitting.segments(prims)
    described = Polygon(fitting.sample_segments(segs, 0.001))
    assert described.is_valid
    # sample_segments caps an arc at 180 chords; account for that actual sagitta
    # and the independent source fixture's 699 chords, rather than assuming .001.
    sagitta = 30 * (1 - math.cos(1.5 * math.pi / 360))
    source_sagitta = 30 * (1 - math.cos(1.5 * math.pi / (2 * 699)))
    assert (
        described.boundary.hausdorff_distance(Polygon(points).boundary)
        <= sagitta + source_sagitta + 1e-9
    )
    dxf = tmp_path / "major.dxf"
    write_fitted_dxf(dxf, [segs])
    (exported,) = list(ezdxf.readfile(dxf).modelspace().query("ARC"))
    assert (exported.dxf.end_angle - exported.dxf.start_angle) % 360 == pytest.approx(270, abs=1e-8)
    solid, area = extrude_fitted([segs], 4, described)
    expected_area = 30**2 * (1 + 3 * math.pi / 4)
    assert area == pytest.approx(expected_area, rel=1e-8)
    assert solid.Volume() == pytest.approx(4 * expected_area, rel=1e-8)


def test_relocated_fillet_witness_survives_repeated_radius_changes():
    # The old world point (0.8,0.2) is angularly inside the quarter. Moving the
    # constrained centre to (3,3) makes that old world point select the complement.
    p = fitting.Primitive(
        "arc",
        {"c": (0.0, 0.0), "r": 3.0, "mid": (0.8, 0.2), "fillet": ((0.0, 0.0), (1.0, 1.0))},
        0.0,
        0.0,
    )
    original_direction = np.array([0.8, 0.2]) / math.hypot(0.8, 0.2)
    fitting.place_fillets([p])
    for radius in (3.0, 3.05, 2.98):
        p.data["r"] = radius
        fitting.place_fillets([p])
        expected_centre = np.array([radius, radius])
        np.testing.assert_allclose(p.data["c"], expected_centre, atol=1e-14)
        np.testing.assert_allclose(
            p.data["mid"], expected_centre + radius * original_direction, atol=1e-14
        )


def test_quarter_sweeps_survive_profile_cad_step_and_dxf(tmp_path):
    prims = fit_chain(blurred_sharp_rectangle(), 1.5)
    segs = fitting.segments(prims)
    transform = reference._Transform(np.eye(2), [0, 0], [-400, -250], 1)
    profile = Profile(
        outer=[transform(p) for p in fitting.sample_segments(segs, 0.005)],
        holes=[],
        primitives={"outer": reference._to_model(segs, transform), "holes": []},
    )
    # Use the worker's validation-sampling scale, with its actual Profile parser,
    # then convert the 5px/mm observations to a 120x70mm part before extrusion.
    mm = 0.2
    polygon = Polygon(np.asarray(ring_polygon(profile.primitives.outer, 0.001 / mm)) * mm)

    def metric(point):
        return tuple(np.asarray(transform(point)) * mm)

    rings = [
        [
            ("line", metric(s[1]), metric(s[2]))
            if s[0] == "line"
            else ("arc", metric(s[1]), metric(s[2]), metric(s[3]))
            for s in segs
        ]
    ]
    solid, area = extrude_fitted(rings, 4.0, polygon)
    assert solid.isValid() and len(solid.Solids()) == 1
    xs = [p.data["c"][0] for p in prims if p.kind == "line" and abs(p.data["d"][1]) > 0.9]
    ys = [p.data["c"][1] for p in prims if p.kind == "line" and abs(p.data["d"][0]) > 0.9]
    expected_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
    expected_area -= sum(p.data["r"] ** 2 * (1 - math.pi / 4) for p in prims if p.kind == "arc")
    expected_area *= mm**2
    assert area == pytest.approx(expected_area, rel=1e-8)
    assert solid.Volume() == pytest.approx(4 * expected_area, rel=1e-8)
    dxf = tmp_path / "quarters.dxf"
    write_fitted_dxf(dxf, rings)
    exported = list(ezdxf.readfile(dxf).modelspace().query("ARC"))
    assert len(exported) == 4
    for arc in exported:
        assert (arc.dxf.end_angle - arc.dxf.start_angle) % 360 == pytest.approx(90, abs=1e-7)
    step = tmp_path / "quarters.step"
    cq.exporters.export(solid, str(step))
    imported = cq.importers.importStep(str(step)).val()
    assert imported.isValid()
    assert imported.Volume() == pytest.approx(solid.Volume(), rel=1e-9)
    assert dimensions_of(imported) == pytest.approx(dimensions_of(solid), abs=1e-7)
