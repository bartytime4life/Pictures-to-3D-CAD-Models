"""Decode a bounded photograph and derive explicit polygon boundaries."""

import base64
import io
import warnings

import cv2
import numpy as np
from PIL import ExifTags, Image, UnidentifiedImageError
from pydantic import ValidationError
from shapely.geometry import Polygon

from .models import Profile

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 16_000_000
MAX_SIDE = 1400
TINY_AREA = 9  # Contour area, in working-image pixels, below the trace resolution.
ORIENTATION = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}
cv2.setNumThreads(1)


class TraceError(ValueError):
    pass


def to_eight_bit(image):
    """Scale 16-bit grayscale samples to 8 bits; Pillow's RGB conversion clips them to white.

    Pillow decodes 16-bit grayscale PNG as I;16 (I in older releases), with samples 0-65535.
    """
    if image.mode != "I" and not image.mode.startswith("I;16"):
        return image
    samples = np.asarray(image)
    gray = (np.clip(samples, 0, 65535) >> 8).astype(np.uint8)
    key = image.info.get("transparency")
    if isinstance(key, int):
        # Match the 16-bit transparent key before precision is reduced.
        alpha = np.where(samples == key, 0, 255).astype(np.uint8)
        return Image.fromarray(np.dstack([gray, alpha]))
    return Image.fromarray(gray)


def to_pixel_edges(ring, distance):
    """Offset a ring traced through boundary-pixel centres onto those pixels' outer edges.

    OpenCV follows the centres of the part's boundary pixels, which leaves an outer ring
    half a pixel inside the part and a hole ring half a pixel inside the surrounding
    material. Use +0.5 to grow an outer ring and -0.5 to shrink a hole. Mitre joins move
    every edge by exactly that distance without adding vertices at shallow corners. The
    low mitre limit bevels corners sharper than about 130 degrees, so a right-angle corner
    reaches at most about 0.07 px past its pixel edge and a needle-sharp spike about
    0.25 px; axis-aligned extents stay exact. A higher limit lets rotated corners overshoot
    by 0.2 px or more, and rounded joins, though exact, add many vertices.

    Returns None when a hole collapses to nothing; the caller counts it as a tiny region.
    Any other degenerate result (an already-invalid ring, or a ring that splits or gains
    an interior) keeps the traced ring unchanged, so a ring is never made less valid than
    the trace; Profile validation still rejects an invalid combination.
    """
    polygon = Polygon(ring)
    if not polygon.is_valid:
        return ring
    moved = polygon.buffer(distance, join_style="mitre", mitre_limit=1.1)
    if moved.is_empty:
        return None
    if not isinstance(moved, Polygon) or moved.interiors or not moved.is_valid:
        return ring
    return [list(point) for point in moved.exterior.coords[:-1]]


