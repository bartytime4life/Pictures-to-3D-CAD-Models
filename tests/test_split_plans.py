"""Bounded grid optimization, real connected pieces and explicit apply/rebuild."""

import io
import json
import math
import zipfile

import cadquery as cq
import pytest
from fastapi.testclient import TestClient
from shapely.affinity import rotate
from shapely.errors import GEOSException
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from backend import app as api
from backend import printing
from backend.models import DesignSettings


def check_proposal(polygon, thickness, design, plan):
    assert plan["status"] == "suggested" and plan["grids_considered"] == 11
    assert plan["grids_failed"] == 0
    assert 1 < plan["piece_count"] <= 8
    assert plan["columns"] * plan["rows"] <= 8
    assert sum(p["area_mm2"] for p in plan["pieces"]) == pytest.approx(polygon.area)
    candidate = design.model_copy(
        update={
            "output_mode": "split",
            "split_columns": plan["columns"],
            "split_rows": plan["rows"],
        }
    )
    pieces = printing.split_profile(polygon, candidate)
    assert unary_union(pieces).symmetric_difference(polygon).area < 1e-8
    for polygon_piece, proposed in zip(pieces, plan["pieces"], strict=True):
        fit = proposed["bed_fit"]
        x0, y0, x1, y1 = rotate(polygon_piece, fit["rotation_deg"], origin=(0, 0)).bounds
        assert x1 - x0 <= design.bed_width_mm - 2 * design.bed_margin_mm + 1e-6
        assert y1 - y0 <= design.bed_depth_mm - 2 * design.bed_margin_mm + 1e-6
        assert proposed["dimensions"]["thickness"] == thickness


@pytest.mark.parametrize("depth,bed_width,bed_depth", [(80, 150, 110), (10, 110, 110)])
def test_two_pieces_are_minimal_and_each_fits_at_a_verified_angle(depth, bed_width, bed_depth):
    polygon = box(0, 0, 250, depth)
    design = DesignSettings(bed_width_mm=bed_width, bed_depth_mm=bed_depth)
    original, settings = polygon.wkt, design.model_dump()
    plan = printing.suggest_split_plan(polygon, 4, design)
    check_proposal(polygon, 4, design, plan)
    assert (plan["columns"], plan["rows"], plan["piece_count"]) == (2, 1, 2)
    # No single piece can fit: its 250 mm edge exceeds the bed diagonal.
    assert 250 > math.hypot(bed_width - 10, bed_depth - 10)
    if depth == 10:
        assert all(p["bed_fit"]["rotation_deg"] == pytest.approx(45) for p in plan["pieces"])
    assert polygon.wkt == original and design.model_dump() == settings


def test_empty_grid_cell_is_not_counted_as_a_piece():
    polygon = Polygon([(0, 0), (100, 0), (100, 10), (10, 10), (10, 100), (0, 100)])
    design = DesignSettings(bed_width_mm=60, bed_depth_mm=60)
    plan = printing.suggest_split_plan(polygon, 4, design)
    check_proposal(polygon, 4, design, plan)
    assert (plan["columns"], plan["rows"], plan["piece_count"]) == (2, 2, 3)


def test_symmetric_ties_prefer_fewer_rows():
    plan = printing.suggest_split_plan(
        box(0, 0, 200, 200), 4, DesignSettings(bed_width_mm=210, bed_depth_mm=110)
    )
    assert (plan["columns"], plan["rows"], plan["piece_count"]) == (2, 1, 2)


def test_already_fitting_diagonal_part_is_not_split():
    assert (
        printing.suggest_split_plan(
            box(0, 0, 125, 10), 4, DesignSettings(bed_width_mm=110, bed_depth_mm=110)
        )
        is None
    )


@pytest.mark.parametrize(
    "shape,excluded",
    [("unknown", []), ("circular", []), ("rectangular", [[[0, 0], [1, 0], [1, 1]]])],
)
def test_unverified_beds_do_not_produce_suggestions(shape, excluded):
    design = DesignSettings(printer_id="catalog/test", bed_width_mm=110, bed_depth_mm=110)
    assert (
        printing.suggest_split_plan(
            box(0, 0, 250, 80), 4, design, {"bed_shape": shape, "excluded_areas_mm": excluded}
        )
        is None
    )


def test_impossible_height_margin_and_eight_piece_limit_are_explained():
    polygon = box(0, 0, 1000, 1000)
    design = DesignSettings(bed_width_mm=20, bed_depth_mm=20, bed_height_mm=20)
    height = printing.suggest_split_plan(polygon, 21, design)
    assert height["status"] == "no_fit" and height["grids_considered"] == 0
    assert "thickness" in height["reason"]
    margin = printing.suggest_split_plan(
        polygon, 4, design.model_copy(update={"bed_margin_mm": 10})
    )
    assert margin["status"] == "no_fit" and margin["grids_considered"] == 0
    limited = printing.suggest_split_plan(polygon, 4, design)
    assert limited["status"] == "no_fit" and limited["grids_considered"] == 11
    assert "at most 8" in limited["reason"]


