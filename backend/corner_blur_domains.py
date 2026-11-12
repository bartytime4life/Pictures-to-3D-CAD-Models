"""Conditional joint radius/blur sets; one common blur explains all observations.

Version 2 extends the fixed-corner developer analysis to supplied independent
Gaussian sigma domains. Interval divisions enclose blur dependence without a
monotonicity assumption in sigma. Radius monotonicity holds for each sigma and
thus uniformly over its domain. Only accepted/unknown parameter boxes are
projected to radius: projecting rejected nuisance boxes would be unsound.
"""

from collections import Counter, deque
from dataclasses import dataclass
from decimal import Decimal

from . import corner_feasibility as fixed
from .decimal_bounds import Interval, _normalizer

_FIELDS = (fixed._FIELDS - {"blur_sigma"}) | {"blur_sigma_intervals", "blur_resolution"}
PARAMETER_ORDER = ("radius", "sigma_x", "sigma_y")


@dataclass(frozen=True)
class Config:
    fixed: fixed.Config
    blur_domains: tuple
    blur_resolution: tuple


def _blur_domains(value, *, string_only=False):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("blur_sigma_intervals: require two closed intervals")
    result = []
    for i, pair in enumerate(value):
        if isinstance(pair, Interval) and not string_only:
            domain = pair
        else:
            domain = Interval(*fixed._pair(pair, f"blur_sigma_intervals[{i}]",
                                           string_only=string_only))
        if not Decimal(".000001") <= domain.lo <= domain.hi <= 1_000_000:
            raise ValueError("blur_sigma_intervals: require 0.000001 <= lower <= upper <= 1000000")
        result.append(domain)
    return tuple(result)


