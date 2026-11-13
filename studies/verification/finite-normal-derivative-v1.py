#!/usr/bin/env python3
"""Replay the frozen finite-chord normal-derivative qualification.

Required --output NEW_JSON is refused before numerical imports or analysis if
the destination exists (including a dangling symlink) or its parent is absent.
The direct source-s oracle uses no production private helper or moment formula.
An unchanged positive-area helper supplies the separately scoped angular-FD
corroboration. This experiment performs no fit, renderer or archived-data replay.
Floating guards and quadrature comparisons are not certified error bounds or
physical camera qualification. All planned scenes and queries are retained.
"""

# Every broad catch records a protocol failure; it cannot qualify unknown data.
# ruff: noqa: BLE001

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import itertools
import json
import math
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-normal-derivative-v1.json"
SUPPLEMENT = ROOT / "studies/finite-normal-derivative-compressed-chart-v1.json"
PLAN_SHA256 = "d31b8ad03b5fe1af8b69dc47be5445b2ebf7034e951254814a57010f3b43de9f"
SUPPLEMENT_SHA256 = "f0bc2095ba23cceb2ffb13d7f915051620cd2496f71a43ebfd0d2f951037e234"
API_PATH = "backend/finite_normal.py"
NP = None  # Numerical imports occur only after CLI/input/output preflight.
RULES = {}
SMALLEST = math.nextafter(0.0, 1.0)


class OracleUnresolved(ArithmeticError):
    """An explicitly retained numerical/work-limit oracle outcome."""

    def __init__(self, message, *, status="numerical_unknown"):
        super().__init__(message)
        self.status = status


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"nonfinite JSON literal: {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("JSON float is not representable as finite float64")
        return number

    return json.loads(
        Path(path).read_text(),
        object_pairs_hook=pairs,
        parse_constant=nonfinite,
        parse_float=finite_float,
    )


def json_ready(value):
    """Validate the saved representation; never turn nonfinite floats into text."""
    return json.loads(json.dumps(value, allow_nan=False))


def exception_record(error):
    return {"type": type(error).__name__, "message": str(error)[:4096]}


