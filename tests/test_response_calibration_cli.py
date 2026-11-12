"""Exact calibration request/provenance/refusal checks; no photo or server IO."""

import hashlib
import json
import subprocess
import sys

import pytest

from scripts import response_calibration as cli


def request(**changes):
    result = {
        "version": 1,
        "units": {"input": "normalized exposure", "output": "normalized source level"},
        "nodes": [{"input": "0", "output": ["0", "0"]}, {"input": "1", "output": ["1", "1"]}],
        "slope_bounds": ["0", "2"],
        "queries": ["0.25", "0.5", "0.75"],
    }
    result.update(changes)
    return result


def test_exact_report_envelopes_and_original_input_bytes_are_bound():
    data = json.dumps(request(), indent=3).encode()
    report = cli.analyze_bytes(data)
    assert report["queries"] == [
        {"input": "1/4", "output": ["0", "1/2"]},
        {"input": "1/2", "output": ["0", "1"]},
        {"input": "3/4", "output": ["1/2", "1"]},
    ]
    assert report["input"] == request()
    assert report["provenance"]["input_sha256"] == hashlib.sha256(data).hexdigest()
    for name, sha in report["provenance"]["source_sha256"].items():
        assert hashlib.sha256((cli.ROOT / name).read_bytes()).hexdigest() == sha


def test_incompatible_model_keeps_proof_and_marks_queries_unavailable():
    raw = request(
        nodes=[{"input": "0", "output": ["1", "1"]}, {"input": "1", "output": ["0", "0"]}]
    )
    report = cli.analyze_bytes(json.dumps(raw).encode())
    assert report["calibration"]["status"] == "incompatible"
    assert report["calibration"]["contradiction"] is not None
    assert all(q["unavailable"] == "incompatible_calibration" for q in report["queries"])
    raw["queries"] = ["NaN"]
    with pytest.raises(ValueError):
        cli.analyze_bytes(json.dumps(raw).encode())


@pytest.mark.parametrize(
    "change",
    [
        {"version": True},
        {"version": 2},
        {"unknown": 1},
        {"nodes": []},
        {"units": {"input": "x"}},
        {"units": {"input": "x\n", "output": "y"}},
        {"queries": [0.5]},
        {"queries": [True]},
        {"queries": ["1/2"]},
        {"queries": ["2"]},
        {"queries": ["0"] * 257},
        {"slope_bounds": [0, None]},
        {"slope_bounds": ["2", "1"]},
        {"nodes": [{"input": "0", "output": [0, 1]}]},
    ],
)
def test_invalid_schema_numbers_and_outside_domain_are_refused(change):
    with pytest.raises((ValueError, TypeError)):
        cli.analyze_bytes(json.dumps(request(**change)).encode())


def test_duplicate_keys_nonfinite_json_and_oversize_input_are_refused():
    for data in [b'{"version":1,"version":1}', b'{"x": NaN}', b" " * (cli.MAX_INPUT_BYTES + 1)]:
        with pytest.raises(ValueError):
            cli.analyze_bytes(data)


def test_source_mutation_is_refused_without_a_conclusion(monkeypatch):
    real = cli.source_hashes()
    calls = []

    def hashes():
        calls.append(1)
        return real if len(calls) < 3 else {**real, "changed": "source"}

    monkeypatch.setattr(cli, "source_hashes", hashes)
    with pytest.raises(ValueError, match="source changed"):
        cli.analyze_bytes(json.dumps(request()).encode())


def test_explicit_cli_from_unrelated_directory_and_existing_output_preservation(tmp_path):
    source, output = tmp_path / "input.json", tmp_path / "result.json"
    source.write_text(json.dumps(request()))
    args = [
        sys.executable,
        str(cli.ROOT / "scripts/response_calibration.py"),
        str(source),
        "--output",
        str(output),
    ]
    done = subprocess.run(
        args, cwd=tmp_path, capture_output=True, text=True, timeout=15, check=True
    )
    assert done.stdout == output.read_text()
    assert json.loads(done.stdout)["calibration"]["status"] == "compatible"
    previous = output.read_bytes()
    again = subprocess.run(
        args, cwd=tmp_path, capture_output=True, text=True, timeout=15, check=False
    )
    assert again.returncode == 2 and again.stdout == "" and output.read_bytes() == previous
    help_run = subprocess.run(
        args[:2] + ["--help"], cwd=tmp_path, capture_output=True, text=True, timeout=15, check=False
    )
    assert help_run.returncode == 0 and "usage:" in help_run.stdout
    no_args = subprocess.run(
        args[:2], cwd=tmp_path, capture_output=True, text=True, timeout=15, check=False
    )
    assert no_args.returncode == 2 and no_args.stdout == ""


def test_invalid_input_creates_no_output(tmp_path):
    source, output = tmp_path / "bad.json", tmp_path / "not-created.json"
    source.write_text(json.dumps(request(queries=["-1"])))
    with pytest.raises(SystemExit) as error:
        cli.main([str(source), "--output", str(output)])
    assert error.value.code == 2 and not output.exists()
