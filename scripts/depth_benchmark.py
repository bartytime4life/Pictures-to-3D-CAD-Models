"""Score AI depth against the true heights behind the generated moon sample.

    .venv/bin/python scripts/depth_benchmark.py [--json]

The relief studio's moon "photograph" (frontend/public/relief-sample.png) and its depth
map (relief-sample-depth.png) come from one procedural sphere, so the depth map is the
exact shape the photo shows. This compares two ways of getting height from the photo:

* brightness: the studio's Photo mode, CIE L* lightness of the decoded sRGB luminance;
* AI depth: the optional Depth Anything V2 Small model (needs make depth-model).

Each is scored on three regions: the whole picture, the sphere's disc, and the sunlit
part of the disc (where the photo shows the surface at all). See backend/depth.py score()
for the metrics. Results are for this one synthetic scene, not a general accuracy claim.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import depth
from backend.relief import lightness, relative_luminance, srgb_to_linear

PHOTO = ROOT / "frontend/public/relief-sample.png"
TRUTH = ROOT / "frontend/public/relief-sample-depth.png"
# Lightness (L*, 0..100) above which a disc pixel counts as sunlit. The sample's night
# side is black apart from crater detail; 5 L* is about 0.6% luminance.
LIT_LSTAR = 5.0


def load():
    image = Image.open(PHOTO).convert("RGB")
    rgb = np.asarray(image, dtype=np.float64) / 255
    truth = np.asarray(Image.open(TRUTH), dtype=np.float64) / 65535
    lstar = lightness(relative_luminance(srgb_to_linear(rgb)))
    return image, lstar, truth


def regions(lstar, truth):
    disc = truth > 0
    return {"picture": np.ones_like(disc), "disc": disc, "lit disc": disc & (lstar > LIT_LSTAR)}


def run(runner=None):
    image, lstar, truth = load()
    masks = regions(lstar, truth)
    methods = {"brightness (Photo mode)": lstar / 100}
    info = None
    state = depth.status()
    if runner is not None or state["available"]:
        field, info = depth.estimate_depth(image, runner=runner)
        methods["AI depth"] = field
    results = {
        name: {region: depth.score(field, truth, mask) for region, mask in masks.items()}
        for name, field in methods.items()
    }
    coverage = {region: float(mask.mean()) for region, mask in masks.items()}
    return {"model": info, "unavailable": state["reason"], "coverage": coverage, "results": results}


def main():
    report = run()
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
        return
    if report["model"] is None:
        print(f"AI depth skipped: {report['unavailable']}")
    else:
        m = report["model"]
        print(f"{m['model']} ({m['license']}, rev {m['revision']}), input {m['input_px']} px")
    print(
        f"{'method':26} {'region':10} {'share':>6} {'Spearman':>9} {'Pearson':>8} {'aligned RMS':>12}"
    )
    for name, by_region in report["results"].items():
        for region, s in by_region.items():
            print(
                f"{name:26} {region:10} {report['coverage'][region]:6.1%} {s['spearman']:9.3f} "
                f"{s['pearson']:8.3f} {s['aligned_rms_fraction']:11.1%}"
            )


if __name__ == "__main__":
    main()
