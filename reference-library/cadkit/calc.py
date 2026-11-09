"""Handbook formulas as small, tested functions (standard library only).

Units are millimetres unless a parameter name says otherwise. Functions that
return a single number are plain formulas. Functions that return a ``dict``
include a ``warnings`` list with domain cautions; warnings never change a
result, they only flag conditions the handbook says to treat with care.

Warning thresholds (mirrored by the browser calculators):

- ``REFERENCE_PX_WARNING`` (200 px): a short reference makes endpoint picking
  dominate the scale.
- ``EXTRAPOLATION_WARNING`` (3x): a feature much longer than the reference
  extrapolates beyond the controlled length.
- ``DEPTH_RATIO_WARNING`` (0.2): when |delta| / Z exceeds this, the off-plane
  correction is large and depends strongly on the assumed camera distance.
- ``SEGMENT_WARNING`` (720): a segment count this high usually signals an
  error tolerance tighter than the export or printer can use.
- ``ASPECT_WARNING_PERCENT`` (1 %): reference proportions that disagree by more
  than this need an explanation (tilt, uneven resampling, non-physical image).
"""

from __future__ import annotations

import math
from typing import Iterable

REFERENCE_PX_WARNING = 200.0
EXTRAPOLATION_WARNING = 3.0
DEPTH_RATIO_WARNING = 0.2
SEGMENT_WARNING = 720
ASPECT_WARNING_PERCENT = 1.0
FULL_FRAME_DIAGONAL_MM = math.hypot(36.0, 24.0)  # 43.2666... mm
BETZ_LIMIT = 16.0 / 27.0
MM_PER_UNIT = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}
MAX_DECIMALS = 12  # more printed decimals than this is not a physical label

# Evidence classes from handbook section 3, weakest last. Aliases map labels
# used in registers and reports onto the four classes:
#   confirmed -> measured        (read from a verified drawing or file)
#   estimated -> image-derived   (computed from an image under stated assumptions)
#   nominal, proposed, synthetic -> inferred (chosen, published, or teaching values)
EVIDENCE_ORDER = ("measured", "image-derived", "inferred", "unknown")
EVIDENCE_ALIASES = {
    "confirmed": "measured",
    "estimated": "image-derived",
    "image_derived": "image-derived",
    "nominal": "inferred",
    "proposed": "inferred",
    "synthetic": "inferred",
}


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {value!r}")
    return value


def _nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be zero or a positive finite number, got {value!r}")
    return value


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return value


def _finite_result(name: str, value: float) -> float:
    """Reject a result that overflowed (inf) or became NaN: the inputs are out of range."""
    if not math.isfinite(value):
        raise ValueError(f"{name} is too large to represent; check the inputs")
    return value


# --- Section 5: planar scale and uncertainty -------------------------------

def planar_scale(known_length_mm: float, reference_px: float) -> float:
    """Millimetres per pixel on an undistorted, front-facing (or rectified) plane."""
    return _positive("known_length_mm", known_length_mm) / _positive("reference_px", reference_px)


def scaled_length(feature_px: float, scale: float) -> float:
    """Feature length in millimetres at a planar scale (mm/pixel)."""
    return _nonnegative("feature_px", feature_px) * _positive("scale", scale)


def scale_warnings(reference_px: float, feature_px: float | None = None) -> list[str]:
    warnings = []
    if reference_px < REFERENCE_PX_WARNING:
        warnings.append(
            f"Reference spans {reference_px:g} px (< {REFERENCE_PX_WARNING:g} px): "
            "endpoint picking error dominates the scale."
        )
    if feature_px is not None and feature_px > EXTRAPOLATION_WARNING * reference_px:
        warnings.append(
            f"Feature is {feature_px / reference_px:.1f}x the reference length: "
            "this extrapolates beyond the controlled region."
        )
    return warnings


def scale_report(known_length_mm: float, reference_px: float, feature_px: float | None = None) -> dict:
    """Planar scale, optional feature length, and warnings."""
    scale = planar_scale(known_length_mm, reference_px)
    result = {"scale_mm_per_px": scale}
    if feature_px is not None:
        result["feature_length_mm"] = scaled_length(feature_px, scale)
    result["warnings"] = scale_warnings(float(reference_px), None if feature_px is None else float(feature_px))
    return result


