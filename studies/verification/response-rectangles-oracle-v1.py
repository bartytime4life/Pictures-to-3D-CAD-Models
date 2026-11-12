"""Independent exact oracle for conditional uncertain-input response rectangles.

Use --output NEW_JSON. A bounded, fully retained development census compares
production with generic difference graphs and original-rectangle cone formulas,
checks common PL witnesses/rectangle assignments and source-indexed contradictions,
and distinguishes existential inputs from one curve valid for every input.
This runner reads no JSON requests and imports no production numeric conversion.
--help and output refusal do not execute the census. No camera or physical claim.
"""

import argparse
import copy
import hashlib
import itertools
import json
import platform
import random
import subprocess
import sys
import time
from collections import Counter
from decimal import Context, localcontext
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import response_rectangles as production

SEED = 260112
SEEDED_CASES = 128
MAX_RECTANGLES = 6
SOURCE_PATHS = (
    Path(__file__).resolve(),
    ROOT / "backend/response_rectangles.py",
    ROOT / "backend/response_calibration.py",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rational(value):
    """Independent fixture conversion, never the production parser."""
    if isinstance(value, (bool, float)):
        raise TypeError("oracle fixtures require exact numbers")
    return F(value)


def exact_json(value):
    if isinstance(value, F):
        return str(value.numerator) if value.denominator == 1 else str(value)
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    return value


def rectangle(a, b, low, high=None):
    return {"input": [a, b], "output": [low, low if high is None else high]}


def normalize(rectangles):
    return [tuple(rational(v) for v in (*r["input"], *r["output"])) for r in rectangles]


def original_constraints(data, mode):
    """Return independent one-sided constraints, preserving original provenance."""
    constraints = []
    for index, (a, b, low, high) in enumerate(data):
        if mode == "some":
            constraints += [(a, "upper", high, index, "left"), (b, "lower", low, index, "right")]
        elif mode == "all":
            constraints += [(a, "lower", low, index, "left"), (b, "upper", high, index, "right")]
        else:
            raise ValueError("invalid oracle mode")
    return constraints


def cone_oracle(data, slopes, mode, queries):
    """Original-rectangle all-pair cone inequalities, no chain propagation."""
    m, M = slopes
    constraints = original_constraints(data, mode)
    lows = [(x, value) for x, bound, value, _, _ in constraints if bound == "lower"]
    highs = [(x, value) for x, bound, value, _, _ in constraints if bound == "upper"]

    def lower_at(x):
        values = [
            value + (m if x >= at else M) * (x - at)
            for at, value in lows
            if x >= at or M is not None
        ]
        return max(values) if values else None

    def upper_at(x):
        values = [
            value + (m if x <= at else M) * (x - at)
            for at, value in highs
            if x <= at or M is not None
        ]
        return min(values) if values else None

    for x, upper in highs:
        implied = lower_at(x)
        if implied is not None and implied > upper:
            return None
    return {x: (lower_at(x), upper_at(x)) for x in queries}


def graph_oracle(data, slopes, mode, queries):
    """Generic closure on distinct ORIGINAL endpoint variables plus query nodes.

    Duplicate coordinates retain separate variables with equality edges. Node0 is
    fixed zero; d[i][j] bounds value_j-value_i. Every coordinate pair gets slope
    edges, independently of the production endpoint grouping/chain algorithm.
    None is a missing graph path, hence an honestly unbounded marginal side.
    """
    require(0 < len(data) <= MAX_RECTANGLES, "oracle rectangle population exceeds its cap")
    constraints = original_constraints(data, mode)
    coordinates = [c[0] for c in constraints] + list(queries)
    size = len(coordinates) + 1
    distance = [[None] * size for _ in range(size)]
    for i in range(size):
        distance[i][i] = F(0)

    def edge(i, j, value):
        if distance[i][j] is None or value < distance[i][j]:
            distance[i][j] = value

    for index, (_, bound, value, _, _) in enumerate(constraints, 1):
        edge(index, 0, -value) if bound == "lower" else edge(0, index, value)
    m, M = slopes
    for i, x in enumerate(coordinates, 1):
        for j, y in enumerate(coordinates, 1):
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
    if any(distance[i][i] < 0 for i in range(size)):
        return None
    bands = {}
    for i, x in enumerate(coordinates, 1):
        lower = None if distance[i][0] is None else -distance[i][0]
        interval = lower, distance[0][i]
        if x in bands:
            require(bands[x] == interval, "graph duplicate equality failed")
        bands[x] = interval
    return bands


def fixed_slope_oracle(data, slope, mode, queries):
    """For f(x)=s*x+c, intersect original rectangle intercept intervals."""
    if mode == "some":
        low = max(L - slope * b for a, b, L, U in data)
        high = min(U - slope * a for a, b, L, U in data)
    else:
        low = max(L - slope * a for a, b, L, U in data)
        high = min(U - slope * b for a, b, L, U in data)
    if low > high:
        return None
    return {x: (slope * x + low, slope * x + high) for x in queries}


def fixed_output_input_oracle(data, slopes):
    """Independent original-variable graph for some-input exact-output fixtures.

    Vertices are the unknown chosen INPUTS, not response endpoint values. For
    y_i<y_j, finite positive M requires x_j-x_i>=(y_j-y_i)/M; positive m also
    requires x_j-x_i<=(y_j-y_i)/m. Equal outputs require equal inputs only when
    m>0. This finite-M subset avoids strict-inequality numerical conventions.
    """
    m, M = slopes
    require(
        M is not None and all(low == high for _, _, low, high in data),
        "invalid fixed-output oracle subset",
    )
    if M == 0:
        return len({low for _, _, low, _ in data}) == 1
    size = len(data) + 1
    distance = [[None] * size for _ in range(size)]
    for index in range(size):
        distance[index][index] = F(0)

    def edge(i, j, value):
        if distance[i][j] is None or value < distance[i][j]:
            distance[i][j] = value

    for index, (a, b, _, _) in enumerate(data, 1):
        edge(index, 0, -a)
        edge(0, index, b)
    for i, (_, _, yi, _) in enumerate(data, 1):
        for j, (_, _, yj, _) in enumerate(data, 1):
            if yi < yj:
                edge(j, i, -(yj - yi) / M)
                if m > 0:
                    edge(i, j, (yj - yi) / m)
            elif yi == yj and m > 0:
                edge(i, j, F(0))
    for via in range(size):
        for i in range(size):
            if distance[i][via] is None:
                continue
            for j in range(size):
                if distance[via][j] is not None:
                    edge(i, j, distance[i][via] + distance[via][j])
    return all(distance[i][i] >= 0 for i in range(size))


def expected_groups(data, mode):
    constraints = original_constraints(data, mode)
    groups = []
    for x in sorted({c[0] for c in constraints}):
        at = [c for c in constraints if c[0] == x]
        lows = [c[2] for c in at if c[1] == "lower"]
        highs = [c[2] for c in at if c[1] == "upper"]
        provenance = sorted((c[3], c[4], c[1], c[2]) for c in at)
        groups.append(
            (
                x,
                max(lows) if lows else None,
                min(highs) if highs else None,
                tuple(sorted({c[3] for c in at})),
                provenance,
            )
        )
    return groups


def group_signature(groups):
    return [
        (
            g.input,
            g.lower,
            g.upper,
            tuple(g.source_indices),
            sorted((c.source_index, c.endpoint, c.bound, c.value) for c in g.endpoint_constraints),
        )
        for g in groups
    ]


def interpolate(witness, x):
    points = [(p.input, p.output) for p in witness]
    require(points[0][0] <= x <= points[-1][0], "assignment lies outside witness domain")
    for at, value in points:
        if x == at:
            return value
    for (a, low), (b, high) in itertools.pairwise(points):
        if a < x < b:
            return low + (high - low) * (x - a) / (b - a)
    raise AssertionError("witness interpolation did not cover assignment")


def witness_checks(result, data, slopes, mode, graph):
    endpoints = sorted({x for a, b, _, _ in data for x in (a, b)})
    require(
        [p.input for p in result.witness] == endpoints, "shared witness omits/reorders endpoints"
    )
    m, M = slopes
    for point in result.witness:
        low, high = graph[point.input]
        require(low is None or low <= point.output, "witness violates lower envelope")
        require(high is None or point.output <= high, "witness violates upper envelope")
        require(isinstance(point.output, F), "witness output is not exact rational")
    for left, right in itertools.combinations(result.witness, 2):
        delta, change = right.input - left.input, right.output - left.output
        require(m * delta <= change, "shared witness violates lower slope")
        require(M is None or change <= M * delta, "shared witness violates upper slope")
    require(
        [a.source_index for a in result.assignments] == list(range(len(data))),
        "assignments lose original source order",
    )
    for assignment, (a, b, low, high) in zip(result.assignments, data, strict=True):
        require(
            isinstance(assignment.input, F) and isinstance(assignment.output, F),
            "assignment coordinates are not exact rational",
        )
        fa, fb = interpolate(result.witness, a), interpolate(result.witness, b)
        require(
            tuple(assignment.endpoint_outputs) == (fa, fb),
            "assignment endpoint outputs differ from common curve",
        )
        require(
            a <= assignment.input <= b and low <= assignment.output <= high,
            "assignment misses original rectangle",
        )
        require(
            interpolate(result.witness, assignment.input) == assignment.output,
            "assignment is not on common PL witness",
        )
        if mode == "some":
            require(fa <= high and fb >= low, "existential rectangle endpoint conditions fail")
        else:
            require(low <= fa <= fb <= high, "common curve does not fit every allowed input")


def contradiction_checks(result, data, slopes, mode):
    proof = result.contradiction
    require(
        proof is not None and not result.nodes and not result.witness and not result.assignments,
        "incompatibility lacks a proof or exposes a witness",
    )
    require(
        type(proof.lower_source) is int and type(proof.upper_source) is int,
        "proof indices are not exact integers",
    )
    require(
        0 <= proof.lower_source < len(data) and 0 <= proof.upper_source < len(data),
        "proof points outside original sources",
    )
    constraints = original_constraints(data, mode)
    low_sources = [
        c
        for c in constraints
        if c[1] == "lower" and c[3] == proof.lower_source and c[4] == proof.lower_endpoint
    ]
    high_sources = [
        c
        for c in constraints
        if c[1] == "upper" and c[3] == proof.upper_source and c[4] == proof.upper_endpoint
    ]
    require(
        len(low_sources) == len(high_sources) == 1,
        "proof endpoint/bound is not an original constraint",
    )
    xl, _, low, _, _ = low_sources[0]
    xu, _, high, _, _ = high_sources[0]
    at, (m, M) = proof.at_input, slopes
    domain = [x for a, b, _, _ in data for x in (a, b)]
    require(min(domain) <= at <= max(domain), "proof leaves declared input domain")
    require(at >= xl or M is not None, "lower proof uses omitted backward upper slope")
    require(at <= xu or M is not None, "upper proof uses omitted forward upper slope")
    derived_low = low + (m if at >= xl else M) * (at - xl)
    derived_high = high + (m if at <= xu else M) * (at - xu)
    require(
        (derived_low, derived_high) == (proof.implied_lower, proof.implied_upper),
        "proof is not implied by original bound cones",
    )
    require(derived_low > derived_high, "contradiction is not strict")


def check_case(name, rectangles, slopes=(0, None), *, mode="some", category="named"):
    data = normalize(rectangles)
    slopes = rational(slopes[0]), None if slopes[1] is None else rational(slopes[1])
    endpoints = sorted({x for a, b, _, _ in data for x in (a, b)})
    queries = sorted({endpoints[0], endpoints[-1], (endpoints[0] + endpoints[-1]) / 2})
    record = {
        "case": name,
        "category": category,
        "input_mode": mode,
        "rectangles": data,
        "slope_bounds": slopes,
    }
    try:
        graph = graph_oracle(data, slopes, mode, queries)
        cones = cone_oracle(data, slopes, mode, sorted(set(endpoints + queries)))
        require(graph == cones, "generic graph and original-rectangle cone oracles disagree")
        if (
            mode == "some"
            and slopes[1] is not None
            and all(low == high for _, _, low, high in data)
        ):
            require(
                fixed_output_input_oracle(data, slopes) == (graph is not None),
                "original fixed-output chosen-input oracle disagrees",
            )
            record["original_fixed_output_input_graph_checked"] = True
        if slopes[0] == slopes[1]:
            analytic = fixed_slope_oracle(data, slopes[0], mode, sorted(set(endpoints + queries)))
            require(graph == analytic, "original fixed-slope intercept oracle disagrees")
            record["fixed_slope_intercept_checked"] = True
        result = production.calibrate_rectangles(rectangles, slope_bounds=slopes, input_mode=mode)
        record.update(
            {
                "oracle_status": "compatible" if graph is not None else "incompatible",
                "production": result.to_dict(),
            }
        )
        json.dumps(record["production"], allow_nan=False)
        require(result.status == record["oracle_status"], "production/oracle status differs")
        require(
            result.input_mode == mode and result.slope_bounds == slopes,
            "reported conditions changed",
        )
        require(
            [(tuple(r.input), tuple(r.output)) for r in result.rectangles]
            == [((a, b), (low, high)) for a, b, low, high in data],
            "normalized original rectangles changed",
        )
        require(
            group_signature(result.source_groups) == expected_groups(data, mode),
            "source groups lose bounds/provenance",
        )
        if graph is None:
            contradiction_checks(result, data, slopes, mode)
            try:
                result.query(queries[0])
            except ValueError:
                record["incompatible_query_refused"] = True
            else:
                raise AssertionError("incompatible result allowed a query")
        else:
            require(result.contradiction is None, "compatible result has a contradiction")
            expected = [(x, *graph[x]) for x in endpoints]
            require(
                [(g.input, g.lower, g.upper) for g in result.nodes] == expected,
                "tight endpoint marginals differ",
            )
            witness_checks(result, data, slopes, mode, graph)
            query_records = []
            for x in queries:
                actual = result.query(x)
                require((actual.lower, actual.upper) == graph[x], "tight query interval differs")
                query_records.append(
                    {
                        "input": x,
                        "oracle_interval": graph[x],
                        "production_interval": [actual.lower, actual.upper],
                    }
                )
            record["queries"] = query_records
            for outside in (endpoints[0] - 1, endpoints[-1] + 1):
                try:
                    result.query(outside)
                except ValueError:
                    pass
                else:
                    raise AssertionError("query extrapolated outside declared domain")
            record["outside_queries_refused"] = True
        record["verification"] = "passed"
    except Exception as error:  # noqa: BLE001 - retain failures and continue the declared census.
        record.update(
            {
                "verification": "failed",
                "failure": {"type": type(error).__name__, "message": str(error)},
            }
        )
    return record


def named_cases():
    tiny = F(1, 10**40)
    return [
        ("unbounded_midpoint", [rectangle(0, 1, 0)], (0, None)),
        ("finite_upper_midpoint", [rectangle(0, 1, 0)], (0, 2)),
        ("same_range_distinct_hits", [rectangle(0, 1, 0), rectangle(0, 1, 1)], (0, 1)),
        ("same_range_insufficient_slope", [rectangle(0, 1, 0), rectangle(0, 1, 1)], (0, F(1, 2))),
        (
            "shared_offset_box_relaxation",
            [rectangle(0, 0, 0), rectangle(0, 1, 0), rectangle(1, 2, 2)],
            (1, 1),
        ),
        ("anchored_identity_some_not_all", [rectangle(0, 0, 0), rectangle(0, 1, F(1, 2))], (1, 1)),
        ("touching_closed_endpoint", [rectangle(-1, 0, 0), rectangle(0, 1, 1)], (0, None)),
        ("point_duplicate_contact", [rectangle(0, 0, 0, 1), rectangle(0, 0, 1, 2)], (0, None)),
        ("point_duplicate_conflict", [rectangle(0, 0, 0), rectangle(0, 0, 1)], (0, None)),
        (
            "negative_coordinates_outputs",
            [rectangle(-3, -1, -4, -2), rectangle(-2, 1, -1, 2)],
            (F(1, 2), 2),
        ),
        ("constant_intersection", [rectangle(-2, 1, -1, 2), rectangle(0, 4, 1, 3)], (0, 0)),
        ("constant_conflict", [rectangle(-2, 1, -1, 0), rectangle(0, 4, 1, 3)], (0, 0)),
        ("strict_lower_plateau", [rectangle(0, 0, 0), rectangle(1, 1, 0)], (F(1, 10), None)),
        ("finite_slope_closed_boundary", [rectangle(0, 0, 0), rectangle(1, 1, 2)], (0, 2)),
        ("one_point_domain", [rectangle(2, 2, -3, 4)], (2, 3)),
        ("tiny_exact_input_gap", [rectangle(1, 1, 0), rectangle(1 + tiny, 1 + tiny, tiny)], (1, 1)),
        (
            "nested_unordered_rectangles",
            [rectangle(1, 2, 1, 2), rectangle(-1, 3, 0, 4), rectangle(0, 1, 0, 1)],
            (0, 3),
        ),
        ("lower_slope_unknown_upper", [rectangle(0, 1, 2, 3), rectangle(2, 3, 1, 4)], (1, None)),
    ]


def seeded_cases():
    rng = random.Random(SEED)
    cases = []
    for index in range(SEEDED_CASES):
        rectangles = []
        for _ in range(1 + index % 5):
            a = F(rng.randrange(-8, 9), 4)
            b = a + F(rng.randrange(9), 4)
            low = F(rng.randrange(-12, 13), 4)
            rectangles.append(rectangle(a, b, low, low + F(rng.randrange(9), 4)))
        m = rng.choice([F(0), F(1, 2), F(1)])
        M = None if index % 3 == 0 else m + rng.choice([F(0), F(1, 2), F(2)])
        cases.append((f"seeded_{index:03d}", rectangles, (m, M)))
    return cases


def fixed_output_cases():
    rng = random.Random(SEED + 2)
    cases = []
    for index in range(16):
        rectangles = []
        for _ in range(1 + index % 5):
            a = F(rng.randrange(-8, 9), 4)
            rectangles.append(rectangle(a, a + F(rng.randrange(9), 4), F(rng.randrange(-8, 9), 4)))
        m = rng.choice([F(0), F(1, 2), F(1)])
        cases.append(
            (f"fixed_outputs_{index:02d}", rectangles, (m, m + rng.choice([F(0), F(1, 2), F(2)])))
        )
    return cases


def control(name, callback, *, refuses=False):
    record = {"case": name}
    try:
        details = callback()
        require(not refuses, "invalid input unexpectedly accepted")
        if details is not None:
            record["details"] = details
        record["verification"] = "passed"
    except (TypeError, ValueError) as error:
        record.update(
            {
                "verification": "passed" if refuses else "failed",
                "exception": type(error).__name__,
                "message": str(error),
            }
        )
    except Exception as error:  # noqa: BLE001 - retain all control failures too.
        record.update(
            {"verification": "failed", "exception": type(error).__name__, "message": str(error)}
        )
    return record


def schema_controls():
    cases = [
        ("empty", [], (0, None), "some"),
        ("unknown_field", [{"input": [0, 1], "output": [0, 1], "extra": 1}], (0, None), "some"),
        ("reversed_input", [rectangle(1, 0, 0)], (0, None), "some"),
        ("reversed_output", [rectangle(0, 1, 1, 0)], (0, None), "some"),
        ("float_input", [rectangle(0, 0.5, 0)], (0, None), "some"),
        ("boolean_output", [rectangle(0, 1, True)], (0, None), "some"),
        ("nonfinite_text", [rectangle("NaN", 1, 0)], (0, None), "some"),
        ("decimal_digits", [rectangle("9" * 41, "9" * 41, 0)], (0, None), "some"),
        ("rational_bits", [rectangle(F(1, 2**513), 1, 0)], (0, None), "some"),
        ("negative_lower", [rectangle(0, 1, 0)], (-1, None), "some"),
        ("reversed_slopes", [rectangle(0, 1, 0)], (2, 1), "some"),
        ("float_upper", [rectangle(0, 1, 0)], (0, 0.5), "some"),
        ("unknown_mode", [rectangle(0, 1, 0)], (0, None), "robust"),
    ]
    return [
        control(
            name,
            lambda rs=rs, slopes=slopes, mode=mode: production.calibrate_rectangles(
                rs, slope_bounds=slopes, input_mode=mode
            ),
            refuses=True,
        )
        for name, rs, slopes, mode in cases
    ]


def context_control():
    fixtures = [rectangle("0.1", "0.4", "0.2", "0.8"), rectangle("0.8", "1.1", "0.7", "1.3")]
    for mode in ("some", "all"):
        direct = production.calibrate_rectangles(
            fixtures, slope_bounds=("0.3", "2"), input_mode=mode
        ).to_dict()
        with localcontext(Context(prec=2, Emin=-2, Emax=2, clamp=1)):
            hostile = production.calibrate_rectangles(
                fixtures, slope_bounds=("0.3", "2"), input_mode=mode
            ).to_dict()
        require(direct == hostile, "global Decimal context changed exact analysis")
    return {"input_modes_checked": ["some", "all"]}


def accepted_count_control():
    count = 512
    rows = [rectangle(0, 1, 0, 1) for _ in range(count)]
    for mode in ("some", "all"):
        result = production.calibrate_rectangles(rows, input_mode=mode)
        require(
            result.status == "compatible" and len(result.rectangles) == count,
            "valid count boundary failed",
        )
        require(
            len(result.nodes) == 2
            and all(tuple(g.source_indices) == tuple(range(count)) for g in result.source_groups),
            "count boundary loses original provenance",
        )
    return {"rectangles_per_mode": count, "input_modes_checked": ["some", "all"]}


def refused_count_control():
    consumed = []

    def generator():
        for index in range(513):
            consumed.append(index)
            yield rectangle(0, 1, 0, 1)

    try:
        production.calibrate_rectangles(generator())
    except ValueError:
        require(len(consumed) == 513, "unexpected generator consumption at count refusal")
        return {"consumed": len(consumed), "refused_as_invalid_not_incompatible": True}
    raise AssertionError("oversized rectangle population accepted")


def quantifier_controls(records):
    by_name = {(r["case"], r["input_mode"]): r for r in records}
    for name in (
        "same_range_distinct_hits",
        "shared_offset_box_relaxation",
        "anchored_identity_some_not_all",
    ):
        require(
            by_name[name, "some"].get("oracle_status") == "compatible",
            "named existential control failed",
        )
        require(
            by_name[name, "all"].get("oracle_status") == "incompatible",
            "named common-curve universal control failed",
        )
    # f(x)=x is fixed by slope1 and (0,0). Shared offset would require
    # x_1=delta=0 and x_2=1+delta=2, impossible for one delta.
    require(F(0) != F(2) - 1, "shared offset counterexample lost")
    # For one common uncertain input, f(x)=0 and f(x)=1 cannot both hold.
    require(F(0) != F(1), "common-input counterexample lost")
    return {
        "shared_offset_required_values": [F(0), F(1)],
        "correlated_model": "incompatible analytically; independent rectangle relaxation compatible",
        "quantifier": "all means exists one curve for every allowed input, not a new curve per assignment",
    }


def source_hashes():
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE_PATHS
    }


