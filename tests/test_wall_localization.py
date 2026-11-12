"""Independent wall profiles, abstention, resource bounds and actual-call-path regressions."""

import json
import math
from types import SimpleNamespace

import numpy as np
import pytest

from backend import edges, reference
from scripts import wall_localization_study as study


def normal_cdf(values):
    values = np.asarray(values)
    return np.asarray([0.5 * math.erfc(-x / math.sqrt(2)) for x in values.flat]).reshape(values.shape)


def supplied_profile(monkeypatch, band=3.2, sigma=1.2, offset=2.6, rate=0.05,
                     top=90.0, wall=150.0, paper=170.0):
    """Replace only sampling with an independently specified continuum profile."""
    width = max(band - rate * offset, 0)

    def sample(image, x, y):
        t = x - 80
        left = normal_cdf((t + width - offset) / sigma)
        right = normal_cdf((t - offset) / sigma)
        return top * (1 - left) + wall * (left - right) + paper * right

    monkeypatch.setattr(edges, "sample_keys", sample)
    return np.zeros((80, 180)), np.asarray([[80.5, 40.5]]), np.asarray([[1., 0.]])


@pytest.mark.parametrize("wall", [110., 130., 150., 165.])
@pytest.mark.parametrize("rate", [0., 0.05])
def test_bright_wall_position_beyond_old_search_is_recovered(monkeypatch, wall, rate):
    image, points, normals = supplied_profile(monkeypatch, wall=wall, rate=rate)
    moved, tones, rss = edges.two_step_refine(image, points, normals, np.asarray([3.2]), 1.2,
                                              band_rate=rate, with_residuals=True)
    assert moved[0, 0] - points[0, 0] == pytest.approx(2.6, abs=4e-6)
    assert tones[0] == pytest.approx(wall, abs=0.0003)
    assert 0 <= rss[0] < 1e-6


@pytest.mark.parametrize("band", [0.01, 0.03, 3.2])
@pytest.mark.parametrize("rate", [0., 0.05])
@pytest.mark.parametrize("levels", [(90., 170.), (0., 255.), (255., 0.)])
def test_exact_single_step_interpretations_remain_unresolved(monkeypatch, band, rate, levels):
    top, paper = levels
    image, points, normals = supplied_profile(monkeypatch, band=band, sigma=1., offset=0.,
                                              rate=rate, top=top, wall=top, paper=paper)
    moved, tones, rss = edges.two_step_refine(image, points, normals, np.asarray([band]), 1.,
                                              band_rate=rate, with_residuals=True)
    assert np.array_equal(moved, points)
    assert np.isnan(tones[0]) and rss[0] == math.inf


def test_an_independently_fixed_tone_is_a_different_conditional_problem(monkeypatch):
    image, points, normals = supplied_profile(monkeypatch, offset=0., wall=90.)
    moved, tones, rss = edges.two_step_refine(image, points, normals, np.asarray([3.2]), 1.2,
                                              wall_tone=90., band_rate=0.05, with_residuals=True)
    assert moved[0, 0] == pytest.approx(points[0, 0], abs=4e-6)
    assert tones[0] == 90. and rss[0] < 1e-6


@pytest.mark.parametrize("offset", [-0.72, 8.])
def test_endpoint_or_out_of_range_minimum_is_not_moved_inward(monkeypatch, offset):
    image, points, normals = supplied_profile(monkeypatch, offset=offset, rate=0.)
    moved, tones, rss = edges.two_step_refine(image, points, normals, np.asarray([3.2]), 1.2,
                                              wall_tone=150., with_residuals=True)
    assert np.array_equal(moved, points)
    assert np.isnan(tones[0]) and rss[0] == math.inf


def test_flat_profile_preserves_the_seed(monkeypatch):
    image, points, normals = supplied_profile(monkeypatch, top=90., wall=90., paper=90.)
    moved, tones, rss = edges.two_step_refine(image, points, normals, np.asarray([3.2]), 1.2,
                                              with_residuals=True)
    assert np.array_equal(moved, points)
    assert np.isnan(tones[0]) and rss[0] == math.inf


def test_invalid_and_oversized_profiles_do_not_poison_an_independent_fit(monkeypatch):
    image, points, normals = supplied_profile(monkeypatch)
    points = np.repeat(points, 3, axis=0)
    normals = np.repeat(normals, 3, axis=0)
    moved, tones, rss = edges.two_step_refine(image, points, normals, np.asarray([math.nan, 1e9, 3.2]), 1.2,
                                              band_rate=0.05, with_residuals=True)
    assert np.array_equal(moved[:2], points[:2])
    assert np.isnan(tones[:2]).all() and np.isposinf(rss[:2]).all()
    assert moved[2, 0] - points[2, 0] == pytest.approx(2.6, abs=4e-6)


