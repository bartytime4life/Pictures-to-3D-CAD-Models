"""Real rectangle CLI contracts; no photograph, server or physical calibration."""

import hashlib
import json
import subprocess
import sys

import pytest

from scripts import response_rectangles as cli


def request(**changes):
    result = {
        "version": 1,
        "units": {"input": "normalized exposure", "output": "normalized source level"},
        "rectangles": [
            {"input": ["0", "0"], "output": ["0", "0"]},
            {"input": ["1", "1"], "output": ["1", "1"]},
        ],
        "slope_bounds": ["0", "2"],
        "queries": ["0.25", "0.5", "0.75"],
    }
    result.update(changes)
    return result


def analyze(raw):
    return cli.analyze_bytes(json.dumps(raw).encode())


def test_exact_envelopes_units_input_bytes_and_all_sources_are_bound():
    raw = request(units={"input": "normalized exposure", "output": "μm of declared output"})
    data = json.dumps(raw, indent=3, ensure_ascii=False).encode()
    report = cli.analyze_bytes(data)
    assert report["format"] == "pictures-to-cad-response-rectangles-result"
    assert report["version"] == 1
    assert report["input"] == raw and report["units"] == raw["units"]
    assert report["queries"] == [
        {"input": "1/4", "output": ["0", "1/2"]},
        {"input": "1/2", "output": ["0", "1"]},
        {"input": "3/4", "output": ["1/2", "1"]},
    ]
    assert report["unbounded_semantics"] == {
        "lower_null": "negative_infinity",
        "upper_null": "positive_infinity",
    }
    provenance = report["provenance"]
    assert provenance["input_sha256"] == hashlib.sha256(data).hexdigest()
    assert {
        "backend/response_rectangles.py",
        "backend/response_calibration.py",
        "scripts/response_rectangles.py",
    } <= provenance["source_sha256"].keys()
    for name, digest in provenance["source_sha256"].items():
        assert hashlib.sha256((cli.ROOT / name).read_bytes()).hexdigest() == digest


def test_omitted_options_keep_raw_request_and_apply_some_input_defaults():
    raw = request()
    for key in ("slope_bounds", "queries"):
        del raw[key]
    report = analyze(raw)
    assert report["input"] == raw
    assert report["calibration"]["input_mode"] == "some"
    assert report["calibration"]["slope_bounds"] == ["0", None]
    assert report["queries"] == []


def test_true_half_infinite_and_doubly_unbounded_queries_are_not_finite_guesses():
    report = analyze(
        request(
            rectangles=[{"input": ["0", "1"], "output": ["0", "0"]}],
            slope_bounds=["0", None],
            queries=["0", "0.5", "1"],
        )
    )
    assert report["calibration"]["status"] == "compatible"
    assert report["queries"] == [
        {"input": "0", "output": [None, "0"]},
        {"input": "1/2", "output": [None, None]},
        {"input": "1", "output": ["0", None]},
    ]
    # A serialized finite PL witness coexists with honestly unbounded envelopes.
    assert all(isinstance(p["output"], str) for p in report["calibration"]["witness"])
    assert "Infinity" not in json.dumps(report, allow_nan=False)


def test_finite_slope_changes_the_unbounded_midpoint_to_exact_finite_bounds():
    report = analyze(
        request(
            rectangles=[{"input": ["0", "1"], "output": ["0", "0"]}],
            slope_bounds=["0", "2"],
            queries=["0.5"],
        )
    )
    assert report["queries"] == [{"input": "1/2", "output": ["-1", "1"]}]


def test_some_input_and_one_curve_for_all_inputs_have_distinct_conclusions():
    raw = request(
        rectangles=[{"input": ["0", "1"], "output": ["0", "0"]}],
        slope_bounds=["1", "1"],
        queries=["0.5"],
    )
    some = analyze({**raw, "input_mode": "some"})
    robust = analyze({**raw, "input_mode": "all"})
    assert some["calibration"]["status"] == "compatible"
    assert some["queries"] == [{"input": "1/2", "output": ["-1/2", "1/2"]}]
    assert robust["calibration"]["status"] == "incompatible"
    proof = robust["calibration"]["contradiction"]
    assert proof["lower_source"] == proof["upper_source"] == 0
    assert proof["lower_endpoint"] == "left" and proof["upper_endpoint"] == "right"
    assert robust["queries"] == [{"input": "1/2", "unavailable": "incompatible_calibration"}]


@pytest.mark.parametrize("mode", ["some", "all"])
def test_duplicate_nondegenerate_rectangles_preserve_endpoints_and_sources(mode):
    box = {"input": ["0", "1"], "output": ["0", "1"]}
    report = analyze(request(rectangles=[box, box], input_mode=mode, queries=["0", "1"]))
    calibration = report["calibration"]
    assert calibration["status"] == "compatible"
    assert calibration["rectangles"] == [box, box]
    assert [group["input"] for group in calibration["source_groups"]] == ["0", "1"]
    assert all(group["source_indices"] == [0, 1] for group in calibration["source_groups"])
    assert [assignment["source_index"] for assignment in calibration["assignments"]] == [0, 1]