def trace_image(
    data: bytes, threshold: int = -1, inverted: bool = False, detail: str = "standard"
) -> dict:
    if not data or len(data) > MAX_BYTES:
        raise TraceError("Choose an image between 1 byte and 10 MiB.")
    notices = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as raw:
                # Cameras store an embedded preview or second view as an MPO JPEG.
                if raw.format not in {"PNG", "JPEG", "WEBP", "MPO"}:
                    raise TraceError("Use a PNG, JPEG, or WebP image.")
                if raw.width * raw.height > MAX_PIXELS:
                    raise TraceError("The image exceeds 16 megapixels. Resize it and try again.")
                if min(raw.size) < 16:
                    raise TraceError("Use an image at least 16 pixels wide and tall.")
                if raw.format == "MPO":
                    raw.seek(0)  # The primary image; later frames are previews or other views.
                elif getattr(raw, "n_frames", 1) != 1:
                    raise TraceError("Use a still image rather than an animation.")
                raw.load()
                # Read only the orientation. Pillow's exif_transpose also re-serializes the
                # remaining EXIF, which raises on malformed but otherwise harmless tags, and
                # EXIF is discarded below.
                try:
                    method = ORIENTATION.get(raw.getexif().get(ExifTags.Base.Orientation, 1))
                except Exception:  # noqa: BLE001 - any malformed EXIF block is untrusted input.
                    method = None
                    notices.append(
                        "The image's orientation metadata could not be read, so it was traced as stored. Check that the outline is oriented like the part before measuring the reference width."
                    )
                normalized = to_eight_bit(raw.transpose(method) if method else raw)
                if "A" in normalized.getbands() or "transparency" in normalized.info:
                    rgba = normalized.convert("RGBA")
                    image = Image.new("RGB", rgba.size, "white")
                    image.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    image = normalized.convert("RGB")
                image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
                image.load()
    except TraceError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,  # A damaged PNG chunk can fail only when its pixels are loaded.
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise TraceError(
            "The image could not be decoded. Try a valid PNG, JPEG, or WebP under 16 megapixels."
        ) from exc

    gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    mode = cv2.THRESH_BINARY if inverted else cv2.THRESH_BINARY_INV
    if threshold == -1:
        used_threshold, mask = cv2.threshold(gray, 0, 255, mode | cv2.THRESH_OTSU)
    elif 0 <= threshold <= 255:
        used_threshold, mask = cv2.threshold(gray, threshold, 255, mode)
    else:
        raise TraceError("Threshold must be Automatic or between 0 and 255.")
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        raise TraceError("No outline found. Adjust the threshold or use a contrasting background.")
    hierarchy = hierarchy[0]
    roots = [i for i, node in enumerate(hierarchy) if node[3] == -1]
    chosen = max(roots, key=lambda i: cv2.contourArea(contours[i]))
    outer = contours[chosen]
    if cv2.contourArea(outer) < 64:
        raise TraceError("The part is too small to trace. Crop closer or use a clearer photo.")
    x, y, w, h = cv2.boundingRect(outer)
    if x <= 0 or y <= 0 or x + w >= image.width or y + h >= image.height:
        raise TraceError(
            "The outline touches the image edge. Include the entire part, or switch foreground polarity."
        )
    other_parts = [
        i
        for i in roots
        if i != chosen and cv2.contourArea(contours[i]) > max(64, cv2.contourArea(outer) * 0.01)
    ]
    if other_parts:
        notices.append(
            f"Found {len(other_parts) + 1} separate regions. Only the largest is selected; crop the image if this is the wrong part."
        )
    epsilon = {"coarse": 1.5, "standard": 0.75, "fine": 0.35}[detail]

    def points(contour):
        return cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2).astype(float).tolist()

    def image_coordinates(ring):
        # Shift from OpenCV's pixel-centre frame to the image frame, where pixel i spans
        # [i, i + 1] and the image spans [0, width]; the browser overlay uses this frame.
        return [[px + 0.5, py + 0.5] for px, py in ring]

    holes = []
    small_holes = 0
    for i, node in enumerate(hierarchy):
        if node[3] != chosen:
            continue
        if cv2.contourArea(contours[i]) < TINY_AREA:
            small_holes += 1
            continue
        child = node[2]
        while child != -1:
            # A speck inside a hole is as far below the trace resolution as a tiny hole.
            if cv2.contourArea(contours[child]) >= TINY_AREA:
                raise TraceError(
                    "A hole contains another region. Remove markings or shadows, or adjust the threshold before tracing again."
                )
            small_holes += 1
            child = hierarchy[child][0]
        hole = points(contours[i])
        if len(hole) >= 3:
            hole = to_pixel_edges(hole, -0.5)
        if hole is not None and len(hole) >= 3:
            holes.append(image_coordinates(hole))
        else:
            small_holes += 1
    if small_holes:
        notices.append(
            f"Ignored {small_holes} tiny region(s) under the trace resolution. Inspect small features before exporting."
        )
    outline = points(outer)
    if len(outline) >= 3:
        outline = to_pixel_edges(outline, 0.5) or outline  # Growing a ring cannot empty it.
    try:
        profile = Profile(outer=image_coordinates(outline), holes=holes)
    except ValidationError as exc:
        raise TraceError(
            "The traced outline is too complex or intersects itself. Adjust threshold, reduce detail, or try a cleaner photo."
        ) from exc
    buffer = io.BytesIO()
    image.info.clear()
    image.save(buffer, "PNG")
    xs, ys = zip(*profile.outer)
    return {
        "image": {
            "width": image.width,
            "height": image.height,
            "data_url": "data:image/png;base64,"
            + base64.b64encode(buffer.getvalue()).decode("ascii"),
        },
        "profile": profile.model_dump(),
        "bounds": {
            "x": min(xs),
            "y": min(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
        },
        "threshold": int(used_threshold),
        "warnings": notices,
    }
