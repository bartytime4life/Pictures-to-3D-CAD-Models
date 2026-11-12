"""Known coordinate maps through the real reference fitting pipeline.

The controlled rings test coordinate transport, not Gaussian-model accuracy. The
rendered photos exercise actual detection and retain mixed-frame approximations.
"""

import math

import numpy as np
import pytest

from backend import fitting, reference, tone
from backend.models import Profile
from backend.tracing import trace_image
from tests import synthetic as S

MIXED_NOTE = "Some curved edges use measurements from both the top and bottom"


def _circle(radius, centre=(120.0, 100.0), *, hole=False):
    angle = np.linspace(0, 2 * math.pi, 200, endpoint=False)
    directions = np.column_stack([np.cos(angle), np.sin(angle)])
    return np.asarray(centre) + radius * directions, -directions if hole else directions


def _capsule(radius=12.0, half_core=30.0):
    pieces, normals = [], []
    for centre, start in [((half_core, 0), -math.pi / 2), ((-half_core, 0), math.pi / 2)]:
        angle = np.linspace(start, start + math.pi, 150)
        outward = np.column_stack([np.cos(angle), np.sin(angle)])
        pieces.append(np.asarray(centre) + radius * outward)
        normals.append(outward)
    points_out, normals_out = [], []
    for index in range(2):
        points_out.extend(pieces[index])
        normals_out.extend(normals[index])
        line = np.linspace(pieces[index][-1], pieces[(index + 1) % 2][0], 100)[1:-1]
        points_out.extend(line)
        normals_out.extend(np.tile(normals[index][-1], (len(line), 1)))
    return np.asarray(points_out) + [120, 100], np.asarray(normals_out)


def _known_trace(
    monkeypatch,
    *,
    kind,
    thickness,
    covariance=None,
    sigma=2.0,
    nadir=(120.0, 100.0),
    inverse_mixed=False,
    force_unresolved=False,
):
    """Known source rings with real thickness map, fitting, export and validation.

    Sheet detection, intensity estimation and wall localization are outside this
    coordinate fixture. With inverse_mixed, prescribe a valid corrected contour and
    independently enlarge only its known top samples in the source frame.
    """
    points, normals = _circle(6.0) if kind == "circle" else _capsule()
    if inverse_mixed:
        alpha = 1 - thickness / 100
        top = np.sum(normals * (points - nadir), axis=1) > 0
        points[top] = np.asarray(nadir) + (points[top] - nadir) / alpha
    ring = {"outer": True, "points": points, "covariance": covariance}
    rgb = np.full((320, 420, 3), 180, np.uint8)
    camera = {"height_mm": 100.0, "nadir_mm": np.asarray(nadir) / 2, "focal_source": "exif"}
    captures = {"fillets": [], "corrections": [], "line_refits": []}
    real_refit, real_fillets, real_correct = (
        fitting.refit_lines,
        fitting.fit_fillets,
        fitting.correct_blur,
    )

    def refit(at, prims, margin=0.0, **kwargs):
        # fit_ring's preliminary refit has no frame context; the explicit reference
        # call must receive the aligned per-point scales after correction.
        if "blur_scales" in kwargs:
            captures["line_refits"].append((margin, kwargs["blur_scales"]))
        return real_refit(at, prims, margin=margin, **kwargs)

    def fillets(at, prims, tolerance, measured_sigma, supplied_covariance=None, **kwargs):
        captures["fillets"].append((measured_sigma, supplied_covariance, kwargs.get("blur_scales")))
        result = real_fillets(at, prims, tolerance, measured_sigma, supplied_covariance, **kwargs)
        if force_unresolved:
            for primitive in prims:
                if primitive.kind == "arc":
                    primitive.data.update(
                        blur_unresolved=True, blur_frame_mixed=True, r_sd=math.inf
                    )
        return result

    def correct(prims, measured_sigma, **kwargs):
        result = real_correct(prims, measured_sigma, **kwargs)
        captures["corrections"].append((measured_sigma, kwargs.get("blur_scales"), prims))
        return result

    with monkeypatch.context() as patch:
        patch.setattr(reference.sheet, "find_sheet", lambda *_: object())
        patch.setattr(reference.sheet, "estimate_k1", lambda *_: (0.0, 0.0, 0.0))
        patch.setattr(reference.sheet, "homography", lambda *_: (np.eye(3), (210.0, 297.0), None))
        patch.setattr(reference.sheet, "orthogonal_focal", lambda *_: 100.0)
        patch.setattr(reference.sheet, "camera_pose", lambda *_, **__: camera)
        patch.setattr(reference.sheet, "aspect_ratio_check", lambda *_: 1.0)
        patch.setattr(reference.sheet, "choose_ppm", lambda *_: (2.0, 2.0))
        patch.setattr(reference.sheet, "rectify", lambda *_: rgb.copy())
        patch.setattr(
            reference.sheet, "rectify_gray", lambda *_: np.zeros(rgb.shape[:2], np.float32)
        )
        patch.setattr(
            reference.edges, "segment", lambda *_, **__: (np.ones(rgb.shape[:2], np.uint8), [])
        )
        patch.setattr(reference.edges, "measurement_weights", lambda *_: tone.LUMINANCE)
        patch.setattr(reference.edges, "subpixel_rings", lambda *_: ([ring], sigma, 0))
        patch.setattr(
            reference, "_refine_walls", lambda *_: ([(points.copy(), normals.copy())], [])
        )
        patch.setattr(reference.fitting, "refit_lines", refit)
        patch.setattr(reference.fitting, "fit_fillets", fillets)
        patch.setattr(reference.fitting, "correct_blur", correct)
        result = reference.trace_on_sheet(
            rgb,
            reference="a4",
            sheet_mm=None,
            inverted=False,
            detail="standard",
            thickness_mm=thickness,
            focal_35mm=None,
            snap=True,
            notices=[],
        )
    return result, captures


