"""Real geometry, split-file agreement and conservative printer-envelope evidence."""

import io
import json
import struct
import zipfile

import cadquery as cq
import ezdxf
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from backend import app as api
from backend import printing
from backend.models import BuildRequest, DesignSettings
from backend.worker import build
from tests import readers


def request_body(**changes):
    return {
        "profile": {
            "outer": [[0, 0], [100, 0], [100, 60], [0, 60]],
            "holes": [[[20, 20], [30, 20], [30, 30], [20, 30]]],
        },
        "width_mm": 80,
        "thickness_mm": 4,
        "name": "Measured plate",
        "revision": "design-test",
        **changes,
    }


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(api, "JOB_ROOT", tmp_path_factory.mktemp("print-jobs"))
        with TestClient(api.app) as instance:
            yield instance


@pytest.fixture(scope="module")
def split_model(client):
    response = client.post(
        "/api/build",
        json=request_body(
            design={
                "scale_percent": 200,
                "thickness_percent": 150,
                "color": "#FF6600",
                "material": "petg",
                "output_mode": "split",
                "split_columns": 2,
                "split_rows": 1,
                "bed_width_mm": 100,
                "bed_depth_mm": 120,
                "bed_height_mm": 100,
                "bed_margin_mm": 5,
            }
        ),
    )
    assert response.status_code == 200, response.text
    return response.json()


