"""Directed Gaussian bounds, independently evaluated positive-series controls."""

import math
from decimal import Context, localcontext
from decimal import Decimal as D
from fractions import Fraction as F

import pytest

from backend import normal_cdf_bounds as cdf

PI = D(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117067982148086513282306647"
)


def decimal(f):
    return D(f.numerator) / D(f.denominator)


def positive_series(z):
    """Independent stable positive erf series (DLMF7.6.2), not alternating integral."""
    with localcontext() as context:
        context.prec = 110
        x = decimal(abs(z))
        if not x:
            return D("0.5")
        term = total = x
        for n in range(1000):
            term = term * x * x / D(2 * n + 3)
            total += term
            if term < D("1e-105"):
                break
        else:
            raise AssertionError("independent Decimal oracle failed to converge")
        answer = D("0.5") + (-x * x / 2).exp() * total / (2 * PI).sqrt()
        return answer if z >= 0 else 1 - answer


@pytest.mark.parametrize(
    "z", [F(-6), F(-7, 2), F(-1, 3), F(0), F(1, 10**40), F(1, 3), F(1), F(17, 4), F(6)]
)
def test_exact_outward_bounds_cover_independent_high_precision_series(z):
    result = cdf.normal_cdf_bounds(z)
    value = positive_series(z)
    with localcontext() as context:
        context.prec = 110
        assert decimal(result.lower) <= value <= decimal(result.upper)
    assert F(0) <= result.lower <= result.upper <= F(1)
    assert result.upper - result.lower <= F(2, 10**30)
    if z:
        assert result.certificate.tail_ratio_upper < 1
        assert result.certificate.omitted_sign == (-1) ** result.terms


def test_pi_normalization_is_enclosed_by_integer_inequalities():
    pi_low, pi_high, low, high = cdf.normalization_bounds()
    with localcontext() as context:
        context.prec = 110
        assert decimal(pi_low) <= PI <= decimal(pi_high)
    assert 2 * pi_high * low * low <= 1
    assert 2 * pi_low * high * high >= 1
    assert low < high
    # Machin's angle identity, independently verified by rational tangent addition.
    q = F(1, 5)
    twice = 2 * q / (1 - q * q)
    four = 2 * twice / (1 - twice * twice)
    assert (four - F(1, 239)) / (1 + four * F(1, 239)) == 1


def test_reflection_and_hostile_decimal_context_leave_exact_results_unchanged():
    expected = cdf.normal_cdf_bounds(F(3, 2)).to_dict()
    with localcontext(Context(prec=2, Emin=-2, Emax=2, clamp=1)):
        actual = cdf.normal_cdf_bounds(F(3, 2)).to_dict()
    assert actual == expected
    positive, negative = cdf.normal_cdf_bounds(F(3, 2)), cdf.normal_cdf_bounds(F(-3, 2))
    assert (negative.lower, negative.upper) == (1 - positive.upper, 1 - positive.lower)


def test_finer_requested_grid_and_exact_zero():
    for places in (1, 6, 15, 30):
        result = cdf.normal_cdf_bounds("0.75", places=places)
        assert result.upper - result.lower <= F(2, 10**places)
    zero = cdf.normal_cdf_bounds(0)
    assert zero.lower == zero.upper == F(1, 2) and zero.terms == 0


def test_floating_point_cdf_is_not_silently_certified():
    rigorous = cdf.normal_cdf_bounds(1)
    rounded = F.from_float(0.5 * math.erfc(-1 / math.sqrt(2)))
    assert not rigorous.lower <= rounded <= rigorous.upper
    with pytest.raises(TypeError):
        cdf.normal_cdf_bounds(1.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"places": 0},
        {"places": 31},
        {"max_terms": 0},
        {"max_terms": 257},
        {"places": True},
        {"max_terms": 2.0},
    ],
)
def test_unsupported_resource_requests_are_refused(kwargs):
    with pytest.raises((ValueError, TypeError)):
        cdf.normal_cdf_bounds(1, **kwargs)


def test_magnitude_and_term_exhaustion_are_not_model_incompatibility():
    with pytest.raises(ValueError, match="budget exhausted"):
        cdf.normal_cdf_bounds(6, max_terms=1)
    with pytest.raises(ValueError, match="\\[-6, 6\\]"):
        cdf.normal_cdf_bounds("6.00000001")
