"""Build diagnostics are bounded, path-free and stable for a running backend."""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from backend import build_info

IDENTITY = {"revision": "a" * 40, "dirty": False, "source_sha256": "b" * 64}


def manifest_path(root):
    path = root / "frontend" / "dist" / "build-info.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_manifest(root, **changes):
    payload = {"schema": 1, **IDENTITY, **changes}
    manifest_path(root).write_text(json.dumps(payload))
    return payload


def source_tree(root):
    (root / "backend").mkdir()
    (root / "backend" / "app.py").write_bytes(b"# app\n")
    (root / "backend" / "nested").mkdir()
    (root / "backend" / "nested" / "worker.py").write_bytes(b"# worker\n")
    (root / "pyproject.toml").write_bytes(b"[project]\n")
    return root


def test_source_hash_has_unambiguous_paths_lengths_and_version_domain(tmp_path):
    source_tree(tmp_path)
    digest = hashlib.sha256(b"picad-backend-inputs-v1\0")
    for name in ("backend/app.py", "backend/nested/worker.py", "pyproject.toml"):
        path = name.encode()
        data = (tmp_path / name).read_bytes()
        digest.update(len(path).to_bytes(8, "big") + path + len(data).to_bytes(8, "big") + data)
    assert build_info.source_fingerprint(tmp_path) == digest.hexdigest()
    (tmp_path / "backend" / "app.py").rename(tmp_path / "backend" / "renamed.py")
    assert build_info.source_fingerprint(tmp_path) != digest.hexdigest()


def test_source_hash_excludes_private_data_and_symlinks(tmp_path):
    source_tree(tmp_path)
    initial = build_info.source_fingerprint(tmp_path)
    (tmp_path / "backend" / "private.json").write_text("Private path and model metadata")
    (tmp_path / "photos").mkdir()
    private = tmp_path / "photos" / "private.py"
    private.write_text("private source outside the backend")
    (tmp_path / "backend" / "linked.py").symlink_to(private)
    (tmp_path / "backend" / "linked-directory").symlink_to(
        tmp_path / "photos", target_is_directory=True
    )
    assert build_info.source_fingerprint(tmp_path) == initial
    (tmp_path / "requirements.txt").write_text("example==1\n")
    changed = build_info.source_fingerprint(tmp_path)
    assert changed and changed != initial
    (tmp_path / "requirements.txt").unlink()
    assert build_info.source_fingerprint(tmp_path) == initial


def test_missing_or_oversized_source_is_unknown(tmp_path, monkeypatch):
    assert build_info.source_fingerprint(tmp_path) is None
    source_tree(tmp_path)
    monkeypatch.setattr(build_info, "MAX_SOURCE_FILE_BYTES", 2)
    assert build_info.source_fingerprint(tmp_path) is None


def test_no_git_keeps_a_source_hash_without_disclosing_paths(tmp_path, monkeypatch):
    source_tree(tmp_path)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: None)
    identity = build_info.capture_backend_identity(tmp_path)
    assert identity["revision"] is None and identity["dirty"] is None
    assert build_info.SOURCE_HASH.fullmatch(identity["source_sha256"])
    assert str(tmp_path) not in json.dumps(identity)


def test_git_uses_one_deadline_no_optional_locks_and_no_returned_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/example/git")
    times = iter([100, 100.1, 100.4])
    monkeypatch.setattr(build_info.time, "monotonic", lambda: next(times))
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout="a" * 40 + "\n" if len(calls) == 1 else "?? private/file\n")

    monkeypatch.setattr(build_info.subprocess, "run", run)
    identity = build_info.git_identity(tmp_path)
    assert identity == {"revision": "a" * 40, "dirty": True}
    assert len(calls) == 2
    assert calls[0][1]["timeout"] == pytest.approx(0.65)
    assert calls[1][1]["timeout"] == pytest.approx(0.35)
    assert all(options["env"]["GIT_OPTIONAL_LOCKS"] == "0" for _, options in calls)
    assert all("core.fsmonitor=false" in command for command, _ in calls)
    assert "private" not in json.dumps(identity)
    assert str(tmp_path) not in json.dumps(identity)


def test_git_failure_or_timeout_is_optional(tmp_path, monkeypatch):
    monkeypatch.setattr(build_info.shutil, "which", lambda name: "/example/git")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            return SimpleNamespace(stdout="a" * 40)
        raise subprocess.TimeoutExpired("private-command", 0.1, stderr="private/path")

    monkeypatch.setattr(build_info.subprocess, "run", run)
    assert build_info.git_identity(tmp_path) == {"revision": "a" * 40, "dirty": None}

    def missing(command, **kwargs):
        raise OSError("private/path")

    monkeypatch.setattr(build_info.subprocess, "run", missing)
    assert build_info.git_identity(tmp_path) == {"revision": None, "dirty": None}


