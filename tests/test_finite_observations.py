"""Observation/binding contracts, not finite-shape recovery or camera accuracy."""

import hashlib
import json
import math
import warnings
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from backend import finite_observations as observations


def fixture(*, polarity="dark", angle=0.0):
    """Independent smooth synthetic D-like field; no production fit/forward call."""
    centre = np.array([76.3, 72.7])
    radius, fraction, sigma = 18.0, 0.25, 1.2
    normal = np.array([math.cos(angle), math.sin(angle)])
    tangent = np.array([-normal[1], normal[0]])
    yy, xx = np.mgrid[:160, :170]
    relative = np.stack((xx + 0.5 - centre[0], yy + 0.5 - centre[1]), axis=-1)
    radial = (radius - np.linalg.norm(relative, axis=-1)) / sigma
    chord = (radius * fraction - relative @ normal) / sigma
    cdf = np.vectorize(lambda z: 0.5 * math.erfc(-z / math.sqrt(2)))
    p = cdf(radial) * cdf(chord)
    field = (210.0 - 175.0 * p if polarity == "dark" else 35.0 + 175.0 * p).astype(np.float32)
    angles = np.linspace(math.acos(fraction), 2 * math.pi - math.acos(fraction), 193)
    arc = centre + radius * (np.cos(angles)[:, None] * normal + np.sin(angles)[:, None] * tangent)
    ring = np.vstack((arc, np.linspace(arc[-1], arc[0], 31)[1:-1]))
    return field, ring, normal, sigma


def prepare(*, polarity="dark", angle=0.0):
    field, ring, normal, sigma = fixture(polarity=polarity, angle=angle)
    return observations.prepare_segment_observations(
        field, ring, normal=normal, blur_sigma=sigma, polarity=polarity
    )


@pytest.mark.parametrize("polarity", ["dark", "light"])
@pytest.mark.parametrize("angle", [0.0, 0.37])
def test_crop_and_pixel_centres_are_same_global_observations(polarity, angle):
    field, ring, normal, sigma = fixture(polarity=polarity, angle=angle)
    result = observations.prepare_segment_observations(
        field, ring, normal=normal, blur_sigma=sigma, polarity=polarity
    )
    padding = math.ceil(max(16, 8 * sigma))
    expected_lower = np.floor(ring.min(axis=0)).astype(int) - padding
    expected_upper = np.ceil(ring.max(axis=0)).astype(int) + padding + 1
    assert result.crop_bounds == (*expected_lower, *expected_upper)
    x0, y0 = result.crop_origin
    assert result.source_shape == field.shape
    assert result.sensor_shape == (expected_upper[1] - y0, expected_upper[0] - x0)
    np.testing.assert_array_equal(
        result.field, field[y0 : expected_upper[1], x0 : expected_upper[0]]
    )
    expected_h = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]])
    np.testing.assert_array_equal(result.homography, expected_h)
    for pixels, values in (
        (result.training_pixels, result.training_values),
        (result.heldout_pixels, result.heldout_values),
    ):
        global_indices = pixels + (x0, y0)
        np.testing.assert_array_equal(values, field[global_indices[:, 1], global_indices[:, 0]])
        global_centres = np.column_stack((global_indices + 0.5, np.ones(len(pixels))))
        mapped = global_centres @ result.homography.T
        np.testing.assert_array_equal(mapped[:, :2], pixels + 0.5)
    np.testing.assert_array_equal(result.plane_contour, result.contour + (x0, y0))
    assert (
        result.metadata()["observed_contrast"] < 0
        if polarity == "dark"
        else result.metadata()["observed_contrast"] > 0
    )


def test_global_translation_preserves_crop_samples_radius_fraction_and_translates_bounds():
    field, ring, normal, sigma = fixture(angle=0.37)
    first = observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)
    offset = np.array([11, 7])
    shifted = np.full((field.shape[0] + 20, field.shape[1] + 30), 210, dtype=field.dtype)
    shifted[offset[1] : offset[1] + field.shape[0], offset[0] : offset[0] + field.shape[1]] = field
    second = observations.prepare_segment_observations(
        shifted, ring + offset, normal=normal, blur_sigma=sigma
    )
    for name in (
        "field",
        "training_pixels",
        "training_values",
        "heldout_pixels",
        "heldout_values",
        "contour",
    ):
        np.testing.assert_array_equal(getattr(first, name), getattr(second, name))
    np.testing.assert_array_equal(second.crop_origin, np.array(first.crop_origin) + offset)
    np.testing.assert_allclose(
        second.seed_centre, np.array(first.seed_centre) + offset, rtol=0, atol=3e-14
    )
    np.testing.assert_allclose(
        second.centre_bounds, np.array(first.centre_bounds) + offset[:, None], rtol=0, atol=3e-14
    )
    assert first.radius_bounds == second.radius_bounds
    assert first.chord_fraction_bounds == second.chord_fraction_bounds
    assert first.seed_radius == second.seed_radius and first.seed_fraction == second.seed_fraction