def withhold_pass_claims(value):
    """Retained nested diagnostics cannot remain qualified after a row failure."""
    if isinstance(value, dict):
        return {
            key: (
                False
                if key.endswith("passed") or key in {"oracle_converged", "candidate_resolved"}
                else withhold_pass_claims(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [withhold_pass_claims(item) for item in value]
    return value


def failed_record(identity, stage, error, partial=None):
    """Withhold unsafe whole fields and reset pass flags after a late failure."""
    result = dict(identity)
    withheld = []
    for key, value in (partial or {}).items():
        if key in identity:
            continue
        try:
            result[key] = withhold_pass_claims(json_ready(value))
        except (TypeError, ValueError, OverflowError):
            withheld.append(key)
    result.update(
        status="execution_failure",
        stage=stage,
        error=exception_record(error),
        protocol_passed=False,
        comparison_passed=False,
        oracle_converged=False,
    )
    if withheld:
        result["withheld_unsafe_fields"] = sorted(withheld)
    return json_ready(result)


def scene_failure(index, scene, stage, error, partial=None):
    identity = {"index": index, "id": scene["id"], "kind": scene["kind"], "input": scene}
    result = failed_record(identity, stage, error, partial)
    previous = {q.get("query_index"): q for q in (partial or {}).get("queries", [])}
    result["queries"] = [
        failed_record(
            {
                "query_index": i,
                "pixel": pixel,
                "roles": [r["role"] for r in scene["query_roles"] if r["query_index"] == i],
            },
            stage,
            error,
            previous.get(i),
        )
        for i, pixel in enumerate(scene["pixels_xy"])
    ]
    return result


def area_failure(selection, scene, stage, error, partial=None):
    result = failed_record(
        {"scene_id": scene["id"], "query_indices": selection["query_indices"]},
        stage,
        error,
        partial,
    )
    previous = {q.get("query_index"): q for q in (partial or {}).get("queries", [])}
    result["queries"] = [
        failed_record(
            {"query_index": i, "pixel": scene["pixels_xy"][i]}, stage, error, previous.get(i)
        )
        for i in selection["query_indices"]
    ]
    return result


def validate_output(path):
    path = Path(path).absolute()
    if os.path.lexists(path):
        raise ValueError("output must be a new path, including no existing symlink")
    if not path.parent.is_dir():
        raise ValueError("output parent directory must already exist")
    return path


def load_plans():
    if sha(PLAN) != PLAN_SHA256 or sha(SUPPLEMENT) != SUPPLEMENT_SHA256:
        raise ValueError("frozen plan hash differs")
    plan, extra = strict_json(PLAN), strict_json(SUPPLEMENT)
    if extra["main_plan_sha256"] != PLAN_SHA256:
        raise ValueError("supplement does not bind the main frozen plan")
    scenes = [*plan["scenes"], *extra["scenes"]]
    population = extra["declared_population"]
    if len(scenes) != population["total_scenes"]:
        raise ValueError("planned scene population differs")
    if sum(len(s["pixels_xy"]) for s in scenes) != population["total_queries"]:
        raise ValueError("planned query population differs")
    if len({s["id"] for s in scenes}) != len(scenes):
        raise ValueError("duplicate planned scene IDs")
    for scene in scenes:
        pixels = scene["pixels_xy"]
        if len({tuple(p) for p in pixels}) != len(pixels):
            raise ValueError("scene pixels were not deduplicated")
        for role in scene["query_roles"]:
            if pixels[role["query_index"]] != role["pixel"]:
                raise ValueError("query role mapping differs from frozen pixels")
    for name, expected in plan["inputs_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"frozen input differs: {name}")
    return plan, extra, scenes


def source_hashes(plan):
    # Includes the complete backend Python import closure, not only API source.
    paths = {p.relative_to(ROOT).as_posix() for p in (ROOT / "backend").rglob("*.py")}
    paths.update(plan["inputs_sha256"])
    paths.update(
        (
            API_PATH,
            PLAN.relative_to(ROOT).as_posix(),
            SUPPLEMENT.relative_to(ROOT).as_posix(),
            RUNNER.relative_to(ROOT).as_posix(),
            "pyproject.toml",
            "uv.lock",
        )
    )
    return {
        name: {"sha256": sha(ROOT / name), "bytes": (ROOT / name).stat().st_size}
        for name in sorted(paths)
    }


def load_helper(path):
    spec = importlib.util.spec_from_file_location("finite_normal_independent_area_v1", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load the independently pinned positive-area helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def numerical_imports():
    global NP
    import numpy

    NP = numpy
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("backend.finite_normal")


def rule(order):
    if order not in RULES:
        RULES[order] = NP.polynomial.legendre.leggauss(order)
    return RULES[order]


def dot(a, b):
    return math.fsum(float(x) * float(y) for x, y in zip(a, b, strict=True))


def determinant3(h):
    a, b, c = map(float, h[0])
    d, e, f = map(float, h[1])
    g, i, j = map(float, h[2])
    return math.fsum((a * e * j, b * f * g, c * d * i, -c * e * g, -b * d * j, -a * f * i))


def support_minimum(line, normal, tangent, radius, fraction, half_chord):
    magnitude = math.hypot(*line)
    if magnitude == 0:
        return 0.0
    along = dot(line, normal)
    if -along / magnitude <= fraction:
        return -radius * magnitude
    return radius * fraction * along - half_chord * abs(dot(line, tangent))


def oracle_geometry(scene):
    """Independent local map and scalar 2-D Cholesky; no production helper."""
    normal = NP.asarray(scene["normal"], dtype=float)
    tangent = NP.array([-normal[1], normal[0]])
    radius, fraction = float(scene["radius"]), float(scene["fraction"])
    half_chord = radius * math.sqrt((1 - fraction) * (1 + fraction))
    raw_h = NP.asarray(scene["homography"], dtype=float)
    scale = float(NP.max(NP.abs(raw_h)))
    if not scale > 0 or not math.isfinite(scale):
        raise OracleUnresolved("unrepresentable independent map scale")
    h = raw_h / scale
    centre = NP.asarray(scene["centre"], dtype=float)
    h = h.copy()
    h[:, 2] = NP.array([math.fsum((dot(row[:2], centre), float(row[2]))) for row in h])
    chord = radius * fraction * normal
    midpoint_w = math.fsum((dot(h[2, :2], chord), float(h[2, 2])))
    if midpoint_w < 0:
        h = -h
    chart_minimum = float(h[2, 2]) + support_minimum(
        h[2, :2],
        normal,
        tangent,
        radius,
        fraction,
        half_chord,
    )
    if not chart_minimum > 0:
        raise OracleUnresolved("independent whole-material chart reaches a horizon")
    determinant = abs(determinant3(h))
    covariance = scene["covariance"]
    a, b, b2, d = map(
        float, (covariance[0][0], covariance[0][1], covariance[1][0], covariance[1][1])
    )
    if b != b2 or not a > 0:
        raise OracleUnresolved("independent covariance is not symmetric positive definite")
    l00 = math.sqrt(a)
    l10 = b / l00
    remainder = math.fsum((d, -l10 * l10))
    if not remainder > 0 or not determinant > 0:
        raise OracleUnresolved("independent map/covariance is singular")
    l11 = math.sqrt(remainder)
    return {
        "h": h,
        "chord": chord,
        "tangent": tangent,
        "half_chord": half_chord,
        "l00": l00,
        "l10": l10,
        "l11": l11,
        "log_determinant": math.log(determinant),
        "log_density": -math.log(math.tau) - math.log(l00) - math.log(l11),
        "whole_material_chart_minimum": chart_minimum,
    }


def endpoint(geometry, point, s):
    local = geometry["chord"] + s * geometry["tangent"]
    h = geometry["h"]
    w = math.fsum((dot(h[2, :2], local), float(h[2, 2])))
    if not w > 0:
        raise OracleUnresolved("independent chord endpoint reaches a horizon")
    numerator = [math.fsum((dot(h[i, :2], local), float(h[i, 2]), -point[i] * w)) for i in range(2)]
    x = numerator[0] / (w * geometry["l00"])
    y = (numerator[1] / w - geometry["l10"] * x) / geometry["l11"]
    if not all(math.isfinite(v) for v in (x, y, w)):
        raise OracleUnresolved("unrepresentable independent endpoint")
    return NP.array([x, y]), w


def initial_cuts(geometry, point, multipliers):
    ell = geometry["half_chord"]
    left, w_left = endpoint(geometry, point, -ell)
    right, w_right = endpoint(geometry, point, ell)
    difference = right - left
    length = math.hypot(*difference)
    if not length > 0 or not math.isfinite(length):
        raise OracleUnresolved("unresolved independent image chord length")
    direction = difference / length
    closest = min(1.0, max(0.0, -dot(left, direction) / length))
    cuts = {-ell, 0.0, ell}
    for distance in (0.0, *(sign * k for k in multipliers for sign in (-1, 1))):
        image_fraction = closest + distance / length
        if not 0 < image_fraction < 1:
            continue
        # Projective endpoint interpolation, independent of the moment/z formula.
        denominator = math.fsum(((1 - image_fraction) * w_right, image_fraction * w_left))
        source_fraction = image_fraction * w_left / denominator
        source_s = math.fsum((-ell, 2 * ell * source_fraction))
        if -ell < source_s < ell:
            cuts.add(source_s)
    return sorted(cuts)


def panel_geometry(geometry, point, start, end):
    left, wl = endpoint(geometry, point, start)
    right, wr = endpoint(geometry, point, end)
    difference = right - left
    travel = math.hypot(*difference)
    if travel > 0:
        direction = difference / travel
        along = dot(left, direction)
        location = min(travel, max(0.0, -along))
        minimum_distance = math.hypot(*(left + location * direction))
        other_along = dot(right, direction)
        maximum_along = max(abs(along), abs(other_along))
        minimum_along = 0.0 if along <= 0 <= other_along else min(abs(along), abs(other_along))
        exponent_variation = (maximum_along - minimum_along) * ((maximum_along + minimum_along) / 2)
    else:
        minimum_distance, exponent_variation = math.hypot(*left), 0.0
    log_bound = (
        math.log(end - start)
        + math.log(max(abs(start), abs(end)))
        + geometry["log_determinant"]
        - 3 * math.log(min(wl, wr))
        + geometry["log_density"]
        - minimum_distance * minimum_distance / 2
    )
    return {
        "start": start,
        "end": end,
        "whitened_travel": travel,
        "gaussian_exponent_variation": exponent_variation,
        "denominator_ratio": max(wl, wr) / min(wl, wr),
        "minimum_whitened_segment_distance": minimum_distance,
        "log_absolute_tail_envelope": log_bound,
    }


def direct_rule(geometry, point, start, end, order):
    nodes, weights = rule(order)
    half, middle = (end - start) / 2, (start + end) / 2
    signed_s = middle + half * nodes
    local = geometry["chord"] + signed_s[:, None] * geometry["tangent"]
    h = geometry["h"]
    w = local @ h[2, :2] + h[2, 2]
    if NP.any(w <= 0):
        raise OracleUnresolved("independent quadrature reaches a horizon")
    # Difference before whitening, retaining local geometry throughout.
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
        raise OracleUnresolved("unrepresentable independent quadrature contributions")
    answer = math.fsum(float(v) for v in values)
    absolute = math.fsum(abs(float(v)) for v in values)
    return answer, 128 * sys.float_info.epsilon * absolute


def direct_oracle(scene, pixel, settings, guards):
    """Return both fixed-order integrals; all attempted work remains recorded."""
    result = {
        "status": "numerical_unknown",
        "orders": settings["orders"],
        "values": {str(o): None for o in settings["orders"]},
        "roundoff_estimates": {str(o): None for o in settings["orders"]},
        "evaluations": 0,
        "endpoint_evaluations": 0,
        "rule_evaluations": {str(o): 0 for o in settings["orders"]},
        "panels_inspected": 0,
        "leaf_panels": [],
        "tail_envelope_sum": 0.0,
        "oracle_converged": False,
    }
    sums = {o: [] for o in settings["orders"]}
    errors = {o: [] for o in settings["orders"]}
    try:
        geometry = oracle_geometry(scene)
        result["whole_material_chart_minimum"] = geometry["whole_material_chart_minimum"]
        point = (float(pixel[0]) + 0.5, float(pixel[1]) + 0.5)
        result["evaluations"] += 2
        result["endpoint_evaluations"] += 2
        cuts = initial_cuts(geometry, point, settings["line_distance_multipliers"])
        result["initial_source_cuts"] = cuts
        result["initial_panel_count"] = len(cuts) - 1
        tail_leaf = 1e-13 / result["initial_panel_count"]
        result["per_panel_tail_threshold"] = tail_leaf
        pending = list(reversed(list(itertools.pairwise(cuts))))
        while pending:
            if result["panels_inspected"] >= settings["maximum_panels"]:
                raise OracleUnresolved("independent panel limit", status="work_limit")
            if result["evaluations"] + 2 > settings["maximum_evaluations_per_query"]:
                raise OracleUnresolved("independent endpoint-work limit", status="work_limit")
            start, end = pending.pop()
            result["panels_inspected"] += 1
            result["evaluations"] += 2
            result["endpoint_evaluations"] += 2
            panel = panel_geometry(geometry, point, start, end)
            log_bound = panel["log_absolute_tail_envelope"]
            if log_bound <= math.log(tail_leaf):
                bound = max(SMALLEST, math.exp(log_bound))
                if math.fsum((result["tail_envelope_sum"], bound)) <= 1e-13:
                    result["tail_envelope_sum"] = math.fsum((result["tail_envelope_sum"], bound))
                    panel.update(method="bounded_tail", absolute_tail_envelope=bound)
                    # -inf is a legitimate logarithmic zero bound but not JSON.
                    if not math.isfinite(log_bound):
                        panel["log_absolute_tail_envelope"] = None
                        panel["log_envelope_below_float_range"] = True
                    result["leaf_panels"].append(panel)
                    continue
            resolved = (
                panel["whitened_travel"] <= guards["maximum_whitened_panel_travel"]
                and panel["gaussian_exponent_variation"]
                <= guards["maximum_gaussian_exponent_variation"]
                and panel["denominator_ratio"] <= guards["maximum_denominator_ratio"]
            )
            if resolved:
                required = sum(settings["orders"])
                if result["evaluations"] + required > settings["maximum_evaluations_per_query"]:
                    raise OracleUnresolved("independent rule-work limit", status="work_limit")
                panel.update(method="direct_source_s", values={}, roundoff_estimates={})
                for order in settings["orders"]:
                    result["evaluations"] += order
                    result["rule_evaluations"][str(order)] += order
                    value, error = direct_rule(geometry, point, start, end, order)
                    sums[order].append(value)
                    errors[order].append(error)
                    panel["values"][str(order)] = value
                    panel["roundoff_estimates"][str(order)] = error
                result["leaf_panels"].append(panel)
            else:
                middle = start + (end - start) / 2
                if middle == start or middle == end:
                    raise OracleUnresolved("independent partition reached float resolution")
                pending.extend(((middle, end), (start, middle)))
        for order in settings["orders"]:
            result["values"][str(order)] = math.fsum(sums[order])
            result["roundoff_estimates"][str(order)] = math.fsum(errors[order])
        low, high = (result["values"][str(o)] for o in settings["orders"])
        delta = abs(high - low)
        allowance = settings["order_agreement_abs"] + settings["order_agreement_rel"] * abs(high)
        result.update(
            status="resolved" if delta <= allowance else "order_disagreement",
            order_delta=delta,
            order_allowance=allowance,
            oracle_converged=delta <= allowance,
        )
    except OracleUnresolved as error:
        result.update(status=error.status, error=exception_record(error))
    except Exception as error:
        result.update(status="protocol_failure", error=exception_record(error))
    result["partial_integrals"] = {str(o): math.fsum(sums[o]) for o in settings["orders"]}
    result["work_scope"] = (
        "all initial/panel endpoint maps plus all attempted 96/192 density nodes, per query"
    )
    try:
        return json_ready(result)
    except (TypeError, ValueError, OverflowError) as error:
        return failed_record({}, "oracle_serialization", error, result)


def candidate_record(api, scene, controls):
    answer = api.circular_segment_normal_derivative(
        scene["pixels_xy"],
        scene["radius"],
        scene["fraction"],
        centre=scene["centre"],
        normal=scene["normal"],
        sensor_shape=scene["sensor_shape"],
        homography=scene["homography"],
        psf_covariance=scene["covariance"],
        probability_tolerance=controls["probability_tolerance"],
        max_panels=controls["max_panels"],
        max_evaluations=controls["max_evaluations"],
    )
    if not is_dataclass(answer):
        raise TypeError("candidate result must be its declared dataclass")
    saved = json_ready(asdict(answer))
    size = len(scene["pixels_xy"])
    for key in (
        "derivatives",
        "statuses",
        "estimated_errors",
        "query_methods",
        "query_evaluations",
        "query_panels",
    ):
        if len(saved[key]) != size:
            raise ValueError(f"candidate {key} query count differs")
    for key in ("evaluations", "panels"):
        if isinstance(saved[key], bool) or not isinstance(saved[key], int) or saved[key] < 0:
            raise ValueError(f"invalid candidate {key}")
    if sum(saved["query_evaluations"]) != saved["evaluations"]:
        raise ValueError("candidate evaluation totals do not reconcile")
    if sum(saved["query_panels"]) != saved["panels"]:
        raise ValueError("candidate panel totals do not reconcile")
    if any(
        isinstance(v, bool) or not isinstance(v, int) or v < 0
        for key in ("query_evaluations", "query_panels")
        for v in saved[key]
    ):
        raise ValueError("candidate per-query work counts must be nonnegative integers")
    if saved["evaluations"] > controls["max_evaluations"]:
        raise ValueError("candidate exceeds its cumulative evaluation budget")
    if any(v > controls["max_panels"] for v in saved["query_panels"]):
        raise ValueError("candidate exceeds its per-query panel budget")
    for status, value, error in zip(
        saved["statuses"], saved["derivatives"], saved["estimated_errors"], strict=True
    ):
        if status not in {"resolved", "work_limit", "numerical"}:
            raise ValueError("candidate status is outside the declared enum")
        if status == "resolved":
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or isinstance(error, bool)
                or not isinstance(error, (int, float))
                or not math.isfinite(error)
                or not 0 <= error <= controls["probability_tolerance"]
            ):
                raise ValueError("resolved candidate violates its requested absolute tolerance")
        elif value is not None or error is not None:
            raise ValueError("unknown candidate must withhold derivative and error")
    return saved


def run_scene(index, scene, plan, guards, api):
    identity = {"index": index, "id": scene["id"], "kind": scene["kind"], "input": scene}
    row = {**identity, "candidate": None, "queries": [], "protocol_passed": False}
    started = time.perf_counter()
    try:
        row["candidate"] = candidate_record(api, scene, plan["operator"])
    except Exception as error:
        row["candidate_failure"] = {"stage": "candidate_api", **exception_record(error)}
    for query_index, pixel in enumerate(scene["pixels_xy"]):
        query_identity = {
            "query_index": query_index,
            "pixel": pixel,
            "roles": [r["role"] for r in scene["query_roles"] if r["query_index"] == query_index],
        }
        query = {**query_identity, "comparison_passed": False}
        try:
            oracle = direct_oracle(scene, pixel, plan["oracle"], guards)
            query["oracle"] = oracle
            candidate = row["candidate"]
            if candidate is not None:
                value = candidate["derivatives"][query_index]
                error = candidate["estimated_errors"][query_index]
                query["candidate"] = {
                    "value": value,
                    "estimated_error": error,
                    "status": candidate["statuses"][query_index],
                    "method": candidate["query_methods"][query_index],
                }
                if query["candidate"]["status"] == "resolved":
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        raise ValueError("resolved candidate lacks a real derivative")
                    if not isinstance(error, (int, float)) or isinstance(error, bool) or error < 0:
                        raise ValueError("resolved candidate lacks a nonnegative error estimate")
                    if oracle.get("oracle_converged", False):
                        high = oracle["values"][str(plan["oracle"]["orders"][-1])]
                        allowance = math.fsum(
                            (
                                plan["oracle"]["comparison_abs"],
                                plan["oracle"]["comparison_rel"] * abs(high),
                                error,
                                2 * oracle["order_delta"],
                                oracle["tail_envelope_sum"],
                            )
                        )
                        delta = abs(value - high)
                        query.update(
                            comparison_delta=delta,
                            comparison_allowance=allowance,
                            comparison_passed=delta <= allowance,
                        )
            row["queries"].append(json_ready(query))
        except Exception as error:
            row["queries"].append(failed_record(query_identity, "query_comparison", error, query))
    row["runtime_seconds"] = time.perf_counter() - started
    row["protocol_passed"] = len(row["queries"]) == len(scene["pixels_xy"]) and all(
        q["comparison_passed"] for q in row["queries"]
    )
    row["status"] = "passed" if row["protocol_passed"] else "protocol_failure"
    try:
        return json_ready(row)
    except Exception as error:
        return scene_failure(index, scene, "scene_serialization", error, row)


def area_check(scene, selection, plan, helper, candidate):
    settings = plan["positive_area_corroboration"]
    identity = {"scene_id": scene["id"], "query_indices": selection["query_indices"]}
    result = {**identity, "means": {}, "queries": [], "protocol_passed": False}
    points = NP.asarray([scene["pixels_xy"][i] for i in selection["query_indices"]], float) + 0.5
    result["observation_centres"] = points.tolist()
    h = settings["h_radians"]
    sides = (("plus_h", h), ("minus_h", -h), ("plus_half", h / 2), ("minus_half", -h / 2))
    for order in settings["orders"]:
        result["means"][str(order)] = {}
        for name, angle in sides:
            config = {
                **scene,
                "source": "point",
                "levels": [0.0, 1.0],
                "normal_degrees": scene["normal_degrees"] + math.degrees(angle),
            }
            try:
                # Independently check every rotated material chart before area integration.
                radians = math.radians(config["normal_degrees"])
                config["normal"] = [math.cos(radians), math.sin(radians)]
                chart = oracle_geometry(config)["whole_material_chart_minimum"]
                means = helper.independent_means(
                    points,
                    config,
                    order,
                    {"oracle": {"tail_breakpoints": settings["tail_breakpoints"]}},
                )
                saved = json_ready(means.tolist())
                if len(saved) != len(points):
                    raise ValueError("positive-area mean count differs")
                result["means"][str(order)][name] = {
                    "angle_delta_radians": angle,
                    "normal_degrees": config["normal_degrees"],
                    "normal": config["normal"],
                    "whole_material_chart_minimum": chart,
                    "probabilities": saved,
                }
            except Exception as error:
                result["means"][str(order)][name] = {
                    "status": "execution_failure",
                    "error": exception_record(error),
                }
    for local_index, query_index in enumerate(selection["query_indices"]):
        qid = {"query_index": query_index, "pixel": scene["pixels_xy"][query_index]}
        query = {**qid, "protocol_passed": False}
        try:
            values = {
                order: {
                    name: result["means"][str(order)][name]["probabilities"][local_index]
                    for name, _ in sides
                }
                for order in settings["orders"]
            }
            differences = {
                str(order): {
                    "h": (v["plus_h"] - v["minus_h"]) / (2 * h),
                    "half": (v["plus_half"] - v["minus_half"]) / h,
                }
                for order, v in values.items()
            }
            low_order, high_order = settings["orders"]
            low, high = differences[str(low_order)], differences[str(high_order)]
            low_means, high_means = values[low_order], values[high_order]
            propagated = {
                "h": (
                    abs(high_means["plus_h"] - low_means["plus_h"])
                    + abs(high_means["minus_h"] - low_means["minus_h"])
                )
                / (2 * h),
                "half": (
                    abs(high_means["plus_half"] - low_means["plus_half"])
                    + abs(high_means["minus_half"] - low_means["minus_half"])
                )
                / h,
            }
            order_delta = max(abs(high[k] - low[k]) for k in ("h", "half"))
            order_guard = max(order_delta, *propagated.values())
            half_delta = abs(high["half"] - high["h"])
            richardson = (4 * high["half"] - high["h"]) / 3
            value = None if candidate is None else candidate["derivatives"][query_index]
            resolved = candidate is not None and candidate["statuses"][query_index] == "resolved"
            delta = None if not resolved else abs(value - richardson)
            allowance = settings["candidate_richardson_abs"] + settings[
                "candidate_richardson_rel"
            ] * abs(richardson)
            query.update(
                finite_differences=differences,
                derivative_order_delta=order_delta,
                propagated_area_order_discrepancy=propagated,
                derivative_order_guard_value=order_guard,
                derivative_order_passed=order_guard <= settings["derivative_order_agreement_abs"],
                h_half_delta=half_delta,
                h_half_passed=half_delta <= settings["step_half_agreement_abs"],
                richardson=richardson,
                candidate=value,
                candidate_resolved=resolved,
                candidate_delta=delta,
                candidate_allowance=allowance,
            )
            query["protocol_passed"] = (
                query["derivative_order_passed"]
                and query["h_half_passed"]
                and resolved
                and delta <= allowance
            )
            result["queries"].append(json_ready(query))
        except Exception as error:
            result["queries"].append(failed_record(qid, "positive_area_comparison", error, query))
    result["protocol_passed"] = all(q["protocol_passed"] for q in result["queries"])
    return json_ready(result)


def revision():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def bootstrap_failure(plan, extra, scenes, error):
    """Retain the complete identity census even if numerical startup fails."""
    scene_by_id = {scene["id"]: scene for scene in scenes}
    rows = [scene_failure(i, scene, "study_startup", error) for i, scene in enumerate(scenes)]
    area_rows = [
        area_failure(selection, scene_by_id[selection["scene_id"]], "study_startup", error)
        for selection in plan["positive_area_corroboration"]["selection"]
    ]
    population = extra["declared_population"]
    result = {
        "format": "pictures-to-cad-finite-normal-derivative-result",
        "version": 1,
        "plan_sha256": PLAN_SHA256,
        "supplement_sha256": SUPPLEMENT_SHA256,
        "stage": "study_startup",
        "error": exception_record(error),
        "rows": rows,
        "positive_area": area_rows,
        "protocol_passed": False,
        "source_unchanged": False,
        "summary": {
            "planned_scenes": population["total_scenes"],
            "retained_scenes": len(rows),
            "planned_queries": population["total_queries"],
            "retained_queries": sum(len(row["queries"]) for row in rows),
            "positive_area_scenes": len(area_rows),
            "positive_area_queries": sum(len(row["queries"]) for row in area_rows),
            "scene_passes": 0,
            "query_passes": 0,
            "positive_area_passes": 0,
            "all_scenes_and_queries_retained": True,
            "all_area_queries_retained": True,
            "unit_private_branch_controls_executed_here": False,
        },
        "scope": "Startup failed; every planned identity is retained without a qualified numerical result.",
    }
    for name in ("source_before", "source_after"):
        try:
            result[name] = source_hashes(plan)
        except Exception as source_error:
            result[name] = None
            result[f"{name}_failure"] = exception_record(source_error)
    return json_ready(result)


def run_study(plan, extra, scenes, *, api=None, area_helper=None):
    before = source_hashes(plan)
    started = time.perf_counter()
    setup_errors = {}
    try:
        api = numerical_imports() if api is None else api
        if NP is None:
            # Dependency injection must still explicitly initialize numerical support.
            import numpy

            globals()["NP"] = numpy
    except Exception as error:
        setup_errors["candidate_import"] = error
    try:
        helper = (
            load_helper(ROOT / plan["positive_area_corroboration"]["helper"])
            if area_helper is None
            else area_helper
        )
    except Exception as error:
        setup_errors["area_helper_import"] = error
        helper = None
    rows = []
    for index, scene in enumerate(scenes):
        try:
            if "candidate_import" in setup_errors:
                raise setup_errors["candidate_import"]
            row = run_scene(index, scene, plan, extra["algorithm_resolution_guards"], api)
        except Exception as error:
            row = scene_failure(index, scene, "scene_execution", error)
        rows.append(row)
        print(
            f"scene {index + 1}/{len(scenes)} {scene['id']}: {row['status']}",
            file=sys.stderr,
            flush=True,
        )
    by_id = {row["id"]: row for row in rows}
    scene_by_id = {scene["id"]: scene for scene in scenes}
    area_rows = []
    for selection in plan["positive_area_corroboration"]["selection"]:
        scene = scene_by_id[selection["scene_id"]]
        try:
            if "area_helper_import" in setup_errors:
                raise setup_errors["area_helper_import"]
            if NP is None:
                raise setup_errors["candidate_import"]
            row = area_check(
                scene, selection, plan, helper, by_id[selection["scene_id"]].get("candidate")
            )
        except Exception as error:
            row = area_failure(selection, scene, "positive_area_execution", error)
        area_rows.append(row)
        print(
            f"area {selection['scene_id']}: {'passed' if row['protocol_passed'] else 'failed'}",
            file=sys.stderr,
            flush=True,
        )
    source_after_failure = None
    try:
        after = source_hashes(plan)
    except Exception as error:
        after = None
        source_after_failure = exception_record(error)
    query_rows = [q for row in rows for q in row.get("queries", [])]
    area_queries = [q for row in area_rows for q in row.get("queries", [])]
    population = extra["declared_population"]
    all_retained = (
        len(rows) == population["total_scenes"] and len(query_rows) == population["total_queries"]
    )
    area_retained = len(area_rows) == len(plan["positive_area_corroboration"]["selection"]) and len(
        area_queries
    ) == sum(len(s["query_indices"]) for s in plan["positive_area_corroboration"]["selection"])
    summary = {
        "planned_scenes": population["total_scenes"],
        "retained_scenes": len(rows),
        "planned_queries": population["total_queries"],
        "retained_queries": len(query_rows),
        "scene_passes": sum(row["protocol_passed"] for row in rows),
        "query_passes": sum(q["comparison_passed"] for q in query_rows),
        "oracle_converged_queries": sum(
            q.get("oracle", {}).get("oracle_converged", False) for q in query_rows
        ),
        "positive_area_scenes": len(area_rows),
        "positive_area_queries": len(area_queries),
        "positive_area_passes": sum(q["protocol_passed"] for q in area_queries),
        "all_scenes_and_queries_retained": all_retained,
        "all_area_queries_retained": area_retained,
        "unit_private_branch_controls_executed_here": False,
        "optimizer_calls": 0,
        "renderer_calls": 0,
        "old_archived_data_analyses": 0,
    }
    passed = (
        before == after
        and all_retained
        and area_retained
        and all(row["protocol_passed"] for row in rows)
        and all(row["protocol_passed"] for row in area_rows)
    )
    return json_ready(
        {
            "format": "pictures-to-cad-finite-normal-derivative-result",
            "version": 1,
            "plan_sha256": PLAN_SHA256,
            "supplement_sha256": SUPPLEMENT_SHA256,
            "api_file_sha256": before[API_PATH]["sha256"],
            "helper_sha256": before[plan["positive_area_corroboration"]["helper"]]["sha256"],
            "runner_sha256": before[RUNNER.relative_to(ROOT).as_posix()]["sha256"],
            "source_before": before,
            "source_after": after,
            "source_unchanged": before == after,
            "source_after_failure": source_after_failure,
            "revision": revision(),
            "versions": {
                "python": platform.python_version(),
                "numpy": None if NP is None else NP.__version__,
            },
            "setup_failures": {key: exception_record(error) for key, error in setup_errors.items()},
            "settings": {
                "operator": plan["operator"],
                "oracle": plan["oracle"],
                "algorithm_resolution_guards": extra["algorithm_resolution_guards"],
                "positive_area_corroboration": plan["positive_area_corroboration"],
            },
            "rows": rows,
            "positive_area": area_rows,
            "summary": summary,
            "protocol_passed": passed,
            "runtime_seconds": time.perf_counter() - started,
            "scope": "Conditional signed Gaussian point-probability derivative only; no fit, calibration or production adoption. Unit/private-branch controls are separate evidence, not run by this runner.",
        }
    )


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, metavar="NEW_JSON")
    args = parser.parse_args(arguments)
    try:
        output = validate_output(args.output)
        plan, extra, scenes = load_plans()
        # Exclusive creation closes the race after refusal checks; never overwrite.
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    with os.fdopen(descriptor, "w") as stream:
        try:
            result = run_study(plan, extra, scenes)
        except Exception as error:
            result = bootstrap_failure(plan, extra, scenes, error)
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        stream.write(encoded)
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
