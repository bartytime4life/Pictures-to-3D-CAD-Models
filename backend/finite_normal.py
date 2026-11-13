"""Signed finite-D normal-angle derivatives under supplied Gaussian optics.

The centre/radius/fraction, fixed integer queries, map and covariance are supplied
hypotheses. This operator neither fits nor changes a trace. For a counterclockwise
normal rotation, the chord's outward normal velocity is -s. The complete finite D
must remain in the existing positive projective chart, even though only its chord
contributes to this derivative. Reflection uses the positive area Jacobian.

A fractional-linear coordinate turns the projected chord into an affine sensor
line, so its derivative is a finite Gaussian first moment for affine AND supported
projective maps. Cancellation or unsupported arithmetic falls back to quadrature
in the original plane chord coordinate, never to finite differences. Error and
conditioning guards are engineering estimates, not certified optical uncertainty.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from . import finite_centre_fit as centre_fit
from . import finite_shape as finite

_EPS = np.finfo(float).eps
_ROOT_TAU = math.sqrt(math.tau)
_ROOT_TWO = math.sqrt(2)
_SMALLEST = math.nextafter(0.0, 1.0)
_LOG_TWO = math.log(2.0)


@dataclass(frozen=True)
class NormalDerivative:
    derivatives: tuple[float | None, ...]
    statuses: tuple[str, ...]
    estimated_errors: tuple[float | None, ...]
    evaluations: int
    panels: int
    query_methods: tuple[str, ...]
    query_evaluations: tuple[int, ...]
    query_panels: tuple[int, ...]
    chart_margin: float
    reflected: bool
    method: str = "finite_chord_shape"
    quadrature_certified: bool = False


@dataclass(frozen=True)
class _Normalizer:
    determinant: Fraction
    log_flux: float
    log_moment: float
    log_error: float
    reflected: bool


def _exact_determinant(matrix):
    """Six fixed rational terms for the ACTUAL represented operational map."""
    rows = [[Fraction(float(value)) for value in row] for row in matrix]
    a, b, c = rows
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _fraction_log(value):
    """A binade avoids overflow and log(numerator)-log(denominator) loss.

    Conversion error is measured exactly against the rational mantissa. The
    four-ULP libm/float allowances remain estimates, not interval certificates.
    """
    if value <= 0:
        raise ArithmeticError("unsupported exact positive normalizer")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    mantissa = value / (1 << exponent) if exponent >= 0 else value * (1 << -exponent)
    if mantissa < 1:
        mantissa *= 2
        exponent -= 1
    rounded = float(mantissa)
    conversion = float(abs(Fraction(rounded) - mantissa) / mantissa)
    if not math.isfinite(rounded) or not 0 <= conversion < 1:
        raise ArithmeticError("unrepresentable exact normalizer")
    log_mantissa, log_power = math.log(rounded), exponent * _LOG_TWO
    logarithm = _finite_sum((log_mantissa, log_power))
    error = _finite_sum(
        (
            -math.log1p(-conversion),
            4 * math.ulp(log_mantissa),
            4 * abs(exponent) * math.ulp(_LOG_TWO),
            4 * math.ulp(log_power),
            4 * math.ulp(logarithm),
        )
    )
    return logarithm, error


def _normalizer_from_determinant(determinant, inverse):
    if determinant == 0:
        raise ArithmeticError("operational map determinant is unresolved")
    # A general solve of a lower Cholesky factor can leave a tiny nonzero upper
    # entry. Whitening uses that ACTUAL represented matrix, so its normalizer
    # must include the same entry instead of discarding it or refusing valid
    # supplied covariance. This second determinant also has fixed exact size.
    entries = tuple(float(value) for row in inverse for value in row)
    if not all(math.isfinite(value) for value in entries):
        raise ArithmeticError("unsupported represented Gaussian normalizer")
    first, upper, lower, second = map(Fraction, entries)
    inverse_determinant = first * second - upper * lower
    if inverse_determinant <= 0:
        raise ArithmeticError("unsupported represented whitening determinant")
    log_det, det_error = _fraction_log(abs(determinant))
    log_inverse, inverse_error = _fraction_log(inverse_determinant)
    log_tau, log_root_tau = math.log(math.tau), math.log(_ROOT_TAU)
    log_flux = _finite_sum((log_det, log_inverse, -log_tau))
    log_moment = _finite_sum((log_det, log_inverse, -log_root_tau))
    log_error = _finite_sum(
        (
            det_error,
            inverse_error,
            4 * _EPS,  # Rounded tau/sqrt(tau) constants.
            4 * max(math.ulp(log_tau), math.ulp(log_root_tau)),
            4 * max(math.ulp(log_flux), math.ulp(log_moment)),
        )
    )
    if not math.isfinite(log_error) or log_error >= 1:
        raise ArithmeticError("unresolved Gaussian/map normalizer")
    return _Normalizer(determinant, log_flux, log_moment, log_error, determinant < 0)


def _normalizer(h, inverse):
    """Bounded once-per-call setup, separate from endpoint/node work units."""
    return _normalizer_from_determinant(_exact_determinant(h), inverse)


def _finite_sum(values):
    """Keep represented nonfinite arithmetic separate from programming errors."""
    terms = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in terms):
        raise ArithmeticError("nonfinite derivative arithmetic")
    return math.fsum(terms)


def _positive_log(value):
    if not math.isfinite(value) or value <= 0:
        raise ArithmeticError("unsupported positive derivative scale")
    return math.log(value)


def _normal_mass(low, high):
    """Stable finite normal mass with an explicit estimated function-error guard."""
    if not math.isfinite(low) or not math.isfinite(high) or not low < high:
        raise ArithmeticError("unresolved standardized chord endpoints")
    if low >= 0:
        first, second = math.erfc(low / _ROOT_TWO), math.erfc(high / _ROOT_TWO)
    elif high <= 0:
        first, second = math.erfc(-high / _ROOT_TWO), math.erfc(-low / _ROOT_TWO)
    else:
        first, second = math.erf(high / _ROOT_TWO), math.erf(low / _ROOT_TWO)
    mass = (first - second) / 2
    error = max(_SMALLEST, 16 * _EPS * (abs(first) + abs(second) + abs(mass)))
    if not 0 <= mass <= 1:
        raise ArithmeticError("unsupported finite Gaussian mass")
    return mass, error


def _pdf_difference(low, high):
    """phi(low)-phi(high), using expm1 before subtracting nearby densities."""
    left, right = -(low * low) / 2, -(high * high) / 2
    if not math.isfinite(left) or not math.isfinite(right):
        raise ArithmeticError("unsupported standardized Gaussian scale")
    if left >= right:
        difference = math.exp(left) * -math.expm1(right - left) / _ROOT_TAU
    else:
        difference = -math.exp(right) * -math.expm1(left - right) / _ROOT_TAU
    phi_left, phi_right = math.exp(left) / _ROOT_TAU, math.exp(right) / _ROOT_TAU
    error = max(
        _SMALLEST,
        64 * _EPS * (phi_left + phi_right) * (1 + low * low + high * high),
    )
    return difference, error, phi_left, phi_right


def _scaled(value, log_factor, *, positive_error=False):
    if not math.isfinite(value) or not math.isfinite(log_factor):
        raise ArithmeticError("unrepresentable Gaussian first moment")
    if value == 0:
        return _SMALLEST if positive_error else 0.0
    exponent = log_factor + _positive_log(abs(value))
    if not math.isfinite(exponent):
        raise ArithmeticError("unrepresentable Gaussian first moment")
    magnitude = math.exp(exponent)
    if not math.isfinite(magnitude):
        raise ArithmeticError("unrepresentable Gaussian first moment")
    if positive_error:
        return max(_SMALLEST, magnitude)
    return math.copysign(magnitude, value)


def _closed_form(
    point, h, inverse, normal, radius, fraction, half_chord, tolerance, *, normalizer=None
):
    """First moment in z=s/(1+k*s), using LOCAL plane geometry throughout."""
    tangent = np.array([-normal[1], normal[0]])
    chord = radius * fraction * normal
    denominator = float(h[2, :2] @ chord + h[2, 2])
    rate = float(h[2, :2] @ tangent)
    if not math.isfinite(denominator) or denominator <= 0 or not math.isfinite(rate):
        raise ArithmeticError("unresolved chord projective chart")
    k = rate / denominator
    low_denominator, high_denominator = 1 - k * half_chord, 1 + k * half_chord
    if not all(math.isfinite(value) and value > 0 for value in (low_denominator, high_denominator)):
        raise ArithmeticError("unresolved chord projective chart")
    low, high = -half_chord / low_denominator, half_chord / high_denominator

    # Subtract the raw query BEFORE whitening; never subtract two whitened
    # large world coordinates. H's translated column already includes C.
    matrix = inverse @ (h[:2] - point[:, None] * h[2])
    offset = (matrix[:, :2] @ chord + matrix[:, 2]) / denominator
    numerator = h[:2, :2] @ chord + h[:2, 2]
    velocity = (h[:2, :2] @ tangent - numerator * (rate / denominator)) / denominator
    whitened_velocity = inverse @ velocity
    speed = math.hypot(*whitened_velocity)
    if not speed > 0 or not math.isfinite(speed):
        raise ArithmeticError("unresolved projected chord speed")
    direction = whitened_velocity / speed
    displacement = -offset
    along = _finite_sum(a * b for a, b in zip(direction, displacement, strict=True))
    across = _finite_sum((direction[0] * displacement[1], -direction[1] * displacement[0]))
    z_low, z_high = speed * low - along, speed * high - along
    mass, mass_error = _normal_mass(z_low, z_high)
    density_difference, density_error, phi_low, phi_high = _pdf_difference(z_low, z_high)
    first, second = along * mass, density_difference
    moment = _finite_sum((first, second))

    # Propagate estimated endpoint/dot/normalizer arithmetic in addition to
    # cancellation between the two signed moment terms. No denominator is
    # replaced by an arbitrary physical noise floor.
    coordinate_error = 64 * _EPS * max(1.0, _finite_sum(abs(x) for x in displacement))
    low_error = 64 * _EPS * (1 + abs(speed * low) + abs(along)) + coordinate_error
    high_error = 64 * _EPS * (1 + abs(speed * high) + abs(along)) + coordinate_error
    moment_error = _finite_sum(
        (
            abs(along) * mass_error,
            density_error,
            64 * _EPS * (abs(first) + abs(second)),
            mass * coordinate_error,
            (abs(along) + abs(z_low)) * phi_low * low_error,
            (abs(along) + abs(z_high)) * phi_high * high_error,
        )
    )
    if normalizer is None:
        normalizer = _normalizer(h, inverse)
    log_speed = _positive_log(speed)
    log_denominator = _positive_log(denominator)
    log_factor = normalizer.log_moment - 3 * log_denominator - 2 * log_speed - across * across / 2
    relative_error = (
        normalizer.log_error
        + 64 * _EPS * (1 + 3 * abs(log_denominator) + 2 * abs(log_speed))
        + abs(across) * coordinate_error
    )
    if not math.isfinite(relative_error) or relative_error >= 1:
        raise ArithmeticError("unresolved first-moment conditioning")
    moment_error += abs(moment) * math.expm1(relative_error)
    value = -_scaled(moment, log_factor)
    error = _scaled(moment_error, log_factor, positive_error=True)
    if error > tolerance:
        raise ArithmeticError("first-moment cancellation exceeds numerical allowance")
    return value, error


def _quadrature(
    curve,
    matrix,
    denominator,
    inverse,
    determinant,
    half_chord,
    start,
    end,
    order,
    *,
    normalizer=None,
):
    nodes, weights = finite._RULES[order]
    half = (end - start) / 2
    ts = (start + end) / 2 + half * nodes
    points, _ = curve.at(ts)
    w = points @ denominator[:2] + denominator[2]
    if not np.isfinite(w).all() or np.any(w <= 0):
        raise ArithmeticError("unsupported transformed chord")
    whitened = (points @ matrix[:, :2].T + matrix[:, 2]) / w[:, None]
    if not np.isfinite(whitened).all():
        raise ArithmeticError("unsupported transformed chord")
    if normalizer is None:
        normalizer = _normalizer_from_determinant(Fraction(determinant), inverse)
    log_normalizer = normalizer.log_flux + _positive_log(2 * half_chord) + _positive_log(half)
    terms = []
    for t, point, positive_w, weight in zip(ts, whitened, w, weights, strict=True):
        signed_s = half_chord * (2 * float(t) - 1)
        if signed_s == 0:
            terms.append(0.0)
            continue
        distance = math.hypot(*point)
        logarithm = (
            log_normalizer
            - distance * distance / 2
            - 3 * _positive_log(float(positive_w))
            + _positive_log(abs(signed_s))
            + _positive_log(float(weight))
        )
        if not math.isfinite(logarithm):
            raise ArithmeticError("unsupported chord derivative exponent")
        value = math.exp(logarithm)
        if not math.isfinite(value):
            raise ArithmeticError("unsupported chord derivative term")
        terms.append(-math.copysign(value, signed_s))
    return _finite_sum(terms), _finite_sum(abs(value) for value in terms)


@dataclass(frozen=True)
class _Leaf:
    start: float
    end: float
    value: float | None
    error: float | None
    absolute: float | None


class _WorkLimit(ArithmeticError):
    pass


def _frontier_total(leaves):
    """Upward error sum plus the EXACT dyadic error of the final reduction.

    This certifies only reduction of the represented leaf values/errors. It
    neither certifies those local estimates nor cancels upstream rule error.
    Called only for a potentially acceptable complete frontier, bounding the
    additional exact arithmetic by the existing panel count.
    """
    leaves = tuple(leaves)
    values = tuple(float(leaf.value) for leaf in leaves)
    errors = tuple(float(leaf.error) for leaf in leaves)
    value = _finite_sum(values)
    if not all(math.isfinite(error) and error >= 0 for error in errors):
        raise ArithmeticError("unsupported local frontier error")
    exact_values = sum((Fraction(item) for item in values), Fraction())
    exact_errors = sum((Fraction(item) for item in errors), Fraction())
    exact_total = exact_errors + abs(Fraction(value) - exact_values)
    error = float(exact_total)
    if not math.isfinite(error):
        raise ArithmeticError("unrepresentable frontier error reduction")
    if Fraction(error) < exact_total:
        error = math.nextafter(error, math.inf)
    if not math.isfinite(error):
        raise ArithmeticError("unrepresentable upward frontier error")
    return value, error


def _quadrature_one(
    point,
    curve,
    h,
    inverse,
    half_chord,
    tolerance,
    max_panels,
    evaluations_left,
    *,
    normalizer=None,
):
    """Refine a complete frontier against ONE absolute error allowance.

    Embedded-rule differences, local absolute-magnitude roundoff, normalizer
    allowances, omitted tails and exact final-reduction error are all included.
    The full estimate is not a certified integration enclosure. A parent stays represented until both
    children have been inspected; partial replacement cannot report a value.
    """
    evaluations, panels = 0, 0
    if max_panels < 1 or evaluations_left < 2:
        return None, "work_limit", None, evaluations, panels
    try:
        if normalizer is None:
            normalizer = _normalizer(h, inverse)
        matrix = inverse @ (h[:2] - point[:, None] * h[2])
        normalizer_relative_error = math.expm1(normalizer.log_error)

        def inspect_panel(start, end):
            nonlocal evaluations, panels
            if panels >= max_panels or evaluations + 2 > evaluations_left:
                raise _WorkLimit
            panels += 1
            evaluations += 2  # Full panel endpoint inspection is attempted together.
            distance, length = finite._panel(curve, matrix, h[2], start, end)
            endpoints, _ = finite._at(curve, matrix, h[2], [start, end])
            w_low, w_high = curve.range(h[2], start, end)
            if not all(math.isfinite(value) and value > 0 for value in (w_low, w_high)):
                raise ArithmeticError("unsupported panel projective chart")
            maximum_motion = half_chord * max(abs(2 * start - 1), abs(2 * end - 1))
            log_bound = (
                normalizer.log_flux
                - 3 * _positive_log(w_low)
                + _positive_log(2 * half_chord)
                + _positive_log(end - start)
                + _positive_log(maximum_motion)
                - distance * distance / 2
            )
            if not math.isfinite(log_bound):
                raise ArithmeticError("unsupported chord tail envelope")
            # Tail errors participate in the global frontier sum. A tail can be
            # split again if several individually affordable bounds add to too
            # much error; no fixed allowance is reserved for unused panels.
            adjusted_bound = log_bound + normalizer.log_error
            if adjusted_bound <= math.log(tolerance):
                bound = max(_SMALLEST, math.exp(adjusted_bound))
                return _Leaf(start, end, 0.0, bound, 0.0)

            # A positive-chart projective line traverses its image segment
            # monotonically. The norm is convex on that segment, so its maximum
            # is attained at an endpoint. The outward panel-box distance is a
            # lower bound. These resolution guards prevent a compressed image
            # chord from hiding a narrow w^-3 endpoint spike or density peak.
            maximum_distance = max(math.hypot(*endpoint) for endpoint in endpoints)
            exponent_variation = max(0.0, maximum_distance**2 - distance**2) / 2
            if not math.isfinite(exponent_variation):
                raise ArithmeticError("unsupported panel density variation")
            if length <= 0.5 and exponent_variation <= 8 and w_high / w_low <= 2:
                if evaluations + 36 > evaluations_left:
                    raise _WorkLimit
                evaluations += 12
                low, low_absolute = _quadrature(
                    curve,
                    matrix,
                    h[2],
                    inverse,
                    abs(normalizer.determinant),
                    half_chord,
                    start,
                    end,
                    12,
                    normalizer=normalizer,
                )
                evaluations += 24
                high, absolute = _quadrature(
                    curve,
                    matrix,
                    h[2],
                    inverse,
                    abs(normalizer.determinant),
                    half_chord,
                    start,
                    end,
                    24,
                    normalizer=normalizer,
                )
                if not all(
                    math.isfinite(value) and value >= 0 for value in (low_absolute, absolute)
                ):
                    raise ArithmeticError("unsupported absolute chord contribution")
                # The embedded difference uses BOTH computed rules. Retain an
                # estimated 64-eps node/log-exp/weighted-sum allowance for each
                # rule's absolute contribution, rather than letting signed
                # cancellation erase either scale. This is not a libm or
                # floating-point interval certificate. Shared normalizer error
                # additionally bounds the reported high-rule contribution.
                error = _finite_sum(
                    (
                        abs(high - low),
                        64 * _EPS * _finite_sum((low_absolute, absolute)),
                        normalizer_relative_error * absolute,
                    )
                )
                return _Leaf(start, end, high, error, absolute)
            return _Leaf(start, end, None, None, None)

        frontier, priorities = {}, []
        serial = 0

        def add(leaf):
            nonlocal serial
            serial += 1
            frontier[serial] = leaf
            priority = -math.inf if leaf.error is None else -leaf.error
            heapq.heappush(priorities, (priority, leaf.start, leaf.end, serial))

        add(inspect_panel(0.0, 1.0))
        while frontier:
            if (
                all(leaf.error is not None for leaf in frontier.values())
                and _finite_sum(leaf.error for leaf in frontier.values()) <= tolerance
            ):
                value, error = _frontier_total(frontier.values())
                if error <= tolerance:
                    return value, "resolved", error, evaluations, panels
            _, _, _, key = heapq.heappop(priorities)
            parent = frontier[key]
            middle = (parent.start + parent.end) / 2
            if middle in (parent.start, parent.end):
                return None, "numerical", None, evaluations, panels
            left = inspect_panel(parent.start, middle)
            right = inspect_panel(middle, parent.end)
            # Keep the old complete coverage until BOTH children are present.
            del frontier[key]
            add(left)
            add(right)
        raise ArithmeticError("missing finite-chord frontier")
    except _WorkLimit:
        return None, "work_limit", None, evaluations, panels
    except (ArithmeticError, FloatingPointError):
        # Keep setup, panel, low-rule, high-rule and final-sum failures distinct
        # from unexpected ValueError/TypeError, with all attempted work retained.
        return None, "numerical", None, evaluations, panels


def circular_segment_normal_derivative(
    pixels_xy,
    radius,
    chord_fraction,
    *,
    centre,
    normal=(1.0, 0.0),
    sensor_shape,
    homography,
    psf_covariance,
    probability_tolerance=1e-8,
    max_panels=4096,
    max_evaluations=2_000_000,
):
    """dP/dphi for a CCW normal rotation in radians; no fitted parameters.

    The inherited probability_tolerance name denotes an absolute allowance for
    this signed derivative. Its estimated error is not a certified enclosure.
    Queries use integer indices plus .5. The evaluation limit is cumulative in
    input order; max_panels limits each query, including its analytic attempt.
    An analytic attempt charges two endpoint units and one panel before fallback.
    Quadrature charges two endpoint units per inspected panel and every attempted
    12/24-rule node. All work spent before a fallback remains in returned counts.
    """
    pixels, _ = centre_fit._pixels(pixels_xy, sensor_shape)
    normal = centre_fit._normal(normal)
    raw_h = centre_fit._array(homography, (3, 3), "homography").copy()
    covariance = centre_fit._array(psf_covariance, (2, 2), "psf_covariance").copy()
    controls = centre_fit._controls(probability_tolerance, max_panels, max_evaluations)
    _, h, inverse, chart_margin, reflected = centre_fit._segment_geometry(
        radius, chord_fraction, centre, normal, raw_h, covariance
    )
    # Keep original supplied classification even if homogeneous normalization
    # underflows a nonzero perspective coefficient. Both maps have a closed form.
    supplied_affine = bool(np.all(raw_h[2, :2] == 0))
    closed_method = "affine_closed_form" if supplied_affine else "projective_closed_form"
    radius, fraction = float(radius), float(chord_fraction)
    half_chord = radius * math.sqrt((1 - fraction) * (1 + fraction))
    tangent = np.array([-normal[1], normal[0]])
    curve = finite._Curve(
        radius * fraction * normal - half_chord * tangent,
        2 * half_chord * tangent,
        0.0,
        0.0,
        0.0,
        1.0,
    )
    tolerance, panel_limit, evaluation_limit = controls
    try:
        normalizer = _normalizer(h, inverse)
        reflected = normalizer.reflected
    except (ArithmeticError, FloatingPointError):
        # Valid supplied geometry can still have an unsupported represented
        # operational map. This is neither a physical-singularity assertion nor
        # a reason to fabricate zero probability sensitivity. Setup has fixed
        # size and adds no query-node work; affordable attempts retain 2/1 units.
        normalizer = None
    derivatives, statuses, estimates, methods, query_work, query_panels = [], [], [], [], [], []
    evaluations, panels = 0, 0
    for point in pixels.astype(float) + 0.5:
        used, count = 0, 0
        value, status, error, method = None, "work_limit", None, "not_attempted"
        if evaluations + 2 <= evaluation_limit:
            used, count, method = 2, 1, closed_method
            if normalizer is None:
                status = "numerical"
            else:
                try:
                    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                        value, error = _closed_form(
                            point,
                            h,
                            inverse,
                            normal,
                            radius,
                            fraction,
                            half_chord,
                            tolerance,
                            normalizer=normalizer,
                        )
                    status = "resolved"
                except (ArithmeticError, FloatingPointError):
                    method += "_then_chord_quadrature"
                    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                        value, status, error, fallback_work, fallback_panels = _quadrature_one(
                            point,
                            curve,
                            h,
                            inverse,
                            half_chord,
                            tolerance,
                            panel_limit - count,
                            evaluation_limit - evaluations - used,
                            normalizer=normalizer,
                        )
                    used += fallback_work
                    count += fallback_panels
        derivatives.append(value)
        statuses.append(status)
        estimates.append(error)
        methods.append(method)
        query_work.append(used)
        query_panels.append(count)
        evaluations += used
        panels += count
    return NormalDerivative(
        tuple(derivatives),
        tuple(statuses),
        tuple(estimates),
        evaluations,
        panels,
        tuple(methods),
        tuple(query_work),
        tuple(query_panels),
        float(chart_margin),
        bool(reflected),
    )
