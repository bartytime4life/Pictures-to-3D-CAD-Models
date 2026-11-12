"""Uniform rectangular pixel-aperture means for conditional corner inference.

The aperture is a fixed known product measure, not a coordinate-error box.
Independent uniform aperture coordinates plus independent Gaussian coordinates
remain independent, so positive rectangular covers enclose the averaged corner.
Only radius and one common blur pair vary in the shared version-2 box engine.
"""

from dataclasses import replace
from decimal import Decimal
from functools import lru_cache
from itertools import pairwise

from . import corner_blur_domains as joint
from . import corner_feasibility as fixed
from .decimal_bounds import Interval, _normalizer, normal_cdf

_FIELDS = (joint._FIELDS - {"points"}) | {"pixel_apertures"}
_ZERO, _ONE, _HALF = Decimal(0), Decimal(1), Decimal(".5")


def _aperture(value, field="pixel_aperture", *, string_only=False):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field}: require X and Y aperture intervals")
    axes = []
    for i, pair in enumerate(value):
        if isinstance(pair, Interval) and not string_only:
            axis = pair
        else:
            axis = Interval(*fixed._pair(pair, f"{field}[{i}]", string_only=string_only))
        if max(axis.lo.copy_abs(), axis.hi.copy_abs()) > 1_000_000:
            raise ValueError(f"{field}: coordinate magnitude exceeds 1000000")
        axes.append(axis)
    return tuple(axes)


