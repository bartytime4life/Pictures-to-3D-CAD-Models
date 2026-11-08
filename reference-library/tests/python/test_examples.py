import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import _helpers

CALCULATE = _helpers.EXAMPLES / "calculate.py"
BUILD_PLATE = _helpers.EXAMPLES / "build_plate.py"


class Calculate(unittest.TestCase):
    def test_committed_results_are_current(self):
        proc = subprocess.run([sys.executable, str(CALCULATE), "--check"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_output_option_writes_same_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.json"
            subprocess.run([sys.executable, str(CALCULATE), "--output", str(out)], check=True, capture_output=True)
            self.assertEqual(out.read_text(), _helpers.GOLDEN.read_text())
            out.write_text("{}\n")
            proc = subprocess.run([sys.executable, str(CALCULATE), "--check", "--output", str(out)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)

    def test_runs_from_another_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.json"
            proc = subprocess.run([sys.executable, str(CALCULATE), "--output", str(out)], cwd=tmp,
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(out.read_text())["minimum_circle_segments"], 50)


@unittest.skipUnless(_helpers.HAS_OPENSCAD, "OpenSCAD is not installed")
class BuildPlate(unittest.TestCase):
    def test_pipeline_passes_and_writes_validation_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([sys.executable, str(BUILD_PLATE), "--output-dir", tmp, "--json"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            summary = json.loads(proc.stdout)
            self.assertEqual(summary["status"], "pass")
            self.assertEqual(summary["segments_per_hole"], 25)
            self.assertEqual(summary["mesh"]["genus"], 2)
            with (Path(tmp) / "validation-results.csv").open() as handle:
                rows = list(csv.DictReader(handle))
            template = (_helpers.TEMPLATES / "validation-results.csv").read_text().splitlines()[0].split(",")
            self.assertEqual(list(rows[0].keys()), template)
            self.assertTrue(rows and all(r["status"] == "pass" for r in rows))
            self.assertTrue(all(r["model_revision"].startswith("scad-sha256:") for r in rows))

    def test_design_rule_failure_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            params = Path(tmp) / "p.csv"
            text = (_helpers.EXAMPLES / "plate-parameters.csv").read_text()
            params.write_text(text.replace("min_wall,2,", "min_wall,9,"))
            proc = subprocess.run([sys.executable, str(BUILD_PLATE), "--params", str(params),
                                   "--output-dir", tmp, "--json"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            failed = {c["feature_id"] for c in json.loads(proc.stdout)["checks"] if c["status"] == "fail"}
            self.assertEqual(failed, {"end_wall_mm"})


if __name__ == "__main__":
    unittest.main()
