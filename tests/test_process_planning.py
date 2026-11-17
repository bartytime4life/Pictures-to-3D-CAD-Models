"""Process plans validate and persist without modifying the generated solid."""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import app as api
from backend.models import DesignSettings
from backend.worker import build


def test_legacy_design_gets_defaults_and_small_nozzle_compatible_layer_height():
    defaults = DesignSettings().model_dump()
    assert defaults["layer_height_mm"] == 0.2
    assert defaults["wall_count"] == 3
    assert defaults["infill_percent"] == 15
    assert defaults["supports"] == defaults["adhesion"] == "none"
    assert DesignSettings(nozzle_mm=0.1).layer_height_mm == 0.1
    assert DesignSettings(nozzle_mm=0.15).layer_height_mm == 0.15
    assert DesignSettings(nozzle_mm=0.1, layer_height_mm=0.05).layer_height_mm == 0.05


@pytest.mark.parametrize(
    "settings",
    [
        {"layer_height_mm": 0.049},
        {"layer_height_mm": 1.21, "nozzle_mm": 2},
        {"layer_height_mm": 0.3, "nozzle_mm": 0.2},
        {"layer_height_mm": float("nan")},
        {"wall_count": 0},
        {"wall_count": 13},
        {"wall_count": 2.5},
        {"wall_count": True},
        {"infill_percent": -1},
        {"infill_percent": 101},
        {"infill_percent": float("inf")},
        {"supports": "automatic"},
        {"adhesion": "glue"},
    ],
)
def test_process_rejects_invalid_or_incompatible_values(settings):
    with pytest.raises(ValidationError):
        DesignSettings.model_validate(settings)


def test_invalid_process_is_rejected_before_starting_a_build(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path)
    with TestClient(api.app) as client:
        response = client.post(
            "/api/build",
            json={
                "profile": {"outer": [[0, 0], [20, 0], [20, 10], [0, 10]], "holes": []},
                "width_mm": 20,
                "thickness_mm": 2,
                "design": {"nozzle_mm": 0.4, "layer_height_mm": 0.8},
            },
        )
    assert response.status_code == 422
    assert not list(tmp_path.iterdir())


def test_process_only_changes_persisted_plan_and_not_geometry(tmp_path):
    body = {
        "profile": {"outer": [[0, 0], [20, 0], [20, 10], [0, 10]], "holes": []},
        "width_mm": 20,
        "thickness_mm": 2,
        "design": {},
    }
    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir()
    (baseline_dir / "input.json").write_text(json.dumps(body))
    baseline = build(baseline_dir)
    changed_dir = tmp_path / "changed"
    changed_dir.mkdir()
    plan = {
        "layer_height_mm": 0.12,
        "wall_count": 6,
        "infill_percent": 85,
        "supports": "everywhere",
        "adhesion": "raft",
    }
    body["design"] = plan
    (changed_dir / "input.json").write_text(json.dumps(body))
    changed = build(changed_dir)
    for field in ("dimensions", "volume_mm3", "hole_count", "mesh", "print_fit"):
        assert changed[field] == baseline[field]
    recipe = json.loads((changed_dir / "project.json").read_text())
    assert all(recipe["design"][key] == value for key, value in plan.items())
    assert all(changed["design"][key] == value for key, value in plan.items())
    assert (changed_dir / "model.stl").read_bytes() == (baseline_dir / "model.stl").read_bytes()
