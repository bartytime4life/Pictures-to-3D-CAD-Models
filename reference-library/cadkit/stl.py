"""STL reading and mesh checks (pure Python).

``analyze`` welds vertices closer than ``weld_tol`` and reports the checks from
handbook sections 2, 12, and 18: extents, area, enclosed volume, open or
non-manifold edges, non-manifold vertices, orientation consistency, connected
components, and degenerate faces. A clean result (``watertight``, ``manifold``,
``orientation_consistent``, no degenerate faces) means the triangle soup is a
consistently oriented closed 2-manifold; it does not rule out
self-intersections (handbook section 12).
"""

from __future__ import annotations

import math
import re
import struct
from pathlib import Path
from typing import Iterable, Sequence

from . import calc

Vec = tuple[float, float, float]
Triangle = tuple[Vec, Vec, Vec]

_FLOAT = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_VERTEX = re.compile(rf"vertex\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})", re.IGNORECASE)


def _is_binary(data: bytes) -> bool:
    if len(data) < 84:
        return False
    (count,) = struct.unpack_from("<I", data, 80)
    return len(data) == 84 + 50 * count


def read_stl(path: str | Path) -> list[Triangle]:
    """Read ASCII or binary STL; binary is detected by its exact size, not its header."""
    data = Path(path).read_bytes()
    if _is_binary(data):
        (count,) = struct.unpack_from("<I", data, 80)
        tris = []
        for i in range(count):
            vals = struct.unpack_from("<12f", data, 84 + 50 * i)
            tris.append((tuple(vals[3:6]), tuple(vals[6:9]), tuple(vals[9:12])))
        return tris
    text = data.decode("utf-8", errors="replace")
    if not text.lstrip().lower().startswith("solid"):
        raise ValueError(f"{path}: not a recognizable ASCII or binary STL")
    verts = [tuple(float(g) for g in m.groups()) for m in _VERTEX.finditer(text)]
    if len(verts) % 3:
        raise ValueError(f"{path}: vertex count {len(verts)} is not a multiple of 3")
    return [tuple(verts[i:i + 3]) for i in range(0, len(verts), 3)]


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


_NEIGHBOURS = tuple((i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1))


class _Welder:
    """Merge points closer than ``tol`` (Euclidean), independent of grid alignment.

    Points are hashed into cubic cells of side ``tol``. A point within ``tol`` of a
    representative always lies in that representative's cell or one of its 26
    neighbours, so searching those cells finds every candidate; the nearest one wins.
    Representatives keep their first-seen coordinates, so the result is
    deterministic for a given triangle order. Rounding to a grid alone would split
    two points that straddle a cell boundary, however close they are.
    """

    def __init__(self, tol: float):
        self.tol = tol
        self.tol2 = tol * tol
        self.cells: dict[tuple[int, int, int], list[int]] = {}
        self.points: list[Vec] = []

    @property
    def count(self) -> int:
        return len(self.points)

    def weld(self, p: Vec) -> int:
        x, y, z = float(p[0]), float(p[1]), float(p[2])
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            raise ValueError(f"vertex ({x}, {y}, {z}) is not finite; the file holds NaN or infinite coordinates")
        cx, cy, cz = math.floor(x / self.tol), math.floor(y / self.tol), math.floor(z / self.tol)
        best, best_d2 = -1, self.tol2
        cells, points = self.cells, self.points
        for dx, dy, dz in _NEIGHBOURS:
            for vid in cells.get((cx + dx, cy + dy, cz + dz), ()):
                q = points[vid]
                d2 = (q[0] - x) ** 2 + (q[1] - y) ** 2 + (q[2] - z) ** 2
                if d2 <= best_d2:
                    best, best_d2 = vid, d2
        if best >= 0:
            return best
        vid = len(points)
        points.append((x, y, z))
        cells.setdefault((cx, cy, cz), []).append(vid)
        return vid


