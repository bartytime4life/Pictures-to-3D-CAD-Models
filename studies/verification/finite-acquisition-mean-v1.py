#!/usr/bin/env python3
"""Frozen complete saved-capture acquisition-mean comparison; no new capture/fit."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = "studies/finite-acquisition-mean-v1.json"
SOURCES = (
    PLAN,
    "backend/__init__.py",
    "backend/finite_aperture.py",
    "backend/finite_acquisition.py",
    "tests/test_finite_aperture.py",
    "tests/test_finite_acquisition.py",
    "studies/verification/finite-acquisition-mean-v1.py",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot():
    return {p: sha((ROOT / p).read_bytes()) for p in SOURCES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    out = args.output_dir.absolute()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():
        parser.error("output directory must be fresh with an existing parent")
    before = snapshot()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for path in SOURCES:
        committed = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
        if sha(committed) != before[path]:
            parser.error(f"source not frozen in HEAD: {path}")
    out.mkdir()
    report = {
        "format": "finite-acquisition-mean-study-v1",
        "source_commit": commit,
        "source_before": before,
        "source_after": {},
        "source_unchanged": False,
        "plan_sha256": before[PLAN],
        "artifacts_verified": 0,
        "geometry": [],
        "rows": [],
        "errors": [],
        "passed": False,
        "new_captures": 0,
        "old_gaussian_reference_calls": 0,
        "optimizer_calls": 0,
        "new_acquisition_mean_calls": 0,
        "declared_stage_work": 0,
    }
    progress = (out / "progress.jsonl").open("x")

    def emit(record):
        progress.write(json.dumps(record, allow_nan=False, sort_keys=True) + "\n")
        progress.flush()

    try:
        sys.path.insert(0, str(ROOT))
        import numpy as np

        from backend.finite_acquisition import acquisition_mean
        from backend.finite_aperture import segment_cell_coverage

        report["versions"] = {"python": sys.version, "numpy": np.__version__}
        plan = json.loads((ROOT / PLAN).read_text())
        indexpath = ROOT / plan["population"]["archive_index"]
        index = json.loads(indexpath.read_text())
        report["archive_index_sha256"] = sha(indexpath.read_bytes())
        assert len(index["artifacts"]) == 123
        for item in index["artifacts"]:
            b = (ROOT / item["path"]).read_bytes()
            assert sha(b) == item["sha256"] and len(b) == item["stored_bytes"], item["path"]
            d = gzip.decompress(b) if item["encoding"] == "gzip" else b
            assert sha(d) == item["decoded_sha256"] and len(d) == item["decoded_bytes"]
            report["artifacts_verified"] += 1
        old = json.loads(
            gzip.decompress(
                (
                    ROOT / "studies/results/finite-acquisition-operator-v1-normalized.json.gz"
                ).read_bytes()
            )
        )
        assert len(old["rows"]) == 32
        slots = {}
        for original in old["rows"]:
            for coverage_name in ("saved_polygon", "analytic_D"):
                for lane in ("unquantized", "png"):
                    key = (original["scene"], original["q"], coverage_name, lane)
                    slot = {
                        "scene": key[0],
                        "q": key[1],
                        "coverage": key[2],
                        "lane": key[3],
                        "status": "not_attempted",
                        "passed": False,
                        "predictions": [None] * 441,
                        "query_residuals": [None] * 441,
                    }
                    slots[key] = slot
                    report["rows"].append(slot)
        with (out / "census.json").open("x") as stream:
            json.dump(report["rows"], stream, allow_nan=False, sort_keys=True, indent=2)
        archive = ROOT / "studies/fixtures/finite-acquisition-operator-v1/captures"
        scene_cache = {}
        for original in old["rows"]:
            scene, q = original["scene"], original["q"]
            rowbase = {"scene": scene, "q": q}
            try:
                if scene not in scene_cache:
                    folder = archive / scene
                    metadata = json.loads(gzip.decompress((folder / "scene.json.gz").read_bytes()))
                    with np.load(folder / "source.npz", allow_pickle=False) as z:
                        source = {name: z[name].copy() for name in z.files}
                    c = metadata["config"]
                    exact = segment_cell_coverage(
                        centre=c["centre"],
                        radius=c["radius"],
                        fraction=c["fraction"],
                        normal=metadata["source_geometry"]["normal"],
                        shape=(96, 96),
                        origin=(-16.0, -16.0),
                        pitch=1.0,
                    )
                    target_area = c["radius"] ** 2 * (
                        math.pi / 2
                        + math.asin(c["fraction"])
                        + c["fraction"] * math.sqrt(1 - c["fraction"] ** 2)
                    )
                    area = math.fsum(exact.flat)
                    delta = float(np.max(np.abs(exact - source["coverage"].astype(float))))
                    loss = original["tessellation"]["area_loss_bound"]
                    geometry = {
                        "scene": scene,
                        "analytic_area": area,
                        "closed_form_area": target_area,
                        "area_difference": area - target_area,
                        "max_coverage_difference": delta,
                        "polygon_area_loss_bound": loss,
                        "passed": bool(
                            abs(area - target_area) <= 1e-9 * max(1, c["radius"] ** 2)
                            and delta <= loss + 4 * np.finfo(np.float32).eps
                        ),
                    }
                    report["geometry"].append(geometry)
                    with (out / f"{scene}-analytic-coverage.npy").open("xb") as stream:
                        np.save(stream, exact, allow_pickle=False)
                    scene_cache[scene] = (metadata, source, exact, geometry)
                metadata, source, exact, geometry = scene_cache[scene]
                filename = "q-1.npz" if q == 1 else "q-1p25.npz"
                with np.load(archive / scene / filename, allow_pickle=False) as z:
                    fields = {name: z[name].copy() for name in z.files}
                query = np.asarray(original["pixels"], dtype=np.int64)
                for coverage_name, coverage in (
                    ("saved_polygon", source["coverage"]),
                    ("analytic_D", exact),
                ):
                    for encoded in (False, True):
                        lane = "png" if encoded else "unquantized"
                        record = slots[(scene, q, coverage_name, lane)]
                        record["status"] = "attempted"
                        emit(
                            {
                                k: v
                                for k, v in record.items()
                                if k not in {"predictions", "query_residuals"}
                            }
                        )
                        report["new_acquisition_mean_calls"] += 1
                        result = acquisition_mean(
                            coverage,
                            levels=metadata["levels_linear"],
                            optical_kernel=source["kernel"],
                            output_shape=fields[f"{lane}_final"].shape,
                            output_to_source_index=((1 / q, 0, 16), (0, 1 / q, 16)),
                            post_kernel=source["post_kernel"],
                            queries=query,
                            srgb8=encoded,
                        )
                        stages = dict(result.stages)
                        report["declared_stage_work"] += result.performed_work
                        final = stages["final"].astype(float)
                        oldfinal = fields[f"{lane}_final"].astype(float)
                        residual = final - oldfinal
                        predictions = [float(x) for x in result.intensities]
                        sampled = [float(residual[y, x]) for x, y in query]
                        decoded_delta = (
                            float(
                                np.max(
                                    np.abs(
                                        stages["decoded_linear"].astype(float)
                                        - source["decoded_linear"].astype(float)
                                    )
                                )
                            )
                            if encoded
                            else 0.0
                        )
                        gain = 25 / 16 * math.fsum(abs(x) for x in source["post_kernel"].flat)
                        if encoded:
                            allowance = 0.002 + gain * decoded_delta
                        elif coverage_name == "saved_polygon":
                            allowance = 0.002
                        else:
                            allowance = 0.002 + gain * math.fsum(
                                abs(x) for x in source["kernel"].flat
                            ) * abs(metadata["levels_linear"][0] - metadata["levels_linear"][1]) * (
                                geometry["polygon_area_loss_bound"] + 4 * np.finfo(np.float32).eps
                            )
                        stage_errors = {
                            "source_linear": float(
                                np.max(
                                    np.abs(
                                        stages["source_linear"].astype(float)
                                        - source["source_linear"].astype(float)
                                    )
                                )
                            ),
                            "optical_linear": float(
                                np.max(
                                    np.abs(
                                        stages["optical_linear"].astype(float)
                                        - source["optical_linear"].astype(float)
                                    )
                                )
                            ),
                            "rectified": float(
                                np.max(
                                    np.abs(
                                        stages["rectified"].astype(float)
                                        - fields[f"{lane}_rectified"].astype(float)
                                    )
                                )
                            ),
                            "final": float(np.max(np.abs(residual))),
                        }
                        code_changes = (
                            int(np.count_nonzero(stages["encoded"] != source["png_rgb"][:, :, 0]))
                            if encoded
                            else 0
                        )
                        record.update(
                            status="evaluated",
                            input_sha256=result.input_sha256,
                            required_work=result.required_work,
                            performed_work=result.performed_work,
                            numeric_workspace_bound_bytes=result.numeric_workspace_bound_bytes,
                            stage_max_errors=stage_errors,
                            encoding_code_changes=code_changes,
                            decoded_source_delta=decoded_delta,
                            declared_allowance=float(allowance),
                            predictions=predictions,
                            query_residuals=sampled,
                            query_max_abs=float(max(abs(x) for x in sampled)),
                            query_rms=math.sqrt(math.fsum(x * x for x in sampled) / len(sampled)),
                            raw_one_level_compatible=bool(max(abs(x) for x in sampled) <= 1),
                            passed=bool(
                                all(s == "resolved" for s in result.statuses)
                                and stage_errors["final"] <= allowance
                                and geometry["passed"]
                            ),
                        )
                        target = out / f"{scene}-q{q:g}-{coverage_name}-{lane}.npz"
                        with target.open("xb") as stream:
                            np.savez_compressed(stream, **stages)
                        record["stage_archive"] = {
                            "file": target.name,
                            "sha256": sha(target.read_bytes()),
                        }
                        emit(
                            {
                                k: v
                                for k, v in record.items()
                                if k not in {"predictions", "query_residuals"}
                            }
                        )
            except Exception as exc:  # noqa: BLE001 -- preserve every scene's later eligibility.
                failure = {
                    **rowbase,
                    "status": "exception",
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                    "passed": False,
                }
                emit(failure)
                for key, slot in slots.items():
                    if key[:2] == (scene, q) and "stage_archive" not in slot:
                        slot.update(failure)
    except Exception as exc:  # noqa: BLE001 -- retain preflight/import failures.
        report["errors"].append(
            {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        )
    finally:
        try:
            report["source_after"] = snapshot()
        except OSError as exc:
            report["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        report["source_unchanged"] = before == report["source_after"]
        report["passed"] = bool(
            not report["errors"]
            and report["source_unchanged"]
            and report["artifacts_verified"] == 123
            and len(report["geometry"]) == 16
            and len(report["rows"]) == 128
            and all(r["passed"] for r in report["rows"])
        )
        progress.close()
        with (out / "report.json").open("x") as stream:
            json.dump(report, stream, allow_nan=False, sort_keys=True, indent=2)
            stream.write("\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "passed",
                    "new_acquisition_mean_calls",
                    "declared_stage_work",
                    "source_unchanged",
                )
            }
        )
    )
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
