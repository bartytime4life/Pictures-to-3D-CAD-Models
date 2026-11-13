#!/usr/bin/env python3
"""Replay the frozen V2 finite-normal error-control experiment.

The 337 old scenes are post-hoc synthetic regression; the 80 additional scenes
are prospective. The old requested tolerance/caps and all V1 bytes remain intact.
This runner makes no fit, renderer or residual/photo-archive analysis. Required
--output NEW_JSON is refused before numerical imports if it exists (including a
dangling symlink) or its parent is absent. All scientific failures remain rows.

The pinned V1 runner is loaded in an isolated module for its independent source-s
partition/retention and positive-area bookkeeping. Its file is never changed.
V2 independently implements exact determinant normalization and rule arithmetic;
it calls no production private geometry, determinant, or moment helper. Error
coverage is an empirical check of engineering estimates, not a certified bound.
"""

# Every broad catch retains an explicit failure; it cannot qualify unknown data.
# ruff: noqa: BLE001

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import os
import platform
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-normal-error-control-v2.json"
PLAN_SHA256 = "b59d38b3ca92449c4233b947dd061f7a6591ce1944946b6c10e868afaad3adbb"
ADDENDUM = ROOT / "studies/finite-normal-error-control-inverse-addendum-v2.json"
ADDENDUM_SHA256 = "5703d6fa480ba2801291865b2b9921ba7c8b875ef96adc1beb3d3d4b3bcfb8bd"
V1_RUNNER = "studies/verification/finite-normal-derivative-v1.py"
V1_MAIN = "studies/finite-normal-derivative-v1.json"
V1_SUPPLEMENT = "studies/finite-normal-derivative-compressed-chart-v1.json"
API_PATH = "backend/finite_normal.py"
BASE = None
NP = None
NORMALIZER_RECORDS = {}
EPS = sys.float_info.epsilon
SMALLEST = math.nextafter(0.0, 1.0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load pinned helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_output(path):
    path = Path(path).absolute()
    if os.path.lexists(path):
        raise ValueError("output must be a new path, including no existing symlink")
    if not path.parent.is_dir():
        raise ValueError("output parent directory must already exist")
    return path


def load_context():
    global BASE
    if sha(PLAN) != PLAN_SHA256:
        raise ValueError("frozen V2 plan hash differs")
    if sha(ADDENDUM) != ADDENDUM_SHA256:
        raise ValueError("frozen V2 inverse software addendum hash differs")
    # The immutable helper is stdlib-only at module load; no production import.
    expected_v1 = "8cd752ccf8fef6391d51dc10761f073c3d3f0fb6c45deb977ea346553ee5dd74"
    if sha(ROOT / V1_RUNNER) != expected_v1:
        raise ValueError("frozen V1 helper differs")
    BASE = load_module("finite_normal_v2_pinned_v1_helper", ROOT / V1_RUNNER)
    plan = BASE.strict_json(PLAN)
    addendum = BASE.strict_json(ADDENDUM)
    if (
        addendum["main_plan"] != PLAN.relative_to(ROOT).as_posix()
        or addendum["main_plan_sha256"] != PLAN_SHA256
    ):
        raise ValueError("inverse software addendum refers to a different plan")
    for name, expected in {**plan["inputs_sha256"], **plan["regression_plans"]}.items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"frozen input differs: {name}")
    old_main = BASE.strict_json(ROOT / V1_MAIN)
    old_extra = BASE.strict_json(ROOT / V1_SUPPLEMENT)
    old = [*old_main["scenes"], *old_extra["scenes"]]
    scenes = [*old, *plan["scenes"]]
    population = plan["declared_population"]
    if (
        len(old) != population["regression_scenes"]
        or len(plan["scenes"]) != population["new_scenes"]
    ):
        raise ValueError("old/new scene counts differ from frozen V2 plan")
    if len(scenes) != population["total_scenes"]:
        raise ValueError("total scene count differs")
    if sum(len(s["pixels_xy"]) for s in scenes) != population["total_queries"]:
        raise ValueError("total query count differs")
    for name in ("probability_tolerance", "max_panels", "max_evaluations"):
        if plan["operator"][name] != old_main["operator"][name]:
            raise ValueError("old regression tolerance/caps changed")
    if len({s["id"] for s in scenes}) != len(scenes):
        raise ValueError("scene IDs are not unique")
    for scene in scenes:
        pixels = scene["pixels_xy"]
        if len({tuple(p) for p in pixels}) != len(pixels):
            raise ValueError("planned scene pixels are not deduplicated")
        for role in scene["query_roles"]:
            if pixels[role["query_index"]] != role["pixel"]:
                raise ValueError("planned role-to-query mapping differs")
    by_id = {s["id"]: s for s in scenes}
    selections = plan["positive_area_corroboration"]["selection"]
    if len(selections) != population["area_scenes"]:
        raise ValueError("positive-area scene count differs")
    if sum(len(s["query_indices"]) for s in selections) != population["area_queries"]:
        raise ValueError("positive-area query count differs")
    for selection in selections:
        scene = by_id[selection["scene_id"]]
        if any(not 0 <= i < len(scene["pixels_xy"]) for i in selection["query_indices"]):
            raise ValueError("positive-area query index is outside its frozen scene")
    return plan, scenes


