"""Outward rational bounds for a declared standard-normal CDF on [-6, 6].

An alternating integral series has an explicit first-omitted-term remainder.
Integer fixed-grid rounding encloses every term and sum. Machin arctangent
bounds plus integer square roots enclose 1/sqrt(2*pi). No binary floating-point
value is promoted to an exact Gaussian probability. Bounds concern the supplied
dimensionless coordinate and mathematical Gaussian, not camera calibration.
"""

import math
from dataclasses import dataclass
from fractions import Fraction as F
from functools import lru_cache

from .response_calibration import parse_exact

INTERNAL_PLACES = 60
MAX_PLACES = 30
MAX_TERMS = 256
MAX_ABS_Z = F(6)
SCALE = 10**INTERNAL_PLACES


def _floor(value):
    return value.numerator // value.denominator


def _ceil(value):
    return -((-value.numerator) // value.denominator)


def _atan_bounds(q, terms):
    total = sum(((-1) ** n * q ** (2 * n + 1) / (2 * n + 1) for n in range(terms)), F(0))
    omitted = q ** (2 * terms + 1) / (2 * terms + 1)
    return (total, total + omitted) if terms % 2 == 0 else (total - omitted, total)


@lru_cache(maxsize=1)
def normalization_bounds():
    """Return exact (pi_lower, pi_upper, c_lower, c_upper), c=1/sqrt(2*pi).

    pi = 16*atan(1/5)-4*atan(1/239). Each arctangent is bounded by its alternating
    series. Integer-square-root comparisons bound the reciprocal normalization.
    The cached tuple is immutable; no decimal or floating context is used.
    """
    a_low, a_high = _atan_bounds(F(1, 5), 48)
    b_low, b_high = _atan_bounds(F(1, 239), 16)
    pi_low, pi_high = 16 * a_low - 4 * b_high, 16 * a_high - 4 * b_low
    # isqrt(floor(r)) == floor(sqrt(r)) for nonnegative rational r.
    lower_integer = math.isqrt((SCALE**2 * pi_high.denominator) // (2 * pi_high.numerator))
    upper_integer = math.isqrt((SCALE**2 * pi_low.denominator) // (2 * pi_low.numerator)) + 1
    return pi_low, pi_high, F(lower_integer, SCALE), F(upper_integer, SCALE)


@dataclass(frozen=True)
class CDFCertificate:
    internal_places: int
    partial_sum_lower: F
    partial_sum_upper: F
    first_omitted_term_lower: F
    first_omitted_term_upper: F
    omitted_sign: int
    tail_ratio_upper: F
    integral_lower: F
    integral_upper: F
    normalization_lower: F
    normalization_upper: F

    def to_dict(self):
        return {
            key: str(value) if isinstance(value, F) else value
            for key, value in self.__dict__.items()
        }


@dataclass(frozen=True)
class NormalCDFBounds:
    z: F
    lower: F
    upper: F
    places: int
    terms: int
    reflected: bool
    certificate: CDFCertificate | None

    def to_dict(self):
        return {
            "z": str(self.z),
            "output": [str(self.lower), str(self.upper)],
            "places": self.places,
            "terms": self.terms,
            "reflected": self.reflected,
            "certificate": None if self.certificate is None else self.certificate.to_dict(),
            "scope": "Mathematical standard-normal CDF at the exact supplied z; no physical camera-model claim.",
        }


def normal_cdf_bounds(z, *, places=30, max_terms=256):
    """Closed outward decimal-grid cover of Phi(z), width <= 2*10**(-places).

    z is an exact decimal string/int/Fraction with |z|<=6. places is an integer
    1..30; max_terms is an integer 1..256. Invalid inputs or insufficient terms
    raise an error, never a physical/model incompatibility verdict. All internal
    arithmetic is rational or integer; bounds include directed rounding, series
    remainder and the normalizing constant. Reflection handles negative z.
    """
    z = parse_exact(z)
    if abs(z) > MAX_ABS_Z:
        raise ValueError("standard-normal z must lie in [-6, 6]")
    if type(places) is not int:
        raise TypeError("places must be an integer")
    if type(max_terms) is not int:
        raise TypeError("max_terms must be an integer")
    if not 1 <= places <= MAX_PLACES or not 1 <= max_terms <= MAX_TERMS:
        raise ValueError("places must be 1-30 and max_terms must be 1-256")
    if z == 0:
        return NormalCDFBounds(z, F(1, 2), F(1, 2), places, 0, False, None)
    x, reflected = abs(z), z < 0
    square = x * x
    _, _, c_low, c_high = normalization_bounds()
    term_low, term_high = _floor(x * SCALE), _ceil(x * SCALE)
    partial_low = partial_high = 0
    target_scale = 10**places
    for n in range(max_terms):
        if n % 2 == 0:
            partial_low += term_low
            partial_high += term_high
        else:
            partial_low -= term_high
            partial_high -= term_low
        ratio = square * (2 * n + 1) / (2 * (n + 1) * (2 * n + 3))
        term_low, term_high = _floor(term_low * ratio), _ceil(term_high * ratio)
        included = n + 1
        # For every k>=included, t_(k+1)/t_k <= x^2/[2*(k+1)].
        tail_ratio = square / (2 * (included + 1))
        if tail_ratio >= 1:
            continue
        omitted_sign = 1 if included % 2 == 0 else -1
        integral_low, integral_high = partial_low, partial_high
        if omitted_sign > 0:
            integral_high += term_high
        else:
            integral_low -= term_high
        integral_low, integral_high = F(integral_low, SCALE), F(integral_high, SCALE)
        products = [a * b for a in (integral_low, integral_high) for b in (c_low, c_high)]
        raw_low, raw_high = F(1, 2) + min(products), F(1, 2) + max(products)
        if raw_high - raw_low > F(1, 4 * target_scale):
            continue
        low = max(F(0), F(_floor(raw_low * target_scale), target_scale))
        high = min(F(1), F(_ceil(raw_high * target_scale), target_scale))
        if high - low > F(2, target_scale):
            continue
        certificate = CDFCertificate(
            INTERNAL_PLACES,
            F(partial_low, SCALE),
            F(partial_high, SCALE),
            F(term_low, SCALE),
            F(term_high, SCALE),
            omitted_sign,
            tail_ratio,
            integral_low,
            integral_high,
            c_low,
            c_high,
        )
        if reflected:
            low, high = 1 - high, 1 - low
        return NormalCDFBounds(z, low, high, places, included, reflected, certificate)
    raise ValueError("CDF term budget exhausted before the requested outward width")
