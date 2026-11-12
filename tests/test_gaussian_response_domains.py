"""Shared Gaussian parameters, distinct response quantifiers and exact coverage."""

import copy
import itertools
import json
from decimal import Context, localcontext
from fractions import Fraction as F

import pytest

from backend import gaussian_response_domains as domains


def observation(position, low, high=None):
    return {"position": position, "output": [low, low if high is None else high]}


def calibration(x, low, high=None):
    return {"input": x, "output": [low, low if high is None else high]}


IDENTITY = [calibration(0, 0), calibration(1, 1)]


def analyze(observations, calibration_nodes=(), **options):
    settings = {"offset_bounds": (-1, 1), "sigma_bounds": (1, 1), "max_boxes": 1}
    settings.update(options)
    return domains.analyze_gaussian_response(observations, calibration_nodes, **settings)


def box(node):
    return {key: tuple(map(F, value)) for key, value in node["box"].items()}


def contains(node, offset, sigma):
    b = box(node)
    return b["offset"][0] <= offset <= b["offset"][1] and b["sigma"][0] <= sigma <= b["sigma"][1]


def assert_partition(result):
    """Prove coverage from the full tree and exact children, not summed area."""
    nodes = result["nodes"]
    assert nodes[0]["parent"] is None and nodes[0]["depth"] == 0
    visited = set()

    def visit(index):
        assert index not in visited
        visited.add(index)
        node = nodes[index]
        assert node["index"] == index
        assert node["status"] in {"accepted", "excluded", "unknown", "split"}
        if node["status"] != "split":
            assert node["children"] == []
            return
        assert len(node["children"]) == 2
        left, right = (nodes[i] for i in node["children"])
        parent_box, left_box, right_box = box(node), box(left), box(right)
        axis = node["split_axis"]
        other = "sigma" if axis == "offset" else "offset"
        middle = sum(parent_box[axis]) / 2
        assert F(node["split_at"]) == middle
        assert left_box[axis] == (parent_box[axis][0], middle)
        assert right_box[axis] == (middle, parent_box[axis][1])
        assert left_box[other] == right_box[other] == parent_box[other]
        for child in (left, right):
            assert child["parent"] == index and child["depth"] == node["depth"] + 1
            visit(child["index"])

    visit(0)
    assert visited == set(range(len(nodes)))
    expected = {
        "inner_node_indices": "accepted",
        "unknown_node_indices": "unknown",
        "excluded_node_indices": "excluded",
    }
    for key, status in expected.items():
        assert result[key] == [n["index"] for n in nodes if n["status"] == status]
    assert result["outer_node_indices"] == sorted(
        result["inner_node_indices"] + result["unknown_node_indices"]
    )
    terminals = result["outer_node_indices"] + result["excluded_node_indices"]
    assert len(terminals) == len(set(terminals))
    assert set(terminals) == {n["index"] for n in nodes if n["status"] != "split"}
    assert result["summary"]["created_nodes"] == len(nodes)
    assert result["summary"]["evaluated_boxes"] <= result["settings"]["max_boxes"]


def pl_value(witness, x):
    points = [(F(p["input"]), F(p["output"])) for p in witness]
    for coordinate, value in points:
        if coordinate == x:
            return value
    for (a, low), (b, high) in itertools.pairwise(points):
        if a < x < b:
            return low + (x - a) * (high - low) / (b - a)
    raise AssertionError("query outside returned response witness")


def assert_universal_witness(result, node):
    assert node["proof_kind"] == "universal_response"
    assert node["some"]["status"] == node["all"]["status"] == "compatible"
    witness = node["all"]["witness"]
    m, cap = result["input"]["slope_bounds"]
    m, cap = F(m), None if cap is None else F(cap)
    for left, right in itertools.combinations(witness, 2):
        dx = F(right["input"]) - F(left["input"])
        dy = F(right["output"]) - F(left["output"])
        assert m * dx <= dy
        assert cap is None or dy <= cap * dx
    for row in result["input"]["calibration"]:
        low, high = map(F, row["output"])
        assert low <= pl_value(witness, F(row["input"])) <= high
    for cover in node["input_covers"]:
        row = result["input"]["observations"][cover["observation_index"]]
        low, high = map(F, row["output"])
        a, b = map(F, cover["input"])
        assert low <= pl_value(witness, a) <= pl_value(witness, b) <= high


