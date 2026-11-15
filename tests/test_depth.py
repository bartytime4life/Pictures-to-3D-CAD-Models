"""Evidence for optional AI depth: preprocessing, scoring, model checks and relief builds.

Most tests replace the network with a known function so they run without the 99 MB
model. Tests marked ``needs_model`` run the real model when it is installed
(./scripts/depth-model.sh install) and are skipped otherwise.
"""

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import app as api
from backend import depth, relief
from backend.relief import ReliefError, ReliefSettings

ROOT = Path(__file__).resolve().parent.parent
needs_model = pytest.mark.skipif(
    not depth.status()["available"], reason="AI depth model not installed"
)


def png(array):
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, "PNG")
    return buffer.getvalue()


def column_runner(x):
    """Stand-in network: disparity rises left to right, so the right edge is nearest."""
    _, _, h, w = x.shape
    return np.tile(np.linspace(1.0, 5.0, w, dtype=np.float32), (h, 1))


# --------------------------------------------------------------- preprocessing


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((518, 518), (518, 518)),  # Already the target.
        ((900, 640), (728, 518)),  # Shrink: short side to 518; 900 x 0.809 = 728.4.
        ((4000, 3000), (686, 518)),  # 4000 x 0.1727 = 690.7 -> nearest multiple of 14.
        ((300, 200), (518, 350)),  # Enlarge: long side to 518; 200 x 1.727 = 345.3.
        ((10000, 500), (1554, 84)),  # Our elongation bound: long side 3 x 518.
    ],
)
def test_input_size_follows_the_dpt_processor(size, expected):
    assert depth.input_size(*size) == expected
    assert all(side % depth.PATCH == 0 for side in expected)


def test_preprocess_normalizes_with_imagenet_statistics():
    mean_rgb = np.round(depth.MEAN * 255).astype(np.uint8)
    x = depth.preprocess(np.tile(mean_rgb, (60, 90, 1)))
    assert x.shape == (1, 3, 350, 518) and x.dtype == np.float32
    # A picture of the ImageNet mean colour normalizes to (nearly) zero in every channel;
    # the residue is the 8-bit rounding of the mean, divided by the channel's std.
    residue = (mean_rgb / 255 - depth.MEAN) / depth.STD
    assert np.allclose(x[0].mean(axis=(1, 2)), residue, atol=1e-5)
    white = depth.preprocess(np.full((14, 14, 3), 255, np.uint8))
    assert np.allclose(white[0, :, 0, 0], (1 - depth.MEAN) / depth.STD, atol=1e-5)


def test_normalize_is_min_max_with_white_nearest():
    field = depth.normalize(np.array([[2.0, 4.0], [6.0, 10.0]]))
    assert np.allclose(field, [[0, 0.25], [0.5, 1]])
    assert not depth.normalize(np.full((3, 3), 7.0)).any()
    with pytest.raises(depth.DepthError):
        depth.normalize(np.array([[np.nan, 1.0]]))


def test_estimate_depth_returns_the_picture_resolution():
    image = Image.fromarray(np.zeros((90, 130, 3), np.uint8))
    field, info = depth.estimate_depth(image, runner=column_runner)
    assert field.shape == (90, 130)
    assert field.min() == 0 and field.max() == 1
    assert field[:, -1].mean() > field[:, 0].mean()  # Larger disparity = nearer = whiter.
    assert info["input_px"] == list(depth.input_size(130, 90))
    assert info["license"] == "Apache-2.0"


def test_estimate_depth_refuses_depth_maps_and_bad_outputs():
    with pytest.raises(depth.DepthError, match="already a 16-bit depth map"):
        depth.estimate_depth(Image.new("F", (20, 20)), runner=column_runner)
    with pytest.raises(depth.DepthError, match="unexpected"):
        depth.estimate_depth(Image.new("RGB", (20, 20)), runner=lambda x: np.zeros(5))


# ------------------------------------------------------------------- scoring


def test_score_is_invariant_to_scale_and_shift():
    rng = np.random.default_rng(3)
    truth = rng.random((40, 40))
    s = depth.score(3.0 * truth - 2.0, truth)
    assert s["spearman"] == pytest.approx(1) and s["pearson"] == pytest.approx(1)
    assert s["aligned_rms_fraction"] == pytest.approx(0, abs=1e-12)
    assert s["scale"] == pytest.approx(1 / 3) and s["shift"] == pytest.approx(2 / 3)


