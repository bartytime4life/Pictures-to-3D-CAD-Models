"""Independent exact graph oracle for conditional common-response feasibility.

Run with --output NEW_JSON. Finite named, paired and seeded development controls
compare production status/tight marginals with generic difference constraints,
verify one shared witness and exact contradiction provenance, and retain failures.
Exact rational JSON is not physical camera calibration or a confidence band.
--help and existing-output refusal do not run the census.
"""

import argparse
import copy
import hashlib
import itertools
import json
import math
import platform
import random
import subprocess
import sys
import time
from decimal import Context, localcontext
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import response_calibration as production

SEED = 88374
SEEDED_CASES = 256
MAX_ORACLE_NODES = 12
SOURCE_PATHS = [
    Path(__file__).resolve(),
    ROOT / "backend/response_calibration.py",
]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rational(value):
    """Independent fixture conversion; never call the production numeric parser."""
    if isinstance(value, (bool, float)):
        raise TypeError("oracle inputs must be exact")
    return Fraction(value)


def number_string(value):
    value = rational(value)
    return (
        str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    )


def json_exact(value):
    if isinstance(value, Fraction):
        return number_string(value)
    if isinstance(value, (tuple, list)):
        return [json_exact(item) for item in value]
    if isinstance(value, dict):
        return {key: json_exact(item) for key, item in value.items()}
    return value


def fixture_literal(value):
    if isinstance(value, Fraction):
        return {"kind": "Fraction", "value": number_string(value)}
    return {"kind": type(value).__name__, "value": str(value)}


def node(x, low, high=None):
    return {"input": x, "output": [low, low if high is None else high]}


def normalize(nodes):
    return [
        (rational(item["input"]), rational(item["output"][0]), rational(item["output"][1]))
        for item in nodes
    ]


def graph_oracle(nodes, slopes, query=None):
    """Floyd-Warshall closure on ORIGINAL observation variables, no chain passes.

    d[i][j] bounds y_j-y_i. Node0 is the fixed reference0. Duplicate inputs get
    equality edges independently of the production duplicate-grouping procedure.
    A query is an extra variable with no initial output interval.
    """
    data = normalize(nodes)
    require(0 < len(data) <= MAX_ORACLE_NODES, "oracle population outside its fixed cap")
    lower, upper = rational(slopes[0]), None if slopes[1] is None else rational(slopes[1])
    inputs = [item[0] for item in data]
    if query is not None:
        inputs.append(rational(query))
    dimension = len(inputs) + 1
    distance = [[None] * dimension for _ in range(dimension)]
    for index in range(dimension):
        distance[index][index] = Fraction(0)

    def edge(start, end, bound):
        previous = distance[start][end]
        if previous is None or bound < previous:
            distance[start][end] = bound

    for index, (_, low, high) in enumerate(data, 1):
        edge(0, index, high)
        edge(index, 0, -low)
    order = sorted(range(len(inputs)), key=lambda index: inputs[index])
    for before, after in itertools.pairwise(order):
        delta = inputs[after] - inputs[before]
        if not delta:
            edge(before + 1, after + 1, Fraction(0))
            edge(after + 1, before + 1, Fraction(0))
        else:
            edge(after + 1, before + 1, -lower * delta)
            if upper is not None:
                edge(before + 1, after + 1, upper * delta)
    for through in range(dimension):
        for start in range(dimension):
            if distance[start][through] is None:
                continue
            for end in range(dimension):
                if distance[through][end] is not None:
                    edge(start, end, distance[start][through] + distance[through][end])
    if any(distance[index][index] < 0 for index in range(dimension)):
        return None
    marginals = [(-distance[index][0], distance[0][index]) for index in range(1, dimension)]
    if query is not None:
        require(all(value is not None for value in marginals[-1]), "unbounded query outside domain")
        return marginals[-1]
    groups = []
    for x in sorted(set(inputs)):
        indices = tuple(index for index, current in enumerate(inputs) if current == x)
        values = {marginals[index] for index in indices}
        require(len(values) == 1, "graph duplicate equality failed")
        low, high = values.pop()
        groups.append((x, low, high, indices))
    return groups


def expected_source_groups(nodes):
    data = normalize(nodes)
    groups = []
    for x in sorted({row[0] for row in data}):
        indices = tuple(index for index, row in enumerate(data) if row[0] == x)
        groups.append(
            (x, max(data[i][1] for i in indices), min(data[i][2] for i in indices), indices)
        )
    return groups


def band_signature(bands):
    return [(b.input, b.lower, b.upper, tuple(b.source_indices)) for b in bands]


