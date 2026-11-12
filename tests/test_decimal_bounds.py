"""Independent rational and high-precision checks of conditional enclosures."""

from dataclasses import FrozenInstanceError
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_UP,
    Context,
    Decimal,
    DefaultContext,
    FloatOperation,
    InvalidOperation,
    Overflow,
    localcontext,
)
from fractions import Fraction

import pytest

from backend import decimal_bounds as bounds
from backend.decimal_bounds import Interval, normal_cdf


def contains(interval, value):
    return Fraction(interval.lo) <= Fraction(value) <= Fraction(interval.hi)


def reference_cdf(x):
    """Independent nonalternating expansion times exp(-x*x/2), at 140 digits.

    This regression oracle is not a certified primitive. Its pi constant has
    120 decimal digits; its positive series differs from the production
    alternating integral and uses Decimal.exp only here, never in production.
    """
    pi = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117067982148086513282306647")
    with localcontext(Context(prec=140)):
        x = Decimal(x)
        positive = abs(x)
        term = total = positive
        for n in range(1000):
            term = term * positive * positive / (2 * n + 3)
            total += term
            if term < Decimal("1e-120"):
                answer = Decimal(".5") + (-positive * positive / 2).exp() * total / (2 * pi).sqrt()
                return answer if x >= 0 else 1 - answer
        raise AssertionError("independent reference series did not converge")


def test_point_conversion_is_exact_and_immutable():
    assert Interval.point(0.1).lo == Decimal.from_float(0.1)
    assert Interval.point("0.1").lo == Decimal(".1")
    assert Interval.point(3) == Interval(Decimal(3), Decimal(3))
    with pytest.raises(FrozenInstanceError):
        Interval.point(1).lo = Decimal(2)


@pytest.mark.parametrize("logical", [False, True])
def test_logical_values_are_not_silently_numeric(logical):
    with pytest.raises(TypeError, match="logical"):
        Interval.point(logical)
    with pytest.raises(TypeError, match="logical"):
        Interval(logical, 2)
    with pytest.raises(TypeError, match="logical"):
        Interval.point(2) + logical


def test_float_input_is_exact_even_when_float_mixing_is_trapped():
    with localcontext() as context:
        context.prec = 2
        context.traps[FloatOperation] = True
        for value in (0.1, -0.0, 5e-324, 1.7976931348623157e308):
            actual = Interval.point(value)
            assert actual.lo == actual.hi == Decimal.from_float(value)
        assert Interval.point(-0.0).lo.is_signed()
        assert not context.flags[FloatOperation]
    assert normal_cdf(Interval.point(-0.0)) == Interval.point(".5")


def test_invalid_decimal_syntax_cannot_become_an_unchecked_nan():
    with localcontext() as context:
        context.traps[InvalidOperation] = False
        with pytest.raises(InvalidOperation):
            Interval.point("not a decimal")
        assert not context.flags[InvalidOperation]


@pytest.mark.parametrize("bad", ["NaN", "sNaN", "Infinity", "-Infinity", float("inf"), float("nan")])
def test_nonfinite_inputs_are_rejected(bad):
    with pytest.raises(ValueError):
        Interval.point(bad)
    with pytest.raises(ValueError):
        Interval(0, bad)


def test_invalid_domains_are_rejected():
    with pytest.raises(ValueError):
        Interval(2, 1)
    with pytest.raises(ValueError):
        Interval(-1, 2).sqrt()
    with pytest.raises(TypeError):
        Interval.point(object())
    with pytest.raises(TypeError):
        normal_cdf(1)
    for divisor in (Interval(-1, 1), Interval(0, 1), Interval(-1, 0), Interval.point(0)):
        with pytest.raises(ZeroDivisionError):
            Interval.point(1) / divisor


