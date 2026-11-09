"""Functional evidence for measured geometry, image handling, and API limits."""

import asyncio
import base64
import io
import json
import os
import struct
import subprocess
import sys
import threading
import time
from collections import Counter

import cadquery as cq
import ezdxf
import httpx2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend import app as api
from backend import tracing


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(api, "JOB_ROOT", tmp_path_factory.mktemp("jobs"))
        with TestClient(api.app) as instance:
            yield instance


def image_bytes(*, blank=False, inverse=False, clipped=False, exif=False):
    image = Image.new("RGB", (500, 360), "black" if inverse else "white")
    if not blank:
        draw = ImageDraw.Draw(image)
        foreground, background = ("white", "black") if inverse else ("black", "white")
        draw.rectangle((0 if clipped else 50, 60, 450, 300), fill=foreground)
        draw.ellipse((120, 120, 170, 170), fill=background)
        draw.ellipse((330, 120, 380, 170), fill=background)
    buffer = io.BytesIO()
    if exif:
        metadata = Image.Exif()
        metadata[274] = 6
        metadata[270] = "private metadata should not survive"
        image.save(buffer, "JPEG", quality=95, exif=metadata)
    else:
        image.save(buffer, "PNG")
    return buffer.getvalue()


def trace(client, data=None, **settings):
    return client.post(
        "/api/trace",
        files={"file": ("part.png", data or image_bytes(), "image/png")},
        data=settings,
    )


def valid_request(**changes):
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
        "name": "Measured test plate",
        "revision": "test-revision-1",
        **changes,
    }


@pytest.fixture(scope="module")
def model(client):
    response = client.post("/api/build", json=valid_request())
    assert response.status_code == 200, response.text
    return response.json()


def test_health_and_unknown_api(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/not-an-endpoint").status_code == 404


def test_trace_preserves_holes_and_coordinates(client):
    response = trace(client)
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["profile"]["holes"]) == 2
    # The drawn part covers pixel columns 50-450 and rows 60-300: 401 x 241 pixels.
    assert result["bounds"] == {"x": 50, "y": 60, "width": 401, "height": 241}
    assert result["image"]["width"] == 500
    assert result["image"]["height"] == 360
    image = Image.open(io.BytesIO(base64.b64decode(result["image"]["data_url"].split(",")[1])))
    assert image.size == (500, 360)


def test_trace_light_foreground(client):
    response = trace(client, image_bytes(inverse=True), inverted="true")
    assert response.status_code == 200, response.text
    assert len(response.json()["profile"]["holes"]) == 2


def test_exif_orientation_and_metadata_removal(client):
    response = trace(client, image_bytes(exif=True))
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["image"]["width"], result["image"]["height"]) == (360, 500)
    image = Image.open(io.BytesIO(base64.b64decode(result["image"]["data_url"].split(",")[1])))
    assert not image.getexif()
    assert len(result["profile"]["holes"]) == 2


