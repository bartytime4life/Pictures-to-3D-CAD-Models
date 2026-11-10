"""The optional host launcher accepts generated jobs, never arbitrary commands."""

import asyncio
import hashlib
import json
import os
import threading
from types import SimpleNamespace
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend import app as api
from backend import slicers


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    job_id = "a" * 32
    directory = jobs / job_id
    directory.mkdir()
    (directory / "result.json").write_text("{}")
    (directory / "model.3mf").write_bytes(b"synthetic generated 3MF fixture")
    handoffs = tmp_path / "handoffs"
    monkeypatch.setattr(api, "JOB_ROOT", jobs)
    monkeypatch.setattr(api, "SLICER_HANDOFF_ROOT", handoffs)
    monkeypatch.setenv("PICAD_ENABLE_SLICER_LAUNCH", "1")
    monkeypatch.setattr(slicers, "executable_for", lambda _: "/trusted/slicer with spaces")
    with TestClient(
        api.app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 45678)
    ) as client:
        yield client, job_id, directory, handoffs


def open_slicer(client, job_id, program="bambu", origin="http://127.0.0.1:8000", **kwargs):
    return client.post(
        f"/api/models/{job_id}/slicer/{program}", headers={"Origin": origin}, json={}, **kwargs
    )


def test_discovery_never_executes_or_exposes_paths(bridge):
    client, _, _, _ = bridge
    with mock.patch.object(slicers.subprocess, "Popen") as process:
        response = client.get("/api/slicers")
    assert response.status_code == 200
    programs = response.json()["programs"]
    assert [p["id"] for p in programs] == ["bambu", "prusa"]
    assert programs[1]["target_version"] == "2.9.7"
    assert all(p["version_status"] == "not_checked" for p in programs)
    assert "/trusted" not in response.text
    process.assert_not_called()


def test_launch_uses_fixed_argument_array_and_copy_survives_job_deletion(bridge):
    client, job_id, directory, handoffs = bridge
    original = (directory / "model.3mf").read_bytes()
    with mock.patch.object(
        slicers.subprocess, "Popen", return_value=SimpleNamespace(pid=42)
    ) as run:
        response = open_slicer(client, job_id)
    assert response.status_code == 202, response.text
    result = response.json()
    assert result["status"] == "launch_requested"
    copy = handoffs / result["handoff_id"] / "model.3mf"
    assert copy.read_bytes() == original
    args, options = run.call_args
    assert args[0] == ["/trusted/slicer with spaces", str(copy.resolve())]
    assert options["shell"] is False
    assert options["start_new_session"] is True
    record = json.loads(copy.with_name("handoff.json").read_text())
    assert record["model_sha256"] == hashlib.sha256(original).hexdigest()
    assert record["import_verified"] is False
    assert client.delete(f"/api/models/{job_id}").status_code == 204
    assert copy.read_bytes() == original
    assert not directory.exists()


@pytest.mark.parametrize("program", ["anything", "../bin/sh", "bambu; touch marker"])
def test_program_is_a_fixed_choice(bridge, program):
    client, job_id, _, _ = bridge
    with mock.patch.object(slicers.subprocess, "Popen") as run:
        assert open_slicer(client, job_id, program).status_code in (404, 405)
    run.assert_not_called()


@pytest.mark.parametrize(
    "origin", ["https://evil.test", "null", "http://localhost:8000", "http://127.0.0.1:9000"]
)
def test_other_origins_cannot_start_programs(bridge, origin):
    client, job_id, _, _ = bridge
    with mock.patch.object(slicers.subprocess, "Popen") as run:
        assert open_slicer(client, job_id, origin=origin).status_code == 403
    run.assert_not_called()


def test_launch_is_opt_in_and_no_body_arguments_are_accepted(bridge, monkeypatch):
    client, job_id, _, _ = bridge
    monkeypatch.delenv("PICAD_ENABLE_SLICER_LAUNCH")
    with mock.patch.object(slicers.subprocess, "Popen") as run:
        assert open_slicer(client, job_id).status_code == 409
        bad = client.post(
            f"/api/models/{job_id}/slicer/bambu",
            headers={"Origin": "http://127.0.0.1:8000"},
            json={"executable": "/bin/sh", "args": ["-c", "echo unsafe"]},
        )
        assert bad.status_code == 422
    run.assert_not_called()


