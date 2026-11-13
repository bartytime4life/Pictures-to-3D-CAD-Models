#!/usr/bin/env python3
"""Audit the frozen cell-sensitivity report using saved data and stdlib only.

No candidate, reference, renderer, numerical package or case generator is run.
Complement disk-reference arrays were not saved: their coverage/Cx/Cy/R
maxima cannot be independently reconstructed by this auditor.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path, PurePosixPath

EXPECTED_SHA = "d72bff9c6a7f8b96b540a006623a59f8dfcc9b969f69e97f885eca09bec7be59"
EXPECTED_COMMIT = "c47214d098a234f28784cb174429e687e799a2bf"
EXPECTED_SOURCE_ZIP_SHA = "cf896934f7ce83280e77785dfa83a13a39219660d1c7a0ba33bde0123bccef9a"
ORDER = ["centre_x", "centre_y", "radius", "fraction", "normal_angle"]
KINDS = ["translation", "rotation90", "reflection", "scale2", "subdivision", "complement"]
SPECIAL_NAMES = [
    "coincident-left",
    "coincident-bottom",
    "near-coincidence-inside",
    "near-coincidence-outside",
    "isolated-circle-tangent",
    "isolated-chord-corner",
    "fraction-minus-one",
    "fraction-plus-one",
    "large-world-small-cell",
    "multiple-circle-spans",
    "budget-before-cellwork",
]
FORBIDDEN = {"backend", "numpy", "scipy", "cv2", "PIL", "tests", "torch", "matplotlib"}
BLOCKED = []


class ModelImportBlock:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition(".")[0] in FORBIDDEN:
            BLOCKED.append(fullname)
            raise ImportError(f"saved-data audit forbids model import: {fullname}")


sys.meta_path.insert(0, ModelImportBlock())


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def decode(data):
    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def default_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "backend").is_dir():
            return parent
    return Path.cwd()


class Checks:
    def __init__(self):
        self.counts = Counter()
        self.failures = []

    def check(self, condition, category, message):
        self.counts[category] += 1
        if not condition:
            self.failures.append({"category": category, "message": message})

    def close(self, actual, expected, category, message):
        valid = (
            type(actual) in (int, float)
            and type(expected) in (int, float)
            and math.isfinite(actual)
            and math.isfinite(expected)
        )
        tolerance = 64 * math.ulp(max(1.0, abs(expected))) if valid else 0
        self.check(valid and abs(actual - expected) <= tolerance, category, message)


def native(value, checks, path="$", counts=None):
    if counts is None:
        counts = Counter()
    counts[type(value).__name__] += 1
    checks.check(type(value) in (dict, list, str, int, float, bool, type(None)), "json", path)
    if isinstance(value, dict):
        checks.check("invalid_python_value" not in value, "json", f"{path}: scalar marker absent")
        for key, item in value.items():
            checks.check(type(key) is str, "json", f"{path}: string key")
            native(item, checks, f"{path}.{key}", counts)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            native(item, checks, f"{path}[{index}]", counts)
    elif type(value) is float:
        checks.check(math.isfinite(value), "json", f"{path}: finite")
    return counts


@dataclass(frozen=True)
class _Segment:
    centre: tuple
    radius: float
    centre_exact: tuple
    radius_exact: Fraction
    fraction: Fraction
    normal: tuple


def binding(case):
    # Reconstruct only the input-format/hash contract, not any geometric result.
    centre = tuple(map(float, case["centre"]))
    radius = float(case["radius"])
    fraction = float(case["fraction"])
    normal = tuple(map(float, case["normal"]))
    length = math.hypot(*normal)
    stored = tuple(Fraction(component / length) for component in normal)
    segment = _Segment(
        centre, radius, tuple(map(Fraction, centre)), Fraction(radius), Fraction(fraction), stored
    )
    values = (
        segment,
        tuple(case["shape"]),
        tuple(map(Fraction, case["origin"])),
        Fraction(case["pitch"]),
        "finite-cell-sensitivity-v1",
    )
    return sha(repr(values).encode())


def source_bytes(root, archive, paths, checks):
    data = {}
    archive_records = {}
    if archive is None:
        for name in paths:
            data[name] = (root / name).read_bytes()
        return data, {"mode": "local bytes", "git_required": False}
    raw = archive.read_bytes()
    checks.check(sha(raw) == EXPECTED_SOURCE_ZIP_SHA, "source", "exact public recorded-source ZIP")
    with zipfile.ZipFile(archive) as saved:
        members = [entry for entry in saved.infolist() if not entry.is_dir()]
        checks.check(
            len({entry.filename for entry in members}) == len(members),
            "source",
            "unique source ZIP names",
        )
        checks.check(len(members) <= 1000, "source", "recorded source bounded file count")
        checks.check(
            sum(entry.file_size for entry in members) <= 50_000_000,
            "source",
            "recorded source bounded expanded bytes",
        )
        if len(members) > 1000 or sum(entry.file_size for entry in members) > 50_000_000:
            raise ValueError("recorded source archive exceeds audit limits")
        for entry in members:
            path = PurePosixPath(entry.filename)
            checks.check(
                not path.is_absolute() and ".." not in path.parts,
                "source",
                f"safe source member {entry.filename}",
            )
            contents = saved.read(entry)
            archive_records[entry.filename] = {"bytes": len(contents), "sha256": sha(contents)}
        manifest = decode(saved.read("manifest.json"))
        checks.check(
            manifest["source_commit"] == EXPECTED_COMMIT,
            "source",
            "recorded source manifest commit",
        )
        checks.check(len(manifest["files"]) == 41, "source", "all41 recorded source files")
        checks.check(
            set(archive_records)
            == {item["path"] for item in manifest["files"]} | {"manifest.json"},
            "source",
            "complete source manifest membership",
        )
        for item in manifest["files"]:
            contents = saved.read(item["path"])
            checks.check(
                len(contents) == item["bytes"], "source", "manifest length: " + item["path"]
            )
            checks.check(
                sha(contents) == item["sha256"], "source", "manifest SHA256: " + item["path"]
            )
            blob = b"blob " + str(len(contents)).encode() + b"\0" + contents
            checks.check(
                hashlib.sha1(blob).hexdigest() == item["git_blob_sha1"],
                "source",
                "Git blob bytes: " + item["path"],
            )
            checks.check(
                item["mode"] in {"100644", "100755"},
                "source",
                "recorded file mode: " + item["path"],
            )
        for name in paths:
            matches = [
                entry
                for entry in members
                if entry.filename == name or entry.filename.endswith("/" + name)
            ]
            checks.check(len(matches) == 1, "source", f"unique recorded source {name}")
            if len(matches) != 1:
                raise ValueError(f"missing/ambiguous recorded source: {name}")
            data[name] = saved.read(matches[0])
    return data, {
        "mode": "recorded ZIP read as data",
        "git_required": False,
        "archive_sha256": sha(raw),
        "archive_bytes": len(raw),
        "members": archive_records,
    }


def record_checks(record, case, checks, label):
    rows, cols = case["shape"]
    size = rows * cols
    checks.check(record["shape"] == [rows, cols], "schema", label + ": shape")
    checks.check(record["parameter_order"] == ORDER, "schema", label + ": columns")
    checks.check(len(record["cells"]) == size, "schema", label + ": cell retention")
    checks.check(
        record["input_sha256"] == binding(case), "binding", label + ": geometry input hash"
    )
    for name in ("required_work", "performed_work", "numeric_workspace_bound_bytes"):
        checks.check(type(record[name]) is int and record[name] >= 0, "work", label + ": " + name)
    checks.check(record["required_work"] == size, "work", label + ": required cell work")
    refused = size > case.get("max_work", 65536)
    checks.check(
        record["performed_work"] == (0 if refused else size),
        "work",
        label + ": performed cell work",
    )
    checks.check(
        record["numeric_workspace_bound_bytes"] == 256 * size + 65536,
        "work",
        label + ": declared numeric workspace",
    )
    for index, cell in enumerate(record["cells"]):
        status = cell["status"]
        checks.check(
            status
            in {"resolved", "nondifferentiable", "parameter_endpoint", "unresolved", "work_limit"},
            "schema",
            f"{label}:{index} status",
        )
        coverage = cell["coverage"]
        checks.check(
            (coverage is None and status != "resolved")
            or (type(coverage) in (int, float) and math.isfinite(coverage) and 0 <= coverage <= 1),
            "schema",
            f"{label}:{index} coverage",
        )
        if status == "resolved":
            for name in ("jacobian", "estimated_absolute_error"):
                values = cell[name]
                checks.check(
                    isinstance(values, list) and len(values) == 5,
                    "schema",
                    f"{label}:{index} {name} columns",
                )
                checks.check(
                    all(type(value) in (int, float) and math.isfinite(value) for value in values),
                    "schema",
                    f"{label}:{index} {name} finite",
                )
            checks.check(
                all(value >= 0 for value in cell["estimated_absolute_error"]),
                "schema",
                f"{label}:{index} nonnegative errors",
            )
        else:
            checks.check(
                cell["jacobian"] is None and cell["estimated_absolute_error"] is None,
                "unknown",
                f"{label}:{index} unknown is not zero",
            )
        if refused:
            checks.check(
                status == "work_limit" and coverage is None,
                "unknown",
                f"{label}:{index} refusal retains unknown",
            )


def reference_checks_saved(row, settings, checks, maxima):
    reference = row["independent_reference"]
    case = row["case"]
    pitch = case["pitch"]
    area = pitch * pitch
    flags_all = []
    checks.check(
        [column["parameter"] for column in reference["columns"]] == ORDER,
        "reference",
        case["name"] + ": reference columns",
    )
    for index, column in enumerate(reference["columns"]):
        label = case["name"] + ":" + ORDER[index]
        scale = pitch if index < 3 else 1.0
        checks.close(column["scale"], scale, "arithmetic", label + ": scale")
        actual = row["candidate"]["cells"][0]["jacobian"][index] * scale
        checks.close(column["candidate_scaled"], actual, "arithmetic", label + ": scaled candidate")
        orders = column["raw_area_orders"]
        for order in ("64", "96"):
            checks.check(
                set(orders[order]) == {"1", "2"}, "reference", label + ": both steps saved"
            )
            for divisor in (1, 2):
                data = orders[order][str(divisor)]
                h = settings["fd_step"] / divisor
                expected = (data["plus_area"] - data["minus_area"]) / (2 * h * area)
                checks.close(
                    data["scaled_derivative"], expected, "arithmetic", label + ": area difference"
                )
        coarse = orders["96"]["1"]["scaled_derivative"]
        fine = orders["96"]["2"]["scaled_derivative"]
        richardson = (4 * fine - coarse) / 3
        propagated = max(
            (
                abs(
                    orders["96"][str(divisor)]["plus_area"]
                    - orders["64"][str(divisor)]["plus_area"]
                )
                + abs(
                    orders["96"][str(divisor)]["minus_area"]
                    - orders["64"][str(divisor)]["minus_area"]
                )
            )
            / (2 * (settings["fd_step"] / divisor) * area)
            for divisor in (1, 2)
        )
        boundary = column["boundary_orders"]
        delta = abs(boundary["64"] - boundary["32"])
        fd_limit = settings["candidate_fd_absolute"] + settings["candidate_fd_relative"] * abs(
            richardson
        )
        boundary_limit = settings["candidate_boundary_absolute"] + settings[
            "candidate_boundary_relative"
        ] * abs(boundary["64"])
        for key, value in (
            ("richardson", richardson),
            ("step_delta", abs(fine - coarse)),
            ("noncancelling_area_order_error", propagated),
            ("boundary_order_delta", delta),
            ("fd_limit", fd_limit),
            ("boundary_limit", boundary_limit),
        ):
            checks.close(column[key], value, "arithmetic", label + ": " + key)
        flags = {
            "area_order": propagated <= settings["area_propagated_order_limit"],
            "step": abs(fine - coarse) <= settings["fd_step_delta_limit"],
            "candidate_fd": abs(actual - richardson) <= fd_limit,
            "boundary_order": delta <= settings["boundary_order_limit"],
            "candidate_boundary": abs(actual - boundary["64"]) <= boundary_limit,
        }
        checks.check(
            column["flags"] == flags and column["passed"] is all(flags.values()),
            "qualification",
            label + ": reference flags",
        )
        flags_all.append(all(flags.values()))
        maxima["candidate_vs_saved_richardson_scaled"] = max(
            maxima["candidate_vs_saved_richardson_scaled"], abs(actual - richardson)
        )
        maxima["candidate_vs_saved_boundary_scaled"] = max(
            maxima["candidate_vs_saved_boundary_scaled"], abs(actual - boundary["64"])
        )
    checks.check(
        reference["passed"] is all(flags_all), "qualification", case["name"] + ": reference summary"
    )


def flat_at(record, row, col):
    return record["cells"][row * record["shape"][1] + col]


def invariant_saved(base, variant, settings, checks, gaps):
    kind = variant["kind"]
    old = base["candidate"]
    new = variant["candidate"]
    h, w = old["shape"]
    cov_deltas = []
    jac_deltas = [[] for _ in ORDER]
    qualified = True
    if kind == "complement":
        gaps.append(
            {
                "case": base["case"]["name"],
                "kind": kind,
                "missing": "independent disk coverage and Cx/Cy/R reference arrays",
                "consequence": "saved maxima for coverage/Cx/Cy/R not independently recomputed",
            }
        )
        for before, after in zip(old["cells"], new["cells"], strict=True):
            for index, sign in ((3, -1), (4, 1)):
                value = after["jacobian"][index] + sign * before["jacobian"][index]
                jac_deltas[index].append(abs(value))
                qualified &= abs(value) <= settings["invariant_absolute"]
        for index in (3, 4):
            checks.close(
                variant["jacobian_max_delta"][index],
                max(jac_deltas[index]),
                "arithmetic",
                base["case"]["name"] + ": complement fraction/angle cancellation",
            )
        checks.check(
            qualified,
            "qualification",
            base["case"]["name"] + ": complement fraction/angle cancellation",
        )
        checks.check(
            variant["coverage_max_delta"] <= settings["invariant_absolute"]
            and all(
                type(value) in (int, float) and math.isfinite(value)
                for value in variant["jacobian_max_delta"]
            ),
            "retained_summary",
            base["case"]["name"] + ": complement saved summary is finite",
        )
        return
    for i in range(h):
        for j in range(w):
            before = flat_at(old, i, j)
            target = before["jacobian"].copy()
            target_cov = before["coverage"]
            if kind == "rotation90":
                after = flat_at(new, j, h - 1 - i)
                target[0], target[1] = -target[1], target[0]
            elif kind == "reflection":
                after = flat_at(new, i, w - 1 - j)
                target[0] *= -1
                target[4] *= -1
            elif kind == "subdivision":
                members = [flat_at(new, 2 * i + di, 2 * j + dj) for di in (0, 1) for dj in (0, 1)]
                after = {
                    "coverage": math.fsum(cell["coverage"] for cell in members) / 4,
                    "jacobian": [
                        math.fsum(cell["jacobian"][index] for cell in members) / 4
                        for index in range(5)
                    ],
                }
            else:
                after = flat_at(new, i, j)
                if kind == "scale2":
                    target[:3] = [value / 2 for value in target[:3]]
            cov_deltas.append(abs(after["coverage"] - target_cov))
            for index, actual in enumerate(after["jacobian"]):
                delta = abs(actual - target[index])
                jac_deltas[index].append(delta)
                qualified &= delta <= settings["invariant_absolute"] + settings[
                    "invariant_relative"
                ] * abs(target[index])
    checks.close(
        variant["coverage_max_delta"],
        max(cov_deltas),
        "arithmetic",
        base["case"]["name"] + ": " + kind + " coverage maximum",
    )
    for index, values in enumerate(jac_deltas):
        checks.close(
            variant["jacobian_max_delta"][index],
            max(values),
            "arithmetic",
            base["case"]["name"] + ": " + kind + ": " + ORDER[index] + " maximum",
        )
    qualified &= max(cov_deltas) <= settings["invariant_absolute"] and all(
        cell["status"] == "resolved" for cell in new["cells"]
    )
    checks.check(
        variant["passed"] is bool(qualified),
        "qualification",
        base["case"]["name"] + ": " + kind + " flags",
    )


def run(report_path, root, recorded_source, checks):
    raw = report_path.read_bytes()
    checks.check(sha(raw) == EXPECTED_SHA, "integrity", "exact first frozen report")
    report = decode(raw)
    native_counts = native(report, checks)
    checks.check(
        report["format"] == "finite-cell-sensitivity-study-v1", "integrity", "report format"
    )
    checks.check(report["source_commit"] == EXPECTED_COMMIT, "source", "frozen source commit")
    checks.check(
        report["source_before"] == report["source_after"] and report["source_unchanged"] is True,
        "source",
        "before/after source closure",
    )
    sources, source_mode = source_bytes(root, recorded_source, report["source_before"], checks)
    for name, expected in report["source_before"].items():
        checks.check(sha(sources[name]) == expected, "source", "recorded bytes: " + name)
    plan_path = "studies/finite-cell-sensitivity-v1.json"
    checks.check(sha(sources[plan_path]) == report["plan_sha256"], "source", "plan byte hash")
    plan = decode(sources[plan_path])
    checks.check(
        plan == report["plan"] and plan["settings"] == report["settings"],
        "source",
        "complete frozen plan and settings retained",
    )
    module = ast.parse(sources["backend/finite_aperture_sensitivity.py"])
    freeze = next(
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "_freeze"
    )
    calls = [node.func for node in ast.walk(freeze) if isinstance(node, ast.Call)]
    checks.check(
        any(isinstance(node, ast.Attribute) and node.attr == "frombuffer" for node in calls)
        and any(isinstance(node, ast.Attribute) and node.attr == "tobytes" for node in calls),
        "static_contract",
        "immutable arrays use a bytes-backed frombuffer",
    )
    record_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "ApertureSensitivity"
    )
    checks.check(
        any(
            isinstance(decorator, ast.Call)
            and any(
                keyword.arg == "frozen"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in decorator.keywords
            )
            for decorator in record_class.decorator_list
        ),
        "static_contract",
        "result dataclass frozen",
    )
    tests = sources["tests/test_finite_aperture_sensitivity.py"].decode()
    checks.check(
        "def test_results_are_immutable_and_binding_includes_requested_geometry" in tests
        and "array.setflags(write=True)" in tests,
        "static_contract",
        "separate runtime immutability control retained as source",
    )
    rows = report["rows"]
    expected_names = (
        [f"{kind}-{index}" for kind in ("arc", "chord", "joint") for index in range(6)]
        + [f"grid-{index}" for index in range(4)]
        + SPECIAL_NAMES
    )
    checks.check(
        [row["case"]["name"] for row in rows] == expected_names,
        "census",
        "all33 authored rows in order",
    )
    families = Counter(row["family"] for row in rows)
    checks.check(
        families == {"regular": 18, "grid": 4, "special": 11}, "census", "family denominators"
    )
    checks.check(
        len({row["case"]["name"] for row in rows}) == 33, "census", "row identities unique"
    )
    records = []
    gaps = []
    status_census = Counter()
    scopes = Counter()
    maxima = Counter()
    invariant_count = 0
    for row in rows:
        case = row["case"]
        name = case["name"]
        checks.check(
            row["status"] == "evaluated", "retention", name + ": evaluated, no cleared row"
        )
        record = row["candidate"]
        record_checks(record, case, checks, name)
        records.append(record)
        if row["family"] == "regular" or name == "multiple-circle-spans":
            reference_checks_saved(row, report["settings"], checks, maxima)
            checks.check(
                row["passed"]
                is (
                    row["independent_reference"]["passed"]
                    and all(cell["status"] == "resolved" for cell in record["cells"])
                ),
                "qualification",
                name + ": accuracy outcome",
            )
            scopes["regular_or_multispan_accuracy_rows"] += 1
        elif row["family"] == "grid":
            whole = row["whole_grid"]
            pitch2 = case["pitch"] ** 2
            area = math.fsum(cell["coverage"] for cell in record["cells"]) * pitch2
            summed = [
                math.fsum(cell["jacobian"][index] for cell in record["cells"]) * pitch2
                for index in range(5)
            ]
            checks.close(whole["area"], area, "arithmetic", name + ": integrated saved coverage")
            flags = []
            for index, value in enumerate(summed):
                checks.close(
                    whole["summed_jacobian"][index],
                    value,
                    "arithmetic",
                    name + ": integrated " + ORDER[index],
                )
                expected = whole["expected_jacobian"][index]
                flags.append(
                    abs(value - expected)
                    <= report["settings"]["invariant_absolute"]
                    + report["settings"]["invariant_relative"] * abs(expected)
                )
            area_passed = abs(area - whole["expected_area"]) <= report["settings"][
                "invariant_absolute"
            ] + report["settings"]["invariant_relative"] * abs(whole["expected_area"])
            checks.check(
                whole["flags"] == flags and whole["area_passed"] is area_passed,
                "qualification",
                name + ": whole-grid flags against saved expectations",
            )
            variants = row["invariants"]["rows"]
            expected_kinds = KINDS + (["large_translation"] if name == "grid-2" else [])
            checks.check(
                [item["kind"] for item in variants] == expected_kinds,
                "census",
                name + ": every frame/partition variant retained",
            )
            for variant in variants:
                record_checks(
                    variant["candidate"], variant["case"], checks, name + ":" + variant["kind"]
                )
                records.append(variant["candidate"])
                invariant_saved(row, variant, report["settings"], checks, gaps)
                invariant_count += 1
            checks.check(
                row["invariants"]["passed"] is all(variant["passed"] for variant in variants),
                "qualification",
                name + ": invariant summary",
            )
            checks.check(
                row["passed"] is bool(all(flags) and area_passed and row["invariants"]["passed"]),
                "qualification",
                name + ": grid summary",
            )
            scopes["whole_grid_identity_rows"] += 1
        else:
            statuses = [cell["status"] for cell in record["cells"]]
            expected = case["expected"]
            if expected in ("nondifferentiable", "parameter_endpoint", "work_limit"):
                checks.check(
                    all(status == expected for status in statuses),
                    "unknown",
                    name + ": expected withholding reason",
                )
                checks.check(
                    "independent_reference" not in row and "independent_boundary" not in row,
                    "unknown",
                    name + ": withholding not counted as accuracy",
                )
                scopes["safety_unknown_rows_not_accuracy"] += 1
            elif expected == "resolved_zero_or_unresolved":
                checks.check(
                    all(
                        cell["jacobian"] is None or max(map(abs, cell["jacobian"])) <= 2e-9
                        for cell in record["cells"]
                    ),
                    "qualification",
                    name + ": contact zero or withheld",
                )
                scopes["zero_contact_contract_rows"] += 1
            elif expected == "resolved_or_unresolved":
                independent = row["independent_boundary"]
                resolved = statuses == ["resolved"]
                passed = []
                for index, column in enumerate(independent["columns"]):
                    scale = case["pitch"] if index < 3 else 1
                    actual = record["cells"][0]["jacobian"][index] * scale if resolved else None
                    if resolved:
                        checks.close(
                            column["candidate_scaled"],
                            actual,
                            "arithmetic",
                            name + ": saved special candidate",
                        )
                    limit = report["settings"]["candidate_boundary_absolute"] + report["settings"][
                        "candidate_boundary_relative"
                    ] * abs(column["boundary_high"])
                    checks.close(column["limit"], limit, "arithmetic", name + ": special limit")
                    qualified = (
                        resolved
                        and abs(column["boundary_high"] - column["boundary_low"])
                        <= report["settings"]["boundary_order_limit"]
                        and abs(actual - column["boundary_high"]) <= limit
                    )
                    checks.check(
                        column["passed"] is qualified,
                        "qualification",
                        name + ": special column flag",
                    )
                    passed.append(qualified)
                checks.check(
                    independent["accuracy_qualified"] is bool(resolved and all(passed))
                    and independent["unknown_retained"] is (not resolved),
                    "qualification",
                    name + ": unknown versus accuracy qualification",
                )
                scopes[
                    "resolved_special_boundary_accuracy_rows"
                    if resolved
                    else "special_unknown_not_accuracy"
                ] += 1
            checks.check(
                row["passed"] is True, "qualification", name + ": retained contract outcome"
            )
    for record in records:
        status_census.update(cell["status"] for cell in record["cells"])
    checks.check(
        invariant_count == 25 and len(records) == 58, "census", "25variants/58returned records"
    )
    checks.check(
        report["api_calls"] == {"attempted": 58, "returned": 58},
        "census",
        "declared API call retention",
    )
    checks.check(
        dict(status_census)
        == {key: value for key, value in report["candidate_status_census"].items() if value},
        "census",
        "cell status totals",
    )
    checks.check(
        status_census
        == {"resolved": 7823, "nondifferentiable": 2, "parameter_endpoint": 2, "work_limit": 4},
        "census",
        "known versus withheld cell denominators",
    )
    work = {
        key: sum(record[key] for record in records) for key in ("required_work", "performed_work")
    }
    checks.check(
        report["candidate_record_work"] == work == {"required_work": 7831, "performed_work": 7827},
        "work",
        "cumulative attempted/refused cell work",
    )
    checks.check(
        report["summary"]
        == {
            family: {
                "total": count,
                "passed": sum(row["family"] == family and row["passed"] for row in rows),
            }
            for family, count in families.items()
        },
        "census",
        "family summaries",
    )
    checks.check(
        report["errors"] == [] and report["passed"] is all(row["passed"] for row in rows),
        "qualification",
        "protocol conclusion",
    )
    checks.check(
        not [name for name in sys.modules if name.partition(".")[0] in FORBIDDEN],
        "audit_scope",
        "no scientific modules loaded",
    )
    checks.check(not BLOCKED, "audit_scope", "no prohibited import attempted")
    return {
        "input": {
            "report_sha256": sha(raw),
            "bytes": len(raw),
            "source_commit": report["source_commit"],
            "source_pin_count": len(sources),
            "plan_sha256": report["plan_sha256"],
        },
        "source_verification": source_mode,
        "native_json_types": dict(native_counts),
        "population": {
            "rows": len(rows),
            "families": dict(families),
            "invariants": invariant_count,
            "api_calls": report["api_calls"],
            "status_census": dict(status_census),
            "work": work,
            "qualification_scopes": dict(scopes),
        },
        "saved_comparison_maxima": dict(maxima),
        "missing_saved_reference_arrays": gaps,
        "all_reference_maxima_independently_recomputed": False,
        "limitations": [
            "Four complement rows omit independent disk-reference arrays: coverage/Cx/Cy/R maxima are retained claims, not independently recomputed metrics.",
            "Stored geometric reference values are not re-evaluated; only saved-array arithmetic and flags are checked.",
            "JSON does not prove live NumPy immutability. Frozen bytes-backed implementation and separate immutability test source are checked statically; no runtime test is rerun.",
            "Arithmetic estimates and order agreement are not certified derivative bounds, geometry recovery, camera qualification or interactive latency evidence.",
            "The scope counts include intentional unknown safety controls, not33 accuracy successes.",
        ],
        "import_guard": {
            "enabled": True,
            "forbidden_import_attempts": BLOCKED,
            "scientific_modules_loaded": [],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--recorded-source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("output must be fresh, with an existing parent")
    checks = Checks()
    result = {
        "format": "finite-cell-sensitivity-saved-artifact-audit-v1",
        "audit_sha256": sha(Path(__file__).read_bytes()),
        "scope": "stdlib saved data only; no model/reference/generator/package imports or evaluations",
    }
    try:
        result.update(run(args.report, args.root, args.recorded_source, checks))
    except Exception as error:  # noqa: BLE001 -- retain an audit failure receipt.
        checks.check(False, "audit_execution", f"{type(error).__name__}: {error}")
    result.update(
        passed=not checks.failures,
        checks=sum(checks.counts.values()),
        checks_by_category=dict(checks.counts),
        failures=checks.failures,
    )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, allow_nan=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": result["checks"],
                "failures": len(checks.failures),
                "output": str(args.output),
            },
            allow_nan=False,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
