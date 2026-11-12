"""Independently reconcile paired wall-localization CSV accounting and summaries."""

import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new JSON file; existing files refused")
    args = parser.parse_args()
    plan = json.loads((args.run / "plan.json").read_text())
    result = json.loads((args.run / "results.json").read_text())
    csv_path = args.run / "cases.csv"
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == result["cases_sha256"]
    with csv_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    names = ("wall_levels", "sigmas_px", "phases_px", "quarter_turns", "contrast_inversions", "observations")
    expected = list(itertools.product(*(plan[key] for key in names)))
    assert len(rows) == len(expected) == result["world_scenes"]
    assert {int(row["scene_id"]) for row in rows} == set(range(len(expected)))
    groups = defaultdict(list)
    failed_lanes, initial_matches = 0, 0
    for row in rows:
        fields = (float(row["wall_level"]), float(row["sigma_optical_px"]), float(row["phase_px"]),
                  int(row["quarter_turns"]), row["contrast_inverted"] == "True", row["observation"])
        assert row["contrast_inverted"] in ("True", "False")
        assert fields == expected[int(row["scene_id"])]
        groups[(fields[0], fields[-1])].append(row)
        for label in ("baseline", "candidate"):
            if row[label + "_error"]:
                failed_lanes += 1
                continue
            numeric = ("sigma_used_px", "initial_min_px", "initial_max_px", "final_min_px",
                       "final_max_px", "maximum_absolute_error_px", "elapsed_seconds")
            assert all(math.isfinite(float(row[label + "_" + key])) for key in numeric)
            assert float(row[label + "_sigma_used_px"]) >= 0
            assert float(row[label + "_elapsed_seconds"]) >= 0
            selected = int(row[label + "_selected_points"])
            assert 0 < selected <= int(row[label + "_ring_points"])
            assert 0 <= int(row[label + "_moved_selected_points"]) <= selected
            low, high = float(row[label + "_final_min_px"]), float(row[label + "_final_max_px"])
            assert low <= high
            assert float(row[label + "_maximum_absolute_error_px"]) == max(abs(low), abs(high))
            assert isinstance(json.loads(row[label + "_notes"]), list)
        if not row["baseline_error"] and not row["candidate_error"]:
            assert row["baseline_initial_points_sha256"] == row["candidate_initial_points_sha256"]
            initial_matches += 1
    assert failed_lanes == result["failed_lanes"]
    assert len(groups) == len(result["summary"])
    seen = set()
    for summary in result["summary"]:
        key = summary["wall_level"], summary["observation"]
        assert key not in seen
        seen.add(key)
        group = groups[key]
        assert len(group) == summary["planned"]
        for label in ("baseline", "candidate"):
            valid = [row for row in group if not row[label + "_error"]]
            assert summary[label + "_failed"] == len(group) - len(valid)
            maximum = max((float(row[label + "_maximum_absolute_error_px"]) for row in valid), default=None)
            assert summary[label + "_maximum_absolute_error_px"] == maximum
            assert summary[label + "_scenes_with_movement"] == sum(int(row[label + "_moved_selected_points"]) > 0 for row in valid)
    report = {"world_scenes": len(rows), "paired_successful_initial_matches": initial_matches,
              "failed_lanes": failed_lanes, "complete_unique_cartesian_keys": True,
              "summary_groups_recomputed": len(groups), "cases_sha256": result["cases_sha256"],
              "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "CSV accounting, finite outcomes and summaries; not independent rendering or physical qualification"}
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
