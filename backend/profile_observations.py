"""Developer-only fixed sampling operators and conditional noise accounting.

No production trace or confidence display uses this module. Independent input-pixel
noise is a supplied hypothesis, not an estimate of a real camera's noise or PSF.
"""

import math
from dataclasses import dataclass

import numpy as np

from .sheet import _keys

MAX_PROFILE_SAMPLES = 512
MAX_SOURCE_PIXELS = 2048
MAX_MATRIX_CELLS = 500_000
MAX_FACTOR_WORK = 100_000_000
MAX_FILTER_TERMS = 200_000
MAX_FILTER_WORK = 50_000_000


def _frozen(array):
    result = np.array(array, dtype=np.float64, copy=True)
    result.flags.writeable = False
    return result


def _matrix(value, *, columns=None):
    shape = np.shape(value)
    if len(shape) != 2 or not all(shape):
        raise ValueError("a nonempty two-dimensional matrix is required")
    rows, cols = shape
    if rows > MAX_PROFILE_SAMPLES or cols > MAX_SOURCE_PIXELS or rows * cols > MAX_MATRIX_CELLS:
        raise ValueError("sampling matrix exceeds the declared allocation limits")
    if columns is not None and cols != columns:
        raise ValueError("matrix columns do not match the input pixels")
    result = np.asarray(value, dtype=np.float64)
    if not np.isfinite(result).all():
        raise ValueError("matrix must be finite")
    return result


