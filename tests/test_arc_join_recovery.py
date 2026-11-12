"""Recover an unavailable canonical join without losing unrelated sheet geometry.

The construction-error injections exercise the caller contract; they do not
claim to reproduce the numerical join solver or qualify a camera model.
"""

import copy
import io
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from shapely.geometry import Polygon

from backend import app as api
from backend import edges, fitting, reference
from backend.circular_joins import JoinConstructionError
from backend.models import Profile
from tests import synthetic as S


@pytest.mark.parametrize(
    "reason",
    [
        "near_contact",
        "no_intersection",
        "ambiguous",
        "source_provenance",
        "numerical",
        "work_limit",
        "invalid_cycle",
    ],
)
def test_unavailable_join_retains_the_source_with_a_bounded_targeted_notice(monkeypatch, reason):
    # A concave, independently supplied boundary must not become a convex hull or
    # another analytic shape merely because its fitted join is unavailable.
    points = np.array([[0, 0], [8, 0], [8, 3], [3, 3], [3, 8], [0, 8]], dtype=float)

    def unavailable(_):
        raise JoinConstructionError(reason, "internal diagnostic is not user guidance")

    monkeypatch.setattr(fitting, "segments", unavailable)
    notices = []
    segments, analytic = reference._segments_for(
        points, [object()], 0.001, notices, "hole 2 boundary"
    )
    assert not analytic
    assert all(segment[0] == "line" for segment in segments)
    retained = Polygon(fitting.sample_segments(segments, 0.001))
    assert retained.is_valid and retained.symmetric_difference(Polygon(points)).area == 0
    assert len(notices) == 1
    assert "hole 2 boundary was kept as a traced outline" in notices[0]
    assert "measure critical curves in CAD" in notices[0]
    assert "internal diagnostic" not in notices[0]
    assert len(notices[0]) <= 300


def test_unrelated_construction_error_is_not_silently_converted_to_a_polyline(monkeypatch):
    def broken(_):
        raise ValueError("unexpected implementation defect")

    monkeypatch.setattr(fitting, "segments", broken)
    with pytest.raises(ValueError, match="unexpected implementation defect"):
        reference._segments_for(np.array([[0, 0], [4, 0], [4, 3], [0, 3]]), [object()], 0.01)


def test_invalid_source_after_unavailable_join_is_not_a_missing_sheet(monkeypatch):
    def unavailable(_):
        raise JoinConstructionError("no_intersection")

    monkeypatch.setattr(fitting, "segments", unavailable)
    crossing = np.array([[0, 0], [5, 5], [0, 5], [5, 0]], dtype=float)
    with pytest.raises(reference.ReferenceError_, match="could not be joined reliably") as error:
        reference._segments_for(crossing, [object()], 0.01)
    assert not error.value.sheet_missing


def test_available_circle_keeps_its_exact_description_without_recovery_notices():
    points = circle_points(np.array([17, -21]), 12)
    prims = [fitting.Primitive("circle", {"c": (17, -21), "r": 12.0}, 0, 0)]
    notices = []
    segments, analytic = reference._segments_for(points, prims, 0.02, notices)
    assert analytic and len(segments) == 1 and segments[0][0] == "circle"
    np.testing.assert_array_equal(segments[0][1], [17, -21])
    assert segments[0][2] == 12
    assert notices == []


def circle_points(centre, radius):
    angles = np.arange(256) * (2 * math.pi / 256)
    return centre + radius * np.column_stack([np.cos(angles), np.sin(angles)])


def rejected_primitives():
    # The radius note and snapped-line claims would name geometry that the
    # caller discards. Real fitting/design functions still update these values.
    return [
        fitting.Primitive("line", {"c": (150, 100), "d": np.array([1.0, 0.0])}, 0, 0),
        fitting.Primitive("line", {"c": (400, 200), "d": np.array([0.0, 1.0])}, 0, 0),
        fitting.Primitive(
            "arc",
            {
                "c": (260, 240),
                "r": 20.1,
                "mid": (280.1, 240),
                "r_sd": math.inf,
                "corner_deg": 150.0,
                "reject_join": True,
            },
            0,
            0,
        ),
    ]


@pytest.fixture(scope="module")
def capture():
    return S.colour_photo((80,) * 3, (235,) * 3, (50,) * 3, ppm=3.0, blur=1.2)


