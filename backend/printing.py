"""Deterministic profile changes and conservative printer envelope checks."""

import json
import math
from pathlib import Path

from shapely.errors import GEOSException
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box

from .curve_envelope import ENCLOSURE_DIRECTIONS, fitted_outer_envelope
from .models import DesignSettings
from .placement import FIT_TOLERANCE_MM, rectangular_placement

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "printers.json"
DETAIL_TOLERANCE = {"draft": 0.5, "balanced": 0.25, "fine": 0.1}


class PrintGeometryError(ValueError):
    """A bounded geometry failure whose message is suitable for the user."""


def load_printer_catalog():
    if not CATALOG_PATH.is_file():
        return {"schema_version": 1, "source": None, "printers": []}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


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


def bed_fit(dimensions, design: DesignSettings, printer=None, *, footprint=None, fitted_outer=None):
    """Check one flat piece at any XY angle, retaining a placement witness.

    A polygon footprint is exact for polygon extrusions. When absent (fitted
    curves), first try the solid's enclosing rectangle, then an outer polygon
    from analytic supports of the fitted outer ring. Either positive result is
    safe; failure of an outer bound cannot rule out the actual curved solid.
    """
    basis = "outline" if footprint is not None else "bounding_box"
    common = {"rotated_90": False, "basis": basis}
    if design.printer_id != "custom" and (
        printer is None
        or printer.get("bed_shape") != "rectangular"
        or printer.get("excluded_areas_mm")
    ):
        return {
            "status": "unknown",
            **common,
            "reason": "Placement on this printer's shaped, excluded or unknown bed area is not verified. Check it in your slicer.",
        }
    usable_width = design.bed_width_mm - 2 * design.bed_margin_mm
    usable_depth = design.bed_depth_mm - 2 * design.bed_margin_mm
    width, depth, height = dimensions["width"], dimensions["height"], dimensions["thickness"]
    if height > design.bed_height_mm + FIT_TOLERANCE_MM:
        return {
            **common,
            "status": "too_large",
            "reason": "Exceeds the selected build height in this flat orientation.",
        }
    if min(usable_width, usable_depth) <= 0:
        return {
            **common,
            "status": "too_large",
            "reason": "The selected XY margin leaves no usable bed rectangle.",
        }
    placement = rectangular_placement(
        footprint if footprint is not None else box(0, 0, width, depth), usable_width, usable_depth
    )
    if placement is None and footprint is None and fitted_outer is not None:
        try:
            envelope = fitted_outer_envelope(fitted_outer)
            placement = rectangular_placement(envelope, usable_width, usable_depth)
            common.update(basis="curve_envelope", enclosure_directions=ENCLOSURE_DIRECTIONS)
        except (ValueError, ArithmeticError, GEOSException):
            # A numerical failure in optional planning must not discard valid CAD.
            return {
                **common,
                "status": "unknown",
                "reason": "The curved outline's outer enclosure could not be verified. Check placement in your slicer.",
            }
    if placement is None:
        return {
            **common,
            "status": "too_large" if footprint is not None else "unknown",
            "reason": (
                "No in-plane rotation of this outline fits the rectangular envelope with the selected XY margin."
                if footprint is not None
                else "No checked outer enclosure fits. Placement of the curved outline needs review in your slicer."
            ),
        }
    angle = placement["rotation_deg"]
    turn = f" after an approximately {angle:.6f}° counterclockwise XY turn" if angle else ""
    return {
        **common,
        **placement,
        "status": "fits",
        "rotated_90": math.isclose(angle, 90, abs_tol=1e-9),
        "reason": f"Fits the rectangular envelope with the selected XY margin{turn}; verify the placement in your slicer. Geometry exports keep their original orientation.",
    }


def aggregate_fit(parts):
    statuses = [part["bed_fit"]["status"] for part in parts]
    status = (
        "too_large" if "too_large" in statuses else "unknown" if "unknown" in statuses else "fits"
    )
    reasons = {
        "fits": "Each piece fits separately in the checked rectangular envelope. This is not a printability guarantee.",
        "too_large": "At least one piece exceeds the checked envelope. Reduce scale, change the split or choose another printer.",
        "unknown": "At least one piece needs a placement check in your slicer. Review the per-piece results.",
    }
    return {
        "status": status,
        "rotated_90": False,
        "reason": reasons[status],
        "part_count": len(parts),
    }


def suggest_split_plan(polygon: Polygon, thickness, design: DesignSettings, printer=None):
    """Find the fewest fitting pieces among the eleven supported nontrivial grids.

    Only polygon extrusions are eligible. Every candidate uses the same clipping,
    connected-component limit, area preservation and continuous-angle fit checks
    as a build. Prefer fewer actual pieces, then fewer cut lines, then fewer rows
    and columns. This returns settings to review, never altered source geometry.
    """
    left, bottom, right, top = polygon.bounds
    dimensions = {"width": right - left, "height": top - bottom, "thickness": thickness}
    source_fit = bed_fit(dimensions, design, printer, footprint=polygon)
    if source_fit["status"] != "too_large":
        return None
    no_plan = {"status": "no_fit", "grids_considered": 0, "grids_failed": 0}
    if thickness > design.bed_height_mm + FIT_TOLERANCE_MM:
        return {
            **no_plan,
            "reason": "Splitting does not reduce thickness. Check the build height or thickness setting.",
        }
    if min(design.bed_width_mm, design.bed_depth_mm) <= 2 * design.bed_margin_mm:
        return {
            **no_plan,
            "reason": "The selected margin leaves no usable bed rectangle for split pieces.",
        }

    best, best_rank = None, None
    considered = failed = 0
    for columns in range(1, 5):
        for rows in range(1, 5):
            if columns * rows == 1 or columns * rows > 8:
                continue
            considered += 1
            candidate = design.model_copy(
                update={"output_mode": "split", "split_columns": columns, "split_rows": rows}
            )
            try:
                pieces = split_profile(polygon, candidate)
                checked = []
                for piece in pieces:
                    x0, y0, x1, y1 = piece.bounds
                    dims = {"width": x1 - x0, "height": y1 - y0, "thickness": thickness}
                    fit = bed_fit(dims, candidate, printer, footprint=piece)
                    if fit["status"] != "fits":
                        break
                    checked.append({"dimensions": dims, "area_mm2": piece.area, "bed_fit": fit})
                else:
                    rank = (len(pieces), columns + rows - 2, rows, columns)
                    if best_rank is None or rank < best_rank:
                        best_rank = rank
                        best = {
                            "status": "suggested",
                            "columns": columns,
                            "rows": rows,
                            "piece_count": len(pieces),
                            "pieces": checked,
                        }
            except PrintGeometryError:
                # An optional suggestion must not discard an otherwise valid build.
                # Grids with more than eight connected fragments are unsupported.
                continue
            except GEOSException:
                failed += 1
    return {
        **(best or {"status": "no_fit"}),
        "grids_considered": considered,
        "grids_failed": failed,
        "reason": (
            "Smallest fitting plan found. Some cut grids could not be checked; inspect the cuts and pieces after rebuilding."
            if best and failed
            else "Fewest fitting pieces among the supported straight-cut grids. Review the cuts and assembly after rebuilding."
            if best
            else "No fitting split was found, and some cut grids could not be checked. Try another bed or a different manual plan."
            if failed
            else "No fitting split was found within 1–4 rows, 1–4 columns and at most 8 cells and pieces. Check another bed or a different manual plan."
        ),
    }
