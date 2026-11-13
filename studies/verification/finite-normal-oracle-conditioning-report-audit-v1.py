#!/usr/bin/env python3
"""Audit saved conditioning-report arithmetic; never evaluate nodes or models.

Uses only the standard library. No diagnostic/backend imports, rule generation,
exponential, pi, integral, or scientific-reference reevaluation occurs. A pass
checks saved consistency, not quadrature coefficients or numerical error bounds.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
import os
import sys
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = "studies/finite-normal-oracle-conditioning-v1.json"
PLAN_SHA = "33fd9504167978f1a22522122e7899b0c4bf64ab56905bbf9fa670070a1f8fe2"
DIAGNOSTIC = "studies/verification/finite-normal-oracle-conditioning-v1.py"
DIAGNOSTIC_SHA = "ab69492b6eadaac7a6b76b191b7c7d00b1faf5d74cd43fab02af394ebcca39b1"
V2_PLAN = "studies/finite-normal-error-control-v2.json"
V2_GZIP = "studies/results/finite-normal-error-control-v2.json.gz"
INPUT_SHA = "cd0c2eac7b7062d4cda480c995094293fc9b5991fb55b4c2a86e735aa92bca93"
METHODS = ("baseline", "endpoint_binary64", "exact_source_decimal", "rounded_source_decimal")
ORDERS = (96, 192)
PRECISIONS = (80, 120)


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def strict_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key}")
            result[key] = item
        return result

    def parse_float(token):
        result = float(token)
        if not math.isfinite(result):
            raise ValueError("nonfinite JSON number")
        return result

    def invalid_constant(token):
        raise ValueError(f"nonfinite JSON constant {token}")

    return json.loads(
        value, object_pairs_hook=pairs, parse_float=parse_float, parse_constant=invalid_constant
    )


def decimal(value):
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("nonfinite saved Decimal")
    return result


def fraction_text(value):
    return f"{value.numerator}/{value.denominator}"


def detail_ready(value):
    if isinstance(value, Fraction):
        return fraction_text(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: detail_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [detail_ready(item) for item in value]
    return value


class Audit:
    def __init__(self):
        self.counts = Counter()
        self.failures = []

    def check(self, group, identity, condition, **detail):
        self.counts[group + ":checks"] += 1
        if not condition:
            self.counts[group + ":failed"] += 1
            self.failures.append(detail_ready({"group": group, "identity": identity, **detail}))
        return bool(condition)

    def equal(self, group, identity, actual, expected):
        return self.check(group, identity, actual == expected, actual=actual, expected=expected)

    def guarded(self, group, identity, function):
        try:
            return function()
        except Exception as error:  # noqa: BLE001 -- every failure is retained
            self.check(group, identity, False, error_type=type(error).__name__, error=str(error))
            return None


def source_audit(audit, report, plan, root):
    expected = dict(plan["inputs_sha256"])
    expected[PLAN], expected[DIAGNOSTIC] = PLAN_SHA, None
    transitive = strict_json((root / V2_PLAN).read_bytes())
    for group in ("inputs_sha256", "regression_plans"):
        for name, digest in transitive[group].items():
            if name in expected and expected[name] != digest:
                raise ValueError("conflicting transitive pin")
            expected[name] = digest
    before, after = report["source_before"], report["source_after"]
    audit.equal("source", "nineteen-file-count", len(before), 19)
    audit.equal("source", "complete-set", sorted(before), sorted(expected))
    audit.equal("source", "before-after", before, after)
    audit.equal("source", "unchanged-flag", report["source_unchanged"], before == after)
    for name, pin in expected.items():
        data = (root / name).read_bytes()
        actual = {"sha256": sha_bytes(data), "bytes": len(data), "expected_sha256": pin}
        audit.equal("source", name, before[name], actual)
        if pin is not None:
            audit.equal("source-pin", name, before[name]["sha256"], pin)
    audit.equal("source-pin", "diagnostic", before[DIAGNOSTIC]["sha256"], DIAGNOSTIC_SHA)
    audit.equal("source", "binding-errors", report["binding_errors"], [])


def rule_audit(audit, report, plan):
    audit.equal("rules", "versions", report["versions"], plan["rules"]["environment"])
    audit.equal("rules", "orders", sorted(report["rules"]), ["192", "96"])
    for order in ORDERS:
        record = report["rules"][str(order)]
        payload = {key: record[key] for key in ("nodes_hex", "weights_hex")}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        audit.equal("rules", str(order) + "/hash", record["sha256"], sha_bytes(encoded))
        audit.equal("rules", str(order) + "/order", record["order"], order)
        nodes = [float.fromhex(item) for item in payload["nodes_hex"]]
        weights = [float.fromhex(item) for item in payload["weights_hex"]]
        audit.equal("rules", str(order) + "/node-count", len(nodes), order)
        audit.equal("rules", str(order) + "/weight-count", len(weights), order)
        audit.check(
            "rules",
            str(order) + "/valid-nodes",
            all(finite(x) and -1 < x < 1 for x in nodes)
            and all(a < b for a, b in itertools.pairwise(nodes)),
        )
        audit.check(
            "rules", str(order) + "/positive-weights", all(finite(x) and x > 0 for x in weights)
        )
        audit.equal(
            "rules",
            str(order) + "/canonical-node-hex",
            [v.hex() for v in nodes],
            payload["nodes_hex"],
        )
        audit.equal(
            "rules",
            str(order) + "/canonical-weight-hex",
            [v.hex() for v in weights],
            payload["weights_hex"],
        )
    for precision in PRECISIONS:
        constant = report["constants"][str(precision)]
        audit.equal("constants", str(precision) + "/precision", constant["precision"], precision)
        audit.check("constants", str(precision) + "/finite-pi", decimal(constant["pi"]) > 0)
        # Validate the SAVED finite-series tail from its saved term counts;
        # this is exact rational arithmetic, not pi/atan reevaluation.
        counts = constant["terms"]
        tails = {
            q: Fraction(1, (2 * counts[key] + 1) * q ** (2 * counts[key] + 1))
            for q, key in ((5, "atan_1_5"), (239, "atan_1_239"))
        }
        audit.equal(
            "constants",
            str(precision) + "/tail",
            Fraction(constant["alternating_series_absolute_tail_bound"]),
            16 * tails[5] + 4 * tails[239],
        )
        audit.check(
            "constants",
            str(precision) + "/cutoffs",
            all(v < Fraction(1, 10 ** (precision + 15)) for v in tails.values()),
        )


def family_audit(audit, scene, row):
    identity, supplied = scene["id"], scene["input"]
    for key in ("id", "population", "input", "partition_source"):
        audit.equal("identity", identity + "/" + key, row[key], scene[key])
    h = [[Fraction(v) for v in vector] for vector in supplied["homography"]]
    c, d = h[2][1], h[1][1] - h[2][1] / 2
    audit.check(
        "family",
        identity,
        supplied["centre"] == [0, 0]
        and supplied["radius"] == 1
        and supplied["fraction"] == 0
        and supplied["normal"] == [1, 0]
        and supplied["covariance"] == [[1, 0], [0, 1]]
        and supplied["pixels_xy"] == [[0, 0]]
        and supplied["sensor_shape"] == [3, 3]
        and h[0] == [1, c / 2, Fraction(1, 2)]
        and h[1][0] == 0
        and h[1][2] == Fraction(1, 2)
        and h[2][0] == 0
        and h[2][2] == 1
        and abs(c) < 1
        and d != 0,
    )
    expected = {
        "c": fraction_text(c),
        "d": fraction_text(d),
        "c_float_hex": float(c).hex(),
        "d_float_hex": float(d).hex(),
        "nominal_d": scene.get("nominal_d"),
        "scope": "d from represented H11-H21/2, never nominal_d",
    }
    audit.equal("family", identity + "/parameters", row["represented_parameters"], expected)
    audit.equal(
        "family",
        identity + "/operational-map",
        row["operational_h_hex"],
        [[float(v).hex() for v in vector] for vector in h],
    )


def partition_audit(audit, row, scene, old_rows, layers):
    identity = scene["id"]
    if scene["population"].startswith("post_hoc"):
        old = old_rows[identity]
        query = old["queries"][scene["original_query_index"]]
        partition = query["oracle"]["leaf_panels"]
        original = {
            "row_protocol_passed": old["protocol_passed"],
            "row_status": old["status"],
            "candidate": old["candidate"],
            "query": query,
        }
        audit.equal("old-original", identity + "/input", old["input"], scene["input"])
        audit.equal("old-original", identity + "/full-original", row["original_v2"], original)
    else:
        cuts = sorted(
            {
                -1.0,
                0.0,
                1.0,
                *(-1 + 2.0**-k for k in range(1, layers + 1)),
                *(1 - 2.0**-k for k in range(1, layers + 1)),
            }
        )
        audit.equal("partition", identity + "/fixed-cut-count", len(cuts), 2 * layers + 3)
        partition = [
            {"start": a, "end": b, "method": "direct_source_s"} for a, b in itertools.pairwise(cuts)
        ]
        audit.equal("partition", identity + "/not-old", row["original_v2"], None)
    audit.equal("partition", identity + "/full-partition", row["partition"], partition)
    audit.equal(
        "partition",
        identity + "/hex",
        row["partition_hex"],
        [[float(p["start"]).hex(), float(p["end"]).hex()] for p in partition],
    )
    audit.check(
        "partition",
        identity + "/whole-interval",
        partition[0]["start"] == -1
        and partition[-1]["end"] == 1
        and all(p["start"] < p["end"] for p in partition)
        and all(p["end"] == q["start"] for p, q in itertools.pairwise(partition)),
    )
    tail = math.fsum(
        p["absolute_tail_envelope"] for p in partition if p["method"] == "bounded_tail"
    )
    audit.equal("partition", identity + "/tail", row["saved_omitted_tail_allowance"], tail)
    return partition


def panel_audit(audit, row, partition):
    identity = row["id"]
    audit.equal("panel", identity + "/count", len(row["panels"]), len(partition))
    values = {
        m: {str(o): [] for o in ORDERS}
        if "decimal" not in m
        else {str(p): {str(o): [] for o in ORDERS} for p in PRECISIONS}
        for m in METHODS
    }
    direct = 0
    omitted = 0
    for index, (item, original) in enumerate(zip(row["panels"], partition, strict=True)):
        pid = identity + f"/{index}"
        for key, expected in (
            ("index", index),
            ("start", original["start"]),
            ("end", original["end"]),
            ("original_method", original["method"]),
        ):
            audit.equal("panel", pid + "/" + key, item[key], expected)
        audit.equal("panel", pid + "/methods", sorted(item["methods"]), sorted(METHODS))
        if original["method"] == "bounded_tail":
            omitted += 1
            audit.equal(
                "panel",
                pid + "/tail",
                item["preserved_tail_allowance"],
                original["absolute_tail_envelope"],
            )
            for method in METHODS:
                audit.equal(
                    "panel",
                    pid + "/" + method,
                    item["methods"][method],
                    {"status": "preserved_omission", "no_new_nodes": True},
                )
            continue
        direct += 1
        audit.equal("panel", pid + "/direct-method", original["method"], "direct_source_s")
        a, b = original["start"], original["end"]
        audit.equal(
            "panel",
            pid + "/exact-width",
            item["exact_half_width"],
            fraction_text((Fraction(b) - Fraction(a)) / 2),
        )
        audit.equal(
            "panel", pid + "/float-width", item["float_half_width_hex"], ((b - a) / 2).hex()
        )
        for method in METHODS:
            record = item["methods"][method]
            audit.equal("panel", pid + "/" + method + "/status", record["status"], "evaluated")
            audit.equal(
                "panel", pid + "/" + method + "/orders", sorted(record["by_order"]), ["192", "96"]
            )
            for order in ORDERS:
                key = str(order)
                saved = record["by_order"][key]
                if "decimal" not in method:
                    audit.check(
                        "panel-values",
                        pid + "/" + method + "/" + key,
                        finite(saved["value"])
                        and finite(saved["original_style_error_estimate"])
                        and saved["original_style_error_estimate"] >= 0,
                    )
                    audit.equal(
                        "panel-values",
                        pid + "/" + method + "/hex-" + key,
                        saved["value_hex"],
                        saved["value"].hex(),
                    )
                    values[method][key].append(saved["value"])
                else:
                    audit.equal(
                        "panel-values",
                        pid + "/" + method + "/precisions-" + key,
                        sorted(saved),
                        ["120", "80"],
                    )
                    for precision in PRECISIONS:
                        value = decimal(saved[str(precision)])
                        values[method][str(precision)][key].append(value)
    for method in METHODS:
        work = {
            "attempted_rule_batches": direct * 2,
            "completed_rule_batches": direct * 2,
            "attempted_density_nodes": direct * sum(ORDERS),
            "completed_density_nodes": direct * sum(ORDERS),
            "exact_endpoint_evaluations": direct * 4 if method == "endpoint_binary64" else 0,
            "preserved_omitted_panels": omitted,
        }
        if "decimal" in method:
            for name in (
                "attempted_rule_batches",
                "completed_rule_batches",
                "attempted_density_nodes",
                "completed_density_nodes",
            ):
                work[name] *= 2
        audit.equal("work", identity + "/" + method, row["methods"][method]["work"], work)
        audit.equal(
            "totals",
            identity + "/" + method + "/status",
            row["methods"][method]["status"],
            "evaluated",
        )
        if "decimal" not in method:
            expected = {str(o): math.fsum(values[method][str(o)]) for o in ORDERS}
            audit.equal(
                "totals", identity + "/" + method, row["methods"][method]["values"], expected
            )
        else:
            for precision in PRECISIONS:
                with localcontext() as context:
                    context.prec = precision
                    expected = {
                        str(o): str(sum(values[method][str(precision)][str(o)], Decimal(0)))
                        for o in ORDERS
                    }
                audit.equal(
                    "totals",
                    identity + "/" + method + "/" + str(precision),
                    row["methods"][method]["values"][str(precision)],
                    expected,
                )
    return {"direct_panels": direct, "omitted_panels": omitted}


def criteria_audit(audit, row):
    """Rebuild the frozen Boolean gates from saved values, no reference eval."""
    identity = row["id"]
    required = {
        "all_methods_evaluated": all(row["methods"][m]["status"] == "evaluated" for m in METHODS)
    }
    expected = {
        "required_checks": required,
        "by_order": {},
        "precision_stability": {},
        "baseline_reproduction": {},
    }
    if not required["all_methods_evaluated"]:
        audit.equal("criteria", identity + "/incomplete", row["criteria"], expected)
        return expected
    with localcontext() as context:
        context.prec = 140
        ref = decimal(row["reference"]["120"])
        allowance = (
            Decimal("1e-10")
            + 512 * Decimal.from_float(sys.float_info.epsilon) * abs(ref)
            + Decimal.from_float(row["saved_omitted_tail_allowance"])
        )
        expected["comparison_allowance"] = str(allowance)
        required["reference_precision_stable"] = abs(
            ref - decimal(row["reference"]["80"])
        ) <= Decimal("1e-65") * max(Decimal(1), abs(ref))
        for method in ("exact_source_decimal", "rounded_source_decimal"):
            expected["precision_stability"][method] = {}
            for order in ORDERS:
                low = decimal(row["methods"][method]["values"]["80"][str(order)])
                high = decimal(row["methods"][method]["values"]["120"][str(order)])
                delta = abs(high - low)
                stable = delta <= Decimal("1e-65") * max(Decimal(1), abs(high))
                expected["precision_stability"][method][str(order)] = {
                    "delta": str(delta),
                    "passed": stable,
                }
                required[f"{method}/{order}/precision_stable"] = stable
        for order in ORDERS:
            key = str(order)
            baseline = Decimal.from_float(row["methods"]["baseline"]["values"][key])
            results = {}
            for method in METHODS:
                value = (
                    decimal(row["methods"][method]["values"]["120"][key])
                    if "decimal" in method
                    else Decimal.from_float(row["methods"][method]["values"][key])
                )
                signed = value - ref
                results[method] = {
                    "signed_error": str(signed),
                    "absolute_error": str(abs(signed)),
                    "absolute_error_over_baseline": None
                    if baseline == ref
                    else str(abs(signed) / abs(baseline - ref)),
                }
            expected["by_order"][key] = results
            for method in ("exact_source_decimal", "endpoint_binary64"):
                required[f"{method}/{order}/elementary_comparison"] = (
                    abs(decimal(results[method]["signed_error"])) <= allowance
                )
            if row["original_v2"] is not None:
                required[f"endpoint_binary64/{order}/original_absolute_tolerance"] = abs(
                    decimal(results["endpoint_binary64"]["signed_error"])
                ) <= Decimal("1e-10")
                original = row["original_v2"]["query"]["oracle"]["values"][key]
                current = row["methods"]["baseline"]["values"][key]
                delta = abs(current - original)
                limit = 8 * sys.float_info.epsilon * max(1.0, abs(original))
                passed = delta <= limit
                expected["baseline_reproduction"][key] = {
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
    # Compare individual saved items as well as the entire record so the audit
    # count and failure identities expose which gate differs.
    for key, value in required.items():
        audit.equal(
            "criteria-gate",
            identity + "/" + key,
            row["criteria"]["required_checks"].get(key),
            value,
        )
    audit.equal("criteria", identity + "/all-fields", row["criteria"], expected)
    audit.equal("criteria", identity + "/protocol", row["protocol_passed"], all(required.values()))
    audit.equal(
        "criteria",
        identity + "/status",
        row["status"],
        "passed" if all(required.values()) else "protocol_failure",
    )
    return expected


def scientific_summary(rows):
    result = {}
    with localcontext() as context:
        context.prec = 140
        for population in ("all", "post_hoc", "prospective"):
            selected = (
                rows
                if population == "all"
                else [r for r in rows if r["population"].startswith(population)]
            )
            result[population] = {
                "scenes": len(selected),
                "max_absolute_error_by_method_order": {},
                "old_absolute_passes": 0,
            }
            for method in METHODS:
                result[population]["max_absolute_error_by_method_order"][method] = {
                    str(order): str(
                        max(
                            decimal(r["criteria"]["by_order"][str(order)][method]["absolute_error"])
                            for r in selected
                        )
                    )
                    for order in ORDERS
                }
            if population in ("all", "post_hoc"):
                result[population]["old_absolute_passes"] = sum(
                    r["criteria"]["required_checks"].get(
                        f"endpoint_binary64/{order}/original_absolute_tolerance", False
                    )
                    for r in selected
                    for order in ORDERS
                )
    return result


def audit_report(audit, report, plan, original, root):
    audit.equal(
        "report",
        "format",
        report["format"],
        "pictures-to-cad-finite-normal-oracle-conditioning-result",
    )
    audit.equal("report", "version", report["version"], 1)
    audit.equal("report", "plan-pin", report["plan_sha256"], PLAN_SHA)
    source_audit(audit, report, plan, root)
    rule_audit(audit, report, plan)
    audit.equal("census", "rows", len(report["rows"]), 26)
    audit.equal(
        "original-v2",
        "metadata",
        report["original_canonical"],
        {
            "path": V2_GZIP,
            "decoded_sha256": plan["canonical_decoded_sha256"],
            "decoded_bytes": len(original["decoded"]),
            "protocol_passed": original["report"]["protocol_passed"],
            "summary": original["report"]["summary"],
        },
    )
    old_rows = {r["id"]: r for r in original["report"]["rows"]}
    panel_counts = {}
    for row, scene in zip(report["rows"], plan["scenes"], strict=True):
        identity = scene["id"]
        audit.guarded(
            "family", identity, lambda row=row, scene=scene: family_audit(audit, scene, row)
        )
        partition = audit.guarded(
            "partition",
            identity,
            lambda row=row, scene=scene: partition_audit(
                audit, row, scene, old_rows, plan["partition"]["prospective_endpoint_layers"]
            ),
        )
        if partition is not None:
            panel_counts[identity] = audit.guarded(
                "panel",
                identity,
                lambda row=row, partition=partition: panel_audit(audit, row, partition),
            )
        audit.guarded("criteria", identity, lambda row=row: criteria_audit(audit, row))
    summary = {
        "planned_scenes": 26,
        "retained_scenes": len(report["rows"]),
        "post_hoc_scenes": sum(r["population"].startswith("post_hoc") for r in report["rows"]),
        "prospective_scenes": sum(
            r["population"].startswith("prospective") for r in report["rows"]
        ),
        "scene_passes": sum(r["protocol_passed"] for r in report["rows"]),
        "all_rows_retained": len(report["rows"]) == 26,
    }
    audit.equal("summary", "all-fields", report["summary"], summary)
    audit.equal(
        "summary",
        "protocol",
        report["protocol_passed"],
        report["source_before"] == report["source_after"]
        and len(report["rows"]) == 26
        and all(r["protocol_passed"] for r in report["rows"]),
    )
    for key, expected in (
        ("production_api_calls", 0),
        ("optimizer_calls", 0),
        ("renderer_calls", 0),
        ("original_canonical_replaced", False),
    ):
        audit.equal("scope", key, report[key], expected)
    return {
        "recomputed_summary": summary,
        "panel_counts": panel_counts,
        "scientific_aggregates": scientific_summary(report["rows"]),
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True, metavar="NEW_JSON")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(arguments)
    if os.path.lexists(args.output) or not args.output.parent.is_dir():
        parser.error("output must be fresh (including no symlink) in an existing directory")
    if args.input_sha256 != INPUT_SHA:
        parser.error("input-sha256 must match this auditor's pinned canonical report")
    try:
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as error:
        parser.error(str(error))
    audit = Audit()
    details = None
    observed = None
    with os.fdopen(descriptor, "w") as stream:
        try:
            root = args.root.resolve()
            data = args.input.read_bytes()
            observed = sha_bytes(data)
            audit.equal("input", "external-pin", observed, args.input_sha256)
            if observed != args.input_sha256:
                raise ValueError("input hash differs; no saved calculations audited")
            report = strict_json(data)
            plan = strict_json((root / PLAN).read_bytes())
            audit.equal("input", "plan-pin", sha(root / PLAN), PLAN_SHA)
            decoded = gzip.decompress((root / V2_GZIP).read_bytes())
            audit.equal(
                "input",
                "original-v2-decoded-pin",
                sha_bytes(decoded),
                plan["canonical_decoded_sha256"],
            )
            if sha_bytes(decoded) != plan["canonical_decoded_sha256"]:
                raise ValueError("original V2 decoded hash differs")
            original = {"decoded": decoded, "report": strict_json(decoded)}
            details = audit_report(audit, report, plan, original, root)
            audit.equal("input", "unchanged-after-audit", sha(args.input), observed)
        except Exception as error:  # noqa: BLE001 -- bootstrap failures produce an explicit failed audit
            audit.check(
                "startup-or-audit",
                "execution",
                False,
                error_type=type(error).__name__,
                error=str(error),
            )
        result = {
            "format": "pictures-to-cad-finite-normal-oracle-conditioning-saved-audit",
            "version": 1,
            "auditor_sha256": sha(Path(__file__)),
            "input_sha256": observed,
            "passed": not audit.failures,
            "checks": sum(v for k, v in audit.counts.items() if k.endswith(":checks")),
            "counts": dict(sorted(audit.counts.items())),
            "failures": audit.failures,
            "details": details,
            "actual_model_calls": 0,
            "actual_node_evaluations": 0,
            "actual_reference_evaluations": 0,
            "scope": "Saved-data arithmetic/provenance consistency only. No NumPy/backend/diagnostic import or rule/exponential/pi/model/reference reevaluation. It does not certify nodes, weights, quadrature truncation, arithmetic allowances, or physical accuracy.",
        }
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": result["checks"],
                "failures": len(result["failures"]),
                "output": str(args.output),
            },
            allow_nan=False,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
