#!/usr/bin/env python3
"""Read saved qualification reports with stdlib only; never import a fitter.

This is an independent arithmetic/accounting audit, not optical ground truth,
a timing run, proof of host quietness, or a replacement for any retained miss.
An internally consistent report may still miss either performance goal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN_NAME = "studies/finite-affine-batch-v1.json"
RUNNER_NAME = "studies/verification/finite-affine-batch-v1.py"
EPS = sys.float_info.epsilon
FLAGS = (
    "flat", "tied", "endpoint", "rank_deficient", "geometry_rank",
    "work_exhausted", "refinement_limited", "unrefined_basins", "numerically_unsupported",
)
CLOCKS = {
    "runtime_seconds", "seconds", "inclusive_seconds", "exclusive_seconds",
    "fit_seconds", "remaining_validation_search_refinement_seconds",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parsed_sha(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key: " + key)
            result[key] = value
        return result

    def number(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("nonfinite JSON number")
        return result

    def reject(value):
        raise ValueError("invalid JSON constant: " + value)

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=reject)


def close(a, b):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=128 * EPS, abs_tol=128 * EPS)


def maximum_delta(a, b):
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        if len(a) != len(b):
            raise ValueError("array lengths differ")
        return max((maximum_delta(x, y) for x, y in zip(a, b)), default=0.0)
    return abs(a - b)


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(item) for item in value.values())
    if isinstance(value, list):
        return all(finite_tree(item) for item in value)
    return not isinstance(value, float) or math.isfinite(value)


def resolved(result):
    statuses = result.get("statuses", [])
    values = result.get("probabilities", result.get("jacobian", []))
    return bool(statuses) and len(values) == len(statuses) and all(
        s == "resolved" and value is not None for s, value in zip(statuses, values)
    )


def flags(fit):
    return {name: fit.get(name) for name in FLAGS}


def completion(fit, family):
    complete = fit.get("best") is not None and not any(fit.get(name) for name in (
        "work_exhausted", "refinement_limited", "unrefined_basins", "numerically_unsupported",
    ))
    if family == "photo_v2":
        complete = complete and fit.get("geometry_rank") == 4 and not any(
            fit.get(name) for name in ("flat", "tied", "endpoint", "rank_deficient")
        )
    return bool(complete)


def strip_clocks(value):
    if isinstance(value, dict):
        return {k: strip_clocks(v) for k, v in value.items() if k not in CLOCKS}
    if isinstance(value, list):
        return [strip_clocks(v) for v in value]
    return value


def mapped(point, h):
    q = [math.fsum(a * b for a, b in zip(row, (*point, 1.0))) for row in h]
    return q[0] / q[2], q[1] / q[2]


def operator_norm_at(point, h):
    q = [math.fsum(a * b for a, b in zip(row, (*point, 1.0))) for row in h]
    a, b = [(h[0][j] * q[2] - q[0] * h[2][j]) / q[2] ** 2 for j in (0, 1)]
    c, d = [(h[1][j] * q[2] - q[1] * h[2][j]) / q[2] ** 2 for j in (0, 1)]
    # Eigenvalue of J.T J, written using its two diagonal entries and off-diagonal.
    u, v, w = a*a + c*c, b*b + d*d, a*b + c*d
    return math.sqrt((u + v + math.hypot(u - v, 2*w)) / 2)


def original_geometry(config, best):
    a, b = mapped(best["centre"], config["homography"]), mapped(
        config["centre"], config["homography"],
    )
    return {
        "centre_error_observation_px": math.hypot(a[0] - b[0], a[1] - b[1]),
        "radius_error_times_local_H_operator_norm_px": abs(
            best["radius"] - config["radius"]
        ) * operator_norm_at(config["centre"], config["homography"]),
        "fraction_error": abs(best["chord_fraction"] - config["fraction"]),
    }


def photo_geometry(archived, best):
    ppm, truth = archived["ppm"], archived["truth_after_scoring"]
    centre = [v / ppm for v in best["centre"]]
    return {
        "centre_error_mm": math.hypot(*(a-b for a, b in zip(centre, truth["centre_mm"]))),
        "absolute_radius_error_mm": abs(best["radius"] / ppm - truth["radius_mm"]),
    }


class Audit:
    def __init__(self):
        self.checks = []

    def check(self, name, passed, **detail):
        self.checks.append({"name": name, "passed": bool(passed), **detail})

    def section(self, name, callback):
        try:
            return callback()
        except Exception as error:
            self.check(name + "/audit_exception", False,
                       error={"type": type(error).__name__, "message": str(error)})
            return None


def source_audit(audit, report, plan, expected_plan, expected_runner):
    before, after = report["source_before"], report["source_after"]
    audit.check("binding/frozen_plan", sha(ROOT / PLAN_NAME) == expected_plan
                and report["plan"] == plan and before.get(PLAN_NAME) == expected_plan)
    audit.check("binding/frozen_runner", sha(ROOT / RUNNER_NAME) == expected_runner
                and before.get(RUNNER_NAME) == expected_runner)
    audit.check("binding/before_after", before == after and report["source_unchanged"] is True)
    required = set(plan["input_sha256"]) | set(
        plan["baseline_comparator"]["shared_dependency_sha256"]
    ) | {
        "backend/finite_affine.py", "backend/finite_centre_fit.py", "backend/finite_shape.py",
        "backend/finite_observations.py", "backend/reference.py", "backend/edges.py",
        "backend/sheet.py", "backend/tone.py", "pyproject.toml", PLAN_NAME, RUNNER_NAME,
    }
    audit.check("binding/closure_members", set(before) == required,
                missing=sorted(required - set(before)), extra=sorted(set(before) - required))
    changed = []
    for name, expected in before.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or sha(ROOT / path) != expected:
            changed.append(name)
    audit.check("binding/current_files", not changed, changed=changed)
    for name, expected in {
        **plan["input_sha256"], **plan["baseline_comparator"]["shared_dependency_sha256"],
    }.items():
        audit.check("binding/frozen_input/" + name, before.get(name) == expected)
    audit.check("binding/integrated_sheet", before.get("backend/sheet.py") ==
                plan["integration_refreeze"]["candidate_sheet_sha256"])
    audit.check("binding/strict_json_finite", finite_tree(report))
    original_sources = {
        "backend/finite_centre_fit.py": sha(ROOT / "studies/fixtures/finite-affine-batch-v1/original-finite-centre-fit.py.txt"),
        "backend/finite_shape.py": sha(ROOT / "studies/fixtures/finite-affine-batch-v1/original-finite-shape.py.txt"),
        "backend/sheet.py": sha(ROOT / "studies/fixtures/finite-affine-batch-v1/original-sheet.py.txt"),
        **{k: v for k, v in plan["baseline_comparator"]["shared_dependency_sha256"].items()
           if k.startswith("backend/")},
    }
    for name in ("finite-free-centre-v1", "finite-photo-intensity-v2"):
        old = read(ROOT / ("studies/results/" + name + ".json"))
        audit.check("binding/archive_original_stack/" + name,
                    old["source_unchanged"] is True and all(
                        old["source_before"].get(k) == old["source_after"].get(k) == v
                        for k, v in original_sources.items()))


def operator_audit(audit, report, plan):
    rows, cases = report["operator_cases"], plan["operator_cases"]
    audit.check("operators/population", len(rows) == len(cases) == 16 and
                [r["name"] for r in rows] == [c["name"] for c in cases])
    outcomes = []
    limits = plan["numerical_controls"]
    for row, case in zip(rows, cases):
        name = "operators/" + case["name"]
        a, b = row["original"], row["candidate"]
        parity = maximum_delta(a["probabilities"], b["probabilities"])
        low = row["independent_low_means"]
        high = row["independent_high_means"]
        order = maximum_delta(low, high)
        error = maximum_delta([255*p for p in b["probabilities"]], high)
        base_b = {k: v for k, v in b.items() if k != "diagnostics"}
        fallback = case.get("expected_path") == "scalar_projective"
        passed = resolved(a) and resolved(b) and parity <= limits[
            "scalar_batch_probability_max_delta"
        ] and error <= limits["independent_max_level_error"] and order <= limits[
            "independent_max_level_order_delta"
        ] and (not fallback or (a == base_b and b["diagnostics"]["batched_queries"] == 0))
        audit.check(name + "/deltas", close(parity, row["maximum_probability_delta"])
                    and close(order, row["independent_level_order_delta"])
                    and close(error, row["maximum_independent_level_error"]))
        audit.check(name + "/reported_pass", passed == row["passed"])
        audit.check(name + "/qualified", passed)
        outcomes.append(passed)
    audit.check("operators/summary", report["summary"]["operator_cases"] == 16
                and report["summary"]["operator_passes"] == sum(outcomes))
    return outcomes


def resource_audit(audit, report, plan):
    rows, controls = report["resource_controls"], plan["resource_controls"]
    audit.check("resources/population", len(rows) == len(controls) == 6 and
                [r["name"] for r in rows] == [c["name"] for c in controls])
    outcomes = []
    for row, control in zip(rows, controls):
        name = "resources/" + control["name"]
        count = control.get("query_count", 56)
        if count > 2048:
            passed = row["status"] == "refusal_control" and row["refused"] == [True, True]
        else:
            settings = {**plan["numerical_controls"], **control.get("settings", {})}
            work_limit = 1 if count >= 2048 else settings["max_evaluations"]
            b, d = row["candidate"], row["candidate"]["diagnostics"]
            retained = len(b["probabilities"]) == len(b["statuses"]) == count and all(
                (value is not None) == (status == "resolved")
                for value, status in zip(b["probabilities"], b["statuses"])
            )
            bounded = b["evaluations"] <= work_limit and d["workspace_peak_bytes"] <= d[
                "memory_limit_bytes"
            ]
            accounting = b["evaluations"] == d["batch_evaluations"] + d[
                "fallback_evaluations"
            ] and b["panels"] == d["batch_panels"] + d["fallback_panels"] and d[
                "batched_queries"
            ] + d["fallback_queries"] == count and b["panels"] <= count * settings["max_panels"]
            audit.check(name + "/accounting", accounting)
            audit.check(name + "/stored_components", row["retained"] == retained
                        and row["bounded"] == bounded)
            passed = retained and bounded
        audit.check(name + "/reported_pass", passed == row["passed"])
        audit.check(name + "/qualified", passed)
        outcomes.append(passed)
    audit.check("resources/summary", report["summary"]["resource_controls"] == 6
                and report["summary"]["resource_passes"] == sum(outcomes))
    return outcomes


def derivative_audit(audit, report, plan):
    rows, names = report["derivative_controls"], plan["derivative_controls"]["cases"]
    audit.check("derivatives/population", len(rows) == len(names) == 6
                and [r["name"] for r in rows] == names)
    outcomes = []
    for row in rows:
        name = "derivatives/" + row["name"]
        low, high = row["independent_h_jacobian"], row["independent_half_h_jacobian"]
        delta = maximum_delta(low, high)
        error = maximum_delta(row["candidate"]["jacobian"], high)
        passed = resolved(row["original"]) and resolved(row["candidate"]) and error <= plan[
            "derivative_controls"
        ]["maximum_absolute_column_error"] and delta <= plan[
            "derivative_controls"
        ]["maximum_h_vs_half_h_delta"]
        audit.check(name + "/deltas", close(error, row["maximum_independent_derivative_error"])
                    and close(delta, row["maximum_h_half_h_delta"]))
        audit.check(name + "/reported_pass", passed == row["passed"])
        audit.check(name + "/qualified", passed)
        outcomes.append(passed)
    audit.check("derivatives/summary", report["summary"]["derivative_controls"] == 6
                and report["summary"]["derivative_passes"] == sum(outcomes))
    return outcomes


def datasets():
    original = read(ROOT / "studies/results/finite-free-centre-v1.json")
    photo = read(ROOT / "studies/results/finite-photo-intensity-v2.json")
    source_plan = read(ROOT / "studies/finite-free-centre-v1.json")
    photo_plan = read(ROOT / "studies/finite-photo-intensity-v2.json")
    result = []
    for family, rows in (("original24", original["cases"]), ("photo_v2", photo["rows"])):
        for row in rows:
            eligible = "observed_values_training" in row if family == "original24" else bool(
                row.get("fit_attempted")
            )
            data = {"family": family, "name": row["name"], "lane": row["lane"],
                    "archived": row, "eligible": eligible}
            if eligible:
                obs = row["observed"]
                if family == "original24":
                    cfg = row["config"]
                    angle = math.radians(cfg["normal_degrees"])
                    args = {
                        "sensor_shape": cfg["sensor_shape"], "homography": cfg["homography"],
                        "normal": [math.cos(angle), math.sin(angle)],
                        "psf_covariance": cfg.get("fit_covariance", cfg["covariance"]),
                        **obs["bounds"], **source_plan["fit_settings"],
                        **cfg.get("fit_settings", {}),
                    }
                    train, held = row["observed_values_training"], row["observed_values_heldout"]
                    injection = cfg.get("injection")
                else:
                    args = {
                        "sensor_shape": obs["field_shape"], "homography": obs["homography"],
                        "normal": obs["normal"],
                        "psf_covariance": row["covariance_record"]["canonical"],
                        **obs["bounds"], **photo_plan["fit_settings"],
                    }
                    train, held = obs["training_values"], obs["heldout_values"]
                    injection = None
                data["fit_input"] = {
                    "training_pixels": obs["training_pixels"],
                    "training_values": [float(v) for v in train],
                    "heldout_pixels": obs["heldout_pixels"],
                    "heldout_values": [float(v) for v in held],
                    "arguments": args, "planned_injection": injection,
                }
            result.append(data)
    return result, source_plan, photo_plan


def replay_audit(audit, report):
    expected, source_plan, photo_plan = datasets()
    rows = report["optimizer_replay"]
    identity = lambda r: (r["family"], r["name"], r["lane"])
    audit.check("replay/population", len(rows) == len(expected) == 36
                and list(map(identity, rows)) == list(map(identity, expected)))
    eligible_count = sum(d["eligible"] for d in expected)
    audit.check("replay/eligible32", eligible_count == 32
                and sum(bool(r.get("fit_attempted")) for r in rows) == 32)
    changed_flags, old_passes, new_passes = [], {"original24": 0, "photo_v2": 0}, {
        "original24": 0, "photo_v2": 0,
    }
    by_identity = {}
    for row, data in zip(rows, expected):
        name = "replay/" + "/".join(identity(data))
        archived, family = data["archived"], data["family"]
        audit.check(name + "/archive_binding", row["archived_parsed_row_sha256"] == parsed_sha(archived))
        audit.check(name + "/archived_status", row["archived_status"] == archived["status"])
        if not data["eligible"]:
            audit.check(name + "/original_refusal", not row["fit_attempted"]
                        and row["status"] == archived["status"]
                        and row["reason"] == archived.get("reason")
                        and row["retained_original_outcome"] is True)
            continue
        audit.check(name + "/frozen_input", row["fit_input"] == data["fit_input"]
                    and row["fit_input_sha256"] == parsed_sha(data["fit_input"]))
        fit, original_fit = row["fit"], archived["fit"]
        complete = completion(fit, family)
        audit.check(name + "/completion", row["completion_passed"] == complete)
        geometry = None
        held_error = None
        passed = False
        if fit["best"] is not None:
            best = fit["best"]
            if family == "original24":
                geometry = original_geometry(archived["config"], best)
                predictions = row["heldout_predicted_levels"]
                held_error = maximum_delta(predictions, data["fit_input"]["heldout_values"])
                target = source_plan["matched_targets"]
                passed = complete and all(geometry[k] <= target[k] for k in geometry) and (
                    held_error <= target["heldout_level_max_error"]
                ) and archived["oracle"]["passed"]
            else:
                geometry = photo_geometry(archived, best)
                forward = row["heldout_forward"]
                if resolved(forward):
                    levels = best["levels"]
                    predictions = [levels[0] * (1-p) + levels[1] * p
                                   for p in forward["probabilities"]]
                    held_error = maximum_delta(predictions, data["fit_input"]["heldout_values"])
                    audit.check(name + "/saved_predictions", maximum_delta(
                        predictions, row["heldout_predicted_levels"]
                    ) <= 128 * EPS * max(1, *(abs(v) for v in predictions)))
                    target = photo_plan["targets"]
                    passed = complete and all(geometry[k] <= target[k] for k in geometry) and (
                        held_error <= target["heldout_intensity_max_error"]
                    )
        if geometry is not None:
            audit.check(name + "/geometry_arithmetic", all(
                close(value, row["geometry"][key]) for key, value in geometry.items()
            ))
        if held_error is not None:
            audit.check(name + "/heldout_arithmetic", close(held_error, row["heldout_level_max_error"]))
        if family == "original24" and row["lane"] != "matched":
            passed = None
        passed = bool(passed) if passed is not None else None
        audit.check(name + "/target_recomputed", row["targets_passed"] is passed)
        old_key = "matched_targets_passed" if family == "original24" else "targets_passed"
        old_target = archived.get(old_key)
        old_geometry = None
        if original_fit.get("best") is not None:
            old_geometry = original_geometry(archived["config"], original_fit["best"]) if (
                family == "original24"
            ) else photo_geometry(archived, original_fit["best"])
        old_complete = completion(original_fit, family)
        old_recomputed = False
        if old_geometry is not None:
            if family == "original24":
                target = source_plan["matched_targets"]
                # Archive did not retain its independent predictions. This one
                # historical scalar is source-bound evidence, not re-created truth.
                old_recomputed = old_complete and all(old_geometry[k] <= target[k] for k in old_geometry)
                old_recomputed = old_recomputed and archived.get("heldout_level_max_error", math.inf) <= target["heldout_level_max_error"] and archived["oracle"]["passed"]
            else:
                old_forward = archived["heldout_forward"]
                if resolved(old_forward):
                    levels = original_fit["best"]["levels"]
                    old_predictions = [levels[0] * (1-p) + levels[1] * p
                                       for p in old_forward["probabilities"]]
                    old_error = maximum_delta(old_predictions, data["fit_input"]["heldout_values"])
                    audit.check(name + "/archive_heldout_arithmetic", close(
                        old_error, archived["heldout_intensity_max_error"]
                    ) and maximum_delta(old_predictions, archived["heldout_predicted_intensities"]) <= 128 * EPS * max(1, *(abs(v) for v in old_predictions)))
                    target = photo_plan["targets"]
                    old_recomputed = old_complete and all(old_geometry[k] <= target[k] for k in old_geometry) and old_error <= target["heldout_intensity_max_error"]
        if family == "original24" and row["lane"] != "matched":
            old_recomputed = None
        else:
            old_recomputed = bool(old_recomputed)
        audit.check(name + "/archive_target_recomputed", old_target is old_recomputed)
        old_passes[family] += old_target is True
        new_passes[family] += passed is True
        previous_preserved = old_target is not True or passed is True
        audit.check(name + "/previous_pass_preserved", previous_preserved)
        comparison = row["comparison"]
        same_flags = flags(original_fit) == flags(fit)
        audit.check(name + "/comparison", comparison["before_flags"] == flags(original_fit)
                    and comparison["after_flags"] == flags(fit)
                    and comparison["all_flags_equal"] == same_flags
                    and comparison["previous_pass_preserved"] == previous_preserved
                    and comparison["archived_fit_sha256"] == parsed_sha(original_fit)
                    and comparison["current_fit_sha256"] == parsed_sha(fit))
        old_best, new_best = original_fit.get("best"), fit.get("best")
        deltas = None
        if old_best is not None and new_best is not None:
            deltas = {"centre_components": [b-a for a, b in zip(old_best["centre"], new_best["centre"])],
                      "radius": new_best["radius"]-old_best["radius"],
                      "fraction": new_best["chord_fraction"]-old_best["chord_fraction"],
                      "levels": [b-a for a, b in zip(old_best["levels"], new_best["levels"])],
                      "cost": new_best["cost"]-old_best["cost"]}
        audit.check(name + "/parameter_deltas", comparison["best_parameter_deltas"] == deltas)
        audit.check(name + "/previous_pass_semantics", row["passed"] is previous_preserved
                    and comparison["archived_targets_passed"] is old_target)
        if not same_flags:
            changed_flags.append({"identity": identity(row), "before": flags(original_fit),
                                  "after": flags(fit)})
        by_identity[identity(row)] = {"row": row, "data": data}
    audit.check("replay/archive_previous12plus3", old_passes == {"original24": 12, "photo_v2": 3})
    audit.check("replay/summary_counts", report["summary"]["original_matched_target_passes"] ==
                new_passes["original24"] and report["summary"]["photo_v2_target_passes"] == new_passes["photo_v2"])
    audit.check("replay/summary_flags", report["summary"]["all_archived_completion_flags_equal"] is
                (not changed_flags) and report["summary"]["previous_accuracy_passes_preserved"] is
                all(r["passed"] for r in rows))
    return {"eligible": eligible_count, "old_target_passes": old_passes,
            "new_target_passes": new_passes, "changed_flags": changed_flags,
            "by_identity": by_identity,
            "historical_original24_heldout_scope": "Archived scalar error retained; original archive did not save its independent predicted levels. Candidate prediction deltas and all photo archive predictions are recomputed from saved arrays."}


def cpu_qualified(report, plan):
    env = report["environment"]
    before, after = env.get("affinity_before"), env.get("affinity_after")
    threads = env.get("thread_environment", {})
    return bool(before and after == [min(before)] and not env.get("affinity_errors")
                and threads == plan["timing"]["environment_before_numpy"]
                and all(value == "1" for value in threads.values()))


def group_times(audit, name, row, repeats, warmups, *, family=None, accuracy_fit=None):
    measurements = row["measurements"]
    audit.check(name + "/all_samples", len(measurements) == 2 * (repeats + warmups))
    timed = [r for r in measurements if not r["warmup"]]
    expected_order = [label for i in range(repeats) for label in (
        ("original", "candidate") if i % 2 == 0 else ("candidate", "original")
    )]
    audit.check(name + "/timed_order", [r["method"] for r in timed] == expected_order
                and [r["repeat"] for r in timed] == [i for i in range(repeats) for _ in range(2)])
    first, all_returned, all_ready, all_consistent = {}, True, True, True
    for item in measurements:
        label = item["method"]
        valid = item["status"] == "returned" and isinstance(item.get("seconds"), (int, float))
        valid = valid and math.isfinite(item["seconds"]) and item["seconds"] > 0
        all_returned = all_returned and valid
        ready, consistent = False, False
        if valid:
            result = item["result"]
            ready = completion(result, family) if family else resolved(result)
            if label not in first:
                first[label] = result
            reference = accuracy_fit if family and label == "candidate" else first[label]
            consistent = result == reference and ready
            audit.check(name + "/return_quality/" + label + "/" + str(item["repeat"]),
                        item["required_return_quality"] is ready)
            if family:
                audit.check(name + "/reference_equality/" + label + "/" + str(item["repeat"]),
                            item["same_complete_fit_reference"] is consistent)
        all_ready = all_ready and ready
        all_consistent = all_consistent and consistent
    qualified = all_returned and all_ready
    audit.check(name + "/return_quality_flags", row["all_calls_returned"] is all_returned
                and row["all_required_return_quality_passed"] is qualified)
    medians = {}
    for label in ("original", "candidate"):
        values = [r["seconds"] for r in timed if r["method"] == label and r["status"] == "returned"]
        medians[label] = statistics.median(values) if len(values) == repeats else None
        audit.check(name + "/median/" + label, close(medians[label], row["medians"][label]))
    raw = medians["original"] / medians["candidate"] if all_returned else None
    ratio = raw if qualified else None
    audit.check(name + "/ratios", close(raw, row["raw_median_speedup"])
                and close(ratio, row["median_speedup"]))
    if family:
        final_ratio = ratio if completion(accuracy_fit, family) and all_consistent else None
        audit.check(name + "/complete_fit_consistency", row["all_fit_outputs_consistent"] is all_consistent
                    and row["candidate_accuracy_replay_fit_sha256"] == parsed_sha(accuracy_fit)
                    and row["original_warmup_fit_sha256"] == parsed_sha(first.get("original"))
                    and close(final_ratio, row["qualified_median_speedup"]))
        ratio = final_ratio
    return {"qualified": ratio, "raw": raw, "all_returned": all_returned,
            "all_ready": qualified, "all_fit_outputs_consistent": all_consistent if family else None,
            "sample_count": len(measurements)}


def timing_audit(audit, report, plan, replay):
    cpu = cpu_qualified(report, plan)
    audit.check("timing/fixed_cpu_metadata", report["environment"]["fixed_cpu_timing_qualified"] is cpu
                and report["summary"]["fixed_cpu_timing_qualified"] is cpu)
    kernel = report["kernel_timings"]
    expected_ids = [(r["case"], r["lane"], n, method)
                    for r in plan["timing"]["representative_cases"]
                    for n in plan["timing"]["query_counts"]
                    for method in ("mean", "direct_shape_jacobian")]
    audit.check("timing/kernel_population", len(kernel) == 12 and [
        (r["name"], r["lane"], r["query_count"], r["method"]) for r in kernel
    ] == expected_ids)
    mean_ratios, all_groups = [], []
    for row in kernel:
        name = "timing/kernel/" + "/".join(map(str, (
            row["name"], row["lane"], row["query_count"], row["method"],
        )))
        ratio = group_times(audit, name, row, plan["timing"]["paired_timed_repeats"],
                            plan["timing"]["warmup_calls_each"])
        all_groups.append(ratio)
        if row["method"] == "mean":
            mean_ratios.append(ratio)
    fits = report["fit_timings"]
    expected_fit_ids = [(r["case"], r["lane"]) for r in plan["timing"]["representative_cases"]]
    audit.check("timing/fit_population", len(fits) == 3 and
                [(r["name"], r["lane"]) for r in fits] == expected_fit_ids)
    fit_ratios = []
    for row in fits:
        name = "timing/fit/" + row["name"] + "/" + row["lane"]
        actual = replay["by_identity"][("photo_v2", row["name"], row["lane"])]["row"]["fit"]
        result = group_times(audit, name, row, 3, 1, family="photo_v2", accuracy_fit=actual)
        fit_ratios.append(result)
        all_groups.append(result)
    entries = sum(len(r["measurements"]) for r in fits)
    audit.check("timing/24_real_fit_entries", entries == 24 and
                report["summary"]["timing_optimizer_entries"] == entries)
    audit.check("timing/56_total_entries", report["summary"]["optimizer_entries"] == 56
                and report["summary"]["actual_optimizers_executed"] == 56)
    def geomean(rows, key, count):
        values = [row[key] for row in rows]
        return math.exp(math.fsum(map(math.log, values)) / count) if (
            len(values) == count and all(v is not None and v > 0 for v in values)
        ) else None
    raw_means, raw_fitted = geomean(mean_ratios, "raw", 6), geomean(fit_ratios, "raw", 3)
    means = geomean(mean_ratios, "qualified", 6) if cpu else None
    fitted = geomean(fit_ratios, "qualified", 3) if cpu else None
    summary = report["summary"]
    audit.check("timing/mean_geomean", close(means, summary["mean_geometric_median_speedup"]))
    audit.check("timing/fit_geomean", close(fitted, summary["actual_fit_geometric_median_speedup"]))
    audit.check("timing/raw_geomeans", close(raw_means, summary["raw_mean_geometric_median_speedup"])
                and close(raw_fitted, summary["raw_actual_fit_geometric_median_speedup"]))
    all_returned = all(row["all_returned"] for row in all_groups)
    audit.check("timing/all_requested_calls_flag", summary["all_requested_timing_calls_returned"] is all_returned)
    mean_met = means >= plan["timing"]["mean_geometric_median_speedup_goal"] if means is not None else None
    fit_met = fitted >= plan["timing"]["actual_40_training_fit_geometric_median_speedup_goal"] if fitted is not None else None
    audit.check("timing/goal_booleans", summary["mean_speed_goal_met"] is mean_met
                and summary["actual_fit_speed_goal_met"] is fit_met)
    return {"mean_geomean": means, "fit_geomean": fitted, "mean_goal_met": mean_met,
            "fit_goal_met": fit_met, "raw_mean_geomean": raw_means, "raw_fit_geomean": raw_fitted,
            "fixed_cpu_qualified": cpu,
            "all_samples_retained": len(all_groups) == 15 and sum(r["sample_count"] for r in all_groups) == 216,
            "all_fit_outputs_consistent": all(r["all_fit_outputs_consistent"] for r in fit_ratios)}


def continuation_audit(audit, canonical, continuation):
    a, b = canonical["optimizer_replay"], continuation["optimizer_replay"]
    audit.check("continuation/population", len(a) == len(b) == 36)
    audit.check("continuation/source_closure", canonical["source_before"] == canonical["source_after"]
                == continuation["source_before"] == continuation["source_after"])
    first = b[0]
    audit.check("continuation/first_failure", first["status"] == "execution_failure"
                and not first["completion_passed"] and not first["targets_passed"]
                and not any(k in first for k in ("fit", "heldout_forward", "geometry")))
    audit.check("continuation/one_injection", continuation["first_fit_injection"]["injections"] == 1)
    for i, (old, new) in enumerate(zip(a[1:], b[1:]), 1):
        audit.check("continuation/later_row/" + str(i), strip_clocks(old) == strip_clocks(new))
    entry_audit(audit, continuation, injected=True, prefix="continuation/entries")


def entry_audit(audit, report, *, injected=False, prefix="entries"):
    expected, _, _ = datasets()
    identities = [(d["family"], d["name"], d["lane"], "candidate", "accuracy")
                  for d in expected if d["eligible"]]
    for group in report["fit_timings"]:
        identities.extend(("photo_v2", group["name"], group["lane"], item["method"],
                           "warmup" if item["warmup"] else "timed_repeat")
                          for item in group["measurements"])
    logs, summary = report["optimizer_entry_log"], report["summary"]
    audit.check(prefix + "/ordered_population", len(logs) == len(identities) and [
        (e["family"], e["name"], e["lane"], e["method"], e["purpose"]) for e in logs
    ] == identities)
    real, callable_count = 0, 0
    for index, entry in enumerate(logs):
        is_injected = injected and index == 0
        expected_real = not is_injected
        real += bool(entry["actual_real_fitter_entered"])
        callable_count += bool(entry["actual_callable_entered"])
        audit.check(prefix + "/record/" + str(index),
                    entry["actual_real_fitter_entered"] is expected_real
                    and entry["actual_callable_entered"] is expected_real
                    and entry["callable_name"] == "fit_circular_segment"
                    and entry["callable_module"].endswith("finite_centre_fit")
                    and (entry["status"] == "injected_before_real_core_entry" if is_injected
                         else entry["status"] == "returned"))
    timing_count = sum(e["purpose"] in {"warmup", "timed_repeat"} for e in logs)
    audit.check(prefix + "/summary", summary["optimizer_entries"] == len(logs)
                and summary["accuracy_replay_optimizer_entries"] == 32
                and summary["timing_optimizer_entries"] == timing_count
                and summary["actual_optimizers_executed"] == real
                and summary["actual_callable_entries"] == callable_count
                and summary["attempted_accuracy_dataset_entries"] == 32
                and summary["attempted_timing_dataset_entries"] == timing_count
                and summary["accuracy_replay_rows"] == 36)
    expected_timed = 24 if summary["timing_requested"] else 0
    audit.check(prefix + "/real_counts", len(logs) == 32 + expected_timed
                and real == 32 + expected_timed - int(injected)
                and callable_count == real and timing_count == expected_timed)


def failure_audit(audit, report):
    failures = []
    for section in ("operator_cases", "resource_controls", "derivative_controls", "optimizer_replay"):
        failures.extend((section, row) for row in report[section]
                        if row.get("status") == "execution_failure")
    for section in ("kernel_timings", "fit_timings"):
        for group in report[section]:
            failures.extend((section, row) for row in group.get("measurements", [])
                            if row.get("status") == "execution_failure")
    for index, (section, row) in enumerate(failures):
        withheld = row.get("withheld_non_json_fields", [])
        # Source policy strips only unsafe fields, resets pass flags, and leaves
        # safe diagnostic/context fields intact. No unsafe value can leak back.
        audit.check("failures/" + str(index), finite_tree(row)
                    and not any(row.get(k, False) for k in ("passed", "targets_passed", "completion_passed"))
                    and all(key not in row for key in withheld), section=section)
    audit.check("failures/strict_roundtrip", read_roundtrip(report) == report)


def read_roundtrip(value):
    return json.loads(json.dumps(value, allow_nan=False))


def audit_report(report, plan, expected_plan, expected_runner, continuation=None):
    audit = Audit()
    audit.section("source", lambda: source_audit(audit, report, plan, expected_plan, expected_runner))
    audit.section("operators", lambda: operator_audit(audit, report, plan))
    audit.section("resources", lambda: resource_audit(audit, report, plan))
    audit.section("derivatives", lambda: derivative_audit(audit, report, plan))
    replay = audit.section("replay", lambda: replay_audit(audit, report))
    audit.section("entries", lambda: entry_audit(audit, report))
    audit.section("failures", lambda: failure_audit(audit, report))
    performance = audit.section("timing", lambda: timing_audit(audit, report, plan, replay))
    if continuation is not None:
        audit.section("continuation", lambda: continuation_audit(audit, report, continuation))
        audit.section("continuation_failures", lambda: failure_audit(audit, continuation))
    controls = report["operator_cases"] + report["resource_controls"] + report["derivative_controls"]
    audit.check("summary/kernel_accuracy", report["summary"]["kernel_accuracy_passed"] is
                all(row["passed"] for row in controls))
    failures = [r for r in audit.checks if not r["passed"]]
    return {
        "format": "pictures-to-cad-independent-affine-report-audit", "version": 1,
        "scope": "Stdlib-only saved-data arithmetic/accounting audit; no numerical-module imports, fits, timing, optical truth or host-quietness proof. Performance misses remain misses even if report integrity passes.",
        "checks": audit.checks, "checks_passed": len(audit.checks) - len(failures),
        "checks_failed": len(failures), "all_integrity_checks_passed": not failures,
        "performance": performance,
        "replay": {k: v for k, v in (replay or {}).items() if k != "by_identity"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canonical", type=Path)
    parser.add_argument("--expected-plan-sha", required=True)
    parser.add_argument("--expected-runner-sha", required=True)
    parser.add_argument("--continuation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("fresh output in an existing directory required")
    report = read(args.canonical)
    plan = read(ROOT / PLAN_NAME)
    continuation = read(args.continuation) if args.continuation else None
    result = audit_report(report, plan, args.expected_plan_sha, args.expected_runner_sha, continuation)
    result.update(canonical_sha256=sha(args.canonical), plan_sha256=sha(ROOT / PLAN_NAME),
                  runner_sha256=sha(ROOT / RUNNER_NAME), auditor_sha256=sha(__file__))
    if args.continuation:
        result["continuation_sha256"] = sha(args.continuation)
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    with args.output.open("x") as stream:
        stream.write(encoded)
    print(encoded, end="")
    return 0 if result["all_integrity_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
