"""Advice stays optional, local, bounded and separate from CAD actions."""

import asyncio
import json
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx2
import pytest
from fastapi.testclient import TestClient

from backend import app as api
from backend import assistant, printing

LOCAL_MODEL = {
    "name": "qwen2.5:1.5b",
    "size": 986000000,
    "details": {"parameter_size": "1.5B", "quantization_level": "Q4_K_M"},
}

TEST_PRINTERS = [
    {
        "id": f"test/exampleforge/{name.lower()}",
        "name": f"ExampleForge {name}",
        "manufacturer": "ExampleForge",
        "technology": "FFF",
        "bed_shape": "rectangular",
        "build_volume": {"x_mm": size, "y_mm": size, "z_mm": 250},
        "excluded_areas_mm": [],
        "nozzle_diameters_mm": [0.4, 0.6],
        "default_nozzle_mm": 0.4,
        "features": {"enclosure": None, "multimaterial": None},
    }
    for name, size in (("Compact200", 200), ("Workshop300", 300), ("Tall250", 250))
]


@pytest.fixture(autouse=True)
def printer_catalog(monkeypatch):
    catalog = {"source": {"name": "Synthetic test fixtures"}, "printers": deepcopy(TEST_PRINTERS)}
    for printer in catalog["printers"]:
        printer["profiles"] = [{**deepcopy(printer), "printable_area_mm": []}]
    monkeypatch.setattr(assistant, "load_printer_catalog", lambda: catalog)

    def find_printer(identifier):
        return next((item for item in catalog["printers"] if item["id"] == identifier), None)

    monkeypatch.setattr(assistant, "printer_by_id", find_printer)
    monkeypatch.setattr(printing, "printer_by_id", find_printer)
    return catalog


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    with TestClient(api.app) as instance:
        yield instance


