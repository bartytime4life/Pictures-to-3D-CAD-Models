"""Optional DINOv3 vision features for the photo library, run in a separate local process.

DINOv3 (Siméoni et al., Meta AI, 2025) is a self-supervised Vision Transformer. The
library uses its frozen ViT backbones, distilled from the ViT-7B on the LVD-1689M web
image set, to describe each photograph by feature vectors: one for the whole picture and
one per 16 x 16 pixel patch. Nothing is trained or fine-tuned here.

Licence and installation
    The code and weights are released under Meta's DINOv3 License, not an open-source
    licence, and the weights are only handed out after a request form. They are never
    downloaded, bundled or redistributed by this project. ``scripts/vision-model.sh``
    builds a separate Python environment (PyTorch and the DINOv3 code at one pinned
    commit) and links weight files the user obtained from Meta. Every file is identified
    by its full SHA-256 below and checked before it is loaded; a different or damaged
    file is refused.

Why a separate process
    PyTorch is several gigabytes and is not a dependency of the workbench. The model
    runs in ``backend/vision_worker.py`` under the vision environment's own Python. The
    process is started when pictures are first processed and stopped after five idle
    minutes, which returns the graphics memory. A crash there is an ordinary refusal
    here. This is containment of failures, not a security sandbox.

What the features are used for, and their limits, are described in
``backend/vision_math.py`` and docs/photo-library.md.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
WORKER = Path(__file__).resolve().parent / "vision_worker.py"
LICENSE = "DINOv3 License (Meta)"
CODE_COMMIT = "6876159a11b4df116f30f667f8c9888617df0751"  # facebookresearch/dinov3
INSTALL_HINT = "See docs/photo-library.md, then run ./scripts/vision-model.sh install."
IDLE_SECONDS = 300
START_TIMEOUT = 240
STANDIN = "stand-in"

#: The LVD-1689M ViT backbones the library can use, as Meta names and ships them. The
#: order is the preference on a graphics card: on the rendered benchmark ViT-B/16 matched
#: parts best and runs about three times faster than ViT-L/16 (docs/validation/photo-library.md).
#: ``group``, ``split`` and ``lookalike`` are that model's cosine thresholds: for the
#: same-subject links, for breaking up chained groups by average likeness
#: (vision_math.split_chained) and for near-identical pictures. They were chosen on seven
#: rendered parts and scored on seven others (scripts/vision_benchmark.py --calibrate):
#: of the link and split pairs within 0.02 of the best pair F1, the strictest was taken,
#: because a group that wrongly merges two parts hides one of them.
MODELS = {
    "vitb16": {
        "name": "DINOv3 ViT-B/16",
        "file": "dinov3_vitb16_pretrain_lvd1689m-73cec8be.pth",
        "sha256": "73cec8be7427c8655ceced13ce62f6e20a1fa90d1b4d4a550df17a1144081a7c",
        "bytes": 342_860_279,
        "dim": 768,
        "group": 0.84,
        "split": 0.8,
        "lookalike": 0.96,
    },
    "vitl16": {
        "name": "DINOv3 ViT-L/16",
        "file": "dinov3_vitl16_pretrain_lvd1689m-8aa4cbdd.pth",
        "sha256": "8aa4cbddda325040fc78db2c272754af6ebe8ff2c55f6ec4f1964d8890f66035",
        "bytes": 1_213_050_671,
        "dim": 1024,
        "group": 0.82,
        "split": 0.78,
        "lookalike": 0.96,
    },
    "vits16plus": {
        "name": "DINOv3 ViT-S+/16",
        "file": "dinov3_vits16plus_pretrain_lvd1689m-4057cbaa.pth",
        "sha256": "4057cbaaad8c16657adb09d6815f28d4164eeba30532fde23f0d17313124caea",
        "bytes": 114_924_783,
        "dim": 384,
        "group": 0.84,
        "split": 0.8,
        "lookalike": 0.96,
    },
    "vits16": {
        "name": "DINOv3 ViT-S/16",
        "file": "dinov3_vits16_pretrain_lvd1689m-08c60483.pth",
        "sha256": "08c60483bc63c04f533611e34bf70b120eedb7240f469bc16e9e20bf344b941d",
        "bytes": 86_531_063,
        "dim": 384,
        "group": 0.84,
        "split": 0.8,
        "lookalike": 0.96,
    },
}
#: Without a graphics card the smallest model is preferred: it is the only one quick
#: enough on a processor to index more than a few hundred pictures.
CPU_ORDER = ("vits16", "vits16plus", "vitb16", "vitl16")
STANDIN_MODEL = {"name": "Stand-in (tests only)", "dim": 12, "group": 0.70, "split": 0.5, "lookalike": 0.9995}

_lock = threading.Lock()
_digests: dict[tuple, str] = {}  # File state -> SHA-256, so each file is hashed once.


class VisionError(RuntimeError):
    """The vision model is unavailable or failed (user-facing message)."""


def standin_enabled() -> bool:
    return os.environ.get("PICAD_VISION_STANDIN") == "1"


def weights_dir() -> Path:
    override = os.environ.get("PICAD_VISION_WEIGHTS")
    return Path(override).expanduser() if override else ROOT / ".local" / "vision-model"


def python_path() -> Path:
    override = os.environ.get("PICAD_VISION_PYTHON")
    return Path(override).expanduser() if override else ROOT / ".local" / "vision-env" / "bin" / "python"


def model_info(model: str) -> dict:
    return STANDIN_MODEL if model == STANDIN else MODELS[model]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verified(model: str, directory: Path | None = None) -> Path | None:
    """The model's weight file if present with the pinned size and SHA-256, else None."""
    entry = MODELS[model]
    path = (directory or weights_dir()) / entry["file"]
    try:
        stat = path.stat()
    except OSError:
        return None
    if stat.st_size != entry["bytes"]:
        return None
    key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino)
    with _lock:
        if key not in _digests:
            _digests[key] = _sha256(path)
        digest = _digests[key]
    return path if digest == entry["sha256"] else None