def parse_config(raw):
    """Validate version 2 without supplying any physical nuisance/error bounds."""
    if not isinstance(raw, dict):
        raise ValueError("input: expected a JSON object")  # noqa: TRY004 - schema error
    if any(not isinstance(key, str) for key in raw):
        raise ValueError("input fields: require string keys")
    missing, unknown = _FIELDS - raw.keys(), raw.keys() - _FIELDS
    if missing or unknown:
        raise ValueError(f"input fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    if raw["format"] != fixed.FORMAT or type(raw["version"]) is not int or raw["version"] != 2:
        raise ValueError("format/version: require pictures-to-cad-corner-feasibility version 2")
    domains = _blur_domains(raw["blur_sigma_intervals"], string_only=True)
    # Reuse the common observation/geometry validation, not the version-1 inference.
    common = {k: v for k, v in raw.items() if k in fixed._FIELDS}
    common.update(version=1, blur_sigma=[str(v.lo) for v in domains])
    config = fixed.parse_config(common)
    resolution = fixed._pair(raw["blur_resolution"], "blur_resolution", string_only=True)
    if any(not 0 < v <= 1_000_000 for v in resolution):
        raise ValueError("blur_resolution: require positive subdivision widths <= 1000000")
    if 2 * config.cells * len(config.points) * config.max_boxes > 65536:
        raise ValueError("work limit: 2 * cells * points * max_boxes must not exceed 65536")
    return Config(config, domains, resolution)


def parameter_level_bounds(point, blur_domains, radius, *, cells=32):
    """Enclose all levels at exact radius and every blur in two sigma domains."""
    point = fixed._pair(point, "point")
    domains = _blur_domains(blur_domains)
    radius = fixed._number(radius, "radius")
    cells = fixed._integer(cells, "cells", 256)
    if (any(v.copy_abs() > 1_000_000 for v in point)
            or not 0 <= radius <= 1_000_000):
        raise ValueError("point/radius outside supported numerical domain")
    return fixed._level_bounds_with_sigma(point, domains, radius, cells, x_mass_bound=_x_mass)


def _square(value):
    left, right = Interval.point(value.lo) * value.lo, Interval.point(value.hi) * value.hi
    low = Decimal(0) if value.lo <= 0 <= value.hi else min(left.lo, right.lo)
    return Interval(low, max(left.hi, right.hi))


def _x_mass(a, b, mean, sigma):
    # Both enclosures contain the same mass for EVERY sigma in the box. The
    # density cover scales with strip width, avoiding N-fold CDF dependency loss.
    cdf_mass = fixed._mass(Interval.point(a), Interval.point(b), mean, sigma)
    density = _normalizer() / sigma * (-_square((Interval(a, b) - mean) / sigma) / 2).exp()
    density_mass = fixed._probability((Interval.point(b) - a) * density)
    low, high = max(cdf_mass.lo, density_mass.lo), min(cdf_mass.hi, density_mass.hi)
    if low > high:
        raise ArithmeticError("Gaussian mass enclosures are inconsistent")
    return Interval(low, high)


def _serialized_boxes(boxes):
    return [[[str(axis.lo), str(axis.hi)] for axis in box] for box in boxes]


def analyze(raw):
    """Enclose joint feasible parameters and their existential radius projection.

    Rejection concerns one complete (radius,sigma_x,sigma_y) box, not its radius
    projection. Another blur box can explain the same radius. Full joint boxes
    and separate projected inner/outer sets keep that distinction reviewable.
    """
    config = parse_config(raw)
    common = config.fixed
    domain = (common.radius_domain, *config.blur_domains)
    resolutions = (common.radius_resolution, *config.blur_resolution)
    pending = deque([domain])
    accepted, unknown, excluded = [], [], []
    reasons = Counter()
    evaluated, level_evaluations, cache = 0, 0, {}

    def levels(radius, sigma):
        nonlocal level_evaluations
        key = (radius, *tuple(v for s in sigma for v in (s.lo, s.hi)))
        if key not in cache:
            values = []
            for point in common.points:
                level_evaluations += 1
                values.append(fixed._level_bounds_with_sigma(
                    point, sigma, radius, common.cells, x_mass_bound=_x_mass
                ))
            cache[key] = tuple(values)
        return cache[key]

    while pending and evaluated < common.max_boxes:
        box = pending.popleft()
        evaluated += 1
        radius, *sigma = box
        try:
            low, high = levels(radius.hi, sigma), levels(radius.lo, sigma)
            images = tuple(Interval(a.lo, b.hi) for a, b in zip(low, high))
        except ArithmeticError:
            unknown.append(box)
            reasons["numerical_enclosure"] += 1
            continue
        if any(image.hi < target.lo or image.lo > target.hi
               for image, target in zip(images, common.level_intervals)):
            excluded.append(box)
        elif all(target.lo <= image.lo and image.hi <= target.hi
                 for image, target in zip(images, common.level_intervals)):
            accepted.append(box)
        else:
            widths = [(Interval.point(axis.hi) - axis.lo).hi for axis in box]
            eligible = [i for i in range(3) if widths[i] > resolutions[i]]
            if not eligible:
                unknown.append(box)
                reasons["parameter_resolution"] += 1
                continue
            # Ranking only chooses a split; nearest rounding cannot discard a box.
            chosen = max(eligible, key=lambda i: fixed._PARTITION.divide(widths[i], resolutions[i]))
            axis = box[chosen]
            middle = fixed._PARTITION.divide(fixed._PARTITION.add(axis.lo, axis.hi), Decimal(2))
            if not axis.lo < middle < axis.hi:
                unknown.append(box)
                reasons["midpoint_stagnation"] += 1
                continue
            for half in (Interval(axis.lo, middle), Interval(middle, axis.hi)):
                child = list(box)
                child[chosen] = half
                pending.append(tuple(child))
    budget_exhausted = bool(pending)
    unknown.extend(pending)
    if pending:
        reasons["work_budget"] += len(pending)
    inner = fixed._merged([box[0] for box in accepted])
    outer = fixed._merged([box[0] for box in accepted + unknown])
    return {
        "format": fixed.FORMAT + "-result", "version": 2,
        "status": ("conditional_compatible" if accepted else
                   "conditional_incompatible" if not outer else "unknown"),
        "coordinate_unit": common.coordinate_unit,
        "parameter_order": list(PARAMETER_ORDER),
        "parameter_domain": _serialized_boxes([domain])[0],
        "parameter_boxes": {"accepted": _serialized_boxes(accepted),
                            "unknown": _serialized_boxes(unknown),
                            "excluded": _serialized_boxes(excluded)},
        "inner": fixed._serialized(inner), "outer": fixed._serialized(outer),
        "coverage_complete": True, "classification_complete": not unknown,
        "budget_exhausted": budget_exhausted, "boxes_evaluated": evaluated,
        "level_evaluations": level_evaluations,
        "unknown_reason_counts": dict(sorted(reasons.items())),
        "prior_ceiling_reached": bool(outer and outer[-1].hi == common.radius_domain.hi),
        "assumptions": {
            "geometry": "fixed apex (0,0), +x/+y material, circular cutout, right angle",
            "blur": "one common independent axis-aligned Gaussian within supplied sigma domains",
            "projection": "radius is feasible only if one common blur satisfies every observation",
            "observations": "exact point coordinates and supplied closed linear-light level intervals",
            "not_inferred": "pose, coordinate error, tone response, discrepancy or physical accuracy",
            "subdivision": "radius/blur stopping widths are numerical, not physical uncertainty",
        },
    }
