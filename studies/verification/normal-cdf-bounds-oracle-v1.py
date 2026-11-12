"""Replay bounded, independent exact-rational standard-normal CDF controls.

Requires --output NEW_JSON; --help/refusal never run the census. Every named,
seeded, certificate, reflection and schema/resource outcome is retained, including
failures. No photograph, optical calibration or physical error bound is involved.

The reference does not reuse the production alternating integral or fixed-grid
recurrence. For x>=0 it uses I(x)=exp(-x*x/2)*S(x), where
S(x)=sum x**(2*n+1)/(2*n+1)!!. Indeed S'=1+x*S, so I'=exp(-x*x/2), I(0)=0.
Both S and exp(x*x/2) are positive series. Their first omitted terms and decreasing
successive-term ratios give geometric upper tails; reciprocal positive exp bounds
then enclose exp(-x*x/2). A different pi identity,
pi=4*(atan(1/2)+atan(1/3)), uses exact alternating remainders. The tangent-addition
value is 1 and both positive angles sum below pi/2, fixing its quadrant. Rational
bisection, rather than integer square roots, encloses 1/sqrt(2*pi).
"""

import argparse
import hashlib
import json
import platform
import random
import subprocess
import sys
import time
from dataclasses import replace
from decimal import Context, localcontext
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SEED = 290641
SEEDED_CASES = 24
MAX_REFERENCE_TERMS = 512
REFERENCE_PLACES = 80
SERIES_TOLERANCE = F(1, 10**100)
PI_TOLERANCE = F(1, 10**105)
SOURCE_PATHS = (
    Path(__file__).resolve(),
    ROOT / "backend/normal_cdf_bounds.py",
    ROOT / "backend/response_calibration.py",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def exact_json(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    return value


def source_hashes():
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_PATHS
    }


def git_metadata():
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()

    try:
        return {
            "revision": git("rev-parse", "HEAD"),
            "dirty_files": git("status", "--porcelain", "--untracked-files=all").splitlines(),
        }
    except (OSError, subprocess.SubprocessError):
        return {"revision": None, "dirty_files": None, "reason": "Git metadata unavailable"}


def floor(value):
    return value.numerator // value.denominator


def ceil(value):
    return -((-value.numerator) // value.denominator)


def grid_cover(low, high, places=REFERENCE_PLACES):
    scale = 10**places
    return F(floor(low * scale), scale), F(ceil(high * scale), scale)


def atan_cover(q):
    total = F(0)
    for n in range(MAX_REFERENCE_TERMS):
        total += (-1) ** n * q ** (2 * n + 1) / (2 * n + 1)
        omitted = q ** (2 * n + 3) / (2 * n + 3)
        if omitted <= PI_TOLERANCE:
            return (
                (total - omitted, total, n + 1) if (n + 1) % 2 else (total, total + omitted, n + 1)
            )
    raise ValueError("independent arctangent term cap exhausted")


def reciprocal_sqrt_cover(value):
    low, high = F(0), F(1)
    for _ in range(360):
        middle = (low + high) / 2
        if value * middle * middle <= 1:
            low = middle
        else:
            high = middle
    return low, high


@lru_cache(maxsize=1)
def reference_constants():
    a_low, a_high, a_terms = atan_cover(F(1, 2))
    b_low, b_high, b_terms = atan_cover(F(1, 3))
    # This identity and quadrant are independent of production's Machin formula.
    require((F(1, 2) + F(1, 3)) / (1 - F(1, 2) * F(1, 3)) == 1, "pi identity")
    pi_low, pi_high = 4 * (a_low + b_low), 4 * (a_high + b_high)
    c_low = reciprocal_sqrt_cover(2 * pi_high)[0]
    c_high = reciprocal_sqrt_cover(2 * pi_low)[1]
    require(2 * pi_high * c_low**2 <= 1, "independent normalization lower")
    require(2 * pi_low * c_high**2 >= 1, "independent normalization upper")
    return pi_low, pi_high, c_low, c_high, a_terms, b_terms


def exp_positive_cover(v):
    """Positive exp(v) series; every subsequent ratio <= v/(n+2)."""
    term = total = F(1)
    for n in range(MAX_REFERENCE_TERMS):
        omitted = term * v / (n + 1)
        ratio = v / (n + 2)
        if ratio < 1:
            tail = omitted / (1 - ratio)
            if tail <= SERIES_TOLERANCE:
                return total, total + tail, n + 1
        term = omitted
        total += term
    raise ValueError("independent exponential term cap exhausted")


@lru_cache(maxsize=128)
def positive_reference(x):
    require(isinstance(x, F) and 0 <= x <= 6, "reference coordinate outside fixed domain")
    if not x:
        return F(1, 2), F(1, 2), {"positive_terms": 0, "exponential_terms": 0}
    square = x * x
    term = total = x
    for n in range(MAX_REFERENCE_TERMS):
        omitted = term * square / (2 * n + 3)
        ratio = square / (2 * n + 5)
        if ratio < 1:
            tail = omitted / (1 - ratio)
            if tail <= SERIES_TOLERANCE:
                break
        term = omitted
        total += term
    else:
        raise ValueError("independent positive integral series cap exhausted")
    exp_low, exp_high, exp_terms = exp_positive_cover(square / 2)
    _, _, c_low, c_high, _, _ = reference_constants()
    low = F(1, 2) + c_low * total / exp_high
    high = F(1, 2) + c_high * (total + tail) / exp_low
    require(high - low < F(1, 10**90), "independent reference did not reach its declared width")
    grid_low, grid_high = grid_cover(low, high)
    return (
        grid_low,
        grid_high,
        {
            "positive_terms": n + 1,
            "exponential_terms": exp_terms,
            "maximum_retained_fraction_bits": max(
                max(abs(v.numerator).bit_length(), v.denominator.bit_length())
                for v in (term, total, tail, exp_low, exp_high, low, high)
            ),
            "reported_reference_grid_places": REFERENCE_PLACES,
        },
    )


def reference_cdf(z):
    low, high, details = positive_reference(abs(z))
    return (1 - high, 1 - low, details) if z < 0 else (low, high, details)


def reference_cdf_bounds(z):
    """Independent rigorous rational CDF cover; never import/call production.

    This oracle helper accepts bounded exact Fractions/integers/rational strings.
    It is not the production input parser or a physical input certificate.
    """
    if isinstance(z, (bool, float)) or not isinstance(z, (F, int, str)):
        raise TypeError("independent reference requires an exact coordinate")
    if isinstance(z, str) and len(z) > 4096:
        raise ValueError("independent reference input exceeds its string cap")
    z = F(z)
    if max(abs(z.numerator).bit_length(), z.denominator.bit_length()) > 512 or abs(z) > 6:
        raise ValueError("independent reference requires <=512-bit z in [-6,6]")
    low, high, _ = reference_cdf(z)
    return low, high


def _saved_fraction(value):
    require(type(value) is str and 0 < len(value) <= 4096, "saved exact rational string")
    result = F(value)
    require(str(result) == value, "saved rational must use canonical Fraction spelling")
    require(
        max(abs(result.numerator).bit_length(), result.denominator.bit_length()) <= 8192,
        "saved rational exceeds oracle arithmetic cap",
    )
    return result


def audit_record(record):
    """Validate a saved NormalCDFBounds.to_dict() without production execution.

    Checks exact field/type contracts, every certificate inequality, the rounding
    and reflection recipe, and a separate positive-series Gaussian enclosure.
    Raises on failure; callers must retain the failed record in their own census.
    """
    required = {"z", "output", "places", "terms", "reflected", "certificate", "scope"}
    require(isinstance(record, dict) and set(record) == required, "saved CDF record fields")
    require(
        record["scope"]
        == "Mathematical standard-normal CDF at the exact supplied z; no physical camera-model claim.",
        "saved CDF scope differs from this mathematical contract",
    )
    z = _saved_fraction(record["z"])
    require(
        abs(z) <= 6 and max(abs(z.numerator).bit_length(), z.denominator.bit_length()) <= 512,
        "saved coordinate outside declared domain",
    )
    output = record["output"]
    require(isinstance(output, list) and len(output) == 2, "saved CDF output interval")
    low, high = (_saved_fraction(value) for value in output)
    for key in ("places", "terms"):
        require(type(record[key]) is int, f"saved {key} must be an integer")
    require(type(record["reflected"]) is bool, "saved reflection flag must be boolean")
    raw_certificate = record["certificate"]
    if raw_certificate is None:
        certificate = None
    else:
        integer_fields = {"internal_places", "omitted_sign"}
        rational_fields = {
            "partial_sum_lower",
            "partial_sum_upper",
            "first_omitted_term_lower",
            "first_omitted_term_upper",
            "tail_ratio_upper",
            "integral_lower",
            "integral_upper",
            "normalization_lower",
            "normalization_upper",
        }
        require(
            isinstance(raw_certificate, dict)
            and set(raw_certificate) == integer_fields | rational_fields,
            "saved certificate fields",
        )
        require(
            all(type(raw_certificate[key]) is int for key in integer_fields),
            "saved certificate integer fields",
        )
        certificate = SimpleNamespace(
            **{key: raw_certificate[key] for key in integer_fields},
            **{key: _saved_fraction(raw_certificate[key]) for key in rational_fields},
        )
    result = SimpleNamespace(
        z=z,
        lower=low,
        upper=high,
        places=record["places"],
        terms=record["terms"],
        reflected=record["reflected"],
        certificate=certificate,
    )
    return replay_certificate(result)


def replay_certificate(result):
    z, low, high = result.z, result.lower, result.upper
    require(0 <= low <= high <= 1, "probability range/order")
    require(1 <= result.places <= 30, "reported places")
    scale = 10**result.places
    require((low * scale).denominator == (high * scale).denominator == 1, "output grid")
    require(high - low <= F(2, scale), "promised output width")
    if not z:
        require(low == high == F(1, 2), "exact zero")
        require(
            result.terms == 0 and not result.reflected and result.certificate is None,
            "zero metadata",
        )
        return {"replayed_terms": 0, "reference": [F(1, 2), F(1, 2)]}
    require(result.reflected == (z < 0), "reflection flag")
    require(1 <= result.terms <= 256, "reported term count")
    certificate = result.certificate
    require(certificate is not None and certificate.internal_places == 60, "internal grid")
    internal_scale = 10**certificate.internal_places
    partial = F(0)
    term = abs(z)
    for n in range(result.terms):
        partial += (-1) ** n * term
        term *= z * z * (2 * n + 1) / (2 * (n + 1) * (2 * n + 3))
    require(
        certificate.partial_sum_lower <= partial <= certificate.partial_sum_upper,
        "certificate misses exact alternating partial sum",
    )
    require(
        0 <= certificate.first_omitted_term_lower <= term <= certificate.first_omitted_term_upper,
        "certificate misses exact first omitted term",
    )
    for value in (
        certificate.partial_sum_lower,
        certificate.partial_sum_upper,
        certificate.first_omitted_term_lower,
        certificate.first_omitted_term_upper,
    ):
        require((value * internal_scale).denominator == 1, "certificate fixed-grid endpoint")
    sign = (-1) ** result.terms
    require(certificate.omitted_sign == sign, "omitted sign")
    ratio = z * z / (2 * (result.terms + 1))
    require(certificate.tail_ratio_upper == ratio < 1, "monotone-tail bound")
    # r_k <= x²/[2*(k+1)] <= this ratio for all k>=first omitted index.
    expected_integral = (
        certificate.partial_sum_lower - (certificate.first_omitted_term_upper if sign < 0 else 0),
        certificate.partial_sum_upper + (certificate.first_omitted_term_upper if sign > 0 else 0),
    )
    require(
        (certificate.integral_lower, certificate.integral_upper) == expected_integral,
        "integral cover construction",
    )
    _, _, independent_c_low, independent_c_high, _, _ = reference_constants()
    require(
        0
        < certificate.normalization_lower
        <= independent_c_low
        <= independent_c_high
        <= certificate.normalization_upper,
        "normalization misses independent exact cover",
    )
    products = [
        integral * normalizer
        for integral in expected_integral
        for normalizer in (certificate.normalization_lower, certificate.normalization_upper)
    ]
    raw_low, raw_high = F(1, 2) + min(products), F(1, 2) + max(products)
    require(raw_high - raw_low <= F(1, 4 * scale), "internal stopping width")
    expected_low = max(F(0), F(floor(raw_low * scale), scale))
    expected_high = min(F(1), F(ceil(raw_high * scale), scale))
    if z < 0:
        expected_low, expected_high = 1 - expected_high, 1 - expected_low
    require((low, high) == (expected_low, expected_high), "outward rounding/reflection replay")
    reference_low, reference_high, details = reference_cdf(z)
    require(low <= reference_low <= reference_high <= high, "independent CDF cover not contained")
    return {"replayed_terms": result.terms, "reference": [reference_low, reference_high], **details}


def fixtures():
    named = [
        ("zero", F(0)),
        ("unit", F(1)),
        ("negative_unit", F(-1)),
        ("positive_limit", F(6)),
        ("negative_limit", F(-6)),
        ("third", F(1, 3)),
        ("negative_third", F(-1, 3)),
        ("seventeen_quarters", F(17, 4)),
        ("seven_halves", F(7, 2)),
        ("tiny_positive", F(1, 10**40)),
        ("tiny_negative", F(-1, 10**40)),
        ("near_positive_limit", F(6) - F(1, 10**40)),
        ("near_negative_limit", -F(6) + F(1, 10**40)),
        ("tiny_512bit_fraction", F(1, 2**511)),
    ]
    population = [(name, z, 30, "named") for name, z in named]
    population += [
        (f"grid_{places}_{z}", z, places, "grid")
        for places in (1, 6, 15, 30)
        for z in (F(-23, 4), F(3, 4), F(11, 2))
    ]
    rng = random.Random(SEED)
    for index in range(SEEDED_CASES):
        denominator = rng.choice((7, 64, 97, 100, 128))
        z = F(rng.randint(-6 * denominator, 6 * denominator), denominator)
        population.append((f"seeded_{index:02d}", z, 30, "seeded"))
    return population


def run():
    initial, start = source_hashes(), time.monotonic()
    from backend import normal_cdf_bounds as production

    records = []

    def check(name, category, function, *, inputs=None):
        record = {"case": name, "category": category, "inputs": exact_json(inputs or {})}
        try:
            record["details"] = exact_json(function())
            record["verification"] = "passed"
        except (
            AssertionError,
            ValueError,
            TypeError,
            ArithmeticError,
            AttributeError,
            KeyError,
            IndexError,
            RuntimeError,
        ) as exc:
            record["verification"] = "failed"
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        records.append(record)

    check(
        "stable_source_after_import",
        "provenance",
        lambda: require(initial == source_hashes(), "source changed during import"),
    )
    for name, z, places, category in fixtures():

        def compare(z=z, places=places):
            result = production.normal_cdf_bounds(z, places=places)
            details = audit_record(result.to_dict())
            return {"production": result.to_dict(), "oracle": details}

        check(name, category, compare, inputs={"z": z, "places": places})

    def normalization():
        pi_low, pi_high, c_low, c_high = production.normalization_bounds()
        ref_pi_low, ref_pi_high, ref_c_low, ref_c_high, a_terms, b_terms = reference_constants()
        require(pi_low <= ref_pi_low <= ref_pi_high <= pi_high, "pi misses independent identity")
        require(c_low <= ref_c_low <= ref_c_high <= c_high, "normalization cover")
        require(2 * pi_high * c_low**2 <= 1, "production reciprocal lower inequality")
        require(2 * pi_low * c_high**2 >= 1, "production reciprocal upper inequality")
        return {
            "production_pi": [pi_low, pi_high],
            "independent_pi": [ref_pi_low, ref_pi_high],
            "production_normalization": [c_low, c_high],
            "independent_normalization": [ref_c_low, ref_c_high],
            "independent_arctangent_terms": [a_terms, b_terms],
            "bisection_steps_each": 360,
        }

    check("normalization_and_different_pi_identity", "constant", normalization)
    for z in (F(1, 10**40), F(1, 3), F(1), F(7, 2), F(6)):

        def reflection(z=z):
            positive = production.normal_cdf_bounds(z)
            negative = production.normal_cdf_bounds(-z)
            require(
                (negative.lower, negative.upper) == (1 - positive.upper, 1 - positive.lower),
                "exact reflection",
            )
            require(positive.certificate == negative.certificate, "reflected integral certificate")
            return {"positive": positive.to_dict(), "negative": negative.to_dict()}

        check(f"reflection_{z}", "reflection", reflection, inputs={"abs_z": z})

    def hostile_context():
        expected = production.normal_cdf_bounds(F(5, 3)).to_dict()
        with localcontext(Context(prec=2, Emin=-2, Emax=2, clamp=1)):
            actual = production.normal_cdf_bounds(F(5, 3)).to_dict()
            reference_cdf(F(5, 3))
        require(actual == expected, "ambient decimal context changed production")
        return {
            "production_unchanged": True,
            "reference_uses_only_integer_fraction_arithmetic": True,
        }

    check("hostile_decimal_context", "context", hostile_context)
    refusal_inputs = [
        ("float", 1.0, {}),
        ("boolean", True, {}),
        ("nan_float", float("nan"), {}),
        ("nan_string", "NaN", {}),
        ("infinite_string", "Infinity", {}),
        ("excess_exponent", "1e999", {}),
        ("excess_digits", "1" * 41, {}),
        ("excess_fraction_bits", F(1, 2**513), {}),
        ("above_limit", "6.0000000000001", {}),
        ("below_limit", "-6.0000000000001", {}),
        ("places_zero", 1, {"places": 0}),
        ("places_excess", 1, {"places": 31}),
        ("places_boolean", 1, {"places": True}),
        ("places_float", 1, {"places": 1.0}),
        ("terms_zero", 1, {"max_terms": 0}),
        ("terms_excess", 1, {"max_terms": 257}),
        ("terms_boolean", 1, {"max_terms": True}),
        ("terms_float", 1, {"max_terms": 1.0}),
        ("insufficient_term_budget", 6, {"max_terms": 1}),
    ]
    for name, z, options in refusal_inputs:

        def refuse(z=z, options=options):
            try:
                production.normal_cdf_bounds(z, **options)
            except (ValueError, TypeError) as exc:
                return {"refused_type": type(exc).__name__, "message": str(exc)}
            raise AssertionError("invalid/resource request returned a mathematical interval")

        check(
            name,
            "refusal",
            refuse,
            inputs={"z_type": type(z).__name__, "z_literal": str(z), "options": options},
        )

    mutations = {
        "partial_lower": lambda c: {"partial_sum_lower": c.partial_sum_upper + 1},
        "omitted_upper": lambda c: {"first_omitted_term_upper": F(0)},
        "omitted_sign": lambda c: {"omitted_sign": -c.omitted_sign},
        "tail_ratio": lambda c: {"tail_ratio_upper": F(1)},
        "integral": lambda c: {"integral_lower": c.integral_lower + 1},
        "normalization": lambda c: {"normalization_lower": F(1)},
        "internal_places": lambda c: {"internal_places": 59},
    }
    for name, mutation in mutations.items():

        def rejects(mutation=mutation):
            valid = production.normal_cdf_bounds(F(1))
            changes = mutation(valid.certificate)
            bad = replace(valid, certificate=replace(valid.certificate, **changes))
            try:
                replay_certificate(bad)
            except AssertionError as exc:
                return {"rejected_mutation": exact_json(changes), "message": str(exc)}
            raise AssertionError("tampered certificate escaped independent replay")

        check(f"reject_tampered_{name}", "auditor_control", rejects)

    metadata_mutations = {
        "noncanonical_coordinate": {"z": "1.0"},
        "coordinate_outside_domain": {"z": "7"},
        "noninteger_places": {"places": 30.0},
        "boolean_term_count": {"terms": True},
        "nonboolean_reflection": {"reflected": 0},
        "missing_certificate": {"certificate": None},
        "malformed_output": {"output": ["0"]},
        "unsupported_scope": {"scope": "physical accuracy guaranteed"},
    }
    for name, changes in metadata_mutations.items():

        def rejects_saved(changes=changes):
            valid = production.normal_cdf_bounds(F(1))
            bad = {**valid.to_dict(), **changes}
            try:
                audit_record(bad)
            except (AssertionError, ValueError, TypeError) as exc:
                return {"rejected_metadata": changes, "message": str(exc)}
            raise AssertionError("tampered saved record escaped independent audit")

        check(f"reject_saved_{name}", "auditor_control", rejects_saved)

    final = source_hashes()
    check(
        "stable_source_after_run",
        "provenance",
        lambda: require(initial == final, "source changed during run"),
    )
    return {
        "format": "pictures-to-cad-normal-cdf-bounds-oracle",
        "version": 1,
        "scope": "Fixed mathematical development controls at exact declared z; not camera calibration, physical input uncertainty or unseen evaluation.",
        "population": {"seed": SEED, "seeded_cases": SEEDED_CASES, "cdf_cases": len(fixtures())},
        "reference_method": {
            "integral": "exp(-x²/2) times positive sum x^(2n+1)/(2n+1)!!; first omitted term geometric tail",
            "exponential": "positive exp(x²/2) series with geometric upper tail, then reciprocal bounds",
            "pi": "4*(atan(1/2)+atan(1/3)); exact alternating remainders and quadrant identity",
            "normalization": "two exact rational bisections, 360 steps each",
            "maximum_terms_per_reference_series": MAX_REFERENCE_TERMS,
            "series_absolute_tail_tolerance": str(SERIES_TOLERANCE),
            "reported_reference_grid_places": REFERENCE_PLACES,
        },
        "summary": {
            "checks": len(records),
            "passed": sum(r["verification"] == "passed" for r in records),
            "failed": sum(r["verification"] == "failed" for r in records),
        },
        "cases": records,
        "resource_scope": [
            "Production accepts bounded exact inputs (512-bit rational cap), |z|<=6, at most256 terms, fixed60-place internal grid and requested1..30 output places.",
            "A loose integer recurrence bound is term_high_n <= 6*10^60*19^n for n<=256; finite rational denominators come from the bounded exact coordinate and explicit small integer factors.",
            "Neither production's fixed limits nor this fixed oracle population establish whole-photo runtime or physical accuracy.",
        ],
        "source_sha256_before": initial,
        "source_sha256_after": final,
        "git": git_metadata(),
        "runtime": {"python": platform.python_version(), "seconds": time.monotonic() - start},
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path, help="new JSON destination; replacement refused"
    )
    options = parser.parse_args(arguments)
    try:
        if options.output.exists() or options.output.is_symlink():
            raise ValueError("output already exists; preserve it and choose a fresh destination")
        result = run()
        payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
        options.output.parent.mkdir(parents=True, exist_ok=True)
        with options.output.open("x", encoding="utf-8") as handle:
            handle.write(payload)
        print(
            json.dumps(
                {
                    "output": str(options.output),
                    **result["summary"],
                    "seconds": result["runtime"]["seconds"],
                }
            )
        )
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    return 0 if result["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
