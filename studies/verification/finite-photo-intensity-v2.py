#!/usr/bin/env python3
"""Replay ring-conditioned intensity fits of the SAME archived v1 photo fields.

Required --output NEW_JSON is refused before backend imports/analysis if occupied
or invalid. No image is rendered, no trace is rerun, and no v1 input is modified.
The two covariance lanes share one data-derived crop, selection, seed and domain.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/finite-photo-intensity-v2.json"
RUNNER = Path(__file__).resolve()
FIXTURES = ROOT / "studies/fixtures/finite-moment-photo-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key:{key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"nonfinite JSON value:{value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            nonfinite(value)
        return number

    return json.loads(
        Path(path).read_text(),
        object_pairs_hook=pairs,
        parse_constant=nonfinite,
        parse_float=finite_float,
    )


def parsed_sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_inputs(plan):
    for name, expected in plan["input_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"frozen portable input changed:{name}")
    manifest = strict_json(ROOT / plan["inputs"]["moment_manifest"])
    for name, expected in manifest["archived_files"].items():
        if Path(name).name != name or sha(FIXTURES / name) != expected:
            raise ValueError(f"archived moment input changed:{name}")
    for item in manifest["measurements"]:
        if (
            Path(item["file"]).name != item["file"]
            or sha(FIXTURES / item["file"]) != item["file_sha256"]
        ):
            raise ValueError(f"archived measurement changed:{item['file']}")
    archive = strict_json(ROOT / plan["inputs"]["v1_archive_manifest"])
    for name, expected in archive["files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"archived v1 input changed:{name}")
    baseline = strict_json(ROOT / plan["inputs"]["baseline"])
    moments = strict_json(ROOT / plan["inputs"]["moment_result"])
    v1 = strict_json(ROOT / plan["inputs"]["v1_result"])
    if [r["case"]["name"] for r in baseline["rows"]] != plan["cases"]:
        raise ValueError("baseline six-case order/population changed")
    if [(r["name"], r["lane"]) for r in v1["rows"]] != [
        (name, lane) for name in plan["cases"] for lane in plan["lanes"]
    ]:
        raise ValueError("all12 archived v1 parsed rows required")
    return manifest, baseline, moments, v1


def source_hashes(plan, manifest):
    names = {
        "backend/__init__.py",
        "backend/finite_observations.py",
        "backend/finite_centre_fit.py",
        "backend/finite_shape.py",
        "backend/fitting.py",
        "backend/circular_joins.py",
        "backend/reference.py",
        "backend/edges.py",
        "backend/sheet.py",
        "backend/tone.py",
        "uv.lock",
        "studies/finite-free-centre-v1.json",
        "studies/verification/finite-free-centre-v1.py",
        str(RUNNER.relative_to(ROOT)),
        str(PLAN.relative_to(ROOT)),
        *plan["inputs"].values(),
    }
    names.update(str((FIXTURES / name).relative_to(ROOT)) for name in manifest["archived_files"])
    names.update(
        str((FIXTURES / item["file"]).relative_to(ROOT)) for item in manifest["measurements"]
    )
    archive = strict_json(ROOT / plan["inputs"]["v1_archive_manifest"])
    names.update(archive["files"])
    return {name: sha(ROOT / name) for name in sorted(names)}


def observed_normal(primitives, np):
    lines = [p for p in primitives or [] if p["kind"] == "line"]
    arcs = [p for p in primitives or [] if p["kind"] == "arc"]
    if not lines or not arcs:
        raise ValueError("no observed line/arc witnesses")
    line = max(
        lines, key=lambda p: np.linalg.norm(np.diff(np.asarray(p["data"]["source_ends"]), axis=0))
    )
    arc = max(arcs, key=lambda p: p["data"]["r"])
    direction = np.asarray(line["data"]["d"], float)
    direction /= np.linalg.norm(direction)
    normal = np.array([-direction[1], direction[0]])
    witness = np.asarray(arc["data"]["mid"]) - arc["data"]["c"]
    dot = float(normal @ witness)
    if not math.isfinite(dot) or dot == 0:
        raise ValueError("observed arc sector cannot orient chord normal")
    if dot > 0:
        normal = -normal
    return normal, {
        "normal": normal.tolist(),
        "line": line,
        "arc_sector_witness": arc,
        "negative_sector_dot": float(normal @ witness),
    }


def covariance_record(raw, np):
    raw = np.asarray(raw, float)
    record = {"raw": raw.tolist(), "valid": False}
    if raw.shape != (2, 2) or not np.isfinite(raw).all():
        return {**record, "reason": "nonfinite or invalid covariance shape"}
    asym = float(np.max(np.abs(raw - raw.T)))
    guard = 64 * np.finfo(float).eps * float(np.max(np.abs(raw)))
    record.update(asymmetry=asym, arithmetic_guard=guard)
    if asym > guard:
        return {**record, "reason": "beyond arithmetic symmetry guard"}
    canonical = (raw + raw.T) / 2
    eigen = np.linalg.eigvalsh(canonical)
    record.update(
        canonical=canonical.tolist(),
        maximum_representation_change=float(np.max(np.abs(canonical - raw))),
        eigenvalues=eigen.tolist(),
    )
    if np.any(eigen <= 0):
        return {**record, "reason": "nonpositive covariance; not repaired"}
    try:
        np.linalg.cholesky(canonical)
    except np.linalg.LinAlgError:
        return {**record, "reason": "Cholesky refusal; not repaired"}
    return {**record, "valid": True}


def prepare(helper, field, points, normal, sigma):
    return helper.prepare_segment_observations(
        field, points, normal=normal, blur_sigma=sigma, polarity="dark"
    )


def snapshot(observation):
    return {
        "crop_origin": list(observation.crop_origin),
        "crop_bounds": list(observation.crop_bounds),
        "field_shape": list(observation.field.shape),
        "field_dtype": observation.field.dtype.str,
        "field_sha256": hashlib.sha256(observation.field.tobytes()).hexdigest(),
        "training_pixels": observation.training_pixels.tolist(),
        "training_values": observation.training_values.tolist(),
        "heldout_pixels": observation.heldout_pixels.tolist(),
        "heldout_values": observation.heldout_values.tolist(),
        "homography": observation.homography.tolist(),
        "normal": list(observation.normal),
        "seed_centre": list(observation.seed_centre),
        "seed_radius": observation.seed_radius,
        "seed_fraction": observation.seed_fraction,
        "bounds": observation.bounds,
    }


def shifted_primitives(primitives, offset, np):
    shifted = copy.deepcopy(primitives)
    for p in shifted:
        for name in ("c", "mid"):
            if name in p["data"]:
                p["data"][name] = (np.asarray(p["data"][name]) + offset).tolist()
        if "source_ends" in p["data"]:
            p["data"]["source_ends"] = (np.asarray(p["data"]["source_ends"]) + offset).tolist()
    return shifted


def observation_controls(
    name,
    field,
    points,
    primitives,
    observation,
    common_sigma,
    covariances,
    helper,
    core,
    oracle,
    oracle_plan,
    np,
):
    base = snapshot(observation)
    rows = []
    x0, y0, x1, y1 = map(int, observation.crop_bounds)
    saved_crop = field[y0:y1, x0:x1]
    rows.append(
        {
            "name": "byte-preserving-field-crop",
            "passed": bool(
                observation.field.dtype == saved_crop.dtype
                and observation.field.shape == saved_crop.shape
                and observation.field.tobytes() == saved_crop.tobytes()
                and not observation.field.flags.writeable
            ),
            "source_dtype": saved_crop.dtype.str,
            "crop_dtype": observation.field.dtype.str,
        }
    )
    yy, xx = np.indices(field.shape)
    dirty = np.asarray((xx + yy) % 2 * 255, dtype=field.dtype)
    dirty[y0:y1, x0:x1] = field[y0:y1, x0:x1]
    changed = prepare(helper, dirty, points, np.asarray(observation.normal), common_sigma)
    rows.append(
        {
            "name": "dirty-outside-crop",
            "passed": snapshot(changed) == base,
            "scope": "Only pixels outside fixed ring crop changed; whole-source provenance may change.",
        }
    )
    offset = np.array([11, 7])
    canvas = np.full((field.shape[0] + 7, field.shape[1] + 11), 173.0, dtype=field.dtype)
    canvas[7:, 11:] = field
    n2, _ = observed_normal(shifted_primitives(primitives, offset, np), np)
    translated = prepare(helper, canvas, points + offset, n2, common_sigma)
    shifted = snapshot(translated)
    same_keys = (
        "field_shape",
        "field_dtype",
        "field_sha256",
        "training_pixels",
        "training_values",
        "heldout_pixels",
        "heldout_values",
        "seed_radius",
        "seed_fraction",
    )
    local_same = all(
        shifted[k] == base[k] for k in same_keys if k not in ("seed_radius", "seed_fraction")
    )
    frame_same = bool(
        np.array_equal(
            np.asarray(translated.crop_origin), np.asarray(observation.crop_origin) + offset
        )
        and np.array_equal(
            translated.homography,
            np.asarray(observation.homography)
            @ np.array([[1.0, 0.0, -11.0], [0.0, 1.0, -7.0], [0.0, 0.0, 1.0]]),
        )
        and np.array_equal(translated.normal, observation.normal)
    )
    numerical = max(
        float(
            np.max(
                np.abs(
                    np.asarray(translated.seed_centre)
                    - np.asarray(observation.seed_centre)
                    - offset
                )
            )
        ),
        abs(translated.seed_radius - observation.seed_radius),
        abs(translated.seed_fraction - observation.seed_fraction),
        float(
            np.max(
                np.abs(
                    np.asarray(translated.centre_bounds)
                    - np.asarray(observation.centre_bounds)
                    - offset[:, None]
                )
            )
        ),
        float(
            np.max(
                np.abs(np.asarray(translated.radius_bounds) - np.asarray(observation.radius_bounds))
            )
        ),
        float(
            np.max(
                np.abs(
                    np.asarray(translated.chord_fraction_bounds)
                    - np.asarray(observation.chord_fraction_bounds)
                )
            )
        ),
    )
    rows.append(
        {
            "name": "integer-crop-translation",
            "local_bytes_and_samples_identical": local_same,
            "global_crop_frame_translated_exactly": frame_same,
            "maximum_global_parameter_shift_error_px": numerical,
            "passed": local_same and frame_same and numerical <= 1e-8,
            "offset_xy": offset.tolist(),
            "translated_crop_origin": list(translated.crop_origin),
        }
    )
    try:
        prepare(
            helper,
            field,
            points - points.min(axis=0) + 0.1,
            np.asarray(observation.normal),
            common_sigma,
        )
        rows.append(
            {
                "name": "full-padding-edge-refusal",
                "passed": False,
                "reason": "unexpected acceptance",
            }
        )
    except helper.ObservationPreparationError as error:
        rows.append(
            {
                "name": "full-padding-edge-refusal",
                "passed": error.reason == "crop_edge",
                "reason": error.reason,
            }
        )
    pixels = np.vstack((observation.training_pixels, observation.heldout_pixels))
    global_pixels = pixels + np.asarray(observation.crop_origin, int)
    for lane, cov in covariances.items():
        if not cov["valid"]:
            rows.append(
                {
                    "name": f"intensity-frame-{lane}",
                    "status": "covariance_ineligible",
                    "passed": True,
                }
            )
            continue
        sigma = np.asarray(cov["canonical"])
        args = {
            "centre": observation.seed_centre,
            "normal": observation.normal,
            "psf_covariance": sigma,
        }
        global_mean = core.circular_segment_probabilities(
            global_pixels,
            observation.seed_radius,
            observation.seed_fraction,
            sensor_shape=field.shape,
            homography=np.eye(3),
            **args,
        )
        local_mean = core.circular_segment_probabilities(
            pixels,
            observation.seed_radius,
            observation.seed_fraction,
            sensor_shape=observation.field.shape,
            homography=observation.homography,
            **args,
        )
        available = all(s == "resolved" for s in (*global_mean.statuses, *local_mean.statuses))
        config = {
            "centre": list(observation.seed_centre),
            "radius": observation.seed_radius,
            "fraction": observation.seed_fraction,
            "normal_degrees": math.degrees(
                math.atan2(observation.normal[1], observation.normal[0])
            ),
            "covariance": sigma.tolist(),
            "homography": observation.homography.tolist(),
            "levels": [0.0, 255.0],
            "source": "point",
        }
        low = oracle.independent_means(pixels + 0.5, config, 32, oracle_plan)
        high = oracle.independent_means(pixels + 0.5, config, 64, oracle_plan)
        order_delta = float(np.max(abs(high - low)))
        frame_delta = (
            float(
                255
                * np.max(
                    abs(
                        np.asarray(global_mean.probabilities) - np.asarray(local_mean.probabilities)
                    )
                )
            )
            if available
            else None
        )
        independent_delta = (
            float(np.max(abs(255 * np.asarray(local_mean.probabilities) - high)))
            if available
            else None
        )
        rows.append(
            {
                "name": f"intensity-frame-{lane}",
                "available": available,
                "maximum_global_crop_level_delta": frame_delta,
                "maximum_independent_area_level_delta": independent_delta,
                "independent32_64_level_delta": order_delta,
                "passed": bool(
                    available
                    and frame_delta <= 2e-5
                    and independent_delta <= 2e-5
                    and order_delta <= 1e-7
                ),
                "scope": "Observed seed only, fixed0/255 diagnostic levels; numerical frame/mean checks, not Gaussian/camera validation.",
            }
        )
    return {"name": name, "checks": rows, "all_passed": all(r["passed"] for r in rows)}


def compare_v1(old, new):
    def metrics(row):
        estimates = row.get("preparation_metadata", row.get("observed", {}))
        return {
            "status": row.get("status"),
            "targets_passed": row.get("targets_passed"),
            "completion_passed": row.get("completion_passed"),
            "fit_attempted": row.get("fit_attempted"),
            "geometry_after_scoring": row.get("geometry_after_scoring"),
            "heldout_intensity_max_error": row.get("heldout_intensity_max_error"),
            "background_estimate": estimates.get("background_estimate"),
            "material_estimate": estimates.get("material_estimate"),
            "observed_contrast": estimates.get("observed_contrast"),
        }

    return {
        "name": new["name"],
        "lane": new["lane"],
        "v1_parsed_row_sha256": parsed_sha(old),
        "same_preserved_g_sha256": old.get("g_sha256") == new.get("g_sha256"),
        "v1": metrics(old),
        "v2": metrics(new),
        "v1_rerun": False,
    }


def failed_row(row, error, stage):
    """Retain safe provenance after failure; never turn nonfinite numbers into data.

    A field containing an unsafe payload is withheld in full and named explicitly.
    Independently valid fields remain available, but no prior pass flag survives.
    """
    safe = {}
    withheld = []
    for name, value in row.items():
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            withheld.append(name)
        else:
            safe[name] = value
    safe.update(
        status="execution_failure",
        failure_stage=stage,
        error={"type": type(error).__name__, "message": str(error)},
        completion_passed=False,
        targets_passed=False,
    )
    if withheld:
        safe["withheld_non_json_fields"] = withheld
    return safe


def run_study(plan, *, core=None, helper=None):
    import numpy as np

    start = time.perf_counter()
    manifest, baseline, moments, v1 = load_inputs(plan)
    before = source_hashes(plan, manifest)
    sys.path.insert(0, str(ROOT))
    if core is None:
        from backend import finite_centre_fit as core
    if helper is None:
        from backend import finite_observations as helper
    oracle = load_module(
        "_independent_area_photo_v2", ROOT / "studies/verification/finite-free-centre-v1.py"
    )
    oracle_plan = strict_json(ROOT / "studies/finite-free-centre-v1.json")
    metadata = {r["name"]: r for r in manifest["measurements"]}
    nominal = {
        r["name"]: r
        for r in moments["rows"]
        if r.get("roi_sigmas") == 8 and r.get("background_offset") == 0
    }
    original_by_name = {r["case"]["name"]: r for r in baseline["rows"]}
    v1_rows = {(r["name"], r["lane"]): r for r in v1["rows"]}
    rows = []
    controls = []
    for name in plan["cases"]:
        original = original_by_name[name]
        measured = original.get("measurements", {})
        context = None
        preparation_error = None
        try:
            if name not in metadata or not measured.get("rings"):
                preparation_error = (
                    "upstream_ineligible",
                    original.get("error", "no preserved field/ring"),
                )
            else:
                item = metadata[name]
                path = FIXTURES / item["file"]
                with np.load(path, allow_pickle=False) as archive:
                    field = archive["g"].copy()
                    points = archive["points"].copy()
                if (
                    hashlib.sha256(field.tobytes()).hexdigest() != item["g_sha256"]
                    or hashlib.sha256(points.tobytes()).hexdigest() != item["points_sha256"]
                ):
                    raise ValueError("decoded field/ring differs from portable manifest")
                outer = next(i for i, r in enumerate(measured["rings"]) if r["outer"])
                prims = measured["initial_fits"][outer]
                n, normal_record = observed_normal(prims, np)
                scalar = float(measured["sigma"])
                covariances = {plan["lanes"][0]: covariance_record(np.eye(2) * scalar**2, np)}
                if name in nominal and "covariance" in nominal[name]:
                    covariances[plan["lanes"][1]] = covariance_record(
                        nominal[name]["covariance"], np
                    )
                else:
                    covariances[plan["lanes"][1]] = {
                        "valid": False,
                        "reason": "nominal moment covariance absent",
                    }
                common = max(
                    scalar,
                    math.sqrt(covariances[plan["lanes"][1]]["eigenvalues"][-1])
                    if covariances[plan["lanes"][1]]["valid"]
                    else scalar,
                )
                observed = prepare(helper, field, points, n, common)
                context = {
                    "field": field,
                    "points": points,
                    "primitives": prims,
                    "observed": observed,
                    "normal_record": normal_record,
                    "covariances": covariances,
                    "common_sigma": common,
                    "item": item,
                }
        except helper.ObservationPreparationError as error:
            preparation_error = (
                "observed_seed_ineligible",
                {"reason": error.reason, "message": str(error)},
            )
        except Exception as error:  # noqa: BLE001 - preserve every planned lane after input/preparation failure
            preparation_error = (
                "execution_failure",
                {"type": type(error).__name__, "message": str(error)},
            )
        # A diagnostic control failure is retained separately. It cannot change
        # which successfully prepared observations reach either planned fit.
        if context is not None and preparation_error is None:
            try:
                control = observation_controls(
                    name,
                    context["field"],
                    context["points"],
                    context["primitives"],
                    context["observed"],
                    context["common_sigma"],
                    context["covariances"],
                    helper,
                    core,
                    oracle,
                    oracle_plan,
                    np,
                )
                json.dumps(control, allow_nan=False)
                controls.append(control)
            except Exception as error:  # noqa: BLE001 - controls must not suppress eligible fits
                controls.append(
                    {
                        "name": name,
                        "status": "execution_failure",
                        "error": {"type": type(error).__name__, "message": str(error)},
                        "checks": [],
                        "all_passed": False,
                    }
                )
        for lane in plan["lanes"]:
            started = time.perf_counter()
            row = {
                "index": len(rows),
                "name": name,
                "lane": lane,
                "targets_passed": False,
                "completion_passed": False,
                "fit_attempted": False,
            }
            stage = "preparation_result"
            try:
                if preparation_error:
                    row.update(status=preparation_error[0], reason=preparation_error[1])
                else:
                    observed = context["observed"]
                    field = context["field"]
                    cov = context["covariances"][lane]
                    row.update(
                        g_shape=list(field.shape),
                        g_dtype=field.dtype.str,
                        g_sha256=hashlib.sha256(field.tobytes()).hexdigest(),
                        capture_path=str((FIXTURES / context["item"]["file"]).relative_to(ROOT)),
                        capture_sha256=context["item"]["file_sha256"],
                        ppm=float(measured["ppm"]),
                        captured_scalar_sigma=float(measured["sigma"]),
                        common_sigma=context["common_sigma"],
                        initial_primitive_kinds=[p["kind"] for p in context["primitives"]],
                        normal_from_observations=context["normal_record"],
                        covariance_record=cov,
                        observed=snapshot(observed),
                        preparation_metadata=observed.metadata(),
                    )
                    if not cov["valid"]:
                        row.update(status="covariance_ineligible", reason=cov.get("reason"))
                    else:
                        row["fit_attempted"] = True
                        stage = "inverse_fit"
                        fit = core.fit_circular_segment(
                            observed.training_pixels,
                            observed.training_values,
                            sensor_shape=observed.field.shape,
                            homography=observed.homography,
                            psf_covariance=np.asarray(cov["canonical"]),
                            normal=observed.normal,
                            **observed.bounds,
                            **plan["fit_settings"],
                        )
                        stage = "fit_payload"
                        row.update(status="fit_completed", fit=asdict(fit))
                        if fit.best is not None:
                            best = fit.best
                            stage = "heldout_forward"
                            prediction = core.circular_segment_probabilities(
                                observed.heldout_pixels,
                                best.radius,
                                best.chord_fraction,
                                centre=best.centre,
                                normal=observed.normal,
                                sensor_shape=observed.field.shape,
                                homography=observed.homography,
                                psf_covariance=np.asarray(cov["canonical"]),
                                probability_tolerance=plan["fit_settings"]["probability_tolerance"],
                            )
                            row["heldout_forward"] = asdict(prediction)
                            held_ok = all(s == "resolved" for s in prediction.statuses)
                            if held_ok:
                                stage = "heldout_scoring"
                                means = best.levels[0] * (
                                    1 - np.asarray(prediction.probabilities)
                                ) + best.levels[1] * np.asarray(prediction.probabilities)
                                row["heldout_predicted_intensities"] = means.tolist()
                                row["heldout_intensity_max_error"] = float(
                                    np.max(abs(means - observed.heldout_values))
                                )
                            # Source truth is deliberately read ONLY after fit and heldout scoring.
                            stage = "truth_scoring"
                            baseline_plan = strict_json(ROOT / plan["inputs"]["baseline_plan"])
                            centre = np.asarray(baseline_plan["centre_mm"])
                            radius = float(original["case"]["radius"])
                            ppm = float(measured["ppm"])
                            row["truth_after_scoring"] = {
                                "centre_mm": centre.tolist(),
                                "radius_mm": radius,
                                "fraction": original["case"]["fraction"],
                            }
                            row["geometry_after_scoring"] = {
                                "centre_mm": (np.asarray(best.centre) / ppm).tolist(),
                                "radius_mm": best.radius / ppm,
                                "fraction": best.chord_fraction,
                                "centre_error_mm": float(
                                    np.linalg.norm(np.asarray(best.centre) / ppm - centre)
                                ),
                                "absolute_radius_error_mm": abs(best.radius / ppm - radius),
                                "absolute_fraction_error": abs(
                                    best.chord_fraction - original["case"]["fraction"]
                                ),
                            }
                            truth = [*(centre * ppm), radius * ppm, original["case"]["fraction"]]
                            boxes = [
                                *observed.centre_bounds,
                                observed.radius_bounds,
                                observed.chord_fraction_bounds,
                            ]
                            row["truth_in_observed_domain_after_scoring"] = all(
                                lo <= v <= hi for v, (lo, hi) in zip(truth, boxes, strict=True)
                            )
                            row["completion_passed"] = bool(
                                fit.geometry_rank == 4
                                and not (
                                    fit.work_exhausted
                                    or fit.refinement_limited
                                    or fit.unrefined_basins
                                    or fit.numerically_unsupported
                                    or fit.flat
                                    or fit.tied
                                    or fit.endpoint
                                    or fit.rank_deficient
                                )
                            )
                            row["targets_passed"] = bool(
                                row["completion_passed"]
                                and held_ok
                                and row["geometry_after_scoring"]["centre_error_mm"]
                                <= plan["targets"]["centre_error_mm"]
                                and row["geometry_after_scoring"]["absolute_radius_error_mm"]
                                <= plan["targets"]["absolute_radius_error_mm"]
                                and row["heldout_intensity_max_error"]
                                <= plan["targets"]["heldout_intensity_max_error"]
                            )
                stage = "strict_row_serialization"
                json.dumps(row, allow_nan=False)
            except Exception as error:  # noqa: BLE001 - retain every numerical/fitting failure
                row = failed_row(row, error, stage)
            row["runtime_seconds"] = time.perf_counter() - started
            rows.append(row)
            print(
                json.dumps(
                    {
                        "index": row["index"],
                        "name": name,
                        "lane": lane,
                        "status": row["status"],
                        "targets_passed": row["targets_passed"],
                    },
                    allow_nan=False,
                ),
                file=sys.stderr,
                flush=True,
            )
    paired = []
    for name in plan["cases"]:
        pair = [r for r in rows if r["name"] == name]
        available = all("observed" in r for r in pair)
        paired.append(
            {
                "name": name,
                "available": available,
                "shared_observation_exactly_equal": pair[0]["observed"] == pair[1]["observed"]
                if available
                else None,
            }
        )
    comparison = [compare_v1(v1_rows[r["name"], r["lane"]], r) for r in rows]
    after = source_hashes(plan, manifest)
    summary = {
        "declared_lanes": 12,
        "retained_lanes": len(rows),
        "fit_attempts": sum(r["fit_attempted"] for r in rows),
        "statuses": {
            s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})
        },
        "completed": sum(r["completion_passed"] for r in rows),
        "targets_passed": sum(r["targets_passed"] for r in rows),
        "observation_controls_all_passed": all(c["all_passed"] for c in controls),
        "paired_observations_all_identical": all(
            p["shared_observation_exactly_equal"] for p in paired if p["available"]
        ),
        "v1_rows_compared": len(comparison),
        "v1_targets_passed": sum(r["targets_passed"] for r in v1["rows"]),
    }
    return {
        "format": "pictures-to-cad-finite-photo-intensity-study",
        "version": 2,
        "scope": plan["scope"],
        "plan": plan,
        "plan_sha256": sha(PLAN),
        "runner_sha256": sha(RUNNER),
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "rows": rows,
        "paired_observations": paired,
        "observation_controls": controls,
        "comparison_to_all_v1_rows": comparison,
        "summary": summary,
        "runtime_seconds": time.perf_counter() - start,
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(arguments)
    try:
        output = args.output
        if (
            output.suffix.lower() != ".json"
            or output.exists()
            or output.is_symlink()
            or not output.parent.is_dir()
        ):
            raise ValueError("--output needs a NEW .json in an existing directory")
        result = run_study(strict_json(PLAN))
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        with output.open("x") as stream:
            stream.write(encoded)
        print(encoded, end="")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return (
        0
        if (
            result["source_unchanged"]
            and result["summary"]["targets_passed"] == 12
            and result["summary"]["observation_controls_all_passed"]
            and result["summary"]["paired_observations_all_identical"]
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