def test_dirty_sheet_border_outside_measured_crop_cannot_change_seed_or_samples():
    field, ring, normal, sigma = fixture()
    first = observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)
    dirty = field.copy()
    dirty[:8], dirty[-8:], dirty[:, :8], dirty[:, -8:] = 12, 12, 12, 12
    second = observations.prepare_segment_observations(dirty, ring, normal=normal, blur_sigma=sigma)
    assert np.median(np.r_[dirty[0], dirty[-1], dirty[1:-1, 0], dirty[1:-1, -1]]) == 12
    assert second.metadata()["background_estimate"] == 210
    for name in (
        "field",
        "training_pixels",
        "training_values",
        "heldout_pixels",
        "heldout_values",
        "contour",
    ):
        np.testing.assert_array_equal(getattr(first, name), getattr(second, name))
    assert first.bounds == second.bounds
    assert first.seed_centre == second.seed_centre
    assert first.metadata()["crop_sha256"] == second.metadata()["crop_sha256"]
    assert first.metadata()["source_sha256"] != second.metadata()["source_sha256"]
    assert first.metadata()["binding_sha256"] != second.metadata()["binding_sha256"]


def test_fixed_strata_are_unique_disjoint_and_values_are_bound_to_field():
    result = prepare()
    train, held = result.training_pixels, result.heldout_pixels
    assert train.shape == (40, 2) and held.shape == (16, 2)
    assert len(np.unique(np.vstack((train, held)), axis=0)) == 56
    meta = result.metadata()
    u = (result.field - meta["background_estimate"]) / meta["observed_contrast"]
    training_u, held_u = u[train[:, 1], train[:, 0]], u[held[:, 1], held[:, 0]]
    assert np.all((training_u[:24] > 0.15) & (training_u[:24] < 0.85))
    assert np.all(training_u[24:32] >= 0.9) and np.all(training_u[32:] <= 0.1)
    assert np.all((held_u[:8] > 0.15) & (held_u[:8] < 0.85))
    assert np.all(held_u[8:12] >= 0.9) and np.all(held_u[12:] <= 0.1)
    # Independently reconstruct the exact evenly spaced edge stratum and split.
    xmin, ymin, xmax, ymax = meta["roi_bounds_xy"]
    edge = [
        (x, y)
        for y in range(ymin, ymax + 1)
        for x in range(xmin, xmax + 1)
        if 0.15 < u[y, x] < 0.85
    ]
    my, mx = np.nonzero(u >= 0.5)
    cx, cy = mx.mean() + 0.5, my.mean() + 0.5
    edge.sort(
        key=lambda p: (
            math.atan2(p[1] + 0.5 - cy, p[0] + 0.5 - cx),
            math.hypot(p[0] + 0.5 - cx, p[1] + 0.5 - cy),
            p[1],
            p[0],
        )
    )
    chosen = np.array(edge)[np.rint(np.linspace(0, len(edge) - 1, 32)).astype(int)]
    np.testing.assert_array_equal(
        train[:24], np.array([p for i, p in enumerate(chosen) if i % 4 != 3])
    )
    np.testing.assert_array_equal(held[:8], chosen[3::4])