def witness_checks(result, nodes, slopes):
    data = normalize(nodes)
    lower, upper = rational(slopes[0]), None if slopes[1] is None else rational(slopes[1])
    witness = result.witness
    require(len(witness) == len(result.nodes), "witness omits a distinct input")
    values = {point.input: point.output for point in witness}
    require(len(values) == len(witness), "witness repeats an input")
    for x, lo, hi in data:
        require(lo <= values[x] <= hi, "shared witness violates an original observation")
    for band, point in zip(result.nodes, witness, strict=True):
        require(
            band.input == point.input and band.lower <= point.output <= band.upper,
            "witness violates a tight node band",
        )
    for left, right in itertools.combinations(witness, 2):
        delta = right.input - left.input
        difference = right.output - left.output
        require(delta > 0 and lower * delta <= difference, "witness violates common lower slope")
        require(upper is None or difference <= upper * delta, "witness violates common upper slope")


def contradiction_checks(result, nodes, slopes):
    proof = result.contradiction
    require(proof is not None, "incompatibility lacks an exact contradiction")
    require(not result.nodes and not result.witness, "incompatible result exposes a witness/bands")
    data = normalize(nodes)
    require(
        0 <= proof.lower_source < len(data) and 0 <= proof.upper_source < len(data),
        "contradiction source index is outside original observations",
    )
    lower, upper = rational(slopes[0]), None if slopes[1] is None else rational(slopes[1])
    xlow, low, _ = data[proof.lower_source]
    xhigh, _, high = data[proof.upper_source]
    require(
        xlow <= proof.at_input and xhigh <= proof.at_input, "contradiction transport goes backwards"
    )
    derived_low = low + lower * (proof.at_input - xlow)
    if upper is None:
        require(proof.at_input == xhigh, "unbounded upper slope cannot transport an upper bound")
        derived_high = high
    else:
        derived_high = high + upper * (proof.at_input - xhigh)
    require(
        (derived_low, derived_high) == (proof.implied_lower, proof.implied_upper),
        "contradiction is not implied by its indexed original bounds",
    )
    require(derived_low > derived_high, "contradiction is not strict")
    if proof.kind == "duplicate_input":
        require(xlow == xhigh == proof.at_input, "duplicate certificate has different inputs")
    else:
        require(proof.kind == "slope_bounds", "unrecognized contradiction kind")


def query_points(nodes):
    inputs = sorted({rational(item["input"]) for item in nodes})
    queries = set(inputs)
    for left, right in itertools.pairwise(inputs):
        queries.update(((2 * left + right) / 3, (left + 2 * right) / 3))
    return sorted(queries)


def check_case(name, nodes, slopes=(0, None), *, category="named"):
    record = {
        "case": name,
        "category": category,
        "submitted_nodes": [
            {
                "input": fixture_literal(item["input"]),
                "output": [fixture_literal(value) for value in item["output"]],
            }
            for item in nodes
        ],
        "exact_nodes": normalize(nodes),
        "slope_bounds": [rational(slopes[0]), None if slopes[1] is None else rational(slopes[1])],
    }
    try:
        expected = graph_oracle(nodes, slopes)
        result = production.calibrate_response(nodes, slope_bounds=slopes)
        record["oracle_status"] = "compatible" if expected is not None else "incompatible"
        record["oracle_tight_knots"] = expected
        record["production"] = result.to_dict()
        json.dumps(record["production"], allow_nan=False)
        require(result.status == record["oracle_status"], "production/graph status differs")
        require(
            band_signature(result.source_groups) == expected_source_groups(nodes),
            "source groups lose original bounds or provenance",
        )
        require(
            result.slope_bounds == tuple(record["slope_bounds"]), "reported slope bounds changed"
        )
        if expected is None:
            contradiction_checks(result, nodes, slopes)
            try:
                result.query(nodes[0]["input"])
            except ValueError:
                record["incompatible_query_refused"] = True
            else:
                raise AssertionError("incompatible result allowed a query")
        else:
            require(result.contradiction is None, "compatible result exposes a contradiction")
            require(
                band_signature(result.nodes) == expected, "tight knot marginals differ from graph"
            )
            witness_checks(result, nodes, slopes)
            queries = []
            for x in query_points(nodes):
                envelope = graph_oracle(nodes, slopes, query=x)
                actual = result.query(x)
                require(
                    (actual.lower, actual.upper) == envelope, "query envelope differs from graph"
                )
                queries.append(
                    {
                        "input": x,
                        "oracle_interval": envelope,
                        "production_interval": [actual.lower, actual.upper],
                    }
                )
            record["queries"] = queries
            inputs = sorted({row[0] for row in normalize(nodes)})
            for outside in [inputs[0] - 1, inputs[-1] + 1]:
                try:
                    result.query(outside)
                except ValueError:
                    pass
                else:
                    raise AssertionError("query extrapolated beyond declared knot domain")
            record["outside_queries_refused"] = True
        record["verification"] = "passed"
    except Exception as error:  # noqa: BLE001 - retain a failed case without dropping the census.
        record["verification"] = "failed"
        record["failure"] = {"type": type(error).__name__, "message": str(error)}
    return record


