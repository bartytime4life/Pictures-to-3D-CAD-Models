"""Developer study of optical-source assumptions and fixed digital warp composition.

Run with --output NEW_JSON; no arguments or --help do not execute the study.
All 18 synthetic fields and both radial quadratures are retained. The exact raw
half-plane renderer uses raw line geometry and stdlib erfc, independently checked
by Gaussian integration. A separate S G R comparison checks the known digital
operator against an independent float64 Keys rectification implementation.
Matching digital weights does not qualify the supplied optical PSF, point-sensor
radiance model, camera geometry or real-image source. No production change.
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

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import profile_observations, sheet

EXPECTED_SOURCE_SHA256 = {
    "backend/sheet.py": "a086d7216256726a0e392bd98cbdb1274f5cb5eb096802c17c805349a7747e31",
    "backend/reference.py": "60a8681a3e0154c935cc3256b0aff7f93d19874e9a367d0d6619a5acee0846d0",
    "backend/profile_observations.py": "7eee8b71fc9024cb5c8453ec67aab75f2c21c8c77e975c1fba41b1e3be9f873b",
}

ERFC = np.frompyfunc(math.erfc, 1, 1)
RAW_SHAPE = (192, 256)
PLANE_SIZE = (64.0, 48.0)
PPM = 2.0
P0 = np.array([32.137, 24.219])
Q0 = np.array([128.3, 96.7])
SIGMA = 1.3
LOW, HIGH = 80.0, 200.0
T = np.arange(-64, 65) * 0.125


def cdf(z):
    return 0.5 * np.asarray(ERFC(-np.asarray(z) / math.sqrt(2)), dtype=float)


def project(h, points):
    hp = (
        np.column_stack((np.asarray(points).reshape(-1, 2), np.ones(np.asarray(points).size // 2)))
        @ h.T
    )
    return hp[:, :2] / hp[:, 2, None]


def homography(a, v):
    # q = Q0 + A(p-P0)/(1 + v dot (p-P0)); J(P0)=A.
    h = np.empty((3, 3))
    h[:2, :2] = a + np.outer(Q0, v)
    h[:2, 2] = Q0 * (1 - v @ P0) - a @ P0
    h[2, :2], h[2, 2] = v, 1 - v @ P0
    return h


def cubic(t):
    # Independent piecewise Keys(a=-1/2) polynomial.
    r = np.abs(t)
    return np.where(
        r <= 1,
        1.5 * r**3 - 2.5 * r**2 + 1,
        np.where(r < 2, -0.5 * r**3 + 2.5 * r**2 - 4 * r + 2, 0.0),
    )


def independent_rectification(raw, h):
    xx, yy = np.meshgrid(
        (np.arange(round(PLANE_SIZE[0] * PPM)) + 0.5) / PPM,
        (np.arange(round(PLANE_SIZE[1] * PPM)) + 0.5) / PPM,
    )
    q = project(h, np.column_stack((xx.ravel(), yy.ravel()))) - 0.5
    ix, iy = np.floor(q[:, 0]).astype(int), np.floor(q[:, 1]).astype(int)
    value = np.zeros(len(q))
    for j in range(-1, 3):
        for i in range(-1, 3):
            value += (
                cubic(q[:, 0] - ix - i)
                * cubic(q[:, 1] - iy - j)
                * raw[np.clip(iy + j, 0, RAW_SHAPE[0] - 1), np.clip(ix + i, 0, RAW_SHAPE[1] - 1)]
            )
    return value.reshape(xx.shape)


def production_profile(raw, h, normal):
    rectified = sheet.rectify_gray(raw, h, 0.0, PLANE_SIZE, PPM)
    smoothed = cv2.GaussianBlur(rectified, (0, 0), 0.7)
    coords = P0[:, None] * PPM + normal[:, None] * T - 0.5
    return sheet.sample_keys(smoothed, *coords)


def direct_profile(rectified, normal):
    coords = P0[:, None] * PPM + normal[:, None] * T - 0.5
    return sheet.sample_keys(cv2.GaussianBlur(rectified, (0, 0), 0.7), *coords)


def crossing(values):
    residual = values - (LOW + HIGH) / 2
    ids = np.flatnonzero(residual[:-1] * residual[1:] < 0)
    roots = [
        float((T[i] * residual[i + 1] - T[i + 1] * residual[i]) / (residual[i + 1] - residual[i]))
        for i in ids
    ]
    return min(roots, key=abs) if roots else None


def half_plane_quadrature(z, m, nodes):
    # Condition on the raw Gaussian component with the smaller coefficient.
    x, w = np.polynomial.legendre.leggauss(nodes)
    components = np.sort(np.abs(m))
    s, b = components[0], components[1]
    x, w = x * 10, w * 10
    return np.sum(w * np.exp(-x * x / 2) / math.sqrt(2 * math.pi) * cdf((z - s * x) / b))


def lens_control(nodes):
    # Positive radial coefficient gives a globally monotone central inverse.
    # An undistorted vertical line u=a maps to x=g(y); condition on Gaussian Y.
    s, a, k, sigma = 80.0, 35.0, 0.25, 3.0
    boundary_x = a * (1 + k * a * a / (s * s))

    def graph(y):
        lo = np.full_like(y, -1000.0)
        hi = np.full_like(y, 1000.0)
        for _ in range(70):
            v = (lo + hi) / 2
            mapped = v * (1 + k * (a * a + v * v) / (s * s))
            lo, hi = np.where(mapped < y, v, lo), np.where(mapped >= y, v, hi)
        v = (lo + hi) / 2
        return a * (1 + k * (a * a + v * v) / (s * s))

    z, w = np.polynomial.legendre.leggauss(nodes)
    z, w = z * 10, w * 10
    gaussian_weights = w * np.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    def probability(x):
        return float(gaussian_weights @ cdf((x - graph(sigma * z)) / sigma))

    lo, hi = boundary_x - 0.2, boundary_x + 0.2
    for _ in range(50):
        mid = (lo + hi) / 2
        if probability(mid) < 0.5:
            lo = mid
        else:
            hi = mid
    curvature = (2 * a * k / (s * s)) / (1 + k * a * a / (s * s)) ** 2
    return {
        "quadrature_nodes": nodes,
        "half_tail_extent_sigma": 10,
        "k1": k,
        "normalization_radius_px": s,
        "undistorted_line_offset_px": a,
        "optical_sigma_px": sigma,
        "true_boundary_response": probability(boundary_x),
        "half_level_shift_raw_px": (lo + hi) / 2 - boundary_x,
        "leading_curvature_shift_px": curvature * sigma * sigma / 2,
        "omitted_probability_tail_upper_bound": math.erfc(10 / math.sqrt(2)),
    }


def run():
    yy, xx = np.mgrid[: RAW_SHAPE[0], : RAW_SHAPE[1]]
    raw_q = np.column_stack((xx.ravel() + 0.5, yy.ravel() + 0.5))
    angle = math.radians(25)
    rot = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    maps = [
        ("identity", np.eye(2), [0.0, 0.0]),
        ("affine_anisotropic", np.diag([2.2, 1.4]), [0.0, 0.0]),
        ("affine_shear", np.array([[2.0, 0.7], [0.2, 1.5]]), [0.0, 0.0]),
        ("affine_rotated", rot @ np.diag([2.4, 1.2]), [0.0, 0.0]),
        ("projective_mild", np.array([[2.0, 0.3], [0.1, 1.6]]), [0.006, -0.004]),
        ("projective_strong", np.array([[2.0, 0.3], [0.1, 1.6]]), [0.008, -0.005]),
    ]
    support = np.arange(-3, 4)
    weights = np.exp(-0.5 * (support / 0.7) ** 2)
    weights /= weights.sum()
    smoothing_kernel = np.outer(weights, weights)
    impulse = np.zeros((17, 17))
    impulse[8, 8] = 1
    expected_impulse = np.zeros_like(impulse)
    expected_impulse[5:12, 5:12] = smoothing_kernel
    impulse_error = float(np.max(np.abs(cv2.GaussianBlur(impulse, (0, 0), 0.7) - expected_impulse)))
    if impulse_error > 1e-15:
        raise ValueError("actual GaussianBlur impulse differs from declared seven-tap kernel")
    rows = []
    for name, a, v in maps:
        h = homography(a, np.array(v))
        inverse_h = np.linalg.inv(h)
        chart_denominator = np.column_stack((raw_q, np.ones(len(raw_q)))) @ inverse_h[2]
        if np.min(chart_denominator) <= 0:
            raise ValueError("a raw sensor point leaves the positive inverse projective chart")
        back = project(inverse_h, raw_q)
        for degrees in (0.0, 37.0, 90.0):
            normal = np.array([math.cos(math.radians(degrees)), math.sin(math.radians(degrees))])
            line = np.linalg.solve(h.T, np.r_[normal, -normal @ P0])
            raw_distance = (raw_q @ line[:2] + line[2]) / np.linalg.norm(line[:2])
            raw_exact = (LOW + (HIGH - LOW) * cdf(raw_distance / SIGMA)).reshape(RAW_SHAPE)
            plane_distance = (back - P0) @ normal
            plane_sigma = SIGMA * np.linalg.norm(np.linalg.solve(a.T, normal))
            raw_jacobian = (LOW + (HIGH - LOW) * cdf(plane_distance / plane_sigma)).reshape(
                RAW_SHAPE
            )
            geometric_mean_sigma = SIGMA / math.sqrt(abs(np.linalg.det(a)))
            raw_isotropic = (
                LOW + (HIGH - LOW) * cdf(plane_distance / geometric_mean_sigma)
            ).reshape(RAW_SHAPE)
            truth = production_profile(raw_exact, h, normal)
            jacobian = production_profile(raw_jacobian, h, normal)
            isotropic = production_profile(raw_isotropic, h, normal)
            independent = independent_rectification(raw_exact, h)
            independent_profile = direct_profile(independent, normal)
            final_coordinates = P0[:, None] * PPM + normal[:, None] * T - 0.5
            final = profile_observations.keys_profile(independent.shape, *final_coordinates)
            composed = final.after_filter(
                smoothing_kernel, border="reflect101"
            ).after_rectification(RAW_SHAPE, h, 0.0, PLANE_SIZE, PPM)
            composed_profile = composed.sample(raw_exact)
            actual_rectified = sheet.rectify_gray(raw_exact, h, 0.0, PLANE_SIZE, PPM)
            px, py = np.meshgrid(
                (np.arange(actual_rectified.shape[1]) + 0.5) / PPM,
                (np.arange(actual_rectified.shape[0]) + 0.5) / PPM,
            )
            ideal_plane = LOW + (HIGH - LOW) * cdf(
                ((px - P0[0]) * normal[0] + (py - P0[1]) * normal[1]) / plane_sigma
            )
            skip_raw = direct_profile(ideal_plane, normal)
            row = {
                "mapping": name,
                "minimum_raw_inverse_chart_denominator": float(np.min(chart_denominator)),
                "plane_normal_degrees": degrees,
                "H": h.tolist(),
                "jacobian_at_edge": a.tolist(),
                "sigma_raw_px": SIGMA,
                "sigma_plane_normal": plane_sigma,
                "raw_frozen_jacobian_maximum_error_levels": float(
                    np.max(np.abs(raw_exact - raw_jacobian))
                ),
                "after_actual_pipeline_frozen_jacobian_maximum_error_levels": float(
                    np.max(np.abs(truth - jacobian))
                ),
                "after_actual_pipeline_isotropic_scale_maximum_error_levels": float(
                    np.max(np.abs(truth - isotropic))
                ),
                "skipped_raw_rectification_maximum_error_levels": float(
                    np.max(np.abs(truth - skip_raw))
                ),
                "independent_float64_rectification_maximum_vs_actual_float32_levels": float(
                    np.max(np.abs(independent - actual_rectified))
                ),
                "independent_float64_pipeline_maximum_vs_actual_levels": float(
                    np.max(np.abs(independent_profile - truth))
                ),
                "known_half_level_crossing_rectified_pixels": {
                    "truth": crossing(truth),
                    "frozen_jacobian": crossing(jacobian),
                    "isotropic": crossing(isotropic),
                    "skip_raw": crossing(skip_raw),
                },
            }
            row.update(
                {
                    "known_S_G_R_operator": {
                        "source_pixels": len(composed.pixels_xy),
                        "matrix_cells": composed.matrix.size,
                        "source_pixels_sha256": hashlib.sha256(
                            composed.pixels_xy.astype("<i8").tobytes()
                        ).hexdigest(),
                        "matrix_sha256": hashlib.sha256(
                            composed.matrix.astype("<f8").tobytes()
                        ).hexdigest(),
                        "maximum_vs_independent_float64_pipeline_levels": float(
                            np.max(np.abs(composed_profile - independent_profile))
                        ),
                        "maximum_vs_actual_float32_pipeline_levels": float(
                            np.max(np.abs(composed_profile - truth))
                        ),
                    },
                }
            )
            # Independent Gaussian integration of the raw half-plane response.
            m = line[:2] / np.linalg.norm(line[:2])
            errors = []
            for z in (-2.0, -0.3, 0.0, 0.7, 2.0):
                errors.append(abs(half_plane_quadrature(z, m, 128) - float(cdf(z))))
            row["independent_128_node_gaussian_halfplane_cdf_maximum_error"] = max(errors)
            rows.append(row)
    lens128, lens256 = lens_control(128), lens_control(256)
    return {
        "cases": rows,
        "digital_smoothing_kernel": {
            "support": support.tolist(),
            "one_dimensional_weights": weights.tolist(),
            "border": "reflect101",
            "actual_runtime_impulse_maximum_error": impulse_error,
        },
        "radial_curve_controls": [lens128, lens256],
        "radial_N_2N_half_level_shift_difference_px": abs(
            lens128["half_level_shift_raw_px"] - lens256["half_level_shift_raw_px"]
        ),
        "radial_N_2N_boundary_probability_difference": abs(
            lens128["true_boundary_response"] - lens256["true_boundary_response"]
        ),
    }


def revision_context():
    """Optional metadata; exact file pins also permit a source archive without Git."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new JSON result; existing output paths are refused",
    )
    args = parser.parse_args(arguments)
    if args.output.exists():
        parser.error("output exists; choose a fresh JSON result path")
    script = str(Path(__file__).resolve().relative_to(ROOT))
    paths = [*EXPECTED_SOURCE_SHA256, script]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    if any(hashes[p] != expected for p, expected in EXPECTED_SOURCE_SHA256.items()):
        raise ValueError("pinned production source changed; review before updating the study pins")
    started = time.perf_counter()
    result = run()
    if hashes != {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}:
        raise ValueError("source changed during execution")
    affine = [r for r in result["cases"] if not r["mapping"].startswith("projective")]
    if (
        max(r["after_actual_pipeline_frozen_jacobian_maximum_error_levels"] for r in affine)
        >= 1e-10
    ):
        raise ValueError("affine source-model identity check failed")
    if (
        max(r["independent_128_node_gaussian_halfplane_cdf_maximum_error"] for r in result["cases"])
        >= 1e-12
    ):
        raise ValueError("independent half-plane quadrature check failed")
    if (
        max(
            r["known_S_G_R_operator"]["maximum_vs_independent_float64_pipeline_levels"]
            for r in result["cases"]
        )
        >= 1e-10
    ):
        raise ValueError("known digital-operator agreement check failed")
    result.update(
        {
            "format": "picad-raw-gaussian-warp-edge-results",
            "version": 1,
            "git_revision_context": revision_context(),
            "source_sha256": hashes,
            "source_pin_policy": "Exact production file hashes, independent of commit metadata; this script hash is recorded and checked for changes during execution.",
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "opencv": cv2.__version__,
                "seconds": time.perf_counter() - started,
            },
            "population": "18 declared synthetic fields: identity, three nonidentity affine maps, two nonidentity homographies, each with three plane edge orientations. Two additional radial quadrature orders.",
            "fixed_inputs": {
                "raw_shape": RAW_SHAPE,
                "plane_size": PLANE_SIZE,
                "ppm": PPM,
                "edge_point_plane": P0.tolist(),
                "mapped_edge_point_raw": Q0.tolist(),
                "levels": [LOW, HIGH],
                "optical_sigma_raw_px": SIGMA,
                "postwarp_gaussian_sigma_rectified_px": 0.7,
                "profile_step_rectified_px": 0.125,
            },
            "limits": [
                "Known digital S G R composition and optical source-model adequacy are separate checks. Operator agreement does not validate a PSF.",
                "Synthetic point-sensor radiance means; no detector aperture, finite object, gradients, tone response or real-camera calibration.",
                "Optical Gaussian is supplied, translation invariant, isotropic and defined in raw sensor coordinates before sampling.",
                "Lens-free homographies use a positive inverse projective chart over the complete raw sensor grid. Ideal half-planes extend beyond the finite image.",
                "Radial control is separate conditional quadrature of a known distorted vertical half-plane, not a complete radial pipeline or certified interval proof.",
                "Radial omitted-tail bound is analytic Gaussian probability evaluated in ordinary floating arithmetic; N/2N agreement does not certify quadrature error.",
                "Actual rectify_gray output is float32, followed by actual GaussianBlur and sample_keys; independent float64 composition retains rounding discrepancy.",
                "Half-level roots linearly interpolate the fixed sampled profile; they are not position estimates with calibrated uncertainty.",
                "The seven-tap digital Gaussian is checked against the recorded runtime impulse response, not assumed as an API guarantee.",
                "No segmentation, fitted rings, CAD, production change, full-suite result or physical acceptance.",
            ],
        }
    )
    content = json.dumps(result, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(content)
    print(
        f"Recorded {len(result['cases'])} complete optical-source/digital-operator fields to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
