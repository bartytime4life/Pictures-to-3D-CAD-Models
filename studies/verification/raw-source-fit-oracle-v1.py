"""Independent source-space fitting regression oracle (14 source + 4 level cases).

Run with --output NEW_JSON. Uses independently crossed projective lines and scalar
math.erfc for the Gaussian means, plus a 90-digit Decimal two-parameter box-LS
reference. These are finite development checks, not interval certificates, held-out
optical evidence or physical accuracy/uncertainty qualification. --help never runs
any fitting cases; existing output files are refused before computation.
"""

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import profile_observations as observations
from backend import raw_source_fit as fit

FILES = [
    Path(__file__).resolve(),
    ROOT / "backend/raw_source_fit.py",
    ROOT / "backend/profile_observations.py",
    ROOT / "backend/sheet.py",
]


def hashes():
    return {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in FILES}


def project(h, p):
    p = np.asarray(p)
    q = np.column_stack([p.reshape(-1, 2), np.ones(p.size // 2)]) @ h.T
    return q[:, :2] / q[:, 2, None]


def oracle(xy, h, anchor, normal, covariance, offset):
    t = np.array([-normal[1], normal[0]])
    centre = anchor + offset * normal
    ends = project(h, [centre - 3 * t, centre + 3 * t])
    line = np.cross(np.r_[ends[0], 1.0], np.r_[ends[1], 1.0])
    if line @ np.r_[project(h, [centre + 0.1 * normal])[0], 1.0] < 0:
        line = -line
    width = math.sqrt(line[:2] @ covariance @ line[:2])
    z = ((xy + 0.5) @ line[:2] + line[2]) / width
    return 0.5 * np.array([math.erfc(-v / math.sqrt(2)) for v in z])


def summary(result, truth):
    r = asdict(result)
    r.pop("candidates")
    r.pop("grid_offsets")
    r.pop("grid_costs")
    r["offset_error"] = result.best.offset - truth
    return r


def decimal_box_oracle(a, y, lo=0, hi=255):
    with localcontext() as ctx:
        ctx.prec = 90
        d = lambda z: Decimal.from_float(float(z))
        a = [[d(z) for z in row] for row in a]
        y = [d(z) for z in y]
        lo = Decimal(lo)
        hi = Decimal(hi)
        aa = sum(row[0] ** 2 for row in a)
        bb = sum(row[1] ** 2 for row in a)
        ab = sum(row[0] * row[1] for row in a)
        ay = sum(row[0] * v for row, v in zip(a, y))
        by = sum(row[1] * v for row, v in zip(a, y))
        candidates = []
        det = aa * bb - ab * ab
        if det:
            c = ((ay * bb - by * ab) / det, (by * aa - ay * ab) / det)
            if all(lo <= v <= hi for v in c):
                candidates.append(c)
        for first in (lo, hi):
            second = min(hi, max(lo, (by - ab * first) / bb)) if bb else lo
            candidates.append((first, second))
        for second in (lo, hi):
            first = min(hi, max(lo, (ay - ab * second) / aa)) if aa else lo
            candidates.append((first, second))
        scored = [
            (sum((v - row[0] * c[0] - row[1] * c[1]) ** 2 for row, v in zip(a, y)), c)
            for c in candidates
        ]
        rss, c = min(scored, key=lambda r: r[0])
        return float(rss), [float(z) for z in c]


def require(condition, message="independent control failed"):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path, help="fresh JSON destination; existing files refused"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a fresh JSON path")
    if args.output.suffix.lower() != ".json":
        parser.error("output must have a .json suffix")
    initial = hashes()
    start = time.perf_counter()
    yy, xx = np.mgrid[24:33, 30:39]
    xy = np.column_stack((xx.ravel(), yy.ravel()))
    shape = (80, 100)
    h = np.array([[1.4, 0.2, 3], [0.15, 1.2, 5], [0, 0, 1.0]])
    anchor = np.array([20.3, 17.4])
    normal = np.array([math.cos(math.radians(37)), math.sin(math.radians(37))])
    cov = np.array([[1.69, 0.4], [0.4, 0.81]])
    truth = 0.13719
    prob = oracle(xy, h, anchor, normal, cov, truth)
    values = 200 - 120 * prob
    base = observations.PixelNoise.factor(np.eye(len(xy)), 1.0)
    opts = {
        "sensor_shape": shape,
        "homography": h,
        "anchor": anchor,
        "normal": normal,
        "psf_covariance": cov,
        "offset_bounds": (-0.6, 0.6),
        "grid_points": 65,
        "refinement_iterations": 48,
    }
    rows = []

    def run(name, coordinates=xy, data=values, noise=base, true=truth, **updates):
        options = {**opts, **updates}
        result = fit.fit_plane_edge_offset(coordinates, data, noise, **options)
        rows.append({"case": name, "result": summary(result, true)})
        return result

    model = fit.plane_edge_probabilities(
        xy,
        truth,
        **{
            k: opts[k] for k in ("sensor_shape", "homography", "anchor", "normal", "psf_covariance")
        },
    )
    error = float(np.max(abs(model - prob)))
    require(error < 2e-13, str(error))
    result = run("anisotropic_nonidentity_independent_source")
    require(abs(result.best.offset - truth) < 1e-8)
    baseline_offset = result.best.offset
    for scale in [-1.0, 1e-120, -1e120]:
        result = run("H_scale_" + str(scale), homography=scale * h)
        require(abs(result.best.offset - baseline_offset) < 2e-9)
        require(np.max(abs(np.array(result.best.levels) - [200, 80])) < 1e-7)
    for scale in [1e-6, 1e6]:
        result = run(
            "noise_units_" + str(scale),
            noise=observations.PixelNoise.factor(np.eye(len(xy)), scale),
        )
        require(abs(result.best.offset - baseline_offset) < 2e-9)
        require(
            not any(
                (
                    result.flat,
                    result.plateau,
                    result.tied,
                    result.endpoint,
                    result.numerically_unsupported,
                )
            )
        )
    result = run("normal_reversed", normal=-normal, true=-truth)
    require(abs(result.best.offset + baseline_offset) < 2e-9)
    require(np.max(abs(np.array(result.best.levels) - [80, 200])) < 1e-7)
    swap = np.array([[0, 1], [1, 0]])
    result = run(
        "sensor_axes_swapped",
        coordinates=xy[:, ::-1],
        sensor_shape=shape[::-1],
        homography=np.vstack((h[1], h[0], h[2])),
        psf_covariance=swap @ cov @ swap,
    )
    require(abs(result.best.offset - baseline_offset) < 2e-9)
    rng = np.random.default_rng(71588)
    perm = rng.permutation(len(xy))
    npnoise = observations.PixelNoise.factor(np.eye(len(xy))[:, perm], 1.0)
    result = run("source_order_permuted", coordinates=xy[perm], data=values[perm], noise=npnoise)
    require(abs(result.best.offset - baseline_offset) < 2e-9)
    for constant in [0.0, 128.0]:
        result = run("constant_" + str(constant), data=np.full(len(xy), constant))
        require(result.flat and result.plateau and result.tied and result.endpoint)
    result = run("no_refinement_budget", max_evaluations=65)
    require(result.work_exhausted and result.evaluations == 65)
    # Deliberately outside the unknown mean bounds; noisy observations must be accepted.
    result = run("observations_outside_mean_bounds", data=-20 + 300 * prob)
    require(all(0 <= v <= 255 for v in result.best.levels))
    # Independent 90-digit two-level optimizer on nonphysical generic signed projected designs.
    box = []
    for a, y in [
        (np.array([[1.0, 0], [0, 1], [1, 1]]), np.array([-5.0, 270, 250.0])),
        (np.array([[1.0, -1], [2.0, 1], [-1.0, 3]]), np.array([400.0, -20, 500.0])),
        (np.array([[1.0, 1], [2.0, 2], [3.0, 3]]), np.array([600.0, 1000.0, 1700.0])),
        (np.zeros((3, 2)), np.array([-1.0, 2.0, 3.0])),
    ]:
        reference, c = decimal_box_oracle(a, y)
        actual, levels, rank, _maximum = fit._box_fit(a, y, (0.0, 255.0))
        require(abs(actual - reference) <= 1e-8 * max(1, reference), str((actual, reference)))
        box.append(
            {
                "design": a.tolist(),
                "observed": y.tolist(),
                "actual_cost": actual,
                "oracle_cost": reference,
                "actual_levels": levels.tolist(),
                "oracle_levels": c,
                "design_rank": rank,
            }
        )
    # A true projective chart crossing is explicitly refused.
    bad = h.copy()
    bad[2] = [0.02, 0, -0.4]
    try:
        fit.fit_plane_edge_offset(xy, values, base, **{**opts, "homography": bad})
    except ValueError as exc:
        chart_rejection = str(exc)
    else:
        raise AssertionError("chart crossing accepted")
    # Different retained-row coordinates of the same full source space preserve the objective.
    q, _ = np.linalg.qr(rng.normal(size=(len(xy), len(xy))))
    rotated_noise = observations.PixelNoise.factor(q, 1.0)
    result = run("orthogonal_full_rowspace_basis", noise=rotated_noise)
    require(abs(result.best.offset - baseline_offset) < 2e-9)
    report = {
        "format": "independent-raw-source-fit-api-audit",
        "version": 1,
        "source_sha256": initial,
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "runtime": {"python": platform.python_version(), "numpy": np.__version__},
        "control_count": 14,
        "bounded_level_oracle_count": 4,
        "seconds": time.perf_counter() - start,
        "oracle_probability_maximum_error": error,
        "cases": rows,
        "bounded_level_oracle_cases": box,
        "chart_rejection": chart_rejection,
        "limits": [
            "All cases are declared development controls, not holdout or physical qualification.",
            "Source halfplane renderer crosses forward-projected points and uses scalar erfc with anisotropic covariance.",
            "Decimal box oracle independently solves two-parameter active edges and interior from exact representations of input float values.",
            "Identity/orthogonal source projections deliberately retain all source modes for these invariance controls; the separate raw-source study covers its declared truncated SGR operators.",
            "No production source or tests were edited.",
        ],
    }
    if initial != hashes():
        raise RuntimeError("source changed during audit; rerun with fresh output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "cases": len(rows),
                "box_oracles": len(box),
                "maximum_probability_error": error,
                "baseline": rows[0],
                "chart_rejection": chart_rejection,
                "seconds": report["seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
