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


def _arc_chord(points, edges, is_line, k, tol):
    """Whether line edge k is really a chord of the arc that its neighbours trace.

    The neighbours are the arc edges that adjoin it on either side. Where a side has
    none, and the others are too straight to define a circle (a line fits them within
    tol), the line edge on that side stands in. The edge is a chord when its own points
    lie on the circle fitted to the neighbours, to an RMS of half the tolerance. A
    straight stretch can pass only if it lies along that circle and is no longer than
    the chords the breakpoints cut from it. A slot side never does: the arcs at its two
    ends have different centres.
    """
    m = len(edges)
    first = last = k
    while not is_line[(first - 1) % m]:
        first -= 1
    while not is_line[(last + 1) % m]:
        last += 1
    for a, b in ((first, last), (first - (first == k), last + (last == k))):
        around = np.vstack(
            [span_points(points, edges[a % m][0], edges[k][0]), span_points(points, edges[k][1], edges[b % m][1])]
        )
        if line_tls(around)[2] >= tol:
            break
    else:
        return False
    cx, cy, r, _, _ = fit_circle(around)
    own = span_points(points, *edges[k])
    return bool(np.sqrt(np.mean((np.hypot(own[:, 0] - cx, own[:, 1] - cy) - r) ** 2)) < tol / 2)


