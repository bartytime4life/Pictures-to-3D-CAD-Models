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

from .models import BuildRequest, DesignSettings
from .printing import (
    PrintGeometryError,
    aggregate_fit,
    bed_fit,
    prepare_profile,
    resolve_design,
    split_profile,
)
from .scad import profile_source


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
    polygon, detail_warnings = prepare_profile(polygon, design)
    warnings.extend(detail_warnings)
    polygons = split_profile(polygon, design)
    solids = [extrude_profile(part, thickness) for part in polygons]
    shape = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
    volume = shape.Volume()
    if not math.isclose(volume, polygon.area * thickness, rel_tol=1e-6, abs_tol=1e-7):
        raise PrintGeometryError("The split assembly did not preserve the expected volume.")
    dimensions = dimensions_of(shape)
    export_solid(shape, job_dir, "model")
    (job_dir / "model.scad").write_text(profile_source(polygons, thickness), encoding="utf-8")

    # Each closed DXF loop describes a real part outline, including split edges.
    drawing = ezdxf.new("R2010")
    drawing.units = ezdxf.units.MM
    drawing.header["$MEASUREMENT"] = 1
    modelspace = drawing.modelspace()
    for part in polygons:
        modelspace.add_lwpolyline(
            list(part.exterior.coords)[:-1], close=True, dxfattribs={"layer": "OUTLINE"}
        )
        for ring in part.interiors:
            modelspace.add_lwpolyline(
                list(ring.coords)[:-1], close=True, dxfattribs={"layer": "HOLES"}
            )
    drawing.saveas(job_dir / "profile.dxf")

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
            "bed_fit": bed_fit(part_dimensions, design, printer),
            "mesh": mesh_of(solid),
        }
        if design.output_mode == "split":
            # Individual files sit at XY zero for slicer placement; the manifest
            # records the translation needed to reassemble them without gaps.
            export_solid(solid.translate((-bounds.xmin, -bounds.ymin, 0)), job_dir, part_id)
            part["files"] = {"step": f"{part_id}.step", "stl": f"{part_id}.stl"}
            bundle_files.extend(part["files"].values())
        parts.append(part)

    recipe = {
        "format": "pictures-to-cad",
        "version": 2 if request.design is not None else 1,
        "name": request.name,
        "profile": request.profile.model_dump(),
        "width_mm": request.width_mm,
        "thickness_mm": request.thickness_mm,
        "units": "mm",
        "provenance": "Image outline with user-supplied bounding width and thickness; hidden geometry is not recovered.",
    }
    if request.design is not None:
        recipe["design"] = design.model_dump()
    (job_dir / "project.json").write_text(
        json.dumps(recipe, indent=2, allow_nan=False), encoding="utf-8"
    )

    downloads = {
        kind: f"/api/download/{job_dir.name}/{kind}"
        for kind in ("step", "stl", "dxf", "scad", "project")
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
            "Color and material are saved in the project recipe and parts manifest; STEP/STL/DXF/SCAD do not encode these choices.",
            "Bed fit checks the flat bounding envelope only. Verify placement, small features, supports and material settings in your slicer.",
        ]
    )
    result = {
        "id": job_dir.name,
        "revision": request.revision,
        "dimensions": dimensions,
        "volume_mm3": volume,
        "hole_count": len(polygon.interiors),
        "mesh": mesh_of(shape),
        "downloads": downloads,
        "warnings": warnings,
        "design": design.model_dump(),
        "parts": parts,
        "print_fit": aggregate_fit(parts),
    }
    for name in ("profile.dxf", "model.scad", "project.json"):
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
                    "public": isinstance(exc, PrintGeometryError),
                }
            ),
            encoding="utf-8",
        )
        raise SystemExit(1)