def source_hashes(plan):
    paths = {p.relative_to(ROOT).as_posix() for p in (ROOT / "backend").rglob("*.py")}
    paths.update(plan["inputs_sha256"])
    paths.update(plan["regression_plans"])
    paths.update(
        (
            API_PATH,
            "tests/test_finite_normal_error_control.py",
            PLAN.relative_to(ROOT).as_posix(),
            ADDENDUM.relative_to(ROOT).as_posix(),
            RUNNER.relative_to(ROOT).as_posix(),
            "pyproject.toml",
            "uv.lock",
        )
    )
    return {
        name: {"sha256": sha(ROOT / name), "bytes": (ROOT / name).stat().st_size}
        for name in sorted(paths)
    }


def software_preflight_addendum():
    return {
        "path": ADDENDUM.relative_to(ROOT).as_posix(),
        "sha256": ADDENDUM_SHA256,
        "record": BASE.strict_json(ADDENDUM),
        "execution_scope": "Retained pre-canonical software finding; this runner does not execute its solver diagnostic or unit controls. Scientific scene/query/criterion population is unchanged.",
    }


def requested_tolerance(scene, plan):
    return scene.get("requested_tolerance", plan["operator"]["probability_tolerance"])


def population_name(index, plan):
    return (
        "post_hoc_synthetic_regression"
        if index < plan["declared_population"]["regression_scenes"]
        else "prospective_new_synthetic"
    )


def scene_failure(index, scene, plan, stage, error, partial=None):
    row = BASE.scene_failure(index, scene, stage, error, partial)
    row.update(
        population=population_name(index, plan),
        requested_tolerance=requested_tolerance(scene, plan),
    )
    for query in row["queries"]:
        query.update(estimate_coverage_passed=False, requested_tolerance_passed=False)
    return row


def exact_determinant_normalizer(h):
    """Independent exact dyadic Laplace determinant of this oracle's own map.

    Fraction-to-float conversion error is measured exactly. The log allowance
    below is an explicit engineering guard for libm/reduction, not certification.
    It is unrelated to the production implementation and contains no LU call.
    """
    matrix = [[Fraction.from_float(float(v)) for v in row] for row in h]
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, i, j = matrix[2]
    exact = a * (e * j - f * i) - b * (d * j - f * g) + c * (d * i - e * g)
    if exact == 0:
        raise BASE.OracleUnresolved("independent operational map has exact zero determinant")
    absolute = abs(exact)
    rounded = float(absolute)
    if not math.isfinite(rounded) or rounded <= 0:
        raise BASE.OracleUnresolved("independent determinant cannot be represented")
    relative_exact = abs(Fraction.from_float(rounded) - absolute) / absolute
    conversion = 0.0 if relative_exact == 0 else math.nextafter(float(relative_exact), math.inf)
    if not 0 <= conversion < 1:
        raise BASE.OracleUnresolved("independent determinant conversion is unresolved")
    logarithm = math.log(rounded)
    log_conversion = conversion / (1 - conversion)
    log_arithmetic = 8 * EPS * abs(logarithm)
    return (
        logarithm,
        log_conversion + log_arithmetic,
        {
            "method": "independent_exact_fraction_laplace_3x3",
            "signed_fraction": f"{exact.numerator}/{exact.denominator}",
            "rounded_absolute": rounded,
            "rounded_absolute_hex": rounded.hex(),
            "conversion_relative_error_fraction": f"{relative_exact.numerator}/{relative_exact.denominator}",
            "conversion_relative_error_upward_float": conversion,
            "log_absolute": logarithm,
            "log_conversion_allowance": log_conversion,
            "log_arithmetic_estimate": log_arithmetic,
            "scope": "Own represented localized map; does not certify map construction or libm.",
        },
    )


