"""Evidence for the photo library's vision layer: its numerical steps, the model registry
and the separate model process.

No test here needs PyTorch or the DINOv3 weights. The process protocol is exercised with
the stand-in (colour statistics in place of the network), so these tests establish that
the *integration* behaves, not that the model sees well. Model quality is measured by
scripts/vision_benchmark.py; one test at the end runs the real model when it is installed.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from backend import vision, vision_math
from tests import photos

ROOT = Path(__file__).resolve().parent.parent
needs_model = pytest.mark.skipif(
    not (vision.python_path().is_file() and vision.installed()),
    reason="DINOv3 vision model not installed (./scripts/vision-model.sh)",
)


@pytest.fixture
def standin(monkeypatch, tmp_path):
    monkeypatch.setenv("PICAD_VISION_STANDIN", "1")
    yield tmp_path
    vision.engine.close()
    vision.engine.forget_failure()


@pytest.fixture
def no_model(monkeypatch, tmp_path):
    monkeypatch.delenv("PICAD_VISION_STANDIN", raising=False)
    monkeypatch.delenv("PICAD_VISION_MODEL", raising=False)
    monkeypatch.setenv("PICAD_VISION_WEIGHTS", str(tmp_path / "weights"))
    monkeypatch.setenv("PICAD_VISION_PYTHON", str(tmp_path / "env" / "bin" / "python"))
    yield tmp_path
    vision.engine.close()
    vision.engine.forget_failure()


# ------------------------------------------------------------------ numerical steps


def test_unit_scales_rows_and_leaves_zero_alone():
    out = vision_math.unit(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert np.allclose(out, [[0.6, 0.8], [0.0, 0.0]])


def test_otsu_threshold_separates_two_clusters():
    rng = np.random.default_rng(0)
    values = np.r_[rng.normal(1.0, 0.1, 700), rng.normal(5.0, 0.2, 80)]
    assert 1.5 < vision_math.otsu_threshold(values) < 4.5
    assert vision_math.otsu_threshold(np.full(10, 2.0)) == 2.0  # No spread: nothing above it.


def test_largest_region_is_four_connected():
    grid = np.zeros((6, 6), bool)
    grid[0:2, 0:2] = True  # 4 cells
    grid[3:6, 3:6] = True  # 9 cells, touching the first only diagonally if extended
    grid[2, 2] = True  # Diagonal bridge: must not join them.
    region = vision_math.largest_region(grid)
    assert region.sum() == 9 and region[3:6, 3:6].all()
    assert not vision_math.largest_region(np.zeros((4, 4), bool)).any()


def planted(grid=20, channels=32, seed=0, drift=0.6, noise=0.05):
    """Patch features of a surface that drifts with position, with a block that differs.

    Returns (features 1 x g*g x C, true region). The surface is a + b x + c y in feature
    space, the situation the subject finder models; the block points elsewhere.
    """
    rng = np.random.default_rng(seed)
    base, along_x, along_y, thing = rng.normal(size=(4, channels))
    yy, xx = np.mgrid[0:grid, 0:grid] / (grid - 1) - 0.5
    features = base + drift * xx[..., None] * along_x + drift * yy[..., None] * along_y
    truth = np.zeros((grid, grid), bool)
    truth[6:13, 4:11] = True
    features[truth] = thing + 0.3 * base
    features += rng.normal(0, noise, features.shape)
    return features.reshape(1, grid * grid, channels).astype(np.float32), truth


def test_subject_region_recovers_a_planted_block_on_a_drifting_surface():
    features, truth = planted()
    region = vision_math.subject_regions(features)[0]
    overlap = (region & truth).sum() / (region | truth).sum()
    assert overlap > 0.9
    assert vision_math.region_box(region) == pytest.approx((4 / 20, 6 / 20, 11 / 20, 13 / 20), abs=0.051)


def test_subject_region_is_empty_when_nothing_stands_out():
    rng = np.random.default_rng(1)
    base, along = rng.normal(size=(2, 16))
    xx = np.mgrid[0:12, 0:12][1] / 11 - 0.5
    surface = (base + xx[..., None] * along).reshape(1, 144, 16).astype(np.float32)
    # A smooth surface with no object: whatever Otsu splits off has no direction of its
    # own, so nothing is closer to it than to the surface, or the region is tiny.
    region = vision_math.subject_regions(surface)[0]
    assert region.sum() <= 144 * 0.2
    assert vision_math.region_box(np.zeros((5, 5), bool)) is None


def test_subject_region_ignores_the_surface_drift_a_border_comparison_would_follow():
    # With a strong drift the far corners differ from each other more than the block
    # differs from the surface next to it; a method comparing with border patches fails.
    features, truth = planted(drift=2.0, seed=3)
    region = vision_math.subject_regions(features)[0]
    assert (region & truth).sum() / (region | truth).sum() > 0.85


def test_subject_regions_validates_shape():
    with pytest.raises(ValueError):
        vision_math.subject_regions(np.zeros((1, 10, 4), np.float32))  # Not a square grid.
    with pytest.raises(ValueError):
        vision_math.subject_regions(np.zeros((16, 4), np.float32))


def test_subject_vector_is_the_unit_mean_inside_the_region():
    tokens = np.zeros((2, 9, 3), np.float32)
    tokens[0, :, 0] = 1
    tokens[0, 4] = (0, 2, 0)
    tokens[1, :, 2] = 5
    regions = np.zeros((2, 3, 3), bool)
    regions[0, 1, 1] = True  # Only the centre patch of picture 0; picture 1 has no subject.
    vectors = vision_math.subject_vectors(tokens, regions)
    assert np.allclose(vectors[0], (0, 1, 0))
    assert np.allclose(vectors[1], (0, 0, 1))  # Falls back to the whole picture.


def test_neighbours_match_a_direct_computation_and_exclude_self():
    rng = np.random.default_rng(2)
    vectors = vision_math.unit(rng.normal(size=(37, 8)))
    seen = []
    indices, cosines = vision_math.neighbours(vectors, 5, chunk=10, progress=lambda d, t: seen.append((d, t)))
    scores = vectors @ vectors.T
    np.fill_diagonal(scores, -np.inf)
    expected = np.argsort(-scores, axis=1)[:, :5]
    assert (indices == expected).all()
    assert np.allclose(cosines, np.take_along_axis(scores, expected, axis=1), atol=1e-6)
    assert seen[-1] == (37, 37) and len(seen) == 4
    assert vision_math.neighbours(vectors[:1], 5)[0].shape == (1, 0)


def test_top_matches_orders_by_cosine():
    matrix = vision_math.unit(np.array([[1, 0], [0.9, 0.1], [0, 1], [-1, 0]], float))
    chosen, scores = vision_math.top_matches(matrix, matrix[0], 3)
    assert chosen.tolist() == [0, 1, 2] and scores[0] == pytest.approx(1.0)
    assert vision_math.top_matches(matrix, matrix[0], 0)[0].size == 0


def test_groups_need_the_link_from_both_sides():
    # 0 and 1 are each other's neighbour. 2 lists 0, but 0 does not list 2: no link.
    indices = np.array([[1], [0], [0], [4], [3]])
    cosines = np.array([[0.95], [0.95], [0.93], [0.6], [0.6]], np.float32)
    labels = vision_math.linked_groups(indices, cosines, 0.9)
    assert labels.tolist() == [0, 0, 2, 3, 4]  # 3-4 are mutual but below the threshold.
    assert vision_math.linked_groups(indices, cosines, 0.5).tolist() == [0, 0, 2, 3, 3]


# ----------------------------------------------------------------------- registry


def test_registry_names_files_by_their_hash_and_agrees_with_the_install_script():
    script = (ROOT / "scripts" / "vision-model.sh").read_text(encoding="utf-8")
    table = dict(re.findall(r"'(dinov3_\S+\.pth) ([0-9a-f]{64}) ", script))
    assert len(table) == len(vision.MODELS)
    for entry in vision.MODELS.values():
        assert entry["file"].endswith(f"-{entry['sha256'][:8]}.pth")  # Meta's own naming.
        assert table[entry["file"]] == entry["sha256"]
        assert 0.5 < entry["group"] < entry["lookalike"] < 1
    assert vision.CODE_COMMIT in script
    assert set(vision.CPU_ORDER) == set(vision.MODELS)


def test_status_explains_what_is_missing(no_model):
    state = vision.status()
    assert state["available"] is False and state["installed"] == []
    assert "vision-model.sh" in state["reason"]
    python = no_model / "env" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("")
    assert "weight file" in vision.status()["reason"]


def test_only_a_file_with_the_pinned_size_and_hash_is_accepted(no_model, monkeypatch):
    weights = no_model / "weights"
    weights.mkdir()
    good = b"not really weights"
    import hashlib

    entry = {**vision.MODELS["vits16"], "sha256": hashlib.sha256(good).hexdigest(), "bytes": len(good)}
    monkeypatch.setitem(vision.MODELS, "vits16", entry)
    path = weights / entry["file"]
    path.write_bytes(b"x" * len(good))  # Right size, wrong content.
    assert vision.verified("vits16") is None
    path.write_bytes(good + b"!")  # Wrong size: refused without hashing.
    assert vision.verified("vits16") is None
    path.write_bytes(good)
    assert vision.verified("vits16") == path
    assert list(vision.installed()) == ["vits16"]
    monkeypatch.setenv("PICAD_VISION_MODEL", "vitl16")
    assert "not installed" in vision.status()["reason"]
    monkeypatch.setenv("PICAD_VISION_MODEL", "nonsense")
    assert "must be one of" in vision.status()["reason"]


def test_a_model_process_that_cannot_start_is_reported_not_raised_at_status(no_model, monkeypatch):
    import hashlib

    weights = no_model / "weights"
    weights.mkdir()
    data = b"weights"
    entry = {**vision.MODELS["vits16"], "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    monkeypatch.setitem(vision.MODELS, "vits16", entry)
    (weights / entry["file"]).write_bytes(data)
    python = no_model / "env" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)  # A Python without PyTorch: the worker reports why.
    assert vision.status()["available"] is True
    with pytest.raises(vision.VisionError, match="could not start"):
        vision.engine.start()
    state = vision.status()
    assert state["available"] is False and "could not start" in state["reason"]


# ------------------------------------------------------------------ model process


def test_standin_process_describes_pictures_and_reports_unreadable_ones(standin):
    paths = []
    for index, part in enumerate(("red", "blue")):
        path = standin / f"{part}.png"
        photos.scene(part, index).save(path)
        paths.append(path)
    broken = standin / "broken.png"
    broken.write_bytes(b"not an image")
    arrays, failed = vision.engine.embed([*paths, broken, standin / "missing.png"], standin / "work")
    assert arrays["ok"].tolist() == [True, True, False, False]
    assert set(failed) == {2, 3}
    for key in ("whole", "subject"):
        assert arrays[key].shape == (4, 12)
        assert np.allclose(np.linalg.norm(arrays[key][:2], axis=1), 1, atol=1e-5)
        assert not arrays[key][2:].any()
    assert np.isfinite(arrays["box"][:2]).all() and np.isnan(arrays["box"][2:]).all()
    grid = 28
    region = np.unpackbits(arrays["mask"][0])[: grid * grid].reshape(grid, grid)
    assert 0.02 < region.mean() < 0.5  # The disc, not the whole frame.
    assert list((standin / "work").iterdir()) == []  # The result file is removed after reading.
    state = vision.status()
    assert state["available"] and state["standin"] and state["runtime"]["model"] == vision.STANDIN


def test_engine_restarts_after_the_process_dies(standin):
    path = standin / "red.png"
    photos.scene("red", 0).save(path)
    first = vision.engine.embed([path], standin / "work")[0]["whole"]
    vision.engine._process.kill()
    vision.engine._process.wait()
    second = vision.engine.embed([path], standin / "work")[0]["whole"]
    assert np.allclose(first, second)
    with pytest.raises(ValueError):
        vision.engine.embed([], standin / "work")


def test_worker_protocol_rejects_unknown_requests_and_keeps_running(standin):
    worker = subprocess.Popen(
        [sys.executable, str(vision.WORKER), "--standin"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        hello = json.loads(worker.stdout.readline())
        assert hello["ready"] and hello["grid"] == 28 and hello["input"] == 448
        for request, expected in (
            ("this is not json", {"ok": False}),
            ('{"id": 5, "op": "explode"}', {"id": 5, "ok": False}),
            ('{"id": 6, "op": "ping"}', {"id": 6, "ok": True}),
        ):
            worker.stdin.write(request + "\n")
            worker.stdin.flush()
            reply = json.loads(worker.stdout.readline())
            assert {key: reply[key] for key in expected} == expected
        worker.stdin.write('{"op": "quit"}\n')
        worker.stdin.flush()
        assert worker.wait(timeout=10) == 0
    finally:
        worker.kill()


def test_worker_without_weights_fails_with_a_reason():
    done = subprocess.run(
        [sys.executable, str(vision.WORKER)], input="", capture_output=True, text=True, timeout=60, check=False
    )
    hello = json.loads(done.stdout.splitlines()[0])
    assert done.returncode == 1 and hello["ready"] is False and "candidates" in hello["error"]


# -------------------------------------------------------------------- real model


@needs_model
def test_installed_model_finds_the_part_and_matches_it_across_backgrounds(tmp_path, monkeypatch):
    """The real DINOv3 model, when installed: two parts, three rendered shots each."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import vision_scenes

    monkeypatch.delenv("PICAD_VISION_STANDIN", raising=False)
    paths, labels, truths = [], [], []
    for part in ("flange", "gusset"):
        for view in range(3):
            kind = vision_scenes.BACKGROUNDS[(view * 3 + len(part)) % 8]
            data, truth = vision_scenes.render(part, kind, 900 + view + len(part))
            path = tmp_path / f"{part}-{view}.jpg"
            path.write_bytes(data)
            paths.append(path)
            labels.append(part)
            truths.append(truth)
    try:
        arrays, failed = vision.engine.embed(paths, tmp_path / "work")
    finally:
        vision.engine.close()
    assert not failed and arrays["ok"].all()
    labels = np.array(labels)
    scores = arrays["subject"] @ arrays["subject"].T
    np.fill_diagonal(scores, -np.inf)
    assert (labels[scores.argmax(axis=1)] == labels).all()  # Nearest shot is the same part.
    height, width = truths[0]["mask"].shape
    for box, truth in zip(arrays["box"], truths, strict=True):
        x0, y0, x1, y1 = truth["box"]
        true = (x0 / width, y0 / height, x1 / width, y1 / height)
        overlap_w = max(0, min(box[2], true[2]) - max(box[0], true[0]))
        overlap_h = max(0, min(box[3], true[3]) - max(box[1], true[1]))
        union = (box[2] - box[0]) * (box[3] - box[1]) + (true[2] - true[0]) * (true[3] - true[1])
        assert overlap_w * overlap_h / (union - overlap_w * overlap_h) > 0.5


