"""Actual sampled Gaussian steps: angular bins do not establish covariance rank."""

import math

import numpy as np
import pytest

from backend import edges


def independent_steps(normals, *, reverse_contrast=False):
    """Separate straight-edge patches specified by erfc, with known diag(4,9).

    No production blur renderer, width stub, or covariance fit generates the input.
    This tests the measurement function, not a whole photograph or camera accuracy.
    """
    image = np.empty((256, 256 * len(normals)), np.float32)
    points, repeated = [], []
    covariance = np.diag([4.0, 9.0])
    erfc = np.frompyfunc(math.erfc, 1, 1)
    for k, normal in enumerate(normals):
        normal = np.asarray(normal, float)
        anchor = np.array([128 + 256 * k + 0.3, 128 - 0.2])
        yy, xx = np.mgrid[:256, 256 * k : 256 * (k + 1)]
        sigma = math.sqrt(float(normal @ covariance @ normal))
        z = ((xx + 0.5 - anchor[0]) * normal[0] + (yy + 0.5 - anchor[1]) * normal[1]) / sigma
        probability = 0.5 * erfc(-z / math.sqrt(2)).astype(float)
        image[:, 256 * k : 256 * (k + 1)] = (
            230 - 200 * probability if reverse_contrast else 30 + 200 * probability
        )
        tangent = np.array([-normal[1], normal[0]])
        points.extend(anchor + t * tangent for t in np.linspace(-38, 38, 20))
        repeated.extend([normal] * 20)
    return image, np.asarray(points), np.asarray(repeated), covariance


@pytest.mark.parametrize("reverse_contrast", [False, True])
def test_opposite_normals_in_three_bins_still_have_only_two_independent_directions(
    reverse_contrast,
):
    normal = np.array([math.cos(math.pi / 6), math.sin(math.pi / 6)])
    image, points, normals, _ = independent_steps(
        [normal, -normal, [0, 1]], reverse_contrast=reverse_contrast
    )
    angles = np.degrees(np.arctan2(normals[:, 1], normals[:, 0])) % 180
    direction = np.floor(angles / 30).astype(int) % 6
    # Opposite copies straddle a bin boundary through floating angle reduction.
    counts = np.bincount(direction, minlength=6)
    assert (counts >= edges.MIN_PER_BIN).sum() == 3
    x, y = normals.T
    design = np.column_stack([x * x, 2 * x * y, y * y])
    assert np.linalg.matrix_rank(design) == 2
    widths = edges._edge_widths(image, points, normals, 15, single_step=True)
    assert np.isfinite(widths).sum() == 60
    assert edges.edge_covariance(image, points, normals, 2.5, min_ratio=1.15) is None


@pytest.mark.parametrize("rotation", [0.17, 0.7])
def test_rotating_or_reversing_two_directions_does_not_identify_cross_covariance(rotation):
    a = np.array([math.cos(rotation), math.sin(rotation)])
    b = np.array([-a[1], a[0]])
    image, points, normals, _ = independent_steps([a, -a, b, -b])
    assert edges.edge_covariance(image, points, normals, 2.5) is None


@pytest.mark.parametrize("reverse_contrast", [False, True])
def test_three_genuine_directions_keep_the_covariance_measurement(reverse_contrast):
    angles = [math.pi / 6, math.pi / 2, 5 * math.pi / 6]
    supplied = [[math.cos(a), math.sin(a)] for a in angles]
    image, points, normals, truth = independent_steps(supplied, reverse_contrast=reverse_contrast)
    found = edges.edge_covariance(image, points, normals, 2.5, min_ratio=1.15)
    assert found is not None
    np.testing.assert_allclose(found, truth, atol=0.06, rtol=0)
    assert np.linalg.eigvalsh(found).min() > 0
