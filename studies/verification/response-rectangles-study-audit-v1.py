"""Replay every finite rectangle-study certificate without production fitting.

Use --run RESULT_JSON (default: the bundled canonical study) --output NEW_JSON.
Original-rectangle cone inequalities independently determine both quantifiers;
shared PL witnesses, assignments and source-indexed contradictions are checked
exactly. Saved Gaussian certificates use the separate independent CDF auditor.
Every declared row/failure is retained. This is no continuous-offset, empirical
camera, statistical confidence or physical-accuracy certificate.
"""

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import platform
import re
import time
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/response-rectangles-v1.json"
DEFAULT_RUN = ROOT / "studies/results/response-rectangles-v1.json"
CDF_AUDITOR = ROOT / "studies/verification/normal-cdf-bounds-oracle-v1.py"
SOURCES = (
    "backend/response_calibration.py",
    "backend/response_rectangles.py",
    "backend/normal_cdf_bounds.py",
    "scripts/response_rectangles_study.py",
    "studies/response-rectangles-v1.json",
)
REGIMES = (
    "normalized_endpoints",
    "five_exact_patches_slopes",
    "five_bounded_patches_slopes",
    "incorrect_identity_patches_slopes",
)
MAX_RUN_BYTES = 16 * 1024 * 1024
EXACT = re.compile(r"[+-]?(?:\d+(?:/\d+|\.\d*)?|\.\d+)\Z", re.ASCII)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def number(value):
    """Independent bounded study-rational conversion, not production parsing."""
    if not isinstance(value, str) or len(value) > 4096 or EXACT.fullmatch(value) is None:
        raise ValueError("expected a bounded exact rational/decimal study string")
    try:
        return F(value)
    except ZeroDivisionError as error:
        raise ValueError("study rational denominator must be nonzero") from error


def exact_json(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    return value


def strict_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    with path.open("rb") as stream:
        data = stream.read(MAX_RUN_BYTES + 1)
    if len(data) > MAX_RUN_BYTES:
        raise ValueError("study JSON exceeds the audit's 16 MiB input cap")
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique, parse_constant=nonfinite)


def label(path):
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(run_path):
    paths = [Path(__file__), CDF_AUDITOR, run_path, *[ROOT / p for p in SOURCES]]
    return {label(path): digest(path) for path in paths}


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
        except Exception as error:  # noqa: BLE001 - retain failures and subsequent rows.
            record.update(
                {
                    "verification": "failed",
                    "failure": {"type": type(error).__name__, "message": str(error)},
                }
            )
        self.checks.append(record)
        return record


def equal(actual, expected, message):
    require(actual == expected, message)


def response(x):
    return (23 * x - 3 * x * x) / 20


def rectangles(raw):
    return [tuple(number(v) for v in (*r["input"], *r["output"])) for r in raw]


def constraints(data, mode):
    result = []
    for index, (a, b, low, high) in enumerate(data):
        require(a <= b and low <= high, "unordered original rectangle")
        if mode == "some":
            result += [(b, low, index, "right", "lower"), (a, high, index, "left", "upper")]
        else:
            require(mode == "all", "unknown input quantifier")
            result += [(a, low, index, "left", "lower"), (b, high, index, "right", "upper")]
    return result


def cones(data, slopes, mode, query=None):
    """Original one-sided endpoint cones, independent of chain propagation."""
    m, M = slopes
    require(m >= 0 and (M is None or M >= m), "invalid shared slope bounds")
    sources = constraints(data, mode)
    lows = [(x, value) for x, value, _, _, bound in sources if bound == "lower"]
    highs = [(x, value) for x, value, _, _, bound in sources if bound == "upper"]

    def low_at(x):
        values = [
            value + (m if x >= at else M) * (x - at)
            for at, value in lows
            if x >= at or M is not None
        ]
        return max(values) if values else None

    def high_at(x):
        values = [
            value + (m if x <= at else M) * (x - at)
            for at, value in highs
            if x <= at or M is not None
        ]
        return min(values) if values else None

    if any(low_at(x) is not None and low_at(x) > upper for x, upper in highs):
        return "incompatible", None
    return "compatible", None if query is None else (low_at(query), high_at(query))


def interpolate(points, x):
    for at, value in points:
        if at == x:
            return value
    for (a, low), (b, high) in itertools.pairwise(points):
        if a < x < b:
            return low + (high - low) * (x - a) / (b - a)
    raise AssertionError("assignment lies outside shared PL curve")


