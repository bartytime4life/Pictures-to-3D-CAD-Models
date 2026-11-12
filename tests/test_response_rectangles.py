"""Independent exact rectangle feasibility, quantifiers, witnesses and resources."""

import itertools
import json
import random
from decimal import Context, localcontext
from fractions import Fraction as F

import pytest

from backend import response_rectangles as response


def rectangle(a, b, low, high=None):
    return response.ResponseRectangle((a, b), (low, low if high is None else high))


def pl_value(witness, x):
    for point in witness:
        if point.input == x:
            return point.output
    for left, right in itertools.pairwise(witness):
        if left.input < x < right.input:
            return left.output + (x - left.input) * (right.output - left.output) / (
                right.input - left.input
            )
    raise AssertionError("outside witness domain")


def assert_witness(result):
    assert result.status == "compatible"
    assert len(result.assignments) == len(result.rectangles)
    m, upper = result.slope_bounds
    for band, point in zip(result.nodes, result.witness):
        assert point.input == band.input
        assert band.lower is None or band.lower <= point.output
        assert band.upper is None or point.output <= band.upper
    for left, right in itertools.combinations(result.witness, 2):
        dx, dy = right.input - left.input, right.output - left.output
        assert m * dx <= dy
        assert upper is None or dy <= upper * dx
    for index, (r, chosen) in enumerate(zip(result.rectangles, result.assignments)):
        a, b = r.input
        low, high = r.output
        assert chosen.source_index == index
        assert a <= chosen.input <= b and low <= chosen.output <= high
        assert chosen.output == pl_value(result.witness, chosen.input)
        assert chosen.endpoint_outputs == (pl_value(result.witness, a), pl_value(result.witness, b))
        if result.input_mode == "all":
            assert low <= chosen.endpoint_outputs[0] <= chosen.endpoint_outputs[1] <= high


def assert_proof(result):
    assert result.status == "incompatible" and result.witness == result.assignments == ()
    p = result.contradiction
    lower = result.rectangles[p.lower_source]
    upper = result.rectangles[p.upper_source]
    expected = ("right", "left") if result.input_mode == "some" else ("left", "right")
    assert (p.lower_endpoint, p.upper_endpoint) == expected
    lx = lower.input[int(p.lower_endpoint == "right")]
    ux = upper.input[int(p.upper_endpoint == "right")]
    assert p.at_input >= lx and p.at_input >= ux
    m, cap = result.slope_bounds
    assert p.implied_lower == lower.output[0] + m * (p.at_input - lx)
    if cap is None:
        assert p.at_input == ux
        assert p.implied_upper == upper.output[1]
    else:
        assert p.implied_upper == upper.output[1] + cap * (p.at_input - ux)
    assert p.implied_lower > p.implied_upper


def test_some_uses_genuine_unbounded_marginals_and_finite_common_witness():
    result = response.calibrate_rectangles([rectangle(0, 1, 0, 1)])
    assert_witness(result)
    assert result.query(0) == response.RectangleResponseInterval(None, F(1))
    assert result.query(1) == response.RectangleResponseInterval(F(0), None)
    assert result.query(F(1, 3)) == response.RectangleResponseInterval(None, None)
    payload = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    assert payload["nodes"][0]["output"] == [None, "1"]
    assert payload["nodes"][1]["output"] == ["0", None]
    assert "-infinity" in payload["unbounded_semantics"]
    assert [p.output for p in result.witness] == [1, 1]


def test_all_quantifier_has_finite_bands_even_without_upper_slope():
    result = response.calibrate_rectangles([rectangle(0, 1, 0, 1)], input_mode="all")
    assert_witness(result)
    for x in (0, F(1, 3), 1):
        assert result.query(x) == response.RectangleResponseInterval(0, 1)
    assert [p.output for p in result.witness] == [0, 0]


