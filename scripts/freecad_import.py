"""Report how FreeCAD reads exported STEP and DXF files, as JSON.

Runs inside FreeCAD's own Python, not the workbench environment:
    freecadcmd scripts/freecad_import.py <model.step> <model.dxf> <report.json>
freecadcmd passes no script arguments, so the paths come from FREECAD_CHECK_ARGS
(tab-separated) when set; scripts/freecad_check.py sets it.
"""

import json
import os
import sys

import FreeCAD
import Import
import importDXF
import Part

step_path, dxf_path, report_path = (
    os.environ["FREECAD_CHECK_ARGS"].split("\t")
    if "FREECAD_CHECK_ARGS" in os.environ
    else sys.argv[-3:]
)

document = FreeCAD.newDocument("step")
Import.insert(step_path, document.Name)
shapes = [o.Shape for o in document.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
shape = shapes[0] if len(shapes) == 1 else Part.makeCompound(shapes)
box = shape.BoundBox
faces = {}
for face in shape.Faces:
    kind = type(face.Surface).__name__
    faces[kind] = faces.get(kind, 0) + 1

drawing = FreeCAD.newDocument("dxf")
importDXF.insert(dxf_path, drawing.Name)
edges = [e for o in drawing.Objects if hasattr(o, "Shape") for e in o.Shape.Edges]


def is_circle(edge):
    return isinstance(edge.Curve, Part.Circle)


report = {
    "freecad": ".".join(FreeCAD.Version()[:3]),
    "step": {
        "objects": len(shapes),
        "solids": len(shape.Solids),
        "valid": shape.isValid(),
        "faces": faces,
        "cylinder_radii": sorted(
            f.Surface.Radius for f in shape.Faces if isinstance(f.Surface, Part.Cylinder)
        ),
        "size": [box.XLength, box.YLength, box.ZLength],
        "volume": shape.Volume,
    },
    "dxf": {
        "lines": sum(isinstance(e.Curve, Part.Line) for e in edges),
        "other": sum(not isinstance(e.Curve, (Part.Line, Part.Circle)) for e in edges),
        "circle_radii": sorted(e.Curve.Radius for e in edges if is_circle(e) and e.isClosed()),
        "arc_radii": sorted(e.Curve.Radius for e in edges if is_circle(e) and not e.isClosed()),
    },
}
with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
