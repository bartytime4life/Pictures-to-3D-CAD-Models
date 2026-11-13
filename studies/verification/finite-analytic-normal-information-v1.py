#!/usr/bin/env python3
"""Qualify a new analytic normal column on immutable saved residual data.

This is a new source-bound conditional diagnostic, not a retry or repair of the
failed original residual protocol. Only the normal column is newly evaluated;
old B/G/S, baseline, finite differences and BGS trials remain saved evidence.
Destination and source refusals precede NumPy/backend imports. Scientific and
invented-algebra execution belongs to the one committed canonical run.
"""

# Every broad catch retains a named failure and continues the frozen census.
# ruff: noqa: BLE001

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-analytic-normal-information-v1.json"
PLAN_SHA256 = "28efd2aa241b662bdd2f771be48b37d99283c67033980dafc4e2dae23ff68dfd"
SAVED = "studies/results/finite-residual-information-v1.json.gz"
INTENSITY = "studies/results/finite-photo-intensity-v2.json"
BASE_PATH = "studies/verification/finite-residual-information-v1.py"
ORACLE_PATH = "studies/verification/finite-analytic-normal-oracle-v1.py"
METHOD = ("B", "G", "N", "S")
NP = None
BASE = None


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("nonfinite JSON float conversion")
    return value


def strict_json(data):
    return json.loads(
        data,
        object_pairs_hook=pairs,
        parse_float=finite_float,
        parse_constant=lambda text: (_ for _ in ()).throw(ValueError(text)),
    )


def ready(value):
    return strict_json(json.dumps(value, allow_nan=False))


def error_record(error, stage):
    return {"stage": stage, "type": type(error).__name__, "message": str(error)[:4096]}


def safe_fields(value):
    """Withhold unsafe whole fields explicitly, never replace a NaN with zero."""
    result, withheld = {}, []
    for key, item in value.items():
        try:
            ready(item)
        except (TypeError, ValueError, OverflowError):
            withheld.append(key)
        else:
            result[key] = item
    if withheld:
        result["withheld_unsafe_fields"] = withheld
    return result


def reserve_output(path):
    path = Path(path).absolute()
    if os.path.lexists(path) or not path.parent.is_dir():
        raise ValueError("output must be a fresh nonsymlink path in an existing directory")
    return path, os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)


def snapshot(plan):
    names = set(plan.get("inputs_sha256", {}))
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "backend").rglob("*.py"))
    names.update(
        (PLAN.relative_to(ROOT).as_posix(), RUNNER.relative_to(ROOT).as_posix(), ORACLE_PATH)
    )
    result = {}
    for name in sorted(names):
        try:
            data = (ROOT / name).read_bytes()
            result[name] = {"sha256": digest(data), "bytes": len(data)}
        except OSError as error:
            result[name] = {"error": error_record(error, "source_read")}
    return result


def binding_errors(plan, sources):
    errors = []
    for name, item in sources.items():
        if "error" in item:
            errors.append({"path": name, "reason": "source_read_failure"})
    expected = {**plan.get("inputs_sha256", {}), PLAN.relative_to(ROOT).as_posix(): PLAN_SHA256}
    for name, sha256 in expected.items():
        if sources.get(name, {}).get("sha256") != sha256:
            errors.append({"path": name, "reason": "frozen_source_sha256", "expected": sha256})
    return errors


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load pinned helper: {path}")
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def original_rows(plan, saved):
    rows = saved["rows"]
    if len(rows) != 12 or len(plan["population"]) != 12:
        raise ValueError("saved/frozen population is not 12")
    if saved["protocol_passed"] is not plan["original_residual_protocol_passed"]:
        raise ValueError("original protocol flag changed")
    if saved["source_before"] != saved["source_after"] or not saved["source_unchanged"]:
        raise ValueError("original report did not retain an unchanged source snapshot")
    for expected, row in zip(plan["population"], rows, strict=True):
        if any(expected[key] != row[key] for key in ("index", "name", "lane")):
            raise ValueError("saved row identity/order differs")
        if digest(canonical_bytes(row)) != expected["original_row_sha256"]:
            raise ValueError("complete original row digest differs")
        if expected["eligible"] != (row["status"] != "upstream_ineligible"):
            raise ValueError("saved upstream eligibility differs")
    return rows


def retained_rows(plan, saved=None, *, stage="not_started", error=None):
    old = {row["index"]: row for row in saved.get("rows", [])} if saved else {}
    rows = []
    for expected in plan.get("population", []):
        row = {key: expected[key] for key in ("index", "name", "lane")}
        row.update(status="not_evaluated_protocol_failure", stage=stage, new_fit_pass=False)
        original = old.get(expected["index"])
        if original is not None:
            row.update(
                original_residual_row=copy.deepcopy(original),
                old_targets_passed=original["old_targets_passed"],
                old_completion_passed=original["old_completion_passed"],
            )
        if error is not None:
            row["error"] = error_record(error, stage)
        rows.append(row)
    return rows


def upward(value):
    """Round a nonnegative exact rational upward to a finite binary64."""
    if value < 0:
        raise ValueError("negative error estimate")
    result = float(value)
    if not math.isfinite(result):
        raise ArithmeticError("error estimate is unrepresentable")
    if Fraction(result) < value:
        result = math.nextafter(result, math.inf)
    if not math.isfinite(result):
        raise ArithmeticError("upward error estimate is unrepresentable")
    return result


def rational_text(value):
    return f"{value.numerator}/{value.denominator}"


def scaled_normal(api_value, api_error, oracle_value, oracle_error, levels):
    a, b = map(float, levels)
    contrast = b - a
    value = contrast * api_value
    if not all(math.isfinite(x) for x in (contrast, value)):
        raise ArithmeticError("normal level scaling is unrepresentable")
    delta = abs(Fraction(api_value) - Fraction(oracle_value))
    rounding = abs(Fraction(value) - (Fraction(b) - Fraction(a)) * Fraction(api_value))
    source = abs(Fraction(contrast)) * (Fraction(api_error) + Fraction(oracle_error) + delta)
    return (
        value,
        upward(source + rounding),
        {
            "signed_contrast": contrast,
            "api_error": api_error,
            "oracle_error": oracle_error,
            "api_oracle_delta": upward(delta),
            "api_oracle_delta_exact": rational_text(delta),
            "scaled_source_error_upward": upward(source),
            "exact_level_multiplication_residual": rational_text(rounding),
            "error_combination_exact": rational_text(source + rounding),
        },
    )


