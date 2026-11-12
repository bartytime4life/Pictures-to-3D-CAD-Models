"""Check one common continuous response against exact input/output rectangles.

INPUT.json uses version 1, declared units, decimal-string rectangles, optional
input_mode some/all, optional slope bounds and exact queries. --output NEW_JSON
is required; the same report is printed on stdout. Existing paths are refused.
Null query endpoints mean unbounded directions, not unknown results. This does
not ingest photos, infer physical bounds or change workbench geometry.
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
    "scripts/response_rectangles.py",
)
MAX_INPUT_BYTES = 512 * 1024
MAX_QUERIES = 256


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
    """Validate the entire bounded request before returning a mathematical report."""
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 512 KiB limit")
    hashes = source_hashes()
    from backend.response_calibration import parse_exact
    from backend.response_rectangles import MAX_RECTANGLES, calibrate_rectangles

    if hashes != source_hashes():
        raise ValueError("analysis source changed while importing; rerun with stable source")
    raw = json.loads(
        data.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant
    )
    required, optional = (
        {"version", "units", "rectangles"},
        {"input_mode", "slope_bounds", "queries"},
    )
    if not isinstance(raw, dict) or not required <= raw.keys() or raw.keys() - required - optional:
        raise ValueError(
            "input needs version, units, rectangles and only optional input_mode/slope_bounds/queries"
        )
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("only integer version 1 is supported")
    units = raw["units"]
    if not isinstance(units, dict) or set(units) != {"input", "output"}:
        raise ValueError("units needs exactly input and output labels")
    if any(
        not isinstance(v, str) or not 1 <= len(v) <= 80 or not v.strip() or not v.isprintable()
        for v in units.values()
    ):
        raise ValueError("unit labels must be nonempty printable strings of at most 80 characters")
    rectangles = raw["rectangles"]
    if not isinstance(rectangles, list) or not 1 <= len(rectangles) <= MAX_RECTANGLES:
        raise ValueError(f"rectangles must contain 1-{MAX_RECTANGLES} observations")
    parsed = []
    for index, rectangle in enumerate(rectangles):
        if not isinstance(rectangle, dict) or set(rectangle) != {"input", "output"}:
            raise ValueError("each rectangle needs exactly input and output")
        item = {}
        for axis in ("input", "output"):
            band = rectangle[axis]
            if not isinstance(band, list) or len(band) != 2:
                raise ValueError(f"each {axis} must be a closed two-endpoint interval")
            item[axis] = [
                decimal_string(value, f"rectangle {index} {axis}", parse_exact) for value in band
            ]
        parsed.append(item)
    mode = raw.get("input_mode", "some")
    if mode not in ("some", "all"):
        raise ValueError("input_mode must be 'some' or 'all'")
    slopes = raw.get("slope_bounds", ["0", None])
    if not isinstance(slopes, list) or len(slopes) != 2:
        raise ValueError("slope_bounds needs a lower and optional upper bound")
    slopes = (
        decimal_string(slopes[0], "lower slope", parse_exact),
        None if slopes[1] is None else decimal_string(slopes[1], "upper slope", parse_exact),
    )
    queries = raw.get("queries", [])
    if not isinstance(queries, list) or len(queries) > MAX_QUERIES:
        raise ValueError("queries must be a list of at most 256 exact inputs")
    queries = [decimal_string(x, "query", parse_exact) for x in queries]
    result = calibrate_rectangles(parsed, slope_bounds=slopes, input_mode=mode)
    # An incompatible calibration still gets its exact proof. Query syntax is
    # validated above, while no nonexistent envelope is manufactured for it.
    answers = []
    for x in queries:
        if result.status == "compatible":
            interval = result.query(x)
            answers.append(
                {
                    "input": str(x),
                    "output": [
                        None if bound is None else str(bound)
                        for bound in (interval.lower, interval.upper)
                    ],
                }
            )
        else:
            answers.append({"input": str(x), "unavailable": "incompatible_calibration"})
    metadata = git_metadata()
    if hashes != source_hashes():
        raise ValueError("analysis source changed during this run; rerun with stable source")
    return {
        "format": "pictures-to-cad-response-rectangles-result",
        "version": 1,
        "units": units,
        "input": raw,
        "calibration": result.to_dict(),
        "queries": answers,
        "unbounded_semantics": {
            "lower_null": "negative_infinity",
            "upper_null": "positive_infinity",
        },
        "limits": [
            "Conditional on exact supplied rectangles, input quantifier and one common continuous response.",
            "Nondecreasing permits plateaus; a piecewise-linear witness is not a unique response.",
            "Query envelopes are pointwise marginals; joint observations must be checked together.",
            "Cartesian input boxes do not enforce correlation or realizability by a shared optical model.",
        ],
        "provenance": {
            "input_sha256": hashlib.sha256(data).hexdigest(),
            "source_sha256": hashes,
            "git": metadata,
            "python": platform.python_version(),
        },
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="version-1 exact decimal-string rectangle JSON")
    parser.add_argument(
        "--output", required=True, type=Path, help="new JSON file; existing paths refused"
    )
    options = parser.parse_args(arguments)
    try:
        if options.output.exists() or options.output.is_symlink():
            raise ValueError("output already exists; choose a fresh destination")
        with options.input.open("rb") as handle:
            data = handle.read(MAX_INPUT_BYTES + 1)
        report = analyze_bytes(data)
        text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        options.output.parent.mkdir(parents=True, exist_ok=True)
        with options.output.open("x", encoding="utf-8") as handle:
            handle.write(text)
        print(text, end="")
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
