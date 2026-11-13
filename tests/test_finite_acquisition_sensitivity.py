"""Check the complete smooth geometry-to-intensity derivative, not round8."""

import math

import numpy as np
import pytest

from backend.finite_acquisition_linear import acquisition_linear
from backend.finite_aperture import segment_cell_coverage
from backend.finite_aperture_sensitivity import segment_cell_sensitivity


def geometry():
    return {
        "centre": (0.13, 0.17),
        "radius": 1.1,
        "fraction": 0.2,
        "normal": (0.6, 0.8),
        "shape": (7, 7),
        "origin": (-1.5, -1.5),
        "pitch": 0.5,
    }


def acquisition():
    return {
        "optical_kernel": [[0.0, 0.125, 0.0], [0.25, 0.0, 0.0], [0.0, 0.0, 0.625 + 2**-25]],
        "output_shape": (5, 6),
        "output_to_source_index": [[0.9, 0.1, 0.3], [-0.1, 0.85, 0.5]],
        "post_kernel": [[0.0, 0.0, 0.5], [0.0, 0.25, 0.0], [0.25, 0.0, 0.0]],
        "queries": [[0, 0], [5, 4], [2, 3], [1, 1], [3, 2]],
    }


@pytest.mark.parametrize("column", range(5))
def test_combined_cell_flux_and_signed_linear_stages_against_mean_differences(column):
    options = geometry()
    sensitivity = segment_cell_sensitivity(**options)
    assert set(sensitivity.statuses) == {"resolved"}
    fields = np.dstack((sensitivity.coverage, sensitivity.jacobian))
    propagated = acquisition_linear(fields, **acquisition())
    background, material = 240.0, 30.0
    scale = options["pitch"] if column < 3 else 1.0
    step = 2e-5
    means = []
    for sign in (-1, 1):
        changed = options.copy()
        delta = sign * step * scale
        if column < 2:
            centre = list(changed["centre"])
            centre[column] += delta
            changed["centre"] = tuple(centre)
        elif column == 2:
            changed["radius"] += delta
        elif column == 3:
            changed["fraction"] += delta
        else:
            nx, ny = changed["normal"]
            changed["normal"] = (
                nx * math.cos(delta) - ny * math.sin(delta),
                nx * math.sin(delta) + ny * math.cos(delta),
            )
        coverage = segment_cell_coverage(**changed)
        mean = acquisition_linear(
            background * (1 - coverage) + material * coverage, **acquisition()
        )
        assert set(mean.statuses) == {"resolved"}
        means.append(mean.query_values[:, 0])
    difference = (means[1] - means[0]) / (2 * step)
    predicted = (material - background) * propagated.query_values[:, column + 1] * scale
    np.testing.assert_allclose(predicted, difference, rtol=2e-6, atol=2e-5)


def test_zero_contrast_carries_no_geometry_signal_even_with_nonunit_constant_response():
    sensitivity = segment_cell_sensitivity(**geometry())
    propagated = acquisition_linear(
        np.dstack((sensitivity.coverage, sensitivity.jacobian)), **acquisition()
    )
    equal_level = 123.0
    brightness_columns = np.column_stack(
        (
            propagated.constant_response - propagated.query_values[:, 0],
            propagated.query_values[:, 0],
        )
    )
    mean = brightness_columns @ [equal_level, equal_level]
    np.testing.assert_allclose(mean, equal_level * propagated.constant_response, rtol=0, atol=5e-14)
    np.testing.assert_array_equal(
        (equal_level - equal_level) * propagated.query_values[:, 1:], np.zeros((5, 5))
    )
    assert np.all(propagated.constant_response > 1)


def test_undefined_source_cell_derivatives_cannot_silently_enter_the_linear_operator():
    result = segment_cell_sensitivity(
        centre=(0, 0), radius=2, fraction=0, normal=(1, 0), shape=(2, 2), origin=(0.5, 0.5), pitch=1
    )
    assert "nondifferentiable" in result.statuses
    assert np.isnan(result.jacobian).any()
    with pytest.raises(ValueError, match="finite"):
        acquisition_linear(
            np.dstack((result.coverage, result.jacobian)),
            **dict(acquisition(), output_shape=(1, 1), queries=[[0, 0]]),
        )