def _nonmanifold_vertices(faces: Sequence[tuple[int, int, int]],
                          undirected: dict[tuple[int, int], list[int]]) -> int:
    """Count vertices whose incident faces form more than one fan.

    Faces around a vertex belong to one fan when they are joined through edges at
    that vertex with exactly two faces; an edge with three or more faces joins
    nothing, so both of its ends are reported too. Two closed shells that touch
    at a single vertex share no edge, so every edge still has two faces; only
    this vertex-link test exposes the pinch.
    """
    parent: dict[tuple[int, int], tuple[int, int]] = {}

    def find(c: tuple[int, int]) -> tuple[int, int]:
        root = c
        while parent[root] != root:
            root = parent[root]
        while parent[c] != root:
            parent[c], c = root, parent[c]
        return root

    for fi, ids in enumerate(faces):
        if len(set(ids)) == 3:
            for v in ids:
                parent[(v, fi)] = (v, fi)
    for (a, b), fs in undirected.items():
        if len(fs) != 2:
            continue
        for v in (a, b):
            ra, rb = find((v, fs[0])), find((v, fs[1]))
            if ra != rb:
                parent[rb] = ra
    fans: dict[int, set[tuple[int, int]]] = {}
    for corner in parent:
        fans.setdefault(corner[0], set()).add(find(corner))
    return sum(1 for roots in fans.values() if len(roots) > 1)


def analyze(triangles: Sequence[Triangle], weld_tol: float = 1e-6) -> dict:
    """Topology and geometry summary of a triangle soup."""
    if weld_tol <= 0:
        raise ValueError("weld_tol must be positive")
    n_tri = len(triangles)
    if n_tri == 0:
        raise ValueError("mesh has no triangles")
    welder = _Welder(weld_tol)
    faces = [tuple(welder.weld(p) for p in tri) for tri in triangles]

    xs = [p[0] for t in triangles for p in t]
    ys = [p[1] for t in triangles for p in t]
    zs = [p[2] for t in triangles for p in t]
    bmin = (min(xs), min(ys), min(zs))
    bmax = (max(xs), max(ys), max(zs))
    centre = tuple((bmin[i] + bmax[i]) / 2.0 for i in range(3))

    area = 0.0
    volume6 = 0.0
    degenerate = 0
    area_eps = (weld_tol ** 2)
    for tri, ids in zip(triangles, faces):
        a, b, c = (_sub(p, centre) for p in tri)
        cr = _cross(_sub(b, a), _sub(c, a))
        tri_area = 0.5 * math.sqrt(_dot(cr, cr))
        area += tri_area
        volume6 += _dot(a, _cross(b, c))
        if len(set(ids)) < 3 or tri_area <= area_eps:
            degenerate += 1

    directed: dict[tuple[int, int], int] = {}
    undirected: dict[tuple[int, int], list[int]] = {}
    for fi, ids in enumerate(faces):
        if len(set(ids)) < 3:
            continue
        for k in range(3):
            a, b = ids[k], ids[(k + 1) % 3]
            directed[(a, b)] = directed.get((a, b), 0) + 1
            undirected.setdefault((min(a, b), max(a, b)), []).append(fi)

    boundary = sum(1 for f in undirected.values() if len(f) == 1)
    nonmanifold = sum(1 for f in undirected.values() if len(f) > 2)
    orientation_ok = True
    for (a, b), fs in undirected.items():
        if len(fs) == 2 and not (directed.get((a, b), 0) == 1 and directed.get((b, a), 0) == 1):
            orientation_ok = False
            break

    nonmanifold_vertices = _nonmanifold_vertices(faces, undirected)

    parent = list(range(n_tri))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for fs in undirected.values():
        root = find(fs[0])
        for other in fs[1:]:
            r = find(other)
            if r != root:
                parent[r] = root
    valid = [fi for fi, ids in enumerate(faces) if len(set(ids)) == 3]
    components = len({find(fi) for fi in valid})

    watertight = boundary == 0 and nonmanifold == 0 and bool(valid)
    manifold = nonmanifold == 0 and nonmanifold_vertices == 0
    extents = tuple(bmax[i] - bmin[i] for i in range(3))
    euler = len({i for f in faces if len(set(f)) == 3 for i in f}) - len(undirected) + len(valid)
    # Closed orientable 2-manifolds: chi = sum(2 - 2 g_i), so total genus (through-holes) = (2c - chi) / 2.
    closed_surface = watertight and manifold and orientation_ok
    genus = (2 * components - euler) // 2 if closed_surface and (2 * components - euler) % 2 == 0 else None
    return {
        "triangles": n_tri,
        "vertices": welder.count,
        "bbox_min": list(bmin),
        "bbox_max": list(bmax),
        "extents": list(extents),
        "surface_area": area,
        "volume": volume6 / 6.0,
        "watertight": watertight,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "nonmanifold_vertices": nonmanifold_vertices,
        "manifold": manifold,
        "orientation_consistent": orientation_ok,
        "components": components,
        "degenerate_triangles": degenerate,
        "euler_characteristic": euler,
        "genus": genus,
    }


