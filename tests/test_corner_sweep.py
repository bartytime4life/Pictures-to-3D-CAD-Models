"""Smoke test of scripts/corner_sweep.py, the exact-blur corner sweep behind the fillet
results in docs/reference-sheet.md (section 4) and docs/validation.md."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np

from backend import fitting


def load_sweep():
    path = Path(__file__).resolve().parents[1] / "scripts" / "corner_sweep.py"
    spec = importlib.util.spec_from_file_location("corner_sweep", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_its_blur_matches_the_closed_forms_and_the_fit_recovers_every_corner():
    """The slice integral gives 1 - exp(-R^2/2s^2) at a disc's centre, and the half-level
    of a long straight edge on the edge itself. On one pentagon (90 and 120 degree
    corners, r = 5 sigma) the fitting chain keeps every corner as one arc within 0.1 s."""
    sweep = load_sweep()
    radius, sigma = 10.0, 2.0
    disc = sweep.RoundedPolygon([(-radius, -radius), (radius, -radius), (radius, radius), (-radius, radius)], radius)
    centre = sweep.blurred(disc, np.array([[0.0, 0.0]]), sigma)[0]
    assert abs(centre - (1 - math.exp(-radius * radius / (2 * sigma * sigma)))) < 1e-10
    square = sweep.RoundedPolygon([(0, 0), (200, 0), (200, 200), (0, 200)], 10.0)
    offsets = sweep.half_level(square, np.array([[100.0, 0.0], [200.0, 100.0]]), np.array([[0.0, -1.0], [1.0, 0.0]]), sigma)
    assert np.abs(offsets).max() < 1e-8
    case = sweep.run_case(fitting, 120, 8.0, 1.6)
    assert case["kinds"] == "LA" * 5
    assert all(c["kind"] == "arc" and abs(c["error_s"]) < 0.1 for c in case["corners"])
