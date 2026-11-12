"""Exact conditional feasibility of one scalar nondecreasing response.

Input knots and output bands are supplied exact numbers, not estimated radiance or
certified evaluations of an optical model. Adjacent slope constraints suffice on a
sorted scalar domain. Exact forward/backward propagation yields tight node bands;
a piecewise-linear witness proves compatibility. This does not calibrate a camera,
correct an image or qualify geometry/noise inferred from a photograph.
"""

import math
import re
from bisect import bisect_left
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

MAX_NODES = 1024
MAX_DECIMAL_DIGITS = 40
MAX_DECIMAL_EXPONENT = 64
MAX_STRING_LENGTH = 160
MAX_INPUT_BITS = 512
MAX_RESULT_BITS = 8192
MAX_WORK = 250_000_000
_DECIMAL = re.compile(r"([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d{1,3}))?\Z", re.ASCII)


@dataclass(frozen=True)
class ResponseNode:
    input: object
    output: tuple[object, object]


@dataclass(frozen=True)
class ResponseInterval:
    lower: Fraction
    upper: Fraction


@dataclass(frozen=True)
class ResponseBand:
    input: Fraction
    lower: Fraction
    upper: Fraction
    source_indices: tuple[int, ...]


@dataclass(frozen=True)
class ResponseWitnessPoint:
    input: Fraction
    output: Fraction


@dataclass(frozen=True)
class ResponseContradiction:
    """Two supplied bounds imply implied_lower > implied_upper at at_input.

    lower_source's original lower output is transported forward by lower_slope.
    upper_source's original upper output is transported forward by upper_slope;
    upper_slope=None is permitted only when that source is already at at_input.
    """

    kind: str
    lower_source: int
    upper_source: int
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
            raise ValueError("exact response arithmetic exceeds the work limit")
        self.work += amount

    def result(self, value):
        if max(abs(value.numerator).bit_length(), value.denominator.bit_length()) > MAX_RESULT_BITS:
            raise ValueError("exact response result exceeds the rational-size limit")
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


def parse_exact(value):
    """Parse one bounded exact API value; this does not certify a physical input.

    Decimal strings are interpreted as the exact declared decimal, integers and
    Fractions retain their exact values, and floats/bools are refused. This helper
    can validate query inputs even when a calibration is incompatible.
    """
    if isinstance(value, (bool, float)):
        raise TypeError(
            "supply exact decimal strings, integers or Fractions; floats/bools are refused"
        )
    if isinstance(value, (int, Fraction)):
        result = Fraction(value)
    elif isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise ValueError("exact decimal string exceeds the length limit")
        match = _DECIMAL.fullmatch(value)
        if match is None:
            raise ValueError("supply a finite exact decimal string")
        sign, whole, fractional, leading_fraction, exponent = match.groups()
        whole, fractional = (
            (whole or ""),
            (leading_fraction if leading_fraction is not None else fractional or ""),
        )
        digits = (whole + fractional).lstrip("0")
        exponent = int(exponent or "0")
        if abs(exponent) > MAX_DECIMAL_EXPONENT or len(digits) > MAX_DECIMAL_DIGITS:
            raise ValueError("exact decimal exceeds the digit/exponent limit")
        power = exponent - len(fractional)
        if digits and abs(power + len(digits) - 1) > MAX_DECIMAL_EXPONENT:
            raise ValueError("exact decimal exceeds the adjusted-exponent limit")
        if not digits:
            result = Fraction(0)
        else:
            coefficient = int(digits) * (-1 if sign == "-" else 1)
            result = (
                Fraction(coefficient * 10**power)
                if power >= 0
                else Fraction(coefficient, 10 ** (-power))
            )
    else:
        raise TypeError("supply exact decimal strings, integers or Fractions")
    if max(abs(result.numerator).bit_length(), result.denominator.bit_length()) > MAX_INPUT_BITS:
        raise ValueError("exact input exceeds the rational-size limit")
    return result


def _node(value):
    if isinstance(value, ResponseNode):
        x, band = value.input, value.output
    elif isinstance(value, Mapping) and set(value) == {"input", "output"}:
        x, band = value["input"], value["output"]
    else:
        raise ValueError("each node needs exactly input and output")
    if not isinstance(band, (tuple, list)) or len(band) != 2:
        raise ValueError("node output needs a closed interval")
    x, low, high = parse_exact(x), parse_exact(band[0]), parse_exact(band[1])
    if low > high:
        raise ValueError("node output interval endpoints must be ordered")
    return x, low, high