def validate_result(result, data, slopes, mode):
    expected, _ = cones(data, slopes, mode)
    require(result["input_mode"] == mode, "result quantifier changed")
    actual_slopes = (
        number(result["slope_bounds"][0]),
        None if result["slope_bounds"][1] is None else number(result["slope_bounds"][1]),
    )
    require(actual_slopes == slopes, "result slope assumptions changed")
    require(result["status"] == expected, "status differs from original-rectangle cone feasibility")
    require(type(result["work"]) is int and result["work"] >= 0, "invalid arithmetic-work metadata")
    endpoints = sorted({x for a, b, _, _ in data for x in (a, b)})
    m, M = slopes
    if expected == "compatible":
        require(result["contradiction"] is None, "compatible result exposes a contradiction")
        points = [(number(p["input"]), number(p["output"])) for p in result["witness"]]
        require(
            [x for x, _ in points] == endpoints,
            "shared witness omits/reorders/duplicates endpoints",
        )
        for (x, y), (xx, yy) in itertools.combinations(points, 2):
            dx, dy = xx - x, yy - y
            require(dx > 0 and m * dx <= dy, "shared witness violates lower secant")
            require(M is None or dy <= M * dx, "shared witness violates upper secant")
        assignments = result["assignments"]
        require(
            [a["source_index"] for a in assignments] == list(range(len(data)))
            and all(type(a["source_index"]) is int for a in assignments),
            "assignments lose original source indexing",
        )
        for assigned, (a, b, low, high) in zip(assignments, data, strict=True):
            fa, fb = interpolate(points, a), interpolate(points, b)
            x, y = number(assigned["input"]), number(assigned["output"])
            require(
                tuple(number(v) for v in assigned["endpoint_outputs"]) == (fa, fb),
                "assignment endpoint values differ from common curve",
            )
            require(a <= x <= b and low <= y <= high, "selected point misses original rectangle")
            require(interpolate(points, x) == y, "selected point is not on common PL curve")
            if mode == "some":
                require(fa <= high and fb >= low, "common curve cannot hit the rectangle")
            else:
                require(low <= fa <= fb <= high, "common curve does not cover every allowed input")
        return {"status": expected, "verified_common_witness": True, "assignments": len(data)}
    require(
        not result["witness"] and not result["assignments"],
        "incompatible result exposes witness/assignments",
    )
    proof = result["contradiction"]
    require(isinstance(proof, dict), "incompatibility omits proof")
    i, j = proof["lower_source"], proof["upper_source"]
    require(
        type(i) is int and type(j) is int and 0 <= i < len(data) and 0 <= j < len(data),
        "proof origin is not an original source index",
    )
    sources = constraints(data, mode)
    lower = [c for c in sources if c[2:] == (i, proof["lower_endpoint"], "lower")]
    upper = [c for c in sources if c[2:] == (j, proof["upper_endpoint"], "upper")]
    require(len(lower) == len(upper) == 1, "proof endpoint does not supply that original bound")
    xl, low, *_ = lower[0]
    xu, high, *_ = upper[0]
    at = number(proof["at_input"])
    require(endpoints[0] <= at <= endpoints[-1], "proof leaves endpoint domain")
    require(at >= xl or M is not None, "proof uses nonexistent backward upper slope")
    require(at <= xu or M is not None, "proof uses nonexistent forward upper slope")
    implied_low = low + (m if at >= xl else M) * (at - xl)
    implied_high = high + (m if at <= xu else M) * (at - xu)
    require(
        (implied_low, implied_high)
        == (number(proof["implied_lower"]), number(proof["implied_upper"])),
        "proof transport is not implied by its original sources",
    )
    require(implied_low > implied_high, "proof is not a strict contradiction")
    require(proof["kind"] in ("endpoint_intersection", "slope_bounds"), "unknown proof kind")
    if proof["kind"] == "endpoint_intersection":
        require(xl == xu == at, "endpoint intersection proof refers to distinct inputs")
    return {"status": expected, "verified_original_source_contradiction": True}


