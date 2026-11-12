"""Exact conditional response feasibility for supplied input/output rectangles.

``some`` chooses one input/output point in each Cartesian rectangle. ``all``
requires one common continuous response to stay in each output band throughout
its input interval. Neither quantifier supplies physical calibration or a model
of correlated input error. Endpoint reachability uses exact rationals and genuine
half-infinite bands, not an arbitrary finite stand-in for infinity.
"""

import math
from bisect import bisect_left
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from backend.response_calibration import ResponseWitnessPoint, parse_exact

MAX_RECTANGLES = 512
MAX_ENDPOINTS = 2 * MAX_RECTANGLES
MAX_RESULT_BITS = 8192
MAX_WORK = 250_000_000


@dataclass(frozen=True)
class ResponseRectangle:
    input: tuple[object, object]
    output: tuple[object, object]


@dataclass(frozen=True)
class EndpointConstraint:
    source_index: int
    endpoint: str
    bound: str
    value: Fraction


@dataclass(frozen=True)
class RectangleResponseInterval:
    """None means -infinity for lower, +infinity for upper; not unavailable."""

    lower: Fraction | None
    upper: Fraction | None


@dataclass(frozen=True)
class RectangleResponseBand:
    input: Fraction
    lower: Fraction | None
    upper: Fraction | None
    source_indices: tuple[int, ...]
    endpoint_constraints: tuple[EndpointConstraint, ...]


@dataclass(frozen=True)
class RectangleAssignment:
    source_index: int
    input: Fraction
    output: Fraction
    endpoint_outputs: tuple[Fraction, Fraction]


@dataclass(frozen=True)
class RectangleContradiction:
    """Original rectangle endpoint constraints imply a strict bound conflict.

    Under ``some``, lower/upper constraints originate at right/left endpoints;
    under ``all``, they originate at left/right endpoints. Both finite bounds are
    transported forward to at_input, by the lower/upper slope respectively. An
    unbounded upper slope only permits an upper origin already at at_input.
    """

    kind: str
    lower_source: int
    lower_endpoint: str
    upper_source: int
    upper_endpoint: str
    at_input: Fraction
    implied_lower: Fraction
    implied_upper: Fraction


class _Ledger:
    def __init__(self):
        self.work = 0

    def charge(self, *values, multiplier=1):
        amount = multiplier * sum(
            max(1, abs(v.numerator).bit_length(), v.denominator.bit_length()) ** 2 for v in values
        )
        if self.work + amount > MAX_WORK:
            raise ValueError("exact rectangle arithmetic exceeds the work limit")
        self.work += amount

    def result(self, value):
        if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > MAX_RESULT_BITS:
            raise ValueError("exact rectangle result exceeds the rational-size limit")
        return value

    def add(self, a, b):
        self.charge(a, b)
        return self.result(a + b)

    def sub(self, a, b):
        self.charge(a, b)
        return self.result(a - b)

    def mul(self, a, b):
        self.charge(a, b)
        return self.result(a * b)

    def div(self, a, b):
        self.charge(a, b)
        return self.result(a / b)


def _rectangle(value):
    if isinstance(value, ResponseRectangle):
        xs, ys = value.input, value.output
    elif isinstance(value, Mapping) and set(value) == {"input", "output"}:
        xs, ys = value["input"], value["output"]
    else:
        raise ValueError("each rectangle needs exactly input and output")
    if any(not isinstance(pair, (tuple, list)) or len(pair) != 2 for pair in (xs, ys)):
        raise ValueError("rectangle input/output need closed two-endpoint intervals")
    a, b, low, high = (parse_exact(v) for pair in (xs, ys) for v in pair)
    if a > b or low > high:
        raise ValueError("rectangle interval endpoints must be ordered")
    return ResponseRectangle((a, b), (low, high))


def _rational(value):
    return None if value is None else str(value)


def _max_lower(a, b):
    return b if a is None else a if b is None else max(a, b)


def _min_upper(a, b):
    return b if a is None else a if b is None else min(a, b)