def check_scaled_normal(value, error, expected_value, expected_error):
    if value != expected_value or error != expected_error:
        raise ValueError("normal value/error was scaled twice or used the wrong contrast sign")


def check_normal_payload(payload, count, settings):
    ready(payload)
    if payload["method"] != "finite_chord_shape" or payload["quadrature_certified"] is not False:
        raise ValueError("malformed normal method/certification metadata")
    for key in (
        "derivatives",
        "estimated_errors",
        "statuses",
        "query_methods",
        "query_evaluations",
        "query_panels",
    ):
        if len(payload[key]) != count:
            raise ValueError(f"normal {key} does not retain every query")
    if (
        type(payload["reflected"]) is not bool
        or isinstance(payload["chart_margin"], bool)
        or not isinstance(payload["chart_margin"], (float, int))
        or not math.isfinite(payload["chart_margin"])
        or payload["chart_margin"] <= 0
    ):
        raise ValueError("malformed normal chart metadata")
    for key in ("evaluations", "panels"):
        if type(payload[key]) is not int or payload[key] < 0:
            raise ValueError("malformed normal work counter")
    if payload["evaluations"] > settings["max_evaluations"]:
        raise ValueError("normal evaluation budget exceeded")
    for i, status in enumerate(payload["statuses"]):
        if status not in ("resolved", "work_limit", "numerical"):
            raise ValueError("unrecognized normal status")
        for key in ("query_evaluations", "query_panels"):
            if type(payload[key][i]) is not int or payload[key][i] < 0:
                raise ValueError("malformed per-query normal work")
        if payload["query_panels"][i] > settings["max_panels"]:
            raise ValueError("normal per-query panel budget exceeded")
        if payload["query_methods"][i] not in (
            "not_attempted",
            "affine_closed_form",
            "projective_closed_form",
            "affine_closed_form_then_chord_quadrature",
            "projective_closed_form_then_chord_quadrature",
        ):
            raise ValueError("unrecognized normal query method")
        if status == "resolved":
            for key in ("derivatives", "estimated_errors"):
                if (
                    isinstance(payload[key][i], bool)
                    or not isinstance(payload[key][i], (int, float))
                    or not math.isfinite(payload[key][i])
                ):
                    raise ValueError("nonfinite/malformed resolved normal result")
            if payload["estimated_errors"][i] < 0:
                raise ValueError("negative normal error estimate")
        elif payload["derivatives"][i] is not None or payload["estimated_errors"][i] is not None:
            raise ValueError("unresolved normal fabricated a result/error")
    if (
        sum(payload["query_evaluations"]) != payload["evaluations"]
        or sum(payload["query_panels"]) != payload["panels"]
    ):
        raise ValueError("normal per-query work does not sum to total work")


class Calls:
    def __init__(self, core, normal):
        self.core, self.normal = core, normal
        self.log, self.seen = [], set()
        self.context = {"scope": "not_assigned"}
        self.optimizer_attempts = 0

    def forbidden(self, *args, **kwargs):
        self.optimizer_attempts += 1
        raise AssertionError("optimizer calls are forbidden")

    def evaluate(self, kind, pixels, parameters, settings, label):
        if kind not in ("normal", "mean"):
            raise ValueError("only one normal and one BGNS mean trial are permitted")
        key = (kind, json.dumps(self.context, sort_keys=True))
        record = {
            "kind": kind,
            "label": label,
            "queries": len(pixels),
            "context": copy.deepcopy(self.context),
            "returned": False,
        }
        self.log.append(record)
        try:
            if key in self.seen:
                raise ValueError("duplicate scientific call in one context")
            self.seen.add(key)
            maximum = 15 if kind == "normal" else 10
            if sum(item["kind"] == kind for item in self.log) > maximum:
                raise ValueError("declared scientific call budget exceeded")
            function = (
                self.normal.circular_segment_normal_derivative
                if kind == "normal"
                else self.core.circular_segment_probabilities
            )
            result = function(
                pixels,
                parameters["radius"],
                parameters["fraction"],
                centre=parameters["centre"],
                normal=parameters["normal"],
                sensor_shape=parameters["sensor_shape"],
                homography=parameters["homography"],
                psf_covariance=parameters["covariance"],
                **settings,
            )
            payload = asdict(result)
            record["returned"] = True
            record["payload"] = safe_fields(payload)
            ready(payload)
            # Returned work survives even if a later value/status validator
            # rejects the payload or reports a represented numerical unknown.
            for counter in ("evaluations", "panels"):
                if type(payload[counter]) is not int or payload[counter] < 0:
                    raise ValueError("malformed returned API work counter")
                record[counter] = payload[counter]
            record["statuses"] = copy.deepcopy(payload["statuses"])
            if kind == "normal":
                check_normal_payload(payload, len(pixels), settings)
            else:
                values, _ = BASE.resolved(payload, "probabilities")
                if len(values) != len(pixels):
                    raise ValueError("mean trial changed the fixed query population")
            return payload
        except Exception as error:
            record["error"] = error_record(error, label)
            raise

    def summary(self):
        return {
            "calls": self.log,
            "normal_calls_attempted": sum(item["kind"] == "normal" for item in self.log),
            "normal_queries_attempted": sum(
                item["queries"] for item in self.log if item["kind"] == "normal"
            ),
            "trial_mean_calls_attempted": sum(item["kind"] == "mean" for item in self.log),
            "returned_evaluations": sum(item.get("evaluations", 0) for item in self.log),
            "returned_panels": sum(item.get("panels", 0) for item in self.log),
            "failed_call_work": "Unknown when an API raises before returning counters; every attempted call is retained.",
            "baseline_mean_calls": 0,
            "geometry_jacobian_calls": 0,
            "FD_calls": 0,
            "optimizer_calls": 0,
            "optimizer_attempts": self.optimizer_attempts,
            "renderer_calls": 0,
            "preparation_calls": 0,
        }