def test_chained_groups_are_split_where_the_two_sides_are_not_alike():
    # Three tight clusters on a line: a-b-c, each close to the next, a and c far apart.
    rng = np.random.default_rng(5)
    centres = vision_math.unit(np.array([[1, 0, 0], [0.8, 0.6, 0], [0.28, 0.96, 0]], float))
    vectors = vision_math.unit(np.repeat(centres, 4, axis=0) + rng.normal(0, 0.01, (12, 3)))
    truth = np.repeat(np.arange(3), 4)
    near, cosines = vision_math.neighbours(vectors, 11)
    chained = vision_math.linked_groups(near, cosines, 0.75)
    assert len(set(chained.tolist())) == 1  # 0.8 between neighbouring clusters links all twelve.
    split = vision_math.split_chained(vectors, chained, 0.9)
    assert [len(set(split[truth == k].tolist())) for k in range(3)] == [1, 1, 1]
    assert len(set(split.tolist())) == 3
    assert split.tolist() == [0] * 4 + [4] * 4 + [8] * 4  # Labelled by the lowest member.
    # A group over the size limit is left whole, and pairs are never touched.
    assert (vision_math.split_chained(vectors, chained, 0.9, limit=5) == chained).all()
    pair = np.array([0, 0])
    assert (vision_math.split_chained(vectors[[0, 11]], pair, 0.99) == pair).all()
