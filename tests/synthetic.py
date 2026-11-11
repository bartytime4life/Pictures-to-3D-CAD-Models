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

Coverage is exact: an even-odd scanline at 8 x 8 samples per scene pixel (sample
centres only, so no inclusive-boundary bias such as cv2.fillPoly's).
"""

from __future__ import annotations

import io
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


def coverage(polygon, ppm, x0, y0, shape, samples=8):
    """Exact fraction of each scene pixel inside `polygon` (scene pixel i is centred on
    plane x0 + i / ppm)."""
    edges = []
    for ring in [polygon.exterior, *polygon.interiors]:
        c = (np.asarray(ring.coords) - [x0, y0]) * ppm
        edges.append(np.column_stack([c[:-1], c[1:]]))
    e = np.vstack(edges)
    bx0, by0, bx1, by1 = polygon.bounds
    i0, j0 = max(0, int((bx0 - x0) * ppm) - 2), max(0, int((by0 - y0) * ppm) - 2)
    i1, j1 = min(shape[1], int((bx1 - x0) * ppm) + 3), min(shape[0], int((by1 - y0) * ppm) + 3)
    nx, ny = (i1 - i0) * samples, (j1 - j0) * samples
    xs = i0 - 0.5 + (np.arange(nx) + 0.5) / samples
    ys = j0 - 0.5 + (np.arange(ny) + 0.5) / samples
    ya, yb = e[:, 1:2], e[:, 3:4]
    hit = (ya <= ys) != (yb <= ys)  # edges x rows
    edge_index, row = np.nonzero(hit)
    ex = e[edge_index]
    x = ex[:, 0] + (ys[row] - ex[:, 1]) * (ex[:, 2] - ex[:, 0]) / (ex[:, 3] - ex[:, 1])
    order = np.lexsort((x, row))
    row, x = row[order], x[order]
    col = np.searchsorted(xs, x)
    starts = np.r_[0, np.flatnonzero(np.diff(row)) + 1]
    # Parity must restart on every row.
    parity = np.arange(len(x)) - np.repeat(starts, np.diff(np.r_[starts, len(x)]))
    sign = np.where(parity % 2 == 0, 1.0, -1.0)
    acc = np.zeros((ny, nx + 1), np.float32)
    np.add.at(acc, (row, col), sign)
    fine = np.cumsum(acc, axis=1)[:, :nx]
    out = np.zeros(shape, np.float32)
    out[j0:j1, i0:i1] = fine.reshape(j1 - j0, samples, i1 - i0, samples).mean(axis=(1, 3))
    return out


def project(polygon, matrix):
    def tf(coords):
        c = np.asarray(coords)
        q = np.c_[c, np.ones(len(c))] @ matrix.T
        return q[:, :2] / q[:, 2:]

    return Polygon(tf(polygon.exterior.coords), [tf(r.coords) for r in polygon.interiors])


def undistort_grid(u, v, k1, size):
    """Ideal pixel positions for distorted ones (Newton on the radial cubic)."""
    from backend.sheet import undistort_radius

    w, h = size
    cx, cy, s = w / 2, h / 2, math.hypot(w, h) / 2
    xd, yd = (u - cx) / s, (v - cy) / s
    rd = np.hypot(xd, yd)
    factor = np.divide(undistort_radius(rd, k1), rd, out=np.ones_like(rd), where=rd > 0)
    return cx + xd * factor * s, cy + yd * factor * s


def render(
    *,
    tilt=(22.0, -9.0, 4.0),
    k1=-0.035,
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
    k, rotation, t = camera(tilt, size)
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
    cast = cv2.GaussianBlur(
        cv2.warpAffine(bottom, np.float32([[1, 0, 1.6 * ppm], [0, 1, 1.9 * ppm]]), shape[::-1]),
        (0, 0),
        2.2 * ppm,
    )
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
    iu, iv = undistort_grid(u, v, k1, size)
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
    image = cv2.GaussianBlur(image, (0, 0), blur)
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