def make_rules(report):
    rules = {}
    for order in (64, 96):
        nodes, weights = NP.polynomial.legendre.leggauss(order)
        if (
            not NP.isfinite(nodes).all()
            or not NP.isfinite(weights).all()
            or len(nodes) != order
            or NP.any(NP.abs(nodes) >= 1)
            or NP.any(weights <= 0)
        ):
            raise ValueError("malformed generated rule")
        saved = {
            "nodes_hex": [float(x).hex() for x in nodes],
            "weights_hex": [float(x).hex() for x in weights],
        }
        report[str(order)] = {**saved, "sha256": digest(canonical_bytes(saved)), "order": order}
        nodes.setflags(write=False)
        weights.setflags(write=False)
        rules[order] = (nodes, weights)
    return rules


def elementary_comparisons(elementary, oracle):
    result = []
    if len(elementary["queries"]) != len(oracle["queries"]):
        raise ValueError("elementary/oracle query counts differ")
    eps = Fraction(sys.float_info.epsilon)
    for direct, chord in zip(elementary["queries"], oracle["queries"], strict=True):
        a = Fraction(Decimal(direct["values"]["80"]))
        b = Fraction(Decimal(direct["values"]["120"]))
        absolute = Fraction(Decimal(direct["absolute_sum_120"]))
        difference = abs(a - b)
        stable = difference <= Fraction(1, 10**65) * max(Fraction(1), abs(b))
        if chord.get("qualified") and chord.get("oracle_value") is not None:
            delta = abs(Fraction(chord["oracle_value"]) - b)
            arithmetic = 128 * eps * absolute + difference
            passed = (
                stable
                and delta <= Fraction(chord["estimated_error"]) + arithmetic
                and delta <= Fraction(1, 10**11) + arithmetic
            )
            result.append(
                {
                    "pixel": direct["pixel"],
                    "precision_stable": stable,
                    "oracle_elementary_delta_upward": upward(delta),
                    "elementary_arithmetic_allowance_upward": upward(arithmetic),
                    "passed": bool(passed),
                }
            )
        else:
            result.append(
                {
                    "pixel": direct["pixel"],
                    "precision_stable": stable,
                    "passed": False,
                    "reason": "independent_chord_oracle_unknown",
                }
            )
    return result


def check_oracle_payload(payload, pixels, settings):
    ready(payload)
    if (
        type(payload["qualified"]) is not bool
        or type(payload.get("protocol_failure", False)) is not bool
    ):
        raise ValueError("malformed independent oracle qualification")
    if len(payload["queries"]) != len(pixels):
        raise ValueError("independent oracle changed the fixed query count")
    if payload["status"] not in ("resolved", "numerical_unknown", "protocol_failure"):
        raise ValueError("unrecognized independent oracle batch status")
    for index, (query, pixel) in enumerate(zip(payload["queries"], pixels, strict=True)):
        if (
            query["index"] != index
            or query["pixel"] != list(pixel)
            or type(query["qualified"]) is not bool
        ):
            raise ValueError("independent oracle query order/qualification differs")
        if len(query["panels"]) != 128:
            raise ValueError("independent oracle did not retain all 128 panels")
        if any(type(query[key]) is not bool for key in ("order_converged", "precision_stable")):
            raise ValueError("malformed independent oracle stability flags")
        if query["qualified"] and (
            query["status"] != "resolved"
            or not query["order_converged"]
            or not query["precision_stable"]
        ):
            raise ValueError("inconsistent independent oracle qualification")
        for name, value in query["work"].items():
            if type(value) is not int or value < 0:
                raise ValueError("malformed independent oracle work counter")
            if (
                name.startswith("completed_")
                and value > query["work"][name.replace("completed_", "attempted_", 1)]
            ):
                raise ValueError("independent oracle completed unattempted work")
        if query["work"]["attempted_density_nodes"] > settings["maximum_density_nodes_per_query"]:
            raise ValueError("independent oracle per-query density work exceeded")
    for name, value in payload["work"].items():
        if value != sum(query["work"][name] for query in payload["queries"]):
            raise ValueError("independent oracle work totals differ from queries")
    if payload["qualified"] != all(query["qualified"] for query in payload["queries"]):
        raise ValueError("inconsistent independent oracle batch qualification")


def qualify_normal(payload, oracle, levels, settings):
    count = len(payload["statuses"])
    if len(oracle["queries"]) != count:
        raise ValueError("normal/oracle query count differs")
    values, errors, records = [], [], []
    all_raw = True
    for index, (status, reference) in enumerate(
        zip(payload["statuses"], oracle["queries"], strict=True)
    ):
        record = {
            "index": index,
            "api_status": status,
            "oracle_status": reference.get("status"),
            "qualified": False,
        }
        records.append(record)
        if status != "resolved" or not reference.get("qualified"):
            record["reason"] = "represented_numerical_unknown"
            all_raw = False
            continue
        api_value, api_error = payload["derivatives"][index], payload["estimated_errors"][index]
        oracle_value, oracle_error = reference["oracle_value"], reference["estimated_error"]
        if (
            isinstance(oracle_value, bool)
            or isinstance(oracle_error, bool)
            or not all(
                isinstance(x, (int, float)) and math.isfinite(x)
                for x in (oracle_value, oracle_error)
            )
            or oracle_error < 0
        ):
            raise ValueError("malformed independent oracle value/error")
        delta = abs(Fraction(api_value) - Fraction(oracle_value))
        arithmetic = 64 * Fraction(sys.float_info.epsilon) * abs(Fraction(api_value))
        estimate_bound = Fraction(api_error) + Fraction(oracle_error) + arithmetic
        tolerance_bound = (
            Fraction(settings["probability_tolerance"]) + Fraction(oracle_error) + arithmetic
        )
        qualified = (
            api_error <= settings["probability_tolerance"]
            and delta <= estimate_bound
            and delta <= tolerance_bound
        )
        value, estimate, components = scaled_normal(
            api_value, api_error, oracle_value, oracle_error, levels
        )
        record.update(
            qualified=bool(qualified),
            api_value=api_value,
            oracle_value=oracle_value,
            delta_upward=upward(delta),
            estimate_comparison_allowance_upward=upward(estimate_bound),
            tolerance_comparison_allowance_upward=upward(tolerance_bound),
            level_value=value,
            level_error=estimate,
            error_components=components,
        )
        values.append([value])
        errors.append([estimate])
    return {
        "qualified": bool(
            oracle.get("qualified") and all(record["qualified"] for record in records)
        ),
        "queries": records,
        "block": {
            "values": values if all_raw else None,
            "errors": errors if all_raw else None,
            "labels": ["normal_angle"],
            "scales": [1],
            "units": "source-plane radians",
            "method": "signed_contrast_times_analytic_finite_chord",
            "estimated_not_certified": True,
        },
    }


