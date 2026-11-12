"""Repeat fixed-sampling covariance and false-precision controls on synthetic data.

Run with --output NEW_JSON. No production tracing or physical confidence is changed.
"""

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import profile_observations as observations

PLAN = ROOT / "studies/profile-noise-v1.json"
ERFC = np.frompyfunc(math.erfc, 1, 1)


def cdf(x):
    return .5 * np.asarray(ERFC(-np.asarray(x) / math.sqrt(2)), dtype=float)


def density(x):
    return np.exp(-.5 * np.asarray(x)**2) / math.sqrt(2 * math.pi)


def make_operator(plan, step, repeats):
    count = round(plan["profile_half_width_px"] / step)
    t = np.arange(-count, count + 1) * step
    seed, normal = np.asarray(plan["seed_pixel_edge_coordinates"]), np.asarray(plan["normal"])
    x, y = seed[:, None] + normal[:, None] * np.repeat(t, repeats) - .5
    return observations.keys_profile(tuple(plan["image_shape"]), x, y)


def measure(plan, op, gaussian_draws, draw_indices, label, step, repeats):
    matrix = op.matrix
    std = plan["input_noise_std_linear_levels"]
    factor = observations.PixelNoise.factor(matrix, std)
    distance = (op.pixels_xy + .5 - plan["seed_pixel_edge_coordinates"]) @ plan["normal"]
    sigma = plan["optical_sigma_px"]
    low, high = plan["levels"]
    raw_mean = low + (high - low) * cdf(distance / sigma)
    derivative = -(high - low) * density(distance / sigma) / sigma
    alternate = low + (high - low) * cdf((distance - plan["comparison_offset_px"]) / sigma)
    h = factor.whiten_source(derivative)
    information = float(h @ h)
    noise = std * gaussian_draws[:, draw_indices]
    projected_noise = (noise / std) @ factor.right.T
    delta = projected_noise @ h / information

    sampled_derivative = matrix @ derivative
    row_variance = np.sum((matrix * std)**2, axis=1)
    diagonal_information = float(np.sum(sampled_derivative**2 / row_variance))
    diagonal_weights = sampled_derivative / row_variance / diagonal_information
    actual_diagonal_sd = float(np.linalg.norm((diagonal_weights @ matrix) * std))
    diagonal_delta = noise @ (diagonal_weights @ matrix)
    profile = matrix @ raw_mean
    check = factor.residual(profile, matrix @ alternate)
    stable = factor.whiten_source(raw_mean - alternate)
    return {
        "label": label, "step_px": step, "repeats": repeats,
        "samples": len(matrix), "source_pixels": matrix.shape[1], "retained_rank": factor.rank,
        "svd_cutoff": factor.cutoff, "discarded_largest": factor.discarded_largest,
        "smallest_retained_singular_value": float(factor.singular_values[-1]),
        "largest_inverse_noise_gain": float(1 / factor.singular_values[-1]),
        "source_pixels_sha256": hashlib.sha256(op.pixels_xy.astype("<i8").tobytes()).hexdigest(),
        "matrix_sha256": hashlib.sha256(matrix.astype("<f8").tobytes()).hexdigest(),
        "gls_local_information": information,
        "gls_predicted_local_sd_px": float(1 / math.sqrt(information)),
        "gls_gaussian_trial_sd_px": float(np.std(delta, ddof=1)),
        "diagonal_predicted_local_sd_px": float(1 / math.sqrt(diagonal_information)),
        "diagonal_actual_local_sd_px": actual_diagonal_sd,
        "diagonal_gaussian_trial_sd_px": float(np.std(diagonal_delta, ddof=1)),
        "stable_comparison_cost": float(stable @ stable),
        "profile_comparison": check,
        "row_partition_max_error": float(np.max(np.abs(matrix.sum(axis=1) - 1))),
    }