@pytest.mark.parametrize("covariance", [None, np.diag([1.0, 9.0])], ids=["scalar", "covariance"])
def test_uniform_circle_frame_reaches_the_actual_radius_correction(monkeypatch, covariance):
    result, captured = _known_trace(
        monkeypatch,
        kind="circle",
        thickness=20.0,
        covariance=covariance,
    )
    circle = result["profile"]["primitives"]["outer"][0]
    assert circle["kind"] == "circle"
    # Exact homogeneity of the implemented series, not a claim of optical accuracy.
    expected = 0.8 * (6 + 2**2 / (2 * 6) - 2**4 / (24 * 6**3))
    assert circle["radius"] == pytest.approx(expected, abs=2e-11)
    assert len(captured["corrections"]) == 1
    np.testing.assert_array_equal(captured["corrections"][0][1], np.full(200, 0.8))
    assert not any(MIXED_NOTE in text for text in result["warnings"])


def _arc_centres_and_radii(profile):
    result = []
    for segment in profile["primitives"]["outer"]:
        if segment["kind"] != "arc":
            continue
        a, m, b = (np.asarray(segment[key]) for key in ("start", "mid", "end"))
        # Independent three-point circumcentre for the actual emitted geometry.
        centre = np.linalg.solve(2 * np.vstack([m - a, b - a]), [m @ m - a @ a, b @ b - a @ a])
        result.append((centre, np.linalg.norm(a - centre)))
    return sorted(result, key=lambda item: item[0][0])


@pytest.mark.parametrize("covariance", [None, np.diag([1.0, 9.0])], ids=["scalar", "covariance"])
def test_uniform_slot_frame_commutes_through_the_complete_fitting_chain(monkeypatch, covariance):
    baseline, _ = _known_trace(monkeypatch, kind="capsule", thickness=0.0, covariance=covariance)
    scaled, captured = _known_trace(
        monkeypatch, kind="capsule", thickness=20.0, covariance=covariance
    )
    raw = _arc_centres_and_radii(baseline["profile"])
    mapped = _arc_centres_and_radii(scaled["profile"])
    assert len(raw) == len(mapped) == 2
    assert mapped[1][0][0] - mapped[0][0][0] == pytest.approx(
        0.8 * (raw[1][0][0] - raw[0][0][0]),
        abs=2e-8,
    )
    np.testing.assert_allclose(
        [r for _, r in mapped], 0.8 * np.array([r for _, r in raw]), atol=2e-8
    )
    assert len(captured["fillets"]) == len(captured["line_refits"]) == 1
    for scales in (captured["fillets"][0][2], captured["line_refits"][0][1]):
        np.testing.assert_array_equal(scales, np.full(len(scales), 0.8))
    assert not any(MIXED_NOTE in text for text in scaled["warnings"])


