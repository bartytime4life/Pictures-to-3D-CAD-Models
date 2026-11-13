#!/usr/bin/env python3
"""Audit saved analytic-normal JSON and bytes with the standard library only.

No backend, numerical package, governing runner/oracle, model, reference, rule
generator, optimizer or renderer is imported or called. Exit0 means the saved
artifact is internally consistent, not that its scientific protocol passed.
An honestly retained unknown/failed scientific outcome can pass this audit.
"""

# Broad catches record named audit failures and keep later saved rows auditable.
# ruff: noqa: BLE001

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import sys
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

PLAN = "studies/finite-analytic-normal-information-v1.json"
PLAN_SHA = "28efd2aa241b662bdd2f771be48b37d99283c67033980dafc4e2dae23ff68dfd"
ORIGINAL = "studies/results/finite-residual-information-v1.json.gz"
MAX_BYTES = 2 * 1024**3


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("nonfinite JSON float")
    return value


def load(data):
    return json.loads(
        data,
        object_pairs_hook=unique_pairs,
        parse_float=finite_float,
        parse_constant=lambda text: (_ for _ in ()).throw(ValueError(text)),
    )


def nonnegative(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value >= 0
    )


def upward(value):
    answer = float(value)
    if not math.isfinite(answer) or value < 0:
        raise ValueError("invalid saved error sum")
    return math.nextafter(answer, math.inf) if Fraction(answer) < value else answer


class Checks:
    def __init__(self):
        self.count = 0
        self.groups = Counter()
        self.failures = []

    def test(self, group, name, passed, **details):
        self.count += 1
        self.groups[group] += 1
        if not passed:
            self.failures.append({"group": group, "check": name, **details})

    def exception(self, group, name, error):
        self.test(
            group, name, False, error={"type": type(error).__name__, "message": str(error)[:4096]}
        )


def audit_normal_api(checks, name, payload, count, settings):
    checks.test(
        "normal_api",
        name + "/schema",
        payload["method"] == "finite_chord_shape" and payload["quadrature_certified"] is False,
    )
    keys = (
        "derivatives",
        "statuses",
        "estimated_errors",
        "query_methods",
        "query_evaluations",
        "query_panels",
    )
    checks.test(
        "normal_api",
        name + "/all_queries_retained",
        all(len(payload[key]) == count for key in keys),
    )
    checks.test(
        "normal_api",
        name + "/total_work",
        type(payload["evaluations"]) is int
        and type(payload["panels"]) is int
        and sum(payload["query_evaluations"])
        == payload["evaluations"]
        <= settings["max_evaluations"]
        and sum(payload["query_panels"]) == payload["panels"],
    )
    for index, status in enumerate(payload["statuses"]):
        prefix = f"{name}/{index}"
        checks.test(
            "normal_api", prefix + "/status", status in ("resolved", "work_limit", "numerical")
        )
        checks.test(
            "normal_api",
            prefix + "/work",
            type(payload["query_evaluations"][index]) is int
            and payload["query_evaluations"][index] >= 0
            and type(payload["query_panels"][index]) is int
            and 0 <= payload["query_panels"][index] <= settings["max_panels"],
        )
        if status == "resolved":
            checks.test(
                "normal_api",
                prefix + "/resolved_values",
                not isinstance(payload["derivatives"][index], bool)
                and isinstance(payload["derivatives"][index], (float, int))
                and math.isfinite(payload["derivatives"][index])
                and nonnegative(payload["estimated_errors"][index]),
            )
        else:
            checks.test(
                "normal_api",
                prefix + "/unknown_not_zero",
                payload["derivatives"][index] is None
                and payload["estimated_errors"][index] is None,
            )


