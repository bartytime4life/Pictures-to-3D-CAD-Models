#!/usr/bin/env python3
"""Supplemental8x8/16x16 audit of the SAME saved56 aperture observations.

The original planned4x4/8x8 failure and study exit1 remain unchanged. No fitter
is imported or called. Required --output NEW_JSON refuses overwrite/symlinks.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "studies/verification/finite-free-centre-v1.py"
CANONICAL = ROOT / "studies/results/finite-free-centre-v1.json"
SELF = Path(__file__).resolve()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_audit():
    canonical = json.loads(CANONICAL.read_text())
    plan = canonical["plan"]
    row = next(r for r in canonical["cases"] if r["name"] == "uniform-pixel-aperture")
    source_paths = (
        *canonical["source_after"],
        str(CANONICAL.relative_to(ROOT)),
        str(SELF.relative_to(ROOT)),
    )
    before = {name: sha(ROOT / name) for name in source_paths}
    if any(before[name] != expected for name, expected in canonical["source_after"].items()):
        raise ValueError("original governing source differs; this audit is source-bound")
    spec = importlib.util.spec_from_file_location("_independent_positive_area", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pixels = np.asarray(row["observed"]["training_pixels"] + row["observed"]["heldout_pixels"], int)
    saved = np.asarray(row["observed_values_training"] + row["observed_values_heldout"])
    values8 = module.independent_means(pixels + 0.5, row["config"], 64, plan, aperture_order=8)
    values16 = module.independent_means(pixels + 0.5, row["config"], 64, plan, aperture_order=16)
    delta = float(np.max(np.abs(values16 - values8)))
    after = {name: sha(ROOT / name) for name in source_paths}
    return {
        "format": "pictures-to-cad-finite-free-centre-aperture-supplement",
        "version": 1,
        "scope": "Supplemental same-pixel/no-refit numerical audit. Does NOT replace original4x4/8x8 comparison, relax its criterion, change original exit1, or certify quadrature/physical bias.",
        "original_canonical_sha256": sha(CANONICAL),
        "original_planned_comparison": row["oracle"],
        "pixel_count": len(pixels),
        "pixels_xy": pixels.tolist(),
        "area_order": 64,
        "aperture_orders": [8, 16],
        "values8": values8.tolist(),
        "values16": values16.tolist(),
        "absolute_differences": np.abs(values16 - values8).tolist(),
        "reproduces_original8_bit_identically": bool(np.array_equal(values8, saved)),
        "maximum8_to16_level_delta": delta,
        "original_level_delta_limit": plan["oracle"]["maximum_level_order_delta"],
        "supplemental_delta_within_original_limit": delta
        <= plan["oracle"]["maximum_level_order_delta"],
        "source_before": before,
        "source_after": after,
        "source_unchanged": before == after,
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(arguments)
    try:
        output = args.output
        if (
            output.suffix.lower() != ".json"
            or output.exists()
            or output.is_symlink()
            or not output.parent.is_dir()
        ):
            raise ValueError("--output needs a fresh .json path in an existing directory")
        result = run_audit()
        encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
        with output.open("x") as stream:
            stream.write(encoded)
        print(encoded, end="")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return (
        0
        if (
            result["source_unchanged"]
            and result["reproduces_original8_bit_identically"]
            and result["supplemental_delta_within_original_limit"]
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
