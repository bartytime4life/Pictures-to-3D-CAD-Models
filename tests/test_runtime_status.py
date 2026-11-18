"""Setup reporting works without CAD imports, writes, model downloads or inference."""

import importlib.metadata
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend import runtime_status


@pytest.fixture
def prepared_root(tmp_path, monkeypatch):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").touch()
    (tmp_path / ".venv" / "bin" / "python").chmod(0o700)
    dist = tmp_path / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<script type="module" src="/assets/app.js"></script>')
    (dist / "assets" / "app.js").write_text("export {}")
    monkeypatch.setattr(runtime_status.sys, "version_info", (3, 12, 9))
    monkeypatch.setattr(runtime_status.sys, "prefix", str(tmp_path / ".venv"))
    monkeypatch.setattr(runtime_status.importlib.metadata, "version", lambda name: "1.0")
    return tmp_path


def by_id(report, identifier):
    return next(item for item in report["checks"] if item["id"] == identifier)


def test_optional_ai_never_blocks_prepared_core(prepared_root):
    report = runtime_status.summarize_runtime(root=prepared_root, check_ai=False)
    assert report["ready"]
    assert by_id(report, "ollama")["status"] == "limited"
    assert not by_id(report, "ollama")["required"]


def test_missing_environment_has_recovery_without_creating_files(tmp_path):
    before = set(tmp_path.rglob("*"))
    report = runtime_status.summarize_runtime(root=tmp_path, check_ai=False)
    assert not report["ready"]
    assert by_id(report, "python")["action"]["command"] == "./scripts/setup.sh"
    assert by_id(report, "interface")["action"]["command"] == "npm run build"
    assert set(tmp_path.rglob("*")) == before


def test_wrong_python_is_not_ready(prepared_root, monkeypatch):
    monkeypatch.setattr(runtime_status.sys, "version_info", (3, 13, 1))
    report = runtime_status.summarize_runtime(root=prepared_root, check_ai=False)
    assert not report["ready"]
    assert by_id(report, "python")["status"] == "missing"


def test_environment_must_be_executable_and_current(prepared_root, monkeypatch):
    (prepared_root / ".venv" / "bin" / "python").chmod(0o600)
    assert not runtime_status.summarize_runtime(root=prepared_root, check_ai=False)["ready"]
    (prepared_root / ".venv" / "bin" / "python").chmod(0o700)
    monkeypatch.setattr(runtime_status.sys, "prefix", "/different/environment")
    assert not runtime_status.summarize_runtime(root=prepared_root, check_ai=False)["ready"]


def test_missing_package_is_actionable_and_other_packages_remain_checked(
    prepared_root, monkeypatch
):
    seen = []

    def version(name):
        seen.append(name)
        if name == "cadquery":
            raise importlib.metadata.PackageNotFoundError(name)
        return "1.0"

    monkeypatch.setattr(runtime_status.importlib.metadata, "version", version)
    report = runtime_status.summarize_runtime(root=prepared_root, check_ai=False)
    assert not report["ready"]
    assert "cadquery" in by_id(report, "packages")["detail"]
    assert seen == list(runtime_status.PYTHON_PACKAGES)


@pytest.mark.parametrize(
    "asset", ["/assets/absent.js", "/assets/../../outside.js", "/assets/%2e%2e/%2e%2e/outside.js"]
)
def test_incomplete_or_escaping_assets_are_not_ready(prepared_root, asset):
    (prepared_root / "frontend" / "dist" / "index.html").write_text(
        f'<script src="{asset}"></script>'
    )
    (prepared_root / "outside.js").touch()
    report = runtime_status.summarize_runtime(root=prepared_root, check_ai=False)
    assert by_id(report, "interface")["status"] == "missing"


@pytest.mark.parametrize(
    "body", ["", "not the built app", "<script src='https://example.com/app.js'></script>"]
)
def test_index_without_local_assets_is_incomplete(prepared_root, body):
    (prepared_root / "frontend" / "dist" / "index.html").write_text(body)
    assert not runtime_status.summarize_runtime(root=prepared_root, check_ai=False)["ready"]


