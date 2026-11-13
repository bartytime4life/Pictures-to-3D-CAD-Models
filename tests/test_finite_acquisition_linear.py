"""Independent finite-stencil controls for the unrounded acquisition operator."""

import json
import math
import warnings

import numpy as np
import pytest

from backend import finite_acquisition_linear as linear


def arguments(**changes):
    options = {
        "optical_kernel": [[1.0]],
        "output_shape": (2, 3),
        "output_to_source_index": [[1, 0, -0.5], [0, 1, -0.5]],
        "post_kernel": [[1.0]],
        "queries": [[2, 1], [0, 0], [1, 1], [2, 1]],
    }
    options.update(changes)
    return options


def reflect(index, size):
    if size == 1:
        return 0
    value = index % (2 * size - 2)
    return value if value < size else 2 * size - 2 - value


def cubic(distance):
    x = abs(distance)
    if x <= 1:
        return 1.5 * x**3 - 2.5 * x**2 + 1
    if x < 2:
        return -0.5 * x**3 + 2.5 * x**2 - 4 * x + 2
    return 0.0


def adjoint_row(pixel, source_shape, options):
    """Scatter one query backwards; use unfactored Keys cubics and fsum."""
    optical = np.asarray(options["optical_kernel"])
    post = np.asarray(options["post_kernel"])
    matrix = np.asarray(options["output_to_source_index"])
    out_h, out_w = options["output_shape"]
    h, w = source_shape
    terms = {}
    for py, px in np.ndindex(post.shape):
        if post[py, px] == 0:
            continue
        oy = reflect(pixel[1] + py - post.shape[0] // 2, out_h)
        ox = reflect(pixel[0] + px - post.shape[1] // 2, out_w)
        u = float(matrix[0] @ [ox + 0.5, oy + 0.5, 1])
        v = float(matrix[1] @ [ox + 0.5, oy + 0.5, 1])
        u, v = min(w + 1, max(-2, u)), min(h + 1, max(-2, v))
        for sy in range(math.floor(v) - 1, math.floor(v) + 3):
            for sx in range(math.floor(u) - 1, math.floor(u) + 3):
                sample_weight = cubic(u - sx) * cubic(v - sy) * post[py, px]
                if sample_weight == 0:
                    continue
                iy, ix = min(h - 1, max(0, sy)), min(w - 1, max(0, sx))
                for ky, kx in np.ndindex(optical.shape):
                    if optical[ky, kx] == 0:
                        continue
                    y = reflect(iy + ky - optical.shape[0] // 2, h)
                    x = reflect(ix + kx - optical.shape[1] // 2, w)
                    terms.setdefault((y, x), []).append(sample_weight * optical[ky, kx])
    return {pixel: math.fsum(values) for pixel, values in terms.items()}


def oracle(fields, options):
    image = np.asarray(fields)
    if image.ndim == 2:
        image = image[:, :, None]
    rows = []
    constants = []
    for query in options["queries"]:
        weights = adjoint_row(query, image.shape[:2], options)
        rows.append(
            [
                math.fsum(weight * float(image[y, x, c]) for (y, x), weight in weights.items())
                for c in range(image.shape[2])
            ]
        )
        constants.append(math.fsum(weights.values()))
    return np.asarray(rows), np.asarray(constants)


def test_identity_preserves_binary64_values_and_order_without_calling_rounded_stages(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("the float64 operator must not call a rounded stage")

    monkeypatch.setattr(linear.validation, "_correlate", forbidden)
    monkeypatch.setattr(linear.validation, "_resample", forbidden)
    image = np.array([[1 + 2**-30, -3, 0], [5, 2**-60, 7]], dtype=np.float64)
    result = linear.acquisition_linear(image, **arguments())
    np.testing.assert_array_equal(result.query_values[:, 0], [7, 1 + 2**-30, 2**-60, 7])
    np.testing.assert_array_equal(result.constant_response, np.ones(4))
    assert result.query_values.dtype == np.float64
    assert result.statuses == ("resolved",) * 4
    assert result.required_work == result.performed_work == 228
    assert result.adequacy == "not_evaluated"
    assert result.physical_qualification is False
    assert result.arithmetic_error_certified is False
    assert result.tap_placement_error_included is False


@pytest.mark.parametrize("shape", [(1, 1), (1, 5), (5, 1), (3, 4)])
@pytest.mark.parametrize("phase", [0.0, 0.25, 0.5, 0.8])
def test_asymmetric_correlation_keys_phases_and_both_border_conventions(shape, phase):
    image = np.arange(math.prod(shape), dtype=np.float64).reshape(shape) - 2.75
    optical = np.zeros((3, 3))
    optical[0, 2], optical[1, 0], optical[2, 1] = 0.125, 0.25, 0.625
    post = np.zeros((3, 3))
    post[0, 0], post[2, 1] = 0.75, 0.25
    options = arguments(
        optical_kernel=optical,
        post_kernel=post,
        output_shape=(3, 5),
        output_to_source_index=[[1, 0, phase - 1.5], [0, 1, -0.75]],
        queries=[[0, 0], [4, 2], [2, 1]],
    )
    expected, constant = oracle(image, options)
    result = linear.acquisition_linear(image, **options)
    np.testing.assert_allclose(result.query_values, expected, rtol=0, atol=3e-13)
    np.testing.assert_allclose(result.constant_response, constant, rtol=0, atol=3e-14)
    assert np.max(np.abs(result.query_values - expected)) <= result.estimated_errors[0]


def test_backward_scatter_adjoint_agrees_with_forward_inner_product():
    fields = np.arange(12, dtype=float).reshape(3, 4) / 7 - 0.5
    options = arguments(
        optical_kernel=[[0, 0.125, 0], [0.25, 0, 0], [0, 0, 0.625]],
        post_kernel=[[0, 0, 0.5], [0, 0.5, 0], [0, 0, 0]],
        output_shape=(3, 4),
        output_to_source_index=[[0.75, 0.25, -0.5], [-0.25, 1, 0.25]],
        queries=[[0, 0], [3, 2], [1, 1], [0, 0]],
    )
    query_vector = [1.25, -2, 0.5, -0.75]
    back = {}
    for query, value in zip(options["queries"], query_vector, strict=True):
        for pixel, coefficient in adjoint_row(query, fields.shape, options).items():
            back.setdefault(pixel, []).append(value * coefficient)
    rhs = math.fsum(math.fsum(values) * fields[y, x] for (y, x), values in back.items())
    result = linear.acquisition_linear(fields, **options)
    lhs = math.fsum(
        value * got for value, got in zip(query_vector, result.query_values[:, 0], strict=True)
    )
    assert abs(lhs - rhs) <= math.fsum(map(abs, query_vector)) * result.estimated_errors[0]


def test_six_supplied_channels_include_five_signed_derivatives_and_charged_a1():
    coverage = np.arange(6, dtype=float).reshape(2, 3) / 5
    derivatives = np.stack([(-1) ** j * (j + 1) * (coverage - 0.4) for j in range(5)], axis=2)
    fields = np.dstack((coverage, derivatives))
    options = arguments(output_to_source_index=[[1, 0, -0.25], [0, 1, -0.5]])
    result = linear.acquisition_linear(fields, **options, max_work=798)
    expected, constant = oracle(fields, options)
    np.testing.assert_allclose(result.query_values, expected, rtol=0, atol=3e-14)
    np.testing.assert_allclose(result.constant_response, constant, rtol=0, atol=3e-14)
    assert result.supplied_channels == 6
    assert result.query_values.shape == (4, 6)
    assert len(result.estimated_errors) == 6
    assert result.required_work == result.performed_work == 798
    assert all(error >= 0 for error in result.estimated_errors)


def test_actual_constant_response_preserves_nonunit_kernel_sums_and_brightness_basis():
    coefficient = 1 + 2**-25
    coverage = np.array([[0, 0.25, 0.5], [0.75, 1, 0.125]])
    options = arguments(optical_kernel=[[coefficient]], post_kernel=[[coefficient]])
    result = linear.acquisition_linear(coverage, **options)
    np.testing.assert_array_equal(result.constant_response, [coefficient * coefficient] * 4)
    assert np.all(result.constant_response > 1)
    levels = (240.0, 30.0)
    direct = linear.acquisition_linear(levels[0] * (1 - coverage) + levels[1] * coverage, **options)
    design = np.column_stack(
        (result.constant_response - result.query_values[:, 0], result.query_values[:, 0])
    )
    profiled = design @ levels
    guard = direct.estimated_errors[0] + (abs(levels[0]) + abs(levels[1])) * (
        result.estimated_errors[0] + result.constant_estimated_error
    )
    np.testing.assert_allclose(profiled, direct.query_values[:, 0], rtol=0, atol=guard)
    incorrect = levels[0] + (levels[1] - levels[0]) * result.query_values[:, 0]
    assert np.max(np.abs(incorrect - profiled)) > 1e-6


def test_signed_keys_overshoot_is_retained_without_clamping():
    options = arguments(
        output_shape=(1, 1),
        output_to_source_index=[[0, 0, 0.5], [0, 0, 0]],
        queries=[[0, 0]],
    )
    result = linear.acquisition_linear([[0, 0, 1, 1]], **options)
    assert result.query_values[0, 0] == -0.0625
    assert result.constant_response[0] == 1


def test_cancellation_guard_uses_absolute_input_scale_not_only_output_magnitude():
    options = arguments(
        optical_kernel=[[0.5, 0, 0.5]],
        output_shape=(1, 1),
        output_to_source_index=[[0, 0, 1], [0, 0, 0]],
        queries=[[0, 0]],
    )
    image = [[1e12, 7, -1e12]]
    result = linear.acquisition_linear(image, **options)
    expected, _ = oracle(image, options)
    assert result.query_values[0, 0] == expected[0, 0] == 0
    assert result.estimated_errors[0] > 1e-5
    assert all(np.isfinite(values).all() for _, values in result.error_components)


def test_work_refusal_precedes_coefficients_and_numerical_stages(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("preflight refusal evaluated coefficients or a stage")

    for name in ("_sampling", "_correlate_many", "_resample_many"):
        monkeypatch.setattr(linear, name, forbidden)
    result = linear.acquisition_linear(np.zeros((2, 3, 6)), **arguments(), max_work=797)
    assert result.required_work == 798
    assert result.performed_work == 0
    assert result.query_values is result.constant_response is None
    assert result.estimated_errors is None
    assert result.statuses == ("work_limit",) * 4
    json.dumps(result.to_dict(), allow_nan=False)


def test_pathological_padding_workspace_includes_all_seven_evaluated_channels(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("oversized batch must stop before sampling")

    monkeypatch.setattr(linear, "_sampling", forbidden)
    kernel = np.zeros((31, 31))
    kernel[15, 15] = 1
    result = linear.acquisition_linear(
        np.zeros((1, 65536, 6)),
        **arguments(optical_kernel=kernel, output_shape=(1, 1), queries=[[0, 0]]),
    )
    pads = 7 * 8 * (31 * 65536 + 31 * 65566)
    live_fields = 8 * 65536 * (6 + 7)
    assert result.numeric_workspace_bound_bytes >= pads + live_fields
    assert result.required_work > linear.MAX_WORK
    assert result.performed_work == 0


def test_snapshots_and_immutable_result_arrays(monkeypatch):
    fields = np.arange(12, dtype=float).reshape(2, 3, 2)
    options = arguments(
        optical_kernel=np.array([[1.0]]),
        post_kernel=np.array([[1.0]]),
        output_to_source_index=np.array([[1, 0, -0.5], [0, 1, -0.5]]),
        queries=np.array([[2, 1], [0, 0], [1, 1], [2, 1]]),
    )
    baseline = linear.acquisition_linear(fields, **options)
    real = linear._correlate_many

    def mutate_then_correlate(batch, kernel):
        fields[:] = 123
        for name in ("optical_kernel", "post_kernel", "output_to_source_index", "queries"):
            options[name][:] = 0
        return real(batch, kernel)

    monkeypatch.setattr(linear, "_correlate_many", mutate_then_correlate)
    result = linear.acquisition_linear(fields, **options)
    np.testing.assert_array_equal(result.query_values, baseline.query_values)
    np.testing.assert_array_equal(result.constant_response, baseline.constant_response)
    assert result.input_sha256 == baseline.input_sha256
    for array in (result.query_values, result.constant_response):
        with pytest.raises(ValueError):
            array.flat[0] = 0
        with pytest.raises(ValueError):
            array.setflags(write=True)
    detached = result.to_dict()
    detached["query_values"][0][0] = 1000
    assert result.query_values[0, 0] != 1000


def test_hashes_bind_ordered_operator_and_field_snapshots_separately():
    fields = np.arange(6, dtype=float).reshape(2, 3)
    baseline = linear.acquisition_linear(fields, **arguments())
    changed_fields = linear.acquisition_linear(fields + 1, **arguments())
    assert changed_fields.operator_sha256 == baseline.operator_sha256
    assert changed_fields.input_sha256 != baseline.input_sha256
    for changes in (
        {"optical_kernel": [[1 + 2**-25]]},
        {"post_kernel": [[1 + 2**-25]]},
        {"output_to_source_index": [[1, 0, -0.25], [0, 1, -0.5]]},
        {"queries": [[0, 0], [2, 1], [1, 1], [2, 1]]},
    ):
        changed = linear.acquisition_linear(fields, **arguments(**changes))
        assert changed.operator_sha256 != baseline.operator_sha256
        assert changed.input_sha256 != baseline.input_sha256


@pytest.mark.parametrize("exception", [ArithmeticError, FloatingPointError])
def test_failed_optical_attempt_is_charged_and_retained_as_numerical_unknown(
    monkeypatch, exception
):
    def fail(*args, **kwargs):
        raise exception("injected represented arithmetic failure")

    monkeypatch.setattr(linear, "_correlate_many", fail)
    result = linear.acquisition_linear(np.zeros((2, 3)), **arguments())
    assert result.performed_work == 24  # source packing12 + optical products12.
    assert result.required_work == 228
    assert result.statuses == ("numerical",) * 4
    assert result.query_values is result.constant_response is None
    assert "injected" in result.error
    json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize("exception", [TypeError, ValueError])
def test_unexpected_stage_errors_propagate(monkeypatch, exception):
    def fail(*args, **kwargs):
        raise exception("unexpected stage contract failure")

    monkeypatch.setattr(linear, "_correlate_many", fail)
    with pytest.raises(exception, match="unexpected"):
        linear.acquisition_linear(np.zeros((2, 3)), **arguments())


@pytest.mark.parametrize("stage", ["optical", "Keys", "post"])
def test_nonfinite_computed_stages_never_return_fabricated_finite_values(monkeypatch, stage):
    real = linear._correlate_many
    count = 0

    def correlate(fields, kernel):
        nonlocal count
        count += 1
        if (stage == "optical" and count == 1) or (stage == "post" and count == 2):
            return np.full_like(fields, np.inf)
        return real(fields, kernel)

    monkeypatch.setattr(linear, "_correlate_many", correlate)
    if stage == "Keys":
        monkeypatch.setattr(
            linear, "_resample_many", lambda fields, shape, sampling: np.full((*shape, 2), np.nan)
        )
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        result = linear.acquisition_linear(np.zeros((2, 3)), **arguments())
    assert result.statuses == ("numerical",) * 4
    assert result.query_values is result.constant_response is None
    assert result.performed_work == {"optical": 24, "Keys": 216, "post": 228}[stage]
    json.dumps(result.to_dict(), allow_nan=False)


def test_finite_extreme_signed_fields_retain_a_real_overflow_as_unknown_without_warning():
    signs = np.array([-1, 1, 1, -1])
    fields = np.outer(signs, signs) * 1.7e308
    options = arguments(
        output_shape=(1, 1),
        output_to_source_index=[[0, 0, 1.5], [0, 0, 1.5]],
        queries=[[0, 0]],
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        result = linear.acquisition_linear(fields, **options)
    assert result.statuses == ("numerical",)
    assert result.query_values is result.constant_response is None
    assert result.performed_work == 96
    assert result.required_work == 98
    assert "Keys" in result.error
    json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize(
    "changes",
    [
        {"optical_kernel": [[-1.0]]},
        {"optical_kernel": [[1e308, 1e308, 1e308]]},
        {"optical_kernel": [[0.5, 0.5]]},
        {"optical_kernel": [[math.nan]]},
        {"post_kernel": [[1.001]]},
        {"output_shape": (1, 65537)},
        {"output_shape": (True, 3)},
        {"output_to_source_index": [[1, 0, math.inf], [0, 1, 0]]},
        {"output_to_source_index": [[1, 0, 1000001], [0, 1, 0]]},
        {"queries": [[0.0, 0.0]]},
        {"queries": [[True, False]]},
        {"queries": [[3, 0]]},
        {"queries": []},
        {"max_work": 0},
        {"max_work": True},
        {"max_work": 100000001},
    ],
)
def test_invalid_options_refused_before_stages(monkeypatch, changes):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid input reached stage setup")

    monkeypatch.setattr(linear, "_sampling", forbidden)
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        with pytest.raises(ValueError):
            linear.acquisition_linear(np.zeros((2, 3)), **arguments(**changes))


@pytest.mark.parametrize(
    "fields",
    [
        [],
        [1, 2],
        np.empty((0, 3)),
        np.zeros((1, 65537)),
        np.zeros((2, 3, 0)),
        np.zeros((2, 3, 7)),
        np.zeros((2, 3, 1, 1)),
        [[math.nan]],
        [[math.inf]],
        [[1j]],
        [[10**400]],
    ],
)
def test_invalid_fields_refused(fields):
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        with pytest.raises(ValueError):
            linear.acquisition_linear(fields, **arguments())
