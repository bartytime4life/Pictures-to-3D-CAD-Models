#!/usr/bin/env python3
"""Prospective affine batch qualification; staged, bounded and source-bound.

Required fresh --output is checked before numerical imports. Kernel stage never
fits geometry. Complete stage additionally replays archived fixed observations;
it must be authorized separately by the study owner. Timing requires an explicit
quiet-interval declaration and is sequential, single-thread and single-CPU.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import math
import os
import platform
import statistics
import sys
import time
import types
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/finite-affine-batch-v1.json"
RUNNER = Path(__file__).resolve()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key:" + key)
            result[key] = value
        return result

    def reject(value):
        raise ValueError("nonfinite JSON value:" + value)

    def number(value):
        result = float(value)
        return result if math.isfinite(result) else reject(value)

    return json.loads(
        Path(path).read_text(), object_pairs_hook=pairs, parse_float=number, parse_constant=reject
    )


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def inputs(plan):
    for name, expected in plan["input_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("frozen input changed:" + name)
    for name, expected in plan["baseline_comparator"]["shared_dependency_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("shared original baseline dependency changed:" + name)
    expected_sheet = plan.get("integration_refreeze", {}).get("candidate_sheet_sha256")
    if expected_sheet and sha(ROOT / "backend/sheet.py") != expected_sheet:
        raise ValueError("candidate integrated sheet changed")


def closure(plan):
    names = {
        *plan["input_sha256"],
        *plan["baseline_comparator"]["shared_dependency_sha256"],
        "backend/finite_affine.py",
        "backend/finite_centre_fit.py",
        "backend/finite_shape.py",
        "backend/finite_observations.py",
        "backend/reference.py",
        "backend/edges.py",
        "backend/sheet.py",
        "backend/tone.py",
        "pyproject.toml",
        str(PLAN.relative_to(ROOT)),
        str(RUNNER.relative_to(ROOT)),
    }
    return {name: sha(ROOT / name) for name in sorted(names)}


def failure(identity, error, stage):
    return {
        **identity,
        "status": "execution_failure",
        "stage": stage,
        "error": {"type": type(error).__name__, "message": str(error)},
        "passed": False,
    }


def parsed_sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def safe_failure(row, error, stage):
    """Withhold unsafe fields explicitly; no stale pass flags or fake numbers."""
    safe, withheld = {}, []
    for key, value in row.items():
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            withheld.append(key)
        else:
            safe[key] = value
    safe.update(failure({}, error, stage), completion_passed=False, targets_passed=False)
    if withheld:
        safe["withheld_non_json_fields"] = withheld
    return safe


def append_checked(rows, row, stage):
    try:
        json.dumps(row, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as error:
        row = safe_failure(row, error, stage)
    rows.append(row)


def geometry(config, old, oracle, np):
    h, covariance = config["homography"], config["covariance"]
    if config.get("shape") == "rectangle":
        x0, y0, x1, y1 = config["rectangle_bounds"]
        points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        rings = [[("line", points[i], points[(i + 1) % 4]) for i in range(4)]]
        return old.finite._geometry(rings, h, covariance)
    n = oracle.normal(config)
    result = old._segment_geometry(
        config["radius"], config["fraction"], config["centre"], n, h, covariance
    )
    if config.get("source") == "hole":
        curves, _, _, _, _ = result
        extra = old.finite._Curve(
            np.asarray(config["hole_offset"], float),
            None,
            float(config["hole_radius"]),
            0.0,
            math.tau,
            -1.0,
        )
        return old.finite._geometry_curves(
            [*curves, extra], np.asarray(config["centre"]), h, covariance
        )
    return result


def queries(config, plan, oracle, np):
    base = config.get("query_base")
    if base is None:
        base = np.floor(oracle.mapped([config["centre"]], config["homography"])[0]).astype(int)
    xs = config.get("query_offsets_x", plan["queries"]["offsets_x"])
    ys = config.get("query_offsets_y", plan["queries"]["offsets_y"])
    result = np.array(
        [(int(base[0]) + x, int(base[1]) + y) for y in ys for x in xs], dtype=np.int64
    )
    height, width = config["sensor_shape"]
    if np.any(result < 0) or np.any(result[:, 0] >= width) or np.any(result[:, 1] >= height):
        raise ValueError("planned operator query outside sensor")
    return result


def numerical_settings(plan):
    return {
        key: plan["numerical_controls"][key]
        for key in ("probability_tolerance", "max_panels", "max_evaluations")
    }


def base_fields(result):
    data = asdict(result)
    data.pop("diagnostics", None)
    return data


def rectangle_means(points, config, oracle, np):
    x0, y0, x1, y1 = config["rectangle_bounds"]
    corners = oracle.mapped([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], config["homography"])
    low, high = corners.min(axis=0), corners.max(axis=0)
    sigma = np.sqrt(np.diag(config["covariance"]))
    mass = oracle.normal_mass((low - points) / sigma, (high - points) / sigma)
    return 255.0 * np.prod(mass, axis=1)


def operator_case(case, plan, old, batch, oracle, oracle_plan, np):
    identity = {"name": case["name"]}
    started = time.perf_counter()
    try:
        config = {**copy.deepcopy(plan["base"]), **copy.deepcopy(case["changes"])}
        config["shape"] = case.get("shape", "D")
        pixels = queries(config, plan, oracle, np)
        geo = geometry(config, old, oracle, np)
        settings = numerical_settings(plan)
        a = old.finite._probabilities(pixels, geo, **settings)
        b = batch._probabilities(pixels, geo, **settings)
        available = all(s == "resolved" for s in (*a.statuses, *b.statuses))
        if config["shape"] == "rectangle":
            lo = hi = rectangle_means(pixels + 0.5, config, oracle, np)
            oracle_kind = "exact separable Gaussian rectangle CDF product"
        else:
            lo, hi = [
                oracle.independent_means(pixels + 0.5, config, order, oracle_plan)
                for order in plan["numerical_controls"]["independent_orders"]
            ]
            oracle_kind = "independent positive conic vertical-slice erfc/GL32/64"
        delta = float(np.max(abs(hi - lo)))
        parity = (
            float(np.max(abs(np.asarray(a.probabilities) - np.asarray(b.probabilities))))
            if available
            else None
        )
        error = float(np.max(abs(255 * np.asarray(b.probabilities) - hi))) if available else None
        fallback = case.get("expected_path") == "scalar_projective"
        exact = base_fields(a) == base_fields(b)
        row = {
            **identity,
            "status": "evaluated",
            "config": config,
            "pixels": pixels.tolist(),
            "geometry_contract": "Exact local D C/R/f curves, contained circle hole, or closed rectangle; no new observation generation.",
            "original": asdict(a),
            "candidate": asdict(b),
            "all_resolved": available,
            "maximum_probability_delta": parity,
            "independent_oracle": oracle_kind,
            "independent_level_order_delta": delta,
            "independent_low_means": lo.tolist(),
            "independent_high_means": hi.tolist(),
            "maximum_independent_level_error": error,
            "expected_scalar_fallback": fallback,
            "original_fields_exactly_equal": exact,
            "passed": bool(
                available
                and parity <= plan["numerical_controls"]["scalar_batch_probability_max_delta"]
                and error <= plan["numerical_controls"]["independent_max_level_error"]
                and delta <= plan["numerical_controls"]["independent_max_level_order_delta"]
                and (not fallback or (exact and b.diagnostics.batched_queries == 0))
            ),
        }
        json.dumps(row, allow_nan=False)
    except Exception as error:  # noqa: BLE001 - preserve each prospectively declared case
        row = failure(identity, error, "operator")
    row["runtime_seconds"] = time.perf_counter() - started
    return row


def resources(plan, old, batch, oracle, np):
    config = copy.deepcopy(plan["base"])
    source = old.circular_segment_ring(
        config["radius"], config["fraction"], centre=config["centre"], normal=oracle.normal(config)
    )
    settings = numerical_settings(plan)
    kwargs = {
        "sensor_shape": config["sensor_shape"],
        "homography": config["homography"],
        "psf_covariance": config["covariance"],
    }
    rows = []
    for control in plan["resource_controls"]:
        identity = {"name": control["name"]}
        count = control.get("query_count", 56)
        pixels = (
            queries(config, plan, oracle, np)
            if count == 56
            else np.array([(i % 64, i // 64) for i in range(count)], int)
        )
        limits = {**settings, **control.get("settings", {})}
        if count >= 2048:
            limits["max_evaluations"] = 1
        try:
            if count > old.finite.MAX_POINTS:
                refused = []
                for call in (
                    old.finite.finite_shape_probabilities,
                    batch.finite_shape_probabilities,
                ):
                    try:
                        call(pixels, [source], **kwargs, **limits)
                        refused.append(False)
                    except ValueError:
                        refused.append(True)
                append_checked(
                    rows,
                    {
                        **identity,
                        "status": "refusal_control",
                        "passed": all(refused),
                        "refused": refused,
                    },
                    "resource_serialization",
                )
                continue
            a = old.finite.finite_shape_probabilities(pixels, [source], **kwargs, **limits)
            b = batch.finite_shape_probabilities(
                pixels,
                [source],
                **kwargs,
                **limits,
                **(
                    {"memory_limit_bytes": control["memory_limit_bytes"]}
                    if "memory_limit_bytes" in control
                    else {}
                ),
            )
            bounded = bool(
                b.evaluations <= limits["max_evaluations"]
                and b.diagnostics.workspace_peak_bytes <= b.diagnostics.memory_limit_bytes
            )
            retained = bool(
                len(b.probabilities) == count
                and all(
                    (v is not None) == (s == "resolved")
                    for v, s in zip(b.probabilities, b.statuses, strict=True)
                )
            )
            append_checked(
                rows,
                {
                    **identity,
                    "status": "evaluated",
                    "original": asdict(a),
                    "candidate": asdict(b),
                    "retained": retained,
                    "bounded": bounded,
                    "passed": retained and bounded,
                },
                "resource_serialization",
            )
        except Exception as error:  # noqa: BLE001
            rows.append(failure(identity, error, "resource"))
    return rows


def derivative_checks(plan, old, current, oracle, oracle_plan, np):
    rows = []
    cases = {c["name"]: c for c in plan["operator_cases"]}
    for name in plan["derivative_controls"]["cases"]:
        try:
            case = cases[name]
            config = {**copy.deepcopy(plan["base"]), **copy.deepcopy(case["changes"])}
            pixels = queries(config, plan, oracle, np)
            kwargs = {
                "centre": config["centre"],
                "normal": oracle.normal(config),
                "sensor_shape": config["sensor_shape"],
                "homography": config["homography"],
                "psf_covariance": config["covariance"],
                **numerical_settings(plan),
            }
            original = old.circular_segment_jacobian(
                pixels, config["radius"], config["fraction"], **kwargs
            )
            candidate = current.circular_segment_jacobian(
                pixels, config["radius"], config["fraction"], **kwargs
            )
            differences = []
            for step_factor in (1.0, 0.5):
                columns = []
                for axis, initial in enumerate(plan["derivative_controls"]["oracle_steps"]):
                    step = step_factor * initial
                    configs = []
                    for sign in (1, -1):
                        changed = copy.deepcopy(config)
                        changed["levels"] = [0.0, 1.0]
                        if axis < 2:
                            changed["centre"][axis] += sign * step
                        elif axis == 2:
                            changed["radius"] += sign * step
                        else:
                            changed["fraction"] += sign * step
                        configs.append(
                            oracle.independent_means(pixels + 0.5, changed, 64, oracle_plan)
                        )
                    columns.append((configs[0] - configs[1]) / (2 * step))
                differences.append(np.column_stack(columns))
            available = all(s == "resolved" for s in (*original.statuses, *candidate.statuses))
            err = (
                float(np.max(abs(np.asarray(candidate.jacobian) - differences[-1])))
                if available
                else None
            )
            step_delta = float(np.max(abs(differences[0] - differences[1])))
            append_checked(
                rows,
                {
                    "name": name,
                    "status": "evaluated",
                    "original": asdict(original),
                    "candidate": asdict(candidate),
                    "original_candidate_exactly_equal": asdict(original) == asdict(candidate),
                    "maximum_independent_derivative_error": err,
                    "maximum_h_half_h_delta": step_delta,
                    "independent_h_jacobian": differences[0].tolist(),
                    "independent_half_h_jacobian": differences[1].tolist(),
                    "passed": bool(
                        available
                        and err <= plan["derivative_controls"]["maximum_absolute_column_error"]
                        and step_delta <= plan["derivative_controls"]["maximum_h_vs_half_h_delta"]
                    ),
                },
                "derivative_serialization",
            )
        except Exception as error:  # noqa: BLE001
            rows.append(failure({"name": name}, error, "derivative"))
    return rows


def representative_rows(plan):
    report = strict_json(ROOT / "studies/results/finite-photo-intensity-v2.json")
    return [
        next(r for r in report["rows"] if r["name"] == item["case"] and r["lane"] == item["lane"])
        for item in plan["timing"]["representative_cases"]
    ]


def v2_arguments(row, np):
    observed = row["observed"]
    return {
        "sensor_shape": observed["field_shape"],
        "homography": np.asarray(observed["homography"]),
        "normal": np.asarray(observed["normal"]),
        "psf_covariance": np.asarray(row["covariance_record"]["canonical"]),
        **copy.deepcopy(observed["bounds"]),
    }


def photo_completion_data(data):
    return bool(
        data.get("best") is not None
        and data.get("geometry_rank") == 4
        and not any(
            data.get(key)
            for key in (
                "flat",
                "tied",
                "endpoint",
                "rank_deficient",
                "work_exhausted",
                "refinement_limited",
                "unrefined_basins",
                "numerically_unsupported",
            )
        )
    )


def paired_times(calls, warmups, repeats, *, profile_calls=None):
    rows = []
    for index in range(warmups + repeats):
        order_index = index if index < warmups else index - warmups
        order = ("original", "candidate") if order_index % 2 == 0 else ("candidate", "original")
        for label in order:
            started = time.perf_counter_ns()
            elapsed = None
            row = {"method": label, "warmup": index < warmups, "repeat": index - warmups}
            try:
                if row["warmup"] and profile_calls:
                    result, profile = profile_calls[label]()
                    row["profile"] = profile
                    row["timing_scope"] = "Instrumented warmup; excluded from timed medians."
                else:
                    result = calls[label]()
                    row["timing_scope"] = "Uninstrumented paired call."
                elapsed = (time.perf_counter_ns() - started) / 1e9
                row.update(status="returned", result=asdict(result), evaluations=result.evaluations)
                payload = row["result"]
                row["required_return_quality"] = (
                    bool(payload["statuses"]) and all(s == "resolved" for s in payload["statuses"])
                    if "statuses" in payload
                    else photo_completion_data(payload)
                )
                json.dumps(row, allow_nan=False)
            except Exception as error:  # noqa: BLE001 - later paired calls must still execute
                row = safe_failure(row, error, "paired_call")
            row["seconds"] = (
                elapsed if elapsed is not None else (time.perf_counter_ns() - started) / 1e9
            )
            rows.append(row)
    complete = len(rows) == len(calls) * (warmups + repeats) and all(
        row["status"] == "returned" for row in rows
    )
    medians = {}
    for label in calls:
        values = [
            r["seconds"]
            for r in rows
            if not r["warmup"] and r["method"] == label and r["status"] == "returned"
        ]
        medians[label] = statistics.median(values) if len(values) == repeats else None
    raw_speedup = medians["original"] / medians["candidate"] if complete else None
    qualified = complete and all(row.get("required_return_quality", False) for row in rows)
    return {
        "measurements": rows,
        "medians": medians,
        "all_calls_returned": complete,
        "raw_median_speedup": raw_speedup,
        "median_speedup": raw_speedup if qualified else None,
        "all_required_return_quality_passed": qualified,
        "scope": "Raw times retained; failed/unsafe/unresolved/incomplete returns withhold qualified speedup. Warmups never enter medians.",
    }


def kernel_timings(plan, old, current, batch, np):
    rows = []
    for row in representative_rows(plan):
        obs = row["observed"]
        for count in plan["timing"]["query_counts"]:
            pixels = np.asarray(
                obs["training_pixels"]
                if count == 40
                else [*obs["training_pixels"], *obs["heldout_pixels"]],
                int,
            )
            kwargs = v2_arguments(row, np)
            for key in ("centre_bounds", "radius_bounds", "chord_fraction_bounds"):
                kwargs.pop(key)
            kwargs.update(centre=obs["seed_centre"], **numerical_settings(plan))

            def old_mean(p=pixels, k=kwargs, o=obs):
                return old.circular_segment_probabilities(
                    p, o["seed_radius"], o["seed_fraction"], **k
                )

            def batch_mean(p=pixels, k=kwargs, o=obs):
                return current.circular_segment_probabilities(
                    p, o["seed_radius"], o["seed_fraction"], **k
                )

            for method, calls in (
                ("mean", {"original": old_mean, "candidate": batch_mean}),
                (
                    "direct_shape_jacobian",
                    {
                        "original": lambda p=pixels, k=kwargs, o=obs: old.circular_segment_jacobian(
                            p, o["seed_radius"], o["seed_fraction"], **k
                        ),
                        "candidate": lambda p=pixels, k=kwargs, o=obs: (
                            current.circular_segment_jacobian(
                                p, o["seed_radius"], o["seed_fraction"], **k
                            )
                        ),
                    },
                ),
            ):
                identity = {
                    "name": row["name"],
                    "lane": row["lane"],
                    "query_count": count,
                    "method": method,
                }
                try:
                    rows.append(
                        {
                            **identity,
                            "status": "timed",
                            **paired_times(
                                calls,
                                plan["timing"]["warmup_calls_each"],
                                plan["timing"]["paired_timed_repeats"],
                            ),
                        }
                    )
                except Exception as error:  # noqa: BLE001
                    rows.append(failure(identity, error, "kernel_timing"))
    return rows


def archived_datasets(plan, np):
    """Only saved input arrays/domains: no image rendering or re-preparation."""
    original = strict_json(ROOT / "studies/results/finite-free-centre-v1.json")
    photo = strict_json(ROOT / "studies/results/finite-photo-intensity-v2.json")
    source_plan = strict_json(ROOT / "studies/finite-free-centre-v1.json")
    photo_plan = strict_json(ROOT / "studies/finite-photo-intensity-v2.json")
    result = []
    if len(original["cases"]) != 24 or len(photo["rows"]) != 12:
        raise ValueError("exact archived24+12 populations required")
    if [(row["name"], row["lane"]) for row in original["cases"]] != [
        (row["name"], row["lane"]) for row in source_plan["cases"]
    ]:
        raise ValueError("archived original case order/population differs from its frozen plan")
    if [(row["name"], row["lane"]) for row in photo["rows"]] != [
        (name, lane) for name in photo_plan["cases"] for lane in photo_plan["lanes"]
    ]:
        raise ValueError("archived photo case order/population differs from its frozen plan")
    original_sources = {
        "backend/finite_centre_fit.py": sha(
            ROOT / "studies/fixtures/finite-affine-batch-v1/original-finite-centre-fit.py.txt"
        ),
        "backend/finite_shape.py": sha(
            ROOT / "studies/fixtures/finite-affine-batch-v1/original-finite-shape.py.txt"
        ),
        "backend/sheet.py": sha(
            ROOT / "studies/fixtures/finite-affine-batch-v1/original-sheet.py.txt"
        ),
        **{
            key: value
            for key, value in plan["baseline_comparator"]["shared_dependency_sha256"].items()
            if key.startswith("backend/")
        },
    }
    for report in (original, photo):
        if not report["source_unchanged"] or any(
            report["source_before"].get(name) != expected
            or report["source_after"].get(name) != expected
            for name, expected in original_sources.items()
        ):
            raise ValueError(
                "archived comparator was not qualified on exact original e201/9102/e18c stack"
            )
    for family, rows in (("original24", original["cases"]), ("photo_v2", photo["rows"])):
        for archived in rows:
            dataset = {
                "family": family,
                "name": archived["name"],
                "lane": archived["lane"],
                "archived": archived,
                "archived_parsed_row_sha256": parsed_sha(archived),
                "eligible": "observed_values_training" in archived
                if family == "original24"
                else bool(archived.get("fit_attempted")),
            }
            if not dataset["eligible"]:
                result.append(dataset)
                continue
            obs = archived["observed"]
            if family == "original24":
                cfg = archived["config"]
                angle = math.radians(cfg["normal_degrees"])
                settings = {**source_plan["fit_settings"], **cfg.get("fit_settings", {})}
                settings["level_bounds"] = tuple(settings["level_bounds"])
                arguments = {
                    "sensor_shape": cfg["sensor_shape"],
                    "homography": cfg["homography"],
                    "normal": [math.cos(angle), math.sin(angle)],
                    "psf_covariance": cfg.get("fit_covariance", cfg["covariance"]),
                    **copy.deepcopy(obs["bounds"]),
                    **settings,
                }
                values, held = (
                    archived["observed_values_training"],
                    archived["observed_values_heldout"],
                )
                injection = cfg.get("injection")
            else:
                arguments = {**v2_arguments(archived, np), **photo_plan["fit_settings"]}
                values, held = obs["training_values"], obs["heldout_values"]
                injection = None
            dataset.update(
                training_pixels=np.asarray(obs["training_pixels"], dtype=np.int64),
                training_values=np.asarray(values, dtype=float),
                heldout_pixels=np.asarray(obs["heldout_pixels"], dtype=np.int64),
                heldout_values=np.asarray(held, dtype=float),
                arguments=arguments,
                injection=injection,
            )
            # Serialization of arrays is explicit; input hash is representation-
            # independent and includes every scalar supplied to the optimizer.
            dataset["fit_input"] = {
                "training_pixels": dataset["training_pixels"].tolist(),
                "training_values": dataset["training_values"].tolist(),
                "heldout_pixels": dataset["heldout_pixels"].tolist(),
                "heldout_values": dataset["heldout_values"].tolist(),
                "arguments": {
                    key: value.tolist() if isinstance(value, np.ndarray) else value
                    for key, value in arguments.items()
                },
                "planned_injection": injection,
            }
            dataset["fit_input_sha256"] = parsed_sha(dataset["fit_input"])
            result.append(dataset)
    return result, source_plan, photo_plan


def invoke_fit(
    core, dataset, *, entry_log=None, injection=None, method="candidate", purpose="accuracy"
):
    """One real optimizer call with the SAME optional archived failure injection."""
    original = core.circular_segment_probabilities
    injected_calls = 0

    def first_error(*args, **kwargs):
        nonlocal injected_calls
        injected_calls += 1
        if injected_calls == 1:
            raise ValueError("planned first-forward numerical failure")
        return original(*args, **kwargs)

    try:
        if dataset["injection"] == "first_forward_value_error":
            core.circular_segment_probabilities = first_error
        arguments = copy.deepcopy(dataset["arguments"])
        pixels, values = dataset["training_pixels"], dataset["training_values"]
        call = core.fit_circular_segment
        entry = {
            "family": dataset["family"],
            "name": dataset["name"],
            "lane": dataset["lane"],
            "method": method,
            "purpose": purpose,
            "callable_module": getattr(call, "__module__", "unknown"),
            "callable_name": getattr(call, "__name__", type(call).__name__),
            "actual_callable_entered": False,
            "actual_real_fitter_entered": False,
        }
        if entry_log is not None:
            entry_log.append(entry)
        if injection is not None and method == "candidate":
            injection["candidate_fit_entries"] += 1
            if injection["requested"] and injection["injections"] == 0:
                injection["injections"] += 1
                entry.update(status="injected_before_real_core_entry")
                raise ValueError("planned first actual candidate fit-entry failure")
        entry["actual_callable_entered"] = True
        entry["actual_real_fitter_entered"] = bool(
            entry["callable_module"].endswith("finite_centre_fit")
            and entry["callable_name"] == "fit_circular_segment"
        )
        started = time.perf_counter_ns()
        try:
            fit = call(pixels, values, **arguments)
            entry["status"] = "returned"
            return fit, injected_calls
        except Exception as error:
            entry.update(
                status="exception_inside_callable",
                error={"type": type(error).__name__, "message": str(error)},
            )
            raise
        finally:
            entry["seconds"] = (time.perf_counter_ns() - started) / 1e9
    finally:
        core.circular_segment_probabilities = original


def profiled_fit(core, dataset, **invocation):
    """Exclusive call attribution, outside timed medians; no changed arithmetic."""
    originals, stack, events = {}, [], []
    names = (
        "_segment_geometry",
        "circular_segment_probabilities",
        "circular_segment_jacobian",
        "_box_fit",
        "_projected_jacobians",
    )

    def wrap(name, call):
        def measured(*args, **kwargs):
            frame = {"name": name, "start": time.perf_counter_ns(), "children": 0}
            stack.append(frame)
            event = {"method": name}
            try:
                result = call(*args, **kwargs)
                event["status"] = "returned"
                for key in ("evaluations", "panels"):
                    if hasattr(result, key):
                        event[key] = int(getattr(result, key))
                if hasattr(result, "statuses"):
                    event["statuses"] = list(result.statuses)
                return result
            except Exception as error:
                event.update(
                    status="exception", error={"type": type(error).__name__, "message": str(error)}
                )
                raise
            finally:
                elapsed = time.perf_counter_ns() - frame["start"]
                stack.pop()
                if stack:
                    stack[-1]["children"] += elapsed
                event.update(
                    inclusive_seconds=elapsed / 1e9,
                    exclusive_seconds=(elapsed - frame["children"]) / 1e9,
                )
                events.append(event)

        return measured

    started = time.perf_counter_ns()
    try:
        for name in names:
            originals[name] = getattr(core, name)
            setattr(core, name, wrap(name, originals[name]))
        fit, injection_calls = invoke_fit(core, dataset, **invocation)
    finally:
        elapsed = (time.perf_counter_ns() - started) / 1e9
        for name, original in originals.items():
            setattr(core, name, original)
    attributed = {
        name: math.fsum(e["exclusive_seconds"] for e in events if e["method"] == name)
        for name in names
    }
    return fit, {
        "scope": "Instrumented exclusive attribution; NEVER used as a paired timing sample.",
        "events": events,
        "exclusive_seconds": attributed,
        "fit_seconds": elapsed,
        "remaining_validation_search_refinement_seconds": elapsed - math.fsum(attributed.values()),
        "planned_injection_forward_calls": injection_calls,
    }


def completion(fit, family):
    complete = fit.best is not None and not (
        fit.work_exhausted
        or fit.refinement_limited
        or fit.unrefined_basins
        or fit.numerically_unsupported
    )
    if family == "photo_v2":
        complete = (
            complete
            and fit.geometry_rank == 4
            and not (fit.flat or fit.tied or fit.endpoint or fit.rank_deficient)
        )
    return bool(complete)


def fit_flags(fit):
    return {
        key: fit.get(key)
        for key in (
            "flat",
            "tied",
            "endpoint",
            "rank_deficient",
            "geometry_rank",
            "work_exhausted",
            "refinement_limited",
            "unrefined_basins",
            "numerically_unsupported",
        )
    }


def compare_archived_fit(archived, row, family):
    before, after = archived.get("fit", {}), row.get("fit", {})
    a, b = before.get("best"), after.get("best")
    deltas = None
    if a is not None and b is not None:
        deltas = {
            "centre_components": [y - x for x, y in zip(a["centre"], b["centre"], strict=True)],
            "radius": b["radius"] - a["radius"],
            "fraction": b["chord_fraction"] - a["chord_fraction"],
            "levels": [y - x for x, y in zip(a["levels"], b["levels"], strict=True)],
            "cost": b["cost"] - a["cost"],
        }
    target_key = "matched_targets_passed" if family == "original24" else "targets_passed"
    old_target = archived.get(target_key)
    return {
        "archived_fit_sha256": parsed_sha(before),
        "current_fit_sha256": parsed_sha(after),
        "before_flags": fit_flags(before),
        "after_flags": fit_flags(after),
        "all_flags_equal": fit_flags(before) == fit_flags(after),
        "best_parameter_deltas": deltas,
        "archived_targets_passed": old_target,
        "previous_pass_preserved": old_target is not True or row.get("targets_passed") is True,
        "scope": "Every delta/flag retained; no new fitted-parameter tolerance is invented.",
    }


def replay_dataset(dataset, core, oracle, source_plan, photo_plan, np, **invocation):
    archived = dataset["archived"]
    row = {key: dataset[key] for key in ("family", "name", "lane", "archived_parsed_row_sha256")}
    row["archived_status"] = archived["status"]
    row.update(
        fit_attempted=False,
        completion_passed=False,
        targets_passed=None
        if dataset["family"] == "original24" and dataset["lane"] != "matched"
        else False,
    )
    started = time.perf_counter()
    stage = "eligibility"
    try:
        if not dataset["eligible"]:
            row.update(
                status=archived["status"],
                reason=archived.get("reason"),
                retained_original_outcome=True,
                passed=True,
            )
            return row
        row.update(
            fit_attempted=True,
            fit_input=dataset["fit_input"],
            fit_input_sha256=dataset["fit_input_sha256"],
        )
        stage = "candidate_fit"
        fit, profile = profiled_fit(core, dataset, **invocation)
        row.update(
            status="fit_returned",
            fit=asdict(fit),
            profile=profile,
            completion_passed=completion(fit, dataset["family"]),
        )
        if fit.best is not None:
            stage = "heldout_scoring"
            best = fit.best
            if dataset["family"] == "original24":
                config = archived["config"]
                predicted = {
                    **config,
                    "source": "point",
                    "centre": list(best.centre),
                    "radius": best.radius,
                    "fraction": best.chord_fraction,
                    "levels": list(best.levels),
                    "covariance": dataset["arguments"]["psf_covariance"],
                }
                means = oracle.independent_means(
                    dataset["heldout_pixels"] + 0.5,
                    predicted,
                    source_plan["oracle"]["orders"][1],
                    source_plan,
                )
                row["geometry"] = oracle.geometry_metrics(config, best)
                row["heldout_level_max_error"] = float(
                    np.max(abs(means - dataset["heldout_values"]))
                )
                row["heldout_predicted_levels"] = means.tolist()
                row["original_oracle_evidence"] = copy.deepcopy(archived["oracle"])
                target = source_plan["matched_targets"]
                matched = dataset["lane"] == "matched"
                row["targets_passed"] = (
                    bool(
                        row["completion_passed"]
                        and all(
                            row["geometry"][key] <= target[key]
                            for key in (
                                "centre_error_observation_px",
                                "radius_error_times_local_H_operator_norm_px",
                                "fraction_error",
                            )
                        )
                        and row["heldout_level_max_error"] <= target["heldout_level_max_error"]
                        and archived["oracle"]["passed"]
                    )
                    if matched
                    else None
                )
            else:
                arguments = dataset["arguments"]
                result = core.circular_segment_probabilities(
                    dataset["heldout_pixels"],
                    best.radius,
                    best.chord_fraction,
                    centre=best.centre,
                    normal=arguments["normal"],
                    sensor_shape=arguments["sensor_shape"],
                    homography=arguments["homography"],
                    psf_covariance=arguments["psf_covariance"],
                    probability_tolerance=arguments["probability_tolerance"],
                )
                row["heldout_forward"] = asdict(result)
                resolved = all(s == "resolved" for s in result.statuses)
                if resolved:
                    p = np.asarray(result.probabilities)
                    means = best.levels[0] * (1 - p) + best.levels[1] * p
                    row["heldout_level_max_error"] = float(
                        np.max(abs(means - dataset["heldout_values"]))
                    )
                    row["heldout_predicted_levels"] = means.tolist()
                truth, ppm = archived["truth_after_scoring"], archived["ppm"]
                row["geometry"] = {
                    "centre_error_mm": float(
                        np.linalg.norm(np.asarray(best.centre) / ppm - truth["centre_mm"])
                    ),
                    "absolute_radius_error_mm": abs(best.radius / ppm - truth["radius_mm"]),
                    "fraction": best.chord_fraction,
                    "centre_mm": (np.asarray(best.centre) / ppm).tolist(),
                    "radius_mm": best.radius / ppm,
                }
                target = photo_plan["targets"]
                row["targets_passed"] = bool(
                    row["completion_passed"]
                    and resolved
                    and row["geometry"]["centre_error_mm"] <= target["centre_error_mm"]
                    and row["geometry"]["absolute_radius_error_mm"]
                    <= target["absolute_radius_error_mm"]
                    and row["heldout_level_max_error"] <= target["heldout_intensity_max_error"]
                )
        stage = "archived_comparison"
        row["comparison"] = compare_archived_fit(archived, row, dataset["family"])
        row["passed"] = row["comparison"]["previous_pass_preserved"]
        stage = "strict_row_serialization"
        json.dumps(row, allow_nan=False)
    except Exception as error:  # noqa: BLE001 - every later dataset must execute
        row = safe_failure(row, error, stage)
    finally:
        row["runtime_seconds"] = time.perf_counter() - started
    return row


def optimizer_replay(plan, current, oracle, np, **invocation):
    datasets, source_plan, photo_plan = archived_datasets(plan, np)
    rows = []
    for dataset in datasets:
        row = replay_dataset(dataset, current, oracle, source_plan, photo_plan, np, **invocation)
        rows.append(row)
        print(
            json.dumps(
                {
                    "optimizer_replay": dataset["family"],
                    "name": dataset["name"],
                    "lane": dataset["lane"],
                    "status": row["status"],
                    "targets_passed": row["targets_passed"],
                },
                allow_nan=False,
            ),
            file=sys.stderr,
            flush=True,
        )
    return rows, datasets


def fit_timings(plan, datasets, old, current, accuracy_replay, *, entry_log=None, injection=None):
    rows = []
    selected = {(item["case"], item["lane"]) for item in plan["timing"]["representative_cases"]}
    for dataset in datasets:
        if dataset["family"] != "photo_v2" or (dataset["name"], dataset["lane"]) not in selected:
            continue
        identity = {
            "name": dataset["name"],
            "lane": dataset["lane"],
            "training_count": len(dataset["training_pixels"]),
        }
        try:
            accuracy = next(
                row
                for row in accuracy_replay
                if row["family"] == "photo_v2"
                and row["name"] == dataset["name"]
                and row["lane"] == dataset["lane"]
            )
            result = paired_times(
                {
                    "original": lambda d=dataset: invoke_fit(
                        old, d, entry_log=entry_log, method="original", purpose="timed_repeat"
                    )[0],
                    "candidate": lambda d=dataset: invoke_fit(
                        current,
                        d,
                        entry_log=entry_log,
                        injection=injection,
                        method="candidate",
                        purpose="timed_repeat",
                    )[0],
                },
                1,
                3,
                profile_calls={
                    "original": lambda d=dataset: profiled_fit(
                        old, d, entry_log=entry_log, method="original", purpose="warmup"
                    ),
                    "candidate": lambda d=dataset: profiled_fit(
                        current,
                        d,
                        entry_log=entry_log,
                        injection=injection,
                        method="candidate",
                        purpose="warmup",
                    ),
                },
            )
            original_warmup = next(
                (
                    m.get("result")
                    for m in result["measurements"]
                    if m["method"] == "original" and m["warmup"] and m["status"] == "returned"
                ),
                None,
            )
            for measurement in result["measurements"]:
                reference = (
                    accuracy.get("fit") if measurement["method"] == "candidate" else original_warmup
                )
                measurement["same_complete_fit_reference"] = bool(
                    reference is not None
                    and measurement.get("result") == reference
                    and photo_completion_data(reference)
                )
            result["all_fit_outputs_consistent"] = all(
                m["same_complete_fit_reference"] for m in result["measurements"]
            )
            result["candidate_accuracy_replay_fit_sha256"] = parsed_sha(accuracy.get("fit"))
            result["original_warmup_fit_sha256"] = parsed_sha(original_warmup)
            result["qualified_median_speedup"] = (
                result["median_speedup"]
                if (accuracy.get("completion_passed") and result["all_fit_outputs_consistent"])
                else None
            )
            rows.append({**identity, "status": "timed", **result})
        except Exception as error:  # noqa: BLE001
            rows.append(failure(identity, error, "fit_timing"))
    return rows


def timing_environment(plan):
    """Correctness survives unavailable/denied affinity; timing qualification does not."""
    for key, value in plan["timing"]["environment_before_numpy"].items():
        os.environ[key] = value
    before, after, errors = None, None, []
    if hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"):
        try:
            before = sorted(os.sched_getaffinity(0))
        except OSError as error:
            errors.append(
                {"stage": "get_before", "type": type(error).__name__, "message": str(error)}
            )
        if before:
            try:
                os.sched_setaffinity(0, {before[0]})
            except OSError as error:
                errors.append({"stage": "set", "type": type(error).__name__, "message": str(error)})
            try:
                after = sorted(os.sched_getaffinity(0))
            except OSError as error:
                errors.append(
                    {"stage": "get_after", "type": type(error).__name__, "message": str(error)}
                )
    else:
        errors.append(
            {
                "stage": "availability",
                "type": "unavailable",
                "message": "CPU affinity API unavailable",
            }
        )
    threads = {key: os.environ[key] for key in plan["timing"]["environment_before_numpy"]}
    return {
        "affinity_before": before,
        "affinity_after": after,
        "affinity_errors": errors,
        "fixed_cpu_timing_qualified": bool(
            before
            and after == [before[0]]
            and not errors
            and all(value == "1" for value in threads.values())
        ),
        "thread_environment": threads,
    }


def setup(plan):
    execution = timing_environment(plan)
    import numpy as np

    sys.path.insert(0, str(ROOT))
    package = types.ModuleType("_finite_affine_original")
    package.__path__ = [str(ROOT / "backend")]
    sys.modules[package.__name__] = package
    fixture = ROOT / "studies/fixtures/finite-affine-batch-v1"
    load(package.__name__ + ".sheet", fixture / "original-sheet.py.txt")
    load(package.__name__ + ".finite_shape", fixture / "original-finite-shape.py.txt")
    old = load(
        package.__name__ + ".finite_centre_fit", fixture / "original-finite-centre-fit.py.txt"
    )
    from backend import finite_affine as batch
    from backend import finite_centre_fit as current

    oracle = load(
        "_finite_affine_independent_area", ROOT / "studies/verification/finite-free-centre-v1.py"
    )
    return (
        np,
        old,
        current,
        batch,
        oracle,
        {
            **execution,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "loadavg": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
        },
    )


def without_measurements(value):
    """Drop ONLY clock/profiling time fields, retaining call/work/status data."""
    clock_fields = {
        "runtime_seconds",
        "seconds",
        "inclusive_seconds",
        "exclusive_seconds",
        "fit_seconds",
        "remaining_validation_search_refinement_seconds",
    }
    if isinstance(value, dict):
        return {
            key: without_measurements(item)
            for key, item in value.items()
            if key not in clock_fields
        }
    if isinstance(value, list):
        return [without_measurements(item) for item in value]
    return value


def continuation_audit(canonical, result):
    old, new = canonical["optimizer_replay"], result["optimizer_replay"]
    comparisons = []
    if len(old) == len(new) == 36:
        for index in range(1, 36):
            a, b = without_measurements(old[index]), without_measurements(new[index])
            comparisons.append(
                {
                    "index": index,
                    "family": b["family"],
                    "name": b["name"],
                    "lane": b["lane"],
                    "equal_except_clock_measurements": a == b,
                    "canonical_parsed_row_sha256": parsed_sha(a),
                    "continuation_parsed_row_sha256": parsed_sha(b),
                }
            )
    injection = result["first_fit_injection"]
    entries = result.get("optimizer_entry_log", [])
    expected_timed = 24 if result.get("summary", {}).get("timing_requested") else 0
    checks = {
        "all36_rows_retained": len(new) == 36,
        "first_entry_only_injected": injection["injections"] == 1,
        "first_row_explicit_failure": bool(
            new
            and new[0]["status"] == "execution_failure"
            and not new[0]["completion_passed"]
            and not new[0]["targets_passed"]
        ),
        "all35_later_rows_identical_except_clocks": len(comparisons) == 35
        and all(r["equal_except_clock_measurements"] for r in comparisons),
        "source_input_closure_unchanged": canonical["source_before"]
        == canonical["source_after"]
        == result["source_before"]
        == result["source_after"],
        "all32_accuracy_entry_attempts_logged": sum(e["purpose"] == "accuracy" for e in entries)
        == 32,
        "31_later_real_accuracy_function_entries": sum(
            e["purpose"] == "accuracy" and e["actual_real_fitter_entered"] for e in entries
        )
        == 31,
        "all_required_real_timed_function_entries": sum(
            e["purpose"] in {"warmup", "timed_repeat"} and e["actual_real_fitter_entered"]
            for e in entries
        )
        == expected_timed,
    }
    return {
        "scope": "First candidate fit entry only throws. All35 later optimizer replay rows compared, retaining work, flags, statuses and profile call records; only named clock fields are removed. Timed-repeat speedups are not compared as deterministic data.",
        "checks": checks,
        "later_row_comparisons": comparisons,
        "first_fit_injection": injection,
        "canonical_timing_ignored": bool(
            canonical.get("summary", {}).get("timing_requested")
            and not result.get("summary", {}).get("timing_requested")
        ),
        "expected_real_timed_entries_in_requested_continuation": expected_timed,
        "all_passed": all(checks.values()),
    }


def run(plan, *, timing, complete, inject_first_fit_failure=False):
    inputs(plan)
    before = closure(plan)
    np, old, current, batch, oracle, environment = setup(plan)
    oracle_plan = strict_json(ROOT / "studies/finite-free-centre-v1.json")
    rows = []
    for case in plan["operator_cases"]:
        row = operator_case(case, plan, old, batch, oracle, oracle_plan, np)
        rows.append(row)
        print(
            json.dumps({"case": case["name"], "passed": row["passed"]}), file=sys.stderr, flush=True
        )
    limits = resources(plan, old, batch, oracle, np)
    derivatives = derivative_checks(plan, old, current, oracle, oracle_plan, np)
    timings = kernel_timings(plan, old, current, batch, np) if timing else []
    replay, fit_timing_rows, entry_log = [], [], []
    injection = {
        "requested": inject_first_fit_failure,
        "candidate_fit_entries": 0,
        "injections": 0,
        "scope": "Actual fit-entry exception, not a numerical oracle or no-fit stub.",
    }
    if complete:
        replay, datasets = optimizer_replay(
            plan,
            current,
            oracle,
            np,
            entry_log=entry_log,
            injection=injection,
            method="candidate",
            purpose="accuracy",
        )
        fit_timing_rows = (
            fit_timings(
                plan, datasets, old, current, replay, entry_log=entry_log, injection=injection
            )
            if timing
            else []
        )
    after = closure(plan)
    mean_speedups = [
        r["median_speedup"]
        for r in timings
        if r.get("method") == "mean"
        and r.get("status") == "timed"
        and r.get("median_speedup") is not None
    ]
    expected_mean_timings = len(plan["timing"]["representative_cases"]) * len(
        plan["timing"]["query_counts"]
    )
    speedup = (
        math.exp(statistics.mean(map(math.log, mean_speedups)))
        if len(mean_speedups) == expected_mean_timings
        else None
    )
    raw_mean_speedups = [
        r["raw_median_speedup"]
        for r in timings
        if r.get("method") == "mean" and r.get("raw_median_speedup") is not None
    ]
    raw_mean_speedup = (
        math.exp(statistics.mean(map(math.log, raw_mean_speedups)))
        if len(raw_mean_speedups) == expected_mean_timings
        else None
    )
    fit_speedups = [
        r["qualified_median_speedup"]
        for r in fit_timing_rows
        if r.get("qualified_median_speedup") is not None
    ]
    fit_speedup = (
        math.exp(statistics.mean(map(math.log, fit_speedups))) if len(fit_speedups) == 3 else None
    )
    raw_fit_speedups = [
        r["raw_median_speedup"] for r in fit_timing_rows if r.get("raw_median_speedup") is not None
    ]
    raw_fit_speedup = (
        math.exp(statistics.mean(map(math.log, raw_fit_speedups)))
        if len(raw_fit_speedups) == 3
        else None
    )
    fixed_cpu = environment["fixed_cpu_timing_qualified"]
    speedup = speedup if fixed_cpu else None
    fit_speedup = fit_speedup if fixed_cpu else None
    accuracy_fit_entries = sum(entry["purpose"] == "accuracy" for entry in entry_log)
    timing_fit_entries = sum(entry["purpose"] in {"warmup", "timed_repeat"} for entry in entry_log)
    previous_passes_preserved = all(r.get("passed", False) for r in replay) if complete else None
    summary = {
        "operator_cases": len(rows),
        "operator_passes": sum(r["passed"] for r in rows),
        "resource_controls": len(limits),
        "resource_passes": sum(r["passed"] for r in limits),
        "derivative_controls": len(derivatives),
        "derivative_passes": sum(r["passed"] for r in derivatives),
        "timing_requested": timing,
        "all_requested_timing_calls_returned": all(
            row.get("all_calls_returned", False) for row in [*timings, *fit_timing_rows]
        )
        if timing
        else None,
        "mean_geometric_median_speedup": speedup,
        "raw_mean_geometric_median_speedup": raw_mean_speedup,
        "fixed_cpu_timing_qualified": fixed_cpu,
        "mean_speed_goal_met": speedup >= plan["timing"]["mean_geometric_median_speedup_goal"]
        if speedup is not None
        else None,
        "actual_fit_geometric_median_speedup": fit_speedup,
        "raw_actual_fit_geometric_median_speedup": raw_fit_speedup,
        "actual_fit_speed_goal_met": fit_speedup
        >= plan["timing"]["actual_40_training_fit_geometric_median_speedup_goal"]
        if fit_speedup is not None
        else None,
        "optimizer_entries": accuracy_fit_entries + timing_fit_entries,
        "actual_optimizers_executed": sum(
            entry["actual_real_fitter_entered"] for entry in entry_log
        ),
        "actual_callable_entries": sum(entry["actual_callable_entered"] for entry in entry_log),
        "optimizer_count_scope": "Explicit invoke_fit log AFTER all argument/profile preparation. Real fitter entries require exact production function name/module, not dataset attempts or stubs; an entered function need not converge.",
        "attempted_accuracy_dataset_entries": sum(
            row.get("fit_attempted", False) for row in replay
        ),
        "attempted_timing_dataset_entries": sum(
            len(row.get("measurements", [])) for row in fit_timing_rows
        ),
        "accuracy_replay_rows": len(replay),
        "accuracy_replay_optimizer_entries": accuracy_fit_entries,
        "timing_optimizer_entries": timing_fit_entries,
        "optimizer_stage": "complete requested" if complete else "not requested",
        "previous_accuracy_passes_preserved": previous_passes_preserved,
        "all_archived_completion_flags_equal": all(
            r.get("comparison", {}).get("all_flags_equal", True) for r in replay
        )
        if complete
        else None,
        "original_matched_target_passes": sum(
            r["family"] == "original24"
            and r["lane"] == "matched"
            and r.get("targets_passed") is True
            for r in replay
        ),
        "photo_v2_target_passes": sum(
            r["family"] == "photo_v2" and r.get("targets_passed") is True for r in replay
        ),
        "kernel_accuracy_passed": all(r["passed"] for r in [*rows, *limits, *derivatives]),
    }
    return {
        "format": "pictures-to-cad-finite-affine-batch-study",
        "version": 1,
        "scope": plan["scope"],
        "plan": plan,
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "environment": environment,
        "operator_cases": rows,
        "resource_controls": limits,
        "derivative_controls": derivatives,
        "kernel_timings": timings,
        "optimizer_replay": replay,
        "fit_timings": fit_timing_rows,
        "first_fit_injection": injection,
        "optimizer_entry_log": entry_log,
        "summary": summary,
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--quiet-interval",
        action="store_true",
        help="owner declares no concurrent study/test workload for timings",
    )
    parser.add_argument("--no-timing", action="store_true")
    parser.add_argument(
        "--complete",
        action="store_true",
        help="execute separately authorized archived optimizer stage",
    )
    parser.add_argument("--inject-first-fit-failure", action="store_true")
    parser.add_argument("--canonical", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args(arguments)
    if args.inject_first_fit_failure and not (args.complete and args.canonical and args.audit):
        parser.error(
            "failure continuation requires --complete --canonical EXISTING_JSON --audit NEW_JSON"
        )
    if not args.inject_first_fit_failure and (args.canonical or args.audit):
        parser.error("--canonical/--audit are reserved for the separately authorized continuation")
    if not args.no_timing and not args.quiet_interval:
        parser.error("timings require --quiet-interval or use --no-timing")
    if (
        args.output.suffix.lower() != ".json"
        or args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error("--output requires a NEW .json in an existing directory")
    if args.audit and (
        args.audit == args.output
        or args.audit.suffix.lower() != ".json"
        or args.audit.exists()
        or args.audit.is_symlink()
        or not args.audit.parent.is_dir()
    ):
        parser.error("--audit requires a distinct NEW .json in an existing directory")
    canonical = strict_json(args.canonical) if args.canonical else None
    canonical_sha_before = sha(args.canonical) if args.canonical else None
    result = run(
        strict_json(PLAN),
        timing=not args.no_timing,
        complete=args.complete,
        inject_first_fit_failure=args.inject_first_fit_failure,
    )
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    with args.output.open("x") as stream:
        stream.write(encoded)
    print(encoded, end="")
    if canonical is not None:
        audit = continuation_audit(canonical, result)
        audit["checks"]["canonical_input_unchanged"] = sha(args.canonical) == canonical_sha_before
        audit["all_passed"] = all(audit["checks"].values())
        audit.update(
            canonical_sha256=canonical_sha_before,
            continuation_sha256=sha(args.output),
            runner_sha256=sha(RUNNER),
            plan_sha256=sha(PLAN),
        )
        with args.audit.open("x") as stream:
            json.dump(audit, stream, indent=2, allow_nan=False)
            stream.write("\n")
        return 0 if audit["all_passed"] else 1
    summary = result["summary"]
    passed = result["source_unchanged"] and summary["kernel_accuracy_passed"]
    if args.complete:
        passed = passed and summary["previous_accuracy_passes_preserved"]
    if not args.no_timing:
        passed = (
            passed
            and summary["mean_speed_goal_met"]
            and summary["all_requested_timing_calls_returned"]
        )
        if args.complete:
            passed = passed and summary["actual_fit_speed_goal_met"]
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
