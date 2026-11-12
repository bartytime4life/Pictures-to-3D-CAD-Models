"""Repeat fixed raw-photo -> rectified smoothing -> Keys composition controls.

Run with --output NEW_JSON. All declared fields/maps/profiles are retained.
Measured float32 stage errors are not a calibrated camera-error distribution.
"""

import argparse
import hashlib
import itertools
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import profile_observations as observations
from backend import sheet

PLAN = ROOT / "studies/warp-observations-v1.json"


def source_fields(plan):
    yy, xx = np.mgrid[:plan["source_shape"][0], :plan["source_shape"][1]]
    xx, yy = xx + .5, yy + .5
    z = ((xx - 45.3) * .8 + (yy - 30.6) * .6) / 1.3
    cdf = .5 * np.asarray(np.frompyfunc(math.erfc, 1, 1)(-z / math.sqrt(2)), dtype=float)
    impulse = np.full_like(xx, 100.)
    impulse[4, 5] += 80
    fields = {"constant": np.full_like(xx, 137.25), "ramp": 80 + .6 * xx + .3 * yy,
              "smooth": 130 + 25 * np.sin(.31 * xx + .17 * yy) + 20 * np.cos(.13 * xx - .27 * yy),
              "random": np.random.default_rng(plan["random_seed"]).uniform(20, 220, size=xx.shape),
              "impulse": impulse, "gaussian_step": 90 + 80 * cdf}
    return {name: fields[name] for name in plan["fields"]}


def rectified64(source, matrix, k1, plane, ppm):
    """Float64 staged reference: actual map/sampler, omitting production's cast."""
    shape = tuple(round(v * ppm) for v in plane[::-1])
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    x, y = sheet.plane_to_photo(matrix, k1, source.shape[::-1], (xx + .5) / ppm, (yy + .5) / ppm)
    return sheet.sample_keys(source, x - .5, y - .5)


def gaussian_kernel(plan):
    support = np.asarray(plan["smoothing_support"])
    one = np.exp(-.5 * (support / plan["smoothing_sigma_px"])**2)
    one /= one.sum()
    return np.outer(one, one)


def profile_operators(plan, mapping, k1, ppm):
    shape = tuple(round(v * ppm) for v in plan["plane_size_mm"][::-1])
    count = round(plan["profile_half_width_px"] / plan["profile_step_px"])
    t = np.arange(-count, count + 1) * plan["profile_step_px"]
    kernel = gaussian_kernel(plan)
    result = []
    for profile in plan["profiles"]:
        x, y = np.asarray(profile["seed_plane_mm"])[:, None] * ppm + np.asarray(profile["normal"])[:, None] * t - .5
        final = observations.keys_profile(shape, x, y)
        smooth = final.after_filter(kernel, border="reflect101")
        full = smooth.after_rectification(tuple(plan["source_shape"]), np.asarray(mapping["matrix"]), k1,
                                           plan["plane_size_mm"], ppm)
        result.append((profile["name"], x, y, final, smooth, full))
    return result


def measure(source, rect64, rect32, blur64, blur32, blur_cast64, final, smooth, full, x, y):
    ideal = sheet.sample_keys(blur64, x, y)
    actual = sheet.sample_keys(blur32, x, y)
    predicted = full.sample(source)
    rect_error = rect32.astype(float) - rect64
    blur_error = blur32.astype(float) - blur_cast64
    rect_values = rect_error[smooth.pixels_xy[:, 1], smooth.pixels_xy[:, 0]]
    blur_values = blur_error[final.pixels_xy[:, 1], final.pixels_xy[:, 0]]
    stage_delta = smooth.matrix @ rect_values + final.matrix @ blur_values
    envelope = np.abs(smooth.matrix) @ np.abs(rect_values) + np.abs(final.matrix) @ np.abs(blur_values)
    # Arithmetic diagnostic only; this is not an interval or vendor-rounding proof.
    allowance = float(512 * np.finfo(float).eps * max(1., np.max(np.abs(source))) *
                      max(1., np.max(np.sum(np.abs(full.matrix), axis=1))))
    covariance = full.matrix @ full.matrix.T  # supplied unit independent raw noise only
    variances = np.diag(covariance)
    correlations = np.diag(covariance, 1) / np.sqrt(variances[:-1] * variances[1:])
    return {
        "float64_composition_maximum_error": float(np.max(np.abs(predicted - ideal))),
        "actual_float32_maximum_error": float(np.max(np.abs(predicted - actual))),
        "measured_stage_delta_reconstruction_error": float(np.max(np.abs(actual - predicted - stage_delta))),
        "measured_stage_triangle_envelope_maximum": float(np.max(envelope)),
        "arithmetic_allowance": allowance,
        "envelope_violation_count": int(np.count_nonzero(np.abs(actual - predicted) > envelope + allowance)),
        "rectification_cast_maximum": float(np.max(np.abs(rect_error))),
        "blur_float32_maximum": float(np.max(np.abs(blur_error))),
        "profile_samples": len(final.matrix), "intermediate_pixels": len(smooth.pixels_xy),
        "raw_pixels": len(full.pixels_xy), "matrix_cells": full.matrix.size,
        "matrix_sha256": hashlib.sha256(full.matrix.astype("<f8").tobytes()).hexdigest(),
        "partition_maximum_error": float(np.max(np.abs(full.matrix.sum(axis=1) - 1))),
        "conditional_adjacent_correlation_minimum": float(correlations.min()),
        "conditional_adjacent_correlation_maximum": float(correlations.max()),
    }


