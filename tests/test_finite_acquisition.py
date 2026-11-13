"""Independent discrete-stage contracts; no renderer, fit or optical qualification."""

import json
import warnings

import cv2
import numpy as np
import pytest

from backend import finite_acquisition as acquisition
from backend import sheet, tone


def options(**changes):
    args = {
        "levels": np.array([8.0, 40.0]),
        "optical_kernel": np.array([[1.0]]),
        "post_kernel": np.array([[1.0]]),
        "output_shape": (2, 3),
        "output_to_source_index": np.array([[1.0, 0.0, -0.5], [0.0, 1.0, -0.5]]),
        "queries": np.array([[2, 1], [0, 0], [1, 1]]),
    }
    args.update(changes)
    return args


def stages(result):
    return dict(result.stages)


def all_pixels(shape):
    return np.array([[x, y] for y in range(shape[0]) for x in range(shape[1])], dtype=np.int64)


def test_identity_queries_are_ordered_array_indices_without_an_extra_half_pixel():
    coverage = np.array([[0, 0.25, 0.5], [0.75, 1, 0.125]], dtype=np.float64)
    result = acquisition.acquisition_mean(coverage, **options())
    expected = np.array([[8, 16, 24], [32, 40, 12]], dtype=np.float32)
    assert result.intensities == (12.0, 8.0, 40.0)
    assert result.statuses == ("resolved",) * 3
    for name in ("source_linear", "optical_linear", "rectified", "final"):
        np.testing.assert_array_equal(stages(result)[name], expected)
    assert result.adequacy == "not_evaluated"
    assert result.physical_qualification is False


@pytest.mark.parametrize("phase", [0.0, 0.2, 0.25, 0.4, 0.5, 0.6, 0.75, 0.8])
def test_fractional_keys_phases_and_replicated_borders_match_separate_legacy_sampler(phase):
    coverage = np.array([[0.0, 1.0, 0.125, 0.5], [0.75, 0.25, 1.0, 0.0], [1.0, 0.5, 0.0, 0.25]])
    shape = (4, 5)
    matrix = np.array([[1.0, 0.0, phase - 1.5], [0.0, 1.0, -0.25]])
    result = acquisition.acquisition_mean(
        coverage,
        **options(output_shape=shape, output_to_source_index=matrix, queries=all_pixels(shape)),
    )
    source = (8 + 32 * coverage.astype(np.float32).astype(np.float64)).astype(np.float32)
    yy, xx = np.indices(shape, dtype=float)
    expected = sheet.sample_keys(source, xx + phase - 1, yy + 0.25).astype(np.float32)
    np.testing.assert_allclose(stages(result)["rectified"], expected, rtol=0, atol=1e-5)
    np.testing.assert_allclose(result.intensities, expected.ravel(), rtol=0, atol=1e-5)


@pytest.mark.parametrize("shape", [(1, 1), (1, 5), (5, 1), (3, 5)])
def test_noncentrosymmetric_correlation_reflect101_and_singleton_axes(shape):
    coverage = (np.arange(np.prod(shape)).reshape(shape) % 5).astype(float) / 4
    optical = np.zeros((3, 5))
    optical[0, 4], optical[1, 0], optical[2, 2] = 0.125, 0.25, 0.625
    post = np.zeros((3, 3))
    post[0, 0], post[2, 1] = 0.25, 0.75
    result = acquisition.acquisition_mean(
        coverage,
        **options(
            output_shape=shape,
            optical_kernel=optical,
            post_kernel=post,
            queries=all_pixels(shape),
        ),
    )
    source = (8 + 32 * coverage.astype(np.float32).astype(np.float64)).astype(np.float32)
    expected_optical = cv2.filter2D(source, -1, optical, borderType=cv2.BORDER_REFLECT_101)
    expected_final = cv2.filter2D(expected_optical, -1, post, borderType=cv2.BORDER_REFLECT_101)
    np.testing.assert_allclose(
        stages(result)["optical_linear"], expected_optical, rtol=0, atol=1e-5
    )
    np.testing.assert_allclose(stages(result)["final"], expected_final, rtol=0, atol=1e-5)


