"""Independent containment checks for the continuous-angle bed solver."""

import math
import random

import numpy as np
import pytest
from shapely.affinity import rotate, translate
from shapely.geometry import MultiPoint, Polygon, box

from backend.models import DesignSettings
from backend.placement import FIT_TOLERANCE_MM, rectangular_placement
from backend.printing import bed_fit


def assert_witness(polygon, width, depth, witness):
    assert witness is not None
    assert 0 <= witness["rotation_deg"] < 180
    # GEOS/Shapely rotation is independent of the solver's support coefficients.
    x0, y0, x1, y1 = rotate(polygon, witness["rotation_deg"], origin=(0, 0)).bounds
    assert x1 - x0 <= width + FIT_TOLERANCE_MM
    assert y1 - y0 <= depth + FIT_TOLERANCE_MM
    assert witness["footprint_mm"] == pytest.approx({"width": x1 - x0, "depth": y1 - y0})


def test_diagonal_bar_fits_without_splitting_or_rescaling():
    part = box(0, 0, 125, 10)
    witness = rectangular_placement(part, 100, 100)
    assert_witness(part, 100, 100, witness)
    assert 0 < witness["rotation_deg"] < 90
    # The minimum-area bounding rectangle (125 x 10) itself does not fit this bed.
    assert witness["footprint_mm"]["width"] < 100


@pytest.mark.parametrize("source_angle", [0.1234567, 17.1234567, 67.8912345, 123.456789])
def test_exact_fit_at_an_angle_an_angular_grid_would_miss(source_angle):
    part = rotate(box(0, 0, 100, 20), source_angle, origin=(0, 0))
    witness = rectangular_placement(part, 100, 20)
    assert_witness(part, 100, 20, witness)
    assert witness["rotation_deg"] == pytest.approx(180 - source_angle, abs=1e-7)
    assert rectangular_placement(part, 100 - 1e-4, 20 - 1e-4) is None


def test_actual_outline_can_fit_where_its_source_bounding_rectangle_cannot():
    part = rotate(box(0, 0, 80, 10), 45, origin=(0, 0))
    witness = rectangular_placement(part, 80, 20)
    assert_witness(part, 80, 20, witness)
    assert rectangular_placement(box(*part.bounds), 80, 20) is None


def test_concavity_holes_and_coordinate_translation_do_not_change_containment():
    part = Polygon(
        [(0, 0), (100, 0), (100, 10), (10, 10), (10, 45), (0, 45)],
        holes=[[(2, 2), (8, 2), (8, 8), (2, 8)]],
    )
    part = rotate(part, 23, origin=(0, 0))
    witness = rectangular_placement(part, 105, 60)
    assert_witness(part, 105, 60, witness)
    moved = translate(part, xoff=100_000, yoff=-100_000)
    moved_witness = rectangular_placement(moved, 105, 60)
    assert moved_witness["rotation_deg"] == pytest.approx(witness["rotation_deg"], abs=1e-8)
    assert moved_witness["footprint_mm"] == pytest.approx(witness["footprint_mm"])


def test_unusable_envelope_and_too_large_polygon_are_refused():
    part = box(0, 0, 110, 110)
    for width, depth in [(100, 100), (0, 100), (100, -1)]:
        assert rectangular_placement(part, width, depth) is None


def test_seeded_polygons_recover_known_feasible_placements_and_validate_dense_oracle():
    rng = random.Random(20261111)
    angles = np.linspace(0, math.pi, 3601)
    co, si = np.cos(angles), np.sin(angles)
    for _ in range(30):
        hull = MultiPoint(
            [(rng.uniform(-70, 70), rng.uniform(-20, 20)) for _ in range(20)]
        ).convex_hull
        part = rotate(hull, rng.uniform(0, 180), origin=(0, 0))
        # This constructed bed has at least one exact (unsampled) feasible rotation.
        target = rotate(part, rng.uniform(0, 180), origin=(0, 0))
        x0, y0, x1, y1 = target.bounds
        assert_witness(part, x1 - x0, y1 - y0, rectangular_placement(part, x1 - x0, y1 - y0))
        width, depth = rng.uniform(25, 110), rng.uniform(25, 75)
        xy = np.asarray(part.exterior.coords[:-1])
        widths = np.ptp(xy[:, 0, None] * co - xy[:, 1, None] * si, axis=0)
        depths = np.ptp(xy[:, 0, None] * si + xy[:, 1, None] * co, axis=0)
        witness = rectangular_placement(part, width, depth)
        if np.any((widths <= width) & (depths <= depth)):
            assert witness is not None  # Never miss a placement the dense oracle found.
        if witness is not None:
            assert_witness(part, width, depth, witness)


def test_fit_reports_exact_outline_and_conservative_curve_results_separately():
    part = rotate(box(0, 0, 80, 10), 45, origin=(0, 0))
    x0, y0, x1, y1 = part.bounds
    dimensions = {"width": x1 - x0, "height": y1 - y0, "thickness": 4}
    design = DesignSettings(bed_width_mm=90, bed_depth_mm=30, bed_margin_mm=5)
    exact = bed_fit(dimensions, design, footprint=part)
    assert exact["status"] == "fits" and exact["basis"] == "outline"
    assert_witness(part, 80, 20, exact)
    fallback = bed_fit(dimensions, design)
    assert fallback["status"] == "unknown" and fallback["basis"] == "bounding_box"
    assert "curved outline" in fallback["reason"]
    assert "rotation_deg" not in fallback
    assert bed_fit({**dimensions, "thickness": 251}, design)["status"] == "too_large"
    assert (
        bed_fit(dimensions, design.model_copy(update={"bed_margin_mm": 30}))["status"]
        == "too_large"
    )


def test_bounding_rectangle_witness_encloses_fitted_geometry_and_preserves_legacy_turn():
    design = DesignSettings(bed_width_mm=100, bed_depth_mm=200, bed_margin_mm=5)
    dims = {"width": 150, "height": 80, "thickness": 5}
    result = bed_fit(dims, design)
    assert result["status"] == "fits" and result["rotated_90"]
    assert result["basis"] == "bounding_box" and result["rotation_deg"] == 90
    assert_witness(box(0, 0, 150, 80), 90, 190, result)
