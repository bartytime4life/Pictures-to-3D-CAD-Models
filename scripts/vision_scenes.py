"""Rendered photographs of known flat parts, with exact subject masks, for the vision checks.

Each scene is one of fourteen flat parts lying on one of eight procedural backgrounds,
seen by a tilted camera, with uneven light, a soft contact shadow, optical blur, sensor
noise and JPEG compression. The part's identity and its exact pixel mask are returned
with the photo, so subject detection and same-part matching can be scored.

These are drawings of plates and gaskets, not photographs. They establish that the
pipeline separates and matches *these* shapes under *these* variations; they say nothing
about real cameras, real materials or parts that look alike. This module shares no code
with the workbench or the vision engine.
"""

from __future__ import annotations

import io
import math

import cv2
import numpy as np
from PIL import Image
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

SIZE = (1280, 960)  # Photo width and height in pixels.
PIXELS_PER_MM = 6.0  # Drawing scale of the flat scene before the camera views it.


def _rounded(width, height, radius):
    return box(-width / 2 + radius, -height / 2 + radius, width / 2 - radius, height / 2 - radius).buffer(
        radius, 32
    )


def _holes(shape, centres, diameter):
    return shape.difference(unary_union([Point(x, y).buffer(diameter / 2, 32) for x, y in centres]))


def _regular(sides, radius, turn=0.0):
    return Polygon(
        [
            (radius * math.cos(turn + 2 * math.pi * k / sides), radius * math.sin(turn + 2 * math.pi * k / sides))
            for k in range(sides)
        ]
    )


def _gear(teeth, root, tip):
    points = []
    for k in range(teeth * 4):
        r = tip if k % 4 in (1, 2) else root
        a = 2 * math.pi * (k + 0.5) / (teeth * 4)
        points.append((r * math.cos(a), r * math.sin(a)))
    return Polygon(points)


def parts():
    """Name -> (shapely polygon in millimetres, saved sRGB colour). Fourteen distinct parts."""
    ring = [(28 * math.cos(a), 28 * math.sin(a)) for a in np.arange(6) * math.pi / 3]
    plate = _holes(_rounded(120, 70, 8), [(x, y) for x in (-48, 48) for y in (-25, 25)], 6)
    return {
        "mounting-plate": (plate.difference(Point(-18, 0).buffer(11, 48)), (52, 54, 60)),
        "l-bracket": (
            _holes(unary_union([box(-45, -45, 45, -15), box(-45, -45, -15, 45)]), [(-30, 30), (30, -30), (-30, -30)], 7),
            (150, 155, 160),
        ),
        "ring-gasket": (Point(0, 0).buffer(40, 64).difference(Point(0, 0).buffer(26, 64)), (30, 30, 32)),
        "flange": (_holes(Point(0, 0).buffer(40, 64), ring, 7).difference(Point(0, 0).buffer(14, 48)), (176, 132, 72)),
        "gusset": (_holes(Polygon([(-45, -40), (45, -40), (-45, 40)]).buffer(4, 16), [(-32, -27), (20, -27), (-32, 12)], 7), (66, 92, 140)),
        "hex-plate": (_regular(6, 42).difference(Point(0, 0).buffer(15, 48)), (112, 116, 118)),
        "slot-plate": (
            _rounded(110, 44, 6).difference(box(-36, -5, 36, 5).buffer(5, 16)),
            (196, 60, 48),
        ),
        "cross": (unary_union([box(-48, -13, 48, 13), box(-13, -48, 13, 48)]).buffer(3, 16), (226, 196, 60)),
        "u-clip": (box(-40, -45, 40, 45).difference(box(-18, -22, 18, 46)).buffer(3, 16), (60, 130, 84)),
        "oval-gasket": (
            affinity.scale(Point(0, 0).buffer(1, 64), 55, 30).difference(affinity.scale(Point(0, 0).buffer(1, 64), 40, 16)),
            (120, 42, 42),
        ),
        "d-plate": (_holes(Point(0, 0).buffer(42, 64).intersection(box(-42, -42, 20, 42)), [(-16, 22), (-16, -22)], 8), (232, 232, 226)),
        "gear": (_gear(14, 34, 43).difference(Point(0, 0).buffer(9, 32)), (140, 110, 60)),
        "t-bracket": (
            _holes(unary_union([box(-50, 18, 50, 44), box(-13, -46, 13, 20)]).buffer(2, 16), [(-36, 31), (36, 31), (0, -34)], 7),
            (88, 70, 120),
        ),
        "star-washer": (
            Polygon(
                [
                    ((40 if k % 2 == 0 else 24) * math.cos(math.pi * k / 8), (40 if k % 2 == 0 else 24) * math.sin(math.pi * k / 8))
                    for k in range(16)
                ]
            ).difference(Point(0, 0).buffer(10, 32)),
            (200, 200, 205),
        ),
    }


