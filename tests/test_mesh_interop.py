"""Workbench exports checked by the reference library's independent STL checker.

The workbench builds solids with CadQuery; ``reference-library/cadkit`` is a separate,
standard-library-only implementation of the mesh checks in the handbook (sections 2,
12, and 18). Running one on the other's output ties the two components together: every
exported STL must be closed, manifold, consistently oriented, outward-facing, and must
have exactly one through-hole (genus) per traced hole.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend import app as api

LIBRARY = Path(__file__).resolve().parents[1] / "reference-library"


@pytest.fixture(scope="module")
def mesh():
    """``cadkit.stl`` from the reference library, imported without installing it."""
    sys.path.insert(0, str(LIBRARY))
    try:
        from cadkit import stl
    finally:
        sys.path.remove(str(LIBRARY))
    return stl


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(api, "JOB_ROOT", tmp_path_factory.mktemp("interop-jobs"))
        with TestClient(api.app) as instance:
            yield instance


def square_plate(**changes):
    return {
        "profile": {
            "outer": [[0, 0], [100, 0], [100, 60], [0, 60]],
            "holes": [
                [[20, 20], [30, 20], [30, 30], [20, 30]],
                [[70, 20], [80, 20], [80, 30], [70, 30]],
            ],
        },
        "width_mm": 80,
        "thickness_mm": 4,
        "name": "Interop plate",
        "revision": "interop-1",
        **changes,
    }


def photo_with_round_holes():
    image = Image.new("RGB", (500, 360), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((50, 60, 450, 300), fill="black")
    for x in (120, 330):
        draw.ellipse((x, 120, x + 50, 170), fill="white")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def download(client, url, path):
    response = client.get(url)
    assert response.status_code == 200, response.text
    path.write_bytes(response.content)
    return path


def assert_printable(report, *, holes):
    assert report["watertight"], report
    assert report["manifold"], report
    assert report["orientation_consistent"], report
    assert report["degenerate_triangles"] == 0
    assert report["components"] == 1
    assert report["volume"] > 0, "outward-facing normals give a positive volume"
    assert report["genus"] == holes


def test_combined_stl_is_a_closed_manifold_with_one_genus_per_hole(client, mesh, tmp_path):
    model = client.post("/api/build", json=square_plate()).json()
    path = download(client, model["downloads"]["stl"], tmp_path / "plate.stl")
    report = mesh.analyze(mesh.read_stl(path))
    assert_printable(report, holes=model["hole_count"])
    assert report["extents"] == pytest.approx([80, 48, 4], abs=1e-4)
    # float32 STL coordinates: agree with the B-rep volume to well under 0.01 %.
    assert report["volume"] == pytest.approx(model["volume_mm3"], rel=1e-4)
    assert "agrees" in mesh.unit_hints(report["extents"], expected_mm=80)[0]


def test_traced_photo_with_round_holes_exports_a_valid_mesh(client, mesh, tmp_path):
    traced = client.post(
        "/api/trace",
        files={"file": ("part.png", photo_with_round_holes(), "image/png")},
    )
    assert traced.status_code == 200, traced.text
    profile = traced.json()["profile"]
    assert len(profile["holes"]) == 2
    body = square_plate(profile=profile, width_mm=120, thickness_mm=3)
    model = client.post("/api/build", json=body).json()
    path = download(client, model["downloads"]["stl"], tmp_path / "traced.stl")
    report = mesh.analyze(mesh.read_stl(path))
    assert_printable(report, holes=2)
    assert report["extents"][0] == pytest.approx(120, abs=1e-3)
    assert report["extents"][2] == pytest.approx(3, abs=1e-4)
    assert report["volume"] == pytest.approx(model["volume_mm3"], rel=1e-4)


def test_every_split_part_is_independently_printable(client, mesh, tmp_path):
    design = {"output_mode": "split", "split_columns": 2, "split_rows": 1}
    model = client.post("/api/build", json=square_plate(design=design)).json()
    bundle = zipfile.ZipFile(io.BytesIO(client.get(model["downloads"]["parts"]).content))
    manifest = json.loads(bundle.read("manifest.json"))
    assert len(manifest["parts"]) == 2
    for part in manifest["parts"]:
        path = tmp_path / part["files"]["stl"]
        path.write_bytes(bundle.read(part["files"]["stl"]))
        report = mesh.analyze(mesh.read_stl(path))
        # The 2 x 1 cut runs between the two holes, so each piece keeps one.
        assert_printable(report, holes=1)
        assert report["volume"] == pytest.approx(part["volume_mm3"], rel=1e-4)
        assert report["bbox_min"] == pytest.approx([0, 0, 0], abs=1e-5)


@pytest.mark.parametrize("split", [False, True])
def test_native_openscad_matches_final_scaled_simplified_profiles(client, mesh, tmp_path, split):
    openscad = shutil.which("openscad")
    if not openscad:
        pytest.skip("Native SCAD render comparison requires OpenSCAD.")
    # The top-edge bumps disappear under draft simplification. Matching volume
    # proves the SCAD uses the final profile, not the source pixels or raw scale.
    profile = square_plate()["profile"]
    profile["outer"] = [
        [0, 0], [100, 0], [100, 60], [80, 60], [79, 60.05], [78, 60], [0, 60]
    ]
    response = client.post(
        "/api/build",
        json=square_plate(
            profile=profile,
            design={
                "scale_percent": 150, "thickness_percent": 175,
                "detail_mode": "draft", "nozzle_mm": 0.4,
                "output_mode": "split" if split else "single",
                "split_columns": 2, "split_rows": 1,
            },
        ),
    )
    assert response.status_code == 200, response.text
    model = response.json()
    source = download(client, model["downloads"]["scad"], tmp_path / "model.scad")

    def render(index):
        output = tmp_path / f"render-{index}.stl"
        result = subprocess.run(
            [openscad, "-o", str(output), "-D", f"part_index={index}", str(source)],
            capture_output=True, text=True, timeout=60, check=False,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        assert result.returncode == 0, result.stderr
        return mesh.analyze(mesh.read_stl(output))

    report = render(0)
    assert_printable(report, holes=2)
    assert report["extents"] == pytest.approx(list(model["dimensions"].values()), abs=1e-4)
    assert report["volume"] == pytest.approx(model["volume_mm3"], rel=1e-4)
    if split:
        assert len(model["parts"]) == 2
        for index, part in enumerate(model["parts"], start=1):
            piece = render(index)
            assert_printable(piece, holes=1)
            assert piece["volume"] == pytest.approx(part["volume_mm3"], rel=1e-4)
            assert piece["extents"] == pytest.approx(list(part["dimensions"].values()), abs=1e-4)


def test_documented_meshcheck_command_accepts_a_workbench_export(client, tmp_path):
    model = client.post("/api/build", json=square_plate()).json()
    path = download(client, model["downloads"]["stl"], tmp_path / "model.stl")
    command = [sys.executable, "-m", "cadkit", "meshcheck", str(path), "--expect-mm", "80"]
    result = subprocess.run(
        [*command, "--json"], cwd=LIBRARY, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert (report["status"], report["genus"]) == ("pass", 2)
    text = subprocess.run(command, cwd=LIBRARY, capture_output=True, text=True, check=True)
    assert "through-holes (genus): 2" in text.stdout