def named_cases():
    tiny = Fraction(1, 10**40)
    return [
        ("known_unit_slope", [node(0, 0), node(1, 0, 10), node(2, 2)], (1, 1)),
        (
            "independent_pairs_pass_common_chain_fails",
            [node(0, 0), node(1, 0, 2), node(2, 3)],
            (1, 1),
        ),
        ("upper_slope_conflict", [node(0, 0), node(1, 2)], (0, 1)),
        ("plateau_allowed", [node(0, 0), node(1, 0)], (0, 1)),
        ("positive_lower_rejects_plateau", [node(0, 0), node(1, 0)], ("0.1", 1)),
        (
            "duplicate_common_input_overlap",
            [node(".5", 0, ".7"), node("0.500e0", ".3", 1)],
            (0, None),
        ),
        (
            "duplicate_common_input_conflict",
            [node(".5", ".25"), node(Fraction(1, 2), ".75")],
            (0, None),
        ),
        ("tiny_exact_spacing", [node(1, 0), node(1 + tiny, tiny)], (1, 1)),
        ("between_knot_curve_not_PL_witness", [node(0, 0), node(1, 1)], (0, 2)),
        ("inserted_halfway_query", [node(0, 0), node(".5", -100, 100), node(1, 1)], (0, 2)),
        ("one_third_PL_slope", [node(0, 0), node(3, 1)], (0, 1)),
        ("uncertain_input_midpoint_counterexample", [node(1, 1), node(1, 0)], (0, None)),
        ("allowed_uncertain_input_assignment", [node(2, 1), node(1, 0)], (0, None)),
    ]


def paired_cases():
    anchors = [node(0, 0), node(1, 1)]
    low_query, high_query = node(".6", ".1", ".2"), node(".4", ".8", ".9")
    spatial_a, spatial_b = node(".5", ".25"), node(".5", ".75")
    return [
        ("neighbor_pair_left", [node(0, 0), node(1, 0, 2)], (1, 1)),
        ("neighbor_pair_right", [node(1, 0, 2), node(2, 3)], (1, 1)),
        ("query_envelopes_overlap_individually", anchors, (0, None)),
        ("first_query_individually_feasible", [*anchors, high_query], (0, None)),
        ("second_query_individually_feasible", [*anchors, low_query], (0, None)),
        ("query_choices_have_no_shared_curve", [*anchors, high_query, low_query], (0, None)),
        ("first_spatial_map_feasible", [*anchors, spatial_a], (".5", "1.5")),
        ("second_spatial_map_feasible", [*anchors, spatial_b], (".5", "1.5")),
        ("two_spatial_maps_not_one_curve", [*anchors, spatial_a, spatial_b], (".5", "1.5")),
        ("backward_tightens_every_knot", [node(0, 0, 10), node(1, 0, 10), node(2, 3)], (1, 1)),
        ("closed_duplicate_contact", [node("-0", 0, 1), node(0, 1, 2)], (0, None)),
        (
            "signed_fractional_domain",
            [
                node(Fraction(-2, 3), Fraction(-1, 7), Fraction(1, 2)),
                node(Fraction(1, 3), Fraction(2, 7), Fraction(6, 7)),
            ],
            (Fraction(1, 9), Fraction(7, 8)),
        ),
        ("one_input_point_domain", [node(2, -3, 4)], (2, 3)),
    ]


def seeded_cases():
    rng = random.Random(SEED)
    cases = []
    for index in range(SEEDED_CASES):
        count, previous, inputs = rng.randrange(1, 7), Fraction(-1), []
        for _ in range(count):
            previous += Fraction(rng.randrange(1, 9), 8)
            inputs.append(previous)
        nodes = []
        for x in inputs:
            low = Fraction(rng.randrange(-8, 17), 8)
            nodes.append(node(x, low, low + Fraction(rng.randrange(0, 17), 8)))
        slopes = (
            rng.choice([Fraction(0), Fraction(1, 8), Fraction(1, 2)]),
            rng.choice([Fraction(1, 2), Fraction(1), Fraction(3), None]),
        )
        cases.append((f"seeded_{index:03d}", nodes, slopes))
    return cases


