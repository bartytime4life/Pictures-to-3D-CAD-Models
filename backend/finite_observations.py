"""Observed-ring crop, initializer and fixed samples for a conditional finite-D fit.

This data preparation does not fit intensities, infer a PSF, establish camera/model
adequacy, or accept CAD geometry. The policy is adapted from the frozen
``studies/verification/finite-free-centre-v1.py::observed_seed_roi``. Unlike its
whole-field use in the first photo diagnostic, the background and crossings here
come only from an explicitly recorded measured-ring crop.
"""

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np

MAX_SOURCE_PIXELS = 16_000_000
MAX_CROP_PIXELS = 1_000_000
MAX_RING_POINTS = 20_000
MAX_CROSSINGS = 100_000
MINIMUM_CONTRAST = 12.0
POLICY = "measured-ring-finite-segment-observations-v1"


class ObservationPreparationError(ValueError):
    """Explicit unsupported/invalid input, with a stable machine-readable reason."""

    def __init__(self, reason, message):
        self.reason = reason
        super().__init__(message)


def _fail(reason, message):
    raise ObservationPreparationError(reason, message)


@dataclass(frozen=True)
class _ArraySnapshot:
    """Keep immutable descriptors too: ndarray shape/dtype remain mutable."""

    data: bytes
    dtype: str
    shape: tuple[int, ...]

    def view(self):
        return np.frombuffer(self.data, dtype=self.dtype).reshape(self.shape)


def _snapshot(value):
    array = np.ascontiguousarray(value)
    return _ArraySnapshot(array.tobytes(), array.dtype.str, array.shape)


def _digest(value):
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(f"{array.dtype.str}:{array.shape}:".encode())
    digest.update(memoryview(array).cast("B"))
    return digest.hexdigest()


@dataclass(frozen=True)
class SegmentObservations:
    """Immutable crop and selection; all geometry/bounds remain GLOBAL pixels.

    Pixel arrays contain LOCAL integer indices. The supplied homography maps
    global geometric coordinates to crop geometric coordinates, whose pixel
    centres are indices + .5. ``bounds`` and ``metadata()`` return detached data.
    A successful preparation is not evidence that these bounds contain truth.
    """

    _field: _ArraySnapshot
    _ring_points: _ArraySnapshot
    _normal: _ArraySnapshot
    _homography: _ArraySnapshot
    _training_pixels: _ArraySnapshot
    _training_values: _ArraySnapshot
    _heldout_pixels: _ArraySnapshot
    _heldout_values: _ArraySnapshot
    _contour: _ArraySnapshot
    _plane_contour: _ArraySnapshot
    source_shape: tuple[int, int]
    crop_origin: tuple[int, int]
    crop_bounds: tuple[int, int, int, int]
    blur_sigma: float
    polarity: str
    seed_centre: tuple[float, float]
    seed_radius: float
    seed_fraction: float
    centre_bounds: tuple[tuple[float, float], tuple[float, float]]
    radius_bounds: tuple[float, float]
    chord_fraction_bounds: tuple[float, float]
    _metadata_json: str

    @property
    def field(self):
        return self._field.view()

    @property
    def ring_points(self):
        return self._ring_points.view()

    @property
    def normal(self):
        return self._normal.view()

    @property
    def homography(self):
        return self._homography.view()

    @property
    def training_pixels(self):
        return self._training_pixels.view()

    @property
    def training_values(self):
        return self._training_values.view()

    @property
    def heldout_pixels(self):
        return self._heldout_pixels.view()

    @property
    def heldout_values(self):
        return self._heldout_values.view()

    @property
    def contour(self):
        return self._contour.view()

    @property
    def plane_contour(self):
        return self._plane_contour.view()

    @property
    def bounds(self):
        return {
            "centre_bounds": [list(axis) for axis in self.centre_bounds],
            "radius_bounds": list(self.radius_bounds),
            "chord_fraction_bounds": list(self.chord_fraction_bounds),
        }

    @property
    def sensor_shape(self):
        return self._field.shape

    def metadata(self):
        return json.loads(self._metadata_json)


def _real_array(value, name, *, max_size=None):
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise ObservationPreparationError(
            "invalid_input", f"{name} must be real numeric data"
        ) from error
    if max_size is not None and array.size > max_size:
        _fail("work_limit", f"{name} exceeds {max_size} scalar entries")
    if array.dtype.kind not in "iuf" or (
        not isinstance(value, np.ndarray)
        and any(isinstance(v, (bool, np.bool_)) for v in np.asarray(value, dtype=object).flat)
    ):
        _fail("invalid_input", f"{name} must be real numeric data without booleans")
    return array


