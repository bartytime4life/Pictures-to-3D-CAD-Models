"""Optimizer-contract controls; synthetic residuals do not qualify the optical model."""

import math

import numpy as np
import pytest

from backend import fitting


def fit_residual(monkeypatch, residual, *, radius=10.0):
    """Give the real radius optimizer an explicit objective and unit spatial weights."""
    points = np.array([[0.0, 0.0], [0.0, 1.0]])
    calls = []

    def level(at, centre, r, start, sweep, sigma, *, covariance):
        at = np.asarray(at)
        calls.append(r)
        # The initial spatial-gradient probes have prescribed unit x derivative.
        # All optimizer/uncertainty probes use the unchanged source points.
        delta = at - points
        if np.any(delta):
            return 0.5 + delta[:, 0]
        return 0.5 + np.asarray(residual(r), dtype=float)

    monkeypatch.setattr(fitting, "corner_level", level)
    result = fitting._exact_fillet(
        points,
        (([0.0, 0.0], np.array([0.0, 1.0])), ([0.0, 0.0], np.array([1.0, 0.0]))),
        np.array([1.0, 1.0]),
        (np.array([1.0, 0.0]), np.array([0.0, 1.0])),
        radius,
        1.0,
        0.01,
        1.0,
        covariance=np.eye(2),
    )
    return result, calls


def test_small_unhalved_proposal_retains_current_radius_without_an_uphill_trial(monkeypatch):
    # SSE = d² + (.1 + .005d²)² has its strict minimum at d=0. A forward
    # difference nevertheless proposes a small negative radius increment.
    def residual(r):
        d = r - 10.0
        return [d, 0.1 + 0.005 * d * d]

    h = 0.001
    f = np.asarray(residual(10.0))
    jac = (np.asarray(residual(10.0 + h)) - f) / h
    proposed = -float(jac @ f) / float(jac @ jac)
    assert 0 < abs(proposed) < 1e-6 * 10
    assert np.linalg.norm(residual(10.0 + proposed)) > np.linalg.norm(f)
    result, calls = fit_residual(monkeypatch, residual)
    assert result is not None and result[0] == 10.0
    # Radius zero is the later sharp-corner comparison, not a descent proposal.
    assert not any(0 < radius < 10 for radius in calls)


def test_backtracking_a_large_proposal_into_a_small_move_is_not_convergence(monkeypatch):
    # At d=0 the forward-difference proposal is about -.1px, while very small
    # damped movements round to equal cost. This is not a small GN mapping.
    def residual(r):
        return [1.0 + (r - 10.0) ** 6 / 1e-16, 0.0]

    h = 0.001
    f = np.asarray(residual(10.0))
    jac = (np.asarray(residual(10.0 + h)) - f) / h
    proposed = -float(jac @ f) / float(jac @ jac)
    assert abs(proposed) > 0.09
    result, calls = fit_residual(monkeypatch, residual)
    assert result is None
    # More than one iteration was attempted, rather than accepting the first
    # line-search movement that happened to be smaller than the stop threshold.
    assert len(calls) > 30


def test_no_descent_for_a_large_proposal_remains_unresolved(monkeypatch):
    result, _ = fit_residual(monkeypatch, lambda r: [1.0 + (r - 10.0) ** 2, 0.0])
    assert result is None


def test_finite_projected_zero_step_at_the_sharp_boundary_is_allowed(monkeypatch):
    result, _ = fit_residual(monkeypatch, lambda r: [r + 1.0, r + 1.0], radius=0.0)
    assert result is not None and result[0] == 0.0
    assert all(math.isfinite(value) for value in result[:4])


@pytest.mark.parametrize("sign", [-1, 1])
def test_unrepresentable_residual_arithmetic_cannot_be_projected_into_convergence(
    monkeypatch, sign
):
    result, _ = fit_residual(
        monkeypatch,
        lambda r: [sign * 1e200 * (1 + r), sign * 1e200],
        radius=0.0,
    )
    assert result is None