def audit_oracle(checks, name, oracle, pixels, settings):
    checks.test("oracle", name + "/query_census", len(oracle["queries"]) == len(pixels))
    checks.test(
        "oracle",
        name + "/qualified_aggregate",
        oracle["qualified"] == all(query["qualified"] for query in oracle["queries"]),
    )
    for index, (query, pixel) in enumerate(zip(oracle["queries"], pixels, strict=True)):
        prefix = f"{name}/{index}"
        checks.test(
            "oracle", prefix + "/identity", query["index"] == index and query["pixel"] == pixel
        )
        panels, work = query["panels"], query["work"]
        checks.test("oracle", prefix + "/128_panels", len(panels) == work["planned_panels"] == 128)
        statuses = Counter(panel["status"] for panel in panels)
        checks.test(
            "oracle",
            prefix + "/panel_work",
            work["attempted_panels"] == len(panels) - statuses["not_attempted"]
            and work["completed_panels"]
            == statuses["direct"] + statuses["bounded_tail"] + statuses["guard_failure"]
            and work["omitted_panels"] == statuses["bounded_tail"]
            and work["guard_failures"] == statuses["guard_failure"],
        )
        batches_attempted = batches_completed = density_lower = density_upper = tail_lower = (
            tail_upper
        ) = 0
        for panel_index, panel in enumerate(panels):
            part = f"{prefix}/{panel_index}"
            checks.test(
                "oracle_panel",
                part + "/fixed_partition",
                panel["index"] == panel_index
                and Fraction(panel["u_start_fraction"]) == -1 + Fraction(panel_index, 64)
                and Fraction(panel["u_end_fraction"]) == -1 + Fraction(panel_index + 1, 64),
            )
            attempts = panel.get("precision_attempts", {})
            tail_lower += sum(attempt["status"] == "completed" for attempt in attempts.values())
            tail_upper += len(attempts)
            rules = panel.get("rule_attempts", [])
            batches_attempted += len(rules)
            for attempt in rules:
                if attempt["status"] == "completed":
                    batches_completed += 1
                    density_lower += attempt["order"]
                density_upper += attempt["order"]
            if panel["status"] in ("direct", "bounded_tail", "guard_failure"):
                checks.test(
                    "oracle_panel",
                    part + "/both_precisions",
                    set(panel["precision"]) == {"80", "120"}
                    and all(attempts[key]["status"] == "completed" for key in ("80", "120")),
                )
                tails = all(panel["precision"][key]["tail_eligible"] for key in ("80", "120"))
                guards = all(panel["precision"][key]["guard_passed"] for key in ("80", "120"))
                expected = "bounded_tail" if tails else "direct" if guards else "guard_failure"
                checks.test(
                    "oracle_panel", part + "/shared_precision_decision", panel["status"] == expected
                )
            if panel["status"] == "direct":
                checks.test(
                    "oracle_panel",
                    part + "/complete_four_rules",
                    len(rules) == 4 and all(attempt["status"] == "completed" for attempt in rules),
                )
        checks.test(
            "oracle",
            prefix + "/rule_work",
            work["attempted_rule_batches"] == batches_attempted
            and work["completed_rule_batches"] == batches_completed
            and density_lower
            <= work["completed_density_nodes"]
            <= work["attempted_density_nodes"]
            <= density_upper
            <= settings["maximum_density_nodes_per_query"],
        )
        checks.test(
            "oracle",
            prefix + "/tail_work",
            tail_lower <= work["tail_exponential_calls"] <= tail_upper,
        )
        checks.test(
            "oracle",
            prefix + "/nonnegative_work",
            all(type(value) is int and value >= 0 for value in work.values()),
        )
        if query["qualified"]:
            checks.test(
                "oracle",
                prefix + "/qualified_complete",
                query["status"] == "resolved"
                and query["order_converged"]
                and query["precision_stable"]
                and not query.get("protocol_failure", False)
                and all(panel["status"] in ("direct", "bounded_tail") for panel in panels),
            )
        if "error_components_fraction" in query:
            components = {
                key: Fraction(value) for key, value in query["error_components_fraction"].items()
            }
            error = sum(components.values(), Fraction())
            checks.test(
                "oracle",
                prefix + "/error_fraction_sum",
                all(value >= 0 for value in components.values())
                and error == Fraction(query["estimated_error_fraction"])
                and query["estimated_error"] == upward(error),
            )
            high = Fraction(Decimal(query["values"]["120"]["96"]))
            checks.test(
                "oracle",
                prefix + "/saved_conversion_error",
                query["oracle_value"] == float(high)
                and components["decimal120_to_float_conversion"]
                == abs(Fraction(query["oracle_value"]) - high),
            )
    for key, value in oracle["work"].items():
        checks.test(
            "oracle_work",
            name + "/" + key,
            value == sum(query["work"][key] for query in oracle["queries"]),
        )