@pytest.mark.parametrize(
    "error",
    [printing.PrintGeometryError("Too many fragments"), GEOSException("Intersection failed")],
)
def test_an_unusable_candidate_does_not_discard_the_intact_model(monkeypatch, error):
    def fail(*args):
        raise error

    monkeypatch.setattr(printing, "split_profile", fail)
    result = printing.suggest_split_plan(
        box(0, 0, 250, 80), 4, DesignSettings(bed_width_mm=110, bed_depth_mm=110)
    )
    assert result["status"] == "no_fit" and result["grids_considered"] == 11
    assert result["grids_failed"] == (11 if isinstance(error, GEOSException) else 0)


def test_partial_search_qualifies_its_suggestion(monkeypatch):
    original = printing.split_profile

    def skip_one(polygon, design):
        if (design.split_columns, design.split_rows) == (1, 2):
            raise GEOSException("Numerical intersection failure")
        return original(polygon, design)

    monkeypatch.setattr(printing, "split_profile", skip_one)
    plan = printing.suggest_split_plan(
        box(0, 0, 250, 80), 4, DesignSettings(bed_width_mm=150, bed_depth_mm=110)
    )
    assert plan["status"] == "suggested" and plan["grids_failed"] == 1
    assert "Some cut grids could not be checked" in plan["reason"]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(api, "JOB_ROOT", tmp_path_factory.mktemp("split-plan-jobs"))
        with TestClient(api.app) as instance:
            yield instance


def test_proposal_is_not_exported_as_generated_parts_and_rebuild_matches_it(client, tmp_path):
    payload = {
        "profile": {
            "outer": [[0, 0], [250, 0], [250, 80], [0, 80]],
            "holes": [[[20, 20], [30, 20], [30, 30], [20, 30]]],
        },
        "width_mm": 200,
        "thickness_mm": 4,
        "design": {"bed_width_mm": 150, "bed_depth_mm": 110, "scale_percent": 125},
    }
    response = client.post("/api/build", json=payload)
    assert response.status_code == 200, response.text
    original = response.json()
    plan = original["split_plan"]
    assert original["print_fit"]["status"] == "too_large" and len(original["parts"]) == 1
    assert plan["status"] == "suggested" and plan["piece_count"] == 2
    assert "parts" not in original["downloads"]
    recipe = client.get(original["downloads"]["project"]).json()
    assert recipe["width_mm"] == 200 and recipe["design"]["output_mode"] == "single"
    assert recipe["design"]["scale_percent"] == 125 and original["dimensions"]["width"] == 250
    assert "split_plan" not in recipe
    with zipfile.ZipFile(io.BytesIO(client.get(original["downloads"]["bambu"]).content)) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        assert (
            len(manifest["parts"]) == 1 and manifest["parts"][0]["bed_fit"]["status"] == "too_large"
        )
    payload["design"].update(
        output_mode="split", split_columns=plan["columns"], split_rows=plan["rows"]
    )
    response = client.post("/api/build", json=payload)
    assert response.status_code == 200, response.text
    rebuilt = response.json()
    assert rebuilt["print_fit"]["status"] == "fits" and "split_plan" not in rebuilt
    assert rebuilt["dimensions"] == pytest.approx(original["dimensions"])
    assert rebuilt["volume_mm3"] == pytest.approx(original["volume_mm3"])
    assert rebuilt["hole_count"] == original["hole_count"] == 1
    assert sum(p["volume_mm3"] for p in rebuilt["parts"]) == pytest.approx(original["volume_mm3"])
    assert len(rebuilt["parts"]) == plan["piece_count"]
    for actual, proposed in zip(rebuilt["parts"], plan["pieces"], strict=True):
        assert actual["dimensions"] == pytest.approx(proposed["dimensions"])
        assert actual["bed_fit"]["status"] == "fits"
        assert actual["bed_fit"]["footprint_mm"] == pytest.approx(
            proposed["bed_fit"]["footprint_mm"]
        )
    assert client.get(rebuilt["downloads"]["project"]).json()["width_mm"] == 200
    step_path = tmp_path / "split.step"
    step_path.write_bytes(client.get(rebuilt["downloads"]["step"]).content)
    solid = cq.importers.importStep(str(step_path))
    assert solid.solids().size() == 2
    assert sum(len(face.innerWires()) for face in solid.faces(">Z").vals()) == 1


def test_fitted_curve_does_not_receive_a_polygon_split_claim(client):
    circle = {"kind": "circle", "center": [100, 100], "radius": 100}
    outer = [
        [100 + 100 * math.cos(i * math.tau / 200), 100 + 100 * math.sin(i * math.tau / 200)]
        for i in range(200)
    ]
    response = client.post(
        "/api/build",
        json={
            "profile": {"outer": outer, "primitives": {"outer": [circle]}},
            "width_mm": 300,
            "thickness_mm": 4,
            "design": {"bed_width_mm": 110, "bed_depth_mm": 110},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["geometry"]["kind"] == "fitted"
    assert response.json()["print_fit"]["status"] == "unknown"
    assert "split_plan" not in response.json()
