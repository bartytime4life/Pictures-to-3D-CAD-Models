"""Conditional set inversion for a shared Gaussian edge and scalar response.

Every observation uses the SAME offset and positive sigma. Accepted/excluded
closed parameter boxes are proved; remaining boxes are retained as unknown.
Analytic order families prove forall parameters exists one shared response per
parameter. Numerical all-input witnesses provide the stronger exists one response
forall parameters within a box. Neither conclusion qualifies camera physics.
"""

from collections import deque
from collections.abc import Mapping
from fractions import Fraction as F

from .normal_cdf_bounds import normal_cdf_bounds
from .response_calibration import parse_exact
from .response_rectangles import calibrate_rectangles

MAX_OBSERVATIONS = 32
MAX_CALIBRATION = 128
MAX_BOXES = 4095
MAX_DEPTH = 48


def _pair(values, label):
    if not isinstance(values, (tuple, list)) or len(values) != 2:
        raise ValueError(f"{label} needs two ordered exact endpoints")
    a, b = map(parse_exact, values)
    if a > b:
        raise ValueError(f"{label} endpoints must be ordered")
    return a, b


def _items(values, limit, label):
    if isinstance(values, (str, bytes, Mapping)):
        raise TypeError(f"{label} must be a bounded iterable")
    try:
        iterator = iter(values)
    except TypeError as error:
        raise TypeError(f"{label} must be a bounded iterable") from error
    result = []
    for index, value in enumerate(iterator):
        if index >= limit:
            raise ValueError(f"{label} exceeds its {limit}-item limit")
        result.append(value)
    return result


def _serialize_box(box):
    return {key: list(map(str, pair)) for key, pair in box.items()}


def _z_bounds(position, box):
    values = [(position - e) / sigma for e in box["offset"] for sigma in box["sigma"]]
    return min(values), max(values)


def _compact(result):
    data = result.to_dict()
    return {
        key: data[key]
        for key in (
            "status",
            "input_mode",
            "slope_bounds",
            "witness",
            "assignments",
            "contradiction",
            "work",
        )
    }


def _ordered_evidence(observations, calibration):
    """Exact position order plus the two invariant Gaussian endpoint anchors."""
    entries = []
    for i, (x, low, high) in enumerate(calibration):
        if x in (0, 1):
            entries.append(((0 if x == 0 else 2, F(0)), i, low, high))
    for i, (p, low, high) in enumerate(observations):
        entries.append(((1, p), len(calibration) + i, low, high))
    groups = []
    for key, source, low, high in sorted(entries):
        if not groups or groups[-1]["key"] != key:
            groups.append(
                {
                    "key": key,
                    "sources": [],
                    "lower": low,
                    "upper": high,
                    "lower_source": source,
                    "upper_source": source,
                }
            )
        group = groups[-1]
        group["sources"].append(source)
        if low > group["lower"]:
            group["lower"], group["lower_source"] = low, source
        if high < group["upper"]:
            group["upper"], group["upper_source"] = high, source
    running, origin, origin_rank = None, None, None
    saved = []
    for rank, group in enumerate(groups):
        if running is None or group["lower"] > running:
            running, origin, origin_rank = group["lower"], group["lower_source"], rank
        kind, coordinate = group["key"]
        record = {
            "kind": "observation" if kind == 1 else "calibration_endpoint",
            "coordinate": str(coordinate if kind == 1 else F(kind == 2)),
            "source_indices": group["sources"],
            "output": [str(group["lower"]), str(group["upper"])],
            "selected_output": str(running),
        }
        saved.append(record)
        if running > group["upper"]:
            return {
                "groups": saved,
                "contradiction": {
                    "lower_source": origin,
                    "upper_source": group["upper_source"],
                    "order_relation": "same_input" if origin_rank == rank else "increasing_input",
                    "implied_lower": str(running),
                    "implied_upper": str(group["upper"]),
                },
            }
    return {"groups": saved, "contradiction": None}


