"""QIDI Studio itself imports the 3MF files this app hands to it.

These tests run the installed QIDI Studio's own command line (``--info``), which loads
a model the way the program does and reports its size and whether it is manifold. They
skip when QIDI Studio is not installed: set PICAD_QIDI_STUDIO to its executable or
AppImage, or keep the AppImage in ~/Applications.
"""

import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

import pytest

from backend import slicers
from backend.relief import ReliefSettings, build_relief
from backend.worker import build

ROOT = Path(__file__).resolve().parents[1]
QIDI = slicers.executable_for("qidi")

pytestmark = pytest.mark.skipif(QIDI is None, reason="QIDI Studio is not installed")


def qidi_info(path: Path, workdir: Path):
    """Return QIDI Studio's report for a model file: one {field: value} per object."""
    environment = dict(os.environ, TMPDIR=str(workdir))
    if QIDI.endswith(".AppImage"):
        # Unpack instead of mounting, so the check also works where FUSE is unavailable.
        environment["APPIMAGE_EXTRACT_AND_RUN"] = "1"
    completed = subprocess.run(
        [QIDI, "--info", str(path)],
        cwd=workdir,
        env=environment,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout[-2000:] + completed.stderr[-2000:]
    sections = completed.stdout.split(f"[{path.name}]")[1:]
    assert sections, completed.stdout[-2000:]
    return [
        dict(re.findall(r"^(\w+) = +(.+)$", section, flags=re.MULTILINE)) for section in sections
    ]


def size_of(info):
    return [float(info[key]) for key in ("size_x", "size_y", "size_z")]


def expected_size(dimensions):
    return [dimensions["width"], dimensions["height"], dimensions["thickness"]]


@pytest.fixture(scope="module", params=["single", "split"])
def plate(request, tmp_path_factory):
    """A measured flat part, built and packaged exactly as the workbench does."""
    directory = tmp_path_factory.mktemp(f"qidi-{request.param}")
    body = {
        "name": "QIDI handoff",
        "profile": {
            "outer": [[0, 0], [100, 0], [100, 60], [0, 60]],
            "holes": [[[20, 20], [30, 20], [30, 30], [20, 30]]],
        },
        "width_mm": 80,
        "thickness_mm": 4,
        "design": {"output_mode": request.param, "split_columns": 2, "split_rows": 1},
    }
    (directory / "input.json").write_text(json.dumps(body), encoding="utf-8")
    return directory, build(directory)


def test_qidi_studio_imports_the_handoff_geometry_at_its_built_size(plate, tmp_path):
    """Every built piece arrives as its own manifold object at its built size and volume.

    QIDI Studio reports each object about its own centre, so this checks sizes and
    volumes; the assembled positions are covered by the 3MF writer's own tests.
    """
    directory, result = plate
    with zipfile.ZipFile(directory / "qidi-handoff.zip") as bundle:
        bundle.extractall(tmp_path / "bundle")
    pieces = result["parts"]
    objects = qidi_info(tmp_path / "bundle" / "model.3mf", tmp_path)
    assert len(objects) == len(pieces)
    for info, piece in zip(objects, pieces, strict=True):
        assert info["manifold"] == "yes"
        assert size_of(info) == pytest.approx(expected_size(piece["dimensions"]), abs=0.01)
    total = sum(float(info["volume"]) for info in objects)
    assert total == pytest.approx(result["volume_mm3"], rel=1e-5)
    if len(pieces) == 1:
        # The STL fallback holds the same single solid.
        (stl,) = qidi_info(tmp_path / "bundle" / "model.stl", tmp_path)
        assert size_of(stl) == pytest.approx(expected_size(result["dimensions"]), abs=0.01)
    else:
        # Each piece's own file, for arranging the pieces separately.
        for piece in pieces:
            (info,) = qidi_info(tmp_path / "bundle" / piece["files"]["3mf"], tmp_path)
            assert size_of(info) == pytest.approx(expected_size(piece["dimensions"]), abs=0.01)


def test_qidi_studio_imports_a_relief_with_every_triangle(tmp_path):
    job = tmp_path / "relief"
    job.mkdir()
    settings = ReliefSettings(name="Moon relief", mode="relief", width_mm=100)
    result = build_relief(
        (ROOT / "frontend" / "public" / "relief-sample.png").read_bytes(), settings, job
    )
    (info,) = qidi_info(job / "model.3mf", tmp_path)
    assert int(info["number_of_facets"]) == result["stats"]["mesh"]["triangles"]
    assert float(info["size_x"]) == pytest.approx(100, abs=0.001)
    assert float(info["size_z"]) == pytest.approx(settings.max_mm, abs=0.001)
    assert info["manifold"] == "yes"