def normal_context(
    parameters,
    pixels,
    levels,
    calls,
    oracle_module,
    rules,
    constants,
    plan,
    *,
    elementary_control=None,
):
    result = {"stage": "analytic_normal", "protocol_failure": False, "qualified": False}
    try:
        result["forward"] = calls.evaluate(
            "normal", pixels, parameters, plan["normal_api"]["settings"], "analytic_normal"
        )
    except Exception as error:
        result["api_error"] = error_record(error, "analytic_normal")
        result["protocol_failure"] = not isinstance(error, ArithmeticError)
    result["stage"] = "independent_source_chord"
    try:
        result["oracle"] = oracle_module.evaluate_batch(
            parameters, pixels, rules, plan["source_chord_oracle"], constants=constants
        )
        check_oracle_payload(result["oracle"], pixels, plan["source_chord_oracle"])
        result["protocol_failure"] |= result["oracle"].get("protocol_failure", False)
    except Exception as error:
        result["oracle_error"] = error_record(error, "independent_source_chord")
        result["protocol_failure"] |= not isinstance(error, ArithmeticError)
    if "forward" in result and "oracle" in result:
        try:
            result["qualification"] = qualify_normal(
                result["forward"], result["oracle"], levels, plan["normal_api"]["settings"]
            )
            result["qualified"] = result["qualification"]["qualified"]
        except Exception as error:
            result["qualification_error"] = error_record(error, "normal_qualification")
            result["protocol_failure"] |= not isinstance(error, ArithmeticError)
            result["qualified"] = False
    if elementary_control is not None:
        try:
            result["elementary"] = oracle_module.elementary_reference(elementary_control, constants)
            ready(result["elementary"])
            result["protocol_failure"] |= result["elementary"].get("protocol_failure", False)
            if "oracle" in result:
                result["elementary_comparisons"] = elementary_comparisons(
                    result["elementary"], result["oracle"]
                )
            else:
                result["elementary_comparisons"] = [
                    {"pixel": pixel, "passed": False, "reason": "independent_oracle_unavailable"}
                    for pixel in pixels
                ]
            result["qualified"] = result["qualified"] and all(
                item["passed"] for item in result["elementary_comparisons"]
            )
        except Exception as error:
            result["elementary_error"] = error_record(error, "elementary_control")
            result["protocol_failure"] |= not isinstance(error, ArithmeticError)
            result["qualified"] = False
    result["stage"] = "complete"
    result = safe_fields(result)
    if result.get("withheld_unsafe_fields"):
        result.update(protocol_failure=True, qualified=False)
    if result.get("protocol_failure", False):
        # A later numerical comparison cannot requalify a context whose
        # independent payload or elementary-reference protocol already failed.
        result["qualified"] = False
    return result


def generic_metadata(value):
    """Only new results rename legacy helper terminology; originals stay exact."""
    if isinstance(value, list):
        return [generic_metadata(item) for item in value]
    if isinstance(value, dict):
        return {
            (
                "derivative_qualified" if key == "finite_difference_qualified" else key
            ): generic_metadata(item)
            for key, item in value.items()
        }
    return value


def derivatives_qualified(saved_records, normal_qualified, controls_qualified):
    return bool(
        len(saved_records) >= 3
        and all(record["stable"] for record in saved_records[:3])
        and normal_qualified
        and controls_qualified
    )


def matched_comparison(blocks, residual, policy, *, training=False, qualified=True):
    joined, joined_errors, labels = BASE.block_matrix(blocks, METHOD, training=training)
    reference_report, _, _ = BASE.decompose(joined, joined_errors, policy)
    covariance, covariance_errors, _ = BASE.block_matrix(blocks, ("S",), training=training)
    residual = BASE.array(residual[:40] if training else residual)
    factor = policy["roundoff_multiplier"] * NP.finfo(float).eps * max(1, *joined.shape)
    eta_s = BASE.norm(covariance_errors) + factor * BASE.norm(covariance)
    states = []
    for names in (("B", "G"), ("B", "G", "N")):
        nuisance, errors, nuisance_labels = BASE.block_matrix(blocks, names, training=training)
        report, basis, _ = BASE.decompose(
            nuisance,
            errors,
            policy,
            reference=(joined, joined_errors),
            cutoff=reference_report["cutoff"],
        )
        eta_t = BASE.norm(errors) + factor * BASE.norm(nuisance)
        minimum = (
            report["singular_values"][-1]
            if nuisance.shape[1] and report["full_column_rank_resolved"]
            else None
        )
        gap_known = nuisance.shape[1] == 0 or minimum is not None and minimum > eta_t
        eta_p = (
            0.0
            if nuisance.shape[1] == 0
            else min(1.0, 2 * eta_t / (minimum - eta_t))
            if gap_known
            else None
        )
        known = bool(gap_known and eta_p < 1)
        projection_arithmetic = factor * (BASE.norm(covariance) + eta_s)
        eta_c = (
            eta_s + eta_p * (BASE.norm(covariance) + eta_s) + projection_arithmetic
            if known
            else None
        )
        states.append(
            {
                "name": "".join(names),
                "report": report,
                "basis": basis,
                "labels": nuisance_labels,
                "eta_t": eta_t,
                "smin": minimum,
                "eta_p": eta_p,
                "known": known,
                "eta_c": eta_c,
                "projection_arithmetic": projection_arithmetic,
            }
        )
    both_known = all(state["known"] for state in states)
    tau = (
        max(
            reference_report["cutoff"],
            *(policy["derivative_discrepancy_multiplier"] * state["eta_c"] for state in states),
        )
        if both_known
        else None
    )
    result = {
        "full_BGNS_reference": reference_report,
        "column_labels": labels,
        "base_cutoff": reference_report["cutoff"],
        "common_matched_cutoff": tau,
        "derivative_qualified": bool(qualified),
        "both_nuisance_projectors_qualified": both_known,
        "status": "unknown",
        "nuisances": {},
    }
    for state in states:
        unique = covariance - state["basis"] @ (state["basis"].T @ covariance)
        report, basis, _ = BASE.decompose(
            unique,
            NP.zeros_like(unique),
            policy,
            reference=(joined, joined_errors),
            cutoff=tau if tau is not None else reference_report["cutoff"],
        )
        ceiling = max(0, len(residual) - state["report"]["retained_rank"])
        basis = BASE.projected_rank_policy(
            report,
            basis,
            ceiling,
            projector_known=both_known,
            fd_qualified=qualified,
            nuisance_rank_resolved=state["report"]["rank_resolved"],
        )
        projected_residual = BASE.projected_residual(residual, state["basis"])
        unique_qualified = report["rank_resolved"]
        coordinates = basis.T @ projected_residual
        result["nuisances"][state["name"]] = {
            "nuisance": state["report"],
            "column_labels": state["labels"],
            "nuisance_error_estimate": state["eta_t"],
            "nuisance_smallest_singular_value": state["smin"],
            "projector_error_estimate": state["eta_p"],
            "projector_error_qualified": state["known"],
            "covariance_unprojected_error_estimate": eta_s,
            "projection_arithmetic_estimate": state["projection_arithmetic"],
            "covariance_error_estimate": state["eta_c"],
            "projected_covariance": unique.tolist(),
            "projected_covariance_spectrum": report,
            "residual_dimension_ceiling": ceiling,
            "nuisance_projected_residual": projected_residual.tolist(),
            "qualified_unique_covariance_residual_energy": float(coordinates @ coordinates)
            if unique_qualified
            else None,
            "qualified_unique_covariance_residual_projection": (basis @ coordinates).tolist()
            if unique_qualified
            else None,
            "qualified_unique_covariance_rank": report["retained_rank"]
            if unique_qualified
            else None,
        }
    if (
        both_known
        and qualified
        and all(
            item["projected_covariance_spectrum"]["rank_resolved"]
            for item in result["nuisances"].values()
        )
    ):
        result["status"] = "resolved_under_estimated_guard"
    result["physical_identifiability_claim"] = False
    return result


