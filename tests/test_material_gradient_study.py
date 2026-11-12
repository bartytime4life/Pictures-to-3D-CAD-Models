"""Independent numerical checks for the frozen material-gradient research runner.

The convolution oracle integrates the bounded, piecewise-affine SOURCE against
a Gaussian using segmented Gauss-Legendre rules. Only constant real tails use
stdlib erfc masses. It does not use the runner's truncated-normal moments,
production CDFs, renderer, or slope correction as its probability oracle.
Convergence is a numerical development check, not physical qualification.
"""

import copy
import itertools
import json
import math
from functools import lru_cache

import numpy as np
import pytest

from scripts import material_gradient_study as study


@lru_cache(maxsize=4)
def quadrature(order):
    return np.polynomial.legendre.leggauss(order)


def bounded_source(u, sigma, condition, tail_sigmas):
    """Specified real source, before Gaussian convolution or pixel integration."""
    limit = tail_sigmas * sigma
    u = np.asarray(u, dtype=float)
    material = condition["material"] + condition["material_slope"] * np.maximum(u, -limit)
    paper = condition["paper"] + condition["paper_slope"] * np.minimum(u, limit)
    values = np.where(u < 0, material, paper)
    if "wall" in condition:
        width = sigma * condition["wall_width_sigmas"]
        values = np.where((u >= -width) & (u < 0), condition["wall"], values)
    return values