def test_one_hot_kernel_proves_correlation_direction_at_every_border():
    coverage = np.array([[0, 0.25, 0.5], [0.75, 1, 0.125]])
    kernel = np.zeros((3, 3))
    kernel[0, 2] = 1
    result = acquisition.acquisition_mean(
        coverage, **options(optical_kernel=kernel, queries=all_pixels(coverage.shape))
    )
    # REFLECT_101 maps requested rows [-1,0] to [1,0], columns [1,2,3] to [1,2,1].
    expected = np.array([[40, 12, 40], [16, 24, 16]], dtype=np.float32)
    np.testing.assert_array_equal(stages(result)["optical_linear"], expected)
    np.testing.assert_array_equal(result.intensities, expected.ravel())


@pytest.mark.parametrize("complement,expected", [(False, -6.25), (True, 106.25)])
def test_signed_keys_undershoot_and_complementary_overshoot_are_not_clamped(complement, expected):
    coverage = np.array([[0.0, 0.0, 1.0, 1.0]])
    if complement:
        coverage = 1 - coverage
    result = acquisition.acquisition_mean(
        coverage,
        **options(
            levels=[0, 100],
            output_shape=(1, 1),
            output_to_source_index=[[0, 0, 0.5], [0, 0, 0]],
            queries=[[0, 0]],
        ),
    )
    assert result.statuses == ("resolved",)
    assert result.intensities == (expected,)
    assert stages(result)["final"][0, 0] == expected


def linear_code(code):
    value = code / 255
    return 255 * (value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)


def encoded_code(light):
    value = max(float(light), 0) / 255
    encoded = 255 * (12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055)
    return round(min(255, max(0, encoded)))


@pytest.mark.parametrize("half_code", [0.5, 10.5, 40.5, 128.5, 254.5])
def test_grayscale_encoding_straddles_quantization_threshold_before_keys(half_code):
    coverage = np.array([[0.0, 1.0]])
    levels = [linear_code(half_code - 0.01), linear_code(half_code + 0.01)]
    args = options(levels=levels, output_shape=(1, 2), queries=[[0, 0], [1, 0]])
    decoded = acquisition.acquisition_mean(coverage, **args, srgb8=True)
    unquantized = acquisition.acquisition_mean(coverage, **args)
    actual_source = stages(decoded)["optical_linear"]
    codes = np.array([[encoded_code(x) for x in actual_source[0]]], dtype=np.uint8)
    assert codes.tolist() == [[int(half_code - 0.5), int(half_code + 0.5)]]
    np.testing.assert_array_equal(stages(decoded)["encoded"], codes)
    rgb = np.repeat(codes[:, :, None], 3, axis=2)
    reference = tone.linear_mix(rgb)
    np.testing.assert_array_equal(stages(decoded)["decoded_linear"], reference)
    np.testing.assert_array_equal(decoded.intensities, reference.ravel())
    assert decoded.intensities != unquantized.intensities


def test_all_256_codes_preserve_the_sequential_float32_channel_mix():
    codes = np.arange(256, dtype=np.uint8).reshape(16, 16)
    coverage = np.array([linear_code(float(x)) / 255 for x in codes.flat]).reshape(codes.shape)
    result = acquisition.acquisition_mean(
        coverage,
        **options(levels=[0, 255], output_shape=codes.shape, queries=all_pixels(codes.shape)),
        srgb8=True,
    )
    np.testing.assert_array_equal(stages(result)["encoded"], codes)
    expected = tone.linear_mix(np.repeat(codes[:, :, None], 3, axis=2))
    np.testing.assert_array_equal(stages(result)["decoded_linear"], expected)
    # A one-channel float32 LUT is not the declared sequence of three rounded products/sums.
    assert np.any(expected != tone.linear_from_encoded(codes).astype(np.float32))


