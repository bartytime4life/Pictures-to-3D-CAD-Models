"""Decode a HEIC photo in a child process: python -m backend.heic MAX_PIXELS MIN_SIDE.

HEIC is the default photo format of recent phones. Its decoders (libheif and libde265,
through pi-heif) are native code, and a damaged file can crash them: changing two bytes
of a valid file caused a segmentation fault while its metadata was read. In the server
process that would end the service, so HEIC is decoded in a short-lived child, as CAD
builds are (backend.worker). A crash, a timeout or an oversized image then becomes an
ordinary refusal.

This is containment of failures, not a security sandbox: the child runs as the same
user with the same file access.

The child reads the file from standard input and writes one JSON line, then the
pixels as 8-bit RGB rows. The stored rotation is already applied (pi-heif applies it
and reports orientation 1), and transparency is flattened onto white.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 60
# ISO base media "ftyp" brands of HEVC-coded HEIF images and image sequences.
BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs"}


class HeicError(ValueError):
    """A refusal. `reason` is "pixels", "small" or "decode"."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def is_heic(data):
    """Whether the bytes start with an ISO base media file type box naming an HEVC image
    brand, as its major brand or among its compatible brands."""
    if len(data) < 16 or data[4:8] != b"ftyp":
        return False
    size = int.from_bytes(data[:4], "big")
    box = data[8 : max(16, min(size, 256))]
    brands = {box[:4]} | {box[i : i + 4] for i in range(8, len(box) - 3, 4)}
    return bool(brands & BRANDS)


def decode(data, max_pixels, min_side):
    """Decode HEIC bytes in a child process. Returns (RGB image, 35 mm-equivalent focal
    length or None). Raises HeicError."""
    try:
        child = subprocess.run(
            [sys.executable, "-m", "backend.heic", str(max_pixels), str(min_side)],
            input=data,
            capture_output=True,
            timeout=TIMEOUT,
            cwd=ROOT,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise HeicError("decode") from exc
    header, _, pixels = child.stdout.partition(b"\n")
    try:
        result = json.loads(header)
        if child.returncode != 0 or "error" in result:
            raise HeicError(result.get("error", "decode"))
        width, height = int(result["width"]), int(result["height"])
        if len(pixels) != width * height * 3 or not 0 < width * height <= max_pixels:
            raise HeicError("decode")
        focal = result.get("focal_35mm")
        focal = float(focal) if isinstance(focal, (int, float)) and 5 <= focal <= 600 else None
        return Image.frombytes("RGB", (width, height), pixels), focal
    except (ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, HeicError):
            raise
        raise HeicError("decode") from exc


def _limit_resources():
    """Bound the child's memory and processor time where the platform allows it."""
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT, TIMEOUT))
        resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
    except (ImportError, ValueError, OSError):  # Not POSIX, or a limit the system refuses.
        pass


def main():
    max_pixels, min_side = int(sys.argv[1]), int(sys.argv[2])
    data = sys.stdin.buffer.read()
    _limit_resources()
    from pi_heif import register_heif_opener

    register_heif_opener(decode_threads=1)

    def reply(header, pixels=b""):
        sys.stdout.buffer.write(json.dumps(header).encode() + b"\n" + pixels)
        sys.stdout.buffer.flush()

    with Image.open(io.BytesIO(data)) as raw:
        if raw.format != "HEIF":
            return reply({"error": "decode"})
        if raw.width * raw.height > max_pixels:
            return reply({"error": "pixels"})
        if min(raw.size) < min_side:
            return reply({"error": "small"})
        raw.load()
        try:
            focal = float(raw.getexif().get_ifd(0x8769).get(0xA405))  # FocalLengthIn35mmFilm
        except Exception:  # noqa: BLE001 - optional metadata; any malformed value is ignored.
            focal = None
        if "A" in raw.getbands():
            image = Image.new("RGB", raw.size, "white")
            image.paste(raw.convert("RGBA"), mask=raw.convert("RGBA").getchannel("A"))
        else:
            image = raw.convert("RGB")
    reply({"width": image.width, "height": image.height, "focal_35mm": focal}, image.tobytes())


if __name__ == "__main__":
    main()