@dataclass(frozen=True)
class KeysProfile:
    """Fixed index-coordinate Keys samples, including coalesced border replication."""

    pixels_xy: np.ndarray
    matrix: np.ndarray
    image_shape: tuple

    def sample(self, image):
        image = np.asarray(image)
        xy = self.pixels_xy
        if image.shape != self.image_shape:
            raise ValueError("image shape differs from the declared sampling geometry")
        values = image[xy[:, 1], xy[:, 0]].astype(np.float64)
        if not np.isfinite(values).all():
            raise ValueError("sampled input pixels must be finite")
        with np.errstate(over="ignore", invalid="ignore"):
            result = self.matrix @ values
        if not np.isfinite(result).all():
            raise ValueError("sampled profile overflow")
        return result

    def after_filter(self, kernel, *, border):
        """Compose a declared odd finite correlation kernel BEFORE these samples.

        Border is explicitly 'reflect101' or 'replicate'. This matches float64 linear
        filtering. Float32 storage/filter arithmetic and unknown earlier operators
        require separate discrepancy accounting. It does not infer a camera PSF.
        """
        shape = np.shape(kernel)
        if len(shape) != 2 or any(not 0 < n <= 15 or n % 2 != 1 for n in shape):
            raise ValueError("supply an odd 2-D filter no larger than 15 by 15")
        if border not in ("reflect101", "replicate"):
            raise ValueError("declare reflect101 or replicate filter borders")
        count = len(self.pixels_xy) * shape[0] * shape[1]
        if count > MAX_FILTER_TERMS or count * len(self.matrix) > MAX_FILTER_WORK:
            raise ValueError("filter composition exceeds the declared work limits")
        kernel = np.asarray(kernel, dtype=np.float64)
        if not np.isfinite(kernel).all():
            raise ValueError("filter coefficients must be finite")

        def index(value, size):
            if border == "replicate":
                return np.clip(value, 0, size - 1)
            if size == 1:
                return np.zeros_like(value)
            reflected = value % (2 * size - 2)
            return np.where(reflected < size, reflected, 2 * size - 2 - reflected)

        height, width = self.image_shape
        positions = []
        for j, i in np.ndindex(shape):
            x = index(self.pixels_xy[:, 0] + i - shape[1] // 2, width)
            y = index(self.pixels_xy[:, 1] + j - shape[0] // 2, height)
            positions.append(np.column_stack((x, y)))
        pixels, inverse = np.unique(np.stack(positions, axis=1).reshape(-1, 2), axis=0, return_inverse=True)
        if len(pixels) > MAX_SOURCE_PIXELS or len(self.matrix) * len(pixels) > MAX_MATRIX_CELLS:
            raise ValueError("composed sampling matrix exceeds the declared allocation limits")
        matrix = np.zeros((len(self.matrix), len(pixels)))
        inverse = inverse.reshape(len(self.pixels_xy), kernel.size)
        rows = np.arange(len(matrix))[:, None]
        with np.errstate(over="ignore", invalid="ignore"):
            for k, weight in enumerate(kernel.ravel()):
                np.add.at(matrix, (rows, inverse[:, k]), self.matrix * weight)
        if not np.isfinite(matrix).all():
            raise ValueError("composed operator is not finite")
        keep = np.any(matrix != 0, axis=0)
        pixels = pixels[keep].copy()
        pixels.flags.writeable = False
        return KeysProfile(pixels, _frozen(matrix[:, keep]), self.image_shape)


def keys_profile(image_shape, x, y):
    """Build the actual signed Keys operator for bounded 1-D coordinate arrays.

    Coordinates are index coordinates, as in sheet.sample_keys. Pixel centres for
    geometric forward models are pixels_xy + 0.5. Zero columns are removed; clipping
    happens before duplicate source-pixel weights are added, so covariance is correct
    at replicated borders too. Matrix rows remain distinct even when samples repeat.
    """
    if (len(image_shape) != 2 or any(isinstance(n, (bool, np.bool_)) or
            not isinstance(n, (int, np.integer)) or not 0 < n <= 10**9 for n in image_shape)):
        raise ValueError("image shape must contain two positive bounded integers")
    if np.shape(x) != np.shape(y) or len(np.shape(x)) != 1 or not 0 < np.size(x) <= MAX_PROFILE_SAMPLES:
        raise ValueError("coordinate arrays must have equal bounded nonempty 1-D shapes")
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    if not (np.isfinite(x).all() and np.isfinite(y).all()) or max(np.max(np.abs(x)), np.max(np.abs(y))) > 10**9:
        raise ValueError("sample coordinates must be finite and bounded")
    height, width = image_shape
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    terms, weights = [], []
    for j in range(-1, 3):
        for i in range(-1, 3):
            terms.append(np.column_stack((np.clip(x0 + i, 0, width - 1), np.clip(y0 + j, 0, height - 1))))
            weights.append(_keys(x - x0 - i) * _keys(y - y0 - j))
    terms = np.stack(terms, axis=1)
    pixels, inverse = np.unique(terms.reshape(-1, 2), axis=0, return_inverse=True)
    if len(pixels) > MAX_SOURCE_PIXELS or len(x) * len(pixels) > MAX_MATRIX_CELLS:
        raise ValueError("sampling matrix exceeds the declared allocation limits")
    matrix = np.zeros((len(x), len(pixels)))
    np.add.at(matrix, (np.arange(len(x))[:, None], inverse.reshape(len(x), 16)), np.stack(weights, axis=1))
    keep = np.any(matrix != 0, axis=0)
    pixels = pixels[keep].copy()
    pixels.flags.writeable = False
    return KeysProfile(pixels, _frozen(matrix[:, keep]), tuple(image_shape))


@dataclass(frozen=True)
class PixelNoise:
    """Compact SVD of L = S diag(input_standard_deviations).

    Retaining r singular modes yields W = diag(1/d) U.T and W L = V.T.
    Small singular modes are omitted at a recorded numerical threshold. This is a
    rank decision in floating arithmetic, not a physical noise floor or calibration.
    """

    matrix: np.ndarray
    input_std: np.ndarray
    left: np.ndarray
    singular_values: np.ndarray
    right: np.ndarray
    cutoff: float
    discarded_largest: float

    @classmethod
    def factor(cls, matrix, input_std):
        matrix = _matrix(matrix)
        rows, columns = matrix.shape
        if rows * columns * min(rows, columns) > MAX_FACTOR_WORK:
            raise ValueError("sampling SVD exceeds the declared work limit")
        if np.shape(input_std) not in ((), (columns,)):
            raise ValueError("supply one standard deviation or one for every input pixel")
        std = np.asarray(input_std, dtype=np.float64)
        if std.ndim == 0:
            std = np.full(columns, float(std))
        if std.shape != (columns,) or not np.isfinite(std).all() or np.any(std <= 0):
            raise ValueError("supply a positive finite standard deviation for every input pixel")
        with np.errstate(over="ignore", invalid="ignore"):
            noise = matrix * std
        if not np.isfinite(noise).all():
            raise ValueError("noise operator is not finite")
        left, values, right = np.linalg.svd(noise, full_matrices=False)
        cutoff = float(np.finfo(float).eps * max(noise.shape) * values[0])
        keep = values > cutoff
        if not keep.any():
            raise ValueError("sampling operator has no retained noise modes")
        discarded = float(values[~keep].max()) if (~keep).any() else 0.0
        return cls(_frozen(matrix), _frozen(std), _frozen(left[:, keep]),
                   _frozen(values[keep]), _frozen(right[keep]), cutoff, discarded)

    @property
    def rank(self):
        return len(self.singular_values)

    def _values(self, values):
        shape = np.shape(values)
        if len(shape) not in (1, 2) or shape[0] != self.matrix.shape[0] or (len(shape) == 2 and
                (not 0 < shape[1] <= MAX_SOURCE_PIXELS or shape[0] * shape[1] > MAX_MATRIX_CELLS)):
            raise ValueError("values must have bounded size and one row per observation")
        result = np.asarray(values, dtype=np.float64)
        if result.ndim not in (1, 2) or result.shape[0] != self.matrix.shape[0] or not np.isfinite(result).all():
            raise ValueError("values must be finite with one row per observation")
        return result

    def whiten(self, values):
        values = self._values(values)
        projected = self.left.T @ values
        scale = self.singular_values if values.ndim == 1 else self.singular_values[:, None]
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            result = projected / scale
        if not np.isfinite(result).all():
            raise ValueError("whitened values overflow; noise/conditioning is unsupported")
        return result

    def outside_support(self, values):
        """Component discarded by the retained left range, not a physical residual."""
        values = self._values(values)
        return values - self.left @ (self.left.T @ values)

    def whiten_source(self, values):
        """Stable equivalent of W S values when the input-pixel values are available.

        Avoid reconstructing a tiny singular mode by division after sampling. This
        still uses the retained numerical row space; discarded modes are not restored.
        """
        shape = np.shape(values)
        if len(shape) not in (1, 2) or shape[0] != self.matrix.shape[1] or (len(shape) == 2 and
                not 0 < shape[1] <= 32):
            raise ValueError("source values require one row per input pixel and at most 32 columns")
        values = np.asarray(values, dtype=np.float64)
        if not np.isfinite(values).all():
            raise ValueError("source values must be finite")
        std = self.input_std if values.ndim == 1 else self.input_std[:, None]
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            result = self.right @ (values / std)
        if not np.isfinite(result).all():
            raise ValueError("whitened source values overflow")
        return result

    def residual(self, observed, predicted):
        """Report both GLS cost and the range component a pseudoinverse would ignore."""
        observed, predicted = self._values(observed), self._values(predicted)
        if observed.ndim != 1 or observed.shape != predicted.shape:
            raise ValueError("observed and predicted must be equal-length vectors")
        difference = observed - predicted
        whitened = self.whiten(difference)
        outside = self.outside_support(difference)
        with np.errstate(over="ignore", invalid="ignore"):
            score = float(whitened @ whitened)
        if not math.isfinite(score):
            raise ValueError("residual score overflow")
        # Only a floating arithmetic diagnostic for this supplied linear operator.
        tolerance = float(256 * np.finfo(float).eps * max(self.matrix.shape) *
                          max(1., np.linalg.norm(observed), np.linalg.norm(predicted)))
        if not all(math.isfinite(v) for v in (tolerance, np.linalg.norm(outside), np.max(np.abs(outside)))):
            raise ValueError("support diagnostic overflow")
        return {"squared_whitened_residual": score,
                "outside_support_l2": float(np.linalg.norm(outside)),
                "outside_support_maximum": float(np.max(np.abs(outside))),
                "support_arithmetic_tolerance": tolerance,
                "within_retained_support_tolerance": bool(np.linalg.norm(outside) <= tolerance)}

    def fit_source(self, source_design, observed):
        """Fit a linear mean on input pixels, preserving the fixed sampling operator.

        A profile generated by another operator is refused when its component outside
        the retained range exceeds the numerical diagnostic. No minimum cost is a
        statement of physical fit, global identifiability or calibrated uncertainty.
        """
        shape = np.shape(source_design)
        if len(shape) != 2 or shape[0] != self.matrix.shape[1] or not 0 < shape[1] <= 32:
            raise ValueError("source design must be finite with one row per input pixel and 1-32 columns")
        source = np.asarray(source_design, dtype=np.float64)
        if not np.isfinite(source).all():
            raise ValueError("source design must be finite")
        observed = self._values(observed)
        if observed.ndim != 1:
            raise ValueError("observed must be a vector")
        design = self.matrix @ source
        whitened = self.whiten_source(source)
        coefficients, _, rank, _ = np.linalg.lstsq(whitened, self.whiten(observed), rcond=None)
        if not np.isfinite(coefficients).all():
            raise ValueError("fitted coefficients are not finite")
        residual = self.residual(observed, design @ coefficients)
        if not residual["within_retained_support_tolerance"]:
            raise ValueError("observations have an unsupported component outside the retained sampling range")
        return {"coefficients": coefficients, "design_rank": int(rank),
                "noise_rank": self.rank, "residual_degrees_of_freedom": self.rank - int(rank),
                **residual}