def installed(directory: Path | None = None) -> dict[str, Path]:
    """Verified weight files, in graphics-card preference order."""
    found = {}
    for model in MODELS:
        path = verified(model, directory)
        if path:
            found[model] = path
    return found


def candidates() -> dict[str, Path]:
    """The models the worker may choose from: PICAD_VISION_MODEL alone, or all installed."""
    found = installed()
    wanted = os.environ.get("PICAD_VISION_MODEL", "").strip()
    if wanted:
        if wanted not in MODELS:
            raise VisionError(f"PICAD_VISION_MODEL must be one of {', '.join(MODELS)}.")
        if wanted not in found:
            raise VisionError(f"{MODELS[wanted]['name']} is not installed. {INSTALL_HINT}")
        return {wanted: found[wanted]}
    return found


def status() -> dict:
    """Describe availability without starting the model. Hashes are cached per file state."""
    info = {
        "available": False,
        "reason": "",
        "model": None,
        "license": LICENSE,
        "installed": [],
        "runtime": engine.runtime(),
        "standin": False,
    }
    if standin_enabled():
        info.update(available=True, model=STANDIN_MODEL["name"], license="none", standin=True)
        return info
    try:
        found = candidates()
    except VisionError as exc:
        info["reason"] = str(exc)
        return info
    info["installed"] = [MODELS[model]["name"] for model in found]
    if not python_path().is_file():
        info["reason"] = f"The vision environment is not installed. {INSTALL_HINT}"
        return info
    if not found:
        info["reason"] = f"No verified DINOv3 weight file is installed. {INSTALL_HINT}"
        return info
    failure = engine.failure()
    if failure:
        info["reason"] = failure
        return info
    running = info["runtime"]
    info["available"] = True
    info["model"] = model_info(running["model"])["name"] if running else next(iter(info["installed"]))
    return info


