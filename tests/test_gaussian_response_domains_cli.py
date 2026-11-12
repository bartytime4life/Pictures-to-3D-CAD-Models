"""Strict requests, mathematical status and source-bound CLI output."""

import copy
import hashlib
import json
import subprocess
import sys

import pytest

from scripts import gaussian_response_domains as cli


def request():
    return {
        "version": 1,
        "units": {"position": "source pixels", "output": "normalized level"},
        "observations": [{"position": "0", "output": ["0.5", "0.5"]}],
        "calibration": [{"input": "0", "output": ["0", "0"]}, {"input": "1", "output": ["1", "1"]}],
        "offset_bounds": ["0", "0"],
        "sigma_bounds": ["0.75", "1.25"],
        "slope_bounds": ["1", "1"],
    }


def analyze(raw):
    return cli.analyze_bytes(json.dumps(raw).encode())


def test_exact_source_bound_request_and_nonidentified_sigma():
    raw = request()
    data = json.dumps(raw, indent=2).encode()
    result = cli.analyze_bytes(data)
    assert result["input"] == raw
    assert result["analysis"]["status"] == "compatible"
    assert result["analysis"]["outer_projection"]["sigma"] == ["3/4", "5/4"]
    assert result["provenance"]["input_sha256"] == hashlib.sha256(data).hexdigest()
    assert set(result["provenance"]["source_sha256"]) == set(cli.SOURCE_FILES)
    for path, digest in result["provenance"]["source_sha256"].items():
        assert digest == hashlib.sha256((cli.ROOT / path).read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "key,value",
    [
        ("version", True),
        ("version", 2),
        ("units", {"position": "px"}),
        ("units", {"position": "\n", "output": "x"}),
        ("units", {"position": "x" * 81, "output": "x"}),
        ("observations", []),
        ("observations", [{"position": 0, "output": ["0", "1"]}]),
        ("observations", [{"position": "0", "output": [0, "1"]}]),
        ("observations", [{"position": "1/2", "output": ["0", "1"]}]),
        ("observations", [{"position": "0", "output": ["1", "0"]}]),
        ("observations", [{"position": "0", "output": ["0", "1"], "typo": True}]),
        ("offset_bounds", ["1", "0"]),
        ("offset_bounds", [0, "1"]),
        ("sigma_bounds", ["0", "1"]),
        ("tolerances", ["0", "0.01"]),
        ("slope_bounds", ["1", "0"]),
        ("slope_bounds", ["-1", None]),
        ("calibration", [{"input": "1.1", "output": ["0", "1"]}]),
        ("max_boxes", True),
        ("max_boxes", 0),
        ("max_boxes", 4096),
        ("max_depth", True),
        ("max_depth", -1),
        ("max_depth", 49),
        ("cdf_places", 1.5),
        ("cdf_places", 0),
        ("cdf_places", 31),
        ("typo", "0"),
    ],
)
def test_invalid_request_is_refused_not_incompatible(key, value):
    raw = request()
    raw[key] = value
    with pytest.raises((ValueError, TypeError)):
        analyze(raw)


def test_duplicate_keys_nonfinite_and_input_size_refused():
    data = json.dumps(request())
    for bad in [
        data.replace('"version": 1', '"version": 1, "version": 1'),
        data.replace('"position": "0"', '"position": "0", "position": "1"'),
        data.replace('"version": 1', '"version": NaN'),
    ]:
        with pytest.raises(ValueError):
            cli.analyze_bytes(bad.encode())
    with pytest.raises(ValueError, match="512 KiB"):
        cli.analyze_bytes(b" " * (cli.MAX_INPUT_BYTES + 1))


def test_unknown_feasibility_is_tristate_and_keeps_pending_boxes():
    raw = request()
    raw["offset_bounds"] = ["-1", "1"]
    raw["max_boxes"] = 1
    result = analyze(raw)["analysis"]
    assert result["status"] == "unresolved"
    assert result["summary"]["feasible_parameters_exist"] is None
    assert result["summary"]["has_certified_feasible_parameters"] is False
    assert result["unknown_node_indices"] == [1, 2]
    assert all(result["nodes"][i]["reason"] == "box_limit" for i in (1, 2))


def test_source_changes_refuse_before_and_after_analysis(monkeypatch):
    real = cli.source_hashes
    baseline = real()
    for when in (2, 3):
        calls = 0

        def changed(when=when):
            nonlocal calls
            calls += 1
            return baseline if calls != when else {**baseline, "changed": "x"}

        monkeypatch.setattr(cli, "source_hashes", changed)
        with pytest.raises(ValueError, match="sources changed"):
            analyze(request())


def test_subprocess_stdout_matches_file_and_existing_output_is_preserved(tmp_path):
    input_path = tmp_path / "input.json"
    output = tmp_path / "nested/result.json"
    input_path.write_text(json.dumps(request()))
    args = [
        sys.executable,
        str(cli.ROOT / "scripts/gaussian_response_domains.py"),
        str(input_path),
        "--output",
        str(output),
    ]
    result = subprocess.run(args, cwd=tmp_path, text=True, capture_output=True, check=True)
    assert result.stdout == output.read_text()
    before = output.read_bytes()
    again = subprocess.run(args, cwd=tmp_path, text=True, capture_output=True, check=False)
    assert again.returncode == 2 and output.read_bytes() == before


def test_dangling_output_and_missing_arguments_run_no_analysis(tmp_path, monkeypatch):
    def forbidden(_):
        raise AssertionError("analysis must not run")

    monkeypatch.setattr(cli, "analyze_bytes", forbidden)
    output = tmp_path / "dangling"
    output.symlink_to(tmp_path / "missing")
    for arguments in [[], ["--help"], ["missing.json", "--output", str(output)]]:
        with pytest.raises(SystemExit) as error:
            cli.main(arguments)
        assert error.value.code == (0 if arguments == ["--help"] else 2)


def test_exact_count_boundaries_and_oversized_populations():
    raw = request()
    raw.pop("slope_bounds")
    raw["calibration"] = []
    raw["observations"] = [{"position": "0", "output": ["0", "1"]}] * 32
    assert analyze(raw)["analysis"]["status"] == "compatible"
    raw["observations"].append(copy.deepcopy(raw["observations"][0]))
    with pytest.raises(ValueError, match="1-32"):
        analyze(raw)
    raw = request()
    raw["calibration"] = [{"input": "0", "output": ["0", "0"]}] * 128
    assert analyze(raw)["analysis"]["status"] == "compatible"
    raw["calibration"].append(copy.deepcopy(raw["calibration"][0]))
    with pytest.raises(ValueError, match="0-128"):
        analyze(raw)
