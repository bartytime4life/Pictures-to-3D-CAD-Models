"""Finite circular-segment material averaged over declared rectangular cells.

The material is disc(centre, radius) intersected with
    normal dot (x-centre) <= fraction*radius.
No Gaussian, renderer, contour generator or production fitting implementation is
used. Rectangles are clipped by the chord half-plane, then an independent Green
boundary integral intersects the resulting convex polygon with the unit disk.

Exact rational predicates concern represented, locally normalized input values.
Square roots, atan2 and the final area are binary64 engineering calculations,
not certified enclosures. Only arithmetic-scale range overshoots are clamped;
unresolved intersections or larger inconsistencies raise ArithmeticError.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from numbers import Integral, Real

import numpy as np

MAX_CELLS = 65_536
MAX_COORDINATE = 1e9
MIN_EXTENT = 1e-6
MAX_EXTENT = 1e6
_EPS = 2.0**-52
_HALF = Fraction(1, 2)
_MAX_EXACT_BITS = 8192
_ROOT_FRACTIONAL_BITS = (128, 256, 512)


def _number(value, name, *, limit=MAX_COORDINATE):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number, not a boolean")  # noqa: TRY004 -- one public input-refusal type
    try:
        value = float(value)
    except (OverflowError, ValueError, TypeError, RuntimeWarning) as error:
        raise ValueError(f"{name} cannot be represented as a finite real number") from error
    if not math.isfinite(value) or abs(value) > limit:
        raise ValueError(f"{name} must be finite with absolute value <= {limit:g}")
    return value


def _vector(value, count, name):
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must contain {count} real numbers")  # noqa: TRY004 -- one public input-refusal type
    try:
        entries = tuple(value)
    except TypeError as error:
        raise ValueError(f"{name} must contain {count} real numbers") from error
    if len(entries) != count:
        raise ValueError(f"{name} must contain {count} real numbers")
    return tuple(_number(entry, name) for entry in entries)


def _fraction(value):
    result = Fraction(value)
    if max(result.numerator.bit_length(), result.denominator.bit_length()) > _MAX_EXACT_BITS:
        raise ArithmeticError("exact geometry exceeds the bounded arithmetic resource")
    return result


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


@dataclass(frozen=True)
class _Segment:
    centre: tuple[float, float]
    radius: float
    centre_exact: tuple[Fraction, Fraction]
    radius_exact: Fraction
    fraction: Fraction
    normal: tuple[Fraction, Fraction]


def _segment(centre, radius, fraction, normal):
    centre = _vector(centre, 2, "centre")
    radius = _number(radius, "radius", limit=MAX_EXTENT)
    if not MIN_EXTENT <= radius <= MAX_EXTENT:
        raise ValueError(f"radius must lie in [{MIN_EXTENT:g}, {MAX_EXTENT:g}]")
    fraction = _number(fraction, "fraction", limit=1)
    normal = _vector(normal, 2, "normal")
    length = math.hypot(*normal)
    if not math.isfinite(length) or abs(length - 1) > 64 * _EPS:
        raise ValueError("normal must be unit length within the 64-eps arithmetic guard")
    # This canonicalization is arithmetic-scale only, not a geometric fit.
    unit = tuple(component / length for component in normal)
    return _Segment(
        centre,
        radius,
        tuple(map(_fraction, centre)),
        _fraction(radius),
        _fraction(fraction),
        tuple(map(_fraction, unit)),
    )


def _clip_rectangle(bounds, normal, fraction):
    x0, y0, x1, y1 = bounds
    vertices = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    result = []
    a = vertices[-1]
    da = _dot(normal, a) - fraction
    for b in vertices:
        db = _dot(normal, b) - fraction
        if (da <= 0) != (db <= 0):
            parameter = da / (da - db)
            point = tuple(_fraction(a[k] + parameter * (b[k] - a[k])) for k in (0, 1))
            result.append(point)
        if db <= 0:
            result.append(b)
        a, da = b, db
    # Repeated exact vertices arise when the chord passes through a corner.
    deduplicated = []
    for vertex in result:
        if not deduplicated or vertex != deduplicated[-1]:
            deduplicated.append(vertex)
    if len(deduplicated) > 1 and deduplicated[0] == deduplicated[-1]:
        deduplicated.pop()
    return deduplicated


def _root_compare(bound, *, b, a, discriminant, plus):
    """Exact sign of (-b +/- sqrt(discriminant))/a - bound, a>0."""
    value = -b - a * bound
    if plus:
        if value > 0:
            return 1
        delta = discriminant - value * value
    else:
        if value < 0:
            return -1
        delta = value * value - discriminant
    return (delta > 0) - (delta < 0)


def _fraction_edge_cuts(a, b, discriminant):
    """Bound a root that cannot be represented by an interior binary64 cut.

    Integer square root gives an enclosing dyadic interval of width at most
    2**(-bits) for sqrt(discriminant/a**2). Exact endpoint predicates remain
    authoritative. Fraction midpoints retain sub-ULP distances from 0 or1;
    no root is snapped to an endpoint or admitted by a geometry tolerance.
    """
    beta = b / a
    scaled = discriminant / (a * a)
    interior = tuple(
        _root_compare(0, b=b, a=a, discriminant=discriminant, plus=plus) > 0
        and _root_compare(1, b=b, a=a, discriminant=discriminant, plus=plus) < 0
        for plus in (False, True)
    )
    for bits in _ROOT_FRACTIONAL_BITS:
        numerator = scaled.numerator << (2 * bits)
        denominator = scaled.denominator
        integer = math.isqrt(numerator // denominator)
        lower = Fraction(integer, 1 << bits)
        upper = (
            lower
            if integer * integer * denominator == numerator
            else Fraction(integer + 1, 1 << bits)
        )
        intervals = ((-beta - upper, -beta - lower), (-beta + lower, -beta + upper))
        cuts = [Fraction(0)]
        preceding_upper = Fraction(0)
        for use, (left, right) in zip(interior, intervals, strict=True):
            if not use:
                continue
            if not 0 < left <= right < 1 or left <= preceding_upper:
                break
            cuts.append(_fraction((left + right) / 2))
            preceding_upper = right
        else:
            return (*cuts, Fraction(1)), discriminant
    raise ArithmeticError("circle intersections exceed bounded rational parameter resolution")


def _edge_cuts(a, b, c):
    """Represent interior roots only after exact endpoint-membership decisions."""
    discriminant = b * b - a * c
    if discriminant <= 0:
        return (0.0, 1.0), discriminant
    beta, gamma = float(b / a), float(c / a)
    scaled = float(discriminant / (a * a))
    if not math.isfinite(scaled) or scaled <= 0:
        return _fraction_edge_cuts(a, b, discriminant)
    root = math.sqrt(scaled)
    q = -beta - (root if b >= 0 else -root)
    if not math.isfinite(q) or q == 0:
        return _fraction_edge_cuts(a, b, discriminant)
    roots = (q, gamma / q) if b >= 0 else (gamma / q, q)
    cuts = [0.0]
    for plus, value in zip((False, True), roots, strict=True):
        lower = _root_compare(0, b=b, a=a, discriminant=discriminant, plus=plus)
        upper = _root_compare(1, b=b, a=a, discriminant=discriminant, plus=plus)
        if lower > 0 and upper < 0:
            if not math.isfinite(value) or not cuts[-1] < value < 1:
                return _fraction_edge_cuts(a, b, discriminant)
            cuts.append(value)
    cuts.append(1.0)
    return tuple(cuts), discriminant


def _edge_integrals(u, v):
    d = _subtract(v, u)
    a, b, c = _dot(d, d), _dot(u, d), _dot(u, u) - 1
    if a == 0:
        return []
    cuts, discriminant = _edge_cuts(a, b, c)
    whole_cross = _cross(u, d)
    terms = []
    for lo, hi in pairwise(cuts):
        t0, t1 = Fraction(lo), Fraction(hi)
        midpoint = (t0 + t1) / 2
        radial = a * midpoint * midpoint + 2 * b * midpoint + c
        if discriminant > 0 and radial == 0:
            raise ArithmeticError("circle-piece classification is unresolved")
        cross = whole_cross * (t1 - t0)
        if discriminant > 0 and radial < 0:
            terms.append(float(cross) / 2)
        else:
            # cross(u(t0),u(t1)) uses the whole edge, avoiding subtraction of
            # two rounded intersection positions. The dot product is rational.
            dot = c + 1 + b * (t0 + t1) + a * t0 * t1
            scale = max(abs(cross), abs(dot))
            if scale == 0 or (cross == 0 and dot < 0):
                raise ArithmeticError("unresolved exterior angular branch")
            angle = math.atan2(float(cross / scale), float(dot / scale))
            terms.append(angle / 2)
    return terms


def _local_rectangle_area(segment, bounds):
    if segment.fraction == -1:
        return 0.0, 0.0
    x0, y0, x1, y1 = bounds
    if x0 >= 1 or x1 <= -1 or y0 >= 1 or y1 <= -1:
        return 0.0, 0.0
    polygon = _clip_rectangle(bounds, segment.normal, segment.fraction)
    if len(polygon) < 3:
        return 0.0, 0.0
    edges = tuple(zip(polygon, polygon[1:] + polygon[:1], strict=True))
    twice_area = sum((_cross(a, b) for a, b in edges), Fraction(0))
    if twice_area <= 0:
        if twice_area == 0:
            return 0.0, 0.0
        raise ArithmeticError("clipped rectangle lost its positive orientation")
    polygon_area = twice_area / 2
    radius_squared = segment.radius_exact**2
    if all(_dot(p, p) <= 1 for p in polygon):
        return float(polygon_area * radius_squared), 0.0
    origin_inside = all(_cross(a, b) >= 0 for a, b in edges)
    distances = []
    for u, v in edges:
        d = _subtract(v, u)
        aa, bb, cc = _dot(d, d), _dot(u, d), _dot(u, u)
        if aa == 0:
            continue
        distances.append(cc if bb >= 0 else _dot(v, v) if -bb >= aa else cc - bb * bb / aa)
    if not origin_inside and distances and min(distances) >= 1:
        return 0.0, 0.0
    if origin_inside and all(
        _cross(u, v) >= 0 and _cross(u, v) ** 2 >= _dot(_subtract(v, u), _subtract(v, u))
        for u, v in edges
    ):
        return math.pi * segment.radius**2, 16 * math.ulp(math.pi * segment.radius**2)
    terms = [term for u, v in edges for term in _edge_integrals(u, v)]
    scale = float(radius_squared)
    area = math.fsum(terms) * scale
    upper = min(float(polygon_area * radius_squared), math.pi * segment.radius**2)
    guard = 256 * _EPS * math.fsum(map(abs, terms)) * scale + 32 * math.ulp(upper)
    if not math.isfinite(area) or not math.isfinite(guard):
        raise ArithmeticError("finite material area is not representable")
    if area < -guard or area > upper + guard:
        raise ArithmeticError("material area is outside its geometric bounds beyond roundoff")
    return min(upper, max(0.0, area)), guard


def segment_rectangle_area(centre, radius, fraction, normal, bounds):
    """Area of a disk/chord segment inside (x0,y0,x1,y1), in plane units².

    Coordinates have absolute value at most 1e9, radius lies in [1e-6,1e6],
    fraction in [-1,1], and each rectangle side is positive and at most1e6.
    A near-unit normal is canonicalized within its64eps arithmetic guard.
    """
    segment = _segment(centre, radius, fraction, normal)
    x0, y0, x1, y1 = _vector(bounds, 4, "bounds")
    if not 0 < x1 - x0 <= MAX_EXTENT or not 0 < y1 - y0 <= MAX_EXTENT:
        raise ValueError("rectangle bounds must be ordered with side lengths in (0,1e6]")
    local = tuple(
        (_fraction(value) - segment.centre_exact[axis]) / segment.radius_exact
        for value, axis in ((x0, 0), (y0, 1), (x1, 0), (y1, 1))
    )
    return _local_rectangle_area(segment, local)[0]


def segment_cell_coverage(*, centre, radius, fraction, normal, shape, origin, pitch):
    """Return float64 cell means; origin is cell(0,0)'s plane-coordinate centre.

    Cell(row,col) is centred at origin+pitch*(col,row), with side length pitch.
    At most65,536 cells are accepted, before any output allocation. Grid bounds
    use exact represented origin/pitch arithmetic before local normalization,
    avoiding loss of small cells through repeated large-world additions.
    """
    segment = _segment(centre, radius, fraction, normal)
    try:
        shape = tuple(shape)
    except TypeError as error:
        raise ValueError("shape must contain two positive integers") from error
    if len(shape) != 2 or any(
        isinstance(x, (bool, np.bool_)) or not isinstance(x, Integral) or x <= 0 for x in shape
    ):
        raise ValueError("shape must contain two positive integers")
    rows, cols = map(int, shape)
    if rows > MAX_CELLS or cols > MAX_CELLS or rows * cols > MAX_CELLS:
        raise ValueError(f"shape may contain at most {MAX_CELLS} cells")
    origin = _vector(origin, 2, "origin")
    pitch = _number(pitch, "pitch", limit=MAX_EXTENT)
    if not MIN_EXTENT <= pitch <= MAX_EXTENT:
        raise ValueError(f"pitch must lie in [{MIN_EXTENT:g},{MAX_EXTENT:g}]")
    step = _fraction(pitch)
    exact_origin = tuple(map(_fraction, origin))
    for axis, count in ((0, cols), (1, rows)):
        if any(
            abs(exact_origin[axis] + offset * step) > MAX_COORDINATE
            for offset in (-_HALF, Fraction(count) - _HALF)
        ):
            raise ValueError("complete cell grid must stay within the coordinate bound")
    starts = tuple(
        (exact_origin[k] - segment.centre_exact[k] - step / 2) / segment.radius_exact
        for k in (0, 1)
    )
    local_step = step / segment.radius_exact
    cell_area = float(step * step)
    output = np.empty((rows, cols), dtype=np.float64)
    for row in range(rows):
        y0 = starts[1] + row * local_step
        for col in range(cols):
            x0 = starts[0] + col * local_step
            area, guard = _local_rectangle_area(segment, (x0, y0, x0 + local_step, y0 + local_step))
            value = area / cell_area
            allowance = guard / cell_area + 16 * math.ulp(1.0)
            if not math.isfinite(value) or value < -allowance or value > 1 + allowance:
                raise ArithmeticError("cell coverage is outside [0,1] beyond roundoff")
            output[row, col] = min(1.0, max(0.0, value))
    return output
