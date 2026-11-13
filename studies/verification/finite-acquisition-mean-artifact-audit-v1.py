#!/usr/bin/env python3
"""Read saved JSON/NPZ/NPY bytes and statistics; never run a forward operator."""

from __future__ import annotations

import argparse
import builtins
import gzip
import hashlib
import json
import math
import zipfile
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def strict(data):
    def bad(value):
        raise ValueError(f"nonfinite JSON constant {value}")

    result = json.loads(data, object_pairs_hook=pairs, parse_constant=bad)
    pending = [result]
    while pending:
        node = pending.pop()
        if type(node) is dict:
            if "invalid_python_value" in node:
                raise ValueError("invalid_python_value marker")
            pending.extend(node.values())
        elif type(node) is list:
            pending.extend(node)
        elif type(node) is float and not math.isfinite(node):
            raise ValueError("nonfinite decoded JSON float")
        elif node is not None and type(node) not in (str, bool, int, float):
            raise ValueError("non-native JSON node")
    json.dumps(result, allow_nan=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recorded-source", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("output must be fresh with an existing parent")
    root, folder = args.root.resolve(), args.report.resolve().parent
    # Fail loudly if future changes try to import a candidate/generator/operator.
    original_import = builtins.__import__

    def blocked(name, *positional, **keywords):
        if name.split(".")[0] in {"backend", "tests", "cv2"}:
            raise RuntimeError(f"forbidden scientific import: {name}")
        return original_import(name, *positional, **keywords)

    builtins.__import__ = blocked
    import numpy as np

    checks, errors, input_hashes, stage_records = [], [], {}, []

    def check(name, value):
        checks.append({"check": name, "passed": bool(value)})

    def read(path):
        path = path.resolve()
        data = path.read_bytes()
        input_hashes[str(path)] = sha(data)
        return data

    def load_npz(path):
        read(path)
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        for name, array in arrays.items():
            check(
                f"numeric-finite:{path.name}:{name}",
                array.dtype.kind in "fiu" and np.isfinite(array).all(),
            )
        return arrays

    report_bytes = read(args.report)
    report = strict(report_bytes)
    check(
        "report-known-sha",
        sha(report_bytes) == "bd8127cc84999e7c5572797c46c2ba62bda29e2262ce57375c1e9745ce9133c3",
    )
    check(
        "source-before-after",
        report["source_before"] == report["source_after"] and report["source_unchanged"] is True,
    )
    with zipfile.ZipFile(args.recorded_source) as source_zip:
        read(args.recorded_source)
        source_manifest = strict(source_zip.read("recorded-source-manifest.json"))
        check("recorded-source-commit", source_manifest["source_commit"] == report["source_commit"])
        for relative, expected in report["source_before"].items():
            data = source_zip.read(relative)
            check(
                f"source-snapshot:{relative}",
                sha(data) == expected == source_manifest["files"][relative],
            )
    check(
        "plan-binding",
        report["plan_sha256"] == report["source_before"]["studies/finite-acquisition-mean-v1.json"],
    )
    index_path = root / "studies/results/finite-acquisition-operator-v1-summary.json"
    index_bytes = read(index_path)
    index = strict(index_bytes)
    check("archive-index-binding", sha(index_bytes) == report["archive_index_sha256"])
    check("legacy123-count", len(index["artifacts"]) == report["artifacts_verified"] == 123)
    for artifact in index["artifacts"]:
        data = read(root / artifact["path"])
        decoded = gzip.decompress(data) if artifact["encoding"] == "gzip" else data
        check(
            f"legacy-artifact:{artifact['path']}",
            len(data) == artifact["stored_bytes"]
            and sha(data) == artifact["sha256"]
            and len(decoded) == artifact["decoded_bytes"]
            and sha(decoded) == artifact["decoded_sha256"],
        )
    old = strict(
        gzip.decompress(
            read(root / "studies/results/finite-acquisition-operator-v1-normalized.json.gz")
        )
    )
    originals = {(row["scene"], row["q"]): row for row in old["rows"]}
    check("original-census32", len(old["rows"]) == len(originals) == 32)
    expected_keys = {
        (scene, q, coverage, lane)
        for scene, q in originals
        for coverage in ("saved_polygon", "analytic_D")
        for lane in ("unquantized", "png")
    }
    actual_keys = [(r["scene"], r["q"], r["coverage"], r["lane"]) for r in report["rows"]]
    check(
        "complete128-census",
        len(actual_keys) == len(set(actual_keys)) == 128 and set(actual_keys) == expected_keys,
    )
    check(
        "scene-q-census",
        len({key[0] for key in actual_keys}) == 16
        and {key[1] for key in actual_keys} == {1.0, 1.25},
    )
    geometries = {g["scene"]: g for g in report["geometry"]}
    check("geometry-census16", len(geometries) == len(report["geometry"]) == 16)
    for scene, geometry in geometries.items():
        config_folder = root / "studies/fixtures/finite-acquisition-operator-v1/captures" / scene
        metadata = strict(gzip.decompress(read(config_folder / "scene.json.gz")))
        c = metadata["config"]
        target_area = c["radius"] ** 2 * (
            math.pi / 2
            + math.asin(c["fraction"])
            + c["fraction"] * math.sqrt(1 - c["fraction"] ** 2)
        )
        exact_path = folder / f"{scene}-analytic-coverage.npy"
        read(exact_path)
        exact = np.load(exact_path, allow_pickle=False)
        source = load_npz(config_folder / "source.npz")
        area = math.fsum(exact.flat)
        delta = float(np.max(np.abs(exact - source["coverage"].astype(float))))
        passed = (
            abs(area - target_area) <= 1e-9 * max(1, c["radius"] ** 2)
            and delta <= geometry["polygon_area_loss_bound"] + 4 * np.finfo(np.float32).eps
        )
        check(
            f"saved-geometry-statistics:{scene}",
            exact.shape == (96, 96)
            and np.isfinite(exact).all()
            and geometry["analytic_area"] == area
            and geometry["closed_form_area"] == target_area
            and geometry["area_difference"] == area - target_area
            and geometry["max_coverage_difference"] == delta
            and geometry["passed"] is bool(passed),
        )
    total_work, code_changes, max_errors, compatible = 0, [], {}, {}
    cache = {}
    for row in report["rows"]:
        identity = (row["scene"], row["q"], row["coverage"], row["lane"])
        label = repr(identity)
        scene, q, coverage_name, lane = identity
        if scene not in cache:
            src = root / "studies/fixtures/finite-acquisition-operator-v1/captures" / scene
            meta = strict(gzip.decompress(read(src / "scene.json.gz")))
            source = load_npz(src / "source.npz")
            exact_path = folder / f"{scene}-analytic-coverage.npy"
            read(exact_path)
            exact = np.load(exact_path, allow_pickle=False)
            cache[scene] = src, meta, source, exact
        src, meta, source, exact = cache[scene]
        filename = "q-1.npz" if q == 1 else "q-1p25.npz"
        oldfields = load_npz(src / filename)
        archive = folder / row["stage_archive"]["file"]
        arrays = load_npz(archive)
        check(f"stage-file-sha:{label}", sha(read(archive)) == row["stage_archive"]["sha256"])
        wanted = {"coverage", "source_linear", "optical_linear", "rectified", "final"}
        if lane == "png":
            wanted |= {"encoded", "decoded_linear"}
        check(
            f"stage-schema:{label}",
            set(arrays) == wanted
            and all(
                a.shape == (96, 96) for n, a in arrays.items() if n not in {"rectified", "final"}
            )
            and all(
                arrays[n].shape == oldfields[f"{lane}_final"].shape for n in ("rectified", "final")
            )
            and all(
                a.dtype == (np.uint8 if n == "encoded" else np.float32) for n, a in arrays.items()
            ),
        )
        coverage = source["coverage"] if coverage_name == "saved_polygon" else exact
        check(
            f"coverage-input-stage:{label}",
            np.array_equal(arrays["coverage"], coverage.astype(np.float32)),
        )
        query = np.asarray(originals[(scene, q)]["pixels"], dtype=np.int64)
        shape = oldfields[f"{lane}_final"].shape
        digest = hashlib.sha256()
        for name, a in (
            ("coverage", np.asarray(coverage, dtype=np.float64)),
            ("levels", np.asarray(meta["levels_linear"], dtype=np.float64)),
            ("optical", np.asarray(source["kernel"], dtype=np.float64)),
            ("post", np.asarray(source["post_kernel"], dtype=np.float64)),
            ("map", np.asarray([[1 / q, 0, 16], [0, 1 / q, 16]], dtype=np.float64)),
            ("queries", query),
        ):
            digest.update(repr((name, a.shape, a.dtype.str)).encode())
            digest.update(a.tobytes(order="C"))
        digest.update(repr((shape, lane == "png", "finite-acquisition-v1")).encode())
        check(f"canonical-input-binding:{label}", digest.hexdigest() == row["input_sha256"])
        required = coverage.size * (
            1 + source["kernel"].size + (4 if lane == "png" else 0)
        ) + math.prod(shape) * (16 + source["post_kernel"].size)
        check(
            f"work-and-workspace:{label}",
            row["required_work"] == row["performed_work"] == required
            and row["numeric_workspace_bound_bytes"]
            == 512 * (coverage.size + math.prod(shape)) + 131072,
        )
        total_work += required
        residual = arrays["final"].astype(float) - oldfields[f"{lane}_final"].astype(float)
        predictions = [float(arrays["final"][y, x]) for x, y in query]
        sampled = [float(residual[y, x]) for x, y in query]
        check(
            f"441-query-binding:{label}",
            len(query) == len(row["predictions"]) == len(row["query_residuals"]) == 441
            and predictions == row["predictions"]
            and sampled == row["query_residuals"],
        )
        stage_errors = {
            "source_linear": float(
                np.max(
                    np.abs(
                        arrays["source_linear"].astype(float)
                        - source["source_linear"].astype(float)
                    )
                )
            ),
            "optical_linear": float(
                np.max(
                    np.abs(
                        arrays["optical_linear"].astype(float)
                        - source["optical_linear"].astype(float)
                    )
                )
            ),
            "rectified": float(
                np.max(
                    np.abs(
                        arrays["rectified"].astype(float)
                        - oldfields[f"{lane}_rectified"].astype(float)
                    )
                )
            ),
            "final": float(np.max(np.abs(residual))),
        }
        check(
            f"retained-statistics:{label}",
            stage_errors == row["stage_max_errors"]
            and row["query_max_abs"] == max(abs(x) for x in sampled)
            and row["query_rms"] == math.sqrt(math.fsum(x * x for x in sampled) / len(sampled)),
        )
        decoded_delta = (
            float(
                np.max(
                    np.abs(
                        arrays["decoded_linear"].astype(float)
                        - source["decoded_linear"].astype(float)
                    )
                )
            )
            if lane == "png"
            else 0.0
        )
        changes = (
            int(np.count_nonzero(arrays["encoded"] != source["png_rgb"][:, :, 0]))
            if lane == "png"
            else 0
        )
        gain = 25 / 16 * math.fsum(abs(x) for x in source["post_kernel"].flat)
        allowance = 0.002 + gain * decoded_delta if lane == "png" else 0.002
        if lane == "unquantized" and coverage_name == "analytic_D":
            allowance += (
                gain
                * math.fsum(abs(x) for x in source["kernel"].flat)
                * abs(meta["levels_linear"][0] - meta["levels_linear"][1])
                * (geometries[scene]["polygon_area_loss_bound"] + 4 * np.finfo(np.float32).eps)
            )
        check(
            f"encoding-and-allowance:{label}",
            row["encoding_code_changes"] == changes
            and row["decoded_source_delta"] == decoded_delta
            and row["declared_allowance"] == float(allowance),
        )
        check(
            f"saved-outcome:{label}",
            row["status"] == "evaluated"
            and row["raw_one_level_compatible"] is (max(abs(x) for x in sampled) <= 1)
            and row["passed"]
            is (stage_errors["final"] <= allowance and geometries[scene]["passed"]),
        )
        key = f"{coverage_name}/{lane}"
        max_errors[key] = max(max_errors.get(key, 0), stage_errors["final"])
        compatible[key] = compatible.get(key, 0) + row["raw_one_level_compatible"]
        if lane == "png":
            code_changes.append(changes)
        stage_records.append(
            {
                "identity": list(identity),
                "file": archive.name,
                "sha256": row["stage_archive"]["sha256"],
                "arrays": {
                    n: {
                        "shape": list(a.shape),
                        "dtype": a.dtype.str,
                        "c_order_bytes_sha256": sha(a.tobytes(order="C")),
                    }
                    for n, a in arrays.items()
                },
            }
        )
    check(
        "total-work-and-calls",
        total_work == report["declared_stage_work"] == 487211008
        and report["new_acquisition_mean_calls"] == 128,
    )
    check(
        "no-new-capture-reference-optimizer",
        all(
            report[key] == 0
            for key in ("new_captures", "old_gaussian_reference_calls", "optimizer_calls")
        ),
    )
    check(
        "saved-overall-outcome",
        report["errors"] == []
        and report["passed"] is True
        and all(row["passed"] for row in report["rows"]),
    )
    after = {p: sha(Path(p).read_bytes()) for p in input_hashes}
    check("all-read-inputs-unchanged", after == input_hashes)
    receipt = {
        "format": "independent-saved-acquisition-mean-audit-v1",
        "script_sha256": sha(Path(__file__).read_bytes()),
        "report_sha256": sha(report_bytes),
        "passed": all(c["passed"] for c in checks) and not errors,
        "checks": checks,
        "errors": errors,
        "counts": {
            "checks": len(checks),
            "passed": sum(c["passed"] for c in checks),
            "rows": len(report["rows"]),
            "source_scenes": len(cache),
            "original_output_records": len(originals),
            "stage_archives": len(stage_records),
            "stage_arrays": sum(len(x["arrays"]) for x in stage_records),
            "legacy_artifacts": len(index["artifacts"]),
            "query_predictions": len(report["rows"]) * 441,
            "declared_stage_work": total_work,
        },
        "maximum_final_absolute_difference": max_errors,
        "raw_one_level_compatible": compatible,
        "png_code_changes": {
            "rows": len(code_changes),
            "rows_with_changes": sum(x > 0 for x in code_changes),
            "total_changed_entries": sum(code_changes),
            "maximum_per_row": max(code_changes),
        },
        "inputs_before": input_hashes,
        "inputs_after": after,
        "stage_records": stage_records,
        "audit_scope": {
            "new_scientific_model_calls": 0,
            "new_captures": 0,
            "new_optimizers": 0,
            "scientific_imports_blocked": ["backend", "tests", "cv2"],
            "operations": "strict JSON, hash checks, numeric archive reads, saved-array indexing/differences/statistics and canonical input digest reconstruction only; no forward stage evaluation",
        },
    }
    with args.output.open("x") as stream:
        json.dump(receipt, stream, allow_nan=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "passed": receipt["passed"],
                "counts": receipt["counts"],
                "png_code_changes": receipt["png_code_changes"],
                "maximum_final_absolute_difference": max_errors,
            },
            sort_keys=True,
        )
    )
    return int(not receipt["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
