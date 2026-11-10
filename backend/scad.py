"""Editable OpenSCAD source for the same final planar profiles used by the CAD worker."""

import json
import math


def profile_source(polygons, thickness: float) -> str:
    """Serialize only validated numeric geometry, never project names or arbitrary code."""
    lines = [
        "// Pictures to CAD: reviewed polygon extrusion, coordinates in millimeters.",
        "// These final profiles include the workbench's design scale, detail and split cuts.",
        "// Traced boundaries are approximations, not recovered CAD constraints or feature history.",
        "// Default values match the built assembly. Review dimensions after editing.",
        f"thickness_mm = {json.dumps(thickness, allow_nan=False)};",
        "xy_scale = 1; // Additional XY scale; 1 keeps the exported dimensions.",
        "part_index = 0; // 0 shows the assembly; 1 and above select a split piece.",
        "",
        'assert(thickness_mm > 0 && xy_scale > 0, "Thickness and XY scale must be positive.");',
        f'assert(part_index >= 0 && part_index <= {len(polygons)} && floor(part_index) == part_index, "Choose a whole part index in range.");',
        "",
    ]
    for index, polygon in enumerate(polygons, start=1):
        points = []
        paths = []
        for ring in [polygon.exterior, *polygon.interiors]:
            ring_points = list(ring.coords)[:-1]
            paths.append(list(range(len(points), len(points) + len(ring_points))))
            points.extend(ring_points)
        lines.extend(
            [
                f"module part_{index:02d}() {{",
                "  scale([xy_scale, xy_scale, 1])",
                "    linear_extrude(height = thickness_mm, convexity = 10)",
                "      polygon(",
                f"        points = {json.dumps(points, allow_nan=False)},",
                f"        paths = {json.dumps(paths)}",
                "      );",
                "}",
                "",
            ]
        )
    lines.append("union() {")
    lines.extend(
        f"  if (part_index == 0 || part_index == {index}) part_{index:02d}();"
        for index in range(1, len(polygons) + 1)
    )
    lines.extend(["}", ""])
    return "\n".join(lines)


def fitted_source(rings, thickness: float) -> str:
    """OpenSCAD for a fitted outline: circles stay circle(), other boundaries polygons.

    `rings` are model-millimetre segment rings (outer first), as built by the worker.
    Arcs in non-circular boundaries are sampled within 0.005 mm.
    """
    from .fitting import arc_geometry

    def ring_points(ring):
        points = []
        for segment in ring:
            if segment[0] == "line":
                points.append(list(segment[1]))
                continue
            (cx, cy), r, a0, sweep = arc_geometry(segment[1], segment[2], segment[3])
            step = 2 * math.acos(max(-1.0, 1 - min(0.005 / r, 1)))
            n = max(2, min(720, math.ceil(abs(sweep) / step)))
            points.extend(
                [cx + r * math.cos(a0 + sweep * k / n), cy + r * math.sin(a0 + sweep * k / n)]
                for k in range(n)
            )
        return points

    def facets(r):
        return max(24, min(720, math.ceil(math.pi / math.acos(max(-1.0, 1 - min(0.005 / r, 1))))))

    lines = [
        "// Pictures to CAD: fitted outline extrusion, coordinates in millimeters.",
        "// Circles were fitted to the traced holes and remain circle() primitives; other",
        "// boundaries are fitted lines and arcs sampled within 0.005 mm. A fit is an",
        "// approximation of the photograph, not recovered design intent. Review dimensions.",
        f"thickness_mm = {json.dumps(thickness, allow_nan=False)};",
        "xy_scale = 1; // Additional XY scale; 1 keeps the exported dimensions.",
        "part_index = 0; // This export has one piece; kept for compatibility with split exports.",
        "",
        'assert(thickness_mm > 0 && xy_scale > 0, "Thickness and XY scale must be positive.");',
        'assert(part_index == 0 || part_index == 1, "This export has one piece.");',
        "",
        "module part_01() {",
        "  scale([xy_scale, xy_scale, 1])",
        "    linear_extrude(height = thickness_mm, convexity = 10)",
        "      difference() {",
    ]
    for index, ring in enumerate(rings):
        if ring[0][0] == "circle":
            (cx, cy), r = ring[0][1], ring[0][2]
            body = (
                f"translate({json.dumps([cx, cy], allow_nan=False)}) "
                f"circle(r = {json.dumps(r, allow_nan=False)}, $fn = {facets(r)});"
            )
        else:
            body = f"polygon(points = {json.dumps(ring_points(ring), allow_nan=False)});"
        lines.append("        " + body)
    lines.extend(["      }", "}", "", "part_01();", ""])
    return "\n".join(lines)
