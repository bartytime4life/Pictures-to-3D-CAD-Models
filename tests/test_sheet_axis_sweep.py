"""Independent forward-camera sweep of sheet orientation and held-out dimensions.

This checks the geometric assignment with exact and perturbed edge clouds. It does
not model a full camera sensor or establish accuracy on real photographs.
"""

import itertools
import math

import numpy as np

from backend import sheet


def _rotation(axis, degrees):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _project(matrix, points):
    homogeneous = np.column_stack([points, np.ones(len(points))]) @ matrix.T
    return homogeneous[:, :2] / homogeneous[:, 2, None]


def test_camera_sweep_keeps_holdout_dimensions_or_refuses_ambiguous_axes():
    size = (2400, 1800)
    rng = np.random.default_rng(20261116)
    accepted = rejected = 0
    accepted_standard = rejected_without_exif = 0
    failures = []
    dimensions = [(210, 297), (200, 200), (200, 201), (200, 200.1)]
    tilts = [
        (0, 0, 0),
        (22, -9, 4),
        (60, 10, 4),
        (60, 0, 0),
        (0, 60, 0),
        (60, 0.0001, 4),
        (20, -30, 90),
    ]
    cases = itertools.product(
        dimensions, tilts, [500, 1980, 5000], [False, True], [0, 0.05], range(4)
    )
    for dims, tilt, focal, has_exif, noise, cycle in cases:
        width, height = dims
        rotation = (
            _rotation("z", tilt[2]) @ _rotation("x", tilt[0]) @ _rotation("y", tilt[1])
        )
        translation = np.array([0, 0, focal * 0.4]) - rotation @ np.array(
            [width / 2, height / 2, 0]
        )
        intrinsics = np.array(
            [[focal, 0, size[0] / 2], [0, focal, size[1] / 2], [0, 0, 1]]
        )
        truth = intrinsics @ np.column_stack([rotation[:, :2], translation])
        plane = np.array([[0, 0], [width, 0], [width, height], [0, height]])
        corners = _project(truth, plane)
        assert np.all((corners > 0) & (corners < np.array(size)))
        sides = []
        for index in range(4):
            points = plane[index] + np.linspace(0, 1, 60)[:, None] * (
                plane[(index + 1) % 4] - plane[index]
            )
            projected = _project(truth, points)
            sides.append(projected + rng.normal(0, noise, projected.shape))
        sides = sides[cycle:] + sides[:cycle]
        found = sheet.Sheet(np.roll(corners, -cycle, axis=0), sides, 1)
        context = (dims, tilt, focal, has_exif, noise, cycle)
        standard = dims in ((210, 297), (200, 200))
        equivalent = focal * math.hypot(36, 24) / math.hypot(*size) if has_exif else None
        try:
            matrix, assigned, _ = sheet.homography(
                found, 0, size, dims, focal_35mm=equivalent
            )
        except sheet.SheetError:
            rejected += 1
            rejected_without_exif += not has_exif
            # Ordinary and square sheets with the true focal remain identifiable.
            if standard and has_exif:
                failures.append((context, "unexpected rejection with known focal"))
            continue

        accepted += 1
        accepted_standard += standard
        expected_axes = (width, height) if cycle % 2 == 0 else (height, width)
        if tuple(assigned) != expected_axes:
            failures.append((context, "incorrect axis assignment", assigned, expected_axes))
        # These interior points were not used in fitting or selecting the homography.
        holdout = np.array([[50, 60], [150, 60], [150, 130], [50, 130]])
        recovered = _project(np.linalg.inv(matrix), _project(truth, holdout))
        spans = np.linalg.norm(np.roll(recovered, -1, axis=0) - recovered, axis=1)
        error = float(np.max(np.abs(spans - np.array([100, 70, 100, 70]))))
        # A deterministic regression bound for these sampled edges, not uncertainty.
        if error > (0.1 if noise else 1e-4):
            failures.append((context, "held-out dimension error", error))

    assert accepted + rejected == 1344
    assert accepted_standard > 0 and rejected_without_exif > 0
    assert accepted > 0 and rejected > 0
    assert failures == []