def ratio_uncertainty(p: float, up: float, pref: float, upref: float, lref: float, ulref: float) -> dict:
    """First-order, independent-input uncertainty for ``L = p * Lref / pref``.

    ``(uL/L)^2 = (up/p)^2 + (uLref/Lref)^2 + (upref/pref)^2``. The ``u`` values
    are standard uncertainties; ``expanded_k2`` is ``2 u`` and is only an
    approximate 95 % interval if the combined distribution is near normal.
    """
    p = _positive("p", p)
    pref = _positive("pref", pref)
    lref = _positive("lref", lref)
    up = _nonnegative("up", up)
    upref = _nonnegative("upref", upref)
    ulref = _nonnegative("ulref", ulref)
    length = p * lref / pref
    try:
        relative = math.sqrt((up / p) ** 2 + (ulref / lref) ** 2 + (upref / pref) ** 2)
    except OverflowError:  # a squared ratio beyond the float range
        relative = math.inf
    u = length * relative
    for name, value in (("length", length), ("relative uncertainty", relative), ("u", u), ("2u", 2.0 * u)):
        _finite_result(name, value)
    return {
        "length": length,
        "u": u,
        "relative": relative,
        "expanded_k2": 2.0 * u,
        "warnings": scale_warnings(pref, p),
    }


# --- Section 12: tessellation ------------------------------------------------

def _segment_count(n) -> int:
    try:
        whole = int(n)
    except (TypeError, ValueError, OverflowError):  # None, NaN, infinity
        whole = None
    if whole is None or whole != n or whole < 3:
        raise ValueError(f"n must be an integer of at least 3, got {n!r}")
    return whole


def chord_error(radius: float, n: int) -> float:
    """Maximum radial (sagitta) error of a circle drawn with ``n`` equal chords."""
    radius = _positive("radius", radius)
    return radius * (1.0 - math.cos(math.pi / _segment_count(n)))


def min_segments(radius: float, error: float) -> int:
    """Smallest ``n`` with chord error <= ``error``: ``ceil(pi / acos(1 - e/R))``."""
    radius = _positive("radius", radius)
    error = _positive("error", error)
    if error >= radius:
        raise ValueError("error must be smaller than radius (0 < error < radius)")
    half_angle = math.acos(1.0 - error / radius)
    if half_angle == 0.0:
        raise ValueError("error is too small relative to the radius to give a finite segment count")
    return max(3, math.ceil(math.pi / half_angle))


def chord_report(radius: float, error: float | None = None, segments: int | None = None) -> dict:
    """Segment count for an error, or error for a segment count, with warnings."""
    if (error is None) == (segments is None):
        raise ValueError("give exactly one of error or segments")
    if error is not None:
        n = min_segments(radius, error)
    else:
        n = _segment_count(segments)  # 3.5 is invalid, as in chord_error, not truncated to 3
    result = {
        "radius_mm": float(radius),
        "segments": n,
        "chord_error_mm": chord_error(radius, n),
        "flat_to_flat_diameter_mm": 2.0 * float(radius) * math.cos(math.pi / n),
        "warnings": [],
    }
    if error is not None:
        result["allowed_error_mm"] = float(error)
        result["previous_count_error_mm"] = chord_error(radius, n - 1) if n > 3 else None
    if n > SEGMENT_WARNING:
        result["warnings"].append(
            f"{n} segments (> {SEGMENT_WARNING}): the tolerance is probably tighter than "
            "export, slicing, or printing can use."
        )
    return result


# --- Section 5: off-plane depth and camera distance --------------------------

def depth_factor(z: float, delta: float) -> float:
    """Size factor ``(Z + delta) / Z`` for a feature off the reference plane."""
    z = _positive("z", z)
    delta = _finite("delta", delta)
    if z + delta <= 0:
        raise ValueError("z + delta must be positive (the feature must be in front of the camera)")
    return (z + delta) / z


def depth_factor_range(z_min: float, z_max: float, d_min: float, d_max: float) -> tuple[float, float]:
    """Smallest and largest depth factor over Z and delta intervals.

    ``(Z + d) / Z = 1 + d / Z`` is monotonic in each variable, so the extremes
    lie at the corners. For ``d >= 0`` they are ``(Zmax + dmin) / Zmax`` and
    ``(Zmin + dmax) / Zmin``.
    """
    z_min, z_max = _positive("z_min", z_min), _positive("z_max", z_max)
    d_min, d_max = _finite("d_min", d_min), _finite("d_max", d_max)
    if z_min > z_max or d_min > d_max:
        raise ValueError("ranges must be given as (min, max)")
    corners = [depth_factor(z, d) for z in (z_min, z_max) for d in (d_min, d_max)]
    return min(corners), max(corners)


def depth_report(z: float, delta: float, size: float | None = None) -> dict:
    factor = depth_factor(z, delta)
    result = {"depth_factor": factor}
    if size is not None:
        result["corrected_size_mm"] = _nonnegative("size", size) * factor
    result["warnings"] = []
    if abs(float(delta)) / float(z) > DEPTH_RATIO_WARNING:
        result["warnings"].append(
            f"|delta| / Z = {abs(float(delta)) / float(z):.2f} (> {DEPTH_RATIO_WARNING:g}): the "
            "correction is large and depends strongly on the assumed camera distance."
        )
    return result


