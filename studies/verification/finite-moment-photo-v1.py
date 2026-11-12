#!/usr/bin/env python3
"""Replay fixed synthetic photo-field moments; never alter production geometry.

The original plan, inputs, source probe and all outcomes are archived. Required
--output NEW_JSON is checked before NumPy imports, fixture reads or analysis.
The numerical loop preserves the original probe, including its adverse results.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-moment-photo-v1.json"
FIXTURES = ROOT / "studies/fixtures/finite-moment-photo-v1"
PLAN_SHA256 = "7aa2762c329bb42407addd2416ef7ddb90d552664c64051ac47845fe418a44ad"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unit(f):
    """Exact-form unit-D moments evaluated in floating-point arithmetic."""
    s = math.sqrt((1 - f) * (1 + f))
    angle = math.asin(f) + math.pi / 2
    area = angle + f * s
    mean = -2 * s**3 / (3 * area)
    xx = (angle - f * s * (1 - 2 * f * f)) / (4 * area)
    yy = (3 * angle + f * s * (5 - 2 * f * f)) / (12 * area)
    xxx = (-2 * s**3 / 3 + 2 * s**5 / 5) / area
    xyy = -2 * s**5 / (15 * area)
    return {
        "area": area,
        "mean": mean,
        "varx": xx - mean**2,
        "vary": yy,
        "thirdx": xxx - 3 * mean * xx + 2 * mean**3,
        "thirdxyy": xyy - mean * yy,
    }


def fixture_inputs():
    """Verify immutable archives before reading numerical fixture arrays."""
    if sha(PLAN) != PLAN_SHA256:
        raise ValueError("the original frozen moment plan has changed")
    manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
    if manifest["original_moment_plan_sha256"] != PLAN_SHA256:
        raise ValueError("fixture manifest refers to another moment plan")
    for name, expected in manifest["archived_files"].items():
        if Path(name).name != name or sha(FIXTURES / name) != expected:
            raise ValueError(f"archived input has changed: {name}")
    for item in manifest["measurements"]:
        name = item["file"]
        if Path(name).name != name or sha(FIXTURES / name) != item["file_sha256"]:
            raise ValueError(f"measured field has changed: {name}")
    for version, item in manifest["baselines"].items():
        if item["source_hashes_before"] != item["source_hashes_after"]:
            raise ValueError(f"archived capture source changed during baseline {version}")
        if sha(FIXTURES / f"baseline-{version}-plan.json") != item["plan_sha256"]:
            raise ValueError(f"baseline {version} plan has changed")
        if sha(FIXTURES / f"baseline-{version}-result.json") != item["result_sha256"]:
            raise ValueError(f"baseline {version} result has changed")
    return manifest


def source_hashes(manifest):
    names = {
        str(RUNNER.relative_to(ROOT)),
        str(PLAN.relative_to(ROOT)),
        str((FIXTURES / "manifest.json").relative_to(ROOT)),
        str((FIXTURES / "replay-contracts.py").relative_to(ROOT)),
        *manifest["baselines"]["v2"]["source_hashes_before"],
    }
    names.update(str((FIXTURES / name).relative_to(ROOT)) for name in manifest["archived_files"])
    names.update(str((FIXTURES / item["file"]).relative_to(ROOT)) for item in manifest["measurements"])
    return {name: sha(ROOT / name) for name in sorted(names)}


def replay(plan, baseline, manifest, np):
    """Original numerical operations, with only portable input loading added."""
    rows = []
    by_name = {item["name"]: item for item in manifest["measurements"]}
    for case in baseline["rows"]:
        name = case["case"]["name"]
        m = case["measurements"]
        if not m.get("initial_fits"):
            rows.append({"name": name, "status": "upstream_ineligible", "error": case.get("error")})
            continue
        initial = m["initial_fits"][0]
        arcs = [p for p in initial if p["kind"] == "arc"]
        lines = [p for p in initial if p["kind"] == "line"]
        if not arcs or not lines:
            rows.append({"name": name, "status": "seed_ineligible"})
            continue
        arc = max(arcs, key=lambda p: p["data"]["r"])["data"]
        line = max(lines, key=lambda p: np.linalg.norm(np.subtract(*p["data"]["source_ends"])))["data"]
        n = np.array([-line["d"][1], line["d"][0]])
        if n @ np.subtract(arc["mid"], arc["c"]) > 0:
            n = -n
        n /= np.linalg.norm(n)
        t = np.array([-n[1], n[0]])
        basis = np.column_stack((n, t))
        points = np.asarray(m["rings"][0]["points"])
        item = by_name[name]
        with np.load(FIXTURES / item["file"], allow_pickle=False) as archive:
            g = archive["g"]
            captured_points = archive["points"]
        if (list(g.shape) != item["g_shape"] or str(g.dtype) != item["g_dtype"]
                or hashlib.sha256(g.tobytes(order="C")).hexdigest() != item["g_sha256"]
                or not np.array_equal(points, captured_points)):
            raise ValueError(f"measured-field metadata mismatch: {name}")
        ppm = m["ppm"]
        for padding in plan["roi_sigmas"]:
            pad = max(plan["minimum_padding"], math.ceil(padding * m["sigma"]))
            low = np.maximum(np.floor(points.min(axis=0) - pad).astype(int), 0)
            high = np.minimum(np.ceil(points.max(axis=0) + pad).astype(int) + 1, g.shape[::-1])
            image = g[low[1]:high[1], low[0]:high[0]].astype(float)
            border = np.concatenate((image[0], image[-1], image[1:-1, 0], image[1:-1, -1]))
            bg = float(np.median(border))
            yy, xx = np.mgrid[low[1]:high[1], low[0]:high[0]]
            q = np.column_stack((xx.ravel() + .5, yy.ravel() + .5))
            for offset in plan["background_perturbations"]:
                row = {"name": name, "roi_sigmas": padding, "roi": [low.tolist(), high.tolist()],
                       "background": bg, "background_offset": offset, "normal": n.tolist(),
                       "sensor_shape": list(g.shape)}
                try:
                    weights = (bg + offset - image).ravel()
                    mass = float(weights.sum())
                    if mass <= 0:
                        raise ValueError("nonpositive signed mass")
                    mu = np.sum(q * weights[:, None], axis=0) / mass
                    local = (q - mu) @ basis
                    x, y = local.T
                    prob = weights / mass
                    k30 = float(prob @ (x * x * x))
                    k12 = float(prob @ (x * y * y))
                    row.update(mass=mass, centroid=mu.tolist(), third_xxx=k30, third_xyy=k12,
                               third_xxy=float(prob @ (x * x * y)),
                               third_yyy=float(prob @ (y * y * y)),
                               negative_mass_fraction=float(-weights[weights < 0].sum() / mass))
                    if k12 <= 0:
                        raise ValueError("nonpositive transverse third moment")
                    target = k30 / k12
                    lo, hi = plan["fraction_domain"]
                    ratios = [unit(z)["thirdx"] / unit(z)["thirdxyy"] for z in np.linspace(lo, hi, 257)]
                    if not all(a > b for a, b in itertools.pairwise(ratios)):
                        raise ValueError("sampled ratio order failure")
                    if not ratios[-1] < target < ratios[0]:
                        raise ValueError("observed ratio outside prescribed domain")
                    for _ in range(60):
                        mid = (lo + hi) / 2
                        mom = unit(mid)
                        if mom["thirdx"] / mom["thirdxyy"] > target:
                            lo = mid
                        else:
                            hi = mid
                    fraction = (lo + hi) / 2
                    mom = unit(fraction)
                    radius = (k12 / mom["thirdxyy"]) ** (1 / 3)
                    centre = mu - radius * mom["mean"] * n
                    obs = (local.T * prob) @ local
                    sigma = basis @ (obs - radius**2 * np.diag([mom["varx"], mom["vary"]])) @ basis.T
                    eigen = np.linalg.eigvalsh(sigma)
                    # Synthetic truth is used only AFTER inversion, as in the probe.
                    centre_error = float(np.linalg.norm(centre / ppm - np.array([30., 30.])))
                    radius_error = radius / ppm - case["case"]["radius"]
                    row.update(status="moment_proposal", centre_px=centre.tolist(), radius_px=radius,
                               fraction=fraction, covariance=sigma.tolist(),
                               covariance_eigenvalues=eigen.tolist(),
                               implied_inside_level=bg - mass / (radius**2 * mom["area"]),
                               centre_error_mm=centre_error, radius_error_mm=radius_error,
                               target_pass=centre_error <= .02 and abs(radius_error) <= .02)
                except Exception as exc:  # noqa: BLE001 - retain every original study outcome
                    # Preserve the original per-row refusal policy and diagnostic.
                    row.update(status="refused", error={"type": type(exc).__name__, "message": str(exc)})
                rows.append(row)
    return rows


def summarize(rows):
    nominal = [r for r in rows if r.get("roi_sigmas") == 8 and r.get("background_offset") == 0]
    proposed = [r for r in rows if r["status"] == "moment_proposal"]
    return {
        "row_count": len(rows),
        "attempted_moment_rows": sum("roi_sigmas" in row for row in rows),
        "status_counts": {status: sum(row["status"] == status for row in rows)
                          for status in sorted({row["status"] for row in rows})},
        "nominal_row_count": len(nominal),
        "nominal_geometry_targets_passed": sum(row.get("target_pass", False) for row in nominal),
        "indefinite_or_nonpositive_covariance_rows": sum(min(row["covariance_eigenvalues"]) <= 0 for row in proposed),
        "production_geometry_changed": False,
        "gaussian_psf_certified": False,
        "population_accuracy_estimated": False,
    }


def run():
    import numpy as np

    plan = json.loads(PLAN.read_bytes())
    manifest = fixture_inputs()
    before = source_hashes(manifest)
    baseline = json.loads((FIXTURES / "baseline-v2-result.json").read_bytes())
    original = json.loads((FIXTURES / "original-moment-result.json").read_bytes())
    rows = replay(plan, baseline, manifest, np)
    after = source_hashes(manifest)
    exact_replay = rows == original["rows"]
    unchanged = before == after
    return {
        "format": "pictures-to-cad-finite-moment-photo-replay",
        "version": 1,
        "status": "reproduced" if exact_replay and unchanged else "replay_mismatch",
        "plan_sha256": sha(PLAN),
        "baseline_sha256": sha(FIXTURES / "baseline-v2-result.json"),
        "original_result_sha256": sha(FIXTURES / "original-moment-result.json"),
        "rows": rows,
        "summary": summarize(rows),
        "upstream_baselines": manifest["baselines"],
        "replay_checks": {
            "all_original_rows_exactly_equal": exact_replay,
            "original_row_count": len(original["rows"]),
            "source_and_inputs_unchanged": unchanged,
            "trace_rerun": False,
            "production_imported": False,
        },
        "provenance": {
            "runtime": {"python": platform.python_version(), "numpy": np.__version__},
            "source_hashes_before": before,
            "source_hashes_after": after,
            "current_capture_source_matches_archived": all(
                before[name] == expected
                for name, expected in baseline["source_hashes_before"].items()
            ),
            "capture_source_head": baseline["source_head"],
            "working_tree_revision_queried": False,
            "fixture_manifest_sha256": sha(FIXTURES / "manifest.json"),
            "field_hashes": {item["name"]: item["g_sha256"] for item in manifest["measurements"]},
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, metavar="NEW_JSON")
    args = parser.parse_args(argv)
    output = args.output.expanduser()
    if output.suffix.lower() != ".json":
        parser.error("--output must be a new .json file")
    if output.exists() or output.is_symlink():
        parser.error("--output already exists or is a symlink; choose a new file")
    if not output.parent.is_dir():
        parser.error("--output parent directory must already exist")
    try:
        result = run()
        encoded = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode("utf-8")
        with output.open("xb") as stream:
            stream.write(encoded)
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print(f"finite-moment-photo: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(encoded)
    return 0 if result["status"] == "reproduced" else 1


if __name__ == "__main__":
    raise SystemExit(main())