def protocol(plan):
    require(
        plan["format"] == "pictures-to-cad-response-rectangles-study-plan"
        and type(plan["version"]) is int
        and plan["version"] == 1,
        "unsupported plan",
    )
    expected = {
        "positions": [F(-2) + F(i, 2) for i in range(9)],
        "candidate_offsets": [F(i, 16) for i in range(-4, 5)],
        "observation_halfwidths": [F(0), F(1, 1024)],
        "patch_inputs": [F(i, 4) for i in range(5)],
    }
    for key, values in expected.items():
        require([number(v) for v in plan[key]] == values, f"changed version-1 {key}")
    require(
        plan["cdf_places"] == [6, 12, 24, 30] and all(type(p) is int for p in plan["cdf_places"]),
        "changed CDF precision population",
    )
    require(plan["regimes"] == list(REGIMES), "changed regime population")
    require(
        (
            number(plan["bounded_patch_halfwidth"]),
            number(plan["true_offset"]),
            number(plan["supplied_sigma"]),
        )
        == (F(1, 128), F(0), F(1)),
        "changed generation conditions",
    )
    require(
        plan["true_output_generation_cdf_places"] == 30
        and type(plan["true_output_generation_cdf_places"]) is int,
        "changed truth-cover precision",
    )
    require(plan["response"] == "h(u)=u+(3/20)*u*(1-u)", "changed response")
    return {
        "positions": 9,
        "regimes": 4,
        "halfwidths": 2,
        "precisions": 4,
        "offsets": 9,
        "expected_rows": 288,
    }


def cover_check(record, independent_audit):
    z, precision = number(record["z"]), record["places"]
    require(type(precision) is int and precision in (6, 12, 24, 30), "undeclared cover precision")
    require(
        type(record["terms"]) is int and 0 <= record["terms"] <= 256, "cover term budget invalid"
    )
    low, high = map(number, record["output"])
    require(
        0 <= low <= high <= 1 and high - low <= F(2, 10**precision), "cover range/width invalid"
    )
    require(
        type(record["reflected"]) is bool and record["reflected"] == (z < 0),
        "cover reflection changed",
    )
    if record["certificate"] is not None:
        for key, value in record["certificate"].items():
            if key not in ("internal_places", "omitted_sign"):
                number(value)
    independent_audit(record)
    return {"z": z, "places": precision, "independent_CDF_certificate_verified": True}


def truth_check(item, position, cover):
    low, high = map(number, cover["output"])
    require(number(item["position"]) == position, "truth position changed")
    require(
        tuple(map(number, item["cdf_input"])) == (low, high),
        "truth does not reuse declared 30-place CDF cover",
    )
    observed = response(low), response(high)
    require(
        tuple(map(number, item["recorded_output_cover"])) == observed,
        "truth is not the monotone quadratic image of its CDF cover",
    )
    require(
        0 <= observed[0] <= observed[1] <= 1, "truth-output cover leaves normalized response range"
    )
    return {"position": position, "recorded_output_cover": observed}


def expected_row(key, plan, covers):
    regime, width, precision, offset = key
    xs = (
        [F(0), F(1)]
        if regime == "normalized_endpoints"
        else [number(v) for v in plan["patch_inputs"]]
    )
    patch_width = (
        number(plan["bounded_patch_halfwidth"]) if regime == "five_bounded_patches_slopes" else F(0)
    )
    result = []
    for x in xs:
        y = x if regime == "incorrect_identity_patches_slopes" else response(x)
        result.append((x, x, max(F(0), y - patch_width), min(F(1), y + patch_width)))
    cover_keys = []
    for position in map(number, plan["positions"]):
        z = (position - offset) / number(plan["supplied_sigma"])
        lo, hi = map(number, covers[z, precision]["output"])
        truth_z = (position - number(plan["true_offset"])) / number(plan["supplied_sigma"])
        true_low, true_high = map(number, covers[truth_z, 30]["output"])
        result.append((lo, hi, response(true_low) - width, response(true_high) + width))
        cover_keys.append((z, precision))
    slopes = (F(0), None) if regime == "normalized_endpoints" else (F(17, 20), F(23, 20))
    return result, slopes, cover_keys


