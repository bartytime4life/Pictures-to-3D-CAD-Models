"""Conditional corner observations formed by known fixed signed stencils.

Each term averages the same Gaussian-blurred corner over a known product
aperture. A signed sum is a linear functional, not a probability or a normalized
mean. It need not be monotone in radius: every term is enclosed over the whole
radius box before its signed contribution is added. No weights are normalized
and no composite value is clamped to the probability range.
"""

from dataclasses import replace
from decimal import Decimal
from functools import lru_cache

from . import corner_blur_domains as joint
from . import corner_feasibility as fixed
from . import corner_pixel_apertures as pixels
from .decimal_bounds import Interval

_FIELDS = (joint._FIELDS - {"points"}) | {"sampling_stencils"}
_TERM_FIELDS = {"weight", "pixel_aperture"}
_ZERO = Decimal(0)


def _coefficient_decimal(coefficient, exponent):
    """Construct an exact finite decimal without using the active context."""
    if coefficient == 0:
        return _ZERO
    sign = int(coefficient < 0)
    coefficient = abs(coefficient)
    while coefficient % 10 == 0:
        coefficient //= 10
        exponent += 1
    return Decimal((sign, tuple(map(int, str(coefficient))), exponent))


def _weight_totals(stencil):
    # Common-exponent integer arithmetic is exact even under hostile Decimal
    # contexts. Ignore zero exponents: inputs such as 0E-999999 denote zero and
    # must not create an enormous, unnecessary integer scale.
    weights = [weight for weight, _ in stencil if weight != 0]
    if not weights:
        return {"weight_sum": _ZERO, "negative_sum": _ZERO,
                "positive_sum": _ZERO, "l1": _ZERO}
    exponent = min(weight.as_tuple().exponent for weight in weights)
    negative = positive = 0
    for weight in weights:
        parts = weight.as_tuple()
        coefficient = 0
        for digit in parts.digits:
            coefficient = 10 * coefficient + digit
        coefficient *= 10 ** (parts.exponent - exponent)
        if parts.sign:
            negative -= coefficient
        else:
            positive += coefficient
    return {"weight_sum": _coefficient_decimal(positive + negative, exponent),
            "negative_sum": _coefficient_decimal(negative, exponent),
            "positive_sum": _coefficient_decimal(positive, exponent),
            "l1": _coefficient_decimal(positive - negative, exponent)}


def _stencil(value, field="sampling_stencil", *, string_only=False):
    if not isinstance(value, (list, tuple)) or not 1 <= len(value) <= 256:
        raise ValueError(f"{field}: require 1..256 signed aperture terms")
    terms = []
    for i, term in enumerate(value):
        label = f"{field}[{i}]"
        if not isinstance(term, dict) or term.keys() != _TERM_FIELDS:
            raise ValueError(f"{label}: require exactly weight and pixel_aperture")
        weight = fixed._number(term["weight"], f"{label}.weight", string_only=string_only)
        if weight.copy_abs() > 4:
            raise ValueError(f"{label}.weight: magnitude must not exceed 4")
        aperture = pixels._aperture(term["pixel_aperture"], f"{label}.pixel_aperture",
                                    string_only=string_only)
        terms.append((weight, aperture))
    result = tuple(terms)
    if _weight_totals(result)["l1"] > 4:
        raise ValueError(f"{field}: sum of absolute weights must not exceed 4")
    return result


def _summary(stencil):
    totals = _weight_totals(stencil)
    return {**{key: str(value) for key, value in totals.items()},
            "constant_preserving": totals["weight_sum"] == 1,
            "terms": len(stencil),
            "nonzero_terms": sum(weight != 0 for weight, _ in stencil)}


@lru_cache(maxsize=16)
def _coalesced(stencil):
    """Combine identical apertures exactly, retaining raw input statistics."""
    groups = {}
    for term in stencil:
        weight, aperture = term
        if weight != 0:
            groups.setdefault(aperture, []).append(term)
    result = []
    for aperture, terms in groups.items():
        weight = _weight_totals(terms)["weight_sum"]
        if weight != 0:
            result.append((weight, aperture))
    return tuple(result)


