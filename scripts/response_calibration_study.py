"""Retain finite edge/response ambiguity and externally supplied calibration controls.

Requires --output NEW_JSON. Uses synthetic fields and exact rational constraints;
no camera, server, AI service, native application or physical accuracy is involved.
"""

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from dataclasses import asdict
from fractions import Fraction as F
from pathlib import Path
from statistics import NormalDist

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import profile_observations, raw_source_fit, response_calibration, sheet, tone
from scripts.response_calibration import git_metadata

PLAN = "studies/response-calibration-v1.json"
SOURCES = (
    "backend/response_calibration.py",
    "backend/raw_source_fit.py",
    "backend/profile_observations.py",
    "backend/sheet.py",
    "backend/tone.py",
    "scripts/response_calibration.py",
    "scripts/response_calibration_study.py",
    PLAN,
)


def hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def cdf(value):
    return F.from_float(0.5 * math.erfc(-float(value) / math.sqrt(2)))


def response(value, coefficient):
    return value + coefficient * value * (1 - value)


def node(x, low, high=None):
    return {"input": x, "output": (low, low if high is None else high)}


def json_nodes(nodes):
    return [{"input": str(n["input"]), "output": [str(v) for v in n["output"]]} for n in nodes]


def checked(nodes, slopes=(F(0), None)):
    result = response_calibration.calibrate_response(nodes, slope_bounds=slopes)
    if result.status == "compatible":
        values = {p.input: p.output for p in result.witness}
        assert all(low <= values[n["input"]] <= high for n in nodes for low, high in [n["output"]])
        for left, right in zip(result.witness, result.witness[1:]):
            dx, dy = right.input - left.input, right.output - left.output
            assert slopes[0] * dx <= dy
            assert slopes[1] is None or dy <= slopes[1] * dx
    else:
        assert result.contradiction.implied_lower > result.contradiction.implied_upper
    return result


def compact(result):
    # Every compatible case keeps a common exact witness, every incompatible case
    # keeps its exact indexed proof. Full tight bands are retained for named controls.
    raw = result.to_dict()
    return {key: raw[key] for key in ("status", "witness", "contradiction", "work")}


def named_controls():
    anchors = [node(F(0), F(0)), node(F(1), F(1))]
    baseline = checked(anchors, (F(0), F(2)))
    a, b = node(F(2, 5), F(4, 5)), node(F(3, 5), F(1, 5))
    joint = checked(anchors + [a, b], (F(0), F(2)))
    assert joint.status == "incompatible"
    marginal = {
        "calibration": baseline.to_dict(),
        "queries": [
            {"input": str(x), "output": [str(v.lower), str(v.upper)]}
            for x in (F(2, 5), F(1, 2), F(3, 5))
            for v in [baseline.query(x)]
        ],
        "individual_observations": [checked(anchors + [n], (F(0), F(2))).to_dict() for n in (a, b)],
        "joint_observations": joint.to_dict(),
    }
    left, right = node(F(1, 2), F(1, 4)), node(F(1, 2), F(3, 4))
    spatial = {
        "first_region": checked(anchors + [left], (F(1, 2), F(3, 2))).to_dict(),
        "second_region": checked(anchors + [right], (F(1, 2), F(3, 2))).to_dict(),
        "claimed_common_response": checked(anchors + [left, right], (F(1, 2), F(3, 2))).to_dict(),
    }
    input_error = {
        "declared_uncertain_input": ["0", "2"],
        "fixed_observation": {"input": "1", "output": ["0", "0"]},
        "midpoint_substitution": checked([node(F(1), F(0)), node(F(1), F(1))]).to_dict(),
        "allowed_assignment_input_2": checked([node(F(1), F(0)), node(F(2), F(1))]).to_dict(),
        "scope": "One allowed assignment disproves midpoint rejection; no general uncertain-input solver or universal assignment guarantee.",
    }
    center = response(F(1, 2), F(3, 20))
    integer = round(255 * center)
    bin_low, bin_high = F(2 * integer - 1, 510), F(2 * integer + 1, 510)
    quantization = {
        "kind": "synthetic exact uniform scalar 8-bit quantizer, not phone sRGB processing",
        "true_center": str(center),
        "saved_integer": integer,
        "bin_interval": [str(bin_low), str(bin_high)],
        "bin_interval_interpretation": "Conservative closed cover; ties-to-even can exclude half-step endpoints from the exact quantizer preimage.",
        "incorrect_point_interpretation": checked(
            [node(F(1, 2), center), node(F(1, 2), F(integer, 255))]
        ).to_dict(),
        "correct_bin_interpretation": checked(
            [node(F(1, 2), center), node(F(1, 2), bin_low, bin_high)]
        ).to_dict(),
    }
    image, x, y = np.array([[0.0, 1.0]]), np.array([0.5]), np.array([0.0])
    mean = float(sheet.sample_keys(image, x, y)[0])
    correct = float(sheet.sample_keys(image**2, x, y)[0])
    signed = float(sheet.sample_keys(np.array([[1.0, 0.0, 0.0, 0.0]]), np.array([1.5]), y)[0])
    rgb = np.array([[[0.0, 255.0, 0.0], [127.5, 127.5, 0.0]]])
    encoded = np.clip(np.rint(tone.encoded_from_linear(255 * (rgb / 255) ** 2)), 0, 255).astype(
        np.uint8
    )
    mixed = tone.linear_mix(encoded, (0.5, 0.5, 0.0))[0]
    stage = {
        "actual_Keys_mean": mean,
        "incorrect_square_after_Keys": mean**2,
        "correct_Keys_after_square": correct,
        "signed_Keys_value_outside_source_domain": signed,
        "equal_original_linear_channel_mixes": [127.5, 127.5],
        "per_channel_square_encoded8_decoded_mixes": mixed.tolist(),
        "encoded8_RGB": encoded.tolist(),
    }
    assert mean == 0.5 and correct == 0.5 and signed == -0.0625
    assert mixed[0] - mixed[1] > 60
    return {
        "marginal_vs_common": marginal,
        "spatial_response": spatial,
        "uncertain_inputs": input_error,
        "quantization": quantization,
        "source_stage": stage,
    }


