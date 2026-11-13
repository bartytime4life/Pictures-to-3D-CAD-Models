#!/usr/bin/env python3
"""Diagnose finite-chord oracle arithmetic under the frozen restricted plan.

This is a separate post-hoc/prospective arithmetic diagnostic, not a repaired
canonical qualification. It calls no production API, inverse, renderer or area
model. Four methods share new, recorded binary64 Gauss rules and fixed source
partitions. The original V2 report, flags and error estimates remain unchanged.
--help and destination refusals occur before NumPy or numerical helper imports.
"""

# Broad catches retain explicit failed records, never qualified partial results.
# ruff: noqa: BLE001

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import itertools
import json
import math
import os
import platform
import sys
import time
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-normal-oracle-conditioning-v1.json"
PLAN_SHA256 = "33fd9504167978f1a22522122e7899b0c4bf64ab56905bbf9fa670070a1f8fe2"
V2_PATH = "studies/verification/finite-normal-error-control-v2.py"
V2_PLAN_PATH = "studies/finite-normal-error-control-v2.json"
CANONICAL = "studies/results/finite-normal-error-control-v2.json.gz"
METHODS = ("baseline", "endpoint_binary64", "exact_source_decimal", "rounded_source_decimal")
NP = None


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def unique_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_float(value):
    answer = float(value)
    if not math.isfinite(answer):
        raise ValueError("nonfinite JSON number")
    return answer


