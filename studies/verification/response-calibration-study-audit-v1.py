"""Replay exact witness/proof checks for the complete response-calibration study.

Use --run RESULT_JSON (default: the canonical bundled result) --output NEW_JSON.
The audit independently reconstructs all declared constraints from the result and
plan, verifies compatible witnesses and incompatible source-indexed inequalities,
and retains every checked outcome. It does not call the production calibrator or
rerun a photo pipeline. Exact checks concern frozen rational inputs, not certified
Gaussian probabilities, continuous offset enclosures or physical calibration.
"""

import argparse
import hashlib
import json
import math
import platform
import time
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "studies/response-calibration-v1.json"
DEFAULT_RUN = ROOT / "studies/results/response-calibration-v1.json"
SOURCES = (
    "backend/response_calibration.py",
    "backend/raw_source_fit.py",
    "backend/profile_observations.py",
    "backend/sheet.py",
    "backend/tone.py",
    "scripts/response_calibration.py",
    "scripts/response_calibration_study.py",
    "studies/response-calibration-v1.json",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(path):
    def nonfinite(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(), parse_constant=nonfinite, object_pairs_hook=unique_object)


def label(path):
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def source_hashes(run_path):
    paths = [Path(__file__), run_path, *[ROOT / p for p in SOURCES]]
    return {label(path): digest(path) for path in paths}


def cdf(value):
    # Reproduce the DECLARED rounded source inputs, not an exact optical integral.
    return F.from_float(math.erfc(-float(value) / math.sqrt(2)) / 2)


def response(x):
    # Independent exact polynomial form of x + (3/20)x(1-x).
    return (23 * x - 3 * x * x) / 20


class Audit:
    def __init__(self):
        self.checks = []

    def check(self, name, kind, callback, *args):
        record = {"case": name, "kind": kind}
        try:
            details = callback(*args)
            if details is not None:
                record["details"] = details
            record["verification"] = "passed"
        except Exception as error:  # noqa: BLE001 - retain failures and audit subsequent rows.
            record["verification"] = "failed"
            record["failure"] = {"type": type(error).__name__, "message": str(error)}
        self.checks.append(record)
        return record


def equal(actual, expected, message):
    require(actual == expected, message)


def validate_result(result, nodes, slopes):
    lower, upper = slopes
    require(result["status"] in ("compatible", "incompatible"), "unknown mathematical status")
    if result["status"] == "compatible":
        require(result["contradiction"] is None, "compatible result has a contradiction")
        witness = [(F(p["input"]), F(p["output"])) for p in result["witness"]]
        values = dict(witness)
        require(len(values) == len(witness), "duplicate witness input")
        require(
            [x for x, _ in witness] == sorted({x for x, _, _ in nodes}),
            "missing or unordered witness input",
        )
        for x, lo, hi in nodes:
            require(lo <= values[x] <= hi, "witness violates an original output interval")
        for index, (x, a) in enumerate(witness):
            for y, b in witness[index + 1 :]:
                require(lower * (y - x) <= b - a, "witness violates common lower slope")
                require(
                    upper is None or b - a <= upper * (y - x), "witness violates common upper slope"
                )
    else:
        require(not result["witness"], "incompatible result has a witness")
        proof = result["contradiction"]
        i, j = proof["lower_source"], proof["upper_source"]
        require(
            type(i) is int and type(j) is int and 0 <= i < len(nodes) and 0 <= j < len(nodes),
            "proof index is outside original observations",
        )
        at = F(proof["at_input"])
        xi, low, _ = nodes[i]
        xj, _, high = nodes[j]
        require(xi <= at and xj <= at, "proof transports an original bound backwards")
        implied_low = low + lower * (at - xi)
        if upper is None:
            require(xj == at, "an omitted upper slope cannot transport an upper bound")
            implied_high = high
        else:
            implied_high = high + upper * (at - xj)
        require(
            (implied_low, implied_high) == (F(proof["implied_lower"]), F(proof["implied_upper"])),
            "proof is not implied by its indexed original bounds",
        )
        require(implied_low > implied_high, "contradiction is not strict")
        if proof["kind"] == "duplicate_input":
            require(xi == xj == at, "duplicate proof refers to different inputs")
        else:
            require(proof["kind"] == "slope_bounds", "unknown proof kind")
    return {"status": result["status"]}


def candidate_check(row, index, offset, nodes, slopes):
    require(
        type(row["candidate_index"]) is int
        and row["candidate_index"] == index
        and F(row["offset_sigma"]) == offset,
        "missing, duplicated or misidentified candidate",
    )
    return validate_result(row, nodes, slopes)


def reconstruct_comparison(plan, comparison, truth):
    regimes = {regime["name"]: regime for regime in plan["calibration_regimes"]}
    regime = regimes[comparison["regime"]]
    error = F(comparison["observation_halfwidth"])
    require(error in {F(v) for v in plan["observation_halfwidths"]}, "undeclared observation band")
    require(regime["response"] in ("quadratic", "identity"), "unknown response regime")
    require(regime["patches"] in ("endpoints", "all"), "unknown patch regime")
    inputs = (
        [F(0), F(1)]
        if regime["patches"] == "endpoints"
        else [F(v) for v in plan["calibration_inputs"]]
    )
    patches = []
    for x in inputs:
        mean = response(x) if regime["response"] == "quadratic" else x
        bound = F(0) if x in (0, 1) else F(regime["patch_halfwidth"])
        patches.append((x, mean - bound, mean + bound))
    slopes = (
        F(regime["slope_bounds"][0]),
        None if regime["slope_bounds"][1] is None else F(regime["slope_bounds"][1]),
    )
    submitted = [
        (F(n["input"]), F(n["output"][0]), F(n["output"][1])) for n in comparison["patches"]
    ]
    require(submitted == patches, "calibration patch constraints changed")
    require(comparison["slope_bounds"] == regime["slope_bounds"], "slope conditions changed")
    require(len(truth) == 25, "expected 25 source values")
    return patches, slopes, regime, error


def comparison_summary(comparison, regime, offsets):
    represented = [
        F(row["offset_sigma"])
        for row in comparison["all_candidate_results"]
        if row["status"] == "compatible"
    ]
    require(
        represented == [F(v) for v in comparison["represented_compatible_offsets_sigma"]],
        "represented offsets disagree with complete row statuses",
    )
    require(len(represented) == comparison["compatible_count"], "incorrect compatible denominator")
    if regime["response"] == "quadratic":
        require(F(0) in represented, "truth lost under matching calibration")
    else:
        require(F(0) not in represented, "wrong identity regime unexpectedly retains truth")
    if regime["name"] == "normalization_only":
        require(represented == offsets, "endpoint-only response gauge lost")
    return {
        "regime": regime["name"],
        "output_halfwidth": comparison["observation_halfwidth"],
        "compatible": len(represented),
        "incompatible": len(offsets) - len(represented),
        "reported_true_zero_retained": F(0) in represented,
        "represented_compatible_offsets_sigma": [str(v) for v in represented],
    }


def gauge_check(gauge, positions, truth):
    offset, sigma = F(gauge["offset_sigma"]), F(gauge["sigma_ratio"])
    nodes = [(F(0), F(0), F(0)), (F(1), F(1), F(1))]
    nodes.extend((cdf((t - offset) / sigma), y, y) for t, y in zip(positions, truth, strict=True))
    details = validate_result(gauge["finite_declared_witness"], nodes, (F(0), None))
    require(details["status"] == "compatible", "ideal affine gauge lacks a witness")
    require(
        0 <= gauge["floating_analytic_gauge_maximum_difference"] < 1e-10,
        "reported floating gauge consistency check failed",
    )
    return details


def named_checks(audit, controls):
    anchors = [(F(0), F(0), F(0)), (F(1), F(1), F(1))]
    marginal = controls["marginal_vs_common"]
    audit.check(
        "marginal_base",
        "named_certificate",
        validate_result,
        marginal["calibration"],
        anchors,
        (F(0), F(2)),
    )
    a, b = (F(2, 5), F(4, 5), F(4, 5)), (F(3, 5), F(1, 5), F(1, 5))
    for index, n in enumerate((a, b)):
        audit.check(
            f"individual_query_{index}",
            "named_certificate",
            validate_result,
            marginal["individual_observations"][index],
            anchors + [n],
            (F(0), F(2)),
        )
    audit.check(
        "shared_queries",
        "named_certificate",
        validate_result,
        marginal["joint_observations"],
        anchors + [a, b],
        (F(0), F(2)),
    )
    for query in marginal["queries"]:
        x = F(query["input"])
        audit.check(
            f"query_{x}",
            "named_query",
            equal,
            tuple(F(v) for v in query["output"]),
            (max(F(0), 2 * x - 1), min(F(1), 2 * x)),
            "pointwise query envelope changed",
        )
    audit.check(
        "named_query_population",
        "population",
        equal,
        Counter(F(query["input"]) for query in marginal["queries"]),
        Counter([F(2, 5), F(1, 2), F(3, 5)]),
        "missing or duplicate named query",
    )
    spatial = controls["spatial_response"]
    a, b = (F(1, 2), F(1, 4), F(1, 4)), (F(1, 2), F(3, 4), F(3, 4))
    slopes = (F(1, 2), F(3, 2))
    for key, n in (("first_region", a), ("second_region", b)):
        audit.check(key, "named_certificate", validate_result, spatial[key], anchors + [n], slopes)
    audit.check(
        "shared_spatial_response",
        "named_certificate",
        validate_result,
        spatial["claimed_common_response"],
        anchors + [a, b],
        slopes,
    )
    uncertain = controls["uncertain_inputs"]
    audit.check(
        "input_midpoint",
        "named_certificate",
        validate_result,
        uncertain["midpoint_substitution"],
        [(F(1), F(0), F(0)), (F(1), F(1), F(1))],
        (F(0), None),
    )
    audit.check(
        "allowed_input_assignment",
        "named_certificate",
        validate_result,
        uncertain["allowed_assignment_input_2"],
        [(F(1), F(0), F(0)), (F(2), F(1), F(1))],
        (F(0), None),
    )
    quant = controls["quantization"]
    centre, integer = F(43, 80), round(255 * F(43, 80))
    cover = (F(2 * integer - 1, 510), F(2 * integer + 1, 510))
    audit.check(
        "quantizer_bin",
        "quantization",
        equal,
        (
            F(quant["true_center"]),
            quant["saved_integer"],
            tuple(F(v) for v in quant["bin_interval"]),
        ),
        (centre, integer, cover),
        "quantizer arithmetic changed",
    )
    audit.check(
        "quantizer_point",
        "named_certificate",
        validate_result,
        quant["incorrect_point_interpretation"],
        [(F(1, 2), centre, centre), (F(1, 2), F(integer, 255), F(integer, 255))],
        (F(0), None),
    )
    audit.check(
        "quantizer_cover",
        "named_certificate",
        validate_result,
        quant["correct_bin_interpretation"],
        [(F(1, 2), centre, centre), (F(1, 2), *cover)],
        (F(0), None),
    )
    return {
        "true_center": str(centre),
        "saved_integer": integer,
        "closed_cover_endpoint_codes": [round(255 * value) for value in cover],
        "scope": "Closed outer cover; odd137 excludes both exact ties under ties-to-even.",
    }


def stage_check(stage):
    fields = (
        "actual_Keys_mean",
        "incorrect_square_after_Keys",
        "correct_Keys_after_square",
        "signed_Keys_value_outside_source_domain",
    )
    require(
        [F(stage[key]) for key in fields] == [F(1, 2), F(1, 4), F(1, 2), F(-1, 16)],
        "sampling/response noncommutation control changed",
    )
    require(
        stage["equal_original_linear_channel_mixes"] == [127.5, 127.5]
        and stage["encoded8_RGB"] == [[[0, 255, 0], [137, 137, 0]]],
        "RGB source reconstruction",
    )
    decoded = 255 * ((137 / 255 + 0.055) / 1.055) ** 2.4
    values = stage["per_channel_square_encoded8_decoded_mixes"]
    require(
        values[0] == 127.5 and abs(values[1] - decoded) < 2e-5,
        "independent float64 sRGB check disagrees with recorded float32 mix",
    )
    return {
        "independent_float64_decoded_137": decoded,
        "scope": "Floating stage consistency, not an optical or camera-error bound.",
    }


def mismatch_check(linear, truth):
    best = linear["fit"]["best"]
    edge = best["offset"]
    low, high = best["levels"]
    predicted = [
        low + (high - low) * float(cdf((F(i) - 12 - F.from_float(edge)) / 4)) for i in range(25)
    ]
    cost = sum((float(y) - p) ** 2 for y, p in zip(truth, predicted, strict=True))
    require(abs(cost - best["cost"]) < 1e-15, "independent linear-response cost differs")
    require(linear["offset_error_sigma"] == edge / 4, "raw-coordinate/sigma offset conversion")
    require(
        best["cost"] <= min(linear["fit"]["grid_costs"]), "reported minimum worse than its grid"
    )
    return {
        "independent_cost": cost,
        "offset_error_sigma": linear["offset_error_sigma"],
        "scope": "Separate bounded-level deterministic mismatch model, not a feasibility ranking.",
    }


def audit_run(run_path):
    before, started = source_hashes(run_path), time.perf_counter()
    data, plan = strict_json(run_path), strict_json(PLAN_PATH)
    if (
        data.get("format") != "pictures-to-cad-response-calibration-study"
        or data.get("version") != 1
    ):
        raise ValueError("--run must contain a version-1 response-calibration study")
    audit = Audit()
    audit.check(
        "submitted_plan", "provenance", equal, data["plan"], plan, "recorded/current plans differ"
    )
    recorded_sources = data["provenance"]["source_sha256"]
    audit.check(
        "source_manifest_keys",
        "provenance",
        equal,
        set(recorded_sources),
        set(SOURCES),
        "source manifest differs",
    )
    for path in SOURCES:
        audit.check(
            path,
            "provenance",
            equal,
            before[path],
            recorded_sources.get(path),
            "recorded/current source hashes differ",
        )
    positions = [F(v) for v in data["profile_positions_sigma"]]
    audit.check(
        "positions",
        "population",
        equal,
        positions,
        [F(-3) + F(i, 4) for i in range(25)],
        "position population changed",
    )
    audit.check(
        "plan_positions",
        "population",
        equal,
        positions,
        [F(v) for v in plan["profile_positions_sigma"]],
        "plan positions differ",
    )
    truth = [response(cdf(t)) for t in positions]
    audit.check(
        "source_mean",
        "source",
        equal,
        [F(v) for v in data["true_output_levels"]],
        truth,
        "source reconstruction differs",
    )
    audit.check(
        "source_conditions",
        "source",
        equal,
        (
            F(plan["response_quadratic_coefficient"]),
            F(plan["true_offset_sigma"]),
            F(plan["true_sigma"]),
        ),
        (F(3, 20), F(0), F(1)),
        "version-1 optical/source conditions differ",
    )
    offsets = [F(i, 64) for i in range(-32, 33)]
    audit.check(
        "offset_plan",
        "population",
        equal,
        plan["offset_grid"],
        {"integer_start": -32, "integer_stop": 32, "denominator": 64},
        "offset grid changed",
    )
    audit.check(
        "input_population",
        "population",
        equal,
        len(data["candidate_inputs"]),
        65,
        "missing source input row",
    )
    for index, source in enumerate(data["candidate_inputs"]):
        audit.check(
            f"input_{index}",
            "source",
            equal,
            (
                source["index"],
                F(source["offset_sigma"]),
                [F(v) for v in source["exact_frozen_input_levels"]],
            ),
            (index, offsets[index], [cdf(t - offsets[index]) for t in positions]),
            "frozen candidate input differs",
        )
    comparisons, keys = [], []
    for comparison in data["calibration_comparisons"]:
        name = f"{comparison['regime']}/{comparison['observation_halfwidth']}"
        keys.append((comparison["regime"], F(comparison["observation_halfwidth"])))
        try:
            patches, slopes, regime, error = reconstruct_comparison(plan, comparison, truth)
        except Exception as failure:  # noqa: BLE001 - preserve unreconstructable row failures too.
            for index, _ in enumerate(comparison["all_candidate_results"]):
                audit.check(
                    f"{name}/{index}",
                    "candidate",
                    require,
                    False,
                    f"constraint reconstruction: {failure}",
                )
            continue
        rows = comparison["all_candidate_results"]
        audit.check(
            f"{name}/population", "population", equal, len(rows), 65, "missing candidate row"
        )
        for index, row in enumerate(rows):
            if index >= len(offsets):
                audit.check(
                    f"{name}/{index}", "candidate", require, False, "extra undeclared candidate row"
                )
                continue
            edge = offsets[index]
            nodes = patches + [
                (cdf(t - edge), y - error, y + error) for t, y in zip(positions, truth, strict=True)
            ]
            audit.check(
                f"{name}/{index}", "candidate", candidate_check, row, index, edge, nodes, slopes
            )
        summary = audit.check(
            f"{name}/summary", "comparison", comparison_summary, comparison, regime, offsets
        )
        if summary["verification"] == "passed":
            comparisons.append(summary["details"])
    expected_keys = [
        (regime["name"], F(error))
        for regime in plan["calibration_regimes"]
        for error in plan["observation_halfwidths"]
    ]
    audit.check(
        "crossed_population",
        "population",
        equal,
        Counter(keys),
        Counter(expected_keys),
        "missing/duplicate regime/band",
    )
    audit.check(
        "comparison_population", "population", equal, len(keys), 18, "expected18comparisons"
    )
    for gauge in data["analytic_gauge"]["cases"]:
        audit.check(
            f"gauge_{gauge['offset_sigma']}/{gauge['sigma_ratio']}",
            "gauge",
            gauge_check,
            gauge,
            positions,
            truth,
        )
    expected_gauges = {(e, s) for e in (F(-1, 2), F(0), F(1, 2)) for s in (F(3, 4), F(1), F(5, 4))}
    actual_gauges = [
        (F(g["offset_sigma"]), F(g["sigma_ratio"])) for g in data["analytic_gauge"]["cases"]
    ]
    audit.check(
        "gauge_population",
        "population",
        equal,
        Counter(actual_gauges),
        Counter(expected_gauges),
        "gauge population differs",
    )
    quantization = named_checks(audit, data["named_controls"])
    audit.check("source_stage", "stage", stage_check, data["named_controls"]["source_stage"])
    audit.check(
        "linear_mismatch", "mismatch", mismatch_check, data["linear_response_mismatch"], truth
    )
    candidate_checks = [check for check in audit.checks if check["kind"] == "candidate"]
    audit.check(
        "candidate_denominator",
        "population",
        equal,
        len(candidate_checks),
        1170,
        "expected1170retainedcandidatechecks",
    )
    after = source_hashes(run_path)
    audit.check(
        "source_unchanged", "provenance", equal, after, before, "source/result changed during audit"
    )
    passed_candidates = [check for check in candidate_checks if check["verification"] == "passed"]
    statuses = Counter(check["details"]["status"] for check in passed_candidates)
    failures = [check for check in audit.checks if check["verification"] != "passed"]
    return {
        "format": "independent-response-calibration-study-audit",
        "version": 1,
        "verification": "failed" if failures else "passed",
        "run": label(run_path),
        "source_sha256_before": before,
        "source_sha256_after": after,
        "runtime": {"python": platform.python_version(), "seconds": time.perf_counter() - started},
        "summary": {
            "expected_candidate_rows": 1170,
            "retained_candidate_checks": len(candidate_checks),
            "verified_compatible_witnesses": statuses["compatible"],
            "verified_incompatible_source_proofs": statuses["incompatible"],
            "candidate_failures": len(candidate_checks) - len(passed_candidates),
            "all_checks": len(audit.checks),
            "failed_checks": len(failures),
        },
        "comparisons": comparisons,
        "quantization": quantization,
        "checks": audit.checks,
        "limits": [
            "All declared finite rows are checked; no continuous offset exclusion/enclosure or confidence interval is established.",
            "The exact witness/proof checks concern supplied erfc-derived rational inputs, not certified real optical probabilities or measured calibration bounds.",
            "One shared witness is required across original observations; pointwise query envelopes do not permit independent choices of one response per point.",
            "Finite PL witnesses match declared samples only; the separate ideal affine Gaussian gauge does not establish a general projective/2-D source identity.",
            "Closed quantizer intervals conservatively cover endpoint ties; odd137 has even-code endpoints136/138 under ties-to-even.",
            "The linear-response result is a separate bounded-level deterministic mismatch control, not a performance ranking against exact feasibility.",
            "This audit calls no production calibration, tracing or image-correction function and does not alter any source-noise model or accept CAD geometry.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        default=DEFAULT_RUN,
        help="version-1 result JSON; canonical bundled result by default",
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="new .json destination; existing files refused"
    )
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("output already exists; preserve it and choose a fresh JSON path")
    if args.output.suffix.lower() != ".json":
        parser.error("output must have a .json suffix")
    try:
        report = audit_run(args.run)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        parser.error(f"invalid or incomplete study input: {error}")
    print(
        json.dumps(
            {
                "verification": report["verification"],
                "summary": report["summary"],
                "seconds": report["runtime"]["seconds"],
            },
            indent=2,
        )
    )
    return int(report["verification"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
