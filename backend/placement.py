"""Continuous-angle containment of one polygon in a clear rectangular bed.

At each convex-hull support event, the four supporting vertices can change.
Between events, width and depth have the form a*cos(theta) + b*sin(theta).
Their analytic crossings with the bed limits partition every feasible interval;
testing those crossings and interval interiors avoids an angular sampling grid.
This is O(h^2) time and O(h) storage for h hull vertices (bounded by the input
profile budget plus split intersections). It does not pack pieces or tilt Z.
"""

import math
from itertools import pairwise

import numpy as np
from shapely.geometry import Polygon

FIT_TOLERANCE_MM = 1e-6  # Numerical comparison only, not a fabrication allowance.


def _crossings(a, b, limit, lo, hi):
    """Roots of a*cos(t) + b*sin(t) = limit in the closed interval [lo, hi]."""
    radius = math.hypot(a, b)
    if radius == 0 or abs(limit) > radius:
        return []
    phase = math.atan2(b, a)
    offset = math.acos(max(-1.0, min(1.0, limit / radius)))
    return [
        root
        for sign in (-1, 1)
        for turn in (-1, 0, 1)
        if lo <= (root := phase + sign * offset + turn * math.tau) <= hi
    ]


def rectangular_placement(polygon: Polygon, width: float, depth: float):
    """Return a verified CCW rotation and footprint in mm, or None if none fits.

    Convexification preserves all directional extents, even for concave outlines
    and holes. A half-turn covers every distinct width/depth pair. Prefer the
    familiar 0 and 90 degree placements when they work; otherwise choose among
    analytic candidates by greatest minimum XY clearance, then smallest angle.
    """
    if min(width, depth) <= 0:
        return None
    hull = polygon.convex_hull
    # A rectangle containing the outline also contains its hull. This necessary
    # area bound cheaply rejects impossible candidates during split-plan search.
    if hull.area > (width + FIT_TOLERANCE_MM) * (depth + FIT_TOLERANCE_MM):
        return None
    points = np.asarray(hull.exterior.coords[:-1], dtype=float)
    # Keep projection arithmetic stable when a caller supplies translated coordinates.
    points -= points[0].copy()

    def extents(angle):
        c, s = math.cos(angle), math.sin(angle)
        x = points[:, 0] * c - points[:, 1] * s
        y = points[:, 0] * s + points[:, 1] * c
        return float(np.ptp(x)), float(np.ptp(y))

    def fits(w, d):
        return w <= width + FIT_TOLERANCE_MM and d <= depth + FIT_TOLERANCE_MM

    def record(angle, w, d):
        return {"rotation_deg": math.degrees(angle), "footprint_mm": {"width": w, "depth": d}}

    for angle in (0.0, math.pi / 2):
        w, d = extents(angle)
        if fits(w, d):
            return record(angle, w, d)

    # An edge becomes parallel to X or Y when its normal reaches a support axis.
    edges = np.roll(points, -1, axis=0) - points
    events = {0.0, math.pi}
    for dx, dy in edges:
        direction = math.atan2(dy, dx)
        events.update(((-direction) % math.pi, (math.pi / 2 - direction) % math.pi))
    events = sorted(events)
    best = None
    best_score = -math.inf
    for lo, hi in pairwise(events):
        mid = (lo + hi) / 2
        c, s = math.cos(mid), math.sin(mid)
        x = points[:, 0] * c - points[:, 1] * s
        y = points[:, 0] * s + points[:, 1] * c
        dx, dy = points[np.argmax(x)] - points[np.argmin(x)]
        ex, ey = points[np.argmax(y)] - points[np.argmin(y)]
        a, b, c_, d_ = float(dx), float(-dy), float(ey), float(ex)
        cuts = sorted(
            {lo, hi, *_crossings(a, b, width, lo, hi), *_crossings(c_, d_, depth, lo, hi)}
        )
        candidates = sorted({*cuts, *((left + right) / 2 for left, right in pairwise(cuts))})
        for angle in candidates:
            co, si = math.cos(angle), math.sin(angle)
            w, d = a * co + b * si, c_ * co + d_ * si
            score = min(width - w, depth - d)
            if fits(w, d) and score > best_score:
                best, best_score = angle, score
    if best is None:
        return None
    # Verify the witness against every hull point, independently of interval coefficients.
    w, d = extents(best)
    return record(best, w, d) if fits(w, d) else None