class Engine:
    """One worker process, started on demand. Calls are serialized."""

    def __init__(self):
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._replies: queue.Queue | None = None
        self._hello: dict | None = None
        self._failure = ""
        self._failure_key: tuple | None = None
        self._serial = 0
        self._last_used = 0.0
        self._started_with: tuple | None = None
        self._watchdog: threading.Thread | None = None

    # ------------------------------------------------------------- state

    def runtime(self) -> dict | None:
        """What the worker reported when it last started with the present settings
        (device, model), or None if it has not been started with them."""
        if self._hello and self._started_with == self._configuration():
            return dict(self._hello)
        return None

    def _configuration(self) -> tuple:
        return (
            standin_enabled(),
            str(python_path()),
            str(weights_dir()),
            os.environ.get("PICAD_VISION_MODEL", ""),
            os.environ.get("PICAD_VISION_DEVICE", ""),
        )

    def failure(self) -> str:
        """Why the last start failed, while the configuration is unchanged."""
        return self._failure if self._failure_key == self._configuration() else ""

    def forget_failure(self):
        self._failure, self._failure_key = "", None

    # ------------------------------------------------------------ process

    def _command(self) -> list[str]:
        if standin_enabled():
            return [sys.executable, str(WORKER), "--standin"]
        found = candidates()
        if not python_path().is_file() or not found:
            raise VisionError(status()["reason"] or f"The vision model is not installed. {INSTALL_HINT}")
        command = [str(python_path()), str(WORKER)]
        command += ["--candidates", json.dumps({model: str(path) for model, path in found.items()})]
        command += ["--cpu-order", ",".join(CPU_ORDER)]
        device = os.environ.get("PICAD_VISION_DEVICE", "").strip()
        if device:
            command += ["--device", device]
        return command

    def _start(self):
        command = self._command()
        log_dir = ROOT / ".local" / "vision-model"
        log_dir.mkdir(parents=True, exist_ok=True)
        log = (log_dir / "worker.log").open("wb")
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=log,
                cwd=ROOT,
                # One BLAS thread per NumPy call: the worker runs several such calls at
                # once in its own threads, and nested BLAS threads only contend.
                env={**os.environ, "PYTHONUNBUFFERED": "1", "OPENBLAS_NUM_THREADS": "1"},
            )
        except OSError as exc:
            raise VisionError(f"The vision environment could not be started: {exc}") from exc
        finally:
            log.close()
        replies: queue.Queue = queue.Queue()

        def pump():
            for raw in process.stdout:
                try:
                    replies.put(json.loads(raw))
                except ValueError:
                    continue
            replies.put(None)  # The worker ended.

        threading.Thread(target=pump, daemon=True, name="vision-replies").start()
        self._process, self._replies = process, replies
        hello = self._receive(START_TIMEOUT)
        if not hello or not hello.get("ready"):
            reason = (hello or {}).get("error") or self._log_tail() or "it ended without a message"
            self._stop()
            raise VisionError(f"The vision model could not start: {reason}")
        self._hello = hello
        if self._watchdog is None:
            self._watchdog = threading.Thread(target=self._idle_loop, daemon=True, name="vision-idle")
            self._watchdog.start()

    def _log_tail(self) -> str:
        try:
            text = (ROOT / ".local" / "vision-model" / "worker.log").read_text("utf-8", "replace")
        except OSError:
            return ""
        lines = [line for line in text.strip().splitlines() if line.strip()]
        return lines[-1][:300] if lines else ""

    def _receive(self, timeout: float) -> dict | None:
        try:
            return self._replies.get(timeout=timeout)
        except queue.Empty:
            return None

    def _stop(self):
        process, self._process, self._replies = self._process, None, None
        if process is None:
            return
        try:
            if process.poll() is None:
                process.stdin.write(b'{"op":"quit"}\n')
                process.stdin.flush()
                process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
        if process.poll() is None:
            process.kill()
            process.wait()
        for stream in (process.stdin, process.stdout):
            try:
                stream.close()
            except OSError:
                pass

    def _idle_loop(self):
        while True:
            time.sleep(15)
            idle = float(os.environ.get("PICAD_VISION_IDLE_SECONDS", IDLE_SECONDS))
            waited = self._process is not None and time.monotonic() - self._last_used > idle
            if waited and self._lock.acquire(blocking=False):
                try:
                    if time.monotonic() - self._last_used > idle:
                        self._stop()
                finally:
                    self._lock.release()

    def close(self):
        with self._lock:
            self._stop()

    # -------------------------------------------------------------- calls

    def start(self) -> dict:
        """Start the worker if needed and return what it reported about itself."""
        with self._lock:
            self._ensure()
            self._last_used = time.monotonic()
            return dict(self._hello)

    def _ensure(self):
        configuration = self._configuration()
        running = self._process is not None and self._process.poll() is None
        if running and self._started_with == configuration:
            return
        self._stop()  # Ended, or the environment settings changed since it started.
        try:
            self._start()
        except VisionError as exc:
            self._failure, self._failure_key = str(exc), configuration
            raise
        self._started_with = configuration
        self.forget_failure()

    def embed(self, paths: list[str | Path], workdir: Path) -> tuple[dict, dict[int, str]]:
        """Features for the pictures at ``paths``. Returns (arrays, {index: failure reason}).

        ``arrays`` has ``whole`` and ``subject`` (N x D unit vectors), ``mask`` (packed
        bits of the subject grid), ``box`` (N x 4, NaN without a subject) and ``ok``.
        """
        if not paths:
            raise ValueError("No pictures to embed.")
        with self._lock:
            self._ensure()
            self._serial += 1
            workdir.mkdir(parents=True, exist_ok=True)
            out = workdir / f"features-{uuid.uuid4().hex}.npz"
            request = {"id": self._serial, "op": "embed", "paths": [str(p) for p in paths], "out": str(out)}
            try:
                self._process.stdin.write((json.dumps(request) + "\n").encode("utf-8"))
                self._process.stdin.flush()
                reply = self._receive(60 + 3 * len(paths))
                if reply is None or reply.get("id") != self._serial:
                    raise VisionError("The vision model stopped responding and was restarted.")
                if not reply.get("ok"):
                    raise VisionError(f"The vision model failed: {reply.get('error', 'unknown error')}")
                with np.load(out) as data:
                    arrays = {key: data[key] for key in ("whole", "subject", "mask", "box", "ok")}
            except (OSError, ValueError, KeyError) as exc:
                self._stop()
                raise VisionError(f"The vision model failed: {exc}") from exc
            except VisionError:
                self._stop()
                raise
            finally:
                out.unlink(missing_ok=True)
                self._last_used = time.monotonic()
            failed = {int(index): str(reason) for index, reason in reply.get("failed", [])}
            return arrays, failed


engine = Engine()
atexit.register(engine.close)


def current_model() -> str:
    """Identifier of the model whose features are being produced (starts the worker)."""
    return engine.start()["model"]
