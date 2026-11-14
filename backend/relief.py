"""Image-driven height fields: tactile reliefs and backlit lithophanes.

A photograph (or a grayscale depth map) becomes a thickness map t(x, y) in millimetres.
The map is meshed as one closed solid: a triangulated top surface, vertical side walls
and a flat base at z = 0. Every quantity reported to the user is computed from the
generated geometry or from the stated physical model; nothing here is a print guarantee.

Colour science
    8-bit photo samples are sRGB-encoded. They are decoded to linear light with the
    IEC 61966-2-1 transfer function and combined into relative luminance Y with the
    Rec. 709 / sRGB primaries (0.2126, 0.7152, 0.0722). Reliefs map *perceived*
    lightness (CIE 1976 L*) to height so equal height steps look like equal tone steps.
    Lithophanes target *linear* luminance because transmitted light is linear.

Lithophane physics
    Light crossing a uniform absorbing layer follows the Beer-Lambert law,
    T(t) = exp(-mu * t). Relative to the thinnest wall t_min the viewer sees
    Y = exp(-mu * (t - t_min)), so the required thickness is
    t = t_min - ln(Y) / mu. The material is described by its half-value thickness
    (the extra thickness that halves transmitted light), mu = ln 2 / HVL.
    Scattering in real filament makes this a first-order model; calibrate with the
    printed step wedge and :func:`fit_half_value`.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .three_mf import write_mesh_3mf
from .tracing import load_image

MAX_SAMPLES = 250_000  # Grid vertices in the exported surface (about 500 x 500).
PREVIEW_SIDE = 160  # Longest side of the browser preview grid, in samples.
FWHM_TO_SIGMA = 1 / (2 * math.sqrt(2 * math.log(2)))  # Gaussian sigma per unit FWHM.
LN2 = math.log(2)
BLENDER_SCRIPT = Path(__file__).with_name("blender_relief.py")
# Typical datasheet densities, g/cm^3, for an approximate mass only.
DENSITY = {"pla": 1.24, "petg": 1.27, "abs": 1.04, "asa": 1.07, "tpu": 1.21, "nylon": 1.14}
WEDGE_STEPS = 8
WEDGE_STEP_WIDTH = 10.0
WEDGE_HEIGHT = 25.0
WEDGE_RAMP = 0.02  # mm over which one wedge step rises to the next; far below a nozzle width.


class ReliefError(ValueError):
    """A request or image that cannot form a relief, with a user-facing message."""


class ReliefSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    name: str = Field(default="Relief", min_length=1, max_length=100)
    revision: int = Field(default=0, ge=0)
    mode: Literal["relief", "lithophane"] = "relief"
    # Relief only: a photo maps brightness to height; a depth map is used as stored data.
    source: Literal["photo", "depth"] = "photo"
    width_mm: float = Field(default=100, ge=10, le=400)
    min_mm: float = Field(default=1.6, ge=0.2, le=20)
    max_mm: float = Field(default=4.0, ge=0.4, le=40)
    invert: bool = False
    gamma: float = Field(default=1.0, ge=0.25, le=4)
    denoise: Literal["off", "light", "strong"] = "light"
    nozzle_mm: float = Field(default=0.4, ge=0.1, le=1.2)
    nozzle_filter: bool = True
    pitch_mm: float | None = Field(default=None, ge=0.05, le=5)
    frame_mm: float = Field(default=0, ge=0, le=20)
    half_value_mm: float = Field(default=0.5, ge=0.05, le=10)
    auto_levels: bool = True
    material: Literal["pla", "petg", "abs", "asa", "tpu", "nylon"] = "pla"
    color: str = Field(default="#e8e4da", pattern=r"^#[0-9a-fA-F]{6}$")
    # Sphere shape: a 2:1 equirectangular picture wrapped around a hollow ball whose wall
    # thickness follows the picture, cut flat at the bottom around a light opening.
    shape: Literal["flat", "sphere"] = "flat"
    sphere_diameter_mm: float = Field(default=100, ge=30, le=250)
    opening_mm: float = Field(default=35, ge=10, le=200)
    collar_mm: float = Field(default=3, ge=0, le=20)

    @model_validator(mode="after")
    def check_range(self):
        if self.max_mm - self.min_mm < 0.1:
            raise ValueError("Maximum thickness must exceed minimum thickness by at least 0.1 mm.")
        if self.shape == "sphere":
            inner = self.sphere_diameter_mm / 2 - self.max_mm
            if inner < 10:
                raise ValueError(
                    "The sphere is too small for its thickest wall. Enlarge the sphere or "
                    "thin the wall so the inside is at least 20 mm across."
                )
            if self.opening_mm / 2 > 0.9 * inner:
                raise ValueError(
                    "The opening must be narrower than 90% of the sphere's inside diameter."
                )
        self.color = self.color.lower()
        return self


# ---------------------------------------------------------------------------- colour


def srgb_to_linear(encoded):
    """IEC 61966-2-1 decoding of sRGB samples in 0..1 to linear light in 0..1."""
    v = np.asarray(encoded, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(linear):
    """Inverse of :func:`srgb_to_linear`."""
    v = np.clip(np.asarray(linear, dtype=np.float64), 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


def relative_luminance(rgb):
    """Relative luminance Y of linear Rec. 709 / sRGB primaries (last axis R, G, B)."""
    rgb = np.asarray(rgb, dtype=np.float64)
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def lightness(y):
    """CIE 1976 L* (0..100) of relative luminance Y (0..1) with a white of Y = 1."""
    y = np.clip(np.asarray(y, dtype=np.float64), 0, None)
    delta = 6 / 29
    f = np.where(y > delta**3, np.cbrt(y), y / (3 * delta**2) + 4 / 29)
    return 116 * f - 16


# ------------------------------------------------------------------------ lithophane


def attenuation(half_value_mm):
    """Beer-Lambert attenuation coefficient mu (per mm) of a half-value thickness."""
    return LN2 / half_value_mm


def lithophane_thickness(y, t_min, t_max, half_value_mm):
    """Invert Beer-Lambert: thickness giving relative transmission y (0..1).

    Returns ``(thickness, clipped)``: tones darker than the thickest wall can show are
    clamped to ``t_max``; ``clipped`` marks them.
    """
    mu = attenuation(half_value_mm)
    darkest = math.exp(-mu * (t_max - t_min))
    y = np.asarray(y, dtype=np.float64)
    clipped = y < darkest
    thickness = t_min - np.log(np.clip(y, darkest, 1)) / mu
    return np.clip(thickness, t_min, t_max), clipped


def transmission(thickness, t_min, half_value_mm):
    """Relative transmitted light exp(-mu (t - t_min)) predicted by Beer-Lambert."""
    return np.exp(-attenuation(half_value_mm) * (np.asarray(thickness) - t_min))


def fit_half_value(thickness_mm, readings, scale: Literal["srgb8", "linear"] = "srgb8"):
    """Least-squares Beer-Lambert fit of backlit step-wedge readings.

    ``readings`` are either 8-bit sRGB pixel values (0..255, from a photo taken with
    locked exposure) or linear light readings (a light meter, any unit). The log of
    linear light is regressed on thickness: ln Y = a - mu t. Camera values at or near
    either end of the range carry no slope information and are excluded.
    """
    t = np.asarray(thickness_mm, dtype=np.float64)
    r = np.asarray(readings, dtype=np.float64)
    if t.shape != r.shape or t.ndim != 1 or len(t) < 3:
        raise ReliefError("Enter at least three step readings, one per thickness.")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(r))):
        raise ReliefError("Readings must be numbers.")
    excluded = []
    if scale == "srgb8":
        if np.any((r < 0) | (r > 255)):
            raise ReliefError("Camera readings must be between 0 and 255.")
        usable = (r > 5) & (r < 250)
        excluded = [int(i) for i in np.flatnonzero(~usable)]
        y = srgb_to_linear(r / 255)
    else:
        if np.any(r < 0):
            raise ReliefError("Light readings cannot be negative.")
        usable = r > 0
        excluded = [int(i) for i in np.flatnonzero(~usable)]
        y = r
    t, y = t[usable], y[usable]
    if len(t) < 3 or np.ptp(t) <= 0:
        raise ReliefError(
            "At least three readings must be neither black nor saturated. "
            "Lower the camera exposure or use a dimmer light."
        )
    ln_y = np.log(y)
    design = np.column_stack([np.ones_like(t), t])
    (intercept, slope), *_ = np.linalg.lstsq(design, ln_y, rcond=None)
    mu = -slope
    if not math.isfinite(mu) or mu <= 0:
        raise ReliefError(
            "Brightness did not fall with thickness. Check the step order and keep exposure locked."
        )
    predicted = intercept + slope * t
    residual = ln_y - predicted
    total = float(np.sum((ln_y - ln_y.mean()) ** 2))
    r_squared = 1 - float(np.sum(residual**2)) / total if total > 0 else 1.0
    dof = len(t) - 2
    slope_se = (
        math.sqrt(float(np.sum(residual**2)) / dof / float(np.sum((t - t.mean()) ** 2)))
        if dof > 0
        else float("nan")
    )
    half_value = LN2 / mu
    half_value_se = LN2 * slope_se / mu**2 if math.isfinite(slope_se) else None
    return {
        "mu_per_mm": float(mu),
        "half_value_mm": float(half_value),
        "half_value_se_mm": half_value_se,
        "r_squared": float(r_squared),
        "used_points": len(t),
        "excluded_steps": excluded,
        "model": "ln(Y) = a - mu * t (Beer-Lambert, least squares)",
    }


# --------------------------------------------------------------------------- meshing


def heightfield_mesh(z, xs, ys, keys=None):
    """Close a height field into a watertight, outward-oriented triangle solid.

    ``z[r, c]`` is the top height at ``(xs[c], ys[r])``; ``xs`` increases and ``ys``
    decreases with the row index, so row 0 is the image top. Each grid cell is split
    along the diagonal with the smaller height change, which follows ridges and valleys
    instead of cutting across them. ``keys`` (the exact integer 16-bit levels) decides
    the diagonals when given, so ties break identically in Blender. Side walls drop vertically to a flat base at z = 0,
    triangulated as a fan around an interior centre vertex so no triangle is degenerate.
    """
    z = np.asarray(z, dtype=np.float64)
    ny, nx = z.shape
    xs, ys = np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64)
    if nx < 2 or ny < 2 or len(xs) != nx or len(ys) != ny:
        raise ReliefError("The height field needs at least two samples on each side.")
    if np.any(np.diff(xs) <= 0) or np.any(np.diff(ys) >= 0) or np.any(z <= 0):
        raise ReliefError("The height field grid is not valid.")
    grid_x, grid_y = np.meshgrid(xs, ys)
    top = np.column_stack([grid_x.ravel(), grid_y.ravel(), z.ravel()])
    index = np.arange(nx * ny).reshape(ny, nx)
    a, b = index[:-1, :-1].ravel(), index[:-1, 1:].ravel()  # upper-left, upper-right
    c, d = index[1:, :-1].ravel(), index[1:, 1:].ravel()  # lower-left, lower-right
    flat = z.ravel() if keys is None else np.asarray(keys, dtype=np.int64).ravel()
    along_ad = np.abs(flat[a] - flat[d]) <= np.abs(flat[b] - flat[c])
    tri_top = np.concatenate(
        [
            np.where(along_ad[:, None], np.column_stack([c, d, a]), np.column_stack([c, d, b])),
            np.where(along_ad[:, None], np.column_stack([d, b, a]), np.column_stack([c, b, a])),
        ]
    )
    # Boundary ring, counter-clockwise seen from above, starting at the lower-left corner.
    ring = np.concatenate(
        [
            index[-1, :],  # bottom edge, left to right
            index[-2::-1, -1],  # right edge, upward
            index[0, -2::-1],  # top edge, right to left
            index[1:-1, 0],  # left edge, downward (corner closes the ring)
        ]
    )
    base_start = nx * ny
    count = len(ring)
    base = top[ring].copy()
    base[:, 2] = 0
    centre = np.array([[(xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2, 0.0]])
    vertices = np.concatenate([top, base, centre])
    centre_index = base_start + count
    p, q = np.arange(count), (np.arange(count) + 1) % count
    tp, tq, bp, bq = ring[p], ring[q], base_start + p, base_start + q
    walls = np.concatenate([np.column_stack([bp, bq, tq]), np.column_stack([bp, tq, tp])])
    floor = np.column_stack([np.full(count, centre_index), bq, bp])
    triangles = np.concatenate([tri_top, walls, floor]).astype(np.int64)
    return vertices, triangles


def mesh_report(vertices, triangles):
    """Independent topology and volume checks of a closed triangle mesh.

    The mesh is closed and consistently oriented when every directed edge occurs once
    and its reverse occurs once. A closed orientable surface of genus g satisfies
    V - E + F = 2 - 2g; a relief must be a sphere-like solid (g = 0). The volume is the
    divergence-theorem sum of signed tetrahedra, computed in float64 with fsum.
    """
    v, f = np.asarray(vertices, dtype=np.float64), np.asarray(triangles, dtype=np.int64)
    edges = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    n = len(v)
    forward = edges[:, 0] * n + edges[:, 1]
    reverse = edges[:, 1] * n + edges[:, 0]
    unique, counts = np.unique(forward, return_counts=True)
    closed = bool(
        np.all(counts == 1) and len(unique) == len(forward) and np.all(np.isin(reverse, unique))
    )
    edge_count = len(forward) // 2
    euler = n - edge_count + len(f)
    p0, p1, p2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    cross = np.cross(p1 - p0, p2 - p0)
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    volume = math.fsum(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).tolist()) / 6
    lower, upper = v.min(axis=0), v.max(axis=0)
    return {
        "vertices": int(n),
        "triangles": len(f),
        "edges": edge_count,
        "euler_characteristic": int(euler),
        "genus": (2 - int(euler)) // 2,
        "closed_and_oriented": closed,
        "min_triangle_area_mm2": float(areas.min()),
        "surface_area_mm2": math.fsum(areas.tolist()),
        "volume_mm3": volume,
        "bounds_mm": {"min": lower.tolist(), "max": upper.tolist()},
    }


def heightfield_volume(z, xs, ys, keys=None):
    """Volume of the meshed height field from the top surface alone.

    For a solid whose base lies on z = 0 and whose walls are vertical, the divergence
    theorem with the field (0, 0, z) reduces the volume to the sum over top triangles of
    (projected area) x (mean vertex height). Each grid cell's two triangles each project
    to half the cell, so this needs only the heights and the chosen diagonals.
    """
    z = np.asarray(z, dtype=np.float64)
    dx, dy = np.diff(xs), -np.diff(ys)
    cell_area = dy[:, None] * dx[None, :]
    za, zb = z[:-1, :-1], z[:-1, 1:]
    zc, zd = z[1:, :-1], z[1:, 1:]
    k = z if keys is None else np.asarray(keys, dtype=np.int64)
    along_ad = np.abs(k[:-1, :-1] - k[1:, 1:]) <= np.abs(k[:-1, 1:] - k[1:, :-1])
    # Diagonal a-d: triangles (c, d, a) and (d, b, a); diagonal b-c: (c, d, b), (c, b, a).
    sums = np.where(along_ad, (zc + zd + za) + (zd + zb + za), (zc + zd + zb) + (zc + zb + za))
    return math.fsum((cell_area / 2 * sums / 3).ravel().tolist())


def write_binary_stl(path: Path, vertices, triangles, header=b"Pictures to CAD relief (mm)"):
    v, f = np.asarray(vertices, dtype=np.float64), np.asarray(triangles, dtype=np.int64)
    p0, p1, p2 = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    normal = np.cross(p1 - p0, p2 - p0)
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    record = np.zeros(
        len(f),
        dtype=[("n", "<f4", 3), ("a", "<f4", 3), ("b", "<f4", 3), ("c", "<f4", 3), ("attr", "<u2")],
    )
    record["n"], record["a"], record["b"], record["c"] = normal, p0, p1, p2
    with open(path, "wb") as handle:
        handle.write(header[:80].ljust(80, b" "))
        handle.write(np.uint32(len(f)).tobytes())
        handle.write(record.tobytes())


# ---------------------------------------------------------------------- image fields


def _sample(field, nx, ny):
    """Sample a field at nx x ny grid points spanning the image edge to edge.

    Grid point (i, j) sits at x = i / (nx - 1) of the image width, in the pixel-edge
    frame where the image spans [0, w]. When the grid is coarser than the pixels a
    Gaussian pre-filter (sigma = half the sample step) removes detail the grid cannot
    represent, which would otherwise alias into false patterns.
    """
    h, w = field.shape
    step_x, step_y = w / (nx - 1), h / (ny - 1)
    if step_x > 1 or step_y > 1:
        field = cv2.GaussianBlur(
            field,
            (0, 0),
            sigmaX=max(step_x / 2, 0.01),
            sigmaY=max(step_y / 2, 0.01),
            borderType=cv2.BORDER_REPLICATE,
        )
    map_x = np.clip(np.linspace(0, w, nx) - 0.5, 0, w - 1).astype(np.float32)
    map_y = np.clip(np.linspace(0, h, ny) - 0.5, 0, h - 1).astype(np.float32)
    grid_x, grid_y = np.meshgrid(map_x, map_y)
    return cv2.remap(field, grid_x, grid_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def _image_fields(image):
    """Return (linear luminance Y, display value) arrays in 0..1 and the source kind."""
    if image.mode == "F":
        depth = np.asarray(image, dtype=np.float32)
        return depth.astype(np.float64), depth.astype(np.float64), "16-bit grayscale"
    rgb = np.asarray(image.convert("RGB"), dtype=np.float64) / 255
    y = relative_luminance(srgb_to_linear(rgb))
    gray = np.asarray(image.convert("L"), dtype=np.float64) / 255
    return y, gray, "8-bit sRGB"


def _png_data_url(values, max_side=480):
    """Encode a 0..1 array, already display-encoded, as a small PNG data URL."""
    image = Image.fromarray(np.round(np.clip(values, 0, 1) * 255).astype(np.uint8), "L")
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _grid_size(settings, aspect):
    height_mm = settings.width_mm * aspect
    requested = settings.pitch_mm or max(settings.nozzle_mm / 2, 0.1)
    pitch = requested
    notices = []
    for _ in range(64):
        nx = max(2, round(settings.width_mm / pitch) + 1)
        ny = max(2, round(height_mm / pitch) + 1)
        if nx * ny <= MAX_SAMPLES:
            break
        pitch *= math.sqrt(nx * ny / MAX_SAMPLES) * 1.001
    if pitch > requested * 1.0001:
        notices.append(
            f"Sample spacing was widened from {requested:.3f} mm to {pitch:.3f} mm to keep the "
            f"surface under {MAX_SAMPLES:,} points. Reduce the width for finer sampling."
        )
    return nx, ny, height_mm, notices


def tone_to_thickness(values, settings):
    """Map sampled tone (0..1) to wall thickness in mm, shared by every shape.

    Returns ``(thickness, clipped, target, stats)``. A lithophane inverts Beer-Lambert
    for the target transmission ``target``; ``clipped`` marks tones darker than the
    thickest wall can show. A relief maps (optionally stretched) tone to height.
    """
    t_min, t_max = settings.min_mm, settings.max_mm
    span = t_max - t_min
    stats = {}
    if settings.mode == "lithophane":
        white = float(np.percentile(values, 99.5)) if settings.auto_levels else 1.0
        target = np.clip(values / max(white, 1e-6), 0, 1)
        thickness, clipped = lithophane_thickness(target, t_min, t_max, settings.half_value_mm)
        stats["auto_levels_white"] = white
        return thickness, clipped, target, stats
    v = np.clip(values, 0, 1)
    if settings.auto_levels:
        # Stretch the 0.5th-99.5th percentile tones to the full thickness range, so the
        # chosen thinnest and thickest walls are reached by the picture itself.
        low, high = (float(q) for q in np.percentile(v, [0.5, 99.5]))
        if high - low > 1e-6:
            v = np.clip((v - low) / (high - low), 0, 1)
        stats["auto_levels_range"] = [low, high]
    if settings.invert:
        v = 1 - v
    thickness = t_min + span * v**settings.gamma
    return thickness, np.zeros_like(thickness, dtype=bool), None, stats


def build_relief(data: bytes, settings: ReliefSettings, job_dir: Path) -> dict:
    """Compute the thickness map, mesh it, verify it and write every export."""
    if settings.shape == "sphere":
        from .sphere import build_sphere

        return build_sphere(data, settings, job_dir)
    image, notices = load_image(data, keep_depth=True)
    notices = list(notices)
    luminance, display, sample_kind = _image_fields(image)
    w_px, h_px = image.size
    aspect = h_px / w_px
    if not 0.05 <= aspect <= 20:
        raise ReliefError("The image is too narrow. Crop it closer to the subject.")
    nx, ny, height_mm, grid_notices = _grid_size(settings, aspect)
    notices.extend(grid_notices)
    pitch_x, pitch_y = settings.width_mm / (nx - 1), height_mm / (ny - 1)
    pixel_mm = settings.width_mm / w_px
    t_min, t_max = settings.min_mm, settings.max_mm
    span = t_max - t_min
    lithophane = settings.mode == "lithophane"
    is_depth = image.mode == "F" or (settings.source == "depth" and not lithophane)

    # 1. The quantity that drives thickness, sampled on the grid.
    if lithophane:
        field = luminance
    elif is_depth:
        # A depth map is data, not light: use its stored values without colour decoding.
        field = display
    else:
        field = lightness(luminance) / 100
    if image.mode == "F" and not lithophane and settings.source == "photo":
        notices.append("A 16-bit grayscale image was used as a depth map (white = nearest).")
    values = _sample(field.astype(np.float32), nx, ny).astype(np.float64)

    # 2. Edge-preserving noise reduction: a bilateral filter averages similar tones only.
    if settings.denoise != "off":
        spatial, tonal = {"light": (1.0, 0.04), "strong": (2.0, 0.10)}[settings.denoise]
        sigma_px = spatial * max(1.0, pixel_mm / pitch_x)
        values = cv2.bilateralFilter(
            values.astype(np.float32), d=-1, sigmaColor=tonal, sigmaSpace=sigma_px
        ).astype(np.float64)

    # 3. Tone to thickness.
    thickness_raw, clipped, target, stats = tone_to_thickness(values, settings)

    # 4. Nozzle-width low-pass: a Gaussian whose full width at half maximum equals the
    # nozzle width. Detail narrower than the extruded line cannot be printed laterally.
    if settings.nozzle_filter:
        sigma_mm = settings.nozzle_mm * FWHM_TO_SIGMA
        thickness = cv2.GaussianBlur(
            thickness_raw,
            (0, 0),
            sigmaX=max(sigma_mm / pitch_x, 1e-3),
            sigmaY=max(sigma_mm / pitch_y, 1e-3),
            borderType=cv2.BORDER_REPLICATE,
        )
    else:
        thickness = thickness_raw.copy()
    removed = thickness_raw - thickness
    thickness = np.clip(thickness, t_min, t_max)

    # 5. Optional frame at full thickness, outside the image area.
    frame_x = round(settings.frame_mm / pitch_x) if settings.frame_mm else 0
    frame_y = round(settings.frame_mm / pitch_y) if settings.frame_mm else 0
    if frame_x or frame_y:
        thickness = np.pad(
            thickness, ((frame_y, frame_y), (frame_x, frame_x)), constant_values=t_max
        )

    # 6. 16-bit quantization shared by the mesh, the height-map PNG and Blender, so every
    # export describes identical geometry. The step is span / 65535.
    levels = np.round((thickness - t_min) / span * 65535).astype(np.uint16)
    thickness = t_min + levels.astype(np.float64) / 65535 * span
    gy, gx = thickness.shape
    xs = np.arange(gx) * pitch_x
    ys = (gy - 1 - np.arange(gy)) * pitch_y
    vertices, triangles = heightfield_mesh(thickness, xs, ys, keys=levels)
    report = mesh_report(vertices, triangles)
    surface_volume = heightfield_volume(thickness, xs, ys, keys=levels)
    if not report["closed_and_oriented"] or report["genus"] != 0:
        raise ReliefError("The generated surface did not close into a solid. Try again.")
    if not math.isclose(report["volume_mm3"], surface_volume, rel_tol=1e-9):
        raise ReliefError("The generated solid did not pass its volume cross-check.")

    # Exports.
    write_binary_stl(job_dir / "model.stl", vertices, triangles)
    write_mesh_3mf(
        job_dir / "model.3mf",
        vertices,
        triangles,
        name=settings.name,
        object_name="Lithophane" if lithophane else "Relief",
    )
    cv2.imwrite(str(job_dir / "heightmap.png"), levels)
    dims = {
        "width": float(xs[-1]),
        "height": float(ys[0]),
        "thickness": float(thickness.max()),
        "min_thickness": float(thickness.min()),
    }
    volume = report["volume_mm3"]
    density = DENSITY[settings.material]
    gradient_y, gradient_x = np.gradient(thickness, pitch_y, pitch_x)
    slope = np.degrees(np.arctan(np.hypot(gradient_x, gradient_y)))
    stats.update(
        {
            "grid": {
                "columns": int(gx),
                "rows": int(gy),
                "pitch_x_mm": pitch_x,
                "pitch_y_mm": pitch_y,
                "image_pixel_mm": pixel_mm,
            },
            "source": {"width_px": w_px, "height_px": h_px, "samples": sample_kind},
            "nozzle_filter": {
                "enabled": settings.nozzle_filter,
                "fwhm_mm": settings.nozzle_mm,
                "sigma_mm": settings.nozzle_mm * FWHM_TO_SIGMA,
                "removed_rms_mm": float(np.sqrt(np.mean(removed**2))),
                "removed_max_mm": float(np.max(np.abs(removed))),
            },
            "quantization_step_mm": span / 65535,
            "slope_deg": {"max": float(slope.max()), "p95": float(np.percentile(slope, 95))},
            "mass_g": volume / 1000 * density,
            "density_g_cm3": density,
            "mesh": report,
            "volume_cross_check_mm3": surface_volume,
            "volume_check": {
                "label": "top triangles' projected area × mean height",
                "value_mm3": surface_volume,
                "rel_tol": 1e-9,
            },
        }
    )
    if lithophane:
        mu = attenuation(settings.half_value_mm)
        inner = thickness[frame_y : gy - frame_y or None, frame_x : gx - frame_x or None]
        predicted = transmission(inner, t_min, settings.half_value_mm)
        target_lstar = lightness(target)
        error = np.abs(lightness(predicted) - target_lstar)
        # Tone accuracy is reported where the panel can physically show the tone; clipped
        # shadows are counted separately rather than inflating the reproduction error.
        in_range = error[~clipped] if np.any(~clipped) else error
        contrast = math.exp(mu * span)
        stats["optics"] = {
            "mu_per_mm": mu,
            "half_value_mm": settings.half_value_mm,
            "contrast_ratio": contrast,
            "dynamic_range_stops": span / settings.half_value_mm,
            "darkest_transmission": math.exp(-mu * span),
            "clipped_fraction": float(np.mean(clipped)),
            "tone_error_lstar_mean": float(in_range.mean()),
            "tone_error_lstar_p95": float(np.percentile(in_range, 95)),
            "tone_error_lstar_mean_all": float(error.mean()),
        }
        preview = linear_to_srgb(transmission(thickness, t_min, settings.half_value_mm))
        if stats["optics"]["clipped_fraction"] > 0.02:
            notices.append(
                f"{stats['optics']['clipped_fraction']:.0%} of the picture is darker than the "
                f"panel's {contrast:.0f}:1 range can show; it prints at full thickness, as dark "
                "as this panel gets. For deeper shadows raise the thickest wall or use a less "
                "translucent filament (smaller half-value thickness)."
            )
    else:
        preview = (thickness - t_min) / span
    if pitch_x < pixel_mm * 0.75:
        notices.append(
            f"The surface is sampled every {pitch_x:.3f} mm but each photo pixel covers "
            f"{pixel_mm:.3f} mm; the extra samples interpolate and add no detail."
        )
    if pitch_x > settings.nozzle_mm:
        notices.append(
            f"Sample spacing ({pitch_x:.2f} mm) is wider than the nozzle ({settings.nozzle_mm} mm);"
            " fine detail is limited by the sampling, not the printer."
        )
    notices.append(
        "STL and 3MF coordinates are in millimetres. A height field has no overhangs when "
        "printed flat; check orientation, supports and first-layer fit in your slicer."
    )

    recipe = {
        "format": "pictures-to-cad-relief",
        "version": 1,
        "settings": settings.model_dump(),
        "units": "mm",
        "provenance": "Thickness derived from image tone by the stated model; the source image is not stored.",
    }
    (job_dir / "project.json").write_text(
        json.dumps(recipe, indent=2, allow_nan=False), encoding="utf-8"
    )
    write_blender_bundle(job_dir, settings, dims, gx, gy, pitch_x, pitch_y, frame_x, frame_y)
    downloads = {
        kind: f"/api/download/{job_dir.name}/{kind}"
        for kind in ("stl", "3mf", "heightmap", "blender", "project")
    }
    if lithophane:
        write_wedge(job_dir, t_min, t_max)
        downloads["wedge"] = f"/api/download/{job_dir.name}/wedge"
        stats["wedge_mm"] = wedge_thicknesses(t_min, t_max)

    preview_mesh = _preview_mesh(thickness, xs, ys)
    return {
        "id": job_dir.name,
        "kind": settings.mode,
        "revision": settings.revision,
        "dimensions": dims,
        "volume_mm3": volume,
        "stats": stats,
        "mesh": preview_mesh,
        "preview_image": _png_data_url(preview),
        "downloads": downloads,
        "warnings": notices,
        "settings": settings.model_dump(),
    }


def _preview_mesh(thickness, xs, ys):
    """A coarser closed mesh of the same surface for the browser viewer."""
    gy, gx = thickness.shape
    stride = max(1, math.ceil(max(gx, gy) / PREVIEW_SIDE))
    cols = np.unique(np.append(np.arange(0, gx, stride), gx - 1))
    rows = np.unique(np.append(np.arange(0, gy, stride), gy - 1))
    # Area-average rather than pick every Nth sample, so the coarser preview does not alias
    # sharp edges into a sawtooth. Exports always use the full-resolution surface.
    heights = (
        cv2.resize(thickness, (len(cols), len(rows)), interpolation=cv2.INTER_AREA)
        if stride > 1
        else thickness
    )
    vertices, triangles = heightfield_mesh(heights, xs[cols], ys[rows])
    centre = np.array([(xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2, 0])
    vertices = vertices - centre  # The viewer frames the part about the origin.
    return {
        "vertices": np.round(vertices, 3).ravel().tolist(),
        "triangles": triangles.ravel().tolist(),
    }


# ------------------------------------------------------------------ calibration wedge


def wedge_thicknesses(t_min, t_max, steps=WEDGE_STEPS):
    return [t_min + (t_max - t_min) * k / (steps - 1) for k in range(steps)]


def wedge_mesh(t_min, t_max, steps=WEDGE_STEPS):
    """A step wedge, thinnest step at x = 0, each WEDGE_STEP_WIDTH wide.

    It reuses the height-field mesher on a non-uniform grid: each riser is a ramp of
    WEDGE_RAMP mm, so every face keeps a positive area while printing as a vertical step.
    """
    levels = wedge_thicknesses(t_min, t_max, steps)
    xs, heights = [0.0], [levels[0]]
    for k in range(steps):
        start, end = k * WEDGE_STEP_WIDTH, (k + 1) * WEDGE_STEP_WIDTH
        if k:
            xs.append(start + WEDGE_RAMP / 2)
            heights.append(levels[k])
        if k < steps - 1:
            xs.append(end - WEDGE_RAMP / 2)
        else:
            xs.append(end)
        heights.append(levels[k])
    xs = np.array(xs)
    ys = np.array([WEDGE_HEIGHT, 0.0])
    z = np.vstack([heights, heights])
    return heightfield_mesh(z, xs, ys), (z, xs, ys)


def write_wedge(job_dir: Path, t_min, t_max):
    (vertices, triangles), _ = wedge_mesh(t_min, t_max)
    write_binary_stl(
        job_dir / "calibration-wedge.stl",
        vertices,
        triangles,
        header=b"Pictures to CAD lithophane step wedge (mm)",
    )


# ------------------------------------------------------------------- Blender handoff


BLENDER_README = """# Relief in Blender

