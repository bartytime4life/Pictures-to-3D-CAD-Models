"""Command line for cadkit: ``python3 -m cadkit <command> [options]``.

Every numeric command accepts ``--json``. Exit codes: 0 success, 1 a check
failed (for example a mesh that is not watertight), 2 invalid input.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from . import __version__, calc, homography, params, project, routes, stl


def _fmt(value, digits: int = 6) -> str:
    if isinstance(value, float):
        if value == 0 or 1e-4 <= abs(value) < 1e7:
            return f"{value:.{digits}g}"
        return f"{value:.{digits}e}"
    return str(value)


def _emit(args, result, lines: list[str]) -> None:
    if args.json:
        print(json.dumps(result, indent=2))
        return
    for line in lines:
        print(line)
    warnings = result.get("warnings", []) if isinstance(result, dict) else []
    for w in warnings:
        print(f"warning: {w}")


def cmd_scale(args):
    r = calc.scale_report(args.known_mm, args.reference_px, args.feature_px)
    lines = [f"scale: {_fmt(r['scale_mm_per_px'])} mm/px"]
    if "feature_length_mm" in r:
        lines.append(f"feature length: {_fmt(r['feature_length_mm'])} mm (planar assumption)")
    _emit(args, r, lines)


def cmd_uncertainty(args):
    r = calc.ratio_uncertainty(args.p, args.up, args.pref, args.upref, args.lref, args.ulref)
    _emit(args, r, [
        f"length L: {_fmt(r['length'])} mm",
        f"standard uncertainty u(L): {_fmt(r['u'])} mm ({_fmt(r['relative'] * 100, 4)} %)",
        f"2u: {_fmt(r['expanded_k2'])} mm (approximate 95 % only if near-normal)",
        "model: first-order, independent inputs; omits perspective, distortion, bias, correlation",
    ])


def cmd_chord(args):
    r = calc.chord_report(args.radius, error=args.error, segments=args.segments)
    lines = [
        f"segments: {r['segments']}",
        f"chord error: {_fmt(r['chord_error_mm'])} mm at radius {_fmt(r['radius_mm'])} mm",
        f"flat-to-flat diameter: {_fmt(r['flat_to_flat_diameter_mm'])} mm",
    ]
    if r.get("previous_count_error_mm") is not None:
        lines.append(f"error with {r['segments'] - 1} segments: {_fmt(r['previous_count_error_mm'])} mm")
    _emit(args, r, lines)


def cmd_depth(args):
    r = calc.depth_report(args.z, args.delta, args.size)
    lines = [f"depth factor (Z + delta) / Z: {_fmt(r['depth_factor'])}"]
    if "corrected_size_mm" in r:
        lines.append(f"corrected size: {_fmt(r['corrected_size_mm'])} mm")
    if args.z_range and args.delta_range:
        low, high = calc.depth_factor_range(args.z_range[0], args.z_range[1], args.delta_range[0], args.delta_range[1])
        r["factor_range"] = [low, high]
        lines.append(f"factor range: {_fmt(low, 4)} to {_fmt(high, 4)}")
    _emit(args, r, lines)


def cmd_camera(args):
    r = calc.camera_report(args.f35, args.width_px, args.height_px, args.length_mm, args.length_px)
    _emit(args, r, [
        f"focal length: {_fmt(r['focal_length_px'])} px",
        f"camera distance: {_fmt(r['camera_distance_mm'])} mm",
    ])


def cmd_aspect(args):
    r = calc.aspect_check(args.known[0], args.known[1], args.pixels[0], args.pixels[1])
    _emit(args, r, [
        f"known aspect h/w: {_fmt(r['known_aspect'])}; image aspect: {_fmt(r['image_aspect'])}",
        f"image appears {_fmt(r['squat_percent'], 4)} % squat",
        f"scale horizontal {_fmt(r['scale_h'])} mm/px, vertical {_fmt(r['scale_v'])} mm/px",
        f"vertical stretch relative to horizontal: {_fmt(r['stretch_percent'], 4)} %",
    ])


def cmd_label(args):
    r = calc.rounding_uncertainty(args.value, args.unit, args.decimals)
    _emit(args, r, [
        f"value: {_fmt(r['value_mm'])} mm",
        f"rounding half-interval: +/-{_fmt(r['half_interval_mm'])} mm",
        f"standard uncertainty (rectangular, a/sqrt(3)): {_fmt(r['standard_uncertainty_mm'])} mm",
    ])


def cmd_coating(args):
    loss = calc.coating_loss(args.per_face, args.faces)
    r = {"per_face_mm": args.per_face, "faces": args.faces, "width_loss_mm": loss}
    _emit(args, r, [f"width loss: {_fmt(loss)} mm over {args.faces} coated faces"])


def cmd_gear(args):
    r = calc.gear_pair(args.module, args.teeth[0], args.teeth[1], args.pressure_angle)
    _emit(args, r, [
        f"pitch diameters: {_fmt(r['d1'])} mm, {_fmt(r['d2'])} mm",
        f"nominal centre distance: {_fmt(r['center_distance'])} mm",
        f"speed ratio w2/w1: {_fmt(r['speed_ratio'])}",
        "nominal relations only: no tooth profile, backlash, strength, or profile shift",
    ])


def cmd_wind(args):
    area = args.area if args.area is not None else math.pi * (args.diameter / 2.0) ** 2
    r = calc.wind_report(args.rho, area, args.v, args.cp)
    r["area_m2"] = area
    _emit(args, r, [f"swept area: {_fmt(area)} m^2", f"power estimate: {_fmt(r['power_w'])} W"])


def cmd_coupon(args):
    rows = calc.clearance_series(args.nominal, args.start, args.step, args.count)
    r = {"nominal_mm": args.nominal, "definition": "diametral = hole - pin", "rows": rows,
         "warnings": ["Example test settings, not recommended fits. Print in the intended material, "
                      "orientation, layers, and cooling, and test in the finished state."]}
    lines = ["diametral  radial  hole_diameter (mm)"]
    lines += [f"{row['diametral']:9.3f}  {row['radial']:6.3f}  {row['hole_diameter']:.3f}" for row in rows]
    _emit(args, r, lines)


def cmd_units(args):
    ranked = calc.suggest_unit_conversion(args.observed, args.expected_mm)
    r = {"observed": args.observed, "expected_mm": args.expected_mm, "candidates": ranked}
    lines = [f"{c['relative_error'] * 100:8.2f} %  x{c['factor']:<10.6g} {c['interpretation']}"
             for c in ranked[: args.top]]
    best = ranked[0]
    if best["relative_error"] < 0.05:
        lines.append(f"best: {best['interpretation']} -> {_fmt(best['corrected_mm'])} mm")
    else:
        r["warnings"] = ["No common unit explains the mismatch within 5 %; check which dimension is meant."]
    _emit(args, r, lines)


def cmd_evidence(args):
    weakest = calc.weakest_evidence(args.classes)
    r = {"inputs": args.classes, "weakest": weakest}
    _emit(args, r, [f"derived value class: {weakest}"])


def cmd_route(args):
    data = routes.load_routes()
    if args.list:
        r = {"inputs": data["inputs"], "goals": data["goals"]}
        lines = ["inputs:"] + [f"  {i['id']:<14} {i['label']}" for i in data["inputs"]]
        lines += ["goals:"] + [f"  {g['id']:<14} {g['label']}" for g in data["goals"]]
        _emit(args, r, lines)
        return 0
    if args.all:
        r = routes.all_recommendations(data)
        _emit(args, r, [f"{x['input']:<14} {x['goal']:<12} -> " + " then ".join(x["workflows"])
                        + "".join(f"\n{'':<30}warning: {w}" for w in x["warnings"]) for x in r])
        return 0
    if not (args.input and args.goal):
        raise ValueError("give --input and --goal (see --list), or --all")
    r = routes.recommend(data, args.input, args.goal)
    lines = []
    for i, w in enumerate(r["workflows"]):
        wf = data["workflows"][w]
        lines.append(f"{'start' if i == 0 else 'then '}: {wf['name']} (section {wf['section']})")
        lines.append(f"       {wf['start']}.")
    lines += [f"check: {c}" for c in r["checks"]]
    lines.append("read:  " + ", ".join(r["sources"]))
    lines.append("calculators: " + ", ".join(r["calculators"]))
    _emit(args, r, lines)
    return 0


def _load_points(spec: str):
    stripped = spec.lstrip()
    if stripped.startswith(("[", "{")):  # inline JSON; may be far longer than any file name
        text = spec
    else:
        text = Path(spec).read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, dict):
        return data["src"], data["dst"]
    src = [pair[0] for pair in data]
    dst = [pair[1] for pair in data]
    return src, dst


def cmd_homography(args):
    src, dst = _load_points(args.points)
    r = homography.fit_report(src, dst, at=args.at)
    biggest = max(abs(v) for row in r["H"] for v in row)

    def clean(v):  # hide round-off noise in the display only; --json keeps raw values
        return 0.0 if abs(v) < 1e-12 * biggest else v

    lines = ["H ="] + ["  [" + ", ".join(f"{clean(v): .9g}" for v in row) + "]" for row in r["H"]]
    lines.append(f"points: {r['points']}; RMS residual {_fmt(r['rms_residual'])}; max {_fmt(r['max_residual'])} (plane units)")
    if "local_scale_u" in r:
        lines.append(f"at {r['at']}: maps to {[round(v, 6) for v in r['mapped']]}; "
                     f"local scale u {_fmt(r['local_scale_u'])}, v {_fmt(r['local_scale_v'])} units/px "
                     f"({_fmt(r['local_anisotropy_percent'], 3)} % anisotropy)")
    _emit(args, r, lines)


def cmd_meshcheck(args):
    tris = stl.read_stl(args.stl)
    r = stl.analyze(tris, weld_tol=args.weld_tol)
    r["file"] = str(args.stl)
    r["unit_hints"] = stl.unit_hints(r["extents"], args.expect_mm)
    ok = r["watertight"] and r["manifold"] and r["orientation_consistent"] and r["degenerate_triangles"] == 0
    r["status"] = "pass" if ok else "fail"
    ext = " x ".join(_fmt(e) for e in r["extents"])
    lines = [
        f"file: {args.stl}",
        f"triangles: {r['triangles']}; welded vertices: {r['vertices']}; components: {r['components']}",
        f"extents: {ext} (file units)",
        f"surface area: {_fmt(r['surface_area'])}; volume: {_fmt(r['volume'])}",
        f"watertight: {r['watertight']} (boundary edges {r['boundary_edges']}, non-manifold edges {r['nonmanifold_edges']})",
        f"manifold: {r['manifold']} (non-manifold vertices {r['nonmanifold_vertices']})",
        f"orientation consistent: {r['orientation_consistent']}; degenerate triangles: {r['degenerate_triangles']}",
        f"through-holes (genus): {'n/a (not a closed manifold)' if r['genus'] is None else r['genus']}",
    ] + [f"hint: {h}" for h in r["unit_hints"]] + [f"status: {r['status']}"]
    if r["volume"] < 0:
        lines.append("hint: negative volume suggests inward-facing normals")
    _emit(args, r, lines)
    if not ok and not args.allow_open:
        return 1
    return 0


def cmd_params(args):
    reg = params.load_register(args.csv)
    problems = params.validate(reg, args.require or ())
    r = {"parameters": {k: v.as_dict() for k, v in reg.items()}, "problems": problems}
    lines = [f"{p.parameter_id:<20} {'' if p.value is None else p.value!s:>12} {p.unit:<4} {p.evidence_class}"
             for p in reg.values()]
    lines.append(f"{len(reg)} parameters; {len(problems)} problems")
    lines += [f"problem: {p}" for p in problems]
    _emit(args, r, lines)
    return 1 if problems else 0


def cmd_new_project(args):
    created = project.new_project(args.dir, args.name)
    r = {"project": str(args.dir), "files": [str(p) for p in created]}
    _emit(args, r, [f"created {len(created)} files in {args.dir}"])


def cmd_version(args):
    r = {"cadkit": __version__}
    _emit(args, r, [f"cadkit {__version__}"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m cadkit", description=(
        "Handbook calculators and checks for pictures-to-printable-CAD work. "
        "Lengths in mm unless noted. Results are arithmetic, not measurements."))
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, help_text):
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.add_argument("--json", action="store_true", help="print machine-readable JSON")
        p.set_defaults(func=func)
        return p

    p = add("scale", cmd_scale, "planar scale from a reference, optional feature length")
    p.add_argument("--known-mm", type=float, required=True)
    p.add_argument("--reference-px", type=float, required=True)
    p.add_argument("--feature-px", type=float)

    p = add("uncertainty", cmd_uncertainty, "first-order uncertainty of L = p * Lref / pref")
    for name in ("p", "up", "pref", "upref", "lref", "ulref"):
        p.add_argument(f"--{name}", type=float, required=True)

    p = add("chord", cmd_chord, "tessellation: segments for a chord error, or error for a count")
    p.add_argument("--radius", type=float, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--error", type=float)
    g.add_argument("--segments", type=int)

    p = add("depth", cmd_depth, "off-plane depth correction (Z + delta) / Z")
    p.add_argument("--z", type=float, required=True, help="reference-plane distance from the camera")
    p.add_argument("--delta", type=float, required=True, help="extra depth of the feature (behind is positive)")
    p.add_argument("--size", type=float, help="feature size measured at the reference scale")
    p.add_argument("--z-range", type=float, nargs=2, metavar=("MIN", "MAX"))
    p.add_argument("--delta-range", type=float, nargs=2, metavar=("MIN", "MAX"))

    p = add("camera", cmd_camera, "camera distance from a 35 mm-equivalent focal length")
    p.add_argument("--f35", type=float, required=True)
    p.add_argument("--width-px", type=float, required=True)
    p.add_argument("--height-px", type=float, required=True)
    p.add_argument("--length-mm", type=float, required=True)
    p.add_argument("--length-px", type=float, required=True)

    p = add("aspect", cmd_aspect, "check a reference rectangle's image proportions")
    p.add_argument("--known", type=float, nargs=2, required=True, metavar=("W_MM", "H_MM"))
    p.add_argument("--pixels", type=float, nargs=2, required=True, metavar=("W_PX", "H_PX"))

    p = add("label", cmd_label, "rounding uncertainty of a printed label")
    p.add_argument("--value", type=float, required=True)
    p.add_argument("--unit", choices=("in", "mm", "cm"), default="in")
    p.add_argument("--decimals", type=int, required=True)

    p = add("coating", cmd_coating, "width lost to coatings on slot faces")
    p.add_argument("--per-face", type=float, required=True)
    p.add_argument("--faces", type=int, default=2)

    p = add("gear", cmd_gear, "nominal spur-gear pair relations")
    p.add_argument("--module", type=float, required=True)
    p.add_argument("--teeth", type=int, nargs=2, required=True, metavar=("Z1", "Z2"))
    p.add_argument("--pressure-angle", type=float, default=20.0)

    p = add("wind", cmd_wind, "first wind-power estimate 0.5 rho A v^3 Cp")
    p.add_argument("--rho", type=float, default=1.225, help="air density kg/m^3 (default 1.225)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--area", type=float, help="swept area m^2")
    g.add_argument("--diameter", type=float, help="rotor diameter m")
    p.add_argument("--v", type=float, required=True, help="wind speed m/s")
    p.add_argument("--cp", type=float, required=True)

    p = add("coupon", cmd_coupon, "diametral clearance series for a hole coupon")
    p.add_argument("--nominal", type=float, default=5.0)
    p.add_argument("--start", type=float, default=0.10)
    p.add_argument("--step", type=float, default=0.10)
    p.add_argument("--count", type=int, default=5)

    p = add("units", cmd_units, "rank unit interpretations for an imported extent")
    p.add_argument("--observed", type=float, required=True, help="extent shown after import")
    p.add_argument("--expected-mm", type=float, required=True, help="known real size of that extent")
    p.add_argument("--top", type=int, default=5)

    p = add("evidence", cmd_evidence, "weakest evidence class among inputs")
    p.add_argument("classes", nargs="+")

    p = add("homography", cmd_homography, "fit a plane homography from point pairs")
    p.add_argument("--points", required=True, help='JSON file or inline JSON: [[[u,v],[x,y]], ...] or {"src":..., "dst":...}')
    p.add_argument("--at", type=float, nargs=2, metavar=("U", "V"), help="report local scale at this pixel")

    p = add("meshcheck", cmd_meshcheck, "check an STL: extents, volume, watertightness, components")
    p.add_argument("stl", type=Path)
    p.add_argument("--expect-mm", type=float, help="known real size of the largest extent")
    p.add_argument("--weld-tol", type=float, default=1e-6)
    p.add_argument("--allow-open", action="store_true", help="exit 0 even if the mesh fails checks")

    p = add("params", cmd_params, "load and validate a design-parameter register")
    p.add_argument("csv", type=Path)
    p.add_argument("--require", nargs="*", help="parameter ids that must have values")

    p = add("new-project", cmd_new_project, "scaffold a project folder from the templates")
    p.add_argument("dir", type=Path)
    p.add_argument("--name", required=True)

    p = add("route", cmd_route, "recommend a handbook workflow for an input and a goal")
    p.add_argument("--input", help="what you have (see --list)")
    p.add_argument("--goal", help="what you need (see --list)")
    p.add_argument("--list", action="store_true", help="list input and goal ids")
    p.add_argument("--all", action="store_true", help="every input and goal combination")

    add("version", cmd_version, "print the cadkit version")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = args.func(args)
    except (ValueError, KeyError, FileNotFoundError, FileExistsError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return int(code or 0)


if __name__ == "__main__":
    sys.exit(main())
