"""One bounded CAD process per build. Run with python -m backend.worker JOB_DIR."""

import json
import math
import sys
from pathlib import Path

import cadquery as cq
import ezdxf
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from .models import BuildRequest


def build(job_dir: Path) -> dict:
    request = BuildRequest.model_validate_json((job_dir / "input.json").read_text())
    xs, ys = zip(*request.profile.outer)
    center_x, center_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    scale = request.width_mm / (max(xs) - min(xs))

    def convert(ring):
        return [((x - center_x) * scale, (center_y - y) * scale) for x, y in ring]

    polygon = orient(
        Polygon(convert(request.profile.outer), [convert(r) for r in request.profile.holes]), sign=1
    )
    outer_points = list(polygon.exterior.coords)[:-1]
    hole_points = [list(ring.coords)[:-1] for ring in polygon.interiors]

    def wire(points):
        return cq.Wire.makePolygon([cq.Vector(x, y, 0) for x, y in points], close=True)

    shape = cq.Solid.extrudeLinear(
        wire(outer_points), [wire(r) for r in hole_points], (0, 0, request.thickness_mm)
    )
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError(
            "This outline could not form one valid solid. Review narrow edges and holes."
        )
    volume = shape.Volume()
    expected_volume = polygon.area * request.thickness_mm
    if (
        not math.isfinite(volume)
        or volume <= 0
        or not math.isclose(volume, expected_volume, rel_tol=1e-6, abs_tol=1e-7)
    ):
        raise ValueError("The generated solid did not pass its volume check. Review the outline.")
    bounds = shape.BoundingBox()
    cq.exporters.export(shape, str(job_dir / "model.step"), exportType="STEP")
    cq.exporters.export(
        shape, str(job_dir / "model.stl"), exportType="STL", tolerance=0.05, angularTolerance=0.1
    )
    # DXF is the planar profile, not the projected top and bottom of an extrusion.
    drawing = ezdxf.new("R2010")
    drawing.units = ezdxf.units.MM
    drawing.header["$MEASUREMENT"] = 1
    modelspace = drawing.modelspace()
    modelspace.add_lwpolyline(outer_points, close=True, dxfattribs={"layer": "OUTLINE"})
    for points in hole_points:
        modelspace.add_lwpolyline(points, close=True, dxfattribs={"layer": "HOLES"})
    drawing.saveas(job_dir / "profile.dxf")
    recipe = {
        "format": "pictures-to-cad",
        "version": 1,
        "name": request.name,
        "profile": request.profile.model_dump(),
        "width_mm": request.width_mm,
        "thickness_mm": request.thickness_mm,
        "units": "mm",
        "provenance": "Image outline with user-supplied bounding width and thickness; hidden geometry is not recovered.",
    }
    (job_dir / "project.json").write_text(json.dumps(recipe, indent=2, allow_nan=False))
    vertices, triangles = shape.tessellate(0.05, 0.1)
    result = {
        "id": job_dir.name,
        "revision": request.revision,
        "dimensions": {"width": bounds.xlen, "height": bounds.ylen, "thickness": bounds.zlen},
        "volume_mm3": volume,
        "hole_count": len(hole_points),
        "mesh": {
            "vertices": [v for vertex in vertices for v in vertex.toTuple()],
            "triangles": [v for triangle in triangles for v in triangle],
        },
        "downloads": {
            kind: f"/api/download/{job_dir.name}/{kind}"
            for kind in ("step", "stl", "dxf", "project")
        },
        "warnings": [
            "STL coordinates are in millimeters. Set millimeters explicitly when importing the mesh."
        ],
    }
    for name in ("model.step", "model.stl", "profile.dxf", "project.json"):
        if (job_dir / name).stat().st_size == 0:
            raise ValueError("An export was empty. Try rebuilding the model.")
    (job_dir / "result.json").write_text(json.dumps(result, allow_nan=False))
    return result


if __name__ == "__main__":
    directory = Path(sys.argv[1]).resolve()
    try:
        build(directory)
    except Exception as exc:  # noqa: BLE001 - isolate all CAD kernel failures at the worker boundary.
        # This local worker error is consumed by the server, never rendered as a traceback.
        (directory / "error.json").write_text(json.dumps({"error": str(exc)[:500]}))
        raise SystemExit(1)