@pytest.fixture
def ollama_server(monkeypatch):
    state = {
        "calls": [],
        "tags": {"models": [{"name": "local:small", "size": 100}]},
        "show": {"capabilities": ["completion"]},
        "status": 200,
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            state["calls"].append((self.command, self.path, json.loads(body) if body else None))
            self.send_response(state["status"])
            self.end_headers()
            payload = state["tags"] if self.path == "/api/tags" else state["show"]
            time.sleep(state.get("delay", 0))
            if state.get("drip"):
                for _ in range(10):
                    try:
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        time.sleep(0.02)
                    except (BrokenPipeError, ConnectionResetError):
                        break
                return
            self.wfile.write(
                payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            )

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("PICTURES_CAD_OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
    yield state
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_real_loopback_metadata_transport_verifies_chat_without_inference(
    prepared_root, ollama_server
):
    report = runtime_status.summarize_runtime(root=prepared_root)
    ai = by_id(report, "ollama")
    assert report["ready"] and ai["status"] == "ready"
    assert [(method, path) for method, path, _ in ollama_server["calls"]] == [
        ("GET", "/api/tags"),
        ("POST", "/api/show"),
    ]
    assert "local:small" not in json.dumps(report)
    assert str(prepared_root) not in json.dumps(report)
    assert "127.0.0.1" not in json.dumps(report)


@pytest.mark.parametrize(
    "details",
    [
        {"capabilities": ["embedding"]},
        {"capabilities": ["completion"], "remote_host": "private-host"},
        {"capabilities": "completion"},
    ],
)
def test_embedding_and_remote_metadata_do_not_claim_chat_readiness(
    prepared_root, ollama_server, details
):
    ollama_server["show"] = details
    report = runtime_status.summarize_runtime(root=prepared_root)
    assert report["ready"]
    assert by_id(report, "ollama")["status"] == "limited"


@pytest.mark.parametrize(
    "model",
    [
        {"name": "local:cloud", "size": 500},
        {"name": "local:small", "size": 0},
        {"name": "local:small", "size": 500, "remote_model": "upstream"},
        {"name": "https://private-host/model", "size": 500},
    ],
)
def test_ineligible_models_are_not_requested(prepared_root, ollama_server, model):
    ollama_server["tags"] = {"models": [model]}
    report = runtime_status.summarize_runtime(root=prepared_root)
    assert by_id(report, "ollama")["status"] == "limited"
    assert len(ollama_server["calls"]) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:11434",
        "http://example.com:11434",
        "http://169.254.169.254",
        "http://user:pass@127.0.0.1",
        "http://127.0.0.1/api",
        "http://127.0.0.1:bad",
        "http://127.0.0.1?secret=private",
        "http://[::1]:11434#private",
    ],
)
def test_invalid_endpoint_never_connects_or_discloses_values(prepared_root, monkeypatch, url):
    monkeypatch.setenv("PICTURES_CAD_OLLAMA_URL", url)
    monkeypatch.setattr(
        runtime_status, "_metadata_request", lambda *args: pytest.fail("Must not connect")
    )
    report = runtime_status.summarize_runtime(root=prepared_root)
    assert report["ready"]
    assert by_id(report, "ollama")["status"] == "limited"
    assert url not in json.dumps(report)


@pytest.mark.parametrize("payload", [b"not json", b"[]", {"models": "invalid"}, {"models": []}])
def test_bad_or_empty_metadata_is_optional(prepared_root, ollama_server, payload):
    ollama_server["tags"] = payload
    assert (
        by_id(runtime_status.summarize_runtime(root=prepared_root), "ollama")["status"] == "limited"
    )


def test_redirect_is_not_followed(prepared_root, ollama_server):
    ollama_server["status"] = 302
    report = runtime_status.summarize_runtime(root=prepared_root)
    assert by_id(report, "ollama")["status"] == "limited"
    assert len(ollama_server["calls"]) == 1


def test_ai_metadata_shares_one_deadline(prepared_root, monkeypatch):
    deadlines = []

    def request(address, method, path, deadline, payload=None):
        deadlines.append(deadline)
        if path == "/api/tags":
            return {"models": [{"name": "local:small", "size": 100}]}
        raise TimeoutError

    monkeypatch.setattr(runtime_status, "_metadata_request", request)
    started = time.monotonic()
    report = runtime_status.summarize_runtime(root=prepared_root)
    assert by_id(report, "ollama")["status"] == "limited"
    assert len(deadlines) == 2 and deadlines[0] == deadlines[1]
    assert 0 < deadlines[0] - started <= runtime_status.AI_TIMEOUT + 0.1


