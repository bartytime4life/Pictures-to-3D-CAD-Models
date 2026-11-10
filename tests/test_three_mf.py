"""Read 3MF independently and check final mesh topology, scale and placement."""

import json
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from backend.three_mf import ThreeMFError, indexed_mesh, write_3mf
from backend.worker import build

CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


@pytest.fixture(scope="module")
def mesh_checker():
    library = Path(__file__).resolve().parents[1] / "reference-library"
    sys.path.insert(0, str(library))
    try:
        from cadkit import stl
    finally:
        sys.path.remove(str(library))
    return stl


@pytest.fixture(scope="module", params=["single", "split"])
def model(request, tmp_path_factory):
    directory = tmp_path_factory.mktemp(f"three-mf-{request.param}")
    body = {
        "name": "Tést & <plate>",
        "profile": {
            "outer": [[0, 0], [100, 0], [100, 60], [80, 60], [79, 60.05], [78, 60], [0, 60]],
            "holes": [
                [[20, 20], [30, 20], [30, 30], [20, 30]],
                [[70, 20], [80, 20], [80, 30], [70, 30]],
            ],
        },
        "width_mm": 80,
        "thickness_mm": 4,
        "design": {
            "scale_percent": 150,
            "thickness_percent": 175,
            "detail_mode": "draft",
            "output_mode": request.param,
            "split_columns": 2,
            "split_rows": 1,
        },
    }
    (directory / "input.json").write_text(json.dumps(body), encoding="utf-8")
    return directory, build(directory)


def read_3mf(path):
    with zipfile.ZipFile(path) as package:
        assert set(package.namelist()) == {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
        types = ET.fromstring(package.read("[Content_Types].xml"))
        model_type = next(item for item in types if item.attrib.get("Extension") == "model")
        assert (
            model_type.attrib["ContentType"]
            == "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"
        )
        relationships = ET.fromstring(package.read("_rels/.rels"))
        assert len(relationships) == 1
        assert relationships[0].attrib == {
            "Id": "rel0",
            "Type": "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel",
            "Target": "/3D/3dmodel.model",
        }
        root = ET.fromstring(package.read("3D/3dmodel.model"))
    assert root.tag == f"{CORE}model" and root.attrib["unit"] == "millimeter"
    objects = root.findall(f"{CORE}resources/{CORE}object")
    assert [int(item.attrib["id"]) for item in objects] == list(range(1, len(objects) + 1))
    assert [item.attrib["objectid"] for item in root.findall(f"{CORE}build/{CORE}item")] == [
        item.attrib["id"] for item in objects
    ]
    assert not root.findall(".//*[@transform]")
    extracted = []
    for item in objects:
        assert item.attrib["type"] == "model"
        vertices = [
            tuple(float(vertex.attrib[axis]) for axis in "xyz")
            for vertex in item.findall(f"{CORE}mesh/{CORE}vertices/{CORE}vertex")
        ]
        assert len(vertices) == len(set(vertices)), "face-local copies must be welded"
        triangles = [
            tuple(int(triangle.attrib[f"v{index}"]) for index in (1, 2, 3))
            for triangle in item.findall(f"{CORE}mesh/{CORE}triangles/{CORE}triangle")
        ]
        assert all(0 <= index < len(vertices) for triangle in triangles for index in triangle)
        edges = Counter(
            (triangle[index], triangle[(index + 1) % 3])
            for triangle in triangles
            for index in range(3)
        )
        assert all(count == 1 and edges[end, start] == 1 for (start, end), count in edges.items())
        extracted.append([[vertices[index] for index in triangle] for triangle in triangles])
    return root, extracted


def test_3mf_uses_final_scaled_simplified_geometry_and_keeps_parts_separate(model, mesh_checker):
    directory, result = model
    root, meshes = read_3mf(directory / "model.3mf")
    assert len(meshes) == len(result["parts"])
    assert root.find(f"{CORE}metadata[@name='Title']").text == "Tést & <plate>"
    reports = [mesh_checker.analyze(mesh) for mesh in meshes]
    for report, part in zip(reports, result["parts"]):
        assert report["watertight"] and report["manifold"] and report["orientation_consistent"]
        assert report["degenerate_triangles"] == 0 and report["components"] == 1
        assert report["genus"] == (2 if len(meshes) == 1 else 1)
        assert report["volume"] == pytest.approx(part["volume_mm3"], rel=1e-8)
        # CAD kernel bounds can include a 1e-7 mm topological tolerance.
        assert report["bbox_min"] == pytest.approx(part["assembly_offset_mm"], abs=1e-6)
        assert report["extents"] == pytest.approx(list(part["dimensions"].values()), abs=1e-6)
    combined = mesh_checker.analyze([triangle for mesh in meshes for triangle in mesh])
    assert combined["extents"] == pytest.approx([120, 72, 7], abs=1e-8)
    assert sum(report["volume"] for report in reports) == pytest.approx(result["volume_mm3"])
    assert result["downloads"]["3mf"].endswith("/3mf")


def test_individual_split_3mf_matches_normalized_part_and_parts_zip(model, mesh_checker):
    directory, result = model
    if len(result["parts"]) == 1:
        assert not (directory / "parts.zip").exists()
        return
    with zipfile.ZipFile(directory / "parts.zip") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for part in manifest["parts"]:
            filename = part["files"]["3mf"]
            assert archive.read(filename) == (directory / filename).read_bytes()
            _, meshes = read_3mf(directory / filename)
            assert len(meshes) == 1
            report = mesh_checker.analyze(meshes[0])
            assert report["bbox_min"] == pytest.approx([0, 0, 0], abs=1e-6)
            assert report["extents"] == pytest.approx(list(part["dimensions"].values()), abs=1e-6)
            assert report["volume"] == pytest.approx(part["volume_mm3"])


def tetrahedron():
    return {
        "vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1],
        "triangles": [0, 2, 1, 0, 1, 3, 0, 3, 2, 1, 2, 3],
    }


@pytest.mark.parametrize("failure", ["open", "reversed", "index", "nonfinite", "degenerate"])
def test_writer_rejects_invalid_generated_meshes(failure):
    mesh = tetrahedron()
    if failure == "open":
        mesh["triangles"] = mesh["triangles"][:-3]
    elif failure == "reversed":
        mesh["triangles"] = [
            value
            for index in range(0, 12, 3)
            for value in mesh["triangles"][index : index + 3][::-1]
        ]
    elif failure == "index":
        mesh["triangles"][0] = 100
    elif failure == "nonfinite":
        mesh["vertices"][0] = float("nan")
    elif failure == "degenerate":
        mesh["triangles"][0] = mesh["triangles"][1]
    with pytest.raises(ThreeMFError):
        indexed_mesh(mesh)


def test_writer_welds_face_local_copies_without_moving_coordinates(tmp_path):
    source = tetrahedron()
    points = [tuple(source["vertices"][index : index + 3]) for index in range(0, 12, 3)]
    duplicated = {
        "vertices": [coordinate for index in source["triangles"] for coordinate in points[index]],
        "triangles": list(range(12)),
    }
    vertices, triangles = indexed_mesh(duplicated)
    assert set(vertices) == set(points) and len(vertices) == 4 and len(triangles) == 4
    path = tmp_path / "tetra.3mf"
    write_3mf(path, [{"name": "One part", "mesh": duplicated}])
    _, meshes = read_3mf(path)
    assert len(meshes) == 1 and len(meshes[0]) == 4
    with pytest.raises(ThreeMFError):
        write_3mf(tmp_path / "empty.3mf", [])