def oracle_geometry(scene):
    """Independent local map, exact determinant and scalar 2-D Cholesky."""
    normal = NP.asarray(scene["normal"], dtype=float)
    tangent = NP.array([-normal[1], normal[0]])
    radius, fraction = float(scene["radius"]), float(scene["fraction"])
    half_chord = radius * math.sqrt((1 - fraction) * (1 + fraction))
    h = NP.asarray(scene["homography"], dtype=float)
    scale = float(NP.max(NP.abs(h)))
    if not math.isfinite(scale) or scale <= 0:
        raise BASE.OracleUnresolved("unrepresentable independent map scale")
    h = (h / scale).copy()
    centre = NP.asarray(scene["centre"], dtype=float)
    h[:, 2] = NP.array([math.fsum((BASE.dot(row[:2], centre), float(row[2]))) for row in h])
    chord = radius * fraction * normal
    midpoint_w = math.fsum((BASE.dot(h[2, :2], chord), float(h[2, 2])))
    if midpoint_w < 0:
        h = -h
    chart = float(h[2, 2]) + BASE.support_minimum(
        h[2, :2],
        normal,
        tangent,
        radius,
        fraction,
        half_chord,
    )
    if not chart > 0:
        raise BASE.OracleUnresolved("independent whole-material chart reaches horizon")
    log_determinant, log_det_error, det_record = exact_determinant_normalizer(h)
    covariance = scene["covariance"]
    a, b, b2, d = map(
        float, (covariance[0][0], covariance[0][1], covariance[1][0], covariance[1][1])
    )
    if b != b2 or a <= 0:
        raise BASE.OracleUnresolved("independent covariance is not symmetric positive definite")
    l00 = math.sqrt(a)
    l10 = b / l00
    remainder = math.fsum((d, -l10 * l10))
    if remainder <= 0:
        raise BASE.OracleUnresolved("independent covariance factor is unresolved")
    l11 = math.sqrt(remainder)
    density_terms = [-math.log(math.tau), -math.log(l00), -math.log(l11)]
    log_density = math.fsum(density_terms)
    log_error = math.fsum((log_det_error, 8 * EPS * math.fsum(abs(t) for t in density_terms)))
    relative_error = math.expm1(log_error)
    if not math.isfinite(relative_error):
        raise BASE.OracleUnresolved("independent normalizer error is unrepresentable")
    normalizer_record = {
        "determinant": det_record,
        "density_log_terms": density_terms,
        "density_log": log_density,
        "combined_log_error_estimate": log_error,
        "normalizer_relative_error_estimate": relative_error,
        "cholesky_factors": [[l00, 0.0], [l10, l11]],
        "scope": "Engineering conversion/log guard of represented map/factors; not a certified Cholesky or point-coordinate enclosure.",
    }
    NORMALIZER_RECORDS[scene["id"]] = normalizer_record
    return {
        "h": h,
        "chord": chord,
        "tangent": tangent,
        "half_chord": half_chord,
        "l00": l00,
        "l10": l10,
        "l11": l11,
        "log_determinant": log_determinant,
        "log_density": log_density,
        "normalizer_relative_error_estimate": relative_error,
        "whole_material_chart_minimum": chart,
    }


