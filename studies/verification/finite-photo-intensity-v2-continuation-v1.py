#!/usr/bin/env python3
"""Inject the first fit-entry exception; execute all nine later real optimizers.

No source/plan/image changes. Compare all eleven later parsed canonical rows,
removing only fields named runtime_seconds. Result/stdout and a separate audit are
fresh files; this is actual optimizer continuation, unlike no-fit sentinel tests.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "studies/verification/finite-photo-intensity-v2.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(value):
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in value.items() if key != "runtime_seconds"}
    if isinstance(value, list):
        return [normalized(item) for item in value]
    return value


def recorded_path(path):
    path = path.absolute()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.output, args.audit):
        if path.suffix != ".json" or path.exists() or path.is_symlink() or not path.parent.is_dir():
            parser.error("output and audit must be fresh .json paths in existing directories")
    if args.output == args.audit:
        parser.error("output and audit must differ")
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("_photo_v2_first_fit_failure", RUNNER)
    study = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = study
    spec.loader.exec_module(study)
    canonical = study.strict_json(args.canonical)
    control_sha_before = sha(__file__)
    canonical_sha_before = sha(args.canonical)
    runner_sha_before = sha(RUNNER)
    from backend import finite_centre_fit as core

    real_fit = core.fit_circular_segment
    entries = []

    def first_entry_failure(*positional, **keywords):
        index = len(entries)
        entry = {"index": index, "pixel_count": len(positional[0]), "actual_optimizer": index != 0}
        entries.append(entry)
        if index == 0:
            entry["status"] = "injected_first_entry_exception"
            raise ValueError("ACTUAL_FIRST_FIT_ENTRY_FAILURE_V1")
        try:
            result = real_fit(*positional, **keywords)
        except Exception as error:
            entry["status"] = "actual_optimizer_exception"
            entry["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        entry["status"] = "actual_optimizer_returned"
        return result

    core.fit_circular_segment = first_entry_failure
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            study_exit = study.main(["--output", str(args.output)])
    finally:
        core.fit_circular_segment = real_fit
    report = study.strict_json(args.output)
    comparisons = []
    for index in range(1, 12):
        old, new = canonical["rows"][index], report["rows"][index]
        old_normal, new_normal = normalized(old), normalized(new)
        comparisons.append(
            {
                "index": index,
                "name": new["name"],
                "lane": new["lane"],
                "identical_except_runtime_seconds": old_normal == new_normal,
                "canonical_parsed_row_sha256": study.parsed_sha(old_normal),
                "continuation_parsed_row_sha256": study.parsed_sha(new_normal),
            }
        )
    first = report["rows"][0]
    checks = [
        {"name": "all-twelve-planned-rows-retained", "passed": len(report["rows"]) == 12},
        {
            "name": "one-entry-injected-nine-later-real-optimizers",
            "passed": len(entries) == 10
            and sum(e["actual_optimizer"] for e in entries) == 9
            and entries[0]["status"] == "injected_first_entry_exception"
            and all(e["status"] == "actual_optimizer_returned" for e in entries[1:]),
        },
        {
            "name": "first-failure-explicit-and-no-pass-flags",
            "passed": first["index"] == 0
            and first["status"] == "execution_failure"
            and first["failure_stage"] == "inverse_fit"
            and first["error"]["message"] == "ACTUAL_FIRST_FIT_ENTRY_FAILURE_V1"
            and not first["completion_passed"]
            and not first["targets_passed"],
        },
        {
            "name": "all-eleven-later-parsed-rows-identical",
            "passed": len(comparisons) == 11
            and all(row["identical_except_runtime_seconds"] for row in comparisons),
        },
        {
            "name": "two-original-upstream-refusals-retained",
            "passed": sum(row["status"] == "upstream_ineligible" for row in report["rows"]) == 2,
        },
        {
            "name": "same-observation-checks",
            "passed": report["observation_controls"] == canonical["observation_controls"],
        },
        {
            "name": "strict-file-stdout-identical",
            "passed": args.output.read_text() == captured.getvalue(),
        },
        {
            "name": "full-governing-closure-unchanged",
            "passed": report["source_unchanged"]
            and report["source_before"]
            == report["source_after"]
            == canonical["source_before"]
            == canonical["source_after"],
        },
        {"name": "canonical-preserved", "passed": sha(args.canonical) == canonical_sha_before},
        {
            "name": "runner-and-contract-script-unchanged",
            "passed": sha(RUNNER) == runner_sha_before and sha(__file__) == control_sha_before,
        },
    ]
    audit = {
        "format": "finite-photo-intensity-v2-actual-first-fit-failure-contract",
        "scope": "Only first fit entry raises; nine later real optimizers execute. All eleven later parsed rows compared, including both upstream refusals; only runtime_seconds fields removed.",
        "canonical": {
            "path": recorded_path(args.canonical),
            "sha256": canonical_sha_before,
        },
        "control_result": {"path": recorded_path(args.output), "sha256": sha(args.output)},
        "runner_sha256": runner_sha_before,
        "contract_script_sha256": control_sha_before,
        "study_exit_code": study_exit,
        "fit_entries": entries,
        "later_row_comparisons": comparisons,
        "checks": checks,
        "summary": {
            "checks": len(checks),
            "passes": sum(c["passed"] for c in checks),
            "actual_optimizers_executed": sum(e["actual_optimizer"] for e in entries),
            "retained_rows": len(report["rows"]),
            "all_passed": all(c["passed"] for c in checks),
        },
    }
    with args.audit.open("x") as stream:
        json.dump(audit, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(captured.getvalue(), end="")
    print(json.dumps({"continuation_audit": audit["summary"]}, allow_nan=False), file=sys.stderr)
    return 0 if audit["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