@pytest.mark.parametrize("a,b", [
    (("-7.01", "-2.3"), ("-3.7", "-0.09")),
    (("-3", "0"), ("1.3", "9.1")),
    (("-3", "4"), ("-2", "7")),
    (("0", "4"), ("1.3", "9.1")),
    (("0.1234567890123456789012345678901234567890123456789012345678901234567", "2"),
     ("-3.1", "-0.000000000000000000000000000000000000000000000000001")),
])
def test_arithmetic_contains_exact_rational_extrema(a, b):
    left, right = Interval(*a), Interval(*b)
    endpoints = [(Fraction(x), Fraction(y)) for x in (left.lo, left.hi) for y in (right.lo, right.hi)]
    for actual, exact in ((left + right, [x + y for x, y in endpoints]),
                          (left - right, [x - y for x, y in endpoints]),
                          (left * right, [x * y for x, y in endpoints])):
        assert contains(actual, min(exact)) and contains(actual, max(exact))
    if not right.lo <= 0 <= right.hi:
        exact = [x / y for x, y in endpoints]
        assert contains(left / right, min(exact)) and contains(left / right, max(exact))


def test_reflected_operators_and_exact_negation():
    long = Decimal("1.23456789012345678901234567890123456789012345678901234567890123456789")
    assert (-Interval.point(long)).lo == long.copy_negate()
    assert contains(3 + Interval.point(".25"), Fraction(13, 4))
    assert contains(3 - Interval.point(".25"), Fraction(11, 4))
    assert contains(3 * Interval.point(".25"), Fraction(3, 4))
    assert contains(3 / Interval.point(7), Fraction(3, 7))


@pytest.mark.parametrize("low,high", [("0", "0"), ("0", "2"), ("2", "3"),
                                      ("4", "4"), ("1e-100", "3e-99"), ("1e100", "4e101")])
def test_square_root_bounds_are_verified_by_exact_squaring(low, high):
    result = Interval(low, high).sqrt()
    assert result.lo >= 0
    assert Fraction(result.lo) ** 2 <= Fraction(Decimal(low))
    assert Fraction(result.hi) ** 2 >= Fraction(Decimal(high))
    if low == high == "0":
        assert result == Interval.point(0)


def rational_exp_enclosure(value):
    """Independent exact-rational Taylor enclosure, for |value|<=8.

    For positive x the tail after term160 is bounded geometrically: its first
    term is a161, and every following ratio is <=x/162<1. Negative x uses the
    reciprocal enclosure. No Decimal.exp or floating exponential is used.
    """
    value = Fraction(value)
    if value < 0:
        low, high = rational_exp_enclosure(-value)
        return 1 / high, 1 / low
    assert value <= 8
    term = total = Fraction(1)
    for n in range(1, 161):
        term = term * value / n
        total += term
    first_omitted = term * value / 161
    return total, total + first_omitted / (1 - value / 162)


@pytest.mark.parametrize("value", ["-8", "-3", "-1", "-.125", "0", ".125", ".5", "1", "3", "8"])
def test_exponential_contains_an_independent_rational_enclosure(value):
    low, high = rational_exp_enclosure(Decimal(value))
    result = Interval.point(value).exp()
    assert Fraction(result.lo) <= low <= high <= Fraction(result.hi)
    if value == "0":
        assert result == Interval.point(1)


def test_exponential_interval_is_monotone_and_preserves_exact_zero_endpoint():
    result = Interval("-3", ".125").exp()
    low, _ = rational_exp_enclosure(-3)
    _, high = rational_exp_enclosure(Fraction(1, 8))
    assert Fraction(result.lo) <= low and high <= Fraction(result.hi)
    assert result.lo == Interval.point(-3).exp().lo
    assert result.hi == Interval.point(".125").exp().hi
    assert Interval("-1", "0").exp().hi == 1
    assert Interval("0", "1").exp().lo == 1
    assert Interval.point("-0").exp() == Interval.point(1)


def test_exponential_underflow_retains_positive_upper_bound():
    # exp(-3000000) is positive but below the smallest output subnormal. It
    # cannot become the singleton zero. Gaussian exponents may reach this case.
    result = Interval.point(-3_000_000).exp()
    assert result.lo == 0 and result.hi == Decimal("1e-1000058")
    assert Interval(-3_000_000, 0).exp() == Interval(0, 1)


