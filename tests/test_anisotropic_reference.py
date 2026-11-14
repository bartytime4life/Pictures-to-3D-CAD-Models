"""Coordinate-stage checks for a supplied rectified Gaussian covariance.

These use exact geometric maps and analytic Gaussian quadrant probabilities. The
controlled trace test bypasses image detection; it is not a camera qualification.
"""

import math

import numpy as np
import pytest
from shapely.geometry import LineString, Polygon

from backend import edges, fitting, reference, tone
from backend.models import Profile
from backend.tracing import trace_image
from tests import synthetic as S


def _rotation(angle):
    return np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])


def _phi(value):
    return 0.5 * math.erfc(-value / math.sqrt(2))


@pytest.mark.parametrize("angle", [0.0, 0.63])
def test_top_face_homothety_scales_the_gaussian_covariance_in_squared_units(angle):
    """A rotated sharp quadrant has an independent separable-Gaussian answer.

    The actual thickness map contracts both geometry and standard deviations by
    alpha. Keeping the old covariance instead has a demonstrably different level.
    """
    rotation = _rotation(angle)
    sigma_x, sigma_y = 0.5, 1.5
    covariance = rotation @ np.diag([sigma_x**2, sigma_y**2]) @ rotation.T
    point = np.array([[0.3, 0.5]]) @ rotation.T
    centre = np.zeros(2)
    nadir = np.array([10.0, 10.0]) @ rotation.T
    normal = np.array([[-1.0, -1.0]]) @ rotation.T / math.sqrt(2)
    alpha = 0.8
    mapped, top = edges.correct_thickness(point, normal, nadir, 100.0, 20.0)
    assert top.tolist() == [True]
    np.testing.assert_allclose(mapped, nadir + alpha * (point - nadir), atol=2e-15)
    mapped_centre = nadir + alpha * (centre - nadir)
    answer = _phi(0.3 / sigma_x) * _phi(0.5 / sigma_y)
    actual = fitting.corner_level(
        mapped,
        mapped_centre,
        0.0,
        math.pi + angle,
        math.pi / 2,
        math.sqrt(sigma_x * sigma_y) * alpha,
        covariance=covariance * alpha**2,
    )
    np.testing.assert_allclose(actual, [answer], rtol=0, atol=2e-6)
    wrong = fitting.corner_level(
        mapped,
        mapped_centre,
        0.0,
        math.pi + angle,
        math.pi / 2,
        math.sqrt(sigma_x * sigma_y),
        covariance=covariance,
    )
    assert abs(float(wrong[0]) - answer) > 0.025


def _rounded_rectangle():
    """An exact finite CCW plate and its independently specified outward normals."""
    centres = [(162.0, 73.0), (162.0, 127.0), (78.0, 127.0), (78.0, 73.0)]
    starts = [-math.pi / 2, 0.0, math.pi / 2, math.pi]
    arcs, normals = [], []
    for centre, start in zip(centres, starts):
        angles = np.linspace(start, start + math.pi / 2, 25)
        directions = np.column_stack([np.cos(angles), np.sin(angles)])
        arcs.append(np.asarray(centre) + 8 * directions)
        normals.append(directions)
    points_out, normals_out = [], []
    for index in range(4):
        points_out.extend(arcs[index])
        normals_out.extend(normals[index])
        following = (index + 1) % 4
        line = np.linspace(arcs[index][-1], arcs[following][0], 60)[1:-1]
        points_out.extend(line)
        normals_out.extend(np.tile(normals[index][-1], (len(line), 1)))
    return np.asarray(points_out), np.asarray(normals_out)


