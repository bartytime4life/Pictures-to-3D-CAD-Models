"""Cell-boundary flux for a continuously varied disk/chord geometry.

This differentiates the unrounded area model around the stored canonicalized
normal m. The angle parameter rotates m continuously at its fixed exact norm;
it does not differentiate binary64 normal canonicalization or acquisition casts.
Unknown Jacobians contain NaN and explicit statuses, never fabricated zeros.
Arithmetic error estimates are engineering guards, not certified enclosures.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import pairwise
from numbers import Integral

import numpy as np

from . import finite_aperture as aperture

PARAMETER_ORDER = ("centre_x", "centre_y", "radius", "fraction", "normal_angle")
MAX_WORK = aperture.MAX_CELLS
_EPS = 2.0**-52
_TAU = 2 * math.pi
_DECIMAL_MOMENT_GUARD = 1e-90


class _Unknown(ArithmeticError):
    pass


class _Nondifferentiable(_Unknown):
    pass


def _sign(value):
    return (value > 0) - (value < 0)


def _surd_sign(a, b, d):
    """Exact sign of a+b*sqrt(d), for rational a,b and d>=0."""
    if b == 0 or d == 0:
        return _sign(a)
    if a == 0 or _sign(a) == _sign(b):
        return _sign(b)
    return _sign(a) * _sign(a * a - b * b * d)


def _decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


@dataclass(frozen=True)
class _Event:
    line: tuple[Fraction, Fraction]
    offset: Fraction
    branch: int
    a: tuple[Fraction, Fraction]
    b: tuple[Fraction, Fraction]
    d: Fraction
    angle: float


def _linear_sign(event, coefficients, offset=Fraction(0)):
    a = sum((coefficients[i] * event.a[i] for i in (0, 1)), -offset)
    b = sum((coefficients[i] * event.b[i] for i in (0, 1)), Fraction(0))
    return _surd_sign(a, b, event.d)


def _same_point(a, b):
    # A circle/line intersection is fixed by its line and signed tangent branch.
    if _linear_sign(a, b.line, b.offset) != 0:
        return False
    return _linear_sign(a, (-b.line[1], b.line[0])) == b.branch


def _events(line, offset):
    nx, ny = line
    q = nx * nx + ny * ny
    d = aperture._fraction(q - offset * offset)
    if d < 0:
        return []
    a = tuple(aperture._fraction(offset * n / q) for n in line)
    events = []
    for branch in (0,) if d == 0 else (-1, 1):
        b = tuple(aperture._fraction(branch * n / q) for n in (-ny, nx))
        with localcontext() as context:
            context.prec = 96
            root = _decimal(d).sqrt()
            coordinates = tuple(float(_decimal(a[i]) + _decimal(b[i]) * root) for i in (0, 1))
        # A nonzero exact component that loses its sign needs more precision.
        for i, value in enumerate(coordinates):
            expected = _surd_sign(a[i], b[i], d)
            if _sign(value) != expected:
                raise _Unknown("circle event component is unresolved")
        angle = math.atan2(coordinates[1], coordinates[0]) % _TAU
        events.append(_Event(line, offset, branch, a, b, d, angle))
    return events


def _arc_terms(bounds, normal, fraction, radius):
    x0, y0, x1, y1 = bounds
    if x0 >= 1 or x1 <= -1 or y0 >= 1 or y1 <= -1:
        return (0.0, 0.0, 0.0), 0.0
    # Include the positive-x seam as a real, exactly identified point.
    seam = _events((Fraction(0), Fraction(1)), Fraction(0))[0]
    assert seam.branch == -1
    events = [seam]
    for line, offset in (
        ((Fraction(1), Fraction(0)), x0),
        ((Fraction(1), Fraction(0)), x1),
        ((Fraction(0), Fraction(1)), y0),
        ((Fraction(0), Fraction(1)), y1),
        (normal, fraction),
    ):
        for event in _events(line, offset):
            if not any(_same_point(event, prior) for prior in events):
                events.append(event)
    events.sort(key=lambda event: event.angle)
    cuts = [event.angle for event in events] + [_TAU]
    if cuts[0] != 0:
        raise _Unknown("circle seam ordering is unresolved")
    # Distinct exact events are never tolerance-merged or snapped together.
    if any(b - a <= 128 * _EPS for a, b in pairwise(cuts)):
        raise _Unknown("distinct circle events are not separated in binary64")
    terms = []
    nx, ny = map(float, normal)
    f = float(fraction)
    for a, b in pairwise(cuts):
        midpoint = (a + b) / 2
        x, y = math.cos(midpoint), math.sin(midpoint)
        margins = (
            (x - float(x0), 1 + abs(float(x0))),
            (float(x1) - x, 1 + abs(float(x1))),
            (y - float(y0), 1 + abs(float(y0))),
            (float(y1) - y, 1 + abs(float(y1))),
            (f - nx * x - ny * y, 1 + abs(f) + abs(nx) + abs(ny)),
        )
        if any(value < -128 * _EPS * scale for value, scale in margins):
            continue
        if any(abs(value) <= 128 * _EPS * scale for value, scale in margins):
            raise _Unknown("arc interval classification is unresolved")
        width = b - a
        chord = 2 * math.sin(width / 2)
        terms.append(
            (
                radius * chord * math.cos(midpoint),
                radius * chord * math.sin(midpoint),
                radius * width,
            )
        )
    totals = tuple(math.fsum(term[i] for term in terms) for i in range(3))
    # Endpoint-angle, trigonometric, product and summation engineering allowance.
    guard = 1024 * _EPS * radius * len(terms)
    return totals, guard


def _compare_root(value, squared, root_sign):
    if root_sign < 0:
        return -_compare_root(-value, squared, 1)
    if value < 0:
        return -1
    return _sign(value * value - squared)


def _chord_terms(bounds, normal, fraction, radius):
    nx, ny = normal
    q = nx * nx + ny * ny
    d = q - fraction * fraction
    if d <= 0:
        raise _Unknown("normal/chord tangent geometry is withheld")
    foot = (fraction * nx / q, fraction * ny / q)
    direction = (-ny, nx)
    lower = upper = None
    coincident = False
    for axis, (lo, hi) in enumerate(((bounds[0], bounds[2]), (bounds[1], bounds[3]))):
        if direction[axis] == 0:
            if not lo <= foot[axis] <= hi:
                return (0.0,) * 5, (0.0,) * 5
            coincident |= foot[axis] in (lo, hi)
            continue
        a, b = sorted(((lo - foot[axis]) / direction[axis], (hi - foot[axis]) / direction[axis]))
        lower = a if lower is None else max(lower, a)
        upper = b if upper is None else min(upper, b)
    assert lower is not None and upper is not None
    squared = d / (q * q)
    if (
        lower >= upper
        or _compare_root(upper, squared, -1) <= 0
        or _compare_root(lower, squared, 1) >= 0
    ):
        return (0.0,) * 5, (0.0,) * 5
    if coincident:
        raise _Nondifferentiable("positive-length chord coincides with a cell side")
    low_is_root = _compare_root(lower, squared, -1) < 0
    high_is_root = _compare_root(upper, squared, 1) > 0
    # High precision is used only for this bounded algebraic clipping moment.
    with localcontext() as context:
        context.prec = 96
        cap = _decimal(squared).sqrt()
        low = -cap if low_is_root else _decimal(lower)
        high = cap if high_is_root else _decimal(upper)
        length = float(high - low)
        midpoint = float((high + low) / 2)
    if not math.isfinite(length) or length <= 0 or not math.isfinite(midpoint):
        raise _Unknown("positive chord interval is not representable")
    # The near-unit input contract bounds retained v endpoints by two. With
    # 96 decimal digits, this deliberately loose absolute allowance covers the
    # bounded rational divisions, square root and endpoint moments. Do not
    # claim binary64 relative accuracy after extreme Decimal cancellation.
    if length <= _DECIMAL_MOMENT_GUARD / (64 * _EPS):
        raise _Unknown("chord moment cancellation exceeds its relative precision guard")
    r2 = radius * radius
    terms = (
        radius * float(nx) * length,
        radius * float(ny) * length,
        radius * float(fraction) * length,
        r2 * length,
        -r2 * float(q) * length * midpoint,
    )
    decimal_guards = (
        radius * abs(float(nx)) * _DECIMAL_MOMENT_GUARD,
        radius * abs(float(ny)) * _DECIMAL_MOMENT_GUARD,
        radius * abs(float(fraction)) * _DECIMAL_MOMENT_GUARD,
        r2 * _DECIMAL_MOMENT_GUARD,
        r2 * float(q) * _DECIMAL_MOMENT_GUARD * (abs(midpoint) + length + _DECIMAL_MOMENT_GUARD),
    )
    guards = tuple(
        256 * _EPS * abs(value) + 16 * math.ulp(value) + decimal_guard
        for value, decimal_guard in zip(terms, decimal_guards, strict=True)
    )
    return terms, guards


def _freeze(array):
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


@dataclass(frozen=True)
class ApertureSensitivity:
    coverage: np.ndarray
    jacobian: np.ndarray
    estimated_absolute_error: np.ndarray
    statuses: tuple[str, ...]
    input_sha256: str
    required_work: int
    performed_work: int
    numeric_workspace_bound_bytes: int
    parameter_order: tuple[str, ...] = PARAMETER_ORDER
    error_estimate_is_certified: bool = False


def segment_cell_sensitivity(
    *, centre, radius, fraction, normal, shape, origin, pitch, max_work=MAX_WORK
):
    """Return coverage and five unrounded area sensitivities on a source grid.

    The grid/geometry contract is the finite_aperture contract. Flat statuses
    use row-major order. A Jacobian unknown fills all its columns with NaN;
    coverage can still be available. Work counts complete cell evaluations,
    not arithmetic instructions. Endpoint fractions are explicitly withheld.
    Numeric workspace excludes Python/exact-number/allocator/caller overhead.
    """
    segment = aperture._segment(centre, radius, fraction, normal)
    try:
        shape = tuple(shape)
    except TypeError as error:
        raise ValueError("shape must contain two positive integers") from error
    if len(shape) != 2 or any(
        isinstance(x, (bool, np.bool_)) or not isinstance(x, Integral) or x <= 0 for x in shape
    ):
        raise ValueError("shape must contain two positive integers")
    rows, cols = map(int, shape)
    count = rows * cols
    if rows > MAX_WORK or cols > MAX_WORK or count > MAX_WORK:
        raise ValueError("shape may contain at most 65536 cells")
    if (
        isinstance(max_work, (bool, np.bool_))
        or not isinstance(max_work, Integral)
        or not 1 <= max_work <= MAX_WORK
    ):
        raise ValueError("max_work must be an integer in [1,65536]")
    origin = aperture._vector(origin, 2, "origin")
    pitch = aperture._number(pitch, "pitch", limit=aperture.MAX_EXTENT)
    if not aperture.MIN_EXTENT <= pitch <= aperture.MAX_EXTENT:
        raise ValueError("pitch must lie in [1e-6,1e6]")
    exact_origin = tuple(map(aperture._fraction, origin))
    step = aperture._fraction(pitch)
    for axis, size in ((0, cols), (1, rows)):
        if any(
            abs(exact_origin[axis] + offset * step) > aperture.MAX_COORDINATE
            for offset in (-Fraction(1, 2), Fraction(size) - Fraction(1, 2))
        ):
            raise ValueError("complete cell grid must stay within the coordinate bound")
    starts = tuple(
        (exact_origin[i] - segment.centre_exact[i] - step / 2) / segment.radius_exact
        for i in (0, 1)
    )
    local_step = step / segment.radius_exact
    binding = hashlib.sha256(
        repr((segment, (rows, cols), exact_origin, step, "finite-cell-sensitivity-v1")).encode()
    ).hexdigest()
    # Coverage, two five-column arrays, immutable copies, plus fixed scratch.
    workspace = 256 * count + 65536
    coverage = np.full((rows, cols), np.nan)
    jacobian = np.full((rows, cols, 5), np.nan)
    errors = np.full((rows, cols, 5), np.nan)
    if count > max_work:
        return ApertureSensitivity(
            _freeze(coverage),
            _freeze(jacobian),
            _freeze(errors),
            ("work_limit",) * count,
            binding,
            count,
            0,
            workspace,
        )
    statuses = []
    cell_area = float(step * step)
    for row in range(rows):
        y0 = starts[1] + row * local_step
        for col in range(cols):
            x0 = starts[0] + col * local_step
            bounds = (x0, y0, x0 + local_step, y0 + local_step)
            try:
                area, area_guard = aperture._local_rectangle_area(segment, bounds)
                value = area / cell_area
                allowance = area_guard / cell_area + 16 * math.ulp(1.0)
                if not math.isfinite(value) or not -allowance <= value <= 1 + allowance:
                    raise _Unknown("coverage is not resolved")
                coverage[row, col] = min(1.0, max(0.0, value))
                if abs(segment.fraction) == 1:
                    statuses.append("parameter_endpoint")
                    continue
                chord, chord_guards = _chord_terms(
                    bounds, segment.normal, segment.fraction, segment.radius
                )
                arc, arc_guard = _arc_terms(
                    bounds, segment.normal, segment.fraction, segment.radius
                )
                for parameter in range(5):
                    arc_value = arc[parameter] if parameter < 3 else 0.0
                    total = math.fsum((arc_value, chord[parameter])) / cell_area
                    guard = (
                        chord_guards[parameter] + (arc_guard if parameter < 3 else 0)
                    ) / cell_area + 32 * math.ulp(total)
                    if not math.isfinite(total) or not math.isfinite(guard):
                        raise _Unknown("sensitivity is not representable")
                    jacobian[row, col, parameter] = total
                    errors[row, col, parameter] = guard
                statuses.append("resolved")
            except _Nondifferentiable:
                jacobian[row, col] = np.nan
                errors[row, col] = np.nan
                statuses.append("nondifferentiable")
            except ArithmeticError:
                jacobian[row, col] = np.nan
                errors[row, col] = np.nan
                statuses.append("unresolved")
    return ApertureSensitivity(
        _freeze(coverage),
        _freeze(jacobian),
        _freeze(errors),
        tuple(statuses),
        binding,
        count,
        count,
        workspace,
    )
