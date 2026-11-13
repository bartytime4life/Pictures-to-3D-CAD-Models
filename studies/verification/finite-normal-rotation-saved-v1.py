#!/usr/bin/env python3
"""Post-hoc rotation identity from saved arrays; no model or new forward calls.

This does not replace the original failed FD control, qualify the unknown normal
columns, or execute a new trial. Independent synthetic validation is future work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

EXPECTED_REPORT = "b1d15d4e006d1f65823cb6bd20810cd127d6d6ac6912973d590f38bd8acc6c74"
EXPECTED_RUNNER = "c4da819d3bf34bc4183fe55529d87acedc2946bf0fcdcd878ae2fd20eb3e7d69"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reject(value):
    raise ValueError("nonfinite JSON constant: " + value)


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def product(a, b):
    return [[math.fsum(a[i][k] * b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


def analyze(row):
    baseline = row["baseline"]
    parameters = baseline["parameters"]
    h = parameters["homography"]
    if h != [[1.0, 0.0, h[0][2]], [0.0, 1.0, h[1][2]], [0.0, 0.0, 1.0]]:
        raise ValueError("this saved analysis supports translation-only homographies")
    covariance = parameters["covariance"]
    a, b = covariance[0]
    if covariance[1][0] != b or a <= 0 or a * covariance[1][1] - b * b <= 0:
        raise ValueError("strict symmetric positive-definite covariance required")
    d = covariance[1][1]
    l00 = math.sqrt(a)
    l10 = b / l00
    l11 = math.sqrt(d - l10 * l10)
    inverse = [[1 / l00, 0.0], [-l10 / (l00 * l11), 1 / l11]]
    commutator = [[2 * b, d - a], [d - a, -2 * b]]
    whitened = product(product(inverse, commutator), [list(x) for x in zip(*inverse, strict=True)])
    coefficients = [
        whitened[0][0],
        whitened[1][1],
        (whitened[0][1] + whitened[1][0]) / math.sqrt(2),
    ]
    widths = baseline["domain_widths"]
    centre = parameters["centre"]
    geometric = row["blocks"]["G"]
    covariance_block = row["blocks"]["S"]
    normal = row["finite_differences"][3]
    entries = normal["entries"]
    assert [entry["h"] for entry in entries] == [0.001, 0.0005]
    derived, errors, global_queries, terms_saved = [], [], [], []
    for i, pixel in enumerate(row["observations"]["pixels_xy"]):
        q = [pixel[j] + 0.5 - h[j][2] for j in range(2)]
        lever = [-(q[1] - centre[1]), q[0] - centre[0]]
        terms = [geometric["values"][i][j] / widths[j] * lever[j] for j in range(2)]
        terms += [covariance_block["values"][i][j] * coefficients[j] for j in range(3)]
        estimated = math.fsum(
            abs(lever[j]) * geometric["errors"][i][j] / widths[j] for j in range(2)
        )
        estimated += math.fsum(
            abs(coefficients[j]) * covariance_block["errors"][i][j] for j in range(3)
        )
        estimated += 64 * sys.float_info.epsilon * max(1.0, math.fsum(abs(t) for t in terms))
        global_queries.append(q)
        derived.append(math.fsum(terms))
        errors.append(estimated)
        terms_saved.append(terms)
    coarse, fine = [entry["derivative"] for entry in entries]
    assert len(derived) == len(coarse) == len(fine) == 56
    coarse_difference = [x - y for x, y in zip(coarse, derived, strict=True)]
    fine_difference = [x - y for x, y in zip(fine, derived, strict=True)]
    richardson = [(4 * y - x) / 3 for x, y in zip(coarse, fine, strict=True)]
    richardson_difference = [x - y for x, y in zip(richardson, derived, strict=True)]
    maximum = lambda values: max(abs(x) for x in values)
    return {
        **{key: row[key] for key in ("index", "name", "lane")},
        "status": "posthoc_saved_array_identity_unvalidated",
        "original_status": row["status"],
        "original_normal_FD_stable": normal["stable"],
        "original_normal_status_preserved": True,
        "global_queries_xy": global_queries,
        "covariance_commutator": commutator,
        "whitened_covariance_velocity": whitened,
        "covariance_chart_coefficients": coefficients,
        "geometric_and_covariance_terms": terms_saved,
        "derived_level_normal_column": derived,
        "combined_estimated_error_not_certified": errors,
        "coarse_FD_minus_identity": coarse_difference,
        "fine_FD_minus_identity": fine_difference,
        "richardson_from_saved_FD_minus_identity": richardson_difference,
        "max_abs_coarse_difference": maximum(coarse_difference),
        "max_abs_fine_difference": maximum(fine_difference),
        "max_abs_richardson_difference": maximum(richardson_difference),
        "max_estimated_identity_error": max(errors),
        "coarse_to_fine_max_difference_ratio": maximum(coarse_difference) / maximum(fine_difference)
        if maximum(fine_difference)
        else None,
        "qualification": "Consistency with saved derivatives only; no independent forward validation, replacement N qualification or new fit pass.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("fresh output in an existing directory required")
    if sha(args.report) != EXPECTED_REPORT:
        parser.error("only the exact archived diagnostic report is supported")
    saved = json.loads(args.report.read_text(), parse_constant=reject, object_pairs_hook=pairs)
    assert saved["runner_sha256"] == EXPECTED_RUNNER and saved["protocol_passed"] is False
    assert len(saved["rows"]) == 12
    result = {
        "format": "pictures-to-cad-posthoc-saved-rotation-identity",
        "version": 1,
        "report_sha256": EXPECTED_REPORT,
        "runner_sha256": sha(__file__),
        "derivation": "N = G_C dot J(q_global-C) + S dot chart(L^-1*(Sigma*J-J*Sigma)*L^-T); J=[[0,-1],[1,0]]",
        "scope": "Post-hoc arithmetic on all saved eligible rows, motivated by the failed normal FD guard; not prospective independent validation.",
        "original_protocol_passed": False,
        "original_report_unchanged": True,
        "production_imports": 0,
        "new_forward_calls": 0,
        "new_optimizer_calls": 0,
        "new_trial_steps": 0,
        "rows": [
            analyze(row)
            if "blocks" in row
            else {
                **{key: row[key] for key in ("index", "name", "lane")},
                "status": "upstream_ineligible_preserved",
            }
            for row in saved["rows"]
        ],
    }
    assert sha(args.report) == EXPECTED_REPORT
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rows": len(result["rows"]),
                "original_protocol_passed": False,
                "forward_calls": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