def _band_dict(band):
    return {
        "input": str(band.input),
        "output": [_rational(band.lower), _rational(band.upper)],
        "source_indices": list(band.source_indices),
        "endpoint_constraints": [
            {
                "source_index": constraint.source_index,
                "endpoint": constraint.endpoint,
                "bound": constraint.bound,
                "value": str(constraint.value),
            }
            for constraint in band.endpoint_constraints
        ],
    }


@dataclass(frozen=True)
class RectangleCalibration:
    status: str
    rectangles: tuple[ResponseRectangle, ...]
    source_groups: tuple[RectangleResponseBand, ...]
    nodes: tuple[RectangleResponseBand, ...]
    witness: tuple[ResponseWitnessPoint, ...]
    assignments: tuple[RectangleAssignment, ...]
    contradiction: RectangleContradiction | None
    slope_bounds: tuple[Fraction, Fraction | None]
    input_mode: str
    work: int

    def query(self, x):
        """Tight pointwise marginal on the endpoint span, not a joint selection.

        A None lower/upper denotes an unbounded marginal in that direction. The
        finite returned witness need not attain finite marginal endpoints.
        """
        if self.status != "compatible":
            raise ValueError("an incompatible response has no query envelope")
        x = parse_exact(x)
        if x < self.nodes[0].input or x > self.nodes[-1].input:
            raise ValueError("query lies outside the supplied endpoint domain")
        index = bisect_left(tuple(b.input for b in self.nodes), x)
        if self.nodes[index].input == x:
            band = self.nodes[index]
            return RectangleResponseInterval(band.lower, band.upper)
        left, right = self.nodes[index - 1], self.nodes[index]
        ledger = _Ledger()
        dx, remaining = ledger.sub(x, left.input), ledger.sub(right.input, x)
        m, upper = self.slope_bounds
        low = None if left.lower is None else ledger.add(left.lower, ledger.mul(m, dx))
        high = None if right.upper is None else ledger.sub(right.upper, ledger.mul(m, remaining))
        if upper is not None:
            if right.lower is not None:
                low = _max_lower(low, ledger.sub(right.lower, ledger.mul(upper, remaining)))
            if left.upper is not None:
                high = _min_upper(high, ledger.add(left.upper, ledger.mul(upper, dx)))
        return RectangleResponseInterval(low, high)

    def to_dict(self):
        """JSON-compatible exact rationals with explicit unbounded semantics."""
        proof = self.contradiction
        return {
            "status": self.status,
            "input_mode": self.input_mode,
            "conditional_on": "Exact supplied Cartesian input/output rectangles and one common continuous response; not physical camera calibration or correlated-input feasibility.",
            "unbounded_semantics": "In node/query output bands, null lower means -infinity and null upper means +infinity; these are not missing estimates. A null upper slope means no finite upper bound.",
            "slope_bounds": [str(self.slope_bounds[0]), _rational(self.slope_bounds[1])],
            "rectangles": [
                {"input": [str(x) for x in r.input], "output": [str(y) for y in r.output]}
                for r in self.rectangles
            ],
            "source_groups": [_band_dict(b) for b in self.source_groups],
            "nodes": [_band_dict(b) for b in self.nodes],
            "witness": [{"input": str(p.input), "output": str(p.output)} for p in self.witness],
            "assignments": [
                {
                    "source_index": a.source_index,
                    "input": str(a.input),
                    "output": str(a.output),
                    "endpoint_outputs": [str(y) for y in a.endpoint_outputs],
                }
                for a in self.assignments
            ],
            "contradiction": None
            if proof is None
            else {
                "kind": proof.kind,
                "lower_source": proof.lower_source,
                "lower_endpoint": proof.lower_endpoint,
                "upper_source": proof.upper_source,
                "upper_endpoint": proof.upper_endpoint,
                "at_input": str(proof.at_input),
                "implied_lower": str(proof.implied_lower),
                "implied_upper": str(proof.implied_upper),
            },
            "work": self.work,
        }


def _proof(kind, lower_origin, upper_origin, x, low, high):
    return RectangleContradiction(
        kind,
        lower_origin.source_index,
        lower_origin.endpoint,
        upper_origin.source_index,
        upper_origin.endpoint,
        x,
        low,
        high,
    )