This folder rebuilds the generated relief as an editable Blender scene. It was written
for Blender 4.2 LTS or later and checked with Blender 5.3. Units are millimetres.

## Open it

- **Automatic:** in a terminal, from this folder, run
  `blender --python build_relief.py`
- **From Blender:** open Blender, switch to the *Scripting* workspace, open
  `build_relief.py` from this folder and press *Run Script*.

The script reads `relief.json` and `heightmap.png` from its own folder. It does not
download anything or change Blender preferences.

## What you get

- `Relief` - a closed solid built the same way as `model.stl`. A flat relief has a
  flat base, vertical walls and a top surface lifted by a **Displace** modifier that
  reads `heightmap.png` (16-bit, one pixel per vertex). A sphere's outer surface is
  moved outward along each radius by a **Geometry Nodes** modifier ("Radial height")
  reading the same map. Change *Strength* to rescale the height live; it equals
  maximum minus minimum thickness.
- A camera and lights. Lithophanes get a Cycles scene with a *Volume Absorption*
  material whose density is the attenuation coefficient mu (per mm), so a render
  shows the Beer-Lambert prediction: a flat panel is lit by a backlight behind it, a
  lamp by an emitting sphere just inside its wall. Reliefs get a low raking light
  that shows surface detail.
- `model.stl` - the exact exported geometry, if you prefer to import a mesh instead.

