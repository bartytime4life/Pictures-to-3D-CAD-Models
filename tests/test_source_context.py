"""Private real-trace source binding, not camera or inverse-model qualification."""

import copy
import hashlib
import io
import json
import math
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, PngImagePlugin

from backend import app as api
from backend import finite_shape_fit, reference, sheet, tone, tracing
from backend.models import Profile
from backend.source_context import TraceSourceContext, trace_with_source
from tests import synthetic as S


def sha(array_or_bytes):
    if isinstance(array_or_bytes, np.ndarray):
        array_or_bytes = array_or_bytes.tobytes()
    return hashlib.sha256(array_or_bytes).hexdigest()


@pytest.fixture(scope="module")
def photo():
    return S.render(tilt=(0.0, 0.0, 17.0), k1=0, shadow=0, gradient=0, noise=0)[0]


@pytest.fixture(scope="module")
def captured(photo):
    """Observe the actual source input and actual display transform, without stubs."""
    seen = {}
    real_rectify = sheet.rectify_gray
    real_transform = reference._Transform

    def record_rectify(image, matrix, k1, plane, ppm, **kwargs):
        seen.update(field=image.copy(), matrix=matrix.copy(), k1=k1, plane=plane, ppm=ppm)
        return real_rectify(image, matrix, k1, plane, ppm, **kwargs)

    class RecordTransform(real_transform):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            seen["transform"] = self
            seen["pairs"] = []

        def __call__(self, point):
            out = super().__call__(point)
            if len(seen["pairs"]) < 20:
                seen["pairs"].append((np.asarray(point).copy(), out))
            return out

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sheet, "rectify_gray", record_rectify)
        patch.setattr(reference, "_Transform", RecordTransform)
        result, context = trace_with_source(photo, reference="a4")
    assert context is not None
    return result, context, seen


@pytest.fixture(scope="module")
def repeated(photo):
    return trace_with_source(photo, reference="a4")


@pytest.fixture(scope="module")
def colour_photo():
    return S.colour_photo((120, 120, 120), (220, 220, 220), (0, 255, 0))


def test_capture_is_the_actual_prewarp_field_and_records_requested_options(photo, captured):
    result, context, seen = captured
    metadata = context.metadata()
    upright = np.asarray(Image.open(io.BytesIO(photo)).convert("RGB"))
    assert context.working_field.dtype == np.dtype("<f4")
    assert np.array_equal(context.working_field, seen["field"])
    assert metadata["input_sha256"] == sha(photo)
    assert metadata["input_bytes"] == len(photo)
    assert metadata["upright_rgb_shape"] == list(upright.shape)
    assert metadata["upright_rgb_sha256"] == sha(upright)
    assert metadata["working_rgb_sha256"] == sha(upright)
    assert metadata["working_field_sha256"] == sha(seen["field"])
    assert metadata["working_field_shape"] == list(seen["field"].shape)
    assert metadata["reduction"]["applied"] is False
    assert metadata["trace_options"] == {
        "reference": "a4",
        "threshold": -1,
        "inverted": False,
        "detail": "standard",
        "sheet_mm": None,
        "thickness_mm": None,
        "snap": True,
        "fallback": False,
        "focal_35mm": None,
    }
    assert not metadata["sensor_raw"] and not metadata["psf_calibrated"]
    assert not metadata["noise_calibrated"] and not metadata["response_calibrated"]
    assert result["profile"]["reference"]["lens_k1"] == seen["k1"] == 0
    json.dumps(metadata, allow_nan=False)


def test_unchanged_response_and_per_request_binding(photo, captured, repeated):
    result, context, _ = captured
    again, second = repeated
    assert result == again == tracing.trace_image(photo, reference="a4")
    first_meta, second_meta = context.metadata(), second.metadata()
    assert first_meta["request_id"] != second_meta["request_id"]
    assert context.sha256 != second.sha256
    for key in ("input_sha256", "working_field_sha256", "profile_sha256"):
        assert first_meta[key] == second_meta[key]
    assert set(result) == {"image", "profile", "bounds", "threshold", "warnings"}
    assert "working_field" not in repr(context)