def focal_px_from_35mm(f35: float, width_px: float, height_px: float) -> float:
    """Focal length in pixels from a 35 mm-equivalent focal length (diagonal definition)."""
    f35 = _positive("f35", f35)
    diagonal_px = math.hypot(_positive("width_px", width_px), _positive("height_px", height_px))
    return f35 * diagonal_px / FULL_FRAME_DIAGONAL_MM


def camera_distance(f_px: float, length_mm: float, length_px: float) -> float:
    """Distance to a reference of known length at roughly constant depth: ``f_px L / l``."""
    return _positive("f_px", f_px) * _positive("length_mm", length_mm) / _positive("length_px", length_px)


def camera_report(f35: float, width_px: float, height_px: float, length_mm: float, length_px: float) -> dict:
    f_px = focal_px_from_35mm(f35, width_px, height_px)
    return {
        "focal_length_px": f_px,
        "camera_distance_mm": camera_distance(f_px, length_mm, length_px),
        "warnings": [
            "Assumes the original uncropped frame, a centred principal point, and negligible "
            "distortion; screenshots and crops break these assumptions."
        ],
    }


def aspect_check(known_w: float, known_h: float, px_w: float, px_h: float) -> dict:
    """Compare a reference rectangle's image proportions with its known proportions."""
    known_w, known_h = _positive("known_w", known_w), _positive("known_h", known_h)
    px_w, px_h = _positive("px_w", px_w), _positive("px_h", px_h)
    known_aspect = known_h / known_w
    image_aspect = px_h / px_w
    squat_percent = (1.0 - image_aspect / known_aspect) * 100.0
    scale_h = known_w / px_w
    scale_v = known_h / px_h
    stretch_percent = (scale_v / scale_h - 1.0) * 100.0
    warnings = []
    if abs(squat_percent) > ASPECT_WARNING_PERCENT:
        warnings.append(
            f"Image proportions differ from the known shape by {abs(squat_percent):.2f} %: confirm "
            "plane tilt with converging lines; otherwise suspect cropping, uneven resampling, or a "
            "non-physical image, and use one uniform scale off the plane."
        )
    return {
        "known_aspect": known_aspect,
        "image_aspect": image_aspect,
        "squat_percent": squat_percent,
        "scale_h": scale_h,
        "scale_v": scale_v,
        "stretch_percent": stretch_percent,
        "warnings": warnings,
    }


# --- Section 3: labels and rounding -----------------------------------------

def rounding_uncertainty(value: float, unit: str = "in", decimals: int = 2) -> dict:
    """Rounding interval of a printed value, as a rectangular distribution (GUM 4.3.7).

    A value printed to ``decimals`` places lies within +/- half a unit in the
    last place; the standard uncertainty of rounding alone is ``a / sqrt(3)``.
    """
    unit = unit.lower()
    if unit not in ("in", "mm", "cm"):
        raise ValueError("unit must be 'in', 'mm', or 'cm'")
    if int(decimals) != decimals or not 0 <= decimals <= MAX_DECIMALS:
        raise ValueError(f"decimals must be an integer from 0 to {MAX_DECIMALS}")
    value = _finite("value", value)
    factor = MM_PER_UNIT[unit]
    half_interval = 0.5 / (10 ** int(decimals))
    half_interval_mm = half_interval * factor
    return {
        "value_mm": value * factor,
        "half_interval_mm": half_interval_mm,
        "standard_uncertainty_mm": half_interval_mm / math.sqrt(3.0),
        "warnings": [
            "Rounding only: manufacturing tolerance is separate and usually larger. "
            "Converting units adds digits, not knowledge."
        ],
    }


# --- Sections 11 and 15: coatings and clearances -----------------------------

def coating_loss(per_face_mm: float, faces: int = 2) -> float:
    """Width lost from a slot or bore when ``faces`` coated faces bound it."""
    if int(faces) != faces or faces < 0:
        raise ValueError("faces must be a non-negative integer")
    return int(faces) * _nonnegative("per_face_mm", per_face_mm)


def clearance_series(nominal_mm: float, start: float, step: float, count: int) -> list[dict]:
    """Diametral clearance series for a hole coupon around a nominal pin diameter.

    ``diametral`` = hole - pin, ``radial`` = half of that. Values are rounded to
    1e-6 mm so that 0.1 + 0.2 reads as 0.3.
    """
    nominal_mm = _positive("nominal_mm", nominal_mm)
    start = _finite("start", start)
    step = _finite("step", step)
    if int(count) != count or count < 1:
        raise ValueError("count must be a positive integer")
    rows = []
    for i in range(int(count)):
        diametral = round(start + i * step, 6)
        hole = round(nominal_mm + diametral, 6)
        if hole <= 0:
            raise ValueError("every hole diameter must be positive")
        rows.append({"diametral": diametral, "radial": round(diametral / 2.0, 6), "hole_diameter": hole})
    return rows


