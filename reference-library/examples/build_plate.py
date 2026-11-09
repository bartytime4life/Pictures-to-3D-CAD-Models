"""Build and check the synthetic two-hole plate from its parameter register.

This is handbook section 17 in miniature: one parameter file drives the CAD
render, and the checks read the generated mesh rather than trusting the model.

    python3 examples/build_plate.py                    # render, check, write CSV
    python3 examples/build_plate.py --json             # machine-readable summary
    python3 examples/build_plate.py --require-openscad # fail if OpenSCAD is missing

Steps: load ``plate-parameters.csv`` -> render ``two-hole-plate.scad`` with
``openscad -D`` overrides to a binary STL -> analyze the STL with cadkit ->
apply consistency and design-rule checks -> write ``validation-results.csv``
(template columns) next to the STL. Exit status 1 if any check fails.

Passing these checks says the mesh matches the parameters and the stated
design rules. It is not a physical print test.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from cadkit import __version__, calc, params, scad, stl  # noqa: E402

SCAD_VARIABLES = ("plate_length", "plate_width", "plate_thickness", "hole_diameter", "hole_spacing", "chord_error")
REQUIRED = SCAD_VARIABLES + ("min_wall",)
VALIDATION_COLUMNS = (
    "feature_id", "model_revision", "target_mm", "lower_limit_mm", "upper_limit_mm", "measured_mm",
    "instrument", "setup", "uncertainty_or_limitation", "status", "evidence_file",
)
EXTENT_TOL = 1e-6     # mm; float32 represents these plate coordinates exactly
VOLUME_REL_TOL = 1e-5  # float32 vertex rounding at a 30 mm scale is far below this
RADIUS_TOL = 1e-4      # mm


def scad_segments(radius: float, chord_error: float) -> int:
    """Segment count used by two-hole-plate.scad: max(16, ceil(180 / acos(1 - e / r)))."""
    return max(16, calc.min_segments(radius, chord_error))


def check(name, target, lower, upper, measured, note=""):
    ok = (lower is None or measured >= lower) and (upper is None or measured <= upper)
    return {"feature_id": name, "target": target, "lower": lower, "upper": upper,
            "measured": measured, "status": "pass" if ok else "fail", "note": note}


def run(param_path: Path, scad_path: Path, out_dir: Path) -> dict:
    register = params.load_register(param_path)
    problems = params.validate(register, REQUIRED)
    if problems:
        raise ValueError("parameter register problems: " + "; ".join(problems))
    p = {k: register[k].value for k in REQUIRED}
    L, W, T = p["plate_length"], p["plate_width"], p["plate_thickness"]
    d, s, e, min_wall = p["hole_diameter"], p["hole_spacing"], p["chord_error"], p["min_wall"]
    r = d / 2.0
    n = scad_segments(r, e)

    stl_path = out_dir / "two-hole-plate.stl"
    result = scad.render(scad_path, stl_path, params.to_openscad_defines(register, {k: k for k in SCAD_VARIABLES}))
    if not result.ok:
        raise RuntimeError("OpenSCAD render failed:\n" + (result.stderr or result.stdout))
    tris = stl.read_stl(stl_path)
    mesh = stl.analyze(tris)

    # Expected geometry: OpenSCAD places polygon vertices on the circle, so each
    # hole is an inscribed n-gon of area (n / 2) r^2 sin(2 pi / n).
    hole_area = 0.5 * n * r * r * math.sin(2.0 * math.pi / n)
    v_expected = L * W * T - 2.0 * T * hole_area
    v_true_circles = L * W * T - 2.0 * T * math.pi * r * r

    centres = [(-s / 2.0, 0.0), (s / 2.0, 0.0)]
    hole_vertices = set()
    for tri in tris:
        for v in tri:
            if abs(v[0]) < L / 2.0 - 1e-4 and abs(v[1]) < W / 2.0 - 1e-4:
                hole_vertices.add(v)
    radial_dev = max((abs(min(math.hypot(v[0] - cx, v[1] - cy) for cx, cy in centres) - r)
                      for v in hole_vertices), default=math.inf)
    left = [v for v in hole_vertices if v[0] < 0]
    right = [v for v in hole_vertices if v[0] > 0]
    end_wall = min(L / 2.0 - abs(v[0]) for v in hole_vertices)
    side_wall = min(W / 2.0 - abs(v[1]) for v in hole_vertices)
    web = min(v[0] for v in right) - max(v[0] for v in left)

    checks = [
        check("extent_x_mm", L, L - EXTENT_TOL, L + EXTENT_TOL, mesh["extents"][0]),
        check("extent_y_mm", W, W - EXTENT_TOL, W + EXTENT_TOL, mesh["extents"][1]),
        check("extent_z_mm", T, T - EXTENT_TOL, T + EXTENT_TOL, mesh["extents"][2]),
        check("volume_mm3", v_expected, v_expected * (1 - VOLUME_REL_TOL), v_expected * (1 + VOLUME_REL_TOL),
              mesh["volume"], f"inscribed {n}-gon holes; true circles would give {v_true_circles:.4f} mm3"),
        check("components_count", 1, 1, 1, mesh["components"], "count, not mm"),
        check("boundary_edges_count", 0, 0, 0, mesh["boundary_edges"], "count, not mm; 0 means closed"),
        check("nonmanifold_edges_count", 0, 0, 0, mesh["nonmanifold_edges"], "count, not mm"),
        check("nonmanifold_vertices_count", 0, 0, 0, mesh["nonmanifold_vertices"], "count, not mm; 0 means no pinched vertices"),
        check("orientation_inconsistent", 0, 0, 0, 0 if mesh["orientation_consistent"] else 1, "flag, not mm"),
        check("degenerate_triangles_count", 0, 0, 0, mesh["degenerate_triangles"], "count, not mm"),
        check("through_hole_genus_count", 2, 2, 2, -1 if mesh["genus"] is None else mesh["genus"],
              "topology: genus of the closed surface equals the number of through-holes"),
        check("hole_vertex_count", 4 * n, 4 * n, 4 * n, len(hole_vertices), f"2 holes x {n} segments x top and bottom"),
        check("hole_radius_max_deviation_mm", 0.0, None, RADIUS_TOL, radial_dev, f"vertices on r = {r:g} mm about x = +/-{s / 2:g}"),
        check("end_wall_mm", L / 2.0 - s / 2.0 - r, min_wall, None, end_wall, "design rule: >= min_wall"),
        check("side_wall_mm", W / 2.0 - r, min_wall, None, side_wall, "design rule: >= min_wall"),
        check("web_between_holes_mm", s - d, min_wall, None, web, "design rule: >= min_wall"),
    ]

    revision = "scad-sha256:" + hashlib.sha256(scad_path.read_bytes()).hexdigest()[:12]
    setup = f"OpenSCAD {result.version} binary STL; -D overrides from {param_path.name}; {n} segments per hole"
    csv_path = out_dir / "validation-results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(VALIDATION_COLUMNS)
        for c in checks:
            writer.writerow([
                c["feature_id"], revision, _num(c["target"]), _num(c["lower"]), _num(c["upper"]),
                _num(c["measured"]), f"cadkit {__version__} stl.analyze", setup,
                "float32 STL coordinates; geometry check, not a physical measurement"
                + (f"; {c['note']}" if c["note"] else ""),
                c["status"], f"output/{stl_path.name}",
            ])
    return {
        "status": "pass" if all(c["status"] == "pass" for c in checks) else "fail",
        "openscad_version": result.version,
        "model_revision": revision,
        "segments_per_hole": n,
        "stl": str(stl_path),
        "validation_csv": str(csv_path),
        "mesh": mesh,
        "checks": checks,
    }


def _num(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.9g}"
    return str(value)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render and check the synthetic two-hole plate.")
    parser.add_argument("--params", type=Path, default=HERE / "plate-parameters.csv")
    parser.add_argument("--scad", type=Path, default=HERE / "two-hole-plate.scad")
    parser.add_argument("--output-dir", type=Path, default=HERE / "output")
    parser.add_argument("--require-openscad", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not scad.find_openscad():
        print("skip: OpenSCAD not found (install it or set CADKIT_OPENSCAD); no render or mesh checks were run",
              file=sys.stderr)
        return 1 if args.require_openscad else 0
    summary = run(args.params, args.scad, args.output_dir)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        m = summary["mesh"]
        print(f"OpenSCAD {summary['openscad_version']} -> {summary['stl']}")
        print(f"{m['triangles']} triangles, {m['vertices']} vertices, {m['components']} component(s), "
              f"watertight={m['watertight']}, volume={m['volume']:.4f} mm3")
        for c in summary["checks"]:
            print(f"  {c['status']:4}  {c['feature_id']:<30} measured {_num(c['measured']):>12}  target {_num(c['target'])}")
        print(f"{summary['status'].upper()}: wrote {summary['validation_csv']}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