def test_order_family_is_parameter_dependent_and_keeps_original_sources():
    result = analyze(
        [
            observation(1, "0.6", "0.7"),
            observation(-1, "0.2", "0.3"),
            observation(1, "0.65", "0.8"),
        ],
        IDENTITY,
        sigma_bounds=(1, 2),
    )
    assert_partition(result)
    root = result["nodes"][0]
    assert root["status"] == "accepted" and root["proof_kind"] == "ordered_response_family"
    assert root["some"] is root["all"] is None and result["cdf_evaluations"] == []
    groups = root["order_evidence"]["groups"]
    assert [g["source_indices"] for g in groups] == [[0], [3], [2, 4], [1]]
    assert [F(g["selected_output"]) for g in groups] == [0, F(1, 5), F(13, 20), 1]
    assert result["summary"]["feasible_parameters_exist"] is True


def test_order_family_can_use_strict_gaussian_interior_beyond_numerical_range():
    result = analyze([observation(1000, F(1, 2))], IDENTITY)
    assert result["nodes"][0]["proof_kind"] == "ordered_response_family"
    assert result["status"] == "compatible" and result["cdf_evaluations"] == []
    # This uses 0<Phi(finite z)<1 symbolically, even when a float CDF saturates.
    assert result["nodes"][0]["order_evidence"]["groups"][1]["kind"] == "observation"


@pytest.mark.parametrize("slopes", [(0, None), (0, 32), (1, None)])
def test_invariant_order_excludes_shared_parameters_for_every_slope_prior(slopes):
    result = analyze([observation(1000, 1), observation(1001, 0)], slope_bounds=slopes)
    assert_partition(result)
    root = result["nodes"][0]
    assert root["proof_kind"] == "invariant_order_contradiction"
    proof = root["order_evidence"]["contradiction"]
    assert proof["order_relation"] == "increasing_input"
    assert (proof["lower_source"], proof["upper_source"]) == (0, 1)
    assert F(proof["implied_lower"]) > F(proof["implied_upper"])
    assert result["status"] == "incompatible" and result["outer_node_indices"] == []
    assert result["cdf_evaluations"] == []


def test_duplicate_positions_are_one_exact_input_and_nearby_positions_remain_distinct():
    duplicate = analyze([observation("0.1", 0), observation("0.10", "1e-40")])
    assert (
        duplicate["nodes"][0]["order_evidence"]["contradiction"]["order_relation"] == "same_input"
    )
    nearby = analyze([observation(0, 0), observation("1e-40", 1)])
    groups = nearby["nodes"][0]["order_evidence"]["groups"]
    assert len(groups) == 2 and [g["coordinate"] for g in groups] == ["0", str(F(1, 10**40))]
    assert nearby["nodes"][0]["proof_kind"] == "ordered_response_family"


def test_anchor_order_conflict_keeps_calibration_before_observation_indices():
    result = analyze([observation(0, "0.2")], [calibration(0, "0.7"), calibration(1, 1)])
    proof = result["nodes"][0]["order_evidence"]["contradiction"]
    assert (proof["lower_source"], proof["upper_source"]) == (0, 2)
    assert proof["order_relation"] == "increasing_input"
    assert result["status"] == "incompatible"


def test_exact_zero_input_certifies_entire_sigma_interval_without_identifying_sigma():
    result = analyze(
        [observation(0, F(1, 2))],
        IDENTITY,
        offset_bounds=(0, 0),
        sigma_bounds=(1, 2),
        slope_bounds=(1, 1),
    )
    assert_partition(result)
    assert result["inner_node_indices"] == [0] and result["unknown_node_indices"] == []
    assert_universal_witness(result, result["nodes"][0])
    assert len(result["cdf_evaluations"]) == 1
    assert result["cdf_evaluations"][0]["output"] == ["1/2", "1/2"]
    assert result["outer_projection"]["sigma"] == ["1", "2"]


def test_constant_response_with_zero_upper_slope_gets_universal_not_family_proof():
    result = analyze(
        [observation(-1, 2, 3), observation(1, 2, 4)],
        sigma_bounds=(1, 2),
        slope_bounds=(0, 0),
    )
    assert result["nodes"][0]["proof_kind"] == "universal_response"
    assert_universal_witness(result, result["nodes"][0])