def plate(mode="RGB", part="black", background="white"):
    """A 401 x 241 pixel part with a 51 x 51 pixel square hole at columns and rows 120-170."""
    image = Image.new(mode, (500, 360), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((50, 60, 450, 300), fill=part)
    draw.rectangle((120, 120, 170, 170), fill=background)
    return image


def encoded(image, file_format="PNG", **options):
    buffer = io.BytesIO()
    image.save(buffer, file_format, **options)
    return buffer.getvalue()


def extent(ring):
    xs, ys = zip(*ring)
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def test_trace_follows_pixel_edges_rather_than_boundary_pixel_centres(client):
    response = trace(client, encoded(plate()))
    assert response.status_code == 200, response.text
    result = response.json()
    # Pixel i spans [i, i + 1], so columns 50-450 span 50 to 451.
    assert result["bounds"] == {"x": 50, "y": 60, "width": 401, "height": 241}
    (hole,) = result["profile"]["holes"]
    assert extent(hole) == (120, 120, 51, 51)


def test_pixel_edge_offset_never_makes_a_ring_less_valid():
    square = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert extent(tracing.to_pixel_edges(square, 0.5)) == (-0.5, -0.5, 11, 11)
    shrunk = sorted(map(tuple, tracing.to_pixel_edges(square, -0.5)))
    assert shrunk == [(0.5, 0.5), (0.5, 9.5), (9.5, 0.5), (9.5, 9.5)]
    # A corner pointing along an axis is bevelled close to its half-pixel offset.
    diamond = [[0, 5], [5, 0], [10, 5], [5, 10]]
    assert extent(tracing.to_pixel_edges(diamond, 0.5))[2] == pytest.approx(11, abs=0.11)
    bowtie = [[0, 0], [10, 10], [10, 0], [0, 10]]
    assert tracing.to_pixel_edges(bowtie, 0.5) == bowtie  # Left for Profile validation.
    assert tracing.to_pixel_edges([[0, 0], [1, 0], [1, 1], [0, 1]], -0.5) is None
    # A narrow waist would split the hole in two; keep the traced ring instead.
    dumbbell = [[0, 0], [4, 0], [4, 1.6], [6, 1.6], [6, 0], [10, 0], [10, 4], [6, 4], [6, 2.4]]
    dumbbell += [[4, 2.4], [4, 4], [0, 4]]
    assert tracing.to_pixel_edges(dumbbell, -0.5) == dumbbell


@pytest.mark.parametrize("case", ["webp-damaged-header", "png-damaged-header", "jpeg-retyped-tag"])
def test_malformed_exif_is_traced_instead_of_failing(client, case):
    damaged_header = b"XX\x00*\x00\x00\x00\x08\x00\x00"  # Invalid TIFF byte-order mark.
    metadata = Image.Exif()
    metadata[274] = 6  # Rotated orientation, still readable below.
    metadata[282] = 72.0  # XResolution, a RATIONAL value.
    retyped = bytearray(metadata.tobytes())
    entry = retyped.find(struct.pack(">HH", 282, 5))
    assert entry != -1
    retyped[entry + 2 : entry + 4] = struct.pack(">H", 2)  # Declare the rational as ASCII.
    data, size, unreadable = {
        "webp-damaged-header": (encoded(plate(), "WEBP", exif=damaged_header), (500, 360), True),
        "png-damaged-header": (encoded(plate(), "PNG", exif=damaged_header), (500, 360), True),
        "jpeg-retyped-tag": (
            encoded(plate(), "JPEG", exif=b"Exif\x00\x00" + bytes(retyped)),
            (360, 500),
            False,
        ),
    }[case]
    response = trace(client, data)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["image"]["width"], result["image"]["height"]) == size
    assert len(result["profile"]["holes"]) == 1
    notice = any("orientation metadata could not be read" in w for w in result["warnings"])
    assert notice is unreadable


def test_camera_mpo_jpeg_uses_its_primary_image(client):
    primary = plate()
    data = encoded(primary, "MPO", save_all=True, append_images=[primary.resize((160, 120))])
    assert Image.open(io.BytesIO(data)).format == "MPO"
    response = trace(client, data)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["image"]["width"], result["image"]["height"]) == (500, 360)
    assert result["bounds"]["width"] == pytest.approx(401, abs=1)
    assert len(result["profile"]["holes"]) == 1


def test_animated_png_is_still_rejected(client):
    blank = Image.new("RGB", (500, 360), "white")
    response = trace(client, encoded(plate(), save_all=True, append_images=[blank]))
    assert response.status_code == 422
    assert "still image" in response.json()["detail"]


@pytest.mark.parametrize("transparent_background", [False, True])
def test_sixteen_bit_grayscale_png_is_scaled_rather_than_clipped(client, transparent_background):
    samples = np.full((360, 500), 60000, dtype=np.uint16)
    samples[60:301, 50:451] = 20000
    samples[120:171, 120:171] = 60000
    image = Image.fromarray(samples)
    assert image.mode == "I;16"
    options = {"transparency": 60000} if transparent_background else {}
    response = trace(client, encoded(image, **options))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["bounds"] == {"x": 50, "y": 60, "width": 401, "height": 241}
    assert len(result["profile"]["holes"]) == 1


def part_with_island_in_hole(island):
    image = Image.new("RGB", (500, 360), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((50, 60, 450, 300), fill="black")
    draw.ellipse((120, 120, 220, 220), fill="white")
    draw.rectangle((170, 170, 169 + island, 169 + island), fill="black")
    return encoded(image)


def test_speck_inside_a_hole_is_ignored_like_a_tiny_hole(client):
    response = trace(client, part_with_island_in_hole(2))
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["profile"]["holes"]) == 1
    assert any("Ignored 1 tiny region(s)" in warning for warning in result["warnings"])


def test_substantial_island_inside_a_hole_is_rejected(client):
    response = trace(client, part_with_island_in_hole(20))
    assert response.status_code == 422
    assert "A hole contains another region" in response.json()["detail"]


@pytest.mark.parametrize(
    "data", [b"not an image", image_bytes(blank=True), image_bytes(clipped=True)]
)
def test_unusable_images_have_recoverable_errors(client, data):
    response = trace(client, data)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_upload_size_limit(client):
    response = trace(client, b"x" * (10 * 1024 * 1024 + 1))
    assert response.status_code == 413