def direct_rule(geometry, point, start, end, order):
    """Independent source-s density nodes, not the production moment formula."""
    nodes, weights = BASE.rule(order)
    half, middle = (end - start) / 2, (start + end) / 2
    signed_s = middle + half * nodes
    local = geometry["chord"] + signed_s[:, None] * geometry["tangent"]
    h = geometry["h"]
    w = local @ h[2, :2] + h[2, 2]
    if NP.any(w <= 0):
        raise BASE.OracleUnresolved("independent quadrature reaches horizon")
    matrix = h[:2] - NP.asarray(point)[:, None] * h[2]
    numerator = local @ matrix[:, :2].T + matrix[:, 2]
    x = numerator[:, 0] / (w * geometry["l00"])
    y = (numerator[:, 1] / w - geometry["l10"] * x) / geometry["l11"]
    values = NP.zeros(order)
    active = signed_s != 0
    with NP.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        logarithm = (
            math.log(half)
            + geometry["log_density"]
            + geometry["log_determinant"]
            + NP.log(NP.abs(signed_s[active]))
            + NP.log(weights[active])
            - 3 * NP.log(w[active])
            - (x[active] * x[active] + y[active] * y[active]) / 2
        )
        values[active] = -NP.sign(signed_s[active]) * NP.exp(logarithm)
    if not NP.isfinite(values).all():
        raise BASE.OracleUnresolved("unrepresentable independent quadrature contributions")
    answer = math.fsum(float(v) for v in values)
    absolute = math.fsum(abs(float(v)) for v in values)
    error = absolute * (128 * EPS + geometry["normalizer_relative_error_estimate"])
    return answer, max(SMALLEST, error) if absolute > 0 else 0.0


def initialize_models():
    global NP
    import numpy

    NP = numpy
    BASE.NP = numpy
    # Only this isolated V1-helper module instance is adapted; no file changes.
    BASE.oracle_geometry = oracle_geometry
    BASE.direct_rule = direct_rule
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("backend.finite_normal")


def direct_oracle(scene, pixel, plan):
    NORMALIZER_RECORDS.pop(scene["id"], None)
    result = BASE.direct_oracle(scene, pixel, plan["oracle"], plan["algorithm_resolution_guards"])
    try:
        result["normalizer"] = NORMALIZER_RECORDS.get(scene["id"])
        result["roundoff_scope"] = (
            "Local128eps absolute-node sum plus independent determinant conversion/log estimate and32eps final absolute-leaf reduction; no certified enclosure."
        )
        result["local_roundoff_estimates"] = dict(result["roundoff_estimates"])
        result["final_reduction_estimates"] = {}
        result["tail_envelopes_by_order"] = {
            str(o): result["tail_envelope_sum"] for o in plan["oracle"]["orders"]
        }
        if result.get("oracle_converged", False):
            for order in plan["oracle"]["orders"]:
                key = str(order)
                absolute = math.fsum(
                    abs(p["values"][key])
                    for p in result["leaf_panels"]
                    if p["method"] == "direct_source_s"
                )
                reduction = 32 * EPS * absolute
                result["final_reduction_estimates"][key] = reduction
                result["roundoff_estimates"][key] = math.fsum(
                    (result["roundoff_estimates"][key], reduction)
                )
        return BASE.json_ready(result)
    except Exception as error:
        return BASE.failed_record({}, "oracle_v2_error_accounting", error, result)


