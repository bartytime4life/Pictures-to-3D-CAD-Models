"""Decode a bounded photograph and derive explicit polygon boundaries."""

import base64
import io
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError

from .models import Profile

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 16_000_000
MAX_SIDE = 1400
cv2.setNumThreads(1)


class TraceError(ValueError):
    pass


def trace_image(
    data: bytes, threshold: int = -1, inverted: bool = False, detail: str = "standard"
) -> dict:
    if not data or len(data) > MAX_BYTES:
        raise TraceError("Choose an image between 1 byte and 10 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as raw:
                if raw.format not in {"PNG", "JPEG", "WEBP"}:
                    raise TraceError("Use a PNG, JPEG, or WebP image.")
                if raw.width * raw.height > MAX_PIXELS:
                    raise TraceError("The image exceeds 16 megapixels. Resize it and try again.")
                if min(raw.size) < 16:
                    raise TraceError("Use an image at least 16 pixels wide and tall.")
                if getattr(raw, "n_frames", 1) != 1:
                    raise TraceError("Use a still image rather than an animation.")
                normalized = ImageOps.exif_transpose(raw)
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
    notices = []
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

    holes = []
    small_holes = 0
    for i, node in enumerate(hierarchy):
        if node[3] != chosen:
            continue
        if cv2.contourArea(contours[i]) < 9:
            small_holes += 1
            continue
        if node[2] != -1:
            raise TraceError(
                "A hole contains another region. Remove markings or shadows, or adjust the threshold before tracing again."
            )
        hole = points(contours[i])
        if len(hole) >= 3:
            holes.append(hole)
        else:
            small_holes += 1
    if small_holes:
        notices.append(
            f"Ignored {small_holes} tiny region(s) under the trace resolution. Inspect small features before exporting."
        )
    try:
        profile = Profile(outer=points(outer), holes=holes)
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
