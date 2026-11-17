"""Evidence for the photo library: measurements, the crunch pipeline, storage rules and
the HTTP routes.

Feature vectors come from the stand-in process (colour statistics), so these tests run
without PyTorch or model weights. They establish how the library behaves around the
model; what the real model can tell apart is measured by scripts/vision_benchmark.py.
"""

import csv
import hashlib
import io
import os
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import app as api
from backend import library, vision
from tests import photos

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def lib(monkeypatch, tmp_path):
    """An empty library in a temporary folder, with the stand-in feature process."""
    monkeypatch.setenv("PICAD_LIBRARY_DIR", str(tmp_path / "library"))
    monkeypatch.setenv("PICAD_LIBRARY_WORKERS", "2")
    monkeypatch.setenv("PICAD_VISION_STANDIN", "1")
    monkeypatch.delenv("PICAD_LIBRARY_FOLDERS", raising=False)
    yield tmp_path
    library.job.cancel()
    library.job.wait(60)
    vision.engine.close()
    vision.engine.forget_failure()


def crunch(expect="finished"):
    library.start_crunch()
    library.job.wait(120)
    state = library.job.state()
    assert state["stage"] == expect, state
    return state["summary"]


def named(view="all", **options):
    return {photo["name"]: photo for photo in library.list_photos(view=view, limit=500, **options)["photos"]}


# ------------------------------------------------------------------- measurements


def step_image(blur, size=(600, 800), noise=1.5, seed=0):
    """A dark rectangle on a light ground, blurred by a known Gaussian, with noise."""
    rng = np.random.default_rng(seed)
    image = np.full(size, 210, np.float32)
    image[150:450, 200:600] = 50
    image = cv2.GaussianBlur(image, (0, 0), blur) if blur else image
    return image + rng.normal(0, noise, size).astype(np.float32)


def test_edge_blur_follows_a_known_blur():
    readings = [library.edge_blur(step_image(blur))[0] for blur in (1.0, 2.0, 3.0, 4.0)]
    assert readings == sorted(readings)
    # A pixel-sampled step read with bilinear sampling adds about 0.45 px in quadrature.
    for blur, reading in zip((1.0, 2.0, 3.0, 4.0), readings, strict=True):
        assert reading == pytest.approx(np.hypot(blur, 0.45), rel=0.08)
    sharp = library.edge_blur(step_image(0))[0]
    assert sharp < 0.7


def test_edge_blur_declines_pictures_without_clear_edges():
    rng = np.random.default_rng(1)
    noise = np.full((400, 500), 128, np.float32) + rng.normal(0, 3, (400, 500)).astype(np.float32)
    reading, tiles = library.edge_blur(noise)
    assert reading is None and np.isnan(tiles).all()
    assert library.edge_blur(np.zeros((20, 20), np.float32))[0] is None  # Too small to tile.


def test_edge_blur_is_not_fooled_by_faint_noisy_edges():
    # A 10-level step in 6-level noise used to read as an impossibly sharp edge.
    rng = np.random.default_rng(4)
    image = np.full((600, 800), 100, np.float32)
    image[:, 400:] = 110
    image[300:, :] += 100  # One strong, blurred edge as well.
    image = cv2.GaussianBlur(image, (0, 0), 2.0) + rng.normal(0, 6, image.shape).astype(np.float32)
    reading, tiles = library.edge_blur(image)
    assert reading == pytest.approx(2.0, rel=0.25)
    assert np.nanmin(tiles) >= 0.2


def test_edges_between_equally_bright_colours_are_still_measured():
    red, green = (200, 40, 40), (40, 110, 80)  # Rec. 601 luma 88 and 86: no brightness edge.
    image = np.zeros((480, 640, 3), np.uint8)
    image[:] = green
    cv2.circle(image, (320, 240), 150, red, -1)
    image = cv2.GaussianBlur(image, (0, 0), 2.0)
    luma = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
    assert library.edge_blur(luma)[0] is None
    reading = library.edge_blur(library.contrast_image(image))[0]
    assert reading == pytest.approx(2.0, rel=0.2)
    flat = library.contrast_image(np.full((50, 60, 3), 90, np.uint8))  # No colour variation at all.
    assert flat.shape == (50, 60) and np.isfinite(flat).all()


