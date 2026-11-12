"""Coverage transport at the real sheet-trace/fitter boundary, not image accuracy."""

import numpy as np
import pytest

from backend import edges, fitting, reference, sheet, tone


@pytest.mark.parametrize("sigma", [1.0, 0.0], ids=["refined-walls", "unmeasured-blur"])
def test_support_uses_final_camera_once_and_final_refined_pairs(monkeypatch, sigma):
    """A hole-derived pose replaces the assumed pose before either contour moves.

    Sheet detection and subpixel measurements are explicit fixtures. The actual
    trace_on_sheet and _refine_walls control flow runs; wall-profile fitting supplies
    a known displacement. Capture the inputs to the fitter, before unrelated display
    and CAD stages, and compare transport with the independent homothety formula.
    """
    ppm, thickness = 4.0, 4.0
    initial_height, final_height, final_focal = 80.0, 240.0, 900.0
    initial_nadir, final_nadir = np.array([-5.0, 30.0]), np.array([5.0, 35.0])
    angle = 0.123 + np.arange(240) * (2 * np.pi / 240)
    unit = np.column_stack([np.cos(angle), np.sin(angle)])
    indices = np.arange(0, len(unit), 2)
    rings, originals, fine_normals, coarse_normals = [], [], [], []
    for outer, centre, radius, offset in (
        (True, (160.0, 160.0), 100.0, (-0.65, -0.25)),
        (False, (180.0, 160.0), 20.0, (-0.45, 0.55)),
    ):
        support = np.asarray(centre) + radius * unit
        points = support[indices] + offset
        rings.append(
            {
                "outer": outer,
                "points": points.copy(),
                "support": support.copy(),
                "support_indices": indices.copy(),
            }
        )
        originals.append((points, support))
        # These are analytic material normals for the two translated circles.
        coarse_normals.append(unit if outer else -unit)
        fine_normals.append(coarse_normals[-1][indices])

    rgb = np.full((320, 400, 3), 180, np.uint8)
    mask = np.zeros(rgb.shape[:2], np.uint8)
    monkeypatch.setattr(sheet, "find_sheet", lambda *args: object())
    monkeypatch.setattr(sheet, "estimate_k1", lambda *args: (0.0, 0.0, 0.0))
    monkeypatch.setattr(sheet, "homography", lambda *args: (np.eye(3), (100.0, 80.0), None))
    monkeypatch.setattr(sheet, "orthogonal_focal", lambda *args: None)
    monkeypatch.setattr(sheet, "aspect_ratio_check", lambda *args: 1.0)
    monkeypatch.setattr(sheet, "choose_ppm", lambda *args: (ppm, ppm))
    monkeypatch.setattr(sheet, "rectify", lambda *args: rgb)
    monkeypatch.setattr(sheet, "rectify_gray", lambda *args: np.full(mask.shape, 100.0))
    monkeypatch.setattr(edges, "segment", lambda *args, **kwargs: (mask, []))
    monkeypatch.setattr(edges, "measurement_weights", lambda *args: tone.LUMINANCE)
    monkeypatch.setattr(edges, "subpixel_rings", lambda *args: (rings, sigma, 0))

    def pose(matrix, size, exif_focal_35mm=None, focal_px=None):
        if focal_px is None:
            return {
                "height_mm": initial_height,
                "nadir_mm": initial_nadir.copy(),
                "focal_px": 200.0,
                "focal_source": "assumed",
            }
        assert focal_px == final_focal
        return {
            "height_mm": final_height,
            "nadir_mm": final_nadir.copy(),
            "focal_px": final_focal,
            "focal_source": "given",
        }

    monkeypatch.setattr(sheet, "camera_pose", pose)
    wall_calls = []

    def wall_fit(image, points, normals, band, blur, wall_tone=None):
        # The zero-blur branch must never fit a wall profile. The blur may be one per
        # point (each edge's own spread under a directional blur).
        assert np.all(np.asarray(blur) > 0)
        wall_calls.append(wall_tone)
        return points + 0.4 * normals, np.full(len(points), 27.0)

    monkeypatch.setattr(edges, "two_step_refine", wall_fit)
    monkeypatch.setattr(edges, "pooled_wall_tone", lambda *args: 27.0)
    refine_calls = []
    real_refine = reference._refine_walls

    def capture_refinement(image, supplied_rings, camera, *args):
        # Retrying the wall model must start from the original observations, not
        # already refined points or support transported under the provisional pose.
        for ring, (points, support) in zip(supplied_rings, originals):
            np.testing.assert_array_equal(ring["points"], points)
            np.testing.assert_array_equal(ring["support"], support)
            np.testing.assert_array_equal(ring["support_indices"], indices)
        refined, notes = real_refine(image, supplied_rings, camera, *args)
        refine_calls.append((camera["focal_source"], [(p.copy(), n.copy()) for p, n in refined]))
        return refined, notes

    monkeypatch.setattr(reference, "_refine_walls", capture_refinement)

    def infer_focal(holes, pose_at, *args):
        assert len(refine_calls) == 1 and len(holes) == 1
        np.testing.assert_allclose(holes[0][0], refine_calls[0][1][1][0] / ppm)
        np.testing.assert_allclose(holes[0][1], fine_normals[1], atol=1e-12)
        assert pose_at(final_focal)["height_mm"] == final_height
        return final_focal, 1

    monkeypatch.setattr(edges, "roundness_focal", infer_focal)
    corrections = []
    real_correct = edges.correct_thickness

    def capture_correction(points, normals, nadir, height, depth):
        corrections.append((points.copy(), normals.copy(), nadir.copy(), height, depth))
        return real_correct(points, normals, nadir, height, depth)

    monkeypatch.setattr(edges, "correct_thickness", capture_correction)
    fitted_inputs = []

    class CapturedBothRings(Exception):
        pass

    def capture_fit(points, tol, min_line, *, support_points, support_error):
        fitted_inputs.append((points.copy(), support_points.copy(), support_error))
        if len(fitted_inputs) == len(rings):
            raise CapturedBothRings

    monkeypatch.setattr(fitting, "fit_ring", capture_fit)
    with pytest.raises(CapturedBothRings):
        reference.trace_on_sheet(
            rgb,
            reference="custom",
            sheet_mm=(100.0, 80.0),
            inverted=False,
            detail="standard",
            thickness_mm=thickness,
            focal_35mm=None,
            snap=False,
            notices=[],
        )

    assert [source for source, _ in refine_calls] == ["assumed", "holes"]
    assert len(corrections) == 2 * len(rings)
    assert len(fitted_inputs) == len(rings)
    assert bool(wall_calls) == bool(sigma)

    def expected_transport(pixel_points, normals):
        # Independent plane-height projection inverse: only the top silhouette
        # scales about N by (H-t)/H. Other points retain their sheet coordinates.
        mm = pixel_points / ppm
        relative = mm - final_nadir
        top = np.sum(relative * normals, axis=1) > 0
        assert top.any() and (~top).any()
        return (mm - top[:, None] * (thickness / final_height) * relative) * ppm

    for i, ((original_points, original_support), captured) in enumerate(
        zip(originals, fitted_inputs)
    ):
        refined_points, measured_normals = refine_calls[-1][1][i]
        np.testing.assert_allclose(measured_normals, fine_normals[i], atol=1e-12)
        expected_points = expected_transport(refined_points, fine_normals[i])
        expected_support = expected_transport(original_support, coarse_normals[i])
        np.testing.assert_allclose(captured[0], expected_points, rtol=0, atol=1e-12)
        np.testing.assert_allclose(captured[1], expected_support, rtol=0, atol=1e-12)
        expected_error = np.linalg.norm(expected_points - expected_support[indices], axis=1).max()
        assert captured[2] == pytest.approx(expected_error, rel=0, abs=1e-12)
        np.testing.assert_array_equal(rings[i]["support_indices"], indices)
        # Each measured/coarse pair is transported exactly once with the FINAL
        # camera. The coarse input is still the original full contour.
        for call, before in zip(corrections[2 * i : 2 * i + 2], (refined_points, original_support)):
            np.testing.assert_array_equal(call[0], before / ppm)
            np.testing.assert_array_equal(call[2], final_nadir)
            assert call[3:] == (final_height, thickness)
        if sigma:
            assert np.max(np.abs(refined_points - refine_calls[0][1][i][0])) > 0.01
            before_refinement = expected_transport(original_points, fine_normals[i])
            stale_error = np.linalg.norm(
                before_refinement - expected_support[indices], axis=1
            ).max()
            assert abs(expected_error - stale_error) > 0.01
            first_refinement = expected_transport(refine_calls[0][1][i][0], fine_normals[i])
            provisional_error = np.linalg.norm(
                first_refinement - expected_support[indices], axis=1
            ).max()
            assert abs(expected_error - provisional_error) > 0.01
        else:
            np.testing.assert_array_equal(refined_points, original_points)