def test_exponential_overflow_is_explicit_even_when_only_padding_overflows(monkeypatch):
    with pytest.raises(Overflow):
        Interval.point(3_000_000).exp()
    # At prec3/Emax2, exp(6.907) rounds to finite999 but its next value is
    # Infinity. Refuse this too; finite endpoints must not hide upper overflow.
    monkeypatch.setattr(bounds, "_NEAREST", Context(prec=3, Emin=-2, Emax=2))
    assert bounds._NEAREST.exp(Decimal("6.907")) == Decimal(999)
    with pytest.raises(Overflow, match="enclosure exceeds"):
        Interval.point("6.907").exp()


def test_underflow_rounds_outward_in_both_signs_and_square_root():
    # At prec60/Emin-999999 the smallest positive subnormal is 1e-1000058.
    # These exact Decimal literals remain representable as inputs even when an
    # operation's output needs directed underflow. Avoid constructing enormous
    # Fractions: comparison of finite Decimals is exact and context-independent.
    positive = Interval.point("1e-1000058") / 10
    negative = Interval.point("-1e-1000058") / 10
    assert positive.lo == 0 and positive.hi == Decimal("1e-1000058")
    assert negative.lo == Decimal("-1e-1000058") and negative.hi == 0
    assert positive.lo <= Decimal("1e-1000059") <= positive.hi
    assert negative.lo <= Decimal("-1e-1000059") <= negative.hi
    root = Interval.point("1e-2000200").sqrt()
    assert root.lo == 0 < Decimal("1e-1000100") <= root.hi
    cdf = normal_cdf(Interval.point("1e-1000100"))
    assert cdf.lo == Decimal(".5") < cdf.hi


@pytest.mark.parametrize("operation", [
    lambda: Interval.point("1e999999") * 10,
    lambda: Interval.point(1) / Interval.point("1e-1000000"),
    lambda: Interval.point("1e2000000").sqrt(),
])
def test_overflow_fails_instead_of_returning_a_finite_uncertified_bound(operation):
    with pytest.raises(Overflow):
        operation()


@pytest.mark.parametrize("x", ["-8", "-3", "-.125", "0", ".125", ".5", "1", "2", "3", "6", "7.9", "8"])
def test_normal_cdf_contains_independent_high_precision_reference(x):
    result = normal_cdf(Interval.point(x))
    assert contains(result, reference_cdf(x))
    assert Fraction(result.hi) - Fraction(result.lo) < Fraction(1, 10**38)


@pytest.mark.parametrize("x,prefix", [
    (".5", ".69146246127401310363770461060833773988360217555458"),
    ("1", ".84134474606854294858523254563203792247791296672660"),
    ("2", ".97724986805182079279971736283346656252822377629832"),
    ("3", ".99865010196836990547334818523240502262217063184161"),
    ("8", ".99999999999999937790394257282158764840048274118115"),
])
def test_known_normal_cdf_digits(x, prefix):
    # Check the independent oracle's leading digits as well as containment.
    with localcontext(Context(prec=140)):
        assert abs(reference_cdf(x) - Decimal(prefix)) < Decimal("1e-50")
    result = normal_cdf(Interval.point(x))
    assert contains(result, reference_cdf(x))


def test_cdf_containment_near_branch_boundaries_and_across_the_cancellation_region():
    # Unique rational-grid endpoints exercise the growing early terms near8,
    # with an independent nonalternating oracle. Include both sides of the
    # deliberately coarse tail branch and very small values around symmetry0.
    with localcontext(Context(prec=140)):
        grid = [Decimal(k) / 8 for k in range(-64, 65)]
        grid += [Decimal("8.00000000000000000001"), Decimal("7.99999999999999999999"),
                 Decimal("-8.00000000000000000001"), Decimal("-7.99999999999999999999"),
                 Decimal("1e-70"), Decimal("-1e-70")]
    for x in grid:
        actual = normal_cdf(Interval.point(x))
        assert contains(actual, reference_cdf(x)), (x, actual)


