"""Exact common-response feasibility, independent witnesses and finite resources."""

import itertools
import json
import random
from decimal import Context, localcontext
from fractions import Fraction as F

import pytest

from backend import response_calibration as response


def node(x, low, high=None):
    return response.ResponseNode(x, (low, low if high is None else high))


def assert_witness(result):
    assert result.status == "compatible"
    low, high = result.slope_bounds
    for band, point in zip(result.nodes, result.witness):
        assert band.input == point.input
        assert band.lower <= point.output <= band.upper
    for left, right in zip(result.witness, result.witness[1:]):
        delta = right.input - left.input
        assert low * delta <= right.output - left.output
        assert high is None or right.output - left.output <= high * delta


def test_duplicate_knots_share_one_intersection_and_keep_provenance():
    result = response.calibrate_response(
        [node("1", "0.2", "0.3"), node("1.0", "0.25", "0.4"), node(0, 0)]
    )
    assert_witness(result)
    assert len(result.nodes) == 2
    assert result.nodes[1].lower == F(1, 4) and result.nodes[1].upper == F(3, 10)
    assert result.nodes[1].source_indices == (0, 1)


def test_duplicate_conflict_has_strict_exact_certificate():
    result = response.calibrate_response(
        [node(1, "0.2", "0.3"), node(1, "0.30000000000000000001", "0.4")]
    )
    proof = result.contradiction
    assert result.status == "incompatible" and result.nodes == () and result.witness == ()
    assert proof.kind == "duplicate_input"
    assert (proof.lower_source, proof.upper_source) == (1, 0)
    assert proof.implied_lower > proof.implied_upper


def test_closed_boundary_contact_is_feasible():
    result = response.calibrate_response([node(0, 0), node(1, 1)], slope_bounds=(1, 1))
    assert_witness(result)
    assert result.query(F(1, 3)) == response.ResponseInterval(F(1, 3), F(1, 3))
    assert result.to_dict()["witness"][1]["output"] == "1"


def test_forward_backward_bands_are_tight_and_witness_is_common():
    result = response.calibrate_response(
        [node(0, 0, 1), node(1, 0, 1), node(2, 1)], slope_bounds=(0, "0.25")
    )
    assert [b.lower for b in result.nodes] == [F(1, 2), F(3, 4), F(1)]
    assert [b.upper for b in result.nodes] == [F(1), F(1), F(1)]
    assert [p.output for p in result.witness] == [F(1, 2), F(3, 4), F(1)]
    assert_witness(result)
    # Individually reachable marginal values need not form one feasible curve.
    assert result.nodes[0].upper > result.nodes[1].lower


@pytest.mark.parametrize("slopes", [(0, "0.4"), ("0.6", None)])
def test_finite_upper_and_positive_lower_can_each_exclude(slopes):
    result = response.calibrate_response([node(0, 0), node(2, 1)], slope_bounds=slopes)
    assert result.status == "incompatible"
    assert result.contradiction.implied_lower > result.contradiction.implied_upper


def test_monotonicity_contradiction_keeps_original_source_indices():
    result = response.calibrate_response([node(2, "0.1", "0.2"), node(0, "0.8", "0.9")])
    assert result.status == "incompatible"
    proof = result.contradiction
    assert proof.lower_source == 1 and proof.upper_source == 0
    assert (proof.implied_lower, proof.implied_upper) == (F(4, 5), F(1, 5))


def test_tight_query_envelope_differs_from_one_linear_witness():
    result = response.calibrate_response([node(0, 0), node(1, 1)], slope_bounds=(0, 2))
    assert result.query(F(1, 4)) == response.ResponseInterval(F(0), F(1, 2))
    assert result.query(F(3, 4)) == response.ResponseInterval(F(1, 2), F(1))
    assert [p.output for p in result.witness] == [0, 1]


