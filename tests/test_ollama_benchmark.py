"""The benchmark must distinguish measured evidence from missing or rejected output."""

import json

import pytest

from backend import assistant
from scripts.benchmark_ollama import run_benchmark, timing_metrics


def fake_ollama(monkeypatch, *, proposal=None, remote=False, timeout=False):
    calls = []

    def request(method, path, payload=None, **kwargs):
        calls.append((method, path, payload))
        if path == "/api/version":
            return {"version": "test-only"}
        if path == "/api/tags":
            return {
                "models": [{"name": "test:small", "size": 1234, "digest": "synthetic-model-digest"}]
            }
        if path == "/api/show":
            return {
                "capabilities": ["completion"],
                **({"remote_host": "https://example.invalid"} if remote else {}),
            }
        assert path == "/api/chat"
        if payload["messages"] == []:
            return {"done": True, "done_reason": "unload"}
        if timeout:
            raise assistant.AssistantError(504, "Synthetic inference timeout")
        return {
            "done": True,
            "done_reason": "stop",
            "message": {
                "content": json.dumps({"answer": "Review the outline.", "proposal": proposal})
            },
            "eval_count": 20,
            "eval_duration": 2_000_000_000,
            "load_duration": 500_000_000,
        }

    monkeypatch.setattr(assistant, "ollama_request", request)
    return calls


def test_missing_metrics_do_not_become_invented_performance():
    metrics = timing_metrics({}, 0.2)
    assert metrics["wall_seconds"] == 0.2
    assert metrics["eval_count"] is None
    assert metrics["output_tokens_per_second"] is None
    assert (
        timing_metrics({"eval_count": 20, "eval_duration": 0}, 1)["output_tokens_per_second"]
        is None
    )


def test_metrics_use_generation_duration_not_total_latency():
    metrics = timing_metrics({"eval_count": 20, "eval_duration": 2_000_000_000}, 10)
    assert metrics["output_tokens_per_second"] == 10
    assert metrics["wall_seconds"] == 10


@pytest.mark.parametrize("scenario", ["missing", "remote"])
def test_unavailable_and_remote_models_never_trigger_inference(monkeypatch, tmp_path, scenario):
    calls = fake_ollama(monkeypatch, remote=scenario == "remote")
    name = "test:missing" if scenario == "missing" else "test:small"
    output = tmp_path / "report.json"
    assert run_benchmark([name], output, 120) == 1
    result = json.loads(output.read_text())["models"][0]
    assert result["error"]
    assert result["runs"] == []
    assert not any(path == "/api/chat" for _, path, _ in calls)


def test_invalid_suggestion_is_recorded_even_when_production_discards_it(monkeypatch, tmp_path):
    fake_ollama(monkeypatch, proposal={"width_mm": 120})
    output = tmp_path / "report.json"
    assert run_benchmark(["test:small"], output, 120) == 1
    result = json.loads(output.read_text())["models"][0]
    assert len(result["runs"]) == 9
    assert all(run["validated"] for run in result["runs"])
    assert all(not run["schema_valid"] for run in result["runs"])
    assert all(run["response"]["proposal"] is None for run in result["runs"])
    assert "width_mm" in result["runs"][0]["raw_response"]["message"]["content"]


def test_timeout_stops_model_and_preserves_failure_evidence(monkeypatch, tmp_path):
    fake_ollama(monkeypatch, timeout=True)
    output = tmp_path / "report.json"
    assert run_benchmark(["test:small"], output, 120) == 1
    result = json.loads(output.read_text())["models"][0]
    assert len(result["runs"]) == 1
    assert result["stopped_early"]
    assert result["runs"][0]["error"] == "Synthetic inference timeout"
    assert result["runs"][0]["metrics"]["output_tokens_per_second"] is None


def test_schema_success_does_not_assert_semantic_quality(monkeypatch, tmp_path):
    calls = fake_ollama(monkeypatch)
    output = tmp_path / "report.json"
    assert run_benchmark(["test:small"], output, 120) == 0
    result = json.loads(output.read_text())["models"][0]
    assert all(run["schema_valid"] for run in result["runs"])
    assert all(run["manual_review"] is None for run in result["runs"])
    assert result["runs"][0]["lexical_observations"]["mentions_measuring"] is False
    payload = next(
        payload for _, path, payload in calls if path == "/api/chat" and payload["messages"]
    )
    assert payload["messages"][0]["content"] == assistant.SYSTEM_PROMPT
    assert (
        payload["format"]["properties"]["answer"] == assistant.OUTPUT_SCHEMA["properties"]["answer"]
    )
    assert payload["format"]["properties"]["proposal"]["anyOf"][1]["properties"]["printer_id"][
        "enum"
    ] == ["custom"]
    assert "No overall winner is selected automatically" in output.with_suffix(".md").read_text()