def test_colour_measurement_retains_selected_mix_instead_of_luminance(colour_photo, monkeypatch):
    seen = []
    actual = sheet.rectify_gray

    def record(image, *args, **kwargs):
        seen.append(image.copy())
        return actual(image, *args, **kwargs)

    monkeypatch.setattr(sheet, "rectify_gray", record)
    result, context = trace_with_source(colour_photo, reference="a4")
    assert context is not None and len(seen) == 1
    weights = context.metadata()["channel_weights"]
    assert not np.allclose(weights, tone.LUMINANCE)
    assert any("colour mix" in item for item in result["profile"]["reference"]["notes"])
    assert np.array_equal(context.working_field, seen[0])
    rgb = np.asarray(Image.open(io.BytesIO(colour_photo)).convert("RGB"))
    assert np.array_equal(context.working_field, tone.linear_mix(rgb, weights))
    assert np.max(np.abs(context.working_field - tone.linear_luminance(rgb))) > 20


def test_display_inverse_uses_actual_rotation_crop_scale_and_plane_units(captured):
    result, context, seen = captured
    transform = seen["transform"]
    assert abs(transform.rotation[0, 1]) > 0.1
    assert np.linalg.norm(transform.origin) > 1
    source, display = map(np.asarray, zip(*seen["pairs"]))
    mapped = context.display_to_plane(display, profile=result["profile"])
    np.testing.assert_allclose(mapped, source / seen["ppm"], atol=1e-12, rtol=1e-14)
    assert not mapped.flags.writeable
    # These are geometric display coordinates: the inverse must not add half a pixel.
    delta = context.display_to_plane(display + [1, 0], profile=result["profile"]) - mapped
    expected = transform.rotation.T[:, 0] / (transform.scale * seen["ppm"])
    np.testing.assert_allclose(delta, np.tile(expected, (len(delta), 1)), atol=1e-12)


def test_source_indices_preserve_order_values_and_geometric_centres(captured):
    result, context, seen = captured
    pixels = np.array([[100, 120], [10, 20], [99, 121]], dtype=np.int64)
    observation = context.source_pixels(pixels, profile=result["profile"])
    assert observation.context_sha256 == context.sha256
    np.testing.assert_array_equal(observation.pixels_xy, pixels)
    np.testing.assert_array_equal(observation.raw_values, seen["field"][pixels[:, 1], pixels[:, 0]])
    np.testing.assert_array_equal(observation.matrix, np.eye(3))
    np.testing.assert_array_equal(observation.samples, observation.raw_values)
    # A geometric source centre maps back to precisely this index, with no second offset.
    centres = observation.pixels_xy.astype(float) + 0.5
    np.testing.assert_array_equal(np.floor(centres).astype(int), pixels)
    noise = observation.noise([1.0, 2.0, 3.0])
    np.testing.assert_array_equal(noise.input_std, [1, 2, 3])
    np.testing.assert_allclose(noise.matrix, np.eye(3))


@pytest.mark.parametrize(
    "pixels",
    [
        [],
        [[1, 2], [1, 2]],
        [[1.0, 2.0]],
        [[True, 2]],
        [[1, np.bool_(False)]],
        [[-1, 2]],
        [[10**6, 1]],
        [[1, 2, 3]],
        [[i, 0] for i in range(513)],
        [[math.nan, 2]],
    ],
)
def test_source_query_refuses_invalid_or_ambiguous_pixel_binding(captured, pixels):
    result, context, _ = captured
    with pytest.raises((ValueError, TypeError)):
        context.source_pixels(pixels, profile=result["profile"])


def test_context_metadata_and_all_observation_arrays_are_isolated(captured):
    result, context, _ = captured
    before = context.sha256
    metadata = context.metadata()
    metadata["channel_weights"][0] = -10
    metadata["trace_options"]["snap"] = False
    assert context.sha256 == before
    assert context.metadata()["trace_options"]["snap"] is True
    pixels = np.array([[10, 20], [30, 40]])
    observation = context.source_pixels(pixels, profile=result["profile"])
    pixels[:] = 0
    np.testing.assert_array_equal(observation.pixels_xy, [[10, 20], [30, 40]])
    arrays = [
        context.working_field,
        observation.pixels_xy,
        observation.raw_values,
        observation.matrix,
        observation.samples,
    ]
    for array in arrays:
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array.setflags(write=True)
        with pytest.raises(ValueError):
            array.flat[0] = 0
    with pytest.raises(FrozenInstanceError):
        context._record_json = "{}"
    assert context.sha256 == before


