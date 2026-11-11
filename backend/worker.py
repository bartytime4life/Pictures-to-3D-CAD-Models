"""One bounded CAD process per build. Run with python -m backend.worker JOB_DIR."""

import json
import math
import sys
import zipfile
from pathlib import Path

import cadquery as cq
import ezdxf
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from . import drawing
from .fitting import arc_geometry
from .models import BuildRequest, DesignSettings, ring_polygon
from .printing import (
    PrintGeometryError,
    aggregate_fit,
    bed_fit,
    prepare_profile,
    resolve_design,
    split_profile,
)
from .scad import fitted_source, profile_source
from .slicer_handoff import write_slicer_handoffs
from .three_mf import ThreeMFError, write_3mf


def extrude_profile(polygon, thickness):
    polygon = orient(polygon, sign=1)

    def wire(points):
        return cq.Wire.makePolygon([cq.Vector(x, y, 0) for x, y in points], close=True)

    shape = cq.Solid.extrudeLinear(
        wire(list(polygon.exterior.coords)[:-1]),
        [wire(list(ring.coords)[:-1]) for ring in polygon.interiors],
        (0, 0, thickness),
    )
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise PrintGeometryError(
            "This outline could not form a valid solid. Review narrow edges, holes and the split grid."
        )
    volume = shape.Volume()
    if (
        not math.isfinite(volume)
        or volume <= 0
        or not math.isclose(volume, polygon.area * thickness, rel_tol=1e-6, abs_tol=1e-7)
    ):
        raise PrintGeometryError(
            "The generated solid did not pass its volume check. Review the outline."
        )
    return shape


def model_rings(primitives, convert, scale):
    """Fitted segments in model millimetres: ("line", a, b), ("arc", a, m, b), ("circle", c, r)."""
    rings = []
    for ring in [primitives.outer, *primitives.holes]:
        out = []
        for s in ring:
            if s.kind == "circle":
                out.append(("circle", convert([s.center])[0], s.radius * scale))
            elif s.kind == "line":
                a, b = convert([s.start, s.end])
                out.append(("line", a, b))
            else:
                out.append(("arc", *convert([s.start, s.mid, s.end])))
        rings.append(out)
    return rings


def wire_of(ring):
    def v(p):
        return cq.Vector(p[0], p[1], 0)

    if ring[0][0] == "circle":
        return cq.Wire.makeCircle(ring[0][2], v(ring[0][1]), cq.Vector(0, 0, 1))
    edges = []
    for s in ring:
        if s[0] == "line":
            edges.append(cq.Edge.makeLine(v(s[1]), v(s[2])))
        else:
            edges.append(cq.Edge.makeThreePointArc(v(s[1]), v(s[2]), v(s[3])))
    return cq.Wire.assembleEdges(edges)


# Fitted rings are sampled within this distance (mm) of each arc for the solid check.
SAMPLE_SAGITTA_MM = 0.001


def extrude_fitted(rings, thickness, polygon):
    """Extrude exact lines, arcs and circles; checked against the reviewed polygon."""
    try:
        wires = [wire_of(ring) for ring in rings]
        face = cq.Face.makeFromWires(wires[0], wires[1:])
        shape = cq.Solid.extrudeLinear(wires[0], wires[1:], (0, 0, thickness))
    except Exception as exc:
        raise PrintGeometryError(
            "The fitted outline could not form a solid. Re-trace with design-intent snapping off."
        ) from exc
    volume = shape.Volume()
    if (
        not shape.isValid()
        or len(shape.Solids()) != 1
        or not math.isfinite(volume)
        or not math.isclose(volume, face.Area() * thickness, rel_tol=1e-6)
        # The exact solid must be the outline the user reviewed (sampled within microns).
        # An inscribed sample loses under one sagitta per unit of boundary length, so
        # allow that much on top of the relative tolerance (small circles need it).
        or not math.isclose(
            face.Area(), polygon.area, rel_tol=1e-4, abs_tol=SAMPLE_SAGITTA_MM * polygon.length
        )
    ):
        raise PrintGeometryError(
            "The fitted outline did not pass its solid checks. Re-trace with design-intent snapping off."
        )
    return shape, face.Area()


