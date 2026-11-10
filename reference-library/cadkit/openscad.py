"""Local, traceable OpenSCAD builds for the two mechanical teaching models.

The browser and this module share one parameter schema. Builds commit a new
directory only after rendering and independent mesh checks succeed.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, calc, params, scad, stl

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "assets/data/openscad-models.json"


def catalog():
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def model_spec(model, data=None):
    try:
        return (data if data is not None else catalog())["models"][model]
    except KeyError:
        raise ValueError("choose model plate or coupon") from None


def default_register(model, spec=None):
    return {p["id"]: params.Param(p["id"], float(p["default"]), p["unit"],
            p["evidence_class"], p["source_or_rationale"], used_by=model,
            notes=p.get("notes", "")) for p in (spec or model_spec(model))["parameters"]}


def register_csv(register):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=params.COLUMNS)
    writer.writeheader()
    writer.writerows(p.as_dict() for p in register.values())
    return output.getvalue()


def geometry(model, register, spec=None):
    """Validate before launching OpenSCAD; return analytic layout expectations."""
    spec = spec or model_spec(model)
    required = [p["id"] for p in spec["parameters"]]
    problems = params.validate(register, required)
    extra = set(register) - set(required)
    if extra:
        problems.append("unsupported parameters: " + ", ".join(sorted(extra)))
    p = {}
    for field in spec["parameters"]:
        pid = field["id"]
        if pid not in register:
            continue
        row = register[pid]
        value = row.value
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            problems.append(f"{pid}: needs a finite numeric value")
            continue
        p[pid] = value
        if row.unit != field["unit"]:
            problems.append(f"{pid}: unit must be {field['unit']!r}; values are never auto-converted")
        if not row.source_or_rationale.strip():
            problems.append(f"{pid}: record a source or rationale")
        lower, upper = field.get("min", -math.inf), field.get("max", math.inf)
        if value < lower or (field.get("exclusive_min") and value == lower) or value > upper:
            problems.append(f"{pid}: outside the supported range")
        if field.get("integer") and value != int(value):
            problems.append(f"{pid}: must be an integer")
    if problems:
        raise ValueError("; ".join(problems))

    def segments(diameter):
        radius = diameter / 2
        if not 0 < p["chord_error"] < radius:
            raise ValueError("chord_error must be positive and less than the smallest hole radius")
        # Bound work before acos/large tessellations, also avoiding roundoff to 1.
        if p["chord_error"] < radius * (1 - math.cos(math.pi / 720)):
            raise ValueError("chord_error would require more than 720 segments per hole")
        return max(16, calc.min_segments(radius, p["chord_error"]))

    if model == "plate":
        L, W, T, d, s = (p[k] for k in ("plate_length", "plate_width", "plate_thickness", "hole_diameter", "hole_spacing"))
        walls = [(L-s-d)/2, (W-d)/2, s-d]
        if min(walls) < p["min_wall"]:
            raise ValueError("plate end walls, side walls and web must each meet min_wall")
        n = segments(d)
        holes = [{"x": x, "y": 0, "radius": d/2, "segments": n} for x in (-s/2, s/2)]
        notch_volume = 0
    else:
        count = int(p["clearance_count"])
        ds = [p["pin_diameter"] + p["clearance_start"] + i*p["clearance_step"] for i in range(count)]
        ns = [segments(d) for d in ds]
        rs = [d/2/math.cos(math.pi/n) for d,n in zip(ds, ns)]
        rmax = max(rs)
        pitch = 2*rmax+p["min_wall"]
        L = 2*(p["end_wall"]+rmax)+(count-1)*pitch
        W, T = 2*(p["min_wall"]+rmax), p["thickness"]
        if p["end_wall"] < p["min_wall"]:
            raise ValueError("end_wall must be at least min_wall")
        if (p["end_wall"]+p["min_wall"]+2*rmax-p["notch_size"])/math.sqrt(2)-rmax < p["min_wall"]:
            raise ValueError("notch_size leaves less than min_wall beside the first hole")
        holes = [{"x": p["end_wall"]+rmax+i*pitch, "y": p["min_wall"]+rmax,
                  "radius": r, "segments": n} for i,(r,n) in enumerate(zip(rs,ns))]
        notch_volume = p["notch_size"]**2/2*T
    volume = L*W*T-notch_volume-sum(h["segments"]/2*h["radius"]**2 * math.sin(2*math.pi/h["segments"])*T for h in holes)
    return {"extents": [L,W,T], "volume": volume, "holes": holes, "values": p}


def check_mesh(triangles, expected):
    mesh = stl.analyze(triangles)
    checks = []

    def check(name, target, actual, tolerance=0):
        checks.append({"feature_id": name, "target": target, "actual": actual,
                       "tolerance": tolerance, "status": "pass" if abs(actual-target) <= tolerance else "fail"})

    for axis, actual, target in zip("xyz", mesh["extents"], expected["extents"]):
        check(f"extent_{axis}_mm", target, actual, max(1e-4, abs(target)*2e-7))
    check("volume_mm3", expected["volume"], mesh["volume"], max(1e-4, abs(expected["volume"])*2e-5))
    for name, target in (("components",1), ("boundary_edges",0), ("nonmanifold_edges",0),
                         ("nonmanifold_vertices",0), ("degenerate_triangles",0)):
        check(name, target, mesh[name])
    check("watertight",1,int(mesh["watertight"]))
    check("orientation_consistent",1,int(mesh["orientation_consistent"]))
    check("through_holes",len(expected["holes"]), mesh["genus"] if mesh["genus"] is not None else -1)
    vertices = {v for tri in triangles for v in tri}
    for i, hole in enumerate(expected["holes"]):
        distances = [math.hypot(v[0]-hole["x"], v[1]-hole["y"]) for v in vertices]
        ring = [d for d in distances if abs(d-hole["radius"]) < 1e-3]
        check(f"hole_{i+1}_ring_vertices",2*hole["segments"],len(ring))
        check(f"hole_{i+1}_radial_deviation_mm",0,max((abs(d-hole["radius"]) for d in ring), default=1e99),1e-4)
    return mesh, checks


def doctor():
    executable = scad.find_openscad()
    detected_version = scad.version(executable) if executable else None
    return {"status": "ready" if detected_version else ("error" if executable else "missing"), "executable": executable,
            "version": detected_version,
            "models": list(catalog()["models"]), "units": "mm",
            "preview_available": bool(os.environ.get("DISPLAY") or shutil.which("xvfb-run") or os.name == "nt"),
            "scope": "Local executable discovery; no installation or physical qualification."}


def _preview(source, dest, executable):
    command = [executable,"-o",str(dest),"--render","--autocenter","--viewall","--imgsize=1200,800",str(source)]
    if os.name == "posix" and not os.environ.get("DISPLAY"):
        xvfb = shutil.which("xvfb-run")
        if not xvfb:
            raise ValueError("PNG preview needs a display or xvfb-run; omit --preview to build STL only")
        command = [xvfb,"-a",*command]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    log = result.stdout + result.stderr
    if result.returncode or "ERROR:" in log or not dest.is_file() or not dest.stat().st_size:
        raise RuntimeError("OpenSCAD PNG preview failed: " + log)
    return command, log


def build(model, output_dir, parameter_path=None, preview=False):
    schema_bytes = SCHEMA.read_bytes()
    spec = model_spec(model,json.loads(schema_bytes))
    parameter_bytes = Path(parameter_path).read_bytes() if parameter_path else register_csv(default_register(model,spec)).encode()
    register = params.parse_register(parameter_bytes.decode("utf-8"),str(parameter_path or "<synthetic defaults>"))
    expected = geometry(model, register, spec)
    executable = scad.find_openscad()
    if not executable:
        raise FileNotFoundError("OpenSCAD not found; set CADKIT_OPENSCAD or install OpenSCAD")
    dest = Path(output_dir).absolute()
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; choose a new output directory to preserve earlier builds")
    dest.parent.mkdir(parents=True, exist_ok=True)
    template = ROOT / spec["template"]
    source_bytes = template.read_bytes()
    sha = lambda b: hashlib.sha256(b).hexdigest()
    revision = sha(source_bytes+b"\0"+parameter_bytes+b"\0"+schema_bytes)
    with tempfile.TemporaryDirectory(prefix=".cadkit-build-",dir=dest.parent) as scratch:
        stage = Path(scratch) / "result"
        stage.mkdir()
        source = source_bytes.decode("utf-8")
        for key,value in {**expected["values"],**spec.get("fixed",{})}.items():
            assignment = scad.format_define(key,value)+";"
            pattern = rf"(?m)^{re.escape(key)}\s*=\s*[^;]+;"
            if re.search(pattern,source):
                source = re.sub(pattern,lambda _:assignment,source,count=1)
            else:
                source = assignment+"\n"+source
        source = "// Local CAD workspace export. Units mm. See parameters.csv for evidence.\n"+source
        if model == "plate":
            source += ('\nassert(min_wall > 0, "minimum wall must be positive");\n'
                       'assert((plate_length-hole_spacing-hole_diameter)/2 >= min_wall, "end wall below minimum");\n'
                       'assert((plate_width-hole_diameter)/2 >= min_wall, "side wall below minimum");\n'
                       'assert(hole_spacing-hole_diameter >= min_wall, "web below minimum");\n')
        (stage/"source.scad").write_text(source,encoding="utf-8")
        (stage/"parameters.csv").write_bytes(parameter_bytes)
        result = scad.render(stage/"source.scad",stage/"model.stl",executable=executable)
        if not result.ok:
            raise RuntimeError("OpenSCAD render failed: "+result.stderr+result.stdout)
        mesh,checks = check_mesh(stl.read_stl(stage/"model.stl"),expected)
        if any(c["status"] != "pass" for c in checks):
            raise RuntimeError("Rendered mesh failed checks: "+", ".join(c["feature_id"] for c in checks if c["status"] != "pass"))
        (stage/"render.log").write_text(result.stdout+result.stderr,encoding="utf-8")
        with (stage/"validation-results.csv").open("w",newline="",encoding="utf-8") as handle:
            writer = csv.DictWriter(handle,fieldnames=("feature_id","target","actual","tolerance","status"))
            writer.writeheader()
            writer.writerows(checks)
        preview_command = None
        if preview:
            preview_command,log = _preview(stage/"source.scad",stage/"preview.png",executable)
            (stage/"preview.log").write_text(log,encoding="utf-8")
        record = {"schema_version":1,"status":"passed","model":model,"units":"mm",
                  "built_at":datetime.now(timezone.utc).isoformat(),"model_revision_sha256":revision,
                  "cadkit_version":__version__,"openscad_version":result.version,
                  "output_dir":str(dest),"parameters":{k:v.as_dict() for k,v in register.items()},
                  "input_sha256":{"template":sha(source_bytes),"parameters":sha(parameter_bytes),"schema":sha(schema_bytes)},
                  "outputs_sha256":{p.name:sha(p.read_bytes()) for p in sorted(stage.iterdir()) if p.is_file()},
                  "command":result.command,"preview_command":preview_command,
                  "command_path_note":"Commands record temporary build paths; files were moved together into output_dir after passing checks.",
                  "warnings":result.warnings,"mesh":mesh,"checks":checks,
                  "physical_printing":"not performed","slicing":"not performed",
                  "scope":"Mesh topology and analytic geometry checks. Parameters retain their stated evidence; no physical fit, strength or print qualification."}
        (stage/"build.json").write_text(json.dumps(record,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        if dest.exists():
            raise FileExistsError(f"{dest} appeared during build; earlier data was preserved")
        stage.rename(dest)
    return record