# --- Section 16: gears and wind ----------------------------------------------

def gear_pair(module: float, z1: int, z2: int, pressure_angle_deg: float = 20.0) -> dict:
    """Nominal external spur-gear relations: ``d = m z``, ``a = m (z1 + z2) / 2``, ``w2/w1 = -z1/z2``."""
    module = _positive("module", module)
    for name, z in (("z1", z1), ("z2", z2)):
        if int(z) != z or z < 1:
            raise ValueError(f"{name} must be a positive integer")
    z1, z2 = int(z1), int(z2)
    pressure_angle_deg = float(pressure_angle_deg)
    if not 0.0 < pressure_angle_deg < 90.0:  # also rejects NaN
        raise ValueError(f"pressure_angle_deg must be between 0 and 90 degrees, got {pressure_angle_deg!r}")
    alpha = math.radians(pressure_angle_deg)
    undercut_limit = 2.0 / math.sin(alpha) ** 2
    warnings = []
    for name, z in (("z1", z1), ("z2", z2)):
        if z < undercut_limit:
            warnings.append(
                f"{name} = {z} is below the theoretical undercut limit 2/sin^2(alpha) = "
                f"{undercut_limit:.1f} for unshifted full-depth teeth; use profile shift or a validated generator."
            )
    return {
        "d1": module * z1,
        "d2": module * z2,
        "center_distance": module * (z1 + z2) / 2.0,
        "speed_ratio": -z1 / z2,
        "undercut_limit_teeth": undercut_limit,
        "warnings": warnings,
    }


def wind_power(rho: float, area_m2: float, v: float, cp: float) -> float:
    """First estimate of extracted wind power in watts: ``0.5 rho A v^3 Cp``."""
    rho = _positive("rho", rho)
    area_m2 = _positive("area_m2", area_m2)
    v = _nonnegative("v", v)
    cp = _nonnegative("cp", cp)
    if cp > BETZ_LIMIT:
        raise ValueError(f"cp = {cp:g} exceeds the Betz limit 16/27 = {BETZ_LIMIT:.4f}")
    try:
        power = 0.5 * rho * area_m2 * v ** 3 * cp
    except OverflowError:  # v ** 3 beyond the float range
        power = math.inf
    return _finite_result("power", power)


def wind_report(rho: float, area_m2: float, v: float, cp: float) -> dict:
    return {
        "power_w": wind_power(rho, area_m2, v, cp),
        "warnings": [
            "Running power only: start-up torque must overcome friction, imbalance, and mechanism "
            "resistance at the initial configuration (torque = P / w cannot be evaluated at zero speed)."
        ],
    }


# --- Section 3: evidence classes ---------------------------------------------

def normalize_evidence(label: str) -> str:
    key = str(label).strip().lower().replace(" ", "-")
    key = EVIDENCE_ALIASES.get(key, key)
    if key not in EVIDENCE_ORDER:
        known = ", ".join(EVIDENCE_ORDER + tuple(EVIDENCE_ALIASES))
        raise ValueError(f"unknown evidence class {label!r}; expected one of: {known}")
    return key


def weakest_evidence(classes: Iterable[str]) -> str:
    """A derived value inherits the weakest class among its inputs."""
    normalized = [normalize_evidence(c) for c in classes]
    if not normalized:
        raise ValueError("at least one evidence class is required")
    return max(normalized, key=EVIDENCE_ORDER.index)


# --- Section 2: unit mismatch on import ---------------------------------------

def suggest_unit_conversion(observed_extent: float, expected_mm: float) -> list[dict]:
    """Rank unit interpretations that would turn an imported extent into the expected size.

    ``observed_extent`` is the number the importer shows; ``expected_mm`` is a
    known real dimension of the same extent. Candidates cover a file authored
    in mm, cm, m, in, or ft and read as mm (factor > 1), and the reverse case of
    a millimetre file already scaled up as if it were in another unit (factor < 1).
    """
    observed_extent = _positive("observed_extent", observed_extent)
    expected_mm = _positive("expected_mm", expected_mm)
    candidates = []
    for unit, factor in MM_PER_UNIT.items():
        candidates.append({
            "interpretation": f"file units are {unit}" if unit != "mm" else "file units are mm (no change)",
            "unit": unit,
            "factor": factor,
        })
        if unit != "mm":
            candidates.append({
                "interpretation": f"mm geometry already scaled as if it were {unit}",
                "unit": f"1/{unit}",
                "factor": 1.0 / factor,
            })
    for c in candidates:
        corrected = observed_extent * c["factor"]
        c["corrected_mm"] = corrected
        c["relative_error"] = abs(corrected - expected_mm) / expected_mm
    candidates.sort(key=lambda c: c["relative_error"])
    return candidates