def test_raw_kernel_coefficients_are_preserved_rather_than_renormalized():
    kernel = np.array([[np.nextafter(np.float32(1), np.float32(2))]], dtype=np.float32)
    result = acquisition.acquisition_mean(
        np.zeros((2, 3)), **options(levels=[100, 200], optical_kernel=kernel)
    )
    expected = np.float32(100 * float(kernel[0, 0]))
    assert expected > 100
    np.testing.assert_array_equal(stages(result)["optical_linear"], np.full((2, 3), expected))


def test_extreme_supported_map_saturates_replicated_borders_without_integer_overflow():
    result = acquisition.acquisition_mean(
        np.array([[0, 0.25, 0.5], [0.75, 1, 0.125]]),
        **options(output_to_source_index=[[0, 0, -1e6], [0, 0, 1e6]]),
    )
    assert result.intensities == (32.0,) * 3


@pytest.mark.parametrize("srgb8", [False, True])
def test_insufficient_work_retains_every_query_without_attempting_a_stage(monkeypatch, srgb8):
    def forbidden(*args, **kwargs):
        raise AssertionError("numerical stage executed after preflight refusal")

    monkeypatch.setattr(acquisition, "_correlate", forbidden)
    monkeypatch.setattr(acquisition, "_resample", forbidden)
    monkeypatch.setattr(acquisition, "_encode", forbidden)
    kernel = np.ones((3, 3)) / 9
    required = 6 * (1 + 9 + (4 if srgb8 else 0)) + 6 * (16 + 9)
    result = acquisition.acquisition_mean(
        np.zeros((2, 3)),
        **options(optical_kernel=kernel, post_kernel=kernel),
        srgb8=srgb8,
        max_work=required - 1,
    )
    assert result.required_work == required
    assert result.performed_work == 0
    assert result.intensities == (None,) * 3
    assert result.statuses == ("work_limit",) * 3
    assert result.stages == ()
    assert type(result.numeric_workspace_bound_bytes) is int


def test_exact_work_budget_completes_and_public_scalar_payload_is_native_json():
    required = 6 * (1 + 1) + 6 * (16 + 1)
    result = acquisition.acquisition_mean(np.zeros((2, 3)), **options(), max_work=required)
    assert result.required_work == result.performed_work == required
    assert result.statuses == ("resolved",) * 3
    payload = vars(result).copy()
    payload["stages"] = [(name, value.tolist()) for name, value in result.stages]
    json.dumps(payload, allow_nan=False)


def test_input_snapshots_survive_mutation_during_first_stage(monkeypatch):
    coverage = np.array([[0, 0.25, 0.5], [0.75, 1, 0.125]], dtype=np.float32)
    kwargs = options()
    baseline = acquisition.acquisition_mean(coverage, **kwargs)
    original = acquisition._correlate
    mutated = False

    def mutate_then_filter(image, kernel):
        nonlocal mutated
        if not mutated:
            mutated = True
            coverage[:] = 0
            kwargs["levels"][:] = 0
            kwargs["optical_kernel"][:] = 0
            kwargs["post_kernel"][:] = 0
            kwargs["output_to_source_index"][:] = 0
            kwargs["queries"][:] = 0
        return original(image, kernel)

    monkeypatch.setattr(acquisition, "_correlate", mutate_then_filter)
    result = acquisition.acquisition_mean(coverage, **kwargs)
    assert mutated
    assert result.input_sha256 == baseline.input_sha256
    assert result.intensities == baseline.intensities
    for (left_name, left), (right_name, right) in zip(result.stages, baseline.stages, strict=True):
        assert left_name == right_name
        np.testing.assert_array_equal(left, right)


def test_every_returned_stage_is_bytes_backed_and_cannot_be_made_writable():
    result = acquisition.acquisition_mean(np.zeros((2, 3)), **options(), srgb8=True)
    for _, array in result.stages:
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array.setflags(write=True)
        with pytest.raises(ValueError):
            array.flat[0] = 1


