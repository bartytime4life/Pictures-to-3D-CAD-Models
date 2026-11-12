"""Retain finite common-response candidates with outward Gaussian input bounds.

Run --output NEW_JSON. Both input quantifiers are checked for every candidate.
Some-incompatible boxes exclude the supplied analytic model; all-compatible
boxes certify one response for every covered input. Remaining box-compatible
cases are undetermined, not asserted feasible for correlated Gaussian inputs.
No photographs, production correction or physical calibration are involved.
"""

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PLAN = ROOT / "studies/response-rectangles-v1.json"
SOURCE_FILES = (
    "backend/response_calibration.py",
    "backend/response_rectangles.py",
    "backend/normal_cdf_bounds.py",
    "scripts/response_rectangles_study.py",
    "studies/response-rectangles-v1.json",
)


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def git_context():
    try:

        def git(*args):
            return subprocess.check_output(
                ["git", "-C", str(ROOT), *args], text=True, timeout=5
            ).strip()

        return {
            "revision": git("rev-parse", "HEAD"),
            "dirty_files": git("status", "--porcelain", "--untracked-files=all").splitlines(),
        }
    except (OSError, subprocess.SubprocessError):
        return {"revision": None, "dirty_files": None, "reason": "Git metadata unavailable"}


def h(value):
    return value + F(3, 20) * value * (1 - value)


def compact(result):
    data = result.to_dict()
    return {
        key: data[key]
        for key in (
            "status",
            "input_mode",
            "slope_bounds",
            "witness",
            "assignments",
            "contradiction",
            "work",
        )
    }


def classify(some, all_inputs):
    if some.status == "incompatible":
        if all_inputs.status != "incompatible":
            raise AssertionError("all feasible must imply some feasible")
        return "excluded_by_outer_boxes"
    if all_inputs.status == "compatible":
        return "one_response_for_all_covered_inputs"
    return "undetermined_by_boxes"


