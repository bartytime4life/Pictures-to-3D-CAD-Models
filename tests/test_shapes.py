"""Exact shape composition, export geometry, bounded API inputs and worker cleanup."""

import math

import cadquery as cq
import ezdxf
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import app as api
from backend.shape_worker import design_profile
from backend.shapes import ShapeBuildRequest


def shape(kind="rectangle", **changes):
    return {"id": "base", "kind": kind, "width_mm": 60, "height_mm": 30, **changes}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    with TestClient(api.app) as instance:
        yield instance


def test_washer_exports_exact_circles_and_roundtrips_step(client):
    result = client.post(
        "/api/designer/build",
        json={
            "thickness_mm": 3,
            "shapes": [
                shape("circle", width_mm=40, height_mm=40),
                shape("circle", id="hole", operation="cut", width_mm=14, height_mm=14),
            ],
        },
    )
    assert result.status_code == 200, result.text
    model = result.json()
    expected = math.pi * (20**2 - 7**2) * 3
    assert model["volume_mm3"] == pytest.approx(expected, rel=1e-8)
    assert model["dimensions"] == pytest.approx(
        {"width": 40, "height": 40, "thickness": 3}, abs=1e-6
    )
    assert model["geometry"]["circles"] == 2
    assert model["hole_count"] == 1
    directory = api.JOB_ROOT / model["id"]
    assert len(ezdxf.readfile(directory / "profile.dxf").modelspace().query("CIRCLE")) == 2
    imported = cq.importers.importStep(str(directory / "model.step")).val()
    assert imported.isValid() and imported.Volume() == pytest.approx(expected, rel=1e-7)
    assert client.get(model["downloads"]["stl"]).status_code == 200
    assert client.get(model["downloads"]["project"]).json()["profile"]["primitives"]


def test_overlapping_shapes_fuse_with_exact_semicircle(client):
    result = client.post(
        "/api/designer/build",
        json={
            "thickness_mm": 4,
            "shapes": [
                shape(),
                shape("circle", id="tab", x_mm=30, width_mm=30, height_mm=30),
            ],
        },
    )
    assert result.status_code == 200, result.text
    model = result.json()
    assert model["volume_mm3"] == pytest.approx((60 * 30 + math.pi * 15**2 / 2) * 4, rel=1e-7)
    assert model["dimensions"]["width"] == pytest.approx(75, abs=1e-6)
    assert model["geometry"]["arcs"] == 1


def test_disconnected_shapes_fail_with_actionable_message_and_no_orphan_job(client):
    result = client.post(
        "/api/designer/build", json={"shapes": [shape(), shape(id="other", x_mm=200)]}
    )
    assert result.status_code == 422
    assert "one connected part" in result.json()["detail"]
    assert not list(api.JOB_ROOT.iterdir())
    assert not api.app.state.cad_lock.locked()


@pytest.mark.parametrize(
    "kind,w,h,radius",
    [
        ("rectangle", 40, 30, 0),
        ("rounded_rectangle", 40, 30, 5),
        ("rounded_rectangle", 30, 30, 15),
        ("slot", 30, 30, 3),
        ("slot", 10, 40, 3),
        ("triangle", 40, 30, 0),
        ("hexagon", 40, 30, 0),
    ],
)
def test_common_shapes_form_valid_profiles(kind, w, h, radius):
    profile = design_profile(
        ShapeBuildRequest(shapes=[shape(kind, width_mm=w, height_mm=h, corner_mm=radius)])
    )
    assert profile.primitives and not profile.holes
    assert len(profile.outer) <= 2000


def test_cutout_can_open_an_edge_to_form_a_notch():
    request = ShapeBuildRequest(
        shapes=[
            shape(),
            shape("circle", id="cut", x_mm=30, width_mm=10, height_mm=10, operation="cut"),
        ]
    )
    profile = design_profile(request)
    assert profile.holes == []
    assert any(segment.kind == "arc" for segment in profile.primitives.outer)


@pytest.mark.parametrize(
    "shapes",
    [
        [shape(operation="cut")],
        [shape(width_mm=0)],
        [shape(x_mm=1001)],
        [shape("rounded_rectangle", corner_mm=20)],
        [shape("execute")],
        [shape(), shape()],
        [shape(id=str(index)) for index in range(17)],
    ],
)
def test_invalid_shape_input_is_refused_before_starting_a_worker(client, shapes):
    result = client.post("/api/designer/build", json={"shapes": shapes})
    assert result.status_code == 422
    assert not list(api.JOB_ROOT.iterdir())


def test_nonfinite_shape_coordinates_are_rejected():
    with pytest.raises(ValidationError):
        ShapeBuildRequest(shapes=[shape(x_mm=float("nan"))])
