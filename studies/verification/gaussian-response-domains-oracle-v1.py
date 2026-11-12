"""Independent finite oracle for shared Gaussian response-domain set inversion.

Use --output NEW_JSON. Checks exact parameter-box splits/coverage, independent
response-cone and difference-graph feasibility, shared witness/proof certificates
and saved outward CDF certificates. Budgets retain unknown boxes; synthetic
controls establish no physical calibration or noise/confidence qualification.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import random
import re
import subprocess
import sys
import time
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CDF_HELPER = ROOT / "studies/verification/normal-cdf-bounds-oracle-v1.py"
RECTANGLE_HELPER = ROOT / "studies/verification/response-rectangles-study-audit-v1.py"
SEED = 260113
STUDY_PLAN = ROOT / "studies/gaussian-response-domains-v1.json"
STUDY_SOURCES = (
    "backend/response_calibration.py",
    "backend/response_rectangles.py",
    "backend/normal_cdf_bounds.py",
    "backend/gaussian_response_domains.py",
    "scripts/gaussian_response_domain_study.py",
    "studies/gaussian-response-domains-v1.json",
)
SOURCE_PATHS = (
    Path(__file__).resolve(),
    CDF_HELPER,
    RECTANGLE_HELPER,
    ROOT / "backend/gaussian_response_domains.py",
    ROOT / "backend/response_rectangles.py",
    ROOT / "backend/response_calibration.py",
    ROOT / "backend/normal_cdf_bounds.py",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def exact(value):
    """Independent fixture conversion; no production numeric conversion."""
    if isinstance(value, (bool, float)):
        raise TypeError("oracle requires exact fixture numbers")
    if isinstance(value, str) and (
        len(value) > 4096
        or re.fullmatch(r"[+-]?(?:\d+(?:/\d+|\.\d*)?|\.\d+)", value, re.ASCII) is None
    ):
        raise ValueError("expected a bounded exact rational/decimal string")
    try:
        return F(value)
    except ZeroDivisionError as error:
        raise ValueError("exact rational denominator must be nonzero") from error


def exact_json(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    return value


def source_hashes(extra=()):
    return {
        str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in (*SOURCE_PATHS, *extra)
    }


def load_helper(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def z_range(position, box):
    """Independent linear-fractional extrema from all four exact corners."""
    (elo, ehi), (slo, shi) = box
    require(elo <= ehi and 0 < slo <= shi, "invalid Gaussian parameter box")
    values = [(position - e) / sigma for e in (elo, ehi) for sigma in (slo, shi)]
    return min(values), max(values)


def graph_status(rectangles, slopes, mode):
    """Generic all-pair exact graph on ORIGINAL endpoint response variables."""
    require(0 < len(rectangles) <= 16, "oracle graph population exceeds 16 rectangles")
    data = []
    for a, b, low, high in rectangles:
        require(a <= b and low <= high, "unordered original rectangle")
        data.extend(
            [(b, low, "lower"), (a, high, "upper")]
            if mode == "some"
            else [(a, low, "lower"), (b, high, "upper")]
        )
    m, M = slopes
    size = len(data) + 1
    distance = [[None] * size for _ in range(size)]
    for i in range(size):
        distance[i][i] = F(0)

    def edge(i, j, value):
        if distance[i][j] is None or value < distance[i][j]:
            distance[i][j] = value

    for i, (_, value, bound) in enumerate(data, 1):
        edge(i, 0, -value) if bound == "lower" else edge(0, i, value)
    for i, (x, _, _) in enumerate(data, 1):
        for j, (y, _, _) in enumerate(data, 1):
            if x == y:
                edge(i, j, F(0))
            elif x < y:
                edge(j, i, -m * (y - x))
                if M is not None:
                    edge(i, j, M * (y - x))
    for via in range(size):
        for i in range(size):
            if distance[i][via] is None:
                continue
            for j in range(size):
                if distance[via][j] is not None:
                    edge(i, j, distance[i][via] + distance[via][j])
    return "incompatible" if any(distance[i][i] < 0 for i in range(size)) else "compatible"


def verify_partition(domain, tolerances, nodes):
    """Check exact binary child covers, rather than a volume-only equality.

    Adapted nodes use path (root=''), box, split_axis (None at a leaf), and label.
    Splits use exact longest width/tolerance, offset winning ties. Closed children
    share their split face, so a finite full binary tree covers the whole prior.
    """
    require(all(t > 0 for t in tolerances), "partition tolerances must be positive")
    by_path = {n["path"]: n for n in nodes}
    require(len(by_path) == len(nodes) and "" in by_path, "missing/duplicated root or node path")
    require(all(set(path) <= {"0", "1"} for path in by_path), "nonbinary partition path")
    visited, leaves = set(), []

    def visit(path, expected_box):
        require(path in by_path, "partition dropped a child/pending box")
        require(path not in visited, "partition revisits a node")
        node = by_path[path]
        visited.add(path)
        require(node["box"] == expected_box, "node box differs from exact parent cover")
        axis = node["split_axis"]
        if axis is None:
            require(
                node["label"] in ("inner", "excluded", "unknown"),
                "leaf has no terminal classification",
            )
            require(
                path + "0" not in by_path and path + "1" not in by_path,
                "terminal node has children",
            )
            leaves.append(node)
            return
        require(type(axis) is int and axis in (0, 1), "invalid split axis")
        ratios = [
            (hi - low) / tolerance
            for (low, hi), tolerance in zip(expected_box, tolerances, strict=True)
        ]
        expected_axis = 0 if ratios[0] >= ratios[1] else 1
        require(
            axis == expected_axis and ratios[axis] > 1,
            "split violates exact longest-width/tolerance or resolution stop",
        )
        low, high = expected_box[axis]
        midpoint = (low + high) / 2
        require(low < midpoint < high, "split does not divide a nondegenerate interval")
        first, second = list(expected_box), list(expected_box)
        first[axis], second[axis] = (low, midpoint), (midpoint, high)
        visit(path + "0", tuple(first))
        visit(path + "1", tuple(second))

    visit("", domain)
    require(visited == set(by_path), "partition contains unreachable/overlapping descendant nodes")
    require(len(nodes) == 2 * (len(nodes) - len(leaves)) + 1, "partition is not a full binary tree")
    return {
        "nodes": len(nodes),
        "leaves": len(leaves),
        "leaf_labels": dict(Counter(n["label"] for n in leaves)),
        "coverage_proof": "exact recursive closed-child union; no volume-only test",
    }


class Retained:
    def __init__(self):
        self.records = []

    def check(self, name, category, callback, *args):
        record = {"case": name, "category": category}
        try:
            details = callback(*args)
            if details is not None:
                record["details"] = details
            record["verification"] = "passed"
        except Exception as error:  # noqa: BLE001 - retain failures and continue the census.
            record.update(
                {
                    "verification": "failed",
                    "failure": {"type": type(error).__name__, "message": str(error)},
                }
            )
        self.records.append(record)
        return record


def box_tuple(raw):
    require(isinstance(raw, dict) and set(raw) == {"offset", "sigma"}, "box axes changed")
    return tuple(tuple(exact(x) for x in raw[key]) for key in ("offset", "sigma"))


def check_tree(result, config):
    nodes = result["nodes"]
    require(
        [n["index"] for n in nodes] == list(range(len(nodes)))
        and all(type(n["index"]) is int for n in nodes),
        "node indices missing/duplicated/reordered",
    )
    adapted, visited = [], set()

    def walk(index, parent, depth, path):
        require(
            type(index) is int and 0 <= index < len(nodes) and index not in visited,
            "invalid/cyclic/shared child index",
        )
        visited.add(index)
        node = nodes[index]
        require(
            node["parent"] == parent and (parent is None or type(node["parent"]) is int),
            "node parent differs from tree",
        )
        require(
            type(node["depth"]) is int and node["depth"] == depth, "node depth differs from tree"
        )
        is_split = node["status"] == "split"
        axis = ("offset", "sigma").index(node["split_axis"]) if is_split else None
        adapted.append(
            {
                "path": path,
                "box": box_tuple(node["box"]),
                "split_axis": axis,
                "label": {"accepted": "inner"}.get(node["status"], node["status"]),
            }
        )
        if is_split:
            require(
                len(node["children"]) == 2 and depth < config["max_depth"],
                "split violates depth/child count",
            )
            low, high = box_tuple(node["box"])[axis]
            require(
                exact(node["split_at"]) == (low + high) / 2,
                "saved split coordinate is not exact midpoint",
            )
            for bit, child in enumerate(node["children"]):
                walk(child, index, depth + 1, path + str(bit))
        else:
            require(
                node["children"] == [] and node["split_axis"] is None and node["split_at"] is None,
                "terminal retains a split/children",
            )

    walk(0, None, 0, "")
    require(visited == set(range(len(nodes))), "tree contains unreachable nodes")
    domain = tuple(tuple(map(exact, config[key])) for key in ("offset_bounds", "sigma_bounds"))
    return verify_partition(domain, tuple(map(exact, config["tolerances"])), adapted)


def expected_order(config):
    """Independent fixed order of endpoint calibration and Gaussian positions."""
    sources = []
    for index, item in enumerate(config["calibration"]):
        x, (low, high) = exact(item["input"]), tuple(map(exact, item["output"]))
        if x in (0, 1):
            sources.append(((0 if x == 0 else 2, F(0)), index, low, high))
    for index, item in enumerate(config["observations"], len(config["calibration"])):
        low, high = map(exact, item["output"])
        sources.append(((1, exact(item["position"])), index, low, high))
    groups = []
    for key in sorted({item[0] for item in sources}):
        at = sorted((i, lo, hi) for k, i, lo, hi in sources if k == key)
        groups.append(
            (key, [i for i, _, _ in at], max(lo for _, lo, _ in at), min(hi for _, _, hi in at))
        )
    running, records, failed_at = None, [], None
    for key, indices, low, high in groups:
        running = low if running is None else max(running, low)
        records.append(
            {
                "kind": "observation" if key[0] == 1 else "calibration_endpoint",
                "coordinate": str(key[1] if key[0] == 1 else F(key[0] == 2)),
                "source_indices": indices,
                "output": [str(low), str(high)],
                "selected_output": str(running),
            }
        )
        if running > high:
            failed_at = len(records) - 1
            break
    return sources, groups, records, failed_at


def check_order(node, config):
    sources, _groups, saved, failed_at = expected_order(config)
    evidence = node["order_evidence"]
    require(
        evidence["groups"] == saved,
        "ordered evidence loses group/intersection/running-max provenance",
    )
    if node["proof_kind"] == "ordered_response_family":
        require(
            failed_at is None and evidence["contradiction"] is None,
            "ordered family contradicts an output band",
        )
        require(
            tuple(config["slope_bounds"]) == (0, None)
            and all(exact(c["input"]) in (0, 1) for c in config["calibration"]),
            "ordered family used outside its regularity/calibration scope",
        )
        require(node["status"] == "accepted", "ordered family has wrong classification")
        return {
            "certificate": "forall parameters exists one shared response per parameter",
            "groups": len(saved),
        }
    require(
        node["proof_kind"] == "invariant_order_contradiction" and failed_at is not None,
        "invalid invariant-order exclusion",
    )
    proof = evidence["contradiction"]
    i, j = proof["lower_source"], proof["upper_source"]
    require(type(i) is int and type(j) is int, "order contradiction indices must be integers")
    lower = [s for s in sources if s[1] == i]
    upper = [s for s in sources if s[1] == j]
    require(len(lower) == len(upper) == 1, "order proof references omitted/interior/unknown source")
    kl, _, low, _ = lower[0]
    ku, _, _, high = upper[0]
    require(kl <= ku and low > high, "original order sources do not contradict monotonicity")
    require(
        (exact(proof["implied_lower"]), exact(proof["implied_upper"])) == (low, high),
        "order contradiction does not use original bounds",
    )
    require(
        proof["order_relation"] == ("same_input" if kl == ku else "increasing_input"),
        "order proof relation changed",
    )
    require(node["status"] == "excluded", "order contradiction not excluded")
    return {
        "certificate": "no shared nondecreasing response at any parameter",
        "groups": len(saved),
    }


def check_node(node, result, config, rectangle_helper):
    status, reason, proof = node["status"], node["reason"], node["proof_kind"]
    require(
        status in ("accepted", "excluded", "unknown", "split"),
        "pending/unrecognized final node status",
    )
    box = box_tuple(node["box"])
    slopes = tuple(config["slope_bounds"])
    if proof in ("ordered_response_family", "invariant_order_contradiction"):
        require(
            node["index"] == 0
            and node["input_covers"] == []
            and node["some"] is None
            and node["all"] is None,
            "symbolic shortcut unexpectedly uses numerical covers",
        )
        return check_order(node, config)
    require(node["order_evidence"] is None, "numerical node exposes unverified order evidence")
    if reason == "box_limit":
        require(
            status == "unknown"
            and proof is None
            and not node["input_covers"]
            and node["some"] is None
            and node["all"] is None
            and node["error"] is None,
            "unevaluated budget node fabricated evidence/certainty",
        )
        return {"unknown": "unevaluated pending box retained"}
    data = [
        (exact(c["input"]), exact(c["input"]), *map(exact, c["output"]))
        for c in config["calibration"]
    ]
    covers = node["input_covers"]
    require(
        [c["observation_index"] for c in covers] == list(range(len(covers)))
        and len(covers) <= len(config["observations"]),
        "observation cover order/count changed",
    )
    for cover, observation in zip(covers, config["observations"]):
        require(type(cover["observation_index"]) is int, "cover observation index not an integer")
        expected_z = z_range(exact(observation["position"]), box)
        require(
            tuple(map(exact, cover["z"])) == expected_z,
            "standardized coordinate cover misses exact four-corner extrema",
        )
        indices = cover["lower_cdf"], cover["upper_cdf"]
        require(
            all(type(i) is int and 0 <= i < len(result["cdf_evaluations"]) for i in indices),
            "CDF reference index invalid",
        )
        low_cdf, high_cdf = (result["cdf_evaluations"][i] for i in indices)
        require(
            (exact(low_cdf["z"]), exact(high_cdf["z"])) == expected_z,
            "profile reuses a CDF certificate at the wrong coordinate",
        )
        require(
            low_cdf["places"] == high_cdf["places"] == config["cdf_places"], "CDF precision changed"
        )
        interval = exact(low_cdf["output"][0]), exact(high_cdf["output"][1])
        require(
            tuple(map(exact, cover["input"])) == interval,
            "input interval is not outward CDF endpoint composition",
        )
        data.append((*interval, *map(exact, observation["output"])))
    if reason == "numerical_or_arithmetic_limit":
        require(
            status == "unknown"
            and proof is None
            and isinstance(node["error"], str)
            and node["error"],
            "arithmetic failure fabricated a mathematical conclusion",
        )
    else:
        require(
            len(covers) == len(config["observations"]) and node["error"] is None,
            "evaluated node omits observation covers",
        )
    modes = {}
    for mode in ("some", "all"):
        if node[mode] is not None:
            require(
                len(covers) == len(config["observations"]),
                "response result used an incomplete observation model",
            )
            graph = graph_status(data, slopes, mode)
            require(
                graph == rectangle_helper.cones(data, slopes, mode)[0],
                "independent graph/cone statuses differ",
            )
            rectangle_helper.validate_result(node[mode], data, slopes, mode)
            require(node[mode]["status"] == graph, "response status differs from generic graph")
            modes[mode] = graph
    if status == "accepted":
        require(
            proof == "universal_response"
            and reason == "every_input_witness"
            and modes == {"some": "compatible", "all": "compatible"},
            "numerical acceptance lacks one universal shared response",
        )
    elif status == "excluded":
        require(
            proof == "rectangle_contradiction"
            and reason == "some_input_contradiction"
            and modes == {"some": "incompatible"}
            and node["all"] is None,
            "numerical exclusion lacks existential infeasibility",
        )
    elif reason != "numerical_or_arithmetic_limit":
        require(
            proof is None and modes == {"some": "compatible", "all": "incompatible"},
            "unresolved node changes the response quantifier",
        )
        widths = [high - low for low, high in box]
        if status == "split":
            require(reason == "needs_refinement", "unexplained split")
        elif reason == "tolerance":
            require(
                all(w <= t for w, t in zip(widths, config["tolerances"], strict=True)),
                "tolerance stop before declared resolution",
            )
        elif reason == "depth_limit":
            require(node["depth"] >= config["max_depth"], "premature depth stop")
        else:
            raise AssertionError("unexplained unknown node")
    return {
        "status": status,
        "proof_kind": proof,
        "checked_response_modes": modes,
        "observation_covers": len(covers),
    }


def check_report(result, config):
    require(
        result["format"] == "pictures-to-cad-gaussian-response-domain-analysis"
        and type(result["version"]) is int
        and result["version"] == 1,
        "result format changed",
    )
    expected_input = {
        "observations": [
            {
                "position": str(exact(o["position"])),
                "output": [str(exact(x)) for x in o["output"]],
            }
            for o in config["observations"]
        ],
        "calibration": [
            {
                "input": str(exact(c["input"])),
                "output": [str(exact(x)) for x in c["output"]],
            }
            for c in config["calibration"]
        ],
        **{
            key: [None if x is None else str(exact(x)) for x in config[key]]
            for key in ("offset_bounds", "sigma_bounds", "slope_bounds")
        },
    }
    require(result["input"] == expected_input, "result loses exact original input/assumptions")
    expected_settings = {key: config[key] for key in ("cdf_places", "max_boxes", "max_depth")}
    expected_settings["tolerances"] = list(map(str, config["tolerances"]))
    require(result["settings"] == expected_settings, "result settings changed")
    nodes = result["nodes"]
    index_sets = {
        name: [n["index"] for n in nodes if n["status"] == state]
        for name, state in (("inner", "accepted"), ("unknown", "unknown"), ("excluded", "excluded"))
    }
    for name, indices in index_sets.items():
        require(
            result[name + "_node_indices"] == indices,
            "terminal index list drops/duplicates/relabels boxes",
        )
    outer = sorted(index_sets["inner"] + index_sets["unknown"])
    require(result["outer_node_indices"] == outer, "outer set is not inner union unknown")
    expected_status = (
        "unresolved"
        if index_sets["unknown"]
        else "compatible"
        if index_sets["inner"]
        else "incompatible"
    )
    require(result["status"] == expected_status, "top status invents certainty")
    evaluated_indices = [n["index"] for n in nodes if n["reason"] != "box_limit"]
    require(
        evaluated_indices == list(range(len(evaluated_indices)))
        and 1 <= len(evaluated_indices) <= config["max_boxes"],
        "BFS evaluation order/work budget changed",
    )
    if index_sets["unknown"] and any(n["reason"] == "box_limit" for n in nodes):
        require(
            len(evaluated_indices) == config["max_boxes"],
            "pending node called budget-limited before budget exhaustion",
        )
    cdfs = result["cdf_evaluations"]
    require(
        len({(exact(c["z"]), c["places"]) for c in cdfs}) == len(cdfs),
        "CDF cache records duplicated",
    )
    work = sum(n[mode]["work"] for n in nodes for mode in ("some", "all") if n[mode] is not None)
    summary = result["summary"]
    expected_summary = {
        "evaluated_boxes": len(evaluated_indices),
        "created_nodes": len(nodes),
        "accepted_leaves": len(index_sets["inner"]),
        "unknown_leaves": len(index_sets["unknown"]),
        "excluded_leaves": len(index_sets["excluded"]),
        "cdf_evaluations": len(cdfs),
        "response_work": work,
        "has_certified_feasible_parameters": bool(index_sets["inner"]),
        "feasible_parameters_exist": True if index_sets["inner"] else None if outer else False,
    }
    require(
        summary == expected_summary,
        "summary/three-valued feasibility differs from full retained tree",
    )
    for axis in ("offset", "sigma"):
        expected = (
            None
            if not outer
            else (
                min(exact(nodes[i]["box"][axis][0]) for i in outer),
                max(exact(nodes[i]["box"][axis][1]) for i in outer),
            )
        )
        actual = result["outer_projection"][axis]
        require(
            (None if actual is None else tuple(map(exact, actual))) == expected,
            "outer coordinate hull loses a retained box",
        )
    return {
        "status": result["status"],
        "evaluated_boxes": len(evaluated_indices),
        "leaves": {key: len(value) for key, value in index_sets.items()},
    }


def options(**changes):
    values = {
        "observations": [
            {"position": F(0), "output": [F(0), F(0)]},
            {"position": F(1), "output": [F(1), F(1)]},
        ],
        "calibration": [],
        "offset_bounds": (F(-1), F(1)),
        "sigma_bounds": (F(1), F(1)),
        "slope_bounds": (F(0), None),
        "tolerances": (F(1, 2), F(1, 4)),
        "cdf_places": 6,
        "max_boxes": 1,
        "max_depth": 8,
    }
    values.update(changes)
    return values


def named_cases(cdf_helper):
    identity_cal = [
        {"input": F(0), "output": [F(0), F(0)]},
        {"input": F(1), "output": [F(1), F(1)]},
    ]
    mismatch = [
        {"position": F(0), "output": [F(1, 2), F(1, 2)]},
        {"position": F(1), "output": [F(3, 5), F(3, 5)]},
    ]
    truth = []
    for p in (F(-1), F(0), F(1)):
        low, high = cdf_helper.reference_cdf_bounds(p)
        scale = 10**6
        lo = F((low * scale).numerator // (low * scale).denominator, scale) - F(1, 1024)
        hi = F(-(-(high * scale).numerator // (high * scale).denominator), scale) + F(1, 1024)
        truth.append({"position": p, "output": [lo, hi]})
    return [
        ("ordered_response_family", options(), "compatible"),
        (
            "invariant_order_exclusion",
            options(
                observations=[
                    {"position": F(0), "output": [F(1), F(1)]},
                    {"position": F(1), "output": [F(0), F(0)]},
                ]
            ),
            "incompatible",
        ),
        (
            "equal_position_shared_output",
            options(
                observations=[
                    {"position": F(0), "output": [F(0), F(1)]},
                    {"position": F(0), "output": [F(1, 2), F(3, 2)]},
                ]
            ),
            "compatible",
        ),
        (
            "equal_position_conflicting_output",
            options(
                observations=[
                    {"position": F(0), "output": [F(0), F(0)]},
                    {"position": F(0), "output": [F(1), F(1)]},
                ]
            ),
            "incompatible",
        ),
        (
            "endpoint_calibration_order_exclusion",
            options(calibration=[{"input": F(0), "output": [F(2), F(2)]}]),
            "incompatible",
        ),
        (
            "symbolic_family_outside_numerical_CDF_domain",
            options(offset_bounds=(F(100), F(101))),
            "compatible",
        ),
        ("finite_slope_budget1", options(slope_bounds=(F(0), F(32))), "unresolved"),
        ("finite_slope_refined", options(slope_bounds=(F(0), F(32)), max_boxes=7), "compatible"),
        (
            "identity_mismatch_budget1",
            options(observations=mismatch, calibration=identity_cal, slope_bounds=(F(1), F(1))),
            "unresolved",
        ),
        (
            "identity_mismatch_budget3",
            options(
                observations=mismatch,
                calibration=identity_cal,
                slope_bounds=(F(1), F(1)),
                max_boxes=3,
                tolerances=(F(1, 4), F(1, 4)),
            ),
            "unresolved",
        ),
        (
            "identity_mismatch_refined",
            options(
                observations=mismatch,
                calibration=identity_cal,
                slope_bounds=(F(1), F(1)),
                max_boxes=5,
                tolerances=(F(1, 4), F(1, 4)),
            ),
            "incompatible",
        ),
        (
            "interior_calibration_disables_order_family",
            options(calibration=[{"input": F(1, 2), "output": [F(0), F(1)]}]),
            "unresolved",
        ),
        (
            "tolerance_unknown",
            options(slope_bounds=(F(0), F(32)), tolerances=(F(2), F(1))),
            "unresolved",
        ),
        ("depth_unknown", options(slope_bounds=(F(0), F(32)), max_depth=0), "unresolved"),
        (
            "normalized_width_tie_offset_first",
            options(
                slope_bounds=(F(0), F(32)),
                offset_bounds=(F(-1, 2), F(1, 2)),
                sigma_bounds=(F(3, 4), F(5, 4)),
                tolerances=(F(1, 4), F(1, 8)),
            ),
            "unresolved",
        ),
        (
            "sigma_split",
            options(
                slope_bounds=(F(0), F(32)),
                offset_bounds=(F(-1, 2), F(1, 2)),
                sigma_bounds=(F(3, 4), F(5, 4)),
                tolerances=(F(1), F(1, 8)),
                max_boxes=3,
            ),
            None,
        ),
        (
            "known_identity_truth_retained",
            options(
                observations=truth,
                calibration=identity_cal,
                slope_bounds=(F(1), F(1)),
                offset_bounds=(F(-1, 4), F(1, 4)),
                sigma_bounds=(F(3, 4), F(5, 4)),
                tolerances=(F(1, 8), F(1, 8)),
                max_boxes=7,
            ),
            None,
        ),
    ]


def seeded_cases():
    rng = random.Random(SEED)
    result = []
    for index in range(12):
        observations = []
        for p in range(1 + index % 3):
            low = F(rng.randrange(5), 4)
            observations.append(
                {"position": F(p, 2), "output": [low, low + F(rng.randrange(3), 4)]}
            )
        m = rng.choice([F(0), F(1, 2)])
        M = rng.choice([F(2), F(8), None])
        result.append(
            (
                f"seeded_{index:02d}",
                options(
                    observations=observations,
                    calibration=[{"input": F(1, 2), "output": [F(0), F(1)]}] if index % 2 else [],
                    slope_bounds=(m, M),
                    offset_bounds=(F(-1, 2), F(1, 2)),
                    sigma_bounds=(F(3, 4), F(5, 4)),
                    max_boxes=3,
                ),
                None,
            )
        )
    return result


def saved_config(analysis):
    """Reconstruct bounded saved assumptions without a production parser."""
    raw, settings = analysis["input"], analysis["settings"]
    config = {
        "observations": [
            {"position": exact(o["position"]), "output": list(map(exact, o["output"]))}
            for o in raw["observations"]
        ],
        "calibration": [
            {"input": exact(c["input"]), "output": list(map(exact, c["output"]))}
            for c in raw["calibration"]
        ],
        **{
            key: tuple(None if x is None else exact(x) for x in raw[key])
            for key in ("offset_bounds", "sigma_bounds", "slope_bounds")
        },
        "tolerances": tuple(map(exact, settings["tolerances"])),
        **{key: settings[key] for key in ("cdf_places", "max_boxes", "max_depth")},
    }
    require(
        0 < len(config["observations"])
        and len(config["observations"]) + len(config["calibration"]) <= 16,
        "independent verifier supports at most 16 response rectangles",
    )
    require(
        0 < len(analysis["nodes"]) <= 511 and len(analysis["cdf_evaluations"]) <= 1024,
        "saved analysis exceeds bounded independent verifier resources",
    )
    z_range(
        config["observations"][0]["position"],
        tuple(config[key] for key in ("offset_bounds", "sigma_bounds")),
    )
    require(
        all(
            len(config[key]) == 2
            for key in ("offset_bounds", "sigma_bounds", "slope_bounds", "tolerances")
        ),
        "saved interval arity invalid",
    )
    require(all(t > 0 for t in config["tolerances"]), "saved tolerances not positive")
    require(
        all(
            0 <= c["input"] <= 1 and len(c["output"]) == 2 and c["output"][0] <= c["output"][1]
            for c in config["calibration"]
        ),
        "saved calibration outside normalized domain or unordered",
    )
    require(
        all(
            len(o["output"]) == 2 and o["output"][0] <= o["output"][1]
            for o in config["observations"]
        ),
        "saved observation band unordered",
    )
    m, M = config["slope_bounds"]
    require(m >= 0 and (M is None or M >= m), "saved slope bounds invalid")
    for key, low, high in (("cdf_places", 1, 30), ("max_boxes", 1, 4095), ("max_depth", 0, 48)):
        require(
            type(config[key]) is int and low <= config[key] <= high, "saved integer setting invalid"
        )
    return config


def analysis_checks(analysis, config, cdf_helper, rectangle_helper):
    checks = Retained()
    checks.check("tree_coverage", "partition", check_tree, analysis, config)
    checks.check("report", "report", check_report, analysis, config)
    for index, cdf in enumerate(analysis["cdf_evaluations"]):
        checks.check(f"CDF/{index}", "CDF_certificate", cdf_helper.audit_record, cdf)
    for index, node in enumerate(analysis["nodes"]):
        checks.check(
            f"node/{index}",
            "node_certificate",
            check_node,
            node,
            analysis,
            config,
            rectangle_helper,
        )
    return checks


def verify_analysis(analysis):
    """Audit one saved JSON analysis without production imports or calls.

    Returns verified counts or raises on any failed check. Deliberately bounded
    to 16 response rectangles, 511 nodes and 1024 CDF records; refusal is an auditor
    resource limit, not mathematical incompatibility. The caller must bind this
    file and both independent helper sources when preserving the result.
    """
    config = saved_config(analysis)
    before = source_hashes((CDF_HELPER, RECTANGLE_HELPER))
    cdf_helper = load_helper("independent_saved_domain_CDF", CDF_HELPER)
    rectangle_helper = load_helper("independent_saved_domain_response", RECTANGLE_HELPER)
    checks = analysis_checks(analysis, config, cdf_helper, rectangle_helper).records
    failures = [c for c in checks if c["verification"] != "passed"]
    require(
        not failures,
        "saved analysis failed independent checks: "
        + "; ".join(c["case"] + ": " + c["failure"]["message"] for c in failures),
    )
    require(
        source_hashes((CDF_HELPER, RECTANGLE_HELPER)) == before,
        "independent verifier sources changed during saved analysis audit",
    )
    return {
        "verification": "passed",
        "checks": len(checks),
        "nodes": len(analysis["nodes"]),
        "CDF_certificates": len(analysis["cdf_evaluations"]),
        "status": analysis["status"],
        "summary": analysis["summary"],
    }


def check_case(name, config, expected, production, cdf_helper, rectangle_helper, *, inject=None):
    record = {"case": name, "input": config, "expected_status": expected}
    try:
        actual_function = None
        if inject:
            actual_function = getattr(production, inject)

            def exhausted(*args, **kwargs):
                raise ArithmeticError("injected oracle numerical-limit control")

            setattr(production, inject, exhausted)
        try:
            result = production.analyze_gaussian_response(
                config["observations"],
                config["calibration"],
                **{k: v for k, v in config.items() if k not in ("observations", "calibration")},
            )
        finally:
            if inject:
                setattr(production, inject, actual_function)
        record["production"] = result
        json.dumps(result, allow_nan=False)
        checks = analysis_checks(result, config, cdf_helper, rectangle_helper)
        if expected is not None:
            checks.check(
                "analytic_expected_status",
                "analytic_control",
                require,
                result["status"] == expected,
                "declared analytical/control status differs",
            )
        if name == "known_identity_truth_retained":
            retained = any(
                all(
                    lo <= point <= hi
                    for (lo, hi), point in zip(
                        box_tuple(result["nodes"][i]["box"]), (F(0), F(1)), strict=True
                    )
                )
                for i in result["outer_node_indices"]
            )
            falsely_excluded = any(
                all(
                    lo <= point <= hi
                    for (lo, hi), point in zip(
                        box_tuple(result["nodes"][i]["box"]), (F(0), F(1)), strict=True
                    )
                )
                for i in result["excluded_node_indices"]
            )
            checks.check(
                "known_true_parameter_pair",
                "analytic_control",
                require,
                retained and not falsely_excluded,
                "known identity Gaussian truth was excluded",
            )
        if inject:
            checks.check(
                "injected_limit_is_unknown",
                "analytic_control",
                require,
                result["nodes"][0]["status"] == "unknown"
                and result["nodes"][0]["reason"] == "numerical_or_arithmetic_limit"
                and result["summary"]["feasible_parameters_exist"] is None,
                "numerical failure invented certainty",
            )
        record["checks"] = checks.records
        record["verification"] = (
            "failed" if any(c["verification"] == "failed" for c in checks.records) else "passed"
        )
    except Exception as error:  # noqa: BLE001 - retain every failing named/seeded case.
        record.update(
            {
                "verification": "failed",
                "failure": {"type": type(error).__name__, "message": str(error)},
            }
        )
    return record


def schema_controls(production):
    records = []
    invalid = [
        ("zero_sigma", {"sigma_bounds": (0, 1)}),
        ("negative_sigma", {"sigma_bounds": (-1, -1)}),
        ("reversed_offset", {"offset_bounds": (1, 0)}),
        ("float_parameter", {"offset_bounds": (0.0, 1)}),
        ("boolean_budget", {"max_boxes": True}),
        ("zero_budget", {"max_boxes": 0}),
        ("too_large_budget", {"max_boxes": 4096}),
        ("negative_depth", {"max_depth": -1}),
        ("zero_tolerance", {"tolerances": (0, 1)}),
        ("invalid_precision", {"cdf_places": 31}),
        ("negative_lower_slope", {"slope_bounds": (-1, None)}),
        ("outside_calibration_domain", {"calibration": [{"input": 2, "output": [0, 1]}]}),
        ("empty_observations", {"observations": []}),
        ("unsupported_numerical_CDF_root", {"offset_bounds": (10, 11), "slope_bounds": (0, 1)}),
    ]
    for name, changes in invalid:
        config = options(**changes)
        try:
            production.analyze_gaussian_response(
                config["observations"],
                config["calibration"],
                **{k: v for k, v in config.items() if k not in ("observations", "calibration")},
            )
        except (TypeError, ValueError) as error:
            records.append(
                {
                    "case": name,
                    "verification": "passed",
                    "refused": True,
                    "exception": type(error).__name__,
                    "message": str(error),
                }
            )
        except Exception as error:  # noqa: BLE001 - unexpected refusal is a retained failure.
            records.append(
                {
                    "case": name,
                    "verification": "failed",
                    "exception": type(error).__name__,
                    "message": str(error),
                }
            )
        else:
            records.append({"case": name, "verification": "failed", "refused": False})
    return records


def partition_controls():
    domain = ((F(0), F(2)), (F(1), F(1)))
    valid = [
        {"path": "", "box": domain, "split_axis": 0, "label": "split"},
        {"path": "0", "box": ((F(0), F(1)), (F(1), F(1))), "split_axis": None, "label": "unknown"},
        {"path": "1", "box": ((F(1), F(2)), (F(1), F(1))), "split_axis": None, "label": "unknown"},
    ]
    records = []
    for name, nodes, should_pass in [
        ("valid_shared_face_tree", valid, True),
        ("missing_pending_child", valid[:2], False),
        (
            "overlap_plus_gap_same_total_length",
            [
                valid[0],
                {**valid[1], "box": ((F(0), F(3, 2)), (F(1), F(1)))},
                {**valid[2], "box": ((F(0), F(1, 2)), (F(1), F(1)))},
            ],
            False,
        ),
        ("duplicate_terminal_path", [*valid, valid[2]], False),
    ]:
        try:
            details = verify_partition(domain, (F(1, 2), F(1)), nodes)
        except AssertionError as error:
            records.append(
                {
                    "case": name,
                    "verification": "failed" if should_pass else "passed",
                    "refused": True,
                    "message": str(error),
                }
            )
        else:
            records.append(
                {
                    "case": name,
                    "verification": "passed" if should_pass else "failed",
                    "details": details,
                }
            )
    return records


def run_oracle():
    before, started = source_hashes(), time.perf_counter()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from backend import gaussian_response_domains as production

    cdf_helper = load_helper("independent_CDF_domain_oracle", CDF_HELPER)
    rectangle_helper = load_helper("independent_rectangle_domain_oracle", RECTANGLE_HELPER)
    named, seeded = named_cases(cdf_helper), seeded_cases()
    cases = [
        check_case(name, config, expected, production, cdf_helper, rectangle_helper)
        for name, config, expected in [*named, *seeded]
    ]
    for target in ("normal_cdf_bounds", "calibrate_rectangles"):
        cases.append(
            check_case(
                "injected_" + target + "_limit",
                options(slope_bounds=(F(0), F(32))),
                "unresolved",
                production,
                cdf_helper,
                rectangle_helper,
                inject=target,
            )
        )
    controls = [*schema_controls(production), *partition_controls()]
    after = source_hashes()
    controls.append(
        {"case": "source_unchanged", "verification": "passed" if before == after else "failed"}
    )
    failed_cases = sum(c["verification"] == "failed" for c in cases)
    failed_controls = sum(c["verification"] == "failed" for c in controls)
    checks = [check for case in cases for check in case.get("checks", [])]
    return {
        "format": "independent-gaussian-response-domains-oracle",
        "version": 1,
        "verification": "failed" if failed_cases + failed_controls else "passed",
        "source_sha256_before": before,
        "source_sha256_after": after,
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "runtime": {"python": platform.python_version(), "seconds": time.perf_counter() - started},
        "population": {
            "named": len(named),
            "seeded": len(seeded),
            "injected_numerical_limits": 2,
            "retained_cases": len(cases),
            "controls": len(controls),
            "seed": SEED,
        },
        "summary": {
            "passed_cases": len(cases) - failed_cases,
            "failed_cases": failed_cases,
            "passed_controls": len(controls) - failed_controls,
            "failed_controls": failed_controls,
            "individual_checks": len(checks),
            "failed_individual_checks": sum(c["verification"] == "failed" for c in checks),
            "CDF_certificates": sum(c["category"] == "CDF_certificate" for c in checks),
            "node_certificates": sum(c["category"] == "node_certificate" for c in checks),
        },
        "cases": cases,
        "controls": controls,
        "limits": [
            "Named and seeded cases are finite development controls, not unseen/physical evaluation. The set-inversion target is conditional on supplied Gaussian/affine geometry, positions, output intervals and response regularity.",
            "Exact recursive midpoint-child unions prove coverage of the whole closed prior, including shared faces and unevaluated pending boxes. A volume equality alone is not used.",
            "Independent original-rectangle cones and generic difference graphs verify numerical feasibility; separately source-bound independent helpers replay saved CDF/witness/proof certificates without using production calibration to decide correctness.",
            "Ordered response families prove forall parameter pairs exists a common response per pair; universal-response witnesses prove the stronger exists one response for all covered inputs within their box. Different boxes need not share one response.",
            "Some-compatible Cartesian boxes alone establish no coupled feasibility; all-incompatible alone establishes no exclusion. Budgets and numerical failures remain unknown, not false certainty.",
            "Coordinate projection hulls lose correlation; their Cartesian product is not a feasibility certificate. No finite-resolution completeness, asymptotic convergence, noise/confidence, camera-calibration or physical-accuracy claim is made.",
            "This oracle reads no request JSON, ingests no photographs, changes no production/noise model and accepts no CAD geometry.",
        ],
    }


def strict_json(path):
    def unique(pairs):
        values = {}
        for key, value in pairs:
            if key in values:
                raise ValueError(f"duplicate JSON key: {key}")
            values[key] = value
        return values

    def nonfinite(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    with path.open("rb") as stream:
        data = stream.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("saved study exceeds the 16 MiB audit cap")
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique, parse_constant=nonfinite)


STUDY_CASES = (
    "endpoint_order_family",
    "reversed_order_contradiction",
    "finite_slope_feasible_overlap",
    "finite_slope_incompatible_overlap",
    "exact_zero_sigma_alias",
    "thin_feasible_offset_line",
    "identity_joint_band",
    "nonlinear_response_joint_band",
    "rounded_binary_level_singleton",
)


def study_protocol(plan):
    require(
        plan["format"] == "pictures-to-cad-gaussian-response-domain-study-plan"
        and type(plan["version"]) is int
        and plan["version"] == 1,
        "unsupported saved study plan",
    )
    require(plan["cases"] == list(STUDY_CASES), "study case population changed")
    require(
        plan["budgets"] == [1, 7, 63] and all(type(x) is int for x in plan["budgets"]),
        "study budgets changed",
    )
    require(
        type(plan["cdf_places"]) is int
        and plan["cdf_places"] == 24
        and type(plan["max_depth"]) is int
        and plan["max_depth"] == 24,
        "study precision/depth changed",
    )
    require(
        tuple(map(exact, plan["tolerances"])) == (F(1, 32), F(1, 16)), "study tolerances changed"
    )
    truth = plan["truth"]
    require(
        (
            exact(truth["offset"]),
            exact(truth["sigma"]),
            tuple(map(exact, truth["positions"])),
            exact(truth["additional_output_halfwidth"]),
        )
        == (F(0), F(1), (F(-1), F(0), F(1)), F(1, 32)),
        "study truth model changed",
    )
    require(
        type(truth["generation_places"]) is int
        and truth["generation_places"] == 30
        and truth["response"] == "h(u)=u+(3/20)*u*(1-u)",
        "truth generation changed",
    )
    return {"cases": 9, "budgets": 3, "expected_rows": 27}


def truth_record(item, position, cdf_helper):
    require(
        exact(item["position"]) == position
        and exact(item["cdf"]["z"]) == position
        and item["cdf"]["places"] == 30,
        "truth CDF coordinate/precision changed",
    )
    cdf_helper.audit_record(item["cdf"])
    low, high = map(exact, item["cdf"]["output"])
    curve = lambda u: (23 * u - 3 * u * u) / 20
    require(
        tuple(map(exact, item["identity_output"])) == (low - F(1, 32), high + F(1, 32)),
        "identity band omits generation cover or declared error",
    )
    require(
        tuple(map(exact, item["response_output"]))
        == (curve(low) - F(1, 32), curve(high) + F(1, 32)),
        "quadratic band is not its monotone interval image",
    )
    return {"position": position, "CDF_certificate": "independently replayed"}


def study_models(truth):
    curve = lambda u: (23 * u - 3 * u * u) / 20
    anchor = lambda x, y: {"input": x, "output": [y, y]}
    identity_cal = [anchor(F(0), F(0)), anchor(F(1), F(1))]
    curved_cal = [anchor(x, curve(x)) for x in (F(0), F(1, 4), F(1, 2), F(3, 4), F(1))]
    identity_obs, curved_obs = [], []
    for item in truth:
        low, high = map(exact, item["cdf"]["output"])
        p = exact(item["position"])
        identity_obs.append({"position": p, "output": [low - F(1, 32), high + F(1, 32)]})
        curved_obs.append(
            {"position": p, "output": [curve(low) - F(1, 32), curve(high) + F(1, 32)]}
        )

    def model(obs, cal=(), offset=(F(-1), F(1)), sigma=(F(1), F(1)), slopes=(F(0), None)):
        return {
            "observations": obs,
            "calibration": list(cal),
            "offset_bounds": list(offset),
            "sigma_bounds": list(sigma),
            "slope_bounds": list(slopes),
        }

    joint = (F(-1, 4), F(1, 4)), (F(3, 4), F(5, 4))
    obs = lambda p, y: {"position": F(p), "output": [F(y), F(y)]}
    rounded = F.from_float(0.5 * math.erfc(-1 / math.sqrt(2)))
    return {
        STUDY_CASES[0]: model(curved_obs, identity_cal, *joint),
        STUDY_CASES[1]: model([obs(0, 1), obs(1, 0)]),
        STUDY_CASES[2]: model([obs(0, 0), obs(1, 1)], slopes=(F(0), F(32))),
        STUDY_CASES[3]: model(
            [obs(0, F(1, 2)), obs(1, F(3, 5))], identity_cal, slopes=(F(1), F(1))
        ),
        STUDY_CASES[4]: model(
            [obs(0, F(1, 2))], identity_cal, (F(0), F(0)), joint[1], (F(1), F(1))
        ),
        STUDY_CASES[5]: model([obs(0, F(1, 2))], identity_cal, *joint, (F(1), F(1))),
        STUDY_CASES[6]: model(identity_obs, identity_cal, *joint, (F(1), F(1))),
        STUDY_CASES[7]: model(curved_obs, curved_cal, *joint, (F(17, 20), F(23, 20))),
        STUDY_CASES[8]: model(
            [obs(1, rounded)], identity_cal, (F(0), F(0)), (F(1), F(1)), (F(1), F(1))
        ),
    }, rounded


def study_row_metadata(row, index, key, model, plan):
    require(
        type(row["index"]) is int
        and row["index"] == index
        and (row["case"], row["max_boxes"]) == key
        and type(row["max_boxes"]) is int,
        "study row missing/duplicated/reordered",
    )
    require(
        row["verification"] == "executed", "study retained an execution failure, not a certificate"
    )
    require(row["model"] == exact_json(model), "row model differs from independent declarations")
    config = {
        **model,
        "tolerances": tuple(map(exact, plan["tolerances"])),
        "cdf_places": plan["cdf_places"],
        "max_depth": plan["max_depth"],
        "max_boxes": key[1],
    }
    check_report(row["analysis"], config)
    return {"case": key[0], "max_boxes": key[1], "original_model_checked": True}


def study_geometry(row):
    name, budget, analysis = row["case"], row["max_boxes"], row["analysis"]
    if name in (STUDY_CASES[0], STUDY_CASES[4]):
        require(
            analysis["status"] == "compatible" and analysis["inner_node_indices"] == [0],
            "family or zero-input sigma alias lost whole-prior feasibility",
        )
    elif name in (STUDY_CASES[1], STUDY_CASES[8]):
        require(
            analysis["status"] == "incompatible", "order or rounded-singleton contradiction lost"
        )
    elif name == STUDY_CASES[2]:
        require(
            analysis["status"] == ("unresolved" if budget == 1 else "compatible"),
            "finite-slope overlap control changes certainty before/after refinement",
        )
    elif name == STUDY_CASES[3]:
        require(
            analysis["status"] == ("unresolved" if budget == 1 else "incompatible")
            and not analysis["inner_node_indices"],
            "coupled identity mismatch invented feasibility",
        )
    elif name == STUDY_CASES[5]:
        require(
            analysis["status"] == "unresolved" and not analysis["inner_node_indices"],
            "thin feasible line falsely becomes an inner box or empty set",
        )
        intervals = []
        for index, node in enumerate(analysis["nodes"]):
            if node["status"] == "split":
                continue
            offset, sigma = box_tuple(node["box"])
            if offset[0] <= 0 <= offset[1]:
                require(
                    index not in analysis["excluded_node_indices"],
                    "excluded closed box intersects feasible e=0 line",
                )
                intervals.append(sigma)
        intervals.sort()
        require(
            intervals and intervals[0][0] == F(3, 4), "outer set drops start of feasible sigma line"
        )
        reach = intervals[0][1]
        for low, high in intervals[1:]:
            require(low <= reach, "outer set has a gap on feasible e=0 line")
            reach = max(reach, high)
        require(reach == F(5, 4), "outer set drops end of feasible sigma line")
    elif name in (STUDY_CASES[6], STUDY_CASES[7]):
        truth = F(0), F(1)
        contains = lambda node: all(
            lo <= value <= high
            for (lo, high), value in zip(box_tuple(node["box"]), truth, strict=True)
        )
        require(
            any(contains(analysis["nodes"][i]) for i in analysis["outer_node_indices"])
            and not any(contains(analysis["nodes"][i]) for i in analysis["excluded_node_indices"]),
            "generated joint truth excluded",
        )
    else:
        raise AssertionError("undeclared study case")
    return {"case": name, "max_boxes": budget, "analytic_geometry_retained": True}


def study_summary(item, row):
    a = row["analysis"]
    expected = {
        "case": row["case"],
        "max_boxes": row["max_boxes"],
        "status": a["status"],
        "inner": a["summary"]["accepted_leaves"],
        "excluded": a["summary"]["excluded_leaves"],
        "unknown": a["summary"]["unknown_leaves"],
        "evaluated": a["summary"]["evaluated_boxes"],
        "outer_projection": a["outer_projection"],
    }
    require(item == expected, "saved summary differs from full independently audited analysis")
    return {"summary_checked": True}


def audit_study(run_path):
    run_path = run_path.resolve()
    extra = (run_path, *[ROOT / p for p in STUDY_SOURCES])
    before, started = source_hashes(extra), time.perf_counter()
    data, plan = strict_json(run_path), strict_json(STUDY_PLAN)
    if (
        not isinstance(data, dict)
        or data.get("format") != "pictures-to-cad-gaussian-response-domain-study"
        or type(data.get("version")) is not int
        or data["version"] != 1
    ):
        raise ValueError("--run requires a version-1 Gaussian response-domain study")
    if any(
        not isinstance(data[key], list) or len(data[key]) > cap
        for key, cap in (("rows", 64), ("summaries", 64), ("truth", 16))
    ):
        raise ValueError("saved study population exceeds bounded audit limits")
    checks = Retained()
    checks.check("plan_protocol", "population", study_protocol, plan)
    checks.check(
        "recorded_plan", "provenance", require, data["plan"] == plan, "recorded/current plan differ"
    )
    for key in ("source_sha256_before", "source_sha256_after"):
        checks.check(
            key,
            "provenance",
            require,
            data[key] == {p: before[p] for p in STUDY_SOURCES},
            "recorded/current study source hashes differ",
        )
    cdf_helper = load_helper("independent_saved_study_truth_CDF", CDF_HELPER)
    positions = [F(-1), F(0), F(1)]
    checks.check(
        "truth_population",
        "population",
        require,
        [exact(t["position"]) for t in data["truth"]] == positions,
        "truth positions missing/duplicated/reordered",
    )
    for index, item in enumerate(data["truth"]):
        if index < len(positions):
            checks.check(
                f"truth/{index}", "truth", truth_record, item, positions[index], cdf_helper
            )
        else:
            checks.check(f"truth/{index}", "truth", require, False, "undeclared truth row")
    models, rounded = study_models(data["truth"])
    checks.check(
        "rounded_binary_control",
        "analytic_control",
        require,
        exact(data["rounded_level_control"]) == rounded,
        "rounded binary control changed",
    )
    low, high = map(exact, data["truth"][2]["cdf"]["output"])
    checks.check(
        "rounded_binary_outside_real_CDF_cover",
        "analytic_control",
        require,
        not low <= rounded <= high,
        "binary level was silently treated as the exact mathematical CDF",
    )
    grid = [(name, budget) for name in STUDY_CASES for budget in (1, 7, 63)]
    checks.check(
        "row_population",
        "population",
        require,
        len(data["rows"]) == 27,
        "all 27 study analyses must be retained",
    )
    for index, row in enumerate(data["rows"]):
        if index >= len(grid):
            checks.check(f"row/{index}", "row_metadata", require, False, "extra undeclared row")
            continue
        key = grid[index]
        checks.check(
            f"model/{index}",
            "row_metadata",
            study_row_metadata,
            row,
            index,
            key,
            models[key[0]],
            plan,
        )
        checks.check(
            f"analysis/{index}", "saved_analysis", lambda row=row: verify_analysis(row["analysis"])
        )
        checks.check(f"geometry/{index}", "analytic_geometry", study_geometry, row)
    checks.check(
        "summary_population",
        "population",
        require,
        len(data["summaries"]) == 27,
        "all 27 summaries must be retained",
    )
    for index, item in enumerate(data["summaries"]):
        if index < len(data["rows"]):
            checks.check(
                f"summary/{index}", "study_summary", study_summary, item, data["rows"][index]
            )
        else:
            checks.check(
                f"summary/{index}",
                "study_summary",
                require,
                False,
                "summary has no retained analysis",
            )
    expected_summary = {
        "expected_rows": 27,
        "retained_rows": len(data["rows"]),
        "execution_failures": sum(
            isinstance(r, dict) and r.get("verification") == "execution_failure"
            for r in data["rows"]
        ),
    }
    checks.check(
        "global_summary",
        "study_summary",
        require,
        data["summary"] == expected_summary,
        "global study denominator/failure count incorrect",
    )
    after = source_hashes(extra)
    checks.check(
        "source_unchanged",
        "provenance",
        require,
        before == after,
        "study/source/helper changed during saved audit",
    )
    failures = [c for c in checks.records if c["verification"] != "passed"]
    verified = [
        c["details"]
        for c in checks.records
        if c["category"] == "saved_analysis" and c["verification"] == "passed"
    ]
    return {
        "format": "independent-gaussian-response-domain-study-audit",
        "version": 1,
        "verification": "failed" if failures else "passed",
        "run": str(run_path),
        "source_sha256_before": before,
        "source_sha256_after": after,
        "runtime": {"python": platform.python_version(), "seconds": time.perf_counter() - started},
        "population": {
            "expected_analyses": 27,
            "retained_rows": len(data["rows"]),
            "truth_profiles": 1,
            "truth_positions": 3,
        },
        "summary": {
            "all_checks": len(checks.records),
            "failed_checks": len(failures),
            "verified_analyses": len(verified),
            "verified_nodes": sum(d["nodes"] for d in verified),
            "verified_CDF_certificates": sum(d["CDF_certificates"] for d in verified)
            + sum(
                c["category"] == "truth" and c["verification"] == "passed" for c in checks.records
            ),
            "internal_analysis_checks": sum(d["checks"] for d in verified),
        },
        "checks": checks.records,
        "limits": [
            "All 27 fixed case/budget analyses are replayed without production imports/calls. Shared truth generation is independently certificate-checked; budgets reuse models and one truth profile rather than independent captures.",
            "Exact closed-tree coverage and local certificates give conditional inner/outer parameter sets, not convergence, finite-resolution completeness, physical accuracy or a globally shared response over the accepted union.",
            "The saved-analysis verifier caps 16 response rectangles, 511 nodes and 1024 CDF records per analysis; exceeding these is an audit-resource refusal, not mathematical incompatibility.",
        ],
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        help="replay a saved 27-analysis study without production calls; omit for generated census",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new .json report; existing files/symlinks refused",
    )
    args = parser.parse_args(arguments)
    if args.output.exists() or args.output.is_symlink():
        parser.error("output already exists; preserve it and choose a fresh destination")
    if args.output.suffix.lower() != ".json":
        parser.error("output must have a .json suffix")
    try:
        report = audit_study(args.run) if args.run is not None else run_oracle()
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
        parser.error(f"invalid/incomplete audit input: {error}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(exact_json(report), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "verification": report["verification"],
                "population": report["population"],
                "summary": report["summary"],
                "seconds": report["runtime"]["seconds"],
            },
            indent=2,
        )
    )
    return int(report["verification"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