def test_positive_lower_slope_distinguishes_existential_and_universal_input():
    rectangles = [rectangle(0, 2, 0, 1)]
    some = response.calibrate_rectangles(rectangles, slope_bounds=(1, None))
    all_inputs = response.calibrate_rectangles(rectangles, slope_bounds=(1, None), input_mode="all")
    assert_witness(some)
    assert_proof(all_inputs)
    assert all_inputs.contradiction.lower_source == all_inputs.contradiction.upper_source == 0


def test_some_assignment_recovers_exact_crossing_on_shared_pl_curve():
    result = response.calibrate_rectangles(
        [rectangle(0, 0, 0), rectangle(1, 1, F(1, 4)), rectangle(2, 2, 2), rectangle(0, 2, F(1, 2))]
    )
    assert_witness(result)
    assert result.assignments[3].input == F(8, 7)
    assert result.assignments[3].output == F(1, 2)
    assert result.assignments[3].endpoint_outputs == (0, 2)


def test_overlapping_rectangles_do_not_require_midpoint_input_order():
    result = response.calibrate_rectangles([rectangle(0, 3, 2), rectangle(1, 2, 1)])
    assert_witness(result)
    assert result.assignments[0].input > result.assignments[1].input


@pytest.mark.parametrize("mode", ["some", "all"])
def test_touching_intervals_cannot_reverse_ordered_levels(mode):
    result = response.calibrate_rectangles(
        [rectangle(0, 1, 2), rectangle(1, 2, 1)], input_mode=mode
    )
    assert_proof(result)


@pytest.mark.parametrize("mode", ["some", "all"])
def test_degenerate_intervals_and_duplicate_endpoints_preserve_sources(mode):
    result = response.calibrate_rectangles(
        [rectangle(1, 1, F(1, 4), F(1, 2)), rectangle(1, 1, F(1, 3), F(2, 3))],
        input_mode=mode,
    )
    assert_witness(result)
    assert len(result.nodes) == 1
    assert result.query(1) == response.RectangleResponseInterval(F(1, 3), F(1, 2))
    assert result.source_groups[0].source_indices == (0, 1)
    assert len(result.source_groups[0].endpoint_constraints) == 4
    with pytest.raises(ValueError, match="outside"):
        result.query(F(10000000001, 10000000000))


def test_nearby_exact_endpoints_are_not_tolerance_merged():
    result = response.calibrate_rectangles(
        [rectangle(0, 0, 0), rectangle(0, "1e-40", "1e-30")], slope_bounds=(0, 1)
    )
    assert len(result.source_groups) == 2
    assert_proof(result)
    assert result.contradiction.implied_upper == F(1, 10**40)


def test_independent_cartesian_inputs_do_not_model_one_shared_shift():
    # Independent x1 in [0,1], x2 in [1,2] can choose 0,2 for f(x)=x.
    result = response.calibrate_rectangles(
        [rectangle(0, 1, 0), rectangle(1, 2, 2)], slope_bounds=(1, 1)
    )
    assert_witness(result)
    assert [a.input for a in result.assignments] == [0, 2]
    # A shared shift x1=t,x2=t+1 would force output difference 1, not 2.
    assert result.assignments[1].output - result.assignments[0].output != 1


def test_some_endpoint_feasibility_does_not_validate_an_arbitrary_jumping_curve():
    # A 0/2 step can skip output 1 despite endpoint straddling; the solver returns
    # its own continuous response, not a certificate for that discontinuous step.
    result = response.calibrate_rectangles([rectangle(0, 1, 1)])
    assert_witness(result)
    assert result.assignments[0].output == 1


def endpoint_data(rectangles, mode):
    lower, upper = [], []
    for r in rectangles:
        a, b = r.input
        low, high = r.output
        lower.append((b if mode == "some" else a, low))
        upper.append((a if mode == "some" else b, high))
    return lower, upper


