"""Trace a part photographed on a reference sheet: metric, perspective- and lens-corrected.

Stages: find the sheet (backend.sheet) -> estimate radial distortion from its edges ->
homography -> one resampling onto a millimetre grid -> segment the part and locate its
boundary to sub-pixel precision (backend.edges) -> optionally undo top-face parallax
for the entered thickness -> fit lines, arcs and circles with residuals and optional
design-intent snapping (backend.fitting) -> a display crop and a Profile whose
coordinates are display pixels of known size.

The scale comes from the sheet's stated size; the user's outside-width measurement
becomes an independent check of it. Sub-pixel positions are measured in linear light,
decoding the photo as sRGB (backend.tone).
"""

from __future__ import annotations

import base64
import io
import math

import cv2
import numpy as np
from PIL import Image
from pydantic import ValidationError
from shapely.geometry import Polygon

from . import edges, fitting, sheet, tone
from .models import Profile

DISPLAY_SIDE = 1400
DISPLAY_MARGIN_MM = 12.0
MAX_TOTAL_VERTICES = 1900
POLYLINE_TOLERANCE_MM = {"coarse": 0.15, "standard": 0.05, "fine": 0.02}


class ReferenceError_(ValueError):
    """A user-facing failure. `sheet_missing` marks failures to find or use the sheet,
    which a caller may replace by tracing without it."""

    def __init__(self, message, sheet_missing=False):
        super().__init__(message)
        self.sheet_missing = sheet_missing


def sheet_size(reference, sheet_mm):
    if reference in sheet.SHEETS:
        return sheet.SHEETS[reference]
    if reference != "custom" or not sheet_mm:
        raise ReferenceError_("Enter the custom sheet's measured width and height.")
    w, h = (float(v) for v in sheet_mm)
    if not all(math.isfinite(v) and 10 <= v <= 2000 for v in (w, h)):
        raise ReferenceError_("Custom sheet sides must be between 10 and 2000 mm.")
    return (w, h)


def _segments_for(points, prims, tolerance_px):
    """Segments in rectified pixels: fitted primitives, else a simplified polyline."""
    if prims:
        return fitting.segments(prims), True
    ring = Polygon(points).simplify(tolerance_px, preserve_topology=True)
    vertices = np.asarray(ring.exterior.coords)[:-1] if not ring.is_empty else points
    if len(vertices) < 3:
        vertices = points
    return [("line", vertices[k], vertices[(k + 1) % len(vertices)]) for k in range(len(vertices))], False


def _to_model(segs, transform):
    out = []
    for s in segs:
        if s[0] == "circle":
            out.append({"kind": "circle", "center": list(transform(s[1])), "radius": float(s[2]) * transform.scale})
        elif s[0] == "line":
            out.append({"kind": "line", "start": list(transform(s[1])), "end": list(transform(s[2]))})
        else:
            out.append({"kind": "arc", "start": list(transform(s[1])), "mid": list(transform(s[2])), "end": list(transform(s[3]))})
    # Share exact end/start coordinates so closure survives float formatting.
    for current, following in zip(out, out[1:] + out[:1]):
        if current["kind"] != "circle":
            current["end"] = list(following["start"])
    return out


class _Transform:
    """Rectified pixels -> display pixels: rotate about `centre`, then crop and scale."""

    def __init__(self, rotation, centre, origin, scale):
        self.rotation = np.asarray(rotation, float)
        self.centre = np.asarray(centre, float)
        self.origin = np.asarray(origin, float)
        self.scale = float(scale)

    def __call__(self, point):
        p = np.asarray(point, float)
        p = ((p - self.centre) @ self.rotation.T + self.centre - self.origin) * self.scale
        return (float(p[0]), float(p[1]))