def test_some_feasibility_does_not_claim_one_coupled_parameter_witness():
    # Identity response: first datum forces e=0, while Phi(1) is not 3/5.
    # Independent covered inputs can nevertheless choose 1/2 and 3/5.
    result = analyze(
        [observation(0, F(1, 2)), observation(1, F(3, 5))],
        IDENTITY,
        slope_bounds=(1, 1),
    )
    assert_partition(result)
    root = result["nodes"][0]
    assert root["some"]["status"] == "compatible" and root["all"]["status"] == "incompatible"
    assert result["status"] == "unresolved" and result["inner_node_indices"] == []
    assert result["summary"]["has_certified_feasible_parameters"] is False
    assert result["summary"]["feasible_parameters_exist"] is None


def test_all_incompatibility_does_not_exclude_parameter_dependent_finite_slope_fits():
    # Every actual theta is feasible: the two inputs differ by integral phi over
    # a unit interval in [-1,2]. pi<4 and exp(2)<9 give that gap >1/27>1/32.
    # One slope<=32 PL response per theta fits 0 and1. Overlapping input covers
    # preclude a single response for ALL covered inputs, so root remains unknown.
    result = analyze([observation(0, 0), observation(1, 1)], slope_bounds=(0, 32))
    assert_partition(result)
    root = result["nodes"][0]
    assert root["some"]["status"] == "compatible" and root["all"]["status"] == "incompatible"
    first, second = root["input_covers"]
    assert max(F(first["input"][0]), F(second["input"][0])) <= min(
        F(first["input"][1]), F(second["input"][1])
    )
    assert result["excluded_node_indices"] == [] and result["unknown_node_indices"]
    assert result["summary"]["feasible_parameters_exist"] is None


@pytest.mark.parametrize(
    "position,offset,sigma,expected",
    [
        (-1, (-2, 1), (1, 2), (F(-2), F(1))),
        (1, (-2, 0), (1, 3), (F(1, 3), F(3))),
        (-2, (0, 1), (1, 3), (F(-3), F(-2, 3))),
        (0, (-1, 1), (1, 2), (F(-1), F(1))),
    ],
)
def test_z_extrema_are_exact_four_corner_bounds_with_source_linkage(
    position, offset, sigma, expected
):
    result = analyze(
        [observation(position, -10, 10)],
        offset_bounds=offset,
        sigma_bounds=sigma,
        slope_bounds=(0, 1),
        cdf_places=12,
    )
    node = result["nodes"][0]
    cover = node["input_covers"][0]
    assert tuple(map(F, cover["z"])) == expected
    lower = result["cdf_evaluations"][cover["lower_cdf"]]
    upper = result["cdf_evaluations"][cover["upper_cdf"]]
    assert F(lower["z"]) == expected[0] and F(upper["z"]) == expected[1]
    assert cover["input"] == [lower["output"][0], upper["output"][1]]
    for e in (*map(F, offset), sum(map(F, offset)) / 2):
        for s in (*map(F, sigma), sum(map(F, sigma)) / 2):
            assert expected[0] <= (F(position) - e) / s <= expected[1]
    assert_universal_witness(result, node)


@pytest.mark.parametrize("budget", [1, 2, 3, 7])
def test_budget_keeps_current_and_pending_boxes_in_an_exact_closed_partition(budget):
    result = analyze(
        [observation(0, 0), observation(1, 1)],
        slope_bounds=(0, 32),
        sigma_bounds=(1, 2),
        max_boxes=budget,
    )
    assert_partition(result)
    assert result["summary"]["evaluated_boxes"] == budget
    assert any(n["reason"] == "box_limit" for n in result["nodes"])
    for e in (F(-1), F(-1, 2), F(0), F(1, 2), F(1)):
        for sigma in (F(1), F(3, 2), F(2)):
            assert any(contains(result["nodes"][i], e, sigma) for i in result["outer_node_indices"])


@pytest.mark.parametrize(
    "tolerances,expected_axis,split",
    [((1, 1), "offset", F(0)), ((2, 1), "sigma", F(2))],
)
def test_longest_normalized_width_split_and_offset_tie_are_exact(tolerances, expected_axis, split):
    result = analyze(
        [observation(0, F(1, 2)), observation(1, F(3, 5))],
        IDENTITY,
        sigma_bounds=(1, 3),
        slope_bounds=(1, 1),
        tolerances=tolerances,
    )
    root = result["nodes"][0]
    assert root["status"] == "split" and root["split_axis"] == expected_axis
    assert F(root["split_at"]) == split
    assert_partition(result)