def convolution_oracle(t, sigma, condition, *, tail_sigmas=12, order=16):
    """Integrate the bounded source over the whole real line independently."""
    t = np.asarray(t, dtype=float)
    limit = tail_sigmas * sigma
    landmarks = [-limit, 0., limit]
    if "wall" in condition:
        landmarks.append(-sigma * condition["wall_width_sigmas"])
    landmarks = sorted(set(landmarks))
    left, right = landmarks[0], landmarks[-1]
    # Outside the landmarks the source is constant, so real tails are exact
    # erfc expressions, rather than numerical truncation at a finite window.
    left_mass = np.array([.5 * math.erfc((x - left) / (sigma * math.sqrt(2)))
                          for x in t.flat]).reshape(t.shape)
    right_mass = np.array([.5 * math.erfc((right - x) / (sigma * math.sqrt(2)))
                           for x in t.flat]).reshape(t.shape)
    result = (float(bounded_source(left - sigma, sigma, condition, tail_sigmas)) * left_mass
              + float(bounded_source(right + sigma, sigma, condition, tail_sigmas)) * right_mass)
    nodes, weights = quadrature(order)
    for lo, hi in itertools.pairwise(landmarks):
        # Each cell has width <=sigma. Partitioning at every discontinuity and
        # affine-source join avoids asking a rule to integrate across a wall.
        cells = max(1, math.ceil((hi - lo) / sigma))
        cuts = np.linspace(lo, hi, cells + 1)
        for a, b in itertools.pairwise(cuts):
            u = (a + b) / 2 + (b - a) / 2 * nodes
            source = bounded_source(u, sigma, condition, tail_sigmas)
            kernel = np.exp(-.5 * ((u - t[..., None]) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
            result += np.sum(kernel * source * weights, axis=-1) * (b - a) / 2
    return result


def condition(**changes):
    return {"name": "independent", "material": 90., "paper": 170.,
            "material_slope": 1., "paper_slope": -1., **changes}


def plan():
    return json.loads(study.PLAN.read_text())


@pytest.mark.parametrize("source", [
    condition(material_slope=0, paper_slope=0),
    condition(material_slope=1, paper_slope=.5),
    condition(material_slope=-1, paper_slope=1),
    condition(material=170, paper=90, material_slope=1, paper_slope=-1),
    condition(material_slope=0, paper_slope=0, wall=130, wall_width_sigmas=1.5),
    condition(material_slope=0, paper_slope=0, wall=55, wall_width_sigmas=1.5),
    condition(material_slope=0, paper_slope=0, wall=130, wall_width_sigmas=12),
])
@pytest.mark.parametrize("sigma,tail_sigmas", [(1.2, 12), (2.4, 12), (.6, 2)])
def test_truncated_affine_profiles_match_real_source_convolution(source, sigma, tail_sigmas):
    limit = sigma * tail_sigmas
    t = np.array([-2 * limit, -limit - sigma, -limit, -limit + sigma,
                  -.1 * sigma, 0, .1 * sigma, limit - sigma, limit, limit + sigma, 2 * limit])
    coarse = convolution_oracle(t, sigma, source, tail_sigmas=tail_sigmas, order=8)
    reference = convolution_oracle(t, sigma, source, tail_sigmas=tail_sigmas, order=16)
    assert np.max(np.abs(coarse - reference)) < 3e-12
    actual = study.blurred_profile(t, sigma, source, tail_sigmas=tail_sigmas)
    assert np.max(np.abs(actual - reference)) < 3e-12


@pytest.mark.parametrize("source", [
    condition(material=12, paper=243, material_slope=1, paper_slope=1),
    condition(material=243, paper=12, material_slope=-1, paper_slope=-1),
    condition(material=0, paper=255, material_slope=0, paper_slope=0),
])
def test_source_endpoints_at_zero_and_255_remain_valid_bounded_profiles(source):
    t = np.array([-24., -12., -11.9, -.1, 0, .1, 11.9, 12., 24.])
    reference = convolution_oracle(t, 1., source)
    actual = study.blurred_profile(t, 1., source)
    assert np.min(actual) >= -3e-12 and np.max(actual) <= 255 + 3e-12
    assert np.max(np.abs(actual - reference)) < 3e-12


@pytest.mark.parametrize("source", [condition(), condition(material_slope=0, paper_slope=0,
                                                           wall=130, wall_width_sigmas=1.5)])
@pytest.mark.parametrize("t", [-30., -1.5, 0., .3, 30.])
def test_scalar_profile_api_agrees_with_array_and_independent_integral(source, t):
    scalar = study.blurred_profile(t, 1.2, source)
    assert np.shape(scalar) == ()
    assert float(scalar) == float(study.blurred_profile(np.array([t]), 1.2, source)[0])
    assert abs(float(scalar) - float(convolution_oracle(t, 1.2, source))) < 3e-12


def test_invalid_source_endpoints_and_nonflat_wall_controls_are_refused():
    for source in [condition(material=1, material_slope=1),
                   condition(paper=254, paper_slope=1),
                   condition(wall=130, wall_width_sigmas=1.5)]:
        with pytest.raises(ValueError):
            study.blurred_profile(np.array([0., 1.]), 1.2, source)


def test_rendered_point_and_square_aperture_means_match_the_independent_convolution():
    source, sigma, size = condition(), 1.2, 5
    normal, centre = np.array([.6, .8]), np.array([2.3, 2.7])
    yy, xx = np.mgrid[:size, :size]
    t = (xx + .5 - centre[0]) * normal[0] + (yy + .5 - centre[1]) * normal[1]
    point = study.render(source, sigma, normal, centre, size)
    assert np.max(np.abs(point - convolution_oracle(t, sigma, source))) < 3e-12
    nodes, weights = quadrature(6)
    expected = np.zeros((size, size))
    for u, wu in zip(nodes / 2, weights / 2):
        for v, wv in zip(nodes / 2, weights / 2):
            expected += wu * wv * convolution_oracle(t + u * normal[0] + v * normal[1], sigma, source)
    actual = study.render(source, sigma, normal, centre, size, order=6)
    refined = study.render(source, sigma, normal, centre, size, order=12)
    assert np.max(np.abs(actual - expected)) < 3e-12
    assert np.max(np.abs(actual - refined)) < 1e-10
    constant = study.render(condition(material=111, paper=111, material_slope=0, paper_slope=0),
                            sigma, normal, centre, size, order=6)
    assert np.max(np.abs(constant - 111)) < 3e-12


def test_independent_srgb_encoding_quantizes_known_values_and_refuses_clipping():
    light = np.array([[0, .0031308 * 255, .18 * 255, 255]], dtype=float)
    encoded = study.encode_srgb8(light)
    assert encoded.dtype == np.uint8
    assert encoded.shape == (1, 4, 3)
    assert encoded[0, :, 0].tolist() == [0, 10, 118, 255]
    assert np.array_equal(encoded[:, :, 0], encoded[:, :, 1])
    assert np.array_equal(encoded[:, :, 1], encoded[:, :, 2])
    for invalid in (np.nan, np.inf, -1, 256):
        with pytest.raises(ValueError):
            study.encode_srgb8(np.array([[invalid]]))


@pytest.mark.parametrize("method", ["paper_only", "two_affine_ablation"])
@pytest.mark.parametrize("angle", [0, 45, 90])
def test_fixed_profile_geometry_is_invariant_to_global_affine_intensity(method, angle):
    config = plan()
    # Hold eligibility fixed: the production saved-contrast gate is intentionally
    # photometric and is not claimed to be invariant under arbitrary gains.
    config["minimum_saved_contrast"] = 0
    normal = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
    centre = np.full(2, 24.) + .25 * normal
    image = study.render(condition(), 2.4, normal, centre, 48)
    for sign in (-1, 1):
        expected = study.measure(image, centre, normal, 2.4, config, method=method, normal_sign=sign)
        assert expected["kept"]
        for offset, gain in ((30., .5), (-10., 1.25), (255., -1.)):
            actual = study.measure(offset + gain * image, centre, normal, 2.4, config,
                                   method=method, normal_sign=sign)
            assert actual["kept"]
            assert abs(actual["offset_px"] - expected["offset_px"]) < 3e-12


@pytest.mark.parametrize("method", ["paper_only", "two_affine_ablation"])
@pytest.mark.parametrize("sigma", [1.2, 2.4])
def test_normal_reversal_also_reverses_the_geometric_paper_side(method, sigma):
    config = plan()
    for angle, phase in itertools.product((0, 45, 90), (0, .25, .5, .75)):
        normal = np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
        centre = np.full(2, 24.) + phase * normal
        image = study.render(condition(), sigma, normal, centre, 48)
        positive = study.measure(image, centre, normal, sigma, config, method=method, normal_sign=1)
        negative = study.measure(image, centre, normal, sigma, config, method=method, normal_sign=-1)
        assert positive["kept"] is negative["kept"] is True
        assert abs(positive["offset_px"] - negative["offset_px"]) < 3e-12


@pytest.mark.parametrize("method", ["paper_only", "two_affine_ablation"])
def test_noninteger_profile_window_is_symmetric_under_normal_reversal(method):
    config, sigma = plan(), 1.37
    normal = np.array([math.sqrt(.5), math.sqrt(.5)])
    centre = np.full(2, 24.) + .5 * normal
    yy, xx = np.mgrid[:48, :48]
    t = (xx + .5 - centre[0]) * normal[0] + (yy + .5 - centre[1]) * normal[1]
    source = condition(material_slope=-1, paper_slope=-1)
    image = 255 - convolution_oracle(t, sigma, source)
    # 5sigma/step=54.8: a grid started at-reach cannot both include0 and mirror
    # its samples. Reversing the supplied normal must not change the physical
    # profile or its crossing, including when the paper-side sign is reversed.
    positive = study.measure(image, centre, normal, sigma, config, method=method, normal_sign=1)
    negative = study.measure(image, centre, normal, sigma, config, method=method, normal_sign=-1)
    assert positive["kept"] is negative["kept"] is True
    assert abs(positive["offset_px"] - negative["offset_px"]) < 3e-12


def test_material_gradient_bias_is_retained_as_a_limitation_not_hidden_by_the_study():
    config, sigma = plan(), 2.4
    normal, centre = np.array([1., 0.]), np.array([24.25, 24.])
    image = study.render(condition(material_slope=1, paper_slope=0), sigma, normal, centre, 48)
    production = study.measure(image, centre, normal, sigma, config, method="paper_only", normal_sign=1)
    ablation = study.measure(image, centre, normal, sigma, config, method="two_affine_ablation", normal_sign=1)
    assert production["kept"] is ablation["kept"] is True
    assert production["offset_px"] < -.1
    assert abs(ablation["offset_px"]) < .02
    assert abs(production["offset_px"]) > 5 * abs(ablation["offset_px"])
    # This control has no wall. It is not evidence that material-side flattening
    # can be removed where a narrow wall contaminates the same profile region.


def test_summary_preserves_rejections_failures_and_groups_with_no_kept_offsets():
    rows = []
    for name, offset, error in [("mixed", .1, None), ("mixed", -.2, None),
                                ("mixed", None, None), ("mixed", None, "ValueError: injected"),
                                ("none_kept", None, None), ("none_kept", None, "ValueError: injected")]:
        rows.append({"stage": "point_known_sigma", "condition": name, "method": "paper_only",
                     "kept": offset is not None, "offset_px": offset, "error": error})
    summary = study.summarize(rows)
    by_condition = {row["condition"]: row for row in summary}
    mixed, missing = by_condition["mixed"], by_condition["none_kept"]
    assert (mixed["cases"], mixed["kept"], mixed["rejected"], mixed["failed"]) == (4, 2, 1, 1)
    assert mixed["mean_offset_px"] == pytest.approx(-.05)
    assert mixed["min_offset_px"] == -.2 and mixed["max_offset_px"] == .1
    assert mixed["max_abs_offset_px"] == .2
    assert (missing["cases"], missing["kept"], missing["rejected"], missing["failed"]) == (2, 0, 1, 1)
    for key in ("min_offset_px", "max_offset_px", "max_abs_offset_px", "mean_offset_px"):
        assert missing[key] is None
    assert sum(row["cases"] for row in summary) == len(rows)
    assert all(row["cases"] == row["kept"] + row["rejected"] + row["failed"] for row in summary)


def test_small_crossed_run_keeps_failed_and_rejected_measurements(monkeypatch):
    config = copy.deepcopy(plan())
    config.update(conditions=[condition(name="flat", material_slope=0, paper_slope=0),
                              condition(name="low", material=120, paper=125, material_slope=0, paper_slope=0)],
                  sigmas_px=[1.2], normal_angles_degrees=[0], normal_phases_px=[.25],
                  contrast_inversions=[False], stages=["point_known_sigma"])
    original = study.measure

    def one_method_fails(*args, **kwargs):
        if kwargs["method"] == "two_affine_ablation":
            raise ValueError("independent injected measurement failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(study, "measure", one_method_fails)
    rows, change = study.run_study(config)
    assert len(rows) == 8
    assert sum(row["kept"] for row in rows) == 2
    assert sum(row["error"] is not None for row in rows) == 4
    assert sum(not row["kept"] and row["error"] is None for row in rows) == 2
    assert all(row["offset_px"] is None for row in rows if not row["kept"])
    assert change <= config["quadrature_check_tolerance"]
    assert sum(group["cases"] for group in study.summarize(rows)) == 8


def test_existing_output_directory_is_refused_before_any_study_execution(tmp_path, monkeypatch):
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "owner.txt"
    sentinel.write_text("preserve this result\n")

    def must_not_run(*args, **kwargs):
        pytest.fail("an existing output directory must be refused before running the census")

    monkeypatch.setattr(study, "run_study", must_not_run)
    with pytest.raises(SystemExit) as error:
        study.main(["--output", str(destination)])
    assert error.value.code == 2
    assert sentinel.read_text() == "preserve this result\n"
    assert sorted(path.name for path in destination.iterdir()) == ["owner.txt"]
