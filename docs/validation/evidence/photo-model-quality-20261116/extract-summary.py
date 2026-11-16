"""Print selected executed review fields without copying photos, meshes or local paths.

Usage: python extract-summary.py /path/to/figure-base-refinement-20261116-v2
The source review records and model files must still match their bound hashes.
"""
import hashlib
import json
import sys
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


package = Path(sys.argv[1]).resolve()
records = {}
for name in ("final-reference-review.json", "mechanical-geometry.json", "source-tests.json",
             "exported-pocket-measurements.json", "source-revision.json"):
    records[name] = json.loads((package / "validation" / name).read_text())
image = records["final-reference-review.json"]
mechanical = records["mechanical-geometry.json"]
assert image["pass"] and not mechanical["failures"]
assert mechanical["status"].startswith("pass:")
for figure in image["figures"].values():
    for key in ("original_source", "serialized_assembly"):
        assert sha(Path(figure[key]["path"])) == figure[key]["sha256"]
for mesh in mechanical["mesh_topology"].values():
    assert sha(Path(mesh["path"])) == mesh["sha256"]
summary = {
    "kind": "selected-fields-from-executed-external-model-reviews",
    "scope": "External character-model pipeline; case study only, no workbench sculpt capability",
    "source_commit": records["source-revision.json"]["commit"],
    "source_records": [{"name": name, "sha256": sha(package / "validation" / name)}
                       for name in records],
    "figures": {name: {
        "original_sha256": figure["original_source"]["sha256"],
        "delivered_sha256": figure["serialized_assembly"]["sha256"],
        "rigid_serialization_check": figure["rigid_serialization_check"],
        "accepted_transform": figure["accepted_transform"],
        "scenarios": figure["scenarios"],
        "acceptance": figure["acceptance"],
    } for name, figure in image["figures"].items()},
    "mechanical": {
        "insertion": mechanical["insertion"],
        "joints": [{key: joint[key] for key in (
            "figure", "boot", "required_radial_wall_mm", "radial_wall_probe_radii_mm",
            "radial_wall_probe_z_mm", "radial_wall_missing_mm3", "floor_probe_missing_mm3",
            "radial_wall_excluded_for_figure_insertion_mm3")} for joint in mechanical["joints"]],
        "keepouts": mechanical["keepouts"],
        "mesh_topology": {name: {key: value for key, value in mesh.items() if key != "path"}
                          for name, mesh in mechanical["mesh_topology"].items()},
        "uniform_solid_stability": mechanical["uniform_solid_stability"],
    },
    "maximum_sampled_pocket_error_mm": max(
        model["max_opening_error_mm"]
        for model in records["exported-pocket-measurements.json"]["models"]),
    "external_source_tests": {
        key: records["source-tests.json"][key] for key in ("tests_run", "result", "log_sha256")
    },
    "physical_fit_or_strength_validated": False,
    "limitations": image["limitations"],
}
requirement = summary["mechanical"]["uniform_solid_stability"]["source_requirement"]
requirement["file_name"] = Path(requirement.pop("path")).name
print(json.dumps(summary, indent=2, allow_nan=False))
