"""Metric sheet-axis assignment under perspective, including ambiguous cameras.

Exact projected edge clouds isolate geometry from image processing. The rendered
regression also runs the real image-to-profile path against independently known
dimensions; these synthetic checks are not physical camera calibration.
"""

import math

import cv2
import numpy as np
import pytest

from backend import sheet, tracing
from tests import synthetic as S


def projected_sheet(tilt, *, sheet_mm=(210.0, 297.0), size=(2400, 1800), roll=0, focal=None, distance=440.0):
    focal = 1980.0 * size[0] / 2400 if focal is None else focal
    k = np.array([[focal, 0, size[0] / 2], [0, focal, size[1] / 2], [0, 0, 1.0]])
    rotation = S._rot("z", tilt[2]) @ S._rot("x", tilt[0]) @ S._rot("y", tilt[1])
    translation = np.array([0, 0, distance]) - rotation @ np.array([*np.asarray(sheet_mm) / 2, 0])
    matrix = k @ np.column_stack([rotation[:, 0], rotation[:, 1], translation])
    matrix /= matrix[2, 2]
    w, h = sheet_mm
    plane = np.roll(np.array([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]), -roll, axis=0)
    corners = sheet.project(matrix, plane)
    fraction = np.linspace(0.08, 0.92, 37)[:, None]
    sides = [sheet.project(matrix, (1 - fraction) * plane[i] + fraction * plane[(i + 1) % 4]) for i in range(4)]
    return sheet.Sheet(corners, sides, 1), matrix, focal


def recovered_lengths(matrix, truth):
    rectangle = np.array([[55.0, 110.0], [155.0, 110.0], [155.0, 180.0], [55.0, 180.0]])
    recovered = sheet.project(np.linalg.inv(matrix), sheet.project(truth, rectangle))
    return np.linalg.norm(np.roll(recovered, -1, axis=0) - recovered, axis=1)


@pytest.mark.parametrize("tilt", [(0, 0, 4), (22, -9, 4), (50, 10, 4), (50, 0, 4), (10, 60, 94)])
@pytest.mark.parametrize("roll", range(4))
def test_projected_sheet_preserves_dimensions_when_foreshortening_reverses_appearance(tilt, roll):
    found, truth, _ = projected_sheet(tilt, roll=roll)
    diagnostic = {}
    matrix, _, _ = sheet.homography(found, 0.0, (2400, 1800), (210, 297), diagnostics=diagnostic)
    np.testing.assert_allclose(recovered_lengths(matrix, truth), [100, 70, 100, 70], atol=3e-5, rtol=0)
    if tilt in ((50, 10, 4), (50, 0, 4)):
        assert diagnostic["axis_corrected"]


@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
def test_axis_evidence_does_not_depend_on_image_resolution_or_homography_scale(scale):
    size = (round(2400 * scale), round(1800 * scale))
    for tilt, source in [((0, 0, 4), "focal-range"), ((50, 0, 4), "aspect-feasibility"), ((50, 10, 4), "sheet")]:
        _, truth, _ = projected_sheet(tilt, size=size)
        unit = truth @ np.diag([210.0, 297.0, 1.0])
        for multiplier in (-7.0, 0.03, 1.0, 1e4):
            assert sheet._sheet_axis_order(unit * multiplier, size, (210, 297)) == (False, source)


@pytest.mark.parametrize("tilt", [(70, 0, 4), (0, 60, 4)])
def test_two_physically_possible_sheet_orientations_are_refused_without_metadata(tilt):
    found, _, _ = projected_sheet(tilt)
    with pytest.raises(sheet.SheetError, match="does not identify which reference-sheet edge"):
        sheet.homography(found, 0.0, (2400, 1800), (210, 297))


def test_exif_resolves_an_otherwise_ambiguous_sheet_without_assuming_a_phone_lens():
    found, truth, focal = projected_sheet((70, 0, 4))
    equivalent = focal * math.hypot(36, 24) / math.hypot(2400, 1800)
    diagnostic = {}
    matrix, _, _ = sheet.homography(
        found, 0.0, (2400, 1800), (210, 297), focal_35mm=equivalent, diagnostics=diagnostic
    )
    assert diagnostic["axis_source"] == "exif"
    np.testing.assert_allclose(recovered_lengths(matrix, truth), [100, 70, 100, 70], atol=3e-5, rtol=0)


def test_conflicting_metadata_and_sheet_focal_do_not_silently_choose_an_axis():
    found, _, _ = projected_sheet((50, 10, 4))
    conflicting = 500 * math.hypot(36, 24) / math.hypot(2400, 1800)
    with pytest.raises(sheet.SheetError, match="metadata and the reference-sheet perspective disagree"):
        sheet.homography(found, 0.0, (2400, 1800), (210, 297), focal_35mm=conflicting)


def test_square_sheet_has_no_axis_assignment_ambiguity():
    found, truth, _ = projected_sheet((70, 0, 94), sheet_mm=(220.0, 220.0))
    diagnostic = {}
    matrix, plane, _ = sheet.homography(found, 0.0, (2400, 1800), (220, 220), diagnostics=diagnostic)
    assert plane == (220, 220) and diagnostic == {"axis_source": "square", "axis_corrected": False}
    np.testing.assert_allclose(recovered_lengths(matrix, truth), [100, 70, 100, 70], atol=3e-5, rtol=0)


