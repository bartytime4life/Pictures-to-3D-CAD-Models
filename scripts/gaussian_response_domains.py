"""Enclose continuous shared Gaussian edge/response parameter domains.

INPUT.json declares exact positions, output/calibration bands and offset/sigma
bounds. The same parameters and one response apply to all observations. Accepted,
excluded and unresolved boxes retain their certificates and coverage tree.
--output NEW_JSON is required; stdout contains the same report. No photographs,
production corrections or physical calibration are inferred.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE_FILES = (
    "backend/response_calibration.py",
    "backend/response_rectangles.py",
    "backend/normal_cdf_bounds.py",
    "backend/gaussian_response_domains.py",
    "scripts/gaussian_response_domains.py",
)
MAX_INPUT_BYTES = 512 * 1024


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def git_metadata():
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True, timeout=5
        ).stdout.strip()

    try:
        return {
            "revision": git("rev-parse", "HEAD"),
            "dirty_files": git("status", "--porcelain", "--untracked-files=all").splitlines(),
        }
    except (OSError, subprocess.SubprocessError):
        return {"revision": None, "dirty_files": None, "reason": "Git metadata unavailable"}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"nonfinite JSON value {value!r} is refused")


def decimal_string(value, label, parse_exact):
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an exact decimal string")
    return parse_exact(value)


def analyze_bytes(data):
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 512 KiB limit")
    before = source_hashes()
    from backend.gaussian_response_domains import (
        MAX_CALIBRATION,
        MAX_OBSERVATIONS,
        analyze_gaussian_response,
    )
    from backend.response_calibration import parse_exact

    if before != source_hashes():
        raise ValueError("analysis sources changed while importing")
    raw = json.loads(
        data.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant
    )
    required = {"version", "units", "observations", "offset_bounds", "sigma_bounds"}
    optional = {"calibration", "slope_bounds", "tolerances", "cdf_places", "max_boxes", "max_depth"}
    if not isinstance(raw, dict) or not required <= raw.keys() or raw.keys() - required - optional:
        raise ValueError(
            "input needs version, units, observations, offset_bounds, sigma_bounds and only documented settings"
        )
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("only integer version 1 is supported")
    units = raw["units"]
    if not isinstance(units, dict) or set(units) != {"position", "output"}:
        raise ValueError("units needs exactly position and output labels")
    if any(
        not isinstance(v, str) or not 1 <= len(v) <= 80 or not v.strip() or not v.isprintable()
        for v in units.values()
    ):
        raise ValueError("unit labels must be nonempty printable strings of at most 80 characters")

    def pair(value, label):
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError(f"{label} needs two decimal-string endpoints")
        return [decimal_string(v, label, parse_exact) for v in value]

    normalized = {}
    for field, key, low, high in (
        ("observations", "position", 1, MAX_OBSERVATIONS),
        ("calibration", "input", 0, MAX_CALIBRATION),
    ):
        values = raw.get(field, [])
        if not isinstance(values, list) or not low <= len(values) <= high:
            raise ValueError(f"{field} must contain {low}-{high} observations")
        parsed = []
        for row in values:
            if not isinstance(row, dict) or set(row) != {key, "output"}:
                raise ValueError(f"each {field} row needs exactly {key} and output")
            parsed.append(
                {
                    key: decimal_string(row[key], key, parse_exact),
                    "output": pair(row["output"], "output"),
                }
            )
        normalized[field] = parsed
    kwargs = {key: pair(raw[key], key) for key in ("offset_bounds", "sigma_bounds")}
    if "tolerances" in raw:
        kwargs["tolerances"] = pair(raw["tolerances"], "tolerances")
    if "slope_bounds" in raw:
        values = raw["slope_bounds"]
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError("slope_bounds needs a lower and optional upper")
        kwargs["slope_bounds"] = [
            decimal_string(values[0], "lower slope", parse_exact),
            None if values[1] is None else decimal_string(values[1], "upper slope", parse_exact),
        ]
    for key in ("cdf_places", "max_boxes", "max_depth"):
        if key in raw:
            kwargs[key] = raw[key]
    result = analyze_gaussian_response(
        normalized["observations"], normalized["calibration"], **kwargs
    )
    if before != source_hashes():
        raise ValueError("analysis sources changed during execution")
    return {
        "format": "pictures-to-cad-gaussian-response-domains-result",
        "version": 1,
        "units": units,
        "input": raw,
        "analysis": result,
        "provenance": {
            "input_sha256": hashlib.sha256(data).hexdigest(),
            "source_sha256": before,
            "git": git_metadata(),
            "python": platform.python_version(),
        },
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="version-1 exact decimal-string model JSON")
    parser.add_argument(
        "--output", required=True, type=Path, help="fresh JSON destination; existing paths refused"
    )
    args = parser.parse_args(arguments)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output already exists; choose a fresh destination")
        with args.input.open("rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
        report = analyze_bytes(data)
        result = json.dumps(report, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(result)
        print(result, end="")
    except (OSError, ValueError, TypeError, RecursionError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
