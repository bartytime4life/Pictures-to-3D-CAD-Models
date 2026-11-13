#!/usr/bin/env python3
"""Exact algebra controls for a separately qualified acquisition-operator study.

Import performs no control evaluation. run_controls() uses only Fraction
arithmetic and returns JSON-ready records; it imports no rendering, fitting,
NumPy, production Keys or Gaussian-probability implementation.
"""

from __future__ import annotations

import argparse
import json
import os
from fractions import Fraction
from pathlib import Path

PHASES = ("0", "1/5", "1/4", "2/5", "1/2", "3/5", "3/4", "4/5")
NODES = (-1, 0, 1, 2)


def rational(value):
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError("exact controls require an integer or Fraction")
    return Fraction(value)


def encoded(value):
    return str(rational(value))


def keys_weight(displacement):
    """Keys a=-1/2 at an exact displacement; signed and unclamped."""
    x = abs(rational(displacement))
    if x <= 1:
        return (Fraction(3, 2) * x - Fraction(5, 2)) * x * x + 1
    if x < 2:
        return ((-x / 2 + Fraction(5, 2)) * x - 4) * x + 2
    return Fraction(0)


def weights_at_phase(phase):
    phase = rational(phase)
    if not 0 <= phase <= 1:
        raise ValueError("phase must lie in the closed unit interval")
    return tuple(keys_weight(phase - index) for index in NODES)


def _check(name, actual, expected):
    return {
        "name": name,
        "actual": encoded(actual),
        "expected": encoded(expected),
        "passed": actual == expected,
    }


def _bound(name, actual, upper):
    return {
        "name": name,
        "actual": encoded(actual),
        "upper": encoded(upper),
        "passed": actual <= upper,
    }


def _trim(poly):
    result = list(poly)
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result)


def _add(left, right):
    length = max(len(left), len(right))
    return _trim(
        tuple(
            (left[i] if i < len(left) else Fraction(0))
            + (right[i] if i < len(right) else Fraction(0))
            for i in range(length)
        )
    )


def _scale(poly, factor):
    return _trim(tuple(value * factor for value in poly))


def _multiply(left, right):
    result = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] += a * b
    return _trim(tuple(result))


def _power(poly, exponent):
    result = (Fraction(1),)
    for _ in range(exponent):
        result = _multiply(result, poly)
    return result