@pytest.fixture
def local_ollama(monkeypatch):
    """Use the real bounded HTTP client against a small local test daemon."""
    state = {
        "calls": [],
        "/api/tags": {"models": [LOCAL_MODEL]},
        "/api/show": {"capabilities": ["completion"]},
        "/api/chat": {
            "done": True,
            "done_reason": "stop",
            "message": {
                "content": json.dumps(
                    {
                        "answer": "Try coarse detail, then review the outline.",
                        "proposal": {"detail": "coarse"},
                    }
                ),
            },
        },
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            state["calls"].append((self.command, self.path, json.loads(body) if body else None))
            payload = state.get(self.path, {})
            self.send_response(state.get("status", 200))
            self.send_header("Content-Type", "application/json")
            self.end_headers()
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


def request_body(**changes):
    return {
        "model": LOCAL_MODEL["name"],
        "question": "The outline is noisy. What can I do?",
        "context": {
            "threshold": -1,
            "inverted": False,
            "detail": "standard",
            "width_mm": 80,
            "thickness_mm": 4,
            "has_image": True,
            "has_model": True,
            "hole_count": 3,
            "warnings": [],
        },
        **changes,
    }


def test_local_chat_only_suggests_validated_trace_settings(client, local_ollama):
    status = client.get("/api/assistant/status").json()
    assert status["running"]
    assert status["recommended_model"] == LOCAL_MODEL["name"]
    assert status["models"][0]["size_bytes"] == LOCAL_MODEL["size"]
    response = client.post("/api/assistant/chat", json=request_body())
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["proposal"] == {"detail": "coarse"}
    assert result["warnings"] == [assistant.REVIEW_WARNING]
    assert result["elapsed_seconds"] >= 0
    payload = local_ollama["calls"][-1][2]
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["num_ctx"] == 8192
    assert payload["options"]["num_predict"] == 512
    assert "images" not in json.dumps(payload)
    assert "tools" not in payload
    context = json.loads(payload["messages"][1]["content"])["project_context"]
    assert context["width_mm"] == 80
    assert {path for _, path, _ in local_ollama["calls"]} == {
        "/api/tags",
        "/api/show",
        "/api/chat",
    }
    assert not list(api.JOB_ROOT.iterdir())  # Advice cannot create CAD/export jobs.


def test_offline_status_is_recoverable_and_chat_has_clear_error(client, monkeypatch):
    def unavailable(*args, **kwargs):
        raise assistant.AssistantError(503, "Ollama is not running locally.")

    monkeypatch.setattr(assistant, "ollama_request", unavailable)
    status = client.get("/api/assistant/status")
    assert status.status_code == 200
    assert status.json()["running"] is False
    assert status.json()["models"] == []
    response = client.post("/api/assistant/chat", json=request_body())
    assert response.status_code == 503
    assert "not running" in response.json()["detail"]
    assert client.get("/api/health").status_code == 200


def test_empty_installation_does_not_download_a_model(client, local_ollama):
    local_ollama["/api/tags"] = {"models": []}
    status = client.get("/api/assistant/status").json()
    assert status["running"] and status["models"] == []
    assert status["recommended_model"] is None
    assert "Install a local model" in status["detail"]
    assert client.post("/api/assistant/chat", json=request_body()).status_code == 409
    assert all(path == "/api/tags" for _, path, _ in local_ollama["calls"])


def test_model_preference_uses_only_installed_choices(local_ollama, monkeypatch):
    local_ollama["/api/tags"]["models"].append({"name": "qwen3:1.7b", "size": 1400000000})
    monkeypatch.delenv("PICTURES_CAD_OLLAMA_MODEL", raising=False)
    assert assistant.assistant_status()["recommended_model"] == "qwen3:1.7b"
    monkeypatch.setenv("PICTURES_CAD_OLLAMA_MODEL", LOCAL_MODEL["name"])
    assert assistant.assistant_status()["recommended_model"] == LOCAL_MODEL["name"]
    monkeypatch.setenv("PICTURES_CAD_OLLAMA_MODEL", "missing:latest")
    assert assistant.assistant_status()["recommended_model"] == "qwen3:1.7b"


def test_chat_timeout_has_a_recoverable_error(client, monkeypatch):
    def timeout(method, path, payload=None, **kwargs):
        if path == "/api/tags":
            return {"models": [LOCAL_MODEL]}
        if path == "/api/show":
            return {"capabilities": ["completion"]}
        raise assistant.AssistantError(504, "Ollama took too long. Try a smaller model.")

    monkeypatch.setattr(assistant, "ollama_request", timeout)
    result = client.post("/api/assistant/chat", json=request_body())
    assert result.status_code == 504
    assert "smaller model" in result.json()["detail"]
    assert not api.app.state.assistant_lock.locked()


@pytest.mark.parametrize(
    "address",
    [
        "https://ollama.com",
        "http://example.com:11434",
        "http://127.0.0.1.evil.test",
        "http://user:pass@127.0.0.1",
        "http://127.0.0.1:11434/api",
        "http://127.0.0.1?x=1",
        "http://127.0.0.1:0",
        "http://127.0.0.1:70000",
        "http://[::1",
        "file:///tmp/model",
    ],
)
def test_remote_or_ambiguous_ollama_urls_are_rejected(address, monkeypatch):
    monkeypatch.setenv("PICTURES_CAD_OLLAMA_URL", address)
    with pytest.raises(assistant.AssistantError, match="loopback"):
        assistant.ollama_address()


def test_cloud_models_and_unknown_model_do_not_trigger_generation(client, local_ollama):
    local_ollama["/api/tags"]["models"] += [
        {"name": "qwen3:cloud", "size": 123},
        {"name": "remote:latest", "size": 123, "remote_host": "https://ollama.com"},
        {"name": "alias:latest", "size": 123, "remote_model": "remote-model"},
        {"name": "empty:latest", "size": 0},
    ]
    status = client.get("/api/assistant/status").json()
    assert [item["name"] for item in status["models"]] == [LOCAL_MODEL["name"]]
    for name in ("qwen3:cloud", "remote:latest", "missing:latest"):
        response = client.post("/api/assistant/chat", json=request_body(model=name))
        assert response.status_code == 409
    assert all(path != "/api/chat" for _, path, _ in local_ollama["calls"])


def test_remote_model_alias_and_embedding_model_rejected_before_chat(client, local_ollama):
    for details in ({"remote_host": "https://ollama.com"}, {"capabilities": ["embedding"]}):
        local_ollama["/api/show"] = details
        response = client.post("/api/assistant/chat", json=request_body())
        assert response.status_code == 409
    assert all(path != "/api/chat" for _, path, _ in local_ollama["calls"])


@pytest.mark.parametrize(
    "proposal",
    [
        {"width_mm": 100},
        {"threshold": 999},
        {"threshold": 0},
        {"threshold": True},
        {"threshold": "128"},
        {"inverted": "true"},
        {"detail": "ultra"},
        ["fine"],
    ],
)
def test_invalid_or_measurement_proposals_are_discarded(proposal):
    raw = {
        "message": {"content": json.dumps({"answer": "Review your trace.", "proposal": proposal})}
    }
    result = assistant.parse_chat_response(raw)
    assert result["proposal"] is None
    assert len(result["warnings"]) == 2


@pytest.mark.parametrize(
    "proposal",
    [
        {"scale_percent": 0},
        {"thickness_percent": 401},
        {"color": "red"},
        {"material": "carbon-fiber-certified"},
        {"detail_mode": "ultra"},
        {"nozzle_mm": 0.01},
        {"output_mode": "assembly-with-joints"},
        {"split_columns": 2.5},
        {"printer_id": "invented-perfect-printer"},
        {"bed_width_mm": 9000},
        {"scale_percent": float("nan")},
    ],
)
def test_invalid_design_and_unknown_printer_suggestions_are_discarded(proposal):
    result = assistant.parse_chat_response(
        {
            "message": {
                "content": json.dumps({"answer": "Review the suggestion.", "proposal": proposal})
            }
        }
    )
    assert result["proposal"] is None
    assert len(result["warnings"]) == 2


def set_response(
    local_ollama, proposal, answer="Review the proposed settings, then apply if suitable."
):
    local_ollama["/api/chat"]["message"]["content"] = json.dumps(
        {"answer": answer, "proposal": proposal}
    )


def test_explicit_design_proposal_preserves_measurements_and_does_not_build(client, local_ollama):
    proposal = {
        "scale_percent": 150,
        "thickness_percent": 125,
        "color": "#00aaff",
        "material": "petg",
        "detail_mode": "balanced",
        "nozzle_mm": 0.6,
        "output_mode": "split",
        "split_columns": 3,
        "split_rows": 2,
    }
    set_response(local_ollama, proposal)
    body = request_body(
        question="Make the design larger at 150%, increase thickness to 125%, use blue PETG and six pieces."
    )
    result = client.post("/api/assistant/chat", json=body)
    assert result.status_code == 200, result.text
    assert result.json()["proposal"] == proposal
    assert body["context"]["width_mm"] == 80
    assert body["context"]["thickness_mm"] == 4
    assert not list(api.JOB_ROOT.iterdir())


def test_unrequested_resizing_is_removed_while_useful_advice_remains(client, local_ollama):
    set_response(local_ollama, {"scale_percent": 200, "thickness_percent": 200, "detail": "coarse"})
    result = client.post("/api/assistant/chat", json=request_body()).json()
    assert result["proposal"] == {"detail": "coarse"}
    assert any("size suggestion was withheld" in warning for warning in result["warnings"])


@pytest.mark.parametrize(
    "question,scale",
    [
        ("Make it 20% wider.", 120),
        ("Set the width to 100 mm.", 125),
        ("Make the part longer.", 120),
        ("Fit it on my printer.", 90),
        ("Reduce its height by 10%.", 90),
        ("Adjust the length to 40 mm.", 50),
        ("20% narrower, please.", 80),
    ],
)
def test_natural_resize_requests_keep_reviewable_relative_scale(question, scale):
    request = assistant.AssistantRequest.model_validate(request_body(question=question))
    response = assistant.review_proposal(
        {
            "answer": "Review the suggested relative scale.",
            "proposal": {"scale_percent": scale},
            "warnings": [],
        },
        request,
    )
    assert response["proposal"] == {"scale_percent": scale}
    assert request.context.width_mm == 80
    assert request.context.thickness_mm == 4


@pytest.mark.parametrize(
    "question",
    [
        "Which export should I use for CAD editing, STEP or STL?",
        "Explain the units in exported files.",
        "Will it fit on my printer?",
    ],
)
def test_export_explanations_and_fit_checks_do_not_authorize_resizing(question):
    request = assistant.AssistantRequest.model_validate(request_body(question=question))
    response = assistant.review_proposal(
        {
            "answer": "Review the export settings.",
            "proposal": {"scale_percent": 90},
            "warnings": [],
        },
        request,
    )
    assert response["proposal"] is None
    assert any("size suggestion was withheld" in warning for warning in response["warnings"])


@pytest.mark.parametrize(
    "question,sizes",
    [
        # Negated size or thickness wording withholds only that axis.
        ("Don't change the thickness, just make it blue.", set()),
        ("Don't make it bigger, just change the color", set()),
        (
            (
                "My current XY scale is 150%. Make that design 20% larger, keep its thickness, "
                "and propose blue PETG."
            ),
            {"scale_percent"},
        ),
        ("Don’t change the width, length or thickness. Use blue.", set()),
        ("Make it fit my printer without changing the thickness.", {"scale_percent"}),
        ("Make it 20% larger with the thickness unchanged.", {"scale_percent"}),
        # Positive requests still reach review, including after an unrelated negation.
        ("Keep the width the same, but make it 50% thicker.", {"thickness_percent"}),
        ("Keep the thickness and make it 20% larger.", {"scale_percent"}),
        ("Don't change the color, but make it 20% wider.", {"scale_percent"}),
        (
            "Make it 20% wider and increase the thickness to 150%.",
            {"scale_percent", "thickness_percent"},
        ),
    ],
)
def test_negated_size_wording_does_not_authorize_that_change(question, sizes):
    request = assistant.AssistantRequest.model_validate(request_body(question=question))
    response = assistant.review_proposal(
        {
            "answer": "Review the suggested changes.",
            "proposal": {"scale_percent": 120, "thickness_percent": 150, "color": "#0000ff"},
            "warnings": [],
        },
        request,
    )
    assert set(response["proposal"]) == sizes | {"color"}
    withheld = any("size suggestion was withheld" in w for w in response["warnings"])
    assert withheld is (len(sizes) < 2)


def test_requested_scale_cannot_exceed_known_cad_dimension_limits(client, local_ollama):
    body = request_body(question="Double the size of this part.")
    body["context"]["width_mm"] = 1500
    set_response(local_ollama, {"scale_percent": 200})
    response = client.post("/api/assistant/chat", json=body).json()
    assert response["proposal"] is None
    assert any("supported CAD dimensions" in warning for warning in response["warnings"])


def test_noop_color_uses_the_same_normalization_as_the_design(client, local_ollama):
    set_response(local_ollama, {"color": "#9CA3AF"})
    response = client.post("/api/assistant/chat", json=request_body()).json()
    assert response["proposal"] is None


def test_kernel_bounding_box_tolerance_does_not_reject_a_valid_limit_part(client, local_ollama):
    body = request_body(question="Use blue for the preview.")
    body["context"]["geometry"] = {
        "width_mm": 2000.0000002,
        "height_mm": 2000.0000002,
        "thickness_mm": 500.0000002,
    }
    set_response(local_ollama, {"color": "#00aaff"})
    response = client.post("/api/assistant/chat", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["proposal"] == {"color": "#00aaff"}
    body["context"]["geometry"]["width_mm"] = 2000.01
    assert client.post("/api/assistant/chat", json=body).status_code == 422


def test_partial_design_patch_is_checked_against_existing_split_count(client, local_ollama):
    body = request_body()
    body["context"]["design"] = {"output_mode": "split", "split_columns": 2, "split_rows": 4}
    set_response(local_ollama, {"split_columns": 3})
    result = client.post("/api/assistant/chat", json=body).json()
    assert result["proposal"] is None
    assert any("supported design" in warning for warning in result["warnings"])


def test_printer_selection_resolves_bed_before_the_user_reviews_it(client, local_ollama):
    set_response(
        local_ollama,
        {"printer_id": TEST_PRINTERS[1]["id"], "bed_width_mm": 999, "bed_height_mm": 1000},
    )
    result = client.post(
        "/api/assistant/chat",
        json=request_body(question="Choose the ExampleForge Workshop300 for this design."),
    ).json()
    assert result["proposal"]["printer_id"] == TEST_PRINTERS[1]["id"]
    assert result["proposal"]["bed_width_mm"] == 300
    assert result["proposal"]["bed_depth_mm"] == 300
    # 250 is already the current value, so it need not appear as a change.
    assert "bed_height_mm" not in result["proposal"]
    assert "nozzle_mm" not in result["proposal"]


def test_printer_context_is_bounded_and_uses_catalog_facts(client, local_ollama, printer_catalog):
    for index in range(7):
        printer_catalog["printers"].append(
            {**TEST_PRINTERS[0], "id": f"test/additional/{index}", "name": f"Printer {index}"}
        )
    body = request_body(question="Compare Compact200 and Workshop300 for my part.")
    body["context"]["design"] = {"printer_id": TEST_PRINTERS[0]["id"]}
    body["context"]["geometry"] = {
        "width_mm": 80,
        "height_mm": 34,
        "thickness_mm": 4,
        "parts": [{"width_mm": 80, "height_mm": 34, "thickness_mm": 4}],
    }
    response = client.post("/api/assistant/chat", json=body)
    assert response.status_code == 200, response.text
    payload = local_ollama["calls"][-1][2]
    context = json.loads(payload["messages"][1]["content"])
    assert context["selected_printer"]["build_volume"]["x_mm"] == 200
    assert context["selected_printer"]["features"]["enclosure"] is None
    assert "unknown" in context["selected_printer"]["material_compatibility"]
    assert len(context["printer_candidates"]) == 2
    assert context["limits"]["toolpaths_and_physical_print_validation"] is False
    assert context["project_context"]["geometry"]["parts"][0]["width_mm"] == 80
    allowed = payload["format"]["properties"]["proposal"]["anyOf"][1]["properties"]["printer_id"][
        "enum"
    ]
    assert set(allowed) == {"custom", TEST_PRINTERS[0]["id"], TEST_PRINTERS[1]["id"]}
    many = assistant.printer_candidates(" ".join(f"Printer {index}" for index in range(7)))
    assert len(many) == 5


def test_unrequested_catalog_printer_is_not_offered(client, local_ollama):
    set_response(local_ollama, {"printer_id": TEST_PRINTERS[2]["id"], "bed_width_mm": 250})
    result = client.post("/api/assistant/chat", json=request_body()).json()
    assert result["proposal"] is None
    assert any("unrequested printer" in warning for warning in result["warnings"])


def test_model_matching_does_not_confuse_a_mini_with_its_parent_model(printer_catalog):
    for index, name in enumerate(("ExampleForge A1", "ExampleForge A1 mini", "ExampleForge Mini")):
        printer_catalog["printers"].append(
            {**TEST_PRINTERS[0], "id": f"test/overlapping/{index}", "name": name}
        )
    assert [item["name"] for item in assistant.printer_candidates("Choose A1 mini.")] == [
        "ExampleForge A1 mini"
    ]
    assert {item["name"] for item in assistant.printer_candidates("Compare A1 mini and A1.")} == {
        "ExampleForge A1",
        "ExampleForge A1 mini",
    }
    assert assistant.printer_candidates("I need a mini printer.") == []


def test_changed_nozzle_uses_matching_profile_dimensions_before_review(
    client, local_ollama, printer_catalog
):
    printer = printer_catalog["printers"][0]
    printer["profiles"] = [
        {**deepcopy(printer["profiles"][0]), "nozzle_diameters_mm": [0.4]},
        {
            **deepcopy(printer["profiles"][0]),
            "nozzle_diameters_mm": [0.6],
            "build_volume": {"x_mm": 190, "y_mm": 195, "z_mm": 240},
        },
    ]
    body = request_body(question="Use a 0.6 mm nozzle.")
    body["context"]["design"] = {
        "printer_id": printer["id"],
        "bed_width_mm": 200,
        "bed_depth_mm": 200,
    }
    set_response(local_ollama, {"nozzle_mm": 0.6})
    response = client.post("/api/assistant/chat", json=body).json()
    assert response["proposal"] == {
        "nozzle_mm": 0.6,
        "bed_width_mm": 190,
        "bed_depth_mm": 195,
        "bed_height_mm": 240,
    }
    set_response(local_ollama, {"nozzle_mm": 0.8})
    response = client.post("/api/assistant/chat", json=body).json()
    assert response["proposal"] == {"nozzle_mm": 0.8}
    assert any("unambiguous" in warning for warning in response["warnings"])


def test_custom_bed_change_is_explicit_when_a_catalog_printer_is_selected(client, local_ollama):
    body = request_body(question="Use my custom 350 mm wide bed.")
    body["context"]["design"] = {"printer_id": TEST_PRINTERS[0]["id"]}
    set_response(local_ollama, {"bed_width_mm": 350})
    result = client.post("/api/assistant/chat", json=body).json()
    assert result["proposal"] == {"printer_id": "custom", "bed_width_mm": 350}
    assert any("physical printer" in warning for warning in result["warnings"])


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"message": {"content": "Not JSON"}},
        {"message": {"content": '{"answer":"Try coarse detail."}'}},
        {"message": {"content": '{"answer":[],"proposal":null}'}},
        {"message": {"content": '{"answer":"ok","proposal":null,"code":"run"}'}},
        {"message": {"content": '{"answer":"ok","proposal":null}', "tool_calls": [{}]}},
        {"done_reason": "length", "message": {"content": '{"answer":"ok","proposal":null}'}},
    ],
)
def test_malformed_truncated_or_action_outputs_are_rejected(raw):
    with pytest.raises(assistant.AssistantError) as failure:
        assistant.parse_chat_response(raw)
    assert failure.value.status_code == 502


