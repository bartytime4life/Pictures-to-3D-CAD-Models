"""Small drawn pictures for the photo-library tests: one plain shape on a plain ground.

They are deliberately simple. The library tests check the pipeline's behaviour with the
stand-in feature process (colour statistics, backend/vision_worker.py --standin), which
tells differently coloured shapes apart. They say nothing about the real vision model.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

GROUNDS = [(235, 235, 230), (60, 60, 70), (40, 110, 80), (170, 140, 100)]
PARTS = {
    "red": ((200, 40, 40), "disc"),
    "blue": (((40, 60, 200)), "disc"),
    "yellow": ((230, 200, 40), "bar"),
    "black": ((20, 20, 20), "bar"),
}


def scene(part: str, view: int, size=(640, 480), blur=0.0) -> Image.Image:
    """One coloured shape at a pseudo-random place on one of four grounds."""
    colour, kind = PARTS[part]
    rng = np.random.default_rng(sorted(PARTS).index(part) * 100 + view)
    ground = GROUNDS[(view + sorted(PARTS).index(part)) % len(GROUNDS)]
    image = Image.new("RGB", size, ground)
    draw = ImageDraw.Draw(image)
    cx = int(rng.integers(180, size[0] - 180))
    cy = int(rng.integers(150, size[1] - 150))
    r = int(rng.integers(70, 110))
    if kind == "disc":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)
    else:
        draw.rectangle([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=colour)
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    noisy = np.asarray(image, np.float32) + rng.normal(0, 3, (size[1], size[0], 3))
    return Image.fromarray(np.clip(noisy, 0, 255).astype(np.uint8))


def encoded(image: Image.Image, kind="PNG", **options) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, kind, **options)
    return buffer.getvalue()


def write_set(folder, views=4, parts=("red", "blue", "yellow", "black")) -> list[str]:
    """Write ``views`` shots of each part as PNG files; returns their names."""
    names = []
    for part in parts:
        for view in range(views):
            name = f"{part}-{view}.png"
            scene(part, view).save(folder / name)
            names.append(name)
    return names