def test_score_rank_correlation_ignores_monotonic_distortion():
    truth = np.linspace(0, 1, 200)
    s = depth.score(truth**5, truth)
    assert s["spearman"] == pytest.approx(1)
    assert s["pearson"] < 0.9 and s["aligned_rms_fraction"] > 0.05
    assert depth.score(-truth, truth)["spearman"] == pytest.approx(-1)


def test_score_uses_average_ranks_for_ties_and_honours_the_mask():
    # Spearman with ties equals Pearson on average ranks: ranks of [1,1,2] are [0.5,0.5,2].
    s = depth.score(np.array([1.0, 1.0, 2.0]), np.array([1.0, 2.0, 3.0]))
    assert s["spearman"] == pytest.approx(np.corrcoef([0.5, 0.5, 2], [0, 1, 2])[0, 1])
    truth = np.arange(10.0)
    estimate = truth.copy()
    estimate[5:] = -estimate[5:]
    mask = np.arange(10) < 5
    assert depth.score(estimate, truth, mask)["spearman"] == pytest.approx(1)
    flat = depth.score(np.ones(10), truth)
    assert flat["spearman"] == 0 and flat["aligned_rms_fraction"] > 0
    with pytest.raises(ValueError):
        depth.score(truth, np.ones(10))


# ------------------------------------------------------------- model checks


def test_status_reports_missing_wrong_and_verified_files(tmp_path, monkeypatch):
    missing = depth.status(tmp_path / "absent.onnx")
    assert not missing["available"] and "depth-model.sh install" in missing["reason"]
    small = tmp_path / "small.onnx"
    small.write_bytes(b"not the model")
    assert "wrong size" in depth.status(small)["reason"]
    monkeypatch.setattr(depth, "MODEL_BYTES", small.stat().st_size)
    assert "SHA-256" in depth.status(small)["reason"]
    monkeypatch.setattr(depth, "MODEL_SHA256", hashlib.sha256(small.read_bytes()).hexdigest())
    assert depth.status(small)["available"]


def test_model_path_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PICAD_DEPTH_MODEL", str(tmp_path / "m.onnx"))
    assert depth.model_path() == tmp_path / "m.onnx"
    monkeypatch.delenv("PICAD_DEPTH_MODEL")
    assert depth.model_path() == depth.DEFAULT_PATH


def test_runner_refuses_an_unverified_model(tmp_path):
    with pytest.raises(depth.DepthError, match="not installed"):
        depth.OnnxRunner(tmp_path / "absent.onnx")


def test_install_script_pins_the_same_model_as_the_backend():
    script = (ROOT / "scripts/depth-model.sh").read_text(encoding="utf-8")
    assert f"PICAD_DEPTH_SHA256={depth.MODEL_SHA256}" in script
    assert f"PICAD_DEPTH_REVISION={depth.MODEL_REVISION}" in script
    assert depth.DEFAULT_PATH.relative_to(ROOT).as_posix() in script
    assert ".local/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    status = subprocess.run(
        ["bash", str(ROOT / "scripts/depth-model.sh"), "status"],
        check=False,
        env={"PATH": "/usr/bin:/bin", "PICAD_DEPTH_MODEL": "/nonexistent/model.onnx"},
        capture_output=True,
        text=True,
    )
    assert status.returncode == 1 and "Not installed" in status.stdout


# -------------------------------------------------------------- relief builds


def test_ai_depth_is_limited_to_flat_reliefs():
    with pytest.raises(ValueError, match="flat reliefs only"):
        ReliefSettings(source="ai", mode="lithophane")
    with pytest.raises(ValueError, match="flat reliefs only"):
        ReliefSettings(source="ai", shape="sphere")
    assert ReliefSettings(source="ai").source == "ai"


@pytest.fixture
def fake_model(monkeypatch):
    monkeypatch.setattr(
        relief, "estimate_depth", lambda image: depth.estimate_depth(image, runner=column_runner)
    )