def test_subject_blur_reads_only_the_tiles_on_the_subject():
    tiles = np.full((library.TILES, library.TILES), 4.0, np.float32)
    tiles[6:12, 6:12] = 1.5  # A sharp subject in a soft scene.
    tiles[0, 0] = np.nan
    whole = np.concatenate([np.array([0, 0, 1, 1], np.float32), tiles.ravel()]).astype(np.float16).tobytes()
    region = np.zeros((28, 28), bool)
    region[8:13, 8:13] = True  # Covers tiles 7..11 of 24; growing by one patch adds a rim.
    assert library.subject_blur(whole, region) == pytest.approx(1.5)
    assert library.subject_blur(whole, np.zeros((28, 28), bool)) is None
    assert library.subject_blur(None, region) is None
    assert library.subject_blur(b"\x00" * 10, region) is None
    # The measured area can be a central crop: the same tiles then lie elsewhere.
    crop = np.concatenate([np.array([0.5, 0.5, 1, 1], np.float32), tiles.ravel()]).astype(np.float16).tobytes()
    assert library.subject_blur(crop, region) is None  # The subject is outside the crop.


def exif_jpeg(image, orientation=None, taken=None, make=None, model=None, gps=False):
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    if make:
        exif[0x010F] = make
    if model:
        exif[0x0110] = model
    if taken:
        exif.get_ifd(0x8769)[0x9003] = taken
    if gps:
        exif.get_ifd(0x8825)[2] = (52.0, 30.0, 0.0)
    return photos.encoded(image, "JPEG", quality=92, exif=exif)