def test_explicit_width_alone_controls_bounds_and_metadata_without_covariance_input():
    field, ring, normal, sigma = fixture()
    result = observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)
    meta = result.metadata()
    assert result.seed_centre == tuple(meta["seed_centre"])
    pad = max(0.5 * result.seed_radius, 3 * sigma)
    np.testing.assert_array_equal(
        result.centre_bounds, [[c - pad, c + pad] for c in result.seed_centre]
    )
    assert result.radius_bounds == (
        max(0.05, 0.25 * result.seed_radius),
        max(2 * result.seed_radius, meta["observed_extent"]),
    )
    assert result.chord_fraction_bounds == (
        max(-0.98, result.seed_fraction - 0.45),
        min(0.98, result.seed_fraction + 0.45),
    )
    assert result.bounds == meta["bounds"]
    encoded = meta.copy()
    binding = encoded.pop("binding_sha256")
    assert (
        hashlib.sha256(
            json.dumps(encoded, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        == binding
    )
    changed = observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=4.0)
    assert changed.blur_sigma == 4 and changed.metadata()["padding"] == 32
    assert changed.metadata()["binding_sha256"] != binding


def test_arrays_metadata_and_bounds_survive_caller_mutation_and_are_immutable():
    field, ring, normal, sigma = fixture()
    result = observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)
    before = result.metadata()
    field[:], ring[:], normal[:] = 0, 0, 0
    assert result.metadata() == before
    assert np.any(result.field != 0) and np.any(result.ring_points != 0)
    for name in (
        "field",
        "ring_points",
        "normal",
        "homography",
        "training_pixels",
        "training_values",
        "heldout_pixels",
        "heldout_values",
        "contour",
        "plane_contour",
    ):
        array = getattr(result, name)
        with pytest.raises(ValueError):
            array.flat[0] = 0
        with pytest.raises(ValueError):
            array.setflags(write=True)
    altered = result.metadata()
    altered["bounds"]["radius_bounds"][0] = 999
    detached = result.bounds
    detached["centre_bounds"][0][0] = 999
    assert result.metadata() == before and result.bounds == before["bounds"]
    with pytest.raises(FrozenInstanceError):
        result.seed_radius = 999


def test_pixel_centre_crossings_have_no_added_or_missing_half_pixel():
    # Independent linear field: a crossing between index1 and2 at x=2.25,
    # with y at each actual pixel centre. This is not index coordinate1.75.
    u = np.tile(np.array([0.0, 0.2, 0.6, 1.0]), (8, 1))
    actual = observations._crossings(u)
    np.testing.assert_array_equal(actual[:, 0], np.full(8, 2.25))
    np.testing.assert_array_equal(actual[:, 1], np.arange(8) + 0.5)


def test_full_crop_padding_is_required_instead_of_silent_clipping():
    field, ring, normal, sigma = fixture()
    shifted_ring = ring - (45, 0)
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations.prepare_segment_observations(
            field, shifted_ring, normal=normal, blur_sigma=sigma
        )
    assert error.value.reason == "crop_edge"


def test_crop_material_contact_is_explicitly_unsupported():
    field, ring, normal, sigma = fixture()
    x0 = int(np.floor(ring[:, 0].min())) - 16
    field[60:65, x0] = 35
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)
    assert error.value.reason == "crop_edge"


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda f, r, k: (np.full_like(f, 100), r, k), "contrast"),
        (lambda f, r, k: (210 - 5 * (210 - f) / 175, r, k), "contrast"),
        (lambda f, r, k: (np.where(f < 100, 35, 210), r, k), "insufficient_stratum"),
        (lambda f, r, k: (f, r, {**k, "normal": [2, 0]}), "invalid_input"),
        (lambda f, r, k: (f, r, {**k, "normal": [True, 0]}), "invalid_input"),
        (lambda f, r, k: (f, r, {**k, "blur_sigma": True}), "invalid_input"),
        (lambda f, r, k: (f, r, {**k, "blur_sigma": float("nan")}), "invalid_input"),
        (lambda f, r, k: (f, r, {**k, "blur_sigma": 0}), "invalid_input"),
        (lambda f, r, k: (f, r, {**k, "polarity": "automatic"}), "invalid_input"),
        (lambda f, r, k: (f, r[:2], k), "invalid_input"),
        (lambda f, r, k: (f.astype(complex), r, k), "invalid_input"),
        (lambda f, r, k: (f[0], r, k), "invalid_input"),
    ],
)
def test_invalid_or_unsupported_inputs_are_typed(change, reason):
    field, ring, normal, sigma = fixture()
    field, ring, kwargs = change(field, ring, {"normal": normal, "blur_sigma": sigma})
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations.prepare_segment_observations(field, ring, **kwargs)
    assert error.value.reason == reason


@pytest.mark.parametrize("where", ["field", "ring", "normal"])
def test_nonfinite_inputs_are_refused(where):
    field, ring, normal, sigma = fixture()
    {"field": field, "ring": ring, "normal": normal}[where].flat[0] = np.nan
    with pytest.raises(observations.ObservationPreparationError):
        observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)


def test_resource_caps_refuse_before_seed_or_selection_work(monkeypatch):
    field, ring, normal, sigma = fixture()
    monkeypatch.setattr(observations, "MAX_SOURCE_PIXELS", field.size - 1)
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)
    assert error.value.reason == "work_limit"
    monkeypatch.setattr(observations, "MAX_SOURCE_PIXELS", field.size)
    monkeypatch.setattr(observations, "MAX_CROP_PIXELS", 20)
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations.prepare_segment_observations(field, ring, normal=normal, blur_sigma=sigma)
    assert error.value.reason == "work_limit"


