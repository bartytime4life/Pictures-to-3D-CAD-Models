"""Replay finite canonical-arc geometry, search and conditional optical controls.

Reference intersections use Decimal80 raw-direction quadratics and exhaustive
small-cycle products, independently of production foot construction, reduced
costs and dynamic programming. The Gaussian lane uses a separately specified
finite indicator and stdlib erfc quadrature. These are numerical developer
controls, not formal exact constructions or physical-camera qualification.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import sys
import time
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/canonical-arcs-v1.json"
ERFC = np.frompyfunc(math.erfc, 1, 1)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dec(x):
    return Decimal.from_float(float(x))


def vec(x):
    return tuple(map(dec, x))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), Decimal(0))


def primitive(kind, data):
    return SimpleNamespace(kind=kind, data=data)


def reference_junction(a, b):
    if a.kind == b.kind == "line":
        c, d, e, f = vec(a.data["c"]), vec(a.data["d"]), vec(b.data["c"]), vec(b.data["d"])
        det = d[0] * f[1] - d[1] * f[0]
        if not det:
            return []
        v = sub(e, c)
        t = (v[0] * f[1] - v[1] * f[0]) / det
        return [tuple(x + t * y for x, y in zip(c, d))]
    line, arc = (a, b) if a.kind == "line" else (b, a)
    c, d, centre = vec(line.data["c"]), vec(line.data["d"]), vec(arc.data["c"])
    v, r = sub(c, centre), dec(arc.data["r"])
    aa, bb, cc = dot(d, d), 2 * dot(d, v), dot(v, v) - r * r
    discriminant = bb * bb - 4 * aa * cc
    if discriminant < 0:
        return []
    root = discriminant.sqrt()
    ts = [(-bb - root) / (2 * aa)]
    if root:
        ts.append((-bb + root) / (2 * aa))
    return [tuple(x + t * y for x, y in zip(c, d)) for t in ts]


def feasible(p, a, b):
    if a == b:
        return False
    if p.kind == "line":
        observed = sub(vec(p.data["source_ends"][1]), vec(p.data["source_ends"][0]))
        return dot(sub(b, a), observed) > 0
    centre = np.asarray(p.data["c"])
    angle = lambda q: math.atan2(float(q[1]) - centre[1], float(q[0]) - centre[0])
    start, end, mid = angle(a), angle(b), angle(p.data["mid"])
    if p.data["source_sweep"] > 0:
        sweep, along = (end - start) % math.tau, (mid - start) % math.tau
    else:
        sweep, along = (start - end) % math.tau, (start - mid) % math.tau
    return 0 < along < sweep < math.tau


def brute(prims):
    with localcontext() as ctx:
        ctx.prec = 80
        joins = [reference_junction(p, prims[(i + 1) % len(prims)]) for i, p in enumerate(prims)]
        if any(not j for j in joins):
            return []
        paths = []
        for points in itertools.product(*joins):
            if not all(feasible(p, points[i - 1], points[i]) for i, p in enumerate(prims)):
                continue
            score = Decimal(0)
            for i, q in enumerate(points):
                for witness in (
                    prims[i].data["source_ends"][1],
                    prims[(i + 1) % len(prims)].data["source_ends"][0],
                ):
                    delta = sub(q, vec(witness))
                    score += dot(delta, delta)
            paths.append((score, points))
        return sorted(paths, key=lambda p: p[0])


def level(points, radius, chord, sigma, order=24):
    """Exact finite slice formula, numerical composite GL, no production model calls.

    x=-R cos(theta), y bounds=+/-R sin(theta), theta in[0,acos(-h/R)].
    Gaussian x density times the exact erfc-based Gaussian y-interval mass.
    """
    p = np.atleast_2d(points)
    nodes, weights = np.polynomial.legendre.leggauss(order)
    cuts = np.linspace(0, math.acos(-chord / radius), 9)
    theta = (cuts[:-1, None] + cuts[1:, None]) / 2 + (cuts[1:, None] - cuts[:-1, None]) * nodes / 2
    x, height = -radius * np.cos(theta), radius * np.sin(theta)
    jac = radius * np.sin(theta) * (cuts[1:, None] - cuts[:-1, None]) * weights / 2
    px, py = p[:, 0, None, None], p[:, 1, None, None]
    cdf = lambda z: 0.5 * ERFC(-z / math.sqrt(2)).astype(float)
    mass = cdf((height - py) / sigma) - cdf((-height - py) / sigma)
    density = np.exp(-0.5 * ((x - px) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    return np.sum(mass * density * jac, axis=(1, 2))


def observations(radius, chord, sigma):
    anchor = np.array([(-radius + chord) / 2, 0.0])
    angles = np.arange(720) * math.tau / 720
    rays = np.column_stack([np.cos(angles), np.sin(angles)])
    projection = rays @ anchor
    circle = -projection + np.sqrt(projection**2 + radius**2 - anchor @ anchor)
    plane = np.full(720, math.inf)
    np.divide(chord - anchor[0], rays[:, 0], out=plane, where=rays[:, 0] > 0)
    truth = np.minimum(circle, plane)
    lo, hi = np.maximum(0, truth - 5 * sigma), truth + 5 * sigma
    assert level([anchor], radius, chord, sigma)[0] > 0.5
    assert (level(anchor + lo[:, None] * rays, radius, chord, sigma) > 0.5).all()
    assert (level(anchor + hi[:, None] * rays, radius, chord, sigma) < 0.5).all()
    for _ in range(34):
        mid = (lo + hi) / 2
        inside = level(anchor + mid[:, None] * rays, radius, chord, sigma) > 0.5
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    points = anchor + ((lo + hi) / 2)[:, None] * rays
    audit = float(
        np.max(
            np.abs(
                level(points, radius, chord, sigma, 24) - level(points, radius, chord, sigma, 48)
            )
        )
    )
    return points, anchor + truth[:, None] * rays, audit


def circle_of(segment):
    a, m, b = map(np.asarray, segment[1:])
    u, v = m - a, b - a
    cross = u[0] * v[1] - u[1] * v[0]
    rotate = lambda q: np.array([-q[1], q[0]])
    centre = a + ((v @ v) * rotate(u) - (u @ u) * rotate(v)) / (2 * cross)
    radius = math.dist(centre, a)
    start, mid, end = [math.atan2(*(q - centre)[::-1]) for q in (a, m, b)]
    ccw = (end - start) % math.tau
    sweep = ccw if (mid - start) % math.tau < ccw else ccw - math.tau
    return centre, radius, start, sweep


def sampled(segments):
    points = []
    for segment in segments:
        if segment[0] == "line":
            points.append(segment[1])
        elif segment[0] == "arc":
            c, r, angle, sweep = circle_of(segment)
            theta = angle + np.arange(1024) * sweep / 1024
            points.extend(c + r * np.column_stack([np.cos(theta), np.sin(theta)]))
        else:
            c, r = segment[1:]
            theta = np.arange(2048) * math.tau / 2048
            points.extend(c + r * np.column_stack([np.cos(theta), np.sin(theta)]))
    return np.asarray(points)


def _geometry_case(case):
    from backend.circular_joins import JoinConstructionError, assemble

    prims = [primitive(p["kind"], copy.deepcopy(p["data"])) for p in case["primitives"]]
    paths = brute(prims)
    row = {
        "name": case["name"],
        "enumerated_feasible_cycles": len(paths),
        "minimum_score": str(paths[0][0]) if paths else None,
        "runner_up_gap": str(paths[1][0] - paths[0][0]) if len(paths) > 1 else None,
    }
    try:
        segments = assemble(prims)
        row["status"] = "accepted"
        emitted = [np.asarray(s[-1]) for s in segments]
        matches = [
            (score, points)
            for score, points in paths
            if max(math.dist(q, ref) for q, ref in zip(emitted, points)) < 1e-8
        ]
        if not matches:
            raise AssertionError("emitted junctions absent from independent enumeration")
        if abs(matches[0][0] - paths[0][0]) >= Decimal("1e-8"):
            raise AssertionError("selected cycle is not the reference objective minimum")
        row["selected_score"] = str(matches[0][0])
    except JoinConstructionError as exc:
        row["status"] = exc.reason
    row["checks"] = {"expected_outcome": row["status"] == case["expected"]}
    return row


def _dp_case(case):
    from backend.circular_joins import _minimum_cycle

    costs, compatible = case["costs"], case["compatibility"]
    n = len(costs)
    joins = [
        [SimpleNamespace(lower=float(c - 0.125), upper=float(c + 0.125)) for c in row]
        for row in costs
    ]
    paths = [
        p
        for p in itertools.product(range(2), repeat=n)
        if all(compatible[k][p[k - 1]][p[k]] != 0 for k in range(n))
    ]
    row = {
        "name": case["name"],
        "feasible_paths": len(paths),
        "unknown_transitions": sum(x == 2 for a in compatible for b in a for x in b),
        "checks": {},
    }
    for upper in (False, True):
        bound = "upper" if upper else "lower"
        expected = [(sum(getattr(joins[k][p[k]], bound) for k in range(n)), p) for p in paths]
        result = _minimum_cycle(joins, compatible, upper=upper)
        row["checks"][f"minimum_{bound}"] = (
            result is None
            if not expected
            else result is not None
            and abs(result[0] - min(score for score, _ in expected)) < 1e-10
            and any(p == result[1] and abs(score - result[0]) < 1e-10 for score, p in expected)
        )
        if result is not None:
            excluded = result[1]
            other = [(score, p) for score, p in expected if p != excluded]
            alternative = _minimum_cycle(joins, compatible, upper=upper, excluded=excluded)
            row["checks"][f"different_path_{bound}"] = (
                alternative is None
                if not other
                else alternative is not None
                and abs(alternative[0] - min(score for score, _ in other)) < 1e-10
                and alternative[1] != excluded
            )
    row["status"] = "checked"
    return row


def _finite_d_case(case):
    from backend import fitting
    from backend.circular_joins import JoinConstructionError

    radius, h, sigma = (float(case[k]) for k in ("radius", "chord", "sigma"))
    points, truth, audit = observations(radius, h, sigma)
    row = {
        "name": case["name"],
        "radius": radius,
        "chord": h,
        "sigma": sigma,
        "count": len(points),
        "input_sha256": hashlib.sha256(points.tobytes()).hexdigest(),
        "GL24vs48_level_delta": audit,
        "checks": {"quadrature_order_agreement": audit < 1e-10},
    }
    prims = fitting.fit_ring(points, 0.15, 1.0)
    row["initial_kinds"] = None if prims is None else [p.kind for p in prims]

    def curves():
        return (
            None
            if prims is None
            else [
                {"kind": p.kind, "c": list(map(float, p.data["c"])), "r": float(p.data["r"])}
                for p in prims
                if p.kind in ("arc", "circle")
            ]
        )

    row["initial_curves"] = curves()
    segments = None
    if prims:
        fitting.correct_blur(prims, sigma)
        try:
            segments = fitting.segments(prims)
            row["status"] = "analytic"
        except JoinConstructionError as exc:
            row["status"] = exc.reason
    else:
        row["status"] = "initial_polyline"
    final = points if segments is None else sampled(segments)
    polygon, truth_polygon = Polygon(final), Polygon(truth)
    row["final_polygon_valid"] = bool(polygon.is_valid)
    row["sampled_boundary_discrepancy"] = polygon.boundary.hausdorff_distance(
        truth_polygon.boundary
    )
    beta = math.acos(h / radius)
    row["true_area"] = radius**2 * (math.pi - beta) + h * math.sqrt(radius**2 - h**2)
    row["final_sampled_area"] = polygon.area
    row["area_discrepancy"] = polygon.area - row["true_area"]
    row["corrected_curves"] = curves()
    row["checks"]["finite_valid_output"] = bool(
        polygon.is_valid and math.isfinite(row["sampled_boundary_discrepancy"])
    )
    if segments:
        identity = max(
            [0.0]
            + [
                max(math.dist(circle_of(s)[0], p.data["c"]), abs(circle_of(s)[1] - p.data["r"]))
                for p, s in zip(prims, segments)
                if p.kind == "arc"
            ]
        )
        row["maximum_stored_emitted_circle_error"] = identity
        row["checks"]["stored_emitted_circle_agreement"] = identity < 1e-8
    return row


def _load_plan():
    plan = json.loads(PLAN.read_text())
    if plan.get("format") != "pictures-to-cad-canonical-arcs-oracle" or plan.get("version") != 1:
        raise ValueError("unsupported plan")
    if tuple(len(plan[k]) for k in ("geometry", "dp", "finite_gaussian")) != (33, 96, 3):
        raise ValueError("plan must retain all 33 geometry,96 DP and3 Gaussian rows")
    for case in plan["geometry"]:
        if not 2 <= len(case["primitives"]) <= 8:
            raise ValueError("small-cycle oracle work limit")
    for case in plan["dp"]:
        costs, compatible = case["costs"], case["compatibility"]
        if not 2 <= len(costs) <= 6 or any(len(row) != 2 for row in costs):
            raise ValueError("DP work limit")
        if len(compatible) != len(costs) or any(
            len(a) != 2 or any(len(b) != 2 or any(x not in (0, 1, 2) for x in b) for b in a)
            for a in compatible
        ):
            raise ValueError("invalid ternary matrices")
    if [(c["radius"], c["chord"], c["sigma"]) for c in plan["finite_gaussian"]] != [
        ("10", "-6", "1.3"),
        ("10", "0", "1.3"),
        ("10", "6", "1.3"),
    ]:
        raise ValueError("finite Gaussian work/fixture contract changed")
    return plan


def _source_hashes():
    paths = [
        ROOT / "backend" / name for name in ("circular_joins.py", "fitting.py", "sheet.py")
    ] + [Path(__file__).resolve(), PLAN]
    return {str(path.relative_to(ROOT)): sha(path) for path in paths}


def run_plan(plan):
    """Retain every planned row, including injected execution failures."""
    rows = []
    for lane, function in (
        ("geometry", _geometry_case),
        ("dp", _dp_case),
        ("finite_gaussian", _finite_d_case),
    ):
        for case in plan[lane]:
            try:
                row = function(case)
                row["pass"] = all(row["checks"].values())
                # A nonfinite or unserializable diagnostic is a retained row
                # failure, not a late report-writing failure that loses all rows.
                json.dumps(row, allow_nan=False)
            except Exception as exc:  # noqa: BLE001 - retain every planned row after a failure
                row = {
                    "name": case["name"],
                    "status": "execution_failure",
                    "pass": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "checks": {},
                }
            row["lane"] = lane
            rows.append(row)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new JSON destination; existing paths and symlinks refused",
    )
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("--output must be a new destination")
    ancestor = args.output.parent
    while not ancestor.exists() and not ancestor.is_symlink():
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        parser.error("--output parent must be a directory or creatable beneath one")
    plan = _load_plan()
    before = _source_hashes()
    started = time.perf_counter()
    # Production imports happen only after argument/destination checks.
    sys.path.insert(0, str(ROOT))
    rows = run_plan(plan)
    after = _source_hashes()
    failures = sum(not row["pass"] for row in rows)
    report = {
        "format": "pictures-to-cad-canonical-arcs-oracle-result",
        "version": 1,
        "scope": __doc__,
        "assumptions": plan["assumptions"],
        "arithmetic": plan["arithmetic"],
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
        "elapsed_seconds": time.perf_counter() - started,
        "summary": {
            "rows": len(rows),
            "failed_rows": failures,
            "execution_failures": sum(row["status"] == "execution_failure" for row in rows),
            "checks": sum(len(row["checks"]) for row in rows),
            "geometry_statuses": dict(
                Counter(row["status"] for row in rows if row["lane"] == "geometry")
            ),
            "optical_statuses": dict(
                Counter(row["status"] for row in rows if row["lane"] == "finite_gaussian")
            ),
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return int(failures != 0 or before != after)


if __name__ == "__main__":
    raise SystemExit(main())