def _float64(array, name):
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        result = np.array(array, dtype=np.float64, copy=True)
    if not np.all(np.isfinite(result)):
        _fail("nonfinite", f"{name} is not representable in finite float64 arithmetic")
    return result


def _crossings(u):
    """All strict adjacent-centre brackets plus exact-level nodes, once each."""
    residual = u - 0.5
    left, right = residual[:, :-1], residual[:, 1:]
    hy, hx = np.nonzero(((left < 0) & (right > 0)) | ((left > 0) & (right < 0)))
    top, bottom = residual[:-1], residual[1:]
    vy, vx = np.nonzero(((top < 0) & (bottom > 0)) | ((top > 0) & (bottom < 0)))
    zy, zx = np.nonzero(residual == 0)
    if len(hx) + len(vx) + len(zx) > MAX_CROSSINGS:
        _fail("work_limit", f"threshold crossings exceed {MAX_CROSSINGS}")
    horizontal = np.column_stack(
        (hx + 0.5 - left[hy, hx] / (right[hy, hx] - left[hy, hx]), hy + 0.5)
    )
    vertical = np.column_stack((vx + 0.5, vy + 0.5 - top[vy, vx] / (bottom[vy, vx] - top[vy, vx])))
    zero = np.column_stack((zx + 0.5, zy + 0.5))
    contour = np.unique(np.vstack((horizontal, vertical, zero)), axis=0)
    if len(contour) < 8:
        _fail("insufficient_contour", "observed crop has fewer than 8 threshold crossings")
    return contour


def _spread(items, count, name):
    if len(items) < count:
        _fail(
            "insufficient_stratum",
            f"observed {name} stratum has {len(items)} pixels; needs {count}",
        )
    return items[np.rint(np.linspace(0, len(items) - 1, count)).astype(int)]