def fitted_counts(rings):
    counts = {"lines": 0, "arcs": 0, "circles": 0}
    for ring in rings:
        for s in ring:
            counts[{"line": "lines", "arc": "arcs", "circle": "circles"}[s[0]]] += 1
    return counts


def write_fitted_dxf(path, rings):
    """LINE, ARC and CIRCLE entities: true geometry for CAD/CAM import."""
    document = ezdxf.new("R2010")
    document.units = ezdxf.units.MM
    document.header["$MEASUREMENT"] = 1
    modelspace = document.modelspace()
    for index, ring in enumerate(rings):
        layer = {"layer": "OUTLINE" if index == 0 else "HOLES"}
        for s in ring:
            if s[0] == "circle":
                modelspace.add_circle(s[1], s[2], dxfattribs=layer)
            elif s[0] == "line":
                modelspace.add_line(s[1], s[2], dxfattribs=layer)
            else:
                (cx, cy), r, a0, sweep = arc_geometry(s[1], s[2], s[3])
                start, end = (a0, a0 + sweep) if sweep > 0 else (a0 + sweep, a0)
                modelspace.add_arc(
                    (cx, cy), r, math.degrees(start), math.degrees(end), dxfattribs=layer
                )
    document.saveas(path)


def dimensions_of(shape):
    bounds = shape.BoundingBox()
    return {"width": bounds.xlen, "height": bounds.ylen, "thickness": bounds.zlen}


def mesh_of(shape):
    vertices, triangles = shape.tessellate(0.05, 0.1)
    return {
        "vertices": [v for vertex in vertices for v in vertex.toTuple()],
        "triangles": [v for triangle in triangles for v in triangle],
    }


def export_solid(shape, directory, basename):
    cq.exporters.export(shape, str(directory / f"{basename}.step"), exportType="STEP")
    cq.exporters.export(
        shape,
        str(directory / f"{basename}.stl"),
        exportType="STL",
        tolerance=0.05,
        angularTolerance=0.1,
    )
    for suffix in ("step", "stl"):
        if (directory / f"{basename}.{suffix}").stat().st_size == 0:
            raise PrintGeometryError("An export was empty. Try rebuilding the model.")


def _sampled(primitives, convert, scale):
    """Outer and hole vertex lists of the fitted rings, within 1 micron of each arc."""
    sampled = [convert(ring_polygon(ring, SAMPLE_SAGITTA_MM / scale)) for ring in [primitives.outer, *primitives.holes]]
    return sampled[0], sampled[1:]


