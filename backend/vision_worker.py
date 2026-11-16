"""The photo library's model process: python backend/vision_worker.py --candidates JSON

This file runs under the *vision environment's* Python (PyTorch and the DINOv3 code;
see scripts/vision-model.sh), not the workbench's. It imports nothing from the
workbench except ``vision_math``, which needs only NumPy. ``backend.vision`` starts it,
keeps it alive while pictures are being processed, and stops it when idle so the
graphics memory is returned.

Choosing the model
    ``--candidates`` is a JSON object of model identifier to verified weight file, in
    order of preference on a graphics card. Without one, the first identifier of
    ``--cpu-order`` that is a candidate is used instead: only the small models are quick
    enough on a processor.

Protocol (one JSON object per line)
    On start the worker loads the model and writes ``{"ready": true, ...}`` describing
    the device, or ``{"ready": false, "error": "..."}`` and exits.
    ``{"id": 1, "op": "embed", "paths": [...], "out": "/dir/result.npz"}`` reads those
    pictures, runs the model and writes an .npz file with, for every picture in order:
    ``whole`` (unit class-token vector), ``subject`` (unit mean of the subject's patch
    vectors), ``mask`` (the subject region, packed bits of a g x g grid), ``box``
    (x0, y0, x1, y1 as fractions of the picture, NaN when no subject) and ``ok``.
    The reply is ``{"id": 1, "ok": true, "failed": [[index, "reason"], ...]}``.
    ``{"op": "quit"}`` or end of input stops the worker.
    Everything else the libraries print goes to standard error.

Pictures are the library's own previews (at most 512 pixels on the long side). Each is
resized to a 448 x 448 square with bicubic resampling, the square resize the model's
authors use, and normalized with the ImageNet mean and standard deviation. On a CUDA
device the model runs under 16-bit autocast; the class tokens then agree with 32-bit
ones to a cosine of 0.99999 on the benchmark pictures.

``--standin`` replaces the network with simple colour and texture statistics. It needs
no PyTorch and exists so the workbench's tests can exercise this protocol and the
library without the model. It is not a vision model and is never chosen automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vision_math  # Sibling module: importable from either environment.

INPUT = 448
PATCH = 16
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
HUB = {
    "vits16": "dinov3_vits16",
    "vits16plus": "dinov3_vits16plus",
    "vitb16": "dinov3_vitb16",
    "vitl16": "dinov3_vitl16",
}


def read_picture(path: str) -> np.ndarray:
    """One preview as uint8 448 x 448 x 3."""
    from PIL import Image

    with Image.open(path) as picture:
        picture = picture.convert("RGB").resize((INPUT, INPUT), Image.Resampling.BICUBIC)
        return np.asarray(picture, dtype=np.uint8)


class Standin:
    """Colour and texture statistics per patch, in place of the network (tests only)."""

    name, device, device_name, precision, dim = "stand-in", "cpu", "no model", "float32", 12

    def features(self, pictures: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        batch = pictures.shape[0]
        grid = INPUT // PATCH
        cells = pictures.astype(np.float32).reshape(batch, grid, PATCH, grid, PATCH, 3) / 255
        mean = cells.mean(axis=(2, 4))
        spread = cells.std(axis=(2, 4))
        # Opponent colours and brightness make differently coloured regions point in
        # clearly different directions, as a real model's features do for different things.
        r, g, b = mean[..., 0], mean[..., 1], mean[..., 2]
        channels = [r, g, b, r - g, g - b, b - r, r + g + b - 1.5, *np.moveaxis(spread * 4, -1, 0)]
        channels += [np.abs(r - 0.5), np.abs(g - 0.5)]
        tokens = np.stack(channels, axis=-1).reshape(batch, grid * grid, -1).astype(np.float32)
        tokens = tokens - 0.25
        # Whole picture: the mean colour of each quarter of the frame, about mid-grey.
        half = grid // 2
        quarters = mean.reshape(batch, 2, half, 2, half, 3).mean(axis=(2, 4)).reshape(batch, 12) - 0.5
        return vision_math.unit(quarters), tokens


class Dinov3:
    def __init__(self, candidates: dict[str, str], cpu_order: list[str], device: str):
        import torch
        from dinov3.hub import backbones

        self.torch = torch
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        self.device = device
        if device == "cuda":
            self.device_name = torch.cuda.get_device_name(0)
        elif device == "mps":
            self.device_name = "Apple GPU"
        else:
            torch.set_num_threads(max(1, min(8, (os.cpu_count() or 2) - 1)))
            self.device_name = "CPU"
        self.precision = "float16 autocast" if device == "cuda" else "float32"
        order = list(candidates) if device != "cpu" else [m for m in cpu_order if m in candidates]
        model = next((m for m in order + list(candidates) if m in HUB and m in candidates), None)
        if model is None:
            raise ValueError("No usable model among the candidates.")
        weights = candidates[model]
        network = getattr(backbones, HUB[model])(pretrained=False)
        # weights_only: the file is read as tensors, never as executable pickle code.
        state = torch.load(weights, map_location="cpu", weights_only=True)
        network.load_state_dict(state, strict=True)
        self.network = network.to(device).eval()
        self.name = model
        self.dim = int(network.embed_dim)
        self.mean = torch.tensor(MEAN, device=device).view(1, 3, 1, 1)
        self.std = torch.tensor(STD, device=device).view(1, 3, 1, 1)

    def features(self, pictures: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        torch = self.torch
        x = torch.from_numpy(pictures).to(self.device).permute(0, 3, 1, 2).float().div_(255)
        x = (x - self.mean) / self.std
        with torch.inference_mode():
            if self.device == "cuda":
                with torch.autocast("cuda", dtype=torch.float16):
                    out = self.network.forward_features(x)
            else:
                out = self.network.forward_features(x)
        whole = out["x_norm_clstoken"].float().cpu().numpy()
        tokens = out["x_norm_patchtokens"].float().cpu().numpy()
        return vision_math.unit(whole), tokens


def embed(engine, paths: list[str], out: str, loaders: ThreadPoolExecutor, finishers: ThreadPoolExecutor, batch: int) -> list:
    """Read, run and describe ``paths``; write the arrays to ``out``. Returns failures.

    Three stages overlap: pictures are read by ``loaders`` threads, the model runs on
    this thread, and the subject of each finished batch is found by ``finishers``
    threads (NumPy releases the interpreter lock inside its array operations). At most
    six finished batches wait at once, which bounds the patch features held in memory.
    """
    grid = INPUT // PATCH
    count = len(paths)
    whole = np.zeros((count, engine.dim), np.float32)
    subject = np.zeros((count, engine.dim), np.float32)
    mask = np.zeros((count, (grid * grid + 7) // 8), np.uint8)
    box = np.full((count, 4), np.nan, np.float32)
    ok = np.zeros(count, bool)
    failed = []

    def load(index):
        try:
            return index, read_picture(paths[index]), None
        except Exception as exc:  # noqa: BLE001 - any unreadable preview is reported, not fatal.
            return index, None, f"{type(exc).__name__}: {exc}"[:200]

    def finish(rows, vectors, tokens):
        # Each call writes its own rows of the shared arrays, so no lock is needed.
        regions = vision_math.subject_regions(tokens)
        whole[rows] = vectors
        subject[rows] = vision_math.subject_vectors(tokens, regions)
        mask[rows] = np.packbits(regions.reshape(len(rows), -1), axis=1)
        for row, region in zip(rows, regions, strict=True):
            found = vision_math.region_box(region)
            if found:
                box[row] = found
        ok[rows] = True

    starts = list(range(0, count, batch))
    reading = [loaders.map(load, range(start, min(start + batch, count))) for start in starts[:2]]
    waiting = []
    for position in range(len(starts)):
        loaded = list(reading.pop(0))
        ahead = position + 2  # Keep two batches being read while the model runs.
        if ahead < len(starts):
            reading.append(loaders.map(load, range(starts[ahead], min(starts[ahead] + batch, count))))
        good = [(index, picture) for index, picture, error in loaded if error is None]
        failed += [[index, error] for index, _, error in loaded if error is not None]
        if not good:
            continue
        rows = [index for index, _ in good]
        vectors, tokens = engine.features(np.stack([picture for _, picture in good]))
        if not (np.isfinite(vectors).all() and np.isfinite(tokens).all()):
            failed += [[index, "The model returned invalid values."] for index in rows]
            continue
        waiting.append(finishers.submit(finish, rows, vectors, tokens))
        if len(waiting) >= 6:
            waiting.pop(0).result()
    for future in waiting:
        future.result()
    temporary = out + ".part"
    with open(temporary, "wb") as handle:
        np.savez(handle, whole=whole, subject=subject, mask=mask, box=box, ok=ok)
    os.replace(temporary, out)
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidates", default="{}")
    parser.add_argument("--cpu-order", default="vits16,vits16plus,vitb16,vitl16")
    parser.add_argument("--device", default="auto", choices=("auto", "cuda", "mps", "cpu"))
    parser.add_argument("--standin", action="store_true")
    args = parser.parse_args()

    protocol = os.fdopen(os.dup(1), "w", buffering=1, encoding="utf-8")
    os.dup2(2, 1)  # Anything a library prints goes to standard error from here on.
    sys.stdout = sys.stderr

    def send(message):
        protocol.write(json.dumps(message, separators=(",", ":")) + "\n")
        protocol.flush()

    try:
        if args.standin:
            engine = Standin()
            runtime = "none"
        else:
            candidates = json.loads(args.candidates)
            if not isinstance(candidates, dict) or not candidates:
                raise ValueError("--candidates must name at least one weight file.")
            engine = Dinov3(candidates, args.cpu_order.split(","), args.device)
            runtime = f"PyTorch {engine.torch.__version__}"
    except Exception as exc:  # noqa: BLE001 - reported to the workbench as the start-up reason.
        send({"ready": False, "error": f"{type(exc).__name__}: {exc}"[:500]})
        return 1
    batch = 32 if engine.device == "cuda" else 8
    send(
        {
            "ready": True,
            "model": engine.name,
            "device": engine.device,
            "device_name": engine.device_name,
            "precision": engine.precision,
            "runtime": runtime,
            "dim": engine.dim,
            "grid": INPUT // PATCH,
            "input": INPUT,
        }
    )
    with ThreadPoolExecutor(max_workers=8) as loaders, ThreadPoolExecutor(max_workers=4) as finishers:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except ValueError:
                send({"ok": False, "error": "Request is not JSON."})
                continue
            identifier = request.get("id")
            operation = request.get("op")
            if operation == "quit":
                break
            if operation == "ping":
                send({"id": identifier, "ok": True})
                continue
            if operation != "embed":
                send({"id": identifier, "ok": False, "error": "Unknown operation."})
                continue
            started = time.perf_counter()
            try:
                failed = embed(
                    engine, list(request["paths"]), str(request["out"]), loaders, finishers, batch
                )
            except Exception as exc:  # noqa: BLE001 - one failed request must not end the worker.
                send({"id": identifier, "ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]})
                continue
            send(
                {
                    "id": identifier,
                    "ok": True,
                    "failed": failed,
                    "seconds": round(time.perf_counter() - started, 3),
                }
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