def row_check(row, index, key, expected, slopes, cover_keys):
    require(
        type(row["index"]) is int and row["index"] == index,
        "row index missing/duplicated/reordered",
    )
    actual_key = (
        row["regime"],
        number(row["observation_halfwidth"]),
        row["cdf_places"],
        number(row["offset"]),
    )
    require(
        type(row["cdf_places"]) is int and actual_key == key,
        "row is not its declared crossed hypothesis",
    )
    require(
        rectangles(row["rectangles"]) == expected,
        "original rectangles differ from independently reconstructed patches/CDF/output bands",
    )
    actual_slopes = (
        number(row["slope_bounds"][0]),
        None if row["slope_bounds"][1] is None else number(row["slope_bounds"][1]),
    )
    require(actual_slopes == slopes, "row slope bounds changed")
    require(
        [(number(c["z"]), c["places"]) for c in row["cdf_covers"]] == cover_keys
        and all(type(c["places"]) is int for c in row["cdf_covers"]),
        "row references incorrect shared CDF covers",
    )
    return {
        "regime": key[0],
        "halfwidth": key[1],
        "precision": key[2],
        "offset": key[3],
        "rectangles": len(expected),
    }


def classification(data, slopes):
    some, _ = cones(data, slopes, "some")
    all_inputs, _ = cones(data, slopes, "all")
    require(
        not (some == "incompatible" and all_inputs == "compatible"),
        "universal feasible cannot be existential infeasible",
    )
    if some == "incompatible":
        return "excluded_by_outer_boxes"
    return (
        "one_response_for_all_covered_inputs"
        if all_inputs == "compatible"
        else "undetermined_by_boxes"
    )


def classification_check(row, data, slopes, key):
    expected = classification(data, slopes)
    require(row["classification"] == expected, "classification changes the quantifier conclusion")
    if key[3] == 0 and key[0] != "incorrect_identity_patches_slopes":
        require(
            expected != "excluded_by_outer_boxes", "correctly generated zero offset was excluded"
        )
    if key[0] == "normalized_endpoints":
        require(
            expected == "one_response_for_all_covered_inputs",
            "endpoint-only flexible response control changed",
        )
    if key[0] == "incorrect_identity_patches_slopes":
        require(expected == "excluded_by_outer_boxes", "wrong identity response control changed")
    return {
        "classification": expected,
        "correct_regime_true_offset": key[3] == 0 and key[0] != "incorrect_identity_patches_slopes",
    }


def summary_check(item, key, classified):
    regime, width, precision = key
    require(
        (item["regime"], number(item["observation_halfwidth"]), item["cdf_places"]) == key
        and type(item["cdf_places"]) is int,
        "summary hypothesis changed",
    )
    selected = [(k[3], value) for k, value in classified if k[:3] == key]
    counts = dict(Counter(value for _, value in selected))
    require(
        type(item["candidates"]) is int and item["candidates"] == len(selected) == 9,
        "summary candidate denominator incorrect",
    )
    require(item["counts"] == counts, "summary counts differ from independently classified rows")
    actual = {
        name: [number(v) for v in offsets] for name, offsets in item["classified_offsets"].items()
    }
    expected = {name: [x for x, value in selected if value == name] for name in sorted(counts)}
    require(actual == expected, "summary drops/relabels/reorders hypothesis offsets")
    return {"regime": regime, "halfwidth": width, "precision": precision, "counts": counts}