@pytest.mark.parametrize(
    "method",
    [
        "assert_profile",
        "display_to_plane",
        "source_pixels",
        "observe_display",
        "point_gaussian_geometry",
    ],
)
def test_profile_binding_rejects_valid_but_stale_geometry(captured, method):
    result, context, _ = captured
    profile = copy.deepcopy(result["profile"])
    # Removing an exact description is valid Profile data, but loses this trace revision.
    profile["primitives"] = None
    Profile.model_validate(profile)
    call = getattr(context, method)
    with pytest.raises(ValueError, match="profile differs"):
        if method == "assert_profile":
            call(profile)
        elif method == "point_gaussian_geometry":
            call(profile=profile)
        else:
            call([[10, 20]], profile=profile)
    context.assert_profile(json.loads(json.dumps(result["profile"])))
    context.assert_profile(Profile.model_validate(result["profile"]))


def _keys_weight(x):
    x = abs(x)
    return (
        1.5 * x**3 - 2.5 * x * x + 1
        if x <= 1
        else (-0.5 * x**3 + 2.5 * x * x - 4 * x + 2 if x < 2 else 0)
    )


def _manual_sample(context, plane_point, smoothing):
    """Explicit scalar tap loops, without any production operator builder."""
    meta = context.metadata()
    height, width = meta["rectified_shape"]
    sx, sy = np.asarray(plane_point) * meta["rectified_ppm"] - 0.5
    x0, y0 = math.floor(sx), math.floor(sy)
    kernel = np.exp(-(np.arange(-3, 4, dtype=float) ** 2) / (2 * 0.7**2))
    kernel /= kernel.sum()
    offsets = list(range(-3, 4)) if smoothing else [0]
    h = np.asarray(meta["plane_mm_to_undistorted_working_photo"])

    def reflect(index, size):
        value = index % (2 * size - 2)
        return value if value < size else 2 * size - 2 - value

    total = 0.0
    for j in range(-1, 3):
        for i in range(-1, 3):
            weight = _keys_weight(sx - x0 - i) * _keys_weight(sy - y0 - j)
            ix, iy = min(max(x0 + i, 0), width - 1), min(max(y0 + j, 0), height - 1)
            for dy in offsets:
                for dx in offsets:
                    gx, gy = reflect(ix + dx, width), reflect(iy + dy, height)
                    raw = h @ np.array(
                        [(gx + 0.5) / meta["rectified_ppm"], (gy + 0.5) / meta["rectified_ppm"], 1]
                    )
                    ux, uy = raw[:2] / raw[2]
                    cx, cy = meta["radial_centre_xy"]
                    gain = (
                        1
                        + meta["lens_k1"]
                        * ((ux - cx) ** 2 + (uy - cy) ** 2)
                        / meta["radial_scale"] ** 2
                    )
                    px, py = cx + (ux - cx) * gain - 0.5, cy + (uy - cy) * gain - 0.5
                    source = float(
                        sheet.sample_keys(context.working_field, np.array(px), np.array(py))
                    )
                    blur = kernel[dx + 3] * kernel[dy + 3] if smoothing else 1
                    total += weight * blur * source
    return total


@pytest.mark.parametrize("smoothing", [False, True])
def test_display_observation_matches_explicit_ordered_sgr_taps(captured, smoothing):
    result, context, _ = captured
    # One boundary location plus one exterior grid-border location exercises reflect101.
    points = [result["profile"]["outer"][0]]
    metadata = context.metadata()
    inverse_display = np.asarray(metadata["display_to_plane_mm"])
    plane_border = np.array([0.2, 0.3]) / metadata["rectified_ppm"]
    points.append(np.linalg.solve(inverse_display[:2, :2], plane_border - inverse_display[:2, 2]))
    observation = context.observe_display(points, profile=result["profile"], smoothing=smoothing)
    plane = context.display_to_plane(points, profile=result["profile"])
    expected = [_manual_sample(context, p, smoothing) for p in plane]
    np.testing.assert_allclose(observation.samples, expected, atol=2e-11, rtol=1e-13)
    np.testing.assert_array_equal(
        observation.raw_values,
        context.working_field[observation.pixels_xy[:, 1], observation.pixels_xy[:, 0]],
    )
    np.testing.assert_allclose(observation.matrix.sum(axis=1), 1, atol=2e-13)