def test_metadata_body_size_is_bounded(prepared_root, ollama_server):
    ollama_server["tags"] = b" " * (runtime_status.MAX_METADATA_BYTES + 1)
    report = runtime_status.summarize_runtime(root=prepared_root)
    assert by_id(report, "ollama")["status"] == "limited"


def test_slow_body_cannot_extend_the_metadata_budget(prepared_root, ollama_server, monkeypatch):
    ollama_server["drip"] = True
    monkeypatch.setattr(runtime_status, "AI_TIMEOUT", 0.06)
    started = time.monotonic()
    report = runtime_status.summarize_runtime(root=prepared_root)
    assert time.monotonic() - started < 0.5
    assert report["ready"]
    assert by_id(report, "ollama")["status"] == "limited"


@pytest.mark.parametrize(
    "version,expected",
    [
        ("v22.11.0\n", "limited"),
        ("v22.12.0\n", "ready"),
        ("v24.1.0\n", "ready"),
        ("invalid", "limited"),
    ],
)
def test_development_tools_are_optional(prepared_root, monkeypatch, version, expected):
    monkeypatch.setattr(runtime_status.shutil, "which", lambda name: name)
    monkeypatch.setattr(
        runtime_status.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=version)
    )
    report = runtime_status.summarize_runtime(
        root=prepared_root, check_ai=False, include_development=True
    )
    assert report["ready"]
    assert by_id(report, "development")["status"] == expected


def test_module_import_does_not_require_third_party_packages():
    # A clean interpreter must be able to import doctor before setup has installed dependencies.
    import subprocess
    import sys

    completed = subprocess.run(
        [sys.executable, "-S", "-B", "-c", "from backend.runtime_status import summarize_runtime"],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert completed.returncode == 0, completed.stderr


def test_runtime_route_is_not_cached_and_returns_fresh_checks(monkeypatch):
    import asyncio

    import httpx2

    from backend import app as api

    calls = []

    def summary():
        calls.append(True)
        ready = len(calls) == 1
        return {
            "ready": ready,
            "checks": [
                runtime_status._check(
                    "packages",
                    "CAD packages",
                    "ready" if ready else "missing",
                    True,
                    "Synthetic dependency result.",
                )
            ],
        }

    monkeypatch.setattr(api, "summarize_runtime", summary)

    async def exercise():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=api.app), base_url="http://test"
        ) as client:
            first = await client.get("/api/runtime")
            second = await client.get("/api/runtime")
        assert first.status_code == second.status_code == 200
        assert first.headers["cache-control"] == second.headers["cache-control"] == "no-store"
        assert first.json()["ready"] is True
        assert second.json()["ready"] is False
        assert by_id(first.json(), "packages")["status"] == "ready"
        assert by_id(second.json(), "packages")["status"] == "missing"

    asyncio.run(exercise())
    assert len(calls) == 2


def test_runtime_metadata_runs_off_event_loop_and_does_not_block_health(monkeypatch):
    import asyncio

    import httpx2

    from backend import app as api

    started, release = threading.Event(), threading.Event()
    worker_threads = []

    def slow_summary():
        worker_threads.append(threading.get_ident())
        started.set()
        release.wait(timeout=2)
        return {
            "ready": True,
            "checks": [
                runtime_status._check(
                    "packages",
                    "CAD packages",
                    "ready",
                    True,
                    "Synthetic dependency result.",
                )
            ],
        }

    monkeypatch.setattr(api, "summarize_runtime", slow_summary)

    async def exercise():
        event_loop_thread = threading.get_ident()
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=api.app), base_url="http://test"
        ) as client:
            pending = asyncio.create_task(client.get("/api/runtime"))
            try:
                assert await asyncio.wait_for(asyncio.to_thread(started.wait, 1), timeout=1.5)
                assert len(worker_threads) == 1
                assert worker_threads[0] != event_loop_thread
                assert not pending.done()
                health = await asyncio.wait_for(client.get("/api/health"), timeout=0.5)
                assert health.status_code == 200
            finally:
                release.set()
                response = await asyncio.wait_for(pending, timeout=1)
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"

    try:
        asyncio.run(exercise())
    finally:
        release.set()