def coverage(candidate_value, candidate_error, tolerance, oracle, orders):
    """Frozen estimated-error and requested-tolerance comparisons, separately."""
    high = oracle["values"][str(orders[-1])]
    tail = oracle["tail_envelopes_by_order"]
    components = {
        "oracle_roundoff192": oracle["roundoff_estimates"][str(orders[-1])],
        "twice_order_delta": 2 * oracle["order_delta"],
        "tail96": tail[str(orders[0])],
        "tail192": tail[str(orders[-1])],
        "oracle_final_relative_roundoff": 32 * EPS * abs(high),
    }
    if not oracle.get("oracle_converged", False) or oracle.get("status") != "resolved":
        raise ValueError("comparison requires a resolved, converged independent oracle")
    numbers = (candidate_value, candidate_error, tolerance, high, *components.values())
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in numbers
    ):
        raise ValueError("comparison quantities must be finite real numbers")
    if (
        not 0 <= candidate_error <= tolerance
        or tolerance <= 0
        or any(v < 0 for v in components.values())
    ):
        raise ValueError("comparison requires nonnegative errors within requested tolerance")
    oracle_allowance = math.fsum(components.values())
    delta = abs(candidate_value - high)
    estimated_limit = math.fsum((candidate_error, oracle_allowance))
    requested_limit = math.fsum((tolerance, oracle_allowance))
    return {
        "comparison_delta": delta,
        "oracle_allowance_components": components,
        "oracle_allowance": oracle_allowance,
        "estimate_coverage_allowance": estimated_limit,
        "requested_tolerance_allowance": requested_limit,
        "estimate_coverage_passed": delta <= estimated_limit,
        "requested_tolerance_passed": delta <= requested_limit,
        "comparison_passed": delta <= estimated_limit and delta <= requested_limit,
    }


def run_scene(index, scene, plan, api):
    identity = {
        "index": index,
        "id": scene["id"],
        "kind": scene["kind"],
        "input": scene,
        "population": population_name(index, plan),
        "requested_tolerance": requested_tolerance(scene, plan),
    }
    row = {**identity, "candidate": None, "queries": [], "protocol_passed": False}
    started = time.perf_counter()
    controls = {**plan["operator"], "probability_tolerance": identity["requested_tolerance"]}
    try:
        row["candidate"] = BASE.candidate_record(api, scene, controls)
    except Exception as error:
        row["candidate_failure"] = {"stage": "candidate_api", **BASE.exception_record(error)}
    for i, pixel in enumerate(scene["pixels_xy"]):
        qid = {
            "query_index": i,
            "pixel": pixel,
            "roles": [r["role"] for r in scene["query_roles"] if r["query_index"] == i],
        }
        query = {
            **qid,
            "comparison_passed": False,
            "estimate_coverage_passed": False,
            "requested_tolerance_passed": False,
        }
        try:
            oracle = direct_oracle(scene, pixel, plan)
            query["oracle"] = oracle
            candidate = row["candidate"]
            if candidate is not None:
                query["candidate"] = {
                    "value": candidate["derivatives"][i],
                    "estimated_error": candidate["estimated_errors"][i],
                    "status": candidate["statuses"][i],
                    "method": candidate["query_methods"][i],
                }
                if candidate["statuses"][i] == "resolved" and oracle.get("oracle_converged", False):
                    query.update(
                        coverage(
                            candidate["derivatives"][i],
                            candidate["estimated_errors"][i],
                            identity["requested_tolerance"],
                            oracle,
                            plan["oracle"]["orders"],
                        )
                    )
            row["queries"].append(BASE.json_ready(query))
        except Exception as error:
            row["queries"].append(BASE.failed_record(qid, "query_comparison", error, query))
    row["runtime_seconds"] = time.perf_counter() - started
    row["protocol_passed"] = all(q["comparison_passed"] for q in row["queries"])
    row["status"] = "passed" if row["protocol_passed"] else "protocol_failure"
    try:
        return BASE.json_ready(row)
    except Exception as error:
        return scene_failure(index, scene, plan, "scene_serialization", error, row)


def population_summary(rows, name):
    selected = [r for r in rows if r["population"] == name]
    queries = [q for r in selected for q in r["queries"]]
    return {
        "scenes": len(selected),
        "queries": len(queries),
        "scene_passes": sum(r["protocol_passed"] for r in selected),
        "query_passes": sum(q.get("comparison_passed", False) for q in queries),
        "estimate_coverage_passes": sum(q.get("estimate_coverage_passed", False) for q in queries),
        "requested_tolerance_passes": sum(
            q.get("requested_tolerance_passed", False) for q in queries
        ),
        "unknown_or_failed_queries": sum(not q.get("comparison_passed", False) for q in queries),
    }