def _line(points, a, b):
    """The line through the ring's points from a to b, as a primitive."""
    seg = span_points(points, a, b)
    c, d, rms = line_tls(seg)
    res = np.abs((seg - c) @ np.array([-d[1], d[0]]))
    return Primitive("line", {"c": c, "d": d}, rms, float(res.max()), (a, b))


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
    # A chord of an arc can be as long as sqrt(12 r tol) before a breakpoint splits it.
    # Where that reaches min_line (a large radius, a wide blur or a small part) the
    # chord passes for a line, and the arc would be cut into short straight pieces.
    # Give such edges back to their arc, each judged against the arc as grown so far.
    absorbed = []
    changed = True
    while changed:
        changed = False
        for k in range(m):
            if is_line[k] and _arc_chord(points, edges, is_line, k, tol):
                is_line[k] = False
                absorbed.append(k)
                changed = True
    # One chord is not an arc: an edge still between two lines goes back to being one.
    for k in absorbed:
        if is_line[k - 1] and is_line[(k + 1) % m]:
            is_line[k] = True
    if not any(is_line):
        return None
    # What that leaves: an arc cut into as few as two chords that each pass for a line
    # (at a wide corner, or under a wide blur), which the rule above sends back. Runs
    # along one circle that no line fits are marked curved, while each chord is still
    # its own edge. This also rotates the list to start with a line.
    edges, is_line = _curved_runs(points, edges, is_line, tol)
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
            prims.append(_line(points, *edges[k]))
            k += 1
            continue
        j = k
        while j < len(edges) and not is_line[j]:
            j += 1
        a, b = edges[k][0], edges[j - 1][1]
        seg = span_points(points, a, b)
        acx, acy, ar, arms, amx = fit_circle(seg)
        length = float(np.linalg.norm(np.diff(seg, axis=0), axis=1).sum())
        prims.append(
            Primitive(
                "arc", {"c": (acx, acy), "r": ar, "mid": tuple(seg[len(seg) // 2]), "length": length}, arms, amx, (a, b)
            )
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
            merged = _line(points, l1.span[0], l2.span[1])
            if merged.rms >= tol:
                return None
            keep = [q for i, q in enumerate(prims) if i not in {(k - 1) % m, k, (k + 1) % m}]
            insert_at = min((k - 1) % m, k)
            prims = keep[:insert_at] + [merged] + keep[insert_at:]
            changed = True
            break
    # Points near a tangent point belong to the neighbouring line as much as to the arc;
    # left in, they pull the arc centre toward the line. Trim them and refit.
    n, m = len(points), len(prims)
    corners = set()
    for k, p in enumerate(prims):
        if p.kind != "arc":
            continue
        seg = span_points(points, *p.span)
        off = [
            np.abs((seg - q.data["c"]) @ np.array([-q.data["d"][1], q.data["d"][0]]))
            if q.kind == "line"
            else np.full(len(seg), np.inf)
            for q in (prims[k - 1], prims[(k + 1) % m])
        ]
        keep = (off[0] > tol) & (off[1] > tol)
        if keep.sum() >= 8:
            acx, acy, ar, arms, amx = fit_circle(seg[keep])
            p.data.update(c=(acx, acy), r=ar)
            p.rms, p.max_abs = arms, amx
            continue
        # Too few of its points are clear of the lines for that. The arc is a small one,
        # often a sharp corner that only the blur rounds, and it keeps the points near its
        # lines, but not a straight run of them. A breakpoint can fall anywhere on a
        # straight edge (the ring's first point is one). Where it falls just short of a
        # corner it cuts off a stub that is too short to be a line, and the stub comes
        # here with the corner: one arc through both fits neither. So each line runs on
        # to the last point within half the tolerance of it, and the arc is fitted to the
        # points between. Fewer than three define no circle, and the lines then meet at
        # a corner.
        near = [np.flatnonzero(distance < tol / 2) for distance in off]
        lo = int(near[0][-1]) if len(near[0]) else 0
        hi = int(next((i for i in near[1] if i >= lo), len(seg) - 1))
        a = p.span[0]
        if lo > 0:
            prims[k - 1] = _line(points, prims[k - 1].span[0], (a + lo) % n)
        if hi < len(seg) - 1:
            prims[(k + 1) % m] = _line(points, (a + hi) % n, prims[(k + 1) % m].span[1])
        if hi - lo < 2:
            corners.add(k)
        elif hi - lo < len(seg) - 1:
            seg = seg[lo : hi + 1]
            acx, acy, ar, arms, amx = fit_circle(seg)
            length = float(np.linalg.norm(np.diff(seg, axis=0), axis=1).sum())
            p.data.update(c=(acx, acy), r=ar, mid=tuple(seg[len(seg) // 2]), length=length)
            p.rms, p.max_abs, p.span = arms, amx, ((a + lo) % n, (a + hi) % n)
    prims = [p for k, p in enumerate(prims) if k not in corners]
    # Each line's span runs into its neighbouring arcs; refit it on its straight part,
    # so its direction (which axis snapping relies on) and offset are the edge's own.
    refit_lines(points, prims)
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


def _fits_arc(points, a, b, tol):
    """One circle fits the span to half the line tolerance (RMS) and 1.5 tolerances
    (worst point)."""
    seg = span_points(points, a, b)
    *_, rms, max_abs = fit_circle(seg)
    return rms < 0.5 * tol and max_abs < 1.5 * tol


def _bowed_chords(points, edges, is_line, k, j):
    """Whether every line edge of run k..j is itself curved along the run's circle: its
    own points lie closer to that circle (RMS) than to their own best line. A chord of
    an arc bows by L^2/8r and passes; a straight facet or flat does not, however well
    the run as a whole fits a circle."""
    cx, cy, r, _, _ = fit_circle(span_points(points, edges[k][0], edges[j][1]))
    for e in range(k, j + 1):
        if is_line[e]:
            own = span_points(points, *edges[e])
            on_circle = float(np.sqrt(np.mean((np.hypot(own[:, 0] - cx, own[:, 1] - cy) - r) ** 2)))
            if on_circle >= line_tls(own)[2]:
                return False
    return True


def _curved_runs(points, edges, is_line, tol):
    """Return (edges, is_line) with runs of chords along one large arc marked curved.

    Douglas-Peucker cuts an arc into chords whose sagitta is at most 1.5 tolerances, so
    an arc of radius above about min_line^2 / (12 tol) yields chords that are long enough,
    and straight enough, to pass as lines; the arc is then described as a run of short
    lines. Each longest run of two or more consecutive edges that one circle fits
    (_fits_arc) is marked curved when it contains such a line, one line does not fit
    the whole run within tolerance, and each of its line edges bows along the circle
    (_bowed_chords). Pieces of one straight edge fit a line, and straight facets or
    flats do not bow, so neither is taken for an arc. The longest straight edge is never
    absorbed: the list is rotated to start with it, so no run wraps around the ring.
    """
    m = len(edges)
    lengths = [float(np.linalg.norm(points[b] - points[a])) if s else -1.0 for (a, b), s in zip(edges, is_line)]
    first = int(np.argmax(lengths))
    edges, is_line = edges[first:] + edges[:first], list(is_line[first:] + is_line[:first])
    if m < 4:
        return edges, is_line
    curved = [not s for s in is_line]
    k = 1
    while k + 1 < m:
        j = k + 1
        if not _fits_arc(points, edges[k][0], edges[j][1], tol):
            k += 1
            continue
        while j + 1 < m and _fits_arc(points, edges[k][0], edges[j + 1][1], tol):
            j += 1
        if (
            any(is_line[k : j + 1])
            and line_tls(span_points(points, edges[k][0], edges[j][1]))[2] >= tol
            and _bowed_chords(points, edges, is_line, k, j)
        ):
            curved[k : j + 1] = [True] * (j + 1 - k)
            k = j + 1
        else:
            k += 1
    return edges, [not c for c in curved]


def blur_corrected_radius(r, sigma):
    """True radius of a circular edge whose Gaussian-blurred half-level contour has
    radius r.

    For a disc of radius R blurred by an isotropic Gaussian of sigma, expanding
    P(|X| <= R) = 1/2 in powers of sigma/R gives the half-level radius
    r = R - sigma^2/(2R) - (5/24) sigma^4/R^3 + O(sigma^6/R^5), for either polarity.
    Inverting the series: R = r + sigma^2/(2r) - sigma^4/(24 r^3) + O(sigma^6/r^5).
    """
    return r + sigma * sigma / (2 * r) - sigma**4 / (24 * r**3)


def blur_shrink(radius, sigma):
    """How far inside a circular edge of the given true radius its Gaussian-blurred
    half-level contour lies (the series in blur_corrected_radius), and the derivative
    of that distance with respect to the radius."""
    return (
        sigma**2 / (2 * radius) + 5 * sigma**4 / (24 * radius**3),
        -(sigma**2) / (2 * radius**2) - 5 * sigma**4 / (8 * radius**4),
    )


def erfc(x):
    """Complementary error function, vectorised; fractional error below 1.2e-7 everywhere
    (the Chebyshev fit of Numerical Recipes' erfcc)."""
    x = np.asarray(x, dtype=np.float64)
    z = np.abs(x)
    t = 1.0 / (1.0 + 0.5 * z)
    poly = -z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (
        -0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277))))
    ))))
    with np.errstate(invalid="ignore"):
        tail = np.where(z == np.inf, 0.0, t * np.exp(poly))
    return np.where(x >= 0, tail, 2.0 - tail)


