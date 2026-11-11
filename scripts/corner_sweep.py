"""Exact-blur corner sweep: how well the tracer's fitting chain recovers filleted corners.

Each case is a convex pentagon ("house") with every corner filleted at one radius r:
two right-angled base corners, two wall corners and an apex. An apex of 60 degrees
gives corners of 90, 150 and 60 degrees; an apex of 120 gives 90 and 120 degrees. The
pentagon is blurred by an isotropic Gaussian in the continuum, with no pixels, its
half-level outline is traced exactly, and that outline goes through the fitting chain
of backend.reference with design-intent snapping on: fit_ring, snap_axes, refit_lines,
fit_fillets and correct_blur, with the tolerances backend.reference uses at 5 px/mm.

The blur is computed independently of backend.fitting.corner_level. Each vertical line
meets a convex shape in one interval [bot(x), top(x)], so

    u(p) = int phi_s(x - px) [Phi((top(x) - py)/s) - Phi((bot(x) - py)/s)] dx.

top and bot are exact: the max and min over the fillet discs and offset edges, which
all lie in the shape and make up its boundary. The integral is Gauss-Legendre between
the shape's breakpoints, each piece under a cosine substitution that removes the
square-root ends where an arc has a vertical tangent. The half-level point is solved
along each true boundary normal by Illinois regula falsi.

Errors are reported in units of the blur shrink s = sigma^2/2r + 5 sigma^4/24r^3. A
corner is "lost" when it is neither one arc nor reported sharp. A corner reported
sharp is checked against its stated bound (the largest fillet the photo leaves
possible there), which must be at least the true radius; two edges that meet with no
bound stated (a fillet that vanished silently) count as lost.

    .venv/bin/python scripts/corner_sweep.py            # 24 cases, about four minutes
    .venv/bin/python scripts/corner_sweep.py --quick    # 4 cases
    .venv/bin/python scripts/corner_sweep.py --backend ../other-checkout

--backend runs the fitting chain of another checkout, for a before-and-after comparison.
The exit status is 1 if a corner is lost or a sharp corner's bound is below its true
radius.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ERF = np.frompyfunc(math.erf, 1, 1)
GL_X, GL_W = np.polynomial.legendre.leggauss(16)
SUB = 6
PPM = 5.0


def normal_cdf(z):
    return 0.5 * (1.0 + ERF(z / math.sqrt(2.0)).astype(np.float64))


class RoundedPolygon:
    """A convex polygon (counter-clockwise) with every corner filleted at radius r."""

    def __init__(self, vertices, r):
        p = np.asarray(vertices, dtype=np.float64)
        n = len(p)
        d = np.roll(p, -1, axis=0) - p
        d /= np.linalg.norm(d, axis=1)[:, None]
        out = np.column_stack([d[:, 1], -d[:, 0]])
        centres = np.array([
            np.linalg.solve(np.array([out[i - 1], out[i]]), [out[i - 1] @ p[i] - r, out[i] @ p[i] - r])
            for i in range(n)
        ])
        self.r, self.p, self.d, self.out, self.centres = r, p, d, out, centres
        self.seg_a = centres + r * out
        self.seg_b = np.roll(centres, -1, axis=0) + r * out
        self.angles = [math.degrees(math.acos(np.clip(-d[i - 1] @ d[i], -1, 1))) for i in range(n)]
        xs = np.concatenate([self.seg_a[:, 0], self.seg_b[:, 0], centres[:, 0] - r, centres[:, 0] + r])
        self.xmin, self.xmax = float(xs.min()), float(xs.max())
        self.breaks = np.unique(np.clip(xs, self.xmin, self.xmax))

    def top_bot(self, x):
        top, bot = np.full(x.shape, -np.inf), np.full(x.shape, np.inf)
        for cx, cy in self.centres:
            ok = np.abs(x - cx) <= self.r
            h = np.sqrt(np.clip(self.r * self.r - (x - cx) ** 2, 0, None))
            top = np.where(ok, np.maximum(top, cy + h), top)
            bot = np.where(ok, np.minimum(bot, cy - h), bot)
        for a, b in zip(self.seg_a, self.seg_b):
            if abs(b[0] - a[0]) < 1e-12:
                continue
            ok = (x >= min(a[0], b[0])) & (x <= max(a[0], b[0]))
            y = a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0])
            top = np.where(ok, np.maximum(top, y), top)
            bot = np.where(ok, np.minimum(bot, y), bot)
        return top, bot

    def boundary(self, step):
        """True boundary points about `step` apart, outward normals and, for each point,
        its corner index (arc points) or -1 (edge points), counter-clockwise."""
        pts, nrm, owner = [], [], []
        for i in range(len(self.p)):
            a0 = math.atan2(self.out[i - 1][1], self.out[i - 1][0])
            a1 = math.atan2(self.out[i][1], self.out[i][0])
            while a1 < a0:
                a1 += 2 * math.pi
            k = max(2, round((a1 - a0) * self.r / step))
            for t in a0 + (a1 - a0) * (np.arange(k) + 0.5) / k:
                u = np.array([math.cos(t), math.sin(t)])
                pts.append(self.centres[i] + self.r * u), nrm.append(u), owner.append(i)
            a, b = self.seg_a[i], self.seg_b[i]
            k = max(2, round(float(np.linalg.norm(b - a)) / step))
            for s in (np.arange(k) + 0.5) / k:
                pts.append(a + s * (b - a)), nrm.append(self.out[i]), owner.append(-1)
        return np.array(pts), np.array(nrm), np.array(owner)


def blurred(shape, p, sigma):
    """u(p) for an (N, 2) array of points."""
    px, py = p[:, 0], p[:, 1]
    lo = np.clip(px - 9 * sigma, shape.xmin, shape.xmax)
    hi = np.clip(px + 9 * sigma, shape.xmin, shape.xmax)
    cuts = np.sort(np.concatenate([lo[:, None], np.clip(shape.breaks[None], lo[:, None], hi[:, None]), hi[:, None]], 1), 1)
    a, b = cuts[:, :-1], cuts[:, 1:]
    f = np.arange(SUB + 1) / SUB
    sa = a[..., None] + (b - a)[..., None] * f[None, None, :-1]
    sb = a[..., None] + (b - a)[..., None] * f[None, None, 1:]
    s = (GL_X + 1) / 2
    x = sa[..., None] + (sb - sa)[..., None] * (1 - np.cos(np.pi * s)) / 2
    jac = (sb - sa)[..., None] * (np.pi / 2) * np.sin(np.pi * s) * GL_W / 2
    top, bot = shape.top_bot(x)
    inside = np.isfinite(top)
    pyb = py[:, None, None, None]
    cross = np.where(
        inside, normal_cdf((np.where(inside, top, 0) - pyb) / sigma) - normal_cdf((np.where(inside, bot, 0) - pyb) / sigma), 0
    )
    gauss = np.exp(-0.5 * ((x - px[:, None, None, None]) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    return np.sum(gauss * cross * jac, axis=(1, 2, 3))


def half_level(shape, pts, nrm, sigma, chunk=400):
    """Signed offset (outward positive) of the half-level crossing along each normal."""
    out = np.empty(len(pts))
    for c in range(0, len(pts), chunk):
        p, n = pts[c : c + chunk], nrm[c : c + chunk]
        lo, hi = np.full(len(p), -3.0 * sigma), np.full(len(p), 3.0 * sigma)
        flo = blurred(shape, p + lo[:, None] * n, sigma) - 0.5
        fhi = blurred(shape, p + hi[:, None] * n, sigma) - 0.5
        side = np.zeros(len(p))
        t = lo
        for _ in range(60):
            t = (lo * fhi - hi * flo) / (fhi - flo)
            ft = blurred(shape, p + t[:, None] * n, sigma) - 0.5
            inner = ft > 0
            lo, flo, fhi = np.where(inner, t, lo), np.where(inner, ft, flo), np.where(inner & (side == 1), fhi / 2, fhi)
            hi, fhi, flo = np.where(~inner, t, hi), np.where(~inner, ft, fhi), np.where(~inner & (side == -1), flo / 2, flo)
            side = np.where(inner, 1, -1)
            if np.abs(hi - lo).max() < 1e-11 or np.abs(ft).max() < 1e-14:
                break
        out[c : c + chunk] = t
    return out


def house(apex_deg, width=300.0, height=200.0):
    rise = width / 2 * math.tan(math.radians(90 - apex_deg / 2))
    return [(0, 0), (width, 0), (width, height), (width / 2, height + rise), (0, height)]


def shrink(r, sigma):
    return sigma**2 / (2 * r) + 5 * sigma**4 / (24 * r**3)


def fit_snapped(fitting, ring, sigma):
    """The fitting chain of backend.reference with snapping on, in pixels at PPM."""
    tol = max(0.03, 0.15 * sigma / PPM) * PPM
    min_line = min(max(0.025 * float(np.ptp(ring, axis=0).max()) / PPM, 1.0), 3.0) * PPM
    prims = fitting.fit_ring(ring, tol, min_line)
    if prims is None:
        return None
    fitting.snap_axes([prims])
    try:
        fitting.refit_lines(ring, prims, margin=3 * sigma)
    except TypeError:  # a checkout from before refit_lines took a margin
        fitting.refit_lines(ring, prims)
    fitting.fit_fillets(ring, prims, tol, sigma)
    fitting.correct_blur(prims, sigma)
    return prims


def run_case(fitting, apex, r, sigma, step=1.0):
    shape = RoundedPolygon(house(apex), r)
    pts, nrm, _ = shape.boundary(step)
    ring = pts + half_level(shape, pts, nrm, sigma)[:, None] * nrm
    s = shrink(r, sigma)
    prims = fit_snapped(fitting, ring, sigma)
    corners = [{"angle": round(a), "true_r": r} for a in shape.angles]
    if prims is None:
        return {"apex": apex, "r": r, "sigma": sigma, "s": s, "kinds": "polyline", "corners": corners}
    vertices = shape.p
    for p in prims:
        if p.kind == "arc":
            i = int(np.argmin(np.linalg.norm(shape.centres - np.asarray(p.data["c"]), axis=1)))
            corners[i].update(kind="arc", r=float(p.data["r"]), error_s=(float(p.data["r"]) - r) / s, sd=p.data.get("r_sd"))
    m = len(prims)
    for k, p in enumerate(prims):
        q = prims[(k + 1) % m]
        if p.kind == q.kind == "line":
            c1, d1, c2, d2 = (np.asarray(v, dtype=np.float64) for v in (p.data["c"], p.data["d"], q.data["c"], q.data["d"]))
            t = np.linalg.solve(np.column_stack([d1, -d2]), c2 - c1)
            meet = c1 + t[0] * d1
            i = int(np.argmin(np.linalg.norm(vertices - meet, axis=1)))
            # Reported sharp only with a bound on any fillet there; without one the
            # fillet vanished silently, and the corner is lost.
            if "sharp_bound" in q.data:
                corners[i].update(kind="sharp", bound=float(q.data["sharp_bound"]))
    kinds = "".join(p.kind[0].upper() for p in prims)
    return {"apex": apex, "r": r, "sigma": sigma, "s": s, "kinds": kinds, "corners": corners}


def summarise(results):
    lost, low_bound, rows = [], [], {}
    for case in results:
        for c in case["corners"]:
            kind = c.get("kind")
            if kind == "arc":
                band = "r/sigma < 5" if case["r"] / case["sigma"] < 5 else "r/sigma >= 5"
                key = (c["angle"], band)
                rows[key] = max(rows.get(key, 0.0), abs(c["error_s"]))
            elif kind == "sharp":
                if c["bound"] < c["true_r"]:
                    low_bound.append((case["apex"], case["r"], case["sigma"], c["angle"], c.get("bound")))
            else:
                lost.append((case["apex"], case["r"], case["sigma"], c["angle"]))
    return rows, lost, low_bound


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", type=Path, default=Path(__file__).resolve().parents[1], help="checkout whose backend to test")
    parser.add_argument("--quick", action="store_true", help="four cases instead of 24")
    parser.add_argument("--json", type=Path, metavar="FILE", help="also save every case as JSON")
    args = parser.parse_args()
    sys.path.insert(0, str(args.backend.resolve()))
    from backend import fitting

    sigmas, radii = ((1.6,), (8.0, 40.0)) if args.quick else ((1.6, 2.5), (5.0, 8.0, 12.5, 20.0, 40.0, 80.0))
    results, started = [], time.time()
    for sigma in sigmas:
        for apex in (60, 120):
            for r in radii:
                case = run_case(fitting, apex, r, sigma)
                results.append(case)
                described = " ".join(
                    f"{c['angle']}:{c['error_s']:+.2f}" if c.get("kind") == "arc"
                    else f"{c['angle']}:sharp<{c['bound']:.1f}" if c.get("kind") == "sharp"
                    else f"{c['angle']}:lost"
                    for c in case["corners"]
                )
                print(f"sigma {sigma} px, apex {apex:3d}, r {r:5.1f} px (r/sigma {r / sigma:4.1f}): {case['kinds']:12s} {described}  [{time.time() - started:.0f} s]", flush=True)
    rows, lost, low_bound = summarise(results)
    print("\nWorst fillet radius error, in blur shrinks s:")
    print("| Corner | r/sigma < 5 | r/sigma >= 5 |\n| --- | --- | --- |")
    for angle in sorted({a for a, _ in rows}):
        cells = [f"{rows[(angle, band)]:.2f}" if (angle, band) in rows else "-" for band in ("r/sigma < 5", "r/sigma >= 5")]
        print(f"| {angle} deg | {cells[0]} | {cells[1]} |")
    sharp = sum(c.get("kind") == "sharp" for case in results for c in case["corners"])
    print(f"\nCorners lost (neither one arc nor reported sharp): {len(lost)} {lost if lost else ''}")
    print(f"Corners reported sharp: {sharp}; with a bound below the true radius: {len(low_bound)} {low_bound if low_bound else ''}")
    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
    return 1 if lost or low_bound else 0


if __name__ == "__main__":
    sys.exit(main())