@pytest.mark.parametrize("dimensions", [(200.0, 201.0), (200.0, 200.1)])
@pytest.mark.parametrize("metadata", [False, True])
def test_near_square_tilted_sheet_is_unsupported_while_frontal_order_stays_supported(dimensions, metadata):
    tilted, _, focal = projected_sheet((60, 10, 4), sheet_mm=dimensions)
    equivalent = focal * math.hypot(36, 24) / math.hypot(2400, 1800) if metadata else None
    with pytest.raises(sheet.SheetError, match="sides are too close in length"):
        sheet.homography(tilted, 0.0, (2400, 1800), dimensions, focal_35mm=equivalent)
    frontal, truth, _ = projected_sheet((0, 0, 4), sheet_mm=dimensions)
    diagnostic = {}
    matrix, _, _ = sheet.homography(frontal, 0.0, (2400, 1800), dimensions, diagnostics=diagnostic)
    assert diagnostic["axis_source"] == "focal-range"
    np.testing.assert_allclose(recovered_lengths(matrix, truth), [100, 70, 100, 70], atol=3e-5, rtol=0)


def test_consistent_metadata_takes_priority_over_noise_sensitive_single_photo_focal():
    dimensions = (210.0, 297.0)
    found, truth, focal = projected_sheet((60, 10, 4), sheet_mm=dimensions, focal=5000, distance=2000)
    rng = np.random.default_rng(20261116)
    found.sides = [side + rng.normal(0, 0.05, side.shape) for side in found.sides]
    equivalent = focal * math.hypot(36, 24) / math.hypot(2400, 1800)
    diagnostic = {}
    matrix, plane, _ = sheet.homography(
        found, 0.0, (2400, 1800), dimensions, focal_35mm=equivalent, diagnostics=diagnostic
    )
    assert diagnostic["axis_source"] == "exif" and plane == dimensions
    np.testing.assert_allclose(recovered_lengths(matrix, truth), [100, 70, 100, 70], atol=0.03, rtol=0)


def test_wrong_sheet_proportions_are_not_forced_to_pass_the_independent_check():
    found, _, focal = projected_sheet((0, 0, 4))
    matrix, _, _ = sheet.homography(found, 0.0, (2400, 1800), (215.9, 279.4))
    expected = (210 / 297) / (215.9 / 279.4)
    assert sheet.aspect_ratio_check(matrix, (2400, 1800), focal) == pytest.approx(expected, abs=1e-6)
    assert abs(expected - 1) > 0.08


@pytest.mark.parametrize("tilt,focal,seed,dimensions", [
    ((75, 0.1, 4), 5000, 25, (210, 297)),
    ((70, 0.1, 4), 5000, 98, (210, 297)),
    ((60, 0.1, 4), 1980, 1, (200, 204)),
])
@pytest.mark.parametrize("cycle", range(4))
@pytest.mark.parametrize("metadata", [False, True])
def test_unstable_inferred_focal_cannot_swap_axes_or_veto_original_metadata(
    tilt, focal, seed, dimensions, cycle, metadata
):
    """A nonzero orthogonality constraint can be dominated by subpixel error.

    The first case formerly accepted 141.436 x 49.493 for a 100 x 70 rectangle,
    while the separate sheet-proportion check differed by only 0.3%.
    """
    found, truth, _ = projected_sheet(
        tilt, sheet_mm=dimensions, focal=focal, distance=focal * 0.4
    )
    rng = np.random.default_rng(seed)
    found.sides = [side + rng.normal(0, 0.05, side.shape) for side in found.sides]
    found.sides = found.sides[cycle:] + found.sides[:cycle]
    found.corners = np.roll(found.corners, -cycle, axis=0)
    if not metadata:
        with pytest.raises(sheet.SheetError, match="does not identify which reference-sheet edge"):
            sheet.homography(found, 0.0, (2400, 1800), dimensions)
        return
    equivalent = focal * math.hypot(36, 24) / math.hypot(2400, 1800)
    diagnostic = {}
    matrix, assigned, _ = sheet.homography(
        found, 0.0, (2400, 1800), dimensions, focal_35mm=equivalent, diagnostics=diagnostic
    )
    assert diagnostic["axis_source"] == "exif"
    assert assigned == (dimensions if cycle % 2 == 0 else dimensions[::-1])
    np.testing.assert_allclose(recovered_lengths(matrix, truth), [100, 70, 100, 70], atol=0.03, rtol=0)


def test_rendered_foreshortened_photo_recovers_the_plate_dimensions():
    """The old apparent-length assignment made the 120 x 70 plate about 169 x 50 mm."""
    data, _ = S.render(tilt=(50.0, 10.0, 4.0), shadow=0.0, gradient=0.0, k1=0.0)
    result = tracing.trace_image(data, reference="a4")
    profile = result["profile"]
    points = np.asarray(profile["outer"]) * profile["reference"]["mm_per_px"]
    _, lengths, _ = cv2.minAreaRect(points.astype(np.float32))
    np.testing.assert_allclose(sorted(lengths), [70.0, 120.0], atol=0.15, rtol=0)
    assert max(S.feature_errors(profile).values()) < 0.15