_GL6 = np.polynomial.legendre.leggauss(6)
SIGMA_REL_SD = 0.05  # relative uncertainty of a measured edge blur (edges.edge_sigma)
# Systematic error of a straight edge's traced position, in pixels: on rendered photos
# the sub-pixel tracer places axis-aligned and diagonal edges about 0.03 px apart.
EDGE_SYS_SD = 0.03


def corner_level(points, centre, radius, start, sweep, sigma, pieces=None):
    """The blurred indicator of a rounded corner, at each point: the probability that a
    Gaussian of `sigma` about the point falls inside the corner.

    The corner is convex: an arc of `radius` about `centre`, from angle `start` counter-
    clockwise through `sweep` (< pi), and the two lines tangent to it at its ends, running
    away from the arc without end. Its half-level contour is the traced edge of the part
    whichever side the material is on, since the two blurred indicators sum to one.

    Seen from the centre the corner is star-shaped: a ray at angle a leaves it at
    R(a) = radius across the arc, at radius / cos(a - end) beyond each tangent point (for
    a quarter turn), and never in the opening between the lines. With q = centre - p,
    b = q.e(a) and h^2 = |q|^2 - b^2, the radial integral of the Gaussian has the closed
    form

        [exp(-|q|^2/2s^2) - exp(-((R+b)^2 + h^2)/2s^2)] / 2pi
            - b/(s sqrt(2pi)) exp(-h^2/2s^2) [Q(b/s) - Q((R+b)/s)],

    Q the upper normal tail, leaving one smooth integral over the angle. That runs over
    the directions within 9 sigma of the point (all directions when it is that close to
    the centre), by composite 6-point Gauss-Legendre broken at the arc's ends: 40
    pieces, or 160 when some point is that close, since rays from the centre then graze
    the edges and their exit point moves fast with the angle.
    """
    p = np.atleast_2d(np.asarray(points, dtype=np.float64))
    q = np.asarray(centre, dtype=np.float64)[None] - p
    dist2 = (q * q).sum(axis=1)
    dist = np.sqrt(dist2)
    toward = np.arctan2(-q[:, 1], -q[:, 0])
    half = np.where(dist > 9 * sigma, np.arcsin(np.minimum(1.0, 9 * sigma / np.maximum(dist, 1e-300))), math.pi)
    if pieces is None:
        pieces = 40 if (dist > 9 * sigma).all() else 160
    lo, hi = toward - half, toward + half
    end = start + sweep
    base = np.array([start - math.pi / 2, start, end, end + math.pi / 2])
    nearest = base[None] + 2 * math.pi * np.round((toward[:, None] - base[None]) / (2 * math.pi))
    cuts = np.clip(nearest, lo[:, None], hi[:, None])
    grid = lo[:, None] + (hi - lo)[:, None] * np.linspace(0.0, 1.0, pieces + 1)[None]
    bounds = np.sort(np.concatenate([grid, cuts], axis=1), axis=1)
    a, b = bounds[:, :-1, None], bounds[:, 1:, None]
    nodes, weights = _GL6
    angle = (a + b) / 2 + (b - a) / 2 * nodes
    weight = (b - a) / 2 * weights
    turn = np.mod(angle - (start - math.pi / 2), 2 * math.pi)
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        c1, c2 = np.cos(angle - start), np.cos(angle - end)
        reach = np.full(angle.shape, np.inf)
        reach = np.where((turn < math.pi / 2) & (c1 > 0), radius / c1, reach)
        reach = np.where((turn >= math.pi / 2) & (turn < math.pi / 2 + sweep), radius, reach)
        reach = np.where((turn >= math.pi / 2 + sweep) & (turn < math.pi + sweep) & (c2 > 0), radius / c2, reach)
        along = q[:, 0, None, None] * np.cos(angle) + q[:, 1, None, None] * np.sin(angle)
        off2 = np.maximum(dist2[:, None, None] - along * along, 0.0)
        far = reach + along
        two_s2 = 2 * sigma * sigma
        outer = np.where(np.isinf(far), 0.0, np.exp(-(far * far + off2) / two_s2))
        first = (np.exp(-dist2 / two_s2)[:, None, None] - outer) / (2 * math.pi)
        tails = 0.5 * erfc(along / (sigma * math.sqrt(2))) - 0.5 * erfc(far / (sigma * math.sqrt(2)))
        second = -along / (sigma * math.sqrt(2 * math.pi)) * np.exp(-off2 / two_s2) * tails
    return ((first + second) * weight).sum(axis=(1, 2))


