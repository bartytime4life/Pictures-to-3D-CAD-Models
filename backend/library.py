"""The photo library: index whole folders of photographs, measure them and organize them.

The library is a local catalogue, not a copy of the user's photos. For every picture it
keeps a small preview, a few measurements and (with the optional vision model) feature
vectors, in ``.local/library`` (or ``PICAD_LIBRARY_DIR``). Originals are read where
they are and never changed, moved or deleted. Pictures added through the browser instead
of from a folder are stored under ``uploads`` there, because no other copy is reachable.

Stages of a crunch
    1. Scan      Walk the added folders; note new, changed and vanished files.
    2. Read      Decode each new picture with the workbench's own decoders and limits
                 (in parallel worker processes), measure its edge blur, brightness and
                 clipping, and write a preview of at most 512 pixels.
    3. Features  With the vision model installed: a whole-picture vector, a subject
                 region and a subject vector for each preview (backend.vision).
    4. Organize  Exact copies (same SHA-256), look-alikes (near-identical pictures),
                 groups (same subject) and the best shot of each group.

Edge blur
    Measured on one channel: the colour direction in which the picture varies most
    (``contrast_direction``), so that an edge between two equally bright colours counts.
    ``edge_blur`` reports the width of the picture's strongest edges as the standard
    deviation, in the picture's own pixels, of the Gaussian that would blur a step into
    them. For such an edge of height H the steepest slope is H / (sigma sqrt(2 pi)), so
    sigma = H / (slope sqrt(2 pi)). A single slope sample is noisy, so the rise R across
    +-d (d about one sigma) is used instead: R / H = erf(d / (sigma sqrt 2)). The picture
    is first smoothed by 1 px (removed again in quadrature), the strongest edge point of
    each tile of a 24 x 24 grid is taken, its profile is sampled along the gradient, and
    H is read at +-(3 sigma + 1) px; four iterations settle d and that reach. The median
    over edge points is reported, and the per-tile values are kept so the blur can be
    read on the subject alone once the vision model has found it.
    Rendered experiments include pixel integration and JPEG as well as the applied
    blur; see docs/validation/photo-library.md for the validation scope.
    A JPEG of 7.6 megapixels or more is decoded at half scale or less, as its decoder
    allows, and the reading is scaled back to the photo's own pixels; on such photos
    blur below about one pixel is not resolved. A reading above about 5 measured pixels
    is cut short by the 12-pixel profile and reads low.
    It compares shots of the same scene well. Across different scenes it also reflects
    how sharp the scene's own edges are, so it is a ranking aid, not a lens measurement.

Detail
    A group's best shot is the one with the most *detail*: the subject's longer side in
    pixels divided by the edge blur, that is, how many blur widths span the part.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import multiprocessing
import os
import re
import shutil
import sqlite3
import threading
import time
import warnings
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from contextlib import contextmanager
from pathlib import Path

import cv2
import numpy as np
from PIL import ExifTags, Image

from . import heic, vision, vision_math
from .tracing import (
    MAX_BYTES,
    MAX_PIXELS,
    MIN_SIDE,
    ORIENTATION,
    TOO_MANY_PIXELS,
    TOO_SMALL,
    TraceError,
    decode_with_pillow,
    exif_focal_35mm,
)

ROOT = Path(__file__).resolve().parent.parent
SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif"}
PREVIEW_SIDE = 512
PREVIEW_QUALITY = 85
MAX_PHOTOS = 250_000
NEIGHBOURS = 12
FEATURE_BATCH = 512
READ_STALL_SECONDS = 180  # With no reader returning for this long, the read stage gives up.
PRE_SMOOTH = 1.0
REACH = 12
SCHEMA = 1
TOO_LARGE = "The file is larger than 32 MiB."
SORTS = {
    "added": "p.id DESC",
    "taken": "p.taken_at IS NULL, p.taken_at DESC, p.id DESC",
    "name": "p.name COLLATE NOCASE, p.id",
    "sharp": "COALESCE(f.subject_blur_px, p.blur_px) IS NULL, COALESCE(f.subject_blur_px, p.blur_px), p.id",
    "detail": "p.detail IS NULL, p.detail DESC, p.id",
    "size": "p.width * p.height DESC, p.id",
}
VIEWS = {
    "all": "1",
    "best": "p.best = 1",
    "duplicates": "p.dup_set IS NOT NULL",
    "grouped": "p.group_id IS NOT NULL",
    "failed": "p.state = 'failed'",
}


class LibraryError(ValueError):
    """A refusal with a user-facing message."""


class Busy(LibraryError):
    """Another library job is running."""


def library_root() -> Path:
    override = os.environ.get("PICAD_LIBRARY_DIR")
    return Path(override).expanduser().resolve() if override else ROOT / ".local" / "library"


def worker_count() -> int:
    try:
        wanted = int(os.environ.get("PICAD_LIBRARY_WORKERS", "0"))
    except ValueError:
        wanted = 0
    return wanted if wanted > 0 else max(1, min((os.cpu_count() or 2) - 2, 24))


# ------------------------------------------------------------------- measurements


TILES = 24
WINDOW = REACH + 9  # Half-size of the full-resolution window cut round each edge point.
# erf on a grid, to invert rise / step = erf(d / (sigma sqrt 2)) by interpolation.
_ERF_ARGUMENT = np.linspace(0.02, 3.0, 600)
_ERF = np.array([math.erf(value) for value in _ERF_ARGUMENT])


def contrast_direction(rgb: np.ndarray) -> np.ndarray:
    """Unit colour direction in which the picture varies most (first principal component).

    Brightness alone hides an edge between two colours of equal brightness, such as a
    red part on a green cutting mat. This direction keeps such an edge; for an ordinary
    picture it is close to brightness. It is found from a sample of about 100,000 pixels.
    """
    stride = max(1, int(math.sqrt(rgb.shape[0] * rgb.shape[1] / 100_000)))
    sample = rgb[::stride, ::stride].reshape(-1, 3).astype(np.float64)
    covariance = np.cov(sample, rowvar=False)
    direction = np.linalg.eigh(covariance)[1][:, -1] if np.isfinite(covariance).all() else np.zeros(3)
    if direction.sum() < 0:
        direction = -direction
    if not np.isfinite(direction).all() or np.allclose(direction, 0):
        direction = np.ones(3) / math.sqrt(3)
    return direction.astype(np.float32)


def contrast_image(rgb: np.ndarray) -> np.ndarray:
    """The picture as one float32 channel along ``contrast_direction``."""
    # Float input: on 8-bit input OpenCV would also return 8 bits and clip at 255.
    return cv2.transform(rgb.astype(np.float32), contrast_direction(rgb).reshape(1, 3))


def edge_blur(image: np.ndarray) -> tuple[float | None, np.ndarray]:
    """Gaussian width, in pixels, of a picture's strongest edges.

    ``image`` is an 8-bit RGB picture, measured along its ``contrast_direction``, or a
    single float channel. Returns (width, tiles). ``width`` is None when the picture has
    too few clear edges to tell (see the module text). ``tiles`` is a 24 x 24 float32
    map of the width at each tile's strongest edge, NaN where the tile has no clear
    edge; it lets the blur be read on the subject alone once the subject is known.

    Only the edge points are examined at full resolution. A large picture is first
    halved to find the strongest edge of each tile; a window of +-21 pixels is then cut
    from the full-resolution picture round each such point, and everything else is
    measured inside those windows. A 12-megapixel photo is measured from about a
    megapixel of windows plus one pass over a quarter-size copy.
    """
    colour = image.ndim == 3
    direction = contrast_direction(image) if colour else None
    height, width = image.shape[:2]
    empty = np.full((TILES, TILES), np.nan, np.float32)
    factor = 2 if min(height, width) >= 1200 else 1
    if factor > 1:
        coarse = cv2.resize(image, (width // factor, height // factor), interpolation=cv2.INTER_AREA)
    else:
        coarse = image
    coarse = cv2.transform(coarse.astype(np.float32), direction.reshape(1, 3)) if colour else coarse.astype(np.float32)
    coarse = cv2.GaussianBlur(coarse, (0, 0), PRE_SMOOTH)
    magnitude = cv2.magnitude(
        cv2.Scharr(coarse, cv2.CV_32F, 1, 0) / 32,  # Scharr's weights sum to 32 per pixel step.
        cv2.Scharr(coarse, cv2.CV_32F, 0, 1) / 32,
    )
    margin = -(-(WINDOW + 1) // factor) + 1  # Keeps every full-resolution window inside the picture.
    coarse_h, coarse_w = magnitude.shape
    tile_h, tile_w = (coarse_h - 2 * margin) // TILES, (coarse_w - 2 * margin) // TILES
    if tile_h < 2 or tile_w < 2:
        return None, empty
    inner = magnitude[margin : margin + tile_h * TILES, margin : margin + tile_w * TILES]
    blocks = inner.reshape(TILES, tile_h, TILES, tile_w).transpose(0, 2, 1, 3).reshape(TILES * TILES, -1)
    where = blocks.argmax(axis=1)
    peak = blocks[np.arange(TILES * TILES), where]
    keep = peak >= max(0.3 * float(peak.max()), 1.0)
    if keep.sum() < 8:
        return None, empty
    tile = np.flatnonzero(keep)
    ys = ((tile // TILES) * tile_h + where[tile] // tile_w + margin) * factor + factor // 2
    xs = ((tile % TILES) * tile_w + where[tile] % tile_w + margin) * factor + factor // 2

    # Full-resolution windows round the edge points, laid side by side in one image so
    # that smoothing, gradients and profile sampling are each a single call.
    span = np.arange(-WINDOW, WINDOW + 1)
    side = span.size
    windows = image[(ys[:, None] + span)[:, :, None], (xs[:, None] + span)[:, None, :]]
    windows = windows.astype(np.float32) @ direction if colour else windows.astype(np.float32)
    count = len(tile)
    across = math.ceil(math.sqrt(count))
    sheet = np.zeros((math.ceil(count / across) * side, across * side), np.float32)
    origin_y, origin_x = (np.arange(count) // across) * side, (np.arange(count) % across) * side
    for index in range(count):
        sheet[origin_y[index] : origin_y[index] + side, origin_x[index] : origin_x[index] + side] = windows[index]
    smooth = cv2.GaussianBlur(sheet, (0, 0), PRE_SMOOTH)
    gx = cv2.Scharr(smooth, cv2.CV_32F, 1, 0) / 32
    gy = cv2.Scharr(smooth, cv2.CV_32F, 0, 1) / 32
    # The exact edge point: the steepest pixel within a few pixels of each window's centre.
    near = factor + 2
    centre_rows = (origin_y[:, None] + WINDOW + np.arange(-near, near + 1))[:, :, None]
    centre_cols = (origin_x[:, None] + WINDOW + np.arange(-near, near + 1))[:, None, :]
    local = cv2.magnitude(gx, gy)[centre_rows, centre_cols].reshape(count, -1)
    best = local.argmax(axis=1)
    steep = np.maximum(local[np.arange(count), best], 1e-6)
    point_y = origin_y + WINDOW - near + best // (2 * near + 1)
    point_x = origin_x + WINDOW - near + best % (2 * near + 1)
    normal_x, normal_y = gx[point_y, point_x] / steep, gy[point_y, point_x] / steep
    offsets = np.arange(-REACH, REACH + 0.25, 0.5, dtype=np.float32)
    sample_x = (point_x[:, None] + normal_x[:, None] * offsets[None]).astype(np.float32)
    sample_y = (point_y[:, None] + normal_y[:, None] * offsets[None]).astype(np.float32)
    profile = cv2.remap(smooth, sample_x, sample_y, cv2.INTER_LINEAR)
    centre = len(offsets) // 2
    rows = np.arange(count)
    sigma = np.full(count, 2.0, np.float32)
    step = np.zeros(count, np.float32)
    for _ in range(4):
        # Step height between the plateaus at +-(3 sigma + 1), and the rise across +-d
        # with d about one sigma: for a Gaussian edge, rise / step = erf(d / (sigma sqrt 2)).
        reach = np.clip(3 * sigma + 1, 3, REACH)
        low = np.searchsorted(offsets, -reach)
        high = np.minimum(np.searchsorted(offsets, reach), len(offsets) - 1)
        step = profile[rows, high] - profile[rows, low]
        half = np.clip(np.round(sigma * 2), 2, 8).astype(int)  # d in half-pixel samples: 1 to 4 px.
        rise = profile[rows, centre + half] - profile[rows, centre - half]
        ratio = np.clip(rise / np.maximum(step, 1e-6), _ERF[0], _ERF[-1])
        sigma = np.clip((half / 2) / (math.sqrt(2) * np.interp(ratio, _ERF, _ERF_ARGUMENT)), 0.3, REACH / 2)
    # An edge cannot be sharper than the smoothing applied above; a reading clearly below
    # it is noise on a faint edge, not sharpness, and is discarded.
    clear = (step > 8) & (sigma >= 0.9 * PRE_SMOOTH)  # Edges of at least 8 of 255 levels.
    widths = np.sqrt(np.maximum(sigma * sigma - PRE_SMOOTH * PRE_SMOOTH, 0.04))
    flat = empty.ravel()
    flat[tile[clear]] = widths[clear]
    if clear.sum() < 8:
        return None, empty
    return float(np.median(widths[clear])), flat.reshape(TILES, TILES)


def subject_blur(blur_map: bytes | None, region: np.ndarray) -> float | None:
    """Edge blur on the subject alone: the median over the tiles lying on its region.

    ``blur_map`` is a photo's stored map (the measured area as fractions of the picture,
    then the 24 x 24 tile widths). A tile counts when its centre falls on the region
    grown by one patch, which takes in the subject's outline. At least four such tiles
    with a clear edge are required; otherwise None, and the whole picture's value stands.
    """
    if not blur_map:
        return None
    values = np.frombuffer(blur_map, np.float16).astype(np.float32)
    if values.size != 4 + TILES * TILES:
        return None
    x0, y0, x1, y1 = values[:4]
    tiles = values[4:].reshape(TILES, TILES)
    grid = region.shape[0]
    grown = region.copy()
    grown[1:] |= region[:-1]
    grown[:-1] |= region[1:]
    grown[:, 1:] |= region[:, :-1]
    grown[:, :-1] |= region[:, 1:]
    centres = (np.arange(TILES) + 0.5) / TILES
    columns = np.clip(((x0 + centres * (x1 - x0)) * grid).astype(int), 0, grid - 1)
    lines = np.clip(((y0 + centres * (y1 - y0)) * grid).astype(int), 0, grid - 1)
    on_subject = grown[np.ix_(lines, columns)] & np.isfinite(tiles)
    if on_subject.sum() < 4:
        return None
    return float(np.median(tiles[on_subject]))


def _exif(data: bytes) -> tuple[str | None, str | None]:
    """(time taken, camera) from EXIF, or Nones. Location tags are deliberately not read."""
    try:
        with Image.open(io.BytesIO(data)) as raw:
            exif = raw.getexif()
            taken = exif.get_ifd(0x8769).get(0x9003) or exif.get(0x0132)  # DateTimeOriginal, DateTime
            camera = " ".join(str(exif.get(tag, "")).strip("\x00 ") for tag in (0x010F, 0x0110)).strip()
    except Exception:  # noqa: BLE001 - optional metadata from untrusted input.
        return None, None
    stamp = None
    if isinstance(taken, str):
        match = re.fullmatch(r"(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})", taken.strip("\x00 "))
        if match:
            stamp = "{}-{}-{}T{}:{}:{}".format(*match.groups())
    printable = "".join(ch for ch in camera if ch.isprintable())[:80]
    return stamp, printable or None


DRAFT_PIXELS = 1_900_000  # A large JPEG is decoded at the smallest scale that keeps this many pixels.


def _draft_scale(width: int, height: int) -> int:
    """1, 2, 4 or 8: the largest JPEG decoding reduction that leaves 1.9 megapixels."""
    scale = 1
    while scale < 8 and width * height / (4 * scale * scale) >= DRAFT_PIXELS:
        scale *= 2
    return scale


def _decode_jpeg_reduced(data: bytes):
    """Decode a large JPEG at 1/2, 1/4 or 1/8 scale. Returns (image, focal, scale) or None.

    A JPEG decoder can produce a reduced picture directly from the stored cosine
    coefficients, which is several times faster than decoding every pixel and, more
    importantly here, moves a fraction of the memory: two dozen reader processes
    decoding 12-megapixel photos in full are limited by memory traffic to about 27
    photos a second on a 16-core machine, however many of them run.

    The checks are the workbench decoder's (tracing.decode_with_pillow): the stored size
    is limited before any pixel is decoded, the first frame of an MPO is used, and the
    stored orientation is applied. Returns None when the file is not a JPEG large enough
    to reduce, so the caller uses the ordinary decoder.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as raw:
            if raw.format not in ("JPEG", "MPO"):
                return None
            width, height = raw.size
            if width * height > MAX_PIXELS:
                raise TraceError(TOO_MANY_PIXELS)
            if min(width, height) < MIN_SIDE:
                raise TraceError(TOO_SMALL)
            scale = _draft_scale(width, height)
            if scale == 1:
                return None
            if raw.format == "MPO":
                raw.seek(0)
            raw.draft("RGB", (width // scale, height // scale))
            scale = max(1, round(width / raw.width))  # What the decoder actually granted.
            raw.load()
            try:
                exif = raw.getexif()
                method = ORIENTATION.get(exif.get(ExifTags.Base.Orientation, 1))
                focal = exif_focal_35mm(exif)
            except Exception:  # noqa: BLE001 - any malformed EXIF block is untrusted input.
                method, focal = None, None
            image = (raw.transpose(method) if method else raw).convert("RGB")
            image.load()
            quarter_turns = (
                Image.Transpose.ROTATE_90,
                Image.Transpose.ROTATE_270,
                Image.Transpose.TRANSPOSE,
                Image.Transpose.TRANSVERSE,
            )
            size = (height, width) if method in quarter_turns else (width, height)
    return image, focal, scale, size


def read_photo(path: str, preview: str) -> dict:
    """Decode one file, measure it and write its preview. Runs in a worker process.

    Returns the photo's facts, or ``{"error": reason}``. Never raises for a bad file.
    """
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_BYTES + 1)
    except OSError as exc:
        return {"error": f"The file could not be read ({exc.strerror or 'unknown error'})."}
    if len(data) > MAX_BYTES:
        return {"error": TOO_LARGE}
    if not data:
        return {"error": "The file is empty."}
    facts = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    scale, original_size = 1, None
    try:
        if heic.is_heic(data):
            try:
                image, focal = heic.decode(data, MAX_PIXELS, MIN_SIDE)
            except heic.HeicError as exc:
                reason = {"pixels": TOO_MANY_PIXELS, "small": TOO_SMALL}.get(exc.reason)
                return {**facts, "error": reason or "The HEIC image could not be decoded."}
            picture_format, taken, camera = "HEIC", None, None
        else:
            with Image.open(io.BytesIO(data)) as probe:
                picture_format = probe.format or ""
            reduced = _decode_jpeg_reduced(data)
            if reduced:
                image, focal, scale, original_size = reduced
            else:
                image, focal = decode_with_pillow(data, [])
            taken, camera = _exif(data)
    except TraceError as exc:
        return {**facts, "error": str(exc)}
    except Exception:  # noqa: BLE001 - Pillow's decoders raise many types for damaged files.
        return {**facts, "error": "The image could not be decoded."}
    width, height = original_size or image.size
    rgb = np.asarray(image, dtype=np.uint8)
    blur, tiles = edge_blur(rgb)
    if scale > 1:
        # Measured on the reduced picture: widths scale back, less the variance that
        # averaging scale x scale pixels added ((scale^2 - 1) / 12 original pixels^2).
        added = (scale * scale - 1) / 12
        tiles = np.sqrt(np.maximum((tiles * scale) ** 2 - added, 0.04))
        blur = None if blur is None else math.sqrt(max((blur * scale) ** 2 - added, 0.04))
    # The measured area as fractions of the picture (all of it), then the tile widths (float16).
    blur_map = np.concatenate([np.array([0, 0, 1, 1], np.float32), tiles.ravel()]).astype(np.float16).tobytes()
    shrink = min(1.0, PREVIEW_SIDE / max(image.size))
    target_size = (max(1, round(image.width * shrink)), max(1, round(image.height * shrink)))
    small = image.resize(target_size, Image.Resampling.LANCZOS, reducing_gap=2.0) if shrink < 1 else image
    levels = np.asarray(small.convert("L"), dtype=np.uint8)
    target = Path(preview)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".part")
    small.save(temporary, "JPEG", quality=PREVIEW_QUALITY)
    os.replace(temporary, target)
    return {
        **facts,
        "width": width,
        "height": height,
        "format": picture_format,
        "taken_at": taken,
        "camera": camera,
        "focal_35mm": focal,
        "blur_px": blur,
        "blur_map": blur_map,
        "brightness": float(levels.mean()),
        "clipped": float(((levels >= 250) | (levels <= 5)).mean()),
    }