def data_from_saved(row):
    baseline, observations = row["baseline"], row["observations"]
    return {
        "parameters": copy.deepcopy(baseline["parameters"]),
        "levels": copy.deepcopy(baseline["levels"]),
        "bounds": copy.deepcopy(baseline["bounds"]),
        "domain_widths": copy.deepcopy(baseline["domain_widths"]),
        "pixels": copy.deepcopy(observations["pixels_xy"]),
        "values": copy.deepcopy(observations["values"]),
        "mean": copy.deepcopy(baseline["mean"]),
        "residual": copy.deepcopy(baseline["residual"]),
    }


def analyze_data(data, blocks, calls, plan, qualified, analysis):
    """No original row, old flag, evaluation or truth object enters this worker."""
    if any("truth" in key or "scoring" in key or "old_" in key for key in data):
        raise ValueError("truth/old flags are forbidden in the analysis worker")
    analysis["derivative_qualified"] = bool(qualified)
    missing = [name for name in METHOD if blocks[name]["values"] is None]
    if missing:
        analysis.update(
            status="diagnostic_unknown",
            numerically_unresolved_blocks=missing,
            step={
                "model": list(METHOD),
                "status": "withheld",
                "reason": "numerically_unresolved_derivative",
                "local_linearization_qualified": False,
            },
        )
        return
    analysis["information"] = {}
    for training in (False, True):
        scope = "training40" if training else "all56"
        matrix, errors, labels = BASE.block_matrix(blocks, METHOD, training=training)
        report, basis, _ = BASE.decompose(matrix, errors, plan["rank_policy"])
        report.update(
            raw_rank_resolved=report["rank_resolved"],
            raw_full_column_rank_resolved=report["full_column_rank_resolved"],
            derivative_qualified=bool(qualified),
            rank_resolved=bool(report["rank_resolved"] and qualified),
            full_column_rank_resolved=bool(report["full_column_rank_resolved"] and qualified),
            column_labels=labels,
            status="evaluated" if qualified else "unknown_derivative_qualification",
        )
        residual = BASE.array(data["residual"][:40] if training else data["residual"])
        projected = BASE.projected_residual(residual, basis)
        report.update(
            projected_residual=projected.tolist(),
            projected_residual_energy=float(projected @ projected),
            projection_interpretation="Raw truncated diagnostic; qualified claims require derivative/rank guards.",
        )
        nuisance, nuisance_errors, _ = BASE.block_matrix(blocks, ("B", "G", "N"), training=training)
        covariance, covariance_errors, _ = BASE.block_matrix(blocks, ("S",), training=training)
        native = generic_metadata(
            BASE.covariance_comparison(
                nuisance,
                nuisance_errors,
                covariance,
                covariance_errors,
                residual,
                plan["rank_policy"],
                fd_qualified=qualified,
            )
        )
        analysis["information"][scope] = {
            "full_BGNS": report,
            "native_BGN_versus_S": native,
            "matched_BG_and_BGN_versus_S": matched_comparison(
                blocks,
                data["residual"],
                plan["rank_policy"],
                training=training,
                qualified=qualified,
            ),
        }
    analysis["step"] = {
        "model": list(METHOD),
        "status": "withheld",
        "local_linearization_qualified": False,
    }
    if not qualified:
        analysis["step"]["reason"] = "derivative_or_global_controls_unknown"
        analysis["status"] = "diagnostic_unknown"
        return
    try:
        BASE.tangent_step(
            data, blocks, METHOD, BASE.array(data["mean"]), calls, plan, True, analysis["step"]
        )
        analysis["step"] = generic_metadata(analysis["step"])
        training = analysis["information"]["training40"]["full_BGNS"]
        actual = analysis["step"]["training_matrix"]
        analysis["step"]["reported_full_training_cutoff_same"] = (
            actual["cutoff"] == training["cutoff"]
            and actual["singular_values"] == training["singular_values"]
        )
        if not analysis["step"]["reported_full_training_cutoff_same"]:
            raise ValueError("trial used a different full-J training cutoff")
    except Exception as error:
        BASE.step_failure(analysis["step"], error)
    analysis["status"] = (
        "diagnostic_protocol_failure"
        if analysis["step"].get("protocol_failure")
        else "diagnostic_evaluated"
    )


