"""Independent analytic and exported-solid checks of conservative curved placement."""

import copy
import io
import json
import math
import zipfile

import cadquery as cq
import numpy as np
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import MultiPoint, Polygon

from backend import app as api
from backend import printing, worker
from backend.curve_envelope import ENCLOSURE_DIRECTIONS, fitted_outer_envelope
from backend.models import DesignSettings
from backend.placement import rectangular_placement


def capsule_profile():
    outer = [(10, 0), (115, 0)]
    outer += [(115 + 10 * math.cos(t), 10 + 10 * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 61)[1:]]
    outer += [(10, 20)]
    outer += [(10 + 10 * math.cos(t), 10 + 10 * math.sin(t)) for t in np.linspace(math.pi / 2, 3 * math.pi / 2, 61)[1:-1]]
    hole = [(60 + 3 * math.cos(t), 10 + 3 * math.sin(t)) for t in np.linspace(0, math.tau, 60, endpoint=False)]
    return {
        "outer": outer, "holes": [hole],
        "primitives": {
            "outer": [
                {"kind": "line", "start": [10, 0], "end": [115, 0]},
                {"kind": "arc", "start": [115, 0], "mid": [125, 10], "end": [115, 20]},
                {"kind": "line", "start": [115, 20], "end": [10, 20]},
                {"kind": "arc", "start": [10, 20], "mid": [0, 10], "end": [10, 0]},
            ],
            "holes": [[{"kind": "circle", "center": [60, 10], "radius": 3}]],
        },
    }


@pytest.mark.parametrize("sweep", [-1.5 * math.pi, -math.pi, -math.pi / 2, math.pi / 2, math.pi, 1.5 * math.pi])
@pytest.mark.parametrize("start", [-0.017, 2.1])
def test_outer_bound_contains_clockwise_counterclockwise_major_and_wrapping_arcs(start, sweep):
    centre = np.array([100_000.0, -100_000.0])
    radius = 17.5

    def point(angle):
        return tuple(centre + radius * np.array([math.cos(angle), math.sin(angle)]))

    a, mid, b = point(start), point(start + sweep / 2), point(start + sweep)
    ring = [("arc", a, mid, b), ("line", b, a)]
    original = copy.deepcopy(ring)
    enclosure = fitted_outer_envelope(ring)
    # This oracle uses the known circle, not arc_geometry or support coefficients.
    dense = MultiPoint([point(t) for t in np.linspace(start, start + sweep, 4097)])
    assert enclosure.covers(dense)
    assert len(enclosure.exterior.coords) <= ENCLOSURE_DIRECTIONS + 1
    assert ring == original


def test_inscribed_circle_cannot_create_a_false_positive_fit():
    radius = 50.01
    sampled = Polygon([(radius * math.cos(t), radius * math.sin(t)) for t in np.linspace(0, math.tau, 24, endpoint=False)])
    assert rectangular_placement(sampled, 100, 100) is not None
    fit = printing.bed_fit(
        {"width": 2 * radius, "height": 2 * radius, "thickness": 4},
        DesignSettings(bed_width_mm=110, bed_depth_mm=110),
        fitted_outer=[("circle", (0, 0), radius)],
    )
    assert fit["status"] == "unknown" and fit["basis"] == "curve_envelope"
    assert "rotation_deg" not in fit


def test_maximum_segment_budget_produces_a_bounded_outer_polygon():
    points = [(100 * math.cos(t), 100 * math.sin(t)) for t in np.linspace(0, math.tau, 2000, endpoint=False)]
    ring = [("line", a, b) for a, b in zip(points, points[1:] + points[:1])]
    enclosure = fitted_outer_envelope(ring)
    assert len(enclosure.exterior.coords) <= ENCLOSURE_DIRECTIONS + 1
    assert enclosure.covers(Polygon(points))


def test_numerical_enclosure_failure_remains_unknown(monkeypatch):
    def fail(*args):
        raise ValueError("Numerical enclosure failure")

    monkeypatch.setattr(printing, "fitted_outer_envelope", fail)
    fit = printing.bed_fit(
        {"width": 125, "height": 20, "thickness": 4},
        DesignSettings(bed_width_mm=110, bed_depth_mm=110),
        fitted_outer=[("circle", (0, 0), 50)],
    )
    assert fit["status"] == "unknown" and "could not be verified" in fit["reason"]


@pytest.mark.parametrize("shape,excluded", [("circular", []), ("unknown", []), ("rectangular", [[[0, 0], [1, 0], [0, 1]]])])
def test_shaped_or_excluded_beds_are_still_unverified(shape, excluded):
    fit = printing.bed_fit(
        {"width": 125, "height": 20, "thickness": 4},
        DesignSettings(printer_id="catalog/test", bed_width_mm=110, bed_depth_mm=110),
        {"bed_shape": shape, "excluded_areas_mm": excluded},
        fitted_outer=[("circle", (0, 0), 50)],
    )
    assert fit["status"] == "unknown" and "rotation_deg" not in fit


