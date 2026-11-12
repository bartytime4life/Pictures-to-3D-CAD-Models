"""Retain complete shared-parameter response covers for fixed development controls.

Run --output NEW_JSON. Every declared case/budget is retained, including unknown
regions and execution failures. The study uses one repeated three-position truth
profile plus analytic controls; it is not an empirical camera or accuracy study.
"""

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PLAN = ROOT / "studies/gaussian-response-domains-v1.json"
SOURCES = (
    "backend/response_calibration.py",
    "backend/response_rectangles.py",
    "backend/normal_cdf_bounds.py",
    "backend/gaussian_response_domains.py",
    "scripts/gaussian_response_domain_study.py",
    "studies/gaussian-response-domains-v1.json",
)


def source_hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def exact_json(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: exact_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(v) for v in value]
    return value


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


def run_study():
    before = source_hashes()
    from backend.gaussian_response_domains import analyze_gaussian_response
    from backend.normal_cdf_bounds import normal_cdf_bounds

    if before != source_hashes():
        raise ValueError("study source changed while importing")
    plan = json.loads(PLAN.read_text())
    start = time.monotonic()
    expected = [
        "endpoint_order_family",
        "reversed_order_contradiction",
        "finite_slope_feasible_overlap",
        "finite_slope_incompatible_overlap",
        "exact_zero_sigma_alias",
        "thin_feasible_offset_line",
        "identity_joint_band",
        "nonlinear_response_joint_band",
        "rounded_binary_level_singleton",
    ]
    if (
        plan["format"] != "pictures-to-cad-gaussian-response-domain-study-plan"
        or plan["version"] != 1
        or plan["cases"] != expected
    ):
        raise ValueError("unsupported fixed development plan")
    if not 1 <= len(plan["budgets"]) <= 8 or any(
        type(b) is not int or not 1 <= b <= 4095 for b in plan["budgets"]
    ):
        raise ValueError("invalid study budget population")

    def h(x):
        return x + F(3, 20) * x * (1 - x)

    def obs(p, low, high=None):
        return {"position": F(p), "output": [F(low), F(low if high is None else high)]}

    def anchor(x, y):
        return {"input": F(x), "output": [F(y), F(y)]}

    identity = [anchor(0, 0), anchor(1, 1)]
    curved = [anchor(x, h(x)) for x in (F(0), F(1, 4), F(1, 2), F(3, 4), F(1))]
    truth_plan = plan["truth"]
    truth = []
    identity_obs = []
    curved_obs = []
    halfwidth = F(truth_plan["additional_output_halfwidth"])
    if halfwidth < 0 or truth_plan["response"] != "h(u)=u+(3/20)*u*(1-u)":
        raise ValueError("invalid truth-response declaration")
    if not 1 <= len(truth_plan["positions"]) <= 16:
        raise ValueError("invalid truth positions")
    for p in map(F, truth_plan["positions"]):
        cover = normal_cdf_bounds(
            (p - F(truth_plan["offset"])) / F(truth_plan["sigma"]),
            places=truth_plan["generation_places"],
        )
        truth.append(
            {
                "position": str(p),
                "cdf": cover.to_dict(),
                "identity_output": [str(cover.lower - halfwidth), str(cover.upper + halfwidth)],
                "response_output": [
                    str(h(cover.lower) - halfwidth),
                    str(h(cover.upper) + halfwidth),
                ],
            }
        )
        identity_obs.append(obs(p, cover.lower - halfwidth, cover.upper + halfwidth))
        curved_obs.append(obs(p, h(cover.lower) - halfwidth, h(cover.upper) + halfwidth))

    def model(
        observations, calibration=(), offset=("-1", "1"), sigma=("1", "1"), slopes=("0", None)
    ):
        return {
            "observations": observations,
            "calibration": calibration,
            "offset_bounds": list(map(F, offset)),
            "sigma_bounds": list(map(F, sigma)),
            "slope_bounds": [F(slopes[0]), None if slopes[1] is None else F(slopes[1])],
        }

    joint = (("-0.25", "0.25"), ("0.75", "1.25"))
    rounded = F.from_float(0.5 * math.erfc(-1 / math.sqrt(2)))
    models = {
        expected[0]: model(curved_obs, identity, *joint),
        expected[1]: model([obs(0, 1), obs(1, 0)]),
        expected[2]: model([obs(0, 0), obs(1, 1)], slopes=("0", "32")),
        expected[3]: model([obs(0, "0.5"), obs(1, "0.6")], identity, slopes=("1", "1")),
        expected[4]: model([obs(0, "0.5")], identity, ("0", "0"), ("0.75", "1.25"), ("1", "1")),
        expected[5]: model([obs(0, "0.5")], identity, *joint, ("1", "1")),
        expected[6]: model(identity_obs, identity, *joint, ("1", "1")),
        expected[7]: model(curved_obs, curved, *joint, ("0.85", "1.15")),
        expected[8]: model([obs(1, rounded)], identity, ("0", "0"), ("1", "1"), ("1", "1")),
    }
    rows = []
    for name in expected:
        for budget in plan["budgets"]:
            row = {
                "index": len(rows),
                "case": name,
                "max_boxes": budget,
                "model": exact_json(models[name]),
            }
            try:
                result = analyze_gaussian_response(
                    **models[name],
                    cdf_places=plan["cdf_places"],
                    tolerances=plan["tolerances"],
                    max_depth=plan["max_depth"],
                    max_boxes=budget,
                )
                row.update(verification="executed", analysis=result)
            except (ValueError, TypeError, ArithmeticError) as error:
                row.update(
                    verification="execution_failure",
                    error_type=type(error).__name__,
                    error=str(error),
                )
            rows.append(row)
    after = source_hashes()
    if before != after:
        raise ValueError("study source changed during execution")
    summaries = [
        {
            "case": row["case"],
            "max_boxes": row["max_boxes"],
            "status": row.get("analysis", {}).get("status", row["verification"]),
            "inner": row.get("analysis", {}).get("summary", {}).get("accepted_leaves", 0),
            "excluded": row.get("analysis", {}).get("summary", {}).get("excluded_leaves", 0),
            "unknown": row.get("analysis", {}).get("summary", {}).get("unknown_leaves", 0),
            "evaluated": row.get("analysis", {}).get("summary", {}).get("evaluated_boxes", 0),
            "outer_projection": row.get("analysis", {}).get("outer_projection"),
        }
        for row in rows
    ]
    return {
        "format": "pictures-to-cad-gaussian-response-domain-study",
        "version": 1,
        "plan": plan,
        "truth": truth,
        "rows": rows,
        "summaries": summaries,
        "rounded_level_control": str(rounded),
        "summary": {
            "expected_rows": len(expected) * len(plan["budgets"]),
            "retained_rows": len(rows),
            "execution_failures": sum(r["verification"] == "execution_failure" for r in rows),
        },
        "source_sha256_before": before,
        "source_sha256_after": after,
        "git": git_context(),
        "runtime": {"python": platform.python_version(), "seconds": time.monotonic() - start},
        "limits": [
            "All budgets reuse the same fixed models and truth profile; no independent captures.",
            "Inner/outer joint boxes concern the supplied mathematical model; projection hulls lose correlation.",
            "Unknown boxes, including thin feasible sets and budget limits, do not become exclusion.",
            "Different parameter pairs may require different common response functions; no single calibration of the whole union.",
            "No physical Gaussian PSF, real noise bound, product correction or manufacturing acceptance is qualified.",
        ],
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path, help="fresh JSON destination; existing paths refused"
    )
    args = parser.parse_args(arguments)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output already exists; choose a fresh destination")
        result = run_study()
        text = json.dumps(exact_json(result), indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(text)
        print(text, end="")
        return int(result["summary"]["execution_failures"] != 0)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