def _controlled_trace(
    monkeypatch,
    *,
    thickness,
    covariance,
    nadir,
    unresolved=False,
    hole=False,
    actual_fillets=False,
):
    """Keep the real point map, ring fit, line refit, assembly and Profile validation.

    Image detection and wall brightness fitting are outside this coordinate test.
    The corner dispatch is observed without making an image-model accuracy claim.
    """
    points, normals = _rounded_rectangle()
    if thickness and nadir[0] == 500.0:
        # Prescribe a continuous corrected plate for the mixed-height control.
        # Its source top points are enlarged; bottom points are unchanged.
        alpha = (100.0 - thickness) / 100.0
        top = np.sum(normals * (points - nadir), axis=1) > 0
        points[top] = np.asarray(nadir) + (points[top] - nadir) / alpha
    original = points.copy()
    ppm = 2.0
    sigma = math.sqrt(0.5 * 1.5)
    rgb = np.full((320, 420, 3), 180, dtype=np.uint8)
    ring = {"outer": True, "points": points, "covariance": covariance}
    rings = [ring]
    if hole:
        angle = np.linspace(0.0, -2 * math.pi, 100, endpoint=False)
        circle = [120.0, 100.0] + 6 * np.column_stack([np.cos(angle), np.sin(angle)])
        rings.append({"outer": False, "points": circle, "covariance": covariance})
    camera = {"height_mm": 100.0, "nadir_mm": np.asarray(nadir) / ppm, "focal_source": "exif"}
    monkeypatch.setattr(reference.sheet, "find_sheet", lambda *_: object())
    monkeypatch.setattr(reference.sheet, "estimate_k1", lambda *_: (0.0, 0.0, 0.0))
    monkeypatch.setattr(reference.sheet, "homography", lambda *_: (np.eye(3), (210.0, 297.0), None))
    monkeypatch.setattr(reference.sheet, "orthogonal_focal", lambda *_: 100.0)
    monkeypatch.setattr(reference.sheet, "camera_pose", lambda *_, **__: camera)
    monkeypatch.setattr(reference.sheet, "aspect_ratio_check", lambda *_: 1.0)
    monkeypatch.setattr(reference.sheet, "choose_ppm", lambda *_: (ppm, ppm))
    monkeypatch.setattr(reference.sheet, "rectify", lambda *_: rgb.copy())
    monkeypatch.setattr(
        reference.sheet, "rectify_gray", lambda *_: np.zeros(rgb.shape[:2], np.float32)
    )
    monkeypatch.setattr(
        reference.edges, "segment", lambda *_args, **_kwargs: (np.ones(rgb.shape[:2], np.uint8), [])
    )
    monkeypatch.setattr(reference.edges, "measurement_weights", lambda *_: tone.LUMINANCE)
    monkeypatch.setattr(reference.edges, "subpixel_rings", lambda *_: (rings, sigma, 0))
    monkeypatch.setattr(
        reference, "_refine_walls", lambda *_: ([(points.copy(), normals.copy())], [])
    )
    captured = {}
    real_refit = fitting.refit_lines
    real_fillets = fitting.fit_fillets

    def refit(at, prims, margin=0.0, **kwargs):
        captured["margin"] = margin
        return real_refit(at, prims, margin=margin, **kwargs)

    def fillets(at, prims, tolerance, measured_sigma, supplied_covariance, *, blur_scales=None):
        captured.update(
            points=at.copy(), covariance=supplied_covariance, scales=blur_scales, prims=prims
        )
        if actual_fillets:
            return real_fillets(
                at,
                prims,
                tolerance,
                measured_sigma,
                supplied_covariance,
                blur_scales=blur_scales,
            )
        # Leave this controlled stage's exact input geometry intact downstream.
        # A separate actual-fit test exercises the inference on matched contours.
        for primitive in prims:
            if primitive.kind == "arc":
                primitive.data["blur_modelled"] = True
                if unresolved:
                    primitive.data["blur_unresolved"] = True
                    primitive.data["r_sd"] = math.inf

    monkeypatch.setattr(reference.fitting, "refit_lines", refit)
    monkeypatch.setattr(reference.fitting, "fit_fillets", fillets)
    result = reference.trace_on_sheet(
        rgb,
        reference="a4",
        sheet_mm=None,
        inverted=False,
        detail="standard",
        thickness_mm=thickness,
        focal_35mm=None,
        snap=True,
        notices=[],
    )
    return result, captured, ring, original, normals, sigma


