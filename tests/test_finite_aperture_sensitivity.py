"""Independent smooth-area Jacobian checks; no rounded acquisition derivative."""

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

from backend.finite_aperture_sensitivity import segment_cell_sensitivity

_PATH = Path(__file__).resolve().parents[1] / "studies/verification/finite-cell-sensitivity-v1.py"
_SPEC = importlib.util.spec_from_file_location("independent_cell_sensitivity_controls", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
oracle = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(oracle)


@pytest.mark.parametrize("case", oracle.regular_cases(), ids=lambda case: case["name"])
def test_regular_cells_against_positive_area_steps_and_independent_flux(case):
    result = segment_cell_sensitivity(
        **oracle.options(case), **({"max_work": case["max_work"]} if "max_work" in case else {})
    )
    assert result.statuses == ("resolved",)
    reference = oracle.reference_checks(case, result.jacobian[0, 0])
    assert reference["passed"], reference


@pytest.mark.parametrize("case", oracle.grid_cases(), ids=lambda case: case["name"])
def test_complete_grid_integrates_the_shape_derivative(case):
    result = segment_cell_sensitivity(**oracle.options(case))
    assert set(result.statuses) == {"resolved"}
    expected_area, expected = oracle.full_grid_expectation(case)
    cell_area = case["pitch"] ** 2
    assert math.fsum(map(float, result.coverage.flat)) * cell_area == pytest.approx(
        expected_area, abs=2e-8
    )
    total = [math.fsum(map(float, result.jacobian[..., k].flat)) * cell_area for k in range(5)]
    np.testing.assert_allclose(total, expected, atol=2e-8, rtol=2e-8)


@pytest.mark.parametrize("index", range(4))
def test_complement_subdivision_and_coordinate_frames(index):
    case = oracle.grid_cases()[index]
    baseline = segment_cell_sensitivity(**oracle.options(case))
    assert set(baseline.statuses) == {"resolved"}
    checks = oracle.invariant_checks(case, baseline, segment_cell_sensitivity)
    assert checks["passed"], checks


@pytest.mark.parametrize("case", oracle.special_cases(), ids=lambda case: case["name"])
def test_contacts_endpoints_and_multiple_spans_are_explicit(case):
    result = segment_cell_sensitivity(
        **oracle.options(case), **({"max_work": case["max_work"]} if "max_work" in case else {})
    )
    record = oracle.candidate_record(result, case)
    assert oracle.special_pass(case, record), record
    if case["expected"] == "resolved_with_boundary":
        reference = oracle.reference_checks(case, result.jacobian[0, 0])
        assert reference["passed"], reference
    if case["name"] == "large-world-small-cell" and result.statuses == ("resolved",):
        expected = (
            np.asarray(
                oracle.boundary_quadrature(
                    oracle.cell_bounds(case),
                    centre=case["centre"],
                    radius=case["radius"],
                    fraction=case["fraction"],
                    stored_normal=oracle.canonical_normal(case["normal"]),
                    order=64,
                )
            )
            / case["pitch"] ** 2
        )
        scales = np.array([case["pitch"]] * 3 + [1, 1])
        np.testing.assert_allclose(
            result.jacobian[0, 0] * scales, expected * scales, atol=2e-9, rtol=2e-9
        )


def test_budget_withholds_the_whole_grid_before_cell_work():
    case = {**oracle.grid_cases()[0], "shape": (2, 2)}
    result = segment_cell_sensitivity(**oracle.options(case), max_work=3)
    assert result.required_work == 4 and result.performed_work == 0
    assert result.statuses == ("work_limit",) * 4
    assert np.isnan(result.coverage).all()
    assert np.isnan(result.jacobian).all()
    assert np.isnan(result.estimated_absolute_error).all()


def test_unknowns_cannot_be_mistaken_for_zero_sensitivity():
    case = oracle.special_cases()[0]
    result = segment_cell_sensitivity(**oracle.options(case))
    assert result.statuses == ("nondifferentiable",)
    assert np.isfinite(result.coverage).all()
    assert np.isnan(result.jacobian).all()
    assert np.isnan(result.estimated_absolute_error).all()


def test_results_are_immutable_and_binding_includes_requested_geometry():
    case = oracle.regular_cases()[0]
    result = segment_cell_sensitivity(**oracle.options(case))
    for array in (result.coverage, result.jacobian, result.estimated_absolute_error):
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array.setflags(write=True)
    changed = segment_cell_sensitivity(
        **{**oracle.options(case), "fraction": case["fraction"] + 0.01}
    )
    assert result.input_sha256 != changed.input_sha256
    assert result.error_estimate_is_certified is False
    assert tuple(result.parameter_order) == oracle.ORDER


@pytest.mark.parametrize(
    "changes",
    [
        {"normal": (2, 0)},
        {"fraction": 1.01},
        {"radius": True},
        {"shape": (257, 256)},
        {"pitch": 0},
        {"max_work": True},
    ],
)
def test_invalid_or_excessive_requests_are_refused(changes):
    case = oracle.options(oracle.regular_cases()[0])
    case.update(changes)
    with pytest.raises(ValueError):
        segment_cell_sensitivity(**case)