def run_study():
    before = source_hashes()
    from backend.normal_cdf_bounds import normal_cdf_bounds
    from backend.response_calibration import calibrate_response
    from backend.response_rectangles import calibrate_rectangles

    if before != source_hashes():
        raise ValueError("study sources changed while importing")
    plan = json.loads(PLAN.read_text())
    if plan["format"] != "pictures-to-cad-response-rectangles-study-plan" or plan["version"] != 1:
        raise ValueError("unsupported study plan")
    positions = tuple(map(F, plan["positions"]))
    offsets = tuple(map(F, plan["candidate_offsets"]))
    places = tuple(plan["cdf_places"])
    halfwidths = tuple(map(F, plan["observation_halfwidths"]))
    patches = tuple(map(F, plan["patch_inputs"]))
    true_offset, sigma = F(plan["true_offset"]), F(plan["supplied_sigma"])
    if not (
        1 <= len(positions) <= 32
        and 1 <= len(offsets) <= 33
        and 1 <= len(places) <= 8
        and 1 <= len(halfwidths) <= 4
        and len(patches) <= 16
    ):
        raise ValueError("study population exceeds its finite caps")
    if (
        sigma <= 0
        or any(width < 0 for width in halfwidths)
        or any(type(p) is not int or not 1 <= p <= 30 for p in places)
    ):
        raise ValueError("invalid study bounds")
    regimes = plan["regimes"]
    if regimes != [
        "normalized_endpoints",
        "five_exact_patches_slopes",
        "five_bounded_patches_slopes",
        "incorrect_identity_patches_slopes",
    ]:
        raise ValueError("unsupported study regimes")
    if (
        any(not 0 <= x <= 1 for x in patches)
        or not {F(0), F(1)} <= set(patches)
        or F(plan["bounded_patch_halfwidth"]) < 0
        or plan["response"] != "h(u)=u+(3/20)*u*(1-u)"
    ):
        raise ValueError("study response and calibration patches must use the declared [0,1] model")
    start = time.monotonic()

    @lru_cache(maxsize=2048)
    def cdf(z, precision):
        return normal_cdf_bounds(z, places=precision)

    truth = []
    for x in positions:
        cover = cdf((x - true_offset) / sigma, plan["true_output_generation_cdf_places"])
        truth.append(
            {
                "position": str(x),
                "cdf_input": [str(cover.lower), str(cover.upper)],
                "recorded_output_cover": [str(h(cover.lower)), str(h(cover.upper))],
            }
        )

    rows = []
    for regime in regimes:
        bounded = regime == "five_bounded_patches_slopes"
        patch_width = F(plan["bounded_patch_halfwidth"]) if bounded else F(0)
        patch_xs = (F(0), F(1)) if regime == "normalized_endpoints" else patches
        patch_rectangles = []
        for x in patch_xs:
            level = x if regime == "incorrect_identity_patches_slopes" else h(x)
            patch_rectangles.append(
                {
                    "input": [x, x],
                    "output": [max(F(0), level - patch_width), min(F(1), level + patch_width)],
                }
            )
        slopes = (F(0), None) if regime == "normalized_endpoints" else (F(17, 20), F(23, 20))
        for halfwidth in halfwidths:
            for precision in places:
                for offset in offsets:
                    rectangles = list(patch_rectangles)
                    covers = []
                    for x, observed in zip(positions, truth):
                        z = (x - offset) / sigma
                        cover = cdf(z, precision)
                        low, high = map(F, observed["recorded_output_cover"])
                        rectangles.append(
                            {
                                "input": [cover.lower, cover.upper],
                                "output": [low - halfwidth, high + halfwidth],
                            }
                        )
                        covers.append({"z": str(z), "places": precision})
                    row = {
                        "index": len(rows),
                        "regime": regime,
                        "observation_halfwidth": str(halfwidth),
                        "cdf_places": precision,
                        "offset": str(offset),
                        "cdf_covers": covers,
                        "slope_bounds": [
                            str(slopes[0]),
                            None if slopes[1] is None else str(slopes[1]),
                        ],
                        "rectangles": [
                            {axis: list(map(str, rect[axis])) for axis in ("input", "output")}
                            for rect in rectangles
                        ],
                    }
                    try:
                        some = calibrate_rectangles(
                            rectangles, slope_bounds=slopes, input_mode="some"
                        )
                        all_inputs = calibrate_rectangles(
                            rectangles, slope_bounds=slopes, input_mode="all"
                        )
                        row.update(
                            classification=classify(some, all_inputs),
                            some=compact(some),
                            all=compact(all_inputs),
                        )
                    except (ValueError, TypeError, ArithmeticError, AssertionError) as exc:
                        row.update(
                            classification="execution_failure",
                            error_type=type(exc).__name__,
                            error=str(exc),
                        )
                    rows.append(row)

    # Exact named controls expose changes in the question, not empirical accuracy.
    controls = []

    def control(name, rectangles, slopes=("0", None), modes=("some", "all")):
        results = {
            mode: compact(calibrate_rectangles(rectangles, slope_bounds=slopes, input_mode=mode))
            for mode in modes
        }
        data = {
            "name": name,
            "rectangles": rectangles,
            "slope_bounds": [str(slopes[0]), None if slopes[1] is None else str(slopes[1])],
            "results": results,
        }
        controls.append(data)
        return data

    midpoint = control(
        "midpoint_changes_existential_question",
        [{"input": ["0", "2"], "output": ["1", "1"]}, {"input": ["1", "1"], "output": ["0", "0"]}],
    )
    midpoint["midpoint_fixed_input_result"] = calibrate_response(
        [{"input": "1", "output": ["1", "1"]}, {"input": "1", "output": ["0", "0"]}]
    ).to_dict()
    control(
        "same_non_degenerate_interval_not_duplicate_knot",
        [{"input": ["0", "1"], "output": ["0", "0"]}, {"input": ["0", "1"], "output": ["1", "1"]}],
    )
    control("strict_slope_some_vs_all", [{"input": ["0", "1"], "output": ["0", "0"]}], ("1", "1"))
    for name, slopes in [
        ("unbounded_marginals_finite_witness", ("0", None)),
        ("finite_upper_slope_midpoint", ("0", "2")),
    ]:
        item = control(name, [{"input": ["0", "1"], "output": ["0", "0"]}], slopes)
        result = calibrate_rectangles(item["rectangles"], slope_bounds=slopes, input_mode="some")
        item["some_queries"] = [
            {
                "input": x,
                "output": [
                    None if y is None else str(y)
                    for y in (result.query(x).lower, result.query(x).upper)
                ],
            }
            for x in ("0", "0.5", "1")
        ]
    correlated = control(
        "shared_offset_is_not_cartesian_selection",
        [{"input": ["0", "1"], "output": ["1", "1"]}, {"input": ["1", "2"], "output": ["1", "1"]}],
        ("1", "1"),
    )
    correlated["coupled_model"] = {
        "inputs": ["delta", "1+delta"],
        "delta": ["0", "1"],
        "forced_output_difference": "1",
        "observed_output_difference": "0",
        "status": "incompatible_by_exact_unit_slope_identity",
    }
    cover = cdf(F(1), 30)
    rounded = F.from_float(0.5 * math.erfc(-1 / math.sqrt(2)))
    controls.append(
        {
            "name": "rounded_float_is_not_exact_gaussian_probability",
            "z": "1",
            "certified_cover": [str(cover.lower), str(cover.upper)],
            "frozen_float": str(rounded),
            "float_inside_cover": cover.lower <= rounded <= cover.upper,
        }
    )

    summaries = []
    for regime in regimes:
        for halfwidth in halfwidths:
            for precision in places:
                selected = [
                    r
                    for r in rows
                    if r["regime"] == regime
                    and r["observation_halfwidth"] == str(halfwidth)
                    and r["cdf_places"] == precision
                ]
                counts = Counter(r["classification"] for r in selected)
                summaries.append(
                    {
                        "regime": regime,
                        "observation_halfwidth": str(halfwidth),
                        "cdf_places": precision,
                        "candidates": len(selected),
                        "counts": dict(counts),
                        "classified_offsets": {
                            kind: [r["offset"] for r in selected if r["classification"] == kind]
                            for kind in sorted(counts)
                        },
                    }
                )
    all_covers = []
    zs = sorted({(x - offset) / sigma for x in positions for offset in offsets} | {F(1)})
    for z in zs:
        for precision in sorted(set(places) | {plan["true_output_generation_cdf_places"]}):
            all_covers.append(cdf(z, precision).to_dict())
    nesting = []
    for z in zs:
        for coarse, fine in zip(sorted(places), sorted(places)[1:]):
            a, b = cdf(z, coarse), cdf(z, fine)
            nesting.append(
                {
                    "z": str(z),
                    "coarse": coarse,
                    "fine": fine,
                    "nested": a.lower <= b.lower <= b.upper <= a.upper,
                }
            )
    after = source_hashes()
    if before != after:
        raise ValueError("study sources changed during execution")
    failures = sum(r["classification"] == "execution_failure" for r in rows)
    return {
        "format": "pictures-to-cad-response-rectangles-study",
        "version": 1,
        "plan": plan,
        "source_sha256_before": before,
        "source_sha256_after": after,
        "git": git_context(),
        "runtime": {"python": platform.python_version(), "seconds": time.monotonic() - start},
        "truth": truth,
        "cdf_covers": all_covers,
        "cdf_nesting_checks": nesting,
        "rows": rows,
        "summaries": summaries,
        "controls": controls,
        "summary": {
            "expected_rows": len(regimes) * len(halfwidths) * len(places) * len(offsets),
            "retained_rows": len(rows),
            "execution_failures": failures,
            "classification_counts": dict(Counter(r["classification"] for r in rows)),
        },
        "limits": [
            "Finite candidate offsets only; no continuous exclusion, global uniqueness or confidence interval.",
            "Excluded outer boxes exclude the supplied Gaussian model; compatible some boxes alone may use unrealizable Cartesian input selections.",
            "All-compatible boxes provide one response for every covered input, including the supplied correlated Gaussian vector.",
            "Undetermined box results must stay undetermined; this runner does not substitute midpoint inputs.",
            "Truth output bands include outward 30-place Gaussian generation covers, even when additional observation halfwidth is zero.",
            f"All comparisons reuse one {len(positions)}-position synthetic truth profile; rows are hypotheses, not independent captures.",
            "Optics, affine geometry, response regularity, calibration and error bands are supplied mathematical assumptions; no physical camera qualification.",
        ],
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path, help="new JSON result; existing paths refused"
    )
    options = parser.parse_args(arguments)
    try:
        if options.output.exists() or options.output.is_symlink():
            raise ValueError("output already exists; choose a fresh destination")
        report = run_study()
        text = json.dumps(report, indent=2, allow_nan=False) + "\n"
        options.output.parent.mkdir(parents=True, exist_ok=True)
        with options.output.open("x") as handle:
            handle.write(text)
        print(text, end="")
        return 1 if report["summary"]["execution_failures"] else 0
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