def audit_elementary(checks, name, elementary, oracle):
    checks.test(
        "elementary",
        name + "/qualified_aggregate",
        elementary["qualified"] == all(query["qualified"] for query in elementary["queries"]),
    )
    for query in elementary["queries"]:
        prefix = f"{name}/{query['index']}"
        for precision, record in query["records"].items():
            work = record["work"]
            checks.test(
                "elementary",
                prefix + f"/{precision}/work",
                0
                <= work["completed_density_exponential_calls"]
                <= work["attempted_density_exponential_calls"]
                <= 3
                and 0 <= work["completed_cdf_calls"] <= work["attempted_cdf_calls"] <= 2,
            )
            for endpoint in ("lower", "upper"):
                progress = record["cdf_" + endpoint + "_work"]
                if progress:
                    checks.test(
                        "elementary",
                        prefix + f"/{precision}/{endpoint}/terms",
                        0
                        <= progress["completed_retained_terms"]
                        <= progress["attempted_retained_terms"]
                        <= 10000
                        and 0
                        <= progress["completed_candidate_terms"]
                        <= progress["attempted_candidate_terms"]
                        <= 10000,
                    )
            if record["status"] == "completed":
                checks.test(
                    "elementary",
                    prefix + f"/{precision}/complete",
                    work["completed_density_exponential_calls"] == 3
                    and work["completed_cdf_calls"] == 2,
                )
        if query["qualified"]:
            low = Fraction(Decimal(query["values"]["80"]))
            high = Fraction(Decimal(query["values"]["120"]))
            checks.test(
                "elementary",
                prefix + "/precision",
                abs(high - low) <= Fraction(1, 10**65) * max(Fraction(1), abs(high))
                and all(record["status"] == "completed" for record in query["records"].values())
                and not query["protocol_failure"],
            )
    checks.test(
        "elementary",
        name + "/same_pixels",
        [query["pixel"] for query in elementary["queries"]]
        == [query["pixel"] for query in oracle["queries"]],
    )


