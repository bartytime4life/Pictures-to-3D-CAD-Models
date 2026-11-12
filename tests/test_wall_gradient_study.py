"""Independent convolution and constrained-fit checks for the developer study."""

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts import wall_gradient_study as study


def quadrature_source(t, edge, band, sigma, tail, levels):
    """Integrate explicit piecewise source values; no analytic basis helper."""
    nodes, weights = np.polynomial.legendre.leggauss(100)
    x = np.asarray(t) - edge
    result = levels[0] * np.asarray([0.5 * math.erfc((v + tail) / sigma / math.sqrt(2)) for v in x])
    result += levels[4] * np.asarray([0.5 * math.erfc((tail - v) / sigma / math.sqrt(2)) for v in x])
    intervals = [(-tail, -band, levels[0], levels[1]),
                 (-band, 0, levels[2], levels[2]), (0, tail, levels[3], levels[4])]
    for low, high, start, end in intervals:
        if high == low:
            continue
        q = (high + low) / 2 + (high - low) * nodes / 2
        light = start + (end - start) * (q - low) / (high - low)
        density = np.exp(-0.5 * ((q[None, :] - x[:, None]) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
        result += (density * light * weights).sum(axis=1) * (high - low) / 2
    return result


@pytest.mark.parametrize("band", [0, 0.15, 1.5, 4.0])
@pytest.mark.parametrize("inverted", [False, True])
def test_bounded_source_matches_independently_integrated_segments(band, inverted):
    sigma, tail, edge = 1.3, 15.6, 0.23
    t = np.linspace(-20, 20, 61)
    levels = np.asarray([24., 48., 78., 236., 212.])
    if inverted:
        levels = 255 - levels
    basis = study.source_basis(t, edge, band, sigma, tail)
    assert np.max(np.abs(basis.sum(axis=1) - 1)) < 5e-15
    assert basis.min() > -5e-15 and basis.max() < 1 + 5e-15
    expected = quadrature_source(t, edge, band, sigma, tail, levels)
    assert np.max(np.abs(basis @ levels - expected)) < 3e-11


def test_box_fit_satisfies_independent_convex_optimality_conditions():
    rng = np.random.default_rng(61)
    for columns in [1, 3, 5]:
        design = rng.normal(size=(13, columns))
        observed = design @ np.linspace(-80, 310, columns) + rng.normal(size=13)
        coefficients, _ = study.bounded_projection(design, observed)
        assert np.all((coefficients >= 0) & (coefficients <= 255))
        gradient = design.T @ (design @ coefficients - observed)
        assert np.all(gradient[coefficients == 0] >= -1e-8)
        assert np.all(gradient[coefficients == 255] <= 1e-8)
        free = (coefficients > 0) & (coefficients < 255)
        assert np.max(np.abs(gradient[free]), initial=0) < 1e-8


def test_rank_deficient_box_face_has_an_optimal_representative():
    design = np.asarray([[1., 1., 0.], [0., 0., 1.]])
    coefficients, _ = study.bounded_projection(design, np.asarray([490., -20.]))
    assert coefficients[0] + coefficients[1] == pytest.approx(490)
    assert coefficients[2] == 0


def test_constrained_projection_does_not_clip_an_unconstrained_solution():
    design = np.asarray([[1., 1.], [1., 2.], [1., 3.]])
    observed = design @ [-20., 100.]
    coefficients, _ = study.bounded_projection(design, observed)
    assert coefficients[0] == 0
    assert coefficients[1] == pytest.approx(float(np.arange(1, 4) @ observed) / 14)
    assert coefficients[1] != 100


def test_zero_band_removes_wall_level_but_not_a_contrasted_edge():
    t = np.linspace(-5, 5, 81)
    basis = study.source_basis(t, 0, 0, 1, 12)
    assert np.array_equal(basis[:, 2], np.zeros(len(t)))
    shifted = study.source_basis(t, 0.2, 0, 1, 12)
    levels = [48., 48., 200., 236., 236.]
    assert np.max(np.abs(shifted @ levels - basis @ levels)) > 10


def test_exact_wall_label_ambiguity_with_known_nonzero_band():
    plan = json.loads(study.PLAN.read_text())
    result = study.exact_ambiguity(plan)
    assert result["edge_separation_px"] == 1.5
    assert result["maximum_float_difference"] < 1e-12
    assert result["minimum_worst_case_error_px_for_same_returned_edge"] == 0.75


def test_midpoint_witness_obeys_both_synthetic_error_budgets():
    t = np.arange(-8, 8.001, 0.125)
    observed = study.source_basis(t, 0, 0.15, 1, 12) @ [48., 48., 78., 236., 236.]
    result = study.fit_at_geometry(t, observed, 0.1, 0.15, 1, 12, "joint_gradients")
    assert np.all((result["levels"] >= 0) & (result["levels"] <= 255))
    predicted = study.source_basis(t, 0.1, 0.15, 1, 12) @ result["levels"]
    common = (observed + predicted) / 2
    assert np.max(np.abs(common - observed)) <= result["midpoint_error_bound"]
    assert np.max(np.abs(common - predicted)) <= result["midpoint_error_bound"]
    assert result["midpoint_error_bound"] < 0.01


@pytest.mark.parametrize("arguments", [(0, 1, 0, 12), (0, -1, 1, 12), (0, 12, 1, 12), (math.nan, 1, 1, 12)])
def test_source_refuses_invalid_geometry(arguments):
    with pytest.raises(ValueError):
        study.source_basis([0], *arguments)


def small_plan():
    plan = copy.deepcopy(json.loads(study.PLAN.read_text()))
    plan["sigmas_px"] = [1.65]
    plan["conditions"] = [plan["conditions"][0]]
    plan["contrast_inversions"] = [False]
    plan["direct_lane"].update(band_width_sigmas=[1.5], offsets_sigmas=[0.0, 0.1])
    plan["image_lane"].update(band_width_sigmas=[1.5], normal_angles_degrees=[37.], normal_phases_px=[0.61])
    return plan


def test_small_actual_image_lane_records_all_treatments():
    rows, error = study.image_study(small_plan())
    assert len(rows) == 4
    assert all(r["error"] is None for r in rows)
    assert error < 1e-6
    fixed = [r for r in rows if r["method"] == "true_fixed_wall_tone"]
    assert all(abs(r["offset_sigmas"]) < 0.04 for r in fixed)


def test_cli_writes_complete_source_bound_outputs_and_refuses_overwrite(tmp_path, monkeypatch):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(small_plan()))
    monkeypatch.setattr(study, "PLAN", path)
    output = tmp_path / "run"
    assert study.main(["--output", str(output)]) == 0
    results = json.loads((output / "results.json").read_text())
    assert results["direct_world_scenes"] == 1 and results["direct_rows"] == 4
    assert results["image_world_scenes"] == 1 and results["image_rows"] == 4
    assert results["physical_qualification"] is False
    assert set(results["artifact_sha256"]) == {"geometry-fits.csv", "image-fits.csv"}
    previous = (output / "results.json").read_bytes()
    with pytest.raises(SystemExit, match="2"):
        study.main(["--output", str(output)])
    assert (output / "results.json").read_bytes() == previous


def test_withheld_production_profiles_remain_unknown_without_execution_failures(tmp_path, monkeypatch):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(small_plan()))
    monkeypatch.setattr(study, "PLAN", path)

    def unresolved(image, points, *args, **kwargs):
        return points.copy(), np.full(len(points), np.nan), np.full(len(points), np.inf)

    monkeypatch.setattr(study.edges, "two_step_refine", unresolved)
    output = tmp_path / "run"
    assert study.main(["--output", str(output)]) == 0
    result = json.loads((output / "results.json").read_text())
    assert result["version"] == 2
    assert all(group["failed"] == 0 and group["resolved"] == 0 and group["unresolved"] == 1
               and group["maximum_absolute_offset_px"] is None for group in result["image_summary"])
    audit = tmp_path / "audit.json"
    script = Path(study.ROOT) / "studies/verification/wall-gradient-audit.py"
    subprocess.run([sys.executable, str(script), "--run", str(output), "--output", str(audit)], check=True)
    assert json.loads(audit.read_text())["unresolved_image_rows"] == 4