def _noise(rng, shape, scale):
    """Smooth random field in about -1..1 with features `scale` pixels across."""
    field = cv2.GaussianBlur(rng.standard_normal(shape).astype(np.float32), (0, 0), scale)
    return field / (np.abs(field).max() + 1e-9)


BACKGROUNDS = ("paper", "desk", "cutting-mat", "wood", "fabric", "concrete", "dark-table", "kraft")


def background(kind, rng, shape):
    """A procedural surface as float32 RGB, 0..255."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if kind == "paper":
        base = np.full((h, w, 3), (238, 238, 234), np.float32) + 2 * _noise(rng, (h, w), 1.5)[..., None]
    elif kind == "desk":
        base = np.full((h, w, 3), (168, 170, 172), np.float32) + 6 * _noise(rng, (h, w), 30)[..., None]
    elif kind == "cutting-mat":
        base = np.full((h, w, 3), (38, 104, 74), np.float32)
        step = 10 * PIXELS_PER_MM
        lines = (np.minimum(xx % step, yy % step) < 1.5).astype(np.float32)
        base += lines[..., None] * np.array((150, 130, 120), np.float32)
    elif kind == "wood":
        grain = np.sin(yy / 5.5 + 14 * _noise(rng, (h, w), 60)) * 0.5 + 0.5
        base = (146, 104, 66) + grain[..., None] * np.array((44, 36, 26), np.float32)
        base = base.astype(np.float32) + 5 * _noise(rng, (h, w), 2)[..., None]
    elif kind == "fabric":
        weave = np.sin(xx * 1.1) * np.sin(yy * 1.1)
        base = np.full((h, w, 3), (92, 96, 128), np.float32) + 14 * weave[..., None] + 8 * _noise(rng, (h, w), 12)[..., None]
    elif kind == "concrete":
        base = np.full((h, w, 3), (128, 126, 122), np.float32) + 22 * _noise(rng, (h, w), 4)[..., None] + 14 * _noise(rng, (h, w), 40)[..., None]
    elif kind == "dark-table":
        base = np.full((h, w, 3), (34, 32, 36), np.float32) + 5 * _noise(rng, (h, w), 25)[..., None]
    elif kind == "kraft":
        base = np.full((h, w, 3), (176, 142, 100), np.float32) + 9 * _noise(rng, (h, w), 2.5)[..., None] + 6 * _noise(rng, (h, w), 50)[..., None]
    else:
        raise ValueError(f"Unknown background {kind!r}.")
    return np.clip(base, 0, 255)


def _rasterize(polygon, shape):
    """Anti-aliased coverage of a polygon given in scene pixels (4 x 4 supersampling)."""
    h, w = shape
    big = np.zeros((h * 4, w * 4), np.uint8)
    shapes = polygon.geoms if hasattr(polygon, "geoms") else [polygon]
    for piece in shapes:
        cv2.fillPoly(big, [np.round(np.array(piece.exterior.coords) * 4).astype(np.int32)], 255)
        for ring in piece.interiors:
            cv2.fillPoly(big, [np.round(np.array(ring.coords) * 4).astype(np.int32)], 0)
    return cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


def render(part, background_kind, seed, *, size=SIZE, quality=None, subject_share=None):
    """One photo of ``part`` (a name from ``parts()``). Returns (JPEG bytes, truth).

    ``truth`` holds the part name, the background, a boolean subject mask at the photo's
    size, the subject's bounding box (x0, y0, x1, y1) in pixels and the Gaussian blur
    applied, in pixels. The same seed gives the same photo.
    """
    rng = np.random.default_rng(seed)
    shape, colour = parts()[part]
    w, h = size
    scene = (h, w)
    # Place the part: any rotation, its long side a quarter to three fifths of the frame
    # width, shrunk if needed so that it lies inside the frame with a clear margin.
    share = subject_share if subject_share is not None else rng.uniform(0.25, 0.6)
    minx, miny, maxx, maxy = shape.bounds
    turned = affinity.rotate(shape, rng.uniform(0, 360), origin=(0, 0))
    tx0, ty0, tx1, ty1 = turned.bounds
    pad = 0.07 * w
    scale = min(
        share * w / max(maxx - minx, maxy - miny),
        (w - 2 * pad) / (tx1 - tx0),
        (h - 2 * pad) / (ty1 - ty0),
    )
    placed = affinity.scale(turned, scale, scale, origin=(0, 0))
    px0, py0, px1, py1 = placed.bounds
    placed = affinity.translate(
        placed,
        rng.uniform(pad - px0, w - pad - px1) if w - pad - px1 > pad - px0 else (w - px0 - px1) / 2,
        rng.uniform(pad - py0, h - pad - py1) if h - pad - py1 > pad - py0 else (h - py0 - py1) / 2,
    )

    surface = background(background_kind, rng, scene)
    cover = _rasterize(placed, scene)
    # Soft contact shadow, offset toward one side.
    shadow = cv2.GaussianBlur(cover, (0, 0), 0.012 * w)
    offset = np.float32([[1, 0, rng.uniform(-0.012, 0.012) * w], [0, 1, rng.uniform(0.004, 0.014) * w]])
    shadow = cv2.warpAffine(shadow, offset, (w, h))
    surface *= (1 - rng.uniform(0.15, 0.4) * shadow * (1 - cover))[..., None]
    # The part: its colour with a faint brushed texture and a light edge bevel.
    tone = np.array(colour, np.float32) * rng.uniform(0.88, 1.08)
    top = tone + 5 * _noise(rng, scene, 3)[..., None] + 7 * _noise(rng, scene, 45)[..., None]
    flat = surface * (1 - cover[..., None]) + np.clip(top, 0, 255) * cover[..., None]

    # Camera: a random perspective (tilt up to about 30 degrees) and uneven light.
    jitter = rng.uniform(-0.09, 0.09, (4, 2)) * (w, h)
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    view = cv2.getPerspectiveTransform(corners, np.float32(corners + jitter))
    photo = cv2.warpPerspective(flat, view, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    mask = cv2.warpPerspective(cover, view, (w, h), flags=cv2.INTER_LINEAR) > 0.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    angle = rng.uniform(0, 2 * math.pi)
    ramp = ((xx / w - 0.5) * math.cos(angle) + (yy / h - 0.5) * math.sin(angle)) * rng.uniform(0.1, 0.45)
    photo *= (rng.uniform(0.85, 1.1) * (1 + ramp))[..., None]
    blur = rng.uniform(0.6, 2.2)
    photo = cv2.GaussianBlur(photo, (0, 0), blur)
    photo += rng.normal(0, rng.uniform(1.5, 4.0), photo.shape).astype(np.float32)
    rgb = np.clip(np.round(photo), 0, 255).astype(np.uint8)

    buffer = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buffer, "JPEG", quality=quality or int(rng.integers(72, 95)))
    ys, xs = np.nonzero(mask)
    truth = {
        "part": part,
        "background": background_kind,
        "mask": mask,
        "box": (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1),
        "blur_px": float(blur),
    }
    return buffer.getvalue(), truth


def dataset(views=8, seed=2026, names=None):
    """Yield (file name, JPEG bytes, truth) for each part in ``views`` different shots.

    ``names`` selects parts (default: all fourteen). Backgrounds rotate so that every
    part is seen on several surfaces and every surface carries several parts: matching
    by background alone cannot pass.
    """
    names = sorted(parts()) if names is None else list(names)
    for p, part in enumerate(names):
        for v in range(views):
            kind = BACKGROUNDS[(p * 3 + v) % len(BACKGROUNDS)]
            data, truth = render(part, kind, seed * 1000 + p * 100 + v)
            yield f"{part}-{v:02d}-{kind}.jpg", data, truth