def test_original_bytes_differ_while_decoded_pixels_remain_identical(colour_photo):
    image = Image.open(io.BytesIO(colour_photo))
    info = PngImagePlugin.PngInfo()
    info.add_text("note", "Different container metadata, same decoded pixels")
    buffer = io.BytesIO()
    image.save(buffer, "PNG", pnginfo=info)
    _, first = trace_with_source(colour_photo, reference="a4")
    _, second = trace_with_source(buffer.getvalue(), reference="a4")
    a, b = first.metadata(), second.metadata()
    assert a["input_sha256"] != b["input_sha256"]
    for key in ("upright_rgb_sha256", "working_rgb_sha256", "working_field_sha256"):
        assert a[key] == b[key]


def test_decode_record_follows_orientation_and_transparency(colour_photo):
    upright = np.asarray(Image.open(io.BytesIO(colour_photo)).convert("RGB")).copy()
    rgba = np.dstack([upright, np.full(upright.shape[:2], 255, np.uint8)])
    rgba[:8, :8, 3] = 0
    expected = upright.copy()
    expected[:8, :8] = 255
    stored = Image.fromarray(rgba).transpose(Image.Transpose.ROTATE_90)
    exif = Image.Exif()
    exif[274] = 6
    buffer = io.BytesIO()
    stored.save(buffer, "PNG", exif=exif)
    _, context = trace_with_source(buffer.getvalue(), reference="a4")
    metadata = context.metadata()
    assert stored.size == (expected.shape[0], expected.shape[1])
    assert metadata["upright_rgb_shape"] == list(expected.shape)
    assert metadata["upright_rgb_sha256"] == sha(expected)
    assert metadata["working_rgb_sha256"] == sha(expected)
    assert metadata["reduction"]["applied"] is False


def test_reduction_binds_actual_working_frame_and_disallows_point_model(colour_photo, monkeypatch):
    rgb = np.asarray(Image.open(io.BytesIO(colour_photo)).convert("RGB"))
    seen = {}
    actual = tone.reduce_in_linear_light

    def record(image, scale):
        seen["input"] = image.copy()
        seen["scale"] = scale
        seen["output"] = actual(image, scale)
        return seen["output"]

    monkeypatch.setattr(tracing, "WORKING_PIXELS", int(rgb.shape[0] * rgb.shape[1] * 0.64))
    monkeypatch.setattr(tone, "reduce_in_linear_light", record)
    result, context = trace_with_source(colour_photo, reference="a4")
    metadata = context.metadata()
    np.testing.assert_array_equal(seen["input"], rgb)
    assert metadata["upright_rgb_sha256"] == sha(rgb)
    assert metadata["working_rgb_sha256"] == sha(seen["output"])
    assert metadata["working_rgb_shape"] == list(seen["output"].shape)
    assert context.working_field.shape == seen["output"].shape[:2]
    assert metadata["reduction"]["applied"] is True
    assert metadata["reduction"]["scale_xy"] == [
        seen["output"].shape[1] / rgb.shape[1],
        seen["output"].shape[0] / rgb.shape[0],
    ]
    assert seen["output"].shape[:2] == (
        round(rgb.shape[0] * seen["scale"]),
        round(rgb.shape[1] * seen["scale"]),
    )
    with pytest.raises(ValueError, match="prior area reduction"):
        context.point_gaussian_geometry(profile=result["profile"])


