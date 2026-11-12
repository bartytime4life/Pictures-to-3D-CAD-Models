"""Source-bound synthetic control accounting and CLI preservation contracts."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts import postblur_operator_study, profile_noise_study


def test_density_and_repeat_controls_do_not_create_independent_noise_information():
    plan = json.loads(profile_noise_study.PLAN.read_text())
    result = profile_noise_study.run(plan)
    rows = result["cases"]
    assert len(rows) == 7
    assert {r["retained_rank"] for r in rows} == {16}
    assert len({r["source_pixels_sha256"] for r in rows}) == 1
    assert np.ptp([r["gls_local_information"] for r in rows]) < 2e-10
    assert np.ptp([r["stable_comparison_cost"] for r in rows]) < 1e-10
    for row in rows:
        assert row["profile_comparison"]["within_retained_support_tolerance"]
        assert abs(row["gls_gaussian_trial_sd_px"] / row["gls_predicted_local_sd_px"] - 1) < .03
        assert abs(row["diagonal_gaussian_trial_sd_px"] / row["diagonal_actual_local_sd_px"] - 1) < .03
    dense = [r for r in rows if r["label"] == "density"]
    assert [r["samples"] for r in dense] == [25, 49, 97, 193]
    assert dense[-1]["diagonal_predicted_local_sd_px"] < dense[0]["diagonal_predicted_local_sd_px"] / 2
    assert dense[-1]["diagonal_actual_local_sd_px"] > 4 * dense[-1]["diagonal_predicted_local_sd_px"]
    alias = result["global_alias"]
    assert alias["separation_px"] > 3
    assert alias["maximum_profile_difference"] < 1e-12
    assert all(0 < r["conditional_local_sd_px"] < .05 for r in alias["interpretations"])
    assert not result["outside_support_counterexample"]["within_retained_support_tolerance"]
    assert [r["information"] for r in result["changed_rowspace_control"]] == [0., 1.]
    assert [r["rank"] for r in result["numerical_truncation_control"]] == [2, 1]


def test_composed_known_postblur_retains_aliases_and_float32_discrepancy():
    result = postblur_operator_study.run()
    assert len(result["cases"]) == 12
    assert result["kernel"]["actual_impulse_maximum_error"] < 1e-15
    for row in result["cases"]:
        composed = row["models"]["composed_gaussian_keys"]
        final_only = row["models"]["final_only_moment_sigma"]
        assert final_only["truth_prediction_maximum"] > .002
        assert composed["truth_prediction_maximum"] < (5e-13 if row["dtype"] == "float64" else 3e-5)
        if row["one_step_alias"]:
            assert composed["finite_search"]["single_step_alias_detected"]
            assert not final_only["finite_search"]["single_step_alias_detected"]
        else:
            assert abs(composed["finite_search"]["best"]["edge"] - row["true_edge_px"]) < 1e-6


@pytest.mark.parametrize("script", ["profile_noise_study.py", "postblur_operator_study.py"])
def test_cli_requires_explicit_new_output_and_preserves_existing_file(tmp_path, script):
    runner = Path(__file__).resolve().parents[1] / "scripts" / script
    for args, expected in [([], 2), (["--help"], 0)]:
        process = subprocess.run([sys.executable, str(runner), *args], capture_output=True, check=False)
        assert process.returncode == expected
    existing = tmp_path / "result.json"
    existing.write_bytes(b"preserve this exact file\n")
    process = subprocess.run([sys.executable, str(runner), "--output", str(existing)], capture_output=True, check=False)
    assert process.returncode == 2
    assert existing.read_bytes() == b"preserve this exact file\n"
