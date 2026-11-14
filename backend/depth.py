"""Optional single-photo depth estimation with a pinned, locally stored model.

The model is Depth Anything V2 Small (Yang et al., 2024), Apache-2.0, exported to ONNX
by the onnx-community project. It is never downloaded by setup: run
``./scripts/depth-model.sh install`` to fetch the exact file pinned below. Every load
checks its SHA-256, so a different or damaged file is refused instead of run.

What the network returns
    A *relative inverse depth* (disparity-like) map: larger values are nearer. Like
    MiDaS, the model is trained with a scale- and shift-invariant loss, so its output is
    only defined up to d = a / z + b with unknown a > 0 and b. Ordering (what is in front
    of what) is meaningful; ratios and absolute distances are not. Two known depths in
    the scene would be needed to recover a and b; a single photograph has none.

How the workbench uses it
    The disparity is resampled to the photograph's pixels and normalized to 0..1 with
    white = nearest, the same convention as a stored depth map. Physical size still
    comes only from the width and thickness range the user enters. A relief is a
    compressed (bas-relief) rendering of depth in any case: under orthographic viewing a
    surface z(x, y) and lambda * z(x, y) + mu * x + nu * y shade identically under
    suitably transformed lighting (the generalized bas-relief ambiguity, Belhumeur,
    Kriegman and Yuille, 1999), which is why sculptors may flatten depth freely.

Pre-processing follows the model's published DPTImageProcessor configuration exactly:
keep aspect ratio, scale so that the side whose scale factor is closest to 1 reaches 518
pixels, round each side to a multiple of 14 (the ViT patch size), bicubic resampling,
rescale to 0..1 and normalize with the ImageNet mean and standard deviation.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "Depth Anything V2 Small"
MODEL_LICENSE = "Apache-2.0"
MODEL_REPOSITORY = "onnx-community/depth-anything-v2-small"
MODEL_REVISION = "4472b7362082ad9968fee890ca0f1e5aca36b93d"
MODEL_FILE = "onnx/model.onnx"
MODEL_SHA256 = "afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c"
MODEL_BYTES = 99_060_839
MODEL_URL = f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/{MODEL_REVISION}/{MODEL_FILE}"
DEFAULT_PATH = ROOT / ".local" / "depth-model" / "depth-anything-v2-small.onnx"

TARGET_SIDE = 518  # preprocessor_config.json "size"
PATCH = 14  # ViT-S/14 patch size: "ensure_multiple_of"
MAX_INPUT_SIDE = 3 * TARGET_SIDE  # Our bound for very elongated pictures; see input_size.
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
INSTALL_HINT = "Install it with ./scripts/depth-model.sh install, then restart the workbench."

_lock = threading.Lock()
_digests: dict[tuple, str] = {}  # File state -> SHA-256, so each file is hashed once.


class DepthError(ValueError):
    """The depth model is unavailable or the picture cannot be estimated (user-facing)."""


def model_path() -> Path:
    override = os.environ.get("PICAD_DEPTH_MODEL")
    return Path(override).expanduser() if override else DEFAULT_PATH


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _runtime_available() -> bool:
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def status(path: Path | None = None) -> dict:
    """Describe availability without running the model. The hash is cached per file state."""
    path = path or model_path()
    info = {
        "available": False,
        "model": MODEL_NAME,
        "license": MODEL_LICENSE,
        "revision": MODEL_REVISION[:12],
        "bytes": MODEL_BYTES,
        "reason": "",
    }
    if not _runtime_available():
        info["reason"] = "The ONNX runtime is not installed. Run ./scripts/setup.sh again."
        return info
    try:
        stat = path.stat()
    except OSError:
        info["reason"] = f"The depth model is not installed. {INSTALL_HINT}"
        return info
    if stat.st_size != MODEL_BYTES:
        info["reason"] = f"The depth model file has the wrong size. {INSTALL_HINT}"
        return info
    key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino)
    with _lock:
        if key not in _digests:
            _digests[key] = _sha256(path)
        digest = _digests[key]
    if digest != MODEL_SHA256:
        info["reason"] = f"The depth model file failed its SHA-256 check. {INSTALL_HINT}"
        return info
    info["available"] = True
    return info


def _constrain(value: float, multiple: int = PATCH) -> int:
    """DPTImageProcessor's constrain_to_multiple_of (no min/max bound): nearest multiple."""
    return max(multiple, int(round(value / multiple) * multiple))


def input_size(width: int, height: int) -> tuple[int, int]:
    """Network input (width, height) for a picture, following the model's preprocessor.

    With keep_aspect_ratio the processor computes both scale factors to 518 and keeps
    the one closer to 1, so a large photo is shrunk until its *short* side is 518 and a
    small one is enlarged until its *long* side is 518. Each side is then rounded to a
    multiple of 14. For pictures more elongated than 3:1 we additionally limit the long
    side to 1554 pixels (3 x 518), which bounds memory and run time; the notes say so.
    """
    scale_w, scale_h = TARGET_SIDE / width, TARGET_SIDE / height
    scale = scale_w if abs(1 - scale_w) < abs(1 - scale_h) else scale_h
    if max(width, height) * scale > MAX_INPUT_SIDE:
        scale = MAX_INPUT_SIDE / max(width, height)
    return _constrain(width * scale), _constrain(height * scale)