def run_oracle():
    before, started = source_hashes(), time.perf_counter()
    named, seeded = named_cases(), seeded_cases()
    records = [
        check_case(*case, mode=mode, category=category)
        for category, cases in (("named", named), ("seeded", seeded))
        for case in cases
        for mode in ("some", "all")
    ]
    fixed_outputs = fixed_output_cases()
    records.extend(
        check_case(*case, mode="some", category="original_fixed_output_inputs")
        for case in fixed_outputs
    )
    rng = random.Random(SEED + 1)
    variants = [*named[:8], *seeded[:8]]
    for name, original, slopes in variants:
        shuffled = copy.deepcopy(original)
        rng.shuffle(shuffled)
        duplicate = [*copy.deepcopy(original), copy.deepcopy(original[0])]
        for mode in ("some", "all"):
            records.append(
                check_case(name + "_permuted", shuffled, slopes, mode=mode, category="permutation")
            )
            records.append(
                check_case(name + "_duplicate", duplicate, slopes, mode=mode, category="duplicate")
            )
    controls = schema_controls()
    controls.append(control("hostile_decimal_context", context_control))
    controls.append(control("accepted_rectangle_count_512", accepted_count_control))
    controls.append(control("refused_rectangle_count_513", refused_count_control))
    controls.append(
        control("quantifier_and_correlation_limits", lambda: quantifier_controls(records))
    )
    after = source_hashes()
    controls.append(
        control(
            "source_unchanged", lambda: require(before == after, "source changed during oracle run")
        )
    )
    failures = sum(r["verification"] != "passed" for r in [*records, *controls])
    statuses = Counter(r.get("oracle_status", "unavailable") for r in records)
    return {
        "format": "independent-response-rectangles-oracle",
        "version": 1,
        "verification": "failed" if failures else "passed",
        "source_sha256_before": before,
        "source_sha256_after": after,
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "runtime": {"python": platform.python_version(), "seconds": time.perf_counter() - started},
        "population": {
            "named_per_mode": len(named),
            "seeded_per_mode": len(seeded),
            "permutations_per_mode": len(variants),
            "duplicates_per_mode": len(variants),
            "original_fixed_output_input_cases": len(fixed_outputs),
            "mathematical_cases": len(records),
            "controls": len(controls),
            "seed": SEED,
            "oracle_maximum_rectangles": MAX_RECTANGLES,
        },
        "summary": {
            "passed": len(records) + len(controls) - failures,
            "failed": failures,
            "compatible": statuses["compatible"],
            "incompatible": statuses["incompatible"],
            "oracle_unavailable": statuses["unavailable"],
            "by_input_mode": {
                mode: {
                    "cases": sum(r["input_mode"] == mode for r in records),
                    "compatible": sum(
                        r["input_mode"] == mode and r.get("oracle_status") == "compatible"
                        for r in records
                    ),
                    "incompatible": sum(
                        r["input_mode"] == mode and r.get("oracle_status") == "incompatible"
                        for r in records
                    ),
                }
                for mode in ("some", "all")
            },
            "original_fixed_output_input_graph_checks": sum(
                r.get("original_fixed_output_input_graph_checked", False) for r in records
            ),
            "fixed_slope_intercept_checks": sum(
                r.get("fixed_slope_intercept_checked", False) for r in records
            ),
        },
        "cases": records,
        "controls": controls,
        "limits": [
            "Finite independent closed input/output rectangles and shared slope bounds are supplied assumptions; correlated input/output errors, shared gain/offset and spatial response functions are not represented.",
            "some means there exists one curve and one independently chosen point per rectangle. all means there exists one curve whose output is in the supplied band at every allowed input; it is not for every assignment there exists a newly fitted curve.",
            "Generic all-pair difference graphs retain separate original endpoint variables/equality edges. Original rectangle cone and fixed-slope intercept oracles do not use production parsing or propagation.",
            "The finite-upper-slope exact-output subset additionally checks original unknown chosen input variables against reciprocal secant bounds, independently of endpoint reduction.",
            "Null lower/upper envelope sides denote genuine minus/plus infinity respectively; no arbitrary finite truncation is introduced.",
            "Query envelopes are tight pointwise marginals. Independent choices from several query bands need not belong to one common response.",
            "A finite continuous PL witness demonstrates conditional existence only, not uniqueness, inferred camera response, inversion, extrapolation, physical optical bounds or CAD acceptance.",
            "All fixtures are declared development controls, including incompatible/failed cases; there is no unseen or physical evaluation and no image/noise-model correction.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new .json destination; existing files/symlinks refused",
    )
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("output already exists; preserve it and choose a fresh JSON path")
    if args.output.suffix.lower() != ".json":
        parser.error("output must have a .json suffix")
    report = run_oracle()
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