def test_unchanged_suggestion_is_not_an_action(client, local_ollama):
    local_ollama["/api/chat"]["message"]["content"] = json.dumps(
        {
            "answer": "Automatic threshold is already selected.",
            "proposal": {"threshold": -1},
        }
    )
    assert client.post("/api/assistant/chat", json=request_body()).json()["proposal"] is None


def test_request_limits_reject_photos_and_bad_context(client, local_ollama):
    for changes in (
        {"question": " "},
        {"question": "x" * 1601},
        {"model": "http://remote.test?model=x"},
        {"context": {"image": "photo data"}},
        {"context": {"width_mm": -5}},
        {"context": {"threshold": 0}},
        {"context": {"warnings": ["x" * 301]}},
        {"context": {"warnings": ["warning"] * 9}},
    ):
        assert client.post("/api/assistant/chat", json=request_body(**changes)).status_code == 422
    assert not local_ollama["calls"]


def test_http_failures_are_sanitized_and_redirects_are_not_followed(local_ollama, monkeypatch):
    for code, expected in ((302, 502), (404, 409), (500, 502)):
        local_ollama["status"] = code
        local_ollama["/api/tags"] = {"error": "secret server detail"}
        with pytest.raises(assistant.AssistantError) as failure:
            assistant.installed_models()
        assert failure.value.status_code == expected
        assert "secret" not in failure.value.detail
    local_ollama["status"] = 200
    local_ollama["/api/tags"] = b"not JSON"
    with pytest.raises(assistant.AssistantError, match="unreadable"):
        assistant.installed_models()
    monkeypatch.setattr(assistant, "MAX_RESPONSE_BYTES", 32)
    local_ollama["/api/tags"] = b"x" * 33
    with pytest.raises(assistant.AssistantError, match="too much"):
        assistant.installed_models()


def test_inference_slot_survives_cancelled_http_request(tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def slow_chat(request):
        started.set()
        release.wait(timeout=5)
        return {
            "model": request.model,
            "answer": "Review your trace.",
            "proposal": None,
            "warnings": [],
            "elapsed_seconds": 0.1,
        }

    monkeypatch.setattr(api, "chat", slow_chat)
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")

    async def exercise():
        async with (
            api.lifespan(api.app),
            httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=api.app), base_url="http://test"
            ) as client,
        ):
            first = asyncio.create_task(client.post("/api/assistant/chat", json=request_body()))
            await asyncio.wait_for(asyncio.to_thread(started.wait), timeout=2)
            first.cancel()
            await asyncio.sleep(0)
            assert api.app.state.assistant_lock.locked()
            second = await client.post("/api/assistant/chat", json=request_body())
            assert second.status_code == 429
            assert (await client.get("/api/health")).status_code == 200
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await first
            assert not api.app.state.assistant_lock.locked()

    try:
        asyncio.run(exercise())
    finally:
        release.set()