def cone_oracle(rectangles, slopes, mode, x=None):
    lower, upper = endpoint_data(rectangles, mode)
    m, cap = slopes
    for lx, low in lower:
        for ux, high in upper:
            if lx <= ux:
                if low + m * (ux - lx) > high:
                    return None
            elif cap is not None and low > high + cap * (lx - ux):
                return None
    if x is None:
        return True
    lows = [low + m * (x - t) for t, low in lower if t <= x]
    highs = [high - m * (t - x) for t, high in upper if t >= x]
    if cap is not None:
        lows += [low - cap * (t - x) for t, low in lower if t > x]
        highs += [high + cap * (x - t) for t, high in upper if t < x]
    return response.RectangleResponseInterval(
        max(lows) if lows else None, min(highs) if highs else None
    )


@pytest.mark.parametrize("mode", ["some", "all"])
def test_seeded_rectangles_match_independent_all_source_cones(mode):
    rng = random.Random(604231)
    settings = [(F(0), None), (F(1, 2), None), (F(0), F(0)), (F(0), F(2)), (F(1, 2), F(3, 2))]
    for _ in range(120):
        rectangles = []
        for _ in range(rng.randint(1, 4)):
            a, b = sorted(F(rng.randint(-4, 4), rng.choice((1, 2, 3))) for _ in range(2))
            low, high = sorted(F(rng.randint(-4, 4), rng.choice((1, 2, 3))) for _ in range(2))
            rectangles.append(rectangle(a, b, low, high))
        slopes = rng.choice(settings)
        result = response.calibrate_rectangles(rectangles, slope_bounds=slopes, input_mode=mode)
        if cone_oracle(rectangles, slopes, mode) is None:
            assert_proof(result)
        else:
            assert_witness(result)
            xs = sorted({x for r in rectangles for x in r.input})
            queries = xs + [(2 * a + b) / 3 for a, b in itertools.pairwise(xs)]
            for x in queries:
                assert result.query(x) == cone_oracle(rectangles, slopes, mode, x)


@pytest.mark.parametrize("mode", ["some", "all"])
def test_equal_slopes_match_independent_closed_form_intercept_feasibility(mode):
    rng = random.Random(733)
    for _ in range(80):
        slope = rng.choice((F(0), F(1, 2), F(2)))
        rectangles = [
            rectangle(
                *sorted(F(rng.randint(-4, 4), 3) for _ in range(2)),
                *sorted(F(rng.randint(-4, 4), 2) for _ in range(2)),
            )
            for _ in range(3)
        ]
        if mode == "some":
            lo = max(r.output[0] - slope * r.input[1] for r in rectangles)
            hi = min(r.output[1] - slope * r.input[0] for r in rectangles)
        else:
            lo = max(r.output[0] - slope * r.input[0] for r in rectangles)
            hi = min(r.output[1] - slope * r.input[1] for r in rectangles)
        result = response.calibrate_rectangles(
            rectangles, slope_bounds=(slope, slope), input_mode=mode
        )
        if lo > hi:
            assert_proof(result)
        else:
            assert_witness(result)
            for band in result.nodes:
                assert (band.lower, band.upper) == (
                    lo + slope * band.input,
                    hi + slope * band.input,
                )