def unit_hints(extents: Iterable[float], expected_mm: float | None = None) -> list[str]:
    """Plain-language hints about likely unit or scale mistakes on import (section 2)."""
    ext = [float(e) for e in extents]
    largest = max(ext) if ext else 0.0
    hints = []
    if largest <= 0:
        return ["Mesh has zero extent."]
    if expected_mm is not None:
        best = calc.suggest_unit_conversion(largest, expected_mm)[0]
        if best["factor"] != 1.0 and best["relative_error"] < 0.05:
            hints.append(
                f"Largest extent {largest:g} matches the expected {expected_mm:g} mm if "
                f"{best['interpretation']} (x{best['factor']:g} -> {best['corrected_mm']:g} mm)."
            )
        elif best["factor"] == 1.0 and best["relative_error"] <= 0.005:
            hints.append(f"Largest extent {largest:g} mm agrees with the expected {expected_mm:g} mm (within 0.5 %).")
        elif best["factor"] == 1.0 and best["relative_error"] < 0.05:
            hints.append(
                f"Units look like mm, but the largest extent {largest:g} mm differs from the expected "
                f"{expected_mm:g} mm by {best['relative_error'] * 100:.1f} %: check the scale and which dimension is meant."
            )
        else:
            hints.append(
                f"Largest extent {largest:g} does not match {expected_mm:g} mm under any common unit "
                "(closest: " + f"{best['interpretation']}, {best['relative_error'] * 100:.1f} % off). "
                "Check which dimension the expectation refers to and whether the mesh was scaled by a bounding box."
            )
    if largest < 1.0:
        hints.append("Largest extent is under 1 unit: the file may be in metres (x1000 to mm).")
    elif largest < 10.0:
        hints.append("Largest extent is under 10 units: check for centimetres (x10) or inches (x25.4).")
    elif largest > 2000.0:
        hints.append("Largest extent exceeds 2000 units: check for micrometres or a double conversion.")
    return hints


def _normal(tri: Triangle) -> Vec:
    cr = _cross(_sub(tri[1], tri[0]), _sub(tri[2], tri[0]))
    length = math.sqrt(_dot(cr, cr)) or 1.0
    return (cr[0] / length, cr[1] / length, cr[2] / length)


def write_stl_ascii(path: str | Path, triangles: Sequence[Triangle], name: str = "cadkit") -> None:
    lines = [f"solid {name}"]
    for tri in triangles:
        n = _normal(tri)
        lines.append(f"  facet normal {n[0]:.9g} {n[1]:.9g} {n[2]:.9g}")
        lines.append("    outer loop")
        for p in tri:
            lines.append(f"      vertex {p[0]:.17g} {p[1]:.17g} {p[2]:.17g}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="ascii")


def write_stl_binary(path: str | Path, triangles: Sequence[Triangle], header: bytes = b"cadkit binary STL") -> None:
    out = bytearray(header[:80].ljust(80, b" "))
    out += struct.pack("<I", len(triangles))
    for tri in triangles:
        out += struct.pack("<12fH", *_normal(tri), *tri[0], *tri[1], *tri[2], 0)
    Path(path).write_bytes(bytes(out))


def box(size: Vec = (1.0, 1.0, 1.0), origin: Vec = (0.0, 0.0, 0.0)) -> list[Triangle]:
    """Outward-oriented axis-aligned box as 12 triangles (useful for tests)."""
    x0, y0, z0 = origin
    x1, y1, z1 = x0 + size[0], y0 + size[1], z0 + size[2]
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    tris = []
    for a, b, c, d in quads:
        tris.append((v[a], v[b], v[c]))
        tris.append((v[a], v[c], v[d]))
    return tris
