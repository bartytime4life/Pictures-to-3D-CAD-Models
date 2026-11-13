"""Read saved artifacts only; no NumPy/backend/generator/reference imports."""

import argparse
import ast
import gzip
import hashlib
import json
import math
import struct
import traceback
import zipfile
from collections import Counter
from pathlib import Path

RAW_SHA = "15df34975e0d2c56325a8e4efbea07145a6f0958133e4413a1b36f2ae5a29078"
FIRST_SHA = "c5cef04f49969d607fb85c425bb6b1192e4ef60e373f6412eaf55cc664a2ffc0"
OLD_SHA = "21a2f8389094a76bbd14a3d7a43933fe56a32da8296092ebdcdac2980220e72a"
NEW_SHA = "ce46423ede03885fcd702204abe97653a86c77a2ebc86999605d8d733c820a51"
SOURCE = {
    "coverage",
    "source_linear",
    "optical_linear",
    "png_rgb",
    "decoded_linear",
    "kernel",
    "post_kernel",
}
FIELDS = {"unquantized_rectified", "unquantized_final", "png_rectified", "png_final"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse(data):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError("duplicate key: " + k)
            out[k] = v
        return out

    def reject(x):
        raise ValueError("nonfinite JSON: " + x)

    def finite(x):
        y = float(x)
        if not math.isfinite(y):
            reject(x)
        return y

    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject, parse_float=finite)


def tags(v, path=()):
    out = []
    if isinstance(v, dict):
        for k in ("invalid_python_value", "invalid_nonfinite_float"):
            if k in v:
                out.append({"path": list(path), "kind": k, "value": v[k]})
        for k, child in v.items():
            out.extend(tags(child, path + (k,)))
    elif isinstance(v, list):
        for i, child in enumerate(v):
            out.extend(tags(child, path + (i,)))
    return out


def load_npy(data):
    if data[:6] != b"\x93NUMPY":
        raise ValueError("not NPY")
    ver = tuple(data[6:8])
    if ver == (1, 0):
        size, offset = struct.unpack("<H", data[8:10])[0], 10
    elif ver in ((2, 0), (3, 0)):
        size, offset = struct.unpack("<I", data[8:12])[0], 12
    else:
        raise ValueError("unsupported NPY version")
    if size > 65536:
        raise ValueError("NPY header limit")
    h = ast.literal_eval(data[offset : offset + size].decode())
    formats = {"<f4": ("<f", 4), "<f8": ("<d", 8), "|u1": ("B", 1)}
    if (
        set(h) != {"descr", "shape", "fortran_order"}
        or h["fortran_order"] is not False
        or h["descr"] not in formats
    ):
        raise ValueError("object or undeclared NPY type/layout")
    shape = h["shape"]
    if not isinstance(shape, tuple) or any(
        type(n) is not int or not 0 < n <= 100000 for n in shape
    ):
        raise ValueError("NPY shape limit")
    fmt, width = formats[h["descr"]]
    raw = data[offset + size :]
    if len(raw) != math.prod(shape) * width:
        raise ValueError("NPY byte count")
    if h["descr"] != "|u1" and not all(math.isfinite(x[0]) for x in struct.iter_unpack(fmt, raw)):
        raise ValueError("nonfinite NPY")
    return {"dtype": h["descr"], "shape": list(shape), "raw": raw, "sha": sha(raw)}


class Audit:
    def __init__(self):
        self.count = 0
        self.failures = []
        self.scenes = []

    def check(self, ok, label, detail=None):
        self.count += 1
        if not ok:
            self.failures.append({"check": label, "detail": detail})

    def sources(self, before, after, root, label):
        self.check(before == after, label + "/before_after")
        for name, expected in before.items():
            self.check(sha((root / name).read_bytes()) == expected, label + "/" + name)

    def archive(self, path, record, keys, label):
        self.check(
            path.name == record["file"] and sha(path.read_bytes()) == record["sha256"],
            label + "/container",
        )
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)) or any(i.file_size > 20000000 for i in infos):
                raise ValueError("NPZ duplicate/size")
            self.check(set(names) == {k + ".npy" for k in keys}, label + "/numeric_member_census")
            arrays = {n[:-4]: load_npy(z.read(n)) for n in names}
        self.check(set(record["arrays"]) == keys, label + "/record_census")
        for key, arr in arrays.items():
            wanted = record["arrays"][key]
            self.check(
                arr["dtype"] == wanted["dtype"]
                and arr["shape"] == wanted["shape"]
                and arr["sha"] == wanted["c_order_bytes_sha256"],
                label + "/" + key + "/raw_binding",
            )
        return arrays


