"""Deterministic profile changes and conservative printer envelope checks."""

import json
import math
from pathlib import Path

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box

from .models import DesignSettings

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "printers.json"
DETAIL_TOLERANCE = {"draft": 0.5, "balanced": 0.25, "fine": 0.1}


class PrintGeometryError(ValueError):
    """A bounded geometry failure whose message is suitable for the user."""


def load_printer_catalog():
    if not CATALOG_PATH.is_file():
        return {"schema_version": 1, "source": None, "printers": []}
    return json.loads(CATALOG_PATH.read_text())


def printer_by_id(printer_id):
    return next(
        (
            item
            for item in load_printer_catalog().get("printers", [])
            if item.get("id") == printer_id
        ),
        None,
    )


def resolve_design(design: DesignSettings):
    """Known profiles, rather than stale browser values, supply printer dimensions."""
    printer = printer_by_id(design.printer_id) if design.printer_id != "custom" else None
    warnings = []
    if printer:
        matching = [
            profile
            for profile in printer.get("profiles", [])
            if any(
                math.isclose(design.nozzle_mm, value, abs_tol=1e-6)
                for value in profile.get("nozzle_diameters_mm", [])
            )
        ]
        geometry_keys = ("build_volume", "bed_shape", "printable_area_mm", "excluded_areas_mm")
        geometries = {
            json.dumps({key: profile.get(key) for key in geometry_keys}, sort_keys=True)
            for profile in matching
        }
        if len(geometries) != 1:
            warnings.append(
                "The selected printer and nozzle do not resolve to one unambiguous bed profile. "
                "Bed placement is not verified; choose a matching profile in your slicer."
            )
            return design, {**printer, "bed_shape": "unknown"}, warnings
        profile = matching[0]
        printer = {**printer, **{key: profile.get(key) for key in geometry_keys}}
        volume = profile["build_volume"]
        design = design.model_copy(
            update={
                "bed_width_mm": volume["x_mm"],
                "bed_depth_mm": volume["y_mm"],
                "bed_height_mm": volume["z_mm"],
            }
        )
    elif design.printer_id != "custom":
        warnings.append(
            "This printer is not in the local catalog. Its bed fit has not been verified."
        )
    return design, printer, warnings


def prepare_profile(polygon: Polygon, design: DesignSettings):
    """Simplify in physical XY millimeters while retaining every hole."""
    warnings = []
    if design.detail_mode == "original":
        return polygon, warnings
    tolerance = design.nozzle_mm * DETAIL_TOLERANCE[design.detail_mode]
    simplified = polygon.simplify(tolerance, preserve_topology=True)
    if (
        not isinstance(simplified, Polygon)
        or not simplified.is_valid
        or simplified.is_empty
        or simplified.area <= 0
        or len(simplified.interiors) != len(polygon.interiors)
    ):
        raise PrintGeometryError(
            "This detail setting could not preserve the outline and holes. Choose Original detail."
        )
    warnings.append(
        f"{design.detail_mode.capitalize()} detail approximates the outline with a {tolerance:g} mm simplification tolerance. "
        "Inspect small features; this is not a printer accuracy guarantee."
    )
    return simplified, warnings


def _polygon_members(geometry):
    if isinstance(geometry, Polygon):
        return [geometry] if not geometry.is_empty and geometry.area > 0 else []
    if isinstance(geometry, (MultiPolygon, GeometryCollection)):
        return [polygon for member in geometry.geoms for polygon in _polygon_members(member)]
    return []


def split_profile(polygon: Polygon, design: DesignSettings):
    if design.output_mode == "single":
        return [polygon]
    left, bottom, right, top = polygon.bounds
    parts = []
    for row in range(design.split_rows):
        y0 = bottom + (top - bottom) * row / design.split_rows
        y1 = bottom + (top - bottom) * (row + 1) / design.split_rows
        for column in range(design.split_columns):
            x0 = left + (right - left) * column / design.split_columns
            x1 = left + (right - left) * (column + 1) / design.split_columns
            pieces = _polygon_members(polygon.intersection(box(x0, y0, x1, y1)))
            parts.extend(sorted(pieces, key=lambda item: item.bounds))
    if not parts or len(parts) > 8:
        raise PrintGeometryError(
            "This split creates more than 8 separate pieces. Use a smaller grid or single-piece output."
        )
    if any(not part.is_valid or part.area <= 0 for part in parts):
        raise PrintGeometryError("The split produced an invalid piece. Choose a different grid.")
    if not math.isclose(sum(part.area for part in parts), polygon.area, rel_tol=1e-9, abs_tol=1e-8):
        raise PrintGeometryError(
            "The split did not preserve the outline area. Choose a different grid."
        )
    return parts


def bed_fit(dimensions, design: DesignSettings, printer=None):
    """Bounding-box placement only: flat on Z, optionally rotated 90 degrees."""
    if design.printer_id != "custom" and (
        printer is None
        or printer.get("bed_shape") != "rectangular"
        or printer.get("excluded_areas_mm")
    ):
        return {
            "status": "unknown",
            "rotated_90": False,
            "reason": "Placement on this printer's shaped, excluded or unknown bed area is not verified. Check it in your slicer.",
        }
    usable_width = design.bed_width_mm - 2 * design.bed_margin_mm
    usable_depth = design.bed_depth_mm - 2 * design.bed_margin_mm
    width, depth, height = dimensions["width"], dimensions["height"], dimensions["thickness"]
    tolerance = 1e-6
    fits_z = height <= design.bed_height_mm + tolerance
    straight = width <= usable_width + tolerance and depth <= usable_depth + tolerance
    rotated = depth <= usable_width + tolerance and width <= usable_depth + tolerance
    fits = fits_z and (straight or rotated)
    return {
        "status": "fits" if fits else "too_large",
        "rotated_90": bool(fits and not straight and rotated),
        "reason": (
            "Fits the rectangular envelope with the selected XY margin after a 90-degree rotation; slicer checks are still required."
            if fits and not straight
            else "Fits the rectangular envelope with the selected XY margin; slicer checks are still required."
            if fits
            else "Exceeds the usable rectangular envelope in this flat orientation, including a 90-degree rotation."
        ),
    }


def aggregate_fit(parts):
    statuses = [part["bed_fit"]["status"] for part in parts]
    status = (
        "too_large" if "too_large" in statuses else "unknown" if "unknown" in statuses else "fits"
    )
    reasons = {
        "fits": "Each piece fits separately in the checked rectangular envelope. This is not a printability guarantee.",
        "too_large": "At least one piece exceeds the checked envelope. Reduce scale, change the split or choose another printer.",
        "unknown": "Bed placement is not verified for this printer. Check every piece in your slicer.",
    }
    return {
        "status": status,
        "rotated_90": False,
        "reason": reasons[status],
        "part_count": len(parts),
    }
