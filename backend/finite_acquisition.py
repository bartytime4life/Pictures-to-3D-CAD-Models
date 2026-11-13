"""Supplied-cell acquisition means; no calibration, inverse, or trace integration.

The input is a source-cell material fraction, not a point indicator. Explicit
finite kernels are correlated with REFLECT_101 borders. Keys resampling uses
replicated borders and signed weights. The optional grayscale sRGB8 branch
uses ties-to-even encoding and a sequential float32 Rec.709 decoding mix.
These declared numerical stages are hypotheses, not a physical camera model.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

MAX_CELLS = 65_536
MAX_QUERIES = 4096
MAX_KERNEL = 31
MAX_WORK = 100_000_000


@dataclass(frozen=True)
class AcquisitionMean:
    intensities: tuple[float | None, ...]
    statuses: tuple[str, ...]
    stages: tuple[tuple[str, np.ndarray], ...]
    input_sha256: str
    required_work: int
    performed_work: int
    numeric_workspace_bound_bytes: int
    adequacy: str = "not_evaluated"
    physical_qualification: bool = False


def _integer(value, minimum, maximum, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")  # noqa: TRY004 -- one input-refusal API
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
    return int(value)


def _dimensions(value, name):
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"{name} must be (rows, columns)")
    rows, cols = (_integer(x, 1, MAX_CELLS, name) for x in value)
    if rows * cols > MAX_CELLS:
        raise ValueError(f"{name} exceeds {MAX_CELLS} cells")
    return rows, cols


def _array(value, shape, name):
    if np.shape(value) != shape or np.iscomplexobj(value):
        raise ValueError(f"{name} has invalid shape or complex values")
    try:
        with np.errstate(over="ignore", invalid="ignore"):
            a = np.array(value, dtype=np.float64, copy=True)
    except (OverflowError, TypeError, ValueError):
        raise ValueError(f"{name} must contain binary64 finite numbers") from None
    if not np.isfinite(a).all():
        raise ValueError(f"{name} must be finite")
    return a


def _kernel(value, name):
    shape = np.shape(value)
    if len(shape) != 2 or any(not 1 <= n <= MAX_KERNEL or n % 2 != 1 for n in shape):
        raise ValueError(f"{name} must have odd dimensions <= {MAX_KERNEL}")
    a = _array(value, shape, name)
    if np.any((a < 0) | (a > 1.000002)) or abs(math.fsum(a.flat) - 1) > 2e-6:
        raise ValueError(f"{name} must be nonnegative and sum to one within 2e-6")
    # Preserve represented coefficients, including float32 coefficient sums.
    return a


def _freeze(a):
    a = np.ascontiguousarray(a)
    return np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)


def _correlate(image, kernel):
    ry, rx = (n // 2 for n in kernel.shape)
    # NumPy reflect excludes the edge sample, matching REFLECT_101. For an axis
    # of length one the reflected extension is necessarily constant.
    padded = np.pad(image.astype(np.float64), ((ry, ry), (0, 0)), mode="reflect")
    padded = np.pad(padded, ((0, 0), (rx, rx)), mode="reflect")
    out = np.zeros(image.shape, np.float64)
    h, w = image.shape
    for j, row in enumerate(kernel):
        for i, weight in enumerate(row):
            out += weight * padded[j : j + h, i : i + w]
    return out.astype(np.float32)


def _weights(f):
    g = 1 - f
    return (
        -f * g * g / 2,
        g * (g * g + 3 * f * g + f * f / 2),
        f * (g * g / 2 + 3 * f * g + f * f),
        -f * f * g / 2,
    )


def _resample(image, shape, matrix):
    yy, xx = np.indices(shape, dtype=np.float64)
    # The matrix maps output geometric pixel centres to source ARRAY indices.
    u = matrix[0, 0] * (xx + 0.5) + matrix[0, 1] * (yy + 0.5) + matrix[0, 2]
    v = matrix[1, 0] * (xx + 0.5) + matrix[1, 1] * (yy + 0.5) + matrix[1, 2]
    # Replicated borders permit saturation before integer conversion; this also
    # avoids int64 overflow on a finite but extreme supplied affine map.
    u, v = np.clip(u, -2, image.shape[1] + 1), np.clip(v, -2, image.shape[0] + 1)
    ix, iy = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    wx, wy = _weights(u - ix), _weights(v - iy)
    out = np.zeros(shape, np.float64)
    for j in range(4):
        row = np.zeros(shape, np.float64)
        sy = np.clip(iy + j - 1, 0, image.shape[0] - 1)
        for i in range(4):
            row += wx[i] * image[sy, np.clip(ix + i - 1, 0, image.shape[1] - 1)]
        out += wy[j] * row
    return out.astype(np.float32)


def _decode(values):
    v = np.asarray(values, np.float64) / 255
    return 255 * np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def _encode(values):
    v = np.maximum(np.asarray(values, np.float64), 0) / 255
    encoded = 255 * np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)
    return np.rint(np.clip(encoded, 0, 255)).astype(np.uint8)


def acquisition_mean(
    coverage,
    *,
    levels,
    optical_kernel,
    output_shape,
    output_to_source_index,
    post_kernel,
    queries,
    srgb8=False,
    max_work=MAX_WORK,
):
    """Predict ordered intensity queries through a declared discrete acquisition.

    ``coverage[j,i]`` is material area / source-cell area. Levels are supplied
    [background, material] linear values on a 0..255 scale. ``queries`` contains
    integer [x,y] OUTPUT array indices. The 2x3 affine matrix maps output pixel
    centres (x+.5,y+.5) directly to source array-index coordinates. A half-pixel
    photo-coordinate correction must already be incorporated in that map.

    Work counts scalar kernel products and Keys taps, plus source mixing cells;
    it is not a timing estimate. A whole-image budget refusal returns one unknown
    per requested query, no evaluated stages, and performed_work=0. Input errors
    raise ValueError before the numerical stages. The numeric workspace bound
    excludes Python/allocator overhead and caller-owned input storage.
    """
    if type(srgb8) is not bool:
        raise ValueError("srgb8 must be a boolean")
    source_shape = _dimensions(tuple(np.shape(coverage)), "source shape")
    shape = _dimensions(output_shape, "output shape")
    cov = _array(coverage, source_shape, "coverage")
    if np.any((cov < 0) | (cov > 1)):
        raise ValueError("coverage must lie in [0,1]")
    level = _array(levels, (2,), "levels")
    if np.any((level < 0) | (level > 255)):
        raise ValueError("levels must lie in [0,255]")
    optical, post = _kernel(optical_kernel, "optical kernel"), _kernel(post_kernel, "post kernel")
    matrix = _array(output_to_source_index, (2, 3), "output map")
    if np.max(np.abs(matrix)) > 1e6:
        raise ValueError("output map exceeds coordinate limit")
    qshape = np.shape(queries)
    if len(qshape) != 2 or qshape[1] != 2 or not 1 <= qshape[0] <= MAX_QUERIES:
        raise ValueError("queries must have shape (1..4096,2)")
    q = np.asarray(queries)
    if q.dtype.kind not in "iu" or np.any(q < 0):
        raise ValueError("queries must contain nonnegative integers")
    if np.any(q[:, 0] >= shape[1]) or np.any(q[:, 1] >= shape[0]):
        raise ValueError("query outside output image")
    q = q.astype(np.int64, copy=True)
    budget = _integer(max_work, 1, MAX_WORK, "max_work")
    source_cells, output_cells = math.prod(source_shape), math.prod(shape)
    required = source_cells * (1 + optical.size + (4 if srgb8 else 0))
    required += output_cells * (16 + post.size)
    # A row/column pad can greatly exceed the input cell count on a thin image.
    # Both pad allocations coexist while the second np.pad is being evaluated.
    workspace = (
        512 * (source_cells + output_cells)
        + 8
        * (
            (source_shape[0] + optical.shape[0] - 1) * source_shape[1]
            + (source_shape[0] + optical.shape[0] - 1) * (source_shape[1] + optical.shape[1] - 1)
            + (shape[0] + post.shape[0] - 1) * shape[1]
            + (shape[0] + post.shape[0] - 1) * (shape[1] + post.shape[1] - 1)
        )
        + 262144
    )
    digest = hashlib.sha256()
    for name, a in (
        ("coverage", cov),
        ("levels", level),
        ("optical", optical),
        ("post", post),
        ("map", matrix),
        ("queries", q),
    ):
        digest.update(repr((name, a.shape, a.dtype.str)).encode())
        digest.update(a.tobytes(order="C"))
    digest.update(repr((shape, srgb8, "finite-acquisition-v1")).encode())
    binding = digest.hexdigest()
    if required > budget:
        return AcquisitionMean(
            (None,) * len(q), ("work_limit",) * len(q), (), binding, required, 0, workspace
        )
    # Match the declared source coverage-storage stage before brightness mixing.
    cov32 = cov.astype(np.float32)
    cov64 = cov32.astype(np.float64)
    source = (level[0] * (1 - cov64) + level[1] * cov64).astype(np.float32)
    optical_image = _correlate(source, optical)
    stages = [("coverage", cov32), ("source_linear", source), ("optical_linear", optical_image)]
    measurement = optical_image
    if srgb8:
        encoded = _encode(optical_image)
        lut = _decode(np.arange(256)).astype(np.float32)
        measurement = np.zeros(source_shape, np.float32)
        for weight in (0.2126, 0.7152, 0.0722):
            measurement += np.float32(weight) * lut[encoded]
        stages.extend((("encoded", encoded), ("decoded_linear", measurement)))
    rectified = _resample(measurement, shape, matrix)
    final = _correlate(rectified, post)
    stages.extend((("rectified", rectified), ("final", final)))
    if not all(np.isfinite(a).all() for _, a in stages):
        raise ArithmeticError("nonfinite acquisition stage")
    values = tuple(float(final[y, x]) for x, y in q)
    return AcquisitionMean(
        values,
        ("resolved",) * len(q),
        tuple((name, _freeze(a)) for name, a in stages),
        binding,
        required,
        required,
        workspace,
    )