def named_check(item, covers):
    name = item["name"]
    boxes = {
        "midpoint_changes_existential_question": (
            [(F(0), F(2), F(1), F(1)), (F(1), F(1), F(0), F(0))],
            (F(0), None),
        ),
        "same_non_degenerate_interval_not_duplicate_knot": (
            [(F(0), F(1), F(0), F(0)), (F(0), F(1), F(1), F(1))],
            (F(0), None),
        ),
        "strict_slope_some_vs_all": ([(F(0), F(1), F(0), F(0))], (F(1), F(1))),
        "unbounded_marginals_finite_witness": ([(F(0), F(1), F(0), F(0))], (F(0), None)),
        "finite_upper_slope_midpoint": ([(F(0), F(1), F(0), F(0))], (F(0), F(2))),
        "shared_offset_is_not_cartesian_selection": (
            [(F(0), F(1), F(1), F(1)), (F(1), F(2), F(1), F(1))],
            (F(1), F(1)),
        ),
    }
    if name == "rounded_float_is_not_exact_gaussian_probability":
        low, high = map(number, covers[F(1), 30]["output"])
        frozen = F.from_float(0.5 * math.erfc(-1 / math.sqrt(2)))
        require(
            number(item["z"]) == 1 and tuple(map(number, item["certified_cover"])) == (low, high),
            "float control uses wrong mathematical CDF cover",
        )
        require(
            number(item["frozen_float"]) == frozen,
            "float control changes declared binary approximation",
        )
        require(
            type(item["float_inside_cover"]) is bool
            and item["float_inside_cover"] == (low <= frozen <= high) is False,
            "float is falsely promoted into the exact Gaussian cover",
        )
        return {"frozen_binary_float_is_outside_30_place_cover": True}
    require(name in boxes, "unexpected named control")
    data, slopes = boxes[name]
    require(
        rectangles(item["rectangles"]) == data
        and (
            number(item["slope_bounds"][0]),
            None if item["slope_bounds"][1] is None else number(item["slope_bounds"][1]),
        )
        == slopes,
        "named control conditions changed",
    )
    require(set(item["results"]) == {"some", "all"}, "named control omits a quantifier")
    details = {
        mode: validate_result(item["results"][mode], data, slopes, mode) for mode in ("some", "all")
    }
    if name in (
        "midpoint_changes_existential_question",
        "same_non_degenerate_interval_not_duplicate_knot",
        "strict_slope_some_vs_all",
        "shared_offset_is_not_cartesian_selection",
    ):
        require(
            details["some"]["status"] == "compatible"
            and details["all"]["status"] == "incompatible",
            "named quantifier distinction lost",
        )
    if name in ("unbounded_marginals_finite_witness", "finite_upper_slope_midpoint"):
        queries = item["some_queries"]
        require(
            [number(q["input"]) for q in queries] == [F(0), F(1, 2), F(1)],
            "named query population changed",
        )
        for query in queries:
            actual = tuple(None if v is None else number(v) for v in query["output"])
            require(
                actual == cones(data, slopes, "some", number(query["input"]))[1],
                "named tight/unbounded query differs from original cones",
            )
    if name == "midpoint_changes_existential_question":
        result = item["midpoint_fixed_input_result"]
        require(
            result["status"] == "incompatible" and not result["witness"],
            "midpoint substitution no longer changes feasibility",
        )
        proof = result["contradiction"]
        lows, highs = [F(1), F(0)], [F(1), F(0)]
        i, j = proof["lower_source"], proof["upper_source"]
        require(
            type(i) is int and type(j) is int and 0 <= i < 2 and 0 <= j < 2,
            "fixed midpoint proof source invalid",
        )
        require(
            proof["kind"] == "duplicate_input"
            and number(proof["at_input"]) == 1
            and (number(proof["implied_lower"]), number(proof["implied_upper"]))
            == (lows[i], highs[j])
            and lows[i] > highs[j],
            "fixed midpoint duplicate proof is invalid",
        )
    if name == "shared_offset_is_not_cartesian_selection":
        require(
            item["coupled_model"]
            == {
                "inputs": ["delta", "1+delta"],
                "delta": ["0", "1"],
                "forced_output_difference": "1",
                "observed_output_difference": "0",
                "status": "incompatible_by_exact_unit_slope_identity",
            },
            "shared-offset counterexample changed",
        )
        # Unit slope fixes output difference to input difference1, independent
        # of a response intercept and the common delta. Box selection allows
        # both chosen inputs to be1 and therefore solves a different problem.
        require(F(1) != F(0), "shared-offset exact contradiction lost")
    return details