def _quiet_worker():
    try:
        os.nice(5)  # Keep the workbench responsive while every core decodes.
    except OSError:
        pass


_BLAS_THREADS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")


@contextmanager
def _single_threaded_children():
    """While active, processes started from here get one linear-algebra thread each.

    NumPy's BLAS starts a thread per core in every process. Two dozen reader processes
    each doing that for a 3 x 3 eigenproblem spend their time contending: reading
    12-megapixel photos ran at 30 a second instead of over 100. The setting is read when
    a process loads NumPy, so it is placed in the environment the readers inherit; this
    process, whose NumPy is already loaded, keeps its threads.
    """
    before = {name: os.environ.get(name) for name in _BLAS_THREADS}
    os.environ.update(dict.fromkeys(_BLAS_THREADS, "1"))
    try:
        yield
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


# ------------------------------------------------------------------------- store

_store_init_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    root = library_root()
    root.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(root / "library.sqlite3", timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
    except BaseException:
        connection.close()
        raise
    return connection


@contextmanager
def database():
    # A first page load requests summary and photos concurrently. SQLite's WAL
    # transition can refuse that race immediately despite busy_timeout. Serialize
    # opening/migration only; normal reads and transactions remain concurrent.
    with _store_init_lock:
        connection = _connect()
        try:
            _migrate(connection)
        except BaseException:
            connection.close()
            raise
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


_migrated: set[str] = set()


def _migrate(connection):
    key = str(library_root())
    if key in _migrated:
        return
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS folders(
            id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, added_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS photos(
            id INTEGER PRIMARY KEY,
            folder_id INTEGER REFERENCES folders(id) ON DELETE CASCADE,
            path TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            bytes INTEGER, mtime_ns INTEGER, sha256 TEXT,
            width INTEGER, height INTEGER, format TEXT,
            taken_at TEXT, camera TEXT, focal_35mm REAL,
            blur_px REAL, blur_map BLOB, brightness REAL, clipped REAL, detail REAL,
            state TEXT NOT NULL DEFAULT 'pending', error TEXT, added_at REAL NOT NULL,
            group_id INTEGER, dup_set INTEGER, dup_kind TEXT, best INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS photos_state ON photos(state);
        CREATE INDEX IF NOT EXISTS photos_sha ON photos(sha256);
        CREATE INDEX IF NOT EXISTS photos_group ON photos(group_id);
        CREATE INDEX IF NOT EXISTS photos_dup ON photos(dup_set);
        CREATE TABLE IF NOT EXISTS features(
            photo_id INTEGER PRIMARY KEY REFERENCES photos(id) ON DELETE CASCADE,
            model TEXT NOT NULL, whole BLOB NOT NULL, subject BLOB NOT NULL,
            mask BLOB NOT NULL, grid INTEGER NOT NULL,
            box_x0 REAL, box_y0 REAL, box_x1 REAL, box_y1 REAL, subject_blur_px REAL);
        """
    )
    connection.execute("INSERT OR IGNORE INTO meta VALUES ('schema', ?)", (str(SCHEMA),))
    connection.execute("INSERT OR IGNORE INTO meta VALUES ('revision', '0')")
    connection.commit()
    _migrated.add(key)


def _bump(connection):
    """Mark that pictures or features changed, so cached vectors are reloaded."""
    connection.execute("UPDATE meta SET value = CAST(value AS INTEGER) + 1 WHERE key = 'revision'")


def preview_path(photo_id: int) -> Path:
    return library_root() / "previews" / f"{photo_id // 1000:04d}" / f"{photo_id}.jpg"


def _photo_row(row: sqlite3.Row) -> dict:
    keys = set(row.keys())
    item = {
        "id": row["id"],
        "name": row["name"],
        "width": row["width"],
        "height": row["height"],
        "blur_px": None if row["blur_px"] is None else round(row["blur_px"], 2),
        "subject_blur_px": (
            round(row["subject_blur_px"], 2) if "subject_blur_px" in keys and row["subject_blur_px"] is not None else None
        ),
        "detail": None if row["detail"] is None else round(row["detail"], 1),
        "taken_at": row["taken_at"],
        "state": row["state"],
        "group_id": row["group_id"],
        "dup_set": row["dup_set"],
        "dup_kind": row["dup_kind"],
        "best": bool(row["best"]),
    }
    if "box_x0" in keys and row["box_x0"] is not None:
        item["box"] = [round(row[k], 4) for k in ("box_x0", "box_y0", "box_x1", "box_y1")]
    return item


# ---------------------------------------------------------------------- vectors


class Vectors:
    """Feature vectors of every described photo, loaded once per library revision."""

    def __init__(self):
        self._lock = threading.Lock()
        self._key = None
        self.ids = np.empty(0, np.int64)
        self.whole = np.empty((0, 0), np.float32)
        self.subject = np.empty((0, 0), np.float32)
        self.model = None

    def load(self):
        with self._lock:
            with database() as db:
                revision = db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0]
                key = (str(library_root()), revision)
                if key == self._key:
                    return self
                rows = db.execute(
                    "SELECT photo_id, model, whole, subject FROM features ORDER BY photo_id"
                ).fetchall()
            models = {row["model"] for row in rows}
            model = max(models, key=lambda m: sum(row["model"] == m for row in rows)) if models else None
            rows = [row for row in rows if row["model"] == model]
            self.ids = np.array([row["photo_id"] for row in rows], np.int64)
            if rows:
                self.whole = np.stack([np.frombuffer(row["whole"], np.float16) for row in rows]).astype(np.float32)
                self.subject = np.stack([np.frombuffer(row["subject"], np.float16) for row in rows]).astype(np.float32)
            else:
                self.whole = self.subject = np.empty((0, 0), np.float32)
            self.model, self._key = model, key
            return self


vectors = Vectors()


# ------------------------------------------------------------------------- jobs


class Job:
    """One background crunch. At most one runs at a time."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self._state = {"running": False}

    def state(self) -> dict:
        with self._lock:
            state = dict(self._state)
        if state.get("running") and state.get("stage_started"):
            elapsed = max(time.time() - state["stage_started"], 1e-3)
            done, total = state.get("done", 0), state.get("total", 0)
            state["rate"] = round(done / elapsed, 1)
            state["eta_seconds"] = round((total - done) / (done / elapsed)) if done and total > done else None
        return state

    def _set(self, **changes):
        with self._lock:
            self._state.update(changes)

    def stage(self, name, total=0):
        self._set(stage=name, done=0, total=total, stage_started=time.time())

    def advance(self, done, total=None):
        with self._lock:
            self._state["done"] = done
            if total is not None:
                self._state["total"] = total

    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def cancel(self):
        self._cancel.set()

    def start(self, work, label):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise Busy("The library is already crunching photos. Wait for it to finish or cancel it.")
            self._cancel.clear()
            self._state = {
                "running": True,
                "label": label,
                "stage": "starting",
                "done": 0,
                "total": 0,
                "started": time.time(),
                "stage_started": time.time(),
                "error": None,
                "summary": None,
            }

            def run():
                summary, error = None, None
                try:
                    summary = work(self)
                except vision_math.SearchCancelled:
                    pass  # Keep the existing groups; stage below records cancellation.
                except LibraryError as exc:
                    error = str(exc)
                except vision.VisionError as exc:
                    error = str(exc)
                except Exception as exc:  # noqa: BLE001 - reported to the user; the service keeps running.
                    error = f"The crunch stopped on an unexpected error ({type(exc).__name__})."
                self._set(
                    running=False,
                    stage="cancelled" if self.cancelled() and not error else ("failed" if error else "finished"),
                    error=error,
                    summary=summary,
                    finished=time.time(),
                )

            self._thread = threading.Thread(target=run, daemon=True, name="library-crunch")
            self._thread.start()

    def wait(self, timeout=None):
        thread = self._thread
        if thread is not None:
            thread.join(timeout)


job = Job()


# ------------------------------------------------------------------------- scan


def _walk(folder: Path):
    """Yield (path, size, mtime_ns) of image files below ``folder``; no hidden or linked dirs.

    The library's own storage is skipped wherever it is, so its previews are never indexed.
    """
    own = str(library_root())
    stack = [folder]
    while stack:
        current = stack.pop()
        if str(current) == own:
            continue
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in SUFFIXES:
                    stat = entry.stat(follow_symlinks=False)
                    yield entry.path, stat.st_size, stat.st_mtime_ns
            except OSError:
                continue


def _scan(current: Job) -> dict:
    """Bring the photo table in line with the folders on disk. Returns counts."""
    counts = {"new": 0, "changed": 0, "gone": 0}
    with database() as db:
        folders = db.execute("SELECT id, path FROM folders").fetchall()
    for folder in folders:
        current.stage("scan")
        seen: dict[str, tuple[int, int]] = {}
        for path, size, mtime in _walk(Path(folder["path"])):
            seen[path] = (size, mtime)
            if len(seen) % 500 == 0:
                current.advance(len(seen))
                if current.cancelled():
                    return counts
        with database() as db:
            known = {
                row["path"]: (row["id"], row["bytes"], row["mtime_ns"])
                for row in db.execute(
                    "SELECT id, path, bytes, mtime_ns FROM photos WHERE folder_id = ?", (folder["id"],)
                )
            }
            total = db.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
            now = time.time()
            for path, (size, mtime) in seen.items():
                if path not in known:
                    if total >= MAX_PHOTOS:
                        raise LibraryError(f"The library holds at most {MAX_PHOTOS:,} photos.")
                    db.execute(
                        "INSERT OR IGNORE INTO photos(folder_id, path, name, bytes, mtime_ns, added_at)"
                        " VALUES (?, ?, ?, ?, ?, ?)",
                        (folder["id"], path, Path(path).name, size, mtime, now),
                    )
                    counts["new"] += 1
                    total += 1
                elif known[path][1:] != (size, mtime):
                    db.execute(
                        "UPDATE photos SET state='pending', error=NULL, bytes=?, mtime_ns=? WHERE id=?",
                        (size, mtime, known[path][0]),
                    )
                    db.execute("DELETE FROM features WHERE photo_id=?", (known[path][0],))
                    counts["changed"] += 1
            gone = [photo_id for path, (photo_id, *_rest) in known.items() if path not in seen]
            for photo_id in gone:
                db.execute("DELETE FROM photos WHERE id=?", (photo_id,))
                preview_path(photo_id).unlink(missing_ok=True)
            counts["gone"] += len(gone)
            if counts["changed"] or gone:
                _bump(db)
    return counts


# ------------------------------------------------------------------------- read


def _read(current: Job) -> dict:
    with database() as db:
        pending = db.execute("SELECT id, path FROM photos WHERE state='pending' ORDER BY id").fetchall()
    counts = {"read": 0, "failed": 0}
    if not pending:
        return counts
    current.stage("read", len(pending))
    context = multiprocessing.get_context("spawn")  # Never fork a threaded server process.
    workers = min(worker_count(), len(pending))
    queue = iter(pending)
    done = 0
    results: list[tuple[int, dict]] = []

    def flush():
        if not results:
            return
        with database() as db:
            for photo_id, facts in results:
                if "error" in facts:
                    db.execute(
                        "UPDATE photos SET state='failed', error=?, sha256=? WHERE id=?",
                        (facts["error"], facts.get("sha256"), photo_id),
                    )
                else:
                    db.execute(
                        "UPDATE photos SET state='ready', error=NULL, sha256=?, bytes=?, width=?, height=?,"
                        " format=?, taken_at=?, camera=?, focal_35mm=?, blur_px=?, blur_map=?, brightness=?,"
                        " clipped=? WHERE id=?",
                        (
                            facts["sha256"], facts["bytes"], facts["width"], facts["height"], facts["format"],
                            facts["taken_at"], facts["camera"], facts["focal_35mm"], facts["blur_px"],
                            facts["blur_map"], facts["brightness"], facts["clipped"], photo_id,
                        ),
                    )  # fmt: skip
                db.execute("DELETE FROM features WHERE photo_id=?", (photo_id,))
            _bump(db)
        results.clear()

    with _single_threaded_children():
        pool = ProcessPoolExecutor(max_workers=workers, mp_context=context, initializer=_quiet_worker)
        running = {}

        def submit():
            row = next(queue, None)
            if row is None:
                return False
            running[pool.submit(read_photo, row["path"], str(preview_path(row["id"])))] = row["id"]
            return True

        stalled = False
        try:
            for _ in range(workers * 2):
                if not submit():
                    break
            while running:
                finished, _ = wait(running, timeout=READ_STALL_SECONDS, return_when=FIRST_COMPLETED)
                if not finished:
                    # No reader has returned for minutes: one decode takes well under a
                    # second and a HEIC child is stopped after 60 s. Waiting on would hold
                    # the library, and Cancel, for ever.
                    stalled = True
                    raise LibraryError(
                        "The photo readers stopped responding. Crunch again; if it repeats,"
                        " set PICAD_LIBRARY_WORKERS to a smaller number."
                    )
                for future in finished:
                    photo_id = running.pop(future)
                    try:
                        facts = future.result()
                    except BrokenProcessPool:
                        # A reader process died (out of memory, or killed). Which photo it
                        # held is unknown, so none is marked as failed; the rest stay pending.
                        raise LibraryError(
                            "The photo readers stopped unexpectedly. Crunch again; if it repeats,"
                            " set PICAD_LIBRARY_WORKERS to a smaller number."
                        ) from None
                    except Exception:  # noqa: BLE001 - one unreadable photo must not stop the rest.
                        facts = {"error": "The image could not be decoded."}
                    results.append((photo_id, facts))
                    counts["failed" if "error" in facts else "read"] += 1
                    done += 1
                    if not current.cancelled():
                        submit()
                current.advance(done)
                if len(results) >= 200:
                    flush()
        finally:
            for future in running:
                future.cancel()
            if stalled:
                # Stop the readers themselves; a normal shutdown would wait for them.
                for process in list((getattr(pool, "_processes", None) or {}).values()):
                    process.kill()
            pool.shutdown(wait=not stalled, cancel_futures=True)
            flush()
    return counts


# --------------------------------------------------------------------- features


def _features(current: Job) -> dict:
    def waiting(db):
        return [
            row["id"]
            for row in db.execute(
                "SELECT p.id FROM photos p LEFT JOIN features f ON f.photo_id = p.id"
                " WHERE p.state='ready' AND f.photo_id IS NULL ORDER BY p.id"
            )
        ]

    with database() as db:
        todo = waiting(db)
    if not todo:
        return {"described": 0}  # Nothing new: the model is not even started.
    current.stage("model")
    state = vision.status()
    if not state["available"]:
        return {"described": 0, "skipped": state["reason"]}
    model = vision.current_model()
    with database() as db:
        # Features from another model cannot be compared with this one's: start over.
        stale = db.execute("SELECT COUNT(*) FROM features WHERE model != ?", (model,)).fetchone()[0]
        if stale:
            db.execute("DELETE FROM features WHERE model != ?", (model,))
            _bump(db)
            todo = waiting(db)
    counts = {"described": 0, "model": vision.model_info(model)["name"]}
    current.stage("features", len(todo))
    workdir = library_root() / "tmp"
    for start in range(0, len(todo), FEATURE_BATCH):
        if current.cancelled():
            break
        batch = todo[start : start + FEATURE_BATCH]
        arrays, _ = vision.engine.embed([preview_path(i) for i in batch], workdir)
        grid = math.isqrt(arrays["mask"].shape[1] * 8)
        with database() as db:
            marks = ",".join("?" * len(batch))
            maps = dict(db.execute(f"SELECT id, blur_map FROM photos WHERE id IN ({marks})", batch).fetchall())
            for index, photo_id in enumerate(batch):
                if not arrays["ok"][index]:
                    continue
                box = arrays["box"][index]
                box = [None] * 4 if np.isnan(box).any() else [float(v) for v in box]
                region = np.unpackbits(arrays["mask"][index])[: grid * grid].reshape(grid, grid).astype(bool)
                on_subject = subject_blur(maps.get(photo_id), region) if region.any() else None
                db.execute(
                    "INSERT OR REPLACE INTO features VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        photo_id, model,
                        arrays["whole"][index].astype(np.float16).tobytes(),
                        arrays["subject"][index].astype(np.float16).tobytes(),
                        arrays["mask"][index].tobytes(), grid, *box, on_subject,
                    ),
                )  # fmt: skip
                counts["described"] += 1
            _bump(db)
        current.advance(min(start + FEATURE_BATCH, len(todo)))
    return counts


# --------------------------------------------------------------------- organize


def organize(current: Job | None = None) -> dict:
    """Recompute copies, look-alikes, groups, detail and best shots for the whole library."""
    if current:
        current.stage("organize")

    def check_cancelled():
        if current and current.cancelled():
            raise vision_math.SearchCancelled()

    check_cancelled()
    with database() as db:
        photos = db.execute(
            "SELECT p.id, p.sha256, p.width, p.height, COALESCE(f.subject_blur_px, p.blur_px) AS blur_px,"
            " f.box_x0, f.box_y0, f.box_x1, f.box_y1"
            " FROM photos p LEFT JOIN features f ON f.photo_id = p.id WHERE p.state='ready' ORDER BY p.id"
        ).fetchall()
    ids = [row["id"] for row in photos]
    position = {photo_id: index for index, photo_id in enumerate(ids)}
    parent = list(range(len(ids)))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def join(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    # Exact copies: the same bytes under different names or in different folders.
    by_hash: dict[str, int] = {}
    exact = set()
    for index, row in enumerate(photos):
        first = by_hash.setdefault(row["sha256"], index)
        if first != index:
            join(first, index)
            exact.update((first, index))

    # Detail: how many blur widths span the subject (or half the frame without one).
    detail = {}
    for row in photos:
        if not row["blur_px"]:
            continue
        if row["box_x0"] is None:
            span = 0.5 * max(row["width"], row["height"])
        else:
            span = max((row["box_x1"] - row["box_x0"]) * row["width"], (row["box_y1"] - row["box_y0"]) * row["height"])
        detail[row["id"]] = span / row["blur_px"]

    groups = np.arange(len(ids))
    loaded = vectors.load()
    counts = {"copies": 0, "lookalikes": 0, "groups": 0}
    if loaded.ids.size >= 2:
        info = vision.model_info(loaded.model)
        rows = np.array([position[i] for i in loaded.ids.tolist() if i in position], np.int64)
        keep = np.array([i in position for i in loaded.ids.tolist()])
        if current:
            current.stage("organize", int(2 * keep.sum()))
        steps = int(keep.sum())
        near, near_cos = vision_math.neighbours(
            loaded.whole[keep], NEIGHBOURS, progress=(lambda d, t: current.advance(d)) if current else None,
            cancelled=current.cancelled if current else None,
        )
        for i, j in zip(*np.nonzero(near_cos >= info["lookalike"]), strict=True):
            a, b = int(rows[i]), int(rows[near[i, j]])
            if find(a) != find(b):
                join(a, b)
        alike, alike_cos = vision_math.neighbours(
            loaded.subject[keep], NEIGHBOURS, progress=(lambda d, t: current.advance(steps + d)) if current else None,
            cancelled=current.cancelled if current else None,
        )
        check_cancelled()
        labels = vision_math.linked_groups(alike, alike_cos, info["group"])
        labels = vision_math.split_chained(loaded.subject[keep], labels, info["split"])
        groups[rows] = rows[labels]

    check_cancelled()

    dup_root = [find(index) for index in range(len(ids))]
    dup_sizes: dict[int, int] = {}
    for root in dup_root:
        dup_sizes[root] = dup_sizes.get(root, 0) + 1
    group_sizes: dict[int, int] = {}
    for label in groups.tolist():
        group_sizes[label] = group_sizes.get(label, 0) + 1

    best: dict[int, int] = {}
    for index, photo_id in enumerate(ids):
        label = int(groups[index])
        if group_sizes[label] < 2:
            continue
        score = detail.get(photo_id, -1.0)
        if label not in best or score > detail.get(ids[best[label]], -1.0):
            best[label] = index
    winners = set(best.values())

    with database() as db:
        check_cancelled()
        db.execute("UPDATE photos SET group_id=NULL, dup_set=NULL, dup_kind=NULL, best=0, detail=NULL")
        for index, photo_id in enumerate(ids):
            if index % 256 == 0:
                check_cancelled()  # Closing an uncommitted connection rolls back all regrouping.
            in_set = dup_sizes[dup_root[index]] > 1
            label = int(groups[index])
            db.execute(
                "UPDATE photos SET detail=?, group_id=?, dup_set=?, dup_kind=?, best=? WHERE id=?",
                (
                    detail.get(photo_id),
                    ids[label] if group_sizes[label] > 1 else None,
                    ids[dup_root[index]] if in_set else None,
                    ("exact" if index in exact else "lookalike") if in_set else None,
                    int(index in winners),
                    photo_id,
                ),
            )
        check_cancelled()
        counts["copies"] = len(exact)
        counts["lookalikes"] = sum(1 for i in range(len(ids)) if dup_sizes[dup_root[i]] > 1 and i not in exact)
        counts["groups"] = sum(1 for size in group_sizes.values() if size > 1)
    return counts


def crunch(current: Job) -> dict:
    """Scan, read, describe and organize. The work of every library job.

    The vision model is optional: when it is missing or cannot start, the photos are
    still read and organized by exact copies, and the reason is reported.
    """
    summary = {"scan": _scan(current)}
    if not current.cancelled():
        summary["read"] = _read(current)
    if not current.cancelled():
        try:
            summary["features"] = _features(current)
        except vision.VisionError as exc:
            summary["features"] = {"described": 0, "skipped": str(exc)}
    if not current.cancelled():
        summary["organize"] = organize(current)
    return summary


def start_crunch(label="Crunching photos"):
    job.start(crunch, label)


def start_reorganize():
    """Regroup after photos were removed (no scanning, reading or model work)."""
    job.start(lambda current: {"organize": organize(current)}, "Reorganizing")


# ---------------------------------------------------------------------- folders


def home() -> Path:
    return Path.home()


def browse(path: str | None) -> dict:
    """List the folders inside ``path`` (default: the home folder) for the folder picker."""
    try:
        folder = Path(path).expanduser().resolve(strict=True) if path else home().resolve()
    except (OSError, RuntimeError, ValueError):
        raise LibraryError("That folder does not exist.") from None
    if not folder.is_dir():
        raise LibraryError("That is not a folder.")
    children, photos = [], 0
    try:
        entries = sorted(os.scandir(folder), key=lambda entry: entry.name.lower())
    except OSError:
        raise LibraryError("That folder cannot be opened.") from None
    for entry in entries:
        if entry.name.startswith("."):
            continue
        try:
            if entry.is_dir(follow_symlinks=False):
                children.append({"name": entry.name, "path": entry.path})
            elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in SUFFIXES:
                photos += 1
        except OSError:
            continue
    shortcuts = []
    for name in ("Pictures", "Downloads", "Desktop", "Documents"):
        candidate = home() / name
        if candidate.is_dir():
            shortcuts.append({"name": name, "path": str(candidate)})
    return {
        "path": str(folder),
        "name": folder.name or str(folder),
        "parent": None if folder.parent == folder else str(folder.parent),
        "folders": children[:2000],
        "photos": photos,
        "home": str(home()),
        "shortcuts": shortcuts,
    }


def add_folder(path: str) -> dict:
    try:
        folder = Path(path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise LibraryError("That folder does not exist.") from None
    if not folder.is_dir():
        raise LibraryError("That is not a folder.")
    root = library_root()
    if folder == root or root in folder.parents:
        raise LibraryError("The library's own storage folder cannot be added.")
    with database() as db:
        for row in db.execute("SELECT path FROM folders"):
            known = Path(row["path"])
            if known == folder or known in folder.parents:
                raise LibraryError(f"{known} is already in the library.")
            if folder in known.parents:
                raise LibraryError(f"{known}, inside that folder, is already in the library. Remove it first.")
        cursor = db.execute("INSERT INTO folders(path, added_at) VALUES (?, ?)", (str(folder), time.time()))
        return {"id": cursor.lastrowid, "path": str(folder)}


def remove_folder(folder_id: int):
    with database() as db:
        row = db.execute("SELECT id FROM folders WHERE id=?", (folder_id,)).fetchone()
        if row is None:
            raise LibraryError("Folder not found.")
        photo_ids = [r["id"] for r in db.execute("SELECT id FROM photos WHERE folder_id=?", (folder_id,))]
        db.execute("DELETE FROM folders WHERE id=?", (folder_id,))
        _bump(db)
    for photo_id in photo_ids:
        preview_path(photo_id).unlink(missing_ok=True)


# ---------------------------------------------------------------------- uploads

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")
_upload_lock = threading.Lock()


def add_upload(name: str, data: bytes) -> dict:
    """Keep a picture sent through the browser. Returns its id; identical bytes are stored once."""
    if not data:
        raise LibraryError("Choose a PNG, JPEG, WebP, HEIC or AVIF image.")
    if len(data) > MAX_BYTES:
        raise LibraryError("Choose an image under 32 MiB.")
    suffix = Path(name or "").suffix.lower()
    if suffix not in SUFFIXES:
        raise LibraryError("Choose a PNG, JPEG, WebP, HEIC or AVIF image.")
    digest = hashlib.sha256(data).hexdigest()
    clean = _SAFE_NAME.sub("_", Path(name).name).strip(" .")[:120] or f"photo{suffix}"
    target = library_root() / "uploads" / digest[:2] / digest / clean
    # One upload at a time: the browser sends several at once, and two identical files
    # must not both pass the "already stored?" check.
    with _upload_lock, database() as db:
        row = db.execute(
            "SELECT id FROM photos WHERE folder_id IS NULL AND sha256=? LIMIT 1", (digest,)
        ).fetchone()
        if row:
            return {"id": row["id"], "duplicate": True}
        if db.execute("SELECT COUNT(*) FROM photos").fetchone()[0] >= MAX_PHOTOS:
            raise LibraryError(f"The library holds at most {MAX_PHOTOS:,} photos.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o600)
        stat = target.stat()
        cursor = db.execute(
            "INSERT INTO photos(folder_id, path, name, bytes, mtime_ns, sha256, added_at)"
            " VALUES (NULL, ?, ?, ?, ?, ?, ?)",
            (str(target), clean, stat.st_size, stat.st_mtime_ns, digest, time.time()),
        )
        return {"id": cursor.lastrowid, "duplicate": False}


# ---------------------------------------------------------------------- queries


def summary() -> dict:
    with database() as db:
        row = db.execute(
            "SELECT COUNT(*) AS photos, COALESCE(SUM(state='ready'), 0) AS ready,"
            " COALESCE(SUM(state='pending'), 0) AS pending, COALESCE(SUM(state='failed'), 0) AS failed,"
            " COALESCE(SUM(bytes), 0) AS bytes, COUNT(DISTINCT group_id) AS groups,"
            " COALESCE(SUM(dup_set IS NOT NULL AND dup_set != id), 0) AS spare,"
            " COALESCE(SUM(best), 0) AS best FROM photos"
        ).fetchone()
        described = db.execute("SELECT COUNT(*) FROM features").fetchone()[0]
        folders = [
            {"id": f["id"], "path": f["path"], "photos": f["photos"]}
            for f in db.execute(
                "SELECT f.id, f.path, COUNT(p.id) AS photos FROM folders f"
                " LEFT JOIN photos p ON p.folder_id = f.id GROUP BY f.id ORDER BY f.path"
            )
        ]
        uploads = db.execute("SELECT COUNT(*) FROM photos WHERE folder_id IS NULL").fetchone()[0]
    return {**dict(row), "described": described, "folders": folders, "uploads": uploads}


def list_photos(view="all", sort="added", query="", offset=0, limit=200, group=None, dup=None) -> dict:
    if view not in VIEWS or sort not in SORTS:
        raise LibraryError("Unknown view or sort order.")
    where, parameters = [VIEWS[view]], []
    if view != "failed":
        where.append("p.state != 'failed'")
    if query:
        where.append("p.name LIKE ? ESCAPE '\\'")
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        parameters.append(f"%{escaped}%")
    if group is not None:
        where.append("p.group_id = ?")
        parameters.append(group)
    if dup is not None:
        where.append("p.dup_set = ?")
        parameters.append(dup)
    clause = " AND ".join(where)
    order = SORTS[sort]
    if view == "duplicates" and dup is None:
        order = "p.dup_set, p.id"
    with database() as db:
        total = db.execute(f"SELECT COUNT(*) FROM photos p WHERE {clause}", parameters).fetchone()[0]
        rows = db.execute(
            "SELECT p.*, f.box_x0, f.box_y0, f.box_x1, f.box_y1, f.subject_blur_px FROM photos p"
            f" LEFT JOIN features f ON f.photo_id = p.id WHERE {clause} ORDER BY {order} LIMIT ? OFFSET ?",
            [*parameters, max(1, min(limit, 500)), max(0, offset)],
        ).fetchall()
    return {"total": total, "offset": offset, "photos": [_photo_row(row) for row in rows]}


def list_groups(offset=0, limit=60) -> dict:
    with database() as db:
        total = db.execute("SELECT COUNT(DISTINCT group_id) FROM photos WHERE group_id IS NOT NULL").fetchone()[0]
        groups = db.execute(
            "SELECT group_id, COUNT(*) AS size FROM photos WHERE group_id IS NOT NULL"
            " GROUP BY group_id ORDER BY size DESC, group_id LIMIT ? OFFSET ?",
            (max(1, min(limit, 200)), max(0, offset)),
        ).fetchall()
        result = []
        for group in groups:
            members = db.execute(
                "SELECT id, name, best FROM photos WHERE group_id=? ORDER BY best DESC, detail DESC, id LIMIT 6",
                (group["group_id"],),
            ).fetchall()
            result.append(
                {
                    "id": group["group_id"],
                    "size": group["size"],
                    "cover": members[0]["id"],
                    "name": members[0]["name"],
                    "members": [m["id"] for m in members],
                }
            )
    return {"total": total, "offset": offset, "groups": result}


def get_photo(photo_id: int) -> dict:
    with database() as db:
        row = db.execute(
            "SELECT p.*, f.model, f.mask, f.grid, f.box_x0, f.box_y0, f.box_x1, f.box_y1, f.subject_blur_px,"
            " fo.path AS folder"
            " FROM photos p LEFT JOIN features f ON f.photo_id = p.id"
            " LEFT JOIN folders fo ON fo.id = p.folder_id WHERE p.id=?",
            (photo_id,),
        ).fetchone()
        if row is None:
            raise LibraryError("Photo not found.")
        group_size = dup_size = 0
        if row["group_id"] is not None:
            group_size = db.execute("SELECT COUNT(*) FROM photos WHERE group_id=?", (row["group_id"],)).fetchone()[0]
        if row["dup_set"] is not None:
            dup_size = db.execute("SELECT COUNT(*) FROM photos WHERE dup_set=?", (row["dup_set"],)).fetchone()[0]
    item = _photo_row(row)
    item.update(
        path=row["path"] if row["folder_id"] is not None else None,
        source="folder" if row["folder_id"] is not None else "upload",
        bytes=row["bytes"],
        format=row["format"],
        camera=row["camera"],
        focal_35mm=row["focal_35mm"],
        brightness=None if row["brightness"] is None else round(row["brightness"], 1),
        clipped=None if row["clipped"] is None else round(row["clipped"], 4),
        error=row["error"],
        group_size=group_size,
        dup_size=dup_size,
        model=vision.model_info(row["model"])["name"] if row["model"] else None,
    )
    if row["mask"] is not None:
        grid = row["grid"]
        bits = np.unpackbits(np.frombuffer(row["mask"], np.uint8))[: grid * grid].reshape(grid, grid)
        item["subject"] = {
            "grid": grid,
            "rows": ["".join("1" if cell else "0" for cell in line) for line in bits],
            "share": round(float(bits.mean()), 4),
        }
    return item


def original_file(photo_id: int) -> tuple[Path, str]:
    """The photo's original file and name, refused if it changed or vanished since indexing."""
    with database() as db:
        row = db.execute("SELECT path, name, bytes, mtime_ns FROM photos WHERE id=?", (photo_id,)).fetchone()
    if row is None:
        raise LibraryError("Photo not found.")
    path = Path(row["path"])
    try:
        stat = path.stat()
    except OSError:
        raise LibraryError("The original file is no longer there. Rescan the library.") from None
    if (stat.st_size, stat.st_mtime_ns) != (row["bytes"], row["mtime_ns"]):
        raise LibraryError("The original file has changed since it was indexed. Rescan the library.")
    return path, row["name"]


def remove_photo(photo_id: int):
    with database() as db:
        row = db.execute("SELECT path, folder_id FROM photos WHERE id=?", (photo_id,)).fetchone()
        if row is None:
            raise LibraryError("Photo not found.")
        if row["folder_id"] is not None:
            raise LibraryError(
                "This photo comes from an added folder. Remove the folder from the library,"
                " or move the file out of it and rescan."
            )
        db.execute("DELETE FROM photos WHERE id=?", (photo_id,))
        _bump(db)
    preview_path(photo_id).unlink(missing_ok=True)
    stored = Path(row["path"])
    uploads = library_root() / "uploads"
    if uploads in stored.parents:  # Only ever delete the library's own stored copy.
        shutil.rmtree(stored.parent, ignore_errors=True)


def clear():
    """Forget everything the library derived. Originals in added folders are untouched."""
    root = library_root()
    with database() as db:
        db.execute("DELETE FROM features")
        db.execute("DELETE FROM photos")
        db.execute("DELETE FROM folders")
        _bump(db)
    for name in ("previews", "uploads", "tmp"):
        shutil.rmtree(root / name, ignore_errors=True)


def _rows_for(ids: list[int], scores: list[float]) -> list[dict]:
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    with database() as db:
        rows = {
            row["id"]: row
            for row in db.execute(
                "SELECT p.*, f.box_x0, f.box_y0, f.box_x1, f.box_y1, f.subject_blur_px FROM photos p"
                f" LEFT JOIN features f ON f.photo_id = p.id WHERE p.id IN ({marks})",
                ids,
            )
        }
    found = []
    for photo_id, score in zip(ids, scores, strict=True):
        if photo_id in rows:
            found.append({**_photo_row(rows[photo_id]), "score": round(float(score), 4)})
    return found


def similar(photo_id: int, limit=60) -> dict:
    """Photos whose subject most resembles this photo's, best first (cosine of subject vectors)."""
    loaded = vectors.load()
    where = np.flatnonzero(loaded.ids == photo_id)
    if not where.size:
        raise LibraryError("This photo has no vision features yet. Install the vision model and crunch again.")
    index = int(where[0])
    chosen, scores = vision_math.top_matches(loaded.subject, loaded.subject[index], min(limit, 200) + 1)
    pairs = [(int(loaded.ids[i]), float(s)) for i, s in zip(chosen, scores, strict=True) if i != index]
    pairs = pairs[: min(limit, 200)]
    return {"photos": _rows_for([p for p, _ in pairs], [s for _, s in pairs]), "model": vision.model_info(loaded.model)["name"]}


def search_by_picture(name: str, data: bytes, limit=60) -> dict:
    """Photos resembling a picture that is not in the library. Nothing about it is kept."""
    loaded = vectors.load()
    if not loaded.ids.size:
        raise LibraryError("No photo has vision features yet. Install the vision model and crunch first.")
    if vision.current_model() != loaded.model:
        raise LibraryError("The library was described by another model. Crunch it again first.")
    workdir = library_root() / "tmp"
    workdir.mkdir(parents=True, exist_ok=True)
    stem = hashlib.sha256(data).hexdigest()[:24]
    source, preview = workdir / f"query-{stem}{Path(name or '').suffix.lower()}", workdir / f"query-{stem}.jpg"
    try:
        if not data or len(data) > MAX_BYTES:
            raise LibraryError("Choose an image under 32 MiB.")
        source.write_bytes(data)
        facts = read_photo(str(source), str(preview))
        if "error" in facts:
            raise LibraryError(facts["error"])
        arrays, failed = vision.engine.embed([preview], workdir)
        if failed or not arrays["ok"][0]:
            raise LibraryError("The picture could not be described.")
        chosen, scores = vision_math.top_matches(loaded.subject, arrays["subject"][0], min(limit, 200))
    finally:
        source.unlink(missing_ok=True)
        preview.unlink(missing_ok=True)
    return {
        "photos": _rows_for([int(loaded.ids[i]) for i in chosen], [float(s) for s in scores]),
        "model": vision.model_info(loaded.model)["name"],
    }


EXPORT_COLUMNS = (
    "id", "name", "path", "source", "state", "error", "sha256", "bytes", "format", "width", "height",
    "taken_at", "camera", "focal_35mm", "blur_px", "subject_blur_px", "brightness", "clipped", "detail",
    "group_id", "best", "dup_set", "dup_kind",
    "subject_x0", "subject_y0", "subject_x1", "subject_y1",
)  # fmt: skip


def export_rows():
    """Yield the catalogue as dictionaries, one per photo, in id order."""
    with database() as db:
        rows = db.execute(
            "SELECT p.*, f.box_x0, f.box_y0, f.box_x1, f.box_y1, f.subject_blur_px FROM photos p"
            " LEFT JOIN features f ON f.photo_id = p.id ORDER BY p.id"
        ).fetchall()
    known = set(rows[0].keys()) if rows else set()
    for row in rows:
        yield {
            **{key: row[key] for key in EXPORT_COLUMNS if key in known},
            "path": row["path"] if row["folder_id"] is not None else "",
            "source": "folder" if row["folder_id"] is not None else "upload",
            "subject_x0": row["box_x0"],
            "subject_y0": row["box_y0"],
            "subject_x1": row["box_x1"],
            "subject_y1": row["box_y1"],
        }


def _csv_safe(value):
    """Spreadsheets run a cell that starts with = + - or @ as a formula: quote it as text."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return "" if value is None else value


def export_csv() -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in export_rows():
        writer.writerow({key: _csv_safe(row.get(key)) for key in EXPORT_COLUMNS})
    return buffer.getvalue()


def export_json() -> str:
    return json.dumps({"schema": SCHEMA, "photos": list(export_rows())}, ensure_ascii=False)