@pytest.mark.parametrize("kind", ["circle", "capsule"])
@pytest.mark.parametrize("covariance", [None, np.diag([1.0, 9.0])], ids=["scalar", "covariance"])
def test_mixed_emitted_approximation_warns_once_and_does_not_claim_stationary_blur(
    monkeypatch, kind, covariance
):
    result, captured = _known_trace(
        monkeypatch,
        kind=kind,
        thickness=20.0,
        covariance=covariance,
        nadir=(170.0, 100.0),
        inverse_mixed=True,
    )
    Profile.model_validate(result["profile"])
    assert sum(MIXED_NOTE in text for text in result["warnings"]) == 1
    assert sum(MIXED_NOTE in text for text in result["profile"]["reference"]["notes"]) == 1
    assert any(
        p.data.get("blur_frame_mixed") for _, _, prims in captured["corrections"] for p in prims
    )
    assert {p["kind"] for p in result["profile"]["primitives"]["outer"]} != {"line"}
    for _, scales, _ in captured["corrections"]:
        assert set(scales) == {0.8, 1.0}


def test_an_explicitly_rejected_candidate_does_not_warn_about_emitted_mixed_curves(monkeypatch):
    # Inject a rejected candidate to test final-output warning gating. Real mixed
    # scalar nonparallel corners retain their explicitly approximate geometry.
    result, _ = _known_trace(
        monkeypatch,
        kind="capsule",
        thickness=20.0,
        covariance=np.diag([1.0, 9.0]),
        force_unresolved=True,
    )
    assert {p["kind"] for p in result["profile"]["primitives"]["outer"]} == {"line"}
    assert not any(MIXED_NOTE in text for text in result["warnings"])
    assert any("corner radius could not be determined" in text for text in result["warnings"])


@pytest.mark.parametrize("blur", [1.0, (1.0, 3.0)], ids=["scalar", "directional"])
def test_actual_thick_photo_retains_valid_approximate_curves_and_one_mixed_frame_notice(
    monkeypatch, blur
):
    mixed_scalar_corners = []
    real_fillets = fitting.fit_fillets

    def inspect_fillets(points, prims, *args, **kwargs):
        before = []
        scales = kwargs.get("blur_scales")
        if blur == 1.0 and scales is not None:
            for index, primitive in enumerate(prims):
                previous, following = prims[index - 1], prims[(index + 1) % len(prims)]
                if primitive.kind != "arc" or previous.kind != "line" or following.kind != "line":
                    continue
                d1, d2 = np.asarray(previous.data["d"]), np.asarray(following.data["d"])
                if abs(d1[0] * d2[1] - d1[1] * d2[0]) < math.sin(math.radians(5)):
                    continue
                start, end = previous.span[0], following.span[1]
                if end < start:
                    end += len(scales)
                values = [scales[i % len(scales)] for i in range(start, end + 1)]
                if values and min(values) != max(values):
                    before.append((primitive, following))
        result = real_fillets(points, prims, *args, **kwargs)
        for primitive, following in before:
            mixed_scalar_corners.append(
                {
                    "retained": any(p is primitive for p in prims),
                    "data": dict(primitive.data),
                    "next_line": dict(following.data),
                }
            )
        return result

    monkeypatch.setattr(fitting, "fit_fillets", inspect_fillets)
    data, _ = S.render(blur=blur, thickness=4.0)
    result = trace_image(data, reference="a4", thickness_mm=4.0)
    profile = Profile.model_validate(result["profile"])
    assert any(p.kind == "circle" for ring in profile.primitives.holes for p in ring)
    assert sum(MIXED_NOTE in text for text in result["warnings"]) == 1
    assert sum(MIXED_NOTE in text for text in profile.reference.notes) == 1
    if blur == 1.0:
        # The original real-renderer regression's limits are unchanged. In
        # particular, validity or source proximity cannot replace outer accuracy.
        limits = {"small": 0.03, "bore": 0.05, "slot": 0.06, "position": 0.05, "outer": 0.05}
        errors = S.feature_errors(result["profile"])
        assert {key: value for key, value in errors.items() if value > limits[key]} == {}
        assert mixed_scalar_corners
        for corner in mixed_scalar_corners:
            assert corner["retained"]
            assert corner["data"]["blur_frame_mixed"]
            assert math.isinf(corner["data"]["r_sd"])
            assert not corner["data"].get("blur_unresolved")
            assert not corner["data"].get("sharp")
            assert "sharp_bound" not in corner["data"]
            assert "sharp_bound" not in corner["next_line"]