def strict_json(value):
    return json.loads(
        value,
        object_pairs_hook=unique_pairs,
        parse_float=parse_float,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def json_ready(value):
    return strict_json(json.dumps(value, allow_nan=False))


def error_record(error):
    return {"type": type(error).__name__, "message": str(error)[:4096]}


def fraction_text(value):
    return f"{value.numerator}/{value.denominator}"


def decimal_text(value):
    if not value.is_finite():
        raise ArithmeticError("nonfinite Decimal result")
    return str(value)


def rational(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("expected represented finite real input")
    if not math.isfinite(value):
        raise ValueError("nonfinite represented input")
    return Fraction(value)


def to_decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def validate_output(path):
    path = Path(path).absolute()
    if os.path.lexists(path) or not path.parent.is_dir():
        raise ValueError("output must be a fresh path in an existing directory")
    return path


def source_snapshot(plan):
    # load_v2_context validates these transitive pins even though no production
    # model is imported. Carry every consulted file in this runner's own receipt.
    expected = dict(plan.get("inputs_sha256", {}))
    expected[PLAN.relative_to(ROOT).as_posix()] = PLAN_SHA256
    expected[RUNNER.relative_to(ROOT).as_posix()] = None
    closure_error = None
    try:
        v2_plan = strict_json((ROOT / V2_PLAN_PATH).read_text())
        for group in ("inputs_sha256", "regression_plans"):
            pins = v2_plan[group]
            if not isinstance(pins, dict):
                raise TypeError(f"V2 {group} must be a path/hash mapping")
            for name, digest in pins.items():
                if (
                    not isinstance(name, str)
                    or Path(name).is_absolute()
                    or ".." in Path(name).parts
                    or not isinstance(digest, str)
                    or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)
                ):
                    raise ValueError("invalid transitive V2 source pin")
                if name in expected and expected[name] != digest:
                    raise ValueError(f"conflicting transitive V2 source pin: {name}")
                expected[name] = digest
    except Exception as error:
        # A readable main plan still supplies the complete 26-row identity
        # census when this indirect plan is missing or malformed.
        closure_error = error_record(error)
    result = {}
    for name, digest in sorted(expected.items()):
        try:
            data = (ROOT / name).read_bytes()
            result[name] = {
                "sha256": sha_bytes(data),
                "bytes": len(data),
                "expected_sha256": digest,
            }
        except OSError as error:
            result[name] = {"error": error_record(error), "expected_sha256": digest}
    if closure_error is not None:
        result.setdefault(V2_PLAN_PATH, {})["closure_error"] = closure_error
    return result


def binding_errors(plan, before):
    result = []
    for name, item in before.items():
        if "error" in item:
            result.append({"path": name, "reason": "source_read_failure"})
        if "closure_error" in item:
            result.append({"path": name, "reason": "transitive_source_discovery_failure"})
        expected = item.get("expected_sha256")
        if expected is not None and item.get("sha256") != expected:
            result.append({"path": name, "reason": "frozen_input_sha256"})
    return result


def family(scene):
    """Assert the complete restriction before using its elementary identity."""
    supplied = scene["input"]
    if (
        supplied["centre"] != [0.0, 0.0]
        or supplied["radius"] != 1.0
        or supplied["fraction"] != 0.0
        or supplied["normal"] != [1.0, 0.0]
        or supplied["covariance"] != [[1.0, 0.0], [0.0, 1.0]]
        or supplied["pixels_xy"] != [[0, 0]]
        or supplied["sensor_shape"] != [3, 3]
    ):
        raise ValueError("scene is outside the frozen restricted shape/query/PSF family")
    h = [[rational(v) for v in row] for row in supplied["homography"]]
    if len(h) != 3 or any(len(row) != 3 for row in h):
        raise ValueError("restricted homography must be 3x3")
    c = h[2][1]
    d = h[1][1] - c / 2
    if (
        h[0] != [Fraction(1), c / 2, Fraction(1, 2)]
        or h[1][0] != 0
        or h[1][2] != Fraction(1, 2)
        or h[2][0] != 0
        or h[2][2] != 1
        or not abs(c) < 1
        or d == 0
    ):
        raise ValueError("homography is outside the exact declared c/d family")
    return h, c, d


def load_v2_context():
    spec = importlib.util.spec_from_file_location("conditioning_pinned_v2", ROOT / V2_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load pinned V2 stdlib context")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_context()  # Validation/stdlib helper loading only, never initialize_models.
    return module


def rules_once(np, base, orders):
    records, rules = {}, {}
    for order in orders:
        nodes, weights = np.polynomial.legendre.leggauss(order)
        if (
            not np.isfinite(nodes).all()
            or not np.isfinite(weights).all()
            or len(nodes) != order
            or len(weights) != order
            or np.any(np.abs(nodes) >= 1)
            or np.any(weights <= 0)
        ):
            raise ValueError("invalid generated finite Gauss rule")
        payload = {
            "nodes_hex": [float(v).hex() for v in nodes],
            "weights_hex": [float(v).hex() for v in weights],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        records[str(order)] = {**payload, "sha256": sha_bytes(encoded), "order": order}
        nodes.setflags(write=False)
        weights.setflags(write=False)
        rules[order] = (nodes, weights)
    base.RULES = rules.copy()
    return rules, records


def machin_pi(precision):
    """Alternating rational arctangents, 15 decimal digits past each context."""
    threshold = Fraction(1, 10 ** (precision + 15))

    def atan_reciprocal(q):
        total, power, sign, count = Fraction(), q, 1, 0
        while True:
            total += Fraction(sign, (2 * count + 1) * power)
            count += 1
            power *= q * q
            omitted = Fraction(1, (2 * count + 1) * power)
            if omitted < threshold:
                return total, omitted, count
            if count > 10000:
                raise ArithmeticError("bounded Machin series did not terminate")
            sign = -sign

    first, first_tail, first_count = atan_reciprocal(5)
    second, second_tail, second_count = atan_reciprocal(239)
    exact = 16 * first - 4 * second
    with localcontext() as context:
        context.prec = precision + 15
        extended = to_decimal(exact)
        context.prec = precision
        value = +extended
    return value, {
        "precision": precision,
        "pi": decimal_text(value),
        "terms": {"atan_1_5": first_count, "atan_1_239": second_count},
        "alternating_series_absolute_tail_bound": fraction_text(16 * first_tail + 4 * second_tail),
        "scope": "Finite Machin series tail bound; Decimal conversion/evaluation not certified.",
    }


def elementary_reference(c, d, precision, pi):
    with localcontext() as context:
        context.prec = precision
        plus = to_decimal(-d * d / (2 * (1 + c) ** 2)).exp()
        minus = to_decimal(-d * d / (2 * (1 - c) ** 2)).exp()
        answer = (plus - minus) / (2 * pi * to_decimal(abs(d)))
        return decimal_text(answer)


def fixed_partitions(scene, old_rows, layers):
    if scene["population"].startswith("post_hoc"):
        original = old_rows[scene["id"]]
        if original["input"] != scene["input"]:
            raise ValueError("saved old scene differs from frozen diagnostic input")
        query = original["queries"][scene["original_query_index"]]
        leaves = query["oracle"]["leaf_panels"]
        if (
            not leaves
            or leaves[0]["start"] != -1
            or leaves[-1]["end"] != 1
            or any(a["end"] != b["start"] for a, b in itertools.pairwise(leaves))
            or any(p["start"] >= p["end"] for p in leaves)
        ):
            raise ValueError("old saved forest does not completely partition the source chord")
        return [dict(p) for p in leaves], {
            "row_protocol_passed": original["protocol_passed"],
            "row_status": original["status"],
            "candidate": original["candidate"],
            "query": query,
        }
    cuts = sorted(
        {
            -1.0,
            0.0,
            1.0,
            *(-1.0 + 2.0**-k for k in range(1, layers + 1)),
            *(1.0 - 2.0**-k for k in range(1, layers + 1)),
        }
    )
    if len(cuts) != 2 * layers + 3:
        raise ValueError("fixed endpoint partition count differs")
    return [
        {"start": a, "end": b, "method": "direct_source_s"} for a, b in itertools.pairwise(cuts)
    ], None


def exact_residual(h, s):
    # The asserted source chord is (0,s), query centre is (.5,.5).
    homogeneous = [row[1] * s + row[2] for row in h]
    w = homogeneous[2]
    if w <= 0:
        raise ArithmeticError("exact source node reaches a projective horizon")
    return w, [homogeneous[i] - w / 2 for i in (0, 1)]


def endpoint_rule(geometry, point, start, end, order, rules):
    """Round exact homogeneous endpoints once, then positive interpolation."""
    nodes, weights = rules[order]
    h = [[Fraction(float(v)) for v in row] for row in geometry["h"]]
    wa, ra = exact_residual(h, Fraction(start))
    wb, rb = exact_residual(h, Fraction(end))
    left, right = (1 - nodes) / 2, (1 + nodes) / 2
    w = left * float(wa) + right * float(wb)
    numerator = left[:, None] * NP.asarray([float(v) for v in ra])
    numerator += right[:, None] * NP.asarray([float(v) for v in rb])
    half, middle = (end - start) / 2, (start + end) / 2
    signed_s = middle + half * nodes
    if NP.any(w <= 0):
        raise ArithmeticError("interpolated source node reaches horizon")
    x = numerator[:, 0] / (w * geometry["l00"])
    y = (numerator[:, 1] / w - geometry["l10"] * x) / geometry["l11"]
    active = signed_s != 0
    values = NP.zeros(order)
    with NP.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        logarithm = (
            math.log(half)
            + geometry["log_density"]
            + geometry["log_determinant"]
            + NP.log(NP.abs(signed_s[active]))
            + NP.log(weights[active])
            - 3 * NP.log(w[active])
            - (x[active] ** 2 + y[active] ** 2) / 2
        )
        values[active] = -NP.sign(signed_s[active]) * NP.exp(logarithm)
    if not NP.isfinite(values).all():
        raise ArithmeticError("nonfinite endpoint-interpolated contributions")
    answer = math.fsum(float(v) for v in values)
    absolute = math.fsum(abs(float(v)) for v in values)
    error = absolute * (
        128 * sys.float_info.epsilon + geometry["normalizer_relative_error_estimate"]
    )
    return answer, error


def rational_terms(h, start, end, order, rules, mode):
    """No density evaluation: retain exact amplitudes and Gaussian exponents."""
    nodes, weights = rules[order]
    a, b = Fraction(start), Fraction(end)
    exact_half, exact_middle = (b - a) / 2, (a + b) / 2
    rounded_s = (start + end) / 2 + ((end - start) / 2) * nodes
    determinant = h[1][1] - h[2][1] / 2  # Asserted family has exact determinant d.
    terms = []
    for node, weight, rounded in zip(nodes, weights, rounded_s, strict=True):
        s = (
            (exact_middle + exact_half * Fraction(float(node)))
            if mode == "exact_source_decimal"
            else Fraction(float(rounded))
        )
        w, residual = exact_residual(h, s)
        exponent = -(residual[0] ** 2 + residual[1] ** 2) / (2 * w * w)
        amplitude = -s * abs(determinant) * exact_half * Fraction(float(weight)) / (w**3)
        terms.append((amplitude, exponent))
    return terms


def decimal_rule(terms, precision, pi, work):
    with localcontext() as context:
        context.prec = precision
        value = Decimal(0)
        for amplitude, exponent in terms:
            work["attempted_density_nodes"] += 1
            contribution = to_decimal(amplitude) * to_decimal(exponent).exp() / (2 * pi)
            if not contribution.is_finite():
                raise ArithmeticError("nonfinite Decimal source contribution")
            value += contribution
            work["completed_density_nodes"] += 1
        return decimal_text(value)


def method_work():
    return {
        "attempted_rule_batches": 0,
        "completed_rule_batches": 0,
        "attempted_density_nodes": 0,
        "completed_density_nodes": 0,
        "exact_endpoint_evaluations": 0,
        "preserved_omitted_panels": 0,
    }


def record_failure(container, stage, error):
    container.update(
        status="execution_failure", stage=stage, error=error_record(error), protocol_passed=False
    )


def run_scene(scene, old_rows, plan, v2, rules, constants):
    row = {
        "id": scene["id"],
        "population": scene["population"],
        "input": scene["input"],
        "status": "running",
        "protocol_passed": False,
        "methods": {},
        "panels": [],
    }
    started = time.perf_counter()
    stage = "restricted_family"
    try:
        h, c, d = family(scene)
        row["represented_parameters"] = {
            "c": fraction_text(c),
            "d": fraction_text(d),
            "c_float_hex": float(c).hex(),
            "d_float_hex": float(d).hex(),
            "nominal_d": scene.get("nominal_d"),
            "scope": "d from represented H11-H21/2, never nominal_d",
        }
        stage = "fixed_partition"
        leaves, original = fixed_partitions(
            scene, old_rows, plan["partition"]["prospective_endpoint_layers"]
        )
        row["original_v2"] = original
        row["partition_source"] = scene["partition_source"]
        row["partition"] = [dict(p) for p in leaves]
        row["partition_hex"] = [[float(p["start"]).hex(), float(p["end"]).hex()] for p in leaves]
        tail = math.fsum(
            p["absolute_tail_envelope"] for p in leaves if p["method"] == "bounded_tail"
        )
        row["saved_omitted_tail_allowance"] = tail
        if original is None and tail != 0:
            raise ValueError("prospective scenes may not omit any source interval")
        stage = "original_independent_geometry"
        geometry = v2.oracle_geometry(scene["input"])
        if [[Fraction(float(v)) for v in r] for r in geometry["h"]] != h:
            raise ValueError("restricted operational map differs from declared exact source map")
        row["operational_h_hex"] = [[float(v).hex() for v in r] for r in geometry["h"]]
        row["original_normalizer"] = v2.NORMALIZER_RECORDS[scene["id"]]
        row["reference"] = {}
        for precision in plan["precision"]["decimal_contexts"]:
            row["reference"][str(precision)] = elementary_reference(
                c, d, precision, constants[precision]
            )
        orders = plan["rules"]["orders"]
        precisions = plan["precision"]["decimal_contexts"]
        accumulators = {}
        for method in METHODS:
            row["methods"][method] = {"status": "running", "work": method_work(), "values": {}}
            accumulators[method] = (
                {str(o): [] for o in orders}
                if "decimal" not in method
                else {str(p): {str(o): [] for o in orders} for p in precisions}
            )
        for index, panel in enumerate(leaves):
            item = {
                "index": index,
                "start": panel["start"],
                "end": panel["end"],
                "original_method": panel["method"],
                "methods": {},
            }
            row["panels"].append(item)
            if panel["method"] == "bounded_tail":
                item["preserved_tail_allowance"] = panel["absolute_tail_envelope"]
                for method in METHODS:
                    row["methods"][method]["work"]["preserved_omitted_panels"] += 1
                    item["methods"][method] = {"status": "preserved_omission", "no_new_nodes": True}
                continue
            if panel["method"] != "direct_source_s":
                raise ValueError("unknown original forest leaf method")
            a, b = panel["start"], panel["end"]
            item["exact_half_width"] = fraction_text((Fraction(b) - Fraction(a)) / 2)
            item["float_half_width_hex"] = ((b - a) / 2).hex()
            for method in METHODS:
                record = {"status": "running", "by_order": {}}
                item["methods"][method] = record
                work = row["methods"][method]["work"]
                try:
                    for order in orders:
                        if method in ("baseline", "endpoint_binary64"):
                            work["attempted_rule_batches"] += 1
                            work["attempted_density_nodes"] += order
                            if method == "baseline":
                                value, error = v2.direct_rule(geometry, (0.5, 0.5), a, b, order)
                            else:
                                work["exact_endpoint_evaluations"] += 2
                                value, error = endpoint_rule(
                                    geometry, (0.5, 0.5), a, b, order, rules
                                )
                            if not all(math.isfinite(v) for v in (value, error)) or error < 0:
                                raise ValueError("malformed finite binary64 rule result")
                            work["completed_rule_batches"] += 1
                            work["completed_density_nodes"] += order
                            record["by_order"][str(order)] = {
                                "value": value,
                                "value_hex": value.hex(),
                                "original_style_error_estimate": error,
                            }
                            accumulators[method][str(order)].append(value)
                        else:
                            terms = rational_terms(h, a, b, order, rules, method)
                            record["by_order"][str(order)] = {}
                            for precision in precisions:
                                work["attempted_rule_batches"] += 1
                                value = decimal_rule(terms, precision, constants[precision], work)
                                work["completed_rule_batches"] += 1
                                record["by_order"][str(order)][str(precision)] = value
                                accumulators[method][str(precision)][str(order)].append(value)
                    record["status"] = "evaluated"
                except Exception as error:
                    record_failure(record, f"panel/{index}/{method}", error)
                    row["methods"][method]["status"] = "execution_failure"
        for method in METHODS:
            result = row["methods"][method]
            if result["status"] == "execution_failure":
                result["partial_values"] = accumulators[method]
                continue
            if "decimal" in method:
                for precision in precisions:
                    with localcontext() as context:
                        context.prec = precision
                        result["values"][str(precision)] = {
                            str(o): decimal_text(
                                sum(
                                    (
                                        Decimal(v)
                                        for v in accumulators[method][str(precision)][str(o)]
                                    ),
                                    Decimal(0),
                                )
                            )
                            for o in orders
                        }
            else:
                result["values"] = {str(o): math.fsum(accumulators[method][str(o)]) for o in orders}
                if not all(math.isfinite(v) for v in result["values"].values()):
                    raise ArithmeticError("nonfinite final binary64 method total")
            result["status"] = "evaluated"
        stage = "frozen_criteria"
        row["criteria"] = evaluate_criteria(row, plan)
        row["protocol_passed"] = all(row["criteria"]["required_checks"].values())
        row["status"] = "passed" if row["protocol_passed"] else "protocol_failure"
    except Exception as error:
        record_failure(row, stage, error)
    row["runtime_seconds"] = time.perf_counter() - started
    try:
        return json_ready(row)
    except Exception as error:
        # Unsafe fields are withheld in their entirety, not converted to NaN
        # strings or synthetic zeroes. Keep safe identities and explicit names.
        safe = {"id": scene["id"], "population": scene["population"], "input": scene["input"]}
        withheld = []
        for key, value in row.items():
            try:
                safe[key] = json_ready(value)
            except Exception:
                withheld.append(key)
        record_failure(safe, "row_serialization", error)
        safe["withheld_unsafe_fields"] = withheld
        return safe


def evaluate_criteria(row, plan):
    """Only frozen gates; baseline errors and ratios are descriptive."""
    required = {
        "all_methods_evaluated": all(row["methods"][m]["status"] == "evaluated" for m in METHODS)
    }
    details = {
        "required_checks": required,
        "by_order": {},
        "precision_stability": {},
        "baseline_reproduction": {},
    }
    if not required["all_methods_evaluated"]:
        return details
    with localcontext() as context:
        context.prec = 140
        ref = Decimal(row["reference"]["120"])
        allowance = (
            Decimal("1e-10")
            + 512 * Decimal.from_float(sys.float_info.epsilon) * abs(ref)
            + Decimal.from_float(row["saved_omitted_tail_allowance"])
        )
        details["comparison_allowance"] = decimal_text(allowance)
        refstable = abs(ref - Decimal(row["reference"]["80"])) <= Decimal("1e-65") * max(
            Decimal(1), abs(ref)
        )
        required["reference_precision_stable"] = refstable
        for method in ("exact_source_decimal", "rounded_source_decimal"):
            details["precision_stability"][method] = {}
            for order in plan["rules"]["orders"]:
                low = Decimal(row["methods"][method]["values"]["80"][str(order)])
                high = Decimal(row["methods"][method]["values"]["120"][str(order)])
                delta = abs(high - low)
                stable = delta <= Decimal("1e-65") * max(Decimal(1), abs(high))
                details["precision_stability"][method][str(order)] = {
                    "delta": decimal_text(delta),
                    "passed": stable,
                }
                required[f"{method}/{order}/precision_stable"] = stable
        for order in plan["rules"]["orders"]:
            key = str(order)
            baseline = Decimal.from_float(row["methods"]["baseline"]["values"][key])
            by_order = {}
            for method in METHODS:
                value = (
                    Decimal(row["methods"][method]["values"]["120"][key])
                    if "decimal" in method
                    else Decimal.from_float(row["methods"][method]["values"][key])
                )
                signed = value - ref
                by_order[method] = {
                    "signed_error": decimal_text(signed),
                    "absolute_error": decimal_text(abs(signed)),
                    "absolute_error_over_baseline": None
                    if baseline == ref
                    else decimal_text(abs(signed) / abs(baseline - ref)),
                }
            details["by_order"][key] = by_order
            required[f"exact_source_decimal/{order}/elementary_comparison"] = (
                abs(Decimal(by_order["exact_source_decimal"]["signed_error"])) <= allowance
            )
            required[f"endpoint_binary64/{order}/elementary_comparison"] = (
                abs(Decimal(by_order["endpoint_binary64"]["signed_error"])) <= allowance
            )
            if row["original_v2"] is not None:
                required[f"endpoint_binary64/{order}/original_absolute_tolerance"] = abs(
                    Decimal(by_order["endpoint_binary64"]["signed_error"])
                ) <= Decimal("1e-10")
                original = row["original_v2"]["query"]["oracle"]["values"][key]
                current = row["methods"]["baseline"]["values"][key]
                delta = abs(current - original)
                limit = 8 * sys.float_info.epsilon * max(1.0, abs(original))
                passed = delta <= limit
                details["baseline_reproduction"][key] = {
                    "saved_original": original,
                    "saved_original_hex": original.hex(),
                    "new_baseline": current,
                    "new_baseline_hex": current.hex(),
                    "absolute_delta": delta,
                    "allowance": limit,
                    "tolerance_passed": passed,
                    "exact_hex_equal": current.hex() == original.hex(),
                }
                required[f"baseline/{order}/original_reproduction"] = passed
    return details


def startup_rows(plan, stage, error):
    return [
        {
            "id": s["id"],
            "population": s["population"],
            "input": s["input"],
            "status": "execution_failure",
            "stage": stage,
            "error": error_record(error),
            "protocol_passed": False,
        }
        for s in plan.get("scenes", [])
    ]


def run(plan):
    before = source_snapshot(plan)
    started = time.perf_counter()
    report = {
        "format": "pictures-to-cad-finite-normal-oracle-conditioning-result",
        "version": 1,
        "plan_sha256": sha(PLAN),
        "source_before": before,
        "rows": [],
        "rules": {},
        "constants": {},
        "protocol_passed": False,
        "scope": plan.get("scope"),
        "production_api_calls": 0,
        "optimizer_calls": 0,
        "renderer_calls": 0,
        "original_canonical_replaced": False,
    }
    stage = "source_binding"
    try:
        errors = binding_errors(plan, before)
        report["binding_errors"] = errors
        if errors:
            raise ValueError("frozen source/plan binding differs")
        if len(plan["scenes"]) != 26 or plan["population"] != {
            "post_hoc_scenes": 2,
            "prospective_scenes": 24,
            "queries_per_scene": 1,
            "total_scenes": 26,
        }:
            raise ValueError("frozen diagnostic census differs")
        for scene in plan["scenes"]:
            family(scene)
        stage = "saved_canonical_input"
        decoded = gzip.decompress((ROOT / CANONICAL).read_bytes())
        if sha_bytes(decoded) != plan["canonical_decoded_sha256"]:
            raise ValueError("original canonical decoded hash differs")
        original = strict_json(decoded)
        old_rows = {r["id"]: r for r in original["rows"]}
        report["original_canonical"] = {
            "path": CANONICAL,
            "decoded_sha256": sha_bytes(decoded),
            "decoded_bytes": len(decoded),
            "protocol_passed": original["protocol_passed"],
            "summary": original["summary"],
        }
        stage = "stdlib_v2_context"
        v2 = load_v2_context()
        stage = "numpy_and_rules"
        global NP
        import numpy

        NP = numpy
        report["versions"] = {"python": platform.python_version(), "numpy": NP.__version__}
        if report["versions"] != plan["rules"]["environment"]:
            raise ValueError("declared Python/NumPy rule-generation environment differs")
        v2.NP = NP
        v2.BASE.NP = NP
        rules, report["rules"] = rules_once(NP, v2.BASE, plan["rules"]["orders"])
        stage = "decimal_constants"
        constants = {}
        for precision in plan["precision"]["decimal_contexts"]:
            constants[precision], report["constants"][str(precision)] = machin_pi(precision)
        stage = "scene_evaluation"
        for scene in plan["scenes"]:
            print(
                f"{len(report['rows']) + 1}/26 {scene['id']}: starting",
                file=sys.stderr,
                flush=True,
            )
            row = run_scene(scene, old_rows, plan, v2, rules, constants)
            report["rows"].append(row)
            print(
                f"{len(report['rows'])}/26 {scene['id']}: {row['status']}",
                file=sys.stderr,
                flush=True,
            )
    except Exception as error:
        report["startup_failure"] = {"stage": stage, **error_record(error)}
        completed = {r["id"] for r in report["rows"]}
        report["rows"].extend(
            r for r in startup_rows(plan, stage, error) if r["id"] not in completed
        )
    after = source_snapshot(plan)
    report.update(
        source_after=after,
        source_unchanged=before == after,
        runtime_seconds=time.perf_counter() - started,
    )
    report["summary"] = {
        "planned_scenes": 26,
        "retained_scenes": len(report["rows"]),
        "post_hoc_scenes": sum(r["population"].startswith("post_hoc") for r in report["rows"]),
        "prospective_scenes": sum(
            r["population"].startswith("prospective") for r in report["rows"]
        ),
        "scene_passes": sum(r["protocol_passed"] for r in report["rows"]),
        "all_rows_retained": len(report["rows"]) == 26,
    }
    report["protocol_passed"] = (
        before == after
        and len(report["rows"]) == 26
        and all(r["protocol_passed"] for r in report["rows"])
    )
    return json_ready(report)


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, metavar="NEW_JSON")
    args = parser.parse_args(arguments)
    try:
        output = validate_output(args.output)
        # Reserve destination exclusively before any optional numerical import.
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    with os.fdopen(descriptor, "w") as stream:
        try:
            plan = strict_json(PLAN.read_text())
            result = run(plan)
        except Exception as error:
            result = {
                "format": "pictures-to-cad-finite-normal-oracle-conditioning-result",
                "version": 1,
                "protocol_passed": False,
                "stage": "unreadable_plan_or_report",
                "error": error_record(error),
                "rows": [],
                "scope": "No complete identity census was available; no success claim.",
            }
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
    return 0 if result["protocol_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