def preprocess(rgb: np.ndarray) -> np.ndarray:
    """uint8 H x W x 3 sRGB -> float32 1 x 3 x h x w network input."""
    height, width = rgb.shape[:2]
    size = input_size(width, height)
    resized = Image.fromarray(rgb, "RGB").resize(size, Image.Resampling.BICUBIC)
    x = (np.asarray(resized, dtype=np.float32) / 255 - MEAN) / STD
    return np.ascontiguousarray(x.transpose(2, 0, 1)[None], dtype=np.float32)


def normalize(disparity: np.ndarray) -> np.ndarray:
    """Map relative inverse depth to 0..1 with white = nearest (min-max, no clipping).

    Min-max keeps every estimated value; the relief's auto levels later stretch the
    0.5th-99.5th percentiles when that option is on.
    """
    low, high = float(disparity.min()), float(disparity.max())
    if not np.isfinite(low) or not np.isfinite(high):
        raise DepthError("The depth model returned invalid values for this picture.")
    if high - low < 1e-9:
        return np.zeros_like(disparity, dtype=np.float64)
    return (disparity.astype(np.float64) - low) / (high - low)


class OnnxRunner:
    """Run the verified model on CPU. Created once per worker process."""

    def __init__(self, path: Path | None = None):
        path = path or model_path()
        state = status(path)
        if not state["available"]:
            raise DepthError(state["reason"])
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.log_severity_level = 3
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

    def __call__(self, x: np.ndarray) -> np.ndarray:
        output = self.session.run(None, {self.input_name: x})[0]
        return np.asarray(output, dtype=np.float32).reshape(output.shape[-2:])


def estimate_depth(image: Image.Image, runner=None) -> tuple[np.ndarray, dict]:
    """Estimate a 0..1 depth field (white = nearest) at the picture's own resolution.

    ``runner`` maps the 1 x 3 x h x w input to an h x w disparity; tests pass a stand-in.
    """
    if image.mode == "F":
        raise DepthError(
            "This picture is already a 16-bit depth map. Choose the Depth map picture type."
        )
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    x = preprocess(rgb)
    runner = runner or OnnxRunner()
    started = time.perf_counter()
    disparity = np.asarray(runner(x), dtype=np.float32)
    seconds = time.perf_counter() - started
    if disparity.ndim != 2 or disparity.shape[0] < 2 or disparity.shape[1] < 2:
        raise DepthError("The depth model returned an unexpected result for this picture.")
    full = cv2.resize(disparity, (width, height), interpolation=cv2.INTER_CUBIC)
    field = normalize(full)
    info = {
        "model": MODEL_NAME,
        "license": MODEL_LICENSE,
        "revision": MODEL_REVISION[:12],
        "input_px": [int(x.shape[3]), int(x.shape[2])],
        "seconds": round(seconds, 3),
    }
    return field, info


# ---------------------------------------------------------------------- scoring


def _ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks (ties share the mean rank), as used by Spearman's coefficient."""
    order = np.argsort(values, kind="stable")
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.arange(values.size, dtype=np.float64)
    sorted_values = values[order]
    starts = np.flatnonzero(np.r_[True, sorted_values[1:] != sorted_values[:-1]])
    ends = np.r_[starts[1:], values.size]
    for start, end in zip(starts, ends, strict=True):
        if end - start > 1:
            ranks[order[start:end]] = (start + end - 1) / 2
    return ranks


def score(estimate: np.ndarray, truth: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Compare an estimated depth field with true heights where ``mask`` is set.

    * ``spearman``: rank correlation, which measures ordering only and is unaffected by
      any monotonic rescaling of the estimate (+1 = same order, 0 = unrelated).
    * ``pearson``: linear correlation.
    * ``aligned_rms_fraction``: RMS error after the least-squares scale and shift that
      best map the estimate onto the truth (the alignment used to evaluate MiDaS-style
      relative depth), as a fraction of the true height span.
    """
    e = np.asarray(estimate, dtype=np.float64)
    t = np.asarray(truth, dtype=np.float64)
    if mask is not None:
        e, t = e[mask], t[mask]
    e, t = e.ravel(), t.ravel()
    if e.size < 3 or np.ptp(t) == 0:
        raise ValueError("Scoring needs at least three samples with varying truth.")
    design = np.c_[e, np.ones_like(e)]
    (scale, shift), *_ = np.linalg.lstsq(design, t, rcond=None)
    residual = t - design @ (scale, shift)
    flat = np.ptp(e) == 0
    return {
        "samples": int(e.size),
        "spearman": 0.0 if flat else float(np.corrcoef(_ranks(e), _ranks(t))[0, 1]),
        "pearson": 0.0 if flat else float(np.corrcoef(e, t)[0, 1]),
        "aligned_rms_fraction": float(np.sqrt(np.mean(residual**2)) / np.ptp(t)),
        "scale": float(scale),
        "shift": float(shift),
    }
