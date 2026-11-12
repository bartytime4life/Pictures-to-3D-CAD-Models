"""Reconcile the complete wall-gradient CSVs against the frozen plan and summary."""

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new JSON record; existing files refused")
    args = parser.parse_args()
    plan = json.loads((args.run / "plan.json").read_text())
    result = json.loads((args.run / "results.json").read_text())
    assert result["version"] in (1, 2)
    records = {}
    for name in ("geometry-fits.csv", "image-fits.csv"):
        path = args.run / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == result["artifact_sha256"][name]
        with path.open(newline="") as stream:
            records[name] = list(csv.DictReader(stream))
    direct, images = records.values()
    direct_scenes = list(itertools.product(plan["sigmas_px"], plan["direct_lane"]["band_width_sigmas"],
                                          plan["conditions"], plan["contrast_inversions"]))
    expected_direct = set(itertools.product(range(len(direct_scenes)), plan["direct_lane"]["offsets_sigmas"],
                                           plan["direct_lane"]["models"]))
    actual_direct = {(int(r["scene_id"]), float(r["offset_sigmas"]), r["model"]) for r in direct}
    assert len(direct) == len(actual_direct) and actual_direct == expected_direct
    for row in direct:
        sigma, width, condition, inverted = direct_scenes[int(row["scene_id"])]
        assert float(row["sigma_px"]) == sigma and float(row["band_sigmas"]) == width
        assert row["condition"] == condition["name"] and row["contrast_inverted"] == str(inverted)
        assert row["error"] == ""
        levels = [float(row[k]) for k in ("top_left", "top_edge", "wall", "paper_edge", "paper_right")]
        assert all(math.isfinite(v) and 0 <= v <= 255 for v in levels)
        assert all(math.isfinite(float(row[k])) and float(row[k]) >= 0
                   for k in ("sse", "maximum_difference", "midpoint_error_bound"))
    for summary in result["witness_summary"]:
        eligible = [r for r in direct if r["model"] == summary["model"] and float(r["offset_px"]) != 0]
        witnesses = [r for r in eligible if float(r["midpoint_error_bound"]) <= summary["illustrative_level_bound"]]
        assert len(eligible) == summary["alternative_fits_examined"]
        assert len(witnesses) == summary["witnesses_found"]
        assert max((abs(float(r["offset_px"])) for r in witnesses), default=None) == summary["maximum_demonstrated_edge_separation_px"]
    image_scenes = list(itertools.product(plan["sigmas_px"], plan["image_lane"]["band_width_sigmas"],
                                         plan["conditions"], plan["contrast_inversions"],
                                         plan["image_lane"]["normal_angles_degrees"], plan["image_lane"]["normal_phases_px"]))
    expected_images = set(itertools.product(range(len(image_scenes)), plan["image_lane"]["stages"],
                                           plan["image_lane"]["methods"]))
    actual_images = {(int(r["scene_id"]), r["stage"], r["method"]) for r in images}
    assert len(images) == len(actual_images) and actual_images == expected_images
    for row in images:
        sigma, width, condition, inverted, angle, phase = image_scenes[int(row["scene_id"])]
        assert float(row["sigma_px"]) == sigma and float(row["band_sigmas"]) == width
        assert row["condition"] == condition["name"] and row["contrast_inverted"] == str(inverted)
        assert float(row["normal_degrees"]) == angle and float(row["phase_px"]) == phase
        assert row["error"] == ""
        resolved = result["version"] == 1 or row["resolved"] == "True"
        if result["version"] == 2:
            assert row["resolved"] in ("True", "False")
        if resolved:
            assert all(math.isfinite(float(row[k])) for k in ("offset_px", "offset_sigmas", "wall_level", "reported_sse"))
        else:
            assert all(row[k] == "" for k in ("offset_px", "offset_sigmas", "wall_level", "reported_sse"))
    for summary in result["image_summary"]:
        group = [r for r in images if all(r[k] == summary[k] for k in ("stage", "method", "condition"))
                 and float(r["band_sigmas"]) == summary["band_sigmas"]]
        valid = [r for r in group if result["version"] == 1 or r["resolved"] == "True"]
        offsets = [float(r["offset_px"]) for r in valid]
        assert summary["planned"] == len(group) and summary["failed"] == 0
        if result["version"] == 2:
            assert summary["resolved"] == len(valid)
            assert summary["unresolved"] == len(group) - len(valid)
        assert summary["median_offset_px"] == (statistics.median(offsets) if offsets else None)
        assert summary["maximum_absolute_offset_px"] == (max(abs(v) for v in offsets) if offsets else None)
        assert summary["fitted_wall_outside_0_255"] == sum(not 0 <= float(r["wall_level"]) <= 255 for r in valid)
    report = {"direct_rows": len(direct), "image_rows": len(images), "complete_unique_cartesian_keys": True,
              "all_fitted_source_nodes_physical": True, "failed_rows": 0,
              "unresolved_image_rows": sum(result["version"] == 2 and row["resolved"] == "False" for row in images),
              "image_summary_groups_recomputed": len(result["image_summary"]),
              "witness_summary_groups_recomputed": len(result["witness_summary"]),
              "artifact_sha256": result["artifact_sha256"],
              "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Complete CSV arithmetic/coverage audit; not an independent production renderer, optimization certificate or physical qualification"}
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