def summarize(rows, area_rows, plan):
    queries = [q for r in rows for q in r["queries"]]
    area_queries = [q for r in area_rows for q in r["queries"]]
    declared = plan["declared_population"]
    result = {
        "planned_scenes": declared["total_scenes"],
        "retained_scenes": len(rows),
        "planned_queries": declared["total_queries"],
        "retained_queries": len(queries),
        "scene_passes": sum(r["protocol_passed"] for r in rows),
        "query_passes": sum(q.get("comparison_passed", False) for q in queries),
        "estimate_coverage_passes": sum(q.get("estimate_coverage_passed", False) for q in queries),
        "requested_tolerance_passes": sum(
            q.get("requested_tolerance_passed", False) for q in queries
        ),
        "oracle_converged_queries": sum(
            q.get("oracle", {}).get("oracle_converged", False) for q in queries
        ),
        "positive_area_scenes": len(area_rows),
        "positive_area_queries": len(area_queries),
        "positive_area_passes": sum(q["protocol_passed"] for q in area_queries),
        "all_scenes_and_queries_retained": len(rows) == declared["total_scenes"]
        and len(queries) == declared["total_queries"],
        "all_area_queries_retained": len(area_rows) == declared["area_scenes"]
        and len(area_queries) == declared["area_queries"],
        "unit_private_branch_controls_executed_here": False,
        "optimizer_calls": 0,
        "renderer_calls": 0,
        "residual_or_photo_archive_analyses": 0,
    }
    result["by_population"] = {
        name: population_summary(rows, name)
        for name in ("post_hoc_synthetic_regression", "prospective_new_synthetic")
    }
    old_ids = {r["id"] for r in rows if r["population"] == "post_hoc_synthetic_regression"}
    result["positive_area_by_population"] = {
        "old_regression_queries": sum(
            len(r["queries"]) for r in area_rows if r["scene_id"] in old_ids
        ),
        "old_regression_passes": sum(
            q["protocol_passed"]
            for r in area_rows
            if r["scene_id"] in old_ids
            for q in r["queries"]
        ),
        "new_prospective_queries": sum(
            len(r["queries"]) for r in area_rows if r["scene_id"] not in old_ids
        ),
        "new_prospective_passes": sum(
            q["protocol_passed"]
            for r in area_rows
            if r["scene_id"] not in old_ids
            for q in r["queries"]
        ),
    }
    return result


def bootstrap_failure(plan, scenes, error):
    rows = [scene_failure(i, scene, plan, "study_startup", error) for i, scene in enumerate(scenes)]
    by_id = {s["id"]: s for s in scenes}
    area_rows = [
        BASE.area_failure(selection, by_id[selection["scene_id"]], "study_startup", error)
        for selection in plan["positive_area_corroboration"]["selection"]
    ]
    result = {
        "format": "pictures-to-cad-finite-normal-error-control-result",
        "version": 2,
        "plan_sha256": PLAN_SHA256,
        "software_preflight_addendum": software_preflight_addendum(),
        "stage": "study_startup",
        "error": BASE.exception_record(error),
        "rows": rows,
        "positive_area": area_rows,
        "summary": summarize(rows, area_rows, plan),
        "protocol_passed": False,
        "source_unchanged": False,
    }
    for name in ("source_before", "source_after"):
        try:
            result[name] = source_hashes(plan)
        except Exception as source_error:
            result[name] = None
            result[f"{name}_failure"] = BASE.exception_record(source_error)
    return BASE.json_ready(result)