def _rational(value):
    return (
        str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    )


def _band_dict(value):
    return {
        "input": _rational(value.input),
        "output": [_rational(value.lower), _rational(value.upper)],
        "source_indices": list(value.source_indices),
    }


@dataclass(frozen=True)
class ResponseCalibration:
    status: str
    source_groups: tuple[ResponseBand, ...]
    nodes: tuple[ResponseBand, ...]
    witness: tuple[ResponseWitnessPoint, ...]
    contradiction: ResponseContradiction | None
    slope_bounds: tuple[Fraction, Fraction | None]
    work: int

    def query(self, x):
        """Tight marginal output envelope inside the supplied knot domain only.

        Arbitrary independent choices from multiple query bands need not belong to
        one shared response. Append observations as nodes and recalibrate to test
        joint feasibility. The returned witness need not attain these envelopes.
        """
        if self.status != "compatible":
            raise ValueError("an incompatible response has no query envelope")
        x = parse_exact(x)
        if x < self.nodes[0].input or x > self.nodes[-1].input:
            raise ValueError("query lies outside the supplied knot domain")
        index = bisect_left(tuple(node.input for node in self.nodes), x)
        if self.nodes[index].input == x:
            return ResponseInterval(self.nodes[index].lower, self.nodes[index].upper)
        left, right = self.nodes[index - 1], self.nodes[index]
        ledger = _Ledger()
        dx, remaining = ledger.sub(x, left.input), ledger.sub(right.input, x)
        lower_slope, upper_slope = self.slope_bounds
        low = ledger.add(left.lower, ledger.mul(lower_slope, dx))
        high = ledger.sub(right.upper, ledger.mul(lower_slope, remaining))
        if upper_slope is not None:
            low = max(low, ledger.sub(right.lower, ledger.mul(upper_slope, remaining)))
            high = min(high, ledger.add(left.upper, ledger.mul(upper_slope, dx)))
        return ResponseInterval(low, high)

    def to_dict(self):
        """JSON-compatible exact rational strings, never rounded floating endpoints."""
        proof = self.contradiction
        return {
            "status": self.status,
            "conditional_on": "Exact supplied input knots, output intervals and common slope bounds; not physical camera calibration.",
            "slope_bounds": [
                _rational(self.slope_bounds[0]),
                None if self.slope_bounds[1] is None else _rational(self.slope_bounds[1]),
            ],
            "source_groups": [_band_dict(group) for group in self.source_groups],
            "nodes": [_band_dict(node) for node in self.nodes],
            "witness": [
                {"input": _rational(point.input), "output": _rational(point.output)}
                for point in self.witness
            ],
            "contradiction": None
            if proof is None
            else {
                "kind": proof.kind,
                "lower_source": proof.lower_source,
                "upper_source": proof.upper_source,
                "at_input": _rational(proof.at_input),
                "implied_lower": _rational(proof.implied_lower),
                "implied_upper": _rational(proof.implied_upper),
            },
            "work": self.work,
        }


