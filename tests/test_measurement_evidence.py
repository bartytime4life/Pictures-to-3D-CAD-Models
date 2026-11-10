"""Measurement notes survive real CAD exports without becoming geometry inputs."""

import copy
import hashlib
import json
import zipfile

import pytest
from pydantic import ValidationError

from backend.models import BuildRequest
from backend.worker import build


def measured_request():
    return {
        "name": "Reference-scaled plate",
        "profile": {"outer": [[0, 0], [100, 0], [100, 60], [0, 60]], "holes": []},
        "width_mm": 80,
        "thickness_mm": 4,
        "reference_calibration": {
            "known_length_mm": 40,
            "reference_points": [[10, 20], [60, 20]],
            "image_size": {"width": 100, "height": 60},
        },
        "measured_height_mm": 47,
        "design": {"scale_percent": 150},
    }


@pytest.fixture(scope="module")
def measured_model(tmp_path_factory):
    directory = tmp_path_factory.mktemp("measurement-exports")
    (directory / "input.json").write_text(json.dumps(measured_request()), encoding="utf-8")
    return directory, build(directory)


@pytest.mark.parametrize("kind", ["project", "bambu", "prusa"])
def test_export_preserves_source_measurements_separately_from_design(measured_model, kind):
    directory, result = measured_model
    if kind == "project":
        recipe = json.loads((directory / "project.json").read_text(encoding="utf-8"))
    else:
        with zipfile.ZipFile(directory / f"{kind}-handoff.zip") as bundle:
            payload = bundle.read("project.json")
            manifest = json.loads(bundle.read("manifest.json"))
            assert (
                manifest["files"]["project.json"]["sha256"] == hashlib.sha256(payload).hexdigest()
            )
            recipe = json.loads(payload)
    assert recipe["version"] == 2
    for field in ("reference_calibration", "measured_height_mm", "width_mm", "thickness_mm"):
        assert recipe[field] == measured_request()[field]
    assert result["dimensions"] == pytest.approx({"width": 120, "height": 72, "thickness": 4})
    # The independent 47 mm check never changes the inferred 48 mm source height.
    assert recipe["measured_height_mm"] == 47
    assert recipe["design"]["scale_percent"] == 150
    assert "data_url" not in json.dumps(recipe) and "photo" not in recipe
    body = {key: recipe[key] for key in measured_request()}
    assert BuildRequest.model_validate_json(json.dumps(body)).reference_calibration is not None


@pytest.mark.parametrize(
    "mutation",
    [
        {"width_mm": 81},
        {"measured_height_mm": 0},
        {"measured_height_mm": 2001},
        {"measured_height_mm": "47"},
        {"reference_calibration": {"known_length_mm": 0}},
        {"reference_calibration": {"known_length_mm": "40"}},
        {"reference_calibration": {"reference_points": [[10, 20], [10.5, 20]]}},
        {"reference_calibration": {"reference_points": [[-1, 20], [60, 20]]}},
        {"reference_calibration": {"reference_points": [[10, 20], [101, 20]]}},
        {"reference_calibration": {"reference_points": [[10, 20], [float("inf"), 20]]}},
        {"reference_calibration": {"image_size": {"width": 99, "height": 60}}},
        {"reference_calibration": {"image_size": {"width": 100.5, "height": 60}}},
        {"reference_calibration": {"image_size": {"width": 1401, "height": 60}}},
        {"reference_calibration": {"image": "data:image/png;base64,private"}},
    ],
)
def test_inconsistent_or_unbounded_measurements_are_rejected(mutation):
    body = copy.deepcopy(measured_request())
    if "reference_calibration" in mutation:
        body["reference_calibration"].update(mutation["reference_calibration"])
    else:
        body.update(mutation)
    with pytest.raises(ValidationError):
        BuildRequest.model_validate_json(json.dumps(body))


def test_height_only_measurement_creates_importable_version_two_recipe(tmp_path):
    body = measured_request()
    del body["reference_calibration"], body["design"]
    (tmp_path / "input.json").write_text(json.dumps(body), encoding="utf-8")
    build(tmp_path)
    recipe = json.loads((tmp_path / "project.json").read_text(encoding="utf-8"))
    assert recipe["version"] == 2 and recipe["design"]["scale_percent"] == 100
    assert recipe["measured_height_mm"] == 47
    assert "reference_calibration" not in recipe
