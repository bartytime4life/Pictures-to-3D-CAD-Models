#!/usr/bin/env python3
"""Audit saved V2 JSON only; no model, NumPy, quadrature or scientific replay.

This checks arithmetic/provenance consistency of reported values. It cannot
certify quadrature nodes, local error estimates, libm, or a physical model.
An internally consistent failed scientific protocol can pass this audit.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

PLAN = "studies/finite-normal-error-control-v2.json"
PLAN_SHA = "b59d38b3ca92449c4233b947dd061f7a6591ce1944946b6c10e868afaad3adbb"
ADDENDUM = "studies/finite-normal-error-control-inverse-addendum-v2.json"
ADDENDUM_SHA = "5703d6fa480ba2801291865b2b9921ba7c8b875ef96adc1beb3d3d4b3bcfb8bd"
RUNNER = "studies/verification/finite-normal-error-control-v2.py"
RUNNER_SHA = "835814c5c9bf23d1f8945474ca9b9412ae5a12ff0f358d0e09b6e8bea9d5cdc6"
API = "backend/finite_normal.py"
TEST = "tests/test_finite_normal_error_control.py"
OLD_MAIN = "studies/finite-normal-derivative-v1.json"
OLD_EXTRA = "studies/finite-normal-derivative-compressed-chart-v1.json"
OLD_RUNNER = "studies/verification/finite-normal-derivative-v1.py"
EPS = sys.float_info.epsilon
SMALLEST = math.nextafter(0.0, 1.0)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def integer(value):
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def strict_read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def finite_float(token):
        value = float(token)
        if not math.isfinite(value):
            raise ValueError("nonfinite JSON number")
        return value

    def bad_constant(token):
        raise ValueError(f"nonfinite JSON constant: {token}")

    return json.loads(
        Path(path).read_text(),
        object_pairs_hook=pairs,
        parse_float=finite_float,
        parse_constant=bad_constant,
    )


class Audit:
    def __init__(self):
        self.counts = Counter()
        self.failures = []
        self.max_arithmetic_ulp_discrepancy = 0.0

    def check(self, group, identity, condition, **detail):
        self.counts[group + ":checks"] += 1
        if not condition:
            self.counts[group + ":failed"] += 1
            self.failures.append({"group": group, "identity": identity, **detail})
        return bool(condition)

    def equal(self, group, identity, actual, expected):
        return self.check(group, identity, actual == expected, actual=actual, expected=expected)

    def arithmetic(self, group, identity, actual, expected, ulps=0):
        okay = number(actual) and number(expected)
        distance = None
        if okay:
            allowance = ulps * max(math.ulp(float(actual)), math.ulp(float(expected)))
            distance = abs(actual - expected)
            okay = distance <= allowance
            if ulps and distance:
                self.max_arithmetic_ulp_discrepancy = max(
                    self.max_arithmetic_ulp_discrepancy,
                    distance / max(math.ulp(float(actual)), math.ulp(float(expected))),
                )
        return self.check(
            group,
            identity,
            okay,
            actual=actual,
            expected=expected,
            arithmetic_ulps_allowed=ulps,
            absolute_difference=distance,
        )

    def guarded(self, group, identity, function):
        try:
            return function()
        except Exception as error:  # noqa: BLE001 -- failure is retained as an audit failure
            self.check(group, identity, False, error_type=type(error).__name__, error=str(error))
            return None


def audit_normalizer(audit, identity, record):
    """Only saved exact/log/factor arithmetic, not new density evaluations."""
    determinant = record["determinant"]
    exact = Fraction(determinant["signed_fraction"])
    rounded = float(abs(exact))
    relative = abs(Fraction.from_float(rounded) - abs(exact)) / abs(exact)
    upward = 0.0 if relative == 0 else math.nextafter(float(relative), math.inf)
    audit.equal("normalizer", identity + "/fraction-nonzero", exact != 0, True)
    audit.arithmetic(
        "normalizer", identity + "/det-round", determinant["rounded_absolute"], rounded
    )
    audit.equal(
        "normalizer", identity + "/det-hex", determinant["rounded_absolute_hex"], rounded.hex()
    )
    audit.equal(
        "normalizer",
        identity + "/conversion-fraction",
        Fraction(determinant["conversion_relative_error_fraction"]),
        relative,
    )
    audit.arithmetic(
        "normalizer",
        identity + "/conversion-upward",
        determinant["conversion_relative_error_upward_float"],
        upward,
    )
    logarithm = math.log(rounded)
    conversion_log = upward / (1 - upward)
    arithmetic = 8 * EPS * abs(logarithm)
    audit.arithmetic("normalizer", identity + "/log", determinant["log_absolute"], logarithm)
    audit.arithmetic(
        "normalizer",
        identity + "/log-conversion",
        determinant["log_conversion_allowance"],
        conversion_log,
    )
    audit.arithmetic(
        "normalizer",
        identity + "/log-arithmetic",
        determinant["log_arithmetic_estimate"],
        arithmetic,
    )
    terms = record["density_log_terms"]
    audit.check("normalizer", identity + "/log-terms", len(terms) == 3 and all(map(number, terms)))
    audit.arithmetic(
        "normalizer", identity + "/density-log", record["density_log"], math.fsum(terms)
    )
    log_error = math.fsum((conversion_log + arithmetic, 8 * EPS * math.fsum(map(abs, terms))))
    audit.arithmetic(
        "normalizer",
        identity + "/combined-log-error",
        record["combined_log_error_estimate"],
        log_error,
    )
    audit.arithmetic(
        "normalizer",
        identity + "/relative-error",
        record["normalizer_relative_error_estimate"],
        math.expm1(log_error),
    )


def audit_oracle(audit, identity, oracle, plan):
    settings, guards = plan["oracle"], plan["algorithm_resolution_guards"]
    orders = list(map(str, settings["orders"]))
    for key in ("evaluations", "endpoint_evaluations", "panels_inspected"):
        audit.check("oracle-work", identity + "/" + key, integer(oracle[key]), actual=oracle[key])
    audit.check(
        "oracle-work",
        identity + "/caps",
        oracle["evaluations"] <= settings["maximum_evaluations_per_query"]
        and oracle["panels_inspected"] <= settings["maximum_panels"],
    )
    audit.equal("oracle-work", identity + "/orders", oracle["orders"], settings["orders"])
    for key in orders:
        audit.check(
            "oracle-work",
            identity + "/rule-count-" + key,
            integer(oracle["rule_evaluations"][key])
            and oracle["rule_evaluations"][key] % int(key) == 0,
        )
    audit.equal(
        "oracle-work",
        identity + "/total",
        oracle["evaluations"],
        oracle["endpoint_evaluations"] + sum(oracle["rule_evaluations"].values()),
    )
    leaves = oracle.get("leaf_panels", [])
    direct, tails = [], []
    for index, panel in enumerate(leaves):
        pid = identity + f"/leaf-{index}"
        audit.check(
            "oracle-panel",
            pid + "/interval",
            number(panel["start"]) and number(panel["end"]) and panel["start"] < panel["end"],
        )
        for name in (
            "whitened_travel",
            "gaussian_exponent_variation",
            "minimum_whitened_segment_distance",
        ):
            audit.check("oracle-panel", pid + "/" + name, number(panel[name]) and panel[name] >= 0)
        audit.check(
            "oracle-panel",
            pid + "/denominator",
            number(panel["denominator_ratio"]) and panel["denominator_ratio"] >= 1,
        )
        if panel["method"] == "direct_source_s":
            direct.append(panel)
            audit.check(
                "oracle-panel",
                pid + "/three-guards",
                panel["whitened_travel"] <= guards["maximum_whitened_panel_travel"]
                and panel["gaussian_exponent_variation"]
                <= guards["maximum_gaussian_exponent_variation"]
                and panel["denominator_ratio"] <= guards["maximum_denominator_ratio"],
            )
            for key in orders:
                value, error = panel["values"][key], panel["roundoff_estimates"][key]
                audit.check(
                    "oracle-panel",
                    pid + "/rule-values-" + key,
                    number(value) and number(error) and error >= 0,
                )
                # Absolute-node sums are not saved. Check only their necessary
                # inequality; do not claim to replay rule nodes or density.
                minimum = abs(value) * (
                    128 * EPS + oracle["normalizer"]["normalizer_relative_error_estimate"]
                )
                audit.check(
                    "oracle-panel",
                    pid + "/necessary-roundoff-" + key,
                    error + 4 * max(math.ulp(error), math.ulp(minimum)) >= minimum,
                )
        elif panel["method"] == "bounded_tail":
            tails.append(panel)
            bound, log_bound = panel["absolute_tail_envelope"], panel["log_absolute_tail_envelope"]
            audit.check(
                "oracle-tail",
                pid + "/range",
                number(bound) and 0 < bound <= oracle["per_panel_tail_threshold"],
            )
            if log_bound is None:
                audit.equal(
                    "oracle-tail",
                    pid + "/below-range",
                    panel.get("log_envelope_below_float_range"),
                    True,
                )
                audit.equal("oracle-tail", pid + "/minimum-float", bound, SMALLEST)
            else:
                audit.arithmetic(
                    "oracle-tail", pid + "/exponential", bound, max(SMALLEST, math.exp(log_bound))
                )
                audit.check(
                    "oracle-tail",
                    pid + "/threshold-log",
                    log_bound <= math.log(oracle["per_panel_tail_threshold"]),
                )
        else:
            audit.check("oracle-panel", pid + "/method-enum", False, actual=panel["method"])
    total_tail = 0.0
    for panel in tails:
        total_tail = math.fsum((total_tail, panel["absolute_tail_envelope"]))
    audit.arithmetic("oracle-tail", identity + "/total", oracle["tail_envelope_sum"], total_tail)
    audit.check("oracle-tail", identity + "/global-cap", total_tail <= 1e-13)
    if "initial_source_cuts" in oracle:
        cuts = oracle["initial_source_cuts"]
        audit.check(
            "oracle-partition",
            identity + "/initial-cuts",
            all(number(x) for x in cuts) and all(x < y for x, y in itertools.pairwise(cuts)),
        )
        audit.equal(
            "oracle-partition",
            identity + "/initial-count",
            oracle["initial_panel_count"],
            len(cuts) - 1,
        )
        audit.arithmetic(
            "oracle-tail",
            identity + "/threshold",
            oracle["per_panel_tail_threshold"],
            1e-13 / (len(cuts) - 1),
        )
        audit.equal(
            "oracle-work",
            identity + "/endpoint-count",
            oracle["endpoint_evaluations"],
            2 + 2 * oracle["panels_inspected"],
        )
    converged = oracle.get("oracle_converged") is True
    if oracle["status"] in {"resolved", "order_disagreement"}:
        sorted_leaves = sorted(leaves, key=lambda p: p["start"])
        cuts = oracle["initial_source_cuts"]
        audit.equal("oracle-partition", identity + "/full-left", sorted_leaves[0]["start"], cuts[0])
        audit.equal(
            "oracle-partition", identity + "/full-right", sorted_leaves[-1]["end"], cuts[-1]
        )
        audit.check(
            "oracle-partition",
            identity + "/no-gaps-or-overlaps",
            all(p["end"] == q["start"] for p, q in itertools.pairwise(sorted_leaves)),
        )
        audit.equal(
            "oracle-partition",
            identity + "/complete-binary-forest",
            oracle["panels_inspected"],
            2 * len(leaves) - oracle["initial_panel_count"],
        )
        for key in orders:
            audit.equal(
                "oracle-work",
                identity + "/rule-leaf-count-" + key,
                oracle["rule_evaluations"][key],
                int(key) * len(direct),
            )
            total = math.fsum(p["values"][key] for p in direct)
            local = math.fsum(p["roundoff_estimates"][key] for p in direct)
            reduction = 32 * EPS * math.fsum(abs(p["values"][key]) for p in direct)
            audit.arithmetic(
                "oracle-sums", identity + "/value-" + key, oracle["values"][key], total
            )
            audit.arithmetic(
                "oracle-sums", identity + "/partial-" + key, oracle["partial_integrals"][key], total
            )
            audit.arithmetic(
                "oracle-sums",
                identity + "/local-roundoff-" + key,
                oracle["local_roundoff_estimates"][key],
                local,
            )
            if converged:
                audit.arithmetic(
                    "oracle-sums",
                    identity + "/final-roundoff-" + key,
                    oracle["final_reduction_estimates"][key],
                    reduction,
                )
                audit.arithmetic(
                    "oracle-sums",
                    identity + "/roundoff-" + key,
                    oracle["roundoff_estimates"][key],
                    math.fsum((local, reduction)),
                )
            else:
                audit.arithmetic(
                    "oracle-sums",
                    identity + "/roundoff-" + key,
                    oracle["roundoff_estimates"][key],
                    local,
                )
            audit.arithmetic(
                "oracle-tail",
                identity + "/order-tail-" + key,
                oracle["tail_envelopes_by_order"][key],
                total_tail,
            )
        delta = abs(oracle["values"][orders[-1]] - oracle["values"][orders[0]])
        allowance = settings["order_agreement_abs"] + settings["order_agreement_rel"] * abs(
            oracle["values"][orders[-1]]
        )
        audit.arithmetic("oracle-sums", identity + "/order-delta", oracle["order_delta"], delta)
        audit.arithmetic(
            "oracle-sums", identity + "/order-limit", oracle["order_allowance"], allowance
        )
        audit.equal("oracle-sums", identity + "/order-pass", converged, delta <= allowance)
        audit.equal(
            "oracle-sums",
            identity + "/status",
            oracle["status"],
            "resolved" if delta <= allowance else "order_disagreement",
        )
    else:
        audit.equal("oracle-sums", identity + "/unknown-no-convergence", converged, False)
    if oracle.get("normalizer") is not None:
        audit.guarded(
            "normalizer", identity, lambda: audit_normalizer(audit, identity, oracle["normalizer"])
        )


def audit_candidate(audit, identity, candidate, scene, tolerance, controls):
    count = len(scene["pixels_xy"])
    for key in (
        "derivatives",
        "statuses",
        "estimated_errors",
        "query_methods",
        "query_evaluations",
        "query_panels",
    ):
        audit.equal("candidate-schema", identity + "/length-" + key, len(candidate[key]), count)
    for key in ("evaluations", "panels"):
        audit.check("candidate-work", identity + "/" + key, integer(candidate[key]))
    for index in range(count):
        qid = identity + f"/{index}"
        status, value, error = (
            candidate[key][index] for key in ("statuses", "derivatives", "estimated_errors")
        )
        audit.check(
            "candidate-schema", qid + "/status", status in {"resolved", "work_limit", "numerical"}
        )
        audit.check(
            "candidate-schema",
            qid + "/method",
            isinstance(candidate["query_methods"][index], str)
            and bool(candidate["query_methods"][index]),
        )
        if status == "resolved":
            audit.check(
                "candidate-schema",
                qid + "/finite-within-requested",
                number(value) and number(error) and 0 <= error <= tolerance,
            )
        else:
            audit.check(
                "candidate-schema", qid + "/unknown-withheld", value is None and error is None
            )
        audit.check(
            "candidate-work",
            qid + "/counts",
            integer(candidate["query_evaluations"][index])
            and integer(candidate["query_panels"][index])
            and candidate["query_panels"][index] <= controls["max_panels"],
        )
    audit.equal(
        "candidate-work",
        identity + "/evaluations-sum",
        candidate["evaluations"],
        sum(candidate["query_evaluations"]),
    )
    audit.equal(
        "candidate-work",
        identity + "/panels-sum",
        candidate["panels"],
        sum(candidate["query_panels"]),
    )
    audit.check(
        "candidate-work",
        identity + "/evaluation-budget",
        candidate["evaluations"] <= controls["max_evaluations"],
    )
    audit.equal(
        "candidate-schema", identity + "/not-certified", candidate["quadrature_certified"], False
    )
    audit.equal(
        "candidate-schema", identity + "/method-label", candidate["method"], "finite_chord_shape"
    )
    audit.check(
        "candidate-schema",
        identity + "/chart",
        number(candidate["chart_margin"]) and candidate["chart_margin"] > 0,
    )
    audit.check(
        "candidate-schema",
        identity + "/reflection-boolean",
        isinstance(candidate["reflected"], bool),
    )


def audit_query(audit, identity, query, index, scene, candidate, tolerance, plan):
    audit.equal("query-identity", identity + "/index", query["query_index"], index)
    audit.equal("query-identity", identity + "/pixel", query["pixel"], scene["pixels_xy"][index])
    audit.equal(
        "query-identity",
        identity + "/roles",
        query["roles"],
        [r["role"] for r in scene["query_roles"] if r["query_index"] == index],
    )
    oracle = query.get("oracle")
    if oracle is not None:
        audit.guarded("oracle", identity, lambda: audit_oracle(audit, identity, oracle, plan))
    eligible = (
        candidate is not None
        and oracle is not None
        and candidate["statuses"][index] == "resolved"
        and oracle.get("oracle_converged") is True
    )
    if candidate is not None:
        expected = {
            "value": candidate["derivatives"][index],
            "estimated_error": candidate["estimated_errors"][index],
            "status": candidate["statuses"][index],
            "method": candidate["query_methods"][index],
        }
        audit.equal("candidate-schema", identity + "/query-copy", query.get("candidate"), expected)
    if eligible and not query.get("error"):
        high = oracle["values"]["192"]
        components = {
            "oracle_roundoff192": oracle["roundoff_estimates"]["192"],
            "twice_order_delta": 2 * abs(high - oracle["values"]["96"]),
            "tail96": oracle["tail_envelopes_by_order"]["96"],
            "tail192": oracle["tail_envelopes_by_order"]["192"],
            "oracle_final_relative_roundoff": 32 * EPS * abs(high),
        }
        audit.equal(
            "coverage",
            identity + "/allowance-components",
            query["oracle_allowance_components"],
            components,
        )
        allowance = math.fsum(components.values())
        estimate_limit = math.fsum((candidate["estimated_errors"][index], allowance))
        requested_limit = math.fsum((tolerance, allowance))
        delta = abs(candidate["derivatives"][index] - high)
        for name, expected in (
            ("oracle_allowance", allowance),
            ("estimate_coverage_allowance", estimate_limit),
            ("requested_tolerance_allowance", requested_limit),
            ("comparison_delta", delta),
        ):
            audit.arithmetic("coverage", identity + "/" + name, query[name], expected)
        estimate, requested = delta <= estimate_limit, delta <= requested_limit
        for name, expected in (
            ("estimate_coverage_passed", estimate),
            ("requested_tolerance_passed", requested),
            ("comparison_passed", estimate and requested),
        ):
            audit.equal("coverage", identity + "/" + name, query[name], expected)
    else:
        for name in ("estimate_coverage_passed", "requested_tolerance_passed", "comparison_passed"):
            audit.equal(
                "coverage", identity + "/unqualified-" + name, query.get(name, False), False
            )


def audit_area(audit, row, selection, scene, candidate, settings):
    identity = scene["id"]
    audit.equal(
        "area-identity", identity + "/indices", row["query_indices"], selection["query_indices"]
    )
    audit.equal(
        "area-identity", identity + "/count", len(row["queries"]), len(selection["query_indices"])
    )
    if "observation_centres" in row:
        audit.equal(
            "area-identity",
            identity + "/centres",
            row["observation_centres"],
            [
                [x + 0.5, y + 0.5]
                for x, y in (scene["pixels_xy"][i] for i in selection["query_indices"])
            ],
        )
    h = settings["h_radians"]
    labels = {"plus_h": h, "minus_h": -h, "plus_half": h / 2, "minus_half": -h / 2}
    for key in map(str, settings["orders"]):
        for label, angle in labels.items():
            record = row.get("means", {}).get(key, {}).get(label, {})
            if "probabilities" not in record:
                audit.check(
                    "area-unknown",
                    identity + "/" + key + "/" + label,
                    record.get("status") == "execution_failure" or row.get("stage") is not None,
                )
                continue
            audit.equal(
                "area-means",
                identity + "/" + key + "/" + label + "/angle",
                record["angle_delta_radians"],
                angle,
            )
            audit.equal(
                "area-means",
                identity + "/" + key + "/" + label + "/degrees",
                record["normal_degrees"],
                scene["normal_degrees"] + math.degrees(angle),
            )
            audit.check(
                "area-means",
                identity + "/" + key + "/" + label + "/values",
                len(record["probabilities"]) == len(selection["query_indices"])
                and all(number(p) for p in record["probabilities"])
                and number(record["whole_material_chart_minimum"])
                and record["whole_material_chart_minimum"] > 0,
            )
    for local, (query, qi) in enumerate(zip(row["queries"], selection["query_indices"])):
        qid = identity + f"/{qi}"
        audit.equal("area-identity", qid + "/query-index", query["query_index"], qi)
        audit.equal("area-identity", qid + "/pixel", query["pixel"], scene["pixels_xy"][qi])
        if "finite_differences" not in query:
            audit.equal("area-unknown", qid + "/no-green", query["protocol_passed"], False)
            continue
        values = {
            str(order): {
                label: row["means"][str(order)][label]["probabilities"][local] for label in labels
            }
            for order in settings["orders"]
        }
        differences = {
            key: {
                "h": (v["plus_h"] - v["minus_h"]) / (2 * h),
                "half": (v["plus_half"] - v["minus_half"]) / h,
            }
            for key, v in values.items()
        }
        low, high = (differences[str(order)] for order in settings["orders"])
        lowv, highv = (values[str(order)] for order in settings["orders"])
        propagated = {
            "h": (abs(highv["plus_h"] - lowv["plus_h"]) + abs(highv["minus_h"] - lowv["minus_h"]))
            / (2 * h),
            "half": (
                abs(highv["plus_half"] - lowv["plus_half"])
                + abs(highv["minus_half"] - lowv["minus_half"])
            )
            / h,
        }
        order_delta = max(abs(high[k] - low[k]) for k in ("h", "half"))
        order_guard = max(order_delta, *propagated.values())
        half_delta = abs(high["half"] - high["h"])
        richardson = (4 * high["half"] - high["h"]) / 3
        resolved = candidate is not None and candidate["statuses"][qi] == "resolved"
        value = None if candidate is None else candidate["derivatives"][qi]
        delta = abs(value - richardson) if resolved else None
        allowance = settings["candidate_richardson_abs"] + settings[
            "candidate_richardson_rel"
        ] * abs(richardson)
        audit.equal(
            "area-calculation",
            qid + "/finite-differences",
            query["finite_differences"],
            differences,
        )
        audit.equal(
            "area-calculation",
            qid + "/propagated",
            query["propagated_area_order_discrepancy"],
            propagated,
        )
        for key, expected in (
            ("derivative_order_delta", order_delta),
            ("derivative_order_guard_value", order_guard),
            ("h_half_delta", half_delta),
            ("richardson", richardson),
            ("candidate_allowance", allowance),
        ):
            audit.arithmetic("area-calculation", qid + "/" + key, query[key], expected)
        for key, expected in (
            ("candidate", value),
            ("candidate_delta", delta),
            ("candidate_resolved", resolved),
            ("derivative_order_passed", order_guard <= settings["derivative_order_agreement_abs"]),
            ("h_half_passed", half_delta <= settings["step_half_agreement_abs"]),
        ):
            audit.equal("area-calculation", qid + "/" + key, query[key], expected)
        passed = (
            order_guard <= settings["derivative_order_agreement_abs"]
            and half_delta <= settings["step_half_agreement_abs"]
            and resolved
            and delta <= allowance
        )
        audit.equal("area-calculation", qid + "/protocol", query["protocol_passed"], passed)
    audit.equal(
        "area-calculation",
        identity + "/row-protocol",
        row["protocol_passed"],
        all(q["protocol_passed"] for q in row["queries"]),
    )


def population_summary(rows):
    queries = [q for r in rows for q in r["queries"]]
    return {
        "scenes": len(rows),
        "queries": len(queries),
        "scene_passes": sum(r["protocol_passed"] for r in rows),
        "query_passes": sum(q.get("comparison_passed", False) for q in queries),
        "estimate_coverage_passes": sum(q.get("estimate_coverage_passed", False) for q in queries),
        "requested_tolerance_passes": sum(
            q.get("requested_tolerance_passed", False) for q in queries
        ),
        "unknown_or_failed_queries": sum(not q.get("comparison_passed", False) for q in queries),
    }


def audit_report(audit, report, root, plan, scenes, args):
    audit.equal(
        "binding",
        "result-format",
        report["format"],
        "pictures-to-cad-finite-normal-error-control-result",
    )
    audit.equal("binding", "version", report["version"], 2)
    for field, expected in (
        ("plan_sha256", PLAN_SHA),
        ("runner_sha256", RUNNER_SHA),
        ("api_file_sha256", args.expected_api_sha256),
    ):
        audit.equal("binding", field, report[field], expected)
    addendum = report["software_preflight_addendum"]
    audit.equal("binding", "addendum-path", addendum["path"], ADDENDUM)
    audit.equal("binding", "addendum-sha", addendum["sha256"], ADDENDUM_SHA)
    audit.equal("binding", "addendum-record", addendum["record"], strict_read(root / ADDENDUM))
    before, after = report["source_before"], report["source_after"]
    audit.equal("binding", "source-interval", before, after)
    audit.equal("binding", "source-unchanged", report["source_unchanged"], before == after)
    required = {p.relative_to(root).as_posix() for p in (root / "backend").rglob("*.py")}
    required.update(plan["inputs_sha256"])
    required.update(plan["regression_plans"])
    required.update({PLAN, ADDENDUM, RUNNER, API, TEST, "pyproject.toml", "uv.lock"})
    audit.equal("binding", "source-set", sorted(before), sorted(required))
    pins = {
        **plan["inputs_sha256"],
        **plan["regression_plans"],
        PLAN: PLAN_SHA,
        ADDENDUM: ADDENDUM_SHA,
        RUNNER: RUNNER_SHA,
        API: args.expected_api_sha256,
        TEST: args.expected_test_sha256,
    }
    for name in sorted(required):
        path = root / name
        actual = {"sha256": digest(path), "bytes": path.stat().st_size}
        audit.equal("binding", name, before.get(name), actual)
        if name in pins:
            audit.equal("binding-pin", name, before.get(name, {}).get("sha256"), pins[name])
    audit.equal("binding", "v1-helper", report["v1_helper_sha256"], pins[OLD_RUNNER])
    audit.equal(
        "binding",
        "area-helper",
        report["positive_area_helper_sha256"],
        pins[plan["positive_area_corroboration"]["helper"]],
    )
    rows = report["rows"]
    audit.equal("census", "scene-count", len(rows), 417)
    audit.equal("census", "query-count", sum(len(r["queries"]) for r in rows), 4832)
    for index, (row, scene) in enumerate(zip(rows, scenes)):
        identity = scene["id"]
        population = "post_hoc_synthetic_regression" if index < 337 else "prospective_new_synthetic"
        tolerance = scene.get("requested_tolerance", 1e-10)
        for key, expected in (
            ("index", index),
            ("id", identity),
            ("kind", scene["kind"]),
            ("input", scene),
            ("population", population),
            ("requested_tolerance", tolerance),
        ):
            audit.equal("scene-identity", identity + "/" + key, row[key], expected)
        audit.equal(
            "scene-identity",
            identity + "/query-count",
            len(row["queries"]),
            len(scene["pixels_xy"]),
        )
        candidate = row.get("candidate")
        if candidate is not None:
            audit.guarded(
                "candidate",
                identity,
                lambda identity=identity, candidate=candidate, scene=scene, tolerance=tolerance: (
                    audit_candidate(audit, identity, candidate, scene, tolerance, plan["operator"])
                ),
            )
        for qi, query in enumerate(row["queries"]):
            audit.guarded(
                "query",
                identity + f"/{qi}",
                lambda qi=qi, query=query, identity=identity, scene=scene, candidate=candidate, tolerance=tolerance: (
                    audit_query(
                        audit, identity + f"/{qi}", query, qi, scene, candidate, tolerance, plan
                    )
                ),
            )
        passed = all(q["comparison_passed"] for q in row["queries"])
        audit.equal("scene-protocol", identity, row["protocol_passed"], passed)
        audit.equal(
            "scene-protocol",
            identity + "/status",
            row["status"],
            "passed" if passed else "protocol_failure",
        )
    lookup = {r["id"]: r for r in rows}
    scene_lookup = {s["id"]: s for s in scenes}
    area_rows = report["positive_area"]
    selections = plan["positive_area_corroboration"]["selection"]
    audit.equal("census", "area-count", len(area_rows), 24)
    audit.equal("census", "area-queries", sum(len(r["queries"]) for r in area_rows), 72)
    for row, selection in zip(area_rows, selections):
        identity = selection["scene_id"]
        audit.equal("area-identity", identity + "/scene-id", row["scene_id"], identity)
        audit.guarded(
            "area",
            identity,
            lambda row=row, selection=selection, identity=identity: audit_area(
                audit,
                row,
                selection,
                scene_lookup[identity],
                lookup[identity].get("candidate"),
                plan["positive_area_corroboration"],
            ),
        )
    queries = [q for r in rows for q in r["queries"]]
    area_queries = [q for r in area_rows for q in r["queries"]]
    old_ids = {s["id"] for s in scenes[:337]}
    summary = {
        "planned_scenes": 417,
        "retained_scenes": len(rows),
        "planned_queries": 4832,
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
        "all_scenes_and_queries_retained": len(rows) == 417 and len(queries) == 4832,
        "all_area_queries_retained": len(area_rows) == 24 and len(area_queries) == 72,
        "unit_private_branch_controls_executed_here": False,
        "optimizer_calls": 0,
        "renderer_calls": 0,
        "residual_or_photo_archive_analyses": 0,
        "by_population": {
            name: population_summary([r for r in rows if r["population"] == name])
            for name in ("post_hoc_synthetic_regression", "prospective_new_synthetic")
        },
        "positive_area_by_population": {
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
        },
    }
    audit.equal("summary", "all-summary-fields", report["summary"], summary)
    protocol = (
        before == after
        and summary["all_scenes_and_queries_retained"]
        and summary["all_area_queries_retained"]
        and all(r["protocol_passed"] for r in rows)
        and all(r["protocol_passed"] for r in area_rows)
    )
    audit.equal("summary", "overall-protocol", report["protocol_passed"], protocol)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--expected-api-sha256", required=True)
    parser.add_argument("--expected-test-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True, metavar="NEW_JSON")
    args = parser.parse_args()
    if os.path.lexists(args.output) or not args.output.parent.is_dir():
        parser.error("output must be fresh (no symlink) with an existing parent")
    for key in ("input_sha256", "expected_api_sha256", "expected_test_sha256"):
        value = getattr(args, key)
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            parser.error(key + " must be a lowercase SHA256")
    root = args.root.resolve()
    audit = Audit()
    input_sha = digest(args.input)
    audit.equal("binding", "input-external-sha", input_sha, args.input_sha256)
    plan = strict_read(root / PLAN)
    audit.equal("binding", "plan-external-sha", digest(root / PLAN), PLAN_SHA)
    audit.equal("binding", "addendum-external-sha", digest(root / ADDENDUM), ADDENDUM_SHA)
    scenes = [
        *strict_read(root / OLD_MAIN)["scenes"],
        *strict_read(root / OLD_EXTRA)["scenes"],
        *plan["scenes"],
    ]
    report = strict_read(args.input)
    summary = audit.guarded(
        "report", "whole-report", lambda: audit_report(audit, report, root, plan, scenes, args)
    )
    audit.equal("binding", "input-unchanged-through-audit", digest(args.input), input_sha)
    result = {
        "format": "finite-normal-v2-saved-data-independent-audit",
        "version": 1,
        "auditor_sha256": digest(__file__),
        "input": str(args.input),
        "input_sha256": input_sha,
        "external_api_sha256": args.expected_api_sha256,
        "external_test_sha256": args.expected_test_sha256,
        "passed": not audit.failures,
        "counts": dict(sorted(audit.counts.items())),
        "checks": sum(v for k, v in audit.counts.items() if k.endswith(":checks")),
        "failures": audit.failures,
        "recomputed_summary": summary,
        "study_protocol_passed": report.get("protocol_passed"),
        "max_arithmetic_ulp_discrepancy": audit.max_arithmetic_ulp_discrepancy,
        "unpassed_queries": [
            {
                "scene": r["id"],
                "query_index": q["query_index"],
                "pixel": q["pixel"],
                "candidate": q.get("candidate"),
                "oracle_status": q.get("oracle", {}).get("status"),
                "comparison_delta": q.get("comparison_delta"),
                "estimate_coverage_allowance": q.get("estimate_coverage_allowance"),
                "requested_tolerance_allowance": q.get("requested_tolerance_allowance"),
            }
            for r in report.get("rows", [])
            for q in r["queries"]
            if not q.get("comparison_passed", False)
        ],
        "actual_model_entries": 0,
        "actual_oracle_entries": 0,
        "actual_area_entries": 0,
        "scope": "Saved JSON and stdlib arithmetic only. Reconciles reported sums/guards/errors/work/FDs/coverage/provenance; no evaluation or import of candidate/oracle/model. Does not certify rule-node densities, embedded error estimates, matrix construction or physical accuracy. Audit consistency and scientific protocol outcome are separate.",
    }
    with args.output.open("x") as stream:
        json.dump(
            result,
            stream,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            default=lambda value: (
                f"{value.numerator}/{value.denominator}"
                if isinstance(value, Fraction)
                else (_ for _ in ()).throw(TypeError(type(value).__name__))
            ),
        )
        stream.write("\n")
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": result["checks"],
                "failures": len(audit.failures),
                "study_protocol_passed": result["study_protocol_passed"],
                "output": str(args.output),
            },
            allow_nan=False,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
