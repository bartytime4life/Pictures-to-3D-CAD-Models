"""Outer convex bounds for exact fitted lines, circular arcs and circles.

Each sampled normal uses the analytic maximum over the entire boundary, not
sampled curve points. Its supporting half-plane contains the whole solid.
Intersecting 256 such half-planes therefore gives an outer polygon: fitting
that polygon certifies a placement, but failing to fit it is inconclusive.
"""

import math

import numpy as np
from shapely.geometry import Polygon

from .fitting import arc_geometry
from .placement import FIT_TOLERANCE_MM

ENCLOSURE_DIRECTIONS = 256


def fitted_outer_envelope(outer):
    """Enclose one model-space fitted ring; holes cannot increase its extents.

    Work near the origin to stabilize translated input. Adjacent equally spaced
    supporting lines intersect in cyclic order, producing at most 256 vertices.
    Work is O(s * 256) for s segments, with O(256) temporary storage. The existing
    continuous-angle solver then searches rotations of this outer polygon.
    """
    origin = np.asarray(outer[0][1], dtype=float)
    angles = np.arange(ENCLOSURE_DIRECTIONS) * (math.tau / ENCLOSURE_DIRECTIONS)
    normals = np.column_stack((np.cos(angles), np.sin(angles)))
    support = np.full(ENCLOSURE_DIRECTIONS, -np.inf)
    for segment in outer:
        kind = segment[0]
        if kind == "circle":
            centre = np.asarray(segment[1]) - origin
            support = np.maximum(support, normals @ centre + segment[2])
            continue
        points = [np.asarray(point) - origin for point in segment[1:]]
        for point in (points[0], points[-1]):
            support = np.maximum(support, normals @ point)
        if kind == "arc":
            centre, radius, start, sweep = arc_geometry(*points)
            # Inside the signed sweep the maximum occurs at the radial normal;
            # outside it the maximum is at one of the two endpoints checked above.
            phase = ((1 if sweep > 0 else -1) * (angles - start)) % math.tau
            inside = phase <= abs(sweep) + 1e-12
            support[inside] = np.maximum(
                support[inside], normals[inside] @ centre + radius
            )
        elif kind != "line":
            raise ValueError("Unsupported fitted boundary segment.")
    if not np.isfinite(support).all():
        raise ValueError("Fitted boundary support is not finite.")
    # Outward numerical padding, not a fabrication allowance or accuracy estimate.
    support += FIT_TOLERANCE_MM
    step = math.tau / ENCLOSURE_DIRECTIONS
    tangent = np.column_stack((-normals[:, 1], normals[:, 0]))
    offset = (np.roll(support, -1) - support * math.cos(step)) / math.sin(step)
    vertices = support[:, None] * normals + offset[:, None] * tangent
    polygon = Polygon(vertices + origin).convex_hull
    if not isinstance(polygon, Polygon) or not polygon.is_valid or polygon.area <= 0:
        raise ValueError("Fitted boundary enclosure is not a valid polygon.")
    return polygon