def test_zero_symmetry_monotonicity_and_input_interval():
    assert normal_cdf(Interval.point(0)) == Interval.point(".5")
    for x in (".125", "1.3", "7.999999999999999999999999"):
        assert normal_cdf(Interval.point(Decimal(x).copy_negate())) == 1 - normal_cdf(Interval.point(x))
    result = normal_cdf(Interval("-.5", "2"))
    assert result.lo == normal_cdf(Interval.point("-.5")).lo
    assert result.hi == normal_cdf(Interval.point(2)).hi
    assert contains(result, reference_cdf("-.5"))
    assert contains(result, reference_cdf(2))


def test_tail_enclosures_are_explicitly_coarse_and_monotone():
    eight = normal_cdf(Interval.point(8))
    tail = normal_cdf(Interval(9, "1e1000000"))
    assert tail == Interval(eight.lo, 1)
    assert normal_cdf(Interval("-1e1000000", -9)) == 1 - tail
    assert normal_cdf(Interval(-9, 9)) == Interval(0, 1)
    assert contains(tail, reference_cdf(9))


def test_all_primitives_ignore_adversarial_global_context():
    def calculation():
        a, b = Interval("-.1234567890123456789", "2.7890123456789012345"), Interval(".3", "1.7")
        return (a + b, a - b, -a, a * b, a / b, b.sqrt(), a.exp(), b.exp(),
                Interval.point(0.1), normal_cdf(Interval("-.3141592653589793", "7.123456789012345")))

    expected = calculation()
    bounds._cdf_endpoint.cache_clear()
    bounds._normalizer.cache_clear()
    with localcontext() as context:
        context.prec, context.rounding = 2, ROUND_UP
        context.Emax, context.Emin = 2, -2
        for signal in context.traps:
            context.traps[signal] = True
        before = context.copy()
        assert calculation() == expected
        assert context.flags == before.flags
        assert context.prec == before.prec and context.rounding == before.rounding


def test_context_factory_is_independent_of_mutated_default_context(monkeypatch):
    # Context() inherits unspecified fields from DefaultContext, not merely the
    # current context. Recreate the private contexts under an adversarial default
    # without reloading the module or changing the public Interval class identity.
    argument = Interval("-.2718281828459045", "7.6543210987654321")
    expected = normal_cdf(argument), argument.exp()
    for name, value in {"prec": 2, "rounding": ROUND_UP, "Emin": -2,
                        "Emax": 2, "capitals": 0, "clamp": 1}.items():
        monkeypatch.setattr(DefaultContext, name, value)
    for signal in DefaultContext.traps:
        monkeypatch.setitem(DefaultContext.traps, signal, True)
        monkeypatch.setitem(DefaultContext.flags, signal, True)
    for name, rounding in (("_DOWN", ROUND_FLOOR), ("_UP", ROUND_CEILING),
                           ("_NEAREST", ROUND_HALF_EVEN)):
        fresh = bounds._context(rounding)
        assert fresh.prec == 60 and fresh.Emin == -999999 and fresh.Emax == 999999
        assert fresh.clamp == 0 and fresh.capitals == 1
        assert not any(fresh.flags.values())
        monkeypatch.setattr(bounds, name, fresh)
    bounds._cdf_endpoint.cache_clear()
    bounds._normalizer.cache_clear()
    assert (normal_cdf(argument), argument.exp()) == expected


def test_exhausted_series_raises_without_partial_result(monkeypatch):
    bounds._cdf_endpoint.cache_clear()
    monkeypatch.setattr(bounds, "_MAX_TERMS", 0)
    with pytest.raises(ArithmeticError, match="work limit"):
        normal_cdf(Interval.point("2.34567890123456789"))
    with pytest.raises(ArithmeticError, match="work limit"):
        bounds._atan_reciprocal(5)


def test_endpoint_cache_is_bounded():
    assert bounds._cdf_endpoint.cache_info().maxsize == 2048
    assert bounds._normalizer.cache_info().maxsize == 1
