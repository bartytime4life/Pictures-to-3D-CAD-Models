"""Independent, local development probe; not a physical error or confidence study.

Analytic node-basis fits are checked against segmented Gaussian quadrature of
the bounded source itself. No production fitter or synthetic renderer is used.
"""

import argparse
import hashlib
import json
import math
import subprocess
from itertools import pairwise, product
from pathlib import Path

import numpy as np


def phi(z):
    z = np.asarray(z, dtype=float)
    return np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def cdf(z):
    z = np.asarray(z, dtype=float)
    return np.array([0.5 * math.erfc(-float(v) / math.sqrt(2)) for v in z.flat]).reshape(z.shape)


def analytic_basis(t, e, w, s, length):
    x = np.asarray(t) - e
    u = cdf(-(x + w) / s)
    a = cdf(x / s)
    v = cdf((x + w) / s) - a
    material = x * u - s * phi((x + w) / s)
    material -= (x + length) * cdf(-(x + length) / s) - s * phi((x + length) / s)
    paper = x * a + s * phi(x / s)
    paper -= (x - length) * cdf((x - length) / s) + s * phi((x - length) / s)
    return np.column_stack(((-w * u - material) / (length - w),
                            (length * u + material) / (length - w),
                            v, a - paper / length, paper / length))


def source_integral(t, e, w, s, length, nodes, order):
    """Integrate linear source segments directly, with erfc constant tails.

    Every finite interval is split into pieces of length at most s, and the
    resulting smooth Gaussian integrands use independent Gauss-Legendre nodes.
    """
    x = np.asarray(t) - e
    c_left, c_wall, wall, a_edge, a_right = nodes
    result = c_left * cdf((-length - x) / s) + a_right * cdf((x - length) / s)
    gz, gw = np.polynomial.legendre.leggauss(order)
    for lo, hi, first, last in ((-length, -w, c_left, c_wall),
                                (-w, 0.0, wall, wall),
                                (0.0, length, a_edge, a_right)):
        if lo == hi:
            continue
        edges = np.linspace(lo, hi, max(1, math.ceil((hi - lo) / s)) + 1)
        for left, right in pairwise(edges):
            q = (right + left) / 2 + (right - left) / 2 * gz
            source = first + (last - first) * (q - lo) / (hi - lo)
            result += (right - left) / 2 * (phi((x[:, None] - q[None, :]) / s) / s) @ (gw * source)
    return result


def box_lstsq(matrix, y):
    """Enumerate all box faces; a finite numerical witness, not an interval proof."""
    unconstrained, *_ = np.linalg.lstsq(matrix, y, rcond=None)
    if np.all((unconstrained >= 0) & (unconstrained <= 255)):
        return unconstrained, 1
    best = None
    attempts = 0
    for face in product((-1, 0, 1), repeat=5):
        attempts += 1
        free = np.flatnonzero(np.array(face) == 0)
        fixed = np.flatnonzero(np.array(face) != 0)
        coeff = np.zeros(5)
        coeff[fixed] = np.where(np.array(face)[fixed] > 0, 255.0, 0.0)
        if len(free):
            coeff[free], *_ = np.linalg.lstsq(matrix[:, free], y - matrix[:, fixed] @ coeff[fixed], rcond=None)
        if np.any(coeff < -1e-9) or np.any(coeff > 255 + 1e-9):
            continue
        coeff = np.clip(coeff, 0, 255)
        residual = matrix @ coeff - y
        rss = float(residual @ residual)
        if best is None or rss < best[0]:
            best = rss, coeff
    assert best is not None
    return best[1], attempts + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new JSON result; existing files refused')
    args = parser.parse_args()
    s = 2.0
    length = 12 * s
    rows = []
    for ratio, offsets in ((0.1, (0.1, 0.25, 0.5)), (0.5, (0.1, 0.25)),
                           (1.0, (0.1, 0.25, 0.5)), (1.5, (0.1, 0.25))):
        w = ratio * s
        truth = np.array((90 - length, 90 - w, 130, 170, 170 - length))
        t = np.arange(-(w + 4 * s), 4 * s + 0.125 / 2, 0.125)
        dense = np.linspace(t[0], t[-1], 10001)
        y = source_integral(t, 0, w, s, length, truth, 16)
        analytic_y = analytic_basis(t, 0, w, s, length) @ truth
        dense_truth = source_integral(dense, 0, w, s, length, truth, 16)
        for e in offsets:
            matrix = analytic_basis(t, e, w, s, length)
            witness, attempts = box_lstsq(matrix, y)
            predicted8 = source_integral(t, e, w, s, length, witness, 8)
            predicted16 = source_integral(t, e, w, s, length, witness, 16)
            dense8 = source_integral(dense, e, w, s, length, witness, 8)
            dense16 = source_integral(dense, e, w, s, length, witness, 16)
            difference = predicted16 - y
            rows.append({"sigma": s, "band": w, "e": e, "L": length,
                         "truth_nodes": truth.tolist(), "witness_nodes": witness.tolist(),
                         "witness_slopes": [(witness[1] - witness[0]) / (length - w),
                                            (witness[4] - witness[3]) / length],
                         "sample_count": len(t), "fit_attempts": attempts,
                         "sample_rms": float(np.sqrt(np.mean(difference**2))),
                         "sample_max_abs": float(np.max(np.abs(difference))),
                         "dense_10001_max_abs": float(np.max(np.abs(dense16 - dense_truth))),
                         "quadrature_8_vs_16_max": float(max(np.max(np.abs(predicted8 - predicted16)),
                                                            np.max(np.abs(dense8 - dense16)))),
                         "basis_vs_source_max": float(max(np.max(np.abs(analytic_y - y)),
                                                          np.max(np.abs(matrix @ witness - predicted16)))),
                         "partition_unity_max": float(np.max(np.abs(matrix.sum(axis=1) - 1))),
                         "min_basis": float(matrix.min())})
    t = np.linspace(-30, 30, 10001)
    e, w, s = 0.0, 2.0, 2.0
    one = source_integral(t, e, w, s, 24, [90, 90, 90, 170, 170], 16)
    two = source_integral(t, e + w, w, s, 24, [90, 90, 170, 170, 170], 16)
    output = {"kind": "floating development witnesses, not a certified error bound",
              "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "numpy": np.__version__, "cases": rows,
              "exact_ambiguity": {"e1": e, "e2": e + w, "w": w, "sigma": s,
                                  "reason": "Both bounded sources equal90 for t<0 and170 for t>=0",
                                  "floating_source_integral_max_difference": float(np.max(np.abs(one - two)))}}
    destination = args.output
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(output, indent=2) + '\n')
    print(json.dumps({"result": str(destination), "cases": len(rows),
                      "max_quadrature_delta": max(row["quadrature_8_vs_16_max"] for row in rows),
                      "max_basis_delta": max(row["basis_vs_source_max"] for row in rows),
                      "exact_ambiguity_float_delta": output["exact_ambiguity"]["floating_source_integral_max_difference"]}, indent=2))


if __name__ == "__main__":
    main()
