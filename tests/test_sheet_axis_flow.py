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
@pytest.mark.parametrize("tilt,focal,distance,seed", [
    ((70, 0, 0), 1980, 440, None),
    ((75, 0.1, 4), 5000, 2000, 25),
], ids=["exact-ambiguous", "noisy-weak-perspective"])
def test_ambiguous_detected_sheet_cannot_fall_back_to_an_uncorrected_profile(
    monkeypatch, fallback, tilt, focal, distance, seed
):
    # The exact view has two positive-focal explanations; tiny edge errors in
    # the weak two-axis view formerly produced a wrong but accepted scale.
    # Supply detection to isolate API/error propagation, leaving the real
    # homography and its sensitivity check active.
    x, y, z = map(math.radians, tilt)
    rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    rotation = rz @ rx @ ry
    k = np.array([[focal, 0, 1200], [0, focal, 900], [0, 0, 1]])
    t = np.array([0, 0, distance]) - rotation @ np.array([105, 148.5, 0])
    camera = k @ np.column_stack([rotation[:, :2], t])
    camera /= camera[2, 2]
    plane = np.array([[0, 0], [210, 0], [210, 297], [0, 297]])

    def project(points):
        rays = np.column_stack([points, np.ones(len(points))]) @ camera.T
        return rays[:, :2] / rays[:, 2:]

    fraction = np.linspace(0.08, 0.92, 37)[:, None]
    sides = [
        project((1 - fraction) * plane[i] + fraction * plane[(i + 1) % 4])
        for i in range(4)
    ]
    if seed is not None:
        rng = np.random.default_rng(seed)
        sides = [side + rng.normal(0, 0.05, side.shape) for side in sides]
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
    assert "original uncropped photo" in detail
    assert "profile" not in response.json()