@pytest.mark.parametrize(
    "options,reason",
    [({"max_depth": 0}, "depth_limit"), ({"tolerances": (3, 2)}, "tolerance")],
)
def test_depth_and_tolerance_limits_withhold_without_discarding_the_root(options, reason):
    result = analyze([observation(0, 0), observation(1, 1)], slope_bounds=(0, 32), **options)
    assert_partition(result)
    assert len(result["nodes"]) == 1 and result["nodes"][0]["reason"] == reason
    assert result["unknown_node_indices"] == result["outer_node_indices"] == [0]


@pytest.mark.parametrize("places", [6, 30])
def test_singleton_geometry_can_remain_unknown_due_to_finite_cdf_cover(places):
    # At the exact geometry some f(u)=u+c fits the single observation. Positive
    # lower slope forbids its exact output over the nonzero CDF cover width.
    result = analyze(
        [observation(1, F(1, 2))],
        offset_bounds=(0, 0),
        slope_bounds=(1, None),
        cdf_places=places,
    )
    assert result["status"] == "unresolved"
    node = result["nodes"][0]
    assert node["reason"] == "tolerance"
    assert node["some"]["status"] == "compatible" and node["all"]["status"] == "incompatible"
    assert result["summary"]["feasible_parameters_exist"] is None
    assert_partition(result)


def test_codimension_one_feasible_line_survives_closed_subdivision():
    result = analyze(
        [observation(0, F(1, 2))],
        IDENTITY,
        sigma_bounds=(1, 2),
        slope_bounds=(1, 1),
        tolerances=(F(1, 32), F(1, 32)),
        max_boxes=31,
    )
    assert_partition(result)
    assert result["excluded_node_indices"] and result["unknown_node_indices"]
    for sigma in (F(1), F(5, 4), F(3, 2), F(7, 4), F(2)):
        assert any(contains(result["nodes"][i], F(0), sigma) for i in result["outer_node_indices"])
        assert not any(
            contains(result["nodes"][i], F(0), sigma) for i in result["excluded_node_indices"]
        )


def test_outer_coordinate_hull_does_not_assert_its_cartesian_product_is_feasible():
    result = analyze(
        [observation(0, F(1, 2), F(3, 4))],
        IDENTITY,
        offset_bounds=(-1, 0),
        sigma_bounds=(1, 2),
        slope_bounds=(1, 1),
        tolerances=(F(1, 16), F(1, 16)),
        cdf_places=12,
        max_boxes=127,
    )
    assert_partition(result)
    assert any(contains(result["nodes"][i], -1, 2) for i in result["inner_node_indices"])
    assert any(contains(result["nodes"][i], 0, 1) for i in result["inner_node_indices"])
    assert result["outer_projection"] == {"offset": ["-1", "0"], "sigma": ["1", "2"]}
    # (-1,1) belongs to the coordinate hull, but Phi(1)>3/4 excludes it.
    assert any(contains(result["nodes"][i], -1, 1) for i in result["excluded_node_indices"])
    assert not any(contains(result["nodes"][i], -1, 1) for i in result["inner_node_indices"])


def test_numerical_contradiction_has_original_calibration_then_observation_provenance():
    result = analyze(
        [observation(0, F(9, 10))],
        IDENTITY,
        offset_bounds=(F(-1, 10), F(1, 10)),
        slope_bounds=(1, 1),
    )
    assert_partition(result)
    root = result["nodes"][0]
    assert root["proof_kind"] == "rectangle_contradiction" and root["all"] is None
    proof = root["some"]["contradiction"]
    assert (proof["lower_source"], proof["upper_source"]) == (2, 0)
    assert F(proof["implied_lower"]) > F(proof["implied_upper"])
    assert result["summary"]["feasible_parameters_exist"] is False
    assert result["outer_projection"] == {"offset": None, "sigma": None}


def test_local_cdf_arithmetic_failure_retains_unknown_coverage(monkeypatch):
    def exhausted(*args, **kwargs):
        raise ValueError("injected exact CDF resource limit")

    monkeypatch.setattr(domains, "normal_cdf_bounds", exhausted)
    result = analyze([observation(0, 0, 1)], slope_bounds=(0, 1))
    assert_partition(result)
    root = result["nodes"][0]
    assert root["status"] == "unknown" and root["reason"] == "numerical_or_arithmetic_limit"
    assert "injected exact CDF resource limit" in root["error"]
    assert result["inner_node_indices"] == result["excluded_node_indices"] == []
    assert result["outer_node_indices"] == [0]


