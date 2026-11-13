"""Synthetic phone photos of a known part on a reference sheet, with exact ground truth.

The scene is a 120 x 70 mm plate (R8 corners, 4 x D6 holes, a D22 bore, a 24 x 8 slot)
on an A4 sheet on a textured table. The camera is a pinhole with a chosen tilt and
polynomial radial distortion; the photo has uneven light, vignetting, a soft contact
shadow, optical blur, noise and JPEG compression. A thick part has vertical walls,
rendered as projected slices below its top face.

Light mixes linearly. Surface tones are given as saved 0-255 values and taken to
linear light; uneven light, vignetting and the shadow scale that light; partial
coverage and optical blur mix it; the result is then saved through a camera tone curve
(sRGB's, or a plain gamma).

Polygon coverage is integrated over each scene pixel, including holes. Lens
inversion is independent of the production solver. The default radial model
still agrees with production assumptions; optional k2 supplies model-mismatch
experiments, not an extra correction supported by the workbench.
"""

from __future__ import annotations

import io
import itertools
import math

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, box

SHEET = (210.0, 297.0)
PART = {"width": 120.0, "height": 70.0, "corner": 8.0}
SMALL_HOLES = [(x, y) for x in (-48.0, 48.0) for y in (-25.0, 25.0)]
BORE = (-20.0, 0.0, 22.0)
SLOT = (25.0, 0.0, 24.0, 8.0)
POSE = {"centre": (105.0, 150.0), "angle_deg": 8.0}


