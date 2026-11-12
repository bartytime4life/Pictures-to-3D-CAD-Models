"""Reproduce wall-localization development cases against a pinned Git baseline.

    .venv/bin/python scripts/wall_localization_study.py --output NEW_DIRECTORY

Both implementations receive identical independent Gaussian rectangle/wall fields.
This is a local segmentation/subpixel/refinement comparison, not physical accuracy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import importlib.abc
import importlib.util
import itertools
import json
import math
import platform
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "studies/wall-localization-v1.json"
sys.path.insert(0, str(ROOT))
_ERFC = np.frompyfunc(math.erfc, 1, 1)


def cdf(z):
    return 0.5 * np.asarray(_ERFC(-np.asarray(z) / math.sqrt(2)), dtype=float)


def edge_response(t, sigma, aperture):
    """Independent Gaussian step, optionally averaged over a unit pixel interval."""
    if not aperture:
        return cdf(t / sigma)

    def integral(x):
        return x * cdf(x / sigma) + sigma * np.exp(-0.5 * (x / sigma) ** 2) / math.sqrt(2 * math.pi)

    return integral(t + 0.5) - integral(t - 0.5)


def transform(points, quarter, width, inverse=False):
    points = np.asarray(points)
    if not quarter:
        return points.copy()
    if inverse:
        return np.stack((width - points[..., 1], points[..., 0]), axis=-1)
    return np.stack((points[..., 1], width - points[..., 0]), axis=-1)


def render_scene(plan, wall, sigma, phase, quarter, inverted, observation):
    width, height = plan["image_size"]
    left, right, top, bottom = 60 + phase, 130 + phase, 40 + phase, 120 + phase
    rate = plan["thickness_mm"] / (plan["camera_height_mm"] - plan["thickness_mm"])
    band = rate * left
    yy, xx = np.mgrid[:height, :width] + 0.5
    aperture = observation == "uniform_pixel_mean"
    sx = edge_response(xx - left, sigma, aperture) - edge_response(xx - right, sigma, aperture)
    sy = edge_response(yy - top, sigma, aperture) - edge_response(yy - bottom, sigma, aperture)
    sw = edge_response(xx - left, sigma, aperture) - edge_response(xx - left - band, sigma, aperture)
    image = plan["paper_level"] + (plan["top_level"] - plan["paper_level"]) * sx * sy
    image += (wall - plan["top_level"]) * sw * sy
    if quarter:
        image = np.rot90(image)
    if inverted:
        image = 255 - image
    if not np.isfinite(image).all() or image.min() < 0 or image.max() > 255:
        raise ArithmeticError("independent light field outside [0,255]")
    value = image / 255
    encoded = np.where(value <= 0.0031308, 12.92 * value,
                       1.055 * np.maximum(value, 0.0031308) ** (1 / 2.4) - 0.055)
    saved = np.rint(255 * encoded).astype(np.uint8)
    nadir_px = transform(np.asarray([0., (top + bottom) / 2]), quarter, width)
    camera = {"height_mm": plan["camera_height_mm"], "nadir_mm": nadir_px / plan["ppm"]}
    return image, saved, camera, (left, right, top, bottom)


class PinnedBackend(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Load trusted repository Python from an exact local Git commit in its own package."""

    def __init__(self, revision):
        self.revision = revision
        self.namespace = "_wall_baseline_" + revision[:12]
        self.sources, self.hashes = {}, {}

    def find_spec(self, fullname, path=None, target=None):
        if fullname != self.namespace and not fullname.startswith(self.namespace + "."):
            return None
        relative = "backend" + fullname[len(self.namespace):].replace(".", "/")
        relative += "/__init__.py" if fullname == self.namespace else ".py"
        raw = subprocess.check_output(["git", "show", f"{self.revision}:{relative}"], cwd=ROOT)
        self.sources[fullname] = relative, raw
        return importlib.util.spec_from_loader(fullname, self, is_package=fullname == self.namespace)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        relative, raw = self.sources[module.__name__]
        module.__file__ = f"git:{self.revision}:{relative}"
        self.hashes[relative] = hashlib.sha256(raw).hexdigest()
        # Execute only repository source from the plan's exact trusted local Git commit.
        exec(compile(raw, module.__file__, "exec"), module.__dict__)  # noqa: S102


def image_hash(value):
    return hashlib.sha256(np.asarray(value, dtype="<f8").tobytes()).hexdigest()


def run_pipeline(modules, image, saved, camera, geometry, plan, quarter, inverted):
    edges, reference = modules
    start = time.perf_counter()
    mask, segment_notes = edges.segment(saved, plan["ppm"], part_lighter=inverted)
    rings, sigma, tiny = edges.subpixel_rings(mask, image, plan["ppm"])
    index = next(i for i, ring in enumerate(rings) if ring["outer"])
    before = rings[index]["points"].copy()
    if not math.isfinite(sigma) or sigma < 0 or not np.isfinite(before).all():
        raise ArithmeticError("non-finite initial observations or invalid blur")
    original = transform(before, quarter, plan["image_size"][0], inverse=True)
    left, _, top, bottom = geometry
    selected = (original[:, 0] < left + 10) & (original[:, 1] > top + 15) & (original[:, 1] < bottom - 15)
    if not selected.any():
        raise ArithmeticError("no selected left-edge observations")
    refined, notes = reference._refine_walls(image, rings, camera, plan["thickness_mm"], sigma, plan["ppm"])
    after = refined[index][0]
    if after.shape != before.shape or not np.isfinite(after).all():
        raise ArithmeticError("invalid refined boundary")
    final = transform(after, quarter, plan["image_size"][0], inverse=True)
    errors = final[selected, 0] - left
    initial_errors = original[selected, 0] - left
    if not np.isfinite(errors).all() or not np.isfinite(initial_errors).all():
        raise ArithmeticError("non-finite selected boundary errors")
    return {"ring_points": len(before), "selected_points": int(selected.sum()), "sigma_used_px": float(sigma),
            "initial_min_px": float(initial_errors.min()), "initial_max_px": float(initial_errors.max()),
            "final_min_px": float(errors.min()), "final_max_px": float(errors.max()),
            "maximum_absolute_error_px": float(np.max(np.abs(errors))),
            "moved_selected_points": int(np.count_nonzero(np.any(after[selected] != before[selected], axis=1))),
            "initial_points_sha256": image_hash(before), "tiny": int(tiny),
            "notes": json.dumps(segment_notes + notes), "elapsed_seconds": time.perf_counter() - start}