def calibrate_response(nodes, *, slope_bounds=("0", None)):
    """Feasibility of one common response on the closed supplied knot domain.

    Nodes are ResponseNode objects or mappings with exactly input/output fields.
    All numeric inputs are decimal strings, integers or Fractions. Duplicate input
    values constrain one common output, so their bands are intersected. The response
    is nondecreasing with common slope lower<=secant<=upper; None omits an upper
    bound. Slopes use output units per input unit. Piecewise-linear interpolation
    of the witness obeys those bounds; no extrapolation or inverse is asserted.

    Individual valid bands that contradict collectively return incompatible and an
    exact source-indexed inequality. Invalid numeric types raise TypeError; invalid/resource values raise ValueError
    and never return a partial mathematical conclusion. Work counts bounded rational
    operand-bit units, including a conservative sort allowance; not wall-clock time.
    """
    if not isinstance(slope_bounds, (tuple, list)) or len(slope_bounds) != 2:
        raise ValueError("slope_bounds needs a nonnegative lower and optional upper")
    lower = parse_exact(slope_bounds[0])
    upper = None if slope_bounds[1] is None else parse_exact(slope_bounds[1])
    if lower < 0 or (upper is not None and upper < lower):
        raise ValueError("slope bounds must obey 0 <= lower <= upper")
    if isinstance(nodes, (str, bytes, Mapping)):
        raise TypeError("supply a bounded iterable of response nodes")
    try:
        iterator = iter(nodes)
    except TypeError as exc:
        raise ValueError("supply a bounded iterable of response nodes") from exc
    ledger, normalized = _Ledger(), []
    for index, value in enumerate(iterator):
        if index >= MAX_NODES:
            raise ValueError("response node count exceeds the limit")
        item = _node(value)
        ledger.charge(*item)
        normalized.append((*item, index))
    if not normalized:
        raise ValueError("supply at least one response node")
    largest_x = max(
        (item[0] for item in normalized),
        key=lambda x: max(abs(x.numerator).bit_length(), x.denominator.bit_length()),
    )
    ledger.charge(
        largest_x, multiplier=2 * len(normalized) * max(1, math.ceil(math.log2(len(normalized))))
    )
    ordered = sorted(normalized, key=lambda item: item[0])
    groups, origins = [], []
    for x, lo, hi, index in ordered:
        if groups and x == groups[-1].input:
            previous = groups[-1]
            low_origin, high_origin = origins[-1]
            if lo > previous.lower:
                low_origin = index
            if hi < previous.upper:
                high_origin = index
            groups[-1] = ResponseBand(
                x,
                max(lo, previous.lower),
                min(hi, previous.upper),
                previous.source_indices + (index,),
            )
            origins[-1] = low_origin, high_origin
        else:
            groups.append(ResponseBand(x, lo, hi, (index,)))
            origins.append((index, index))
    for group, (low_origin, high_origin) in zip(groups, origins):
        if group.lower > group.upper:
            proof = ResponseContradiction(
                "duplicate_input", low_origin, high_origin, group.input, group.lower, group.upper
            )
            return ResponseCalibration(
                "incompatible", tuple(groups), (), (), proof, (lower, upper), ledger.work
            )
    lows, highs = [groups[0].lower], [groups[0].upper]
    low_origins, high_origins = [origins[0][0]], [origins[0][1]]
    for i in range(1, len(groups)):
        delta = ledger.sub(groups[i].input, groups[i - 1].input)
        implied_low = ledger.add(lows[-1], ledger.mul(lower, delta))
        lo, lo_origin = groups[i].lower, origins[i][0]
        if implied_low > lo:
            lo, lo_origin = implied_low, low_origins[-1]
        hi, hi_origin = groups[i].upper, origins[i][1]
        if upper is not None:
            implied_high = ledger.add(highs[-1], ledger.mul(upper, delta))
            if implied_high < hi:
                hi, hi_origin = implied_high, high_origins[-1]
        if lo > hi:
            proof = ResponseContradiction(
                "slope_bounds", lo_origin, hi_origin, groups[i].input, lo, hi
            )
            return ResponseCalibration(
                "incompatible", tuple(groups), (), (), proof, (lower, upper), ledger.work
            )
        lows.append(lo)
        highs.append(hi)
        low_origins.append(lo_origin)
        high_origins.append(hi_origin)
    for i in range(len(groups) - 2, -1, -1):
        delta = ledger.sub(groups[i + 1].input, groups[i].input)
        highs[i] = min(highs[i], ledger.sub(highs[i + 1], ledger.mul(lower, delta)))
        if upper is not None:
            lows[i] = max(lows[i], ledger.sub(lows[i + 1], ledger.mul(upper, delta)))
    bands = tuple(
        ResponseBand(g.input, lo, hi, g.source_indices) for g, lo, hi in zip(groups, lows, highs)
    )
    witness = [ResponseWitnessPoint(bands[0].input, bands[0].lower)]
    for i in range(1, len(bands)):
        delta = ledger.sub(bands[i].input, bands[i - 1].input)
        value = max(bands[i].lower, ledger.add(witness[-1].output, ledger.mul(lower, delta)))
        witness.append(ResponseWitnessPoint(bands[i].input, value))
    return ResponseCalibration(
        "compatible", tuple(groups), bands, tuple(witness), None, (lower, upper), ledger.work
    )