def test_executed_reduction_is_recorded_even_if_rounded_shape_is_unchanged(
    colour_photo, monkeypatch
):
    rgb = np.asarray(Image.open(io.BytesIO(colour_photo)).convert("RGB"))
    monkeypatch.setattr(tracing, "WORKING_PIXELS", rgb.shape[0] * rgb.shape[1] - 1)
    result, context = trace_with_source(colour_photo, reference="a4")
    metadata = context.metadata()
    assert metadata["upright_rgb_shape"] == metadata["working_rgb_shape"]
    assert metadata["reduction"]["scale_xy"] == [1.0, 1.0]
    assert metadata["reduction"]["applied"] is True
    with pytest.raises(ValueError, match="prior area reduction"):
        context.point_gaussian_geometry(profile=result["profile"])


def test_late_profile_failure_does_not_publish_capture(photo, monkeypatch):
    published = []
    measured = []
    real_rectify = sheet.rectify_gray

    def record(*args, **kwargs):
        measured.append(True)
        return real_rectify(*args, **kwargs)

    def fail_profile(**kwargs):
        return Profile(outer=[])

    monkeypatch.setattr(sheet, "rectify_gray", record)
    monkeypatch.setattr(reference, "Profile", fail_profile)
    with pytest.raises(tracing.TraceError, match="valid profile"):
        tracing.trace_image(photo, reference="a4", fallback=True, _source_capture=published.append)
    assert measured == [True] and published == []


def test_explicit_sheet_fallback_and_plain_trace_retain_no_context(monkeypatch):
    image = Image.new("RGB", (500, 360), "white")
    ImageDraw.Draw(image).rectangle((50, 60, 450, 300), fill="black")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    photo = buffer.getvalue()

    def no_sheet(*args, **kwargs):
        raise sheet.SheetError("No reference sheet was found")

    monkeypatch.setattr(sheet, "find_sheet", no_sheet)
    result, context = trace_with_source(photo, reference="a4", fallback=True)
    assert context is None and "reference" not in result["profile"]
    plain, context = trace_with_source(photo)
    assert context is None and "reference" not in plain["profile"]
    with pytest.raises(tracing.TraceError):
        trace_with_source(photo, reference="a4")


