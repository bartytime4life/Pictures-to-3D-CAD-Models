"""Complete control accounting, measured stage decomposition and output contracts."""

import itertools
import json
import subprocess
import sys
from pathlib import Path

from scripts import warp_observation_study as study


def test_all_declared_maps_fields_scales_and_profiles_remain_in_results():
    plan = json.loads(study.PLAN.read_text())
    result = study.run(plan)
    expected = set(itertools.product([m["name"] for m in plan["maps"]], plan["radial_k1"],
                                     plan["pixels_per_mm"], plan["fields"], [p["name"] for p in plan["profiles"]]))
    actual = [(r["map"], r["k1"], r["ppm"], r["field"], r["profile"]) for r in result["cases"]]
    assert len(actual) == len(set(actual)) == len(expected) == 324
    assert set(actual) == expected
    assert result["summary"]["distinct_source_arrays"] == 6
    assert result["summary"]["processed_chains"] == 108
    assert result["runtime_gaussian_impulse_maximum_error"] < 1e-15
    for row in result["cases"]:
        assert row["float64_composition_maximum_error"] < 1e-12
        assert row["actual_float32_maximum_error"] < 5e-5
        assert row["measured_stage_delta_reconstruction_error"] < 1e-12
        assert row["envelope_violation_count"] == 0
        assert row["profile_samples"] == 49
        assert row["partition_maximum_error"] < 1e-14
        assert row["raw_pixels"] <= 2048 and row["matrix_cells"] <= 500_000
        assert -.00000000000001 < row["conditional_adjacent_correlation_minimum"] <= 1 + 1e-14
        assert row["conditional_adjacent_correlation_maximum"] <= 1 + 1e-14


def test_study_cli_requires_new_output_and_preserves_existing_file(tmp_path):
    runner = Path(__file__).resolve().parents[1] / "scripts/warp_observation_study.py"
    for args, expected in [([], 2), (["--help"], 0)]:
        process = subprocess.run([sys.executable, str(runner), *args], capture_output=True, check=False)
        assert process.returncode == expected
    existing = tmp_path / "result.json"
    existing.write_bytes(b"keep the original receipt\n")
    process = subprocess.run([sys.executable, str(runner), "--output", str(existing)], capture_output=True, check=False)
    assert process.returncode == 2
    assert existing.read_bytes() == b"keep the original receipt\n"
