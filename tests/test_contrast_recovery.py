"""Recoverable weak-edge failures, using real rendered captures and tracing code."""

import io

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import app as api
from backend import edges, reference, tone
from tests import synthetic as S

GUIDANCE = (
    "The part's outline is not clear enough to measure. Retake the photo in focus "
    "with stronger contrast between the part and the sheet."
)


@pytest.fixture(scope="module")
def weak_capture():
    # The sheet still contrasts with the table and segmentation finds the part;
    # none of the outer boundary's local profiles survives the first edge pass.
    return S.colour_photo((185,) * 3, (220,) * 3, (200,) * 3, ppm=3.0, blur=4.0)


def test_weak_capture_has_actionable_reference_error(weak_capture):
    with Image.open(io.BytesIO(weak_capture)) as image:
        rgb = np.asarray(image)
    with pytest.raises(reference.ReferenceError_, match="in focus") as failure:
        reference.trace_on_sheet(
            rgb,
            reference="a4",
            sheet_mm=None,
            inverted=False,
            detail="standard",
            thickness_mm=None,
            focal_35mm=None,
            snap=True,
            notices=[],
        )
    assert str(failure.value) == GUIDANCE
    assert isinstance(failure.value.__cause__, edges.EdgeError)


def test_retained_hole_cannot_substitute_for_an_unmeasurable_outer_boundary():
    y, x = np.indices((160, 160))
    radius_squared = (x + 0.5 - 80) ** 2 + (y + 0.5 - 80) ** 2
    material = (radius_squared < 50**2) & (radius_squared > 12**2)
    # The outer edge has only eight saved levels of contrast. The hole has
    # strong contrast and can survive even when the outer boundary does not.
    saved = np.where(radius_squared < 50**2, 212.0, 220.0)
    saved[radius_squared < 12**2] = 0.0
    light = cv2.GaussianBlur(tone.linear_from_encoded(saved), (0, 0), 1.2)
    with pytest.raises(edges.EdgeError, match="in focus") as failure:
        edges.subpixel_rings(material.astype(np.uint8), light, 1.0)
    assert str(failure.value) == GUIDANCE


@pytest.mark.parametrize("clear_part", [160, 201], ids=["stronger-contrast", "zero-blur-estimate"])
def test_weak_capture_api_guidance_and_subsequent_valid_trace(
    weak_capture, clear_part, monkeypatch, tmp_path
):
    monkeypatch.setattr(api, "JOB_ROOT", tmp_path / "jobs")
    with TestClient(api.app) as client:
        rejected = client.post(
            "/api/trace",
            files={"file": ("weak.png", weak_capture, "image/png")},
            data={"reference": "a4"},
        )
        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["detail"] == GUIDANCE

        clear = S.colour_photo((185,) * 3, (220,) * 3, (clear_part,) * 3, ppm=3.0, blur=1.2)
        recovered = client.post(
            "/api/trace",
            files={"file": ("clear.png", clear, "image/png")},
            data={"reference": "a4"},
        )
        assert recovered.status_code == 200, recovered.text
        profile = recovered.json()["profile"]
        measured = profile["reference"]
        assert measured["kind"] == "a4"
        assert len(profile["holes"]) == 1
        (outer,), ((hole,),) = profile["primitives"]["outer"], profile["primitives"]["holes"]
        assert outer["kind"] == hole["kind"] == "circle"
        assert abs(2 * outer["radius"] * measured["mm_per_px"] - 60) < 0.03
        assert abs(2 * hole["radius"] * measured["mm_per_px"] - 16) < 0.03
        if clear_part == 201:
            # An unavailable blur estimate is still a valid median-level trace.
            assert measured["edge_blur_mm"] == 0.0
