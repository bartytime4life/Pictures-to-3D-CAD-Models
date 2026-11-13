#!/usr/bin/env python3
"""Normalize only the known saved acquisition report's NumPy scalar markers.

No model, reference, renderer or numerical package is imported. The original
report is immutable. This conversion assigns no scientific qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

SOURCE_SHA256 = "15df34975e0d2c56325a8e4efbea07145a6f0958133e4413a1b36f2ae5a29078"
FLOAT32 = re.compile(r"np\.float32\(([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\)")


def allowed(path, kind):
    if len(path) < 4 or path[0] != "rows" or type(path[1]) is not int or not 0 <= path[1] < 32:
        return False
    if kind == "bool":
        return path[2:] == ("quantization", "passed")
    if path[2:] == ("quantization", "propagated_envelope"):
        return True
    return (
        len(path) == 7
        and path[2] == "models"
        and path[3] in {"nominal_gaussian", "moment_gaussian"}
        and path[4] == "comparisons"
        and path[5] in {"unquantized", "decoded_png"}
        and path[6] in {"floating_allowance", "total_engineering_allowance"}
    )


def normalize(value, path=(), records=None):
    if records is None:
        records = []
    if isinstance(value, dict) and "invalid_python_value" in value:
        if set(value) != {"invalid_python_value"}:
            raise ValueError("mixed scalar marker")
        marker = value["invalid_python_value"]
        if set(marker) != {"type", "repr"} or not allowed(path, marker["type"]):
            raise ValueError(f"unexpected scalar marker at {path!r}")
        if marker["type"] == "bool":
            if marker["repr"] != "np.True_":
                raise ValueError("unexpected saved boolean representation")
            result, bits = True, None
        elif marker["type"] == "float32":
            match = FLOAT32.fullmatch(marker["repr"])
            if match is None:
                raise ValueError("unexpected saved binary32 representation")
            packed = struct.pack("<f", float(match[1]))
            result, bits = struct.unpack("<f", packed)[0], packed.hex()
            if not math.isfinite(result):
                raise ValueError("nonfinite scalar cannot be normalized")
        else:
            raise ValueError("unsupported scalar type")
        records.append(
            {
                "path": list(path),
                "original_marker": marker,
                "native_value": result,
                "binary32_little_endian_hex": bits,
            }
        )
        return result
    if isinstance(value, dict):
        if "invalid_nonfinite_float" in value:
            raise ValueError("nonfinite values are not covered by this repair")
        return {key: normalize(item, (*path, key), records) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item, (*path, index), records) for index, item in enumerate(value)]
    return value


def convert(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("input must match the exact retained continuation report")
    source = json.loads(raw)
    records = []
    result = normalize(source, records=records)
    counts = {
        kind: sum(r["original_marker"]["type"] == kind for r in records)
        for kind in ("float32", "bool")
    }
    if counts != {"float32": 288, "bool": 32}:
        raise ValueError("saved scalar census differs")
    result["source_result_format"] = result["format"]
    result["format"] = "pictures-to-cad-finite-acquisition-normalized-result"
    result["execution_declared_protocol_passed"] = result.pop("protocol_passed")
    result["raw_scalar_serialization_passed"] = False
    result["normalization"] = {
        "source_sha256": SOURCE_SHA256,
        "operation": "Strict saved-marker conversion; binary32 values retain their represented bits.",
        "changed_scalar_count": len(records),
        "counts": counts,
        "changes": records,
        "new_model_reference_generator_calls": 0,
        "scientific_qualification": "Not assigned by this serialization conversion.",
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True, type=Path, help="Original decoded report, exact SHA-256 required"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="New strict-JSON file; existing parent"
    )
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("output must be fresh and its parent must exist")
    if not args.input.is_file() or args.input.stat().st_size > 64 * 1024 * 1024:
        parser.error("input must be a regular report of at most64MiB")
    try:
        result = convert(args.input.read_bytes())
    except (ValueError, OverflowError, struct.error) as exc:
        parser.error(str(exc))
    encoded = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with args.output.open("xb") as stream:
        stream.write(encoded)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "changed_scalars": result["normalization"]["changed_scalar_count"],
                "new_scientific_calls": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