def edge_gauge_cases():
    # Rounded erfc values are exact rational stand-ins here, not certified optics.
    positions = [-2, -1, 0, 1, 2]
    cdf = lambda value: Fraction.from_float(0.5 * math.erfc(-value / math.sqrt(2)))
    outputs = [cdf(value) for value in positions]
    cases = []
    for offset in [Fraction(0), Fraction(1, 2), Fraction(1)]:
        inputs = [cdf(value - float(offset)) for value in positions]
        cases.append(
            (
                f"normalized_edge_response_gauge_{number_string(offset)}",
                [
                    node(0, 0),
                    *[node(x, y) for x, y in zip(inputs, outputs, strict=True)],
                    node(1, 1),
                ],
                (0, None),
            )
        )
    return cases


def refusal_control(name, callback, expected_words=None):
    record = {"case": name}
    try:
        returned = callback()
    except (ValueError, TypeError) as error:
        record.update({"refused": True, "exception": type(error).__name__, "message": str(error)})
        record["verification"] = (
            "passed" if expected_words is None or expected_words in str(error) else "failed"
        )
    except Exception as error:  # noqa: BLE001 - unexpected refusal types are recorded failures.
        record.update(
            {
                "refused": True,
                "exception": type(error).__name__,
                "message": str(error),
                "verification": "failed",
            }
        )
    else:
        record.update(
            {"refused": False, "returned_type": type(returned).__name__, "verification": "failed"}
        )
    return record


def analytic_control(name, callback):
    """Keep unexpected failures of analytically specified boundary controls too."""
    record = {"case": name}
    try:
        record.update(callback())
        record["verification"] = "passed"
    except Exception as error:  # noqa: BLE001 - retain every failed resource control.
        record.update(
            {"verification": "failed", "exception": type(error).__name__, "message": str(error)}
        )
    return record


def resource_controls():
    controls = []
    for name, value in [
        ("float", 0.1),
        ("boolean", True),
        ("NaN_text", "NaN"),
        ("exponent_over_limit", "1e65"),
        ("digits_over_limit", "9" * 41),
        ("rational_over_limit", Fraction(1, 2**513)),
        ("string_over_limit", "0" * 161),
    ]:
        controls.append(
            refusal_control(
                name, lambda value=value: production.calibrate_response([node(value, 0)])
            )
        )
    for name, nodes, slopes in [
        ("empty_nodes", [], (0, None)),
        ("unknown_field", [{"input": 0, "output": [0, 1], "extra": 1}], (0, None)),
        ("reversed_band", [node(0, 2, 1)], (0, None)),
        ("negative_slope", [node(0, 0)], (-1, None)),
        ("reversed_slopes", [node(0, 0)], (2, 1)),
        ("float_slope", [node(0, 0)], (0, 0.5)),
    ]:
        controls.append(
            refusal_control(
                name,
                lambda nodes=nodes, slopes=slopes: production.calibrate_response(
                    nodes, slope_bounds=slopes
                ),
            )
        )
    consumed = []

    def too_many_nodes():
        for index in range(1025):
            consumed.append(index)
            yield node(0, 0, 1)

    count = refusal_control(
        "node_cap_1025", lambda: production.calibrate_response(too_many_nodes()), "count"
    )
    count["consumed_nodes"] = len(consumed)
    if len(consumed) != 1025:
        count["verification"] = "failed"
        count["consumption_failure"] = "unexpected iterable consumption at count limit"
    controls.append(count)
    controls.append(
        refusal_control(
            "finite_work_cap_not_incompatibility",
            lambda: production.calibrate_response([node(2**510 + i, 0, 1) for i in range(256)]),
            "work limit",
        )
    )

    def accepted_node_cap():
        accepted = production.calibrate_response([node(0, 0, 1) for _ in range(1024)])
        require(
            accepted.status == "compatible"
            and len(accepted.nodes) == 1
            and accepted.nodes[0].source_indices == tuple(range(1024)),
            "1024-node boundary did not preserve provenance",
        )
        return {
            "status": accepted.status,
            "source_count": len(accepted.nodes[0].source_indices),
            "work": accepted.work,
        }

    controls.append(analytic_control("node_cap_1024", accepted_node_cap))

    def context_invariance():
        direct = production.calibrate_response(
            [node("0.1", "0.2", "0.4"), node("0.9", "0.8", "1.1")], slope_bounds=("0.3", "2")
        ).to_dict()
        with localcontext(Context(prec=2, Emin=-2, Emax=2, clamp=1)):
            hostile = production.calibrate_response(
                [node("0.1", "0.2", "0.4"), node("0.9", "0.8", "1.1")],
                slope_bounds=("0.3", "2"),
            ).to_dict()
        require(direct == hostile, "Decimal context changed exact calibration")
        return {"status": direct["status"]}

    controls.append(analytic_control("hostile_decimal_context", context_invariance))
    for name, value in [
        ("rational_512_bit_boundary", 2**511),
        ("decimal_40_digit_boundary", "9" * 40),
        ("string_160_character_boundary", "0" * 160),
    ]:

        def accepted_number(value=value):
            accepted = production.calibrate_response([node(value, 0, 1)])
            expected = rational(value)
            require(
                accepted.status == "compatible"
                and len(accepted.nodes) == 1
                and accepted.nodes[0].input == expected
                and (accepted.nodes[0].lower, accepted.nodes[0].upper) == (0, 1),
                "valid numeric boundary changed its mathematical input",
            )
            return {"status": accepted.status, "exact_input": expected}

        controls.append(analytic_control(name, accepted_number))
    return controls