def run(plan):
    fields = source_fields(plan)
    kernel = gaussian_kernel(plan)
    impulse = np.zeros((17, 17))
    impulse[8, 8] = 1.
    expected = np.zeros_like(impulse)
    radius = len(kernel) // 2
    expected[8-radius:9+radius, 8-radius:9+radius] = kernel
    kernel_error = float(np.max(np.abs(cv2.GaussianBlur(impulse, (0, 0), plan["smoothing_sigma_px"]) - expected)))
    if kernel_error > 1e-15:
        raise ValueError("runtime Gaussian kernel does not match the declared finite support")
    rows = []
    for mapping, k1, ppm in itertools.product(plan["maps"], plan["radial_k1"], plan["pixels_per_mm"]):
        operators = profile_operators(plan, mapping, k1, ppm)
        for name, source in fields.items():
            rect64 = rectified64(source, np.asarray(mapping["matrix"]), k1, plan["plane_size_mm"], ppm)
            rect32 = sheet.rectify_gray(source, np.asarray(mapping["matrix"]), k1, plan["plane_size_mm"], ppm)
            blur64 = cv2.GaussianBlur(rect64, (0, 0), plan["smoothing_sigma_px"])
            blur32 = cv2.GaussianBlur(rect32, (0, 0), plan["smoothing_sigma_px"])
            blur_cast64 = cv2.GaussianBlur(rect32.astype(float), (0, 0), plan["smoothing_sigma_px"])
            for profile, x, y, final, smooth, full in operators:
                row = {"map": mapping["name"], "k1": k1, "ppm": ppm, "field": name, "profile": profile}
                row.update(measure(source, rect64, rect32, blur64, blur32, blur_cast64, final, smooth, full, x, y))
                rows.append(row)
    summary = {key: max(r[key] for r in rows) for key in ["float64_composition_maximum_error", "actual_float32_maximum_error",
               "measured_stage_delta_reconstruction_error", "measured_stage_triangle_envelope_maximum", "raw_pixels",
               "matrix_cells", "partition_maximum_error"]}
    summary.update({"rows": len(rows), "envelope_violation_count": sum(r["envelope_violation_count"] for r in rows),
                    "distinct_source_arrays": len(fields), "processed_chains": len(rows) // len(plan["profiles"])})
    return {"cases": rows, "summary": summary,
            "runtime_gaussian_impulse_maximum_error": kernel_error,
            "source_arrays_sha256": {name: hashlib.sha256(x.astype("<f8").tobytes()).hexdigest() for name, x in fields.items()}}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new JSON result; existing paths are refused")
    args = parser.parse_args(arguments)
    if args.output.exists():
        parser.error("output exists; choose a new JSON path")
    files = ["backend/profile_observations.py", "backend/sheet.py", "scripts/warp_observation_study.py", "studies/warp-observations-v1.json"]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    started = time.perf_counter()
    plan = json.loads(PLAN.read_text())
    result = run(plan)
    if hashes != {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}:
        raise ValueError("source changed during execution")
    result.update({"format": "picad-warp-observations-results", "version": 1, "plan": plan, "source_sha256": hashes,
                   "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "runtime": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__,
                               "seconds": time.perf_counter() - started},
                   "limits": ["Fixed supplied maps, profiles and already-linear synthetic arrays; no estimated camera/geometry.",
                              "Float64 reference intentionally shares production map/sampler; independent scalar tests check coordinates separately.",
                              "Stage errors are measured for these inputs. Triangle accounting plus arithmetic allowance is not a vendor-certified or physical bound.",
                              "Raw unit-noise correlation is supplied, not a measured or postselection-calibrated noise model.",
                              "No sensor PSF, detector aperture, nonlinear tone/channel response, full trace or physical accuracy qualification."]})
    content = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(content)
    print(f"Recorded {len(result['cases'])} warp/profile readouts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