def mesh_bounds(mesh):
    vertices = mesh["vertices"]
    axes = [vertices[index::3] for index in range(3)]
    assert vertices and all(0 <= value < len(vertices) // 3 for value in mesh["triangles"])
    return [min(axis) for axis in axes], [max(axis) for axis in axes]


def test_design_scales_actual_geometry_without_replacing_measured_inputs(client, split_model):
    assert split_model["dimensions"] == pytest.approx({"width": 160, "height": 96, "thickness": 6})
    # The source polygon has 5900 square pixels; scale is 1.6 mm per pixel.
    assert split_model["volume_mm3"] == pytest.approx(5900 * 1.6**2 * 6)
    assert split_model["hole_count"] == 1
    low, high = mesh_bounds(split_model["mesh"])
    assert [end - start for start, end in zip(low, high)] == pytest.approx([160, 96, 6])
    recipe = client.get(split_model["downloads"]["project"]).json()
    assert recipe["version"] == 2
    assert recipe["width_mm"] == 80 and recipe["thickness_mm"] == 4
    assert recipe["profile"] == request_body()["profile"]
    assert recipe["design"]["color"] == "#ff6600"
    assert recipe["design"]["material"] == "petg"
    assert recipe["design"]["scale_percent"] == 200


def test_split_drawings_show_every_piece_in_its_assembled_place(client, split_model):
    area = split_model["volume_mm3"] / split_model["dimensions"]["thickness"]
    region, root = readers.svg_region(client.get(split_model["downloads"]["svg"]).text)
    outline, holes = root.findall(f"{readers.SVG}g")
    assert len(outline) == len(split_model["parts"]) == 2 and len(holes) == 1
    assert region.area == pytest.approx(area)
    x0, y0, x1, y1 = region.bounds
    assert (x1 - x0, y1 - y0) == pytest.approx((160, 96))
    page, content = readers.pdf_parts(client.get(split_model["downloads"]["pdf"]).content)
    assert page == pytest.approx((210.0, 279.4), abs=1e-3)
    closed, _, _ = readers.pdf_paths(content)
    pieces = sorted((readers.Polygon(ring) for ring in closed), key=lambda p: -p.area)
    assert len(pieces) == 3
    assert pieces[0].area + pieces[1].area - pieces[2].area == pytest.approx(area)


def test_split_zip_contains_distinct_valid_solids_with_matching_volume(
    client, split_model, tmp_path
):
    response = client.get(split_model["downloads"]["parts"])
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    assert len(split_model["parts"]) == 2
    assert split_model["print_fit"]["status"] == "fits"
    assert sum(part["volume_mm3"] for part in split_model["parts"]) == pytest.approx(
        split_model["volume_mm3"]
    )
    with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
        assert set(bundle.namelist()) == {
            "manifest.json",
            "part-01.step",
            "part-01.stl",
            "part-01.3mf",
            "part-02.step",
            "part-02.stl",
            "part-02.3mf",
        }
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["format"] == "pictures-to-cad-parts" and manifest["units"] == "mm"
        assert manifest["total_volume_mm3"] == pytest.approx(split_model["volume_mm3"])
        assert len(manifest["parts"]) == 2
        imported_volumes = []
        for part in manifest["parts"]:
            step_path = tmp_path / part["files"]["step"]
            step_path.write_bytes(bundle.read(part["files"]["step"]))
            solid = cq.importers.importStep(str(step_path)).val()
            assert solid.isValid() and len(solid.Solids()) == 1
            imported_volumes.append(solid.Volume())
            assert solid.Volume() == pytest.approx(part["volume_mm3"])
            bounds = solid.BoundingBox()
            assert [bounds.xmin, bounds.ymin, bounds.zmin] == pytest.approx([0, 0, 0], abs=1e-5)
            assert [bounds.xlen, bounds.ylen, bounds.zlen] == pytest.approx(
                [
                    part["dimensions"]["width"],
                    part["dimensions"]["height"],
                    part["dimensions"]["thickness"],
                ]
            )
            stl = bundle.read(part["files"]["stl"])
            triangle_count = struct.unpack_from("<I", stl, 80)[0]
            assert len(stl) == 84 + 50 * triangle_count
            assert triangle_count > 0
            points = [
                struct.unpack_from("<fff", stl, 84 + face * 50 + 12 + vertex * 12)
                for face in range(triangle_count)
                for vertex in range(3)
            ]
            assert [min(point[axis] for point in points) for axis in range(3)] == pytest.approx(
                [0, 0, 0], abs=1e-5
            )
            corresponding = next(item for item in split_model["parts"] if item["id"] == part["id"])
            low, high = mesh_bounds(corresponding["mesh"])
            assert low == pytest.approx(part["assembly_offset_mm"], abs=1e-5)
            assert [end - start for start, end in zip(low, high)] == pytest.approx(
                [
                    bounds.xlen,
                    bounds.ylen,
                    bounds.zlen,
                ]
            )
            assert "mesh" not in part
        assert imported_volumes[0] != pytest.approx(
            imported_volumes[1]
        )  # Only one part has the hole.
        assert sum(imported_volumes) == pytest.approx(manifest["total_volume_mm3"])
    assembly_path = tmp_path / "assembly.step"
    assembly_path.write_bytes(client.get(split_model["downloads"]["step"]).content)
    assembly = cq.importers.importStep(str(assembly_path)).val()
    assert assembly.isValid() and len(assembly.Solids()) == 2
    assert assembly.Volume() == pytest.approx(split_model["volume_mm3"])


def test_original_single_output_remains_compatible_and_has_no_parts_download(tmp_path, client):
    directory = tmp_path / "legacy"
    directory.mkdir()
    (directory / "input.json").write_text(json.dumps(request_body()))
    result = build(directory)
    assert result["dimensions"] == pytest.approx({"width": 80, "height": 48, "thickness": 4})
    assert len(result["parts"]) == 1 and "parts" not in result["downloads"]
    recipe = json.loads((directory / "project.json").read_text())
    assert recipe["version"] == 1 and "design" not in recipe
    # An unavailable bundle must be a recoverable 404, not a FileResponse error.
    job_id = "a" * 32
    api_dir = api.JOB_ROOT / job_id
    api_dir.mkdir()
    (api_dir / "result.json").write_text("{}")
    assert client.get(f"/api/download/{job_id}/parts").status_code == 404


def test_nozzle_detail_changes_real_export_outline_and_retains_holes(tmp_path):
    outer = [
        [0, 0],
        [100, 0],
        [100, 50],
        [80, 50],
        [79, 50.05],
        [78, 50],
        [60, 50],
        [59, 50.05],
        [58, 50],
        [0, 50],
    ]
    payload = request_body(
        profile={"outer": outer, "holes": [[[20, 20], [25, 20], [25, 25], [20, 25]]]},
        width_mm=100,
        design={"detail_mode": "draft", "nozzle_mm": 0.4},
    )
    (tmp_path / "input.json").write_text(json.dumps(payload))
    result = build(tmp_path)
    expected = Polygon(outer, payload["profile"]["holes"]).simplify(0.2, preserve_topology=True)
    drawing = ezdxf.readfile(tmp_path / "profile.dxf")
    outlines = list(drawing.modelspace().query('LWPOLYLINE[layer=="OUTLINE"]'))
    assert len(outlines) == 1 and len(outlines[0]) < len(outer)
    assert result["hole_count"] == 1
    assert result["volume_mm3"] == pytest.approx(expected.area * 4)
    assert any("0.2 mm simplification tolerance" in message for message in result["warnings"])
    source = Polygon(outer, payload["profile"]["holes"])
    unchanged, warnings = printing.prepare_profile(source, DesignSettings())
    assert unchanged.equals_exact(source, 0) and not warnings


def test_grid_counts_connected_fragments_and_preserves_area():
    comb = unary_union([box(0, 0, 90, 2), *[box(i * 10, 0, i * 10 + 4, 10) for i in range(9)]])
    assert isinstance(comb, Polygon)
    with pytest.raises(printing.PrintGeometryError, match="more than 8"):
        printing.split_profile(
            comb, DesignSettings(output_mode="split", split_columns=1, split_rows=2)
        )
    ring = box(0, 0, 100, 60).difference(box(40, 20, 60, 40))
    pieces = printing.split_profile(ring, DesignSettings(output_mode="split", split_columns=2))
    assert len(pieces) == 2
    assert unary_union(pieces).equals(ring)
    assert sum(piece.area for piece in pieces) == pytest.approx(ring.area)


@pytest.mark.parametrize(
    "design",
    [
        {"scale_percent": 9},
        {"scale_percent": 401},
        {"thickness_percent": 0},
        {"color": "red"},
        {"material": "unknown"},
        {"detail_mode": "infinite"},
        {"nozzle_mm": 0.09},
        {"nozzle_mm": 8.1},
        {"split_columns": 4, "split_rows": 4},
        {"split_columns": True},
        {"bed_width_mm": 19},
        {"bed_height_mm": 5001},
        {"bed_margin_mm": 31},
        {"scale_percent": float("nan")},
        {"unknown": "setting"},
    ],
)
def test_design_limits(design):
    with pytest.raises(ValidationError):
        BuildRequest.model_validate(request_body(design=design))


@pytest.mark.parametrize(
    "changes",
    [
        {"width_mm": 1000, "design": {"scale_percent": 400}},
        {"thickness_mm": 200, "design": {"thickness_percent": 400}},
        {"width_mm": 0.1, "design": {"scale_percent": 10}},
    ],
)
def test_effective_cad_dimensions_stay_bounded(changes):
    with pytest.raises(ValidationError):
        BuildRequest.model_validate(request_body(**changes))


def test_bed_fit_checks_margin_rotation_height_and_unknown_shapes():
    design = DesignSettings(bed_width_mm=100, bed_depth_mm=200, bed_height_mm=100, bed_margin_mm=5)
    dims = {"width": 150, "height": 80, "thickness": 5}
    assert printing.bed_fit(dims, design)["rotated_90"]
    assert printing.bed_fit({**dims, "thickness": 101}, design)["status"] == "too_large"
    assert printing.bed_fit({**dims, "height": 91}, design)["status"] == "too_large"
    selected = design.model_copy(update={"printer_id": "catalog/example"})
    for printer in (
        None,
        {"bed_shape": "circular"},
        {"bed_shape": "polygon"},
        {"bed_shape": "rectangular", "excluded_areas_mm": [[[0, 0], [2, 0], [2, 2]]]},
    ):
        assert printing.bed_fit(dims, selected, printer)["status"] == "unknown"


def test_known_printer_uses_exact_nozzle_profile_and_rejects_ambiguous_fit(tmp_path, monkeypatch):
    def profile(nozzle, width):
        return {
            "nozzle_diameters_mm": [nozzle],
            "build_volume": {"x_mm": width, "y_mm": 200, "z_mm": 2100},
            "bed_shape": "rectangular",
            "printable_area_mm": [[0, 0], [width, 0], [width, 200], [0, 200]],
            "excluded_areas_mm": [],
        }

    catalog = {
        "schema_version": 1,
        "printers": [{"id": "catalog/real", "profiles": [profile(0.4, 220), profile(0.6, 180)]}],
    }
    path = tmp_path / "printers.json"
    path.write_text(json.dumps(catalog))
    monkeypatch.setattr(printing, "CATALOG_PATH", path)
    settings, printer, warnings = printing.resolve_design(
        DesignSettings(
            printer_id="catalog/real",
            nozzle_mm=0.6,
            bed_width_mm=1000,
            bed_height_mm=1000,
        )
    )
    assert settings.bed_width_mm == 180 and settings.bed_height_mm == 2100
    assert not warnings
    assert (
        printing.bed_fit({"width": 190, "height": 190, "thickness": 5}, settings, printer)["status"]
        == "too_large"
    )
    catalog["printers"][0]["profiles"].append(profile(0.6, 160))
    path.write_text(json.dumps(catalog))
    settings, printer, warnings = printing.resolve_design(settings)
    assert (
        warnings
        and printing.bed_fit({"width": 50, "height": 50, "thickness": 5}, settings, printer)[
            "status"
        ]
        == "unknown"
    )
    settings, printer, warnings = printing.resolve_design(
        settings.model_copy(update={"nozzle_mm": 0.8})
    )
    assert warnings and printer["bed_shape"] == "unknown"


def test_catalog_is_available_offline_and_profiles_fit_supported_input_bounds(client):
    response = client.get("/api/printers")
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["schema_version"] == 1 and len(catalog["printers"]) >= 1
    assert catalog["source"]["commit"]
    for printer in catalog["printers"]:
        for profile in printer["profiles"]:
            volume = profile["build_volume"]
            for nozzle in profile["nozzle_diameters_mm"]:
                DesignSettings(
                    nozzle_mm=nozzle,
                    bed_width_mm=volume["x_mm"],
                    bed_depth_mm=volume["y_mm"],
                    bed_height_mm=volume["z_mm"],
                )
