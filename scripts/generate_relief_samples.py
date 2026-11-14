"""Generate the relief studio's synthetic moon samples from one crater list.

    .venv/bin/python scripts/generate_relief_samples.py [OUTPUT_DIR]

Writes ``relief-sample.png`` (a lit, cratered sphere: an 8-bit sRGB "photograph") and
``relief-sample-depth.png`` (the same sphere's height as a 16-bit depth map, white =
nearest) to OUTPUT_DIR, by default ``frontend/public``. Both use the same seeded
crater positions and radii, so the depth map is the true shape behind the photo.
Everything is procedural; no photograph or third-party data is involved.
"""

import sys
from pathlib import Path

import cv2
import numpy as np

WIDTH, HEIGHT = 900, 640
CENTRE_X, CENTRE_Y, RADIUS = 450, 320, 270  # Sphere outline, in pixels.
SEED = 11
# Crater depth and rim height as fractions of each crater's radius: a simple bowl.
BOWL_DEPTH = 0.2
RIM_HEIGHT = 0.05
# The depth map's white level, in sphere radii. A fixed scale (rather than the peak)
# keeps the shape exact: a dome of span = DEPTH_FULL_SCALE x radius is a hemisphere.
DEPTH_FULL_SCALE = 1.1


def features():
    """Seeded maria (albedo patches) and craters, in sphere-normalized coordinates."""
    rng = np.random.default_rng(SEED)
    maria = [(*rng.uniform(-0.7, 0.7, 2), rng.uniform(0.12, 0.3)) for _ in range(9)]
    craters = [(*rng.uniform(-0.95, 0.95, 2), rng.uniform(0.015, 0.11)) for _ in range(60)]
    return rng, maria, craters


def grid():
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(float)
    dx, dy = (x - CENTRE_X) / RADIUS, (y - CENTRE_Y) / RADIUS
    return dx, dy


def photo():
    """Lambert-lit sphere with albedo maria and crater shading, sRGB encoded."""
    rng, maria, craters = features()
    dx, dy = grid()
    r2 = dx**2 + dy**2
    inside = r2 < 1
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    light = np.array([-0.55, -0.35, 0.76])
    light /= np.linalg.norm(light)
    lambert = np.clip(dx * light[0] + dy * light[1] + nz * light[2], 0, 1)
    albedo = np.full(dx.shape, 0.78)
    for px, py, s in maria:
        albedo -= 0.28 * np.exp(-((dx - px) ** 2 + (dy - py) ** 2) / (2 * s * s))
    shade = np.ones(dx.shape)
    for px, py, rr in craters:
        d = np.hypot(dx - px, dy - py) / rr
        ring = np.exp(-(((d - 1) / 0.22) ** 2))
        bowl = np.exp(-((d / 0.8) ** 2))
        # Lit from the upper left: the far rim is bright and the near rim dark.
        angle = ((dx - px) * light[0] + (dy - py) * light[1]) / (np.hypot(dx - px, dy - py) + 1e-9)
        shade += 0.35 * ring * (-angle) - 0.12 * bowl * angle
        albedo += 0.06 * ring
    linear = np.where(inside, np.clip(albedo, 0.2, 1) * lambert * np.clip(shade, 0.3, 1.6), 0)
    stars = (rng.random(dx.shape) > 0.9993) * rng.uniform(0.2, 0.8, dx.shape)
    linear = np.clip(np.where(inside, linear, stars * 0.6) + 0.004, 0, 1)
    linear = cv2.GaussianBlur(linear, (0, 0), 0.8)
    srgb = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)
    rgb = np.dstack([srgb * 0.97, srgb * 0.985, srgb])
    return (np.clip(rgb, 0, 1) * 255).round().astype(np.uint8)[..., ::-1]  # BGR for OpenCV


def depth():
    """Height of the same sphere and craters; 0 is the background and 65535 is
    DEPTH_FULL_SCALE sphere radii above it.

    The sphere's height is sqrt(1 - r^2) in units of its radius. Each crater adds a
    raised rim and a bowl scaled by its radius, following the sphere's surface.
    """
    _, _, craters = features()
    dx, dy = grid()
    r2 = dx**2 + dy**2
    inside = r2 < 1
    height = np.sqrt(np.clip(1 - r2, 0, 1))
    for px, py, rr in craters:
        d = np.hypot(dx - px, dy - py) / rr
        ring = np.exp(-(((d - 1) / 0.22) ** 2))
        bowl = np.exp(-((d / 0.8) ** 2))
        height += rr * (RIM_HEIGHT * ring - BOWL_DEPTH * bowl)
    height = np.where(inside, np.clip(height, 0, None), 0) / DEPTH_FULL_SCALE
    if height.max() > 1:
        raise ValueError("Crater rims exceed the depth map's full scale.")
    return np.round(height * 65535).astype(np.uint16)


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output / "relief-sample.png"), photo())
    cv2.imwrite(str(output / "relief-sample-depth.png"), depth())


if __name__ == "__main__":
    main(
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "frontend/public"
    )