def test_missing_app_model_and_expired_job_are_recoverable(bridge, monkeypatch):
    client, job_id, directory, _ = bridge
    monkeypatch.setattr(slicers, "executable_for", lambda _: None)
    assert open_slicer(client, job_id).status_code == 409
    assert open_slicer(client, "f" * 32).status_code == 404
    os.utime(directory, (0, 0))
    assert open_slicer(client, job_id).status_code == 410


def test_launch_error_keeps_the_prepared_copy(bridge):
    client, job_id, _, handoffs = bridge
    with mock.patch.object(slicers.subprocess, "Popen", side_effect=OSError("fixture error")):
        response = open_slicer(client, job_id)
    assert response.status_code == 409
    copies = list(handoffs.glob("*/model.3mf"))
    assert len(copies) == 1
    assert json.loads(copies[0].with_name("handoff.json").read_text())["status"] == "prepared"


def test_repeated_successful_launches_are_rate_limited(bridge):
    client, job_id, _, _ = bridge
    with mock.patch.object(
        slicers.subprocess, "Popen", return_value=SimpleNamespace(pid=42)
    ) as run:
        assert open_slicer(client, job_id).status_code == 202
        assert open_slicer(client, job_id).status_code == 429
    assert run.call_count == 1


def test_repeated_request_cancellation_keeps_native_worker_locked(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def slow_launch(*_):
        entered.set()
        assert release.wait(5)
        return {"status": "launch_requested"}

    monkeypatch.setattr(api, "launch", slow_launch)
    monkeypatch.setattr(api, "resolve_job", lambda _: tmp_path)
    request = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        url="http://127.0.0.1:8000/api/models/fixture/slicer/bambu",
        headers={"origin": "http://127.0.0.1:8000", "content-type": "application/json"},
    )

    async def scenario():
        monkeypatch.setattr(api.app.state, "slicer_lock", asyncio.Lock(), raising=False)
        monkeypatch.setattr(api.app.state, "slicer_last_launch", 0, raising=False)
        call = asyncio.create_task(
            api.open_in_slicer("fixture", "bambu", request, api.SlicerLaunchRequest())
        )
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            for _ in range(3):
                call.cancel()
                await asyncio.sleep(0.01)
                assert api.app.state.slicer_lock.locked()
                assert not call.done()
            assert api.app.state.slicer_last_launch > 0
        finally:
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await call
        assert not api.app.state.slicer_lock.locked()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "client,host,origin,ctype,allowed",
    [
        ("127.0.0.1", "http://127.0.0.1:8000", "http://127.0.0.1:8000", "application/json", True),
        ("::1", "http://[::1]:8000", "http://[::1]:8000", "application/json; charset=utf-8", True),
        ("192.0.2.10", "http://127.0.0.1:8000", "http://127.0.0.1:8000", "application/json", False),
        ("127.0.0.1", "http://evil.test:8000", "http://evil.test:8000", "application/json", False),
        ("127.0.0.1", "http://127.0.0.1:8000", "http://127.0.0.1:8000", "text/plain", False),
        ("127.0.0.1", "http://127.0.0.1:8000", None, "application/json", False),
    ],
)
def test_local_host_and_origin_gate(client, host, origin, ctype, allowed):
    assert slicers.launch_request_allowed(client, host, origin, ctype) is allowed


def test_configured_path_is_not_a_command_or_silent_fallback(tmp_path, monkeypatch):
    candidate = tmp_path / "slicer with spaces"
    candidate.write_text("fixture only, never execute")
    candidate.chmod(0o755)
    monkeypatch.setenv("PICAD_PRUSA_SLICER", str(candidate))
    assert slicers.executable_for("prusa") == str(candidate.resolve())
    monkeypatch.setenv("PICAD_PRUSA_SLICER", str(candidate) + " --print")
    with mock.patch.object(slicers.shutil, "which") as search:
        assert slicers.executable_for("prusa") is None
    search.assert_not_called()
    monkeypatch.setenv("PICAD_PRUSA_SLICER", str(tmp_path))
    assert slicers.executable_for("prusa") is None
