"""A separate float64 linear acquisition model, without storage/encoding rounds.

The fixed operator correlates supplied raw kernels using REFLECT_101, samples
with signed Keys weights and replicated borders, and gathers ordered queries.
It is defined by the computed binary64 sampling indices/weights; arithmetic
error estimates do not cover placement sensitivity of an ideal real affine map.
This model is not the rounded finite_acquisition evaluator or a calibrated PSF.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

from . import finite_acquisition as validation

MAX_CHANNELS = 6
MAX_WORK = validation.MAX_WORK
_EPS = 2.0**-52
_UNIT = 2.0**-53
_TINY = math.ulp(0.0)


@dataclass(frozen=True)
class LinearAcquisition:
    query_values: np.ndarray | None
    constant_response: np.ndarray | None
    statuses: tuple[str, ...]
    estimated_errors: tuple[float, ...] | None
    constant_estimated_error: float | None
    error_components: tuple[tuple[str, tuple[float, ...]], ...]
    input_sha256: str
    operator_sha256: str
    supplied_channels: int
    required_work: int
    performed_work: int
    numeric_workspace_bound_bytes: int
    keys_l1_bound: float | None
    error: str | None = None
    arithmetic_error_certified: bool = False
    tap_placement_error_included: bool = False
    adequacy: str = "not_evaluated"
    physical_qualification: bool = False

    def to_dict(self):
        """Return detached native data; unknown arrays remain absent, not zeros."""
        return {
            "query_values": None if self.query_values is None else self.query_values.tolist(),
            "constant_response": (
                None if self.constant_response is None else self.constant_response.tolist()
            ),
            "statuses": list(self.statuses),
            "estimated_errors": (
                None if self.estimated_errors is None else list(self.estimated_errors)
            ),
            "constant_estimated_error": self.constant_estimated_error,
            "error_components": {name: list(values) for name, values in self.error_components},
            "input_sha256": self.input_sha256,
            "operator_sha256": self.operator_sha256,
            "supplied_channels": self.supplied_channels,
            "required_work": self.required_work,
            "performed_work": self.performed_work,
            "numeric_workspace_bound_bytes": self.numeric_workspace_bound_bytes,
            "keys_l1_bound": self.keys_l1_bound,
            "error": self.error,
            "arithmetic_error_certified": self.arithmetic_error_certified,
            "tap_placement_error_included": self.tap_placement_error_included,
            "adequacy": self.adequacy,
            "physical_qualification": self.physical_qualification,
        }


def _digest_array(digest, name, array):
    digest.update(repr((name, array.shape, array.dtype.str)).encode())
    digest.update(array.tobytes(order="C"))


def _sampling(shape, source_shape, matrix):
    yy, xx = np.indices(shape, dtype=np.float64)
    u = matrix[0, 0] * (xx + 0.5) + matrix[0, 1] * (yy + 0.5) + matrix[0, 2]
    v = matrix[1, 0] * (xx + 0.5) + matrix[1, 1] * (yy + 0.5) + matrix[1, 2]
    u = np.clip(u, -2, source_shape[1] + 1)
    v = np.clip(v, -2, source_shape[0] + 1)
    ix, iy = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    wx, wy = validation._weights(u - ix), validation._weights(v - iy)
    # This is the unaggregated absolute row sum. Replicated duplicate taps can
    # cancel; retaining their separate absolute values is conservative.
    xnorm = sum(map(np.abs, wx))
    ynorm = sum(map(np.abs, wy))
    l1 = math.nextafter(float(np.max(xnorm * ynorm)) * (1 + 32 * _EPS), math.inf)
    return ix, iy, wx, wy, l1


def _correlate_many(fields, kernel):
    ry, rx = (n // 2 for n in kernel.shape)
    padded = np.pad(fields, ((ry, ry), (0, 0), (0, 0)), mode="reflect")
    padded = np.pad(padded, ((0, 0), (rx, rx), (0, 0)), mode="reflect")
    result = np.zeros(fields.shape, dtype=np.float64)
    h, w, _ = fields.shape
    for j, row in enumerate(kernel):
        for i, weight in enumerate(row):
            result += weight * padded[j : j + h, i : i + w]
    return result


def _resample_many(fields, shape, sampling):
    ix, iy, wx, wy, _ = sampling
    result = np.zeros((*shape, fields.shape[2]), dtype=np.float64)
    for j in range(4):
        row = np.zeros_like(result)
        sy = np.clip(iy + j - 1, 0, fields.shape[0] - 1)
        for i in range(4):
            sx = np.clip(ix + i - 1, 0, fields.shape[1] - 1)
            row += wx[i][..., None] * fields[sy, sx]
        result += wy[j][..., None] * row
    return result


def _gamma(operations):
    return operations * _UNIT / (1 - operations * _UNIT)


def _roundoff(scale, gain, operations):
    # gamma_n bounds dot-product accumulation under the usual floating model.
    # The additive term retains gradual-underflow arithmetic. Evaluation of the
    # guard and fixed-tap construction still make the final estimate engineering,
    # not a certified enclosure or an exact real-map error bound.
    return _gamma(operations) * gain * scale + operations * _TINY


def _finite(values, stage):
    if not np.isfinite(values).all():
        raise ArithmeticError(f"nonfinite {stage}")


def acquisition_linear(
    fields,
    *,
    optical_kernel,
    output_shape,
    output_to_source_index,
    post_kernel,
    queries,
    max_work=MAX_WORK,
):
    """Apply a fixed float64 operator to 1..6 finite signed source fields.

    ``fields`` is (rows,columns) or (rows,columns,channels). The 2x3 map takes
    output geometric centres (x+.5,y+.5) to source ARRAY indices. Kernels and
    grid/map/query caps match finite_acquisition. No coverage range is imposed:
    signed geometry derivatives are supported. Nonfinite input is refused.

    A constant channel is generated and evaluated beside ALL supplied channels,
    so A1 uses the same path without enforcing constant preservation. Successful
    values have shape (queries,supplied_channels); A1 has shape (queries,).

    With D=channels+1, required work is D*[N*(1+Ko)+M*(16+Kp)]: source packing,
    optical products, Keys products and post products. Coefficient preparation,
    validation and hashing are bounded separately by grid/query caps; this is
    not an instruction/time count. Work refusal occurs before coefficient/stage
    evaluation. Failed attempted stages retain their full declared charge.
    Returned arrays are bytes-backed immutable snapshots. Bounds exclude caller
    storage and Python/allocator overhead, and do not guarantee process RSS.
    Error estimates concern this operator's arithmetic on the supplied fields,
    not uncertainty/error in a cell-area or derivative evaluator. A supplied
    source error can be propagated separately by the optical/post coefficient
    L1 norms and the returned Keys L1 bound.
    """
    field_shape = np.shape(fields)
    if len(field_shape) not in (2, 3):
        raise ValueError("fields must have shape (rows,columns[,channels])")
    source_shape = validation._dimensions(tuple(field_shape[:2]), "source shape")
    channels = (
        validation._integer(field_shape[2], 1, MAX_CHANNELS, "channels")
        if len(field_shape) == 3
        else 1
    )
    source = validation._array(fields, field_shape, "fields").reshape(*source_shape, channels)
    shape = validation._dimensions(output_shape, "output shape")
    optical = validation._kernel(optical_kernel, "optical kernel")
    post = validation._kernel(post_kernel, "post kernel")
    matrix = validation._array(output_to_source_index, (2, 3), "output map")
    if np.max(np.abs(matrix)) > 1e6:
        raise ValueError("output map exceeds coordinate limit")
    qshape = np.shape(queries)
    if len(qshape) != 2 or qshape[1] != 2 or not 1 <= qshape[0] <= validation.MAX_QUERIES:
        raise ValueError("queries must have shape (1..4096,2)")
    query = np.asarray(queries)
    if query.dtype.kind not in "iu" or np.any(query < 0):
        raise ValueError("queries must contain nonnegative integers")
    if np.any(query[:, 0] >= shape[1]) or np.any(query[:, 1] >= shape[0]):
        raise ValueError("query outside output image")
    query = query.astype(np.int64, copy=True)
    budget = validation._integer(max_work, 1, MAX_WORK, "max_work")
    n, m, d = math.prod(source_shape), math.prod(shape), channels + 1
    required = d * (n * (1 + optical.size) + m * (16 + post.size))
    pads = (
        (source_shape[0] + optical.shape[0] - 1) * source_shape[1]
        + (source_shape[0] + optical.shape[0] - 1) * (source_shape[1] + optical.shape[1] - 1)
        + (shape[0] + post.shape[0] - 1) * shape[1]
        + (shape[0] + post.shape[0] - 1) * (shape[1] + post.shape[1] - 1)
    )
    workspace = 512 * d * (n + m) + 8 * d * pads + 32 * len(query) * (d + 2) + 65536
    operator_digest = hashlib.sha256()
    for name, array in (("optical", optical), ("post", post), ("map", matrix), ("queries", query)):
        _digest_array(operator_digest, name, array)
    operator_digest.update(repr((source_shape, shape, "finite-acquisition-linear-v1")).encode())
    operator_binding = operator_digest.hexdigest()
    input_digest = hashlib.sha256(operator_binding.encode())
    _digest_array(input_digest, "fields", source)
    binding = input_digest.hexdigest()
    performed = 0

    def result(
        status, *, values=None, constant=None, errors=None, components=(), l1=None, error=None
    ):
        return LinearAcquisition(
            None if values is None else validation._freeze(values),
            None if constant is None else validation._freeze(constant),
            (status,) * len(query),
            None if errors is None else tuple(map(float, errors[:channels])),
            None if errors is None else float(errors[channels]),
            components,
            binding,
            operator_binding,
            channels,
            required,
            performed,
            workspace,
            l1,
            error,
        )

    if required > budget:
        return result("work_limit")
    try:
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            sampling = _sampling(shape, source_shape, matrix)
            performed += n * d
            batch = np.ones((*source_shape, d), dtype=np.float64)
            batch[:, :, :channels] = source
            source_max = np.max(np.abs(batch), axis=(0, 1))
            performed += n * optical.size * d
            blurred = _correlate_many(batch, optical)
            _finite(blurred, "optical correlation")
            optical_max = np.max(np.abs(blurred), axis=(0, 1))
            performed += m * 16 * d
            rectified = _resample_many(blurred, shape, sampling)
            _finite(rectified, "Keys resampling")
            rectified_max = np.max(np.abs(rectified), axis=(0, 1))
            performed += m * post.size * d
            final = _correlate_many(rectified, post)
            _finite(final, "post correlation")
            go = math.nextafter(math.fsum(map(abs, optical.flat)), math.inf)
            gp = math.nextafter(math.fsum(map(abs, post.flat)), math.inf)
            gk = sampling[-1]
            eo = _roundoff(source_max, go, 2 * optical.size)
            ek = _roundoff(optical_max, gk, 16)
            ep = _roundoff(rectified_max, gp, 2 * post.size)
            terms = (gp * gk * eo, gp * ek, ep)
            errors = np.array([math.fsum(float(t[j]) for t in terms) for j in range(d)])
            errors = np.nextafter(errors * (1 + 64 * _EPS), math.inf)
            _finite(errors, "arithmetic error estimate")
        components = tuple(
            (name, tuple(map(float, values)))
            for name, values in zip(("optical", "Keys", "post"), terms, strict=True)
        )
        return result(
            "resolved",
            values=final[query[:, 1], query[:, 0], :channels],
            constant=final[query[:, 1], query[:, 0], channels],
            errors=errors,
            components=components,
            l1=gk,
        )
    except ArithmeticError as error:
        return result("numerical", error=str(error))
