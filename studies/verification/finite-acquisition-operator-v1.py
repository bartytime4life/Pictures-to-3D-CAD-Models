#!/usr/bin/env python3
"""One prospective known-map acquisition experiment; never fits a photograph.

The required fresh output directory is checked before numerical imports. Each
original stage, row failure and first report is retained. Gaussian adequacy is
an experimental outcome distinct from successful protocol execution.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
import traceback
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/finite-acquisition-operator-v1.json"
PLAN_SHA256 = "bf12681eeda0c44552a94ea5f033424bf20aca2f9f56c83ed9226b404675989e"
HELPER_SHA256 = {
    "studies/verification/finite-acquisition-stages-v1.py": "21a2f8389094a76bbd14a3d7a43933fe56a32da8296092ebdcdac2980220e72a",
    "studies/verification/finite-acquisition-controls-v1.py": "ea83c6bb2ac18b992ca87d29e7b8b35f6972d6c20d058fb0dda83687a5daad7f",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ValueError(f"nonfinite JSON value: {value}")

    def finite(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            reject(value)
        return parsed

    return json.loads(
        Path(path).read_text(), object_pairs_hook=pairs, parse_constant=reject, parse_float=finite
    )


def portable_payload(value):
    """Retain malformed numeric results explicitly without invalid JSON tokens."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_nonfinite_float": repr(value)}
    if isinstance(value, dict):
        return {k: portable_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable_payload(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"invalid_python_value": {"type": type(value).__name__, "repr": repr(value)}}


def valid_result(result, count):
    arrays = (result.probabilities, result.statuses, result.estimated_errors, result.tail_bounds)
    if any(not isinstance(a, (tuple, list)) or len(a) != count for a in arrays):
        return False
    if any(type(n) is not int or n < 0 for n in (result.evaluations, result.panels)):
        return False
    if result.evaluations > 20_000_000 or result.panels > count * 8192:
        return False
    if (
        isinstance(result.chart_margin, bool)
        or not isinstance(result.chart_margin, (int, float))
        or not math.isfinite(result.chart_margin)
        or result.chart_margin <= 0
    ):
        return False
    if any(
        type(getattr(result, name, None)) is not bool
        for name in ("reflected", "topology_validated", "quadrature_certified")
    ):
        return False
    for p, status, error, tail in zip(*arrays, strict=True):
        if (
            status not in {"resolved", "work_limit", "numerical", "invalid_winding"}
            or isinstance(tail, bool)
            or not isinstance(tail, (int, float))
            or not math.isfinite(tail)
            or tail < 0
        ):
            return False
        if status == "resolved":
            if (
                isinstance(p, bool)
                or isinstance(error, bool)
                or not isinstance(p, (int, float))
                or not isinstance(error, (int, float))
                or not math.isfinite(p)
                or not math.isfinite(error)
                or error < 0
                or error > 1e-9
                or not -error - 2e-12 <= p <= 1 + error + 2e-12
            ):
                return False
        elif p is not None or (
            error is not None
            and (
                isinstance(error, bool)
                or not isinstance(error, (int, float))
                or not math.isfinite(error)
                or error < 0
            )
        ):
            return False
    return True


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_bindings(plan):
    names = set(plan["input_sha256"])
    names.add(str(PLAN.relative_to(ROOT)))
    names.update(
        "studies/verification/" + name
        for name in (
            "finite-acquisition-operator-v1.py",
            "finite-acquisition-stages-v1.py",
            "finite-acquisition-controls-v1.py",
        )
    )
    # Include the imported backend/test source closure rather than just entrypoints.
    names.update(
        name
        for name in subprocess.check_output(
            ["git", "ls-files", "backend", "tests"], cwd=ROOT, text=True
        ).splitlines()
        if name.endswith(".py")
    )
    return {name: sha(ROOT / name) for name in sorted(names)}


def d_geometry(config):
    angle = math.radians(config["normal_degrees"])
    n = (math.cos(angle), math.sin(angle))
    t = (-n[1], n[0])
    c, r, f = config["centre"], config["radius"], config["fraction"]
    height = math.sqrt(1 - f * f)
    start = [c[k] + r * (f * n[k] + height * t[k]) for k in range(2)]
    end = [c[k] + r * (f * n[k] - height * t[k]) for k in range(2)]
    mid = [c[k] - r * n[k] for k in range(2)]
    return [[("arc", start, mid, end), ("line", end, start)]]


def forward_call(core, work, lane, pixels, rings, **kwargs):
    call = {
        "lane": lane,
        "queries": len(pixels),
        "completed": False,
        "pixels": pixels.tolist() if hasattr(pixels, "tolist") else pixels,
        "rings": rings,
        "supplied": {k: v.tolist() if hasattr(v, "tolist") else v for k, v in kwargs.items()},
    }
    work.append(call)
    try:
        result = core.finite_shape_probabilities(pixels, rings, **kwargs)
    except Exception as exc:
        call["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    call.update(completed=True, evaluations=result.evaluations, panels=result.panels)
    call["returned_result"] = portable_payload(asdict(result))
    call["valid_payload"] = valid_result(result, len(pixels))
    return result


def gaussian_controls(core, work):
    points = [[0, 0], [10, 10], [19, 19], [29, 10], [35, 35], [15, 31]]
    corners = [[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]]
    ring = [[("line", corners[k], corners[(k + 1) % 4]) for k in range(4)]]
    rows = [
        {"q": q, "sigma": sigma, "pixels": points, "passed": False}
        for q in (1.0, 1.25)
        for sigma in (1.2, 3.0)
    ]
    for row in rows:
        q, sigma = row["q"], row["sigma"]
        try:
            reference = []
            for x, y in points:
                masses = []
                for p in (x + 0.5, y + 0.5):
                    lo = (10 * q - p) / (q * sigma * math.sqrt(2))
                    hi = (30 * q - p) / (q * sigma * math.sqrt(2))
                    masses.append(0.5 * (math.erfc(lo) - math.erfc(hi)))
                reference.append(math.prod(masses))
            row["reference"] = reference
            result = forward_call(
                core,
                work,
                "rectangle_control",
                points,
                ring,
                sensor_shape=[80, 80],
                homography=[[q, 0, 0], [0, q, 0], [0, 0, 1]],
                psf_covariance=[[q * q * sigma * sigma, 0], [0, q * q * sigma * sigma]],
                probability_tolerance=1e-9,
                max_panels=8192,
                max_evaluations=20_000_000,
            )
            row["api"] = portable_payload(asdict(result))
            row["valid_payload"] = valid_result(result, len(points))
            if row["valid_payload"]:
                row["passed"] = all(
                    status == "resolved"
                    and value is not None
                    and error is not None
                    and abs(value - expected) <= error + 2e-12
                    and abs(value - expected) <= 1e-8
                    for status, value, error, expected in zip(
                        result.statuses,
                        result.probabilities,
                        result.estimated_errors,
                        reference,
                        strict=True,
                    )
                )
        except Exception as exc:  # noqa: BLE001 -- preserve every control and continue.
            row["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
    return {"rows": rows, "passed": all(row["passed"] for row in rows)}


def keys_controls(sheet, np):
    rows = []
    for f in map(Fraction, ("0", "1/5", "1/4", "2/5", "1/2", "3/5", "3/4", "4/5")):
        expected = [
            -f * (1 - f) ** 2 / 2,
            1 - Fraction(5, 2) * f**2 + Fraction(3, 2) * f**3,
            f / 2 + 2 * f**2 - Fraction(3, 2) * f**3,
            -(f**2) * (1 - f) / 2,
        ]
        actual = sheet._keys(float(f) - np.asarray([-1, 0, 1, 2], float))
        delta = max(abs(float(a) - float(b)) for a, b in zip(actual, expected))
        rows.append(
            {
                "phase": str(f),
                "expected": list(map(str, expected)),
                "production": actual.tolist(),
                "max_error": delta,
                "passed": delta <= 2e-14,
            }
        )
    return {"rows": rows, "passed": all(row["passed"] for row in rows)}


def independent_coverage(config, coverage, np):
    from shapely.geometry import Polygon, box

    c, r = config["centre"], config["radius"]
    phi = math.radians(config["normal_degrees"])
    n, t = (math.cos(phi), math.sin(phi)), (-math.sin(phi), math.cos(phi))
    a = math.acos(config["fraction"])
    vertices = []
    for k in range(8193):
        angle = a + (2 * math.pi - 2 * a) * k / 8192
        vertices.append(
            [16 + c[j] + r * (math.cos(angle) * n[j] + math.sin(angle) * t[j]) for j in range(2)]
        )
    polygon = Polygon(vertices)
    rows = []
    x0, y0, x1, y1 = polygon.bounds
    for y in range(max(0, math.floor(y0 - 0.5)), min(coverage.shape[0], math.ceil(y1 + 0.5))):
        for x in range(max(0, math.floor(x0 - 0.5)), min(coverage.shape[1], math.ceil(x1 + 0.5))):
            expected = polygon.intersection(box(x - 0.5, y - 0.5, x + 0.5, y + 0.5)).area
            if not 0 < expected < 1:
                continue
            actual = float(coverage[y, x])
            rows.append(
                {
                    "pixel": [x, y],
                    "intersection_area": expected,
                    "coverage": actual,
                    "error": abs(expected - actual),
                }
            )
            if len(rows) == 16:
                break
        if len(rows) == 16:
            break
    return {"rows": rows, "passed": len(rows) == 16 and all(r["error"] <= 2e-7 for r in rows)}


def constant_controls(sheet, cv2, np, levels):
    rows = []
    matrix = np.asarray([[1, 0, 16.5], [0, 1, 16.5], [0, 0, 1]], float)
    for q in (1.0, 1.25):
        for level in levels:
            field = np.full((96, 96), level, np.float32)
            rectified = sheet.rectify_gray(field, matrix, 0, (64, 64), q)
            final = cv2.GaussianBlur(rectified, (0, 0), 0.7)
            error = float(np.max(np.abs(final.astype(float) - level)))
            rows.append({"q": q, "level": level, "max_error": error, "passed": error <= 2e-4})
    return {"rows": rows, "passed": all(row["passed"] for row in rows)}


def covariance(config, q, kernel_covariance, post_covariance, np):
    if config["blur"] == "isotropic":
        nominal = np.eye(2) * 1.2**2
    else:
        angle = math.radians(30)
        rotation = np.array(
            [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
        )
        nominal = rotation @ np.diag([9.0, 1.0]) @ rotation.T
    return {
        "nominal_gaussian": q * q * nominal + np.eye(2) * 0.7**2,
        "moment_gaussian": q * q * (kernel_covariance + np.eye(2) / 12) + post_covariance,
    }


def kernel_covariance(kernel, np):
    height, width = kernel.shape
    yy, xx = np.mgrid[:height, :width].astype(float)
    coordinates = np.stack((xx - width // 2, yy - height // 2), axis=-1)
    normalized = kernel.astype(float) / float(np.sum(kernel, dtype=float))
    mean = np.sum(normalized[..., None] * coordinates, axis=(0, 1))
    centered = coordinates - mean
    return np.einsum("ij,ija,ijb->ab", normalized, centered, centered)


def comparison(observed, predicted, errors, tessellation, floating, np):
    residual = observed.astype(float) - predicted
    maximum = float(np.max(np.abs(residual)))
    api_uncertainty = float(np.max(errors))
    uncertainty = api_uncertainty + tessellation + floating
    if maximum + uncertainty <= 1:
        status = "compatible"
    elif maximum - uncertainty > 1:
        status = "incompatible"
    else:
        status = "inconclusive"
    return {
        "residuals": residual.tolist(),
        "max_abs": maximum,
        "rms": float(np.sqrt(np.mean(residual**2))),
        "max_api_level_error": api_uncertainty,
        "tessellation_allowance": tessellation,
        "floating_allowance": floating,
        "total_engineering_allowance": uncertainty,
        "adequacy": status,
    }


def evaluate_row(config, metadata, source, fields, qualified, core, work, np):
    q = metadata["q"]
    centre = np.floor(q * np.asarray(config["centre"])).astype(int)
    points = np.asarray(
        [
            [int(centre[0] + x), int(centre[1] + y)]
            for y in range(-20, 21, 2)
            for x in range(-20, 21, 2)
        ],
        int,
    )
    background, material = metadata["levels_linear"]
    contrast = material - background
    observations = {
        "unquantized": fields["unquantized_final"][points[:, 1], points[:, 0]],
        "decoded_png": fields["png_final"][points[:, 1], points[:, 0]],
    }
    quantization = float(
        np.max(
            np.abs(source["decoded_linear"].astype(float) - source["optical_linear"].astype(float))
        )
    )
    peak = max(
        1.0,
        float(np.max(np.abs(source["decoded_linear"]))),
        float(np.max(np.abs(source["optical_linear"]))),
    )
    floating = 64 * np.finfo(np.float32).eps * 25 / 16 * peak
    envelope = 25 / 16 * quantization + floating
    difference = float(
        np.max(
            np.abs(fields["png_final"].astype(float) - fields["unquantized_final"].astype(float))
        )
    )
    theta = 2 * math.pi - 2 * math.acos(config["fraction"])
    area_loss_bound = config["radius"] ** 2 * theta**3 / (12 * 8192**2)
    tessellation_bound = area_loss_bound * float(np.max(source["kernel"])) * 25 / 16 * abs(contrast)
    qualified = qualified and difference <= envelope and tessellation_bound <= 1e-3
    row = {
        "scene": config["name"],
        "q": q,
        "pixels": points.tolist(),
        "observations": {k: v.astype(float).tolist() for k, v in observations.items()},
        "quantization": {
            "source_max": quantization,
            "propagated_envelope": envelope,
            "actual_final_max": difference,
            "passed": difference <= envelope,
        },
        "tessellation": {
            "area_loss_bound": area_loss_bound,
            "level_bound": tessellation_bound,
            "passed": tessellation_bound <= 1e-3,
        },
        "models": {},
        "status": "evaluated" if qualified else "reference_control_failed",
    }
    if not qualified:
        row["models"] = {
            name: {
                "status": "reference_control_failed",
                "comparisons": {lane: {"adequacy": "numerical_unknown"} for lane in observations},
            }
            for name in ("nominal_gaussian", "moment_gaussian")
        }
        return row
    matrices = covariance(
        config,
        q,
        kernel_covariance(source["kernel"], np),
        kernel_covariance(source["post_kernel"], np),
        np,
    )
    for name, matrix in matrices.items():
        # Canonicalize arithmetic symmetry only; these are declared supplied hypotheses.
        matrix = (matrix + matrix.T) / 2
        record = {
            "covariance": matrix.tolist(),
            "resolved": False,
            "comparisons": {lane: {"adequacy": "numerical_unknown"} for lane in observations},
        }
        row["models"][name] = record
        try:
            result = forward_call(
                core,
                work,
                "main_" + name,
                points,
                d_geometry(config),
                sensor_shape=fields["png_final"].shape,
                homography=[[q, 0, 0], [0, q, 0], [0, 0, 1]],
                psf_covariance=matrix,
                probability_tolerance=1e-9,
                max_panels=8192,
                max_evaluations=20_000_000,
            )
            record["api"] = portable_payload(asdict(result))
            record["valid_payload"] = valid_result(result, len(points))
            resolved = record["valid_payload"] and all(
                s == "resolved"
                and p is not None
                and e is not None
                and math.isfinite(p)
                and math.isfinite(e)
                for s, p, e in zip(result.statuses, result.probabilities, result.estimated_errors)
            )
            record["resolved"] = resolved
            if resolved:
                predicted = background + contrast * np.asarray(result.probabilities)
                errors = abs(contrast) * np.asarray(result.estimated_errors)
                record["predicted"] = predicted.tolist()
                for lane, values in observations.items():
                    record["comparisons"][lane] = comparison(
                        values, predicted, errors, tessellation_bound, floating, np
                    )
            else:
                row["status"] = "api_unresolved"
        except Exception as exc:  # noqa: BLE001 -- retain failures and continue the frozen census.
            record["error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            row["status"] = "api_unresolved"
    return row


def run(plan, output, report):
    before = source_bindings(plan)
    report["source_before"] = before
    import cv2
    import numpy as np

    from backend import finite_shape as core
    from backend import sheet

    stages = load_module(
        "acquisition_stages_v1", ROOT / "studies/verification/finite-acquisition-stages-v1.py"
    )
    exact = load_module(
        "acquisition_controls_v1", ROOT / "studies/verification/finite-acquisition-controls-v1.py"
    )
    report.update(
        {
            "format": "pictures-to-cad-finite-acquisition-operator-result",
            "version": 1,
            "plan_sha256": sha(PLAN),
            "source_before": before,
            "local_source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "opencv": cv2.__version__,
            },
            "scenes": [],
            "rows": [],
            "errors": [],
            "controls": {},
            "forward_calls": [],
            "scope": "New known-map synthetic forward adequacy only. No old replay, fit, target-pass, physical PSF or automatic integration.",
        }
    )
    controls = report["controls"]
    for name, function in (
        ("exact_keys", exact.run_controls),
        ("production_keys", lambda: keys_controls(sheet, np)),
        ("independent_gaussian", lambda: gaussian_controls(core, report["forward_calls"])),
    ):
        try:
            controls[name] = function()
        except Exception as exc:  # noqa: BLE001 -- retain failures and continue the frozen census.
            controls[name] = {
                "passed": False,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            }
    qualified = global_qualified(controls)
    for config in plan["scenes"]:
        try:
            scene_dir = output / config["name"]
            metadata = stages.run_scene(config, scene_dir)
            scene = {"metadata": metadata}
            report["scenes"].append(scene)
            if metadata.get("status") != "complete" or not metadata.get("source_unchanged"):
                raise RuntimeError("scene stages incomplete; retained scene.json is authoritative")
            source_file = scene_dir / "source.npz"
            with np.load(source_file, allow_pickle=False) as archive:
                source = {name: archive[name].copy() for name in archive.files}
            scene["coverage_control"] = independent_coverage(config, source["coverage"], np)
            if "constants" not in controls:
                controls["constants"] = constant_controls(sheet, cv2, np, metadata["levels_linear"])
            for entry in metadata["rows"]:
                try:
                    with np.load(scene_dir / entry["fields_file"], allow_pickle=False) as archive:
                        fields = {name: archive[name].copy() for name in archive.files}
                    row_metadata = {**entry, "levels_linear": metadata["levels_linear"]}
                    report["rows"].append(
                        evaluate_row(
                            config,
                            row_metadata,
                            source,
                            fields,
                            qualified and stage_qualified(scene, entry, controls["constants"]),
                            core,
                            report["forward_calls"],
                            np,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 -- retain failures and continue the frozen census.
                    report["rows"].append(
                        {
                            "scene": config["name"],
                            "q": entry["q"],
                            "status": "row_exception",
                            "error": {
                                "type": type(exc).__name__,
                                "message": str(exc),
                                "traceback": traceback.format_exc(),
                            },
                        }
                    )
        except Exception as exc:  # noqa: BLE001 -- retain failures and continue the frozen census.
            report["errors"].append(
                {
                    "scene": config["name"],
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        # Keep all identities even when a scene or stage fails before it returns.
        for q in (1.0, 1.25):
            if not any(row["scene"] == config["name"] and row["q"] == q for row in report["rows"]):
                report["rows"].append(
                    {"scene": config["name"], "q": q, "status": "scene_exception"}
                )
        with (output / "progress.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "scene": config["name"],
                        "retained_rows": len(report["rows"]),
                        "errors": len(report["errors"]),
                    },
                    allow_nan=False,
                )
                + "\n"
            )
        print(
            json.dumps({"scene": config["name"], "retained_rows": len(report["rows"])}), flush=True
        )
    after = source_bindings(plan)
    report["source_after"] = after
    report["source_unchanged"] = before == after
    report["protocol_passed"] = protocol_passed(report, plan)
    cells = {}
    for row in report["rows"]:
        for model, item in row.get("models", {}).items():
            for lane, value in item["comparisons"].items():
                key = model + "/" + lane
                cells.setdefault(
                    key,
                    {"compatible": 0, "incompatible": 0, "inconclusive": 0, "numerical_unknown": 0},
                )
                cells[key][value["adequacy"]] += 1
    report["adequacy_counts"] = cells
    return report


def global_qualified(controls):
    return controls.get("exact_keys", {}).get("protocol_passed", False) and all(
        controls.get(name, {}).get("passed", False)
        for name in ("production_keys", "independent_gaussian")
    )


def stage_qualified(scene, row, constants):
    return (
        constants.get("passed", False)
        and scene.get("coverage_control", {}).get("passed", False)
        and scene["metadata"].get("status") == "complete"
        and scene["metadata"].get("source_unchanged", False)
        and row.get("status") == "complete"
        and set(row.get("smoothing_comparison", {})) == {"unquantized", "png"}
        and all(
            math.isfinite(v["max_abs_difference"]) and v["max_abs_difference"] <= 2e-4
            for v in row["smoothing_comparison"].values()
        )
    )


def complete_adequacy_census(report, plan):
    """Missing stages remain in the declared denominator as explicit unknowns."""
    for config in plan["scenes"]:
        for q in (1.0, 1.25):
            matches = [r for r in report["rows"] if r["scene"] == config["name"] and r["q"] == q]
            if not matches:
                matches = [{"scene": config["name"], "q": q, "status": "not_completed"}]
                report["rows"].extend(matches)
            for row in matches:
                for model in ("nominal_gaussian", "moment_gaussian"):
                    record = row.setdefault("models", {}).setdefault(model, {})
                    for lane in ("unquantized", "decoded_png"):
                        record.setdefault("comparisons", {}).setdefault(
                            lane, {"adequacy": "numerical_unknown"}
                        )
    counts = {}
    for row in report["rows"]:
        for model, record in row["models"].items():
            for lane, cell in record["comparisons"].items():
                key = model + "/" + lane
                counts.setdefault(
                    key,
                    {
                        s: 0
                        for s in ("compatible", "incompatible", "inconclusive", "numerical_unknown")
                    },
                )
                counts[key][cell["adequacy"]] += 1
    report["adequacy_counts"] = counts


def protocol_passed(report, plan):
    expected = [(c["name"], q) for c in plan["scenes"] for q in (1.0, 1.25)]
    if [(r["scene"], r["q"]) for r in report["rows"]] != expected:
        return False
    if report["errors"] or not report["source_unchanged"] or len(report["scenes"]) != 16:
        return False
    controls = report["controls"]
    if not controls.get("exact_keys", {}).get("protocol_passed", False):
        return False
    if not all(
        controls.get(k, {}).get("passed", False)
        for k in ("production_keys", "independent_gaussian", "constants")
    ):
        return False
    for scene in report["scenes"]:
        if not scene.get("coverage_control", {}).get("passed", False):
            return False
        metadata = scene["metadata"]
        if metadata.get("status") != "complete" or not metadata.get("source_unchanged"):
            return False
        if [r["q"] for r in metadata["rows"]] != [1.0, 1.25]:
            return False
        for row in metadata["rows"]:
            if not stage_qualified(scene, row, controls["constants"]):
                return False
    for row in report["rows"]:
        if (
            row["status"] != "evaluated"
            or not row["quantization"]["passed"]
            or not row["tessellation"]["passed"]
        ):
            return False
        if len(row["pixels"]) != 441 or len(row["models"]) != 2:
            return False
        if not all(item["resolved"] and item["valid_payload"] for item in row["models"].values()):
            return False
    calls = report["forward_calls"]
    main = [c for c in calls if c["lane"].startswith("main_")]
    reference = [c for c in calls if c["lane"] == "rectangle_control"]
    return (
        len(main) == 64
        and sum(c["queries"] for c in main) == 28224
        and len(reference) == 4
        and sum(c["queries"] for c in reference) == 24
        and all(c["completed"] and c["valid_payload"] for c in calls)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Fresh directory with existing parent; refuses existing files/symlinks",
    )
    args = parser.parse_args()
    output = args.output_dir.absolute()
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        parser.error("output directory must be fresh and its parent must exist")
    if sha(PLAN) != PLAN_SHA256:
        parser.error("frozen plan SHA-256 mismatch")
    plan = read_json(PLAN)
    for name, expected in plan["input_sha256"].items():
        if sha(ROOT / name) != expected:
            parser.error(f"frozen source/input changed: {name}")
    for name, expected in HELPER_SHA256.items():
        if sha(ROOT / name) != expected:
            parser.error(f"frozen helper SHA-256 mismatch: {name}")
    # Reserve the destination before importing any numerical implementation.
    output.mkdir(mode=0o700)
    sys.path.insert(0, str(ROOT))
    report = {
        "format": "pictures-to-cad-finite-acquisition-operator-result",
        "version": 1,
        "plan_sha256": sha(PLAN),
        "protocol_passed": False,
        "rows": [],
    }
    try:
        run(plan, output, report)
    except Exception as exc:  # noqa: BLE001 -- retain failures and continue the frozen census.
        report.update(
            {
                "protocol_passed": False,
                "terminal_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            }
        )
        for c in plan["scenes"]:
            for q in (1.0, 1.25):
                if not any(r["scene"] == c["name"] and r["q"] == q for r in report["rows"]):
                    report["rows"].append(
                        {"scene": c["name"], "q": q, "status": "terminal_exception"}
                    )
    try:
        report["source_after"] = source_bindings(plan)
        report["source_unchanged"] = report.get("source_before") == report["source_after"]
        if not report["source_unchanged"]:
            report["protocol_passed"] = False
    except (OSError, subprocess.SubprocessError) as exc:
        report["source_after_error"] = {"type": type(exc).__name__, "message": str(exc)}
        report["protocol_passed"] = False
    complete_adequacy_census(report, plan)
    report = portable_payload(report)
    write_new(output / "report.json", report)
    print(
        json.dumps(
            {"report": str(output / "report.json"), "protocol_passed": report["protocol_passed"]}
        ),
        flush=True,
    )
    return 0 if report["protocol_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