def audit_context(checks, name, context, pixels, levels, plan):
    if "forward" in context:
        audit_normal_api(
            checks, name, context["forward"], len(pixels), plan["normal_api"]["settings"]
        )
    if "oracle" in context:
        audit_oracle(checks, name, context["oracle"], pixels, plan["source_chord_oracle"])
    if "elementary" in context and "oracle" in context:
        audit_elementary(checks, name, context["elementary"], context["oracle"])
    if context.get("protocol_failure"):
        checks.test(
            "qualification", name + "/protocol_never_qualifies", context["qualified"] is False
        )
    qualification = context.get("qualification")
    if qualification is None:
        checks.test(
            "qualification", name + "/missing_qualification_unknown", context["qualified"] is False
        )
        return
    payload, oracle = context["forward"], context["oracle"]
    checks.test(
        "qualification",
        name + "/full_comparison_census",
        len(qualification["queries"]) == len(pixels),
    )
    expected_all, complete_raw = [], True
    level_values, level_errors = [], []
    for index, record in enumerate(qualification["queries"]):
        prefix = f"{name}/{index}"
        reference = oracle["queries"][index]
        checks.test(
            "qualification",
            prefix + "/metadata",
            record["index"] == index
            and record["api_status"] == payload["statuses"][index]
            and record["oracle_status"] == reference.get("status"),
        )
        available = payload["statuses"][index] == "resolved" and reference.get("qualified")
        if not available:
            complete_raw = False
            expected_all.append(False)
            checks.test("qualification", prefix + "/unknown", record["qualified"] is False)
            continue
        value, error = payload["derivatives"][index], payload["estimated_errors"][index]
        oracle_value, oracle_error = reference["oracle_value"], reference["estimated_error"]
        delta = abs(Fraction(value) - Fraction(oracle_value))
        rounding = 64 * Fraction(sys.float_info.epsilon) * abs(Fraction(value))
        estimate_limit = Fraction(error) + Fraction(oracle_error) + rounding
        tolerance_limit = (
            Fraction(plan["normal_api"]["settings"]["probability_tolerance"])
            + Fraction(oracle_error)
            + rounding
        )
        passed = (
            error <= plan["normal_api"]["settings"]["probability_tolerance"]
            and delta <= estimate_limit
            and delta <= tolerance_limit
        )
        expected_all.append(passed)
        checks.test(
            "qualification",
            prefix + "/exact_comparison",
            record["qualified"] == passed
            and record["delta_upward"] == upward(delta)
            and record["estimate_comparison_allowance_upward"] == upward(estimate_limit)
            and record["tolerance_comparison_allowance_upward"] == upward(tolerance_limit),
        )
        a, b = map(float, levels)
        contrast = b - a
        result = contrast * value
        multiplication = abs(Fraction(result) - (Fraction(b) - Fraction(a)) * Fraction(value))
        source = abs(Fraction(contrast)) * (Fraction(error) + Fraction(oracle_error) + delta)
        total = source + multiplication
        parts = record["error_components"]
        checks.test(
            "normal_error",
            prefix + "/exact_scaling",
            record["level_value"] == result
            and record["level_error"] == upward(total)
            and parts["signed_contrast"] == contrast
            and parts["api_error"] == error
            and parts["oracle_error"] == oracle_error
            and Fraction(parts["api_oracle_delta_exact"]) == delta
            and Fraction(parts["exact_level_multiplication_residual"]) == multiplication
            and Fraction(parts["error_combination_exact"]) == total
            and parts["scaled_source_error_upward"] == upward(source),
        )
        level_values.append([result])
        level_errors.append([upward(total)])
    checks.test(
        "qualification",
        name + "/aggregate",
        qualification["qualified"] == bool(oracle["qualified"] and all(expected_all)),
    )
    block = qualification["block"]
    checks.test(
        "normal_error",
        name + "/block",
        block["values"] == (level_values if complete_raw else None)
        and block["errors"] == (level_errors if complete_raw else None),
    )
    expected = qualification["qualified"] and not context.get("protocol_failure", False)
    if "elementary_comparisons" in context:
        expected = expected and all(item["passed"] for item in context["elementary_comparisons"])
    checks.test("qualification", name + "/final_gate", context["qualified"] == expected)


def audit_step(checks, name, row, step):
    if step.get("status") not in ("evaluated_once", "zero_step"):
        checks.test(
            "trial",
            name + "/withheld_no_claim",
            not step.get("local_linearization_qualified", False),
        )
        return
    baseline = row["baseline"]["mean"]
    delta = step["linear_delta"]
    linear = step["linear_prediction"]
    actual = step["actual_prediction"]
    checks.test(
        "trial", name + "/fixed56", len(baseline) == len(delta) == len(linear) == len(actual) == 56
    )
    checks.test(
        "trial",
        name + "/saved_linear",
        all(p == b + d for p, b, d in zip(linear, baseline, delta, strict=True)),
    )
    differences = [(a - b) - d for a, b, d in zip(actual, baseline, delta, strict=True)]
    checks.test("trial", name + "/actual_minus_linear", step["actual_minus_linear"] == differences)
    denominator, maximum = max(map(abs, delta)), max(map(abs, differences))
    allowance = 0.001 + 0.05 * denominator
    checks.test(
        "trial",
        name + "/linearity_decision",
        step["linearity_denominator"] == denominator
        and step["maximum_linearity_discrepancy"] == maximum
        and step["linearity_allowance"] == allowance
        and step["local_linearization_qualified"] == (maximum <= allowance),
    )
    checks.test(
        "trial",
        name + "/same_reported_full_cutoff",
        step["reported_full_training_cutoff_same"] is True
        and step["training_matrix"]["cutoff"]
        == row["analysis"]["information"]["training40"]["full_BGNS"]["cutoff"],
    )
    if step["status"] == "evaluated_once":
        forward, levels = step["actual_forward"], step["trial_levels"]
        expected = [levels[0] + (levels[1] - levels[0]) * p for p in forward["probabilities"]]
        checks.test(
            "trial",
            name + "/actual_prediction_from_saved_probability",
            actual == expected and all(status == "resolved" for status in forward["statuses"]),
        )
    else:
        checks.test(
            "trial",
            name + "/zero_step_not_recovery",
            actual == baseline and step["actual_forward"] is None,
        )