def test_default_http_trace_does_not_capture_or_write_source(
    photo, captured, tmp_path, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("normal HTTP trace must not create private source records")

    monkeypatch.setattr(TraceSourceContext, "_from_trace", forbidden)
    monkeypatch.setattr("backend.source_context._decode_record", forbidden)
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    monkeypatch.chdir(tmp_path)
    with TestClient(api.app) as client:
        response = client.post(
            "/api/trace",
            files={"file": ("photo.jpg", photo, "image/jpeg")},
            data={"reference": "a4"},
        )
    assert response.status_code == 200, response.text
    assert response.json() == json.loads(json.dumps(captured[0]))
    assert list((tmp_path / "jobs").iterdir()) == []
    assert set(tmp_path.iterdir()) == {tmp_path / "jobs"}


def test_fit_bridge_dispatches_bound_observations_and_refuses_other_requests(
    captured, repeated, monkeypatch
):
    result, context, _ = captured
    _, other = repeated
    observation = context.source_pixels([[10, 20], [30, 40]], profile=result["profile"])
    seen = {}
    sentinel = object()

    def fit(pixels, values, noise, **kwargs):
        seen.update(pixels=pixels, values=values, noise=noise, kwargs=kwargs)
        return sentinel

    monkeypatch.setattr(finite_shape_fit, "fit_circular_segment", fit)
    options = {
        "input_std": [1, 2],
        "psf_covariance": [[1.0, 0.2], [0.2, 2.0]],
        "radius_bounds": (7, 9),
        "chord_fraction_bounds": (-0.1, 0.2),
        "max_evaluations": 9,
    }
    saved = copy.deepcopy(result["profile"])
    assert (
        context.fit_circular_segment(observation, profile=result["profile"], **options) is sentinel
    )
    np.testing.assert_array_equal(seen["pixels"], observation.pixels_xy)
    np.testing.assert_array_equal(seen["values"], observation.raw_values)
    np.testing.assert_array_equal(seen["noise"].input_std, [1, 2])
    assert seen["kwargs"]["sensor_shape"] == context.working_field.shape
    np.testing.assert_array_equal(
        seen["kwargs"]["homography"], context.metadata()["plane_mm_to_undistorted_working_photo"]
    )
    assert seen["kwargs"]["psf_covariance"] == options["psf_covariance"]
    assert result["profile"] == saved
    seen.clear()
    with pytest.raises(ValueError, match="different source request"):
        other.fit_circular_segment(observation, profile=result["profile"], **options)
    assert seen == {}
    stale = copy.deepcopy(result["profile"])
    stale["primitives"] = None
    with pytest.raises(ValueError, match="profile differs"):
        context.fit_circular_segment(observation, profile=stale, **options)
    assert seen == {}


@pytest.mark.parametrize("change", ["values", "pixels", "outside", "duplicate", "boolean"])
def test_fit_bridge_rechecks_pixel_values_instead_of_trusting_origin_label(
    captured, monkeypatch, change
):
    result, context, _ = captured
    field = context.working_field
    ymin, xmin = np.unravel_index(np.argmin(field), field.shape)
    ymax, xmax = np.unravel_index(np.argmax(field), field.shape)
    original = context.source_pixels([[xmin, ymin], [xmax, ymax]], profile=result["profile"])
    if change == "values":
        altered = replace(original, raw_values=original.raw_values + 1)
    elif change == "pixels":
        altered = replace(original, pixels_xy=original.pixels_xy[::-1])
    elif change == "outside":
        altered = replace(original, pixels_xy=np.array([[10**9, 0], [xmax, ymax]]))
    elif change == "duplicate":
        altered = replace(original, pixels_xy=np.array([[xmin, ymin], [xmin, ymin]]))
    else:
        altered = replace(original, pixels_xy=np.ones((2, 2), dtype=bool))
    assert altered.context_sha256 == context.sha256

    def forbidden(*args, **kwargs):
        raise AssertionError("unbound source data reached fitter")

    monkeypatch.setattr(finite_shape_fit, "fit_circular_segment", forbidden)
    with pytest.raises(ValueError, match="observation"):
        context.fit_circular_segment(
            altered,
            profile=result["profile"],
            input_std=1,
            psf_covariance=np.eye(2),
            radius_bounds=(7, 9),
            chord_fraction_bounds=(-0.1, 0.2),
        )


def test_full_direct_source_query_cap_remains_ordered_and_immutable(captured):
    result, context, _ = captured
    pixels = np.column_stack((np.arange(512)[::-1], np.full(512, 100)))
    observation = context.source_pixels(pixels, profile=result["profile"])
    np.testing.assert_array_equal(observation.pixels_xy, pixels)
    np.testing.assert_array_equal(observation.samples, context.working_field[100, pixels[:, 0]])
    assert observation.matrix.shape == (512, 512)
    with pytest.raises(ValueError):
        observation.matrix.setflags(write=True)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("lens_k1", 1e-20, "nonzero lens distortion"),
        ("thickness_mm", 1.0, "parallax"),
        ("reduction", {"applied": True}, "prior area reduction"),
    ],
)
def test_unsupported_fit_assumptions_refused_before_forward_call(
    captured, monkeypatch, field, value, reason
):
    result, context, _ = captured
    metadata = context.metadata()
    metadata[field] = value
    # Guard unit control only; actual decoded/reduced-frame capture is tested above.
    unsupported = replace(context, _record_json=json.dumps(metadata))
    observation = unsupported.source_pixels([[10, 20]], profile=result["profile"])

    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported source model reached fitter")

    monkeypatch.setattr(finite_shape_fit, "fit_circular_segment", forbidden)
    with pytest.raises(ValueError, match=reason):
        unsupported.fit_circular_segment(
            observation,
            profile=result["profile"],
            input_std=1,
            psf_covariance=np.eye(2),
            radius_bounds=(7, 9),
            chord_fraction_bounds=(-0.1, 0.2),
        )


@pytest.mark.parametrize("smoothing", [None, 1, "yes", np.bool_(True)])
def test_observation_smoothing_requires_explicit_boolean(captured, smoothing):
    result, context, _ = captured
    with pytest.raises(TypeError):
        context.observe_display([[10, 20]], profile=result["profile"], smoothing=smoothing)


def test_capture_hook_is_not_a_trace_option(photo):
    with pytest.raises(ValueError, match="owned by trace_with_source"):
        trace_with_source(photo, _source_capture=lambda value: None)