def run_study(plan, baseline):
    current = importlib.import_module("backend.edges"), importlib.import_module("backend.reference")
    prior = importlib.import_module(baseline.namespace + ".edges"), importlib.import_module(baseline.namespace + ".reference")
    rows = []
    scenes = itertools.product(plan["wall_levels"], plan["sigmas_px"], plan["phases_px"], plan["quarter_turns"],
                               plan["contrast_inversions"], plan["observations"])
    for scene_id, values in enumerate(scenes):
        quarter, inverted = values[3], values[4]
        image, saved, camera, geometry = render_scene(plan, *values)
        row = dict(zip(("wall_level", "sigma_optical_px", "phase_px", "quarter_turns", "contrast_inverted", "observation"), values))
        row.update(scene_id=scene_id, linear_image_sha256=image_hash(image),
                   segmentation_image_sha256=hashlib.sha256(saved.tobytes()).hexdigest())
        for label, modules in (("baseline", prior), ("candidate", current)):
            result = {key: None for key in ("ring_points", "selected_points", "sigma_used_px", "initial_min_px", "initial_max_px",
                                            "final_min_px", "final_max_px", "maximum_absolute_error_px", "moved_selected_points",
                                            "initial_points_sha256", "tiny", "notes", "elapsed_seconds")}
            error = None
            try:
                result.update(run_pipeline(modules, image, saved, camera, geometry, plan, quarter, inverted))
            except (ArithmeticError, ValueError, StopIteration, cv2.error, np.linalg.LinAlgError) as exc:
                error = f"{type(exc).__name__}: {exc}"
            row.update({label + "_" + key: value for key, value in result.items()})
            row[label + "_error"] = error
        if (row["baseline_error"] is None and row["candidate_error"] is None
                and row["baseline_initial_points_sha256"] != row["candidate_initial_points_sha256"]):
            raise ArithmeticError("pre-refinement observations changed between implementations")
        rows.append(row)
    return rows


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["wall_level"], row["observation"])].append(row)
    summary = []
    for (wall, observation), group in sorted(groups.items()):
        record = {"wall_level": wall, "observation": observation, "planned": len(group)}
        for label in ("baseline", "candidate"):
            valid = [r for r in group if r[label + "_error"] is None]
            if any(not math.isfinite(r[label + "_maximum_absolute_error_px"]) for r in valid):
                raise ArithmeticError("non-finite successful lane in summary")
            record[label + "_failed"] = len(group) - len(valid)
            record[label + "_maximum_absolute_error_px"] = max((r[label + "_maximum_absolute_error_px"] for r in valid), default=None)
            record[label + "_scenes_with_movement"] = sum(r[label + "_moved_selected_points"] > 0 for r in valid)
        summary.append(record)
    return summary


def source_hashes():
    files = ["scripts/wall_localization_study.py", "studies/wall-localization-v1.json"]
    files += subprocess.check_output(["git", "ls-files", "backend/*.py"], cwd=ROOT, text=True).splitlines()
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new result directory; existing paths refused")
    args = parser.parse_args(arguments)
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output already exists; choose a new directory")
    plan = json.loads(PLAN.read_text())
    hashes = source_hashes()
    revision = subprocess.check_output(["git", "rev-parse", "--verify", "--end-of-options", plan["baseline_revision"] + "^{commit}"],
                                       cwd=ROOT, text=True).strip()
    baseline = PinnedBackend(revision)
    sys.meta_path.insert(0, baseline)
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    try:
        rows = run_study(plan, baseline)
    finally:
        sys.meta_path.remove(baseline)
    if source_hashes() != hashes:
        raise RuntimeError("study source changed during execution")
    expected = math.prod(len(plan[k]) for k in ("wall_levels", "sigmas_px", "phases_px", "quarter_turns", "contrast_inversions", "observations"))
    assert len(rows) == expected
    with (args.output / "cases.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = {"format": "pictures-to-cad-wall-localization-result", "version": 1,
              "execution_complete": True, "physical_qualification": False, "world_scenes": len(rows),
              "baseline_revision": revision, "baseline_loaded_source_sha256": baseline.hashes,
              "source_sha256": hashes, "cases_sha256": hashlib.sha256((args.output / "cases.csv").read_bytes()).hexdigest(),
              "failed_lanes": sum(r[label + "_error"] is not None for r in rows for label in ("baseline", "candidate")),
              "summary": summarize(rows),
              "git": {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                      "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))},
              "runtime": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__},
              "limitations": plan["limitations"]}
    (args.output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("execution_complete", "physical_qualification", "world_scenes", "failed_lanes")}))
    return int(result["failed_lanes"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
