"""Editable OpenSCAD source for the same final planar profiles used by the CAD worker."""

import json


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