def test_incompatible_queries_remain_unavailable_but_still_require_valid_syntax():
    raw = request(
        rectangles=[
            {"input": ["0", "0"], "output": ["1", "1"]},
            {"input": ["1", "1"], "output": ["0", "0"]},
        ],
        queries=["-1", "0.5", "2"],
    )
    report = analyze(raw)
    assert report["calibration"]["status"] == "incompatible"
    assert report["calibration"]["contradiction"] is not None
    assert report["calibration"]["nodes"] == report["calibration"]["witness"] == []
    assert all(q["unavailable"] == "incompatible_calibration" for q in report["queries"])
    for query in ("NaN", "1/2", True, 0.5):
        with pytest.raises((TypeError, ValueError)):
            analyze({**raw, "queries": [query]})


@pytest.mark.parametrize(
    "change",
    [
        {"version": True},
        {"version": 1.0},
        {"version": 2},
        {"unknown": "field"},
        {"units": {"input": "x"}},
        {"units": {"input": "x", "output": "y", "extra": "z"}},
        {"units": {"input": " ", "output": "y"}},
        {"units": {"input": "x\n", "output": "y"}},
        {"units": {"input": "x" * 81, "output": "y"}},
        {"units": {"input": 1, "output": "y"}},
        {"rectangles": []},
        {"rectangles": {}},
        {"rectangles": [None]},
        {"rectangles": [{"input": ["0", "1"], "output": ["0", "1"], "extra": 1}]},
        {"rectangles": [{"input": ["0"], "output": ["0", "1"]}]},
        {"rectangles": [{"input": "0", "output": ["0", "1"]}]},
        {"rectangles": [{"input": ["0", "1"], "output": None}]},
        {"rectangles": [{"input": ["1", "0"], "output": ["0", "1"]}]},
        {"rectangles": [{"input": ["0", "1"], "output": ["1", "0"]}]},
        {"rectangles": [{"input": [0, "1"], "output": ["0", "1"]}]},
        {"rectangles": [{"input": ["0", 0.5], "output": ["0", "1"]}]},
        {"rectangles": [{"input": ["0", "1"], "output": [False, "1"]}]},
        {"rectangles": [{"input": ["0", "1"], "output": ["0", 1]}]},
        {"rectangles": [{"input": ["1/2", "1"], "output": ["0", "1"]}]},
        {"rectangles": [{"input": ["NaN", "1"], "output": ["0", "1"]}]},
        {"input_mode": "robust"},
        {"input_mode": "Some"},
        {"input_mode": None},
        {"input_mode": True},
        {"slope_bounds": ["0"]},
        {"slope_bounds": [0, None]},
        {"slope_bounds": [None, "1"]},
        {"slope_bounds": ["0", 1.0]},
        {"slope_bounds": ["-1", None]},
        {"slope_bounds": ["2", "1"]},
        {"queries": "0.5"},
        {"queries": [True]},
        {"queries": [0.5]},
        {"queries": ["1/2"]},
        {"queries": ["2"]},
        {"queries": ["0"] * 257},
    ],
)
def test_invalid_schema_numbers_and_extrapolation_are_refused(change):
    with pytest.raises((TypeError, ValueError)):
        analyze(request(**change))


@pytest.mark.parametrize("raw", [[], None, "request", {"version": 1, "units": {}}])
def test_missing_fields_and_nonobject_requests_are_refused(raw):
    with pytest.raises((TypeError, ValueError)):
        analyze(raw)


@pytest.mark.parametrize(
    "data",
    [
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
        b"\xff",
        b"",
    ],
)
def test_duplicate_keys_nonfinite_json_and_malformed_bytes_are_refused(data):
    with pytest.raises((TypeError, ValueError)):
        cli.analyze_bytes(data)


@pytest.mark.parametrize(
    "original,duplicated",
    [
        ('"version": 1', '"version": 1, "version": 1'),
        (
            '"input": "normalized exposure"',
            '"input": "normalized exposure", "input": "normalized exposure"',
        ),
        ('"input": ["0", "0"]', '"input": ["0", "0"], "input": ["0", "0"]'),
    ],
)
def test_duplicate_keys_in_otherwise_valid_top_level_units_and_rectangle_are_refused(
    original, duplicated
):
    data = json.dumps(request())
    assert original in data
    assert cli.analyze_bytes(data.encode())["calibration"]["status"] == "compatible"
    with pytest.raises(ValueError, match="duplicate JSON key"):
        cli.analyze_bytes(data.replace(original, duplicated, 1).encode())