def test_read_photo_measures_and_writes_a_bounded_preview(tmp_path):
    source = tmp_path / "plate.jpg"
    source.write_bytes(
        exif_jpeg(
            photos.scene("black", 1, size=(1600, 1200)),
            orientation=6,
            taken="2026:03:04 05:06:07",
            make="Acme",
            model="Phone 9",
            gps=True,
        )
    )
    preview = tmp_path / "out" / "1.jpg"
    facts = library.read_photo(str(source), str(preview))
    assert (facts["width"], facts["height"]) == (1200, 1600)  # Orientation 6 is applied.
    assert facts["format"] == "JPEG" and facts["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert facts["taken_at"] == "2026-03-04T05:06:07" and facts["camera"] == "Acme Phone 9"
    assert 0.2 <= facts["blur_px"] < 1.5 and 0 <= facts["clipped"] <= 1
    assert len(facts["blur_map"]) == 2 * (4 + library.TILES**2)
    assert "gps" not in " ".join(facts).lower()  # Location is never read or stored.
    with Image.open(preview) as small:
        assert small.size == (384, 512) and small.format == "JPEG"
        assert not small.getexif()  # The preview carries no metadata.


def test_large_jpegs_are_decoded_reduced_and_reported_in_their_own_pixels(tmp_path):
    assert [library._draft_scale(*size) for size in ((4032, 3024), (3264, 2448), (2000, 1500), (8064, 6048))] == [2, 2, 1, 4]
    # The same 3 px blurred scene saved small (decoded in full) and at 12 megapixels
    # (decoded at half scale): the large one's blur must read about 3 x 2.52 = 7.6 of its
    # own pixels... which exceeds what the profile can follow, so use a sharper one.
    base = photos.scene("black", 1, size=(1600, 1200), blur=1.2)
    small = tmp_path / "small.jpg"
    small.write_bytes(photos.encoded(base, "JPEG", quality=92))
    large = tmp_path / "large.jpg"
    large.write_bytes(
        exif_jpeg(base.resize((4032, 3024), Image.Resampling.BICUBIC), orientation=6, make="Acme", model="Phone 9")
    )
    full = library.read_photo(str(small), str(tmp_path / "small-preview.jpg"))
    reduced = library.read_photo(str(large), str(tmp_path / "large-preview.jpg"))
    assert (reduced["width"], reduced["height"]) == (3024, 4032)  # Its own size, turned upright.
    assert reduced["camera"] == "Acme Phone 9"
    assert reduced["blur_px"] == pytest.approx(full["blur_px"] * 2.52, rel=0.2)
    with Image.open(tmp_path / "large-preview.jpg") as preview:
        assert preview.size == (384, 512)
    assert library._decode_jpeg_reduced(photos.encoded(base, "PNG")) is None
    with pytest.raises(library.TraceError, match="16 pixels"):
        library._decode_jpeg_reduced(photos.encoded(Image.new("RGB", (8, 8)), "JPEG"))


def test_read_photo_refuses_bad_files_without_raising(tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"\x89PNG\r\n\x1a\nnot a png")
    assert library.read_photo(str(bad), str(tmp_path / "p.jpg"))["error"].startswith("The image could not")
    assert "could not be read" in library.read_photo(str(tmp_path / "missing.png"), str(tmp_path / "p.jpg"))["error"]
    empty = tmp_path / "empty.jpg"
    empty.write_bytes(b"")
    assert library.read_photo(str(empty), str(tmp_path / "p.jpg"))["error"] == "The file is empty."
    tiny = tmp_path / "tiny.png"
    Image.new("RGB", (8, 8)).save(tiny)
    assert "16 pixels" in library.read_photo(str(tiny), str(tmp_path / "p.jpg"))["error"]
    assert not (tmp_path / "p.jpg").exists()


def test_read_photo_decodes_heic_with_the_workbench_decoder(tmp_path):
    facts = library.read_photo(str(ROOT / "tests" / "fixtures" / "plain.heic"), str(tmp_path / "p.jpg"))
    assert facts.get("format") == "HEIC" and facts["width"] >= 16
    assert (tmp_path / "p.jpg").is_file()


# ----------------------------------------------------------------------- pipeline


def test_crunch_indexes_describes_and_organizes_a_folder(lib):
    folder = lib / "shots"
    folder.mkdir()
    names = photos.write_set(folder)
    (folder / "red-0-copy.png").write_bytes((folder / "red-0.png").read_bytes())  # Exact copy.
    half = Image.open(folder / "blue-1.png")
    half.resize((320, 240), Image.Resampling.LANCZOS).save(folder / "blue-1-small.png")  # Look-alike.
    (folder / "notes.txt").write_text("not a picture")
    (folder / "broken.jpg").write_bytes(b"\xff\xd8\xff not a jpeg")
    hidden = folder / ".thumbnails"
    hidden.mkdir()
    photos.scene("red", 9).save(hidden / "skip.png")
    library.add_folder(str(folder))
    summary = crunch()
    assert summary["scan"] == {"new": len(names) + 3, "changed": 0, "gone": 0}
    assert summary["read"] == {"read": len(names) + 2, "failed": 1}
    assert summary["features"]["described"] == len(names) + 2
    totals = library.summary()
    assert (totals["photos"], totals["ready"], totals["failed"], totals["described"]) == (19, 18, 1, 18)
    rows = named()
    assert set(rows) == {*names, "red-0-copy.png", "blue-1-small.png"}  # Failed files are listed apart.
    assert "broken.jpg" in named("failed")
    # Exact copy and look-alike sets.
    # A set is named after its lowest photo id; ids follow the folder's listing order.
    assert rows["red-0-copy.png"]["dup_set"] == rows["red-0.png"]["dup_set"]
    assert rows["red-0.png"]["dup_set"] == min(rows["red-0.png"]["id"], rows["red-0-copy.png"]["id"])
    assert rows["red-0-copy.png"]["dup_kind"] == rows["red-0.png"]["dup_kind"] == "exact"
    assert rows["blue-1-small.png"]["dup_set"] == rows["blue-1.png"]["dup_set"]
    assert rows["blue-1-small.png"]["dup_kind"] == "lookalike"
    assert rows["yellow-0.png"]["dup_set"] is None
    # Groups: each colour's shots together, colours apart; one best shot per group.
    by_part = {}
    for name, row in rows.items():
        by_part.setdefault(name.split("-")[0], set()).add(row["group_id"])
    assert all(len(groups) == 1 and None not in groups for groups in by_part.values())
    assert len({next(iter(groups)) for groups in by_part.values()}) == 4
    for part in by_part:
        best = [name for name, row in rows.items() if name.startswith(part) and row["best"]]
        assert len(best) == 1
        members = [row for name, row in rows.items() if name.startswith(part)]
        assert rows[best[0]]["detail"] == max(row["detail"] for row in members)
    assert rows["blue-1-small.png"]["detail"] < rows["blue-1.png"]["detail"]  # Half the pixels across.
    # Previews exist for readable photos only, inside the library's storage.
    assert library.preview_path(rows["red-0.png"]["id"]).is_file()
    assert not library.preview_path(named("failed")["broken.jpg"]["id"]).exists()
    groups = library.list_groups()
    assert groups["total"] == 4 and sorted(group["size"] for group in groups["groups"]) == [4, 4, 5, 5]


def test_rescan_notices_new_changed_and_removed_files_without_redoing_the_rest(lib):
    folder = lib / "shots"
    folder.mkdir()
    photos.write_set(folder, views=2, parts=("red", "blue"))
    library.add_folder(str(folder))
    crunch()
    before = named()
    photos.scene("yellow", 0).save(folder / "yellow-0.png")
    photos.scene("blue", 5).save(folder / "blue-0.png")  # Overwritten with another picture.
    future = time.time() + 5
    os.utime(folder / "blue-0.png", (future, future))
    (folder / "red-1.png").unlink()
    summary = crunch()
    assert summary["scan"] == {"new": 1, "changed": 1, "gone": 1}
    assert summary["read"]["read"] == 2 and summary["features"]["described"] == 2
    after = named()
    assert set(after) == {"red-0.png", "blue-0.png", "blue-1.png", "yellow-0.png"}
    assert after["red-0.png"]["id"] == before["red-0.png"]["id"]
    assert not library.preview_path(before["red-1.png"]["id"]).exists()
    assert crunch()["scan"] == {"new": 0, "changed": 0, "gone": 0}  # Nothing to do the third time.


def test_without_the_model_photos_are_still_indexed_and_exact_copies_found(lib, monkeypatch):
    monkeypatch.delenv("PICAD_VISION_STANDIN")
    monkeypatch.setenv("PICAD_VISION_WEIGHTS", str(lib / "no-weights"))
    monkeypatch.setenv("PICAD_VISION_PYTHON", str(lib / "no-python"))
    folder = lib / "shots"
    folder.mkdir()
    photos.write_set(folder, views=2, parts=("red",))
    (folder / "again.png").write_bytes((folder / "red-1.png").read_bytes())
    library.add_folder(str(folder))
    summary = crunch()
    assert summary["read"]["read"] == 3 and "vision-model.sh" in summary["features"]["skipped"]
    rows = named()
    assert rows["again.png"]["dup_kind"] == "exact" and rows["red-0.png"]["group_id"] is None
    assert all(row["blur_px"] and row["detail"] for row in rows.values())
    with pytest.raises(library.LibraryError, match="no vision features"):
        library.similar(rows["red-0.png"]["id"])


def test_only_one_crunch_runs_and_it_can_be_cancelled(lib):
    folder = lib / "shots"
    folder.mkdir()
    photos.write_set(folder, views=3)
    library.add_folder(str(folder))
    library.start_crunch()
    with pytest.raises(library.Busy):
        library.start_crunch()
    library.job.cancel()
    library.job.wait(120)
    state = library.job.state()
    assert state["running"] is False and state["stage"] in ("cancelled", "finished")
    crunch()  # A later crunch finishes what was left.
    assert library.summary()["ready"] == 12


def test_readers_that_never_answer_end_the_crunch_instead_of_holding_it(lib, monkeypatch):
    from concurrent.futures import Future

    class SilentPool:
        """A reader pool whose work never finishes, as when its processes are frozen."""

        killed = shut = 0

        def __init__(self, **_options):
            process = type("Process", (), {"kill": lambda _self: setattr(SilentPool, "killed", SilentPool.killed + 1)})
            self._processes = {1: process(), 2: process()}

        def submit(self, *_work):
            return Future()

        def shutdown(self, wait=True, cancel_futures=False):
            assert wait is False and cancel_futures is True  # Never waits for frozen readers.
            SilentPool.shut += 1

    monkeypatch.setattr(library, "ProcessPoolExecutor", SilentPool)
    monkeypatch.setattr(library, "READ_STALL_SECONDS", 0.2)
    folder = lib / "shots"
    folder.mkdir()
    photos.write_set(folder, views=1, parts=("red", "blue"))
    library.add_folder(str(folder))
    library.start_crunch()
    library.job.wait(30)
    state = library.job.state()
    assert state["running"] is False and state["stage"] == "failed"
    assert "stopped responding" in state["error"]
    assert (SilentPool.killed, SilentPool.shut) == (2, 1)
    assert library.summary()["pending"] == 2  # Nothing is marked failed; a later crunch retries.
    monkeypatch.undo()
    monkeypatch.setenv("PICAD_LIBRARY_DIR", str(lib / "library"))
    monkeypatch.setenv("PICAD_LIBRARY_WORKERS", "2")
    monkeypatch.setenv("PICAD_VISION_STANDIN", "1")
    crunch()
    assert library.summary()["ready"] == 2


def test_similar_photos_are_the_same_part_first(lib):
    folder = lib / "shots"
    folder.mkdir()
    photos.write_set(folder)
    library.add_folder(str(folder))
    crunch()
    rows = named()
    found = library.similar(rows["yellow-0.png"]["id"], limit=5)
    assert [photo["name"].split("-")[0] for photo in found["photos"][:3]] == ["yellow"] * 3
    assert found["photos"][0]["score"] >= found["photos"][-1]["score"]
    assert rows["yellow-0.png"]["id"] not in [photo["id"] for photo in found["photos"]]
    outside = photos.encoded(photos.scene("blue", 7))
    matches = library.search_by_picture("query.png", outside)
    assert matches["photos"][0]["name"].startswith("blue")
    assert library.summary()["photos"] == 16  # The query picture was not added.
    assert list((library.library_root() / "tmp").iterdir()) == []
    with pytest.raises(library.LibraryError):
        library.search_by_picture("query.png", b"junk")


# ------------------------------------------------------------------ storage rules


def test_folders_are_validated(lib):
    folder = lib / "shots"
    (folder / "inner").mkdir(parents=True)
    with pytest.raises(library.LibraryError, match="does not exist"):
        library.add_folder(str(lib / "nowhere"))
    with pytest.raises(library.LibraryError, match="not a folder"):
        (lib / "file.txt").write_text("x")
        library.add_folder(str(lib / "file.txt"))
    library.library_root().mkdir(parents=True, exist_ok=True)
    with pytest.raises(library.LibraryError, match="own storage"):
        library.add_folder(str(library.library_root()))
    library.add_folder(str(folder / "inner"))
    with pytest.raises(library.LibraryError, match="already in the library"):
        library.add_folder(str(folder / "inner"))
    with pytest.raises(library.LibraryError, match="inside that folder"):
        library.add_folder(str(folder))
    link = lib / "link"
    link.symlink_to(folder / "inner")  # A link resolves to the same folder.
    with pytest.raises(library.LibraryError, match="already in the library"):
        library.add_folder(str(link))


def test_scan_skips_linked_folders_and_the_librarys_own_storage(lib):
    folder = lib / "shots"
    folder.mkdir()
    photos.scene("red", 0).save(folder / "a.png")
    elsewhere = lib / "elsewhere"
    elsewhere.mkdir()
    photos.scene("blue", 0).save(elsewhere / "b.png")
    (folder / "linked").symlink_to(elsewhere, target_is_directory=True)
    (folder / "linked.png").symlink_to(elsewhere / "b.png")
    library.add_folder(str(lib))  # Contains the library's storage folder as well.
    crunch()
    crunch()  # The first crunch's previews must not be picked up by the second.
    assert sorted(named()) == ["a.png", "b.png"]


def test_browse_lists_folders_and_counts_pictures(lib, monkeypatch):
    (lib / "home" / "Pictures" / "parts").mkdir(parents=True)
    (lib / "home" / ".secret").mkdir()
    photos.scene("red", 0).save(lib / "home" / "Pictures" / "one.png")
    monkeypatch.setattr(library, "home", lambda: lib / "home")
    top = library.browse(None)
    assert [folder["name"] for folder in top["folders"]] == ["Pictures"]  # Hidden folders are not listed.
    assert top["shortcuts"] == [{"name": "Pictures", "path": str(lib / "home" / "Pictures")}]
    inner = library.browse(str(lib / "home" / "Pictures"))
    assert inner["photos"] == 1 and inner["parent"] == str(lib / "home")
    assert [folder["name"] for folder in inner["folders"]] == ["parts"]
    with pytest.raises(library.LibraryError):
        library.browse(str(lib / "home" / "missing"))


def test_uploads_are_stored_once_and_only_they_can_be_removed(lib):
    data = photos.encoded(photos.scene("red", 0))
    first = library.add_upload("../../evil name?.png", data)
    again = library.add_upload("other.png", data)
    assert first == {"id": first["id"], "duplicate": False} and again == {"id": first["id"], "duplicate": True}
    stored = list((library.library_root() / "uploads").rglob("*.png"))
    assert len(stored) == 1 and stored[0].name == "evil name_.png"
    assert library.library_root() in stored[0].parents and oct(stored[0].stat().st_mode & 0o777) == "0o600"
    for name, payload, message in (
        ("a.gif", data, "PNG, JPEG"),
        ("a.png", b"", "PNG, JPEG"),
        ("a.png", b"x" * (library.MAX_BYTES + 1), "32 MiB"),
    ):
        with pytest.raises(library.LibraryError, match=message):
            library.add_upload(name, payload)
    crunch()
    assert library.get_photo(first["id"])["source"] == "upload" and library.get_photo(first["id"])["path"] is None
    path, name = library.original_file(first["id"])
    assert path == stored[0] and name == "evil name_.png"
    library.remove_photo(first["id"])
    assert not stored[0].exists() and library.summary()["photos"] == 0
    with pytest.raises(library.LibraryError, match="not found"):
        library.remove_photo(first["id"])


def test_identical_uploads_arriving_together_are_stored_once(lib):
    from concurrent.futures import ThreadPoolExecutor

    data = photos.encoded(photos.scene("blue", 2))
    with ThreadPoolExecutor(8) as pool:
        replies = list(pool.map(lambda index: library.add_upload(f"shot-{index}.png", data), range(8)))
    assert len({reply["id"] for reply in replies}) == 1
    assert sum(not reply["duplicate"] for reply in replies) == 1
    assert library.summary()["photos"] == 1 and len(list((library.library_root() / "uploads").rglob("*.png"))) == 1


def test_a_folder_photo_is_never_deleted_and_changed_originals_are_refused(lib):
    folder = lib / "shots"
    folder.mkdir()
    photos.scene("red", 0).save(folder / "a.png")
    library.add_folder(str(folder))
    crunch()
    photo = named()["a.png"]
    with pytest.raises(library.LibraryError, match="added folder"):
        library.remove_photo(photo["id"])
    assert library.original_file(photo["id"])[0] == folder / "a.png"
    photos.scene("blue", 0).save(folder / "a.png")
    with pytest.raises(library.LibraryError, match="changed since"):
        library.original_file(photo["id"])
    (folder / "a.png").unlink()
    with pytest.raises(library.LibraryError, match="no longer there"):
        library.original_file(photo["id"])
    folder_id = library.summary()["folders"][0]["id"]
    library.remove_folder(folder_id)
    assert library.summary()["photos"] == 0 and not library.preview_path(photo["id"]).exists()
    assert folder.is_dir()  # Removing a folder from the library never touches the folder.


def test_clear_forgets_everything_derived_and_keeps_originals(lib):
    folder = lib / "shots"
    folder.mkdir()
    photos.write_set(folder, views=1, parts=("red", "blue"))
    library.add_folder(str(folder))
    library.add_upload("up.png", photos.encoded(photos.scene("black", 0)))
    crunch()
    library.clear()
    totals = library.summary()
    assert totals["photos"] == 0 and totals["folders"] == [] and totals["described"] == 0
    assert not (library.library_root() / "previews").exists() and not (library.library_root() / "uploads").exists()
    assert sorted(path.name for path in folder.iterdir()) == ["blue-0.png", "red-0.png"]


def test_export_lists_every_photo_and_neutralizes_spreadsheet_formulas(lib):
    folder = lib / "shots"
    folder.mkdir()
    photos.scene("red", 0).save(folder / "=HYPERLINK(1).png")
    photos.scene("blue", 0).save(folder / "plain.png")
    library.add_folder(str(folder))
    crunch()
    rows = sorted(csv.DictReader(io.StringIO(library.export_csv())), key=lambda row: row["name"])
    assert [row["name"] for row in rows] == ["'=HYPERLINK(1).png", "plain.png"]
    assert set(rows[0]) == set(library.EXPORT_COLUMNS) and "blur_map" not in rows[0]
    assert rows[1]["source"] == "folder" and rows[1]["path"].endswith("plain.png")
    assert float(rows[1]["blur_px"]) > 0 and 0 <= float(rows[1]["subject_x0"]) < float(rows[1]["subject_x1"]) <= 1
    assert len(rows[1]["sha256"]) == 64
    import json

    assert sorted(photo["name"] for photo in json.loads(library.export_json())["photos"]) == [
        "=HYPERLINK(1).png",
        "plain.png",
    ]


# --------------------------------------------------------------------------- HTTP


@pytest.fixture
def client(lib):
    with TestClient(api.app) as test_client:
        yield test_client


def wait_for_job(client):
    for _ in range(600):
        job = client.get("/api/library").json()["job"]
        if not job.get("running"):
            return job
        time.sleep(0.05)
    raise AssertionError("The library job did not finish.")


def test_folder_routes_are_only_for_the_workbench_page_on_this_computer(client, lib, monkeypatch):
    state = client.get("/api/library").json()
    assert state["folders_allowed"] is False  # The test client is not a loopback browser.
    assert state["summary"]["photos"] == 0 and state["vision"]["standin"] is True
    assert client.post("/api/library/browse", json={}).status_code == 403
    assert client.post("/api/library/folders", json={"path": str(lib)}).status_code == 403
    request = type(
        "R", (), {"client": type("C", (), {"host": "127.0.0.1"})(), "url": "http://127.0.0.1:8000/api/library/browse",
                  "base_url": "http://127.0.0.1:8000/", "headers": {"origin": "http://127.0.0.1:8000", "content-type": "application/json"}},
    )()  # fmt: skip
    assert api.library_folders_allowed(request) is True
    assert api.library_folders_allowed(request, with_body=False) is True
    request.headers = {"origin": "http://evil.example", "content-type": "application/json"}
    assert api.library_folders_allowed(request) is False  # Another site's page.
    request.headers = {"origin": "http://127.0.0.1:8000", "content-type": "text/plain"}
    assert api.library_folders_allowed(request) is False  # A form post, not the page's JSON.
    request.client.host = "192.168.1.20"
    request.headers = {"origin": "http://127.0.0.1:8000", "content-type": "application/json"}
    assert api.library_folders_allowed(request) is False  # Another computer.
    request.client.host = "127.0.0.1"
    monkeypatch.setenv("PICAD_LIBRARY_FOLDERS", "0")
    assert api.library_folders_allowed(request) is False and api.library_folders_allowed(request, with_body=False) is False


def test_http_workflow_from_upload_to_export(client, lib, monkeypatch):
    for part, view in (("red", 0), ("red", 1), ("blue", 0), ("blue", 1)):
        reply = client.post(
            "/api/library/uploads", files={"file": (f"{part}-{view}.png", photos.encoded(photos.scene(part, view)), "image/png")}
        )
        assert reply.status_code == 200 and reply.json()["duplicate"] is False
    assert client.post("/api/library/uploads", files={"file": ("x.gif", b"GIF89a", "image/gif")}).status_code == 422
    assert client.post("/api/library/crunch", json={}).status_code == 202
    assert client.post("/api/library/crunch", json={"extra": 1}).status_code == 422
    job = wait_for_job(client)
    assert job["stage"] == "finished" and job["summary"]["read"]["read"] == 4
    page = client.get("/api/library/photos", params={"sort": "name"}).json()
    assert page["total"] == 4 and page["photos"][0]["name"] == "blue-0.png"
    assert client.get("/api/library/photos", params={"q": "RED"}).json()["total"] == 2
    assert client.get("/api/library/photos", params={"q": "100%"}).json()["total"] == 0  # Wildcards are literal.
    assert client.get("/api/library/photos", params={"view": "nope"}).status_code == 422
    assert client.get("/api/library/photos", params={"limit": 0}).status_code == 422
    red = next(photo for photo in page["photos"] if photo["name"] == "red-0.png")
    detail = client.get(f"/api/library/photos/{red['id']}").json()
    assert detail["subject"]["grid"] == 28 and len(detail["subject"]["rows"]) == 28 and detail["group_size"] == 2
    assert detail["path"] is None  # An upload's storage path is not revealed.
    preview = client.get(f"/api/library/photos/{red['id']}/preview")
    assert preview.headers["content-type"] == "image/jpeg" and preview.headers["x-content-type-options"] == "nosniff"
    original = client.get(f"/api/library/photos/{red['id']}/original")
    assert original.content == photos.encoded(photos.scene("red", 0)) and "attachment" in original.headers["content-disposition"]
    similar = client.get(f"/api/library/photos/{red['id']}/similar").json()
    assert similar["photos"][0]["name"] == "red-1.png"
    found = client.post(
        "/api/library/search", files={"file": ("q.png", photos.encoded(photos.scene("blue", 3)), "image/png")}
    ).json()
    assert found["photos"][0]["name"].startswith("blue")
    groups = client.get("/api/library/groups").json()
    assert groups["total"] == 2 and {group["size"] for group in groups["groups"]} == {2}
    exported = client.get("/api/library/export")
    assert exported.headers["content-type"].startswith("text/csv") and exported.text.count("\n") == 5
    assert client.get("/api/library/export", params={"format": "json"}).json()["photos"][0]["source"] == "upload"
    assert client.get("/api/library/export", params={"format": "xml"}).status_code == 422
    for missing in ("/api/library/photos/999999", "/api/library/photos/999999/preview", "/api/library/photos/999999/original"):
        assert client.get(missing).status_code == 404
    assert client.get("/api/library/photos/999999/similar").status_code == 422
    assert client.delete(f"/api/library/photos/{red['id']}").status_code == 202
    wait_for_job(client)
    assert client.get("/api/library").json()["summary"]["photos"] == 3
    assert client.delete("/api/library").json() == {"cleared": True}
    assert client.get("/api/library").json()["summary"]["photos"] == 0


def test_http_folder_workflow_and_busy_refusals(client, lib, monkeypatch):
    monkeypatch.setattr(api, "library_folders_allowed", lambda request, with_body=True: True)
    folder = lib / "shots"
    folder.mkdir()
    photos.write_set(folder, views=2, parts=("red", "blue"))
    listing = client.post("/api/library/browse", json={"path": str(lib)}).json()
    assert {"name": "shots", "path": str(folder)} in listing["folders"]
    assert client.post("/api/library/folders", json={}).status_code == 422
    assert client.post("/api/library/folders", json={"path": str(lib / "nope")}).status_code == 422
    started = client.post("/api/library/folders", json={"path": str(folder)})
    assert started.status_code == 202 and started.json()["folder"]["path"] == str(folder)
    busy = client.post("/api/library/crunch", json={})
    if busy.status_code == 409:  # Still running: every changing route refuses politely.
        assert "Retry-After" in busy.headers
        assert client.delete("/api/library").status_code == 409
    assert wait_for_job(client)["stage"] == "finished"
    state = client.get("/api/library").json()
    assert state["summary"]["folders"][0]["photos"] == 4 and state["summary"]["groups"] == 2
    photo = client.get("/api/library/photos").json()["photos"][0]
    assert client.get(f"/api/library/photos/{photo['id']}").json()["path"].startswith(str(folder))
    refused = client.delete(f"/api/library/photos/{photo['id']}")
    assert refused.status_code == 422 and "added folder" in refused.json()["detail"]
    assert client.post("/api/library/cancel", json={}).status_code == 200
    assert client.delete(f"/api/library/folders/{state['summary']['folders'][0]['id']}").status_code == 202
    wait_for_job(client)
    assert client.get("/api/library").json()["summary"]["photos"] == 0
    assert client.delete("/api/library/folders/12345").status_code == 404


def test_another_sites_page_cannot_change_the_library(client):
    data = photos.encoded(photos.scene("red", 0))
    evil = {"Origin": "https://evil.example"}
    own = {"Origin": "http://testserver"}
    upload = {"file": ("a.png", data, "image/png")}
    assert client.post("/api/library/uploads", files=upload, headers=evil).status_code == 403
    assert client.post("/api/library/search", files=upload, headers=evil).status_code == 403
    assert client.post("/api/library/crunch", json={}, headers=evil).status_code == 403
    assert client.delete("/api/library", headers=evil).status_code == 403
    assert client.get("/api/library").json()["summary"]["photos"] == 0
    assert client.post("/api/library/uploads", files=upload, headers=own).status_code == 200
    assert client.post("/api/library/uploads", files=upload, headers={"Origin": "http://testserver:9"}).status_code == 403
    assert client.post("/api/library/uploads", files=upload, headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/library").json()["summary"]["photos"] == 1


def test_upload_size_is_bounded_before_parsing(client):
    huge = b"x" * (library.MAX_BYTES + 200_000)
    reply = client.post("/api/library/uploads", files={"file": ("big.png", huge, "image/png")})
    assert reply.status_code == 413 and "32 MiB" in reply.json()["detail"]
    assert api.body_limit("/api/library/search")[0] == api.body_limit("/api/trace")[0]
    assert api.body_limit("/api/library/crunch")[0] < api.body_limit("/api/library/uploads")[0]