def audit_rank_metadata(checks, name, analysis, qualified):
    for scope, info in analysis.get("information", {}).items():
        prefix = name + "/" + scope
        full = info["full_BGNS"]
        checks.test(
            "information",
            prefix + "/full_gate",
            full["derivative_qualified"] == qualified
            and (not full["rank_resolved"] or qualified and full["raw_rank_resolved"])
            and (not full["full_column_rank_resolved"] or full["rank_resolved"]),
        )
        matched = info["matched_BG_and_BGN_versus_S"]
        nuisance = matched["nuisances"]
        checks.test(
            "information",
            prefix + "/common_reference",
            all(item["nuisance"]["cutoff"] == matched["base_cutoff"] for item in nuisance.values()),
        )
        tau = matched["common_matched_cutoff"]
        if tau is not None:
            expected_tau = max(
                matched["base_cutoff"],
                *(4 * item["covariance_error_estimate"] for item in nuisance.values()),
            )
            checks.test(
                "information",
                prefix + "/matched_tau",
                matched["both_nuisance_projectors_qualified"]
                and tau == expected_tau
                and all(
                    item["projected_covariance_spectrum"]["cutoff"] == tau
                    for item in nuisance.values()
                ),
            )
        for label, item in nuisance.items():
            spectrum, ceiling = (
                item["projected_covariance_spectrum"],
                item["residual_dimension_ceiling"],
            )
            checks.test(
                "information",
                prefix + "/" + label + "/ceiling",
                spectrum["retained_rank"]
                == spectrum["basis_columns_used"]
                == min(ceiling, spectrum["raw_retained_rank"])
                and spectrum["rank_interval"]
                == [min(ceiling, value) for value in spectrum["raw_rank_interval"]],
            )
            if spectrum["rank_resolved"]:
                checks.test(
                    "information",
                    prefix + "/" + label + "/no_ceiling_promotion",
                    qualified
                    and spectrum["raw_rank_resolved"]
                    and spectrum["ceiling_consistent"]
                    and spectrum["raw_rank_interval"][1] <= ceiling,
                )
            else:
                checks.test(
                    "information",
                    prefix + "/" + label + "/unknown_energy",
                    item["qualified_unique_covariance_residual_energy"] is None
                    and item["qualified_unique_covariance_residual_projection"] is None
                    and item["qualified_unique_covariance_rank"] is None,
                )


