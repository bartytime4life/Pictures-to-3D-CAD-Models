#!/usr/bin/env python3
"""Continue uncaptured acquisition scenes after a retained bootstrap failure.

This is an explicit adapter around the frozen driver, not a rerun of its CLI.
Qualified global controls are read from the immutable first result. No control
or reference is evaluated again; all scene-specific controls remain active.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/finite-acquisition-operator-v1-continuation-v1.json"
PLAN_SHA256 = "846d1f26635122a6b5038a5f9347421edc8f61181478702e8e602b99b8994e88"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_driver(path):
    spec = importlib.util.spec_from_file_location("acquisition_frozen_driver_v1", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bindings(plan):
    names = set(plan["input_sha256"])
    names.update({str(PLAN.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))})
    return {name: sha(ROOT / name) for name in sorted(names)}


def admit(plan, first, driver):
    if first.get("protocol_passed") is not False or not first.get("source_unchanged"):
        raise ValueError("original failed-attempt identity changed")
    if first.get("scenes") or len(first.get("rows", [])) != 32:
        raise ValueError("continuation requires zero previous captured scenes")
    if any(row["status"] != "scene_exception" for row in first["rows"]):
        raise ValueError("original capture census changed")
    if not driver.global_qualified(first["controls"]):
        raise ValueError("original global controls are not qualified")
    records = first["controls"]["independent_gaussian"]["rows"]
    if [(r["q"], r["sigma"]) for r in records] != [(q, s) for q in (1.0, 1.25) for s in (1.2, 3.0)]:
        raise ValueError("original rectangle-control identities changed")
    calls = first["forward_calls"]
    if len(calls) != 4 or sum(c["queries"] for c in calls) != 24:
        raise ValueError("original controls/main-call census changed")
    for index, call in enumerate(calls):
        if (
            call["lane"] != "rectangle_control"
            or not call["completed"]
            or not call["valid_payload"]
        ):
            raise ValueError("cannot reuse an incomplete or malformed control")
        if call["returned_result"] != records[index]["api"] or not records[index]["passed"]:
            raise ValueError("original call/reference binding differs")
    before = first["source_before"]
    if first["source_after"] != before:
        raise ValueError("original scientific sources changed during execution")
    for name, original in before.items():
        current = sha(ROOT / name)
        if name == plan["bootstrap_only_allowed_source_change"]:
            if original != plan["old_helper_sha256"] or current != plan["new_helper_sha256"]:
                raise ValueError("bootstrap helper change is outside the admitted pair")
        elif current != original:
            raise ValueError(f"cached-control dependency changed: {name}")
    return calls


def adapters(driver, first, origin_sha):
    original_load = driver.load_module

    def cached_module(name, path):
        module = original_load(name, path)
        if name == "acquisition_controls_v1":
            module.run_controls = lambda: copy.deepcopy(first["controls"]["exact_keys"])
        return module

    def cached_gaussian(core, work):
        del core
        for index, original in enumerate(first["forward_calls"]):
            call = copy.deepcopy(original)
            call.update(
                performed_this_continuation=False,
                original_call_index=index,
                origin_report_sha256=origin_sha,
            )
            work.append(call)
        return copy.deepcopy(first["controls"]["independent_gaussian"])

    driver.load_module = cached_module
    driver.keys_controls = lambda sheet, np: copy.deepcopy(first["controls"]["production_keys"])
    driver.gaussian_controls = cached_gaussian


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="New directory, existing parent; no overwrites",
    )
    args = parser.parse_args()
    output = args.output_dir.absolute()
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        parser.error("output directory must be fresh and its parent must exist")
    if sha(PLAN) != PLAN_SHA256:
        parser.error("continuation plan SHA-256 mismatch")
    plan = json.loads(PLAN.read_text())
    for name, expected in plan["input_sha256"].items():
        if sha(ROOT / name) != expected:
            parser.error(f"frozen continuation input mismatch: {name}")
    driver = load_driver(ROOT / plan["original_driver"])
    original_plan = driver.read_json(ROOT / plan["original_plan"])
    before = bindings(plan)
    output.mkdir(mode=0o700)
    report = {
        "format": "pictures-to-cad-finite-acquisition-continuation-result",
        "version": 1,
        "execution_kind": "bootstrap_corrected_continuation",
        "protocol_passed": False,
        "rows": [],
        "continuation_source_before": before,
        "continuation_plan_sha256": sha(PLAN),
        "original_attempt": {
            "exit_code": 1,
            "protocol_passed": False,
            "report_decoded_sha256": plan["original_report_decoded_sha256"],
        },
    }
    try:
        raw = gzip.decompress((ROOT / plan["original_report"]).read_bytes())
        if hashlib.sha256(raw).hexdigest() != plan["original_report_decoded_sha256"]:
            raise ValueError("original decoded report hash mismatch")
        first = json.loads(raw)
        admit(plan, first, driver)
        # Environment admission performs imports, never a model/reference call.
        sys.path.insert(0, str(ROOT))
        import cv2
        import numpy as np

        versions = {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "opencv": cv2.__version__,
        }
        if versions != first["versions"]:
            raise ValueError("cached-control environment versions changed")
        if Path(sys.executable).absolute() != (ROOT / ".venv/bin/python").absolute():
            raise ValueError("continuation requires the original repository interpreter path")
        report["environment_admission"] = {
            "versions": versions,
            "executable": sys.executable,
            "resolved_executable": str(Path(sys.executable).resolve()),
            "scope": "source and recorded versions; no original package-binary hash proof",
        }
        adapters(driver, first, plan["original_report_decoded_sha256"])
        driver.run(original_plan, output, report)
        report["format"] = "pictures-to-cad-finite-acquisition-continuation-result"
    except Exception as exc:  # noqa: BLE001 -- preserve all declared rows and completed work.
        report["protocol_passed"] = False
        report["continuation_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    report["format"] = "pictures-to-cad-finite-acquisition-continuation-result"
    driver.complete_adequacy_census(report, original_plan)
    for call in report.get("forward_calls", []):
        call.setdefault("performed_this_continuation", True)
    groups = {"new": [], "reused": []}
    for call in report.get("forward_calls", []):
        groups["new" if call["performed_this_continuation"] else "reused"].append(call)
    report["forward_work_by_execution"] = {
        group: {
            "calls": len(calls),
            "queries": sum(c["queries"] for c in calls),
            "completed_calls": sum(c["completed"] for c in calls),
            "evaluations": sum(c.get("evaluations", 0) for c in calls),
            "panels": sum(c.get("panels", 0) for c in calls),
        }
        for group, calls in groups.items()
    }
    try:
        report["source_after"] = driver.source_bindings(original_plan)
        report["source_unchanged"] = report.get("source_before") == report["source_after"]
        if not report["source_unchanged"]:
            report["protocol_passed"] = False
        report["continuation_source_after"] = bindings(plan)
        report["continuation_source_unchanged"] = before == report["continuation_source_after"]
        if not report["continuation_source_unchanged"]:
            report["protocol_passed"] = False
    except (OSError, subprocess.SubprocessError) as exc:
        report["protocol_passed"] = False
        report["continuation_source_error"] = {"type": type(exc).__name__, "message": str(exc)}
    report = driver.portable_payload(report)
    driver.write_new(output / "report.json", report)
    print(
        json.dumps(
            {
                "report": str(output / "report.json"),
                "protocol_passed": report["protocol_passed"],
                "forward_work_by_execution": report["forward_work_by_execution"],
            }
        ),
        flush=True,
    )
    return 0 if report["protocol_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