def build(job_dir: Path) -> dict:
    request = BuildRequest.model_validate_json((job_dir / "input.json").read_text(encoding="utf-8"))
    design, printer, warnings = resolve_design(request.design or DesignSettings())
    xs, ys = zip(*request.profile.outer)
    center_x, center_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    scale = request.width_mm * design.scale_percent / 100 / (max(xs) - min(xs))
    thickness = request.thickness_mm * design.thickness_percent / 100

    def convert(ring):
        return [((x - center_x) * scale, (center_y - y) * scale) for x, y in ring]

    polygon = orient(
        Polygon(convert(request.profile.outer), [convert(r) for r in request.profile.holes]), sign=1
    )
    primitives = request.profile.primitives
    fitted = primitives is not None and design.output_mode == "single"
    geometry = {"kind": "polygon"}
    if fitted:
        rings = model_rings(primitives, convert, scale)
        # The polygon the user reviewed, re-sampled finely, checks the exact solid.
        exact = orient(
            Polygon(*_sampled(primitives, convert, scale)), sign=1
        )
        shape, _ = extrude_fitted(rings, thickness, exact if exact.is_valid else polygon)
        solids, polygons = [shape], [exact if exact.is_valid else polygon]
        volume = shape.Volume()
        geometry = {"kind": "fitted", **fitted_counts(rings)}
        if design.detail_mode != "original":
            warnings.append(
                "Geometry detail does not simplify a fitted outline: its exported edges are the fitted lines, arcs and circles."
            )
    else:
        if primitives is not None:
            warnings.append(
                "Split pieces use the traced outline polygon. Exact arcs and circles are exported only for single-piece output."
            )
        polygon, detail_warnings = prepare_profile(polygon, design)
        warnings.extend(detail_warnings)
        polygons = split_profile(polygon, design)
        solids = [extrude_profile(part, thickness) for part in polygons]
    shape = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
    if not fitted:
        volume = shape.Volume()
        if not math.isclose(volume, polygon.area * thickness, rel_tol=1e-6, abs_tol=1e-7):
            raise PrintGeometryError("The split assembly did not preserve the expected volume.")
    dimensions = dimensions_of(shape)
    export_solid(shape, job_dir, "model")
    if fitted:
        (job_dir / "model.scad").write_text(fitted_source(rings, thickness), encoding="utf-8")
        write_fitted_dxf(job_dir / "profile.dxf", rings)
        loops = drawing.fitted_loops(rings)
    else:
        loops = drawing.polygon_loops(polygons)
        (job_dir / "model.scad").write_text(profile_source(polygons, thickness), encoding="utf-8")
        # Each closed DXF loop describes a real part outline, including split edges.
        outline = ezdxf.new("R2010")
        outline.units = ezdxf.units.MM
        outline.header["$MEASUREMENT"] = 1
        modelspace = outline.modelspace()
        for part in polygons:
            modelspace.add_lwpolyline(
                list(part.exterior.coords)[:-1], close=True, dxfattribs={"layer": "OUTLINE"}
            )
            for ring in part.interiors:
                modelspace.add_lwpolyline(
                    list(ring.coords)[:-1], close=True, dxfattribs={"layer": "HOLES"}
                )
        outline.saveas(job_dir / "profile.dxf")
    # The same loops as the DXF, for cutters and vector editors and for a 1:1 print.
    (job_dir / "profile.svg").write_text(drawing.svg(loops, request.name), encoding="utf-8")
    (job_dir / "drawing.pdf").write_bytes(drawing.pdf(loops, request.name))

    parts = []
    bundle_files = []
    for index, solid in enumerate(solids, start=1):
        part_id = f"part-{index:02d}"
        bounds = solid.BoundingBox()
        part_dimensions = dimensions_of(solid)
        part = {
            "id": part_id,
            "name": f"Part {index}",
            "dimensions": part_dimensions,
            "volume_mm3": solid.Volume(),
            "assembly_offset_mm": [bounds.xmin, bounds.ymin, 0],
            "bed_fit": bed_fit(
                part_dimensions, design, printer, footprint=None if fitted else polygons[index - 1]
            ),
            "mesh": mesh_of(solid),
        }
        if design.output_mode == "split":
            # Individual files sit at XY zero for slicer placement; the manifest
            # records the translation needed to reassemble them without gaps.
            normalized = solid.translate((-bounds.xmin, -bounds.ymin, 0))
            export_solid(normalized, job_dir, part_id)
            write_3mf(
                job_dir / f"{part_id}.3mf",
                [{"name": part["name"], "mesh": mesh_of(normalized)}],
                name=f"{request.name} — {part['name']}",
            )
            part["files"] = {
                "step": f"{part_id}.step", "stl": f"{part_id}.stl", "3mf": f"{part_id}.3mf"
            }
            bundle_files.extend(part["files"].values())
        parts.append(part)

    write_3mf(job_dir / "model.3mf", parts, name=request.name)

    reference = request.profile.reference
    if reference is not None:
        xs_ = [x for x, _ in request.profile.outer]
        sheet_width = (max(xs_) - min(xs_)) * reference.mm_per_px
        scaled_by_sheet = math.isclose(sheet_width, request.width_mm, rel_tol=1e-6)
        provenance = (
            "Image outline rectified on a reference sheet of stated size, with lens, perspective"
            + (" and thickness-parallax" if reference.thickness_mm else "")
            + " correction; "
            + ("scale from the sheet" if scaled_by_sheet else "scale from a user-supplied width")
            + "; user-supplied thickness; hidden geometry is not recovered."
        )
    else:
        provenance = "Image outline with user-supplied bounding width and thickness; hidden geometry is not recovered."
    has_fit = request.profile.primitives is not None or reference is not None
    recipe = {
        "format": "pictures-to-cad",
        "version": 3 if has_fit else (2 if request.design is not None else 1),
        "name": request.name,
        "profile": request.profile.model_dump(exclude_none=True),
        "width_mm": request.width_mm,
        "thickness_mm": request.thickness_mm,
        "units": "mm",
        "provenance": provenance,
    }
    # Every version after 1 carries its design settings: the app requires them to open it.
    if recipe["version"] != 1:
        recipe["design"] = design.model_dump()
    (job_dir / "project.json").write_text(
        json.dumps(recipe, indent=2, allow_nan=False), encoding="utf-8"
    )
    write_slicer_handoffs(
        job_dir,
        name=request.name,
        design=design.model_dump(),
        dimensions=dimensions,
        volume_mm3=volume,
        parts=parts,
    )

    downloads = {
        kind: f"/api/download/{job_dir.name}/{kind}"
        for kind in ("step", "stl", "dxf", "svg", "pdf", "scad", "project", "3mf", "bambu", "prusa")
    }
    if design.output_mode == "split":
        manifest = {
            "format": "pictures-to-cad-parts",
            "version": 1,
            "units": "mm",
            "name": request.name,
            "design": design.model_dump(),
            "assembly_dimensions": dimensions,
            "total_volume_mm3": volume,
            "parts": [
                {key: value for key, value in part.items() if key != "mesh"} for part in parts
            ],
            "notes": [
                "Each part file has its minimum XY at zero and its bottom at Z zero.",
                "Add assembly_offset_mm to each part to reconstruct the combined assembly.",
                "Parts have straight cuts with no connectors, clearance, glue allowance or kerf compensation.",
                "Pieces are checked against the bed separately; arrange and verify each in a slicer.",
            ],
        }
        (job_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8"
        )
        with zipfile.ZipFile(
            job_dir / "parts.zip", "w", compression=zipfile.ZIP_DEFLATED
        ) as bundle:
            for filename in ["manifest.json", *bundle_files]:
                bundle.write(job_dir / filename, arcname=filename)
        downloads["parts"] = f"/api/download/{job_dir.name}/parts"
        warnings.append(
            "Split pieces have straight cuts with no connectors, clearance or kerf compensation. "
            "Use the separate files in the parts ZIP for printing; the combined exports keep the assembled positions."
        )
    warnings.extend(
        [
            "STL coordinates are in millimeters. Set millimeters explicitly when importing the mesh.",
            "Color and material are planning notes in the project and handoff manifests; geometry exports do not assign filament or slicer presets.",
            "Bed fit checks one flat piece at a time in a clear rectangular envelope. Suggested XY turns are not applied to exports. Verify placement, small features, supports and material settings in your slicer.",
        ]
    )
    result = {
        "id": job_dir.name,
        "revision": request.revision,
        "dimensions": dimensions,
        "volume_mm3": volume,
        "hole_count": len(polygon.interiors),
        "geometry": geometry,
        "mesh": mesh_of(shape),
        "downloads": downloads,
        "warnings": warnings,
        "design": design.model_dump(),
        "parts": parts,
        "print_fit": aggregate_fit(parts),
    }
    for name in (
        "profile.dxf", "profile.svg", "drawing.pdf", "model.scad", "project.json", "model.3mf",
        "bambu-handoff.zip", "prusa-handoff.zip",
    ):
        if (job_dir / name).stat().st_size == 0:
            raise PrintGeometryError("An export was empty. Try rebuilding the model.")
    (job_dir / "result.json").write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    directory = Path(sys.argv[1]).resolve()
    try:
        build(directory)
    except Exception as exc:  # noqa: BLE001 - isolate all CAD kernel failures at the worker boundary.
        (directory / "error.json").write_text(
            json.dumps(
                {
                    "error": str(exc)[:500],
                    "public": isinstance(exc, (PrintGeometryError, ThreeMFError)),
                }
            ),
            encoding="utf-8",
        )
        raise SystemExit(1)