def _exact_fillet(seg, lines, v, inward, r, sigma, noise, correlation=None):
    """Fit a fillet's radius to its traced points with the exact blurred corner
    (corner_level) as the model; returns (radius, sd, rms, max_abs, sharp_bound) or
    None. sharp_bound is None for a fillet the photo shows; for one it cannot tell from
    a sharp corner it is the smallest radius it would show.

    `lines` holds the two edges as (point, direction), `inward` their unit normals
    pointing toward the fillet's centre c(r) = c0 + r v, c0 their intersection. Each
    point's residual is (level - 1/2) / |gradient|, its signed distance from the model's
    half-level contour to first order, and r is found by Gauss-Newton. The radius's
    standard deviation combines, each carried through the fit's own derivative:
    the residual noise, inflated by its correlation along the edge (`correlation`,
    measured on the neighbouring straight edges by correlation_factor; one sigma of
    points if not given); the edge blur's uncertainty, SIGMA_REL_SD; and a systematic
    error EDGE_SYS_SD in each edge's position, which a wide corner magnifies most.

    A fillet is visible when its traced outline differs somewhere from that of the
    sharp corner (r = 0) by twice the edge uncertainty, max(noise, EDGE_SYS_SD). One
    that is not is reported as sharp, with the radius at which a fillet would become
    visible found by bisection. (The standard deviation is no guide there: a fillet
    much smaller than the blur changes the outline only as r squared.)
    """
    (c1, d1), (c2, d2) = lines

    def corner(shift1=0.0, shift2=0.0):
        return intersect(np.asarray(c1) + shift1 * inward[0], d1, np.asarray(c2) + shift2 * inward[1], d2)

    c0 = corner()
    starts = [math.atan2(-m[1], -m[0]) for m in inward]
    a1, a2 = starts
    sweep = (a2 - a1) % (2 * math.pi)
    if sweep > math.pi:
        a1, sweep = a2, 2 * math.pi - sweep
    if not 0.02 < sweep < math.pi - 0.02:
        return None

    def level(radius, s=sigma, at=seg, apex=c0):
        return corner_level(at, apex + radius * v, radius, a1, sweep, s)

    h = 0.1 * sigma
    gx = level(r, at=seg + [h, 0]) - level(r, at=seg - [h, 0])
    gy = level(r, at=seg + [0, h]) - level(r, at=seg - [0, h])
    gradient = np.hypot(gx, gy) / (2 * h)
    if not (gradient > 0).all():
        return None

    def residual(radius, s=sigma, apex=c0):
        return (level(radius, s, apex=apex) - 0.5) / gradient

    start_r = r
    for _ in range(25):
        f = residual(r)
        step_r = max(1e-3 * sigma, 1e-4 * r)
        jac = (residual(r + step_r) - f) / step_r
        step = min(-float(jac @ f) / float(jac @ jac), 0.5 * max(r, sigma))
        # r = 0 is the sharp corner, which the same model describes.
        new_r = max(0.0, r + step)
        if new_r > 5 * max(start_r, sigma):
            return None
        done = abs(new_r - r) < 1e-6 * max(r, sigma)
        r = new_r
        if done:
            break
    f = residual(r)
    step_r = max(1e-3 * sigma, 1e-4 * r)
    jac = (residual(r + step_r) - f) / step_r
    jac_sigma = (residual(r, sigma * 1.01) - f) / (0.01 * sigma)
    spacing = float(np.median(np.linalg.norm(np.diff(seg, axis=0), axis=1)))
    rms = float(np.sqrt(np.mean(f * f)))
    nu = max(rms, noise)
    if correlation is None:
        correlation = sigma / max(spacing, 1e-9)
    var_noise = nu * nu * max(1.0, correlation) / float(jac @ jac)
    dr_dsigma = -float(jac @ jac_sigma) / float(jac @ jac)
    var_edges = 0.0
    for shifts in ((0.01, 0.0), (0.0, 0.01)):
        jac_edge = (residual(r, apex=corner(*shifts)) - f) / 0.01
        var_edges += (float(jac @ jac_edge) / float(jac @ jac) * EDGE_SYS_SD) ** 2
    sd = math.sqrt(var_noise + (dr_dsigma * SIGMA_REL_SD * sigma) ** 2 + var_edges)
    sharp = residual(0.0)
    floor = 2 * max(nu, EDGE_SYS_SD)
    bound = None
    if np.abs(f - sharp).max() < floor:
        lo, hi = r, max(4 * sigma, 2 * start_r)
        for _ in range(3):
            if np.abs(residual(hi) - sharp).max() >= floor:
                break
            lo, hi = hi, 2 * hi
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if np.abs(residual(mid) - sharp).max() < floor else (lo, mid)
        bound = hi
    return float(r), sd, rms, float(np.abs(f).max()), bound