def parse_config(raw):
    """Validate v3's known normalized product apertures and shared blur domains."""
    if not isinstance(raw, dict):
        raise ValueError("input: expected a JSON object")  # noqa: TRY004 - schema error
    if any(not isinstance(key, str) for key in raw):
        raise ValueError("input fields: require string keys")
    missing, unknown = _FIELDS - raw.keys(), raw.keys() - _FIELDS
    if missing or unknown:
        raise ValueError(f"input fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    if raw["format"] != fixed.FORMAT or type(raw["version"]) is not int or raw["version"] != 3:
        raise ValueError("format/version: require pictures-to-cad-corner-feasibility version 3")
    supplied = raw["pixel_apertures"]
    if not isinstance(supplied, list) or not 1 <= len(supplied) <= 16:
        raise ValueError("pixel_apertures: require 1..16 uniform rectangular apertures")
    apertures = tuple(_aperture(value, f"pixel_apertures[{i}]", string_only=True)
                      for i, value in enumerate(supplied))
    common = {key: value for key, value in raw.items() if key in joint._FIELDS}
    common.update(version=2, points=[[str(x.lo), str(y.lo)] for x, y in apertures])
    config = joint.parse_config(common)
    return replace(config, fixed=replace(config.fixed, points=apertures))


def _intersection(left, right):
    lo, hi = max(left.lo, right.lo), min(left.hi, right.hi)
    if lo > hi:
        raise ArithmeticError("pixel-aperture enclosures are inconsistent")
    return Interval(lo, hi)


@lru_cache(maxsize=2048)
def _h_scalar(value):
    """Enclose H(t)=t Phi(t)+phi(t), whose derivative is Phi(t)."""
    point = Interval.point(value)
    density = _normalizer() * (-(point * value) / 2).exp()
    natural = point * normal_cdf(point) + density
    # H(t)=E[(t-Z)_+] is nonnegative and H(t)-t=H(-t). Also
    # H(t)<=max(0,t)+phi(t). These bounds control lower-tail cancellation.
    lower = max(_ZERO, value)
    known = Interval(lower, (Interval.point(lower) + density).hi)
    return _intersection(natural, known)


def _h(value):
    # H is monotone, including when an argument interval crosses zero.
    return Interval(_h_scalar(value.lo).lo, _h_scalar(value.hi).hi)


def _averaged_cdf(edge, aperture, sigma):
    """Enclose E_P Phi((edge-P)/sigma), P uniform on the fixed aperture axis.

    Nonzero width is normalized by its full width. Width zero denotes a Dirac
    measure. The sigma interval is one common nuisance, not independently chosen
    in each term; natural interval dependency can widen but cannot shrink bounds.
    """
    if aperture.lo == aperture.hi:
        return normal_cdf((edge - aperture.lo) / sigma)
    if edge.lo == edge.hi == 0 and aperture.lo == aperture.hi.copy_negate():
        return Interval.point(_HALF)
    width = Interval.point(aperture.hi) - aperture.lo
    left = (edge - aperture.lo) / sigma
    right = (edge - aperture.hi) / sigma
    natural = fixed._probability(sigma / width * (_h(left) - _h(right)))
    # Every CDF value averaged lies between its support-endpoint values. This
    # controls tiny-width cancellation without pretending the aperture is a point.
    support = Interval(normal_cdf(right).lo, normal_cdf(left).hi)
    return _intersection(natural, support)


def _mass(lo, hi, aperture, sigma):
    return fixed._probability(_averaged_cdf(hi, aperture, sigma)
                              - _averaged_cdf(lo, aperture, sigma))


def _x_mass(a, b, aperture, sigma):
    averaged = _mass(Interval.point(a), Interval.point(b), aperture, sigma)
    standardized = (Interval(a, b) - aperture) / sigma
    density = _normalizer() / sigma * (-joint._square(standardized) / 2).exp()
    # The averaged density is bounded by this density over every aperture point;
    # integrating over the X strip preserves the bound for every common sigma.
    density_mass = fixed._probability((Interval.point(b) - a) * density)
    return _intersection(averaged, density_mass)


def _level_bounds(aperture, blur_domains, radius, cells):
    x_aperture, y_aperture = aperture
    if x_aperture.lo == x_aperture.hi and y_aperture.lo == y_aperture.hi:
        # Preserve numerical version-2 equivalence, not merely the point limit.
        return joint._point_level_bounds((x_aperture.lo, y_aperture.lo),
                                         blur_domains, radius, cells)
    sx, sy = blur_domains
    zero = Interval.point(0)
    wedge = ((1 - _averaged_cdf(zero, x_aperture, sx))
             * (1 - _averaged_cdf(zero, y_aperture, sy)))
    if radius == 0:
        return fixed._probability(wedge)
    partition = [fixed._PARTITION.divide(fixed._PARTITION.multiply(radius, Decimal(i)),
                                        Decimal(cells)) for i in range(cells + 1)]
    partition[0], partition[-1] = _ZERO, radius
    if any(a >= b for a, b in pairwise(partition)):
        raise ArithmeticError("pixel-aperture cutout partition cannot be represented")
    heights = [fixed._height(radius, x) for x in partition]
    y_masses = [_mass(zero, height, y_aperture, sy) for height in heights]
    lower = upper = zero
    for i, (a, b) in enumerate(pairwise(partition)):
        x_mass = _x_mass(a, b, x_aperture, sx)
        lower = lower + x_mass * y_masses[i + 1]
        upper = upper + x_mass * y_masses[i]
    return fixed._probability(wedge - Interval(lower.lo, upper.hi))


def aperture_level_bounds(pixel_aperture, blur_domains, radius, *, cells=32):
    """Enclose a known uniform aperture's normalized mean, not total flux."""
    aperture = _aperture(pixel_aperture)
    domains = joint._blur_domains(blur_domains)
    radius = fixed._number(radius, "radius")
    cells = fixed._integer(cells, "cells", 256)
    if not 0 <= radius <= 1_000_000:
        raise ValueError("radius outside supported numerical domain")
    return _level_bounds(aperture, domains, radius, cells)


def analyze(raw):
    """Enclose feasible radius/blur tuples for the supplied exact aperture means."""
    result = joint._analyze(parse_config(raw), level_evaluator=_level_bounds)
    assumptions = {
        **result["assumptions"],
        "observations": "supplied normalized linear-light mean intervals of known uniform apertures",
        "pixel_apertures": "fixed known axis-aligned uniform PRODUCT measures; degenerate axes are Dirac points",
        "measurement": "normalized mean, not total flux; one common blur pair satisfies all observations",
        "not_modelled": "rotated/warped footprints, signed resamplers such as Keys, arbitrary intra-pixel response",
        "not_inferred": "aperture bounds, pose, coordinate error, tone response, discrepancy or physical accuracy",
    }
    return {**result, "version": 3, "assumptions": assumptions}
