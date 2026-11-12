"""Known finite Gaussian plus Keys composition on fixed straight-edge controls.

Run with --output NEW_JSON. Neither this study nor its local numerical searches
qualify the earlier warp, camera, detector aperture or physical geometry.
"""

import argparse
import hashlib
import importlib.util
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
from backend import edges, profile_observations, sheet

PROTOTYPE = "studies/verification/wall-keys-forward-prototype-v1.py"
PROTOTYPE_SHA256 = "eb89f4e4a7c4c51b59482e303d848f605c1676518448ab7c0ff21c28b04da2ea"
ERFC = np.frompyfunc(math.erfc, 1, 1)


def cdf(x):
    return .5 * np.asarray(ERFC(-np.asarray(x) / math.sqrt(2)), dtype=float)


class Forward:
    """Adapter for the previously frozen finite-search development prototype."""

    def __init__(self, op, seed, normal, t):
        self.op, self.t = op, t
        self.distance = (op.pixels_xy + .5 - seed) @ normal

    def apply(self, value):
        return self.op.matrix @ value

    def probability(self, location, sigma, model):
        if model != "keys_point":
            raise ValueError("this adapter requires the explicitly composed point-source model")
        return self.apply(cdf((self.distance - location) / sigma))


def prototype():
    path = ROOT / PROTOTYPE
    if hashlib.sha256(path.read_bytes()).hexdigest() != PROTOTYPE_SHA256:
        raise ValueError("frozen search prototype changed; review and pin a new version")
    spec = importlib.util.spec_from_file_location("_postblur_search", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run():
    search = prototype()
    shape, rate, band_true, smoothing = (48, 128), .05, 3.25, .7
    support = np.arange(-3, 4)
    one = np.exp(-.5 * (support / smoothing)**2)
    one /= one.sum()
    kernel = np.outer(one, one)
    impulse = np.zeros((17, 17))
    impulse[8, 8] = 1
    expected = np.zeros_like(impulse)
    expected[5:12, 5:12] = kernel
    impulse_error = float(np.max(np.abs(cv2.GaussianBlur(impulse, (0, 0), smoothing) - expected)))
    if impulse_error > 1e-15:
        raise ValueError("actual GaussianBlur impulse does not match the declared finite kernel")
    rows = []
    for sigma, degrees in ((.8, 0.), (1.3, 0.), (1.3, 37.)):
        angle = math.radians(degrees)
        normal = np.array([math.cos(angle), math.sin(angle)])
        for alias in (True, False):
            bottom = np.array([60.67, 24.3])
            edge = .11743 if alias else 2.61371
            seed, band = bottom - edge * normal, band_true + rate * edge
            levels = np.array([90., 90. if alias else 150., 170.])
            effective = math.sqrt(sigma**2 + float(one @ support**2))
            last, low, high = edges._wall_grid_spec(band, effective, .125, rate)
            t = np.arange(low, high + 1) * .125
            candidates = np.arange(-30, last + 1) * .02 * effective
            yy, xx = np.mgrid[:shape[0], :shape[1]]
            d = (xx + .5 - bottom[0]) * normal[0] + (yy + .5 - bottom[1]) * normal[1]
            p1, p2 = cdf((d + band_true) / sigma), cdf(d / sigma)
            raw = levels[0] * (1 - p1) + levels[1] * (p1 - p2) + levels[2] * p2
            rectified = sheet.rectify_gray(raw, np.eye(3), 0., (shape[1], shape[0]), 1.)
            if not np.array_equal(rectified, raw.astype(np.float32)):
                raise ValueError("identity rectification differs from the declared float32 cast")
            x, y = seed[:, None] + t * normal[:, None] - .5
            direct = profile_observations.keys_profile(shape, x, y)
            composed = direct.after_filter(kernel, border="reflect101")
            for dtype, source in (("float64", raw), ("float32", rectified)):
                observed_image = cv2.GaussianBlur(source, (0, 0), smoothing)
                profile = sheet.sample_keys(observed_image, x, y)
                row = {"optical_sigma_px": sigma, "angle_degrees": degrees,
                       "one_step_alias": alias, "dtype": dtype, "true_edge_px": edge,
                       "band_seed_px": band, "band_rate": rate, "levels_CBA": levels.tolist(),
                       "profile_samples": len(t), "source_pixels": len(composed.pixels_xy),
                       "matrix_cells": composed.matrix.size, "models": {}}
                for name, op, model_sigma in (("final_only_moment_sigma", direct, effective),
                                              ("composed_gaussian_keys", composed, sigma)):
                    forward = Forward(op, seed, normal, t)
                    predicted = (levels[0] * (forward.apply(np.ones(len(forward.distance))) -
                                 forward.probability(edge - band_true, model_sigma, "keys_point")) +
                                 levels[1] * (forward.probability(edge - band_true, model_sigma, "keys_point") -
                                 forward.probability(edge, model_sigma, "keys_point")) +
                                 levels[2] * forward.probability(edge, model_sigma, "keys_point"))
                    row["models"][name] = {
                        "truth_prediction_maximum": float(np.max(np.abs(profile - predicted))),
                        "finite_search": search.search(forward, profile, band, rate, model_sigma, candidates, "keys_point")}
                rows.append(row)
    return {"cases": rows, "kernel": {"sigma": smoothing, "one_dimensional_weights": one.tolist(),
            "support": support.tolist(), "actual_impulse_maximum_error": impulse_error,
            "border": "reflect101", "scope": "Seven-tap support verified for the recorded runtime; not an API guarantee"}}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new JSON result; existing paths are refused")
    args = parser.parse_args(arguments)
    if args.output.exists():
        parser.error("output exists; choose a fresh JSON result path")
    files = ["backend/profile_observations.py", "backend/edges.py", "backend/sheet.py", PROTOTYPE,
             "scripts/postblur_operator_study.py"]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    started = time.perf_counter()
    result = run()
    if hashes != {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}:
        raise ValueError("source changed during execution")
    result.update({"format": "picad-postblur-operator-results", "version": 1, "source_sha256": hashes,
                   "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "runtime": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__,
                               "seconds": time.perf_counter() - started},
                   "population": "Six development fields crossed with two dtypes; reused from the failure-directed probe, not held out",
                   "limits": ["Known straight Gaussian source and supplied optical sigma; final-only comparator receives oracle moment sigma.",
                              "Identity rectification only. No nonlinear tone/channel response, unknown detector, nonidentity warp or physical test.",
                              "Composed linear float64 prediction does not model float32 rounding; retain that discrepancy.",
                              "Finite numerical search and arithmetic alias heuristic, not a continuous global optimization certificate.",
                              "Search is ordinary residual fitting; correlated-noise accounting is evaluated in the separate noise study.",
                              "No production correction or physical accuracy claim."]})
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(text)
    print(f"Recorded {len(result['cases'])} postblur controls to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