def source_hashes():
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_PATHS
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path, help="new .json destination; existing files refused"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a fresh JSON path")
    if args.output.suffix.lower() != ".json":
        parser.error("output must have a .json suffix")
    before, started = source_hashes(), time.perf_counter()
    declared, paired, seeded = named_cases(), paired_cases(), seeded_cases()
    records = [check_case(*case, category="named") for case in declared]
    records.extend(check_case(*case, category="paired") for case in paired)
    records.extend(check_case(*case, category="seeded") for case in seeded)
    records.extend(check_case(*case, category="edge_response_gauge") for case in edge_gauge_cases())
    # Independent source order and duplicate-constraint representation must preserve feasibility.
    rng = random.Random(78129)
    for name, original, slopes in [*declared, *seeded[:16]]:
        shuffled = copy.deepcopy(original)
        rng.shuffle(shuffled)
        records.append(check_case(name + "_permuted", shuffled, slopes, category="permutation"))
        duplicated = [*copy.deepcopy(original), copy.deepcopy(original[0])]
        records.append(
            check_case(name + "_duplicate_constraint", duplicated, slopes, category="duplicate")
        )
    refusals = resource_controls()
    failures = sum(record["verification"] != "passed" for record in [*records, *refusals])
    report = {
        "format": "independent-response-calibration-graph-oracle",
        "version": 1,
        "source_sha256": before,
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "runtime": {"python": platform.python_version(), "seconds": time.perf_counter() - started},
        "population": {
            "named": len(declared),
            "paired": len(paired),
            "seeded": len(seeded),
            "edge_gauge": 3,
            "permutations": len(declared) + 16,
            "duplicate_variants": len(declared) + 16,
            "mathematical_cases": len(records),
            "resource_schema_controls": len(refusals),
            "oracle_maximum_nodes": MAX_ORACLE_NODES,
            "seed": SEED,
        },
        "summary": {
            "passed": len(records) + len(refusals) - failures,
            "failed": failures,
            "compatible": sum(r.get("oracle_status") == "compatible" for r in records),
            "incompatible": sum(r.get("oracle_status") == "incompatible" for r in records),
        },
        "cases": records,
        "resource_schema_controls": refusals,
        "limits": [
            "Exact scalar inputs/output/slope bounds are supplied assumptions, not inferred or justified by this oracle.",
            "Generic graph closure uses separate variables/equality edges for original duplicate inputs and does not import production exact conversion or chain propagation.",
            "Returned query intervals are tight POINTWISE marginals; independently choosing several values does not construct one common response.",
            "A verified PL witness proves existence only, not uniqueness, real camera calibration, inversion or extrapolation.",
            "Named, paired and seeded cases are fixed development controls; no unseen evaluation, optical error bound or physical acceptance is claimed.",
            "Gaussian-edge gauge fixtures use rounded erfc values treated as exact rational stand-ins; they demonstrate conditional monotone flexibility, not certified optical probabilities.",
            "Large-node resource controls use direct analytic expectations rather than cubic graph closure; work refusal is not mathematical incompatibility.",
            "No production image correction, inferred response, altered source-noise model or CAD acceptance is introduced.",
        ],
    }
    if before != source_hashes():
        raise RuntimeError("source changed during oracle run; use a new source-frozen execution")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(json_exact(report), stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "population": report["population"],
                "summary": report["summary"],
                "seconds": report["runtime"]["seconds"],
            },
            indent=2,
        )
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