def verify(report, root, checks):
    checks.test(
        "format",
        "report",
        report["format"] == "pictures-to-cad-finite-analytic-normal-information"
        and report["version"] == 1,
    )
    plan_bytes = (root / PLAN).read_bytes()
    plan = load(plan_bytes)
    checks.test(
        "binding",
        "frozen_plan",
        sha(plan_bytes) == report["plan_sha256"] == PLAN_SHA and plan == report["plan"],
    )
    checks.test(
        "binding",
        "48_source_snapshot",
        len(report["source_before"]) == len(report["source_after"]) == 48
        and report["source_before"] == report["source_after"]
        and report["source_unchanged"] is True,
    )
    for name, metadata in report["source_before"].items():
        data = (root / name).read_bytes()
        checks.test(
            "binding", name, sha(data) == metadata["sha256"] and len(data) == metadata["bytes"]
        )
    for name, expected in plan["inputs_sha256"].items():
        checks.test("binding", "pin/" + name, report["source_before"][name]["sha256"] == expected)
    original_bytes = gzip.decompress((root / ORIGINAL).read_bytes())
    original = load(original_bytes)
    checks.test(
        "preservation",
        "decoded_original",
        sha(original_bytes) == plan["original_residual_decoded_sha256"]
        and original["protocol_passed"] is report["original_residual"]["protocol_passed"] is False,
    )
    checks.test(
        "preservation",
        "old_controls_summary",
        original["summary"] == report["original_residual"]["summary"]
        and original["independent_forward_controls"]
        == report["original_residual"]["independent_forward_controls"]
        and report["original_residual"]["original_replaced_or_relabelled"] is False,
    )
    rows = report["rows"]
    checks.test("census", "12_rows", len(rows) == len(plan["population"]) == 12)
    controls = report["normal_controls"]
    expected_controls = [*plan["controls"], plan["legacy_normal_control"]]
    checks.test("census", "5_controls", len(controls) == len(expected_controls) == 5)
    for saved, defined in zip(controls, expected_controls, strict=True):
        checks.test(
            "control",
            defined["id"],
            saved["id"] == defined["id"] and saved["definition"] == defined,
        )
        try:
            audit_context(
                checks,
                defined["id"],
                saved["new_analytic"],
                defined["pixels"],
                defined["levels"],
                plan,
            )
        except Exception as error:
            checks.exception("control", defined["id"], error)
    checks.test(
        "preservation",
        "old_failed_normal_control",
        controls[-1]["original_failed_FD_control"] == original["independent_forward_controls"][3]
        and controls[-1]["original_failed_FD_control"]["passed"] is False,
    )
    algebra = report["algebra_controls"]
    checks.test(
        "control",
        "10_algebra_names",
        [item["name"] for item in algebra] == plan["algebra_controls"] and len(algebra) == 10,
    )
    controls_qualified = all(item["passed"] for item in algebra) and all(
        item["new_analytic"]["qualified"] and not item["new_analytic"]["protocol_failure"]
        for item in controls
    )
    checks.test(
        "qualification",
        "global_controls",
        report["independent_controls_qualified"] == controls_qualified,
    )
    for row, expected, old in zip(rows, plan["population"], original["rows"], strict=True):
        name = f"row{expected['index']}"
        try:
            checks.test(
                "census",
                name,
                all(row[key] == expected[key] == old[key] for key in ("index", "name", "lane")),
            )
            checks.test(
                "preservation",
                name + "/full_original",
                row["original_residual_row"] == old
                and sha(canonical(row["original_residual_row"])) == expected["original_row_sha256"],
            )
            checks.test(
                "preservation",
                name + "/old_flags",
                row["old_targets_passed"] == old["old_targets_passed"]
                and row["old_completion_passed"] == old["old_completion_passed"],
            )
            if not expected["eligible"]:
                checks.test(
                    "census",
                    name + "/upstream_refusal",
                    row["status"] == "upstream_ineligible"
                    and row["new_normal_calls"] == row["new_trial_calls"] == 0,
                )
                continue
            for key in ("observations", "baseline", "active_brightness"):
                checks.test("preservation", name + "/" + key, row[key] == old[key])
            for key in ("B", "G", "S"):
                checks.test(
                    "preservation", name + "/block" + key, row["blocks"][key] == old["blocks"][key]
                )
            for block_name, block in row["blocks"].items():
                if block["errors"] is not None:
                    checks.test(
                        "arrays",
                        name + "/" + block_name,
                        len(block["values"]) == len(block["errors"]) == 56
                        and all(
                            nonnegative(value) for values in block["errors"] for value in values
                        ),
                    )
            audit_context(
                checks,
                name,
                row["normal"],
                old["observations"]["pixels_xy"],
                old["baseline"]["levels"],
                plan,
            )
            if "qualification" in row["normal"]:
                checks.test(
                    "normal_error",
                    name + "/same_qualified_block",
                    row["blocks"]["N"] == row["normal"]["qualification"]["block"],
                )
            qualification = row["qualification"]
            saved_s = all(record["stable"] for record in old["finite_differences"][:3])
            cov_controls = all(
                item["passed"] for item in original["independent_forward_controls"][:3]
            )
            expected_qualified = (
                saved_s
                and cov_controls
                and row["normal"]["qualified"]
                and not row["normal"]["protocol_failure"]
                and controls_qualified
            )
            checks.test(
                "qualification",
                name + "/derivative_gate",
                qualification["derivative_qualified"] == expected_qualified
                and qualification["historical_normal_FD_not_a_new_gate"] is True,
            )
            analysis = row["analysis"]
            audit_rank_metadata(checks, name, analysis, expected_qualified)
            if "step" in analysis:
                if not expected_qualified:
                    checks.test(
                        "trial",
                        name + "/unqualified_no_trial",
                        analysis["step"]["status"] == "withheld",
                    )
                audit_step(checks, name, row, analysis["step"])
        except Exception as error:
            checks.exception("row", name, error)
    calls = report["work"]["calls"]
    normals, trials = (
        [item for item in calls if item["kind"] == "normal"],
        [item for item in calls if item["kind"] == "mean"],
    )
    expected_contexts = [
        {"scope": "normal_control", "id": item["id"]} for item in expected_controls
    ]
    expected_contexts += [
        {"scope": "archived_row", **{key: item[key] for key in ("index", "name", "lane")}}
        for item in plan["population"]
        if item["eligible"]
    ]
    checks.test(
        "call_budget",
        "normal_context_order",
        [item["context"] for item in normals] == expected_contexts,
    )
    checks.test(
        "call_budget",
        "15_calls_578_queries",
        len(normals) == report["work"]["normal_calls_attempted"] == 15
        and sum(item["queries"] for item in normals)
        == report["work"]["normal_queries_attempted"]
        == 578,
    )
    checks.test(
        "call_budget",
        "at_most_10_BGNS_trials",
        len(trials) == report["work"]["trial_mean_calls_attempted"] <= 10
        and len({canonical(item["context"]) for item in trials}) == len(trials)
        and all(
            item["context"]["scope"] == "archived_row" and item["queries"] == 56 for item in trials
        ),
    )
    checks.test(
        "call_budget",
        "no_other_science",
        len(calls) == len(normals) + len(trials)
        and all(
            report["work"][key] == 0
            for key in (
                "baseline_mean_calls",
                "geometry_jacobian_calls",
                "FD_calls",
                "optimizer_calls",
                "optimizer_attempts",
                "renderer_calls",
                "preparation_calls",
            )
        ),
    )
    checks.test(
        "call_budget",
        "returned_work",
        report["work"]["returned_evaluations"] == sum(item.get("evaluations", 0) for item in calls)
        and report["work"]["returned_panels"] == sum(item.get("panels", 0) for item in calls),
    )
    contexts = [item["new_analytic"] for item in controls] + [
        row["normal"] for row in rows if "normal" in row
    ]
    oracle_work = Counter()
    for context in contexts:
        oracle_work.update(context.get("oracle", {}).get("work", {}))
    checks.test(
        "call_budget",
        "oracle_work",
        dict(oracle_work) == report["source_chord_oracle_work"]
        and oracle_work["attempted_density_nodes"]
        <= plan["source_chord_oracle"]["maximum_density_nodes_total"],
    )
    executed = [
        row["analysis"]["step"]
        for row in rows
        if row.get("analysis", {}).get("step", {}).get("status") == "evaluated_once"
    ]
    comparisons = [
        query
        for context in contexts
        for query in context.get("qualification", {}).get("queries", [])
    ]
    aggregate = report["summary"]
    checks.test(
        "summary",
        "normal_comparisons",
        aggregate["normal_contexts_retained"] == len(contexts)
        and aggregate["normal_queries_compared"] == len(comparisons)
        and aggregate["normal_query_comparisons_passed"]
        == sum(query["qualified"] for query in comparisons),
    )
    checks.test(
        "summary",
        "old_flags",
        aggregate["old_targets_passed"] == sum(row["old_targets_passed"] for row in rows) == 3
        and aggregate["old_completions_passed"]
        == sum(row["old_completion_passed"] for row in rows)
        == 10
        and aggregate["new_fit_pass_count"] is None,
    )
    checks.test(
        "summary",
        "no_vacuous_linearity_claim",
        aggregate["executed_BGNS_linearity_all_passed"]
        == (all(step["local_linearization_qualified"] for step in executed) if executed else None),
    )
    expected_protocol = bool(
        report["source_unchanged"]
        and not report.get("startup_failure")
        and not report.get("binding_errors")
        and len(rows) == 12
        and sum(row["status"] == "upstream_ineligible" for row in rows) == 2
        and all(
            row["status"] in ("diagnostic_evaluated", "diagnostic_unknown", "upstream_ineligible")
            for row in rows
        )
        and len(contexts) == 15
        and len(comparisons) == 578
        and all(query["qualified"] for query in comparisons)
        and all(item["passed"] for item in algebra)
        and all(item["new_analytic"]["qualified"] for item in controls)
        and all(step["local_linearization_qualified"] for step in executed)
        and len(normals) == 15
        and sum(item["queries"] for item in normals) == 578
        and len(trials) <= 10
        and report["work"]["optimizer_attempts"] == 0
        and oracle_work["attempted_density_nodes"]
        <= plan["source_chord_oracle"]["maximum_density_nodes_total"]
        and all(not context.get("protocol_failure", False) for context in contexts)
        and all(
            not row.get("analysis", {}).get("step", {}).get("protocol_failure", False)
            for row in rows
        )
    )
    checks.test("summary", "honest_global_protocol", report["protocol_passed"] == expected_protocol)
    return {
        "input_protocol_passed": report["protocol_passed"],
        "rows": len(rows),
        "normal_calls": len(normals),
        "normal_queries": sum(item["queries"] for item in normals),
        "trial_mean_calls": len(trials),
        "old_original_protocol_passed": original["protocol_passed"],
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="decoded complete canonical JSON")
    parser.add_argument(
        "--input-sha256", required=True, help="exact expected SHA256 of decoded input bytes"
    )
    parser.add_argument("--output", type=Path, required=True, metavar="NEW_JSON")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository used for source checks; defaults to working directory",
    )
    args = parser.parse_args(arguments)
    output = args.output.absolute()
    if os.path.lexists(output) or not output.parent.is_dir():
        parser.error("output must be fresh (including no symlink) in an existing directory")
    if len(args.input_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.input_sha256):
        parser.error("--input-sha256 must be 64 lowercase hexadecimal digits")
    checks = Checks()
    result = {
        "format": "pictures-to-cad-finite-analytic-normal-saved-audit",
        "version": 1,
        "scope": "Saved JSON/bytes/exact rational and elementary scalar arithmetic only. No model/reference/rule generation, NumPy, SVD, optimizer or scientific replay. A passing audit is not a passing scientific result.",
        "auditor_sha256": sha(Path(__file__).read_bytes()),
        "input": str(args.input),
        "expected_input_sha256": args.input_sha256,
    }
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if args.input.stat().st_size > MAX_BYTES:
            raise ValueError("saved JSON exceeds the explicit 2 GiB auditor loading limit")
        data = args.input.read_bytes()
        result.update(input_sha256=sha(data), input_bytes=len(data))
        if sha(data) != args.input_sha256:
            raise ValueError("saved input hash differs")
        report = load(data)
        result["outcome"] = verify(report, args.root.resolve(), checks)
        checks.test("binding", "input_unchanged_during_audit", args.input.read_bytes() == data)
    except Exception as error:
        checks.exception("audit", "incomplete_audit", error)
    result.update(
        check_count=checks.count,
        checks_by_group=dict(checks.groups),
        failures=checks.failures,
        failure_count=len(checks.failures),
        passed=not checks.failures,
    )
    with os.fdopen(descriptor, "w") as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(
        json.dumps(
            {
                "output": str(output),
                "checks": checks.count,
                "failures": len(checks.failures),
                "passed": result["passed"],
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