def polynomial_identities():
    """Compare complete rational coefficient lists, not sampled phase values."""
    zero, one = Fraction(0), Fraction(1)
    phase, complement = (zero, one), (one, -one)
    # Ascending powers of phase, derived independently from the two Keys pieces.
    weights = {
        -1: (zero, -one / 2, one, -one / 2),
        0: (one, zero, -5 * one / 2, 3 * one / 2),
        1: (zero, one / 2, 2 * one, -3 * one / 2),
        2: (zero, zero, -one / 2, one / 2),
    }
    moments = []
    for degree in range(5):
        total = (zero,)
        for index, weight in weights.items():
            total = _add(total, _multiply(weight, _power((Fraction(index), -one), degree)))
        moments.append(total)
    expected = (
        (one,),
        (zero,),
        (zero,),
        _multiply(_multiply(phase, complement), (one, -2 * one)),
        _scale(_multiply(_power(phase, 2), _power(complement, 2)), -9),
    )
    signed_absolute = _add(_add(weights[0], weights[1]), _scale(_add(weights[-1], weights[2]), -1))
    gap = _add((Fraction(5, 4),), _scale(signed_absolute, -1))
    square = _power((-one / 2, one), 2)
    negative_factors = {
        -1: _scale(_multiply(phase, _power(complement, 2)), -one / 2),
        2: _scale(_multiply(_power(phase, 2), complement), -one / 2),
    }
    positive_factors = {
        0: _multiply(
            complement,
            _add(
                _add(_power(complement, 2), _scale(_multiply(phase, complement), 3)),
                _scale(_power(phase, 2), one / 2),
            ),
        ),
        1: _multiply(
            phase,
            _add(
                _add(
                    _scale(_power(complement, 2), one / 2), _scale(_multiply(phase, complement), 3)
                ),
                _power(phase, 2),
            ),
        ),
    }
    checks = [
        {
            "name": f"centred_moment_{degree}_polynomial",
            "actual_coefficients": [encoded(x) for x in actual],
            "expected_coefficients": [encoded(x) for x in target],
            "passed": actual == target,
        }
        for degree, (actual, target) in enumerate(zip(moments, expected, strict=True))
    ]
    checks.extend(
        {
            "name": f"negative_node_{index}_factorization",
            "actual_coefficients": [encoded(x) for x in weights[index]],
            "expected_coefficients": [encoded(x) for x in factor],
            "passed": weights[index] == factor,
        }
        for index, factor in negative_factors.items()
    )
    checks.extend(
        {
            "name": f"nonnegative_node_{index}_factorization",
            "actual_coefficients": [encoded(x) for x in weights[index]],
            "expected_coefficients": [encoded(x) for x in factor],
            "passed": weights[index] == factor,
        }
        for index, factor in positive_factors.items()
    )
    checks.extend(
        {
            "name": name,
            "actual_coefficients": [encoded(x) for x in actual],
            "expected_coefficients": [encoded(x) for x in target],
            "passed": actual == target,
        }
        for name, actual, target in (
            ("absolute_row_formula", signed_absolute, _add((one,), _multiply(phase, complement))),
            (
                "absolute_row_lower_gap_is_nonnegative_product",
                _add(signed_absolute, (-one,)),
                _multiply(phase, complement),
            ),
        )
    )
    checks.append(
        {
            "name": "absolute_row_bound_gap_is_nonnegative_square",
            "actual_coefficients": [encoded(x) for x in gap],
            "expected_coefficients": [encoded(x) for x in square],
            "passed": gap == square,
            "scope": "Uses weight signs on phase in [0,1]; 5/4-L1=(phase-1/2)^2.",
        }
    )
    return {
        "all_phase_domain": "0 <= f <= 1",
        "sign_argument": {
            "nonnegative_factors": ["f", "1-f"],
            "outer_weights": {"-1": "-f*(1-f)^2/2", "2": "-f^2*(1-f)/2"},
            "inner_weights": {
                "0": "(1-f)*((1-f)^2+3*f*(1-f)+f^2/2)",
                "1": "f*((1-f)^2/2+3*f*(1-f)+f^2)",
            },
            "conclusion": "Outer weights are nonpositive and inner weights nonnegative throughout the stated domain.",
        },
        "all_phase_bound_argument": {
            "row": "L1=1+f*(1-f); L1-1=f*(1-f)>=0; 5/4-L1=(f-1/2)^2>=0.",
            "tensor": "Sum absolute tensor weights factors into the two row L1 values, each in [1,5/4], so the two-dimensional gain is at most 25/16.",
        },
        "weights_polynomial_ascending": {
            str(index): [encoded(x) for x in weight] for index, weight in weights.items()
        },
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }


def phase_control(phase):
    phase = rational(phase)
    weights = weights_at_phase(phase)
    moments = tuple(
        sum(
            (
                weight * (index - phase) ** degree
                for index, weight in zip(NODES, weights, strict=True)
            ),
            Fraction(0),
        )
        for degree in range(5)
    )
    absolute = sum(map(abs, weights), Fraction(0))
    negative = sum((weight for weight in weights if weight < 0), Fraction(0))
    checks = [
        _check("constant_reproduction", moments[0], Fraction(1)),
        _check("centred_first_moment", moments[1], Fraction(0)),
        _check("centred_second_moment", moments[2], Fraction(0)),
        _check("centred_third_moment", moments[3], phase * (1 - phase) * (1 - 2 * phase)),
        _check("centred_fourth_moment", moments[4], -9 * phase**2 * (1 - phase) ** 2),
        _check("absolute_row_identity", absolute, 1 + phase * (1 - phase)),
        _bound("absolute_row_bound", absolute, Fraction(5, 4)),
        _check("negative_weight_sum", negative, -phase * (1 - phase) / 2),
    ]
    for degree in (1, 2):
        raw = sum(
            (weight * index**degree for index, weight in zip(NODES, weights, strict=True)),
            Fraction(0),
        )
        checks.append(_check(f"degree_{degree}_monomial_reproduction", raw, phase**degree))
    ramp = (Fraction(7, 3), Fraction(11, 7))
    quadratic = (Fraction(-2, 5), Fraction(13, 11), Fraction(17, 19))
    for name, coefficients in (("linear_ramp", ramp), ("quadratic", quadratic)):
        samples = tuple(
            sum(
                (coefficient * index**degree for degree, coefficient in enumerate(coefficients)),
                Fraction(0),
            )
            for index in NODES
        )
        interpolated = sum(
            (weight * sample for weight, sample in zip(weights, samples, strict=True)), Fraction(0)
        )
        target = sum(
            (coefficient * phase**degree for degree, coefficient in enumerate(coefficients)),
            Fraction(0),
        )
        checks.append(_check(name, interpolated, target))
    return {
        "phase": encoded(phase),
        "nodes": list(NODES),
        "weights": [encoded(weight) for weight in weights],
        "centred_moments_0_through_4": [encoded(value) for value in moments],
        "absolute_row_sum": encoded(absolute),
        "negative_sum": encoded(negative),
        "negative_indices": [
            index for index, weight in zip(NODES, weights, strict=True) if weight < 0
        ],
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }


def tensor_control(xphase, yphase):
    xphase, yphase = rational(xphase), rational(yphase)
    xweights, yweights = weights_at_phase(xphase), weights_at_phase(yphase)
    entries = [
        (x, y, wx * wy)
        for x, wx in zip(NODES, xweights, strict=True)
        for y, wy in zip(NODES, yweights, strict=True)
    ]
    absolute = sum((abs(value) for _, _, value in entries), Fraction(0))
    product = sum(map(abs, xweights), Fraction(0)) * sum(map(abs, yweights), Fraction(0))
    checks = [
        _check(
            "constant_reproduction",
            sum((value for _, _, value in entries), Fraction(0)),
            Fraction(1),
        ),
        _check("absolute_tensor_factorization", absolute, product),
        _bound("absolute_tensor_bound", absolute, Fraction(25, 16)),
    ]
    for dx, dy in ((1, 0), (0, 1), (2, 0), (0, 2), (1, 1)):
        value = sum((weight * x**dx * y**dy for x, y, weight in entries), Fraction(0))
        checks.append(_check(f"monomial_{dx}_{dy}", value, xphase**dx * yphase**dy))
    return {
        "xphase": encoded(xphase),
        "yphase": encoded(yphase),
        "weights": [{"index": [x, y], "weight": encoded(value)} for x, y, value in entries],
        "negative_indices": [[x, y] for x, y, value in entries if value < 0],
        "absolute_row_sum": encoded(absolute),
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }


def halfplane_coverage(index, edge):
    """Fraction of [index,index+1] on the material side x<=edge."""
    index, edge = rational(index), rational(edge)
    return max(Fraction(0), min(Fraction(1), edge - index))