def analyze_gaussian_response(
    observations,
    calibration=(),
    *,
    offset_bounds,
    sigma_bounds,
    slope_bounds=("0", None),
    tolerances=("0.01", "0.01"),
    cdf_places=24,
    max_boxes=127,
    max_depth=24,
):
    """Return a JSON-ready exact inner/outer cover of shared (offset,sigma).

    Observations are {position,output:[L,U]}; fixed calibration is
    {input,output:[L,U]} with normalized inputs in [0,1]. Numbers use the prior
    exact decimal/int/Fraction parser; floats and booleans are refused. All
    parameter boxes are closed, including shared bisection faces. Valid numerical
    limits preserve unknown boxes. Unsupported initial numerical CDF domains
    refuse the whole request; analytic order certificates need no CDF evaluation.
    """
    offset = _pair(offset_bounds, "offset_bounds")
    sigma = _pair(sigma_bounds, "sigma_bounds")
    if sigma[0] <= 0:
        raise ValueError("sigma must be strictly positive throughout the domain")
    if not isinstance(tolerances, (tuple, list)) or len(tolerances) != 2:
        raise ValueError("tolerances needs positive offset and sigma widths")
    tolerance = tuple(map(parse_exact, tolerances))
    if any(value <= 0 for value in tolerance):
        raise ValueError("tolerances must be strictly positive")
    if not isinstance(slope_bounds, (tuple, list)) or len(slope_bounds) != 2:
        raise ValueError("slope_bounds needs a lower and optional upper")
    m = parse_exact(slope_bounds[0])
    upper = None if slope_bounds[1] is None else parse_exact(slope_bounds[1])
    if m < 0 or (upper is not None and upper < m):
        raise ValueError("slope bounds must obey 0 <= lower <= upper")
    for name, value, low, high in (
        ("cdf_places", cdf_places, 1, 30),
        ("max_boxes", max_boxes, 1, MAX_BOXES),
        ("max_depth", max_depth, 0, MAX_DEPTH),
    ):
        if type(value) is not int:
            raise TypeError(f"{name} must be an integer")
        if not low <= value <= high:
            raise ValueError(f"{name} must lie in [{low},{high}]")
    obs, cal = [], []
    for row in _items(observations, MAX_OBSERVATIONS, "observations"):
        if not isinstance(row, Mapping) or set(row) != {"position", "output"}:
            raise ValueError("each observation needs exactly position and output")
        low, high = _pair(row["output"], "observation output")
        obs.append((parse_exact(row["position"]), low, high))
    if not obs:
        raise ValueError("supply at least one observation")
    for row in _items(calibration, MAX_CALIBRATION, "calibration"):
        if not isinstance(row, Mapping) or set(row) != {"input", "output"}:
            raise ValueError("each calibration node needs exactly input and output")
        x = parse_exact(row["input"])
        if not 0 <= x <= 1:
            raise ValueError("calibration inputs must lie in [0,1]")
        low, high = _pair(row["output"], "calibration output")
        cal.append((x, low, high))
    root = {"offset": offset, "sigma": sigma}
    inputs = {
        "observations": [{"position": str(p), "output": [str(lo), str(hi)]} for p, lo, hi in obs],
        "calibration": [{"input": str(x), "output": [str(lo), str(hi)]} for x, lo, hi in cal],
        "offset_bounds": list(map(str, offset)),
        "sigma_bounds": list(map(str, sigma)),
        "slope_bounds": [str(m), None if upper is None else str(upper)],
    }
    settings = {
        "tolerances": list(map(str, tolerance)),
        "cdf_places": cdf_places,
        "max_boxes": max_boxes,
        "max_depth": max_depth,
    }
    boxes, nodes, cdfs, cache = [root], [], [], {}

    def new_node(box, parent, depth):
        index = len(nodes)
        nodes.append(
            {
                "index": index,
                "parent": parent,
                "depth": depth,
                "box": _serialize_box(box),
                "status": "pending",
                "reason": None,
                "proof_kind": None,
                "order_evidence": None,
                "input_covers": [],
                "some": None,
                "all": None,
                "split_axis": None,
                "split_at": None,
                "children": [],
                "error": None,
            }
        )
        return index

    new_node(root, None, 0)
    order = _ordered_evidence(obs, cal)
    family = m == 0 and upper is None and all(x in (0, 1) for x, _, _ in cal)
    evaluated = response_work = 0
    if order["contradiction"] is not None:
        nodes[0].update(
            status="excluded",
            reason="invariant_input_order",
            proof_kind="invariant_order_contradiction",
            order_evidence=order,
        )
        evaluated = 1
    elif family:
        nodes[0].update(
            status="accepted",
            reason="monotone_response_family",
            proof_kind="ordered_response_family",
            order_evidence=order,
        )
        evaluated = 1
    else:
        # Only numerical fallback needs the bounded CDF's domain. No clipping.
        if any(abs(z) > 6 for p, _, _ in obs for z in _z_bounds(p, root)):
            raise ValueError("numerical root CDF coordinates must all lie in [-6,6]")

        def cdf(z):
            if z not in cache:
                value = normal_cdf_bounds(z, places=cdf_places)
                cache[z] = len(cdfs)
                cdfs.append(value.to_dict())
            return cache[z], cdfs[cache[z]]

        queue = deque([0])
        while queue:
            index = queue.popleft()
            node, box = nodes[index], boxes[index]
            if evaluated >= max_boxes:
                node.update(status="unknown", reason="box_limit")
                continue
            evaluated += 1
            rectangles = [{"input": [x, x], "output": [lo, hi]} for x, lo, hi in cal]
            try:
                for i, (p, lo, hi) in enumerate(obs):
                    z_low, z_high = _z_bounds(p, box)
                    lower_index, lower_record = cdf(z_low)
                    upper_index, upper_record = cdf(z_high)
                    a, b = F(lower_record["output"][0]), F(upper_record["output"][1])
                    node["input_covers"].append(
                        {
                            "observation_index": i,
                            "z": [str(z_low), str(z_high)],
                            "input": [str(a), str(b)],
                            "lower_cdf": lower_index,
                            "upper_cdf": upper_index,
                        }
                    )
                    rectangles.append({"input": [a, b], "output": [lo, hi]})
                some = calibrate_rectangles(rectangles, slope_bounds=(m, upper), input_mode="some")
                response_work += some.work
                node["some"] = _compact(some)
                if some.status == "incompatible":
                    node.update(
                        status="excluded",
                        reason="some_input_contradiction",
                        proof_kind="rectangle_contradiction",
                    )
                    continue
                all_inputs = calibrate_rectangles(
                    rectangles, slope_bounds=(m, upper), input_mode="all"
                )
                response_work += all_inputs.work
                node["all"] = _compact(all_inputs)
                if all_inputs.status == "compatible":
                    node.update(
                        status="accepted",
                        reason="every_input_witness",
                        proof_kind="universal_response",
                    )
                    continue
            except (ValueError, ArithmeticError) as error:
                node.update(
                    status="unknown",
                    reason="numerical_or_arithmetic_limit",
                    error=f"{type(error).__name__}: {error}",
                )
                continue
            widths = tuple(box[key][1] - box[key][0] for key in ("offset", "sigma"))
            if all(width <= tol for width, tol in zip(widths, tolerance)):
                node.update(status="unknown", reason="tolerance")
            elif node["depth"] >= max_depth:
                node.update(status="unknown", reason="depth_limit")
            else:
                axis = 0 if widths[0] / tolerance[0] >= widths[1] / tolerance[1] else 1
                key = ("offset", "sigma")[axis]
                low, high = box[key]
                middle = (low + high) / 2
                left, right = dict(box), dict(box)
                left[key], right[key] = (low, middle), (middle, high)
                children = []
                for child in (left, right):
                    child_index = new_node(child, index, node["depth"] + 1)
                    boxes.append(child)
                    queue.append(child_index)
                    children.append(child_index)
                node.update(
                    status="split",
                    reason="needs_refinement",
                    split_axis=key,
                    split_at=str(middle),
                    children=children,
                )
    inner = [n["index"] for n in nodes if n["status"] == "accepted"]
    unknown = [n["index"] for n in nodes if n["status"] == "unknown"]
    excluded = [n["index"] for n in nodes if n["status"] == "excluded"]
    outer = sorted(inner + unknown)
    projection = {
        key: None
        if not outer
        else [str(min(boxes[i][key][0] for i in outer)), str(max(boxes[i][key][1] for i in outer))]
        for key in ("offset", "sigma")
    }
    return {
        "format": "pictures-to-cad-gaussian-response-domain-analysis",
        "version": 1,
        "status": "unresolved" if unknown else "compatible" if inner else "incompatible",
        "input": inputs,
        "settings": settings,
        "nodes": nodes,
        "cdf_evaluations": cdfs,
        "inner_node_indices": inner,
        "unknown_node_indices": unknown,
        "excluded_node_indices": excluded,
        "outer_node_indices": outer,
        "outer_projection": projection,
        "summary": {
            "evaluated_boxes": evaluated,
            "created_nodes": len(nodes),
            "accepted_leaves": len(inner),
            "unknown_leaves": len(unknown),
            "excluded_leaves": len(excluded),
            "cdf_evaluations": len(cdfs),
            "response_work": response_work,
            "has_certified_feasible_parameters": bool(inner),
            "feasible_parameters_exist": True if inner else False if not outer else None,
        },
        "limits": [
            "Conditional on one affine 1D Gaussian source, exact positions/output bounds and shared response regularity; no camera calibration.",
            "Every parameter pair uses one response shared by all observations; different parameter pairs/accepted boxes may use different responses.",
            "Ordered families prove forall parameters exists a response; universal-response certificates prove the stronger exists a response forall covered inputs within that box.",
            "Some-input compatibility alone is never a coupled-model feasibility certificate; all-input incompatibility alone is never exclusion.",
            "Accepted union is an inner set; accepted plus unknown is an outer set. Closed children share faces and together cover their parent.",
            "Coordinate projection hulls lose correlation and do not make their Cartesian product feasible. No convergence or finite-resolution completeness claim.",
        ],
    }