def test_pixel_limit(client):
    buffer = io.BytesIO()
    Image.new("L", (4001, 4000), 255).save(buffer, "PNG")
    response = trace(client, buffer.getvalue())
    assert response.status_code == 422
    assert "16 megapixels" in response.json()["detail"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("width_mm", 0),
        ("width_mm", -1),
        ("width_mm", 2001),
        ("thickness_mm", 0),
        ("thickness_mm", 501),
        ("name", " "),
    ],
)
def test_invalid_dimensions_and_names(client, field, value):
    response = client.post("/api/build", json=valid_request(**{field: value}))
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("bad_value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_inputs(client, bad_value):
    payload = json.dumps(valid_request()).replace('"width_mm": 80', f'"width_mm": {bad_value}')
    response = client.post(
        "/api/build", content=payload, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "profile",
    [
        {"outer": [[0, 0], [20, 20], [0, 20], [20, 0]], "holes": []},
        {
            "outer": [[0, 0], [10, 0], [10, 10], [0, 10]],
            "holes": [[[20, 20], [30, 20], [30, 30], [20, 30]]],
        },
        {"outer": [[0, 0], [10, 0], [20, 0]], "holes": []},
    ],
)
def test_invalid_topology(client, profile):
    response = client.post("/api/build", json=valid_request(profile=profile))
    assert response.status_code == 422


def test_each_hole_is_bounded_before_its_points_are_parsed(client):
    profile = valid_request()["profile"]
    profile["holes"] = [[[20, 20], [30, 20], [30, 30], *[[20, 30]] * 1998]]
    response = client.post("/api/build", json=valid_request(profile=profile))
    assert response.status_code == 422
    assert response.json()["detail"].startswith(
        "profile.holes.0: List should have at most 2000 items"
    )


def test_real_solid_dimensions_volume_and_revision(model):
    assert model["revision"] == "test-revision-1"
    assert model["hole_count"] == 2
    assert model["dimensions"] == pytest.approx({"width": 80, "height": 48, "thickness": 4})
    # 100x60 profile with two 10x10 holes, scaled by 0.8 in XY and extruded 4mm.
    assert model["volume_mm3"] == pytest.approx((100 * 60 - 2 * 10 * 10) * 0.8**2 * 4)
    assert len(model["mesh"]["vertices"]) > 0
    assert len(model["mesh"]["triangles"]) > 0


def test_step_export_reimports_as_valid_solid(client, model, tmp_path):
    response = client.get(model["downloads"]["step"])
    assert response.status_code == 200
    path = tmp_path / "roundtrip.step"
    path.write_bytes(response.content)
    shape = cq.importers.importStep(str(path)).val()
    assert shape.isValid()
    assert len(shape.Solids()) == 1
    assert shape.Volume() == pytest.approx(14848)
    bounds = shape.BoundingBox()
    assert (bounds.xlen, bounds.ylen, bounds.zlen) == pytest.approx((80, 48, 4))


def test_stl_export_closed_mesh_with_correct_bounds(client, model):
    response = client.get(model["downloads"]["stl"])
    assert response.status_code == 200
    payload = response.content
    count = struct.unpack_from("<I", payload, 80)[0]
    assert count > 0
    assert len(payload) == 84 + count * 50
    edges = Counter()
    vertices = []
    for i in range(count):
        values = struct.unpack_from("<12fH", payload, 84 + i * 50)
        triangle = [tuple(round(v, 6) for v in values[start : start + 3]) for start in (3, 6, 9)]
        vertices.extend(triangle)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((triangle[a], triangle[b])))] += 1
    assert set(edges.values()) == {2}, "Every mesh edge must have exactly two incident triangles."
    axes = list(zip(*vertices))
    assert tuple(max(axis) - min(axis) for axis in axes) == pytest.approx((80, 48, 4))


def test_dxf_export_units_and_closed_holes(client, model):
    response = client.get(model["downloads"]["dxf"])
    drawing = ezdxf.read(io.StringIO(response.text))
    assert drawing.units == ezdxf.units.MM
    rings = list(drawing.modelspace().query("LWPOLYLINE"))
    assert len(rings) == 3
    assert all(ring.closed for ring in rings)
    assert sum(ring.dxf.layer == "HOLES" for ring in rings) == 2


def test_recipe_restores_original_inputs(client, model):
    response = client.get(model["downloads"]["project"])
    recipe = response.json()
    assert recipe["format"] == "pictures-to-cad"
    assert recipe["version"] == 1
    assert recipe["profile"] == valid_request()["profile"]
    assert recipe["width_mm"] == 80
    assert recipe["thickness_mm"] == 4
    assert "image" not in recipe


