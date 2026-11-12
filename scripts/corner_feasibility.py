"""Analyze a supplied conditional corner model; no images or production CAD are changed.

Run `python scripts/corner_feasibility.py INPUT.json`, or `--demo` for a synthetic
sharp-quadrant observation. All dimensional and level bounds must be decimal strings
in the input; the analysis supplies no physical observation-error bounds for you.
Version 2 uses one shared blur choice across all observation points. Its radius
sets project joint (radius, sigma_x, sigma_y) boxes; blur cannot vary per point.
Version 3 observes normalized means over known uniform product pixel apertures,
not arbitrary position uncertainty or total flux.
Version 4 applies supplied signed stencil weights without normalization; the
resulting linear functional is not a probability and is not clamped to [0,1].
Results are JSON on stdout. `--output FILE` also saves them, refusing an existing file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SOURCE_FILES = (
    "backend/corner_feasibility.py",
    "backend/corner_blur_domains.py",
    "backend/corner_pixel_apertures.py",
    "backend/corner_signed_stencils.py",
    "backend/decimal_bounds.py",
    "scripts/corner_feasibility.py",
)
MAX_INPUT_BYTES = 128 * 1024
DEMO = {
    "format": "pictures-to-cad-corner-feasibility",
    "version": 1,
    "coordinate_unit": "px",
    "points": [["0", "0"]],
    "blur_sigma": ["1", "1"],
    "level_intervals": [["0.24", "0.26"]],
    "radius_domain": ["0", "4"],
    "radius_resolution": "0.1",
    "max_boxes": 64,
    "cells": 32,
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"{value} is not a finite JSON value")


def _source_hashes():
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }


def _git_metadata():
    def git(*arguments):
        return subprocess.run(
            ["git", "-C", str(ROOT), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()

    try:
        revision = git("rev-parse", "--verify", "HEAD")
        dirty = bool(git("status", "--porcelain", "--untracked-files=all"))
        source_dirty = bool(
            git("status", "--porcelain", "--untracked-files=all", "--", *SOURCE_FILES)
        )
    except (OSError, subprocess.SubprocessError):
        return {
            "revision": None,
            "worktree_dirty": None,
            "source_dirty": None,
            "unavailable_reason": "Git metadata could not be read; source hashes remain available.",
        }
    return {"revision": revision, "worktree_dirty": dirty, "source_dirty": source_dirty}


def _run(raw_bytes, mode):
    if len(raw_bytes) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the 128 KiB limit.")
    raw = json.loads(
        raw_bytes.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )
    hashes = _source_hashes()
    git_metadata = _git_metadata()

    if isinstance(raw, dict) and type(raw.get("version")) is int and raw["version"] == 4:
        from backend.corner_signed_stencils import analyze
    elif isinstance(raw, dict) and type(raw.get("version")) is int and raw["version"] == 3:
        from backend.corner_pixel_apertures import analyze
    elif isinstance(raw, dict) and type(raw.get("version")) is int and raw["version"] == 2:
        from backend.corner_blur_domains import analyze
    else:
        from backend.corner_feasibility import analyze

    result = analyze(raw)
    if hashes != _source_hashes():
        raise ValueError("Analysis source changed during this run; rerun with unchanged source.")
    return {
        **result,
        "input": raw,
        "provenance": {
            "input_mode": mode,
            "input_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "source_sha256": hashes,
            "git": git_metadata,
        },
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("input", type=Path, nargs="?", help="version 1, 2, 3 or 4 model JSON input")
    source.add_argument("--demo", action="store_true", help="analyze a synthetic sharp quadrant")
    parser.add_argument("--output", type=Path, metavar="FILE",
                        help="also save the JSON result; FILE must not already exist")
    options = parser.parse_args(arguments)
    try:
        if options.demo:
            raw_bytes = (json.dumps(DEMO, indent=2) + "\n").encode("utf-8")
            print(
                "Synthetic sharp-quadrant demo: exact apex (0, 0), independent Gaussian "
                "sigmas (1, 1) px, supplied level [0.24, 0.26]. Conditional compatibility "
                "is not accuracy; radius [0, 4] px is a supplied prior, not an image bound.",
                file=sys.stderr,
            )
        else:
            with options.input.open("rb") as input_file:
                raw_bytes = input_file.read(MAX_INPUT_BYTES + 1)
        report = _run(raw_bytes, "demo" if options.demo else "file")
        text = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if options.output is not None:
            with options.output.open("x", encoding="utf-8", newline="\n") as output:
                output.write(text)
    except FileExistsError:
        print("Cannot save result: output already exists; choose a new file.", file=sys.stderr)
        return 1
    except RecursionError:
        print("Corner feasibility: JSON nesting is too deep.", file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"Corner feasibility: {exc}", file=sys.stderr)
        return 1
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
