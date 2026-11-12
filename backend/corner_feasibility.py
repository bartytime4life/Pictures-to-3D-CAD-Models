"""Conditional radius sets for a fixed Gaussian-blurred rounded right corner.

The material is the positive quadrant minus 0<=x<=r, 0<=y<h_r(x), where
h_r(x)=r-sqrt(2*r*x-x*x). Rectangular cutout covers and outward Decimal
arithmetic enclose continuous probabilities. Nested cutouts bound whole radius
intervals; this is not sampled-grid exclusion or an optical calibration.
"""

from collections import Counter, deque
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation
from itertools import pairwise

from .decimal_bounds import Interval, normal_cdf

FORMAT = "pictures-to-cad-corner-feasibility"
_FIELDS = {
    "format", "version", "coordinate_unit", "points", "blur_sigma",
    "level_intervals", "radius_domain", "radius_resolution", "max_boxes", "cells",
}
_ZERO, _ONE = Decimal(0), Decimal(1)
# These contexts choose exact finite partition coordinates, not numerical bounds.
# The covers are valid for any increasing partition, including rounded choices.
_PARTITION = Context(prec=60, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                     capitals=1, clamp=0, flags=[], traps=[InvalidOperation])


def _number(value, field, *, string_only=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError(f"{field}: use a finite decimal string")  # noqa: TRY004 - schema error
    if string_only and not isinstance(value, str):
        raise ValueError(f"{field}: use a decimal string, not a JSON number")
    if isinstance(value, str) and len(value) > 100:
        raise ValueError(f"{field}: decimal text is too long")
    try:
        result = Decimal(value, context=_PARTITION)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field}: invalid decimal") from exc
    if (not result.is_finite() or len(result.as_tuple().digits) > 40
            or (result != 0 and not -12 <= result.adjusted() <= 12)):
        raise ValueError(f"{field}: require finite decimal, <=40 digits, exponent -12..12")
    return result


def _pair(value, field, *, string_only=False):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field}: expected two values")
    return tuple(_number(v, f"{field}[{i}]", string_only=string_only)
                 for i, v in enumerate(value))


def _integer(value, field, upper):
    if type(value) is not int or not 1 <= value <= upper:
        raise ValueError(f"{field}: expected integer from 1 to {upper}")
    return value


@dataclass(frozen=True)
class Config:
    coordinate_unit: str
    points: tuple
    blur_sigma: tuple
    level_intervals: tuple
    radius_domain: Interval
    radius_resolution: Decimal
    max_boxes: int
    cells: int


