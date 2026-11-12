"""Local CLI input, scientific outcome and provenance contracts; no photo or network IO."""

import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from scripts import corner_feasibility as cli

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "corner_feasibility.py"


def config(**changes):
    """An explicit broad level observation makes a cheap, valid compatible model."""
    result = {
        "format": "pictures-to-cad-corner-feasibility",
        "version": 1,
        "coordinate_unit": "px",
        "points": [["0", "0"]],
        "blur_sigma": ["1", "1"],
        "level_intervals": [["0", "1"]],
        "radius_domain": ["0", "4"],
        "radius_resolution": "0.1",
        "max_boxes": 1,
        "cells": 1,
    }
    result.update(changes)
    return result


def write_input(folder, raw=None):
    path = folder / "input.json"
    path.write_text(json.dumps(config() if raw is None else raw), encoding="utf-8")
    return path


@pytest.mark.parametrize("arguments", [[], ["--demo", "model.json"]])
def test_input_source_is_explicit_and_mutually_exclusive(arguments, capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err


def test_demo_runs_from_an_unrelated_directory_and_writes_only_json_to_stdout(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--demo"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    report = json.loads(completed.stdout)
    assert report["format"] == "pictures-to-cad-corner-feasibility-result"
    assert report["coordinate_unit"] == "px"
    # A sharp quadrant's apex has exact probability 1/4; radius zero cannot be excluded.
    assert any(Decimal(lo) <= 0 <= Decimal(hi) for lo, hi in report["outer"])
    assert report["coverage_complete"] is True
    assert "Synthetic sharp-quadrant" in completed.stderr
    assert "not accuracy" in completed.stderr and "supplied prior" in completed.stderr
    expected = (json.dumps(cli.DEMO, indent=2) + "\n").encode("utf-8")
    assert report["provenance"]["input_mode"] == "demo"
    assert report["provenance"]["input_sha256"] == hashlib.sha256(expected).hexdigest()
    assert report["input"] == cli.DEMO
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({}, "conditional_compatible"),
        ({"level_intervals": [["0.99", "1"]]}, "conditional_incompatible"),
        ({"level_intervals": [["0.24", "0.26"]]}, "unknown"),
    ],
)
def test_valid_scientific_outcomes_all_exit_successfully(changes, status, tmp_path, capsys):
    path = write_input(tmp_path, config(**changes))
    assert cli.main([str(path)]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["input"] == config(**changes)
    assert report["status"] == status
    assert captured.err == ""
    assert list(tmp_path.iterdir()) == [path]
    if status == "unknown":
        assert report["budget_exhausted"] is True
        assert report["unknown"] and report["outer"]
    elif status == "conditional_incompatible":
        assert report["outer"] == []


def test_saved_result_equals_stdout_and_hashes_exact_input_and_current_sources(tmp_path, capsys):
    path = tmp_path / "input.json"
    # The hash must bind the supplied bytes, including CRLF and noncanonical spacing.
    raw = (json.dumps(config(radius_resolution="0.10000000000000000000000000000000000001"),
                      indent=3) + "\r\n").encode("utf-8")
    path.write_bytes(raw)
    output = tmp_path / "result.json"
    assert cli.main([str(path), "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert output.read_bytes() == captured.out.encode("utf-8")
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["input"] == json.loads(raw)
    assert report["input"]["radius_resolution"] == "0.10000000000000000000000000000000000001"
    provenance = report["provenance"]
    assert provenance["input_mode"] == "file"
    assert provenance["input_sha256"] == hashlib.sha256(raw).hexdigest()
    names = {
        "backend/corner_feasibility.py", "backend/decimal_bounds.py",
        "scripts/corner_feasibility.py",
    }
    assert set(provenance["source_sha256"]) == names
    for name in names:
        assert provenance["source_sha256"][name] == hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    revision = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert provenance["git"]["revision"] == revision
    assert type(provenance["git"]["worktree_dirty"]) is bool
    assert type(provenance["git"]["source_dirty"]) is bool


def test_decimal_level_precision_is_preserved_through_the_cli(tmp_path, capsys):
    # At r=0 the independent sharp quadrant has exact probability .25 at its apex.
    # The lower target is strictly larger, although binary64 would round it to .25.
    path = write_input(tmp_path, config(
        radius_domain=["0", "0"],
        level_intervals=[["0.25000000000000000000000000000000000001", "0.26"]],
    ))
    assert cli.main([str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "conditional_incompatible"
    assert report["outer"] == []
    assert report["input"]["level_intervals"] == [
        ["0.25000000000000000000000000000000000001", "0.26"]
    ]


def test_the_128_kib_input_boundary_is_inclusive(tmp_path, capsys):
    path = write_input(tmp_path)
    raw = path.read_bytes()
    path.write_bytes(raw + b" " * (128 * 1024 - len(raw)))
    assert cli.main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "conditional_compatible"


@pytest.mark.parametrize("same_as_input", [False, True])
def test_output_never_overwrites_an_existing_file(same_as_input, tmp_path, capsys):
    path = write_input(tmp_path)
    output = path if same_as_input else tmp_path / "result.json"
    if not same_as_input:
        output.write_bytes(b"keep this existing result\n")
    before = output.read_bytes()
    assert cli.main([str(path), "--output", str(output)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "output already exists" in captured.err
    assert output.read_bytes() == before


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"{broken", "Expecting property name"),
        (b"\xff", "utf-8"),
        (b'{"version":1,"version":1}', "duplicate JSON key"),
        (b'{"points":[["0","0"]],"extra":{"x":1,"x":2}}', "duplicate JSON key"),
        (b'{"x":NaN}', "not a finite JSON value"),
        (b'{"x":Infinity}', "not a finite JSON value"),
        (b'{"x":-Infinity}', "not a finite JSON value"),
        (b"[" * 20000 + b"0" + b"]" * 20000, "nesting is too deep"),
        (b" " * (128 * 1024 + 1), "128 KiB"),
    ],
)
def test_invalid_text_is_actionable_and_creates_no_result(content, message, tmp_path, capsys):
    path = tmp_path / "input.json"
    path.write_bytes(content)
    output = tmp_path / "result.json"
    assert cli.main([str(path), "--output", str(output)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and message in captured.err
    assert "Traceback" not in captured.err
    assert not output.exists()


@pytest.mark.parametrize("change", ["missing_levels", "numeric_coordinate", "numeric_level"])
def test_input_validation_does_not_invent_physical_bounds(change, tmp_path, capsys):
    raw = config()
    if change == "missing_levels":
        del raw["level_intervals"]
    elif change == "numeric_coordinate":
        raw["points"][0][0] = 0
    else:
        raw["level_intervals"][0][0] = 0.0
    path = write_input(tmp_path, raw)
    assert cli.main([str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert ("missing" if change == "missing_levels" else "decimal string") in captured.err


def test_missing_input_and_unwritable_output_are_reported_without_tracebacks(tmp_path, capsys):
    assert cli.main([str(tmp_path / "missing.json")]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "No such file" in captured.err
    path = write_input(tmp_path)
    assert cli.main([str(path), "--output", str(tmp_path / "missing" / "out.json")]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "No such file" in captured.err


def test_missing_git_metadata_is_explicit_and_does_not_invalidate_the_analysis(
    tmp_path, capsys, monkeypatch,
):
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(cli.subprocess, "run", unavailable)
    path = write_input(tmp_path)
    assert cli.main([str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    metadata = report["provenance"]["git"]
    assert metadata["revision"] is None
    assert metadata["worktree_dirty"] is None and metadata["source_dirty"] is None
    assert "could not be read" in metadata["unavailable_reason"]
    assert report["provenance"]["source_sha256"]


def test_source_changed_during_analysis_cannot_emit_a_misbound_report(
    tmp_path, capsys, monkeypatch,
):
    hashes = iter([{"core": "before"}, {"core": "after"}])
    monkeypatch.setattr(cli, "_source_hashes", lambda: next(hashes))
    path = write_input(tmp_path)
    output = tmp_path / "result.json"
    assert cli.main([str(path), "--output", str(output)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "source changed" in captured.err
    assert not output.exists()