def original_selected_x_oracle(rectangles, m, cap):
    """Fixed output points, original selected x_i; no endpoint reduction.

    A symbolic epsilon retains strict ordering for unequal outputs when no upper
    slope exists. Finite difference-constraint closure detects feasibility.
    """
    count = len(rectangles) + 1
    distance = [[None] * count for _ in range(count)]
    for i in range(count):
        distance[i][i] = (F(0), 0)

    def edge(i, j, weight):
        if distance[i][j] is None or weight < distance[i][j]:
            distance[i][j] = weight

    for i, r in enumerate(rectangles, 1):
        edge(0, i, (r.input[1], 0))
        edge(i, 0, (-r.input[0], 0))
    for i, left in enumerate(rectangles, 1):
        for j, right in enumerate(rectangles, 1):
            dy = right.output[0] - left.output[0]
            if dy > 0:
                if cap == 0:
                    return False
                edge(j, i, (-dy / cap, 0) if cap is not None else (F(0), -1))
                if m > 0:
                    edge(i, j, (dy / m, 0))
            elif dy == 0 and m > 0:
                edge(i, j, (F(0), 0))
    for k in range(count):
        for i in range(count):
            for j in range(count):
                if distance[i][k] is not None and distance[k][j] is not None:
                    value = (
                        distance[i][k][0] + distance[k][j][0],
                        distance[i][k][1] + distance[k][j][1],
                    )
                    edge(i, j, value)
    return all(distance[i][i] >= (F(0), 0) for i in range(count))


def test_some_matches_original_selected_input_oracle_including_strict_no_cap_order():
    intervals = [(F(a), F(b)) for a in range(2) for b in range(a, 2)]
    choices = [rectangle(a, b, F(y)) for (a, b), y in itertools.product(intervals, range(2))]
    slopes = [(F(0), None), (F(1), None), (F(0), F(0)), (F(0), F(1)), (F(1), F(1))]
    for rectangles in itertools.product(choices, repeat=2):
        for m, cap in slopes:
            result = response.calibrate_rectangles(rectangles, slope_bounds=(m, cap))
            assert (result.status == "compatible") == original_selected_x_oracle(rectangles, m, cap)


def graph_oracle(rectangles, slopes, mode, query):
    # Every ORIGINAL endpoint occurrence is a separate variable; equal coordinates
    # get equality edges. Add a free query variable, without chain tightening.
    lower, upper = endpoint_data(rectangles, mode)
    entries = [(x, value, True) for x, value in lower] + [(x, value, False) for x, value in upper]
    xs = [x for x, _, _ in entries] + [query]
    count = len(xs) + 1
    d = [[None] * count for _ in range(count)]
    for i in range(count):
        d[i][i] = F(0)

    def edge(i, j, weight):
        if d[i][j] is None or weight < d[i][j]:
            d[i][j] = weight

    for i, (_, value, is_lower) in enumerate(entries, 1):
        edge(i, 0, -value) if is_lower else edge(0, i, value)
    m, cap = slopes
    for i, x in enumerate(xs, 1):
        for j, y in enumerate(xs, 1):
            if x == y:
                edge(i, j, F(0))
            elif x < y:
                edge(j, i, -m * (y - x))
                if cap is not None:
                    edge(i, j, cap * (y - x))
    for k in range(count):
        for i in range(count):
            for j in range(count):
                if d[i][k] is not None and d[k][j] is not None:
                    edge(i, j, d[i][k] + d[k][j])
    if any(d[i][i] < 0 for i in range(count)):
        return None
    return response.RectangleResponseInterval(None if d[-1][0] is None else -d[-1][0], d[0][-1])


@pytest.mark.parametrize("mode", ["some", "all"])
def test_generic_original_endpoint_graph_matches_queries_and_unboundedness(mode):
    for rectangles in (
        [rectangle(F(0), F(2), F(0), F(1))],
        [rectangle(F(0), F(2), F(0), F(1)), rectangle(F(1), F(3), F(1), F(2))],
        [rectangle(F(0), F(2), F(2)), rectangle(F(1), F(3), F(0))],
    ):
        for slopes in ((F(0), None), (F(1, 3), None), (F(0), F(1)), (F(1), F(1))):
            result = response.calibrate_rectangles(rectangles, slope_bounds=slopes, input_mode=mode)
            expected = graph_oracle(rectangles, slopes, mode, F(3, 2))
            if expected is None:
                assert_proof(result)
            else:
                assert_witness(result)
                assert result.query(F(3, 2)) == expected


