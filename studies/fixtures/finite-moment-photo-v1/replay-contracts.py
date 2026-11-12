"""Portable CLI and exact-row checks; every output lives in a temporary folder."""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent
RUNNER = ROOT / "studies/verification/finite-moment-photo-v1.py"


def main():
    checks = 0

    def check(value, message):
        nonlocal checks
        if not value:
            raise AssertionError(message)
        checks += 1

    with tempfile.TemporaryDirectory(prefix="finite-moment-contract-") as directory:
        temp = Path(directory)
        (temp / "numpy.py").write_text("raise SystemExit(91)\n")
        env = {**os.environ, "PYTHONPATH": str(temp)}

        def refusal(arguments):
            result = subprocess.run(
                [sys.executable, "-S", str(RUNNER), *map(str, arguments)],
                capture_output=True, env=env, check=False,
            )
            check(result.returncode == 2, (arguments, result.returncode, result.stderr.decode()))
            check(result.stdout == b"", ("unexpected refusal stdout", arguments))

        help_result = subprocess.run(
            [sys.executable, "-S", str(RUNNER), "--help"],
            capture_output=True, env=env, check=False,
        )
        check(help_result.returncode == 0 and b"--output" in help_result.stdout,
              "help imports numerical dependencies")
        refusal([])
        existing = temp / "existing.json"
        existing.write_bytes(b"KEEP\n")
        refusal(["--output", existing])
        check(existing.read_bytes() == b"KEEP\n", "existing bytes changed")
        dangling = temp / "dangling.json"
        dangling.symlink_to(temp / "missing-target")
        refusal(["--output", dangling])
        check(dangling.is_symlink() and not (temp / "missing-target").exists(), "dangling symlink changed")
        linked = temp / "linked.json"
        linked.symlink_to(existing)
        refusal(["--output", linked])
        check(linked.is_symlink() and existing.read_bytes() == b"KEEP\n", "linked target changed")
        directory_output = temp / "directory.json"
        directory_output.mkdir()
        refusal(["--output", directory_output])
        refusal(["--output", temp / "missing" / "out.json"])
        check(not (temp / "missing").exists(), "created missing parent")
        refusal(["--output", temp / "bad.txt"])
        check(not (temp / "bad.txt").exists(), "created bad extension")

        output = temp / "replay.json"
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--output", str(output)],
            capture_output=True, check=False,
        )
        check(result.returncode == 0, result.stderr.decode())
        check(output.read_bytes() == result.stdout, "stdout differs from saved JSON")
        data = json.loads(result.stdout)
        original = json.loads((FIXTURES / "original-moment-result.json").read_bytes())
        check(data["rows"] == original["rows"], "original numerical rows changed")
        check(data["summary"] == {
            "row_count": 76, "attempted_moment_rows": 75,
            "status_counts": {"moment_proposal": 74, "refused": 1, "upstream_ineligible": 1},
            "nominal_row_count": 5, "nominal_geometry_targets_passed": 4,
            "indefinite_or_nonpositive_covariance_rows": 10,
            "production_geometry_changed": False, "gaussian_psf_certified": False,
            "population_accuracy_estimated": False,
        }, "conservation or adverse outcomes differ")
        check(data["replay_checks"]["source_and_inputs_unchanged"], "inputs drifted")
        check(len(data["provenance"]["field_hashes"]) == 5, "five fields not retained")
        check(all(len(item["outcomes"]) == 6 for item in data["upstream_baselines"].values()),
              "upstream rows missing")
        check(data["provenance"]["source_hashes_before"] == data["provenance"]["source_hashes_after"],
              "source bindings differ")

        second = subprocess.run(
            [sys.executable, str(RUNNER), "--output", str(temp / "second.json")],
            capture_output=True, check=False,
        )
        check(second.returncode == 0 and second.stdout == result.stdout, "same-source replay differs")

        # Deterministically insert an output after validation, before final open.
        import runpy

        entry = runpy.run_path(str(RUNNER))["main"]
        race_output = temp / "raced.json"

        def intervening_writer():
            race_output.write_bytes(b"RACE\n")
            return {"status": "reproduced"}

        entry.__globals__["run"] = intervening_writer
        with redirect_stderr(io.StringIO()):
            exit_code = entry(["--output", str(race_output)])
        check(exit_code == 2 and race_output.read_bytes() == b"RACE\n",
              "exclusive output write lost a race")

        fake = temp / "tampered"
        (fake / "studies/verification").mkdir(parents=True)
        shutil.copyfile(RUNNER, fake / "studies/verification" / RUNNER.name)
        shutil.copyfile(ROOT / "studies/finite-moment-photo-v1.json",
                        fake / "studies/finite-moment-photo-v1.json")
        shutil.copytree(FIXTURES, fake / "studies/fixtures/finite-moment-photo-v1")
        corrupt = fake / "studies/fixtures/finite-moment-photo-v1/small-isotropic-measurement.npz"
        payload = bytearray(corrupt.read_bytes())
        payload[-1] ^= 1
        corrupt.write_bytes(payload)
        target = temp / "tampered.json"
        bad = subprocess.run(
            [sys.executable, str(fake / "studies/verification" / RUNNER.name), "--output", str(target)],
            capture_output=True, check=False,
        )
        check(bad.returncode == 2 and b"measured field has changed" in bad.stderr and not target.exists(),
              "tampered fixture not refused before analysis/output")
        print(json.dumps({
            "contract_checks_passed": checks,
            "all_original_rows_exactly_equal": True,
            "summary": data["summary"],
            "runtime": data["provenance"]["runtime"],
            "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
            "fixture_manifest_sha256": data["provenance"]["fixture_manifest_sha256"],
        }, indent=2))


if __name__ == "__main__":
    main()
