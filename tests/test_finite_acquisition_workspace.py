"""Workspace metadata controls; padding shapes matter independently of cell count."""

import json
from dataclasses import asdict

import numpy as np
import pytest

from backend import finite_acquisition as acquisition


def one_tap(shape):
    kernel = np.zeros(shape)
    kernel[shape[0] // 2, shape[1] // 2] = 1
    return kernel


def refused(monkeypatch, source_shape, optical_shape, output_shape, post_shape, **changes):
    def forbidden(*args, **kwargs):
        pytest.fail("a preflight work refusal must not evaluate a numerical stage")

    for name in ("_correlate", "_resample", "_encode"):
        monkeypatch.setattr(acquisition, name, forbidden)
    options = {
        "levels": (8.0, 40.0),
        "optical_kernel": one_tap(optical_shape),
        "output_shape": output_shape,
        "output_to_source_index": ((1, 0, -0.5), (0, 1, -0.5)),
        "post_kernel": one_tap(post_shape),
        "queries": np.array([[0, 0], [0, 0]], dtype=np.int64),
        "max_work": 1,
    }
    options.update(changes)
    return acquisition.acquisition_mean(np.full(source_shape, 0.25, np.float32), **options)


@pytest.mark.parametrize("source_shape", [(1, 65_536), (65_536, 1)])
def test_thin_image_bound_covers_simultaneously_live_padding_and_source_arrays(
    monkeypatch, source_shape
):
    result = refused(monkeypatch, source_shape, (31, 31), (1, 1), (7, 7))
    h, w = source_shape
    # These two float64 pads coexist during the second assignment in _correlate.
    y_pad = (h + 30) * w * 8
    xy_pad = (h + 30) * (w + 30) * 8
    # Validated coverage, its float32 storage, separate float64 mix input, source.
    live_source = 65_536 * (8 + 4 + 8 + 4)
    proven_lower_bound = y_pad + xy_pad + live_source
    previous_bound = 512 * (65_536 + 1) + 131_072
    if h == 1:
        assert proven_lower_bound == 34_086_160
        assert proven_lower_bound > previous_bound
    assert result.numeric_workspace_bound_bytes >= proven_lower_bound
    assert result.required_work == 63_045_697
    assert result.intensities == (None, None)
    assert result.statuses == ("work_limit", "work_limit")
    assert result.performed_work == 0
    assert result.stages == ()


@pytest.mark.parametrize(
    ("source_shape", "optical_shape", "output_shape", "post_shape", "expected_bytes"),
    [
        ((96, 96), (11, 11), (64, 64), (7, 7), 7_324_224),
        ((96, 96), (25, 25), (80, 80), (7, 7), 8_579_104),
        ((1, 65_536), (31, 31), (1, 1), (7, 7), 66_330_832),
        ((65_536, 1), (31, 31), (1, 1), (7, 7), 50_602_432),
        ((1, 1), (1, 1), (1, 1), (1, 1), 263_200),
    ],
)
def test_preflight_workspace_metadata_for_typical_and_extreme_shapes(
    monkeypatch, source_shape, optical_shape, output_shape, post_shape, expected_bytes
):
    result = refused(monkeypatch, source_shape, optical_shape, output_shape, post_shape)
    assert type(result.numeric_workspace_bound_bytes) is int
    assert result.numeric_workspace_bound_bytes == expected_bytes
    assert result.performed_work == 0
    assert result.stages == ()
    json.dumps(asdict(result), allow_nan=False)


def test_post_padding_is_accounted_even_when_the_source_has_only_one_cell(monkeypatch):
    short = refused(monkeypatch, (1, 1), (1, 1), (1, 65_536), (1, 1))
    wide = refused(monkeypatch, (1, 1), (1, 1), (1, 65_536), (31, 31))
    old_padding = 2 * 65_536 * 8
    new_padding = (31 * 65_536 + 31 * 65_566) * 8
    assert wide.numeric_workspace_bound_bytes - short.numeric_workspace_bound_bytes == (
        new_padding - old_padding
    )
    assert wide.numeric_workspace_bound_bytes > 34_086_160
    assert short.intensities == wide.intensities == (None, None)


@pytest.mark.parametrize("srgb8", [False, True])
def test_workspace_refusal_retains_all_maximum_queries_and_native_metadata(monkeypatch, srgb8):
    result = refused(
        monkeypatch,
        (1, 1),
        (31, 31),
        (1, 1),
        (31, 31),
        queries=np.zeros((4096, 2), dtype=np.int64),
        srgb8=srgb8,
    )
    assert len(result.intensities) == len(result.statuses) == 4096
    assert all(value is None for value in result.intensities)
    assert set(result.statuses) == {"work_limit"}
    assert result.numeric_workspace_bound_bytes > 2 * 4096 * 2 * 8 + 2 * 31 * 31 * 8
    assert result.required_work == 1939 + (4 if srgb8 else 0)
    assert result.performed_work == 0
    json.dumps(asdict(result), allow_nan=False)


def test_metadata_update_does_not_change_ordered_identity_stage_values():
    result = acquisition.acquisition_mean(
        [[0, 0.25, 0.5], [0.75, 1, 0.125]],
        levels=(8, 40),
        optical_kernel=((1,),),
        output_shape=(2, 3),
        output_to_source_index=((1, 0, -0.5), (0, 1, -0.5)),
        post_kernel=((1,),),
        queries=np.array([[2, 1], [0, 0], [1, 1]], dtype=np.int64),
    )
    assert result.intensities == (12.0, 8.0, 40.0)
    assert result.required_work == result.performed_work == 114
    assert result.statuses == ("resolved",) * 3
    assert result.adequacy == "not_evaluated"
    assert result.physical_qualification is False
