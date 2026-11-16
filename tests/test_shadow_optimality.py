"""Independent constrained-solve checks; optical adequacy is tested separately."""

from itertools import product

import numpy as np
import pytest

from backend import shadow


def exhaustive_minimum(matrix, rhs, unbounded):
    """Enumerate all faces; use NumPy's general solve, not the production Cholesky."""
    n = len(rhs)
    candidates = []
    for bits in product((False, True), repeat=n - unbounded):
        free = np.r_[np.ones(unbounded, bool), bits].astype(bool)
        x = np.zeros(n)
        if free.any():
            x[free] = np.linalg.solve(matrix[np.ix_(free, free)], rhs[free])
        if np.all(x[unbounded:] >= -1e-12):
            candidates.append((float(x @ matrix @ x / 2 - rhs @ x), x))
    return min(candidates, key=lambda item: item[0])[1]


def test_a_deleted_shadow_node_must_be_allowed_to_return():
    matrix = np.array([[15., 11., -1.], [11., 26., -24.], [-1., -24., 35.]])
    rhs = np.array([5., 4., -1.])
    # The previous one-way deletion returned (1/3, 0, 0). Its gradient at node 2
    # is -1/3: increasing that zero coefficient strictly improves the objective.
    x = shadow._nonnegative_solve(matrix, rhs)
    np.testing.assert_allclose(x, [86 / 269, 5 / 269, 0], atol=1e-14, rtol=0)
    np.testing.assert_allclose(matrix @ x - rhs, [0, 0, 63 / 269], atol=1e-14)


@pytest.mark.parametrize("unbounded", [0, 2, 6])
def test_shadow_solution_matches_every_face_and_kkt_conditions(unbounded):
    rng = np.random.default_rng(20261116 + unbounded)
    for _ in range(60):
        n = unbounded + 5
        a = rng.normal(size=(n + 3, n))
        matrix = a.T @ a + 0.1 * np.eye(n)
        rhs = rng.normal(size=n)
        expected = exhaustive_minimum(matrix, rhs, unbounded)
        x = shadow._nonnegative_solve(matrix, rhs, unbounded)
        np.testing.assert_allclose(x, expected, atol=2e-11, rtol=2e-11)
        gradient = matrix @ x - rhs
        assert np.all(x[unbounded:] >= 0)
        assert np.all(gradient[unbounded:] >= -2e-11)
        np.testing.assert_allclose(gradient[:unbounded], 0, atol=2e-11)
        np.testing.assert_allclose(x[unbounded:] * gradient[unbounded:], 0, atol=2e-11)


def test_shadow_solution_is_invariant_to_coefficient_units_and_intensity_scale():
    rng = np.random.default_rng(27)
    a = rng.normal(size=(30, 11))
    matrix = a.T @ a + np.eye(11)
    rhs = rng.normal(size=11)
    expected = exhaustive_minimum(matrix, rhs, 6)
    units = np.geomspace(1e-6, 1e6, 11)
    for scale in (1e-12, 1., 1e12):
        x = shadow._nonnegative_solve(
            matrix * units[:, None] * units[None, :] * scale,
            rhs * units * scale, 6,
        )
        np.testing.assert_allclose(x * units, expected, atol=1e-11, rtol=1e-11)


def test_shadow_iteration_exhaustion_does_not_return_an_unfinished_solution():
    with pytest.raises(np.linalg.LinAlgError, match="did not converge"):
        shadow._nonnegative_solve(np.eye(3), np.ones(3), max_steps=0)


def test_a_numerical_shadow_failure_retains_the_profile_line(monkeypatch):
    from tests.test_fidelity_math import _shadowed_scene

    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError("planted failure")

    monkeypatch.setattr(shadow, "_nonnegative_solve", fail)
    image, mask, ppm, sigma = _shadowed_scene((1.6, 1.9), 2.2, ppm=3, sigma=2.5)
    light = shadow.fit_paper_light(image, mask, ppm, sigma)
    assert light.info == {"used": False, "reason": "shadow_solve_failed"}
    assert light.sharp is None and light.blurred is None