def test_common_observations_cannot_use_independent_query_choices():
    calibration = response.calibrate_response([node(0, 0), node(1, 1)])
    assert calibration.query("0.4") == response.ResponseInterval(0, 1)
    assert calibration.query("0.6") == response.ResponseInterval(0, 1)
    joint = response.calibrate_response(
        [node(0, 0), node(1, 1), node("0.4", "0.8", "0.9"), node("0.6", "0.1", "0.2")]
    )
    assert joint.status == "incompatible"


def test_nearby_exact_knots_are_not_tolerance_merged():
    result = response.calibrate_response([node(0, 0), node("1e-40", "1e-30")], slope_bounds=(0, 1))
    assert len(result.source_groups) == 2
    assert result.status == "incompatible"
    assert result.contradiction.implied_upper == F(1, 10**40)


def test_fraction_inputs_and_exact_serialization_have_no_float_rounding():
    result = response.calibrate_response([node(F(1, 3), F(-1, 7)), node(F(2, 3), F(2, 7))])
    payload = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    assert payload["nodes"][0]["input"] == "1/3"
    assert payload["nodes"][0]["output"] == ["-1/7", "-1/7"]
    assert_witness(result)


def test_decimal_context_cannot_change_exact_calculation():
    nodes = [node("0.1", "0.2", "0.4"), node("0.9", "0.8", "1.1")]
    expected = response.calibrate_response(nodes, slope_bounds=("0.3", "2")).to_dict()
    with localcontext(Context(prec=2, Emin=-2, Emax=2, clamp=1)):
        actual = response.calibrate_response(nodes, slope_bounds=("0.3", "2")).to_dict()
    assert actual == expected


def test_one_knot_has_only_a_point_domain_and_no_extrapolation():
    result = response.calibrate_response([node(2, -3, 4)], slope_bounds=(2, 3))
    assert result.query(2) == response.ResponseInterval(-3, 4)
    with pytest.raises(ValueError, match="outside"):
        result.query("2.0000000000001")
    bad = response.calibrate_response([node(0, 1), node(0, 2)])
    with pytest.raises(ValueError, match="incompatible"):
        bad.query(0)


def test_random_chain_marginals_match_independent_exhaustive_integer_oracle():
    rng = random.Random(39017)
    choices = list(itertools.product(range(5), repeat=3))
    for _ in range(60):
        bands = [sorted(rng.sample(range(5), 2)) for _ in range(3)]
        lower, upper = rng.choice([(0, 0), (0, 1), (0, 2), (1, 2)])
        feasible = [
            ys
            for ys in choices
            if all(a <= y <= b for y, (a, b) in zip(ys, bands))
            and all(lower <= b - a <= upper for a, b in itertools.pairwise(ys))
        ]
        result = response.calibrate_response(
            [node(i, *bounds) for i, bounds in enumerate(bands)], slope_bounds=(lower, upper)
        )
        # Chain difference constraints have integer vertices for these integer data.
        if not feasible:
            assert result.status == "incompatible"
            assert result.contradiction.implied_lower > result.contradiction.implied_upper
        else:
            assert_witness(result)
            assert [b.lower for b in result.nodes] == [
                min(y[i] for y in feasible) for i in range(3)
            ]
            assert [b.upper for b in result.nodes] == [
                max(y[i] for y in feasible) for i in range(3)
            ]


def test_query_matches_an_inserted_free_knot_marginal():
    nodes = [node(0, 0, 1), node(1, "0.3", "0.9"), node(2, 1, "1.2")]
    result = response.calibrate_response(nodes, slope_bounds=("0.2", "0.8"))
    for query in [F(1, 4), F(3, 4), F(5, 4), F(7, 4)]:
        inserted = response.calibrate_response(
            [*nodes, node(query, -10, 10)], slope_bounds=("0.2", "0.8")
        )
        marginal = next(b for b in inserted.nodes if b.input == query)
        assert result.query(query) == response.ResponseInterval(marginal.lower, marginal.upper)


