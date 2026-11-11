"""Describe sub-pixel boundary rings with lines, arcs and circles, with residuals.

Each closed ring becomes either one circle, a cycle of lines and arcs, or (when no
analytic description fits within tolerance) a polyline. Optional design-intent snapping
then makes near-axis lines exact, equalises near-equal radii, and rebuilds arcs between
lines as exact tangent fillets or slot end caps. Every snap is reported so the user can
review it. Units are whatever the input points use (rectified pixels here).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .sheet import intersect, line_tls


@dataclass
class Primitive:
    kind: str  # "line" | "arc" | "circle"
    data: dict
    rms: float
    max_abs: float
    span: tuple = field(default=(0, 0))


def fit_circle(points, iterations=25):
    """Kasa algebraic start, then Gauss-Newton on geometric distance.

    Returns (cx, cy, r, rms, max_abs).
    """
    x, y = points[:, 0], points[:, 1]
    a = np.column_stack([x, y, np.ones_like(x)])
    sol, *_ = np.linalg.lstsq(a, x * x + y * y, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = math.sqrt(max(sol[2] + cx * cx + cy * cy, 1e-12))
    for _ in range(iterations):
        dx, dy = x - cx, y - cy
        rho = np.maximum(np.hypot(dx, dy), 1e-12)
        jac = np.column_stack([-dx / rho, -dy / rho, -np.ones_like(rho)])
        step, *_ = np.linalg.lstsq(jac, -(rho - r), rcond=None)
        cx, cy, r = cx + step[0], cy + step[1], r + step[2]
        if np.abs(step).max() < 1e-10:
            break
    residual = np.hypot(x - cx, y - cy) - r
    return float(cx), float(cy), float(abs(r)), float(np.sqrt(np.mean(residual**2))), float(
        np.abs(residual).max()
    )


def dp_indices(points, eps):
    """Douglas-Peucker breakpoints of a closed ring (sorted indices)."""
    n = len(points)
    start = 0
    far = int(np.argmax(np.linalg.norm(points - points[0], axis=1)))
    keep = {start, far}
    stack = [(start, far), (far, start + n)]
    while stack:
        a, b = stack.pop()
        idx = np.arange(a + 1, b)
        if len(idx) == 0:
            continue
        p, q = points[a % n], points[b % n]
        d = q - p
        length = np.linalg.norm(d) + 1e-12
        dist = np.abs((points[idx % n] - p) @ np.array([-d[1], d[0]]) / length)
        j = int(np.argmax(dist))
        if dist[j] > eps:
            k = int(idx[j])
            keep.add(k % n)
            stack.extend([(a, k), (k, b)])
    return sorted(keep)


def span_points(points, a, b):
    n = len(points)
    if b >= a:
        return points[np.arange(a, b + 1) % n]
    return points[np.r_[np.arange(a, n), np.arange(0, b + 1)]]


def fit_ring(points, tol, min_line, circle_rel=0.01):
    """A circle, a cycle of lines and arcs, or None (keep the polyline)."""
    cx, cy, r, rms, mx = fit_circle(points)
    gate = max(tol, circle_rel * r)
    if rms < gate and mx < 4 * gate:
        return [Primitive("circle", {"c": (cx, cy), "r": r}, rms, mx)]
    breaks = dp_indices(points, tol * 1.5)
    m = len(breaks)
    edges = [(breaks[k], breaks[(k + 1) % m]) for k in range(m)]
    is_line = []
    for a, b in edges:
        ok = False
        if np.linalg.norm(points[b] - points[a]) >= min_line:
            ok = line_tls(span_points(points, a, b))[2] < tol
        is_line.append(ok)
    if not any(is_line):
        return None
    first = is_line.index(True)
    edges, is_line = edges[first:] + edges[:first], is_line[first:] + is_line[:first]
    # A straight edge often ends in a short breakpoint edge that runs into the tangent
    # region of the next arc. Merge consecutive line edges that still fit one line, so
    # that pair is not described as two nearly collinear lines.
    merged, merged_line = [], []
    for (a, b), straight in zip(edges, is_line):
        if straight and merged_line and merged_line[-1]:
            start = merged[-1][0]
            if line_tls(span_points(points, start, b))[2] < tol:
                merged[-1] = (start, b)
                continue
        merged.append((a, b))
        merged_line.append(straight)
    if len(merged) > 2 and merged_line[0] and merged_line[-1]:
        start, end = merged[-1][0], merged[0][1]
        if line_tls(span_points(points, start, end))[2] < tol:
            merged[0] = (start, end)
            merged.pop()
            merged_line.pop()
    edges, is_line = merged, merged_line
    prims = []
    k = 0
    while k < len(edges):
        if is_line[k]:
            a, b = edges[k]
            seg = span_points(points, a, b)
            c, d, lrms = line_tls(seg)
            res = np.abs((seg - c) @ np.array([-d[1], d[0]]))
            prims.append(Primitive("line", {"c": c, "d": d}, lrms, float(res.max()), (a, b)))
            k += 1
            continue
        j = k
        while j < len(edges) and not is_line[j]:
            j += 1
        a, b = edges[k][0], edges[j - 1][1]
        seg = span_points(points, a, b)
        acx, acy, ar, arms, amx = fit_circle(seg)
        prims.append(
            Primitive("arc", {"c": (acx, acy), "r": ar, "mid": tuple(seg[len(seg) // 2])}, arms, amx, (a, b))
        )
        k = j
    # An "arc" between two lines running the same way is a noise bump on one straight
    # edge: merge the three into one line when that still fits, else keep the polyline.
    changed = True
    while changed and len(prims) > 3:
        changed = False
        m = len(prims)
        for k, p in enumerate(prims):
            l1, l2 = prims[k - 1], prims[(k + 1) % m]
            if p.kind != "arc" or l1.kind != "line" or l2.kind != "line":
                continue
            d1, d2 = l1.data["d"], l2.data["d"]
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) >= math.sin(math.radians(5)) or d1 @ d2 <= 0:
                continue
            seg = span_points(points, l1.span[0], l2.span[1])
            c, d, lrms = line_tls(seg)
            if lrms >= tol:
                return None
            res = np.abs((seg - c) @ np.array([-d[1], d[0]]))
            merged = Primitive("line", {"c": c, "d": d}, lrms, float(res.max()), (l1.span[0], l2.span[1]))
            keep = [q for i, q in enumerate(prims) if i not in {(k - 1) % m, k, (k + 1) % m}]
            insert_at = min((k - 1) % m, k)
            prims = keep[:insert_at] + [merged] + keep[insert_at:]
            changed = True
            break
    # Points near a tangent point belong to the neighbouring line as much as to the arc;
    # left in, they pull the arc centre toward the line. Trim them and refit.
    m = len(prims)
    for k, p in enumerate(prims):
        if p.kind != "arc":
            continue
        seg = span_points(points, *p.span)
        keep = np.ones(len(seg), bool)
        for q in (prims[k - 1], prims[(k + 1) % m]):
            if q.kind == "line":
                normal = np.array([-q.data["d"][1], q.data["d"][0]])
                keep &= np.abs((seg - q.data["c"]) @ normal) > tol
        if keep.sum() >= 8:
            acx, acy, ar, arms, amx = fit_circle(seg[keep])
            p.data.update(c=(acx, acy), r=ar)
            p.rms, p.max_abs = arms, amx
    # An arc whose residual is far outside tolerance is not an arc: keep the polyline.
    if any(p.kind == "arc" and p.max_abs > 6 * max(tol, circle_rel * p.data["r"]) for p in prims):
        return None
    # Two adjacent lines must meet at a well-defined corner.
    for p, q in zip(prims, prims[1:] + prims[:1]):
        if p.kind == q.kind == "line":
            d1, d2 = p.data["d"], q.data["d"]
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) < math.sin(math.radians(2)):
                return None
    if len(prims) < 2:
        return None
    return prims


def blur_corrected_radius(r, sigma):
    """True radius of a circular edge whose Gaussian-blurred half-level contour has
    radius r.

    For a disc of radius R blurred by an isotropic Gaussian of sigma, expanding
    P(|X| <= R) = 1/2 in powers of sigma/R gives the half-level radius
    r = R - sigma^2/(2R) - (5/24) sigma^4/R^3 + O(sigma^6/R^5), for either polarity.
    Inverting the series: R = r + sigma^2/(2r) - sigma^4/(24 r^3) + O(sigma^6/r^5).
    """
    return r + sigma * sigma / (2 * r) - sigma**4 / (24 * r**3)


def correct_blur(prims, sigma):
    """Undo the blur-curvature shrink of every fitted radius (see blur_corrected_radius).
    Slot end caps take their radius from the line spacing, which blur does not bias."""
    for p in prims:
        if p.kind in ("arc", "circle") and sigma > 0 and not p.data.get("end_cap"):
            p.data["r"] = blur_corrected_radius(p.data["r"], sigma)
    place_fillets(prims)


def snap_axes(rings, angle_tol_deg=0.6):
    """Make lines within angle_tol of the dominant axis (or its perpendicular) exact.

    Returns (notes, axis): axis is the dominant direction in radians within
    (-pi/4, pi/4], or None when there are no lines. Refit the snapped lines' offsets
    with refit_lines afterwards.
    """
    lines = [p for prims in rings for p in prims if p.kind == "line"]
    if not lines:
        return [], None
    angles = np.array([math.atan2(p.data["d"][1], p.data["d"][0]) for p in lines])
    axis = math.atan2(np.sin(4 * angles).sum(), np.cos(4 * angles).sum()) / 4
    snapped = 0
    for p in lines:
        a = math.atan2(p.data["d"][1], p.data["d"][0])
        target = axis + round((a - axis) / (math.pi / 2)) * math.pi / 2
        if abs(math.degrees(a - target)) < angle_tol_deg:
            p.data["d"] = np.array([math.cos(target), math.sin(target)])
            snapped += 1
    notes = [f"{snapped} straight edge(s) made exactly parallel or perpendicular."] if snapped else []
    return notes, axis


def equalise_radii(rings, radius_rel=0.03, scale=1.0, unit="mm"):
    """Give arcs and circles whose radii agree within radius_rel their mean radius."""
    curved = sorted(
        (p for prims in rings for p in prims if p.kind in ("arc", "circle") and not p.data.get("end_cap")),
        key=lambda p: p.data["r"],
    )
    notes, used = [], set()
    for p in curved:
        if id(p) in used:
            continue
        group = [
            q for q in curved
            if id(q) not in used and abs(q.data["r"] - p.data["r"]) < radius_rel * p.data["r"]
        ]
        for q in group:
            used.add(id(q))
        if len(group) > 1:
            mean = float(np.mean([q.data["r"] for q in group]))
            for q in group:
                q.data["r"] = mean
            notes.append(f"{len(group)} radii made equal at {mean * scale:.3f} {unit}.")
    for prims in rings:
        place_fillets(prims)
    return notes


def refit_lines(points, prims):
    """Least-squares offset for each line whose direction was fixed by snapping."""
    for p in prims:
        if p.kind == "line":
            seg = span_points(points, *p.span)
            d = p.data["d"]
            n = np.array([-d[1], d[0]])
            p.data["c"] = n * float(np.mean(seg @ n)) + d * float(np.mean(seg @ d))


def place_fillets(prims):
    """Recentre every constrained fillet for its current radius (centre = c0 + r v)."""
    for p in prims:
        if "fillet" in p.data:
            c0, v = p.data["fillet"]
            p.data["c"] = tuple(np.asarray(c0) + p.data["r"] * np.asarray(v))


def fit_fillets(points, prims, tol):
    """Constrain each arc between two lines to be tangent to both.

    Between non-parallel lines the arc becomes a fillet: its centre lies on the corner
    bisector at c(r) = c0 + r v, and only r is fitted (Gauss-Newton on geometric
    distance), which is far less sensitive to noise than a free three-parameter circle.
    Between parallel lines it becomes a slot end cap: radius half the line spacing,
    centre on the mid-line.
    """
    m = len(prims)
    for k, p in enumerate(prims):
        if p.kind != "arc":
            continue
        l1, l2 = prims[k - 1], prims[(k + 1) % m]
        if l1.kind != "line" or l2.kind != "line":
            continue
        old_c, old_r = np.array(p.data["c"]), p.data["r"]
        d1, d2 = np.asarray(l1.data["d"]), np.asarray(l2.data["d"])
        n1, n2 = np.array([-d1[1], d1[0]]), np.array([-d2[1], d2[0]])
        c1, c2 = np.asarray(l1.data["c"]), np.asarray(l2.data["c"])
        if abs(d1[0] * d2[1] - d1[1] * d2[0]) < math.sin(math.radians(5)):
            if d1 @ d2 > 0:
                continue  # same-direction neighbours: not an end cap
            o1, o2 = float(c1 @ n1), float(c2 @ n1)
            mid = n1 * (o1 + o2) / 2
            p.data["c"] = tuple(mid + d1 * float((old_c - mid) @ d1))
            p.data["r"] = abs(o1 - o2) / 2
            p.data["end_cap"] = True
            continue
        best = None
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                try:
                    c0 = intersect(c1, d1, c2, d2)
                    v = intersect(c1 + n1 * s1, d1, c2 + n2 * s2, d2) - c0
                except np.linalg.LinAlgError:
                    continue
                distance = np.linalg.norm(c0 + old_r * v - old_c)
                if best is None or distance < best[0]:
                    best = (distance, c0, v)
        if best is None or best[0] > max(2.0, 0.25 * old_r):
            continue
        _, c0, v = best
        seg = span_points(points, *p.span)
        keep = (np.abs((seg - c1) @ n1) > tol) & (np.abs((seg - c2) @ n2) > tol)
        seg = seg[keep] if keep.sum() >= 5 else seg
        r = old_r
        for _ in range(20):
            delta = seg - (c0 + r * v)
            rho = np.maximum(np.linalg.norm(delta, axis=1), 1e-12)
            residual = rho - r
            jac = -(delta @ v) / rho - 1
            step = -float(jac @ residual) / float(jac @ jac)
            r += step
            if abs(step) < 1e-10:
                break
        if not (0.5 * old_r < r < 2 * old_r):
            continue
        p.data["r"] = float(r)
        p.data["fillet"] = (tuple(c0), tuple(v))
        place_fillets([p])
        residual = np.linalg.norm(seg - np.asarray(p.data["c"]), axis=1) - r
        p.rms, p.max_abs = float(np.sqrt(np.mean(residual**2))), float(np.abs(residual).max())


def _foot(line, point):
    c, d = np.asarray(line.data["c"]), np.asarray(line.data["d"])
    return c + d * float((np.asarray(point) - c) @ d)


def segments(prims):
    """Ordered closed-ring segments: ("line", a, b), ("arc", a, mid, b) or ("circle", c, r)."""
    if len(prims) == 1 and prims[0].kind == "circle":
        return [("circle", np.array(prims[0].data["c"], float), float(prims[0].data["r"]))]
    m = len(prims)
    ends = {}
    for k, p in enumerate(prims):
        if p.kind != "line":
            continue
        prev, nxt = prims[k - 1], prims[(k + 1) % m]
        a = (
            intersect(prev.data["c"], prev.data["d"], p.data["c"], p.data["d"])
            if prev.kind == "line"
            else _foot(p, prev.data["c"])
        )
        b = (
            intersect(p.data["c"], p.data["d"], nxt.data["c"], nxt.data["d"])
            if nxt.kind == "line"
            else _foot(p, nxt.data["c"])
        )
        ends[k] = (np.asarray(a, float), np.asarray(b, float))
    out = []
    for k, p in enumerate(prims):
        if p.kind == "line":
            out.append(("line", *ends[k]))
            continue
        a, b = ends[(k - 1) % m][1], ends[(k + 1) % m][0]
        c, r = np.asarray(p.data["c"], float), float(p.data["r"])
        a0 = math.atan2(a[1] - c[1], a[0] - c[0])
        a1 = math.atan2(b[1] - c[1], b[0] - c[0])
        am = math.atan2(p.data["mid"][1] - c[1], p.data["mid"][0] - c[0])
        ccw = (a1 - a0) % (2 * math.pi)
        sweep = ccw if (am - a0) % (2 * math.pi) < ccw else ccw - 2 * math.pi
        mid = c + r * np.array([math.cos(a0 + sweep / 2), math.sin(a0 + sweep / 2)])
        out.append(("arc", a, mid, b))
    return out


def arc_geometry(a, m, b):
    """Centre, radius, start angle and signed sweep of the arc through a, m, b."""
    ax, ay = a
    bx, by = m
    cx, cy = b
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        raise ValueError("arc points are collinear")
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    a0 = math.atan2(ay - uy, ax - ux)
    a1 = math.atan2(cy - uy, cx - ux)
    am = math.atan2(by - uy, bx - ux)
    ccw = (a1 - a0) % (2 * math.pi)
    sweep = ccw if (am - a0) % (2 * math.pi) < ccw else ccw - 2 * math.pi
    return (ux, uy), r, a0, sweep


def sample_segments(segs, sagitta):
    """Closed polygon (without repeated first point) within `sagitta` of every arc."""

    def count(r, sweep):
        if r <= sagitta:
            return 8
        step = 2 * math.acos(max(-1.0, 1 - sagitta / r))
        return max(2, math.ceil(abs(sweep) / max(step, 1e-6)))

    if segs[0][0] == "circle":
        _, c, r = segs[0]
        n = max(24, min(360, count(r, 2 * math.pi)))
        t = np.linspace(0, 2 * math.pi, n, endpoint=False)
        return np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)])
    points = []
    for s in segs:
        if s[0] == "line":
            points.append(np.asarray(s[1], float))
        else:
            (ux, uy), r, a0, sweep = arc_geometry(s[1], s[2], s[3])
            n = min(180, count(r, sweep))
            for t in np.linspace(0, 1, n, endpoint=False):
                points.append(np.array([ux + r * math.cos(a0 + sweep * t), uy + r * math.sin(a0 + sweep * t)]))
    return np.array(points)
