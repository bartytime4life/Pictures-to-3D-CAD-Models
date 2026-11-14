"""Spherical reliefs and lithophanes: a picture wrapped around a hollow ball.

The picture is read as an equirectangular (2:1 "world map") image: its horizontal axis
is longitude, 0 to 360 degrees eastward, and its vertical axis is colatitude, from the
north pole (top row) to the south pole (bottom row). The wall thickness t(theta, lambda)
comes from the same tone mapping as a flat relief or lithophane.

Geometry (millimetres, z up, the opening at the bottom):

* The inner surface is a sphere of radius R_in = D / 2 - t_max.
* The outer surface sits at radius R_in + t along each direction, so a lamp at the
  centre shines radially through exactly t of material: Beer-Lambert applies unchanged.
* A horizontal plane cuts both surfaces at the depth where the inner sphere's opening
  has the requested diameter. A collar band at full thickness keeps the outer cut on a
  circle, so the flat annulus between the two cuts can stand on a print bed.

Topologically the solid is a thick bowl: one closed surface of genus 0.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from .relief import (
    DENSITY,
    FWHM_TO_SIGMA,
    ReliefError,
    _image_fields,
    _png_data_url,
    attenuation,
    lightness,
    linear_to_srgb,
    mesh_report,
    tone_to_thickness,
    transmission,
    write_binary_stl,
    write_blender_bundle,
)
from .three_mf import write_mesh_3mf
from .tracing import load_image

MAX_OUTER_SAMPLES = 200_000  # Outer-surface grid points (rows x longitudes).
INNER_ROW_FACTOR = 4  # The smooth inner sphere needs fewer rows than the picture.
PREVIEW_COLUMNS = 160
OVERHANG_DEGREES = 45.0


def sphere_frame(settings):
    """Radii, cut angles and cut height of the requested sphere."""
    r_out = settings.sphere_diameter_mm / 2
    r_in = r_out - settings.max_mm
    half_opening = settings.opening_mm / 2
    theta_in = math.pi - math.asin(half_opening / r_in)
    z_cut = r_in * math.cos(theta_in)  # Negative: below the centre.
    theta_out = math.acos(z_cut / r_out)
    return {
        "r_out": r_out,
        "r_in": r_in,
        "theta_in": theta_in,
        "theta_out": theta_out,
        "z_cut": z_cut,
    }


def _grid(settings, frame):
    """Longitude count L and outer row count n (row 0 is the north pole)."""
    requested = settings.pitch_mm or max(settings.nozzle_mm / 2, 0.1)
    pitch = requested
    for _ in range(64):
        columns = max(24, round(2 * math.pi * frame["r_out"] / pitch))
        rows = max(6, round(frame["theta_out"] * frame["r_out"] / pitch) + 1)
        if columns * rows <= MAX_OUTER_SAMPLES:
            break
        pitch *= math.sqrt(columns * rows / MAX_OUTER_SAMPLES) * 1.001
    notices = []
    if pitch > requested * 1.0001:
        notices.append(
            f"Sample spacing at the equator was widened from {requested:.3f} mm to {pitch:.3f} mm "
            f"to keep the surface under {MAX_OUTER_SAMPLES:,} points."
        )
    return columns, rows, notices


def sample_equirect(field, columns, thetas):
    """Sample an equirectangular field at longitudes j/L * 360 deg and colatitudes thetas.

    The image's left and right edges are the same meridian, so it is padded by wrapping
    before the anti-aliasing Gaussian (sigma = half the sample step) and the bilinear
    lookup. The pole row is averaged: every longitude there is the same point.
    """
    h, w = field.shape
    step_x = w / columns
    step_y = (h / math.pi) * (thetas[1] - thetas[0])
    sigma_x, sigma_y = max(step_x / 2, 0.01), max(step_y / 2, 0.01)
    pad = math.ceil(4 * sigma_x) + 2
    wrapped = np.pad(field, ((0, 0), (pad, pad)), mode="wrap")
    if step_x > 1 or step_y > 1:
        wrapped = cv2.GaussianBlur(
            wrapped, (0, 0), sigmaX=sigma_x, sigmaY=sigma_y, borderType=cv2.BORDER_REFLECT
        )
    map_x = (np.arange(columns) / columns * w - 0.5 + pad).astype(np.float32)
    map_y = np.clip(np.asarray(thetas) / math.pi * h - 0.5, 0, h - 1).astype(np.float32)
    grid_x, grid_y = np.meshgrid(map_x, map_y)
    values = cv2.remap(
        wrapped, grid_x, grid_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    ).astype(np.float64)
    values[0, :] = values[0].mean()
    return values


def nozzle_filter(thickness, thetas, radius, sigma_mm):
    """Gaussian low-pass of width sigma_mm measured on the sphere's surface.

    Along a meridian one row is radius * d_theta long, so a single sigma applies. Along a
    parallel the spacing shrinks to radius * sin(theta) * d_lambda, so each row gets its
    own sigma, applied as a circular (wrap-around) convolution in the Fourier domain:
    the Gaussian's transfer function is exp(-2 pi^2 sigma^2 f^2).
    """
    _rows, columns = thickness.shape
    d_theta = thetas[1] - thetas[0]
    smoothed = cv2.GaussianBlur(
        thickness,
        (0, 0),
        sigmaX=1e-3,
        sigmaY=max(sigma_mm / (radius * d_theta), 1e-3),
        borderType=cv2.BORDER_REPLICATE,
    )
    d_lambda = 2 * math.pi / columns
    ring = radius * np.maximum(np.sin(thetas), 1e-9) * d_lambda
    sigma_columns = sigma_mm / ring
    frequency = np.fft.rfftfreq(columns)
    gain = np.exp(-2 * math.pi**2 * sigma_columns[:, None] ** 2 * frequency[None, :] ** 2)
    smoothed = np.fft.irfft(np.fft.rfft(smoothed, axis=1) * gain, n=columns, axis=1)
    smoothed[0, :] = smoothed[0].mean()
    return smoothed


def _directions(thetas, columns):
    lambdas = np.arange(columns) * 2 * math.pi / columns
    st, ct = np.sin(thetas)[:, None], np.cos(thetas)[:, None]
    return np.stack(
        [
            st * np.cos(lambdas)[None, :],
            st * np.sin(lambdas)[None, :],
            np.broadcast_to(ct, (len(thetas), columns)),
        ],
        axis=-1,
    )


def sphere_mesh(radii, thetas, inner_radius, inner_thetas, keys=None):
    """Close the outer surface, inner sphere and flat cut annulus into one solid.

    ``radii[i, j]`` is the outer radius at colatitude ``thetas[i]`` (row 0 is the pole)
    and longitude 2 pi j / L. Outer cells split along the diagonal with the smaller
    radius change, compared on ``keys`` when given (the exact integer 16-bit levels, so
    ties break identically in every program); the inner sphere uses a fixed diagonal. Returns vertices about the
    sphere centre and int64 triangles, outward-oriented.
    """
    rows, columns = radii.shape
    inner_rows = len(inner_thetas)
    keys = radii if keys is None else np.asarray(keys, dtype=np.int64)
    outer_dir = _directions(thetas, columns)
    inner_dir = _directions(np.asarray(inner_thetas), columns)
    outer = [
        np.array([[0.0, 0.0, radii[0, 0]]]),
        (outer_dir[1:] * radii[1:, :, None]).reshape(-1, 3),
    ]
    inner = [np.array([[0.0, 0.0, inner_radius]]), (inner_dir[1:] * inner_radius).reshape(-1, 3)]
    vertices = np.concatenate(outer + inner)
    inner_base = 1 + (rows - 1) * columns
    j = np.arange(columns)
    jn = (j + 1) % columns

    def ring(base, i):  # Index of every vertex in ring i (i >= 1) of a surface.
        return base + 1 + (i - 1) * columns + j

    def ring_next(base, i):
        return base + 1 + (i - 1) * columns + jn

    triangles = []
    # Outer: pole fan, then bands.
    triangles.append(
        np.column_stack([np.zeros(columns, dtype=np.int64), ring(0, 1), ring_next(0, 1)])
    )
    for i in range(1, rows - 1):
        a, b, c, d = ring(0, i), ring_next(0, i), ring(0, i + 1), ring_next(0, i + 1)
        ra, rb = keys[i, j], keys[i, jn]
        rc, rd = keys[i + 1, j], keys[i + 1, jn]
        along_ad = np.abs(ra - rd) <= np.abs(rb - rc)
        triangles.append(
            np.where(along_ad[:, None], np.column_stack([c, d, a]), np.column_stack([c, d, b]))
        )
        triangles.append(
            np.where(along_ad[:, None], np.column_stack([d, b, a]), np.column_stack([c, b, a]))
        )
    # Inner: the same pattern with every triangle reversed, so normals face the centre.
    pole = np.full(columns, inner_base, dtype=np.int64)
    triangles.append(np.column_stack([pole, ring_next(inner_base, 1), ring(inner_base, 1)]))
    for i in range(1, inner_rows - 1):
        a, b = ring(inner_base, i), ring_next(inner_base, i)
        c, d = ring(inner_base, i + 1), ring_next(inner_base, i + 1)
        triangles.append(np.column_stack([a, d, c]))
        triangles.append(np.column_stack([a, b, d]))
    # Flat annulus between the two cut rings, facing down.
    outer_last, outer_next = ring(0, rows - 1), ring_next(0, rows - 1)
    inner_last, inner_next = ring(inner_base, inner_rows - 1), ring_next(inner_base, inner_rows - 1)
    triangles.append(np.column_stack([outer_next, outer_last, inner_last]))
    triangles.append(np.column_stack([inner_last, inner_next, outer_next]))
    return vertices, np.concatenate(triangles).astype(np.int64)


def smooth_volume(radii, thetas, frame):
    """Volume of the smooth solid the mesh approximates, by numerical integration.

    The region above the cut plane inside a star-shaped surface r(theta, lambda) is the
    solid-angle integral of r^3 / 3 over theta <= theta_cut plus the cone from the centre
    to the cut disc. The inner cap has a closed form.
    """
    mean_cube = (radii**3).mean(axis=1) / 3
    outer = 2 * math.pi * np.trapezoid(mean_cube * np.sin(thetas), thetas)
    depth = -frame["z_cut"]
    outer += math.pi / 3 * (frame["r_out"] * math.sin(frame["theta_out"])) ** 2 * depth
    r_in, theta_in = frame["r_in"], frame["theta_in"]
    inner = 2 * math.pi * r_in**3 / 3 * (1 - math.cos(theta_in))
    inner += math.pi / 3 * (r_in * math.sin(theta_in)) ** 2 * depth
    return float(outer - inner)


def overhang_area(vertices, triangles, degrees=OVERHANG_DEGREES):
    """Downward-facing area steeper than `degrees` from vertical, excluding the bed face."""
    p0, p1, p2 = (vertices[triangles[:, k]] for k in range(3))
    cross = np.cross(p1 - p0, p2 - p0)
    area = 0.5 * np.linalg.norm(cross, axis=1)
    nz = cross[:, 2] / np.maximum(2 * area, 1e-300)
    on_bed = np.all(np.abs(np.stack([p0[:, 2], p1[:, 2], p2[:, 2]])) < 1e-9, axis=0)
    down = (nz < -math.cos(math.radians(degrees))) & ~on_bed
    return float(area[down].sum()), float(area.sum())


def build_sphere(data, settings, job_dir):
    image, notices = load_image(data, keep_depth=True)
    notices = list(notices)
    luminance, display, sample_kind = _image_fields(image)
    w_px, h_px = image.size
    if abs(w_px / h_px - 2) > 0.1:
        notices.append(
            f"The picture is {w_px} × {h_px} pixels, not a 2:1 world map; it was stretched to "
            "wrap the sphere. Use an equirectangular image for undistorted results."
        )
    frame = sphere_frame(settings)
    columns, rows, grid_notices = _grid(settings, frame)
    notices.extend(grid_notices)
    thetas = np.linspace(0, frame["theta_out"], rows)
    t_min, t_max = settings.min_mm, settings.max_mm
    span = t_max - t_min
    lithophane = settings.mode == "lithophane"
    if lithophane:
        field = luminance
    elif image.mode == "F" or settings.source == "depth":
        field = display
    else:
        field = lightness(luminance) / 100
    values = sample_equirect(field.astype(np.float32), columns, thetas)
    r_out = frame["r_out"]
    pitch_equator = 2 * math.pi * r_out / columns
    pitch_meridian = r_out * (thetas[1] - thetas[0])
    if settings.denoise != "off":
        spatial, tonal = {"light": (1.0, 0.04), "strong": (2.0, 0.10)}[settings.denoise]
        pad = max(4, columns // 16)
        wrapped = np.pad(values, ((0, 0), (pad, pad)), mode="wrap").astype(np.float32)
        values = cv2.bilateralFilter(wrapped, d=-1, sigmaColor=tonal, sigmaSpace=spatial)[
            :, pad:-pad
        ].astype(np.float64)
        values[0, :] = values[0].mean()
    thickness_raw, clipped, target, stats = tone_to_thickness(values, settings)
    if settings.nozzle_filter:
        sigma_mm = settings.nozzle_mm * FWHM_TO_SIGMA
        thickness = nozzle_filter(thickness_raw, thetas, r_out, sigma_mm)
    else:
        thickness = thickness_raw.copy()
    removed = thickness_raw - thickness
    thickness = np.clip(thickness, t_min, t_max)
    # Collar: full thickness within collar_mm of the cut (always the last row), so the
    # outer cut is a circle of radius R_out that lies in the cut plane.
    collar = (frame["theta_out"] - thetas) * r_out <= settings.collar_mm
    collar[-1] = True
    thickness[collar] = t_max
    levels = np.round((thickness - t_min) / span * 65535).astype(np.uint16)
    thickness = t_min + levels.astype(np.float64) / 65535 * span
    radii = frame["r_in"] + thickness
    inner_rows = max(4, math.ceil(rows / INNER_ROW_FACTOR))
    inner_thetas = np.linspace(0, frame["theta_in"], inner_rows)
    centred, triangles = sphere_mesh(radii, thetas, frame["r_in"], inner_thetas, keys=levels)
    vertices = centred + np.array([0, 0, -frame["z_cut"]])  # Cut plane at z = 0.
    report = mesh_report(vertices, triangles)
    centre_volume = mesh_report(centred, triangles)["volume_mm3"]
    if not report["closed_and_oriented"] or report["genus"] != 0:
        raise ReliefError("The generated sphere did not close into a solid. Try again.")
    if not math.isclose(report["volume_mm3"], centre_volume, rel_tol=1e-9):
        raise ReliefError("The generated sphere did not pass its volume check.")
    smooth = smooth_volume(radii, thetas, frame)

    write_binary_stl(
        job_dir / "model.stl", vertices, triangles, header=b"Pictures to CAD sphere (mm)"
    )
    write_mesh_3mf(
        job_dir / "model.3mf",
        vertices,
        triangles,
        name=settings.name,
        object_name="Lamp" if lithophane else "Globe",
    )
    cv2.imwrite(str(job_dir / "heightmap.png"), levels)
    volume = report["volume_mm3"]
    overhang, surface = overhang_area(vertices, triangles)
    bed_outer = r_out * math.sin(frame["theta_out"])
    bed_inner = settings.opening_mm / 2
    sin_t = np.maximum(np.sin(thetas), 1e-6)[:, None]
    d_theta = np.gradient(thickness, thetas, axis=0) / r_out
    d_lambda = (np.roll(thickness, -1, axis=1) - np.roll(thickness, 1, axis=1)) / (
        2 * (2 * math.pi / columns) * r_out * sin_t
    )
    usable = (np.sin(thetas) > 0.05)[:, None] & np.ones_like(thickness, dtype=bool)
    slope = np.degrees(np.arctan(np.hypot(d_theta, d_lambda)))[usable]
    dims = {
        "width": float(2 * r_out * 1.0),
        "height": float(vertices[:, 2].max()),
        "thickness": float(thickness.max()),
        "min_thickness": float(thickness.min()),
        "diameter": float(2 * r_out),
        "inner_diameter": float(2 * frame["r_in"]),
        "opening": float(settings.opening_mm),
    }
    stats.update(
        {
            "grid": {
                "columns": columns,
                "rows": rows,
                "pitch_x_mm": pitch_equator,
                "pitch_y_mm": pitch_meridian,
                "image_pixel_mm": 2 * math.pi * r_out / w_px,
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
            "mass_g": volume / 1000 * DENSITY[settings.material],
            "density_g_cm3": DENSITY[settings.material],
            "mesh": report,
            "volume_cross_check_mm3": centre_volume,
            "volume_check": {
                "label": "divergence volume about the sphere centre (equal only for a closed surface)",
                "value_mm3": centre_volume,
                "rel_tol": 1e-9,
            },
            "sphere": {
                "outer_diameter_mm": 2 * r_out,
                "inner_diameter_mm": 2 * frame["r_in"],
                "opening_mm": settings.opening_mm,
                "height_mm": dims["height"],
                "bed_contact_mm2": math.pi * (bed_outer**2 - bed_inner**2),
                "overhang_area_mm2": overhang,
                "overhang_fraction": overhang / surface,
                "overhang_degrees": OVERHANG_DEGREES,
                "smooth_volume_mm3": smooth,
                "polyhedral_vs_smooth": (volume - smooth) / smooth,
            },
        }
    )
    if lithophane:
        mu = attenuation(settings.half_value_mm)
        picture = ~collar
        predicted = transmission(thickness[picture], t_min, settings.half_value_mm)
        error = np.abs(lightness(predicted) - lightness(target[picture]))
        in_range = error[~clipped[picture]] if np.any(~clipped[picture]) else error
        stats["optics"] = {
            "mu_per_mm": mu,
            "half_value_mm": settings.half_value_mm,
            "contrast_ratio": math.exp(mu * span),
            "dynamic_range_stops": span / settings.half_value_mm,
            "darkest_transmission": math.exp(-mu * span),
            "clipped_fraction": float(np.mean(clipped[picture])),
            "tone_error_lstar_mean": float(in_range.mean()),
            "tone_error_lstar_p95": float(np.percentile(in_range, 95)),
            "tone_error_lstar_mean_all": float(error.mean()),
        }
        preview = linear_to_srgb(transmission(thickness, t_min, settings.half_value_mm))
    else:
        preview = (thickness - t_min) / span
    notices.append(
        f"Print it standing on its flat {settings.opening_mm:g} mm opening. "
        f"{overhang / surface:.0%} of the surface faces downward more than "
        f"{OVERHANG_DEGREES:.0f}° from vertical (mostly the inside of the dome); check "
        "supports in your slicer."
    )
    notices.append(
        "STL and 3MF coordinates are in millimetres, with the opening's flat cut at Z zero."
    )

    import json

    recipe = {
        "format": "pictures-to-cad-relief",
        "version": 1,
        "settings": settings.model_dump(),
        "units": "mm",
        "provenance": "Wall thickness derived from image tone by the stated model; the source image is not stored.",
    }
    (job_dir / "project.json").write_text(
        json.dumps(recipe, indent=2, allow_nan=False), encoding="utf-8"
    )
    write_blender_bundle(
        job_dir,
        settings,
        dims,
        columns,
        rows,
        pitch_equator,
        pitch_meridian,
        0,
        0,
        extra={
            "r_in_mm": frame["r_in"],
            "theta_out": frame["theta_out"],
            "theta_in": frame["theta_in"],
            "inner_rows": inner_rows,
            "z_cut_mm": frame["z_cut"],
        },
    )
    downloads = {
        kind: f"/api/download/{job_dir.name}/{kind}"
        for kind in ("stl", "3mf", "heightmap", "blender", "project")
    }
    if lithophane:
        from .relief import wedge_thicknesses, write_wedge

        write_wedge(job_dir, t_min, t_max)
        downloads["wedge"] = f"/api/download/{job_dir.name}/wedge"
        stats["wedge_mm"] = wedge_thicknesses(t_min, t_max)
    return {
        "id": job_dir.name,
        "kind": settings.mode,
        "shape": "sphere",
        "revision": settings.revision,
        "dimensions": dims,
        "volume_mm3": volume,
        "stats": stats,
        "mesh": _preview(radii, thetas, frame),
        "preview_image": _png_data_url(preview),
        "downloads": downloads,
        "warnings": notices,
        "settings": settings.model_dump(),
    }


def _preview(radii, thetas, frame):
    rows, columns = radii.shape
    preview_columns = min(columns, PREVIEW_COLUMNS)
    preview_rows = min(rows, max(8, PREVIEW_COLUMNS // 2))
    small = cv2.resize(radii, (preview_columns, preview_rows), interpolation=cv2.INTER_AREA)
    small[0, :] = small[0].mean()
    small[-1, :] = frame["r_out"]
    preview_thetas = np.linspace(0, frame["theta_out"], preview_rows)
    inner_thetas = np.linspace(0, frame["theta_in"], max(4, preview_rows // INNER_ROW_FACTOR))
    vertices, triangles = sphere_mesh(small, preview_thetas, frame["r_in"], inner_thetas)
    return {
        "vertices": np.round(vertices, 3).ravel().tolist(),
        "triangles": triangles.ravel().tolist(),
    }