def _assignments(rectangles, witness, ledger):
    xs, ys = tuple(p.input for p in witness), tuple(p.output for p in witness)
    assignments = []
    search_allowance = 3 * max(1, math.ceil(math.log2(len(xs))))
    for index, rectangle in enumerate(rectangles):
        a, b = rectangle.input
        low, high = rectangle.output
        ledger.charge(a, b, low, high, multiplier=search_allowance)
        ia, ib = bisect_left(xs, a), bisect_left(xs, b)
        fa, fb = ys[ia], ys[ib]
        ledger.charge(fa, fb)
        if fa >= low:
            x, y = a, fa
        else:
            # The first ordinate >= low has a strictly rising preceding segment.
            j = bisect_left(ys, low, ia + 1, ib + 1)
            dx = ledger.sub(xs[j], xs[j - 1])
            dy = ledger.sub(ys[j], ys[j - 1])
            fraction = ledger.div(ledger.sub(low, ys[j - 1]), dy)
            x, y = ledger.add(xs[j - 1], ledger.mul(fraction, dx)), low
        assignments.append(RectangleAssignment(index, x, y, (fa, fb)))
    return tuple(assignments)


def calibrate_rectangles(rectangles, *, slope_bounds=("0", None), input_mode="some"):
    """Exact feasibility of supplied rectangles with a common continuous response.

    ``some`` means there exist independently chosen points, one per rectangle,
    on the same response. ``all`` requires that response to obey every output band
    for every input in the corresponding interval. Both retain common slope
    bounds. These are logical quantifiers, not statistical independence or error
    probabilities. Floats/bools, invalid requests and resource exhaustion are
    refused; contradictory valid constraints return an indexed exact proof.

    The some-mode endpoint reduction is existential: a discontinuous response
    that jumps over an output band need not itself intersect that rectangle, but
    a feasible finite selection always has a continuous PL representative.
    Work includes endpoint sorting, exact propagation and assignment recovery.
    """
    if input_mode not in ("some", "all"):
        raise ValueError("input_mode must be 'some' or 'all'")
    if not isinstance(slope_bounds, (tuple, list)) or len(slope_bounds) != 2:
        raise ValueError("slope_bounds needs a nonnegative lower and optional upper")
    m = parse_exact(slope_bounds[0])
    upper = None if slope_bounds[1] is None else parse_exact(slope_bounds[1])
    if m < 0 or (upper is not None and upper < m):
        raise ValueError("slope bounds must obey 0 <= lower <= upper")
    if isinstance(rectangles, (str, bytes, Mapping)):
        raise TypeError("supply a bounded iterable of rectangles")
    try:
        iterator = iter(rectangles)
    except TypeError as exc:
        raise ValueError("supply a bounded iterable of rectangles") from exc
    normalized, entries, ledger = [], [], _Ledger()
    lower_endpoint, upper_endpoint = (
        ("right", "left") if input_mode == "some" else ("left", "right")
    )
    for index, value in enumerate(iterator):
        if index >= MAX_RECTANGLES:
            raise ValueError("response rectangle count exceeds the limit")
        rectangle = _rectangle(value)
        a, b = rectangle.input
        low, high = rectangle.output
        ledger.charge(a, b, low, high)
        normalized.append(rectangle)
        entries.extend(
            [
                (
                    b if input_mode == "some" else a,
                    EndpointConstraint(index, lower_endpoint, "lower", low),
                ),
                (
                    a if input_mode == "some" else b,
                    EndpointConstraint(index, upper_endpoint, "upper", high),
                ),
            ]
        )
    if not normalized:
        raise ValueError("supply at least one response rectangle")
    largest_x = max(
        (x for x, _ in entries),
        key=lambda x: max(abs(x.numerator).bit_length(), x.denominator.bit_length()),
    )
    ledger.charge(
        largest_x, multiplier=2 * len(entries) * max(1, math.ceil(math.log2(len(entries))))
    )
    ordered = sorted(entries, key=lambda entry: entry[0])
    groups, origins = [], []
    for x, constraint in ordered:
        if groups and groups[-1].input == x:
            previous, (lo_origin, hi_origin) = groups[-1], origins[-1]
            lo, hi = previous.lower, previous.upper
            if constraint.bound == "lower" and (lo is None or constraint.value > lo):
                lo, lo_origin = constraint.value, constraint
            if constraint.bound == "upper" and (hi is None or constraint.value < hi):
                hi, hi_origin = constraint.value, constraint
            groups[-1] = RectangleResponseBand(
                x,
                lo,
                hi,
                tuple(dict.fromkeys((*previous.source_indices, constraint.source_index))),
                (*previous.endpoint_constraints, constraint),
            )
            origins[-1] = lo_origin, hi_origin
        else:
            is_lower = constraint.bound == "lower"
            groups.append(
                RectangleResponseBand(
                    x,
                    constraint.value if is_lower else None,
                    None if is_lower else constraint.value,
                    (constraint.source_index,),
                    (constraint,),
                )
            )
            origins.append((constraint, None) if is_lower else (None, constraint))

    def incompatible(proof):
        return RectangleCalibration(
            "incompatible",
            tuple(normalized),
            tuple(groups),
            (),
            (),
            (),
            proof,
            (m, upper),
            input_mode,
            ledger.work,
        )

    for group, (lo_origin, hi_origin) in zip(groups, origins):
        if group.lower is not None and group.upper is not None and group.lower > group.upper:
            return incompatible(
                _proof(
                    "endpoint_intersection",
                    lo_origin,
                    hi_origin,
                    group.input,
                    group.lower,
                    group.upper,
                )
            )
    lows, highs = [groups[0].lower], [groups[0].upper]
    low_origins, high_origins = [origins[0][0]], [origins[0][1]]
    for i in range(1, len(groups)):
        delta = ledger.sub(groups[i].input, groups[i - 1].input)
        lo, hi = groups[i].lower, groups[i].upper
        lo_origin, hi_origin = origins[i]
        if lows[-1] is not None:
            implied = ledger.add(lows[-1], ledger.mul(m, delta))
            if lo is None or implied > lo:
                lo, lo_origin = implied, low_origins[-1]
        if upper is not None and highs[-1] is not None:
            implied = ledger.add(highs[-1], ledger.mul(upper, delta))
            if hi is None or implied < hi:
                hi, hi_origin = implied, high_origins[-1]
        if lo is not None and hi is not None and lo > hi:
            return incompatible(
                _proof("slope_bounds", lo_origin, hi_origin, groups[i].input, lo, hi)
            )
        lows.append(lo)
        highs.append(hi)
        low_origins.append(lo_origin)
        high_origins.append(hi_origin)
    for i in range(len(groups) - 2, -1, -1):
        delta = ledger.sub(groups[i + 1].input, groups[i].input)
        if highs[i + 1] is not None:
            highs[i] = _min_upper(highs[i], ledger.sub(highs[i + 1], ledger.mul(m, delta)))
        if upper is not None and lows[i + 1] is not None:
            lows[i] = _max_lower(lows[i], ledger.sub(lows[i + 1], ledger.mul(upper, delta)))
    bands = tuple(
        RectangleResponseBand(g.input, lo, hi, g.source_indices, g.endpoint_constraints)
        for g, lo, hi in zip(groups, lows, highs)
    )
    # Some-mode first endpoint has a finite upper; all-mode first has a finite
    # lower. Thus this always selects a genuine finite value, with no truncation.
    first = bands[0].lower if bands[0].lower is not None else bands[0].upper
    witness = [ResponseWitnessPoint(bands[0].input, first)]
    for i in range(1, len(bands)):
        delta = ledger.sub(bands[i].input, bands[i - 1].input)
        value = ledger.add(witness[-1].output, ledger.mul(m, delta))
        if bands[i].lower is not None:
            value = max(value, bands[i].lower)
        witness.append(ResponseWitnessPoint(bands[i].input, value))
    assignments = _assignments(normalized, witness, ledger)
    return RectangleCalibration(
        "compatible",
        tuple(normalized),
        tuple(groups),
        bands,
        tuple(witness),
        assignments,
        None,
        (m, upper),
        input_mode,
        ledger.work,
    )