@pytest.mark.parametrize("nadir", [(120.0, 100.0), (500.0, 100.0)])
def test_reference_keeps_the_actual_piecewise_thickness_frame_on_covariance_support(
    monkeypatch, nadir
):
    covariance = np.diag([0.25, 2.25])
    result, captured, ring, original, normals, _ = _controlled_trace(
        monkeypatch,
        thickness=20.0,
        covariance=covariance,
        nadir=nadir,
    )
    # Independent geometry: outward-facing top points contract about the nadir;
    # the other source points retain their original plane coordinates.
    top = np.sum(normals * (original - nadir), axis=1) > 0
    expected = original.copy()
    expected[top] = np.asarray(nadir) + 0.8 * (original[top] - nadir)
    # Points on no corrected outline are dropped (edges.correct_silhouette). This
    # prescribed silhouette jumps from the top edge to the bottom edge between two
    # samples, without the wall's edge between them, so the bottom sample beside each
    # switch lies just off it.
    *_, keep = reference.edges.correct_silhouette(original, normals, np.asarray(nadir), 100.0, 20.0, True)
    switches = np.flatnonzero(top != np.roll(top, 1))
    dropped = np.flatnonzero(~keep)
    assert len(dropped) <= len(switches)
    assert all(np.min(np.abs(d - switches)) <= 1 for d in dropped)
    expected, top = expected[keep], top[keep]
    roundoff = 16 * np.finfo(float).eps * max(np.abs(original).max(), max(map(abs, nadir)))
    np.testing.assert_allclose(captured["points"], expected, rtol=0, atol=roundoff)
    np.testing.assert_array_equal(captured["scales"], np.where(top, 0.8, 1.0))
    np.testing.assert_array_equal(ring["blur_scales"], captured["scales"])
    np.testing.assert_array_equal(captured["covariance"], covariance)
    assert captured["margin"] == 4.5
    if nadir[0] == 120.0:
        assert top.all()
        assert np.ptp(captured["points"][:, 0]) == pytest.approx(0.8 * np.ptp(original[:, 0]))
    else:
        assert top.any() and not top.all()
    assert result["profile"]["reference"]["thickness_mm"] == 20.0


@pytest.mark.parametrize("thickness", [0.0, 20.0])
def test_scalar_reference_path_keeps_its_existing_margin_and_no_covariance_scaling(
    monkeypatch, thickness
):
    _, captured, _, _, _, sigma = _controlled_trace(
        monkeypatch,
        thickness=thickness,
        covariance=None,
        nadir=(120.0, 100.0),
    )
    assert captured["margin"] == 3 * sigma
    assert captured["covariance"] is None
    if thickness:
        np.testing.assert_array_equal(captured["scales"], np.full(len(captured["points"]), 0.8))
    else:
        assert captured["scales"] is None


def test_directional_reference_without_thickness_uses_original_covariance_frame(monkeypatch):
    covariance = np.array([[1.0, 0.75], [0.75, 2.0]])
    _, captured, ring, original, _, _ = _controlled_trace(
        monkeypatch,
        thickness=0.0,
        covariance=covariance,
        nadir=(120.0, 100.0),
    )
    np.testing.assert_array_equal(captured["points"], original)
    assert captured["scales"] is None
    assert "blur_scales" not in ring
    assert captured["margin"] == pytest.approx(3 * math.sqrt((3 + math.sqrt(3.25)) / 2))


def test_unresolved_corner_recovers_its_ring_from_source_and_keeps_other_analytic_rings(
    monkeypatch,
):
    covariance = np.diag([0.25, 2.25])
    corrected = []
    equalised = []
    real_correct = fitting.correct_blur
    real_equalise = fitting.equalise_radii

    def correct(prims, sigma, **kwargs):
        corrected.append(prims)
        assert not any(p.data.get("blur_unresolved") for p in prims)
        return real_correct(prims, sigma, **kwargs)

    def equalise(rings, *args, **kwargs):
        equalised.extend(rings)
        assert not any(p.data.get("blur_unresolved") for ring in rings for p in ring)
        return real_equalise(rings, *args, **kwargs)

    monkeypatch.setattr(fitting, "correct_blur", correct)
    monkeypatch.setattr(fitting, "equalise_radii", equalise)
    result, _, _, original, _, _ = _controlled_trace(
        monkeypatch,
        thickness=0.0,
        covariance=covariance,
        nadir=(120.0, 100.0),
        unresolved=True,
        hole=True,
    )
    assert len(corrected) == len(equalised) == 1
    assert [p.kind for p in corrected[0]] == ["circle"]
    primitives = result["profile"]["primitives"]
    assert {piece["kind"] for piece in primitives["outer"]} == {"line"}
    assert primitives["holes"][0][0]["kind"] == "circle"
    # Recover the actual source geometry rather than the unresolved circle metadata.
    # The documented standard polyline tolerance is .05 mm at 2 px/mm.
    assert result["bounds"]["width"] == pytest.approx(float(np.ptp(original[:, 0])), abs=0.1)
    assert result["bounds"]["height"] == pytest.approx(float(np.ptp(original[:, 1])), abs=0.1)
    assert any("corner radius could not be determined" in note for note in result["warnings"])
    assert any(
        "One boundary was kept as a traced outline" in note
        for note in result["profile"]["reference"]["notes"]
    )