def test_local_response_failure_keeps_saved_inputs_and_partial_evidence(monkeypatch):
    original = domains.calibrate_rectangles
    calls = 0

    def exhausted(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ArithmeticError("injected response arithmetic limit")
        return original(*args, **kwargs)

    monkeypatch.setattr(domains, "calibrate_rectangles", exhausted)
    result = analyze([observation(0, 0, 1)], slope_bounds=(0, 1))
    assert_partition(result)
    root = result["nodes"][0]
    assert root["status"] == "unknown" and root["some"]["status"] == "compatible"
    assert root["all"] is None and root["input_covers"]
    assert result["cdf_evaluations"]


@pytest.mark.parametrize(
    "options",
    [
        {"sigma_bounds": (0, 1)},
        {"sigma_bounds": (-1, -1)},
        {"offset_bounds": (1, 0)},
        {"tolerances": (0, 1)},
        {"tolerances": (1,)},
        {"slope_bounds": (-1, None)},
        {"slope_bounds": (2, 1)},
        {"cdf_places": 0},
        {"cdf_places": 31},
        {"cdf_places": True},
        {"max_boxes": 0},
        {"max_boxes": domains.MAX_BOXES + 1},
        {"max_boxes": 1.0},
        {"max_depth": -1},
        {"max_depth": domains.MAX_DEPTH + 1},
        {"max_depth": False},
    ],
)
def test_invalid_settings_are_refused_before_symbolic_shortcuts(options):
    with pytest.raises((TypeError, ValueError)):
        analyze([observation(1000, F(1, 2))], **options)


@pytest.mark.parametrize("value", [True, 0.1, float("nan"), "NaN", "1e999", F(1, 2**513)])
def test_invalid_exact_numbers_are_not_accepted_as_positions_or_levels(value):
    with pytest.raises((TypeError, ValueError)):
        analyze([observation(value, 0)])
    with pytest.raises((TypeError, ValueError)):
        analyze([observation(0, value)])


def test_invalid_schema_calibration_and_numerical_root_range_are_refused():
    for observations, calibration_nodes in (
        ([], []),
        ([{"position": 0, "output": [0, 1], "extra": 1}], []),
        ([observation(0, 2, 1)], []),
        ([observation(0, 0)], [calibration(-1, 0)]),
        ([observation(0, 0)], [calibration(2, 1)]),
        ([observation(0, 0)], [{"input": 0, "output": [0, 1], "extra": 1}]),
    ):
        with pytest.raises((TypeError, ValueError)):
            analyze(observations, calibration_nodes)
    with pytest.raises(ValueError, match="root CDF"):
        analyze([observation(7, 0, 1)], offset_bounds=(0, 0), slope_bounds=(0, 1))
    # An interior calibration disables the symbolic ordered-family shortcut.
    with pytest.raises(ValueError, match="root CDF"):
        analyze([observation(1000, 0, 1)], [calibration(F(1, 2), 0, 1)])


def test_maximum_observation_calibration_counts_and_cdf_cache():
    observations = [observation(0, F(1, 2)) for _ in range(domains.MAX_OBSERVATIONS)]
    anchors = [calibration(i % 2, i % 2) for i in range(domains.MAX_CALIBRATION)]
    result = analyze(observations, anchors, offset_bounds=(0, 0), slope_bounds=(1, 1))
    assert result["nodes"][0]["proof_kind"] == "universal_response"
    assert len(result["cdf_evaluations"]) == 1
    assert len(result["nodes"][0]["all"]["assignments"]) == len(observations) + len(anchors)
    with pytest.raises(ValueError, match="observations"):
        analyze(observation(0, 0) for _ in range(domains.MAX_OBSERVATIONS + 1))
    with pytest.raises(ValueError, match="calibration"):
        analyze(
            [observation(0, 0)], (calibration(0, 0) for _ in range(domains.MAX_CALIBRATION + 1))
        )


def test_inputs_are_preserved_and_decimal_context_cannot_change_json_result():
    observations = [observation("0.1", "0.4", "0.6")]
    inputs = copy.deepcopy(observations)
    options = {"offset_bounds": ("0", "0.2"), "sigma_bounds": (1, 2), "slope_bounds": (0, 1)}
    expected = analyze(observations, **options)
    assert observations == inputs
    with localcontext(Context(prec=2, Emin=-2, Emax=2, clamp=1)):
        actual = analyze(observations, **options)
    assert actual == expected
    assert json.loads(json.dumps(actual, allow_nan=False)) == actual