def test_startup_snapshot_is_stable_after_source_changes_and_returned_dict_edits(
    tmp_path, monkeypatch
):
    source_tree(tmp_path)
    copied = tmp_path / "backend" / "build_info.py"
    shutil.copyfile(build_info.__file__, copied)
    monkeypatch.setattr(build_info.shutil, "which", lambda name: None)
    spec = importlib.util.spec_from_file_location("isolated_build_info", copied)
    isolated = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isolated)
    captured = isolated.runtime_identity()["backend"]
    (tmp_path / "backend" / "app.py").write_text("# changed after startup\n")
    assert isolated.runtime_identity()["backend"] == captured
    assert isolated.capture_backend_identity(tmp_path)["source_sha256"] != captured["source_sha256"]
    captured["revision"] = "c" * 40
    assert isolated.runtime_identity()["backend"]["revision"] is None
    with pytest.raises(TypeError):
        isolated.BACKEND_STARTUP_IDENTITY["revision"] = "c" * 40


def test_valid_manifest_returns_only_identity_and_never_its_location(tmp_path):
    write_manifest(tmp_path)
    identity = build_info.read_interface_identity(tmp_path)
    assert identity == IDENTITY
    assert str(tmp_path) not in json.dumps(identity)
    write_manifest(tmp_path, revision=None, dirty=None, source_sha256=None)
    assert build_info.read_interface_identity(tmp_path) == {
        "revision": None,
        "dirty": None,
        "source_sha256": None,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"schema": 2},
        {"schema": True},
        {"revision": "private/path"},
        {"revision": "a" * 39},
        {"revision": 1},
        {"dirty": 1},
        {"dirty": "true"},
        {"source_sha256": "b" * 63},
        {"source_sha256": []},
        {"private": "raw private metadata"},
    ],
)
def test_unknown_or_malformed_manifest_is_unavailable(tmp_path, changes):
    write_manifest(tmp_path, **changes)
    assert build_info.read_interface_identity(tmp_path) is None


@pytest.mark.parametrize(
    "raw", [b"not json", b"[]", b"null", b"{}", b"\xff", b"[" * 1500 + b"]" * 1500]
)
def test_unreadable_or_incomplete_manifest_is_unavailable(tmp_path, raw):
    manifest_path(tmp_path).write_bytes(raw)
    assert build_info.read_interface_identity(tmp_path) is None


def test_absent_oversized_and_special_manifests_never_block(tmp_path):
    assert build_info.read_interface_identity(tmp_path) is None
    path = manifest_path(tmp_path)
    path.write_bytes(b" " * (build_info.MAX_MANIFEST_BYTES + 1))
    assert build_info.read_interface_identity(tmp_path) is None
    path.unlink()
    private = tmp_path / "private.json"
    private.write_text(json.dumps({"schema": 1, **IDENTITY}))
    path.symlink_to(private)
    assert build_info.read_interface_identity(tmp_path) is None
    path.unlink()
    if hasattr(os, "mkfifo"):
        os.mkfifo(path)
        assert build_info.read_interface_identity(tmp_path) is None


@pytest.mark.parametrize("structured", [False, True])
def test_doctor_reports_identity_without_changing_readiness_or_exposing_paths(
    monkeypatch, capsys, structured
):
    from scripts import doctor

    report = {"ready": True, "checks": [], "identity": {"backend": IDENTITY, "interface": None}}
    calls = []

    def summarize(**kwargs):
        calls.append(kwargs)
        return report

    monkeypatch.setattr(doctor, "summarize_runtime", summarize)
    monkeypatch.setattr(
        doctor.sys, "argv", ["doctor.py", "--skip-ai", *(["--json"] if structured else [])]
    )
    assert doctor.main() == 0
    output = capsys.readouterr().out
    assert calls == [{"include_development": True, "check_ai": False}]
    if structured:
        assert json.loads(output) == report
    else:
        assert "App setup is ready." in output
        assert (
            "Backend startup source snapshot: aaaaaaaaaaaa; clean tree; source bbbbbbbbbbbb"
            in output
        )
        assert "Built interface snapshot: unavailable" in output
        assert "not every byte loaded by Python" in output