To print a version you edited in Blender, export STL with *Apply Modifiers* on and
re-check its dimensions in your slicer. Edits in Blender do not update the workbench.

## Optional command-line checks

```
blender -b --python build_relief.py -- --report report.json --export-stl out.stl
```

writes the evaluated mesh's vertex count, bounds and volume, and an STL of the
evaluated (displaced) solid.
"""


def write_blender_bundle(
    job_dir, settings, dims, columns, rows, pitch_x, pitch_y, frame_x, frame_y, extra=None
):
    lithophane = settings.mode == "lithophane"
    config = {
        "format": "pictures-to-cad-blender-relief",
        "version": 1,
        "name": settings.name,
        "mode": settings.mode,
        "units": "mm",
        "heightmap": "heightmap.png",
        "columns": columns,
        "rows": rows,
        "pitch_x_mm": pitch_x,
        "pitch_y_mm": pitch_y,
        "min_mm": settings.min_mm,
        "max_mm": settings.max_mm,
        "frame_columns": frame_x,
        "frame_rows": frame_y,
        "color": settings.color,
        "mu_per_mm": attenuation(settings.half_value_mm) if lithophane else None,
        "half_value_mm": settings.half_value_mm if lithophane else None,
        "dimensions_mm": dims,
        "diagonal_rule": "split each cell along the diagonal with the smaller height change",
        "shape": settings.shape,
        **(extra or {}),
    }
    payload = {
        "build_relief.py": BLENDER_SCRIPT.read_bytes(),
        "relief.json": (json.dumps(config, indent=2, allow_nan=False) + "\n").encode("utf-8"),
        "heightmap.png": (job_dir / "heightmap.png").read_bytes(),
        "model.stl": (job_dir / "model.stl").read_bytes(),
        "README.md": BLENDER_README.encode("utf-8"),
    }
    manifest = {
        "format": "pictures-to-cad-blender-handoff",
        "version": 1,
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
            for name, data in payload.items()
        },
        "notes": [
            "No source photograph is included.",
            "The script only builds a scene from the files in this folder.",
        ],
    }
    with zipfile.ZipFile(
        job_dir / "blender-relief.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name, data in payload.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2).encode("utf-8"))
