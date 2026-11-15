"""Generate the relief studio's synthetic moon samples from one crater list.

    .venv/bin/python scripts/generate_relief_samples.py [OUTPUT_DIR]

Writes four images to OUTPUT_DIR, by default ``frontend/public``:

* ``relief-sample.png``: a lit, cratered sphere, as an 8-bit sRGB "photograph";
* ``relief-sample-depth.png``: that sphere's height as a 16-bit depth map (white =
  nearest), from the same seeded craters, so it is the true shape behind the photo;
* ``moon-map.png``: a 2:1 equirectangular albedo map of a whole cratered moon, for
  wrapping around a sphere (a moon lamp). It wraps seamlessly at 0/360 degrees;
* ``moon-elevation.tif``: the same moon's heights as a float32 TIFF in kilometres,
  laid out like NASA's floating-point CGI Moon Kit elevation maps.
Everything is procedural; no photograph or third-party data is involved.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

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


MAP_WIDTH, MAP_HEIGHT = 1024, 512
MAP_SEED = 29


MOON_RADIUS_KM = 1737.4  # The mean lunar radius NASA's CGI Moon Kit heights refer to.


def _map_points(width, height):
    rows = (np.arange(height) + 0.5) / height * np.pi  # colatitude
    columns = (np.arange(width) + 0.5) / width * 2 * np.pi  # longitude
    theta, lam = np.meshgrid(rows, columns, indexing="ij")
    return np.stack(
        [np.sin(theta) * np.cos(lam), np.sin(theta) * np.sin(lam), np.cos(theta)], axis=-1
    )


def moon_features():
    """Seeded maria, mottling and craters, drawn in a fixed order so the albedo and
    elevation maps describe the same surface. Sizes are great-circle angles (radians)."""
    rng = np.random.default_rng(MAP_SEED)

    def random_direction():
        v = rng.normal(size=3)
        return v / np.linalg.norm(v)

    maria = [(random_direction(), rng.uniform(0.18, 0.5)) for _ in range(12)]
    mottling = []
    for _ in range(40):
        centre, size = random_direction(), rng.uniform(0.05, 0.2)
        mottling.append((centre, size, rng.uniform(-0.04, 0.04)))
    craters = []
    for _ in range(300):
        # Crater sizes follow a power law, as on real surfaces: many small, few large.
        centre = random_direction()
        size = np.radians(min(0.5 * rng.uniform(0.02, 1) ** -0.75, 8.0))
        craters.append((centre, size, rng.random() < 0.08))
    return maria, mottling, craters


def moon_map():
    """Albedo of a whole moon in equirectangular projection (longitude across, from the
    north pole at the top to the south pole at the bottom).

    Maria and craters are placed at random directions on the unit sphere and measured
    by great-circle angle, so features near the poles are not stretched and the map
    has no seam. Craters have a bright rim and a slightly darker floor.
    """
    points = _map_points(MAP_WIDTH, MAP_HEIGHT)
    maria, mottling, craters = moon_features()
    albedo = np.full(points.shape[:2], 0.78)
    for centre, size in maria:  # Maria: broad, dark, overlapping basins.
        angle = np.arccos(np.clip(points @ centre, -1, 1))
        albedo -= 0.32 * np.exp(-((angle / size) ** 4))
    albedo = np.maximum(albedo, 0.3)
    for centre, size, amount in mottling:  # Low-contrast mottling.
        angle = np.arccos(np.clip(points @ centre, -1, 1))
        albedo += amount * np.exp(-((angle / size) ** 2))
    for centre, size, young in craters:
        angle = np.arccos(np.clip(points @ centre, -1, 1)) / size
        rim = 0.07 * np.exp(-(((angle - 1) / 0.25) ** 2))
        floor = 0.05 * np.exp(-((angle / 0.75) ** 2))
        halo = 0.05 * np.exp(-((angle / 2.5) ** 2)) if young else 0
        albedo += rim - floor + halo
    linear = np.clip(albedo, 0.05, 1.0) ** 1.6  # Albedo to reflectance contrast.
    srgb = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)
    gray = (np.clip(srgb, 0, 1) * 255).round().astype(np.uint8)
    return np.dstack([gray, gray, gray])


ELEVATION_WIDTH, ELEVATION_HEIGHT = 1440, 720  # 4 samples per degree, like ldem_4.tif


def moon_elevation():
    """Heights (float32 km, relative to MOON_RADIUS_KM) of the same moon as moon_map.

    Maria are basins about 2 km deep. Craters follow simple-crater geometry: depth about
    0.2 x diameter and rim height about 0.04 x diameter, capped at 4 km and 1 km as
    large craters flatten. Same projection and units as NASA's floating-point
    CGI Moon Kit maps, so the studio treats both alike.
    """
    points = _map_points(ELEVATION_WIDTH, ELEVATION_HEIGHT)
    maria, _, craters = moon_features()
    height = np.zeros(points.shape[:2])
    for centre, size in maria:
        angle = np.arccos(np.clip(points @ centre, -1, 1))
        height -= 2.0 * np.exp(-((angle / size) ** 4))
    for centre, size, _young in craters:
        diameter_km = 2 * size * MOON_RADIUS_KM
        depth, rim_height = min(0.2 * diameter_km, 4.0), min(0.04 * diameter_km, 1.0)
        angle = np.arccos(np.clip(points @ centre, -1, 1)) / size
        bowl = np.clip(1 - angle**2, 0, None)  # A parabolic bowl inside the rim.
        rim = np.exp(-(((angle - 1) / 0.25) ** 2))
        height += rim_height * rim - depth * bowl
    return height.astype(np.float32)


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output / "relief-sample.png"), photo())
    cv2.imwrite(str(output / "relief-sample-depth.png"), depth())
    cv2.imwrite(str(output / "moon-map.png"), moon_map())
    Image.fromarray(moon_elevation(), "F").save(
        output / "moon-elevation.tif", "TIFF", compression="tiff_adobe_deflate"
    )


if __name__ == "__main__":
    main(
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "frontend/public"
    )
