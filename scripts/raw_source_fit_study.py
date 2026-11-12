"""Reproduce conditional raw-source offset fits and retained mismatch controls.

Requires --output NEW_JSON. No CAD server, physical photo or AI model is used.
The independent renderer crosses two forward-projected points; the developer
model transforms a line by inverse transpose. All predefined cases are kept.
Finite scans, known geometry/PSF/noise, point sensing and synthetic linear fields
remain experimental assumptions. No production correction or confidence label.
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
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import profile_observations as observations
from backend import raw_source_fit, sheet, tone

PLAN = ROOT / "studies/raw-source-fit-v1.json"
ERFC = np.frompyfunc(math.erfc, 1, 1)


def cdf(z):
    return 0.5 * np.asarray(ERFC(-np.asarray(z) / math.sqrt(2)), dtype=float)


def project(h, p):
    v = np.column_stack((np.asarray(p).reshape(-1, 2), np.ones(np.asarray(p).size // 2))) @ h.T
    return v[:, :2] / v[:, 2, None]


def mapping(spec, p0, q0):
    if spec["jacobian"] is None:
        a = math.radians(25)
        j = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]) @ np.diag(
            [2.4, 1.2]
        )
    else:
        j = np.array(spec["jacobian"])
    v = np.array(spec["projective_vector"])
    h = np.empty((3, 3))
    h[:2, :2] = j + np.outer(q0, v)
    h[:2, 2] = q0 * (1 - v @ p0) - j @ p0
    h[2, :2] = v
    h[2, 2] = 1 - v @ p0
    return h, j


def render_line(h, p0, n, e):
    """Independent oracle: cross two forward-projected boundary points, not H^-T ell."""
    tangent = np.array([-n[1], n[0]])
    p = p0 + e * n
    ends = project(h, np.array([p - 8 * tangent, p + 8 * tangent]))
    line = np.cross(np.r_[ends[0], 1.0], np.r_[ends[1], 1.0])
    positive = project(h, [p + 0.1 * n])[0]
    if line @ np.r_[positive, 1.0] < 0:
        line = -line
    return line / np.linalg.norm(line[:2])


def levels_fit(design, y):
    """Global small box-LS by active faces; no clipping of a free optimum."""
    number = design.shape[1]
    coeff, _, rank, _ = np.linalg.lstsq(design, y, rcond=None)
    if np.all((coeff >= 0) & (coeff <= 255)):
        error = y - design @ coeff
        return coeff, float(error @ error), int(rank), float(np.max(np.abs(error)))
    best = None
    for face in itertools.product((-1, 0, 1), repeat=number):
        free = np.array([f == -1 for f in face])
        x = np.array([255.0 if f == 1 else 0.0 for f in face])
        if free.any():
            x[free] = np.linalg.lstsq(design[:, free], y - design[:, ~free] @ x[~free], rcond=None)[
                0
            ]
        if np.any((x < 0) | (x > 255)):
            continue
        err = y - design @ x
        cost = float(err @ err)
        if best is None or cost < best[1]:
            best = (x, cost, int(np.linalg.matrix_rank(design)), float(np.max(np.abs(err))))
    return best


def golden(cost, low, high, iterations):
    phi = (math.sqrt(5) - 1) / 2
    c = high - phi * (high - low)
    d = low + phi * (high - low)
    fc, fd = cost(c), cost(d)
    for _ in range(iterations):
        if fc["rss"] <= fd["rss"]:
            high, d, fd = d, c, fc
            c = high - phi * (high - low)
            fc = cost(c)
        else:
            low, c, fc = c, d, fd
            d = low + phi * (high - low)
            fd = cost(d)
    return min([fc, fd, cost(low), cost(high)], key=lambda r: r["rss"])


def search(cost, bounds, count, iterations):
    grid = np.linspace(*bounds, count)
    rows = [cost(float(e)) for e in grid]
    minima = [rows[0], rows[-1]]
    for i in range(1, len(grid) - 1):
        if rows[i]["rss"] <= rows[i - 1]["rss"] and rows[i]["rss"] <= rows[i + 1]["rss"]:
            minima.append(golden(cost, float(grid[i - 1]), float(grid[i + 1]), iterations))
    minima.sort(key=lambda r: r["rss"])
    winner = dict(minima[0])
    winner["represented_local_basins"] = len(minima) - 2
    winner["at_search_endpoint"] = winner["edge"] in bounds
    winner["sampled_and_refined_minima"] = minima
    return winner


class Field:
    def __init__(self, plan, spec, scene):
        self.plan = plan
        self.scene = scene
        self.p0 = np.array(plan["plane_seed"])
        self.q0 = np.array(plan["raw_mapped_seed"])
        self.h, self.j = mapping(spec, self.p0, self.q0)
        self.inverse = np.linalg.inv(self.h)
        a = math.radians(scene["normal_degrees"])
        self.normal = np.array([math.cos(a), math.sin(a)])
        shape = tuple(round(p * plan["ppm"]) for p in plan["plane_size"][::-1])
        self.raw_shape = tuple(plan["raw_shape"])
        self.t = (
            np.arange(
                -round(plan["profile_half_width_rectified_px"] / plan["profile_step_rectified_px"]),
                round(plan["profile_half_width_rectified_px"] / plan["profile_step_rectified_px"])
                + 1,
            )
            * plan["profile_step_rectified_px"]
        )
        self.coords = self.p0[:, None] * plan["ppm"] + self.normal[:, None] * self.t - 0.5
        self.final = observations.keys_profile(shape, *self.coords)
        support = np.arange(-3, 4)
        one = np.exp(-0.5 * (support / 0.7) ** 2)
        one /= one.sum()
        self.smooth = self.final.after_filter(np.outer(one, one), border="reflect101")
        self.full = self.smooth.after_rectification(
            self.raw_shape, self.h, 0.0, plan["plane_size"], plan["ppm"]
        )
        self.raw_q = self.full.pixels_xy + 0.5
        self.back = (project(self.inverse, self.raw_q) - self.p0) @ self.normal
        self.rect_distance = ((self.smooth.pixels_xy + 0.5) / plan["ppm"] - self.p0) @ self.normal
        self.constant = self.full.matrix @ np.ones(len(self.raw_q))
        self.rect_constant = self.smooth.matrix @ np.ones(len(self.rect_distance))
        self.line0 = np.linalg.solve(self.h.T, np.r_[self.normal, -self.normal @ self.p0])
        self.line_rate = np.linalg.solve(self.h.T, [0.0, 0.0, -1.0])
        self.plane_sigma_ratio = np.linalg.norm(np.linalg.solve(self.j.T, self.normal))
        yy, xx = np.mgrid[: self.raw_shape[0], : self.raw_shape[1]]
        self.render_q = np.column_stack((xx.ravel() + 0.5, yy.ravel() + 0.5))
        self.oracle_difference = 0.0

    def raw_probability(self, e, sigma, q=None):
        q = self.raw_q if q is None else q
        line = self.line0 + e * self.line_rate
        return cdf((q @ line[:2] + line[2]) / (sigma * np.linalg.norm(line[:2])))

    def raw_oracle(self, e, sigma):
        line = render_line(self.h, self.p0, self.normal, e)
        probability = cdf((self.render_q @ line[:2] + line[2]) / sigma)
        internal = self.raw_probability(e, sigma, self.render_q)
        self.oracle_difference = max(
            self.oracle_difference, float(np.max(np.abs(probability - internal)))
        )
        return probability.reshape(self.raw_shape)

    def actual(self, raw):
        image = sheet.rectify_gray(raw, self.h, 0.0, self.plan["plane_size"], self.plan["ppm"])
        return sheet.sample_keys(cv2.GaussianBlur(image, (0, 0), 0.7), *self.coords)

    def source_design(self, e, sigma):
        probability = self.raw_probability(e, sigma)
        return np.column_stack((1 - probability, probability))

    def fit(self, y, model, sigma, *, gls=None, bounds=None, count=None):
        if gls is not None:
            target = gls.whiten(y)
        else:
            target = y

        def cost(e):
            if model == "exact_raw":
                raw_design = self.source_design(e, sigma)
                design = (
                    self.full.matrix @ raw_design if gls is None else gls.whiten_source(raw_design)
                )
            elif model == "frozen_jacobian_raw":
                p = cdf((self.back - e) / (sigma * self.plane_sigma_ratio))
                v = self.full.matrix @ p
                design = np.column_stack((self.constant - v, v))
            elif model == "rectified_scalar":
                p = cdf((self.rect_distance - e) / (sigma * self.plane_sigma_ratio))
                v = self.smooth.matrix @ p
                design = np.column_stack((self.rect_constant - v, v))
            else:
                raise ValueError(model)
            levels, rss, rank, maximum = levels_fit(design, target)
            return {
                "edge": float(e),
                "sigma": float(sigma),
                "levels": levels.tolist(),
                "rss": rss,
                "rank": rank,
                "maximum_fit_space_residual": maximum,
            }

        return search(
            cost,
            bounds or self.plan["edge_search_plane"],
            count or self.plan["edge_grid_points"],
            self.plan["golden_iterations"],
        )


def compact(row, truth, ppm):
    out = {k: v for k, v in row.items() if k != "sampled_and_refined_minima"}
    out["edge_error_plane"] = row["edge"] - truth
    out["edge_error_rectified_px"] = ppm * (row["edge"] - truth)
    return out


def selected(f, raw):
    xy = f.full.pixels_xy
    return raw[xy[:, 1], xy[:, 0]].astype(float)


def source_fit(f, raw, sigma, noise, **overrides):
    options = {
        "sensor_shape": f.raw_shape,
        "homography": f.h,
        "anchor": f.p0,
        "normal": f.normal,
        "psf_covariance": np.eye(2) * sigma**2,
        "offset_bounds": tuple(f.plan["edge_search_plane"]),
        "level_bounds": tuple(f.plan["level_bounds"]),
        "grid_points": f.plan["edge_grid_points"],
        "refinement_iterations": f.plan["golden_iterations"],
        "max_evaluations": f.plan["max_evaluations_per_fit"],
        "work_limit": f.plan["source_fit_work_limit"],
    }
    options.update(overrides)
    fit = raw_source_fit.fit_plane_edge_offset(f.full.pixels_xy, selected(f, raw), noise, **options)
    result = asdict(fit)
    if fit.best is not None:
        result["edge_error_plane"] = fit.best.offset - f.scene["true_edge_plane"]
        result["edge_error_rectified_px"] = f.plan["ppm"] * result["edge_error_plane"]
    return result


def array_hash(a):
    a = np.ascontiguousarray(a)
    return {
        "shape": list(a.shape),
        "dtype": str(a.dtype),
        "sha256": hashlib.sha256(a.tobytes()).hexdigest(),
    }


def conditioned_controls(f, raw, sigma, noise):
    values = selected(f, raw)
    product = f.full.matrix @ values
    shape = tuple(round(v * f.plan["ppm"]) for v in f.plan["plane_size"][::-1])
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    sx, sy = sheet.plane_to_photo(
        f.h, 0.0, f.raw_shape[::-1], (xx + 0.5) / f.plan["ppm"], (yy + 0.5) / f.plan["ppm"]
    )
    rect64 = sheet.sample_keys(raw, sx - 0.5, sy - 0.5)
    staged64 = sheet.sample_keys(cv2.GaussianBlur(rect64, (0, 0), 0.7), *f.coords)
    rows = []
    for name, y in [
        ("stored_matrix_product", product),
        ("float64_staged", staged64),
        ("float32_staged", f.actual(raw)),
    ]:
        fit = f.fit(y, "exact_raw", sigma, gls=noise)
        prediction = f.full.matrix @ (f.source_design(fit["edge"], sigma) @ np.array(fit["levels"]))
        rows.append(
            {
                "observation": name,
                "maximum_vs_stored_matrix_product": float(np.max(np.abs(y - product))),
                "whitened_delta_l2": float(np.linalg.norm(noise.whiten(y - product))),
                "profile_whitening_vs_stable_source_l2": float(
                    np.linalg.norm(noise.whiten(y) - noise.whiten_source(values))
                ),
                "processed_target_fit": compact(fit, f.scene["true_edge_plane"], f.plan["ppm"]),
                "processed_support_diagnostic": noise.residual(y, prediction),
            }
        )
    return {
        "scene": f.scene,
        "noise_rank": noise.rank,
        "smallest_retained_singular_value": float(noise.singular_values[-1]),
        "largest_inverse_gain": float(1 / noise.singular_values[-1]),
        "source_target_fit": source_fit(f, raw, sigma, noise),
        "rows": rows,
    }


def run(plan):
    specs = {m["name"]: m for m in plan["maps"]}
    sigma, ppm = plan["true_raw_optical_sigma"], plan["ppm"]
    baseline, stress, aliases, noisy = [], [], [], []
    conditional = None
    for scene in plan["baseline_fields"]:
        f = Field(plan, specs[scene["map"]], scene)
        e = scene["true_edge_plane"]
        low, high = scene["levels"]
        raw = low + (high - low) * f.raw_oracle(e, sigma)
        y = f.actual(raw)
        noise = observations.PixelNoise.factor(f.full.matrix, plan["supplied_raw_noise_std"])
        fits = {
            model: compact(f.fit(y, model, sigma), e, ppm)
            for model in ["exact_raw", "frozen_jacobian_raw", "rectified_scalar"]
        }
        baseline.append(
            {
                "scene": scene,
                "source_projection_fit": source_fit(f, raw, sigma, noise),
                "processed_OLS_comparators": fits,
                "renderer_probability_maximum_vs_inverse_transpose": f.oracle_difference,
                "raw_pixels": len(f.raw_q),
                "profile_samples": len(f.t),
                "source_array": array_hash(raw),
                "operator": array_hash(f.full.matrix),
                "retained_noise_rank": noise.rank,
            }
        )
    for scene in plan["stress_fields"]:
        f = Field(plan, specs[scene["map"]], scene)
        e = scene["true_edge_plane"]
        low, high = scene["levels"]
        p = f.raw_oracle(e, sigma)
        raw = low + (high - low) * p
        noise = observations.PixelNoise.factor(f.full.matrix, plan["supplied_raw_noise_std"])
        fixed = {
            str(factor): source_fit(f, raw, sigma * factor, noise)
            for factor in plan["sigma_factors_fixed"]
        }
        nonlinear_p = p + plan["nonlinear_response_coefficient"] * p * (1 - p)
        nonlinear = low + (high - low) * nonlinear_p
        encoded = np.clip(np.rint(tone.encoded_from_linear(raw)), 0, 255).astype(np.uint8)
        rgb = np.repeat(encoded[:, :, None], 3, axis=2)
        decoded = tone.linear_mix(rgb)
        stress.append(
            {
                "scene": scene,
                "fixed_sigma_mismatch": fixed,
                "prewarp_float32": {
                    "array": array_hash(raw.astype(np.float32)),
                    "maximum_vs_unrounded_source": float(
                        np.max(np.abs(raw.astype(np.float32) - raw))
                    ),
                    "fit": source_fit(f, raw.astype(np.float32), sigma, noise),
                },
                "nonlinear_response": {
                    "coefficient": plan["nonlinear_response_coefficient"],
                    "array": array_hash(nonlinear),
                    "fit": source_fit(f, nonlinear, sigma, noise),
                },
                "eight_bit_sRGB_roundtrip": {
                    "encoded": array_hash(encoded),
                    "decoded": array_hash(decoded),
                    "maximum_vs_unrounded_source": float(np.max(np.abs(decoded - raw))),
                    "fit": source_fit(f, decoded, sigma, noise),
                },
            }
        )
        band, rate = plan["alias_band_plane"], plan["alias_band_rate"]
        seed_band = band + rate * e
        partner = (e + seed_band) / (1 + rate)

        def wall_source(edge, levels, *, f=f, rate=rate, seed_band=seed_band):
            left = (1 + rate) * edge - seed_band
            p1, p2 = f.raw_probability(left, sigma), f.raw_probability(edge, sigma)
            return np.column_stack((1 - p1, p1 - p2, p2)) @ np.array(levels)

        first = wall_source(e, [low, low, high])
        second = wall_source(partner, [low, high, high])
        aliases.append(
            {
                "scene": scene,
                "silhouette_labels_plane": [e, partner],
                "separation_rectified_px": ppm * (partner - e),
                "raw_label_mean_maximum_difference": float(np.max(np.abs(first - second))),
                "projected_label_mean_maximum_difference": float(
                    np.max(np.abs(noise.whiten_source(first) - noise.whiten_source(second)))
                ),
                "limits": "Identical available raw fields remain compatible with both wall labels; a two-level step fit cannot identify the physical silhouette.",
            }
        )
        draws = []
        rng = np.random.default_rng(plan["noise_seed"])
        for index in range(plan["common_noise_draws"]):
            errors = rng.standard_normal(f.raw_shape) * plan["supplied_raw_noise_std"]
            observed = raw + errors
            fit = source_fit(f, observed, sigma, noise)
            draws.append({"draw": index, "noise_array": array_hash(errors), "fit": fit})
        noisy.append({"scene": scene, "draws": draws})
        if scene["map"] == "identity":
            conditional = conditioned_controls(f, raw, sigma, noise)
    scene = next(s for s in plan["stress_fields"] if s["map"] == "identity")
    f = Field(plan, specs["identity"], scene)
    noise = observations.PixelNoise.factor(f.full.matrix, plan["supplied_raw_noise_std"])
    p = f.raw_oracle(scene["true_edge_plane"], sigma)
    narrow = f.raw_oracle(scene["true_edge_plane"], 1e-4)
    unavailable = f.raw_oracle(0.9, sigma)
    cases = [
        ("constant_128", np.full(f.raw_shape, 128.0), sigma, {}),
        ("constant_zero", np.zeros(f.raw_shape), sigma, {}),
        ("saturated_narrow_source", 80 + 120 * narrow, 1e-4, {}),
        ("source_edge_outside_search", 80 + 120 * unavailable, sigma, {}),
        ("almost_no_contrast", 128 + 1e-7 * p, sigma, {}),
        (
            "no_refinement_budget",
            80 + 120 * p,
            sigma,
            {"max_evaluations": plan["edge_grid_points"]},
        ),
    ]
    identification = []
    for name, raw, supplied_sigma, overrides in cases:
        row = source_fit(f, raw, supplied_sigma, noise, **overrides)
        # These are stress definitions, not necessarily the baseline scene truth.
        row.pop("edge_error_plane", None)
        row.pop("edge_error_rectified_px", None)
        identification.append(
            {
                "case": name,
                "source_array": array_hash(raw),
                "supplied_sigma": supplied_sigma,
                "fit": row,
            }
        )
    base_raw = 80 + 120 * p
    z = np.random.default_rng(plan["noise_seed"] + 1).standard_normal(len(f.raw_q))
    texture = z - noise.right.T @ (noise.right @ z)
    texture *= 20 / np.max(np.abs(texture))
    textured = base_raw.copy()
    xy = f.full.pixels_xy
    textured[xy[:, 1], xy[:, 0]] += texture
    nullspace = {
        "scene": scene,
        "source_levels": [80.0, 200.0],
        "true_edge_plane": scene["true_edge_plane"],
        "raw_texture_maximum": float(np.max(np.abs(texture))),
        "raw_texture_l2": float(np.linalg.norm(texture)),
        "retained_texture_l2": float(np.linalg.norm(noise.whiten_source(texture))),
        "ideal_profile_texture_maximum": float(np.max(np.abs(f.full.matrix @ texture))),
        "source_array": array_hash(textured),
        "fit": source_fit(f, textured, sigma, noise),
        "limits": "A small projected residual can coexist with a large available raw-source mismatch; source-complement diagnostics do not change the selected objective or supply a physical test threshold.",
    }
    return {
        "baseline": baseline,
        "source_stress": stress,
        "global_wall_alias_controls": aliases,
        "conditional_noise_controls": noisy,
        "conditioning": conditional,
        "identification_controls": identification,
        "discarded_source_texture": nullspace,
    }


def serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"unsupported report value: {type(value).__name__}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; choose a fresh JSON path")
    if args.output.suffix.lower() != ".json":
        parser.error("output must be a JSON file")
    paths = [
        "backend/raw_source_fit.py",
        "backend/profile_observations.py",
        "backend/sheet.py",
        "backend/reference.py",
        "backend/tone.py",
        "studies/raw-source-fit-v1.json",
        "scripts/raw_source_fit_study.py",
    ]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    started = time.perf_counter()
    plan = json.loads(PLAN.read_text())
    result = run(plan)
    if hashes != {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}:
        raise ValueError("source changed during experiment")
    result.update(
        {
            "format": "raw-source-offset-study-results",
            "version": 1,
            "plan": plan,
            "source_sha256": hashes,
            "git_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "git_status_porcelain": subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).splitlines(),
            "parameter_units": {
                "offset": "plane-coordinate length (millimetres in this plan)",
                "psf_covariance": "raw pixels squared",
                "source_levels": "prewarp linear-light values on a 0..255 scale",
            },
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "opencv": cv2.__version__,
                "seconds": time.perf_counter() - started,
            },
            "limits": [
                "Fixed lens-free H, fixed unit normal, point-sensor means, known translation-invariant raw Gaussian PSF and supplied independent raw noise. No camera/PSF/noise inference.",
                "Both source target and source model use the same retained V^T D^-1 map. This is algebraically equivalent to profile GLS only for exact fixed linear processing and matching retained modes before rounding/model discrepancy.",
                "Independent raw-line renderer uses two forward-projected boundary points; fitting uses inverse transpose. Original synthetic source arrays and all matrix/rank controls remain bound by hashes.",
                "Brightness is profiled under supplied bounds. Finite grid and local refinements do not prove a global optimum, edge identity or physical uncertainty.",
                "Processed OLS comparators diagnose deterministic discrepancy, not independent observation noise. Processed GLS controls explicitly retain arithmetic/float32 failures.",
                "The 24 common full-sensor Gaussian noise arrays are reused across six source fields, giving 144 conditional fits rather than 144 independent full-scene trials. No coverage/accuracy threshold or physical covariance is inferred.",
                "Real prewarp input is already float32 and decoded from saved intensities. Separate source float32 and actual tone.linear_mix eight-bit sRGB controls retain these earlier discrepancies.",
                "Wrong PSF width, nonlinear response, quantization, low contrast, saturation, endpoints, finite work limits and globally equivalent wall labels remain explicit adverse controls.",
                "No segmentation, radial lens distortion, curved boundary, unknown aperture, wall/parallax/camera inference, production integration, browser/installed-tool acceptance or physical qualification.",
            ],
        }
    )
    content = json.dumps(result, indent=2, allow_nan=False, default=serializable) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(content)
    print(
        json.dumps(
            {
                "baseline_fields": len(result["baseline"]),
                "source_stress_fields": len(result["source_stress"]),
                "alias_controls": len(result["global_wall_alias_controls"]),
                "conditional_noise_fits": sum(
                    len(r["draws"]) for r in result["conditional_noise_controls"]
                ),
                "identification_controls": len(result["identification_controls"]),
                "seconds": result["runtime"]["seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
