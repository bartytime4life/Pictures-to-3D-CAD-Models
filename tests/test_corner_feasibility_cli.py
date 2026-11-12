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


def blur_config(**changes):
    """Explicit joint radius/blur domains, with no inferred physical input bounds."""
    raw = config()
    del raw["blur_sigma"]
    raw.update({
        "version": 2,
        "blur_sigma_intervals": [["1", "2"], ["1", "2"]],
        "blur_resolution": ["0.1", "0.1"],
    })
    raw.update(changes)
    return raw


def aperture_config(**changes):
    """Known uniform product apertures, with a point aperture as a cheap control."""
    raw = blur_config()
    del raw["points"]
    raw.update({
        "version": 3,
        "pixel_apertures": [[["0", "0"], ["0", "0"]]],
    })
    raw.update(changes)
    return raw


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
    assert report["version"] == 1
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


@pytest.mark.parametrize("version", [1, 2, 3])
def test_saved_result_equals_stdout_and_hashes_exact_input_and_current_sources(
    version, tmp_path, capsys,
):
    path = tmp_path / "input.json"
    # The hash must bind the supplied bytes, including CRLF and noncanonical spacing.
    model = {1: config, 2: blur_config, 3: aperture_config}[version]
    supplied = model(radius_resolution="0.10000000000000000000000000000000000001")
    if version == 3:
        supplied["pixel_apertures"] = [
            [["0.10000000000000000000000000000000000001", "0.2"], ["0", "0"]]
        ]
    raw = (json.dumps(supplied, indent=3) + "\r\n").encode("utf-8")
    path.write_bytes(raw)
    output = tmp_path / "result.json"
    assert cli.main([str(path), "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert output.read_bytes() == captured.out.encode("utf-8")
    assert captured.err == ""
    report = json.loads(captured.out)
    assert report["input"] == json.loads(raw)
    assert report["input"]["radius_resolution"] == "0.10000000000000000000000000000000000001"
    if version == 3:
        assert report["input"]["pixel_apertures"][0][0][0] == (
            "0.10000000000000000000000000000000000001"
        )
    provenance = report["provenance"]
    assert provenance["input_mode"] == "file"
    assert provenance["input_sha256"] == hashlib.sha256(raw).hexdigest()
    names = {
        "backend/corner_feasibility.py", "backend/decimal_bounds.py",
        "backend/corner_blur_domains.py", "backend/corner_pixel_apertures.py",
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


@pytest.mark.parametrize("version", [1, 2, 3])
@pytest.mark.parametrize("same_as_input", [False, True])
def test_output_never_overwrites_an_existing_file(version, same_as_input, tmp_path, capsys):
    model = {1: config, 2: blur_config, 3: aperture_config}[version]
    path = write_input(tmp_path, model())
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


@pytest.mark.parametrize(
    ("levels", "status"),
    [
        ([["0", "1"]], "conditional_compatible"),
        ([["0.99", "1"]], "conditional_incompatible"),
        ([["0.24", "0.26"]], "unknown"),
    ],
)
def test_version_two_files_keep_joint_boxes_separate_from_radius_projections(
    levels, status, tmp_path, capsys,
):
    raw = blur_config(level_intervals=levels)
    path = write_input(tmp_path, raw)
    assert cli.main([str(path)]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == ""
    assert report["version"] == 2 and report["status"] == status
    assert report["input"] == raw
    assert report["parameter_order"] == ["radius", "sigma_x", "sigma_y"]
    assert set(report["parameter_boxes"]) == {"accepted", "unknown", "excluded"}
    domain = [["0", "4"], ["1", "2"], ["1", "2"]]
    assert report["parameter_domain"] == domain
    for boxes in report["parameter_boxes"].values():
        for box in boxes:
            assert len(box) == 3
            for bounds, limits in zip(box, domain):
                assert len(bounds) == 2 and all(isinstance(v, str) for v in bounds)
                assert Decimal(limits[0]) <= Decimal(bounds[0]) <= Decimal(bounds[1]) <= Decimal(limits[1])
    assert "excluded" not in report
    if status == "conditional_incompatible":
        assert report["inner"] == report["outer"] == []
        assert report["parameter_boxes"]["excluded"]
    elif status == "unknown":
        assert report["inner"] == [] and report["outer"] == [["0", "4"]]
        assert report["budget_exhausted"] is True
        assert report["parameter_boxes"]["unknown"]
    else:
        assert report["inner"] == report["outer"] == [["0", "4"]]
        assert report["parameter_boxes"]["accepted"]
    provenance = report["provenance"]
    assert provenance["input_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert provenance["source_sha256"]["backend/corner_blur_domains.py"] == hashlib.sha256(
        (ROOT / "backend/corner_blur_domains.py").read_bytes()
    ).hexdigest()


@pytest.mark.parametrize("change", ["missing_domains", "missing_resolution", "wrong_format"])
def test_version_two_requires_explicit_blur_bounds_and_matching_format(change, tmp_path, capsys):
    raw = blur_config()
    if change == "missing_domains":
        del raw["blur_sigma_intervals"]
    elif change == "missing_resolution":
        del raw["blur_resolution"]
    else:
        raw["format"] = "another-analysis"
    path = write_input(tmp_path, raw)
    assert cli.main([str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "Traceback" not in captured.err
    assert ("format" if change == "wrong_format" else "missing") in captured.err


@pytest.mark.parametrize("version", [True, False, 2.0, "2", 3])
def test_only_exact_integer_version_two_dispatches_to_the_blur_analyzer(
    version, tmp_path, capsys, monkeypatch,
):
    from backend import corner_blur_domains

    def wrong_dispatch(raw):
        pytest.fail("only exact integer version 2 may dispatch to the blur analyzer")

    monkeypatch.setattr(corner_blur_domains, "analyze", wrong_dispatch)
    path = write_input(tmp_path, blur_config(version=version))
    assert cli.main([str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "Traceback" not in captured.err


def test_help_explains_that_one_blur_choice_must_explain_every_observation(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["--help"])
    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert "one shared blur choice" in help_text and "cannot vary per point" in help_text
    assert "known uniform product pixel apertures" in help_text
    assert "not arbitrary position uncertainty or total flux" in help_text


@pytest.mark.parametrize("levels", [[["0", "1"]], [["0.99", "1"]], [["0.24", "0.26"]]])
def test_zero_width_aperture_cli_retains_point_observation_outcomes(levels, tmp_path, capsys):
    path = write_input(tmp_path, aperture_config(level_intervals=levels))
    assert cli.main([str(path)]) == 0
    captured = capsys.readouterr()
    aperture = json.loads(captured.out)
    assert captured.err == "" and aperture["version"] == 3
    assert aperture["input"]["pixel_apertures"] == [[["0", "0"], ["0", "0"]]]
    path = write_input(tmp_path, blur_config(level_intervals=levels))
    assert cli.main([str(path)]) == 0
    point = json.loads(capsys.readouterr().out)
    for field in ("status", "inner", "outer", "parameter_order", "parameter_domain",
                  "parameter_boxes", "coverage_complete", "classification_complete"):
        assert aperture[field] == point[field]
    assert "excluded" not in aperture


def test_uniform_aperture_guide_input_preserves_the_sharp_radius_without_point_substitution(
    tmp_path, capsys,
):
    raw = aperture_config(
        pixel_apertures=[[["0", "1"], ["0", "1"]]],
        blur_sigma_intervals=[["1", "1"], ["1", "1"]],
        level_intervals=[["0.4683", "0.4685"]],
        radius_domain=["0", "2"], radius_resolution="0.0625", max_boxes=64, cells=16,
    )
    path = write_input(tmp_path, raw)
    assert cli.main([str(path)]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == "" and report["version"] == 3
    assert report["input"] == raw
    # For a sharp quadrant this known aperture's normalized mean is in the supplied band.
    assert any(Decimal(lo) <= 0 <= Decimal(hi) for lo, hi in report["outer"])
    assert report["coverage_complete"] is True
    assumptions = report["assumptions"]
    assert "known axis-aligned uniform PRODUCT" in assumptions["pixel_apertures"]
    assert "normalized mean, not total flux" in assumptions["measurement"]
    assert "one common blur pair" in assumptions["measurement"]
    assert "Keys" in assumptions["not_modelled"]
    assert "aperture bounds" in assumptions["not_inferred"]
    # Its center point has a different level and cannot stand in for the uniform mean.
    point = blur_config(
        points=[["0.5", "0.5"]], blur_sigma_intervals=[["1", "1"], ["1", "1"]],
        level_intervals=raw["level_intervals"], radius_domain=["0", "0"],
    )
    path = write_input(tmp_path, point)
    assert cli.main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "conditional_incompatible"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing_apertures", "missing"),
        ("points_instead", "pixel_apertures"),
        ("numeric_coordinate", "decimal string"),
        ("reversed_interval", "lower"),
        ("wrong_format", "format"),
        ("unknown_response", "unknown"),
    ],
)
def test_version_three_refuses_implicit_or_unsupported_aperture_inputs(
    change, message, tmp_path, capsys,
):
    raw = aperture_config()
    if change == "missing_apertures":
        del raw["pixel_apertures"]
    elif change == "points_instead":
        del raw["pixel_apertures"]
        raw["points"] = [["0", "0"]]
    elif change == "numeric_coordinate":
        raw["pixel_apertures"][0][0][0] = 0
    elif change == "reversed_interval":
        raw["pixel_apertures"][0][0] = ["1", "0"]
    elif change == "wrong_format":
        raw["format"] = "another-analysis"
    else:
        raw["response_weights"] = ["1", "-1"]
    path = write_input(tmp_path, raw)
    output = tmp_path / "result.json"
    assert cli.main([str(path), "--output", str(output)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and message in captured.err and "Traceback" not in captured.err
    assert not output.exists()


@pytest.mark.parametrize("version", [True, False, 3.0, "3", 4])
def test_only_exact_integer_version_three_dispatches_to_the_pixel_analyzer(
    version, tmp_path, capsys, monkeypatch,
):
    from backend import corner_pixel_apertures

    def wrong_dispatch(raw):
        pytest.fail("only exact integer version 3 may dispatch to the pixel analyzer")

    monkeypatch.setattr(corner_pixel_apertures, "analyze", wrong_dispatch)
    path = write_input(tmp_path, aperture_config(version=version))
    assert cli.main([str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "Traceback" not in captured.err


def test_dirty_pixel_source_is_reported_even_when_it_is_the_only_modified_file(
    tmp_path, monkeypatch,
):
    # Use a separate local repository: changes in the real checkout cannot mask a
    # forgotten provenance path, and no project source or existing Git state changes.
    source = tmp_path / "backend" / "corner_pixel_apertures.py"
    source.parent.mkdir()
    source.write_text("# temporary provenance control\n", encoding="utf-8")

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    git("init", "--quiet")
    git("add", "--", "backend/corner_pixel_apertures.py")
    git("-c", "core.hooksPath=/dev/null", "-c", "user.name=CLI provenance test",
        "-c", "user.email=cli-test@example.invalid", "-c", "commit.gpgSign=false",
        "commit", "--quiet", "-m", "Temporary source baseline")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    baseline = cli._git_metadata()
    assert baseline["revision"] == git("rev-parse", "HEAD")
    assert baseline["worktree_dirty"] is False and baseline["source_dirty"] is False
    source.write_text("# changed temporary provenance control\n", encoding="utf-8")
    changed = cli._git_metadata()
    assert changed["revision"] == baseline["revision"]
    assert changed["worktree_dirty"] is True and changed["source_dirty"] is True


def test_different_blur_choices_per_observation_cannot_make_a_joint_problem_compatible(
    tmp_path, capsys,
):
    # Each level band is feasible at the same coordinate under a different blur.
    # Jointly they are impossible: one shared blur gives one level at that coordinate.
    bands = [["0.70", "0.72"], ["0.47", "0.49"]]
    for sigma, band in zip(("1", "2"), bands):
        path = write_input(tmp_path, blur_config(
            points=[["1", "1"]], radius_domain=["0", "0"],
            blur_sigma_intervals=[[sigma, sigma], [sigma, sigma]],
            level_intervals=[band],
        ))
        assert cli.main([str(path)]) == 0
        assert json.loads(capsys.readouterr().out)["status"] == "conditional_compatible"
    path = write_input(tmp_path, blur_config(
        points=[["1", "1"], ["1", "1"]], radius_domain=["0", "0"],
        level_intervals=bands, max_boxes=127,
    ))
    assert cli.main([str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "conditional_incompatible" and report["outer"] == []
    assert report["parameter_boxes"]["excluded"]
    assert report["budget_exhausted"] is False


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
