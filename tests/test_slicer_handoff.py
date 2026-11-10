"""Portable bundles preserve built geometry and clearly bound planning metadata."""

import hashlib
import json
import zipfile

import pytest

from backend.worker import build


@pytest.fixture(scope="module", params=["single", "split"])
def handoff_model(request, tmp_path_factory):
    directory = tmp_path_factory.mktemp(f"handoff-{request.param}")
    body = {
        "name": "Measured handoff",
        "profile": {
            "outer": [[0, 0], [100, 0], [100, 60], [0, 60]],
            "holes": [[[20, 20], [30, 20], [30, 30], [20, 30]]],
        },
        "width_mm": 80,
        "thickness_mm": 4,
        "design": {
            "scale_percent": 150,
            "thickness_percent": 125,
            "material": "petg",
            "color": "#FF6600",
            "nozzle_mm": 0.6,
            "output_mode": request.param,
            "split_columns": 2,
            "split_rows": 1,
        },
    }
    (directory / "input.json").write_text(json.dumps(body), encoding="utf-8")
    return directory, build(directory)


@pytest.mark.parametrize(
    "slicer_id,name,version",
    [("bambu", "Bambu Studio", "2.9.1"), ("prusa", "PrusaSlicer", "2.9.7")],
)
def test_bundle_contains_hash_verified_geometry_recipe_and_targeted_instructions(
    handoff_model, slicer_id, name, version
):
    directory, result = handoff_model
    with zipfile.ZipFile(directory / f"{slicer_id}-handoff.zip") as bundle:
        files = set(bundle.namelist())
        expected = {"model.3mf", "model.stl", "project.json", "manifest.json", "README.md"}
        if len(result["parts"]) > 1:
            expected.update(
                part["files"][kind] for part in result["parts"] for kind in ("3mf", "stl")
            )
        assert files == expected
        assert not any(
            filename.endswith((".gcode", ".ini", ".config", ".step")) for filename in files
        )
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["format"] == "pictures-to-cad-slicer-handoff" and manifest["version"] == 1
        assert manifest["units"] == "mm" and manifest["name"] == "Measured handoff"
        assert manifest["slicer"]["id"] == slicer_id
        assert manifest["slicer"]["name"] == name
        assert manifest["slicer"]["target_version"] == version
        assert manifest["design"] == result["design"]
        assert manifest["design"]["color"] == "#ff6600"
        assert manifest["design"]["material"] == "petg"
        assert manifest["design"]["nozzle_mm"] == 0.6
        assert manifest["dimensions"] == result["dimensions"]
        assert manifest["volume_mm3"] == result["volume_mm3"]
        assert manifest["geometry_placement"] == "assembled"
        assert manifest["native_slicer_profile"] is False
        assert manifest["slicing_verified"] is False and manifest["printing_verified"] is False
        assert set(manifest["files"]) == files - {"manifest.json"}
        for filename, check in manifest["files"].items():
            data = bundle.read(filename)
            assert check == {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            if filename != "README.md":
                assert data == (directory / filename).read_bytes()
        recipe = json.loads(bundle.read("project.json"))
        assert recipe["width_mm"] == 80 and recipe["thickness_mm"] == 4
        assert recipe["design"]["scale_percent"] == 150
        assert "photo" not in recipe and "image" not in recipe
        notes = bundle.read("README.md").decode("utf-8")
        assert name in notes and version in notes
        assert "geometry only" in notes and "not a native slicer project" in notes
        assert "not installed presets" in notes and "has not sliced" in notes
        assert "choose" in notes.lower() and "layer preview" in notes
        for actual, recorded in zip(result["parts"], manifest["parts"]):
            assert "mesh" not in recorded
            for key in ("id", "dimensions", "volume_mm3", "assembly_offset_mm", "bed_fit"):
                assert recorded[key] == actual[key]
            if "files" in recorded:
                assert set(recorded["files"]) == {"3mf", "stl"}
                assert all(filename in files for filename in recorded["files"].values())
                assert "Arrange and verify every piece independently" in notes
    assert result["downloads"][slicer_id].endswith(f"/{slicer_id}")