def test_closed_input_byte_limit_and_original_whitespace_binding():
    data = json.dumps(request()).encode()
    data += b" " * (cli.MAX_INPUT_BYTES - len(data))
    report = cli.analyze_bytes(data)
    assert len(data) == 512 * 1024
    assert report["provenance"]["input_sha256"] == hashlib.sha256(data).hexdigest()
    with pytest.raises(ValueError, match="512 KiB"):
        cli.analyze_bytes(data + b" ")


def test_rectangle_and_query_population_boundaries():
    box = {"input": ["0", "1"], "output": ["0", "1"]}
    report = analyze(request(rectangles=[box] * 512, queries=["0.5"] * 256))
    assert len(report["calibration"]["rectangles"]) == 512
    assert len(report["calibration"]["assignments"]) == 512
    assert len(report["queries"]) == 256
    with pytest.raises(ValueError):
        analyze(request(rectangles=[box] * 513))


@pytest.mark.parametrize("changed_on_call", [2, 3])
def test_source_change_during_import_or_analysis_refuses_a_conclusion(monkeypatch, changed_on_call):
    real = cli.source_hashes()
    calls = []

    def hashes():
        calls.append(1)
        return real if len(calls) < changed_on_call else {**real, "changed": "source"}

    monkeypatch.setattr(cli, "source_hashes", hashes)
    with pytest.raises(ValueError, match="source changed"):
        analyze(request())


@pytest.mark.parametrize("status", ["compatible", "incompatible"])
def test_real_cli_from_unrelated_directory_stdout_output_and_exit_status(tmp_path, status):
    raw = request()
    if status == "incompatible":
        raw = request(
            rectangles=[{"input": ["0", "1"], "output": ["0", "0"]}],
            input_mode="all",
            slope_bounds=["1", "1"],
        )
    source, output = tmp_path / "input.json", tmp_path / "result.json"
    source.write_text(json.dumps(raw))
    args = [
        sys.executable,
        str(cli.ROOT / "scripts/response_rectangles.py"),
        str(source),
        "--output",
        str(output),
    ]
    done = subprocess.run(
        args, cwd=tmp_path, capture_output=True, text=True, timeout=15, check=False
    )
    assert done.returncode == 0 and done.stderr == ""
    assert done.stdout == output.read_text()
    assert json.loads(done.stdout)["calibration"]["status"] == status
    previous = output.read_bytes()
    again = subprocess.run(
        args, cwd=tmp_path, capture_output=True, text=True, timeout=15, check=False
    )
    assert again.returncode == 2 and again.stdout == "" and output.read_bytes() == previous


def test_help_and_output_refusal_do_not_analyze(monkeypatch, tmp_path):
    def unexpected(_):
        raise AssertionError("analysis executed before argument/output refusal")

    monkeypatch.setattr(cli, "analyze_bytes", unexpected)
    with pytest.raises(SystemExit) as help_exit:
        cli.main(["--help"])
    assert help_exit.value.code == 0
    with pytest.raises(SystemExit) as missing_exit:
        cli.main([])
    assert missing_exit.value.code == 2
    output = tmp_path / "existing.json"
    output.write_bytes(b"preserve original\n")
    with pytest.raises(SystemExit) as existing_exit:
        cli.main([str(tmp_path / "missing-input.json"), "--output", str(output)])
    assert existing_exit.value.code == 2 and output.read_bytes() == b"preserve original\n"
    dangling = tmp_path / "dangling.json"
    dangling.symlink_to(tmp_path / "missing-target.json")
    with pytest.raises(SystemExit) as symlink_exit:
        cli.main([str(tmp_path / "missing-input.json"), "--output", str(dangling)])
    assert symlink_exit.value.code == 2 and dangling.is_symlink()
    assert not (tmp_path / "missing-target.json").exists()


def test_invalid_input_and_resource_refusal_create_no_output(tmp_path, monkeypatch):
    source, output = tmp_path / "input.json", tmp_path / "never-created.json"
    source.write_text(json.dumps(request(queries=["-1"])))
    with pytest.raises(SystemExit) as invalid:
        cli.main([str(source), "--output", str(output)])
    assert invalid.value.code == 2 and not output.exists()
    source.write_text(json.dumps(request()))
    from backend import response_rectangles

    def exhausted(*args, **kwargs):
        raise ValueError("injected exact arithmetic work limit")

    monkeypatch.setattr(response_rectangles, "calibrate_rectangles", exhausted)
    with pytest.raises(SystemExit) as resource:
        cli.main([str(source), "--output", str(output)])
    assert resource.value.code == 2 and not output.exists()


def test_source_change_main_refusal_creates_no_output(tmp_path, monkeypatch):
    source, output = tmp_path / "input.json", tmp_path / "never-created.json"
    source.write_text(json.dumps(request()))
    real = cli.source_hashes()
    calls = []

    def hashes():
        calls.append(1)
        return real if len(calls) < 3 else {**real, "changed": "source"}

    monkeypatch.setattr(cli, "source_hashes", hashes)
    with pytest.raises(SystemExit) as error:
        cli.main([str(source), "--output", str(output)])
    assert error.value.code == 2 and not output.exists()