class BootstrapOnly(ast.NodeTransformer):
    def visit_Import(self, node):
        return None if any(n.name == "importlib.util" for n in node.names) else node

    def visit_ImportFrom(self, node):
        return None if node.module == "tests" else node

    def visit_Assign(self, node):
        if any(isinstance(t, ast.Name) and t.id == "SOURCE_PATHS" for t in node.targets):
            node.value.elts = [
                x
                for x in node.value.elts
                if not isinstance(x, ast.Constant) or x.value != "tests/__init__.py"
            ]
        if any(isinstance(t, ast.Name) and t.id in ("spec", "synthetic") for t in node.targets):
            return None
        if any(
            isinstance(t, ast.Subscript) and ast.unparse(t.value) == "sys.modules"
            for t in node.targets
        ):
            return None
        return self.generic_visit(node)

    def visit_If(self, node):
        if "spec is None" in ast.unparse(node.test):
            return None
        return self.generic_visit(node)

    def visit_Expr(self, node):
        if ast.unparse(node.value).startswith("spec.loader.exec_module("):
            return None
        return self.generic_visit(node)


def run(root, directory, a):
    raw = (directory / "report.json").read_bytes()
    a.check(sha(raw) == RAW_SHA, "raw_report_hash")
    r = parse(raw)
    bad = tags(r)
    kinds = dict(
        Counter(t["value"].get("type") for t in bad if t["kind"] == "invalid_python_value")
    )
    a.check(
        len(bad) == 320
        and kinds == {"float32": 288, "bool": 32}
        and all(t["kind"] == "invalid_python_value" for t in bad),
        "known_raw_serialization_anomaly",
        kinds,
    )
    plan = parse((root / "studies/finite-acquisition-operator-v1.json").read_bytes())
    cp = parse((root / "studies/finite-acquisition-operator-v1-continuation-v1.json").read_bytes())
    firstraw = gzip.decompress((root / cp["original_report"]).read_bytes())
    a.check(sha(firstraw) == FIRST_SHA, "first_decoded_hash")
    first = parse(firstraw)
    a.check(
        first["protocol_passed"] is False
        and first["source_unchanged"] is True
        and not first["scenes"],
        "first_failed_zero_captures",
    )
    a.check(
        len(first["rows"]) == 32 and all(x["status"] == "scene_exception" for x in first["rows"]),
        "first_32_unknown_rows",
    )
    a.check(first["source_before"] == first["source_after"], "first_source_unchanged")
    old = (
        root
        / "studies/fixtures/finite-acquisition-operator-v1/bootstrap-failure/stage-helper-original.py.txt"
    ).read_bytes()
    new = (root / "studies/verification/finite-acquisition-stages-v1.py").read_bytes()
    a.check(sha(old) == OLD_SHA and sha(new) == NEW_SHA, "bootstrap_source_pair")
    trees = [
        ast.dump(BootstrapOnly().visit(ast.parse(x)), include_attributes=False) for x in (old, new)
    ]
    a.check(trees[0] == trees[1], "bootstrap_only_AST_difference")
    for name, expected in first["source_before"].items():
        if name != cp["bootstrap_only_allowed_source_change"]:
            a.check(sha((root / name).read_bytes()) == expected, "first_preserved/" + name)
    manifest = parse(
        (
            root / "studies/fixtures/finite-acquisition-operator-v1/bootstrap-failure/manifest.json"
        ).read_bytes()
    )
    for item in manifest["artifacts"]:
        data = (root / item["path"]).read_bytes()
        a.check(sha(data) == item["sha256"], "first_archive/" + item["path"])
        if "decoded_sha256" in item:
            value = gzip.decompress(data)
            a.check(
                len(value) == item["decoded_bytes"] and sha(value) == item["decoded_sha256"],
                "first_decoded/" + item["path"],
            )
    for prefix in ("", "continuation_"):
        a.sources(r[prefix + "source_before"], r[prefix + "source_after"], root, prefix + "sources")
        a.check(r[prefix + "source_unchanged"] is True, prefix + "source_flag")
    expected_ids = [(c["name"], q) for c in plan["scenes"] for q in (1.0, 1.25)]
    a.check([(x["scene"], x["q"]) for x in r["rows"]] == expected_ids, "32_row_census")
    a.check([s["metadata"]["config"] for s in r["scenes"]] == plan["scenes"], "16_scene_census")
    from PIL import Image

    helper_tags = []
    for config, scene in zip(plan["scenes"], r["scenes"], strict=True):
        name = config["name"]
        here = directory / name
        m = parse((here / "scene.json").read_bytes())
        helper_tags.extend(tags(m))
        a.check(
            m == scene["metadata"] and m["status"] == "complete" and m["source_unchanged"] is True,
            name + "/metadata",
        )
        a.sources(m["source_hashes_before"], m["source_hashes_after"], root, name + "/source")
        a.check(m["levels_linear"][0] > m["levels_linear"][1], name + "/level_order")
        a.check(
            m["source_geometry"]["source_shape"] == [96, 96]
            and m["source_geometry"]["arc_vertices"] == 8193,
            name + "/source_frame",
        )
        a.check(
            m["work_scope"] == {"inverse_optimizer_calls": 0, "new_full_photo_traces": 0},
            name + "/no_inverse",
        )
        a.check(
            m["stage_call_counts"]["attempted"]
            == m["stage_call_counts"]["completed"]
            == len(m["stage_calls"])
            == 18
            and all(c["completed"] is True for c in m["stage_calls"]),
            name + "/stage_calls",
        )
        source = a.archive(
            here / "source.npz", m["source_artifacts"]["arrays"], SOURCE, name + "/source_npz"
        )
        a.check(
            all(
                source[k]["shape"] == [96, 96] and source[k]["dtype"] == "<f4"
                for k in ("coverage", "source_linear", "optical_linear", "decoded_linear")
            ),
            name + "/source_shapes",
        )
        side = 11 if config["blur"] == "isotropic" else 25
        a.check(
            source["kernel"]["shape"] == [side, side] and source["post_kernel"]["shape"] == [7, 7],
            name + "/kernel_shapes",
        )
        png = m["source_artifacts"]["png"]
        a.check(sha((here / png["file"]).read_bytes()) == png["sha256"], name + "/png_hash")
        with Image.open(here / png["file"]) as im:
            a.check(
                im.format == "PNG" and im.mode == "RGB" and im.size == (96, 96),
                name + "/png_header",
            )
            rgb = im.tobytes()
        a.check(
            source["png_rgb"]["shape"] == [96, 96, 3]
            and source["png_rgb"]["dtype"] == "|u1"
            and source["png_rgb"]["raw"] == rgb
            and sha(rgb) == png["decoded_rgb_record"]["c_order_bytes_sha256"]
            and png["lossless_rgb_equal"] is True,
            name + "/exact_png_RGB",
        )
        a.check([x["q"] for x in m["rows"]] == [1.0, 1.25], name + "/two_q")
        for entry in m["rows"]:
            q = entry["q"]
            label = name + "/q" + str(q)
            a.check(
                entry["M"] == [[1.0, 0.0, 16.5], [0.0, 1.0, 16.5], [0.0, 0.0, 1.0]]
                and entry["k1"] == 0
                and entry["plane_size"] == [64.0, 64.0]
                and entry["status"] == "complete",
                label + "/map",
            )
            fields = a.archive(
                here / entry["fields_file"], entry["stage_arrays"], FIELDS, label + "/fields"
            )
            shape = [64, 64] if q == 1 else [80, 80]
            a.check(
                all(x["shape"] == shape and x["dtype"] == "<f4" for x in fields.values()),
                label + "/field_shapes",
            )
            a.check(
                set(entry["smoothing_comparison"]) == {"unquantized", "png"}, label + "/post_census"
            )
            a.check(
                all(
                    type(x[k]) is float and math.isfinite(x[k]) and x[k] >= 0
                    for x in entry["smoothing_comparison"].values()
                    for k in ("max_abs_difference", "whole_max_abs_difference")
                ),
                label + "/post_values",
            )
        a.scenes.append(
            {"scene": name, "source_arrays": 7, "field_arrays": 8, "png_RGB_exact": True}
        )
    a.check(not helper_tags, "helper_metadata_JSON_native", helper_tags)
    for name in ("exact_keys", "production_keys", "independent_gaussian"):
        a.check(r["controls"][name] == first["controls"][name], "cached_control/" + name)
    calls = r["forward_calls"]
    reused = [c for c in calls if c["performed_this_continuation"] is False]
    fresh = [c for c in calls if c["performed_this_continuation"] is True]
    a.check(
        calls[:4] == reused and len(reused) == 4 and sum(c["queries"] for c in reused) == 24,
        "4_cached_calls_24_queries",
    )
    for i, c in enumerate(reused):
        stripped = {
            k: v
            for k, v in c.items()
            if k
            not in {"performed_this_continuation", "origin_report_sha256", "original_call_index"}
        }
        a.check(
            stripped == first["forward_calls"][i]
            and c["original_call_index"] == i
            and c["origin_report_sha256"] == FIRST_SHA,
            "cached_origin/" + str(i),
        )
    a.check(
        len(fresh) == 64 and sum(c["queries"] for c in fresh) == 28224, "64_new_calls_28224_queries"
    )
    for group, members in (("new", fresh), ("reused", reused)):
        wanted = {
            "calls": len(members),
            "queries": sum(c["queries"] for c in members),
            "completed_calls": sum(c["completed"] for c in members),
            "evaluations": sum(c.get("evaluations", 0) for c in members),
            "panels": sum(c.get("panels", 0) for c in members),
        }
        a.check(r["forward_work_by_execution"][group] == wanted, "work_totals/" + group)
    for i, c in enumerate(calls):
        value = c["returned_result"]
        a.check(
            c["completed"] is True
            and c["valid_payload"] is True
            and c["evaluations"] == value["evaluations"]
            and c["panels"] == value["panels"],
            f"calls/{i}/complete_work",
        )
        a.check(
            all(
                len(value[k]) == c["queries"]
                for k in ("probabilities", "statuses", "estimated_errors", "tail_bounds")
            ),
            f"calls/{i}/array_lengths",
        )
        a.check(
            all(s == "resolved" for s in value["statuses"])
            and all(
                type(e) in (int, float) and math.isfinite(e) and e >= 0
                for k in ("estimated_errors", "tail_bounds")
                for e in value[k]
            ),
            f"calls/{i}/statuses_errors",
        )
    for i, row in enumerate(r["rows"]):
        q = row["q"]
        cx, cy = [math.floor(q * c) for c in plan["scenes"][i // 2]["centre"]]
        points = [[cx + x, cy + y] for y in range(-20, 21, 2) for x in range(-20, 21, 2)]
        a.check(row["pixels"] == points, f"rows/{i}/query_grid")
        for j, model in enumerate(("nominal_gaussian", "moment_gaussian")):
            c = fresh[2 * i + j]
            a.check(
                c["lane"] == "main_" + model
                and c["pixels"] == points
                and c["returned_result"] == row["models"][model]["api"]
                and c["supplied"]["homography"] == [[q, 0, 0], [0, q, 0], [0, 0, 1]],
                f"rows/{i}/model_call/{model}",
            )
    return {
        "raw_sha256": sha(raw),
        "reported_protocol_passed": r["protocol_passed"],
        "raw_tag_count": len(bad),
        "raw_tag_types": kinds,
        "raw_tags": bad,
        "raw_serialization_contract_passed": not bad,
        "helper_metadata_tags": len(helper_tags),
        "source_files": len(r["source_before"]),
        "continuation_source_files": len(r["continuation_source_before"]),
        "scenes": len(r["scenes"]),
        "rows": len(r["rows"]),
        "new_calls": len(fresh),
        "new_queries": sum(c["queries"] for c in fresh),
        "cached_calls": len(reused),
        "cached_queries": sum(c["queries"] for c in reused),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        p.error("output must be fresh with existing parent")
    a = Audit()
    result = {
        "format": "finite-acquisition-saved-artifact-audit",
        "auditor_sha256": sha(Path(__file__).read_bytes()),
        "scientific_operator_calls": 0,
        "numpy_imports": 0,
        "backend_generator_reference_imports": 0,
    }
    try:
        result["summary"] = run(args.root.resolve(), args.run_dir.resolve(), a)
    except Exception as exc:  # noqa: BLE001 -- write a durable failed audit.
        a.check(
            False,
            "audit_exception",
            {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
        )
    result.update(
        checks=a.count,
        artifact_failures=a.failures,
        artifact_checks_passed=not a.failures,
        scene_summaries=a.scenes,
    )
    result["raw_serialization_contract_passed"] = result.get("summary", {}).get(
        "raw_serialization_contract_passed", False
    )
    result["passed"] = not a.failures and result["raw_serialization_contract_passed"]
    with args.output.open("x") as out:
        out.write(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "checks",
                    "artifact_checks_passed",
                    "raw_serialization_contract_passed",
                    "passed",
                )
            }
        )
    )
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