def audit_run(run_path):
    before, started = source_hashes(run_path), time.perf_counter()
    data, plan = strict_json(run_path), strict_json(PLAN)
    if (
        not isinstance(data, dict)
        or data.get("format") != "pictures-to-cad-response-rectangles-study"
        or type(data.get("version")) is not int
        or data["version"] != 1
    ):
        raise ValueError("--run must be a version-1 rectangle-study result")
    for key, cap in (
        ("rows", 512),
        ("cdf_covers", 1024),
        ("cdf_nesting_checks", 1024),
        ("truth", 32),
        ("summaries", 64),
        ("controls", 16),
    ):
        if not isinstance(data[key], list) or len(data[key]) > cap:
            raise ValueError(f"invalid/oversized {key} population")
    spec = importlib.util.spec_from_file_location("independent_cdf_certificate_audit", CDF_AUDITOR)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    audit = Audit()
    audit.check("plan_protocol", "population", protocol, plan)
    audit.check(
        "recorded_plan", "provenance", equal, data["plan"], plan, "recorded/current plan differ"
    )
    for field in ("source_sha256_before", "source_sha256_after"):
        audit.check(
            field + "_keys",
            "provenance",
            equal,
            set(data[field]),
            set(SOURCES),
            "study source-manifest keys differ",
        )
        for path in SOURCES:
            audit.check(
                field + "/" + path,
                "provenance",
                equal,
                data[field].get(path),
                before[path],
                "recorded/current source hashes differ",
            )
    positions = [number(v) for v in plan["positions"]]
    precisions = plan["cdf_places"]
    offsets = [number(v) for v in plan["candidate_offsets"]]
    widths = [number(v) for v in plan["observation_halfwidths"]]
    zs = sorted(
        {(x - offset) / number(plan["supplied_sigma"]) for x in positions for offset in offsets}
        | {F(1)}
    )
    cover_keys = [(number(c["z"]), c["places"]) for c in data["cdf_covers"]]
    expected_covers = [(z, p) for z in zs for p in precisions]
    audit.check(
        "CDF_cover_population",
        "population",
        equal,
        Counter(cover_keys),
        Counter(expected_covers),
        "missing/duplicate/extra shared CDF cover",
    )
    covers = dict(zip(cover_keys, data["cdf_covers"], strict=True))
    for index, cover in enumerate(data["cdf_covers"]):
        audit.check(f"CDF/{index}", "CDF_certificate", cover_check, cover, helper.audit_record)
    audit.check(
        "truth_population",
        "population",
        equal,
        [number(t["position"]) for t in data["truth"]],
        positions,
        "truth position population changed",
    )
    for index, item in enumerate(data["truth"]):
        if index >= len(positions):
            audit.check(f"truth/{index}", "truth", require, False, "extra truth row")
        else:
            at = (positions[index] - number(plan["true_offset"])) / number(plan["supplied_sigma"])
            audit.check(
                f"truth/{index}", "truth", truth_check, item, positions[index], covers[at, 30]
            )
    expected_nesting = [(z, a, b) for z in zs for a, b in itertools.pairwise(precisions)]
    actual_nesting = [(number(n["z"]), n["coarse"], n["fine"]) for n in data["cdf_nesting_checks"]]
    audit.check(
        "nesting_population",
        "population",
        equal,
        Counter(actual_nesting),
        Counter(expected_nesting),
        "missing/duplicate/extra precision nesting check",
    )
    for index, item in enumerate(data["cdf_nesting_checks"]):
        z, a, b = number(item["z"]), item["coarse"], item["fine"]
        low_a, high_a = map(number, covers[z, a]["output"])
        low_b, high_b = map(number, covers[z, b]["output"])
        audit.check(
            f"nesting/{index}",
            "CDF_nesting",
            equal,
            (type(item["nested"]) is bool and item["nested"], low_a <= low_b <= high_b <= high_a),
            (True, True),
            "reported nesting is false or not supported by saved bounds",
        )
    grid = list(itertools.product(REGIMES, widths, precisions, offsets))
    audit.check(
        "row_population",
        "population",
        equal,
        len(data["rows"]),
        len(grid),
        "expected every one of288crossed rows",
    )
    classified = []
    for index, row in enumerate(data["rows"]):
        if index >= len(grid):
            audit.check(f"row/{index}", "row", require, False, "extra undeclared row")
            continue
        key = grid[index]
        try:
            expected, slopes, row_covers = expected_row(key, plan, covers)
        except Exception as error:  # noqa: BLE001 - failed reconstructions retain every row.
            for kind in ("row", "some", "all", "classification"):
                audit.check(
                    f"{kind}/{index}",
                    "result" if kind in ("some", "all") else kind,
                    require,
                    False,
                    f"cannot reconstruct declared row: {error}",
                )
            continue
        audit.check(f"row/{index}", "row", row_check, row, index, key, expected, slopes, row_covers)
        for mode in ("some", "all"):
            audit.check(
                f"{mode}/{index}",
                "result",
                lambda mode=mode, row=row, expected=expected, slopes=slopes: validate_result(
                    row[mode], expected, slopes, mode
                ),
            )
        checked = audit.check(
            f"classification/{index}",
            "classification",
            classification_check,
            row,
            expected,
            slopes,
            key,
        )
        classified.append((key, classification(expected, slopes)))
        if checked["verification"] != "passed":
            continue
    summary_keys = list(itertools.product(REGIMES, widths, precisions))
    actual_keys = [
        (s["regime"], number(s["observation_halfwidth"]), s["cdf_places"])
        for s in data["summaries"]
    ]
    audit.check(
        "summary_population",
        "population",
        equal,
        actual_keys,
        summary_keys,
        "summary crossed population changed",
    )
    for index, item in enumerate(data["summaries"]):
        if index < len(summary_keys):
            audit.check(
                f"summary/{index}", "summary", summary_check, item, summary_keys[index], classified
            )
        else:
            audit.check(f"summary/{index}", "summary", require, False, "extra summary")
    names = [
        "midpoint_changes_existential_question",
        "same_non_degenerate_interval_not_duplicate_knot",
        "strict_slope_some_vs_all",
        "unbounded_marginals_finite_witness",
        "finite_upper_slope_midpoint",
        "shared_offset_is_not_cartesian_selection",
        "rounded_float_is_not_exact_gaussian_probability",
    ]
    audit.check(
        "named_population",
        "population",
        equal,
        Counter(c["name"] for c in data["controls"]),
        Counter(names),
        "named controls missing/duplicated/extra",
    )
    for item in data["controls"]:
        audit.check(item["name"], "named_control", named_check, item, covers)
    expected_summary = {
        "expected_rows": 288,
        "retained_rows": len(data["rows"]),
        "execution_failures": sum(
            isinstance(r, dict) and r.get("classification") == "execution_failure"
            for r in data["rows"]
        ),
        "classification_counts": dict(Counter(value for _, value in classified)),
    }
    audit.check(
        "global_summary",
        "summary",
        equal,
        data["summary"],
        expected_summary,
        "global counts differ from all independently classified rows",
    )
    after = source_hashes(run_path)
    audit.check(
        "source_unchanged",
        "provenance",
        equal,
        after,
        before,
        "source/run/helper changed during audit",
    )
    failed = [c for c in audit.checks if c["verification"] != "passed"]
    mode_checks = [c for c in audit.checks if c["kind"] == "result"]
    verified = Counter(c["details"]["status"] for c in mode_checks if c["verification"] == "passed")
    return {
        "format": "independent-response-rectangles-study-audit",
        "version": 1,
        "verification": "failed" if failed else "passed",
        "run": label(run_path),
        "source_sha256_before": before,
        "source_sha256_after": after,
        "runtime": {"python": platform.python_version(), "seconds": time.perf_counter() - started},
        "summary": {
            "expected_rows": 288,
            "retained_rows": len(data["rows"]),
            "mode_result_checks": len(mode_checks),
            "verified_common_witnesses": verified["compatible"],
            "verified_source_contradictions": verified["incompatible"],
            "CDF_cover_checks": sum(c["kind"] == "CDF_certificate" for c in audit.checks),
            "CDF_nesting_checks": len(data["cdf_nesting_checks"]),
            "named_controls": len(data["controls"]),
            "classification_counts": dict(Counter(value for _, value in classified)),
            "all_checks": len(audit.checks),
            "failed_checks": len(failed),
        },
        "CDF_covers_sha256": hashlib.sha256(
            json.dumps(data["cdf_covers"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "checks": audit.checks,
        "limits": [
            "Every finite row and both input quantifiers are audited; finite offset enumeration establishes no continuous exclusion, global uniqueness, confidence interval or physical optical accuracy.",
            "Original-rectangle cones determine conditional feasibility independently of production calibration. Witness secants and original-source proof transport are exact rational checks.",
            "Shared saved CDF certificates are replayed by the separately source-bound independent CDF auditor without production CDF calls; generated output bands are checked as monotone quadratic images of those covers.",
            "Some-compatible boxes can choose unrealizable Cartesian inputs and remain undetermined for correlated Gaussian inputs. All-compatible means one common curve for every covered input, conditional on the supplied model.",
            "All hypotheses reuse one nine-position synthetic truth profile; the288rows are not independent captures or unseen validation.",
            "Queries are pointwise envelopes, not simultaneous independent choices; null bounds retain genuine infinity rather than missing estimates.",
            "The study, independent audit and named controls do not ingest photographs, estimate physical error bounds, change source noise, correct images or accept CAD geometry.",
        ],
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        default=DEFAULT_RUN,
        help="version-1 study JSON; canonical bundled result by default",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new .json report; existing paths/symlinks refused",
    )
    args = parser.parse_args(arguments)
    if args.output.exists() or args.output.is_symlink():
        parser.error("output already exists; preserve it and choose a fresh destination")
    if args.output.suffix.lower() != ".json":
        parser.error("output must have a .json suffix")
    try:
        report = audit_run(args.run)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            json.dump(exact_json(report), stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
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