def test_actual_mixed_thickness_corner_is_withheld_before_scalar_radius_inference(monkeypatch):
    """The actual covariance branch sees both source frames and retains the outline.

    This controlled stage supplies a valid corrected geometry, not a rendered camera
    scene. Its unsupported mixed frame alone is sufficient to withhold inference.
    """
    result, captured, _, _, _, _ = _controlled_trace(
        monkeypatch,
        thickness=20.0,
        covariance=np.diag([0.25, 2.25]),
        nadir=(500.0, 100.0),
        actual_fillets=True,
    )
    assert set(captured["scales"]) == {0.8, 1.0}
    unsupported = [p for p in captured["prims"] if p.data.get("blur_unresolved")]
    assert unsupported
    assert all(math.isinf(p.data["r_sd"]) and not p.data.get("sharp") for p in unsupported)
    assert {p["kind"] for p in result["profile"]["primitives"]["outer"]} == {"line"}
    assert result["bounds"]["width"] == pytest.approx(100.0, abs=0.1)
    assert result["bounds"]["height"] == pytest.approx(70.0, abs=0.1)
    assert any("corner radius could not be determined" in note for note in result["warnings"])


_ERFC = np.frompyfunc(math.erfc, 1, 1)


def _corner_level_by_cutout(points, radius, sx, sy, order):
    """Independent area integral: positive quadrant minus the circular cutout.

    x=r(1-cos theta), y_cut=r(1-sin theta) removes the square-root endpoint.
    The production model instead integrates Gaussian mass over angular rays.
    """
    nodes, weights = np.polynomial.legendre.leggauss(order)
    angle = (nodes + 1) * math.pi / 4
    x = radius * (1 - np.cos(angle))
    height = radius * (1 - np.sin(angle))
    dx = radius * np.sin(angle) * weights * math.pi / 4
    p = np.atleast_2d(points)

    def phi(z):
        return 0.5 * _ERFC(-np.asarray(z) / math.sqrt(2)).astype(float)

    gaussian_x = np.exp(-0.5 * ((x - p[:, 0, None]) / sx) ** 2) / (sx * math.sqrt(2 * math.pi))
    cutout_y = phi((height - p[:, 1, None]) / sy) - phi(-p[:, 1, None] / sy)
    return phi(p[:, 0] / sx) * phi(p[:, 1] / sy) - np.sum(gaussian_x * cutout_y * dx, axis=1)


def _blurred_plate(radius=8.0, sx=0.5, sy=1.5):
    """Four independently inverted corners, joined by remote straight edges.

    The plate is 100 by 70 px. Other corners are at least dozens of blur widths
    away; no production probability evaluator generates the observations.
    """
    pieces, normal_pieces = [], []
    worst_order_delta = 0.0
    for index, vertex in enumerate([(-50, -35), (50, -35), (50, 35), (-50, 35)]):
        x_sigma, y_sigma = (sx, sy) if index % 2 == 0 else (sy, sx)
        angles = np.linspace(math.pi, 1.5 * math.pi, 41)
        arc_normal = np.column_stack([np.cos(angles), np.sin(angles)])
        arc = radius + radius * arc_normal
        extra_x = np.linspace(0.5, 9, 12) * x_sigma
        extra_y = np.linspace(9, 0.5, 12) * y_sigma
        geometric = np.vstack(
            [
                np.column_stack([np.zeros(12), radius + extra_y]),
                arc,
                np.column_stack([radius + extra_x, np.zeros(12)]),
            ]
        )
        normals = np.vstack(
            [np.tile([-1.0, 0.0], (12, 1)), arc_normal, np.tile([0.0, -1.0], (12, 1))]
        )
        lo = np.full(len(geometric), -6 * max(sx, sy))
        hi = -lo
        for _ in range(38):
            mid = (lo + hi) / 2
            trial = geometric + mid[:, None] * normals
            inside = _corner_level_by_cutout(trial, radius, x_sigma, y_sigma, 96) > 0.5
            lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
        half = geometric + ((lo + hi) / 2)[:, None] * normals
        independent = _corner_level_by_cutout(half, radius, x_sigma, y_sigma, 128)
        worst_order_delta = max(worst_order_delta, float(np.max(np.abs(independent - 0.5))))
        turn = _rotation(index * math.pi / 2)
        pieces.append(half @ turn.T + vertex)
        normal_pieces.append(normals @ turn.T)
    points_out, normals_out = [], []
    for index, piece in enumerate(pieces):
        points_out.extend(piece)
        normals_out.extend(normal_pieces[index])
        line = np.linspace(piece[-1], pieces[(index + 1) % 4][0], 50)[1:-1]
        points_out.extend(line)
        normals_out.extend(np.tile(normal_pieces[index][-1], (len(line), 1)))
    return np.asarray(points_out), np.asarray(normals_out), worst_order_delta


