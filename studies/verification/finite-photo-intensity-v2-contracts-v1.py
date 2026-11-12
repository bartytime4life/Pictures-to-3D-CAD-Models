#!/usr/bin/env python3
"""No inverse fitting: actual archived preparation/means and CLI/routing contracts."""

import argparse
import contextlib
import copy
import importlib.util
import io
import json
import math
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "studies/verification/finite-photo-intensity-v2.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    output = parser.parse_args().output
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        parser.error("fresh output required")
    sys.path.insert(0, str(ROOT))
    study = load("_photo_v2_preflight_study", RUNNER)
    plan = study.strict_json(study.PLAN)
    manifest, baseline, moments, _ = study.load_inputs(plan)
    before = study.source_hashes(plan, manifest)
    before["preflight_runner"] = study.sha(__file__)
    checks = []
    calls = []
    original_run = study.run_study

    def forbidden_analysis(*args, **kwargs):
        calls.append("analysis")
        raise AssertionError("CLI refusal attempted analysis")

    study.run_study = forbidden_analysis
    with tempfile.TemporaryDirectory(prefix="photo-v2-preflight-") as name:
        directory = Path(name)
        occupied = directory / "occupied.json"
        occupied.write_text("retained\n")
        dangling = directory / "dangling.json"
        dangling.symlink_to(directory / "absent")
        contracts = [
            ("help", ["--help"], 0),
            ("missing-output", [], 2),
            ("existing-output", ["--output", str(occupied)], 2),
            ("dangling-symlink", ["--output", str(dangling)], 2),
            ("invalid-suffix", ["--output", str(directory / "bad.txt")], 2),
            ("missing-parent", ["--output", str(directory / "missing/new.json")], 2),
        ]
        for label, arguments, expected in contracts:
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                try:
                    code = study.main(arguments)
                except SystemExit as error:
                    code = error.code
            checks.append({"name": label, "passed": code == expected and not calls, "exit": code})
        fake = {
            "source_unchanged": True,
            "summary": {
                "targets_passed": 12,
                "observation_controls_all_passed": True,
                "paired_observations_all_identical": True,
            },
            "scope": "CLI serialization stub only; no preparation or fit",
        }
        study.run_study = lambda *args, **kwargs: fake
        stdout = io.StringIO()
        fresh = directory / "fresh.json"
        with contextlib.redirect_stdout(stdout):
            code = study.main(["--output", str(fresh)])
        checks.append(
            {
                "name": "fresh-strict-file-stdout",
                "passed": code == 0
                and fresh.read_text() == stdout.getvalue()
                and json.loads(stdout.getvalue()) == fake,
                "scope": "stub report exercises CLI serialization, not fitting",
            }
        )
        checks.append(
            {
                "name": "occupied-and-symlink-preserved",
                "passed": occupied.read_text() == "retained\n" and dangling.is_symlink(),
            }
        )
        for label, encoded in (
            ("overflow-float-json-refusal", '{"x":1e9999}'),
            ("negative-overflow-float-json-refusal", '{"x":-1e9999}'),
            ("nonfinite-literal-json-refusal", '{"x":NaN}'),
            ("duplicate-key-json-refusal", '{"x":1,"x":2}'),
        ):
            bad = directory / f"{label}.json"
            bad.write_text(encoded)
            try:
                study.strict_json(bad)
                refused = False
            except ValueError:
                refused = True
            checks.append({"name": label, "passed": refused})
    study.run_study = original_run

    import numpy as np

    from backend import finite_centre_fit as core
    from backend import finite_observations as helper

    fit_calls = []
    original_fit = core.fit_circular_segment

    def forbidden_fit(*args, **kwargs):
        fit_calls.append(len(args[0]))
        raise RuntimeError("NO_FIT_PREFLIGHT_SENTINEL")

    core.fit_circular_segment = forbidden_fit
    oracle = study.load_module(
        "_photo_v2_preflight_area", ROOT / "studies/verification/finite-free-centre-v1.py"
    )
    oracle_plan = study.strict_json(ROOT / "studies/finite-free-centre-v1.json")
    nominal = {
        r["name"]: r
        for r in moments["rows"]
        if r.get("roi_sigmas") == 8 and r.get("background_offset") == 0
    }
    measured_by_name = {r["name"]: r for r in manifest["measurements"]}
    contexts = []
    observation_checks = []
    for original in baseline["rows"]:
        name = original["case"]["name"]
        measured = original.get("measurements", {})
        if name not in measured_by_name or not measured.get("rings"):
            observation_checks.append(
                {"name": name, "status": "upstream_ineligible", "all_passed": True}
            )
            continue
        item = measured_by_name[name]
        with np.load(study.FIXTURES / item["file"], allow_pickle=False) as archive:
            field, points = archive["g"].copy(), archive["points"].copy()
        outer = next(i for i, r in enumerate(measured["rings"]) if r["outer"])
        primitives = measured["initial_fits"][outer]
        normal, normal_record = study.observed_normal(primitives, np)
        scalar = float(measured["sigma"])
        covariances = {
            plan["lanes"][0]: study.covariance_record(np.eye(2) * scalar**2, np),
            plan["lanes"][1]: study.covariance_record(nominal[name]["covariance"], np),
        }
        common = max(scalar, math.sqrt(covariances[plan["lanes"][1]]["eigenvalues"][-1]))
        observation = study.prepare(helper, field, points, normal, common)
        contexts.append(
            {
                "name": name,
                "normal_from_frozen_observed_primitives": normal_record,
                "scalar_from_capture": scalar,
                "common_sigma": common,
                "observed": study.snapshot(observation),
                "metadata": observation.metadata(),
                "seed_inputs": "saved g, observed ring, normal from observed primitives, common sigma, declared dark polarity only; no truth geometry",
            }
        )
        observation_checks.append(
            study.observation_controls(
                name,
                field,
                points,
                primitives,
                observation,
                common,
                covariances,
                helper,
                core,
                oracle,
                oracle_plan,
                np,
            )
        )
    checks.append({"name": "no-fit-during-actual-observation-controls", "passed": not fit_calls})

    # Routing-only run: force one control exception and replace every inverse fit
    # by a sentinel. This proves no eligible lane is blocked; it proves no actual
    # optimizer continuation and is not substituted for the future live contract.
    original_controls = study.observation_controls
    control_calls = []

    def injected_control(name, *args, **kwargs):
        control_calls.append(name)
        if len(control_calls) == 1:
            raise ValueError("FIRST_CONTROL_PREFLIGHT_SENTINEL")
        return {"name": name, "checks": [], "all_passed": True, "scope": "routing stub"}

    study.observation_controls = injected_control
    with contextlib.redirect_stderr(io.StringIO()):
        routing = study.run_study(copy.deepcopy(plan), core=core, helper=helper)
    checks.append(
        {
            "name": "control-failure-independent-fit-routing",
            "passed": len(routing["rows"]) == 12
            and len(fit_calls) == 10
            and routing["observation_controls"][0].get("status") == "execution_failure"
            and sum(r["status"] == "upstream_ineligible" for r in routing["rows"]) == 2
            and all(
                r["fit_attempted"] for r in routing["rows"] if r["name"] != "minor-directional"
            ),
            "sentinel_fit_calls": len(fit_calls),
            "retained_lanes": len(routing["rows"]),
            "scope": "ten sentinel calls, zero inverse optimizers executed; actual first-fit continuation remains pending",
        }
    )

    @dataclass
    class StubFit:
        best: None = None
        cost: float = 0.0

    study.observation_controls = lambda name, *args, **kwargs: {
        "name": name,
        "checks": [],
        "all_passed": True,
        "scope": "routing stub",
    }
    payload_calls = []

    def nonfinite_fit(*args, **kwargs):
        payload_calls.append(1)
        return StubFit(cost=float("nan") if len(payload_calls) == 1 else 0.0)

    core.fit_circular_segment = nonfinite_fit
    with contextlib.redirect_stderr(io.StringIO()):
        nonfinite = study.run_study(copy.deepcopy(plan), core=core, helper=helper)
    first = nonfinite["rows"][0]
    checks.append(
        {
            "name": "nonfinite-fit-payload-retained-json-safely",
            "passed": len(nonfinite["rows"]) == 12
            and len(payload_calls) == 10
            and first["status"] == "execution_failure"
            and first["failure_stage"] == "strict_row_serialization"
            and first["withheld_non_json_fields"] == ["fit"]
            and "fit" not in first
            and "observed" in first
            and not first["targets_passed"]
            and not first["completion_passed"]
            and sum(r["status"] == "fit_completed" for r in nonfinite["rows"]) == 9
            and bool(json.dumps(nonfinite, allow_nan=False)),
            "retained_lanes": len(nonfinite["rows"]),
            "stub_fit_calls": len(payload_calls),
            "scope": "ten dataclass stubs; first contains NaN; zero inverse optimizers",
        }
    )
    # Simulate a diagnostic error after pass flags have already been assigned.
    # The selective injection is at final row serialization, not in the fitter.
    original_dumps = study.json.dumps
    injected = []

    def after_pass_dumps(value, *args, **kwargs):
        if (
            not injected
            and isinstance(value, dict)
            and value.get("index") == 0
            and value.get("status") == "fit_completed"
            and "fit" in value
        ):
            injected.append(1)
            value["targets_passed"] = True
            value["completion_passed"] = True
            raise ValueError("EXCEPTION_AFTER_PASS_FLAGS_PREFLIGHT_SENTINEL")
        return original_dumps(value, *args, **kwargs)

    core.fit_circular_segment = lambda *args, **kwargs: StubFit()
    study.json.dumps = after_pass_dumps
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            after_pass = study.run_study(copy.deepcopy(plan), core=core, helper=helper)
    finally:
        study.json.dumps = original_dumps
    first = after_pass["rows"][0]
    checks.append(
        {
            "name": "exception-after-pass-resets-flags-and-retains-lanes",
            "passed": len(injected) == 1
            and len(after_pass["rows"]) == 12
            and first["status"] == "execution_failure"
            and first["failure_stage"] == "strict_row_serialization"
            and not first["targets_passed"]
            and not first["completion_passed"]
            and sum(r["status"] == "fit_completed" for r in after_pass["rows"]) == 9
            and bool(json.dumps(after_pass, allow_nan=False)),
            "retained_lanes": len(after_pass["rows"]),
            "scope": "row-serialization exception after injected pass flags; dataclass fit stubs only",
        }
    )
    unsafe_control_calls = []

    def unsafe_control(name, *args, **kwargs):
        unsafe_control_calls.append(name)
        return {"name": name, "checks": [{"value": float("inf")}], "all_passed": True}

    study.observation_controls = unsafe_control
    with contextlib.redirect_stderr(io.StringIO()):
        unsafe_controls = study.run_study(copy.deepcopy(plan), core=core, helper=helper)
    checks.append(
        {
            "name": "nonfinite-control-payload-does-not-abort-report-or-fits",
            "passed": len(unsafe_controls["rows"]) == 12
            and len(unsafe_control_calls) == 5
            and all(
                c.get("status") == "execution_failure" and not c["all_passed"]
                for c in unsafe_controls["observation_controls"]
            )
            and sum(r["status"] == "fit_completed" for r in unsafe_controls["rows"]) == 10
            and bool(json.dumps(unsafe_controls, allow_nan=False)),
            "scope": "nonfinite diagnostic stub, ten dataclass fit stubs; zero inverse optimizers",
        }
    )
    study.observation_controls = original_controls
    core.fit_circular_segment = original_fit
    after = study.source_hashes(plan, manifest)
    after["preflight_runner"] = study.sha(__file__)
    checks.append({"name": "full-source-input-closure-unchanged", "passed": before == after})
    result = {
        "format": "finite-photo-intensity-v2-no-fit-preflight",
        "scope": "Actual observed-only preparation and forward means; no inverse fits. CLI success uses a report stub. Continuation routing uses explicit optimizer sentinels.",
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "contracts": checks,
        "observation_controls": observation_checks,
        "prepared_contexts": contexts,
        "summary": {
            "inverse_optimizers_executed": 0,
            "prepared_cases": len(contexts),
            "retained_cases": len(observation_checks),
            "contract_checks": len(checks),
            "contract_passes": sum(c["passed"] for c in checks),
            "actual_observation_checks": sum(len(c.get("checks", [])) for c in observation_checks),
            "actual_observation_passes": sum(
                sum(r["passed"] for r in c.get("checks", [])) for c in observation_checks
            ),
            "all_passed": all(c["passed"] for c in checks)
            and all(c["all_passed"] for c in observation_checks),
        },
    }
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    with output.open("x") as stream:
        stream.write(encoded)
    print(encoded, end="")
    return 0 if result["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
