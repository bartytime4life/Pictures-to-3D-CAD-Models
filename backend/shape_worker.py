"""Exact constructive geometry for the shape designer, isolated by the normal CAD runner."""

import json
import math
import sys
from pathlib import Path

import cadquery as cq

from .fitting import arc_geometry
from .models import BuildRequest, Primitives, Profile
from .printing import PrintGeometryError
from .shapes import DesignShape, ShapeBuildRequest
from .worker import build as build_profile


def shape_solid(shape: DesignShape):
    w, h = shape.width_mm, shape.height_mm
    plane = cq.Workplane("XY")
    if shape.kind == "circle":
        solid = plane.circle(w / 2).extrude(1).val()
    elif shape.kind == "slot":
        length, diameter = max(w, h), min(w, h)
        if math.isclose(length, diameter, abs_tol=1e-9):
            solid = plane.circle(diameter / 2).extrude(1).val()
        else:
            angle = 0 if w >= h else 90
            solid = plane.slot2D(length, diameter, angle).extrude(1).val()
    elif shape.kind in {"triangle", "hexagon"}:
        points = (
            [(-w / 2, h / 2), (0, -h / 2), (w / 2, h / 2)]
            if shape.kind == "triangle"
            else [
                (-w / 4, -h / 2),
                (w / 4, -h / 2),
                (w / 2, 0),
                (w / 4, h / 2),
                (-w / 4, h / 2),
                (-w / 2, 0),
            ]
        )
        solid = plane.polyline(points).close().extrude(1).val()
    else:
        solid = plane.rect(w, h).extrude(1).val()
        if shape.kind == "rounded_rectangle" and shape.corner_mm > 0:
            r = shape.corner_mm
            # The limiting case is a capsule; avoid the kernel's zero-length edges.
            if math.isclose(2 * r, min(w, h), abs_tol=1e-9):
                return shape_solid(shape.model_copy(update={"kind": "slot"}))
            solid = cq.Workplane(obj=solid).edges("|Z").fillet(r).val()
    return solid.rotate((0, 0, 0), (0, 0, 1), shape.rotation_deg).translate(
        (shape.x_mm, shape.y_mm, 0)
    )


def wire_segments(wire):
    """Recover exact lines/arcs from a kernel wire, ordering and orienting its edges."""
    segments = []
    for edge in wire.Edges():
        kind = edge.geomType()
        a, b = edge.positionAt(0), edge.positionAt(1)
        start, end = (a.x, a.y), (b.x, b.y)
        if kind == "CIRCLE":
            center, radius = edge.arcCenter(), edge.radius()
            if math.isclose(edge.Length(), 2 * math.pi * radius, rel_tol=1e-8):
                if len(wire.Edges()) != 1:
                    raise PrintGeometryError("A circular boundary could not be resolved.")
                return [{"kind": "circle", "center": (center.x, center.y), "radius": radius}]
            mid = edge.positionAt(0.5)
            segments.append({"kind": "arc", "start": start, "mid": (mid.x, mid.y), "end": end})
        elif kind == "LINE":
            segments.append({"kind": "line", "start": start, "end": end})
        else:
            raise PrintGeometryError("This shape produced an unsupported curved boundary.")
    if not segments:
        raise PrintGeometryError("The design has no usable boundary.")
    ordered = [segments.pop(0)]
    while segments:
        end = ordered[-1]["end"]
        for index, segment in enumerate(segments):
            if math.dist(end, segment["start"]) < 1e-6:
                ordered.append(segments.pop(index))
                break
            if math.dist(end, segment["end"]) < 1e-6:
                segment["start"], segment["end"] = segment["end"], segment["start"]
                ordered.append(segments.pop(index))
                break
        else:
            raise PrintGeometryError("The design's edges did not form a continuous outline.")
    return ordered


def sampled_ring(segments):
    """A review polygon with cardinal extrema, so later scaling preserves exact dimensions."""
    points = []
    for segment in segments:
        if segment["kind"] == "line":
            points.append(segment["start"])
        elif segment["kind"] == "circle":
            x, y = segment["center"]
            radius = segment["radius"]
            points.extend(
                (x + radius * math.cos(k * math.pi / 48), y + radius * math.sin(k * math.pi / 48))
                for k in range(96)
            )
        else:
            (x, y), radius, a0, sweep = arc_geometry(
                segment["start"], segment["mid"], segment["end"]
            )
            n = max(2, math.ceil(abs(sweep) / (math.pi / 48)))
            parameters = {k / n for k in range(n)}
            for k in range(-8, 9):
                t = (k * math.pi / 2 - a0) / sweep
                if 0 < t < 1:
                    parameters.add(t)
            points.extend(
                (x + radius * math.cos(a0 + sweep * t), y + radius * math.sin(a0 + sweep * t))
                for t in sorted(parameters)
            )
    return points


def design_profile(request: ShapeBuildRequest):
    additions = [shape_solid(shape) for shape in request.shapes if shape.operation == "add"]
    solid = additions[0]
    for other in additions[1:]:
        solid = solid.fuse(other).clean()
    for shape in request.shapes:
        if shape.operation == "cut":
            solid = solid.cut(shape_solid(shape)).clean()
    if not solid.isValid() or len(solid.Solids()) != 1 or solid.Volume() < 1e-6:
        raise PrintGeometryError(
            "The design must be one connected part. Overlap added shapes and keep cutouts from separating it."
        )
    faces = [
        face for face in solid.Faces() if abs(face.Center().z) < 1e-6 and face.normalAt().z < -0.99
    ]
    if len(faces) != 1:
        raise PrintGeometryError("The design did not form one flat outline. Check touching edges.")
    face = faces[0]
    outer = wire_segments(face.outerWire())
    holes = [wire_segments(wire) for wire in face.innerWires()]
    try:
        primitives = Primitives(outer=outer, holes=holes)
        return Profile(
            outer=sampled_ring(outer),
            holes=[sampled_ring(ring) for ring in holes],
            primitives=primitives,
        )
    except ValueError as exc:
        raise PrintGeometryError(
            "The combined outline is too complex or too narrow. Simplify the shapes."
        ) from exc


def build(directory: Path):
    request = ShapeBuildRequest.model_validate_json((directory / "input.json").read_text())
    profile = design_profile(request)
    xs = [x for x, _ in profile.outer]
    built = BuildRequest(
        profile=profile,
        width_mm=max(xs) - min(xs),
        thickness_mm=request.thickness_mm,
        name=request.name,
        revision=request.revision,
    )
    (directory / "input.json").write_text(built.model_dump_json(), encoding="utf-8")
    return build_profile(directory)


if __name__ == "__main__":
    directory = Path(sys.argv[1]).resolve()
    try:
        build(directory)
    except Exception as exc:  # noqa: BLE001 - contain native CAD failures in the worker.
        (directory / "error.json").write_text(
            json.dumps({"error": str(exc)[:500], "public": isinstance(exc, PrintGeometryError)}),
            encoding="utf-8",
        )
        raise SystemExit(1)