def test_actual_fitting_chain_recovers_a_uniformly_transported_finite_plate():
    """Matched synthetic geometry through the real fitting order, no image claim."""
    source, normals, oracle_error = _blurred_plate()
    assert oracle_error < 2e-8
    rotation = _rotation(0.41)
    source, normals = source @ rotation.T, normals @ rotation.T
    covariance = rotation @ np.diag([0.25, 2.25]) @ rotation.T
    points, top = edges.correct_thickness(source, normals, np.zeros(2), 100.0, 20.0)
    assert top.all()
    prims = fitting.fit_ring(points, 0.15, 3.0)
    assert prims is not None
    fitting.snap_axes([prims])
    fitting.refit_lines(points, prims, margin=4.5)
    fitting.fit_fillets(
        points,
        prims,
        0.15,
        math.sqrt(0.75),
        covariance,
        blur_scales=np.full(len(points), 0.8),
    )
    assert not any(p.data.get("blur_unresolved") for p in prims)
    fitting.correct_blur(prims, math.sqrt(0.75))
    fitting.equalise_radii([prims])
    arcs = [p for p in prims if p.kind == "arc"]
    assert len(arcs) == 4
    for arc in arcs:
        assert arc.data["r"] == pytest.approx(6.4, abs=0.015)
        assert math.isfinite(arc.data["r_sd"])
    segments = fitting.segments(prims)
    for primitive, segment in zip(prims, segments):
        if primitive.kind == "arc":
            for point in segment[1:]:
                assert np.linalg.norm(np.asarray(point) - primitive.data["c"]) == pytest.approx(
                    primitive.data["r"],
                    abs=1e-9,
                )
    polygon = Polygon(fitting.sample_segments(segments, 0.005))
    assert polygon.is_valid
    # This checks the complete closed finite geometry, including transported scale.
    expected_area = 0.8**2 * (100 * 70 - (4 - math.pi) * 8**2)
    assert polygon.area == pytest.approx(expected_area, abs=0.15)


def _line_primitives(vertices):
    vertices = np.asarray(vertices, dtype=float)
    return [
        fitting.Primitive(
            "line",
            {"c": point.copy(), "d": (following - point) / np.linalg.norm(following - point)},
            0.0,
            0.0,
        )
        for point, following in zip(vertices, np.roll(vertices, -1, axis=0))
    ]


def test_frozen_geometric_polyline_preserves_a_nearby_source_with_a_small_crossing():
    source = np.array(
        [
            [0, 0],
            [10, 0],
            [10, 10],
            [5, 10],
            [5.1, 10.1],
            [4.9, 10.1],
            [5.05, 9.95],
            [5, 10],
            [0, 10],
        ]
    )
    assert not Polygon(source).is_valid
    prims = _line_primitives([[0, 0], [10, 0], [10, 10], [0, 10]])
    vertices = reference._geometric_source_polyline(source, prims, 0.2)
    assert vertices is not None
    assert Polygon(vertices).is_valid
    np.testing.assert_allclose(vertices, [[0, 0], [10, 0], [10, 10], [0, 10]])
    # The actual complete source curve, including the crossing, remains represented
    # within the geometric-fit budget; vertices alone would be insufficient.
    boundary = LineString(np.vstack([source, source[:1]]))
    assert boundary.buffer(0.2).covers(Polygon(vertices).boundary)
    assert Polygon(vertices).boundary.buffer(0.2).covers(boundary)
    prims[0].data["c"] += 100
    np.testing.assert_allclose(vertices, [[0, 0], [10, 0], [10, 10], [0, 10]])
    assert reference._geometric_source_polyline(source, prims, 0.2) is None


