"""Repeatable local-profile development census; execution is not qualification.

Uses an independent erfc Gaussian-convolution oracle, then actual tone decoding,
Keys rectification, blur measurement and half-level searches. Every measurement
rejection, measurement failure and ablation result is retained.
No production decisions are changed.

    .venv/bin/python scripts/material_gradient_study.py --output NEW_DIRECTORY
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import platform
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import edges, sheet, tone

PLAN = ROOT / "studies/material-gradients-v1.json"
SOURCES = ("scripts/material_gradient_study.py", "studies/material-gradients-v1.json",
           "backend/sheet.py", "backend/edges.py", "backend/tone.py")
_ERFC = np.frompyfunc(math.erfc, 1, 1)


def blurred_profile(t, sigma, condition, *, tail_sigmas=12):
    """Gaussian convolution of two affine half-lines and an optional flat wall.

    Material occupies t<0; paper t>=0. The optional wall replaces a flat
    material band [-width,0]. No production CDF or rendering helper is used.
    """
    t = np.asarray(t, dtype=np.float64)
    z = t / sigma
    cdf = 0.5 * np.asarray(_ERFC(-z / math.sqrt(2)), dtype=np.float64)
    density = np.exp(-z * z / 2) / math.sqrt(2 * math.pi)
    a, b = condition["material"], condition["paper"]
    m, p = condition["material_slope"], condition["paper_slope"]
    value = a + (b - a) * cdf + m * t + (p - m) * (t * cdf + sigma * density)
    limit = tail_sigmas * sigma
    if any(not 0 <= v <= 255 for v in (a, b, a - m * limit, b + p * limit)):
        raise ValueError("source plateau endpoints must lie in 0..255")
    # Replace each infinite affine tail by its endpoint constant. These exact
    # truncated-normal first moments keep the source globally bounded.
    left = (t + limit) / sigma
    right = (t - limit) / sigma
    value -= m * ((t + limit) * 0.5 * np.asarray(_ERFC(left / math.sqrt(2)), dtype=np.float64)
                  - sigma * np.exp(-left * left / 2) / math.sqrt(2 * math.pi))
    value -= p * ((t - limit) * 0.5 * np.asarray(_ERFC(-right / math.sqrt(2)), dtype=np.float64)
                  + sigma * np.exp(-right * right / 2) / math.sqrt(2 * math.pi))
    if "wall" in condition:
        if m != 0 or p != 0:
            raise ValueError("wall controls require flat plateaus")
        width = sigma * condition["wall_width_sigmas"]
        shifted = 0.5 * np.asarray(_ERFC(-(t + width) / sigma / math.sqrt(2)), dtype=np.float64)
        value += (condition["wall"] - a) * (shifted - cdf)
    return value


def render(condition, sigma, normal, centre, size, *, order=None, tail_sigmas=12):
    """Sample the continuum at centres, or average each unit square aperture."""
    y, x = np.mgrid[:size, :size]
    t = (x + 0.5 - centre[0]) * normal[0] + (y + 0.5 - centre[1]) * normal[1]
    if order is None:
        return blurred_profile(t, sigma, condition, tail_sigmas=tail_sigmas)
    nodes, weights = np.polynomial.legendre.leggauss(order)
    image = np.zeros((size, size), dtype=np.float64)
    for u, wu in zip(nodes / 2, weights / 2):
        for v, wv in zip(nodes / 2, weights / 2):
            image += wu * wv * blurred_profile(t + u * normal[0] + v * normal[1], sigma, condition,
                                               tail_sigmas=tail_sigmas)
    return image


def encode_srgb8(light):
    """Independent IEC sRGB encoding and nearest-integer 8-bit quantization."""
    if not np.isfinite(light).all() or light.min() < 0 or light.max() > 255:
        raise ValueError("the rendered field is outside the unclipped 0..255 study domain")
    v = light / 255
    encoded = np.where(v <= 0.0031308, 12.92 * v,
                       1.055 * np.maximum(v, 0.0031308) ** (1 / 2.4) - 0.055)
    gray = np.rint(255 * encoded).astype(np.uint8)
    return np.repeat(gray[:, :, None], 3, axis=2)


def measure(image, centre, normal, sigma, plan, *, method, normal_sign):
    """One supplied straight profile; no segmentation or closed-ring claim."""
    points = np.asarray([centre + plan["start_offset_px"] * normal])
    normals = np.asarray([normal_sign * normal])
    measured_sigma = sigma
    if measured_sigma is None:
        measured_sigma = edges.edge_sigma(image, points, normals)
    moved, keep = sheet.half_level_search(
        image, points, normals, half=max(4.0, 3.5 * measured_sigma),
        sigma=measured_sigma, step=plan["profile_step_px"],
        min_contrast=plan["minimum_saved_contrast"], ring_smoothing=0.0,
        paper_side=np.asarray([normal_sign]) if method == "paper_only" else None,
    )
    return {"kept": bool(keep[0]), "sigma_used_px": float(measured_sigma),
            "offset_px": float((moved[0] - centre) @ normal) if keep[0] else None}


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["stage"], row["condition"], row["method"])].append(row)
    result = []
    for (stage, condition, method), group in sorted(groups.items()):
        offsets = [r["offset_px"] for r in group if r["kept"]]
        result.append({"stage": stage, "condition": condition, "method": method,
                       "cases": len(group), "kept": len(offsets),
                       "rejected": sum(r["error"] is None and not r["kept"] for r in group),
                       "failed": sum(r["error"] is not None for r in group),
                       "min_offset_px": min(offsets) if offsets else None,
                       "max_offset_px": max(offsets) if offsets else None,
                       "max_abs_offset_px": max(map(abs, offsets)) if offsets else None,
                       "mean_offset_px": float(np.mean(offsets)) if offsets else None})
    return result


def run_study(plan):
    """Evaluate the fixed crossed plan, preserving failures instead of filtering."""
    size = plan["image_size"]
    rows, quadrature_error = [], 0.0
    matrix = np.eye(3)
    translation = np.asarray(plan["rectification_translation_px"])
    matrix[:2, 2] = translation
    factors = itertools.product(plan["conditions"], plan["sigmas_px"],
                                plan["normal_angles_degrees"], plan["normal_phases_px"],
                                plan["contrast_inversions"])
    for index, (condition, sigma, angle, phase, inverted) in enumerate(factors):
        radians = math.radians(angle)
        normal = np.asarray([math.cos(radians), math.sin(radians)])
        centre = np.full(2, size / 2) + phase * normal
        point = render(condition, sigma, normal, centre, size, tail_sigmas=plan["slope_tail_sigmas"])
        aperture = render(condition, sigma, normal, centre, size,
                          order=plan["pixel_quadrature_order"], tail_sigmas=plan["slope_tail_sigmas"])
        refined = render(condition, sigma, normal, centre, size,
                         order=plan["quadrature_check_order"], tail_sigmas=plan["slope_tail_sigmas"])
        quadrature_error = max(quadrature_error, float(np.max(np.abs(refined - aperture))))
        if inverted:
            point, aperture = 255 - point, 255 - aperture
        encoded = tone.linear_luminance(encode_srgb8(aperture))
        for stage in plan["stages"]:
            if stage == "point_known_sigma":
                image, target, used_sigma = point, centre, sigma
            elif stage == "aperture_known_sigma":
                image, target, used_sigma = aperture, centre, sigma
            else:
                source = encoded if stage.startswith("srgb8_") else aperture
                rectified = sheet.rectify_gray(source, matrix, 0.0, (size, size), 1.0)
                image = cv2.GaussianBlur(rectified, (0, 0), plan["additional_smoothing_sigma_px"])
                target, used_sigma = centre - translation, None
            for method, sign in itertools.product(plan["methods"], plan["normal_signs"]):
                row = {"scene_id": index, "stage": stage, "condition": condition["name"],
                       "sigma_optical_px": sigma, "angle_degrees": angle,
                       "phase_px": phase, "contrast_inverted": inverted,
                       "normal_sign": sign, "method": method,
                       "kept": False, "sigma_used_px": None, "offset_px": None, "error": None}
                try:
                    row.update(measure(image, target, normal, used_sigma, plan,
                                       method=method, normal_sign=sign))
                    if row["sigma_used_px"] is not None and not math.isfinite(row["sigma_used_px"]):
                        raise ValueError("non-finite measured sigma")
                    if row["offset_px"] is not None and not math.isfinite(row["offset_px"]):
                        raise ValueError("non-finite crossing offset")
                except (ArithmeticError, ValueError, cv2.error) as exc:
                    row.update(kept=False, offset_px=None, error=f"{type(exc).__name__}: {exc}")
                rows.append(row)
    return rows, quadrature_error


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new result directory; existing paths are refused")
    args = parser.parse_args(arguments)
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output already exists; choose a new directory")
    hashes = source_hashes()
    plan = json.loads(PLAN.read_text())
    rows, quadrature_error = run_study(plan)
    if source_hashes() != hashes:
        raise RuntimeError("study source changed during execution")
    expected_scenes = math.prod(len(plan[key]) for key in
                                ("conditions", "sigmas_px", "normal_angles_degrees", "normal_phases_px",
                                 "contrast_inversions"))
    expected_rows = expected_scenes * len(plan["stages"]) * len(plan["methods"]) * len(plan["normal_signs"])
    assert len(rows) == expected_rows
    git = {"revision": None, "dirty": None}
    try:
        git = {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "dirty": bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"],
                                                     cwd=ROOT, text=True))}
    except (OSError, subprocess.CalledProcessError):
        pass
    results = {"format": "pictures-to-cad-material-gradient-study-result", "version": 1,
               "execution_complete": True, "physical_qualification": False,
               "world_scenes": expected_scenes, "rows": len(rows),
               "quadrature_max_change": quadrature_error,
               "quadrature_check_passed": quadrature_error <= plan["quadrature_check_tolerance"],
               "failed_rows": sum(r["error"] is not None for r in rows),
               "source_sha256": hashes, "git": git,
               "runtime": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__},
               "summary": summarize(rows), "limitations": plan["limitations"]}
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    with (args.output / "cases.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    results["cases_sha256"] = hashlib.sha256((args.output / "cases.csv").read_bytes()).hexdigest()
    (args.output / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: results[key] for key in
                      ("world_scenes", "rows", "failed_rows", "quadrature_max_change", "quadrature_check_passed",
                       "execution_complete", "physical_qualification")}))
    return int(results["failed_rows"] > 0 or not results["quadrature_check_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
