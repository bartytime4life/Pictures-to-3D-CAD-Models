"""Independent Gaussian moment checks and a recorded current-model limitation.

Run: .venv/bin/python -m scripts.science_model_audit OUTPUT
Known model limitations are reported separately from verified algebraic identities.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

from backend import shadow, sheet


def half_normal_quadrature(order):
    nodes, weights = np.polynomial.legendre.leggauss(order)
    z = 5 * (nodes + 1)  # [0, 10], omitted polynomial-weighted tails below 1e-18 here
    return z, 5 * weights * np.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def quadratic_moments():
    cases = []
    for sigma in (0.7, 2.0, 4.0):
        for a, b in [
            ((20., 0., 0.), (180., 0., 0.)),
            ((20., 0.2, 0.), (180., -0.6, 0.)),
            ((20., 0.2, 0.03), (180., -0.6, -0.04)),
            ((50., -0.3, -0.02), (150., 0.8, 0.06)),
        ]:
            # I(0) = integral A(-sigma z) phi(z) + B(sigma z) phi(z), z >= 0.
            numerical = []
            for order in (128, 256):
                z, w = half_normal_quadrature(order)
                u = sigma * z
                numerical.append(float(w @ (a[0] - a[1]*u + a[2]*u*u + b[0] + b[1]*u + b[2]*u*u)))
            sharp = (a[0] + b[0])/2 + (b[1] - a[1])*sigma/math.sqrt(2*math.pi) + (a[2] + b[2])*sigma*sigma/2
            # Observed full-plateau quadratics already contain sigma^2 times curvature.
            observed = (a[0] + a[2]*sigma*sigma + b[0] + b[2]*sigma*sigma)/2 + (b[1] - a[1])*sigma/math.sqrt(2*math.pi)
            cases.append({
                "sigma_px": sigma, "material_coefficients": a, "paper_coefficients": b,
                "quadrature_256": numerical[1], "analytic_sharp": sharp,
                "analytic_observed_plateaus": observed,
                "quadrature_error": abs(numerical[1] - sharp),
                "order_doubling_difference": abs(numerical[1] - numerical[0]),
            })
    return cases


def tangential_light_counterexample():
    # Locally straight vertical edge, material on x < 60.5, paper on x > 60.5.
    # Paper light L(x,y)=180+(y-50.5), Gaussian covariance [[4,3],[3,9]] px^2.
    covariance = np.array([[4., 3.], [3., 9.]])
    normal = np.array([1., 0.])
    slope = np.array([0., 1.])
    sigma = math.sqrt(float(normal @ covariance @ normal))
    exact = 100 + float(slope @ covariance @ normal) / (sigma * math.sqrt(2*math.pi))
    z, w = half_normal_quadrature(256)
    # Conditional tangential mean is (Sigma_yx/sigma) z; its independent Gaussian
    # residual integrates to zero for this affine light, so this integral is 2-D exact.
    integral = 10 + float(w @ (180 + covariance[1, 0] / sigma * z))
    yy, _ = np.mgrid[:100, :120]
    paper = 180. + (yy - 50.)
    light = shadow.PaperLight(paper, paper)
    step = 0.125
    t = np.arange(-10., 10. + step/2, step)
    model = sheet._modelled_level(
        light, np.array([[60.5, 50.5]]), normal[None, :], t, step,
        np.array([sigma]), np.full((1, len(t)), 180.), np.array([True]),
        np.array([20.]), (t >= 5)[None, :], np.abs(t) <= 7., np.zeros((1, len(t))),
    )
    reported = float(model[0, np.argmin(np.abs(t))])
    return {
        "status": "unresolved model limitation; no correction delivered",
        "covariance_px2": covariance.tolist(), "paper_gradient_per_px": slope.tolist(),
        "analytic_2d_edge_level": exact, "conditional_quadrature_2d": integral,
        "production_normal_line_level": reported, "missing_level": exact - reported,
        "leading_offset_estimate_px": float(slope @ covariance @ normal) / 160,
        "offset_scope": "first-order estimate from edge slope, not an end-to-end trace measurement",
    }


def audit():
    moments = quadratic_moments()
    tangent = tangential_light_counterexample()
    good = max(r["quadrature_error"] for r in moments) < 1e-10
    good &= abs(tangent["analytic_2d_edge_level"] - tangent["conditional_quadrature_2d"]) < 1e-10
    return {
        "verified_identities_pass": bool(good),
        "scope": "quadratic Gaussian moments and a straight-edge affine-light counterexample only",
        "quadratic_moments": moments, "tangential_light": tangent,
        "sources_sha256": {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ("backend/sheet.py", "backend/shadow.py", "scripts/science_model_audit.py")
        },
    }


if __name__ == "__main__":
    report = audit()
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"identities_pass": report["verified_identities_pass"], "tangential_light": report["tangential_light"]}, indent=2))
    raise SystemExit(0 if report["verified_identities_pass"] else 1)