@pytest.mark.parametrize("source_spike", [False, True])
def test_geometric_source_recovery_refuses_either_direction_outside_the_existing_tube(source_spike):
    square = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], float)
    spike = np.array([[0, 0], [10, 0], [10, 10], [5, 10], [5, 11], [4.9, 10], [0, 10]], float)
    source, candidate = (spike, square) if source_spike else (square, spike)
    assert reference._geometric_source_polyline(source, _line_primitives(candidate), 0.2) is None


def test_geometric_source_recovery_refuses_invalid_candidates_and_excess_work(monkeypatch):
    bow_tie = np.array([[0, 0], [10, 10], [10, 0], [0, 10]], float)
    assert reference._geometric_source_polyline(bow_tie, _line_primitives(bow_tie), 0.2) is None
    source = np.array([[5000, 0], [0, 5000], [-5000, 0], [0, -5000]], float)
    circle = [fitting.Primitive("circle", {"c": (0.0, 0.0), "r": 5000.0}, 0.0, 0.0)]

    def no_allocation(*_args, **_kwargs):
        raise AssertionError("an over-budget arc must be refused before sampling")

    monkeypatch.setattr(reference.np, "linspace", no_allocation)
    assert reference._geometric_source_polyline(source, circle, 0.03) is None


def test_geometric_recovery_sampling_does_not_silently_cap_a_large_circle():
    angles = np.linspace(0, 2 * math.pi, 2048, endpoint=False)
    source = 500 * np.column_stack([np.cos(angles), np.sin(angles)])
    circle = [fitting.Primitive("circle", {"c": (0.0, 0.0), "r": 500.0}, 0.0, 0.0)]
    vertices = reference._geometric_source_polyline(source, circle, 0.03)
    assert vertices is not None
    assert 360 < len(vertices) <= reference.MAX_TOTAL_VERTICES
    midpoints = (vertices + np.roll(vertices, -1, axis=0)) / 2
    # Independent apothem calculation on the actual emitted chords.
    sagitta = np.max(500 - np.linalg.norm(midpoints, axis=1))
    assert sagitta <= 0.03 / 16 + 2e-12


def test_actual_thick_directional_trace_no_longer_crosses_itself_and_keeps_strict_validation(
    monkeypatch,
):
    """The original regression photo; an unresolved radius is never emitted as an arc.

    Its thickness-corrected outline crossed itself where support switches between the
    top and bottom edges, along the wall's vertical edges, and was kept only as a
    bounded geometric fit (_geometric_source_polyline). Those edges are now dropped
    (edges.correct_silhouette): the corrected source is valid, and the photo traces
    with that recovery withheld. The synthetic feature scorer expects analytic outer
    arcs and cannot score this representation; this checks the validated outline.
    """
    captures = []
    original = reference._geometric_source_polyline

    def capture(points, prims, tolerance):
        candidate = original(points, prims, tolerance)
        captures.append((points.copy(), candidate, tolerance))
        return candidate

    monkeypatch.setattr(reference, "_geometric_source_polyline", capture)
    data, _ = S.render(blur=(1.0, 3.0), thickness=4.0)
    result = trace_image(data, reference="a4", thickness_mm=4.0)
    assert not captures
    profile = Profile.model_validate(result["profile"])
    assert {p.kind for p in profile.primitives.outer} == {"line"}
    assert any(p.kind == "circle" for ring in profile.primitives.holes for p in ring)
    assert any("corner radius could not be determined" in note for note in result["warnings"])
    assert not any("corrected trace crossed itself" in note for note in result["warnings"])
    # Without a bounded geometric candidate the strict Profile validation still holds,
    # and the photo traces: no buffer(0), component deletion or relaxed rule.
    monkeypatch.setattr(reference, "_geometric_source_polyline", lambda *_: None)
    Profile.model_validate(trace_image(data, reference="a4", thickness_mm=4.0)["profile"])