def test_input_hash_binds_all_scientific_inputs_and_query_order():
    coverage = np.array([[0, 0.25, 0.5], [0.75, 1, 0.125]])
    baseline = acquisition.acquisition_mean(coverage, **options()).input_sha256
    cases = [
        (coverage + np.array([[0.125, 0, 0], [0, 0, 0]]), {}),
        (coverage, {"levels": [9, 40]}),
        (coverage, {"optical_kernel": [[0, 0, 0], [0, 0.5, 0.5], [0, 0, 0]]}),
        (coverage, {"post_kernel": [[0, 0, 0], [0, 0.5, 0.5], [0, 0, 0]]}),
        (coverage, {"output_to_source_index": [[1, 0, -0.25], [0, 1, -0.5]]}),
        (coverage, {"queries": [[1, 1], [0, 0], [2, 1]]}),
        (coverage, {"output_shape": (3, 3)}),
        (coverage, {"srgb8": True}),
    ]
    hashes = [
        acquisition.acquisition_mean(cov, **options(**changes)).input_sha256
        for cov, changes in cases
    ]
    assert all(value != baseline for value in hashes)
    assert len(set(hashes)) == len(hashes)
    assert acquisition.acquisition_mean(coverage.copy(), **options()).input_sha256 == baseline


@pytest.mark.parametrize(
    "changes",
    [
        {"levels": [0, np.nan]},
        {"levels": [-1, 1]},
        {"levels": [0, 256]},
        {"levels": [0, 1j]},
        {"levels": [0]},
        {"levels": [0, 10**400]},
        {"optical_kernel": [[1, 0]]},
        {"optical_kernel": [[1.01]]},
        {"optical_kernel": [[np.inf]]},
        {"optical_kernel": [[-1]]},
        {"post_kernel": np.ones((33, 1)) / 33},
        {"output_shape": (0, 3)},
        {"output_shape": (257, 256)},
        {"output_shape": (True, 3)},
        {"output_shape": (2.0, 3)},
        {"output_to_source_index": [[1, 0, 1e6 + 1], [0, 1, 0]]},
        {"output_to_source_index": [[1, 0, np.inf], [0, 1, 0]]},
        {"output_to_source_index": np.eye(3)},
        {"queries": [[True, False]]},
        {"queries": [[0.0, 0.0]]},
        {"queries": [[-1, 0]]},
        {"queries": [[3, 0]]},
        {"queries": []},
        {"queries": np.zeros((4097, 2), dtype=int)},
        {"srgb8": np.bool_(True)},
        {"srgb8": 1},
        {"max_work": True},
        {"max_work": 1.0},
        {"max_work": 0},
        {"max_work": acquisition.MAX_WORK + 1},
    ],
)
def test_invalid_options_are_refused_before_any_stage(monkeypatch, changes):
    def forbidden(*args, **kwargs):
        raise AssertionError("stage called with invalid options")

    monkeypatch.setattr(acquisition, "_correlate", forbidden)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValueError):
            acquisition.acquisition_mean(np.zeros((2, 3)), **options(**changes))


@pytest.mark.parametrize(
    "coverage",
    [np.empty((0, 3)), np.zeros((257, 256)), [[-0.1]], [[1.1]], [[np.nan]], [[np.inf]], [[1j]]],
)
def test_invalid_coverage_is_refused(coverage):
    with pytest.raises(ValueError):
        acquisition.acquisition_mean(coverage, **options())


def test_finite_extended_precision_outside_binary64_is_a_typed_refusal():
    if np.finfo(np.longdouble).max <= np.finfo(float).max:
        pytest.skip("this platform has no wider floating input")
    levels = np.array([0, np.finfo(np.longdouble).max], dtype=np.longdouble)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValueError):
            acquisition.acquisition_mean(np.zeros((2, 3)), **options(levels=levels))
