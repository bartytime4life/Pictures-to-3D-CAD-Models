"""Inspect the optional local slicer bridge without starting any application."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.slicers import program_status

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--json", action="store_true")
args = parser.parse_args()
status = program_status()
if args.json:
    print(json.dumps(status, indent=2))
else:
    for program in status["programs"]:
        detected = "executable found; version not checked" if program["detected"] else "not found"
        print(f"{program['name']} (target {program['target_version']}): {detected}")
        print(program["launch_reason"])