MODEL_NOT_FOUND = "Model not found. Rebuild it to create new exports."


@pytest.mark.parametrize(
    "path,detail",
    [
        # Encoded dot segments and backslashes survive URL normalization and reach the route.
        ("/api/download/%2E%2E/step", MODEL_NOT_FOUND),
        ("/api/download/%2e%2e/project", MODEL_NOT_FOUND),
        ("/api/download/..%5C..%5Cetc%5Cpasswd/step", MODEL_NOT_FOUND),
        ("/api/download/not-a-job/step", MODEL_NOT_FOUND),
        ("/api/download/" + "0" * 32 + "/step", MODEL_NOT_FOUND),
        # An encoded slash decodes to extra path segments, which no download route matches.
        ("/api/download/..%2F..%2Fetc%2Fpasswd/step", "API route not found."),
    ],
)
def test_downloads_do_not_expose_arbitrary_files(client, path, detail):
    response = client.get(path)
    assert response.request.url.raw_path.decode() == path, "The client must not normalize it."
    assert response.status_code == 404
    assert response.json()["detail"] == detail


@pytest.mark.parametrize("path", ["/%00", "/index.html%00.js", "/assets/%00/app.js", "/a" * 2500])
def test_unusable_frontend_paths_are_not_found(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found."


def test_expiry_removes_only_stale_directories_with_this_apps_job_files(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path)
    stale = time.time() - api.TTL_SECONDS - 1

    def job_directory(name, filename, *, expired=True):
        directory = tmp_path / name
        directory.mkdir()
        (directory / filename).write_text("{}")
        if expired:
            os.utime(directory, (stale, stale))
        return directory

    jobs = [
        job_directory(digit * 32, marker)
        for digit, marker in zip("123", ("input.json", "result.json", "error.json"))
    ]
    # Another program's similarly named directory in a shared PICTURES_CAD_JOB_DIR.
    foreign = job_directory("4" * 32, "notes.txt")
    current = job_directory("5" * 32, "result.json", expired=False)
    api.cleanup_jobs()
    assert not any(directory.exists() for directory in jobs)
    assert (foreign / "notes.txt").is_file()
    assert (current / "result.json").is_file()


def test_failed_cleanup_pass_does_not_stop_later_expiry(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path)
    monkeypatch.setattr(api, "CLEANUP_INTERVAL", 0.01)
    # This lifespan replaces the module client's locks; put them back afterwards.
    names = ("cad_lock", "trace_lock", "assistant_lock")
    saved = {name: getattr(api.app.state, name) for name in names if hasattr(api.app.state, name)}
    calls = []

    def flaky_cleanup():
        calls.append(len(calls))
        if len(calls) == 2:  # The first periodic pass; the first call is at startup.
            raise PermissionError("Synthetic cleanup failure")

    monkeypatch.setattr(api, "cleanup_jobs", flaky_cleanup)

    async def scenario():
        async with api.lifespan(api.app):
            for _ in range(500):
                if len(calls) >= 4:
                    break
                await asyncio.sleep(0.01)

    try:
        asyncio.run(scenario())  # Shutdown must not re-raise the earlier failure either.
    finally:
        for name, value in saved.items():
            setattr(api.app.state, name, value)
    assert len(calls) >= 4
    assert "Temporary model cleanup failed" in caplog.text


def test_non_ascii_project_name_builds_without_a_utf8_locale(tmp_path):
    """The API and CAD worker must not rely on the locale's default text encoding."""
    script = (
        "import json, locale, sys\n"
        "from fastapi.testclient import TestClient\n"
        "from backend import app as api\n"
        "with TestClient(api.app) as client:\n"
        "    response = client.post('/api/build', json=json.loads(sys.argv[1]))\n"
        "    recipe = response.status_code == 200 and client.get(\n"
        "        response.json()['downloads']['project']).json()\n"
        "print(json.dumps({'encoding': locale.getpreferredencoding(False),\n"
        "    'status': response.status_code, 'name': recipe and recipe['name']}))\n"
    )
    environment = {
        **os.environ,
        "LC_ALL": "C",
        "LANG": "C",
        "PYTHONUTF8": "0",
        "PYTHONCOERCECLOCALE": "0",
        "PICTURES_CAD_JOB_DIR": str(tmp_path),
    }
    # json.dumps escapes the name, so the command line itself stays ASCII.
    body = json.dumps(valid_request(name="Halterung für Rohr"))
    completed = subprocess.run(
        [sys.executable, "-c", script, body],
        check=False,  # Report the child's stderr below instead.
        cwd=api.ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    if "utf" in result["encoding"].lower():
        pytest.skip("This platform's C locale already uses UTF-8.")
    assert result == {"encoding": result["encoding"], "status": 200, "name": "Halterung für Rohr"}


def test_expiry_and_deletion(client, tmp_path):
    job_id = "a" * 32
    directory = api.JOB_ROOT / job_id
    directory.mkdir()
    (directory / "result.json").write_text("{}")
    (directory / "model.step").write_text("expired")
    stale = time.time() - api.TTL_SECONDS - 1
    os.utime(directory, (stale, stale))
    assert client.get(f"/api/download/{job_id}/step").status_code == 410
    assert not directory.exists()
    directory.mkdir()
    (directory / "result.json").write_text("{}")
    assert client.delete(f"/api/models/{job_id}").status_code == 204
    assert not directory.exists()


def test_capacity_is_explicit_and_preserves_existing_exports(client, model, monkeypatch):
    monkeypatch.setattr(api, "MAX_JOBS", 0)
    response = client.post("/api/build", json=valid_request())
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    assert client.get(model["downloads"]["step"]).status_code == 200


def test_worker_timeout_removes_partial_outputs(client, monkeypatch):
    monkeypatch.setattr(api, "BUILD_TIMEOUT", 0.001)
    before = set(api.JOB_ROOT.iterdir())
    response = client.post("/api/build", json=valid_request())
    assert response.status_code == 504
    assert set(api.JOB_ROOT.iterdir()) == before


def test_trace_concurrency_remains_bounded_after_cancellation(client, monkeypatch):
    started, release = threading.Event(), threading.Event()
    calls = []

    def gated_trace(*args):
        calls.append(args)
        started.set()
        if not release.wait(timeout=5):
            raise TimeoutError("Test did not release the trace worker.")
        return {"finished": True}

    monkeypatch.setattr(api, "trace_image", gated_trace)

    async def scenario():
        lock = asyncio.Lock()
        monkeypatch.setattr(api.app.state, "trace_lock", lock)
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=api.app), base_url="http://test"
        ) as http:
            first = asyncio.create_task(
                http.post("/api/trace", files={"file": ("part.png", image_bytes(), "image/png")})
            )
            try:
                assert await asyncio.to_thread(started.wait, 3)
                second = await http.post(
                    "/api/trace", files={"file": ("part.png", image_bytes(), "image/png")}
                )
                assert second.status_code == 429
                assert second.headers["retry-after"] == "3"
                assert len(calls) == 1
                first.cancel()
                await asyncio.sleep(0)
                assert lock.locked(), "Cancellation must not release a still-running native worker."
                first.cancel()  # Repeated cancellation must not create another slot either.
                await asyncio.sleep(0)
                assert lock.locked()
                third = await http.post(
                    "/api/trace", files={"file": ("part.png", image_bytes(), "image/png")}
                )
                assert third.status_code == 429
                assert len(calls) == 1
                release.set()
                with pytest.raises(asyncio.CancelledError):
                    await first
                assert not lock.locked()
                recovered = await http.post(
                    "/api/trace", files={"file": ("part.png", image_bytes(), "image/png")}
                )
                assert recovered.status_code == 200
                assert recovered.json() == {"finished": True}
                assert len(calls) == 2
            finally:
                release.set()
                if not first.done():
                    first.cancel()
                    try:
                        await first
                    except asyncio.CancelledError:
                        pass

    asyncio.run(scenario())


def test_clear_models_removes_completed_jobs_and_refuses_during_build(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path)
    for job_id in ("b" * 32, "c" * 32):
        directory = tmp_path / job_id
        directory.mkdir()
        (directory / "result.json").write_text("{}")
        (directory / "model.step").write_text("completed export")
    incomplete = tmp_path / ("d" * 32)
    incomplete.mkdir()
    (incomplete / "input.json").write_text("{}")

    async def scenario():
        lock = asyncio.Lock()
        monkeypatch.setattr(api.app.state, "cad_lock", lock)
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=api.app), base_url="http://test"
        ) as http:
            await lock.acquire()
            try:
                response = await http.delete("/api/models")
                assert response.status_code == 409
                assert len(list(tmp_path.iterdir())) == 3
            finally:
                lock.release()
            response = await http.delete("/api/models")
            assert response.status_code == 200
            assert response.json() == {"deleted": 2}
            assert list(tmp_path.iterdir()) == [incomplete]
            assert (await http.delete("/api/models")).json() == {"deleted": 0}

    asyncio.run(scenario())
