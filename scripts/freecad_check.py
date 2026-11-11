"""Open a fitted reference-sheet build in FreeCAD and check it against its design.

Renders the synthetic tilted 4 mm plate photo (tests/synthetic.py: 120 x 70 mm,
R8 corners, 4 x D6 holes, a D22 bore, a 24 x 8 slot), traces and builds it with the
workbench's own API, then has FreeCAD import the STEP and DXF exports. FreeCAD is
not installed by setup; set FREECADCMD to its freecadcmd executable (for an
extracted AppImage, squashfs-root/usr/bin/freecadcmd) or put freecadcmd on PATH.

FreeCAD shares the OpenCascade kernel with the STEP export, so this checks that a
separate CAD application imports the files as true cylinders, arcs and circles of
the right sizes; it is not an independent geometry kernel. The photo is synthetic.
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Design of the synthetic plate, and how far a passing import may stray from it (mm).
DESIGN_SIZE = (120.0, 70.0, 4.0)
DESIGN_RADII = {"hole": (3.0, 4), "slot end": (4.0, 2), "corner": (8.0, 4), "bore": (11.0, 1)}
DESIGN_AREA = (
    120 * 70 - (4 - math.pi) * 64 - 4 * math.pi * 9 - math.pi * 121 - (16 * 8 + math.pi * 16)
)
RADIUS_TOLERANCE = 0.05
SIZE_TOLERANCE = 0.1
VOLUME_TOLERANCE = 0.002  # relative


def freecadcmd():
    found = os.environ.get("FREECADCMD") or shutil.which("freecadcmd") or shutil.which("FreeCADCmd")
    if not found or not Path(found).exists():
        sys.exit(
            "FreeCAD not found. Set FREECADCMD to its freecadcmd executable, or put freecadcmd on PATH."
        )
    return found


def build(directory):
    from fastapi.testclient import TestClient

    from backend import app as api
    from tests import synthetic

    api.JOB_ROOT = directory / "jobs"
    api.JOB_ROOT.mkdir()
    with TestClient(api.app) as client:
        photo, _ = synthetic.render(thickness=4.0)
        trace = client.post(
            "/api/trace",
            files={"file": ("photo.jpg", photo, "image/jpeg")},
            data={"reference": "a4", "thickness_mm": "4"},
        )
        trace.raise_for_status()
        result = trace.json()
        profile = result["profile"]
        width = result["bounds"]["width"] * profile["reference"]["mm_per_px"]
        model = client.post(
            "/api/build",
            json={
                "profile": profile,
                "width_mm": width,
                "thickness_mm": 4,
                "name": "Plate",
                "design": {},
            },
        )
        model.raise_for_status()
        model = model.json()
        paths = {}
        for kind in ("step", "dxf"):
            paths[kind] = directory / f"plate.{kind}"
            paths[kind].write_bytes(client.get(model["downloads"][kind]).content)
    return paths, model["geometry"]


def failures(report):
    step, dxf = report["step"], report["dxf"]
    problems = []
    if step["objects"] != 1 or step["solids"] != 1 or not step["valid"]:
        problems.append(
            f"STEP is not one valid solid: {step['objects']} objects, {step['solids']} solids"
        )
    if step["faces"] != {"Plane": 8, "Cylinder": 11}:
        problems.append(f"STEP faces {step['faces']}, expected 8 planes and 11 cylinders")
    expected = sorted(r for r, count in DESIGN_RADII.values() for _ in range(count))
    for label, radii in (
        ("STEP cylinder", step["cylinder_radii"]),
        ("DXF arc and circle", sorted(dxf["arc_radii"] + dxf["circle_radii"])),
    ):
        if len(radii) != len(expected) or any(
            abs(a - b) > RADIUS_TOLERANCE for a, b in zip(radii, expected)
        ):
            problems.append(
                f"{label} radii {[round(r, 3) for r in radii]}, expected {expected} within {RADIUS_TOLERANCE} mm"
            )
    if any(abs(a - b) > SIZE_TOLERANCE for a, b in zip(step["size"], DESIGN_SIZE)):
        problems.append(
            f"STEP size {[round(v, 3) for v in step['size']]}, expected {list(DESIGN_SIZE)}"
        )
    design_volume = DESIGN_AREA * DESIGN_SIZE[2]
    if abs(step["volume"] / design_volume - 1) > VOLUME_TOLERANCE:
        problems.append(f"STEP volume {step['volume']:.1f} mm3, design {design_volume:.1f}")
    if (dxf["lines"], len(dxf["arc_radii"]), len(dxf["circle_radii"]), dxf["other"]) != (
        6,
        6,
        5,
        0,
    ):
        problems.append(
            f"DXF has {dxf['lines']} lines, {len(dxf['arc_radii'])} arcs, {len(dxf['circle_radii'])} circles, {dxf['other']} other edges; expected 6, 6, 5, 0"
        )
    return problems


def main():
    executable = freecadcmd()
    with tempfile.TemporaryDirectory(prefix="freecad-check-") as temporary:
        directory = Path(temporary)
        paths, geometry = build(directory)
        report_path = directory / "report.json"
        environment = {
            **os.environ,
            "FREECAD_CHECK_ARGS": "\t".join(map(str, (paths["step"], paths["dxf"], report_path))),
        }
        run = subprocess.run(
            [executable, str(ROOT / "scripts" / "freecad_import.py")],
            check=False,
            env=environment,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if not report_path.exists():
            sys.exit(
                f"FreeCAD did not report (exit {run.returncode}):\n{run.stdout[-2000:]}\n{run.stderr[-2000:]}"
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
    step, dxf = report["step"], report["dxf"]
    print(
        f"FreeCAD {report['freecad']} imported the fitted build ({geometry['lines']} lines, {geometry['arcs']} arcs, {geometry['circles']} circles)."
    )
    print(
        f"STEP: {step['solids']} solid, valid {step['valid']}, faces {step['faces']}, size {' x '.join(f'{v:.3f}' for v in step['size'])} mm"
    )
    print(f"STEP cylinder radii: {[round(r, 3) for r in step['cylinder_radii']]}")
    print(
        f"STEP volume {step['volume']:.1f} mm3 against design {DESIGN_AREA * DESIGN_SIZE[2]:.1f} ({100 * (step['volume'] / (DESIGN_AREA * DESIGN_SIZE[2]) - 1):+.3f}%)"
    )
    print(
        f"DXF: {dxf['lines']} lines, arcs {[round(r, 3) for r in dxf['arc_radii']]}, circles {[round(r, 3) for r in dxf['circle_radii']]}"
    )
    problems = failures(report)
    for problem in problems:
        print("FAIL:", problem)
    print("FreeCAD import check failed." if problems else "FreeCAD import check passed.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