def halfplane_control(phase, edge):
    phase, edge = rational(phase), rational(edge)
    weights = weights_at_phase(phase)
    # This rational binomial kernel is an algebra toy, NOT a Gaussian kernel.
    blur = ((-1, Fraction(1, 4)), (0, Fraction(1, 2)), (1, Fraction(1, 4)))
    folded = {}
    direct, complement = Fraction(0), Fraction(0)
    for index, weight in zip(NODES, weights, strict=True):
        blurred = sum(
            (mass * halfplane_coverage(index - offset, edge) for offset, mass in blur), Fraction(0)
        )
        direct += weight * blurred
        complement += weight * (1 - blurred)
        for offset, mass in blur:
            source_index = index - offset
            folded[source_index] = folded.get(source_index, Fraction(0)) + weight * mass
    coverage = {index: halfplane_coverage(index, edge) for index in sorted(folded)}
    composed = sum((folded[index] * value for index, value in coverage.items()), Fraction(0))
    unblurred = sum(
        (
            weight * halfplane_coverage(index, edge)
            for index, weight in zip(NODES, weights, strict=True)
        ),
        Fraction(0),
    )
    checks = [
        _check("stagewise_equals_composed", direct, composed),
        _check("complement_sum_no_clamping", direct + complement, Fraction(1)),
        _check("composed_DC_gain", sum(folded.values(), Fraction(0)), Fraction(1)),
        _bound(
            "positive_blur_does_not_expand_row_L1",
            sum(map(abs, folded.values()), Fraction(0)),
            sum(map(abs, weights), Fraction(0)),
        ),
    ]
    if edge == 0 and 0 < phase < 1:
        checks.append(
            {
                "name": "unblurred_Keys_undershoot_retained",
                "actual": encoded(unblurred),
                "passed": unblurred < 0,
            }
        )
        checks.append(
            {
                "name": "unblurred_complement_overshoot_retained",
                "actual": encoded(1 - unblurred),
                "passed": 1 - unblurred > 1,
            }
        )
    return {
        "phase": encoded(phase),
        "edge": encoded(edge),
        "pixel_convention": "index j labels cell [j,j+1], centre j+1/2; Keys query index phase has geometric centre phase+1/2",
        "blur_kernel": [{"offset": index, "weight": encoded(value)} for index, value in blur],
        "coverage": [
            {"index": index, "value": encoded(value)} for index, value in coverage.items()
        ],
        "composed_weights": [
            {"index": index, "weight": encoded(value)} for index, value in sorted(folded.items())
        ],
        "stagewise_response": encoded(direct),
        "composed_response": encoded(composed),
        "complement_response": encoded(complement),
        "unblurred_Keys_response": encoded(unblurred),
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }


def _retained(name, function):
    try:
        return function()
    except Exception as error:  # noqa: BLE001 -- preserve every planned control identity
        return {
            "id": name,
            "passed": False,
            "error": {"type": type(error).__name__, "message": str(error)},
        }


def run_controls():
    """Run only exact algebra controls, with no production/model dependencies."""
    phases = tuple(Fraction(value) for value in PHASES)
    phase_rows = [
        _retained(f"phase/{value}", lambda value=value: phase_control(value)) for value in phases
    ]
    tensor_rows = [
        _retained(f"tensor/{x}/{y}", lambda x=x, y=y: tensor_control(x, y))
        for x in phases
        for y in phases
    ]
    edges = (Fraction(-3, 2), Fraction(0), Fraction(1, 3), Fraction(1), Fraction(5, 2))
    halfplanes = [
        _retained(
            f"halfplane/{phase}/{edge}",
            lambda phase=phase, edge=edge: halfplane_control(phase, edge),
        )
        for phase in phases
        for edge in edges
    ]
    polynomial = _retained("polynomial_identities", polynomial_identities)
    result = {
        "format": "pictures-to-cad-finite-acquisition-exact-controls",
        "version": 1,
        "scope": "Exact Keys algebra and a rational half-plane composition toy. No Gaussian/source renderer, full-D mean, fitting, physical PSF, camera accuracy or error-enclosure qualification.",
        "arithmetic": "stdlib Fraction; all reported exact numbers are rational strings",
        "phase_selection": {
            "all": list(PHASES),
            "quarter_controls": ["0", "1/4", "1/2", "3/4"],
            "known_output_scale_1": ["1/2"],
            "known_output_scale_5_over_4": ["0", "1/5", "2/5", "3/5", "4/5"],
        },
        "polynomial_identities": polynomial,
        "phase_rows": phase_rows,
        "tensor_rows": tensor_rows,
        "halfplane_rows": halfplanes,
        "phase_count": len(phase_rows),
        "tensor_count": len(tensor_rows),
        "halfplane_count": len(halfplanes),
        "protocol_passed": polynomial["passed"]
        and all(row["passed"] for row in (*phase_rows, *tensor_rows, *halfplanes)),
    }
    json.dumps(result, allow_nan=False)
    return result


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, metavar="NEW_JSON")
    args = parser.parse_args(arguments)
    output = args.output.absolute()
    if os.path.lexists(output) or not output.parent.is_dir():
        parser.error("output must be a fresh nonsymlink path in an existing directory")
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as error:
        parser.error(str(error))
    result = run_controls()
    with os.fdopen(descriptor, "w") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {"output": str(output), "protocol_passed": result["protocol_passed"]}, sort_keys=True
        )
    )
    return 0 if result["protocol_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
