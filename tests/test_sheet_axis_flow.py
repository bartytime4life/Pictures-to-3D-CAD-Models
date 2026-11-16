"""Ambiguous calibration is an actionable API refusal, including fallback requests."""

import io
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import app as api
from backend import sheet


@pytest.mark.parametrize("fallback", [False, True])
def test_ambiguous_detected_sheet_cannot_fall_back_to_an_uncorrected_profile(monkeypatch, fallback):
    # Exact single-axis pinhole geometry has two positive-focal explanations at
    # 70 degrees. Detection is supplied here to isolate API/error propagation;
    # neither the homography nor its ambiguity test is mocked.
    angle = math.radians(70)
    rotation = np.array([
        [1, 0, 0], [0, math.cos(angle), -math.sin(angle)],
        [0, math.sin(angle), math.cos(angle)],
    ])
    k = np.array([[1980, 0, 1200], [0, 1980, 900], [0, 0, 1]])
    t = np.array([0, 0, 440]) - rotation @ np.array([105, 148.5, 0])
    camera = k @ np.column_stack([rotation[:, :2], t])
    plane = np.array([[0, 0], [210, 0], [210, 297], [0, 297]])

    def project(points):
        rays = np.column_stack([points, np.ones(len(points))]) @ camera.T
        return rays[:, :2] / rays[:, 2:]

    fraction = np.linspace(0.1, 0.9, 30)[:, None]
    sides = [
        project((1 - fraction) * plane[i] + fraction * plane[(i + 1) % 4])
        for i in range(4)
    ]
    found = sheet.Sheet(project(plane), sides, 1)
    monkeypatch.setattr(sheet, "find_sheet", lambda *args: found)
    monkeypatch.setattr(sheet, "estimate_k1", lambda *args: (0.0, 0.0, 0.0))
    photo = io.BytesIO()
    Image.new("RGB", (2400, 1800), "white").save(photo, "PNG")
    with TestClient(api.app) as client:
        response = client.post(
            "/api/trace", files={"file": ("sheet.png", photo.getvalue(), "image/png")},
            data={"reference": "a4", "fallback": str(fallback).lower()},
        )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "does not identify which reference-sheet edge" in detail
    assert "overhead" in detail
    assert "profile" not in response.json()