def test_relief_from_ai_depth_follows_the_estimate(tmp_path, fake_model):
    # A uniform gray photo has no brightness to follow; only the estimate gives it shape.
    data = png(np.full((80, 160, 3), 128, np.uint8))
    settings = ReliefSettings(source="ai", width_mm=60, min_mm=1, max_mm=5, nozzle_filter=False)
    result = relief.build_relief(data, settings, tmp_path)
    mesh = result["stats"]["mesh"]
    assert mesh["closed_and_oriented"] and mesh["genus"] == 0
    assert result["stats"]["depth_estimate"]["model"] == depth.MODEL_NAME
    assert "depth estimated by" in result["stats"]["source"]["samples"]
    assert any("not measured distances" in w for w in result["warnings"])
    heights = cv2.imread(str(tmp_path / "heightmap.png"), cv2.IMREAD_UNCHANGED)
    assert heights[:, -1].mean() > heights[:, 0].mean() + 60000  # Nearest edge thickest.
    estimate = cv2.imread(str(tmp_path / "depth-estimate.png"), cv2.IMREAD_UNCHANGED)
    assert estimate.dtype == np.uint16 and estimate.shape == (80, 160)
    assert estimate[:, 0].max() == 0 and estimate[:, -1].min() == 65535
    assert "depth" in result["downloads"]
    recipe = json.loads((tmp_path / "project.json").read_text(encoding="utf-8"))
    assert "Depth Anything V2 Small" in recipe["provenance"]


def test_photo_relief_has_no_depth_download(tmp_path):
    data = png(np.full((40, 80, 3), 90, np.uint8))
    result = relief.build_relief(data, ReliefSettings(width_mm=40), tmp_path)
    assert "depth" not in result["downloads"] and result["stats"]["depth_estimate"] is None
    assert not (tmp_path / "depth-estimate.png").exists()


def test_missing_model_is_a_clear_relief_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PICAD_DEPTH_MODEL", str(tmp_path / "absent.onnx"))
    data = png(np.full((40, 80, 3), 90, np.uint8))
    with pytest.raises(ReliefError, match="depth-model.sh install"):
        relief.build_relief(data, ReliefSettings(source="ai", width_mm=40), tmp_path)


# ----------------------------------------------------------------------- API


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    (tmp_path / "jobs").mkdir()
    with TestClient(api.app) as instance:
        yield instance


def test_depth_status_api(client, tmp_path, monkeypatch):
    monkeypatch.setenv("PICAD_DEPTH_MODEL", str(tmp_path / "absent.onnx"))
    response = client.get("/api/relief/depth")
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["available"] is False and body["license"] == "Apache-2.0"
    assert str(tmp_path) not in json.dumps(body)  # No local paths reach the browser.


def test_relief_api_reports_a_missing_model(client, tmp_path, monkeypatch):
    # The worker is a subprocess; it inherits the environment, not monkeypatched code.
    monkeypatch.setenv("PICAD_DEPTH_MODEL", str(tmp_path / "absent.onnx"))
    response = client.post(
        "/api/relief",
        files={"file": ("p.png", png(np.full((40, 80, 3), 90, np.uint8)), "image/png")},
        data={"settings": json.dumps({"source": "ai", "width_mm": 40})},
    )
    assert response.status_code == 422, response.text
    assert "depth-model.sh install" in response.json()["detail"]


# ------------------------------------------------------- the installed model


def test_benchmark_script_runs_with_a_stand_in_model():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import depth_benchmark
    finally:
        sys.path.pop(0)
    report = depth_benchmark.run(runner=column_runner)
    assert set(report["results"]) == {"brightness (Photo mode)", "AI depth"}
    assert set(report["coverage"]) == {"picture", "disc", "lit disc"}
    assert 0.3 < report["coverage"]["lit disc"] < report["coverage"]["disc"] < 0.5


@needs_model
def test_installed_model_recovers_the_moon_dome():
    """Recorded in docs/relief.md: the dome's ordering is recovered where it is lit."""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import depth_benchmark
    finally:
        sys.path.pop(0)
    report = depth_benchmark.run()
    ai = report["results"]["AI depth"]["lit disc"]
    brightness = report["results"]["brightness (Photo mode)"]["lit disc"]
    assert ai["spearman"] > 0.9 and ai["aligned_rms_fraction"] < 0.12
    assert brightness["spearman"] < 0.2  # Lighting, not shape, drives brightness.


@needs_model
def test_installed_model_builds_through_the_api(client):
    data = (ROOT / "frontend/public/relief-sample.png").read_bytes()
    response = client.post(
        "/api/relief",
        files={"file": ("moon.png", data, "image/png")},
        data={"settings": json.dumps({"source": "ai", "width_mm": 60, "max_mm": 6})},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stats"]["mesh"]["closed_and_oriented"]
    assert client.get(body["downloads"]["depth"]).headers["content-type"] == "image/png"