def _refine_walls(g, rings, camera, thickness_mm, sigma, ppm):
    """Each ring's points with the edges that show a narrow side wall refined by the
    two-step model (edges.two_step_refine), before the parallax correction, with their
    material normals and the notes. The rings are not changed. With no measured edge
    blur (edges.edge_sigma returns 0 when no profile has the contrast) the model has no
    scale, and the points are returned as traced."""
    notes = []
    if sigma <= 0:
        return [(ring["points"].copy(), edges.material_normals(ring["points"] / ppm, ring["outer"])) for ring in rings], notes
    ratio = camera["height_mm"] / (camera["height_mm"] - thickness_mm)
    # Bottom-edge silhouette points have the visible wall on their material side, a
    # band (ratio - 1) |(p - N) . n| wide. A single mid-level crossing is biased into
    # the material by up to 0.2 sigma for bands of 1-3 sigma (edges.two_step_refine).
    prepared = []
    for ring in rings:
        mm = ring["points"] / ppm
        normals = edges.material_normals(mm, ring["outer"])
        facing = np.einsum("ij,ij->i", normals, mm - camera["nadir_mm"])
        band = (ratio - 1) * np.maximum(-facing, 0) * ppm
        prepared.append((ring, normals, band))
    # The wall tone is identifiable only where the band is wide (>= 2.5 sigma); there
    # a free two-step fit measures it. Narrower bands are then fitted with it fixed.
    wide = [(r["points"][b >= 2.5 * sigma], n[b >= 2.5 * sigma], b[b >= 2.5 * sigma]) for r, n, b in prepared]
    wide_points = np.vstack([w[0] for w in wide]) if wide else np.empty((0, 2))
    # Refine mainly bands of 1-3 sigma, where a single crossing is biased by 0.14-0.20
    # sigma. Below that the wall tone and edge offset are nearly confounded; above it
    # the local levels already see the wall. In synthetic tests, refining the whole
    # 0.25-4 sigma range made results worse (see docs/validation.md).
    narrow_count = sum(int(((b >= sigma) & (b <= 3 * sigma)).sum()) for _, _, b in prepared)
    wall_tone = None
    if len(wide_points) >= 30:
        _, tones = edges.two_step_refine(
            g, wide_points, np.vstack([w[1] for w in wide]), np.concatenate([w[2] for w in wide]), sigma
        )
        wall_tone = float(np.median(tones))
    else:
        # Too few wide bands: one tone shared by all bands of 1-3.5 sigma
        # (edges.pooled_wall_tone), where a near-frontal photo still has hundreds.
        pool = [(r["points"][(b >= sigma) & (b <= 3.5 * sigma)], n[(b >= sigma) & (b <= 3.5 * sigma)], b[(b >= sigma) & (b <= 3.5 * sigma)]) for r, n, b in prepared]
        pooled = sum(len(p[0]) for p in pool)
        if pooled >= 30:
            wall_tone = edges.pooled_wall_tone(
                g, np.vstack([p[0] for p in pool]), np.vstack([p[1] for p in pool]), np.concatenate([p[2] for p in pool]), sigma
            )
        if wall_tone is not None:
            notes.append(
                f"Side walls are narrower than about 2.5 times the edge blur; their tone was estimated jointly from {pooled} edge points and the edges facing the camera were corrected with it."
            )
    if wall_tone is None and narrow_count:
        notes.append(
            f"Side walls are visible but narrower than about 2.5 times the edge blur, so their tone cannot be measured; edges facing the camera may read up to {0.2 * sigma / ppm:.3f} mm into the part. A slightly tilted photo shows wider walls."
        )
    refined = []
    for ring, normals, band in prepared:
        # Full weight for 1.5-2.5 sigma, tapering linearly to zero at 0.5 and 3.5
        # sigma, so the boundary stays continuous where refinement starts and stops.
        weight = np.clip((band - 0.5 * sigma) / sigma, 0, 1) * np.clip((3.5 * sigma - band) / sigma, 0, 1)
        narrow = weight > 0
        points = ring["points"].copy()
        if wall_tone is not None and narrow.any():
            moved, _ = edges.two_step_refine(g, points[narrow], normals[narrow], band[narrow], sigma, wall_tone=wall_tone)
            points[narrow] += weight[narrow, None] * (moved - points[narrow])
        refined.append((points, normals))
    return refined, notes