def srgb_to_linear(values):
    """IEC 61966-2-1 decoding, written out here independently of backend.tone; both
    sides use a 0-255 scale."""
    v = np.asarray(values, np.float64) / 255
    return 255 * np.where(v <= 0.04045, v / 12.92, ((np.maximum(v, 0.04045) + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(values):
    v = np.maximum(np.asarray(values, np.float64), 0) / 255
    return 255 * np.where(
        v <= 0.0031308, 12.92 * v, 1.055 * np.maximum(v, 0.0031308) ** (1 / 2.4) - 0.055
    )


def stadium(cx, cy, length, width):
    r = width / 2
    core = box(cx - length / 2 + r, cy - r, cx + length / 2 - r, cy + r)
    return core.union(Point(cx - length / 2 + r, cy).buffer(r, 256)).union(
        Point(cx + length / 2 - r, cy).buffer(r, 256)
    )


def part_local():
    w, h, r = PART["width"], PART["height"], PART["corner"]
    outer = box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, 256)
    holes = [Point(x, y).buffer(3.0, 256) for x, y in SMALL_HOLES]
    holes.append(Point(BORE[0], BORE[1]).buffer(BORE[2] / 2, 256))
    holes.append(stadium(*SLOT))
    return Polygon(outer.exterior, [hole.exterior for hole in holes])


def part_on_sheet():
    return affinity.translate(
        affinity.rotate(part_local(), POSE["angle_deg"], origin=(0, 0)), *POSE["centre"]
    )


def _rot(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def camera(tilt=(22.0, -9.0, 4.0), size=(2400, 1800), focal=None, distance=440.0):
    """`focal` defaults to 1980 px at 2400 px wide and scales with the width, so a
    larger photo shows the same field in more pixels."""
    w, h = size
    focal = 1980.0 * w / 2400 if focal is None else focal
    k = np.array([[focal, 0, w / 2], [0, focal, h / 2], [0, 0, 1.0]])
    rotation = _rot("z", tilt[2]) @ _rot("x", tilt[0]) @ _rot("y", tilt[1])
    target = np.array([SHEET[0] / 2, SHEET[1] / 2, 0.0])
    t = np.array([0, 0, distance]) - rotation @ target
    return k, rotation, t


def _accumulate(acc, x0, y0, x1, y1):
    """Add one directed edge's signed area to a row accumulator (a polygon rasteriser's
    accumulation buffer): after a cumulative sum along each row, every cell holds the
    exact signed area of its pixel square [i, i + 1] x [j, j + 1] inside the polygon."""
    if y0 == y1:
        return
    sign = 1.0
    if y0 > y1:
        x0, y0, x1, y1, sign = x1, y1, x0, y0, -1.0
    dxdy = (x1 - x0) / (y1 - y0)
    rows = acc.shape[0]
    first, last = max(0, math.floor(y0)), min(rows, math.ceil(y1))
    x = x0 + dxdy * (max(y0, first) - y0)
    for y in range(first, last):
        dy = min(y + 1.0, y1) - max(float(y), y0)
        x_next = x + dxdy * dy
        d = dy * sign
        lo, hi = (x, x_next) if x < x_next else (x_next, x)
        lo_floor = math.floor(lo)
        i0, i1 = lo_floor, math.ceil(hi)
        if i1 <= i0 + 1:
            # Within one cell: the area right of the edge's mean position stays in it.
            mid = 0.5 * (x + x_next) - lo_floor
            acc[y, i0] += d * (1.0 - mid)
            acc[y, i0 + 1] += d * mid
        else:
            inv = 1.0 / (hi - lo)
            f0 = lo - lo_floor
            a0 = 0.5 * inv * (1.0 - f0) ** 2
            f1 = hi - math.ceil(hi) + 1.0
            am = 0.5 * inv * f1 * f1
            acc[y, i0] += d * a0
            if i1 == i0 + 2:
                acc[y, i0 + 1] += d * (1.0 - a0 - am)
            else:
                a1 = inv * (1.5 - f0)
                acc[y, i0 + 1] += d * (a1 - a0)
                acc[y, i0 + 2 : i1 - 1] += d * inv
                a2 = a1 + (i1 - i0 - 3) * inv
                acc[y, i1 - 1] += d * (1.0 - a2 - am)
            acc[y, i1] += d * am
        x = x_next


def coverage(polygon, ppm, x0, y0, shape):
    """Exact fraction of each scene pixel inside `polygon` (scene pixel i is centred on
    plane x0 + i / ppm).

    Each edge adds its signed area to a row accumulator, which a cumulative sum along
    each row turns into each pixel's covered area: exact for any polygon, holes
    included. Edges are clipped to the image's columns, a stretch left of it standing
    as a vertical edge at its border. (Sampling the coverage on sub-rows instead, as
    this did before, quantised a straight edge's area per pixel by the sub-row
    spacing. At rational slopes, where every pixel along the edge has the same phase,
    that moved the traced edge by up to 0.03 px.)"""
    from shapely.geometry.polygon import orient

    polygon = orient(polygon, 1.0)
    rows, cols = shape
    acc = np.zeros((rows, cols + 2), np.float64)
    for ring in [polygon.exterior, *polygon.interiors]:
        c = (np.asarray(ring.coords, dtype=np.float64) - [x0, y0]) * ppm + 0.5
        for (ax, ay), (bx, by) in itertools.pairwise(c):
            # Split at the image's left and right borders, then clamp what lies outside.
            cuts = [0.0, 1.0]
            for border in (0.0, float(cols)):
                if (ax - border) * (bx - border) < 0:
                    cuts.append((border - ax) / (bx - ax))
            cuts.sort()
            for t0, t1 in itertools.pairwise(cuts):
                px0, py0 = ax + t0 * (bx - ax), ay + t0 * (by - ay)
                px1, py1 = ax + t1 * (bx - ax), ay + t1 * (by - ay)
                _accumulate(acc, min(max(px0, 0.0), cols), py0, min(max(px1, 0.0), cols), py1)
    # The ring orientation sets the sign; exterior and holes have opposite ones.
    return np.clip(np.abs(np.cumsum(acc, axis=1)[:, :cols]), 0.0, 1.0).astype(np.float32)


def project(polygon, matrix):
    def tf(coords):
        c = np.asarray(coords)
        q = np.c_[c, np.ones(len(c))] @ matrix.T
        return q[:, :2] / q[:, 2:]

    return Polygon(tf(polygon.exterior.coords), [tf(r.coords) for r in polygon.interiors])


def _radial_inverse(rd, k1, k2=0.0):
    """Independent central-branch inverse of rd = ru (1 + k1 ru² + k2 ru⁴).

    For the cubic, use the triple-angle identities for sin/sinh, not production
    Newton steps. For a quintic, bracket on its first increasing branch and bisect.
    Refuse a requested sensor radius past a fold; a negative or later root would
    not supply a single-valued central-camera image. Radii use half-diagonal units.
    """
    rd = np.asarray(rd, dtype=np.float64)
    if not np.isfinite(rd).all() or (rd < 0).any() or not all(map(math.isfinite, (k1, k2))):
        raise ValueError("Synthetic lens radii and coefficients must be finite; radii must be nonnegative.")
    if k2 == 0:
        if k1 == 0:
            return rd.copy()
        scale = math.sqrt(3 * abs(k1))
        if not math.isfinite(scale):
            raise ValueError("Synthetic lens coefficient exceeds the numerical renderer domain.")
        argument = 1.5 * scale * rd
        if k1 < 0:
            if (argument > 1).any():
                raise ValueError("Synthetic radial lens folds before the requested sensor radius.")
            return (2 / scale) * np.sin(np.arcsin(argument) / 3)
        return (2 / scale) * np.sinh(np.arcsinh(argument) / 3)

    def forward(radius):
        square = radius * radius
        return radius * (1 + square * (k1 + k2 * square))

    # The first positive root of 1 + 3 k1 q + 5 k2 q² (q = ru²) ends the
    # central monotone branch. The conjugate form avoids subtractive cancellation.
    discriminant = 9 * k1 * k1 - 20 * k2
    limit = math.inf
    if discriminant >= 0:
        denominator = math.sqrt(discriminant) - 3 * k1
        if denominator > 0:
            limit = math.sqrt(2 / denominator)
    maximum = float(np.max(rd, initial=0.0))
    if math.isfinite(limit):
        hi = limit
        if maximum > forward(hi):
            raise ValueError("Synthetic radial lens folds before the requested sensor radius.")
    else:
        hi = max(1.0, maximum)
        for _ in range(64):
            if forward(hi) >= maximum:
                break
            hi *= 2
        else:
            raise ValueError("Synthetic radial lens could not be bracketed.")
    # Per-point brackets retain relative precision near the optical centre.
    upper = 2 * np.minimum(rd, hi / 2)
    for _ in range(64):
        short = forward(upper) < rd
        if not short.any():
            break
        expanded = np.minimum(hi, 2 * upper)
        if np.any(short & (expanded <= upper)):
            raise ValueError("Synthetic radial lens could not be bracketed at numerical precision.")
        upper = np.where(short, expanded, upper)
    else:
        raise ValueError("Synthetic radial lens could not be bracketed.")
    lower = np.zeros_like(rd)
    for _ in range(54):
        mid = lower + (upper - lower) / 2
        below = forward(mid) < rd
        lower = np.where(below, mid, lower)
        upper = np.where(below, upper, mid)
    return lower + (upper - lower) / 2


def undistort_grid(u, v, k1, size, k2=0.0):
    """Ideal pixel positions from an independently inverted radial lens map."""

    w, h = size
    cx, cy, s = w / 2, h / 2, math.hypot(w, h) / 2
    xd, yd = (u - cx) / s, (v - cy) / s
    rd = np.hypot(xd, yd)
    factor = np.divide(_radial_inverse(rd, k1, k2), rd, out=np.ones_like(rd), where=rd > 0)
    return cx + xd * factor * s, cy + yd * factor * s


def rotated_gaussian(major, minor, degrees):
    """A normalised Gaussian kernel with spreads `major` and `minor` px, its major axis
    turned `degrees` from x, sampled out to 4 times the major spread."""
    a = math.radians(degrees)
    rot = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    inverse = np.linalg.inv(rot @ np.diag([major**2, minor**2]) @ rot.T)
    half = math.ceil(4 * major)
    yy, xx = np.mgrid[-half : half + 1, -half : half + 1].astype(np.float64)
    kernel = np.exp(-0.5 * (inverse[0, 0] * xx * xx + 2 * inverse[0, 1] * xx * yy + inverse[1, 1] * yy * yy))
    return (kernel / kernel.sum()).astype(np.float32)


def render(
    *,
    tilt=(22.0, -9.0, 4.0),
    k1=-0.035,
    k2=0.0,
    thickness=0.0,
    slices=12,
    size=(2400, 1800),
    seed=7,
    ppm=8.0,
    shadow=0.25,
    gradient=0.3,
    blur=1.0,
    noise=2.5,
    quality=90,
    tones=(106.0, 236.0, 48.0, 78.0),
    exif_focal_35mm=None,
    gamma=None,
    focal=None,
    distance=440.0,
    shadow_kernel=None,
):
    """Returns (jpeg bytes, truth dict).

    `tones` are the table, sheet, part-top and wall brightness as saved (0-255).
    `shadow` is the fraction of light the part's contact shadow removes at its deepest;
    `gradient` is the strength of the uneven light. Both act on linear light, so a
    0.25 shadow darkens the saved paper by about 12 %, and a shadow that looks 25 %
    darker in the saved photo removes about 47 % of the light.
    `exif_focal_35mm` writes that 35 mm-equivalent focal length into the JPEG's EXIF.
    `gamma` is the camera's tone curve: None for sRGB's, or the exponent of a plain
    power law (saved = linear ** (1 / gamma)), for cameras whose curve differs from the
    sRGB decoding the tracer assumes. 1 saves linear light unchanged.
    `focal` (px) and `distance` (mm) place the camera as in `camera`.
    `k2` is a second radial term for intentional camera-model mismatch. The
    production tracer estimates only k1. Coefficients use radius normalised by
    the image half-diagonal, not OpenCV's focal-length normalisation.
    `shadow_kernel` replaces the shadow's default shape, the footprint moved (1.6, 1.9)
    mm and blurred 2.2 mm, with another (`shadow_kernel_mm`); the tracer's own model of
    the shadow is fitted, so tests need shapes it was not written for.
    `blur` is the sensor's Gaussian blur in photo pixels, or (x, y) for one that differs
    by direction, as a shaken camera's does, or (major, minor, degrees) for such a blur
    whose major axis is turned that far from x.
    """
    if gamma is None:
        to_linear, to_saved = srgb_to_linear, linear_to_srgb
    else:

        def to_linear(v):
            return 255 * (np.clip(v, 0, None) / 255) ** gamma

        def to_saved(v):
            return 255 * (np.clip(v, 0, None) / 255) ** (1 / gamma)

    rng = np.random.default_rng(seed)
    part = part_on_sheet()
    k, rotation, t = camera(tilt, size, focal, distance)
    centre = -rotation.T @ t
    up = -1.0 if centre[2] < 0 else 1.0
    floor = k @ np.column_stack([rotation[:, 0], rotation[:, 1], t])
    floor_inv = np.linalg.inv(floor)
    x0, y0, x1, y1 = -60.0, -60.0, SHEET[0] + 60.0, SHEET[1] + 60.0
    shape = (int((y1 - y0) * ppm), int((x1 - x0) * ppm))

    def box_cov(n, lo, hi, origin):
        c = np.arange(n, dtype=np.float64)
        lo, hi = (lo - origin) * ppm, (hi - origin) * ppm
        return np.clip(np.minimum(c + 0.5, hi) - np.maximum(c - 0.5, lo), 0, 1)

    sheet_a = np.outer(box_cov(shape[0], 0, SHEET[1], y0), box_cov(shape[1], 0, SHEET[0], x0))
    bottom = coverage(part, ppm, x0, y0, shape)
    if thickness > 0:
        walls = bottom.copy()
        for height in np.linspace(0, thickness, slices)[1:-1]:
            g = floor_inv @ k @ np.column_stack(
                [rotation[:, 0], rotation[:, 1], t + up * height * rotation[:, 2]]
            )
            walls = np.maximum(walls, coverage(project(part, g / g[2, 2]), ppm, x0, y0, shape))
        g = floor_inv @ k @ np.column_stack(
            [rotation[:, 0], rotation[:, 1], t + up * thickness * rotation[:, 2]]
        )
        top = coverage(project(part, g / g[2, 2]), ppm, x0, y0, shape)
        material = np.maximum(walls, top)
    else:
        top = material = bottom
    yy, xx = np.mgrid[0 : shape[0], 0 : shape[1]].astype(np.float32)
    grain = 0.5 + 0.5 * np.sin(xx / (ppm * 1.7) + 3 * np.sin(yy / (ppm * 23)))
    table_tone, paper_tone, top_tone, side_tone = tones
    table = table_tone - 14 + 28 * grain + rng.normal(0, 6, shape).astype(np.float32)
    paper = paper_tone + cv2.GaussianBlur(rng.normal(0, 3, shape).astype(np.float32), (0, 0), 2)
    metal = top_tone + cv2.GaussianBlur(rng.normal(0, 8, shape).astype(np.float32), (0, 0), 1.5)
    wall_tone = side_tone + cv2.GaussianBlur(rng.normal(0, 6, shape).astype(np.float32), (0, 0), 1.5)
    if shadow_kernel is None:
        cast = cv2.GaussianBlur(
            cv2.warpAffine(bottom, np.float32([[1, 0, 1.6 * ppm], [0, 1, 1.9 * ppm]]), shape[::-1]),
            (0, 0),
            2.2 * ppm,
        )
    else:
        kernel = shadow_kernel_mm(shadow_kernel, ppm)
        cast = cv2.filter2D(bottom.astype(np.float32), -1, kernel[::-1, ::-1], borderType=cv2.BORDER_CONSTANT)
        cast /= max(float(cast.max()), 1e-9)
    # From here on everything is linear light. The shadow dims the paper. A pixel is
    # linear in its coverages (top is inside material, so material >= top): background
    # where neither covers it, wall where only the walls do, top face elsewhere. Uneven
    # light and vignetting scale the whole scene, and the optical blur follows.
    table, paper, metal, wall_tone = (
        to_linear(np.clip(surface, 0, 255)) for surface in (table, paper, metal, wall_tone)
    )
    paper = paper * (1 - shadow * cast)
    background = table * (1 - sheet_a) + paper * sheet_a
    scene = background * (1 - material) + wall_tone * (material - top) + metal * top
    gx, gy = (xx - shape[1] / 2) / shape[1], (yy - shape[0] / 2) / shape[0]
    scene *= (1 - gradient * (gx * 0.8 + gy * 0.6)) * (1 - 0.35 * (gx**2 + gy**2))
    scene = cv2.GaussianBlur(scene.astype(np.float32), (0, 0), 0.8)
    w, h = size
    u, v = np.meshgrid(np.arange(w, dtype=np.float64) + 0.5, np.arange(h, dtype=np.float64) + 0.5)
    iu, iv = undistort_grid(u, v, k1, size, k2)
    den = floor_inv[2, 0] * iu + floor_inv[2, 1] * iv + floor_inv[2, 2]
    px = (floor_inv[0, 0] * iu + floor_inv[0, 1] * iv + floor_inv[0, 2]) / den
    py = (floor_inv[1, 0] * iu + floor_inv[1, 1] * iv + floor_inv[1, 2]) / den
    image = cv2.remap(
        scene,
        ((px - x0) * ppm).astype(np.float32),
        ((py - y0) * ppm).astype(np.float32),
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT,
    )
    if np.isscalar(blur) or len(blur) == 2:
        blur_x, blur_y = (blur, blur) if np.isscalar(blur) else blur
        image = cv2.GaussianBlur(image, (0, 0), blur_x, sigmaY=blur_y)
    else:
        image = cv2.filter2D(image, -1, rotated_gaussian(*blur), borderType=cv2.BORDER_REFLECT)
    # The camera saves through its tone curve; noise is added on the saved scale, where
    # a processed photo's noise is roughly even across tones.
    grey = np.clip(to_saved(image) + rng.normal(0, noise, image.shape), 0, 255)
    rgb = np.dstack([grey, grey * 0.97, grey * 0.92]).astype(np.uint8)
    from PIL import Image

    picture = Image.fromarray(rgb)
    exif = Image.Exif()
    if exif_focal_35mm:
        exif.get_ifd(0x8769)[0xA405] = int(exif_focal_35mm)  # FocalLengthIn35mmFilm
    buffer = io.BytesIO()
    picture.save(buffer, "JPEG", quality=quality, exif=exif.tobytes())
    encoded = np.frombuffer(buffer.getvalue(), np.uint8)
    truth = {
        "k1": k1,
        "k2": k2,
        "focal_px": float(k[0, 0]),
        "camera_centre_mm": centre.tolist(),
        "floor_homography": (floor / floor[2, 2]).tolist(),
        "thickness_mm": thickness,
        "size": size,
    }
    return encoded.tobytes(), truth


def _flat_photo(table, paper, regions, ppm, blur):
    """PNG bytes of a flat-lit colour photo of an A4 sheet lying square on a table, with
    non-overlapping coloured `regions` [(polygon in sheet millimetres, sRGB colour)] on
    it. Coverage and blur mix linear light in each channel."""
    from PIL import Image
    from shapely import affinity

    margin = 40.0
    shape = (int((SHEET[1] + 2 * margin) * ppm), int((SHEET[0] + 2 * margin) * ppm))

    def cover(n, lo, hi):
        c = np.arange(n, dtype=np.float64)
        return np.clip(np.minimum(c + 0.5, hi * ppm) - np.maximum(c - 0.5, lo * ppm), 0, 1)

    sheet_a = np.outer(
        cover(shape[0], margin, margin + SHEET[1]), cover(shape[1], margin, margin + SHEET[0])
    )
    covers = [
        (coverage(affinity.translate(polygon, margin, margin), ppm, 0.0, 0.0, shape), colour)
        for polygon, colour in regions
    ]
    clear = 1 - sum(a for a, _ in covers)
    channels = []
    for index in range(3):
        t, p = float(srgb_to_linear(table[index])), float(srgb_to_linear(paper[index]))
        light = (t * (1 - sheet_a) + p * sheet_a) * clear
        for a, colour in covers:
            light = light + float(srgb_to_linear(colour[index])) * a
        channels.append(linear_to_srgb(cv2.GaussianBlur(light.astype(np.float32), (0, 0), blur)))
    buffer = io.BytesIO()
    Image.fromarray(np.clip(np.dstack(channels), 0, 255).round().astype(np.uint8)).save(buffer, "PNG")
    return buffer.getvalue()


def colour_photo(table, paper, part, ppm=4.0, blur=1.2):
    """A 60 mm disc with a 16 mm hole, centred on the sheet. `table`, `paper` and `part`
    are saved sRGB colours; `ppm` is photo pixels per millimetre."""
    centre = Point(SHEET[0] / 2, SHEET[1] / 2)
    disc = centre.buffer(30, 512).difference(centre.buffer(8, 512))
    return _flat_photo(table, paper, [(disc, part)], ppm, blur)


def two_colour_photo(table, paper, part, patch, ppm=4.0, blur=1.2):
    """An 80 x 50 mm plate centred on the sheet. Its right 14 mm is the `patch` colour
    and holds an 8 mm hole; the rest is the `part` colour."""
    cx, cy = SHEET[0] / 2, SHEET[1] / 2
    hole = Point(cx + 33, cy).buffer(4, 512)
    main = box(cx - 40, cy - 25, cx + 26, cy + 25)
    minor = box(cx + 26, cy - 25, cx + 40, cy + 25).difference(hole)
    return _flat_photo(table, paper, [(main, part), (minor, patch)], ppm, blur)


def rigid_fit(src, dst):
    """Least-squares rotation + translation (no scale) mapping src onto dst."""
    sc, dc = src.mean(0), dst.mean(0)
    u, _, vt = np.linalg.svd((src - sc).T @ (dst - dc))
    d = np.diag([1, np.sign(np.linalg.det(vt.T @ u.T))])
    rotation = vt.T @ d @ u.T
    return rotation, dc - rotation @ sc


def measure(profile):
    """Millimetre feature measurements from a reference-sheet trace's profile.

    Returns hole diameters, the slot as a polygon, and the rigid-fit errors of the six
    hole centres against the design (no scale is fitted).
    """
    from shapely.geometry import Polygon as P

    mm = profile["reference"]["mm_per_px"]
    from backend.fitting import arc_geometry

    circles, other = [], []
    for ring, segs in zip(profile["holes"], profile["primitives"]["holes"]):
        if len(segs) == 1 and segs[0]["kind"] == "circle":
            c = np.array(segs[0]["center"]) * mm
            circles.append({"centre": c, "diameter": 2 * segs[0]["radius"] * mm})
            continue
        poly = P(np.array(ring) * mm)
        entry = {"centre": np.array(poly.centroid.coords[0]), "poly": poly}
        kinds = [s["kind"] for s in segs]
        if sorted(kinds) == ["arc", "arc", "line", "line"]:
            # A slot measured on its fitted geometry: end-cap centres and radii.
            caps = [arc_geometry(np.array(s["start"]) * mm, np.array(s["mid"]) * mm, np.array(s["end"]) * mm) for s in segs if s["kind"] == "arc"]
            (c1, r1), (c2, r2) = [(np.array(c), r) for c, r, _, _ in caps]
            entry["dims"] = (float(np.linalg.norm(c1 - c2) + r1 + r2), float(r1 + r2))
            entry["centre"] = (c1 + c2) / 2
        other.append(entry)
    circles.sort(key=lambda c: c["diameter"])
    return circles, other


def shadow_kernel_mm(spec, ppm):
    """A normalised shadow kernel on the scene grid (`ppm` per mm): the light reaching a
    point of paper is reduced by the part's footprint convolved with it. `spec` is a
    list of (kind, dx, dy, size, weight) terms in mm: "disc" (a lamp's uniform penumbra
    of that radius), "gauss" (that standard deviation) and "bar" (a long light: a
    segment of that length along x, 0.5 mm wide), each centred at (dx, dy)."""
    reach = max(abs(dx) + abs(dy) + 3 * size for _, dx, dy, size, _ in spec) + 1
    r = int(np.ceil(reach * ppm))
    yy, xx = (np.mgrid[-r : r + 1, -r : r + 1] + 0.0) / ppm
    kernel = np.zeros_like(xx)
    for kind, dx, dy, size, weight in spec:
        u, v = xx - dx, yy - dy
        if kind == "disc":
            part = np.clip(size - np.hypot(u, v) + 0.5 / ppm, 0, 1.0 / ppm) * ppm
        elif kind == "gauss":
            part = np.exp(-0.5 * (u * u + v * v) / size**2)
        elif kind == "bar":
            part = ((np.abs(u) <= size / 2) & (np.abs(v) <= 0.25)).astype(float)
        else:
            raise ValueError(kind)
        kernel += weight * part / part.sum()
    return (kernel / kernel.sum()).astype(np.float32)


def feature_errors(profile):
    circles, other = measure(profile)
    assert len(circles) == 5 and len(other) == 1, (len(circles), len(other))
    small, bore, slot = circles[:4], circles[4], other[0]
    src = np.vstack([bore["centre"], slot["centre"], [c["centre"] for c in small]])
    design_small = np.array(SMALL_HOLES)
    rotation, shift = rigid_fit(src[:2], np.array([BORE[:2], SLOT[:2]]))
    mapped = (src[2:] @ rotation.T) + shift
    order = [int(np.argmin(np.linalg.norm(design_small - p, axis=1))) for p in mapped]
    assert sorted(order) == [0, 1, 2, 3]
    dst = np.vstack([BORE[:2], SLOT[:2], design_small[order]])
    rotation, shift = rigid_fit(src, dst)
    position = np.linalg.norm(src @ rotation.T + shift - dst, axis=1)
    outer = np.array(profile["outer"]) * profile["reference"]["mm_per_px"]
    (_, _), (rw, rh), _ = cv2.minAreaRect(outer.astype(np.float32))
    if "dims" in slot:
        length, width = slot["dims"]
    else:  # polyline: chord sampling can shorten it by up to the sampling tolerance
        rect = cv2.minAreaRect(np.asarray(slot["poly"].exterior.coords, np.float32))
        length, width = max(rect[1]), min(rect[1])
    return {
        "small": max(abs(c["diameter"] - 6.0) for c in small),
        "bore": abs(bore["diameter"] - BORE[2]),
        "slot": max(abs(length - SLOT[2]), abs(width - SLOT[3])),
        "position": float(position.max()),
        "outer": max(abs(max(rw, rh) - PART["width"]), abs(min(rw, rh) - PART["height"])),
    }