def prepare_segment_observations(field, ring_points, *, normal, blur_sigma, polarity="dark"):
    """Prepare one observed finite-D candidate without truth or covariance input.

    Required full crop, in half-open integer indices::

        padding = ceil(max(16, 8 * blur_sigma))
        lower = floor(min(ring_points)) - padding
        upper = ceil(max(ring_points)) + padding + 1

    A crop extending outside the source is refused, never clipped or searched for
    alternative padding. Material reaching its border is also unsupported. The
    normal is supplied, fixed and unit length; it is not inferred from truth.
    ``blur_sigma`` alone controls crop padding, geometry bounds and ROI margin,
    permitting identical observations for distinct supplied covariance models.
    The returned crop and selected values preserve the source dtype and bytes;
    initializer/selection arithmetic uses a separate finite float64 buffer.
    """
    source = _real_array(field, "field", max_size=MAX_SOURCE_PIXELS)
    if source.ndim != 2 or min(source.shape) < 3:
        _fail("invalid_input", "field must have height and width at least 3")
    if source.size > MAX_SOURCE_PIXELS:
        _fail("work_limit", f"source field exceeds {MAX_SOURCE_PIXELS} pixels")
    if not np.all(np.isfinite(source)):
        _fail("nonfinite", "source field must be finite")
    ring = _real_array(ring_points, "ring_points", max_size=2 * MAX_RING_POINTS)
    if ring.ndim != 2 or ring.shape[1:] != (2,) or not 3 <= len(ring) <= MAX_RING_POINTS:
        _fail("invalid_input", f"ring_points must contain 3..{MAX_RING_POINTS} geometric pairs")
    ring = _float64(ring, "ring_points")
    n = _real_array(normal, "normal", max_size=2)
    if n.shape != (2,) or not np.all(np.isfinite(n)):
        _fail("invalid_input", "normal must be a finite unit pair")
    n = _float64(n, "normal")
    length = math.hypot(*n)
    if abs(length - 1) > 64 * np.finfo(float).eps:
        _fail("invalid_input", "normal must be a fixed unit pair")
    n = n / length
    if isinstance(blur_sigma, (bool, np.bool_)) or not isinstance(
        blur_sigma, (int, float, np.integer, np.floating)
    ):
        _fail("invalid_input", "blur_sigma must be a finite positive real scalar")
    sigma = float(blur_sigma)
    if not math.isfinite(sigma) or not 1e-3 <= sigma <= 1e3:
        _fail("invalid_input", "blur_sigma must be in [1e-3, 1e3] pixels")
    if not isinstance(polarity, str) or polarity not in ("dark", "light"):
        _fail("invalid_input", "polarity must be 'dark' or 'light'")
    height, width = source.shape
    if (
        not np.all(np.isfinite(ring))
        or np.any(ring < 0)
        or np.any(ring[:, 0] > width)
        or np.any(ring[:, 1] > height)
        or np.any(np.ptp(ring, axis=0) <= 0)
    ):
        _fail(
            "invalid_input", "ring_points must have finite positive extent inside the source frame"
        )
    padding = math.ceil(max(16.0, 8 * sigma))
    x0, y0 = (int(v) - padding for v in np.floor(ring.min(axis=0)))
    x1, y1 = (int(v) + padding + 1 for v in np.ceil(ring.max(axis=0)))
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        _fail(
            "crop_edge",
            "the measured-ring crop needs its complete declared padding inside the source",
        )
    if (x1 - x0) * (y1 - y0) > MAX_CROP_PIXELS:
        _fail("work_limit", f"measured-ring crop exceeds {MAX_CROP_PIXELS} pixels")
    source_crop = np.array(source[y0:y1, x0:x1], copy=True, order="C")
    crop = _float64(source_crop, "crop field")
    border = np.r_[crop[0], crop[-1], crop[1:-1, 0], crop[1:-1, -1]]
    with np.errstate(over="ignore", invalid="ignore"):
        background = float(np.median(border))
        material = float(np.percentile(crop, 0.2 if polarity == "dark" else 99.8))
        contrast = material - background
    if not math.isfinite(contrast) or (contrast >= 0 if polarity == "dark" else contrast <= 0):
        _fail("contrast", "observed crop has no contrast with the declared material polarity")
    if abs(contrast) < MINIMUM_CONTRAST:
        _fail("contrast", f"observed contrast must be at least {MINIMUM_CONTRAST:g} linear levels")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        u = (crop - background) / contrast
    if not np.all(np.isfinite(u)):
        _fail("nonfinite", "normalized crop intensities are not representable")
    mask = u >= 0.5
    if np.any(np.r_[mask[0], mask[-1], mask[1:-1, 0], mask[1:-1, -1]]):
        _fail("crop_edge", "threshold material reaches the measured-ring crop border")
    contour = _crossings(u)
    # Do all seed arithmetic locally, then translate once; avoid world-coordinate
    # cancellation and keep the initializer equivariant under integer cropping.
    projection = contour @ n
    support = contour[projection <= np.percentile(projection, 65)]
    if len(support) < 6:
        _fail("insufficient_contour", "observed circular support has fewer than 6 crossings")
    origin = support.mean(axis=0)
    local = support - origin
    squares = np.sum(local * local, axis=1)
    try:
        offset, _, rank, _ = np.linalg.lstsq(2 * local, squares - squares.mean(), rcond=None)
    except np.linalg.LinAlgError as error:
        raise ObservationPreparationError(
            "seed_rank", "observed circle seed solve failed"
        ) from error
    if rank != 2:
        _fail("seed_rank", "observed circle seed is rank deficient")
    local_centre = origin + offset
    raw_radius = math.sqrt(float(squares.mean() + offset @ offset))
    extent = float(np.max(np.ptp(contour, axis=0)))
    radius = float(np.clip(raw_radius, 0.05, 4 * extent))
    fraction = float(
        np.clip((np.percentile(projection, 97) - n @ local_centre) / radius, -0.9, 0.9)
    )
    centre = local_centre + (x0, y0)
    pad = max(0.5 * radius, 3 * sigma)
    bounds = {
        "centre_bounds": [[float(c - pad), float(c + pad)] for c in centre],
        "radius_bounds": [max(0.05, 0.25 * radius), max(2 * radius, extent)],
        "chord_fraction_bounds": [max(-0.98, fraction - 0.45), min(0.98, fraction + 0.45)],
    }
    if not np.all(np.isfinite([*centre, raw_radius, radius, fraction, extent])):
        _fail("nonfinite", "observed seed geometry is not representable")
    ys, xs = np.nonzero(mask)
    if not len(xs):
        _fail("insufficient_contour", "observed threshold mask is empty")
    margin = math.ceil(3 * sigma)
    xmin, ymin = max(int(xs.min()) - margin, 0), max(int(ys.min()) - margin, 0)
    xmax, ymax = (
        min(int(xs.max()) + margin, crop.shape[1] - 1),
        min(int(ys.max()) + margin, crop.shape[0] - 1),
    )
    yy, xx = np.mgrid[ymin : ymax + 1, xmin : xmax + 1]
    roi = np.column_stack((xx.ravel(), yy.ravel()))
    normalized_values = u[roi[:, 1], roi[:, 0]]
    edge = roi[(normalized_values > 0.15) & (normalized_values < 0.85)]
    centroid = np.array([xs.mean(), ys.mean()]) + 0.5
    relative = edge + 0.5 - centroid
    order = np.lexsort(
        (edge[:, 0], edge[:, 1], np.hypot(*relative.T), np.arctan2(relative[:, 1], relative[:, 0]))
    )
    strata = [
        _spread(edge[order], 32, "edge"),
        _spread(roi[normalized_values >= 0.9], 12, "material"),
        _spread(roi[normalized_values <= 0.1], 12, "background"),
    ]
    training, heldout = [], []
    for group_index, group in enumerate(strata):
        period = 4 if group_index == 0 else 3
        for i, pixel in enumerate(group):
            (heldout if i % period == period - 1 else training).append(pixel)
    training, heldout = np.array(training, dtype=np.int64), np.array(heldout, dtype=np.int64)
    training_values = source_crop[training[:, 1], training[:, 0]]
    heldout_values = source_crop[heldout[:, 1], heldout[:, 0]]
    homography = np.array([[1.0, 0.0, -x0], [0.0, 1.0, -y0], [0.0, 0.0, 1.0]])
    metadata = {
        "policy": POLICY,
        "source_shape": list(source.shape),
        "source_sha256": _digest(source),
        "source_dtype": source.dtype.str,
        "ring_sha256": _digest(ring),
        "crop_sha256": _digest(source_crop),
        "crop_dtype": source_crop.dtype.str,
        "arithmetic_dtype": crop.dtype.str,
        "selected_values_dtype": source_crop.dtype.str,
        "crop_origin": [x0, y0],
        "crop_bounds": [x0, y0, x1, y1],
        "crop_bounds_semantics": "half-open integer indices; complete padding, no clipping",
        "crop_shape": list(crop.shape),
        "padding": padding,
        "normal": n.tolist(),
        "blur_sigma": sigma,
        "polarity": polarity,
        "homography": homography.tolist(),
        "coordinate_contract": "global geometry; local integer samples; centres=indices+.5; Hcrop=translation(-origin)",
        "background_estimate": background,
        "material_estimate": material,
        "observed_contrast": contrast,
        "minimum_observed_contrast": MINIMUM_CONTRAST,
        "contour_count": len(contour),
        "circular_support_count": len(support),
        "seed_centre": centre.tolist(),
        "seed_radius": radius,
        "unclipped_seed_radius": raw_radius,
        "seed_fraction": fraction,
        "observed_extent": extent,
        "bounds": bounds,
        "roi_bounds_xy": [xmin, ymin, xmax, ymax],
        "roi_bounds_semantics": "inclusive local integer indices",
        "training_count": len(training),
        "heldout_count": len(heldout),
        "training_pixels_sha256": _digest(training),
        "training_values_sha256": _digest(training_values),
        "heldout_pixels_sha256": _digest(heldout),
        "heldout_values_sha256": _digest(heldout_values),
        "scope": "observed initializer and fixed strata only; no fit, PSF calibration, truth containment or topology qualification",
    }
    canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False)
    metadata["binding_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return SegmentObservations(
        _field=_snapshot(source_crop),
        _ring_points=_snapshot(ring),
        _normal=_snapshot(n),
        _homography=_snapshot(homography),
        _training_pixels=_snapshot(training),
        _training_values=_snapshot(training_values),
        _heldout_pixels=_snapshot(heldout),
        _heldout_values=_snapshot(heldout_values),
        _contour=_snapshot(contour),
        _plane_contour=_snapshot(contour + (x0, y0)),
        source_shape=tuple(source.shape),
        crop_origin=(x0, y0),
        crop_bounds=(x0, y0, x1, y1),
        blur_sigma=sigma,
        polarity=polarity,
        seed_centre=tuple(float(v) for v in centre),
        seed_radius=radius,
        seed_fraction=fraction,
        centre_bounds=tuple(tuple(axis) for axis in bounds["centre_bounds"]),
        radius_bounds=tuple(bounds["radius_bounds"]),
        chord_fraction_bounds=tuple(bounds["chord_fraction_bounds"]),
        _metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False),
    )
