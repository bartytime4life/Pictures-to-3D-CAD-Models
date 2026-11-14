"""Evidence for relief and lithophane geometry, colour science, optics and handoffs."""

import hashlib
import io
import json
import math
import shutil
import subprocess
import zipfile
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import app as api
from backend import blender as blender_bridge
from backend import relief, sphere
from backend.relief import ReliefError, ReliefSettings

ROOT = Path(__file__).resolve().parent.parent
BLENDER = shutil.which("blender") or (
    "/snap/bin/blender" if Path("/snap/bin/blender").exists() else None
)


def png(array, mode=None):
    buffer = io.BytesIO()
    Image.fromarray(array, mode).save(buffer, "PNG") if mode else Image.fromarray(array).save(
        buffer, "PNG"
    )
    return buffer.getvalue()


def gradient_photo(width=200, height=100):
    """Left-to-right sRGB ramp from black to white with a mid-gray disc."""
    ramp = np.tile(np.linspace(0, 255, width).round().astype(np.uint8), (height, 1))
    rgb = np.dstack([ramp] * 3)
    cv2.circle(rgb, (width // 2, height // 2), height // 5, (128, 128, 128), -1)
    return png(rgb)


def build(tmp_path, data=None, **settings):
    job = tmp_path / "job"
    job.mkdir(exist_ok=True)
    return relief.build_relief(data or gradient_photo(), ReliefSettings(**settings), job), job


# ------------------------------------------------------------------ colour science


def test_srgb_transfer_matches_published_values():
    # IEC 61966-2-1: the linear segment ends at 0.04045; mid-gray 0.5 decodes to 0.21404.
    assert relief.srgb_to_linear(0.04045) == pytest.approx(0.04045 / 12.92)
    assert relief.srgb_to_linear(0.5) == pytest.approx(0.214041, abs=1e-6)
    assert relief.srgb_to_linear(1.0) == pytest.approx(1.0)
    samples = np.linspace(0, 1, 1001)
    assert np.allclose(relief.linear_to_srgb(relief.srgb_to_linear(samples)), samples, atol=1e-12)


def test_luminance_weights_and_cie_lightness():
    assert relief.relative_luminance([1, 1, 1]) == pytest.approx(1)
    assert relief.relative_luminance([0, 1, 0]) == pytest.approx(0.7152)
    # CIE L*: white is 100, 18% gray is about 49.5, and Y = 0.008856 joins the two branches.
    assert relief.lightness(1.0) == pytest.approx(100)
    assert relief.lightness(0.18) == pytest.approx(49.496, abs=1e-3)
    joint = (6 / 29) ** 3
    assert relief.lightness(joint * (1 - 1e-12)) == pytest.approx(relief.lightness(joint), abs=1e-6)


# ------------------------------------------------------------------------ optics


def test_beer_lambert_inversion_round_trips_and_clips():
    hvl, t_min, t_max = 0.5, 0.8, 3.0
    assert relief.attenuation(hvl) == pytest.approx(math.log(2) / 0.5)
    y = np.linspace(0.05, 1, 200)
    thickness, clipped = relief.lithophane_thickness(y, t_min, t_max, hvl)
    assert not clipped.any()
    assert np.allclose(relief.transmission(thickness, t_min, hvl), y, rtol=1e-12)
    # One half-value thickness halves the light.
    assert relief.transmission(t_min + hvl, t_min, hvl) == pytest.approx(0.5)
    dark, flagged = relief.lithophane_thickness(np.array([0.001]), t_min, t_max, hvl)
    assert flagged.all() and dark[0] == pytest.approx(t_max)


def test_half_value_fit_recovers_synthetic_wedge():
    thickness = relief.wedge_thicknesses(0.8, 3.0)
    mu = math.log(2) / 0.62
    linear = 0.9 * np.exp(-mu * (np.array(thickness) - 0.8))
    fit = relief.fit_half_value(thickness, linear.tolist(), "linear")
    assert fit["half_value_mm"] == pytest.approx(0.62, rel=1e-9)
    assert fit["r_squared"] == pytest.approx(1.0)
    camera = np.round(relief.linear_to_srgb(linear) * 255)
    fit8 = relief.fit_half_value(thickness, camera.tolist(), "srgb8")
    assert fit8["half_value_mm"] == pytest.approx(0.62, rel=0.03)
    assert fit8["half_value_se_mm"] < 0.02


def test_half_value_fit_excludes_saturated_readings_and_rejects_nonsense():
    fit = relief.fit_half_value([1, 2, 3, 4], [255, 200, 120, 70], "srgb8")
    assert fit["excluded_steps"] == [0] and fit["used_points"] == 3
    with pytest.raises(ReliefError, match="did not fall"):
        relief.fit_half_value([1, 2, 3], [50, 100, 150])
    with pytest.raises(ReliefError, match="neither black nor saturated"):
        relief.fit_half_value([1, 2, 3], [255, 255, 3])


# ------------------------------------------------------------------------ meshing


@pytest.mark.parametrize("shape", [(2, 2), (3, 7), (40, 25)])
def test_heightfield_mesh_is_closed_genus_zero_with_two_equal_volumes(shape):
    rng = np.random.default_rng(7)
    z = 0.5 + rng.random(shape) * 3
    xs = np.cumsum(rng.random(shape[1]) + 0.1)
    ys = np.cumsum(rng.random(shape[0]) + 0.1)[::-1]
    vertices, triangles = relief.heightfield_mesh(z, xs, ys)
    report = relief.mesh_report(vertices, triangles)
    assert report["closed_and_oriented"]
    assert report["euler_characteristic"] == 2 and report["genus"] == 0
    assert report["min_triangle_area_mm2"] > 0
    assert report["volume_mm3"] > 0
    assert report["volume_mm3"] == pytest.approx(relief.heightfield_volume(z, xs, ys), rel=1e-12)


def test_flat_heightfield_volume_is_exact_box():
    z = np.full((5, 9), 2.5)
    vertices, triangles = relief.heightfield_mesh(z, np.linspace(0, 40, 9), np.linspace(20, 0, 5))
    assert relief.mesh_report(vertices, triangles)["volume_mm3"] == pytest.approx(40 * 20 * 2.5)


def test_diagonal_follows_the_ridge():
    # A ridge along the a-d diagonal: splitting there keeps the crest, not a saddle.
    z = np.array([[3.0, 1.0], [1.0, 3.0]])
    _, triangles = relief.heightfield_mesh(z, [0, 1], [1, 0])
    top = {tuple(sorted(t)) for t in triangles[:2].tolist()}
    assert top == {(0, 2, 3), (0, 1, 3)}  # both triangles contain vertices 0 and 3


def test_wedge_has_eight_measured_steps(tmp_path):
    (vertices, triangles), _ = relief.wedge_mesh(0.8, 3.0)
    report = relief.mesh_report(vertices, triangles)
    assert report["closed_and_oriented"] and report["genus"] == 0
    steps = relief.wedge_thicknesses(0.8, 3.0)
    assert steps[0] == pytest.approx(0.8) and steps[-1] == pytest.approx(3.0) and len(steps) == 8
    # Each riser's ramp trades half its width between neighbouring steps, so the volume
    # is exactly that of ideal vertical steps.
    expected = sum(t * relief.WEDGE_STEP_WIDTH for t in steps) * relief.WEDGE_HEIGHT
    assert report["volume_mm3"] == pytest.approx(expected, rel=1e-12)
    assert report["bounds_mm"]["max"][:2] == pytest.approx([80, 25])


# -------------------------------------------------------------------- full builds


def read_stl(path):
    data = path.read_bytes()
    count = int(np.frombuffer(data[80:84], "<u4")[0])
    assert len(data) == 84 + 50 * count
    records = np.frombuffer(data[84:], dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    return records["v"]


def test_relief_build_dimensions_tone_mapping_and_exports(tmp_path):
    result, job = build(
        tmp_path,
        width_mm=80,
        min_mm=1,
        max_mm=5,
        nozzle_filter=False,
        denoise="off",
        auto_levels=False,
    )
    dims = result["dimensions"]
    assert dims["width"] == pytest.approx(80) and dims["height"] == pytest.approx(40)
    assert dims["min_thickness"] >= 1 - 1e-9 and dims["thickness"] <= 5 + 1e-9
    heights = cv2.imread(str(job / "heightmap.png"), cv2.IMREAD_UNCHANGED)
    assert heights.dtype == np.uint16
    rows, cols = heights.shape
    assert (cols, rows) == (result["stats"]["grid"]["columns"], result["stats"]["grid"]["rows"])
    row = heights[2].astype(float)
    assert np.all(np.diff(row[: cols // 4]) >= 0)  # Brighter photo = taller relief.
    # Relief tone is CIE L*: mid-gray sRGB 128 maps near L* 53.6% of the span.
    centre = heights[rows // 2, cols // 2] / 65535
    assert centre == pytest.approx(
        relief.lightness(relief.srgb_to_linear(128 / 255)) / 100, abs=0.01
    )
    triangles = read_stl(job / "model.stl")
    assert len(triangles) == result["stats"]["mesh"]["triangles"]
    assert result["volume_mm3"] == pytest.approx(result["stats"]["volume_cross_check_mm3"])
    with zipfile.ZipFile(job / "model.3mf") as archive:
        model = archive.read("3D/3dmodel.model").decode()
    assert 'unit="millimeter"' in model
    assert model.count("<vertex ") == result["stats"]["mesh"]["vertices"]
    assert model.count("<triangle ") == result["stats"]["mesh"]["triangles"]
    assert result["mesh"]["vertices"] and result["preview_image"].startswith("data:image/png")
    assert set(result["downloads"]) == {"stl", "3mf", "heightmap", "blender", "project"}


def test_auto_levels_reach_the_chosen_range(tmp_path):
    # A low-contrast photo (sRGB 70..180) still spans the full thinnest-thickest range.
    ramp = np.tile(np.linspace(70, 180, 240).round().astype(np.uint8), (80, 1))
    photo = png(np.dstack([ramp] * 3))
    stretched, _ = build(tmp_path, photo, min_mm=1, max_mm=5, nozzle_filter=False, denoise="off")
    assert stretched["dimensions"]["min_thickness"] == pytest.approx(1, abs=1e-3)
    assert stretched["dimensions"]["thickness"] == pytest.approx(5, abs=1e-3)
    raw, _ = build(
        tmp_path, photo, min_mm=1, max_mm=5, nozzle_filter=False, denoise="off", auto_levels=False
    )
    assert raw["dimensions"]["min_thickness"] > 1.5 and raw["dimensions"]["thickness"] < 4.5


def test_invert_and_gamma_change_the_mapping(tmp_path):
    base, job = build(tmp_path, nozzle_filter=False, denoise="off")
    plain = cv2.imread(str(job / "heightmap.png"), cv2.IMREAD_UNCHANGED).astype(float)
    build(tmp_path, nozzle_filter=False, denoise="off", invert=True)
    inverted = cv2.imread(str(job / "heightmap.png"), cv2.IMREAD_UNCHANGED).astype(float)
    assert np.allclose(plain + inverted, 65535, atol=1.5)
    build(tmp_path, nozzle_filter=False, denoise="off", gamma=2.0)
    squared = cv2.imread(str(job / "heightmap.png"), cv2.IMREAD_UNCHANGED).astype(float)
    assert np.allclose(squared / 65535, (plain / 65535) ** 2, atol=2e-4)
    assert base["stats"]["nozzle_filter"]["removed_rms_mm"] == 0


def test_nozzle_filter_reports_removed_detail(tmp_path):
    rng = np.random.default_rng(3)
    noise = (rng.random((120, 120)) * 255).astype(np.uint8)
    result, _ = build(tmp_path, png(np.dstack([noise] * 3)), width_mm=30, denoise="off")
    removed = result["stats"]["nozzle_filter"]
    assert removed["enabled"] and removed["removed_rms_mm"] > 0.05
    assert removed["sigma_mm"] == pytest.approx(0.4 / (2 * math.sqrt(2 * math.log(2))))


def test_lithophane_optics_frame_and_wedge(tmp_path):
    result, job = build(
        tmp_path,
        mode="lithophane",
        width_mm=60,
        min_mm=0.8,
        max_mm=3.2,
        frame_mm=4,
        half_value_mm=0.6,
    )
    optics = result["stats"]["optics"]
    assert optics["dynamic_range_stops"] == pytest.approx(2.4 / 0.6)
    assert optics["contrast_ratio"] == pytest.approx(2**4)
    assert 0 <= optics["clipped_fraction"] < 1
    dims = result["dimensions"]
    assert dims["width"] == pytest.approx(68, abs=0.25)
    assert dims["thickness"] == pytest.approx(3.2)
    heights = cv2.imread(str(job / "heightmap.png"), cv2.IMREAD_UNCHANGED)
    assert np.all(heights[:, :10] == 65535)  # The frame is at full thickness.
    # The dark left edge of the photo is thick and the bright right edge thin.
    inner = heights[30:-30, 30:-30]
    assert inner[:, :5].mean() > inner[:, -5:].mean()
    assert "wedge" in result["downloads"] and (job / "calibration-wedge.stl").stat().st_size
    assert result["stats"]["wedge_mm"][0] == pytest.approx(0.8)


def test_16_bit_depth_map_keeps_its_levels(tmp_path):
    depth = np.tile(np.linspace(0, 65535, 300).round().astype(np.uint16), (60, 1))
    buffer = io.BytesIO()
    Image.fromarray(depth).save(buffer, "PNG")
    result, job = build(
        tmp_path,
        buffer.getvalue(),
        source="depth",
        width_mm=30,
        nozzle_filter=False,
        denoise="off",
        auto_levels=False,
    )
    stored = cv2.imread(str(job / "heightmap.png"), cv2.IMREAD_UNCHANGED)[10] / 65535
    # Grid point i samples the ramp at pixel-centre coordinate i / (n - 1) * w - 0.5.
    u = np.linspace(0, 300, len(stored)) - 0.5
    expected = np.clip(u / 299, 0, 1)
    error = np.abs(stored - expected)[3:-3]
    assert error.max() < 0.25 / 255  # Finer than any 8-bit source could represent.
    assert result["stats"]["source"]["samples"] == "16-bit grayscale"


def test_large_width_widens_sampling_within_budget(tmp_path):
    result, _ = build(tmp_path, width_mm=400, nozzle_mm=0.2)
    grid = result["stats"]["grid"]
    assert grid["columns"] * grid["rows"] <= relief.MAX_SAMPLES
    assert any("widened" in w for w in result["warnings"])


def test_settings_validation():
    with pytest.raises(ValueError, match="exceed minimum"):
        ReliefSettings(min_mm=2, max_mm=2.05)
    with pytest.raises(ValueError):
        ReliefSettings(mode="sculpture")
    assert ReliefSettings(color="#ABCDEF").color == "#abcdef"


def test_blender_bundle_is_static_hashed_and_complete(tmp_path):
    result, job = build(tmp_path, mode="lithophane", name='x"); import os #')
    with zipfile.ZipFile(job / "blender-relief.zip") as archive:
        names = set(archive.namelist())
        assert names == set(blender_bridge.BUNDLE_MEMBERS)
        script = archive.read("build_relief.py")
        manifest = json.loads(archive.read("manifest.json"))
        config = json.loads(archive.read("relief.json"))
        for name, entry in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == entry["sha256"]
    # The script is byte-identical to the repository file: no project value is code.
    assert script == (ROOT / "backend" / "blender_relief.py").read_bytes()
    assert config["name"] == 'x"); import os #'
    assert config["mu_per_mm"] == pytest.approx(math.log(2) / 0.5)
    assert config["columns"] == result["stats"]["grid"]["columns"] + 0  # frame_mm is 0


# ------------------------------------------------------------------------- API


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    (tmp_path / "jobs").mkdir()
    with TestClient(api.app) as instance:
        yield instance


def post_relief(client, data=None, **settings):
    return client.post(
        "/api/relief",
        files={"file": ("photo.png", data or gradient_photo(), "image/png")},
        data={"settings": json.dumps(settings)},
    )


def test_relief_api_builds_downloads_and_discards_the_photo(client, tmp_path):
    response = post_relief(client, mode="lithophane", width_mm=40, name="Window")
    assert response.status_code == 200, response.text
    body = response.json()
    job = tmp_path / "jobs" / body["id"]
    assert not (job / "source.upload").exists() and not (job / "input.json").exists()
    for kind, url in body["downloads"].items():
        download = client.get(url)
        assert download.status_code == 200, kind
        assert download.headers["cache-control"] == "private, no-store"
    assert client.get(body["downloads"]["heightmap"]).headers["content-type"] == "image/png"


def test_relief_api_rejects_bad_settings_and_images(client):
    response = post_relief(client, max_mm=1, min_mm=2)
    assert response.status_code == 422 and "exceed minimum" in response.json()["detail"]
    assert post_relief(client, unknown=1).status_code == 422
    bad = client.post(
        "/api/relief",
        files={"file": ("x.png", b"not an image", "image/png")},
        data={"settings": "{}"},
    )
    assert bad.status_code == 422 and "decoded" in bad.json()["detail"]
    assert (
        client.post("/api/relief", files={"file": ("x.png", b"", "image/png")}).status_code == 422
    )


def test_relief_upload_shares_the_photo_size_limit():
    assert api.body_limit("/api/relief") == api.body_limit("/api/trace")


def test_calibration_api(client):
    thickness = relief.wedge_thicknesses(0.8, 3.0)
    readings = (np.exp(-1.2 * (np.array(thickness) - 0.8)) * 1000).tolist()
    response = client.post(
        "/api/relief/calibrate",
        json={"thickness_mm": thickness, "readings": readings, "scale": "linear"},
    )
    assert response.status_code == 200
    assert response.json()["mu_per_mm"] == pytest.approx(1.2)
    rising = client.post(
        "/api/relief/calibrate", json={"thickness_mm": [1, 2, 3], "readings": [10, 20, 30]}
    )
    assert rising.status_code == 422


# -------------------------------------------------------------------- launcher


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    monkeypatch.setattr(api, "JOB_ROOT", jobs)
    monkeypatch.setattr(api, "BLENDER_HANDOFF_ROOT", tmp_path / "handoffs")
    monkeypatch.setenv("PICAD_ENABLE_BLENDER_LAUNCH", "1")
    monkeypatch.setattr(blender_bridge, "executable", lambda: "/trusted/blender")
    job = jobs / ("b" * 32)
    job.mkdir()
    relief.build_relief(gradient_photo(), ReliefSettings(width_mm=20), job)
    (job / "result.json").write_text("{}")
    with TestClient(
        api.app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 45678)
    ) as client:
        yield client, job, tmp_path / "handoffs"


def test_blender_launch_uses_the_static_script_only(launcher):
    client, job, handoffs = launcher
    with mock.patch.object(blender_bridge.subprocess, "Popen") as process:
        process.return_value.pid = 4321
        response = client.post(
            f"/api/models/{job.name}/blender", headers={"Origin": "http://127.0.0.1:8000"}, json={}
        )
    assert response.status_code == 202, response.text
    (args,), options = process.call_args
    folder = handoffs / response.json()["handoff_id"]
    assert args == ["/trusted/blender", "--python", str((folder / "build_relief.py").resolve())]
    assert options["shell"] is False and options["cwd"] == folder
    assert (folder / "build_relief.py").read_bytes() == (
        ROOT / "backend" / "blender_relief.py"
    ).read_bytes()
    assert json.loads((folder / "launch.json").read_text())["pid"] == 4321


def test_blender_launch_requires_local_same_origin_and_opt_in(launcher, monkeypatch):
    client, job, _ = launcher
    with mock.patch.object(blender_bridge.subprocess, "Popen") as process:
        cross = client.post(
            f"/api/models/{job.name}/blender", headers={"Origin": "http://evil.example"}, json={}
        )
        assert cross.status_code == 403
        monkeypatch.setenv("PICAD_ENABLE_BLENDER_LAUNCH", "0")
        off = client.post(
            f"/api/models/{job.name}/blender", headers={"Origin": "http://127.0.0.1:8000"}, json={}
        )
        assert off.status_code == 409 and "off" in off.json()["detail"]
        process.assert_not_called()
    status = client.get("/api/blender").json()
    assert status["launch_available"] is False and "/trusted" not in json.dumps(status)


def test_blender_launch_rejects_unexpected_bundle_members(launcher):
    client, job, _ = launcher
    with zipfile.ZipFile(job / "blender-relief.zip", "a") as archive:
        archive.writestr("../escape.py", "print('no')")
    with mock.patch.object(blender_bridge.subprocess, "Popen") as process:
        response = client.post(
            f"/api/models/{job.name}/blender", headers={"Origin": "http://127.0.0.1:8000"}, json={}
        )
    assert response.status_code == 409 and "incomplete" in response.json()["detail"]
    process.assert_not_called()


def test_blender_executable_keeps_snap_launchers(monkeypatch, tmp_path):
    launcher_path = tmp_path / "blender"
    launcher_path.write_text("#!/bin/sh\n")
    launcher_path.chmod(0o755)
    monkeypatch.setenv("PICAD_BLENDER", str(launcher_path))
    assert blender_bridge.executable() == str(launcher_path)
    monkeypatch.setenv("PICAD_BLENDER", "blender --factory-startup")
    assert blender_bridge.executable() is None


# ------------------------------------------------------- independent Blender check


def run_blender(folder, *args):
    completed = subprocess.run(
        [BLENDER, "-b", "--factory-startup", "--python", "build_relief.py", *args],
        cwd=folder,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stdout[-2000:] + completed.stderr[-2000:]
    return completed


@pytest.mark.skipif(BLENDER is None, reason="Blender is not installed")
@pytest.mark.parametrize("mode", ["relief", "lithophane"])
def test_blender_rebuilds_the_same_solid(tmp_path, mode):
    result, job = build(tmp_path, mode=mode, width_mm=40, frame_mm=2 if mode == "lithophane" else 0)
    folder = tmp_path / "blender"
    with zipfile.ZipFile(job / "blender-relief.zip") as archive:
        archive.extractall(folder)
    run_blender(folder, "--", "--report", "report.json", "--export-stl", "out.stl")
    report = json.loads((folder / "report.json").read_text())
    mesh = result["stats"]["mesh"]
    assert report["manifold"]
    assert (report["vertices"], report["triangles"]) == (mesh["vertices"], mesh["triangles"])
    assert report["volume_mm3"] == pytest.approx(mesh["volume_mm3"], rel=1e-6)
    assert report["bounds_mm"]["max"] == pytest.approx(mesh["bounds_mm"]["max"], abs=1e-4)
    ours = np.unique(np.round(read_stl(job / "model.stl").reshape(-1, 3), 3), axis=0)
    theirs = np.unique(np.round(read_stl(folder / "out.stl").reshape(-1, 3), 3), axis=0)
    assert ours.shape == theirs.shape and np.abs(ours - theirs).max() <= 1.5e-3


@pytest.mark.skipif(BLENDER is None, reason="Blender is not installed")
def test_cycles_render_agrees_with_beer_lambert(tmp_path):
    result, job = build(tmp_path, mode="lithophane", width_mm=40, half_value_mm=0.7)
    folder = tmp_path / "blender"
    with zipfile.ZipFile(job / "blender-relief.zip") as archive:
        archive.extractall(folder)
    (folder / "lowres.py").write_text(
        "import bpy\ns = bpy.context.scene\n"
        "s.render.resolution_x, s.render.resolution_y = 200, 100\n"
        "s.cycles.samples = 32\ns.cycles.device = 'CPU'\n"
    )
    subprocess.run(
        [
            BLENDER,
            "-b",
            "--factory-startup",
            "--python",
            "build_relief.py",
            "--python",
            "lowres.py",
            "--python-expr",
            (
                "import bpy; bpy.context.scene.render.filepath='render.png'; "
                "bpy.ops.render.render(write_still=True)"
            ),
        ],
        cwd=folder,
        capture_output=True,
        timeout=600,
        check=True,
    )
    rendered = cv2.imread(str(folder / "render.png"), cv2.IMREAD_UNCHANGED)[..., :3]
    light = relief.srgb_to_linear(rendered.mean(axis=2) / 255)
    config = json.loads((folder / "relief.json").read_text())
    levels = cv2.imread(str(folder / "heightmap.png"), cv2.IMREAD_UNCHANGED) / 65535
    thickness = config["min_mm"] + levels * (config["max_mm"] - config["min_mm"])
    width, height = result["dimensions"]["width"], result["dimensions"]["height"]
    mm_per_px = 1.1 * max(width, height) / light.shape[1]
    ys, xs = np.mgrid[0 : light.shape[0], 0 : light.shape[1]]
    x = (xs + 0.5 - light.shape[1] / 2) * mm_per_px + width / 2
    y = height / 2 - (ys + 0.5 - light.shape[0] / 2) * mm_per_px
    inside = (x > 1) & (x < width - 1) & (y > 1) & (y < height - 1)
    col = np.clip(np.round(x / config["pitch_x_mm"]).astype(int), 0, config["columns"] - 1)
    row = np.clip(np.round((height - y) / config["pitch_y_mm"]).astype(int), 0, config["rows"] - 1)
    predicted = np.exp(-config["mu_per_mm"] * thickness[row, col])
    assert np.corrcoef(light[inside], predicted[inside])[0, 1] > 0.98
    assert np.median(light[inside] / predicted[inside]) == pytest.approx(1, abs=0.03)


# ------------------------------------------------------------- moon samples


def load_generator():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "generate_relief_samples", ROOT / "scripts" / "generate_relief_samples.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sample_generator_reproduces_both_committed_samples(tmp_path):
    load_generator().main(tmp_path)
    for name in ("relief-sample.png", "relief-sample-depth.png", "moon-map.png"):
        committed = cv2.imread(str(ROOT / "frontend" / "public" / name), cv2.IMREAD_UNCHANGED)
        regenerated = cv2.imread(str(tmp_path / name), cv2.IMREAD_UNCHANGED)
        assert committed.dtype == regenerated.dtype and np.array_equal(committed, regenerated), name


def test_moon_depth_sample_builds_a_true_hemisphere(tmp_path):
    generator = load_generator()
    data = (ROOT / "frontend" / "public" / "relief-sample-depth.png").read_bytes()
    width = 100.0
    radius = generator.RADIUS / generator.WIDTH * width  # 30 mm
    span = generator.DEPTH_FULL_SCALE * radius  # the studio button's setting: 33 mm
    result, job = build(
        tmp_path,
        data,
        source="depth",
        width_mm=width,
        min_mm=1.6,
        max_mm=1.6 + span,
        auto_levels=False,
        denoise="off",
    )
    assert result["stats"]["source"]["samples"] == "16-bit grayscale"
    assert result["stats"]["mesh"]["closed_and_oriented"]
    levels = cv2.imread(str(job / "heightmap.png"), cv2.IMREAD_UNCHANGED) / 65535
    height = levels * span  # above the 1.6 mm base
    grid = result["stats"]["grid"]
    rows, cols = height.shape
    y, x = np.mgrid[0:rows, 0:cols]
    cx = generator.CENTRE_X / generator.WIDTH * (cols - 1)
    cy = generator.CENTRE_Y / generator.HEIGHT * (rows - 1)
    r = np.hypot((x - cx) * grid["pitch_x_mm"], (y - cy) * grid["pitch_y_mm"])
    # Medians over thin rings ignore the craters; a sphere has z = sqrt(R^2 - r^2).
    for ring in (0.0, 10.0, 20.0, 25.0, 28.0):
        band = np.abs(r - ring) < (1.0 if ring else 1.5)
        assert np.median(height[band]) == pytest.approx(math.sqrt(radius**2 - ring**2), abs=0.6), (
            ring
        )
    assert np.median(height[r > radius + 1.5]) == pytest.approx(0, abs=1e-6)


# ------------------------------------------------------------------- spheres


def equirect(array):
    return png(np.dstack([array] * 3).astype(np.uint8))


def sphere_settings(**changes):
    return ReliefSettings(shape="sphere", **changes)


def test_sphere_frame_puts_the_opening_and_both_cuts_in_one_plane():
    settings = sphere_settings(sphere_diameter_mm=100, max_mm=3, opening_mm=40)
    frame = sphere.sphere_frame(settings)
    assert frame["r_in"] == pytest.approx(47)
    # The inner sphere meets the cut plane on a circle of the requested diameter...
    assert frame["r_in"] * math.sin(frame["theta_in"]) == pytest.approx(20)
    # ...and both cuts lie at the same height.
    assert frame["r_in"] * math.cos(frame["theta_in"]) == pytest.approx(frame["z_cut"])
    assert frame["r_out"] * math.cos(frame["theta_out"]) == pytest.approx(frame["z_cut"])


def test_sphere_settings_reject_impossible_shapes():
    with pytest.raises(ValueError, match="too small"):
        sphere_settings(sphere_diameter_mm=30, max_mm=8)
    with pytest.raises(ValueError, match="opening"):
        sphere_settings(sphere_diameter_mm=60, max_mm=3, opening_mm=50)


def test_equirect_sampling_wraps_without_a_seam():
    w, h = 720, 360
    longitude = (np.arange(w) + 0.5) / w * 2 * math.pi
    field = np.tile((np.cos(longitude) + 1) / 2, (h, 1)).astype(np.float32)
    columns = 96
    thetas = np.linspace(0, 2.5, 40)
    values = sphere.sample_equirect(field, columns, thetas)
    expected = (np.cos(np.arange(columns) * 2 * math.pi / columns) + 1) / 2
    assert np.abs(values[5:] - expected).max() < 0.01  # Including longitude 0 at the seam.
    assert np.ptp(values[0]) == 0  # The pole is one point.


def test_spherical_nozzle_filter_keeps_constants_and_wraps():
    thetas = np.linspace(0, 2.6, 50)
    flat = np.full((50, 120), 2.0)
    assert np.allclose(sphere.nozzle_filter(flat, thetas, 50, 0.17), 2.0)
    stripe = flat.copy()
    stripe[:, 0] = 3.0  # A one-column ridge on the seam spreads to both neighbours.
    smoothed = sphere.nozzle_filter(stripe, thetas, 50, 3.0)
    assert smoothed[25, 1] == pytest.approx(smoothed[25, -1], rel=1e-9)
    assert smoothed[25, 1] > 2.0


def test_constant_shell_volume_matches_the_closed_form(tmp_path):
    gray = np.full((300, 600), 128)
    result, _ = build(
        tmp_path,
        equirect(gray),
        shape="sphere",
        mode="relief",
        min_mm=2,
        max_mm=3,
        auto_levels=False,
        denoise="off",
        collar_mm=0,
    )
    frame = sphere.sphere_frame(sphere_settings(min_mm=2, max_mm=3))
    t = result["dimensions"]["min_thickness"]  # Uniform away from the one-row collar.
    r_out, r_in, depth = frame["r_in"] + t, frame["r_in"], -frame["z_cut"]
    theta_out = math.acos(frame["z_cut"] / r_out)

    def cap_and_cone(r, theta):
        return (
            2 * math.pi * r**3 / 3 * (1 - math.cos(theta))
            + math.pi / 3 * (r * math.sin(theta)) ** 2 * depth
        )

    exact = cap_and_cone(r_out, theta_out) - cap_and_cone(r_in, frame["theta_in"])
    stats = result["stats"]
    # The only collar row is at full thickness; the closed form ignores that one row.
    assert stats["sphere"]["smooth_volume_mm3"] == pytest.approx(exact, rel=5e-3)
    # Inscribed triangles approximate the smooth surfaces to second order.
    assert abs(stats["sphere"]["polyhedral_vs_smooth"]) < 5e-3


def test_sphere_build_is_closed_flat_based_and_radially_thick(tmp_path):
    rng = np.random.default_rng(5)
    picture = rng.integers(0, 255, (256, 512))
    result, job = build(
        tmp_path,
        equirect(picture),
        shape="sphere",
        mode="lithophane",
        min_mm=0.8,
        max_mm=3,
        sphere_diameter_mm=80,
        opening_mm=30,
    )
    stats = result["stats"]
    mesh = stats["mesh"]
    assert mesh["closed_and_oriented"] and mesh["euler_characteristic"] == 2
    assert mesh["volume_mm3"] == pytest.approx(stats["volume_check"]["value_mm3"], rel=1e-9)
    assert result["shape"] == "sphere" and "wedge" in result["downloads"]
    vertices = read_stl(job / "model.stl").reshape(-1, 3).astype(np.float64)
    assert vertices[:, 2].min() == pytest.approx(0, abs=1e-4)
    on_bed = vertices[np.abs(vertices[:, 2]) < 1e-4]
    radius = np.hypot(on_bed[:, 0], on_bed[:, 1])
    assert radius.min() == pytest.approx(15, abs=1e-3)  # The 30 mm opening.
    frame = sphere.sphere_frame(sphere_settings(sphere_diameter_mm=80, max_mm=3, opening_mm=30))
    assert radius.max() == pytest.approx(40 * math.sin(frame["theta_out"]), abs=1e-3)
    centre = np.array([0, 0, -frame["z_cut"]])
    distance = np.linalg.norm(vertices - centre, axis=1)
    assert distance.max() <= 40 + 1e-3
    assert stats["sphere"]["bed_contact_mm2"] > 0
    assert 0 < stats["sphere"]["overhang_fraction"] < 0.5
    assert stats["optics"]["dynamic_range_stops"] == pytest.approx(2.2 / 0.5)


def test_sphere_warns_when_the_picture_is_not_a_world_map(tmp_path):
    result, _ = build(tmp_path, gradient_photo(200, 200), shape="sphere")
    assert any("not a 2:1 world map" in warning for warning in result["warnings"])


def test_sphere_api_and_downloads(client):
    picture = np.tile(np.linspace(0, 255, 400), (200, 1))
    response = post_relief(
        client,
        equirect(picture),
        shape="sphere",
        mode="lithophane",
        sphere_diameter_mm=60,
        min_mm=0.8,
        max_mm=2.5,
        opening_mm=25,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["shape"] == "sphere"
    for url in body["downloads"].values():
        assert client.get(url).status_code == 200


@pytest.mark.skipif(BLENDER is None, reason="Blender is not installed")
def test_blender_rebuilds_the_same_sphere(tmp_path):
    rng = np.random.default_rng(9)
    picture = cv2.GaussianBlur(rng.random((200, 400)) * 255, (0, 0), 3)
    result, job = build(
        tmp_path,
        equirect(picture),
        shape="sphere",
        mode="lithophane",
        sphere_diameter_mm=60,
        min_mm=0.8,
        max_mm=2.5,
        opening_mm=25,
    )
    folder = tmp_path / "blender"
    with zipfile.ZipFile(job / "blender-relief.zip") as archive:
        archive.extractall(folder)
    run_blender(folder, "--", "--report", "report.json", "--export-stl", "out.stl")
    report = json.loads((folder / "report.json").read_text())
    mesh = result["stats"]["mesh"]
    assert report["manifold"]
    assert (report["vertices"], report["triangles"]) == (mesh["vertices"], mesh["triangles"])
    assert report["volume_mm3"] == pytest.approx(mesh["volume_mm3"], rel=1e-6)
    ours, theirs = read_stl(job / "model.stl"), read_stl(folder / "out.stl")
    assert ours.shape == theirs.shape
    # Same triangles in the same order, up to the rotation of each triangle's vertices.
    distance = np.min(
        [np.abs(ours - np.roll(theirs, k, axis=1)).max(axis=(1, 2)) for k in range(3)], axis=0
    )
    assert distance.max() < 1e-4


@pytest.mark.skipif(BLENDER is None, reason="Blender is not installed")
def test_cycles_lamp_render_matches_beer_lambert_through_a_shell(tmp_path):
    # A uniform wall: a view ray at distance rho from the centre crosses
    # L = sqrt(R_out^2 - rho^2) - sqrt(R_in^2 - rho^2) of plastic in the front wall, so the
    # glowing interior should appear with brightness exp(-mu L): darker towards the edge.
    gray = np.full((200, 400), 140)
    result, job = build(
        tmp_path,
        equirect(gray),
        shape="sphere",
        mode="lithophane",
        sphere_diameter_mm=60,
        min_mm=0.8,
        max_mm=3,
        opening_mm=20,
        collar_mm=0,
        denoise="off",
        auto_levels=False,
        half_value_mm=0.7,
    )
    folder = tmp_path / "blender"
    with zipfile.ZipFile(job / "blender-relief.zip") as archive:
        archive.extractall(folder)
    size = 240
    (folder / "lowres.py").write_text(
        f"import bpy\ns = bpy.context.scene\ns.render.resolution_x = s.render.resolution_y = {size}\n"
        "s.cycles.samples = 16\ns.cycles.device = 'CPU'\n"
    )
    subprocess.run(
        [
            BLENDER,
            "-b",
            "--factory-startup",
            "--python",
            "build_relief.py",
            "--python",
            "lowres.py",
            "--python-expr",
            (
                "import bpy; bpy.context.scene.render.filepath='render.png'; "
                "bpy.ops.render.render(write_still=True)"
            ),
        ],
        cwd=folder,
        capture_output=True,
        timeout=900,
        check=True,
    )
    light = relief.srgb_to_linear(
        cv2.imread(str(folder / "render.png"), cv2.IMREAD_UNCHANGED)[..., :3].mean(axis=2) / 255
    )
    config = json.loads((folder / "relief.json").read_text())
    r_in = config["r_in_mm"]
    thickness = result["dimensions"]["min_thickness"]  # Uniform; collar is one row only.
    r_out = r_in + thickness
    mu = config["mu_per_mm"]
    mm_per_px = 1.25 * 60 / size
    centre = size / 2 - 0.5
    for rho in (0.0, 0.4 * r_in, 0.7 * r_in):
        column = round(centre + rho / mm_per_px)
        patch = light[round(centre) - 1 : round(centre) + 2, column - 1 : column + 2].mean()
        path = math.sqrt(r_out**2 - rho**2) - math.sqrt(r_in**2 - rho**2)
        assert patch == pytest.approx(math.exp(-mu * path), rel=0.04), rho