@pytest.mark.parametrize("with_hole", [False, True])
def test_curved_placement_preserves_exact_cad_and_checks_downloaded_step(tmp_path, monkeypatch, with_hole):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    profile = capsule_profile()
    if not with_hole:
        profile["holes"] = []
        profile["primitives"]["holes"] = []
    with TestClient(api.app) as client:
        response = client.post("/api/build", json={
            "profile": profile, "width_mm": 125, "thickness_mm": 4,
            "design": {"bed_width_mm": 110, "bed_depth_mm": 110},
        })
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["geometry"] == {"kind": "fitted", "lines": 2, "arcs": 2, "circles": int(with_hole)}
        assert result["print_fit"]["status"] == "fits" and "split_plan" not in result
        fit = result["parts"][0]["bed_fit"]
        assert fit["basis"] == "curve_envelope" and fit["enclosure_directions"] == 256
        assert fit["rotation_deg"] == pytest.approx(45)
        assert result["dimensions"] == pytest.approx({"width": 125, "height": 20, "thickness": 4})
        assert result["parts"][0]["dimensions"] == pytest.approx(result["dimensions"], abs=1e-6)
        step_path = tmp_path / "download.step"
        step_path.write_bytes(client.get(result["downloads"]["step"]).content)
        imported = cq.importers.importStep(str(step_path))
        assert imported.solids().size() == 1
        solid = imported.val()
        assert solid.Volume() == pytest.approx(4 * (2100 + (100 - 9 * with_hole) * math.pi))
        assert sum(len(face.innerWires()) for face in imported.faces(">Z").vals()) == int(with_hole)
        rotated = solid.rotate((0, 0, 0), (0, 0, 1), fit["rotation_deg"]).BoundingBox()
        exact_extent = 105 / math.sqrt(2) + 20
        assert rotated.xlen == pytest.approx(exact_extent)
        assert rotated.ylen == pytest.approx(exact_extent)
        assert rotated.xlen <= fit["footprint_mm"]["width"] <= 100
        assert rotated.ylen <= fit["footprint_mm"]["depth"] <= 100
        # STEP stays in the original orientation; the enclosure is planning data.
        assert solid.BoundingBox().xlen == pytest.approx(125)
        recipe = client.get(result["downloads"]["project"]).json()
        assert recipe["width_mm"] == 125 and recipe["design"]["output_mode"] == "single"
        assert recipe["profile"]["primitives"]["outer"][1]["kind"] == "arc"
        with zipfile.ZipFile(io.BytesIO(client.get(result["downloads"]["bambu"]).content)) as bundle:
            manifest = json.loads(bundle.read("manifest.json"))
            assert manifest["parts"][0]["bed_fit"] == fit


def test_measurements_do_not_change_after_curved_solid_is_meshed():
    solid = (cq.Workplane("XY").moveTo(10, 0).lineTo(115, 0)
             .threePointArc((125, 10), (115, 20)).lineTo(10, 20)
             .threePointArc((0, 10), (10, 0)).close().extrude(4).val())
    expected = {"width": 125, "height": 20, "thickness": 4}
    assert worker.dimensions_of(solid) == pytest.approx(expected, abs=1e-6)
    solid.tessellate(0.05, 0.1)
    assert worker.dimensions_of(solid) == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("angle,extent", [(0, 94.25), (45, 1)])
def test_worker_refuses_an_unconfirmed_witness_without_discarding_cad(tmp_path, monkeypatch, angle, extent):
    # One angle does not fit the bed; the other fits but understates its footprint.
    # Neither may be promoted to a verified placement, even if planning says fits.
    monkeypatch.setattr(worker, "bed_fit", lambda *args, **kwargs: {
        "status": "fits", "basis": "curve_envelope", "rotation_deg": angle,
        "footprint_mm": {"width": extent, "depth": extent}, "rotated_90": False,
    })
    (tmp_path / "input.json").write_text(json.dumps({
        "profile": capsule_profile(), "width_mm": 125, "thickness_mm": 4,
        "design": {"bed_width_mm": 110, "bed_depth_mm": 110},
    }))
    result = worker.build(tmp_path)
    assert result["geometry"]["kind"] == "fitted"
    assert result["print_fit"]["status"] == "unknown"
    assert "rotation_deg" not in result["parts"][0]["bed_fit"]
    assert cq.importers.importStep(str(tmp_path / "model.step")).solids().size() == 1


def test_kernel_placement_failure_preserves_the_cad_export(tmp_path, monkeypatch, caplog):
    def fail(*args):
        raise RuntimeError("Injected kernel rotation failure")

    monkeypatch.setattr(cq.Shape, "rotate", fail)
    (tmp_path / "input.json").write_text(json.dumps({
        "profile": capsule_profile(), "width_mm": 125, "thickness_mm": 4,
        "design": {"bed_width_mm": 110, "bed_depth_mm": 110},
    }))
    result = worker.build(tmp_path)
    assert result["print_fit"]["status"] == "unknown"
    assert "rotation_deg" not in result["parts"][0]["bed_fit"]
    assert "Injected kernel rotation failure" in caplog.text
    assert cq.importers.importStep(str(tmp_path / "model.step")).solids().size() == 1