def install_measurement_fixture(
    monkeypatch, *, rejected="outer", accepted_holes=1, invalid=False, noisy_notes=False
):
    """Supply known rings at the measurement seam; use real sheet scale and output validation."""
    if rejected == "outer":
        outer = np.array([[100, 100], [460, 100], [460, 360], [100, 360]], dtype=float)
        holes = [
            circle_points(np.array([220 + index * 120, 230]), 20) for index in range(accepted_holes)
        ]
        groups = [
            rejected_primitives(),
            *[
                [fitting.Primitive("circle", {"c": (220 + index * 120, 230), "r": 20.0}, 0, 0)]
                for index in range(accepted_holes)
            ],
        ]
    else:
        outer = circle_points(np.array([280, 300]), 150)
        holes = [np.array([[240, 260], [280, 260], [280, 300], [240, 300]], dtype=float)]
        groups = [
            [fitting.Primitive("circle", {"c": (280, 300), "r": 150.0}, 0, 0)],
            rejected_primitives(),
        ]
    if invalid == "crossed_source":
        outer = outer[[0, 2, 1, 3]]
    elif invalid == "hole_outside":
        holes[0] = circle_points(np.array([520, 230]), 20)
        groups[1][0].data["c"] = (520, 230)
    rings = [{"outer": True, "points": outer}, *[{"outer": False, "points": p} for p in holes]]
    monkeypatch.setattr(edges, "subpixel_rings", lambda *args: (copy.deepcopy(rings), 1.0, 0))
    candidates = iter(groups)
    monkeypatch.setattr(
        fitting, "fit_ring", lambda *args, **kwargs: copy.deepcopy(next(candidates))
    )
    # These tests isolate final geometry selection, not the upstream line/corner fitter.
    monkeypatch.setattr(fitting, "refit_lines", lambda *args, **kwargs: None)
    monkeypatch.setattr(fitting, "fit_fillets", lambda *args, **kwargs: None)
    actual_segments = fitting.segments

    def canonical_or_unavailable(prims):
        if any(p.data.get("reject_join") for p in prims):
            raise JoinConstructionError("ambiguous")
        return actual_segments(prims)

    monkeypatch.setattr(fitting, "segments", canonical_or_unavailable)
    if noisy_notes:
        actual_segment = edges.segment

        def segment(*args, **kwargs):
            mask, notes = actual_segment(*args, **kwargs)
            return mask, [*notes, *[f"Earlier capture note {index}." for index in range(20)]]

        monkeypatch.setattr(edges, "segment", segment)


@pytest.mark.parametrize("accepted_holes", [1, 2])
def test_recovery_keeps_analytic_holes_scale_and_only_final_geometry_notes(
    monkeypatch, capture, accepted_holes
):
    install_measurement_fixture(monkeypatch, accepted_holes=accepted_holes, noisy_notes=True)
    with Image.open(io.BytesIO(capture)) as image:
        result = reference.trace_on_sheet(
            np.asarray(image),
            reference="a4",
            sheet_mm=None,
            inverted=False,
            detail="fine",
            thickness_mm=None,
            focal_35mm=None,
            snap=True,
            notices=[],
        )
    profile = Profile.model_validate(result["profile"])
    assert all(segment.kind == "line" for segment in profile.primitives.outer)
    assert [ring[0].kind for ring in profile.primitives.holes] == ["circle"] * accepted_holes
    assert all(len(ring) == 1 for ring in profile.primitives.holes)
    assert profile.reference.kind == "a4"
    assert profile.reference.sheet_mm == (210, 297)
    assert profile.reference.mm_per_px == pytest.approx(0.25)
    notes = profile.reference.notes
    assert len(notes) == 16
    assert notes[0].startswith(f"Fitted {accepted_holes} circle(s), 0 arc(s) and 0 line(s)")
    recovery = next(note for note in notes if "outer boundary was kept" in note)
    assert recovery in result["warnings"]
    assert "more than one possible fitted join" in recovery
    assert not any(
        "fit could not settle" in note or "made exactly parallel" in note for note in notes
    )
    assert not any("Turn on snapping" in note for note in [*notes, *result["warnings"]])
    if accepted_holes == 1:
        assert any(note.startswith("1 fitted radius adjusted to") for note in notes)
        assert not any("radii made equal" in note for note in notes)
    else:
        assert any(note.startswith("2 radii made equal") for note in notes)
        assert not any(note.startswith("3 radii") for note in notes)
    assert not any("Rotated" in note for note in notes)