def trace_on_sheet(rgb, *, reference, sheet_mm, inverted, detail, thickness_mm, focal_35mm, snap, notices):
    size_mm = sheet_size(reference, sheet_mm)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    size = (gray.shape[1], gray.shape[0])
    # Every sub-pixel measurement is made on a linear-light mix of the photo's channels;
    # its saved values are used only to find the sheet and to classify the part
    # (backend.tone).
    try:
        found = sheet.find_sheet(gray, rgb)
    except sheet.SheetError as exc:
        raise ReferenceError_(str(exc), sheet_missing=True) from exc
    k1, before, after = sheet.estimate_k1(found, size)
    matrix, plane, _ = sheet.homography(found, k1, size, size_mm)
    # Independent check of the stated sheet size: its proportions (not its scale) are
    # measurable from the photo (sheet.aspect_ratio_check).
    focal = sheet.orthogonal_focal(matrix, size) or sheet.camera_pose(matrix, size, focal_35mm)["focal_px"]
    aspect = sheet.aspect_ratio_check(matrix, size, focal)
    ppm, native = sheet.choose_ppm(matrix, plane)
    if native < 1.0:
        raise ReferenceError_(
            "The sheet is too small in the photo to measure from. Move closer so it fills most of the frame.",
            sheet_missing=True,
        )
    rectified = sheet.rectify(rgb, matrix, k1, plane, ppm)  # display and classification
    try:
        mask, seg_notes = edges.segment(
            cv2.cvtColor(rectified, cv2.COLOR_RGB2GRAY), ppm, part_lighter=inverted
        )
        weights = edges.measurement_weights(rectified, mask, ppm)
        # The measurement image: exact resampling of the linear-light mix.
        g = cv2.GaussianBlur(
            sheet.rectify_gray(tone.linear_mix(rgb, weights), matrix, k1, plane, ppm), (0, 0), 0.7
        )
        rings, sigma, tiny = edges.subpixel_rings(mask, g, ppm)
    except edges.EdgeError as exc:
        raise ReferenceError_(str(exc), sheet_missing=True) from exc
    notes = list(seg_notes)
    if weights != tone.LUMINANCE:
        notes.append(
            "The part and the sheet differ in colour more than in brightness, so edges were measured on a colour mix"
            f" (red {weights[0]:.0%}, green {weights[1]:.0%}, blue {weights[2]:.0%}). Colour detail is coarser than brightness in a compressed photo."
        )
    stated = plane[0] / plane[1]
    if abs(aspect - 1) > 0.01:
        notes.append(
            f"The sheet's proportions in the photo differ from the chosen size by {100 * (aspect - 1):+.1f} %"
            f" (width : height measured {stated * aspect:.3f}, chosen {stated:.3f}). Check the sheet choice or its measured size; every dimension scales with it."
        )
    else:
        notes.append(
            f"Sheet proportions check: the photo matches the chosen sheet within {100 * abs(aspect - 1):.2f} %."
        )
    camera = None
    if thickness_mm:
        camera = sheet.camera_pose(matrix, size, focal_35mm)
        if thickness_mm >= 0.5 * camera["height_mm"]:
            raise ReferenceError_("The entered thickness is too large for this camera distance. Check the thickness.")
        refined, wall_notes = _refine_walls(g, rings, camera, thickness_mm, sigma, ppm)
        holes_used = 0
        if camera["focal_source"] == "assumed":
            # A nearly frontal view does not fix the focal length, and so the camera
            # height; the holes' roundness after the parallax correction does
            # (edges.roundness_focal). The walls are then refined again with it.
            found = edges.roundness_focal(
                [(points / ppm, normals) for (points, normals), ring in zip(refined, rings) if not ring["outer"]],
                lambda focal: sheet.camera_pose(matrix, size, focal_px=focal),
                thickness_mm,
                math.hypot(*size),
                max(0.03, 0.15 * sigma / ppm),
            )
            if found is not None:
                camera = {**sheet.camera_pose(matrix, size, focal_px=found[0]), "focal_source": "holes"}
                holes_used = found[1]
                refined, wall_notes = _refine_walls(g, rings, camera, thickness_mm, sigma, ppm)
        notes.extend(wall_notes)
        for ring, (points, normals) in zip(rings, refined):
            corrected, _ = edges.correct_thickness(
                points / ppm, normals, camera["nadir_mm"], camera["height_mm"], thickness_mm
            )
            ring["points"] = corrected * ppm
        if camera["focal_source"] == "assumed":
            notes.append(
                "The camera's focal length could not be found from the sheet, the photo's metadata or the holes' shape, so a typical phone lens was assumed for the thickness correction."
            )
        elif camera["focal_source"] == "holes":
            equivalent = camera["focal_px"] / math.hypot(*size) * math.hypot(36, 24)
            notes.append(
                f"The camera's focal length could not be found from the sheet or the photo's metadata. It was estimated as {equivalent:.1f} mm (35 mm equivalent) from the roundness of {holes_used} hole(s): their near and far sides are traced at different heights, and only the right camera height makes them round."
            )
    outer_points = next(r["points"] for r in rings if r["outer"])
    extent_mm = float(np.ptp(outer_points, axis=0).max()) / ppm
    tolerance_px = max(0.03, 0.15 * sigma / ppm) * ppm
    min_line_px = min(max(0.025 * extent_mm, 1.0), 3.0) * ppm
    fitted = [(ring, fitting.fit_ring(ring["points"], tolerance_px, min_line_px)) for ring in rings]
    rings_prims = [p for _, p in fitted if p]
    axis = None
    if snap:
        snap_notes, axis = fitting.snap_axes(rings_prims)
        notes.extend(snap_notes)
        for ring, prims in fitted:
            if prims and any(p.kind == "line" for p in prims):
                fitting.refit_lines(ring["points"], prims, margin=3 * sigma)
                fitting.fit_fillets(ring["points"], prims, tolerance_px, sigma)
    for prims in rings_prims:
        fitting.correct_blur(prims, sigma)
    if snap:
        notes.extend(fitting.equalise_radii(rings_prims, scale=1 / ppm, unit="mm"))
    # First among the notes (after the fit summary), so the 16-note limit keeps them.
    radius_notes = fitting.undetermined_radii(rings_prims, sigma, scale=1 / ppm, unit="mm")
    notes[0:0] = radius_notes
    polyline_px = POLYLINE_TOLERANCE_MM.get(detail, 0.05) * ppm
    described = []
    for ring, prims in fitted:
        segs, analytic = _segments_for(ring["points"], prims, polyline_px)
        polygon = Polygon(fitting.sample_segments(segs, 0.01 * ppm))
        if analytic and (not polygon.is_valid or polygon.area <= 0):
            segs, analytic = _segments_for(ring["points"], None, polyline_px)
        described.append({"outer": ring["outer"], "segments": segs, "analytic": analytic})

    # Display view: the part plus a margin, rotated (when snapping found straight edges)
    # so those edges run along the X and Y axes, at most DISPLAY_SIDE pixels long. One
    # affine resampling of the rectified image; the geometry uses the same transform.
    angle = -axis if axis is not None and abs(axis) > math.radians(0.05) else 0.0
    if angle:
        notes.append(
            f"Rotated {math.degrees(-angle):.2f}° so the part's straight edges align with the X and Y axes."
        )
    centre = outer_points.mean(axis=0)
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    turned = (outer_points - centre) @ rotation.T + centre
    margin = DISPLAY_MARGIN_MM * ppm
    origin = np.floor(turned.min(axis=0) - margin)
    extent = np.ceil(turned.max(axis=0) + margin) - origin
    scale = min(1.0, DISPLAY_SIDE / float(extent.max()))
    out_w, out_h = (math.ceil(v * scale) for v in extent)
    inverse = rotation.T / scale
    shift = rotation.T @ (0.5 / scale + origin - centre) + centre - 0.5
    source = rectified if scale >= 1 else cv2.GaussianBlur(rectified, (0, 0), 0.4 / scale)
    crop = cv2.warpAffine(
        source,
        np.column_stack([inverse, shift]).astype(np.float64),
        (out_w, out_h),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE,
    )
    transform = _Transform(rotation, centre, origin, scale)
    mm_per_px = 1 / (ppm * scale)

    sagitta = 0.01 * ppm * scale
    for _ in range(8):
        rings_out = [
            [transform(p) for p in fitting.sample_segments(d["segments"], sagitta)] for d in described
        ]
        if sum(map(len, rings_out)) <= MAX_TOTAL_VERTICES:
            break
        sagitta *= 2
    else:
        raise ReferenceError_("The outline is too detailed to describe. Choose Simplified outline detail.")
    outer = next(r for r, d in zip(rings_out, described) if d["outer"])
    holes = [r for r, d in zip(rings_out, described) if not d["outer"]]
    seg_outer = next(_to_model(d["segments"], transform) for d in described if d["outer"])
    seg_holes = [_to_model(d["segments"], transform) for d in described if not d["outer"]]
    counts = {"line": 0, "arc": 0, "circle": 0}
    for d in described:
        if d["analytic"]:
            for s in d["segments"]:
                counts[s[0]] += 1
    unfitted = sum(1 for d in described if not d["analytic"])
    notes.insert(
        0,
        f"Fitted {counts['circle']} circle(s), {counts['arc']} arc(s) and {counts['line']} line(s)"
        + (f"; {unfitted} boundary(ies) kept as traced outlines." if unfitted else "."),
    )
    if tiny:
        notes.append(f"Ignored {tiny} tiny region(s) under the trace resolution. Inspect small features before exporting.")
    reference_info = {
        "kind": reference,
        "sheet_mm": [float(size_mm[0]), float(size_mm[1])],
        "mm_per_px": mm_per_px,
        "lens_k1": float(k1),
        "edge_blur_mm": float(sigma / ppm),
        "notes": notes[:16],
    }
    if camera:
        reference_info.update(
            thickness_mm=float(thickness_mm),
            camera_height_mm=camera["height_mm"],
            focal_source=camera["focal_source"],
        )
    try:
        profile = Profile(
            outer=outer,
            holes=holes,
            primitives={"outer": seg_outer, "holes": seg_holes},
            reference=reference_info,
        )
    except ValidationError as exc:
        raise ReferenceError_(
            "The traced outline could not form a valid profile. Improve the photo's contrast or choose Simplified outline detail."
        ) from exc

    image = Image.fromarray(crop)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    px, py = zip(*profile.outer)
    warnings_out = list(notices)
    warnings_out.append(
        f"Scaled from the {'A4' if reference == 'a4' else 'US Letter' if reference == 'letter' else 'custom'} "
        f"sheet ({size_mm[0]:g} × {size_mm[1]:g} mm), corrected for perspective"
        + (f" and lens distortion (edge straightness {before:.2f} → {after:.2f} px)" if k1 else "")
        + (f", and for a {thickness_mm:g} mm thick top face" if camera else "")
        + ". Check the sheet's real size; the measured width is now an independent check."
    )
    mismatch = [n for n in notes if n.startswith("The sheet's proportions in the photo differ")]
    warnings_out.extend(mismatch)
    warnings_out.extend(radius_notes)
    if not camera:
        warnings_out.append(
            "Enter the part's thickness and re-trace (Build does this automatically) to correct for its visible side walls."
        )
    return {
        "image": {
            "width": image.width,
            "height": image.height,
            "data_url": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii"),
        },
        "profile": profile.model_dump(exclude_none=True),
        "bounds": {"x": min(px), "y": min(py), "width": max(px) - min(px), "height": max(py) - min(py)},
        "threshold": 128,
        "warnings": warnings_out,
    }