def parse_config(raw):
    """Validate the explicit v1 model, observations, prior and work limits."""
    if not isinstance(raw, dict):
        raise ValueError("input: expected a JSON object")  # noqa: TRY004 - schema error
    if any(not isinstance(key, str) for key in raw):
        raise ValueError("input fields: require string keys")
    missing, unknown = _FIELDS - raw.keys(), raw.keys() - _FIELDS
    if missing or unknown:
        raise ValueError(f"input fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    if raw["format"] != FORMAT or type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("format/version: require pictures-to-cad-corner-feasibility version 1")
    if raw["coordinate_unit"] not in ("px", "mm"):
        raise ValueError("coordinate_unit: use px or mm consistently")
    points = raw["points"]
    if not isinstance(points, list) or not 1 <= len(points) <= 16:
        raise ValueError("points: require 1..16 observations")
    points = tuple(_pair(p, f"points[{i}]", string_only=True) for i, p in enumerate(points))
    if any(v.copy_abs() > 1_000_000 for p in points for v in p):
        raise ValueError("points: coordinate magnitude exceeds 1000000")
    sigma = _pair(raw["blur_sigma"], "blur_sigma", string_only=True)
    if any(not Decimal(".000001") <= s <= 1_000_000 for s in sigma):
        raise ValueError("blur_sigma: require 0.000001..1000000")
    levels = raw["level_intervals"]
    if not isinstance(levels, list) or len(levels) != len(points):
        raise ValueError("level_intervals: require one interval per point")
    levels = tuple(Interval(*_pair(v, f"level_intervals[{i}]", string_only=True))
                   for i, v in enumerate(levels))
    if any(v.lo < 0 or v.hi > 1 for v in levels):
        raise ValueError("level_intervals: normalized linear-light bounds must lie in [0,1]")
    domain = Interval(*_pair(raw["radius_domain"], "radius_domain", string_only=True))
    if domain.lo < 0 or domain.hi > 1_000_000:
        raise ValueError("radius_domain: require 0 <= lower <= upper <= 1000000")
    resolution = _number(raw["radius_resolution"], "radius_resolution", string_only=True)
    if not 0 < resolution <= 1_000_000:
        raise ValueError("radius_resolution: require 0 < value <= 1000000")
    cells = _integer(raw["cells"], "cells", 256)
    boxes = _integer(raw["max_boxes"], "max_boxes", 512)
    if cells * len(points) * (boxes + 1) > 65536:
        raise ValueError("work limit: cells * points * (max_boxes + 1) must not exceed 65536")
    return Config(raw["coordinate_unit"], points, sigma, levels, domain, resolution, boxes, cells)


def _probability(value):
    # Intersection with a mathematically known range cannot lose the true value.
    lo, hi = max(_ZERO, value.lo), min(_ONE, value.hi)
    if lo > hi:
        raise ArithmeticError("probability enclosure is inconsistent")
    return Interval(lo, hi)


def _mass(lo, hi, mean, sigma):
    return _probability(normal_cdf((hi - mean) / sigma) - normal_cdf((lo - mean) / sigma))


def _height(radius, x):
    if x == 0:
        return Interval.point(radius)
    if x == radius:
        return Interval.point(0)
    r, t = Interval.point(radius), Interval.point(x)
    radicand = 2 * r * t - t * t
    root = Interval(max(_ZERO, radicand.lo), radicand.hi).sqrt()
    height = r - root
    return Interval(max(_ZERO, height.lo), min(radius, height.hi))


def level_bounds(point, blur_sigma, radius, *, cells=32):
    """Enclose the material probability at one exact point and radius.

    Cells partition the cutout in x; its decreasing height gives inner/outer
    rectangles. No unbounded quadrature error is silently treated as zero.
    Float inputs are deliberately refused; use Decimal or decimal text.
    """
    px, py = _pair(point, "point")
    sx, sy = _pair(blur_sigma, "blur_sigma")
    radius = _number(radius, "radius")
    cells = _integer(cells, "cells", 256)
    if (any(v.copy_abs() > 1_000_000 for v in (px, py))
            or not 0 <= radius <= 1_000_000
            or any(not Decimal(".000001") <= s <= 1_000_000 for s in (sx, sy))):
        raise ValueError("point/radius/blur_sigma outside supported numerical domain")
    return _level_bounds((px, py), (sx, sy), radius, cells)


def _level_bounds(point, blur_sigma, radius, cells):
    # Already validated inputs; internally chosen radius endpoints may have more
    # digits or smaller exponents than the external text-input limits.
    px, py = point
    sx, sy = blur_sigma
    px, py, sx, sy = map(Interval.point, (px, py, sx, sy))
    wedge = normal_cdf(px / sx) * normal_cdf(py / sy)
    if radius == 0:
        return _probability(wedge)
    partition = [_PARTITION.divide(_PARTITION.multiply(radius, Decimal(i)), Decimal(cells))
                 for i in range(cells + 1)]
    partition[0], partition[-1] = _ZERO, radius
    if any(a >= b for a, b in pairwise(partition)):
        raise ArithmeticError("cutout partition cannot be represented")
    heights = [_height(radius, x) for x in partition]
    zero = Interval.point(0)
    lower = upper = zero
    y_masses = [_mass(zero, h, py, sy) for h in heights]
    for i, (a, b) in enumerate(pairwise(partition)):
        x_mass = _mass(Interval.point(a), Interval.point(b), px, sx)
        lower = lower + x_mass * y_masses[i + 1]
        upper = upper + x_mass * y_masses[i]
    cutout = Interval(lower.lo, upper.hi)
    return _probability(wedge - cutout)


def radius_box_bounds(point, blur_sigma, radius_box, *, cells=32):
    """Enclose all levels in a radius box using nested-cutout monotonicity."""
    if not isinstance(radius_box, Interval):
        raise TypeError("radius_box must be an Interval")
    low = level_bounds(point, blur_sigma, radius_box.hi, cells=cells).lo
    high = level_bounds(point, blur_sigma, radius_box.lo, cells=cells).hi
    return Interval(low, high)


def _merged(boxes):
    result = []
    for box in sorted(boxes, key=lambda b: b.lo):
        if result and box.lo <= result[-1].hi:
            result[-1] = Interval(result[-1].lo, max(result[-1].hi, box.hi))
        else:
            result.append(box)
    return result


def _serialized(boxes):
    return [[str(box.lo), str(box.hi)] for box in _merged(boxes)]


def analyze(raw):
    """Enclose conditional feasible radii; never discard unresolved work.

    A complete output enclosure inside all level intervals accepts a box.
    Strict disjointness at any point excludes it. Remaining boxes are bisected
    or retained unknown at the width/work/numerical limit, including all queued
    boxes on budget exhaustion. No physical noise/discrepancy bound is inferred.
    """
    config = parse_config(raw)
    pending = deque([config.radius_domain])
    accepted, excluded, unknown = [], [], []
    reasons = Counter()
    evaluated, level_evaluations, cache = 0, 0, {}

    def levels(radius):
        nonlocal level_evaluations
        if radius not in cache:
            measured = []
            for point in config.points:
                level_evaluations += 1
                measured.append(_level_bounds(point, config.blur_sigma, radius, config.cells))
            cache[radius] = tuple(measured)
        return cache[radius]

    while pending and evaluated < config.max_boxes:
        box = pending.popleft()
        evaluated += 1
        try:
            lows, highs = levels(box.hi), levels(box.lo)
            images = tuple(Interval(lo.lo, hi.hi) for lo, hi in zip(lows, highs))
        except ArithmeticError:
            unknown.append(box)
            reasons["numerical_enclosure"] += 1
            continue
        if any(image.hi < target.lo or image.lo > target.hi
               for image, target in zip(images, config.level_intervals)):
            excluded.append(box)
        elif all(target.lo <= image.lo and image.hi <= target.hi
                 for image, target in zip(images, config.level_intervals)):
            accepted.append(box)
        elif (Interval.point(box.hi) - box.lo).hi <= config.radius_resolution:
            unknown.append(box)
            reasons["radius_resolution"] += 1
        else:
            middle = _PARTITION.divide(_PARTITION.add(box.lo, box.hi), Decimal(2))
            if not box.lo < middle < box.hi:
                unknown.append(box)
                reasons["midpoint_stagnation"] += 1
            else:
                pending.extend((Interval(box.lo, middle), Interval(middle, box.hi)))
    budget_exhausted = bool(pending)
    unknown.extend(pending)
    if pending:
        reasons["work_budget"] += len(pending)
    outer = _merged(accepted + unknown)
    status = ("conditional_compatible" if accepted else
              "conditional_incompatible" if not outer else "unknown")
    return {
        "format": FORMAT + "-result", "version": 1,
        "status": status, "coordinate_unit": config.coordinate_unit,
        "inner": _serialized(accepted), "outer": _serialized(outer),
        "accepted": _serialized(accepted), "unknown": _serialized(unknown),
        "excluded": _serialized(excluded),
        "unknown_reason_counts": dict(sorted(reasons.items())),
        "coverage_complete": True, "classification_complete": not unknown,
        "budget_exhausted": budget_exhausted, "boxes_evaluated": evaluated,
        "level_evaluations": level_evaluations,
        "prior_ceiling_reached": bool(outer and outer[-1].hi == config.radius_domain.hi),
        "assumptions": {
            "geometry": "fixed apex (0,0), +x/+y material, circular cutout, right angle",
            "blur": "fixed independent axis-aligned Gaussian, supplied sigmas",
            "observations": "exact point coordinates and supplied closed linear-light level intervals",
            "not_inferred": "pose, blur, coordinate error, tone response, discrepancy or physical accuracy",
            "radius_resolution": "subdivision stopping width, not physical uncertainty",
        },
    }