def test_hole_recovery_keeps_the_analytic_outer_boundary(monkeypatch, capture):
    install_measurement_fixture(monkeypatch, rejected="hole")
    with Image.open(io.BytesIO(capture)) as image:
        result = reference.trace_on_sheet(
            np.asarray(image),
            reference="a4",
            sheet_mm=None,
            inverted=False,
            detail="standard",
            thickness_mm=None,
            focal_35mm=None,
            snap=False,
            notices=[],
        )
    profile = Profile.model_validate(result["profile"])
    assert len(profile.primitives.outer) == 1
    assert profile.primitives.outer[0].kind == "circle"
    assert all(segment.kind == "line" for segment in profile.primitives.holes[0])
    notice = next(note for note in profile.reference.notes if "hole 1 boundary was kept" in note)
    assert notice in result["warnings"]
    assert not any("could not settle" in note for note in profile.reference.notes)


def test_saved_note_budget_covers_all_32_retained_holes(monkeypatch, capture):
    install_measurement_fixture(monkeypatch, rejected="hole")
    rings = [{"outer": True, "points": circle_points(np.array([400, 450]), 180)}]
    for row in range(4):
        for column in range(8):
            centre = np.array([295 + 30 * column, 405 + 30 * row])
            rings.append(
                {
                    "outer": False,
                    "points": centre + np.array([[-8, -8], [8, -8], [8, 8], [-8, 8]]),
                }
            )
    groups = iter(
        [
            [fitting.Primitive("circle", {"c": (400, 450), "r": 180.0}, 0, 0)],
            *[rejected_primitives() for _ in range(32)],
        ]
    )
    monkeypatch.setattr(edges, "subpixel_rings", lambda *args: (copy.deepcopy(rings), 1.0, 0))
    monkeypatch.setattr(fitting, "fit_ring", lambda *args, **kwargs: copy.deepcopy(next(groups)))
    with Image.open(io.BytesIO(capture)) as image:
        result = reference.trace_on_sheet(
            np.asarray(image),
            reference="a4",
            sheet_mm=None,
            inverted=False,
            detail="fine",
            thickness_mm=None,
            focal_35mm=None,
            snap=False,
            notices=[],
        )
    profile = Profile.model_validate(result["profile"])
    assert len(profile.holes) == 32
    assert profile.primitives.outer[0].kind == "circle"
    assert all(segment.kind == "line" for ring in profile.primitives.holes for segment in ring)
    summary = next(note for note in profile.reference.notes if note.startswith("32 boundaries"))
    assert "holes 1, 2, 3" in summary and ", 31, 32)" in summary
    assert len(summary) <= 300 and len(profile.reference.notes) <= 16
    assert summary in result["warnings"]
    assert sum(note.startswith("The hole ") for note in result["warnings"]) == 32
    assert not any("could not settle" in note for note in profile.reference.notes)


@pytest.mark.parametrize("fallback", [False, True])
@pytest.mark.parametrize("invalid", ["crossed_source", "hole_outside"])
def test_invalid_join_fallback_returns_422_then_same_client_can_trace(
    monkeypatch, tmp_path, capture, fallback, invalid
):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    with TestClient(api.app) as client:
        with monkeypatch.context() as local:
            install_measurement_fixture(local, invalid=invalid)
            response = client.post(
                "/api/trace",
                files={"file": ("part.png", capture, "image/png")},
                data={"reference": "a4", "snap": "false", "fallback": str(fallback).lower()},
            )
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == reference.JOIN_RECOVERY_ERROR
        assert "without one" not in response.text
        recovered = client.post(
            "/api/trace",
            files={"file": ("clear.png", capture, "image/png")},
            data={"reference": "a4", "snap": "false"},
        )
        assert recovered.status_code == 200, recovered.text
        profile = recovered.json()["profile"]
        assert profile["reference"]["kind"] == "a4"
        assert profile["primitives"]["outer"][0]["kind"] == "circle"
        assert profile["primitives"]["holes"][0][0]["kind"] == "circle"