def correct_blur(prims, sigma):
    """Undo the blur-curvature shrink of every fitted radius (see blur_corrected_radius).
    Slot end caps take their radius from the line spacing, which blur does not bias, and
    a fillet fitted with the blur in its model (fit_fillets) already has its true radius."""
    for p in prims:
        if p.kind in ("arc", "circle") and sigma > 0 and not (p.data.get("end_cap") or p.data.get("blur_modelled")):
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
            p.data["snapped"] = True
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


UNDETERMINED_REL = 0.1  # a radius with a standard deviation above this fraction is reported


def undetermined_radii(rings, sigma, scale=1.0, unit="mm", limit=300):
    """Notes naming the fitted radii that this photo does not pin down, and the corners
    found sharp. Each note is at most `limit` characters (backend.models' note limit).

    A fillet fitted with the exact corner model carries a standard deviation (r_sd);
    it is reported above UNDETERMINED_REL of the radius. That happens at wide corners,
    where the outline moves only (1/sin(theta/2) - 1) times a change of radius (0.035
    at 150 degrees), so the edge barely constrains the radius; the note gives how far
    the outline itself is uncertain. r_sd is a linearised estimate; once it is a large
    part of the radius the fit is no longer linear and the spread is larger still, so
    the note says "or more". A free arc between two lines (no snapping) is reported
    when it is shorter than 5 sigma: blur then bends all of it, and the free circle's
    radius is not the part's. Corners that fit_fillets found sharp are counted, with the
    largest fillet radius the photo leaves possible there.
    """
    fillets, free, sharp = [], [], []
    for prims in rings:
        m = len(prims)
        for k, p in enumerate(prims):
            if p.kind == "line" and "sharp_bound" in p.data:
                sharp.append(p.data["sharp_bound"])
            if p.kind != "arc" or p.data.get("end_cap"):
                continue
            r, sd = p.data["r"], p.data.get("r_sd")
            if sd is not None:
                angle = p.data.get("corner_deg", 90.0)
                if not math.isfinite(sd):
                    fillets.append(f"R{r * scale:.2f} {unit} (a {angle:.0f}° corner the fit could not settle)")
                elif sd > UNDETERMINED_REL * r:
                    outline = sd * (1 / math.sin(math.radians(angle) / 2) - 1)
                    fillets.append(
                        f"R{r * scale:.2f} ± {sd * scale:.2f} {unit} or more ({angle:.0f}° corner; "
                        f"outline ± {outline * scale:.3f} {unit})"
                    )
            elif (
                sigma > 0
                and "fillet" not in p.data
                and prims[k - 1].kind == prims[(k + 1) % m].kind == "line"
                and p.data.get("length", math.inf) < 5 * sigma
            ):
                free.append(f"R{r * scale:.2f} {unit}")

    def listed(head, items, tail):
        for shown in range(len(items), 0, -1):
            more = f" and {len(items) - shown} more" if shown < len(items) else ""
            text = head + "; ".join(items[:shown]) + more + tail
            if len(text) <= limit:
                return text
        return (head + f"{len(items)} of them" + tail)[:limit]

    notes = []
    if fillets:
        notes.append(listed(f"This photo does not determine {len(fillets)} fillet radius(es) well: ", fillets, ". Measure them if they matter."))
    if free:
        notes.append(listed(f"{len(free)} arc(s) are too short to measure under this photo's blur: ", free, ". Turn on snapping, or measure them."))
    if sharp:
        notes.append(
            f"{len(sharp)} corner(s) traced as sharp: any fillet there is under R{max(sharp) * scale:.2f} {unit}."[:limit]
        )
    return notes