def run():
    initial, start = hashes(), time.monotonic()
    plan = json.loads((ROOT / PLAN).read_text())
    positions = [response_calibration.parse_exact(x) for x in plan["profile_positions_sigma"]]
    spec = plan["offset_grid"]
    if not (
        len(positions) == 25
        and spec == {"integer_start": -32, "integer_stop": 32, "denominator": 64}
    ):
        raise ValueError("version-1 study requires its declared 25-point, 65-offset population")
    coefficient = response_calibration.parse_exact(plan["response_quadratic_coefficient"])
    if coefficient != F(3, 20) or plan["true_offset_sigma"] != "0" or plan["true_sigma"] != "1":
        raise ValueError("version-1 source conditions changed; use a new study version")
    offsets = [
        F(i, spec["denominator"]) for i in range(spec["integer_start"], spec["integer_stop"] + 1)
    ]
    inputs = [[cdf(x - offset) for x in positions] for offset in offsets]
    truth = [response(cdf(x), coefficient) for x in positions]
    if len(plan["calibration_regimes"]) != 6 or len(plan["observation_halfwidths"]) != 3:
        raise ValueError(
            "version-1 study requires six calibration regimes and three observation bands"
        )
    results = []
    for regime in plan["calibration_regimes"]:
        patch_error = F(regime["patch_halfwidth"])
        patch_inputs = [F(x) for x in plan["calibration_inputs"]]
        if regime["patches"] == "endpoints":
            patch_inputs = [F(0), F(1)]
        patches = []
        for x in patch_inputs:
            value = response(x, coefficient) if regime["response"] == "quadratic" else x
            err = F(0) if x in (0, 1) else patch_error
            patches.append(node(x, value - err, value + err))
        slopes = (
            F(regime["slope_bounds"][0]),
            None if regime["slope_bounds"][1] is None else F(regime["slope_bounds"][1]),
        )
        for error_string in plan["observation_halfwidths"]:
            error = F(error_string)
            rows, compatible = [], []
            for index, (offset, xs) in enumerate(zip(offsets, inputs)):
                observations = [
                    node(x, value - error, value + error) for x, value in zip(xs, truth)
                ]
                result = checked(patches + observations, slopes)
                rows.append(
                    {"candidate_index": index, "offset_sigma": str(offset), **compact(result)}
                )
                if result.status == "compatible":
                    compatible.append(str(offset))
            if regime["response"] == "quadratic":
                assert "0" in compatible
            if regime["name"] == "normalization_only":
                assert len(compatible) == len(offsets)
            results.append(
                {
                    "regime": regime["name"],
                    "observation_halfwidth": error_string,
                    "patches": json_nodes(patches),
                    "slope_bounds": regime["slope_bounds"],
                    "compatible_count": len(compatible),
                    "represented_compatible_offsets_sigma": compatible,
                    "all_candidate_results": rows,
                }
            )
    gauges = []
    normal = NormalDist()
    for offset in (F(-1, 2), F(0), F(1, 2)):
        for sigma in (F(3, 4), F(1), F(5, 4)):
            candidate = [cdf((x - offset) / sigma) for x in positions]
            result = checked(
                [node(F(0), F(0)), node(F(1), F(1))]
                + [node(x, value) for x, value in zip(candidate, truth)]
            )
            assert result.status == "compatible"
            transformed = [
                float(
                    response(
                        cdf(float(sigma) * normal.inv_cdf(float(u)) + float(offset)), coefficient
                    )
                )
                for u in candidate
            ]
            delta = max(abs(a - float(b)) for a, b in zip(transformed, truth))
            assert delta < 1e-10
            gauges.append(
                {
                    "offset_sigma": str(offset),
                    "sigma_ratio": str(sigma),
                    "finite_declared_witness": result.to_dict(),
                    "floating_analytic_gauge_maximum_difference": delta,
                }
            )
    pixels = np.column_stack((np.arange(25), np.zeros(25, dtype=int)))
    source_factor = profile_observations.PixelNoise.factor(np.eye(25), 1.0)
    linear_fit = raw_source_fit.fit_plane_edge_offset(
        pixels,
        np.array([float(v) for v in truth]),
        source_factor,
        sensor_shape=(1, 25),
        homography=np.eye(3),
        anchor=[12.5, 0.5],
        normal=[1.0, 0.0],
        psf_covariance=np.eye(2) * 16,
        offset_bounds=(-2, 2),
        level_bounds=(0, 1),
    )
    result = {
        "format": "pictures-to-cad-response-calibration-study",
        "version": 1,
        "plan": plan,
        "units": {
            "offset": "true Gaussian sigma",
            "response_input": "normalized declared optical mean",
            "response_output": "normalized source level",
        },
        "profile_positions_sigma": [str(x) for x in positions],
        "true_output_levels": [str(y) for y in truth],
        "candidate_inputs": [
            {"index": i, "offset_sigma": str(e), "exact_frozen_input_levels": [str(x) for x in xs]}
            for i, (e, xs) in enumerate(zip(offsets, inputs))
        ],
        "calibration_comparisons": results,
        "analytic_gauge": {
            "formula": "h_prime(u) = h(Phi((sigma_prime/sigma)*Phi_inverse(u) + (e_prime-e)/sigma))",
            "scope": "Affine straight Gaussian profile; not a general projective 2-D gauge. Fixed later digital operators preserve identical source fields.",
            "cases": gauges,
        },
        "linear_response_mismatch": {
            "fit": asdict(linear_fit),
            "offset_error_sigma": linear_fit.best.offset / 4,
            "scope": "Different conditional model: two profiled levels and linear response; identity source projection, supplied unit deviations, 4-raw-pixel sigma. This is a mismatch control, not a ranking against exact interval feasibility.",
        },
        "named_controls": named_controls(),
        "provenance": {
            "git": git_metadata(),
            "source_sha256": initial,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "elapsed_seconds": time.monotonic() - start,
        },
    }
    if initial != hashes():
        raise ValueError("study sources changed during execution; refuse unbound results")
    return result


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="fresh JSON destination")
    options = parser.parse_args(arguments)
    try:
        if options.output.exists() or options.output.is_symlink():
            raise ValueError("output already exists; preserve it and choose a new path")
        result = run()
        text = json.dumps(result, indent=2, allow_nan=False) + "\n"
        options.output.parent.mkdir(parents=True, exist_ok=True)
        with options.output.open("x") as handle:
            handle.write(text)
        print(
            json.dumps(
                {
                    "output": str(options.output),
                    "candidate_fits": sum(
                        len(c["all_candidate_results"]) for c in result["calibration_comparisons"]
                    ),
                    "gauge_controls": len(result["analytic_gauge"]["cases"]),
                    "seconds": result["provenance"]["elapsed_seconds"],
                }
            )
        )
    except (OSError, ValueError, TypeError, AssertionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