def parse_config(raw):
    """Validate fixed signed functionals, targets and their term-count work cap."""
    if not isinstance(raw, dict):
        raise ValueError("input: expected a JSON object")  # noqa: TRY004 - schema error
    if any(not isinstance(key, str) for key in raw):
        raise ValueError("input fields: require string keys")
    missing, unknown = _FIELDS - raw.keys(), raw.keys() - _FIELDS
    if missing or unknown:
        raise ValueError(f"input fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    if raw["format"] != fixed.FORMAT or type(raw["version"]) is not int or raw["version"] != 4:
        raise ValueError("format/version: require pictures-to-cad-corner-feasibility version 4")
    supplied = raw["sampling_stencils"]
    if not isinstance(supplied, list) or not 1 <= len(supplied) <= 16:
        raise ValueError("sampling_stencils: require 1..16 signed observations")
    stencils = tuple(_stencil(value, f"sampling_stencils[{i}]", string_only=True)
                     for i, value in enumerate(supplied))
    levels = raw["level_intervals"]
    if not isinstance(levels, list) or len(levels) != len(stencils):
        raise ValueError("level_intervals: require one interval per sampling stencil")
    levels = tuple(Interval(*fixed._pair(value, f"level_intervals[{i}]", string_only=True))
                   for i, value in enumerate(levels))
    if any(value.lo < -4 or value.hi > 4 for value in levels):
        raise ValueError("level_intervals: signed-functional bounds must lie in [-4,4]")
    cells = fixed._integer(raw["cells"], "cells", 256)
    boxes = fixed._integer(raw["max_boxes"], "max_boxes", 512)
    terms = sum(weight != 0 for stencil in stencils for weight, _ in stencil)
    if 2 * cells * terms * boxes > 65536:
        raise ValueError("work limit: 2 * cells * nonzero terms * max_boxes must not exceed 65536")
    # Reuse the common geometry/blur/resolution validation with inexpensive valid
    # dummy observations. Actual signed targets and term-based work accounting
    # were checked above, independently of the legacy [0,1] observation contract.
    common = {key: value for key, value in raw.items() if key in joint._FIELDS}
    common.update(version=2, points=[["0", "0"] for _ in stencils],
                  level_intervals=[["0", "1"] for _ in stencils], cells=1, max_boxes=1)
    config = joint.parse_config(common)
    return replace(config, fixed=replace(config.fixed, points=stencils,
                                         level_intervals=levels, cells=cells, max_boxes=boxes))


def _box_bounds(stencil, blur_domains, radius_box, cells, *, aperture_evaluator=None):
    """Enclose every signed value over the whole joint radius/blur box."""
    evaluate = pixels._level_bounds if aperture_evaluator is None else aperture_evaluator
    total = Interval.point(0)
    for weight, aperture in _coalesced(stencil):
        lower = evaluate(aperture, blur_domains, radius_box.hi, cells)
        upper = evaluate(aperture, blur_domains, radius_box.lo, cells)
        # Each aperture mean is radius-monotone, unlike their signed sum.
        image = Interval(lower.lo, upper.hi)
        total = total + weight * image
    totals = _weight_totals(stencil)
    known = Interval(totals["negative_sum"], totals["positive_sum"])
    low, high = max(total.lo, known.lo), min(total.hi, known.hi)
    if low > high:
        raise ArithmeticError("signed-stencil enclosures are inconsistent")
    return Interval(low, high)


def stencil_box_bounds(stencil, blur_domains, radius_box, *, cells=32):
    """Enclose a fixed signed functional over a complete radius/blur box.

    ``radius_box`` must be an Interval; supplied weights and coordinates accept
    finite Decimal/int/text values, not Python floats or booleans.
    """
    stencil = _stencil(stencil)
    domains = joint._blur_domains(blur_domains)
    if not isinstance(radius_box, Interval):
        raise ValueError("radius_box: require an Interval")  # noqa: TRY004 - API contract
    low = fixed._number(radius_box.lo, "radius_box.lower")
    high = fixed._number(radius_box.hi, "radius_box.upper")
    if not 0 <= low <= high <= 1_000_000:
        raise ValueError("radius_box outside supported numerical domain")
    cells = fixed._integer(cells, "cells", 256)
    return _box_bounds(stencil, domains, radius_box, cells)


def stencil_level_bounds(stencil, blur_domains, radius, *, cells=32):
    """Enclose an exact-radius signed value; this is not a probability."""
    radius = fixed._number(radius, "radius")
    return stencil_box_bounds(stencil, blur_domains, Interval.point(radius), cells=cells)


def analyze(raw):
    """Enclose joint feasible parameters without assuming composite monotonicity."""
    config = parse_config(raw)
    aperture_evaluations = 0

    @lru_cache(maxsize=4096)
    def evaluate(aperture, sigma, radius, cells):
        nonlocal aperture_evaluations
        aperture_evaluations += 1
        return pixels._level_bounds(aperture, sigma, radius, cells)

    def box_evaluator(stencil, sigma, radius, cells):
        return _box_bounds(stencil, tuple(sigma), radius, cells, aperture_evaluator=evaluate)

    result = joint._analyze(config, box_evaluator=box_evaluator)
    assumptions = {
        **result["assumptions"],
        "blur": "one common independent axis-aligned pre-aperture Gaussian within supplied sigma domains",
        "observations": "supplied closed bounds on fixed signed linear material-response functionals",
        "sampling_stencils": "known fixed weights and uniform PRODUCT apertures; degenerate axes are Dirac points",
        "measurement": "signed sum, not probability or normalized mean; no weight normalization or output clamping",
        "radius_enclosure": "whole-radius per-aperture covers summed with their signed weights; composite need not be monotone",
        "not_modelled": "unknown/varying weights, rotated/warped footprints, arbitrary intra-pixel response or nonlinear processing",
        "not_inferred": "weights, apertures, pose, coordinates, tone response, discrepancy or imageprocessor/physical calibration",
    }
    return {**result, "version": 4, "assumptions": assumptions,
            "stencil_summaries": [_summary(stencil) for stencil in config.fixed.points],
            "aperture_evaluations": aperture_evaluations}