def algebra_controls(plan):
    """Ten invented-array controls; invoked only by the committed canonical run."""
    results = []
    eye = None

    def blocks_for(b, g, n, s, n_error=None):
        return {
            name: {
                "values": value.tolist(),
                "errors": (
                    NP.zeros_like(value) if name != "N" or n_error is None else n_error
                ).tolist(),
                "labels": [f"{name}{i}" for i in range(value.shape[1])],
                "scales": [1.0] * value.shape[1],
            }
            for name, value in (("B", b), ("G", g), ("N", n), ("S", s))
        }

    for index, name in enumerate(plan["algebra_controls"]):
        record = {"name": name, "passed": False}
        results.append(record)
        try:
            eye = NP.eye(8)
            b, g = eye[:, :1], eye[:, 1:2]
            n, s = eye[:, 2:3], eye[:, 3:6]
            if index in (1, 2):
                s = eye[:, 2:5]
                n = eye[:, 2:3] if index == 1 else eye[:, 5:6]
            if index == 3:
                g, n, s = eye[:, :0], eye[:, 2:3], eye[:, 1:2] + eye[:, 2:3]
            if index <= 6 and index != 6:
                errors = NP.ones_like(n) * 10 if index == 4 else None
                if index == 5:
                    n, errors = b + 1e-15 * n, NP.ones_like(n) * 1e-10
                blocks = blocks_for(b, g, n, s, errors)
                residual = eye[:, 1] - eye[:, 2] if index == 3 else eye[:, 3]
                comparison = matched_comparison(blocks, residual.tolist(), plan["rank_policy"])
                record["comparison"] = comparison
                bg, bgn = (comparison["nuisances"][key] for key in ("BG", "BGN"))
                if index == 0:
                    passed = (
                        comparison["common_matched_cutoff"] is not None
                        and bg["projected_covariance_spectrum"]["cutoff"]
                        == bgn["projected_covariance_spectrum"]["cutoff"]
                        == comparison["common_matched_cutoff"]
                        and bg["nuisance"]["cutoff"]
                        == bgn["nuisance"]["cutoff"]
                        == comparison["base_cutoff"]
                    )
                elif index == 1:
                    passed = (
                        bg["qualified_unique_covariance_rank"] == 3
                        and bgn["qualified_unique_covariance_rank"] == 2
                    )
                elif index == 2:
                    passed = (
                        bg["qualified_unique_covariance_rank"]
                        == bgn["qualified_unique_covariance_rank"]
                        == 3
                    )
                elif index == 3:
                    passed = (
                        bgn["qualified_unique_covariance_residual_energy"]
                        > bg["qualified_unique_covariance_residual_energy"]
                    )
                else:
                    passed = (
                        not comparison["both_nuisance_projectors_qualified"]
                        and comparison["status"] == "unknown"
                        and not comparison["full_BGNS_reference"]["full_column_rank_resolved"]
                    )
            elif index == 6:
                columns, labels, faces, _ = BASE.free_brightness(
                    NP.array([0.25, 0.5, 0.75]), [0, 255]
                )
                record.update(columns=columns.tolist(), labels=labels, faces=faces)
                passed = (
                    columns.shape == (3, 0)
                    and labels == []
                    and [face["face"] for face in faces] == ["lower", "upper"]
                )
            elif index == 7:
                value, estimate, components = scaled_normal(2.0, 1e-12, 2.0, 1e-13, [200.0, 10.0])
                check_scaled_normal(value, estimate, -380.0, estimate)
                rejected = False
                try:
                    check_scaled_normal(value, estimate * 190, value, estimate)
                except ValueError:
                    rejected = True
                global_pixel = [1 + 0.5 + 3, 2 + 0.5 + 4]
                record.update(
                    value=value,
                    error=estimate,
                    components=components,
                    global_pixel=global_pixel,
                    double_scaling_refused=rejected,
                )
                passed = (
                    rejected
                    and global_pixel == [4.5, 6.5]
                    and value < 0
                    and global_pixel != [5.0, 7.0]
                )
            elif index == 8:
                report = {
                    "rank_interval": [1, 2],
                    "retained_rank": 2,
                    "rank_resolved": False,
                    "full_column_rank_resolved": False,
                    "shape": [4, 2],
                }
                basis = BASE.projected_rank_policy(
                    report,
                    NP.eye(4)[:, :2],
                    1,
                    projector_known=True,
                    fd_qualified=True,
                    nuisance_rank_resolved=True,
                )
                record["rank_report"] = report
                passed = (
                    report["rank_interval"] == [1, 1]
                    and not report["rank_resolved"]
                    and report["raw_rank_interval"] == [1, 2]
                    and basis.shape[1] == report["basis_columns_used"] == 1
                )
            else:
                old = [{"stable": True}] * 3 + [{"stable": False}]
                passed = derivatives_qualified(old, True, True) and old[-1]["stable"] is False
                record["old_FD_stable"] = all(item["stable"] for item in old)
            if not passed:
                raise AssertionError("frozen invented-array algebra control failed")
            record["passed"] = True
        except Exception as error:
            record["error"] = error_record(error, "invented_algebra_control")
    return results