def aliases(plan, op):
    factor = observations.PixelNoise.factor(op.matrix, plan["input_noise_std_linear_levels"])
    d = (op.pixels_xy + .5 - plan["seed_pixel_edge_coordinates"]) @ plan["normal"]
    sigma, band, rate = plan["optical_sigma_px"], plan["alias_band_px"], plan["alias_band_rate"]
    low, high = plan["levels"]
    rows = []
    means = []
    for edge, levels in ((0., np.array([low, low, high])),
                         (band / (1 + rate), np.array([low, high, high]))):
        p1 = cdf((d - (1 + rate) * edge + band) / sigma)
        p2 = cdf((d - edge) / sigma)
        design = np.column_stack((1 - p1, p1 - p2, p2))
        raw = design @ levels
        derivative = (-(levels[1] - levels[0]) * (1 + rate) *
                      density((d - (1 + rate) * edge + band) / sigma) / sigma -
                      (levels[2] - levels[1]) * density((d - edge) / sigma) / sigma)
        w_design, w_derivative = factor.whiten_source(design), factor.whiten_source(derivative)
        projection = np.linalg.lstsq(w_design, w_derivative, rcond=None)[0]
        independent = w_derivative - w_design @ projection
        information = float(independent @ independent)
        rows.append({"edge_px": edge, "levels_CBA": levels.tolist(),
                     "conditional_local_information_with_free_tones": information,
                     "conditional_local_sd_px": 1 / math.sqrt(information)})
        means.append(op.matrix @ raw)
    return {"interpretations": rows, "separation_px": rows[1]["edge_px"],
            "maximum_profile_difference": float(np.max(np.abs(means[0] - means[1]))),
            "comparison": factor.residual(means[0], means[1]),
            "meaning": "Finite local information at either label does not remove identical global mean fields."}


def run(plan):
    configurations = [("density", step, 1) for step in plan["steps_px"]]
    configurations += [("duplicates", plan["steps_px"][0], r) for r in plan["duplicate_counts"]]
    operators = [make_operator(plan, step, repeats) for _, step, repeats in configurations]
    union = np.unique(np.concatenate([op.pixels_xy for op in operators]), axis=0)
    lookup = {tuple(pixel): i for i, pixel in enumerate(union)}
    gaussian = np.random.default_rng(plan["random_seed"]).normal(size=(plan["gaussian_trials"], len(union)))
    rows = [measure(plan, op, gaussian, [lookup[tuple(p)] for p in op.pixels_xy], *config)
            for op, config in zip(operators, configurations)]
    # A covariance pseudoinverse alone gives zero cost for this impossible residual.
    factor = observations.PixelNoise.factor([[1.], [1.]], 1.)
    support = factor.residual(np.array([1., -1.]), np.zeros(2))
    # More sample points need not have the same raw row space: a new pixel can help.
    rowspaces = []
    for matrix in (np.array([[1., 0.]]), np.eye(2)):
        f = observations.PixelNoise.factor(matrix, 1.)
        h = f.whiten_source(np.array([0., 1.]))
        rowspaces.append({"rows": len(matrix), "rank": f.rank, "information": float(h @ h)})
    # Numerical rank truncation can also break the otherwise exact repeat identity.
    truncation = []
    for repeats in (1, 128):
        f = observations.PixelNoise.factor(np.repeat(np.diag([1., 1e-14]), repeats, axis=0), 1.)
        truncation.append({"repeats": repeats, "rank": f.rank, "cutoff": f.cutoff,
                           "discarded_largest": f.discarded_largest})
    return {"cases": rows, "global_alias": aliases(plan, operators[2]),
            "outside_support_counterexample": support, "changed_rowspace_control": rowspaces,
            "numerical_truncation_control": truncation,
            "draw_union_pixels_sha256": hashlib.sha256(union.astype("<i8").tobytes()).hexdigest()}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="new JSON result; existing paths are refused")
    args = parser.parse_args(arguments)
    if args.output.exists():
        parser.error("output exists; choose a fresh JSON result path")
    paths = ["backend/profile_observations.py", "backend/sheet.py", "scripts/profile_noise_study.py",
             "studies/profile-noise-v1.json"]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    started = time.perf_counter()
    plan = json.loads(PLAN.read_text())
    result = run(plan)
    assert hashes == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    result.update({"format": "picad-profile-noise-results", "version": 1, "plan": plan,
                   "source_sha256": hashes,
                   "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                               "seconds": time.perf_counter() - started},
                   "limits": ["Noise variances and Gaussian independent raw pixels are supplied, not calibrated.",
                              "Trials evaluate linearized known-tone offset estimators, not nonlinear fit coverage.",
                              "Whitening alone does not identify aliases or repair optics, source or warp mismatch.",
                              "Invariance requires the same retained raw row space and covariance; rank truncation can change it.",
                              "No production trace, UI confidence label, physical accuracy or installed state changes."]})
    content = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(content)
    print(f"Recorded {len(result['cases'])} complete density/repeat controls to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
