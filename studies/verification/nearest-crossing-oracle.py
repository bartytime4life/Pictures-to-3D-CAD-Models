"""Independent finite-data contact audit; not physical qualification.

Enumerate every five-node {-1,0,1} residual and every searched mask. The
reference constructs connected searched domains, then exact crossing/contact
components from their definition. It does not call the production helper to
construct expected roots. Output/source receipts refuse overwrites.
"""

import hashlib
import itertools
import json
import math
import platform
import subprocess
import sys
from fractions import Fraction as Q
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SOURCE_PATHS = ("backend/sheet.py", "backend/tone.py")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


HASHES = {name: digest(ROOT / name) for name in SOURCE_PATHS}
from backend.sheet import _nearest_profile_crossing as nearest
from backend.sheet import half_level_search


def reference(t, residual, mask):
    contacts = []
    k = 0
    while k < len(mask):
        if not mask[k]:
            k += 1
            continue
        first = k
        while k < len(mask) and mask[k]:
            k += 1
        last = k  # domain node endpoints first..last
        for j in range(first, last):
            if residual[j] * residual[j + 1] < 0:
                a, b = Q(residual[j]), Q(residual[j + 1])
                x, y = Q(t[j]), Q(t[j + 1])
                root = (x * b - y * a) / (b - a)
                contacts.append((abs(root), True, root))
        j = first
        while j <= last:
            if residual[j] != 0:
                j += 1
                continue
            start = j
            while j <= last and residual[j] == 0:
                j += 1
            stop = j - 1
            verified = (start == stop and start > first and stop < last
                        and residual[start - 1] * residual[stop + 1] < 0)
            low, high = Q(t[start]), Q(t[stop])
            distance = Q(0) if low <= 0 <= high else min(abs(low), abs(high))
            contacts.append((distance, verified, low))
    if not contacts:
        return None
    closest = min(contact[0] for contact in contacts)
    winners = [contact for contact in contacts if contact[0] == closest]
    return float(winners[0][2]) if len(winners) == 1 and winners[0][1] else None


def main():
    output = Path(__file__).with_suffix(".json")
    if output.exists():
        raise FileExistsError(output)
    count = 0
    max_error = max_reflection = 0.0
    t = np.arange(-2.0, 3.0)
    for values in itertools.product((-1, 0, 1), repeat=5):
        for mask_values in itertools.product((False, True), repeat=4):
            residual = np.array(values, dtype=float)
            mask = np.array(mask_values, dtype=bool)
            actual = nearest(t, residual, mask)
            expected = reference(tuple(map(int, t)), values, mask_values)
            assert math.isnan(actual) == (expected is None), (values, mask_values, actual, expected)
            if expected is not None:
                max_error = max(max_error, abs(actual - expected))
            reversed_result = nearest(t, residual[::-1], mask[::-1])
            assert math.isnan(actual) == math.isnan(reversed_result)
            if not math.isnan(actual):
                max_reflection = max(max_reflection, abs(actual + reversed_result))
            count += 1

    tiny = []
    t = np.array([-0.125, 0.0, 0.125])
    mask = np.array([True, True])
    for left, middle, right in ((-1.0, 1e-20, 1.0), (-1.0, 1e-200, 1.0),
                                (-1e308, 1.0, 1.0), (-1e308, 1e308, 1e308)):
        residual = np.array([left, middle, right])
        exact = (Q(float(t[0])) * Q(middle) - Q(float(t[1])) * Q(left)) / (Q(middle) - Q(left))
        expected = float(exact)
        actual = nearest(t, residual, mask)
        reflected = nearest(t, residual[::-1], mask)
        assert abs(actual - expected) <= math.ulp(expected)
        assert actual == -reflected
        tiny.append({"residual": [left, middle, right], "expected": expected,
                     "actual": actual, "reflected": reflected})

    size = 48
    centre = np.array([24.0, 24.0])
    coordinates = np.arange(size) + 0.5 - centre[0]
    knots = [-4.5, -3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5, 4.5]
    levels = [0, 0, 0.3, 0.4, 0.9, 0.91, 0.41, 0.3, 0.7, 1]
    image = np.tile(50 + 150 * np.interp(coordinates, knots, levels), (size, 1))
    physical = []
    for sign in (-1, 1):
        moved, keep = half_level_search(image, centre[None], np.array([[float(sign), 0.0]]),
                                       half=8.0, sigma=None)
        offset = float(moved[0, 0] - centre[0])
        assert keep[0] and abs(offset + 1.3) < 2e-14
        physical.append({"normal_sign": sign, "kept": bool(keep[0]), "offset_px": offset})

    assert HASHES == {name: digest(ROOT / name) for name in SOURCE_PATHS}
    result = {"format": "picad-math-nearest-contact-audit", "version": 1,
              "physical_qualification": False,
              "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_sha256": HASHES, "script_sha256": digest(__file__),
              "runtime": {"python": platform.python_version(), "numpy": np.__version__},
              "enumerated_cases": count, "maximum_root_float_error": max_error,
              "maximum_reflection_error": max_reflection, "tiny_roots": tiny,
              "actual_bounded_three_root_image": physical}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