def scientific_run(report, plan, saved, intensity, calls, oracle_module):
    report["rules"] = {}
    rules = make_rules(report["rules"])
    report["constants"] = oracle_module.make_constants((80, 120))
    report["algebra_controls"] = algebra_controls(plan)
    report["normal_controls"] = []
    for control in (*plan["controls"], plan["legacy_normal_control"]):
        calls.context = {"scope": "normal_control", "id": control["id"]}
        print(f"normal control {control['id']}: starting", file=sys.stderr, flush=True)
        result = {"id": control["id"], "definition": copy.deepcopy(control)}
        if control is plan["legacy_normal_control"]:
            result["original_failed_FD_control"] = copy.deepcopy(
                saved["independent_forward_controls"][control["legacy_control_index"]]
            )
        result["new_analytic"] = normal_context(
            control["parameters"],
            control["pixels"],
            control["levels"],
            calls,
            oracle_module,
            rules,
            report["constants"],
            plan,
            elementary_control=control if control in plan["controls"] else None,
        )
        report["normal_controls"].append(result)
        print(
            f"normal control {control['id']}: qualified={result['new_analytic']['qualified']}",
            file=sys.stderr,
            flush=True,
        )
    controls_qualified = all(item["passed"] for item in report["algebra_controls"]) and all(
        item["new_analytic"]["qualified"] and not item["new_analytic"]["protocol_failure"]
        for item in report["normal_controls"]
    )
    report["independent_controls_qualified"] = controls_qualified
    saved_cov_controls = saved["independent_forward_controls"][:3]
    covariance_controls_qualified = len(saved_cov_controls) == 3 and all(
        item["passed"] for item in saved_cov_controls
    )
    intensity_rows = {row["index"]: row for row in intensity["rows"]}
    report["rows"] = retained_rows(plan, saved)
    for index, (expected, old) in enumerate(zip(plan["population"], saved["rows"], strict=True)):
        result = report["rows"][index]
        result["original_row_sha256"] = digest(canonical_bytes(old))
        if not expected["eligible"]:
            result.update(
                status="upstream_ineligible",
                reason=old.get("reason"),
                new_normal_calls=0,
                new_trial_calls=0,
            )
            continue
        print(
            f"row {index + 1}/12 {old['name']} {old['lane']}: starting", file=sys.stderr, flush=True
        )
        calls.context = {
            "scope": "archived_row",
            **{key: old[key] for key in ("index", "name", "lane")},
        }
        start = len(calls.log)
        try:
            result["stage"] = "saved_pixel_binding"
            result["input_binding"] = BASE.verify_pixels(intensity_rows[old["index"]])
            if result["input_binding"] != old["input_binding"]:
                raise ValueError("new saved-pixel binding differs from original")
            data = data_from_saved(old)
            result["observations"] = copy.deepcopy(old["observations"])
            result["baseline"] = copy.deepcopy(old["baseline"])
            result["active_brightness"] = copy.deepcopy(old["active_brightness"])
            result["blocks"] = {
                name: copy.deepcopy(old["blocks"][name]) for name in ("B", "G", "S")
            }
            result["stage"] = "new_normal_and_independent_reference"
            result["normal"] = normal_context(
                data["parameters"],
                data["pixels"],
                data["levels"],
                calls,
                oracle_module,
                rules,
                report["constants"],
                plan,
            )
            result["blocks"]["N"] = (
                result["normal"]
                .get("qualification", {})
                .get(
                    "block",
                    {
                        "values": None,
                        "errors": None,
                        "labels": ["normal_angle"],
                        "scales": [1],
                        "units": "source-plane radians",
                    },
                )
            )
            qualified = derivatives_qualified(
                old["finite_differences"],
                result["normal"]["qualified"] and not result["normal"]["protocol_failure"],
                controls_qualified and covariance_controls_qualified,
            )
            result["qualification"] = {
                "saved_covariance_FD_qualified": all(
                    item["stable"] for item in old["finite_differences"][:3]
                ),
                "saved_covariance_controls_qualified": covariance_controls_qualified,
                "analytic_normal_qualified": result["normal"]["qualified"],
                "global_controls_qualified": controls_qualified,
                "derivative_qualified": qualified,
                "historical_normal_FD_not_a_new_gate": True,
            }
            result["stage"] = "new_N_dependent_algebra_and_single_trial"
            result["analysis"] = {}
            analyze_data(data, result["blocks"], calls, plan, qualified, result["analysis"])
            result["status"] = (
                "diagnostic_protocol_failure"
                if result["normal"]["protocol_failure"]
                else result["analysis"]["status"]
            )
            result["stage"] = "complete"
        except Exception as error:
            result.update(
                status="diagnostic_unknown"
                if isinstance(error, ArithmeticError)
                else "diagnostic_protocol_failure",
                error=error_record(error, result.get("stage", "row_setup")),
            )
        result["work_log_indices"] = list(range(start, len(calls.log)))
        if (
            digest(canonical_bytes(result["original_residual_row"]))
            != expected["original_row_sha256"]
        ):
            result.update(status="diagnostic_protocol_failure", original_row_mutated=True)
        safe = safe_fields(result)
        if safe.get("withheld_unsafe_fields"):
            safe["status"] = "diagnostic_protocol_failure"
        report["rows"][index] = safe
        print(f"row {index + 1}/12: {safe['status']}", file=sys.stderr, flush=True)
    # All parameter choices/predictions are fixed BEFORE any truth is read.
    for row in report["rows"]:
        step = row.get("analysis", {}).get("step")
        if step is not None:
            try:
                row["evaluation_after_all_predictions"] = BASE.descriptive_evaluation(
                    intensity_rows[row["index"]], {"steps": [step]}
                )
            except Exception as error:
                row.update(
                    status="diagnostic_protocol_failure",
                    evaluation_error=error_record(
                        error, "descriptive_evaluation_after_all_predictions"
                    ),
                )