def correlation_factor(residual, max_lag=25):
    """How many times the variance of a mean exceeds that of independent samples, for
    residuals in order along an edge: 1 + 2 (rho_1 + rho_2 + ...), the autocorrelations
    summed until the first that is not positive (Geyer's initial positive sequence)."""
    r = np.asarray(residual, dtype=np.float64)
    r = r - r.mean()
    total_var = float(r @ r)
    if len(r) < 8 or total_var <= 0:
        return 1.0
    total = 0.0
    for lag in range(1, min(max_lag, len(r) // 4) + 1):
        rho = float(r[:-lag] @ r[lag:]) / total_var
        if rho <= 0:
            break
        total += rho
    return 1.0 + 2.0 * total


def refit_lines(points, prims, margin=0.0):
    """Refit each line on the straight part of its span: least-squares offset for a
    line whose direction was fixed by snapping, total least squares otherwise.

    Douglas-Peucker hands a line the first stretch of a neighbouring arc, up to where
    that arc leaves it by 1.5 tolerances; for a large radius that stretch is long and
    tilts or shifts the line. Points past the foot of a neighbouring arc's centre (its
    tangent point), less `margin` (where blur still bends the edge), are left out.
    """
    m = len(prims)
    for k, p in enumerate(prims):
        if p.kind != "line":
            continue
        seg = span_points(points, *p.span)
        d = np.asarray(p.data["d"], dtype=np.float64)
        along = (seg - np.asarray(p.data["c"])) @ d
        forward = 1.0 if along[-1] >= along[0] else -1.0
        keep = np.ones(len(seg), bool)
        for q, sense in ((prims[k - 1], 1.0), (prims[(k + 1) % m], -1.0)):
            if q.kind == "arc":
                tangent = float((np.asarray(q.data["c"]) - np.asarray(p.data["c"])) @ d)
                keep &= sense * forward * (along - tangent) >= margin
        if keep.sum() < max(5, len(seg) // 5):
            keep[:] = True
        seg = seg[keep]
        if p.data.get("snapped"):
            n = np.array([-d[1], d[0]])
            p.data["c"] = n * float(np.mean(seg @ n)) + d * float(np.mean(seg @ d))
        else:
            c, direction, _ = line_tls(seg)
            p.data["c"], p.data["d"] = c, direction * (1.0 if direction @ d >= 0 else -1.0)
        d = np.asarray(p.data["d"])
        residual = (seg - np.asarray(p.data["c"])) @ np.array([-d[1], d[0]])
        p.rms, p.max_abs = float(np.sqrt(np.mean(residual**2))), float(np.abs(residual).max())
        p.data["noise_corr"] = correlation_factor(residual)


def place_fillets(prims):
    """Recentre every constrained fillet for its current radius (centre = c0 + r v)."""
    for p in prims:
        if "fillet" in p.data:
            c0, v = p.data["fillet"]
            p.data["c"] = tuple(np.asarray(c0) + p.data["r"] * np.asarray(v))


def fit_fillets(points, prims, tol, sigma=0.0):
    """Constrain each arc between two lines to be tangent to both.

    Between non-parallel lines the arc becomes a fillet: its centre lies on the corner
    bisector at c(r) = c0 + r v, and only r is fitted (Gauss-Newton on geometric
    distance), which is far less sensitive to noise than a free three-parameter circle.
    Between parallel lines it becomes a slot end cap: radius half the line spacing,
    centre on the mid-line.

    `sigma` is the edge blur. Blur draws the traced arc toward its centre by
    s = sigma^2 / (2r) while the centre stays where it is and the two edges stay where
    they are. A fillet's centre is tied to its radius, so a fit that ignores the blur
    cannot shrink the radius to follow the points: it has to move the centre as well,
    and settles on a radius about 3 s too large (for a right-angle corner), where a free
    circle would read s too small. The points are therefore fitted with a circle of
    radius r - s(r) about c(r), which gives the true radius directly; correct_blur then
    leaves the fillet alone. Within about 2.5 sigma of where the arc meets an edge the
    traced curve is neither arc nor line, and those points are left out.

    That disc model holds only in the middle of a long arc. The radius is then refined
    against the exact blurred corner (corner_level) on the whole corner, including the
    edges out to 5 sigma beyond the tangent points (_exact_fillet), which also gives its
    standard deviation (r_sd; infinite when the exact fit finds no radius). Blur rounds
    a sharp corner too, and the exact model at r = 0 describes it: a fillet whose outline
    the photo cannot tell from a sharp corner's is removed, so its two edges meet, and
    the following edge records the largest fillet radius the photo leaves possible there
    (sharp_bound).
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
        # An arc point 2.5 sigma along the arc from an edge lies (2.5 sigma)^2 / (2r)
        # off that edge.
        clear = max(tol, 3.125 * sigma**2 / old_r)
        keep = (np.abs((seg - c1) @ n1) > clear) & (np.abs((seg - c2) @ n2) > clear)
        if keep.sum() < 5:
            keep = (np.abs((seg - c1) @ n1) > tol) & (np.abs((seg - c2) @ n2) > tol)
        seg = seg[keep] if keep.sum() >= 5 else seg
        r = old_r
        for _ in range(20):
            delta = seg - (c0 + r * v)
            rho = np.maximum(np.linalg.norm(delta, axis=1), 1e-12)
            shrink, slope = blur_shrink(r, sigma) if sigma > 0 else (0.0, 0.0)
            residual = rho - (r - shrink)
            jac = -(delta @ v) / rho - 1 + slope
            step = -float(jac @ residual) / float(jac @ jac)
            r += step
            if abs(step) < 1e-10:
                break
        approximate = 0.5 * old_r < r < 2 * old_r
        if not approximate:
            if sigma <= 0:
                continue
            r = old_r  # a start for the exact fit only
        shrink = blur_shrink(r, sigma)[0] if sigma > 0 else 0.0
        residual = np.linalg.norm(seg - (c0 + r * v), axis=1) - (r - shrink)
        rms, max_abs = float(np.sqrt(np.mean(residual**2))), float(np.abs(residual).max())
        centre = c0 + r * v
        inward = [n * math.copysign(1.0, float((centre - c) @ n)) for n, c in ((n1, c1), (n2, c2))]
        exact = None
        if sigma > 0:
            # The whole corner, with the edges up to 5 sigma beyond the tangent points.
            around = span_points(points, l1.span[0], l2.span[1])
            near = around[np.linalg.norm(around - centre, axis=1) <= math.sqrt(r * r + 25 * sigma * sigma)]
            if len(near) >= 5:
                corr = [q.data["noise_corr"] for q in (l1, l2) if "noise_corr" in q.data]
                exact = _exact_fillet(
                    near, ((c1, d1), (c2, d2)), v, inward, r, sigma, (l1.rms + l2.rms) / 2, max(corr) if corr else None
                )
            if exact is not None:
                r, sd, rms, max_abs, bound = exact
                p.data["r_sd"] = sd
            elif approximate:
                p.data["r_sd"] = math.inf  # the exact fit found no radius: not determined
        if exact is None and not approximate:
            continue
        p.data["r"] = float(r)
        p.data["fillet"] = (tuple(c0), tuple(v))
        # The inward normals of the two edges are pi minus the corner angle apart.
        p.data["corner_deg"] = 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, float(inward[0] @ inward[1])))))
        p.data["blur_modelled"] = sigma > 0
        place_fillets([p])
        p.rms, p.max_abs = rms, max_abs
        if exact is not None and bound is not None:
            # Not to be told from a sharp corner. The next edge keeps the bound on any
            # fillet there for the trace's notes.
            p.data["sharp"] = True
            l2.data["sharp_bound"] = max(l2.data.get("sharp_bound", 0.0), bound)
    prims[:] = [p for p in prims if not p.data.get("sharp")]


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
