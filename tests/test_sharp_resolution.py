"""Independent direct-helper fixture; not a full-photo reachability claim."""

import math

import numpy as np
import pytest

from backend import fitting


def wide_wedge_inputs(nodes=80, amplitude=0.3):
    """Arguments for real _exact_fillet, from an independently blurred sharp wedge.

    Material is y >= tan(beta/2)*abs(x), beta=.09 rad (>5 degrees).
    The bounded deterministic error is correlated, so its RMS is supplied only
    to exercise the existing noise heuristic. No inference-SD assertion is made.
    """
    beta, sigma = 0.09, 0.7
    epsilon = beta / 2
    slope = math.tan(epsilon)
    x = np.linspace(-5 * sigma, 5 * sigma, 81)
    q, w = np.polynomial.legendre.leggauss(nodes)
    left, right = x - 10 * sigma, x + 10 * sigma
    split = np.clip(0, left, right)
    lo, hi = np.column_stack((left, split)), np.column_stack((split, right))
    t = (lo + hi)[..., None] / 2 + (hi - lo)[..., None] * q / 2
    weights = (hi - lo)[..., None] * w / 2
    density = np.exp(-0.5 * ((t - x[:, None, None]) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))

    def cdf(z):
        return np.frompyfunc(lambda a: 0.5 * math.erfc(-a / math.sqrt(2)), 1, 1)(z).astype(float)

    # Separate the integral at the only nonsmooth point; truncated tail <2e-23.
    bottom, top = slope * abs(x), slope * abs(x) + sigma
    for _ in range(48):
        y = (bottom + top) / 2
        level = (weights * density * cdf((y[:, None, None] - slope * abs(t)) / sigma)).sum(axis=(1, 2))
        bottom, top = np.where(level < 0.5, y, bottom), np.where(level >= 0.5, y, top)
    quiet = np.column_stack((x, (bottom + top) / 2))
    middle = len(x) // 2
    z = (quiet[middle, 1] - slope * abs(t[middle])) / sigma
    uy = (weights[middle] * density[middle] * np.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))).sum()
    uxx = (weights[middle] * density[middle] * (t[middle] ** 2 / sigma**4 - 1 / sigma**2) * cdf(z)).sum()
    # Independent osculating radius of the quiet half-level contour at x=0.
    seed = float(-uy / uxx)
    error = amplitude * np.sin(2 * math.pi * x / (2.5 * sigma))
    measured = quiet + np.column_stack((np.zeros(len(x)), error))
    lines = ((np.zeros(2), np.array([-math.cos(epsilon), math.sin(epsilon)])),
             (np.zeros(2), np.array([math.cos(epsilon), math.sin(epsilon)])))
    inward = (np.array([math.sin(epsilon), math.cos(epsilon)]),
              np.array([-math.sin(epsilon), math.cos(epsilon)]))
    return {"seg": measured, "lines": lines, "v": np.array([0.0, 1 / math.cos(epsilon)]),
            "inward": inward, "r": seed, "sigma": sigma,
            "noise": float(np.sqrt(np.mean(error**2))), "correlation": 1.0}, quiet


def separation_at(kwargs, radius):
    """Evaluate the declared numerical crossing contract, using its frozen gradient."""
    beta = 0.09
    seg, seed, sigma = kwargs["seg"], kwargs["r"], kwargs["sigma"]
    start = -math.pi / 2 - beta / 2

    def level(r, at=seg):
        return fitting.corner_level(at, r * kwargs["v"], r, start, beta, sigma)

    h = 0.1 * sigma
    gradient = np.hypot(level(seed, seg + [h, 0]) - level(seed, seg - [h, 0]),
                        level(seed, seg + [0, h]) - level(seed, seg - [0, h])) / (2 * h)
    return float(np.max(np.abs(level(radius) - level(0)) / gradient))


@pytest.mark.parametrize("nodes", [80, 160])
def test_exhausted_radius_resolution_search_is_unresolved(nodes):
    kwargs, _ = wide_wedge_inputs(nodes=nodes, amplitude=0.3)
    # The original endpoint (~311.8px) is below the ~436.5px crossing. A budget
    # limit is not a root bracket; the existing failure sentinel keeps it unknown.
    assert fitting._exact_fillet(**kwargs) is None


def test_final_doubled_endpoint_preserves_a_real_crossing():
    kwargs, _ = wide_wedge_inputs(amplitude=0.2)
    result = fitting._exact_fillet(**kwargs)
    assert result is not None
    _, _, rms, _, resolution = result
    floor = 2 * max(rms, kwargs["noise"], fitting.EDGE_SYS_SD)
    assert resolution is not None and math.isfinite(resolution)
    # This valid crossing is beyond the last checked endpoint in the old loop,
    # but inside the final doubled interval. Do not discard it with for/else.
    assert 8 * kwargs["r"] < resolution < 16 * kwargs["r"]
    assert separation_at(kwargs, resolution) >= floor


def test_independent_wedge_quadrature_converges():
    low, a = wide_wedge_inputs(nodes=80)
    high, b = wide_wedge_inputs(nodes=160)
    np.testing.assert_allclose(a, b, rtol=0, atol=2e-13)
    assert abs(low["r"] - high["r"]) < 1e-8
    assert math.degrees(0.09) > 5


@pytest.mark.parametrize("seed_multiple", [1.0, 2.5])
def test_failed_exact_fit_keeps_positive_geometry_visibly_unresolved(monkeypatch, seed_multiple):
    kwargs, _ = wide_wedge_inputs()
    points, v = kwargs["seg"], kwargs["v"]
    seed = seed_multiple * kwargs["r"]
    lines = [fitting.Primitive("line", {"c": tuple(c), "d": tuple(d)},
                               kwargs["noise"], 0.3, span)
             for (c, d), span in zip(kwargs["lines"], [(0, 25), (55, 80)])]
    arc = fitting.Primitive("arc", {"c": tuple(seed * v), "r": seed,
                                    "mid": tuple(seed * v - [0, seed])},
                            0.01, 0.02, (25, 55))
    calls = []

    def unresolved(*args, **kw):
        calls.append(True)

    monkeypatch.setattr(fitting, "_exact_fillet", unresolved)
    prims = [lines[0], arc, lines[1]]
    fitting.fit_fillets(points, prims, tol=0.01, sigma=kwargs["sigma"])
    assert calls
    assert arc in prims and arc.data["r"] > 0
    if seed_multiple > 1:
        # The geometric approximate fit is outside its acceptance range, so the
        # observed seed must survive; the successful approximate control may move.
        assert arc.data["r"] == seed
    assert arc.data.get("r_sd") == math.inf
    assert "sharp_bound" not in arc.data
    assert "could not settle" in fitting.undetermined_radii([prims], kwargs["sigma"])[0]


def test_sharp_note_describes_model_resolution_not_a_physical_upper_bound():
    line = fitting.Primitive("line", {"sharp_bound": 1.25}, 0.0, 0.0)
    (note,) = fitting.undetermined_radii([[line]], sigma=1.5, scale=0.2)
    assert "assumed blur" in note
    assert "resolution" in note
    assert "R0.25 mm" in note
    assert "Measure" in note
    assert "any fillet" not in note and "under R" not in note