def summary(report, calls):
    rows = report.get("rows", [])
    contexts = [control["new_analytic"] for control in report.get("normal_controls", [])]
    contexts.extend(row["normal"] for row in rows if "normal" in row)
    comparisons = [
        query
        for context in contexts
        for query in context.get("qualification", {}).get("queries", [])
    ]
    trials = [row["analysis"]["step"] for row in rows if row.get("analysis", {}).get("step")]
    executed = [step for step in trials if step.get("status") == "evaluated_once"]
    result = {
        "rows_retained": len(rows),
        "upstream_ineligible": sum(row["status"] == "upstream_ineligible" for row in rows),
        "diagnostic_evaluated": sum(row["status"] == "diagnostic_evaluated" for row in rows),
        "diagnostic_unknown": sum(row["status"] == "diagnostic_unknown" for row in rows),
        "protocol_failure_rows": sum(
            row["status"]
            not in ("diagnostic_evaluated", "diagnostic_unknown", "upstream_ineligible")
            for row in rows
        ),
        "normal_contexts_retained": len(contexts),
        "normal_queries_compared": len(comparisons),
        "normal_query_comparisons_passed": sum(query["qualified"] for query in comparisons),
        "algebra_controls_passed": sum(
            item["passed"] for item in report.get("algebra_controls", [])
        ),
        "normal_controls_qualified": sum(
            control["new_analytic"]["qualified"] for control in report.get("normal_controls", [])
        ),
        "BGNS_trials_executed_once": len(executed),
        "BGNS_zero_steps": sum(step.get("status") == "zero_step" for step in trials),
        "executed_BGNS_linearity_passes": sum(
            step.get("local_linearization_qualified", False) for step in executed
        ),
        "executed_BGNS_linearity_all_passed": all(
            step.get("local_linearization_qualified", False) for step in executed
        )
        if executed
        else None,
        "old_targets_passed": sum(row.get("old_targets_passed") is True for row in rows),
        "old_completions_passed": sum(row.get("old_completion_passed") is True for row in rows),
        "new_fit_pass_count": None,
    }
    work = (
        calls.summary()
        if calls
        else {
            "calls": [],
            "normal_calls_attempted": 0,
            "normal_queries_attempted": 0,
            "trial_mean_calls_attempted": 0,
            "optimizer_calls": 0,
            "optimizer_attempts": 0,
            "renderer_calls": 0,
            "preparation_calls": 0,
        }
    )
    report["work"] = work
    oracle_work = {}
    for context in contexts:
        for name, value in context.get("oracle", {}).get("work", {}).items():
            oracle_work[name] = oracle_work.get(name, 0) + value
    report["source_chord_oracle_work"] = oracle_work
    report["summary"] = result
    report["protocol_passed"] = bool(
        report.get("source_unchanged")
        and not report.get("startup_failure")
        and not report.get("binding_errors")
        and result["rows_retained"] == 12
        and result["upstream_ineligible"] == 2
        and result["protocol_failure_rows"] == 0
        and result["normal_contexts_retained"] == 15
        and result["normal_queries_compared"] == result["normal_query_comparisons_passed"] == 578
        and result["algebra_controls_passed"] == 10
        and result["normal_controls_qualified"] == 5
        and result["executed_BGNS_linearity_passes"] == len(executed)
        and work["normal_calls_attempted"] == 15
        and work["normal_queries_attempted"] == 578
        and work["trial_mean_calls_attempted"] <= 10
        and work["optimizer_attempts"] == 0
        and oracle_work.get("attempted_density_nodes", 0)
        <= report["plan"]["source_chord_oracle"]["maximum_density_nodes_total"]
        and all(not context.get("protocol_failure", False) for context in contexts)
        and all(not step.get("protocol_failure", False) for step in trials)
    )


def run(plan):
    before = snapshot(plan)
    report = {
        "format": "pictures-to-cad-finite-analytic-normal-information",
        "version": 1,
        "plan": plan,
        "plan_sha256": digest(PLAN.read_bytes()),
        "source_before": before,
        "rows": retained_rows(plan),
        "protocol_passed": False,
        "scope": plan["objective"],
        "python": platform.python_version(),
        "production_trace_adoption": False,
    }
    calls, saved, stage = None, None, "source_binding"
    started = time.perf_counter()
    try:
        report["binding_errors"] = binding_errors(plan, before)
        # Read the historical report before refusing another pin so all original
        # rows/flags can be retained. No unverified value reaches scientific code.
        stage = "saved_original_read"
        if before.get(SAVED, {}).get("sha256") != plan["inputs_sha256"][SAVED]:
            raise ValueError("saved original gzip source pin differs")
        with gzip.GzipFile(fileobj=io.BytesIO((ROOT / SAVED).read_bytes())) as stream:
            raw = stream.read(64 * 1024 * 1024 + 1)
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError("saved decoded report exceeds the inherited 64 MiB loading cap")
        saved = strict_json(raw)
        report["rows"] = retained_rows(plan, saved)
        if report["binding_errors"]:
            raise ValueError("frozen source/plan/input differs")
        if digest(raw) != plan["original_residual_decoded_sha256"]:
            raise ValueError("complete original decoded report differs")
        original_rows(plan, saved)
        report["original_residual"] = {
            "compressed_path": SAVED,
            "compressed_sha256": before[SAVED]["sha256"],
            "decoded_sha256": digest(raw),
            "decoded_bytes": len(raw),
            "protocol_passed": saved["protocol_passed"],
            "summary": copy.deepcopy(saved["summary"]),
            "independent_forward_controls": copy.deepcopy(saved["independent_forward_controls"]),
            "work": copy.deepcopy(saved["work"]),
            "source_before": copy.deepcopy(saved["source_before"]),
            "source_after": copy.deepcopy(saved["source_after"]),
            "original_replaced_or_relabelled": False,
        }
        stage = "pinned_stdlib_helpers"
        global BASE, NP
        BASE = load_module("analytic_normal_saved_residual_helper", BASE_PATH)
        oracle_module = load_module("analytic_normal_independent_oracle", ORACLE_PATH)
        intensity = strict_json((ROOT / INTENSITY).read_bytes())
        stage = "numerical_imports_after_binding"
        import numpy

        NP = numpy
        BASE.np = NP
        report["numpy"] = NP.__version__
        sys.path.insert(0, str(ROOT))
        from backend import finite_centre_fit, finite_normal

        calls = Calls(finite_centre_fit, finite_normal)
        finite_centre_fit.fit_circular_segment = calls.forbidden
        stage = "declared_scientific_run"
        scientific_run(report, plan, saved, intensity, calls, oracle_module)
    except Exception as error:
        report["startup_failure"] = error_record(error, stage)
        if not report.get("rows"):
            report["rows"] = retained_rows(plan, saved, stage=stage, error=error)
        for row in report["rows"]:
            if row["status"] == "not_evaluated_protocol_failure":
                row.update(stage=stage, error=error_record(error, stage))
    after = snapshot(plan)
    report.update(
        source_after=after,
        source_unchanged=before == after,
        runtime_seconds=time.perf_counter() - started,
    )
    summary(report, calls)
    return ready(report)


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, metavar="NEW_JSON")
    args = parser.parse_args(arguments)
    try:
        output, descriptor = reserve_output(args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    with os.fdopen(descriptor, "w") as stream:
        try:
            plan = strict_json(PLAN.read_bytes())
            result = run(plan)
        except Exception as error:
            result = {
                "format": "pictures-to-cad-finite-analytic-normal-information",
                "version": 1,
                "protocol_passed": False,
                "error": error_record(error, "unreadable_plan_or_report"),
                "rows": [],
                "scope": "No complete known census available; no scientific success claim.",
            }
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
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
    return 0 if result["protocol_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