@pytest.mark.parametrize("bad", [True, 0.1, float("nan"), "NaN", "1e999", "1" * 41, F(1, 2**513)])
def test_invalid_or_inexact_numbers_are_refused(bad):
    with pytest.raises((ValueError, TypeError)):
        response.calibrate_rectangles([rectangle(bad, 1, 0, 1)])
    with pytest.raises((ValueError, TypeError)):
        response.calibrate_rectangles([rectangle(0, 1, 0, bad)])


def test_invalid_schema_modes_and_slopes_are_refused():
    for rectangles, options in (
        ([], {}),
        ([{"input": [0, 1], "output": [0, 1], "extra": 0}], {}),
        ([rectangle(1, 0, 0)], {}),
        ([rectangle(0, 1, 1, 0)], {}),
        ([{"input": [0], "output": [0, 1]}], {}),
        ([rectangle(0, 1, 0)], {"input_mode": "either"}),
        ([rectangle(0, 1, 0)], {"input_mode": True}),
        ([rectangle(0, 1, 0)], {"slope_bounds": (-1, None)}),
        ([rectangle(0, 1, 0)], {"slope_bounds": (2, 1)}),
        ([rectangle(0, 1, 0)], {"slope_bounds": (0, 0.1)}),
    ):
        with pytest.raises((ValueError, TypeError)):
            response.calibrate_rectangles(rectangles, **options)


def test_decimal_context_cannot_change_exact_result():
    rectangles = [rectangle("0.1", "0.3", "0.2", "0.4"), rectangle("0.8", "0.9", "0.8", "1.1")]
    expected = response.calibrate_rectangles(rectangles, slope_bounds=("0.3", "2")).to_dict()
    with localcontext(Context(prec=2, Emin=-2, Emax=2, clamp=1)):
        assert (
            response.calibrate_rectangles(rectangles, slope_bounds=("0.3", "2")).to_dict()
            == expected
        )


def test_count_cap_and_finite_maximum_population():
    result = response.calibrate_rectangles(
        rectangle(i, i + 1, 0, 1) for i in range(response.MAX_RECTANGLES)
    )
    assert len(result.rectangles) == response.MAX_RECTANGLES
    assert_witness(result)
    with pytest.raises(ValueError, match="count"):
        response.calibrate_rectangles(
            rectangle(i, i, 0) for i in range(response.MAX_RECTANGLES + 1)
        )


def test_work_limit_includes_assignment_recovery_and_queries(monkeypatch):
    rectangles = [rectangle(0, 0, 0), rectangle(2, 2, 2), rectangle(0, 2, F(1, 3))]
    result = response.calibrate_rectangles(rectangles)
    monkeypatch.setattr(response, "MAX_WORK", result.work - 1)
    with pytest.raises(ValueError, match="work limit"):
        response.calibrate_rectangles(rectangles)
    monkeypatch.setattr(response, "MAX_WORK", 1)
    with pytest.raises(ValueError, match="work limit"):
        result.query(F(1, 3))
    with pytest.raises(ValueError, match="work limit"):
        response.calibrate_rectangles([rectangle(0, 1, 0)])


def test_result_size_limit_refuses_without_partial_calibration(monkeypatch):
    monkeypatch.setattr(response, "MAX_RESULT_BITS", 2)
    with pytest.raises(ValueError, match="rational-size"):
        response.calibrate_rectangles([rectangle(0, 2, 0, 1)], slope_bounds=(2, 2))


def test_incompatible_query_and_out_of_domain_are_not_unbounded_estimates():
    bad = response.calibrate_rectangles([rectangle(0, 0, 0), rectangle(0, 0, 1)])
    with pytest.raises(ValueError, match="incompatible"):
        bad.query(0)
    good = response.calibrate_rectangles([rectangle(0, 1, 0, 1)])
    with pytest.raises(ValueError, match="outside"):
        good.query(2)
    with pytest.raises(TypeError):
        good.query(0.5)