@pytest.mark.parametrize("band,sigma,step,rate", [(1e9, 1., .125, 0.), (1., 5e-324, .125, 0.),
                                                (1., 1., 5e-324, 0.), (1e308, 1., .125, 1e308)])
def test_oversized_search_is_rejected_before_image_sampling(monkeypatch, band, sigma, step, rate):
    def forbidden(*args):
        pytest.fail("oversized search reached sampling/allocation")
    monkeypatch.setattr(edges, "sample_keys", forbidden)
    points = np.asarray([[80.5, 40.5]])
    moved, tones, rss = edges.two_step_refine(np.zeros((2, 2)), points, np.asarray([[1., 0.]]),
                                              np.asarray([band]), sigma, step=step, band_rate=rate,
                                              with_residuals=True)
    assert np.array_equal(moved, points)
    assert np.isnan(tones[0]) and rss[0] == math.inf


def test_batching_retains_all_valid_profiles_under_a_small_work_budget(monkeypatch):
    image, points, normals = supplied_profile(monkeypatch)
    points, normals = np.repeat(points, 5, axis=0), np.repeat(normals, 5, axis=0)
    monkeypatch.setattr(edges, "MAX_WALL_BATCH_WORK", 32_000)
    actual = edges._wall_tone_parabolas
    sizes = []

    def checked(image, pts, *args, **kwargs):
        sizes.append(len(pts))
        return actual(image, pts, *args, **kwargs)

    monkeypatch.setattr(edges, "_wall_tone_parabolas", checked)
    moved, tones = edges.two_step_refine(image, points, normals, np.full(5, 3.2), 1.2, band_rate=0.05)
    assert sum(sizes) == 5 and max(sizes) == 1
    assert np.max(np.abs(moved[:, 0] - points[:, 0] - 2.6)) < 4e-6
    assert np.isfinite(tones).all()


@pytest.mark.parametrize("sigma", [.4, 1.2, 2.5])
def test_uniform_aperture_renderer_matches_independent_gaussian_quadrature(sigma):
    t = np.linspace(-10, 10, 41)
    nodes, weights = np.polynomial.legendre.leggauss(40)
    expected = (normal_cdf((t[:, None] + nodes / 2) / sigma) @ weights) / 2
    assert np.max(np.abs(study.edge_response(t, sigma, True) - expected)) < 8e-15


def test_quarter_turn_and_inverse_use_pixel_edge_coordinates():
    points = np.asarray([[.5, .5], [179.5, 159.5], [60.3, 80.3]])
    turned = study.transform(points, 1, 180)
    assert np.array_equal(turned[:2], [[.5, 179.5], [159.5, .5]])
    assert np.max(np.abs(study.transform(turned, 1, 180, inverse=True) - points)) < 1e-14


@pytest.mark.parametrize("wall", [110., 130., 150., 165.])
def test_actual_segmentation_to_wall_correction_handles_the_bright_wall_fixture(wall):
    plan = json.loads(study.PLAN.read_text())
    image, saved, camera, geometry = study.render_scene(plan, wall, 1.2, .3, 0, False, "point")
    result = study.run_pipeline((edges, reference), image, saved, camera, geometry, plan, 0, False)
    assert result["selected_points"] == 50
    assert result["maximum_absolute_error_px"] < .4
    if wall >= 130:
        assert result["initial_min_px"] > 1.7


def test_nonfinite_pipeline_output_is_an_execution_failure():
    plan = json.loads(study.PLAN.read_text())
    fake_edges = SimpleNamespace(segment=lambda *a, **kw: (None, []),
                                 subpixel_rings=lambda *a: ([{"outer": True, "points": np.asarray([[math.nan, 80.]])}], 1., 0))
    with pytest.raises(ArithmeticError, match="non-finite initial"):
        study.run_pipeline((fake_edges, reference), None, None, {}, (60., 130., 40., 120.), plan, 0, False)


def test_summary_does_not_hide_a_nonfinite_successful_case():
    row = {"wall_level": 130., "observation": "point"}
    for label in ("baseline", "candidate"):
        row.update({label + "_error": None, label + "_maximum_absolute_error_px": math.nan,
                    label + "_moved_selected_points": 0})
    with pytest.raises(ArithmeticError, match="non-finite successful"):
        study.summarize([row])