def test_crossing_work_cap_is_a_refusal_not_silent_subsampling(monkeypatch):
    monkeypatch.setattr(observations, "MAX_CROSSINGS", 10)
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations._crossings(np.indices((10, 10)).sum(axis=0) % 2)
    assert error.value.reason == "work_limit"


@pytest.mark.parametrize("dtype", [np.dtype("float32"), np.dtype(">f4"), np.dtype("float64")])
def test_strided_source_crop_and_selected_values_preserve_exact_dtype_and_bytes(dtype):
    field, ring, normal, sigma = fixture()
    backing = np.zeros((2 * field.shape[0], 2 * field.shape[1]), dtype=dtype)
    strided = backing[::2, ::2]
    strided[:] = field
    assert not strided.flags.c_contiguous
    result = observations.prepare_segment_observations(
        strided, ring, normal=normal, blur_sigma=sigma
    )
    x0, y0, x1, y1 = result.crop_bounds
    expected = strided[y0:y1, x0:x1]
    expected_bytes = expected.tobytes(order="C")
    assert result.field.dtype == expected.dtype == dtype
    assert result.field.tobytes() == expected_bytes
    for pixels, values in (
        (result.training_pixels, result.training_values),
        (result.heldout_pixels, result.heldout_values),
    ):
        assert values.dtype == dtype
        assert values.tobytes() == expected[pixels[:, 1], pixels[:, 0]].tobytes()
    metadata = result.metadata()
    assert metadata["source_dtype"] == metadata["crop_dtype"] == dtype.str
    assert metadata["selected_values_dtype"] == dtype.str
    assert metadata["arithmetic_dtype"] == np.dtype("float64").str
    independent_hash = hashlib.sha256(
        f"{dtype.str}:{expected.shape}:".encode() + expected_bytes
    ).hexdigest()
    assert metadata["crop_sha256"] == independent_hash
    strided[:] = 0
    assert result.field.tobytes() == expected_bytes


def test_mutating_view_shape_dtype_or_base_cannot_change_snapshot_descriptors():
    result = prepare()
    before = result.metadata()
    original_shape = result.sensor_shape
    for name in (
        "field",
        "ring_points",
        "normal",
        "homography",
        "training_pixels",
        "training_values",
        "heldout_pixels",
        "heldout_values",
        "contour",
        "plane_contour",
    ):
        array = getattr(result, name)
        shape, dtype, data = array.shape, array.dtype, array.tobytes()
        # NumPy2.5 deprecates shape assignment but still allows it on read-only
        # arrays. Exercise that metadata path without suppressing product errors.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            array.shape = (array.size,)
            array.dtype = np.uint8
            array.base.shape = (1, array.base.size)
        fresh = getattr(result, name)
        assert fresh.shape == shape and fresh.dtype == dtype and fresh.tobytes() == data
        with pytest.raises(ValueError):
            array.base.setflags(write=True)
    assert result.sensor_shape == original_shape
    assert result.metadata() == before


@pytest.mark.parametrize("where", ["field", "ring", "normal"])
def test_finite_extended_precision_overflow_is_typed_before_float64_arithmetic(where):
    if np.finfo(np.longdouble).max <= np.finfo(float).max:
        pytest.skip("platform has no wider finite floating dtype")
    field, ring, normal, sigma = fixture()
    values = {
        "field": field.astype(np.longdouble),
        "ring": ring.astype(np.longdouble),
        "normal": normal.astype(np.longdouble),
    }
    huge = np.longdouble("1e4000")
    assert np.isfinite(huge)
    values[where].flat[0 if where != "field" else 76 + 72 * field.shape[1]] = huge
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations.prepare_segment_observations(
            values["field"], values["ring"], normal=values["normal"], blur_sigma=sigma
        )
    assert error.value.reason == "nonfinite"


def test_finite_percentile_median_intermediate_overflow_is_a_typed_refusal():
    field, ring, normal, sigma = fixture()
    extreme = np.where(field < 100, -1e308, 1e308)
    assert np.all(np.isfinite(extreme))
    with pytest.raises(observations.ObservationPreparationError) as error:
        observations.prepare_segment_observations(extreme, ring, normal=normal, blur_sigma=sigma)
    assert error.value.reason == "contrast"
