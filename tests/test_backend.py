"""Functional evidence for measured geometry, image handling, and API limits."""

import asyncio
import base64
import io
import json
import os
import struct
import threading
import time
from collections import Counter

import cadquery as cq
import ezdxf
import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from backend import app as api


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
    assert result["bounds"] == {"x": 50, "y": 60, "width": 400, "height": 240}
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


@pytest.mark.parametrize(
    "path",
    [
        "/api/download/../../etc/passwd/step",
        "/api/download/not-a-job/step",
        "/api/download/" + "0" * 32 + "/step",
    ],
)
def test_downloads_do_not_expose_arbitrary_files(client, path):
    assert client.get(path).status_code == 404


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
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://test"
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
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app), base_url="http://test"
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