def run_study(plan, scenes, *, api=None, area_helper=None):
    started = time.perf_counter()
    before = source_hashes(plan)
    setup_errors = {}
    try:
        api = initialize_models() if api is None else api
    except Exception as error:
        setup_errors["candidate_import"] = error
    try:
        helper = (
            BASE.load_helper(ROOT / plan["positive_area_corroboration"]["helper"])
            if area_helper is None
            else area_helper
        )
    except Exception as error:
        setup_errors["area_helper_import"] = error
        helper = None
    rows = []
    for i, scene in enumerate(scenes):
        try:
            if "candidate_import" in setup_errors:
                raise setup_errors["candidate_import"]
            row = run_scene(i, scene, plan, api)
        except Exception as error:
            row = scene_failure(i, scene, plan, "scene_execution", error)
        rows.append(row)
        print(
            f"scene {i + 1}/{len(scenes)} {scene['id']}: {row['status']}",
            file=sys.stderr,
            flush=True,
        )
    by_id = {r["id"]: r for r in rows}
    scenes_by_id = {s["id"]: s for s in scenes}
    area_rows = []
    for selection in plan["positive_area_corroboration"]["selection"]:
        scene = scenes_by_id[selection["scene_id"]]
        try:
            if "area_helper_import" in setup_errors:
                raise setup_errors["area_helper_import"]
            if NP is None:
                raise RuntimeError("numerical support unavailable")
            row = BASE.area_check(
                scene, selection, plan, helper, by_id[scene["id"]].get("candidate")
            )
        except Exception as error:
            row = BASE.area_failure(selection, scene, "positive_area_execution", error)
        area_rows.append(row)
        print(
            f"area {scene['id']}: {'passed' if row['protocol_passed'] else 'failed'}",
            file=sys.stderr,
            flush=True,
        )
    after_error = None
    try:
        after = source_hashes(plan)
    except Exception as error:
        after, after_error = None, BASE.exception_record(error)
    summary = summarize(rows, area_rows, plan)
    passed = (
        before == after
        and summary["all_scenes_and_queries_retained"]
        and summary["all_area_queries_retained"]
        and all(r["protocol_passed"] for r in rows)
        and all(r["protocol_passed"] for r in area_rows)
    )
    return BASE.json_ready(
        {
            "format": "pictures-to-cad-finite-normal-error-control-result",
            "version": 2,
            "plan_sha256": PLAN_SHA256,
            "software_preflight_addendum": software_preflight_addendum(),
            "runner_sha256": before[RUNNER.relative_to(ROOT).as_posix()]["sha256"],
            "api_file_sha256": before[API_PATH]["sha256"],
            "v1_helper_sha256": before[V1_RUNNER]["sha256"],
            "positive_area_helper_sha256": before[plan["positive_area_corroboration"]["helper"]][
                "sha256"
            ],
            "source_before": before,
            "source_after": after,
            "source_unchanged": before == after,
            "source_after_failure": after_error,
            "revision": BASE.revision(),
            "versions": {
                "python": platform.python_version(),
                "numpy": None if NP is None else NP.__version__,
            },
            "setup_failures": {
                key: BASE.exception_record(error) for key, error in setup_errors.items()
            },
            "settings": {
                key: plan[key]
                for key in (
                    "operator",
                    "oracle",
                    "algorithm_resolution_guards",
                    "positive_area_corroboration",
                )
            },
            "oracle_reuse": {
                "immutable_helper": V1_RUNNER,
                "isolated_module_only": True,
                "reused": [
                    "source-s cuts/panels/endpoints",
                    "96/192 rules",
                    "retention/strict candidate contract",
                    "positive-area checks",
                ],
                "replaced": [
                    "independent exact determinant/normalizer",
                    "source-s rule error",
                    "final reduction allowance",
                    "both strong coverage comparisons",
                ],
                "old_oracle_numeric_results_assumed_unchanged": False,
            },
            "rows": rows,
            "positive_area": area_rows,
            "summary": summary,
            "protocol_passed": passed,
            "runtime_seconds": time.perf_counter() - started,
            "scope": "337post-hoc synthetic regressions and80prospective new scenes under supplied H/Gaussian covariance. No optimizer, renderer, physical calibration, automatic integration or old residual/photo-archive analysis. Engineering error estimates are not certificates.",
        }
    )


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, metavar="NEW_JSON")
    args = parser.parse_args(arguments)
    try:
        output = validate_output(args.output)
        plan, scenes = load_context()
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    with os.fdopen(descriptor, "w") as stream:
        try:
            result = run_study(plan, scenes)
        except Exception as error:
            result = bootstrap_failure(plan, scenes, error)
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
    print(
        json.dumps(
            {
                "output": str(output),
                "protocol_passed": result["protocol_passed"],
                "summary": result.get("summary"),
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0 if result.get("protocol_passed", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