@pytest.mark.parametrize(
    "value",
    [True, 0.1, float("nan"), "NaN", "Infinity", "1e999", "1e-999", "1" * 41, F(1, 2**513), 2**513],
)
def test_inexact_invalid_and_resource_numbers_are_refused(value):
    with pytest.raises((ValueError, TypeError)):
        response.calibrate_response([node(value, 0)])


def test_invalid_schema_and_slope_configuration_are_refused():
    for nodes, slopes in [
        ([], (0, None)),
        ([{"input": 0, "output": [0, 1], "extra": 1}], (0, None)),
        ([node(0, 2, 1)], (0, None)),
        ([node(0, 0)], (-1, None)),
        ([node(0, 0)], (2, 1)),
        ([node(0, 0)], (0, 0.5)),
    ]:
        with pytest.raises((ValueError, TypeError)):
            response.calibrate_response(nodes, slope_bounds=slopes)


def test_count_and_arithmetic_budgets_refuse_without_partial_conclusions(monkeypatch):
    with pytest.raises(ValueError, match="count"):
        response.calibrate_response(node(i, 0, 1) for i in range(response.MAX_NODES + 1))
    monkeypatch.setattr(response, "MAX_WORK", 1)
    with pytest.raises(ValueError, match="work limit"):
        response.calibrate_response([node(0, 1), node(0, 0)])


def test_fractional_bands_match_independent_exact_polytope_vertices():
    def solve(rows, rhs):
        augmented = [list(row) + [value] for row, value in zip(rows, rhs)]
        for col in range(3):
            pivot = next((r for r in range(col, 3) if augmented[r][col]), None)
            if pivot is None:
                return None
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
            divisor = augmented[col][col]
            augmented[col] = [value / divisor for value in augmented[col]]
            for r in range(3):
                if r != col:
                    multiplier = augmented[r][col]
                    augmented[r] = [
                        a - multiplier * b for a, b in zip(augmented[r], augmented[col])
                    ]
        return tuple(row[-1] for row in augmented)

    xs = [F(-2, 3), F(1, 7), F(8, 5)]
    for bounds, slopes in [
        ([(F(-1, 3), F(1, 2)), (F(1, 4), F(5, 6)), (F(1, 2), F(9, 7))], (F(1, 9), F(7, 8))),
        ([(F(0), F(1, 7)), (F(2, 3), F(3, 4)), (F(4, 5), F(6, 5))], (F(0), F(1, 3))),
        ([(F(-1), F(2, 3)), (F(-1, 2), F(5, 4)), (F(0), F(2))], (F(2, 7), F(3, 2))),
    ]:
        constraints = []
        for i, (lo, hi) in enumerate(bounds):
            unit = [F(int(j == i)) for j in range(3)]
            constraints.extend([(unit, hi), ([-v for v in unit], -lo)])
        for i in range(2):
            delta = xs[i + 1] - xs[i]
            direction = [F(int(j == i + 1) - int(j == i)) for j in range(3)]
            constraints.extend(
                [(direction, slopes[1] * delta), ([-v for v in direction], -slopes[0] * delta)]
            )
        vertices = []
        for active in itertools.combinations(constraints, 3):
            point = solve([c[0] for c in active], [c[1] for c in active])
            if point is not None and all(
                sum(a * b for a, b in zip(row, point)) <= value for row, value in constraints
            ):
                vertices.append(point)
        result = response.calibrate_response(
            [node(x, *band) for x, band in zip(xs, bounds)], slope_bounds=slopes
        )
        if not vertices:
            assert result.status == "incompatible"
        else:
            assert_witness(result)
            assert [b.lower for b in result.nodes] == [
                min(p[i] for p in vertices) for i in range(3)
            ]
            assert [b.upper for b in result.nodes] == [
                max(p[i] for p in vertices) for i in range(3)
            ]


def test_public_exact_parser_remains_available_for_incompatible_query_reports():
    result = response.calibrate_response([node(0, 1), node(0, 2)])
    assert result.status == "incompatible"
    assert response.parse_exact("0.125") == F(1, 8)
    assert response.parse_exact(F(1, 7)) == F(1, 7)
    with pytest.raises(TypeError):
        response.parse_exact(0.125)
    with pytest.raises(ValueError, match="exponent"):
        response.parse_exact("1e999")


