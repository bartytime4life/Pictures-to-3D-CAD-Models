"""Independent arithmetic and camera checks for the corner sensitivity box."""

import itertools
from decimal import Decimal, localcontext

import numpy as np
import pytest

from backend.calibration_bounds import _homography_columns, _Interval, inferred_axis_order
from tests.test_sheet_axis_assignment import projected_sheet


def test_outward_interval_arithmetic_encloses_high_precision_endpoint_results():
    # Decimal.from_float retains the exact binary input values. Rounded float
    # arithmetic must enclose the higher-precision answer, including cancellation.
    rng = np.random.default_rng(20261117)
    pairs = [(-1e150, 1e150), (-1e-150, 1e-150), (0.1, 0.3), (-0.3, -0.1)]
    pairs.extend(tuple(sorted(pair)) for pair in rng.normal(0, 100, (40, 2)))
    with localcontext() as context:
        context.prec = 100
        for left, right in zip(pairs, pairs[1:] + pairs[:1], strict=True):
            a, b = _Interval(*left), _Interval(*right)
            operations = [(a + b, lambda x, y: x + y), (a - b, lambda x, y: x - y),
                          (a * b, lambda x, y: x * y)]
            if not b.lo <= 0 <= b.hi:
                operations.append((a / b, lambda x, y: x / y))
            for bound, operation in operations:
                for x, y in itertools.product(left, right):
                    result = operation(Decimal.from_float(x), Decimal.from_float(y))
                    assert Decimal.from_float(bound.lo) <= result <= Decimal.from_float(bound.hi)
            squared = a.square()
            for x in (*left, (left[0] + left[1]) / 2):
                result = Decimal.from_float(x) ** 2
                assert Decimal.from_float(squared.lo) <= result <= Decimal.from_float(squared.hi)


@pytest.mark.parametrize("tilt", [(22, -9, 4), (50, 10, 4), (60, 10, 94)])
def test_homography_intervals_enclose_independent_linear_solves_at_all_box_vertices(tilt):
    found, _, _ = projected_sheet(tilt, distance=792)
    radius = 0.25
    bounds = _homography_columns(found.corners, (2400, 1800), radius)
    unit = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for signs in itertools.product((-1, 1), repeat=8):
        corners = found.corners + radius * np.asarray(signs).reshape(4, 2)
        # Eight independent projection equations solve h33=1; the production
        # interval helper uses the explicit quadrilateral formula instead.
        equations, target = [], []
        for (x, y), (u, v) in zip(unit, corners - [1200, 900], strict=True):
            equations.extend([[x, y, 1, 0, 0, 0, -u * x, -u * y],
                              [0, 0, 0, x, y, 1, -v * x, -v * y]])
            target.extend([u, v])
        solved = np.r_[np.linalg.solve(equations, target), 1].reshape(3, 3)
        for column in range(2):
            for row in range(3):
                assert bounds[column][row].lo <= solved[row, column] <= bounds[column][row].hi


@pytest.mark.parametrize("corners", [
    np.zeros((4, 2)),
    np.full((4, 2), np.nan),
    np.array([[0, 0], [100, 100], [0, 100], [100, 0]]),
])
def test_invalid_or_horizon_crossing_corner_scenario_has_no_inferred_order(corners):
    assert inferred_axis_order(corners, (2400, 1800)) is None
