"""Joint wall/lighting development experiment and constructive ambiguity witnesses.

No production decisions change. Source levels, geometry and optical blur are
explicit synthetic inputs. A finite-grid least-squares witness is not an
enclosure of every compatible edge or a calibrated physical uncertainty.

    .venv/bin/python scripts/wall_gradient_study.py --output NEW_DIRECTORY
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
from backend import edges

PLAN = ROOT / "studies/wall-gradients-v1.json"
SOURCES = ("scripts/wall_gradient_study.py", "studies/wall-gradients-v1.json",
           "backend/edges.py", "backend/sheet.py", "backend/tone.py")
_ERFC = np.frompyfunc(math.erfc, 1, 1)


def normal_cdf(z):
    """Independent standard-library Gaussian CDF; no production approximation."""
    return 0.5 * np.asarray(_ERFC(-np.asarray(z) / math.sqrt(2)), dtype=np.float64)


def source_basis(t, edge, band, sigma, tail):
    """Blurred bounded source's five node-level coefficients (last axis).

    Source nodes: top at -tail and -band, flat wall [-band,0], paper at
    0 and tail, relative to edge. Linear top/paper segments have constant
    exterior tails. Node levels in [0,255] bound the entire real source.
    Exact basis entries are nonnegative and sum to one. No clipping hides
    floating-point evaluation error in this experiment.
    """
    if not all(math.isfinite(v) for v in (edge, band, sigma, tail)):
        raise ValueError("geometry must be finite")
    if not sigma > 0 or not 0 <= band < tail:
        raise ValueError("require sigma>0 and 0<=band<tail")
    x = np.asarray(t, dtype=np.float64) - edge
    if not np.isfinite(x).all():
        raise ValueError("sample coordinates must be finite")

    def first(z, positive):
        density = sigma * np.exp(-0.5 * (z / sigma) ** 2) / math.sqrt(2 * math.pi)
        return z * normal_cdf(z / sigma) + density if positive else z * normal_cdf(-z / sigma) - density

    top = normal_cdf(-(x + band) / sigma)
    paper = normal_cdf(x / sigma)
    wall = normal_cdf((x + band) / sigma) - paper
    top_moment = first(x + band, False) - first(x + tail, False)
    paper_moment = first(x, True) - first(x - tail, True)
    top_left = -top_moment / (tail - band)
    paper_right = paper_moment / tail
    return np.stack((top_left, top - top_left, wall, paper - paper_right, paper_right), axis=-1)


def bounded_projection(design, observed):
    """Small box-constrained linear least squares via all active faces and SVD.

    First try the unconstrained solution. Otherwise enumerate each coefficient
    as lower-bound, free or upper-bound (at most 3**5 faces). Every feasible
    face's free least-squares solution is evaluated using its direct residual,
    without normal equations or subtracting large squared norms. This is an
    ordinary floating-point optimization, not validated interval arithmetic.
    """
    design, observed = np.asarray(design, float), np.asarray(observed, float)
    if design.ndim != 2 or observed.shape != (len(design),) or not 1 <= design.shape[1] <= 5:
        raise ValueError("require a finite N-by-1..5 design and N observations")
    if not np.isfinite(design).all() or not np.isfinite(observed).all():
        raise ValueError("projection inputs must be finite")
    coefficients = np.linalg.lstsq(design, observed, rcond=None)[0]
    if np.all((coefficients >= 0) & (coefficients <= 255)):
        return coefficients, 1
    best, least, solved = None, math.inf, 1
    for state in itertools.product((-1, 0, 1), repeat=design.shape[1]):
        state = np.asarray(state)
        free = state == 0
        if free.all():
            continue
        trial = np.where(state == 1, 255.0, 0.0)
        if free.any():
            trial[free] = np.linalg.lstsq(design[:, free], observed - design @ trial, rcond=None)[0]
        solved += 1
        if np.any((trial < 0) | (trial > 255)):
            continue
        residual = design @ trial - observed
        cost = float(residual @ residual)
        if cost < least:
            best, least = trial, cost
    if best is None:
        raise ArithmeticError("no feasible box face found")
    return best, solved


def fit_at_geometry(t, observed, edge, band, sigma, tail, model):
    basis = source_basis(t, edge, band, sigma, tail)
    if model == "flat_tones":
        design = np.column_stack((basis[:, 0] + basis[:, 1], basis[:, 2], basis[:, 3] + basis[:, 4]))
    elif model == "joint_gradients":
        design = basis
    else:
        raise ValueError("unknown model")
    coefficient, faces = bounded_projection(design, observed)
    levels = coefficient[[0, 0, 1, 2, 2]] if model == "flat_tones" else coefficient
    predicted = basis @ levels
    residual = predicted - observed
    midpoint = (predicted + observed) / 2
    singular = np.linalg.svd(design, compute_uv=False)
    return {"levels": levels, "sse": float(residual @ residual),
            "maximum_difference": float(np.max(np.abs(residual))),
            "midpoint_error_bound": float(max(np.max(np.abs(midpoint - predicted)),
                                               np.max(np.abs(midpoint - observed)))),
            "design_rank": int(np.linalg.matrix_rank(design)),
            "design_condition": float(singular[0] / singular[-1]) if singular[-1] > 0 else None,
            "faces_solved": faces}


def render(levels, sigma, band, normal, centre, size, tail, order=None):
    y, x = np.mgrid[:size, :size]
    t = (x + 0.5 - centre[0]) * normal[0] + (y + 0.5 - centre[1]) * normal[1]
    if order is None:
        return source_basis(t, 0.0, band, sigma, tail) @ levels
    nodes, weights = np.polynomial.legendre.leggauss(order)
    image = np.zeros_like(t)
    for u, wu in zip(nodes / 2, weights / 2):
        for v, wv in zip(nodes / 2, weights / 2):
            image += wu * wv * (source_basis(t + u * normal[0] + v * normal[1], 0.0, band, sigma, tail) @ levels)
    return image


def direct_study(plan):
    lane = plan["direct_lane"]
    rows = []
    worlds = itertools.product(plan["sigmas_px"], lane["band_width_sigmas"],
                               plan["conditions"], plan["contrast_inversions"])
    for scene, (sigma, width, condition, inverted) in enumerate(worlds):
        band, tail = sigma * width, sigma * plan["source_tail_sigmas"]
        count = math.ceil((band + 4 * sigma) / plan["profile_step_px"])
        t = np.arange(-count, math.ceil(4 * sigma / plan["profile_step_px"]) + 1) * plan["profile_step_px"]
        levels = np.asarray(condition["levels"])
        if inverted:
            levels = 255 - levels
        observed = source_basis(t, 0.0, band, sigma, tail) @ levels
        for offset, model in itertools.product(lane["offsets_sigmas"], lane["models"]):
            row = {"scene_id": scene, "condition": condition["name"], "sigma_px": sigma,
                   "band_sigmas": width, "contrast_inverted": inverted, "offset_sigmas": offset,
                   "offset_px": offset * sigma, "model": model, "sample_count": len(t),
                   "top_left": None, "top_edge": None, "wall": None, "paper_edge": None,
                   "paper_right": None, "sse": None, "maximum_difference": None,
                   "midpoint_error_bound": None, "design_rank": None, "design_condition": None,
                   "faces_solved": None, "error": None}
            try:
                result = fit_at_geometry(t, observed, offset * sigma, band, sigma, tail, model)
                fitted = result.pop("levels")
                row.update(dict(zip(("top_left", "top_edge", "wall", "paper_edge", "paper_right"), fitted)))
                row.update(result)
            except (ArithmeticError, ValueError, np.linalg.LinAlgError) as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(row)
    return rows


def image_study(plan):
    lane = plan["image_lane"]
    size = lane["image_size"]
    rows, quadrature_error = [], 0.0
    worlds = itertools.product(plan["sigmas_px"], lane["band_width_sigmas"], plan["conditions"],
                               plan["contrast_inversions"], lane["normal_angles_degrees"],
                               lane["normal_phases_px"])
    for scene, (sigma, width, condition, inverted, angle, phase) in enumerate(worlds):
        band, tail = sigma * width, sigma * plan["source_tail_sigmas"]
        normal = np.asarray([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
        centre = np.full(2, size / 2) + phase * normal
        levels = np.asarray(condition["levels"])
        if inverted:
            levels = 255 - levels
        point = render(levels, sigma, band, normal, centre, size, tail)
        aperture = render(levels, sigma, band, normal, centre, size, tail,
                          order=lane["aperture_quadrature_order"])
        checked = render(levels, sigma, band, normal, centre, size, tail,
                         order=lane["aperture_check_order"])
        quadrature_error = max(quadrature_error, float(np.max(np.abs(checked - aperture))))
        if not all(np.isfinite(image).all() and image.min() >= -1e-10 and image.max() <= 255 + 1e-10
                   for image in (point, aperture, checked)):
            raise ArithmeticError("rendered field outside bounded light domain")
        seed = centre + lane["start_offset_sigmas"] * sigma * normal
        for stage, method in itertools.product(lane["stages"], lane["methods"]):
            row = {"scene_id": scene, "condition": condition["name"], "sigma_px": sigma,
                   "band_sigmas": width, "contrast_inverted": inverted,
                   "normal_degrees": angle, "phase_px": phase, "stage": stage, "method": method,
                   "offset_px": None, "offset_sigmas": None, "wall_level": None,
                   "reported_sse": None, "error": None}
            try:
                moved, walls, residual = edges.two_step_refine(
                    point if stage == "point_known_sigma" else aperture,
                    seed[None, :], normal[None, :], np.asarray([band]), sigma,
                    wall_tone=levels[2] if method == "true_fixed_wall_tone" else None,
                    step=plan["profile_step_px"], with_residuals=True)
                offset = float((moved[0] - centre) @ normal)
                values = (offset, float(walls[0]), float(residual[0]))
                if not all(math.isfinite(v) for v in values):
                    raise ArithmeticError("non-finite production fit")
                row.update(offset_px=offset, offset_sigmas=offset / sigma,
                           wall_level=values[1], reported_sse=values[2])
            except (ArithmeticError, ValueError, np.linalg.LinAlgError, cv2.error) as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(row)
    return rows, quadrature_error


def exact_ambiguity(plan):
    p = plan["exact_ambiguity"]
    t = np.arange(-8.0, 8.001, plan["profile_step_px"])
    top, paper, width, sigma = p["top_level"], p["paper_level"], p["band_px"], p["sigma_px"]
    tail = plan["source_tail_sigmas"] * sigma
    first = source_basis(t, p["first_edge_px"], width, sigma, tail) @ [top, top, top, paper, paper]
    second = source_basis(t, p["second_edge_px"], width, sigma, tail) @ [top, top, paper, paper, paper]
    return {**p, "maximum_float_difference": float(np.max(np.abs(first - second))),
            "edge_separation_px": abs(p["second_edge_px"] - p["first_edge_px"]),
            "minimum_worst_case_error_px_for_same_returned_edge": width / 2,
            "basis": "Identical real source fields: top left of first edge, paper right of it; the wall/edge labels differ"}


def summarize_images(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["stage"], row["method"], row["condition"], row["band_sigmas"])].append(row)
    result = []
    for key, group in sorted(groups.items()):
        values = np.asarray([row["offset_px"] for row in group if row["error"] is None])
        result.append(dict(zip(("stage", "method", "condition", "band_sigmas"), key)) | {
            "planned": len(group), "failed": sum(row["error"] is not None for row in group),
            "median_offset_px": float(np.median(values)) if len(values) else None,
            "maximum_absolute_offset_px": float(np.max(np.abs(values))) if len(values) else None,
            "fitted_wall_outside_0_255": sum(row["wall_level"] is not None and not 0 <= row["wall_level"] <= 255
                                             for row in group)})
    return result


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory; existing paths are refused")
    args = parser.parse_args(arguments)
    try:
        args.output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output already exists; choose a new directory")
    hashes = source_hashes()
    plan = json.loads(PLAN.read_text())
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    direct = direct_study(plan)
    images, quadrature_error = image_study(plan)
    if source_hashes() != hashes:
        raise RuntimeError("executed source changed during study")
    direct_worlds = math.prod(len(v) for v in (plan["sigmas_px"], plan["direct_lane"]["band_width_sigmas"],
                                             plan["conditions"], plan["contrast_inversions"]))
    image_worlds = math.prod(len(v) for v in (plan["sigmas_px"], plan["image_lane"]["band_width_sigmas"],
                                            plan["conditions"], plan["contrast_inversions"],
                                            plan["image_lane"]["normal_angles_degrees"], plan["image_lane"]["normal_phases_px"]))
    assert len(direct) == direct_worlds * len(plan["direct_lane"]["offsets_sigmas"]) * len(plan["direct_lane"]["models"])
    assert len(images) == image_worlds * len(plan["image_lane"]["stages"]) * len(plan["image_lane"]["methods"])
    artifacts = {}
    for name, rows in (("geometry-fits.csv", direct), ("image-fits.csv", images)):
        with (args.output / name).open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        artifacts[name] = hashlib.sha256((args.output / name).read_bytes()).hexdigest()
    git = {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
           "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True))}
    witnesses = []
    for model, bound in itertools.product(plan["direct_lane"]["models"], plan["direct_lane"]["illustrative_level_error_bounds"]):
        eligible = [r for r in direct if r["model"] == model and r["offset_px"] != 0]
        found = [r for r in eligible if r["error"] is None and r["midpoint_error_bound"] <= bound]
        witnesses.append({"model": model, "illustrative_level_bound": bound, "alternative_fits_examined": len(eligible),
                          "witnesses_found": len(found),
                          "maximum_demonstrated_edge_separation_px": max((abs(r["offset_px"]) for r in found), default=None),
                          "not_an_uncertainty_enclosure": True})
    results = {"format": "pictures-to-cad-wall-gradient-study-result", "version": 1,
               "execution_complete": True, "physical_qualification": False,
               "direct_world_scenes": direct_worlds, "direct_rows": len(direct),
               "image_world_scenes": image_worlds, "image_rows": len(images),
               "failed_rows": sum(r["error"] is not None for r in direct + images),
               "quadrature_max_change": quadrature_error,
               "quadrature_check_passed": quadrature_error <= plan["image_lane"]["quadrature_check_tolerance"],
               "exact_ambiguity": exact_ambiguity(plan), "witness_summary": witnesses,
               "image_summary": summarize_images(images), "source_sha256": hashes,
               "artifact_sha256": artifacts, "git": git,
               "runtime": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__},
               "limitations": plan["limitations"]}
    (args.output / "results.json").write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: results[key] for key in ("execution_complete", "physical_qualification", "direct_world_scenes",
                                                   "direct_rows", "image_world_scenes", "image_rows", "failed_rows",
                                                   "quadrature_max_change", "quadrature_check_passed")}))
    return int(results["failed_rows"] > 0 or not results["quadrature_check_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