def test_random_rational_queries_and_proofs_match_difference_constraint_oracle():
    def all_pairs(nodes, slopes):
        grouped = {}
        for x, lo, hi in nodes:
            if x in grouped:
                a, b = grouped[x]
                grouped[x] = max(a, lo), min(b, hi)
            else:
                grouped[x] = lo, hi
        xs = sorted(grouped)
        size = len(xs) + 1  # final variable is a zero/reference vertex
        reference = size - 1
        distances = [[None] * size for _ in range(size)]
        for i in range(size):
            distances[i][i] = F(0)

        def edge(left, right, bound):
            previous = distances[left][right]
            distances[left][right] = bound if previous is None else min(previous, bound)

        for i, x in enumerate(xs):
            lo, hi = grouped[x]
            edge(reference, i, hi)
            edge(i, reference, -lo)
        for i in range(len(xs) - 1):
            delta = xs[i + 1] - xs[i]
            edge(i + 1, i, -slopes[0] * delta)
            if slopes[1] is not None:
                edge(i, i + 1, slopes[1] * delta)
        for through in range(size):
            for i in range(size):
                for j in range(size):
                    if distances[i][through] is not None and distances[through][j] is not None:
                        edge(i, j, distances[i][through] + distances[through][j])
        if any(distances[i][i] < 0 for i in range(size)):
            return None
        return {x: (-distances[i][reference], distances[reference][i]) for i, x in enumerate(xs)}

    rng = random.Random(651917)
    for _ in range(96):
        original = []
        for _ in range(rng.randrange(1, 7)):
            x = F(rng.randrange(-6, 7), rng.choice([1, 2, 3, 7]))
            a, b = sorted([F(rng.randrange(-8, 9), rng.choice([1, 2, 5])) for _ in range(2)])
            original.append((x, a, b))
        lower = rng.choice([F(0), F(1, 7), F(2, 3)])
        upper = rng.choice([None, lower, lower + F(1, 2), lower + 2])
        slopes = lower, upper
        result = response.calibrate_response(
            [node(x, lo, hi) for x, lo, hi in original], slope_bounds=slopes
        )
        oracle = all_pairs(original, slopes)
        if oracle is None:
            assert result.status == "incompatible"
            proof = result.contradiction
            lx, low, _ = original[proof.lower_source]
            ux, _, high = original[proof.upper_source]
            assert lx <= proof.at_input and ux <= proof.at_input
            assert proof.implied_lower == low + lower * (proof.at_input - lx)
            if upper is None:
                assert ux == proof.at_input
                assert proof.implied_upper == high
            else:
                assert proof.implied_upper == high + upper * (proof.at_input - ux)
            assert proof.implied_lower > proof.implied_upper
        else:
            assert_witness(result)
            assert {b.input: (b.lower, b.upper) for b in result.nodes} == oracle
            first, last = min(oracle), max(oracle)
            query = (first + last) / 2
            with_query = all_pairs([*original, (query, F(-100), F(100))], slopes)
            expected = with_query[query]
            assert result.query(query) == response.ResponseInterval(*expected)


def test_query_and_intermediate_rational_resource_exhaustion_refuse(monkeypatch):
    result = response.calibrate_response([node(0, 0), node(1, 1)], slope_bounds=(0, 2))
    monkeypatch.setattr(response, "MAX_WORK", 1)
    with pytest.raises(ValueError, match="work"):
        result.query(F(1, 2))
    monkeypatch.setattr(response, "MAX_WORK", 250_000_000)
    monkeypatch.setattr(response, "MAX_RESULT_BITS", 4)
    with pytest.raises(ValueError, match="rational-size"):
        response.calibrate_response([node(0, 0, 1), node(F(1, 3), 0, 1)], slope_bounds=(F(1, 7), 1))
