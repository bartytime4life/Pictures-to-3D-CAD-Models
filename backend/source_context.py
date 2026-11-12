"""Opt-in, private, per-request source observations from the real sheet trace path.

The immutable working field precedes rectification/smoothing. It is decoded camera
output, not sensor RAW. The normal HTTP response retains neither this field nor a
server-side source session. A successful capture does not calibrate optics/noise.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field

import cv2
import numpy as np
import PIL

from .models import Profile
from .profile_observations import KeysProfile, PixelNoise, keys_profile


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _array_sha(array):
    return _sha(memoryview(np.ascontiguousarray(array)).cast("B"))


def _immutable(value, dtype="<f8"):
    array = np.asarray(value, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=dtype).reshape(array.shape)


def _profile_json(profile):
    validated = profile if isinstance(profile, Profile) else Profile.model_validate(profile)
    return _json(validated.model_dump(mode="json", exclude_none=True))


def _decode_record(data, image, decoder):
    return {
        "input_sha256": _sha(data),
        "input_bytes": len(data),
        "decoder": decoder,
        "reduction_applied": False,
        "upright_rgb_shape": [image.height, image.width, 3],
        "upright_rgb_sha256": _array_sha(np.asarray(image)),
    }


@dataclass(frozen=True, slots=True)
class SourceObservation:
    """Fixed ordered source pixels, their values, and one declared linear operator.

    This operator uses float64 arithmetic. Actual tracing rounds the rectification
    and smoothing to float32; this discrepancy is not camera noise or calibrated
    away. Input standard deviations must be supplied in working-field level units.
    """

    context_sha256: str
    pixels_xy: np.ndarray = field(repr=False)
    raw_values: np.ndarray = field(repr=False)
    matrix: np.ndarray = field(repr=False)

    @property
    def samples(self):
        return _immutable(self.matrix @ self.raw_values)

    def noise(self, input_std):
        """Conditional independent working-pixel noise, not a camera estimate."""
        return PixelNoise.factor(self.matrix, input_std)


@dataclass(frozen=True, slots=True)
class TraceSourceContext:
    _source_bytes: bytes = field(repr=False)
    _record_json: str = field(repr=False)
    _profile_json: str = field(repr=False)

    @classmethod
    def _from_trace(
        cls,
        source_bytes,
        rgb,
        weights,
        matrix,
        k1,
        plane,
        ppm,
        transform,
        result,
        decode_info,
        thickness_mm,
    ):
        if decode_info is None:
            raise ValueError("source capture requires the decode stage record")
        rotation = transform.rotation
        display_to_plane = np.eye(3)
        display_to_plane[:2, :2] = rotation.T / (transform.scale * ppm)
        display_to_plane[:2, 2] = (
            transform.centre + rotation.T @ (transform.origin - transform.centre)
        ) / ppm
        shape = rgb.shape[:2]
        if len(source_bytes) != int(np.prod(shape)) * 4:
            raise ValueError("source byte count differs from working-image dimensions")
        profile_json = _profile_json(result["profile"])
        reduced = decode_info["reduction_applied"]
        record = {
            "schema": "trace-source-context-v1",
            "request_id": uuid.uuid4().hex,
            **decode_info,
            "working_rgb_shape": list(rgb.shape),
            "working_rgb_sha256": _array_sha(rgb),
            "working_field_sha256": _sha(source_bytes),
            "working_field_dtype": "<f4",
            "working_field_shape": list(shape),
            "working_field_units": "linear sRGB mix on 0..255 scale; assumed response",
            "channel_weights": [float(v) for v in weights],
            "reduction": {
                "applied": reduced,
                "kind": "linear LUT float32 / INTER_AREA / sRGB round uint8"
                if reduced
                else "identity",
                "scale_xy": [
                    rgb.shape[1] / decode_info["upright_rgb_shape"][1],
                    rgb.shape[0] / decode_info["upright_rgb_shape"][0],
                ],
            },
            "plane_mm_to_undistorted_working_photo": np.asarray(matrix).tolist(),
            "lens_k1": float(k1),
            "radial_centre_xy": [shape[1] / 2, shape[0] / 2],
            "radial_scale": float(np.hypot(*shape) / 2),
            "plane_size_mm": [float(v) for v in plane],
            "rectified_ppm": float(ppm),
            "rectified_shape": [round(plane[1] * ppm), round(plane[0] * ppm)],
            "rectification": "Keys a=-0.5, replicate; float64 sum stored float32",
            "smoothing": "Gaussian sigma=0.7, auto support, reflect101; float32",
            "display_to_plane_mm": display_to_plane.tolist(),
            "display_shape": [result["image"]["height"], result["image"]["width"]],
            "profile_sha256": _sha(profile_json.encode()),
            "trace_reference": json.loads(profile_json)["reference"],
            "thickness_mm": float(thickness_mm or 0),
            "psf_calibrated": False,
            "noise_calibrated": False,
            "pose_calibrated": False,
            "response_calibrated": False,
            "pixel_aperture_modelled": False,
            "sensor_raw": False,
            "runtime": {
                "numpy": np.__version__,
                "opencv": cv2.__version__,
                "pillow": PIL.__version__,
            },
        }
        return cls(source_bytes, _json(record), profile_json)

    @property
    def sha256(self):
        return _sha(self._record_json.encode())

    def metadata(self):
        """A detached JSON-compatible record; it contains no image or source values."""
        return json.loads(self._record_json)

    @property
    def working_field(self):
        """A read-only bytes-backed view; its write flag cannot be enabled."""
        return np.frombuffer(self._source_bytes, dtype="<f4").reshape(
            self.metadata()["working_field_shape"]
        )

    def assert_profile(self, profile):
        if _profile_json(profile) != self._profile_json:
            raise ValueError(
                "profile differs from this source context; re-trace before reusing observations"
            )

    def display_to_plane(self, points, *, profile):
        """Profile/display edge coordinates -> sheet mm; no index-centre offset."""
        self.assert_profile(profile)
        points = np.asarray(points, dtype=float)
        if (
            points.ndim != 2
            or points.shape[1] != 2
            or not 0 < len(points) <= 2048
            or not np.isfinite(points).all()
        ):
            raise ValueError("supply 1..2048 finite display-coordinate pairs")
        matrix = np.asarray(self.metadata()["display_to_plane_mm"])
        with np.errstate(over="ignore", invalid="ignore"):
            mapped = points @ matrix[:2, :2].T + matrix[:2, 2]
        if not np.isfinite(mapped).all():
            raise ValueError("display mapping is numerically unsupported")
        return _immutable(mapped)

    def source_pixels(self, pixels_xy, *, profile):
        """Read 1..512 unique in-frame integer (x,y) indices, preserving order.

        Geometric forward models use centres pixels_xy+0.5. There is no clipping,
        interpolation, smoothing, or use of the display crop in this observation.
        """
        self.assert_profile(profile)
        pixels = np.asarray(pixels_xy)
        if (
            pixels.ndim != 2
            or pixels.shape[1] != 2
            or not 0 < len(pixels) <= 512
            or any(isinstance(v, (bool, np.bool_)) for pair in pixels_xy for v in pair)
            or pixels.dtype.kind not in "iu"
            or len(np.unique(pixels, axis=0)) != len(pixels)
        ):
            raise ValueError("supply 1..512 unique integer source pixel pairs")
        height, width = self.working_field.shape
        if np.any(pixels < 0) or np.any(pixels[:, 0] >= width) or np.any(pixels[:, 1] >= height):
            raise ValueError("source pixel is outside the working image")
        pixels = _immutable(pixels, "<i8")
        values = self.working_field[pixels[:, 1], pixels[:, 0]]
        return SourceObservation(
            self.sha256, pixels, _immutable(values), _immutable(np.eye(len(pixels)))
        )

    def observe_display(self, points, *, profile, smoothing=True):
        """Compose fixed Keys samples, optional known smoothing and actual warp.

        `points` are geometric display coordinates; only the geometry is inverted.
        Values come from the working field, never from the display image. Existing
        allocation/work caps of profile_observations apply. This does not undo an
        earlier reduction or infer a source optical PSF.
        """
        if not isinstance(smoothing, bool):
            raise TypeError("smoothing must be a boolean")
        plane = self.display_to_plane(points, profile=profile)
        m = self.metadata()
        coords = plane * m["rectified_ppm"] - 0.5
        op = keys_profile(m["rectified_shape"], coords[:, 0], coords[:, 1])
        if smoothing:
            # OpenCV's auto support for sigma .7 on a float32 input is seven taps.
            kernel = cv2.getGaussianKernel(7, 0.7).ravel()
            op = op.after_filter(np.outer(kernel, kernel), border="reflect101")
        op = op.after_rectification(
            self.working_field.shape,
            m["plane_mm_to_undistorted_working_photo"],
            m["lens_k1"],
            m["plane_size_mm"],
            m["rectified_ppm"],
        )
        return self._observation(op)

    def _observation(self, operator: KeysProfile):
        pixels = _immutable(operator.pixels_xy, "<i8")
        values = self.working_field[pixels[:, 1], pixels[:, 0]]
        return SourceObservation(
            self.sha256, pixels, _immutable(values), _immutable(operator.matrix)
        )

    def point_gaussian_geometry(self, *, profile):
        """Return conditional finite_shape inputs only for its supported geometry.

        A caller still supplies and justifies the raw PSF, noise, radiometry, pixel
        aperture and topology assumptions. Passing this guard is not qualification.
        """
        self.assert_profile(profile)
        m = self.metadata()
        reasons = []
        if m["lens_k1"] != 0:
            reasons.append("nonzero lens distortion")
        if m["reduction"]["applied"]:
            reasons.append("prior area reduction and re-encoding")
        if m["thickness_mm"] != 0:
            reasons.append("top-face/wall parallax correction")
        if reasons:
            raise ValueError("point-Gaussian source model does not cover " + "; ".join(reasons))
        return {
            "sensor_shape": tuple(m["working_field_shape"]),
            "homography": _immutable(m["plane_mm_to_undistorted_working_photo"]),
        }

    def fit_circular_segment(
        self, observation, *, profile, input_std, psf_covariance, **fit_options
    ):
        """Explicit conditional fit using this request's fixed source observations.

        The caller supplies the geometric search, raw PSF and working-field noise
        hypothesis. This does not alter the captured/returned profile. An observation
        from another request is refused even if that request produced equal geometry.
        """
        geometry = self.point_gaussian_geometry(profile=profile)
        if (
            not isinstance(observation, SourceObservation)
            or observation.context_sha256 != self.sha256
        ):
            raise ValueError("observation belongs to a different source request")
        # An origin label alone does not bind public dataclass/replaced values.
        # Recheck against the immutable field before dispatching any numerical fit.
        pixels = np.asarray(observation.pixels_xy)
        if (
            pixels.ndim != 2
            or pixels.shape[1] != 2
            or not 0 < len(pixels) <= 2048
            or any(isinstance(v, (bool, np.bool_)) for pair in observation.pixels_xy for v in pair)
            or pixels.dtype.kind not in "iu"
            or len(np.unique(pixels, axis=0)) != len(pixels)
        ):
            raise ValueError("observation source indices are invalid")
        height, width = self.working_field.shape
        if np.any(pixels < 0) or np.any(pixels[:, 0] >= width) or np.any(pixels[:, 1] >= height):
            raise ValueError("observation source pixel is outside the working image")
        if not np.array_equal(
            observation.raw_values, self.working_field[pixels[:, 1], pixels[:, 0]]
        ):
            raise ValueError("observation values differ from this request's source pixels")
        from .finite_shape_fit import fit_circular_segment

        return fit_circular_segment(
            _immutable(pixels, "<i8"),
            _immutable(self.working_field[pixels[:, 1], pixels[:, 0]]),
            PixelNoise.factor(_immutable(observation.matrix), input_std),
            **geometry,
            psf_covariance=psf_covariance,
            **fit_options,
        )


def trace_with_source(data, **trace_options):
    """Run the normal trace and return (result, context_or_None), privately in memory.

    Context exists only after a complete successful reference-sheet trace. Plain
    silhouette traces and explicit sheet fallbacks return None. Exceptions publish
    no context. No image/session is written to disk, HTTP, a cache or a global.
    """
    from .tracing import trace_image

    if "_source_capture" in trace_options:
        raise ValueError("source capture is owned by trace_with_source")
    contexts = []
    result = trace_image(data, **trace_options, _source_capture=contexts.append)
    context = contexts[0] if contexts else None
    if context is not None:
        context.assert_profile(result["profile"])
    return result, context
