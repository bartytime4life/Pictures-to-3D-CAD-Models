"""Finite Decimal interval arithmetic for conditional numerical enclosures.

Every elementary operation is rounded outward at 60 significant digits, with
explicit contexts independent of decimal.getcontext() and decimal.DefaultContext.
This encloses arithmetic error; it supplies no physical observation-error budget.
Unsupported domains/overflow and exhausted series raise instead of returning a
purported enclosure. Normal-CDF tails beyond +/-8 deliberately remain coarse.
"""

from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
)
from functools import lru_cache

_PRECISION = 60
_MAX_TERMS = 256
_SERIES_EPS = Decimal("1e-65")


def _context(rounding):
    return Context(prec=_PRECISION, rounding=rounding, Emin=-999999,
                   Emax=999999, capitals=1, clamp=0, flags=[],
                   traps=[InvalidOperation, DivisionByZero, Overflow])


_DOWN = _context(ROUND_FLOOR)
_UP = _context(ROUND_CEILING)
_NEAREST = _context(ROUND_HALF_EVEN)
_ZERO, _ONE, _HALF, _EIGHT = map(Decimal, ("0", "1", ".5", "8"))


def _decimal(value):
    if isinstance(value, bool):
        raise TypeError("logical values are not interval endpoints")
    if isinstance(value, float):
        result = Decimal.from_float(value)
    elif isinstance(value, (Decimal, int, str)):
        result = Decimal(value, context=_NEAREST)
    else:
        raise TypeError("interval endpoints must be Decimal, int, str, or finite float")
    if not result.is_finite():
        raise ValueError("interval endpoints must be finite")
    return result


@dataclass(frozen=True)
class Interval:
    """Closed finite interval; floats are exact binary values, bool is rejected."""

    lo: Decimal
    hi: Decimal

    def __post_init__(self):
        lo, hi = _decimal(self.lo), _decimal(self.hi)
        if lo > hi:
            raise ValueError("interval lower endpoint exceeds upper endpoint")
        object.__setattr__(self, "lo", lo)
        object.__setattr__(self, "hi", hi)

    @classmethod
    def point(cls, value):
        value = _decimal(value)
        return cls(value, value)

    def __add__(self, other):
        other = _interval(other)
        return Interval(_DOWN.add(self.lo, other.lo), _UP.add(self.hi, other.hi))

    __radd__ = __add__

    def __neg__(self):
        # Decimal's unary minus applies the active context; copy_negate is exact.
        return Interval(self.hi.copy_negate(), self.lo.copy_negate())

    def __sub__(self, other):
        return self + (-_interval(other))

    def __rsub__(self, other):
        return _interval(other) - self

    def __mul__(self, other):
        other = _interval(other)
        if self.lo >= 0 and other.lo >= 0:
            return Interval(_DOWN.multiply(self.lo, other.lo),
                            _UP.multiply(self.hi, other.hi))
        pairs = ((self.lo, other.lo), (self.lo, other.hi),
                 (self.hi, other.lo), (self.hi, other.hi))
        return Interval(min(_DOWN.multiply(a, b) for a, b in pairs),
                        max(_UP.multiply(a, b) for a, b in pairs))

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = _interval(other)
        if other.lo <= 0 <= other.hi:
            raise ZeroDivisionError("interval divisor contains zero")
        reciprocal = Interval(_DOWN.divide(_ONE, other.hi),
                              _UP.divide(_ONE, other.lo))
        return self * reciprocal

    def __rtruediv__(self, other):
        return _interval(other) / self

    def sqrt(self):
        """Enclose sqrt, including its HALF_EVEN rounding, with adjacent values.

        Python 3.12 Decimal.sqrt is correctly rounded using HALF_EVEN regardless
        of context rounding. See decimal docs and mpdecimal's square-root docs:
        https://docs.python.org/3.12/library/decimal.html#decimal.Decimal.sqrt
        https://www.bytereef.org/mpdecimal/doc/libmpdec/arithmetic.html#square-root
        """
        if self.lo < 0:
            raise ValueError("square root requires a nonnegative interval")
        lo = (_ZERO if self.lo == 0 else
              max(_ZERO, _NEAREST.next_minus(_NEAREST.sqrt(self.lo))))
        hi = (_ZERO if self.hi == 0 else
              _NEAREST.next_plus(_NEAREST.sqrt(self.hi)))
        return Interval(lo, hi)


def _interval(value):
    return value if isinstance(value, Interval) else Interval.point(value)


def _alternating_tail(next_term, positive):
    # The remainder is between zero and the first omitted signed term.
    return (Interval(_ZERO, next_term.hi) if positive else
            Interval(next_term.hi.copy_negate(), _ZERO))


def _atan_reciprocal(denominator):
    """atan(1/q), q>1, by an everywhere decreasing alternating series."""
    power = Interval.point(1) / denominator
    total = power
    square = denominator * denominator
    for n in range(_MAX_TERMS):
        power = power / square
        following = power / (2 * n + 3)
        positive = (n + 1) % 2 == 0
        if following.hi <= _SERIES_EPS:
            return total + _alternating_tail(following, positive)
        total = total + following if positive else total - following
    raise ArithmeticError("atan enclosure series exhausted its work limit")


@lru_cache(maxsize=1)
def _normalizer():
    # Machin: pi = 16 atan(1/5) - 4 atan(1/239). Both series have explicit
    # alternating remainders; no floating-point pi/sqrt/exp/erf is trusted.
    pi = 16 * _atan_reciprocal(5) - 4 * _atan_reciprocal(239)
    return 1 / (2 * pi).sqrt()


@lru_cache(maxsize=2048)
def _cdf_endpoint(x):
    if x == 0:
        return Interval.point(_HALF)
    if x < 0:
        return 1 - _cdf_endpoint(x.copy_abs())
    if x > _EIGHT:
        return Interval(_cdf_endpoint(_EIGHT).lo, _ONE)
    # Integral_0^x exp(-t*t/2) dt = sum_n (-1)^n a_n,
    # a_n = x^(2n+1)/((2n+1)*2^n*n!). All a_n are enclosed positively.
    # a_(n+1)/a_n < x^2/(2(n+1)); once that last bound <=1, every
    # subsequent term decreases. Never use a remainder before this proof holds.
    square = Interval.point(x) * x
    term = total = Interval.point(x)
    for n in range(_MAX_TERMS):
        following = term * square * (2 * n + 1) / (2 * (n + 1) * (2 * n + 3))
        positive = (n + 1) % 2 == 0
        if square.hi <= 2 * (n + 1) and following.hi <= _SERIES_EPS:
            integral = total + _alternating_tail(following, positive)
            result = _HALF + integral * _normalizer()
            return Interval(max(_HALF, result.lo), min(_ONE, result.hi))
        total = total + following if positive else total - following
        term = following
    raise ArithmeticError("normal-CDF enclosure series exhausted its work limit")


def normal_cdf(value: Interval) -> Interval:
    """Enclose the standard normal CDF over a finite closed input interval.

    Monotonicity reduces the input interval to endpoint calculations. Outside
    +/-8, monotonicity and the probability range give a deliberately broad tail
    enclosure; this is not evaluation at the clipped input or a tail estimate.
    Endpoint and normalization caches are bounded and hold immutable intervals.
    """
    if not isinstance(value, Interval):
        raise TypeError("normal_cdf requires an Interval")
    return Interval(_cdf_endpoint(value.lo).lo, _cdf_endpoint(value.hi).hi)
