"""Independent saved-JSON arithmetic/binding audit; no backend imports or replay."""

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--report", type=Path, required=True, help="decoded original canonical JSON")
parser.add_argument(
    "--output", type=Path, required=True, help="fresh audit JSON in an existing directory"
)
args = parser.parse_args()
RUN, OUT = args.report.resolve(), args.output.absolute()
if os.path.lexists(OUT) or not OUT.parent.is_dir():
    parser.error("output must be fresh and its parent must exist")
EXPECTED_RUN = "d31fcb0436daee9e91bd21d78c1650901916a8c2c77bf6c7e351da61c04e113f"
failures = []
checks = 0


def require(condition, detail):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(detail)


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def load(path):
    return json.loads(
        path.read_text(),
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def same(left, right):
    return (
        finite(left) and finite(right) and math.isclose(left, right, rel_tol=4e-15, abs_tol=2e-300)
    )


def integer(value):
    return type(value) is int and value >= 0


def record(name, callback):
    try:
        callback()
    except (AssertionError, ArithmeticError, KeyError, TypeError, ValueError, IndexError) as error:
        failures.append({"scope": name, "type": type(error).__name__, "message": str(error)})


require(sha(RUN) == EXPECTED_RUN, "canonical byte hash")
data = load(RUN)
plan = load(ROOT / "studies/finite-normal-derivative-v1.json")
extra = load(ROOT / "studies/finite-normal-derivative-compressed-chart-v1.json")
scenes = plan["scenes"] + extra["scenes"]
settings = plan["operator"]
oracle_settings = plan["oracle"]
guards = extra["algorithm_resolution_guards"]
require(len(data["rows"]) == len(scenes) == 337, "complete337-scene census")
require(sum(len(s["pixels_xy"]) for s in scenes) == 3886, "declared3886 query census")
require(data["source_before"] == data["source_after"], "before/after source binding")
require(data["source_unchanged"] is True and data["source_after_failure"] is None, "source flags")
require(data["setup_failures"] == {}, "no setup failures")
for name, entry in data["source_before"].items():
    path = ROOT / name
    require(entry["sha256"] == sha(path), f"current source hash:{name}")
    require(entry["bytes"] == path.stat().st_size, f"current source bytes:{name}")
require(data["plan_sha256"] == sha(ROOT / "studies/finite-normal-derivative-v1.json"), "plan pin")
require(
    data["supplement_sha256"]
    == sha(ROOT / "studies/finite-normal-derivative-compressed-chart-v1.json"),
    "supplement pin",
)
require(data["api_file_sha256"] == sha(ROOT / "backend/finite_normal.py"), "API pin")
require(
    data["runner_sha256"] == sha(ROOT / "studies/verification/finite-normal-derivative-v1.py"),
    "runner pin",
)
require(
    data["helper_sha256"] == sha(ROOT / plan["positive_area_corroboration"]["helper"]),
    "area helper pin",
)
require(
    data["settings"]
    == {
        "operator": settings,
        "oracle": oracle_settings,
        "algorithm_resolution_guards": guards,
        "positive_area_corroboration": plan["positive_area_corroboration"],
    },
    "frozen settings",
)
for name, expected in plan["inputs_sha256"].items():
    require(sha(ROOT / name) == expected, f"original source input pin:{name}")

status_counts, method_counts = Counter(), Counter()
oracle_counts = Counter()
candidate_totals = Counter()
unknowns = []
query_count = query_passes = scene_passes = converged = 0
max_resolved_error = max_resolved_delta = max_delta_ratio = 0.0


def audit_row(row, scene, index):
    global query_count, query_passes, scene_passes, converged
    global max_resolved_error, max_resolved_delta, max_delta_ratio
    require(
        row["index"] == index and row["id"] == scene["id"] and row["input"] == scene,
        "frozen row identity/input",
    )
    candidate = row["candidate"]
    require(
        set(candidate)
        == {
            "derivatives",
            "statuses",
            "estimated_errors",
            "evaluations",
            "panels",
            "query_methods",
            "query_evaluations",
            "query_panels",
            "chart_margin",
            "reflected",
            "method",
            "quadrature_certified",
        },
        "candidate exact dataclass schema",
    )
    n = len(scene["pixels_xy"])
    require(len(row["queries"]) == n, "all query identities retained")
    for name in (
        "derivatives",
        "statuses",
        "estimated_errors",
        "query_methods",
        "query_evaluations",
        "query_panels",
    ):
        require(len(candidate[name]) == n, f"candidate aligned field:{name}")
    require(
        candidate["method"] == "finite_chord_shape" and candidate["quadrature_certified"] is False,
        "method/certification semantics",
    )
    require(
        type(candidate["reflected"]) is bool
        and finite(candidate["chart_margin"])
        and 0 < candidate["chart_margin"] <= 1,
        "frame metadata",
    )
    for name in ("evaluations", "panels"):
        require(integer(candidate[name]), f"nonnegative integer{name}")
    require(
        sum(candidate["query_evaluations"])
        == candidate["evaluations"]
        <= settings["max_evaluations"],
        "cumulative evaluation budget/sum",
    )
    require(sum(candidate["query_panels"]) == candidate["panels"], "panel sum")
    candidate_totals.update(evaluations=candidate["evaluations"], panels=candidate["panels"])
    prefix = (
        "affine" if scene["homography"][2][0] == scene["homography"][2][1] == 0 else "projective"
    )
    for j, query in enumerate(row["queries"]):
        query_count += 1
        require(
            query["query_index"] == j and query["pixel"] == scene["pixels_xy"][j],
            "same fixed query order",
        )
        require(
            query["roles"] == [r["role"] for r in scene["query_roles"] if r["query_index"] == j],
            "all query roles",
        )
        status, value, error = (
            candidate["statuses"][j],
            candidate["derivatives"][j],
            candidate["estimated_errors"][j],
        )
        method, work, panels = (
            candidate["query_methods"][j],
            candidate["query_evaluations"][j],
            candidate["query_panels"][j],
        )
        require(
            query["candidate"]
            == {"status": status, "value": value, "estimated_error": error, "method": method},
            "nested candidate copy",
        )
        require(
            integer(work) and integer(panels) and panels <= settings["max_panels"],
            "per-query counters",
        )
        require(status in {"resolved", "numerical", "work_limit"}, "declared status")
        require(
            method
            in {
                "not_attempted",
                f"{prefix}_closed_form",
                f"{prefix}_closed_form_then_chord_quadrature",
            },
            "original-map classification",
        )
        status_counts[status] += 1
        method_counts[method] += 1
        if method == "not_attempted":
            require(work == panels == 0 and status == "work_limit", "unattempted work semantics")
        elif method.endswith("_then_chord_quadrature"):
            require(panels >= 1 and work >= 2 * panels, "charged analytic/fallback endpoints")
            require(
                (work - 2 * panels) % 36 == 0 and work <= 2 + 38 * (panels - 1),
                "canonical paired-rule charges",
            )
        else:
            require(work == 2 and panels == 1 and status == "resolved", "closed attempt charges")
        if status == "resolved":
            require(
                finite(value) and finite(error) and 0 <= error <= settings["probability_tolerance"],
                "finite signed derivative/error",
            )
            max_resolved_error = max(max_resolved_error, error)
        else:
            require(
                value is None and error is None and query["comparison_passed"] is False,
                "unknown has no fabricated value/error/pass",
            )
            unknowns.append(
                {
                    "scene": row["id"],
                    "query": j,
                    "pixel": query["pixel"],
                    "status": status,
                    "evaluations": work,
                    "panels": panels,
                }
            )

        oracle = query["oracle"]
        require(oracle["orders"] == oracle_settings["orders"] == [96, 192], "frozen oracle orders")
        require(
            oracle["status"] == "resolved" and oracle["oracle_converged"] is True,
            "oracle convergence retained",
        )
        converged += 1
        leafs = oracle["leaf_panels"]
        require(leafs and all(x["start"] < x["end"] for x in leafs), "positive leaf intervals")
        require(
            leafs[0]["start"] == oracle["initial_source_cuts"][0]
            and leafs[-1]["end"] == oracle["initial_source_cuts"][-1],
            "whole chord endpoints retained",
        )
        require(
            all(a["end"] == b["start"] for a, b in pairwise(leafs)),
            "closed partition no gaps/overlap",
        )
        require(
            oracle["initial_panel_count"] == len(oracle["initial_source_cuts"]) - 1,
            "initial partition count",
        )
        require(
            oracle["panels_inspected"] + oracle["initial_panel_count"] == 2 * len(leafs),
            "binary split tree census",
        )
        require(
            oracle["endpoint_evaluations"] == 2 + 2 * oracle["panels_inspected"],
            "all oracle endpoint charges",
        )
        direct = [x for x in leafs if x["method"] == "direct_source_s"]
        tails = [x for x in leafs if x["method"] == "bounded_tail"]
        require(len(direct) + len(tails) == len(leafs), "explicit leaf methods")
        for leaf in direct:
            require(
                leaf["whitened_travel"] <= guards["maximum_whitened_panel_travel"]
                and leaf["gaussian_exponent_variation"]
                <= guards["maximum_gaussian_exponent_variation"]
                and leaf["denominator_ratio"] <= guards["maximum_denominator_ratio"],
                "oracle non-tail guard compliance",
            )
        for order in (96, 192):
            require(
                oracle["rule_evaluations"][str(order)] == order * len(direct),
                "all oracle rule charges",
            )
            require(
                same(
                    oracle["values"][str(order)], math.fsum(x["values"][str(order)] for x in direct)
                ),
                "oracle saved integral sum",
            )
            require(
                same(
                    oracle["roundoff_estimates"][str(order)],
                    math.fsum(x["roundoff_estimates"][str(order)] for x in direct),
                ),
                "oracle saved roundoff sum",
            )
        require(
            oracle["evaluations"]
            == oracle["endpoint_evaluations"] + sum(oracle["rule_evaluations"].values())
            <= oracle_settings["maximum_evaluations_per_query"],
            "oracle total work",
        )
        require(
            oracle["panels_inspected"] <= oracle_settings["maximum_panels"], "oracle panel limit"
        )
        require(
            same(
                oracle["tail_envelope_sum"], math.fsum(x["absolute_tail_envelope"] for x in tails)
            ),
            "oracle saved tail sum",
        )
        require(0 <= oracle["tail_envelope_sum"] <= 1e-13, "oracle aggregate tail envelope")
        for leaf in tails:
            require(
                0 < leaf["absolute_tail_envelope"] <= oracle["per_panel_tail_threshold"],
                "oracle per-leaf tail allowance",
            )
        lo, hi = oracle["values"]["96"], oracle["values"]["192"]
        require(same(oracle["order_delta"], abs(hi - lo)), "oracle order discrepancy")
        require(
            same(
                oracle["order_allowance"],
                oracle_settings["order_agreement_abs"]
                + oracle_settings["order_agreement_rel"] * abs(hi),
            )
            and oracle["order_delta"] <= oracle["order_allowance"],
            "frozen oracle convergence allowance",
        )
        oracle_counts.update(
            evaluations=oracle["evaluations"],
            panels=oracle["panels_inspected"],
            leaves=len(leafs),
            direct=len(direct),
            tails=len(tails),
        )
        if status == "resolved":
            allowance = math.fsum(
                (
                    oracle_settings["comparison_abs"],
                    oracle_settings["comparison_rel"] * abs(hi),
                    error,
                    2 * oracle["order_delta"],
                    oracle["tail_envelope_sum"],
                )
            )
            delta = abs(value - hi)
            require(
                same(query["comparison_delta"], delta)
                and same(query["comparison_allowance"], allowance),
                "frozen comparison arithmetic",
            )
            require(query["comparison_passed"] == (delta <= allowance), "honest comparison flag")
            max_resolved_delta = max(max_resolved_delta, delta)
            max_delta_ratio = max(max_delta_ratio, delta / allowance)
        query_passes += query["comparison_passed"]
    passed = all(q["comparison_passed"] for q in row["queries"])
    require(
        row["protocol_passed"] == passed
        and row["status"] == ("passed" if passed else "protocol_failure"),
        "honest row status",
    )
    scene_passes += passed


for i, (row, scene) in enumerate(zip(data["rows"], scenes, strict=True)):
    record(scene["id"], lambda row=row, scene=scene, i=i: audit_row(row, scene, i))

area_passes = 0
by_id = {r["id"]: r for r in data["rows"]}


def audit_area(row, selection):
    global area_passes
    config = plan["positive_area_corroboration"]
    require(
        row["scene_id"] == selection["scene_id"]
        and row["query_indices"] == selection["query_indices"],
        "area declared identity",
    )
    require(len(row["queries"]) == len(selection["query_indices"]), "area all identities retained")
    original = by_id[row["scene_id"]]
    h = config["h_radians"]
    for i, q in enumerate(row["queries"]):
        j = selection["query_indices"][i]
        require(
            q["query_index"] == j and q["pixel"] == original["input"]["pixels_xy"][j],
            "area fixed query",
        )
        require(
            row["observation_centres"][i] == [v + 0.5 for v in q["pixel"]],
            "area geometric pixel centres",
        )
        differences = {}
        values = {}
        for order in (96, 192):
            values[order] = {
                name: row["means"][str(order)][name]["probabilities"][i]
                for name in ("plus_h", "minus_h", "plus_half", "minus_half")
            }
            v = values[order]
            differences[str(order)] = {
                "h": (v["plus_h"] - v["minus_h"]) / (2 * h),
                "half": (v["plus_half"] - v["minus_half"]) / h,
            }
        require(q["finite_differences"] == differences, "area saved differences recompute")
        low, high = differences["96"], differences["192"]
        order_delta = max(abs(high[k] - low[k]) for k in ("h", "half"))
        propagated = {
            "h": (
                abs(values[192]["plus_h"] - values[96]["plus_h"])
                + abs(values[192]["minus_h"] - values[96]["minus_h"])
            )
            / (2 * h),
            "half": (
                abs(values[192]["plus_half"] - values[96]["plus_half"])
                + abs(values[192]["minus_half"] - values[96]["minus_half"])
            )
            / h,
        }
        guard = max(order_delta, *propagated.values())
        half_delta = abs(high["half"] - high["h"])
        richardson = (4 * high["half"] - high["h"]) / 3
        value = original["candidate"]["derivatives"][j]
        delta = abs(value - richardson)
        allowance = config["candidate_richardson_abs"] + config["candidate_richardson_rel"] * abs(
            richardson
        )
        require(
            same(q["derivative_order_delta"], order_delta)
            and same(q["derivative_order_guard_value"], guard)
            and q["propagated_area_order_discrepancy"] == propagated,
            "area order/error arithmetic",
        )
        require(
            same(q["h_half_delta"], half_delta) and same(q["richardson"], richardson),
            "area step/Richardson arithmetic",
        )
        require(
            q["candidate"] == value
            and same(q["candidate_delta"], delta)
            and same(q["candidate_allowance"], allowance),
            "area candidate comparison arithmetic",
        )
        passed = (
            guard <= config["derivative_order_agreement_abs"]
            and half_delta <= config["step_half_agreement_abs"]
            and original["candidate"]["statuses"][j] == "resolved"
            and delta <= allowance
        )
        require(q["protocol_passed"] == passed, "honest area flag")
        area_passes += passed
    require(
        row["protocol_passed"] == all(q["protocol_passed"] for q in row["queries"]),
        "honest area row flag",
    )


require(
    len(data["positive_area"]) == len(plan["positive_area_corroboration"]["selection"]) == 12,
    "complete area scene count",
)
for row, selection in zip(
    data["positive_area"], plan["positive_area_corroboration"]["selection"], strict=True
):
    record(
        f"area:{selection['scene_id']}",
        lambda row=row, selection=selection: audit_area(row, selection),
    )

expected_summary = {
    **data["summary"],
    "retained_scenes": len(data["rows"]),
    "retained_queries": query_count,
    "scene_passes": scene_passes,
    "query_passes": query_passes,
    "oracle_converged_queries": converged,
    "positive_area_passes": area_passes,
}
require(data["summary"] == expected_summary, "recomputed summary counts")
require(
    query_count == 3886
    and query_passes == 3885
    and converged == 3886
    and scene_passes == 336
    and area_passes == 36,
    "reported terminal counts",
)
require(
    data["protocol_passed"] is False and len(unknowns) == 1, "retained failure not relabeled pass"
)
require(
    all(
        data["summary"][key] == 0
        for key in ("optimizer_calls", "renderer_calls", "old_archived_data_analyses")
    ),
    "declared no optimizer/render/archive scope",
)
require(sha(RUN) == EXPECTED_RUN, "canonical bytes unchanged after audit")
result = {
    "format": "pictures-to-cad-finite-normal-saved-json-audit",
    "version": 1,
    "auditor_sha256": sha(Path(__file__)),
    "canonical_path": str(RUN.relative_to(ROOT)) if RUN.is_relative_to(ROOT) else RUN.name,
    "canonical_sha256": EXPECTED_RUN,
    "canonical_bytes": RUN.stat().st_size,
    "source_sha256": {name: entry["sha256"] for name, entry in data["source_before"].items()},
    "checks": checks,
    "audit_passed": not failures,
    "audit_failures": failures,
    "canonical_protocol_passed": False,
    "counts": {
        "scenes": len(data["rows"]),
        "queries": query_count,
        "scene_passes": scene_passes,
        "query_passes": query_passes,
        "oracle_converged_queries": converged,
        "positive_area_passes": area_passes,
    },
    "candidate_statuses": dict(status_counts),
    "candidate_methods": dict(method_counts),
    "candidate_work": dict(candidate_totals),
    "oracle_work": dict(oracle_counts),
    "retained_unknowns": unknowns,
    "max_resolved_error_estimate": max_resolved_error,
    "max_resolved_comparison_delta": max_resolved_delta,
    "max_resolved_delta_over_frozen_allowance": max_delta_ratio,
    "model_calls": 0,
    "operator_imports": 0,
    "scope": "Saved JSON/hash/arithmetic only. Does not rerun or independently validate density nodes or certify numerical error estimates. Canonical protocol remains failed.",
}
with OUT.open("x") as stream:
    json.dump(result, stream, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps(result, sort_keys=True, allow_nan=False))
raise SystemExit(0 if not failures else 1)
