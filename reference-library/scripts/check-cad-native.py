"""Render the files actually downloaded by check-cad.mjs and verify both paths."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from cadkit import openscad, params, scad, stl

QA = ROOT/"tmp/qa"
QA.mkdir(parents=True,exist_ok=True)
REPORT = QA/"cad-native-check.json"
LIB = json.loads((ROOT/"library.json").read_text())
report = {"revision":LIB["revision"],"status":"running","models":{},
          "scope":"Real OpenSCAD renders of synthetic browser downloads and their CSV-driven builds; no physical print or fit test."}


def main():
    if not scad.find_openscad():
        report.update(status="skipped",reason="OpenSCAD not installed; no native render was performed")
        return 0
    browser = json.loads((QA/"cad-check.json").read_text())
    if browser.get("status") != "passed" or browser.get("revision") != LIB["revision"]:
        raise ValueError("Run check-cad.mjs successfully for the current revision first")
    folder = Path(tempfile.mkdtemp(prefix="cad-native-",dir=QA))
    for model in ("plate","coupon"):
        source = QA/"cad-downloads"/(model+".scad")
        parameter_file = QA/"cad-downloads"/(model+"-parameters.csv")
        register = params.load_register(parameter_file)
        expected = openscad.geometry(model,register)
        direct = scad.render(source,folder/(model+"-browser.stl"))
        if not direct.ok:
            raise RuntimeError("Downloaded SCAD render failed: "+direct.stderr)
        mesh,checks = openscad.check_mesh(stl.read_stl(direct.output),expected)
        if any(c["status"] != "pass" for c in checks):
            raise RuntimeError("Downloaded SCAD mesh failed checks: "+json.dumps(checks))
        built = openscad.build(model,folder/(model+"-csv"),parameter_file)
        report["models"][model] = {"status":"passed","openscad_version":direct.version,
            "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "csv_sha256":hashlib.sha256(parameter_file.read_bytes()).hexdigest(),
            "direct_render":str(direct.output.relative_to(ROOT)),"csv_build":str((folder/(model+"-csv")).relative_to(ROOT)),
            "mesh":mesh,"direct_checks":len(checks),"csv_build_checks":len(built["checks"]),
            "values":expected["values"]}
    report["status"] = "passed"
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception as exc:
        report.update(status="failed",error=str(exc))
    REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"report":str(REPORT),"models":list(report["models"])}))
    sys.exit(code)
