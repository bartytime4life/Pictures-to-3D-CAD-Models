#!/usr/bin/env python3
"""Audit saved finite-residual study arrays with the standard library only.

Recompute provenance, residuals, derivative/error arithmetic, guarded subspaces
and training-only steps without importing a model, renderer, array package or
optimizer. Independent Jacobi SVD and pivoted two-pass QR check small saved
matrices; near-cutoff QR comparisons remain withheld. An integrity pass preserves
the study's failed controls and unknowns, and is not optical qualification.
``--self-test`` uses invented algebra/parser controls. ``--report`` requires
explicit hashes of the saved report and frozen diagnostic runner.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "studies/finite-residual-information-v1.json"
ARCHIVE = ROOT / "studies/results/finite-photo-intensity-v2.json"
EPS = sys.float_info.epsilon
EXPECTED_PLAN_SHA256 = "837c626d7add9ebc6927d60245b85c1ad9bd361adaf8205e4bf62a4efd322532"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parsed_sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def strict_loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result

    def floating(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("nonfinite JSON number")
        return result

    def reject(value):
        raise ValueError("invalid JSON constant: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_float=floating, parse_constant=reject)


def read(path):
    if Path(path).stat().st_size > 64 * 1024 * 1024:
        raise ValueError("saved JSON exceeds the auditor's 64 MiB cap")
    return strict_loads(Path(path).read_bytes())


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("array values must be real JSON numbers, not booleans")  # noqa: TRY004 - saved-array refusal contract
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite array element")
    return result


def vector(value, length=None):
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected a vector")  # noqa: TRY004 - saved-array refusal contract
    result = [number(item) for item in value]
    if length is not None and len(result) != length:
        raise ValueError("vector length differs")
    return result


def matrix(value, rows=None, cols=None):
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected a row-major matrix")  # noqa: TRY004 - saved-array refusal contract
    result = [vector(row, cols) for row in value]
    if rows is not None and len(result) != rows:
        raise ValueError("matrix row count differs")
    if result and len({len(row) for row in result}) != 1:
        raise ValueError("ragged matrix")
    return result


def dot(a, b):
    if len(a) != len(b):
        raise ValueError("dot-product dimensions differ")
    return math.fsum(x * y for x, y in zip(a, b))


def norm(a):
    # hypot is scaled, so computing a vector norm does not first square a
    # representable finite entry into infinity.
    return math.hypot(*a)


def columns(a, column_count=None):
    a = matrix(a)
    if not a:
        return [[] for _ in range(column_count or 0)]
    return [list(values) for values in zip(*a)]


def join_matrices(*matrices):
    if not matrices:
        return []
    if len({len(a) for a in matrices}) != 1:
        raise ValueError("matrix row counts differ")
    return [[value for a in matrices for value in a[i]] for i in range(len(matrices[0]))]


def jacobi_svd(a):
    """Independent one-sided Jacobi SVD of the small saved matrices.

    No normal-equation eigensolver is used. QR remains a separate rank check
    when the singular spectrum is sufficiently separated from the cutoff.
    """
    a = matrix(a)
    cols = columns(a)
    count = len(cols)
    right = [[float(i == j) for i in range(count)] for j in range(count)]
    scale = math.fsum(dot(c, c) for c in cols)
    sweeps = 0
    for sweeps in range(1, 101):
        changed = False
        for i in range(count):
            for j in range(i + 1, count):
                alpha, beta, cross = (
                    dot(cols[i], cols[i]),
                    dot(cols[j], cols[j]),
                    dot(cols[i], cols[j]),
                )
                guard = 16 * EPS * (math.sqrt(alpha) * math.sqrt(beta) + EPS * scale)
                if abs(cross) <= guard:
                    continue
                tau = (beta - alpha) / (2 * cross)
                tangent = math.copysign(1.0, tau) / (abs(tau) + math.hypot(1, tau))
                cosine = 1 / math.hypot(1, tangent)
                sine = tangent * cosine
                x, y = cols[i], cols[j]
                cols[i] = [cosine * u - sine * v for u, v in zip(x, y)]
                cols[j] = [sine * u + cosine * v for u, v in zip(x, y)]
                x, y = right[i], right[j]
                right[i] = [cosine * u - sine * v for u, v in zip(x, y)]
                right[j] = [sine * u + cosine * v for u, v in zip(x, y)]
                changed = True
        if not changed:
            break
    else:
        raise ArithmeticError("independent Jacobi SVD did not settle in 100 sweeps")
    order = sorted(range(count), key=lambda i: (-norm(cols[i]), i))
    singular = [norm(cols[i]) for i in order]
    return {
        "singular": singular,
        "u": [[x / s for x in cols[i]] if s else [0.0] * len(a) for i, s in zip(order, singular)],
        "v": [right[i] for i in order],
        "sweeps": sweeps,
    }


def spectral_norm(a):
    return next(iter(jacobi_svd(a)["singular"]), 0.0)


def maximum_delta(a, b):
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            raise ValueError("array length differs")
        return max((maximum_delta(x, y) for x, y in zip(a, b)), default=0.0)
    return abs(a - b)


def near(a, b, *, absolute=1e-9, relative=1e-9):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, abs_tol=absolute, rel_tol=relative)


class Audit:
    def __init__(self):
        self.checks = []
        self.notes = []

    def check(self, name, passed, **details):
        self.checks.append({"name": name, "passed": bool(passed), **details})

    def scalar(self, name, expected, actual, **tolerance):
        self.check(name, near(expected, actual, **tolerance), expected=expected, actual=actual)

    def array(self, name, expected, actual, *, absolute=1e-8, relative=1e-9):
        delta = maximum_delta(expected, actual)

        def largest(x):
            return (
                max((largest(y) for y in x), default=0.0)
                if isinstance(x, (tuple, list))
                else abs(x)
            )

        self.check(name, delta <= absolute + relative * largest(expected), maximum_delta=delta)

    def section(self, name, call):
        try:
            return call()
        except Exception as exc:  # noqa: BLE001 - retain an explicit failed audit section
            self.check(
                name + "/audit_exception",
                False,
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            return None


def subtract(a, b):
    if len(a) != len(b):
        raise ValueError("vector dimensions differ")
    return [x - y for x, y in zip(a, b)]


def add(a, b):
    if len(a) != len(b):
        raise ValueError("vector dimensions differ")
    return [x + y for x, y in zip(a, b)]


def matvec(a, x):
    return [dot(row, x) for row in a]


def projection(q, value):
    """Q contains column vectors; dot products use compensated summation."""
    if not q:
        return [0.0] * len(value)
    coefficients = [dot(column, value) for column in q]
    return [
        math.fsum(c * column[i] for c, column in zip(coefficients, q)) for i in range(len(value))
    ]


def residualize(q, value):
    # Always two passes, including when a vector is already nearly in span(Q).
    result = list(value)
    for _ in range(2):
        result = subtract(result, projection(q, result))
    return result


def pivoted_qr(a, cutoff):
    """Small independent two-pass pivoted QR, without SVD/normal equations.

    This rank convention is a cross-check for well-separated spectra, not a
    claim that a QR pivot is a singular value. Recompute every candidate from
    its original column; do not divide by projected local roundoff norms.
    """
    a = matrix(a)
    cutoff = number(cutoff)
    if cutoff < 0:
        raise ValueError("cutoff must be nonnegative")
    original = columns(a)
    remaining, q, pivots, selected_norms = list(range(len(original))), [], [], []
    while remaining and len(q) < len(a):
        candidates = [(i, residualize(q, original[i])) for i in remaining]
        index, value = max(candidates, key=lambda item: (norm(item[1]), -item[0]))
        length = norm(value)
        if length <= cutoff:
            break
        q.append([item / length for item in value])
        pivots.append(index)
        selected_norms.append(length)
        remaining.remove(index)
    orthogonality = max(
        (abs(dot(x, y) - float(i == j)) for i, x in enumerate(q) for j, y in enumerate(q)),
        default=0.0,
    )
    return {
        "q": q,
        "pivots": pivots,
        "rank": len(q),
        "selected_residual_norms": selected_norms,
        "remaining_residual_norms": {str(i): norm(residualize(q, original[i])) for i in remaining},
        "maximum_orthogonality_error": orthogonality,
    }


def qr_rank_interval(a, cutoff):
    return {
        "lower": pivoted_qr(a, 2 * cutoff)["rank"],
        "nominal": pivoted_qr(a, cutoff)["rank"],
        "upper": pivoted_qr(a, cutoff / 2)["rank"],
        "convention": "QR pivot interval; compare SVD rank only if independently well separated",
    }


def rank_qualification(
    raw_interval, raw_retained, ceiling, columns_count, *, projector=True, fd=True, nuisance=True
):
    raw_resolved = raw_interval[0] == raw_interval[1]
    ceiling_consistent = raw_retained <= ceiling and raw_interval[1] <= ceiling
    resolved = bool(projector and fd and nuisance and raw_resolved and ceiling_consistent)
    retained = min(ceiling, raw_retained)
    return {
        "raw_rank_interval": list(raw_interval),
        "raw_retained_rank": raw_retained,
        "raw_rank_resolved": raw_resolved,
        "raw_full_column_rank_resolved": raw_resolved and raw_retained == columns_count,
        "ceiling_consistent": ceiling_consistent,
        "basis_columns_used": retained,
        "rank_interval": [min(ceiling, x) for x in raw_interval],
        "retained_rank": retained,
        "rank_resolved": resolved,
        "full_column_rank_resolved": resolved and retained == columns_count,
    }


def quotient(a_nuisance, a_covariance, residual, cutoff_nuisance, cutoff_covariance):
    """Independent covariance-space residual projection on training rows."""
    nuisance = pivoted_qr(a_nuisance, cutoff_nuisance)
    qn = nuisance["q"]
    rc = residualize(qn, vector(residual, len(a_nuisance)))
    cov_cols = [residualize(qn, column) for column in columns(a_covariance)]
    projected_cov = [list(row) for row in zip(*cov_cols)]
    cov = pivoted_qr(projected_cov, cutoff_covariance)
    remaining_dimension = len(residual) - nuisance["rank"]
    if cov["rank"] > remaining_dimension:
        raise ArithmeticError("rank exceeds residual dimension")
    fitted_cov = projection(cov["q"], rc)
    final = residualize(cov["q"], rc)
    return {
        "nuisance_rank": nuisance["rank"],
        "covariance_rank_gain": cov["rank"],
        "remaining_dimension": remaining_dimension,
        "nuisance_residual": rc,
        "covariance_explained_residual": fitted_cov,
        "final_residual": final,
        "nuisance_residual_energy": dot(rc, rc),
        "covariance_explained_energy": dot(fitted_cov, fitted_cov),
        "final_residual_energy": dot(final, final),
        "maximum_nuisance_orthogonality": max((abs(dot(x, rc)) for x in qn), default=0.0),
        "qr": {"nuisance": nuisance, "covariance": cov},
    }


def least_squares_full_rank(a, residual, cutoff):
    """Unique full-rank QR solution; rank-deficient SVD solutions stay unknown.

    A pivoted QR basic solution is not the SVD minimum-norm solution when
    columns are dependent. Never compare those coefficients as if equivalent.
    """
    a = matrix(a)
    cols = columns(a)
    qr = pivoted_qr(a, cutoff)
    if qr["rank"] != len(cols):
        return {"status": "rank_deficient_unknown", "rank": qr["rank"], "coefficients": None}
    q, pivots = qr["q"], qr["pivots"]
    right = [dot(v, residual) for v in q]
    coefficients_pivot = [0.0] * len(cols)
    for i in reversed(range(len(cols))):
        tail = math.fsum(
            dot(q[i], cols[pivots[j]]) * coefficients_pivot[j] for j in range(i + 1, len(cols))
        )
        coefficients_pivot[i] = (right[i] - tail) / dot(q[i], cols[pivots[i]])
    coefficients = [0.0] * len(cols)
    for index, pivot in enumerate(pivots):
        coefficients[pivot] = coefficients_pivot[index]
    remaining = subtract(residual, matvec(a, coefficients))
    return {
        "status": "unique_full_rank",
        "rank": qr["rank"],
        "coefficients": coefficients,
        "normal_equation_residual": [dot(column, remaining) for column in cols],
    }


def training_only_solution(design, residual, training_indices, cutoff):
    if len(set(training_indices)) != len(training_indices):
        raise ValueError("duplicate training row")
    return least_squares_full_rank(
        [design[i] for i in training_indices], [residual[i] for i in training_indices], cutoff
    )


def active_brightness(probabilities, levels, lower=0.0, upper=255.0):
    guard = 64 * EPS * 255
    free = [i for i, level in enumerate(levels) if lower + guard < level < upper - guard]
    return {
        "free": free,
        "active_faces": [
            None if i in free else ("lower" if level <= lower + guard else "upper")
            for i, level in enumerate(levels)
        ],
        "matrix": [[(1 - p) if index == 0 else p for index in free] for p in probabilities],
    }


def residual_metrics(values):
    values = vector(values)
    return {
        "maximum_absolute": max(map(abs, values), default=0.0),
        "rms": norm(values) / math.sqrt(len(values)) if values else None,
        "sum_squared": dot(values, values),
        "count": len(values),
    }


def strata_metrics(residual):
    residual = vector(residual, 56)
    return {
        name: residual_metrics(residual[start:end])
        for name, start, end in (
            ("training_edge", 0, 24),
            ("training_material", 24, 32),
            ("training_background", 32, 40),
            ("heldout_edge", 40, 48),
            ("heldout_material", 48, 52),
            ("heldout_background", 52, 56),
        )
    }


def central_difference(plus, minus, step):
    step = number(step)
    if step <= 0:
        raise ValueError("positive finite step required")
    return [(a - b) / (2 * step) for a, b in zip(vector(plus), vector(minus, len(plus)))]


def bound_alpha(values, steps, bounds, fraction=0.9):
    candidates = [1.0]
    for value, step, (lower, upper) in zip(values, steps, bounds):
        if not lower <= value <= upper:
            raise ValueError("anchor outside declared bounds")
        if step > 0:
            candidates.append(fraction * (upper - value) / step)
        elif step < 0:
            candidates.append(fraction * (lower - value) / step)
    return min(candidates)


def archive_binding(plan):
    """Only saved identity/input inspection; no field/array library imports."""
    archive = read(ARCHIVE)
    expected = plan["population"]
    rows = archive["rows"]
    if len(rows) != len(expected) or len(rows) != 12:
        raise ValueError("exact original12 population required")
    result = []
    for row, identity in zip(rows, expected):
        if (row["name"], row["lane"]) != (identity["name"], identity["lane"]):
            raise ValueError("population order/identity differs")
        eligible = bool(row.get("fit_attempted"))
        if eligible != identity["expected_eligible"]:
            raise ValueError("eligibility differs from prospective population")
        result.append(
            {
                "name": row["name"],
                "lane": row["lane"],
                "eligible": eligible,
                "archived_parsed_row_sha256": parsed_sha(row),
                "archived_status": row["status"],
                "original_targets_passed": row["targets_passed"],
                "original_completion_passed": row["completion_passed"],
            }
        )
    return result


def expected_data(row):
    observed, best = row["observed"], row["fit"]["best"]
    intervals = [
        *observed["bounds"]["centre_bounds"],
        observed["bounds"]["radius_bounds"],
        observed["bounds"]["chord_fraction_bounds"],
    ]
    return {
        "pixels": observed["training_pixels"] + observed["heldout_pixels"],
        "values": observed["training_values"] + observed["heldout_values"],
        "levels": best["levels"],
        "bounds": intervals,
        "domain_widths": [b - a for a, b in intervals],
        "parameters": {
            "centre": best["centre"],
            "radius": best["radius"],
            "fraction": best["chord_fraction"],
            "normal": observed["normal"],
            "covariance": row["covariance_record"]["canonical"],
            "homography": observed["homography"],
            "sensor_shape": observed["field_shape"],
        },
    }


def source_audit(audit, report, plan, runner_sha):
    plan_name = str(PLAN.relative_to(ROOT))
    runner_name = "studies/verification/finite-residual-information-v1.py"
    audit.check(
        "source/plan_pin",
        sha(PLAN) == EXPECTED_PLAN_SHA256 == report["plan_sha256"] and report["plan"] == plan,
    )
    audit.check(
        "source/runner_pin", sha(ROOT / runner_name) == runner_sha == report["runner_sha256"]
    )
    before, after = report["source_before"], report["source_after"]
    audit.check("source/interval", before == after and report["source_unchanged"] is True)
    required = (
        set(plan["source_sha256"]) | set(plan["input_sha256"]) | {plan_name, runner_name, "uv.lock"}
    )
    audit.check("source/complete_closure", set(before) == required)
    for name, record in before.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe manifest path")
        audit.check(
            "source/current/" + name,
            record == {"sha256": sha(ROOT / path), "bytes": (ROOT / path).stat().st_size},
        )
    for name, expected in {**plan["source_sha256"], **plan["input_sha256"]}.items():
        audit.check("source/frozen/" + name, before[name]["sha256"] == expected)


def npz_crop(row):
    """Decode only numeric C-order g.npy with stdlib; never load pickle."""
    path = ROOT / "studies/fixtures/finite-moment-photo-v1" / (row["name"] + "-measurement.npz")
    with zipfile.ZipFile(path) as archive:
        if archive.getinfo("g.npy").file_size > 8 * 1024 * 1024:
            raise ValueError("fixture g exceeds auditor's 8 MiB cap")
        raw = archive.read("g.npy")
    if raw[:6] != b"\x93NUMPY":
        raise ValueError("invalid NPY magic")
    major = raw[6]
    size = 2 if major == 1 else 4 if major in (2, 3) else None
    if size is None:
        raise ValueError("unsupported NPY version")
    header_size = int.from_bytes(raw[8 : 8 + size], "little")
    if header_size > 65536:
        raise ValueError("NPY header too large")
    offset = 8 + size + header_size
    header = ast.literal_eval(raw[8 + size : offset].decode("latin1"))
    dtype = header["descr"]
    if dtype not in ("<f4", "<f8") or header["fortran_order"] is not False:
        raise ValueError("only nonobject C-order little-endian float fixtures supported")
    height, width = header["shape"]
    itemsize = 4 if dtype == "<f4" else 8
    data = raw[offset:]
    if len(data) != height * width * itemsize:
        raise ValueError("NPY length differs from numeric shape")
    observed = row["observed"]
    x0, y0, x1, y1 = observed["crop_bounds"]
    if not 0 <= x0 < x1 <= width or not 0 <= y0 < y1 <= height:
        raise ValueError("crop outside fixture")
    crop = b"".join(
        data[(y * width + x0) * itemsize : (y * width + x1) * itemsize] for y in range(y0, y1)
    )
    shape = [y1 - y0, x1 - x0]
    pixels = observed["training_pixels"] + observed["heldout_pixels"]
    if len(set(map(tuple, pixels))) != 56:
        raise ValueError("sample coordinates overlap")
    values = []
    for x, y in pixels:
        if (
            type(x) is not int
            or type(y) is not int
            or not 0 <= x < shape[1]
            or not 0 <= y < shape[0]
        ):
            raise ValueError("sample is not an inbounds integer crop index")
        values.append(
            struct.unpack_from(
                "<f" if itemsize == 4 else "<d", crop, (y * shape[1] + x) * itemsize
            )[0]
        )
    return {
        "fixture": str(path.relative_to(ROOT)),
        "crop_dtype": dtype,
        "crop_shape": shape,
        "crop_raw_sha256": hashlib.sha256(crop).hexdigest(),
        "values": values,
    }


def summary_audit(audit, name, residual, report):
    groups = {"all": residual, "training": residual[:40], "heldout": residual[40:]}
    groups.update(
        {
            key: residual[start:end]
            for key, start, end in (
                ("training_edge", 0, 24),
                ("training_material", 24, 32),
                ("training_background", 32, 40),
                ("heldout_edge", 40, 48),
                ("heldout_material", 48, 52),
                ("heldout_background", 52, 56),
            )
        }
    )
    audit.check(name + "/groups", set(report) == set(groups))
    for key, values in groups.items():
        expected = residual_metrics(values)
        audit.check(name + "/" + key + "/count", report[key]["count"] == len(values))
        audit.scalar(
            name + "/" + key + "/max", expected["maximum_absolute"], report[key]["max_abs"]
        )
        audit.scalar(name + "/" + key + "/rms", expected["rms"], report[key]["rms"])


def mean_side_audit(audit, name, side, levels, length):
    probability = vector(side["probabilities"], length)
    errors = vector(side["forward"]["estimated_errors"], length)
    contrast = levels[1] - levels[0]
    means = [levels[0] + contrast * p for p in probability]
    audit.array(name + "/probability_copy", probability, side["forward"]["probabilities"])
    audit.array(name + "/mean", means, side["mean"])
    audit.array(name + "/error", [abs(contrast) * x for x in errors], side["level_errors"])
    audit.check(
        name + "/resolved",
        side["forward"]["statuses"] == ["resolved"] * length and all(x >= 0 for x in errors),
    )
    return means


def fd_audit(audit, name, record, levels, plan, length=56):
    entries = record["entries"]
    audit.check(
        name + "/steps", [e["h"] for e in entries] == plan["finite_differences"]["central_steps"]
    )
    derivatives, propagated = [], []
    unresolved = False
    for i, entry in enumerate(entries):
        prefix = name + "/h" + str(i)
        if any("error" in entry[side] for side in ("plus", "minus")):
            audit.check(
                prefix + "/unknown",
                entry["derivative"] is None and entry["propagated_error"] is None,
            )
            unresolved = True
            continue
        plus = mean_side_audit(audit, prefix + "/plus", entry["plus"], levels, length)
        minus = mean_side_audit(audit, prefix + "/minus", entry["minus"], levels, length)
        derivative = central_difference(plus, minus, entry["h"])
        eta = [
            (a + b) / (2 * entry["h"])
            for a, b in zip(entry["plus"]["level_errors"], entry["minus"]["level_errors"])
        ]
        audit.array(prefix + "/central", derivative, entry["derivative"])
        audit.array(prefix + "/propagated", eta, entry["propagated_error"])
        derivatives.append(derivative)
        propagated.append(eta)
    if unresolved:
        arithmetic_types = {
            "ArithmeticError",
            "FloatingPointError",
            "OverflowError",
            "ZeroDivisionError",
        }
        failed_sides = [
            entry[side] for entry in entries for side in ("plus", "minus") if "error" in entry[side]
        ]
        protocol = any(side["error"]["type"] not in arithmetic_types for side in failed_sides)
        audit.check(
            name + "/status",
            record["stable"] is False
            and record["protocol_failure"] is protocol
            and record["status"] == ("protocol_failure" if protocol else "numerically_unresolved"),
        )
        audit.check(
            name + "/side_classification",
            all(
                side["protocol_failure"] is (side["error"]["type"] not in arithmetic_types)
                for side in failed_sides
            ),
        )
        return None
    discrepancy = [abs(a - b) for a, b in zip(*derivatives)]
    combined = [d + a + b for d, a, b in zip(discrepancy, *propagated)]
    settings = plan["finite_differences"]
    allowance = [
        settings["absolute_level_derivative_discrepancy"]
        + settings["relative_level_derivative_discrepancy"] * abs(x)
        for x in derivatives[-1]
    ]
    audit.array(name + "/discrepancy", discrepancy, record["h_half_h_discrepancy"])
    audit.array(name + "/combined_error", combined, record["combined_estimated_error"])
    audit.array(name + "/allowance", allowance, record["stability_allowance"])
    stable = all(a <= b for a, b in zip(combined, allowance))
    audit.check(
        name + "/stable", record["stable"] is stable and record["estimated_not_certified"] is True
    )
    return {"column": derivatives[-1], "error": combined, "stable": stable}


def decomposition_audit(
    audit, name, a, errors, report, plan, *, reference=None, cutoff=None, ceiling=None
):
    a, errors = matrix(a), matrix(errors)
    reference = (a, errors) if reference is None else reference
    ref_norm, err_norm = spectral_norm(reference[0]), spectral_norm(reference[1])
    policy = plan["rank_policy"]
    roundoff = (
        policy["roundoff_multiplier"]
        * EPS
        * max(1, len(reference[0]), len(reference[0][0]))
        * ref_norm
    )
    expected_cutoff = (
        max(roundoff, policy["derivative_discrepancy_multiplier"] * err_norm)
        if cutoff is None
        else cutoff
    )
    svd = jacobi_svd(a)
    singular = svd["singular"]
    rank = sum(s > expected_cutoff for s in singular)
    interval = [
        sum(s > 2 * expected_cutoff for s in singular),
        sum(s > expected_cutoff / 2 for s in singular),
    ]
    raw_rank, raw_interval = rank, list(interval)
    if ceiling is not None:
        rank = min(ceiling, rank)
        interval = [min(ceiling, r) for r in interval]
    audit.check(name + "/shape", report["shape"] == [len(a), len(a[0])])
    audit.array(
        name + "/spectrum",
        singular[: min(len(a), len(a[0]))],
        report["singular_values"],
        absolute=1e-9,
    )
    for key, expected in (
        ("unprojected_reference_norm", ref_norm),
        ("unprojected_error_norm", err_norm),
        ("roundoff_cutoff", roundoff),
        ("cutoff", expected_cutoff),
    ):
        audit.scalar(name + "/" + key, expected, report[key], absolute=1e-12, relative=1e-8)
    audit.array(name + "/column_norms", [norm(c) for c in columns(a)], report["column_norms"])
    audit.check(
        name + "/rank", report["retained_rank"] == rank and report["rank_interval"] == interval
    )
    # Compare QR only when all retained/dropped singular values are well apart
    # from the selected guard. No rank equivalence is asserted near a cutoff.
    separation = max(4, 4 * math.sqrt(max(1, len(a[0]))))
    well_separated = all(
        s > separation * expected_cutoff if i < rank else s < expected_cutoff / separation
        for i, s in enumerate(singular)
    )
    if well_separated:
        audit.check(name + "/independent_qr_rank", pivoted_qr(a, expected_cutoff)["rank"] == rank)
    else:
        audit.notes.append(
            {
                "name": name,
                "note": "QR rank comparison withheld near the estimated cutoff; Jacobi spectrum retained.",
            }
        )
    return {
        "basis": [u for u, s in zip(svd["u"], singular) if s > expected_cutoff],
        "rank": rank,
        "interval": interval,
        "cutoff": expected_cutoff,
        "svd": svd,
        "raw_rank": raw_rank,
        "raw_interval": raw_interval,
        "full_resolved": interval[0] == interval[1] == len(a[0]),
    }


def block_arrays(blocks, names, count=56):
    return (
        join_matrices(*(matrix(blocks[n]["values"], 56)[:count] for n in names)),
        join_matrices(*(matrix(blocks[n]["errors"], 56)[:count] for n in names)),
        [label for n in names for label in blocks[n]["labels"]],
    )


def comparison_audit(
    audit,
    name,
    nuisance,
    nuisance_errors,
    covariance,
    covariance_errors,
    residual,
    report,
    plan,
    fd_qualified=True,
):
    joined, joined_errors = (
        join_matrices(nuisance, covariance),
        join_matrices(nuisance_errors, covariance_errors),
    )
    augmented = decomposition_audit(
        audit, name + "/augmented", joined, joined_errors, report["augmented"], plan
    )
    base = decomposition_audit(
        audit,
        name + "/nuisance",
        nuisance,
        nuisance_errors,
        report["nuisance"],
        plan,
        reference=(joined, joined_errors),
    )
    projected = [residualize(base["basis"], column) for column in columns(covariance)]
    projected = [list(row) for row in zip(*projected)]
    audit.array(
        name + "/projected_covariance", projected, report["projected_covariance"], absolute=2e-7
    )
    policy = plan["rank_policy"]
    factor = policy["roundoff_multiplier"] * EPS * max(1, len(joined), len(joined[0]))
    t_norm, s_norm = spectral_norm(nuisance), spectral_norm(covariance)
    t_arithmetic, s_arithmetic = factor * t_norm, factor * s_norm
    eta_t = spectral_norm(nuisance_errors) + t_arithmetic
    eta_s = spectral_norm(covariance_errors) + s_arithmetic
    minimum = base["svd"]["singular"][-1] if base["full_resolved"] and nuisance[0] else None
    gap_known = not nuisance[0] or minimum is not None and minimum > eta_t
    eta_p = (
        0.0 if not nuisance[0] else min(1.0, 2 * eta_t / (minimum - eta_t)) if gap_known else None
    )
    projector_known = bool(gap_known and eta_p < 1)
    projection_arithmetic = factor * (s_norm + eta_s)
    eta_c = eta_s + eta_p * (s_norm + eta_s) + projection_arithmetic if projector_known else None
    cutoff = (
        max(augmented["cutoff"], policy["derivative_discrepancy_multiplier"] * eta_c)
        if projector_known
        else augmented["cutoff"]
    )
    ceiling = max(0, len(residual) - base["rank"])
    unique = decomposition_audit(
        audit,
        name + "/unique",
        projected,
        [[0.0] * 3 for _ in projected],
        report["projected_covariance_spectrum"],
        plan,
        reference=(joined, joined_errors),
        cutoff=cutoff,
        ceiling=ceiling,
    )
    audit.check(
        name + "/projector_qualified", report["projector_error_qualified"] is projector_known
    )
    for key, expected in (
        ("projector_error_estimate", eta_p),
        ("nuisance_error_estimate", eta_t),
        ("nuisance_SVD_arithmetic_estimate", t_arithmetic),
        ("covariance_unprojected_error_estimate", eta_s),
        ("covariance_SVD_arithmetic_estimate", s_arithmetic),
        ("projection_arithmetic_estimate", projection_arithmetic),
        ("nuisance_smallest_singular_value", minimum),
        ("covariance_error_estimate", eta_c),
    ):
        audit.scalar(name + "/" + key, expected, report[key], absolute=1e-10, relative=2e-7)
    r_base = subtract(residual, projection(base["basis"], residual))
    r_all = subtract(residual, projection(augmented["basis"], residual))
    audit.array(
        name + "/nuisance_residual", r_base, report["nuisance_projected_residual"], absolute=1e-6
    )
    audit.array(
        name + "/augmented_residual", r_all, report["augmented_projected_residual"], absolute=1e-6
    )
    for key, value in (
        ("nuisance_residual_energy", dot(r_base, r_base)),
        ("augmented_residual_energy", dot(r_all, r_all)),
        (
            "raw_separately_truncated_residual_energy_difference",
            dot(r_base, r_base) - dot(r_all, r_all),
        ),
    ):
        audit.scalar(name + "/" + key, value, report[key], absolute=1e-6, relative=1e-7)
    rank_interval = [
        max(0, augmented["interval"][0] - base["interval"][1]),
        min(ceiling, max(0, augmented["interval"][1] - base["interval"][0])),
    ]
    audit.check(
        name + "/rank_gain",
        report["residual_dimension_ceiling"] == ceiling
        and report["augmented_minus_nuisance_retained_rank"] == augmented["rank"] - base["rank"]
        and report["rank_gain_cutoff_sensitivity_interval"] == rank_interval,
    )
    audit.check(
        name + "/scope",
        report["physical_identifiability_claim"] is False
        and report["fixed_active_face_only"] is True,
    )
    covariance_space = decomposition_audit(
        audit,
        name + "/covariance_space",
        covariance,
        covariance_errors,
        report["covariance_unprojected"],
        plan,
        reference=(joined, joined_errors),
    )
    overlap = [[dot(t, s) for s in covariance_space["basis"]] for t in base["basis"]]
    angle_singular = (
        jacobi_svd(overlap)["singular"][: min(len(base["basis"]), len(covariance_space["basis"]))]
        if overlap
        else []
    )
    audit.array(
        name + "/principal_angle_cosines",
        [max(0.0, min(1.0, s)) for s in angle_singular],
        [math.cos(a) for a in report["principal_angles_radians"]],
        absolute=1e-7,
    )
    rank_policy = rank_qualification(
        unique["raw_interval"],
        unique["raw_rank"],
        ceiling,
        len(covariance[0]),
        projector=projector_known,
        fd=fd_qualified,
        nuisance=base["interval"][0] == base["interval"][1],
    )
    resolved_rank = rank_policy["rank_resolved"]
    audit.check(
        name + "/unique_rank_status",
        report["projected_covariance_spectrum"]["rank_resolved"] is resolved_rank,
    )
    projected_report = report["projected_covariance_spectrum"]
    audit.check(
        name + "/raw_rank_and_ceiling",
        all(projected_report[k] == v for k, v in rank_policy.items()),
    )
    qualified_projection = projection(unique["basis"][:ceiling], r_base) if resolved_rank else None
    qualified_energy = dot(qualified_projection, qualified_projection) if resolved_rank else None
    audit.scalar(
        name + "/qualified_unique_energy",
        qualified_energy,
        report["qualified_unique_covariance_residual_energy"],
        absolute=1e-6,
        relative=1e-7,
    )
    if qualified_projection is not None:
        audit.array(
            name + "/qualified_unique_projection",
            qualified_projection,
            report["qualified_unique_covariance_residual_projection"],
            absolute=1e-6,
        )
    else:
        audit.check(
            name + "/qualified_projection_withheld",
            report["qualified_unique_covariance_residual_projection"] is None,
        )
    audit.check(
        name + "/qualification_status",
        report["finite_difference_qualified"] is fd_qualified
        and report["qualified_unique_covariance_rank"]
        == (unique["rank"] if resolved_rank else None)
        and report["covariance_uniqueness_status"]
        == ("resolved_under_estimated_guard" if resolved_rank else "unknown"),
    )
    return {
        "projector_known": projector_known,
        "rank_resolved": resolved_rank,
        "unique_rank": unique["rank"],
        "projector_error": eta_p,
    }


def chart2(covariance, coefficients, basis):
    """Independent analytic 2x2 exponential, not the runner's eigh recipe."""
    a, b = covariance[0]
    if covariance[1][0] != b or a <= 0:
        raise ValueError("invalid supplied covariance")
    l00, l10 = math.sqrt(a), b / math.sqrt(a)
    remainder = covariance[1][1] - l10 * l10
    if remainder <= 0:
        raise ValueError("supplied covariance not SPD")
    l11 = math.sqrt(remainder)
    tangent = [
        [math.fsum(c * e[i][j] for c, e in zip(coefficients, basis)) for j in range(2)]
        for i in range(2)
    ]
    middle = (tangent[0][0] + tangent[1][1]) / 2
    diagonal = (tangent[0][0] - tangent[1][1]) / 2
    radius = math.hypot(diagonal, tangent[0][1])
    ratio = math.sinh(radius) / radius if radius else 1.0
    expmid = math.exp(middle)
    exponential = [
        [expmid * (math.cosh(radius) + ratio * diagonal), expmid * ratio * tangent[0][1]],
        [expmid * ratio * tangent[0][1], expmid * (math.cosh(radius) - ratio * diagonal)],
    ]
    lower = [[l00, 0.0], [l10, l11]]
    return [
        [
            math.fsum(
                lower[i][k] * exponential[k][l] * lower[j][l] for k in range(2) for l in range(2)
            )
            for j in range(2)
        ]
        for i in range(2)
    ]


def chart_record_audit(audit, name, record):
    raw = matrix(record["raw"], 2, 2)
    canonical = [[(raw[i][j] + raw[j][i]) / 2 for j in range(2)] for i in range(2)]
    scale = max(abs(x) for row in raw for x in row)
    asymmetry = max(abs(raw[i][j] - raw[j][i]) for i in range(2) for j in range(2))
    audit.array(name + "/canonical_arithmetic", canonical, record["canonical"], absolute=1e-13)
    audit.scalar(name + "/asymmetry", asymmetry, record["asymmetry"], absolute=1e-16)
    audit.scalar(name + "/guard", 64 * EPS * scale, record["arithmetic_guard"], absolute=1e-20)
    audit.scalar(
        name + "/representation_change",
        maximum_delta(raw, canonical),
        record["maximum_representation_change"],
        absolute=1e-16,
    )
    audit.check(
        name + "/SPD_and_guard",
        asymmetry <= 64 * EPS * scale
        and canonical[0][0] > 0
        and canonical[0][0] * canonical[1][1] - canonical[0][1] * canonical[1][0] > 0,
    )


def step_audit(audit, name, step, blocks, data, baseline, plan, fd_stable):
    names = step["model"]
    missing = [n for n in names if blocks[n]["values"] is None]
    if missing:
        audit.check(
            name + "/withheld_missing",
            step["status"] == "withheld" and step["numerically_unresolved_blocks"] == missing,
        )
        return
    a, errors, labels = block_arrays(blocks, names)
    residual = subtract(data["values"], baseline)
    info = decomposition_audit(
        audit, name + "/training", a[:40], errors[:40], step["training_matrix"], plan
    )
    coefficients = vector(step["training_only_coefficients"], len(labels))
    # Independent Jacobi minimum-norm solve in exactly the declared retained
    # TRAINING space. No heldout residual enters this expression.
    independent = [
        math.fsum(
            v[j] * dot(u, residual[:40]) / s
            for u, v, s in zip(info["svd"]["u"], info["svd"]["v"], info["svd"]["singular"])
            if s > info["cutoff"]
        )
        for j in range(len(labels))
    ]
    smallest = min((s for s in info["svd"]["singular"] if s > info["cutoff"]), default=1.0)
    condition = next(iter(info["svd"]["singular"]), 0.0) / smallest
    coefficient_tolerance = max(
        1e-9, 4096 * EPS * max(len(a), len(labels)) * condition * max(1, norm(independent))
    )
    audit.array(
        name + "/training_only_coefficients",
        independent,
        coefficients,
        absolute=coefficient_tolerance,
        relative=1e-8,
    )
    audit.check(name + "/column_order", step["column_labels"] == labels)
    audit.check(
        name + "/no_new_pass",
        step["new_fit_pass"] is False and step["fixed_active_face_only"] is True,
    )
    if not fd_stable or not info["full_resolved"]:
        audit.check(
            name + "/withheld_guard",
            step["status"] == "withheld"
            and step["reason"]
            == ("FD_unknown" if not fd_stable else "training_rank_not_resolved_full_column"),
        )
        return
    if step.get("reason") == "nuisance_projector_condition_unknown":
        audit.check(
            name + "/withheld_projector",
            step["status"] == "withheld"
            and step["projector_condition_qualification"]["projector_error_qualified"] is False,
        )
        return
    by_label = dict(zip(labels, coefficients))
    g = [by_label[n] for n in blocks["G"]["labels"]]
    s = [by_label[n] for n in blocks["S"]["labels"]]
    angle = by_label.get("normal_angle", 0.0)
    settings = plan["steps"]
    constraints = [{"constraint": "unit", "factor": 1.0}]
    for label, cap, magnitude in (
        ("geometry_normalized_max", settings["geometry_normalized_max_cap"], max(map(abs, g))),
        ("covariance_Frobenius", settings["covariance_norm_cap"], norm(s)),
        ("normal_angle", settings["normal_angle_cap_radians"], abs(angle)),
    ):
        if magnitude:
            constraints.append({"constraint": label, "factor": cap / magnitude})
    base_g = [
        *data["parameters"]["centre"],
        data["parameters"]["radius"],
        data["parameters"]["fraction"],
    ]
    delta_g = [x * w for x, w in zip(g, data["domain_widths"])]
    delta_l = [by_label.get("level_" + str(i), 0.0) for i in range(2)]
    for label, value, delta, (lo, hi) in zip(
        blocks["G"]["labels"] + ["level_0", "level_1"],
        base_g + data["levels"],
        delta_g + delta_l,
        data["bounds"] + [[0, 255], [0, 255]],
    ):
        if delta:
            distance = hi - value if delta > 0 else value - lo
            constraints.append(
                {
                    "constraint": "domain_" + label,
                    "factor": settings["domain_distance_fraction"] * distance / abs(delta),
                }
            )
    alpha = max(0.0, min(c["factor"] for c in constraints))
    audit.scalar(name + "/common_alpha", alpha, step["common_alpha"], absolute=1e-13)
    audit.check(
        name + "/constraint_labels",
        [c["constraint"] for c in constraints]
        == [c["constraint"] for c in step["alpha_constraints"]],
    )
    audit.array(
        name + "/constraint_factors",
        [c["factor"] for c in constraints],
        [c["factor"] for c in step["alpha_constraints"]],
    )
    if alpha == 0:
        audit.check(
            name + "/zero_alpha_withheld",
            step["status"] == "withheld" and step["reason"] == "bound_limited_alpha_zero",
        )
        return
    linear_delta = [alpha * x for x in matvec(a, coefficients)]
    linear = add(baseline, linear_delta)
    audit.array(name + "/linear_delta", linear_delta, step["linear_delta"])
    audit.array(name + "/linear_prediction", linear, step["linear_prediction"])
    changed = [x + alpha * d for x, d in zip(base_g, delta_g)]
    levels = [x + alpha * d for x, d in zip(data["levels"], delta_l)]
    audit.array(
        name + "/trial_geometry",
        changed,
        [
            *step["trial_parameters"]["centre"],
            step["trial_parameters"]["radius"],
            step["trial_parameters"]["fraction"],
        ],
    )
    audit.array(name + "/trial_levels", levels, step["trial_levels"])
    audit.check(
        name + "/bounds",
        all(lo <= x <= hi for x, (lo, hi) in zip(changed, data["bounds"]))
        and all(0 <= x <= 255 for x in levels),
    )
    old_n = data["parameters"]["normal"]
    cosine, sine = math.cos(alpha * angle), math.sin(alpha * angle)
    audit.array(
        name + "/trial_normal",
        [cosine * old_n[0] - sine * old_n[1], sine * old_n[0] + cosine * old_n[1]],
        step["trial_parameters"]["normal"],
    )
    trial_sigma = chart2(
        data["parameters"]["covariance"], [alpha * x for x in s], plan["covariance_chart"]["basis"]
    )
    audit.array(
        name + "/trial_covariance_independent_exp",
        trial_sigma,
        step["trial_parameters"]["covariance"],
        absolute=1e-10,
    )
    chart_record_audit(audit, name + "/chart_arithmetic", step["covariance_chart"])
    if step["status"] in ("withheld_numerical_failure", "protocol_failure"):
        audit.check(
            name + "/failed_trial_withheld",
            step["local_linearization_qualified"] is False and "actual_prediction" not in step,
        )
        return
    if step["status"] == "zero_step":
        actual = baseline
        audit.check(name + "/zero_step", not any(coefficients) and step["actual_forward"] is None)
    else:
        forward = step["actual_forward"]
        audit.check(
            name + "/one_trial_resolved",
            step["status"] == "evaluated_once" and forward["statuses"] == ["resolved"] * 56,
        )
        actual = [levels[0] + (levels[1] - levels[0]) * p for p in forward["probabilities"]]
    difference = subtract(subtract(actual, baseline), linear_delta)
    denominator = max(map(abs, linear_delta))
    allowance = (
        settings["actual_vs_linear_absolute_level_allowance"]
        + settings["actual_vs_linear_relative_allowance"] * denominator
    )
    audit.array(name + "/actual_prediction", actual, step["actual_prediction"])
    audit.array(name + "/actual_minus_linear", difference, step["actual_minus_linear"])
    audit.scalar(name + "/linearity_denominator", denominator, step["linearity_denominator"])
    audit.scalar(name + "/linearity_allowance", allowance, step["linearity_allowance"])
    audit.scalar(
        name + "/maximum_linearity_discrepancy",
        max(map(abs, difference)),
        step["maximum_linearity_discrepancy"],
    )
    audit.check(
        name + "/qualification",
        step["local_linearization_qualified"] is (max(map(abs, difference)) <= allowance),
    )
    for key, values in (
        ("baseline_residual_summary", residual),
        ("linear_residual_summary", subtract(data["values"], linear)),
        ("actual_residual_summary", subtract(data["values"], actual)),
        ("linearity_summary", difference),
    ):
        summary_audit(audit, name + "/" + key, values, step[key])


def row_audit(audit, row, archived, plan):
    name = "rows/" + str(archived["index"]) + "/" + archived["name"] + "/" + archived["lane"]
    audit.check(
        name + "/old_flags",
        row["old_targets_passed"] is archived["targets_passed"]
        and row["old_completion_passed"] is archived["completion_passed"],
    )
    audit.check(name + "/no_new_fitpass", row.get("new_fit_pass", False) is False)
    if not archived["fit_attempted"]:
        audit.check(
            name + "/upstream_retained",
            row["status"] == "upstream_ineligible"
            and row.get("reason") == archived.get("reason")
            and row["forward_calls"] == 0,
        )
        return
    data = expected_data(archived)
    observations, baseline = row["observations"], row["baseline"]
    audit.check(
        name + "/observations_exact",
        observations["pixels_xy"] == data["pixels"] and observations["values"] == data["values"],
    )
    audit.check(
        name + "/split_exact",
        observations["indices"] == list(range(56))
        and observations["training_indices"] == list(range(40))
        and observations["heldout_indices"] == list(range(40, 56))
        and observations["split"] == ["training"] * 40 + ["heldout"] * 16
        and observations["strata"]
        == ["edge"] * 24
        + ["material"] * 8
        + ["background"] * 8
        + ["edge"] * 8
        + ["material"] * 4
        + ["background"] * 4,
    )
    for key in ("parameters", "levels", "bounds", "domain_widths"):
        audit.check(name + "/sanitized_input/" + key, baseline[key] == data[key])
    # Fixed input selection is reconstructed exclusively from observed fields,
    # archived bests and supplied covariance, before descriptive truth fields.
    crop = npz_crop(archived)
    audit.check(
        name + "/fixture_byte_values",
        crop["values"] == data["values"]
        and crop["crop_raw_sha256"] == archived["observed"]["field_sha256"]
        and crop["crop_shape"] == data["parameters"]["sensor_shape"]
        and crop["crop_dtype"] == archived["observed"]["field_dtype"],
    )
    binding = row["input_binding"]
    audit.check(
        name + "/binding_copy",
        binding["fixture"] == crop["fixture"]
        and binding["crop_raw_sha256"] == crop["crop_raw_sha256"]
        and binding["crop_dtype"] == crop["crop_dtype"]
        and binding["selected_values_exact"] is True
        and binding["homography_exact"] is True
        and binding["preparation_calls"] == 0,
    )
    x0, y0 = archived["observed"]["crop_origin"]
    audit.check(
        name + "/crop_H", data["parameters"]["homography"] == [[1, 0, -x0], [0, 1, -y0], [0, 0, 1]]
    )
    if "mean" not in baseline:
        audit.check(
            name + "/baseline_unknown",
            row["status"] == "diagnostic_unknown"
            and row["stage"] == "baseline_numerical_unknown"
            and row["local_linearization_qualified"] is False,
        )
        return
    forward = row["baseline_forward"]
    probability, levels = vector(forward["probabilities"], 56), data["levels"]
    contrast = levels[1] - levels[0]
    mean = [levels[0] + contrast * p for p in probability]
    residual = subtract(data["values"], mean)
    audit.array(name + "/baseline_mean", mean, baseline["mean"])
    audit.array(name + "/baseline_residual", residual, baseline["residual"])
    audit.array(name + "/baseline_probability", probability, baseline["probabilities"])
    audit.array(
        name + "/baseline_eta",
        [abs(contrast) * e for e in forward["estimated_errors"]],
        baseline["level_error_estimates"],
    )
    audit.check(name + "/baseline_sign", baseline["residual_sign"] == "observed minus predicted")
    old_forward = archived["heldout_forward"]
    old_predictions = [levels[0] + contrast * p for p in old_forward["probabilities"]]
    audit.array(
        name + "/archived_prediction_arithmetic",
        old_predictions,
        archived["heldout_predicted_intensities"],
    )
    delta = [abs(a - b) for a, b in zip(mean[40:], old_predictions)]
    guards = [
        abs(contrast) * (a + b) + 64 * EPS * max(1, abs(x), abs(y))
        for a, b, x, y in zip(
            forward["estimated_errors"][40:],
            old_forward["estimated_errors"],
            mean[40:],
            old_predictions,
        )
    ]
    audit.notes.append(
        {
            "name": name + "/same_archived_best_heldout_identity",
            "maximum_prediction_delta": max(delta),
            "maximum_combined_estimated_guard": max(guards),
            "all_points_within_estimated_guard": all(d <= g for d, g in zip(delta, guards)),
            "scope": "Same saved geometry/levels/optics and different numerical evaluation. Estimated forward error plus arithmetic only; not a new fit target or certified model bound.",
        }
    )
    summary_audit(audit, name + "/baseline_summary", residual, baseline["summary"])
    blocks = row["blocks"]
    active = active_brightness(probability, levels)
    faces = [
        {
            "level_index": i,
            "value": level,
            "face": "free" if i in active["free"] else active["active_faces"][i],
        }
        for i, level in enumerate(levels)
    ]
    audit.check(
        name + "/active_faces",
        row["active_brightness"]["faces"] == faces
        and row["active_brightness"]["arithmetic_guard"] == 64 * EPS * 255,
    )
    audit.array(name + "/B", active["matrix"], blocks["B"]["values"])
    audit.check(
        name + "/B_labels", blocks["B"]["labels"] == ["level_" + str(i) for i in active["free"]]
    )
    audit.array(
        name + "/B_error",
        [[eta] * len(active["free"]) for eta in forward["estimated_errors"]],
        blocks["B"]["errors"],
    )
    jacobian = row["geometry_derivative"]
    if blocks["G"]["values"] is not None:
        audit.array(
            name + "/G",
            [
                [contrast * j * w for j, w in zip(js, data["domain_widths"])]
                for js in jacobian["jacobian"]
            ],
            blocks["G"]["values"],
        )
        audit.array(
            name + "/G_eta",
            [
                [abs(contrast) * eta * w for w in data["domain_widths"]]
                for eta in jacobian["estimated_errors"]
            ],
            blocks["G"]["errors"],
        )
    audit.check(
        name + "/G_labels_scales",
        blocks["G"]["labels"] == plan["geometry_order"]
        and blocks["G"]["scales"] == data["domain_widths"],
    )
    records = row["finite_differences"]
    audit.check(name + "/FD_population", [r["direction"] for r in records] == [0, 1, 2, "normal"])
    fd = [fd_audit(audit, name + "/FD/" + str(r["direction"]), r, levels, plan) for r in records]
    for record in records:
        for entry in record["entries"]:
            for sign, side_name in ((1, "plus"), (-1, "minus")):
                description = entry[side_name]["parameters"]
                prefix = (
                    name
                    + "/FD_parameters/"
                    + str(record["direction"])
                    + "/"
                    + str(entry["h"])
                    + "/"
                    + side_name
                )
                if record["direction"] == "normal":
                    angle = sign * entry["h"]
                    n = data["parameters"]["normal"]
                    audit.scalar(prefix + "/angle", angle, description["angle_radians"])
                    audit.array(
                        prefix + "/normal",
                        [
                            math.cos(angle) * n[0] - math.sin(angle) * n[1],
                            math.sin(angle) * n[0] + math.cos(angle) * n[1],
                        ],
                        description["normal"],
                    )
                else:
                    coefficients = [0.0] * 3
                    coefficients[record["direction"]] = sign * entry["h"]
                    audit.check(
                        prefix + "/chart_direction", description["coefficients"] == coefficients
                    )
                    chart_record_audit(audit, prefix, description)
                    audit.array(
                        prefix + "/independent_chart",
                        chart2(
                            data["parameters"]["covariance"],
                            coefficients,
                            plan["covariance_chart"]["basis"],
                        ),
                        description["canonical"],
                        absolute=1e-10,
                    )
    for block_name, selected in (("S", fd[:3]), ("N", fd[3:])):
        if any(item is None for item in selected):
            audit.check(
                name + "/" + block_name + "_unknown",
                blocks[block_name]["values"] is None and blocks[block_name]["errors"] is None,
            )
        else:
            audit.array(
                name + "/" + block_name,
                [list(x) for x in zip(*(item["column"] for item in selected))],
                blocks[block_name]["values"],
            )
            audit.array(
                name + "/" + block_name + "_eta",
                [list(x) for x in zip(*(item["error"] for item in selected))],
                blocks[block_name]["errors"],
            )
    audit.check(
        name + "/S_chart_basis",
        blocks["S"]["basis"] == plan["covariance_chart"]["basis"]
        and blocks["S"]["labels"] == ["covariance_q0", "covariance_q1", "covariance_q2"],
    )
    for scope, count in (("all56", 56), ("training40", 40)):
        for names in plan["models"]:
            key = "".join(names)
            report = row["models"][scope][key]
            missing = [n for n in names if blocks[n]["values"] is None]
            if missing:
                audit.check(
                    name + "/models/" + scope + "/" + key + "/unknown",
                    report["status"] == "unknown"
                    and report["numerically_unresolved_blocks"] == missing,
                )
                continue
            a, eta, _labels = block_arrays(blocks, names, count)
            info = decomposition_audit(
                audit, name + "/models/" + scope + "/" + key, a, eta, report, plan
            )
            r = subtract(residual[:count], projection(info["basis"], residual[:count]))
            audit.array(
                name + "/models/" + scope + "/" + key + "/projection",
                r,
                report["projected_residual"],
                absolute=1e-6,
            )
            audit.scalar(
                name + "/models/" + scope + "/" + key + "/energy",
                dot(r, r),
                report["projected_residual_energy"],
                absolute=1e-6,
            )
            needed = fd if "N" in names else fd[:3] if "S" in names else []
            fd_stable = all(item is not None and item["stable"] for item in needed)
            raw_resolved = info["interval"][0] == info["interval"][1]
            audit.check(
                name + "/models/" + scope + "/" + key + "/FD_gates",
                report["finite_difference_qualified"] is fd_stable
                and report["raw_rank_resolved"] is raw_resolved
                and report["raw_full_column_rank_resolved"] is info["full_resolved"]
                and report["rank_resolved"] is (raw_resolved and fd_stable)
                and report["full_column_rank_resolved"] is (info["full_resolved"] and fd_stable),
            )
        for names in (("B",), ("B", "G"), ("B", "G", "N")):
            key = "".join(names) + "_versus_S"
            report = row["covariance_comparisons"][scope][key]
            missing = [n for n in (*names, "S") if blocks[n]["values"] is None]
            if missing:
                audit.check(
                    name + "/comparisons/" + scope + "/" + key + "/unknown",
                    report["status"] == "unknown"
                    and report["numerically_unresolved_blocks"] == missing,
                )
                continue
            t, et, _ = block_arrays(blocks, names, count)
            s, es, _ = block_arrays(blocks, ["S"], count)
            needed = fd if "N" in names else fd[:3]
            stable = all(item is not None and item["stable"] for item in needed)
            comparison_audit(
                audit,
                name + "/comparisons/" + scope + "/" + key,
                t,
                et,
                s,
                es,
                residual[:count],
                report,
                plan,
                stable,
            )
    audit.check(
        name + "/step_population", [s["model"] for s in row["steps"]] == plan["steps"]["models"]
    )
    for step in row["steps"]:
        needed = fd if "N" in step["model"] else fd[:3]
        stable = all(item is not None and item["stable"] for item in needed)
        audit.section(
            name + "/steps/" + "".join(step["model"]),
            lambda step=step, stable=stable: step_audit(
                audit,
                name + "/steps/" + "".join(step["model"]),
                step,
                blocks,
                data,
                mean,
                plan,
                stable,
            ),
        )
    protocol = any(x.get("protocol_failure", False) for x in records + row["steps"])
    unknown = not all(x is not None and x["stable"] for x in fd) or any(
        b["values"] is None for b in blocks.values()
    )
    audit.check(
        name + "/status_classification",
        row["status"]
        == (
            "diagnostic_protocol_failure"
            if protocol
            else "diagnostic_unknown"
            if unknown
            else "diagnostic_evaluated"
        )
        and row["FD_stable"] is all(x is not None and x["stable"] for x in fd)
        and row["local_linearization_qualified"]
        is all(s.get("local_linearization_qualified", False) for s in row["steps"]),
    )
    evaluation = row["evaluation_after_predictions"]
    audit.check(
        name + "/evaluation_old_flags",
        evaluation["old_targets_passed"] is archived["targets_passed"]
        and evaluation["old_completion_passed"] is archived["completion_passed"]
        and evaluation.get("truth_after_predictions") == archived.get("truth_after_scoring"),
    )


def work_audit(audit, report):
    work = report["work"]
    logs = work["calls"]
    for field in ("optimizer_calls", "optimizer_attempts", "renderer_calls", "preparation_calls"):
        audit.check("work/no_" + field, work[field] == 0)
    audit.check(
        "work/kind_counts",
        work["mean_calls_attempted"] == sum(x["kind"] == "mean" for x in logs)
        and work["jacobian_calls_attempted"] == sum(x["kind"] == "jacobian" for x in logs),
    )
    audit.check(
        "work/counters",
        work["returned_evaluations"] == sum(x.get("evaluations", 0) for x in logs)
        and work["returned_panels"] == sum(x.get("panels", 0) for x in logs),
    )
    assigned = set()
    for row in report["rows"]:
        if row["status"] == "upstream_ineligible":
            continue
        for i in row.get("work_log_indices", []):
            expected_context = {
                "scope": "archived_row",
                **{k: row[k] for k in ("index", "name", "lane")},
            }
            audit.check(
                "work/row_binding/" + str(i),
                i not in assigned and logs[i]["context"] == expected_context,
            )
            assigned.add(i)
    control_indices = {
        i
        for i, x in enumerate(logs)
        if x["context"].get("scope") == "independent_positive_area_control"
    }
    audit.check(
        "work/all_calls_assigned",
        assigned.isdisjoint(control_indices)
        and assigned | control_indices == set(range(len(logs))),
    )
    for i, log in enumerate(logs):
        audit.check(
            "work/query_count/" + str(i), log["queries"] == (6 if i in control_indices else 56)
        )
        if log["returned"]:
            audit.check(
                "work/returned/" + str(i),
                len(log["statuses"]) == log["queries"]
                and type(log["evaluations"]) is int
                and log["evaluations"] >= 0
                and type(log["panels"]) is int
                and log["panels"] >= 0,
            )


def independent_controls_audit(audit, report, plan):
    settings = plan["independent_forward_controls"]
    rows = report["independent_forward_controls"]
    audit.check(
        "independent_controls/population", [r["name"] for r in rows] == ["0", "1", "2", "normal"]
    )
    for row in rows:
        prefix = "independent_controls/" + row["name"]
        production = fd_audit(
            audit,
            prefix + "/production",
            row["production_FD"],
            settings["config"]["levels"],
            plan,
            length=6,
        )
        all_derivatives = []
        order_deltas = []
        for h in settings["central_steps"]:
            entries = [
                next(x for x in row["entries"] if x["h"] == h and x["order"] == order)
                for order in settings["orders"]
            ]
            for entry in entries:
                audit.array(
                    prefix + "/oracle_central/" + str(h) + "/" + str(entry["order"]),
                    central_difference(entry["plus"], entry["minus"], h),
                    entry["derivative"],
                )
            order_delta = max(
                maximum_delta(entries[0][side], entries[1][side]) for side in ("plus", "minus")
            )
            order_deltas.append(order_delta)
            all_derivatives.append(central_difference(entries[-1]["plus"], entries[-1]["minus"], h))
        fine = all_derivatives[-1]
        discrepancy = maximum_delta(*all_derivatives)
        error = maximum_delta(production["column"], fine) if production is not None else None
        audit.array(prefix + "/independent_fine", fine, row["independent_derivative"])
        audit.scalar(
            prefix + "/independent_hhalf", discrepancy, row["independent_h_half_discrepancy"]
        )
        audit.scalar(
            prefix + "/production_oracle",
            error,
            row["maximum_production_oracle_derivative_difference"],
        )
        passed = bool(
            production
            and production["stable"]
            and max(order_deltas) <= settings["level_order_allowance"]
            and discrepancy <= settings["level_derivative_allowance"]
            and error <= settings["level_derivative_allowance"]
        )
        audit.check(prefix + "/reported_pass", row["passed"] is passed and row["oracle_calls"] == 8)


def failures_audit(audit, report):
    arithmetic_types = {
        "ArithmeticError",
        "FloatingPointError",
        "OverflowError",
        "ZeroDivisionError",
    }
    for row in report["rows"]:
        for record in row.get("finite_differences", []):
            for entry in record["entries"]:
                failures = [
                    entry[side]["error"] for side in ("plus", "minus") if "error" in entry[side]
                ]
                if failures:
                    audit.check(
                        "failure/FD/"
                        + str(row["index"])
                        + "/"
                        + str(record["direction"])
                        + "/"
                        + str(entry["h"]),
                        entry["derivative"] is None and entry["propagated_error"] is None,
                    )
            if any(
                "error" in entry[side] for entry in record["entries"] for side in ("plus", "minus")
            ):
                audit.check(
                    "failure/FD_stable/" + str(row["index"]) + "/" + str(record["direction"]),
                    record["stable"] is False,
                )
        for i, step in enumerate(row.get("steps", [])):
            if "error" not in step:
                continue
            numerical = step["error"]["type"] in arithmetic_types
            audit.check(
                "failure/step/" + str(row["index"]) + "/" + str(i),
                step["status"]
                == ("withheld_numerical_failure" if numerical else "protocol_failure")
                and step["protocol_failure"] is (not numerical)
                and step["local_linearization_qualified"] is False,
            )
        for key in row.get("withheld_unsafe_fields", []):
            audit.check("failure/no_unsafe/" + str(row["index"]) + "/" + key, key not in row)


def audit_report(report, plan, runner_sha):
    audit = Audit()
    audit.section("source", lambda: source_audit(audit, report, plan, runner_sha))
    archive = read(ARCHIVE)
    identities = [(r["index"], r["name"], r["lane"]) for r in archive["rows"]]
    audit.check(
        "population/exact12",
        len(report["rows"]) == 12
        and [(r["index"], r["name"], r["lane"]) for r in report["rows"]] == identities,
    )
    for row, old in zip(report["rows"], archive["rows"]):
        audit.section(
            "row/" + str(old["index"]), lambda row=row, old=old: row_audit(audit, row, old, plan)
        )
    audit.section("work", lambda: work_audit(audit, report))
    audit.section("independent_controls", lambda: independent_controls_audit(audit, report, plan))
    audit.section("failures", lambda: failures_audit(audit, report))
    audit.check(
        "algebra_control_population",
        [r["name"] for r in report["algebra_controls"]] == plan["algebra_controls"],
    )
    expected_summary = {
        "rows_retained": len(report["rows"]),
        **{
            key: sum(r["status"] == key for r in report["rows"])
            for key in ("diagnostic_evaluated", "diagnostic_unknown", "upstream_ineligible")
        },
        "failures": sum(
            r["status"] not in ("diagnostic_evaluated", "diagnostic_unknown", "upstream_ineligible")
            for r in report["rows"]
        ),
        "controls_passed": sum(
            c.get("passed", False)
            for key in ("algebra_controls", "contract_controls", "independent_forward_controls")
            for c in report[key]
        ),
        "old_targets_passed": sum(r["old_targets_passed"] is True for r in report["rows"]),
        "old_completion_passed": sum(r["old_completion_passed"] is True for r in report["rows"]),
        "new_fit_pass_count": None,
    }
    audit.check("summary/recomputed", report["summary"] == expected_summary)
    audit.check(
        "summary/old_targets_and_completion",
        expected_summary["old_targets_passed"] == 3
        and expected_summary["old_completion_passed"] == 10,
    )
    controls = [
        c
        for key in ("algebra_controls", "contract_controls", "independent_forward_controls")
        for c in report[key]
    ]
    expected_protocol = bool(
        len(report["rows"]) == 12
        and all(c["passed"] for c in controls)
        and all(
            r["status"] in ("diagnostic_evaluated", "diagnostic_unknown", "upstream_ineligible")
            for r in report["rows"]
        )
        and report["source_unchanged"]
        and report["work"]["optimizer_attempts"] == 0
    )
    audit.check("summary/protocol_classification", report["protocol_passed"] is expected_protocol)
    failures = [c for c in audit.checks if not c["passed"]]
    return {
        "format": "pictures-to-cad-independent-residual-information-audit",
        "version": 1,
        "scope": "Stdlib saved-array/provenance/arithmetic audit, independent Jacobi SVD and two-pass pivoted QR. No model/forward/renderer/preparation/optimizer, physical accuracy, certified rank or statistical confidence claim.",
        "checks": audit.checks,
        "checks_passed": len(audit.checks) - len(failures),
        "checks_failed": len(failures),
        "all_integrity_checks_passed": not failures,
        "notes": audit.notes,
        "auditor_sha256": sha(__file__),
    }


def self_test():
    checks = []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})

    e1, e2, e3, e4 = ([float(i == j) for i in range(4)] for j in range(4))
    rows = lambda cols: [list(row) for row in zip(*cols)]
    tol = 1e-12
    nuisance = rows([e1])
    cov = rows([e2, e3, e4])
    out = quotient(nuisance, cov, [1, 2, 3, 4], tol, tol)
    check("three_orthogonal_covariance_directions", out["covariance_rank_gain"] == 3)
    check("orthogonal_projection_energy", abs(out["covariance_explained_energy"] - 29) <= tol)
    check(
        "projection_pythagoras",
        abs(
            out["nuisance_residual_energy"]
            - out["covariance_explained_energy"]
            - out["final_residual_energy"]
        )
        <= tol,
    )
    check("nuisance_orthogonality", out["maximum_nuisance_orthogonality"] <= tol)
    same = quotient(rows([e1, e2]), rows([e1, e2, add(e1, e2)]), [1, 2, 3, 4], tol, tol)
    check("covariance_in_nuisance_span_rank_zero", same["covariance_rank_gain"] == 0)
    check("covariance_in_nuisance_span_energy_zero", same["covariance_explained_energy"] == 0)
    zero = quotient(rows([e1, e2]), rows([e3, e4]), [3, 4, 0, 0], tol, tol)
    check("nuisance_only_residual_no_covariance_signal", zero["covariance_explained_energy"] == 0)
    rounded = [[1, 1, 2], [1, 1 + 1e-15, 2 + 1e-15], [1, 1, 2]]
    ghost = quotient([[1], [1], [1]], rounded, [1, 1, 1], tol, tol)
    check("projected_roundoff_not_renormalized", ghost["covariance_rank_gain"] == 0)
    tiny = quotient(
        [[1, 0], [0, 1], [0, 0]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [1, 2, 3], tol, tol
    )
    check(
        "rank_remaining_dimension_ceiling",
        tiny["covariance_rank_gain"] == tiny["remaining_dimension"] == 1,
    )
    active = active_brightness([0.2, 0.8], [0, 100])
    check(
        "fixed_brightness_face_excluded",
        active["free"] == [1] and active["matrix"] == [[0.2], [0.8]],
    )
    a = [[1, 0], [0, 2], [1, 2]]
    values = [3, 8, 11]
    fitted = least_squares_full_rank(a, values, tol)
    check(
        "training_only_unique_coefficients",
        fitted["status"] == "unique_full_rank"
        and max(abs(x - y) for x, y in zip(fitted["coefficients"], [3, 4])) <= tol,
    )
    check("training_only_normal_equations", norm(fitted["normal_equation_residual"]) <= tol)
    # A full saved-array wrapper explicitly subsets before independent solving;
    # make the held-out row huge and contradictory to expose accidental reuse.
    full_design = [*a, [100, -100]]
    one = training_only_solution(full_design, [*values, 0], [0, 1, 2], tol)
    two = training_only_solution(full_design, [*values, 1e6], [0, 1, 2], tol)
    check("heldout_changes_do_not_enter_coefficients", one == two == fitted)
    check(
        "rankdeficient_coefficients_not_falsely_compared",
        least_squares_full_rank([[1, 2], [2, 4]], [1, 2], tol)["coefficients"] is None,
    )
    interval = qr_rank_interval([[1, 0], [0, 1e-12]], 1e-12)
    check("near_cutoff_kept_interval", interval["lower"] == 1 and interval["upper"] == 2)
    check("finite_difference_arithmetic", central_difference([2, 4], [0, 0], 0.5) == [2, 4])
    check(
        "common_bound_alpha",
        abs(bound_alpha([0.5, 100], [2, -200], [[0, 1], [0, 255]]) - 0.225) <= tol,
    )
    check("all56_strata_retained", sum(v["count"] for v in strata_metrics([0] * 56).values()) == 56)
    diagonal = jacobi_svd([[3, 0, 0], [0, 2, 0], [0, 0, 1], [0, 0, 0]])
    check("jacobi_diagonal_spectrum", maximum_delta(diagonal["singular"], [3, 2, 1]) <= tol)
    conic = [[1, 2], [3, 4], [5, 6]]
    svd = jacobi_svd(conic)
    big_squared = (91 + math.sqrt(8185)) / 2
    check(
        "jacobi_closed_form_spectrum",
        maximum_delta(svd["singular"], [math.sqrt(big_squared), math.sqrt(24 / big_squared)])
        <= 1e-11,
    )
    reconstructed = [
        [
            math.fsum(s * u[i] * v[j] for u, v, s in zip(svd["u"], svd["v"], svd["singular"]))
            for j in range(2)
        ]
        for i in range(3)
    ]
    check("jacobi_reconstructs_original_matrix", maximum_delta(conic, reconstructed) <= 1e-11)
    wide = jacobi_svd([[1, 0, 1], [0, 1, 1]])
    check(
        "jacobi_wide_rank_ceiling",
        maximum_delta(wide["singular"][:2], [math.sqrt(3), 1]) <= 1e-11
        and wide["singular"][2] < tol,
    )
    check(
        "jacobi_empty_brightness_block",
        jacobi_svd([[], [], []])["singular"] == [] and spectral_norm([[], [], []]) == 0,
    )
    sigma = [[2.0, 0.3], [0.3, 1.0]]
    basis = [[[1, 0], [0, 0]], [[0, 0], [0, 1]], [[0, 1 / math.sqrt(2)], [1 / math.sqrt(2), 0]]]
    check(
        "analytic_chart_zero_identity", maximum_delta(chart2(sigma, [0, 0, 0], basis), sigma) <= tol
    )
    isotropic_chart = chart2([[1, 0], [0, 1]], [0.02, 0.02, 0], basis)
    check(
        "analytic_chart_isotropic_closed_form",
        maximum_delta(isotropic_chart, [[math.exp(0.02), 0], [0, math.exp(0.02)]]) <= tol,
    )
    check(
        "rank_ceiling_does_not_resolve_raw_interval",
        [min(1, x) for x in [1, 2]] == [1, 1] and [1, 2][0] != [1, 2][1],
    )
    censored = rank_qualification([1, 2], 1, 1, 3)
    check(
        "capped_unstable_rank_stays_unknown",
        censored["rank_interval"] == [1, 1]
        and censored["rank_resolved"] is False
        and censored["raw_rank_interval"] == [1, 2],
    )
    inconsistent = rank_qualification([2, 2], 2, 1, 3)
    check(
        "raw_count_above_ceiling_stays_unknown",
        inconsistent["retained_rank"] == 1
        and inconsistent["basis_columns_used"] == 1
        and inconsistent["rank_resolved"] is False,
    )
    check(
        "FD_guard_withholds_unique_rank",
        rank_qualification([3, 3], 3, 10, 3, fd=False)["rank_resolved"] is False,
    )
    check(
        "projector_guard_withholds_unique_rank",
        rank_qualification([3, 3], 3, 10, 3, projector=False)["rank_resolved"] is False,
    )
    check(
        "qualified_full_rank_kept",
        rank_qualification([3, 3], 3, 10, 3)["full_column_rank_resolved"] is True,
    )
    invented_plan = {"finite_differences": {"central_steps": [0.001, 0.0005]}}
    for error_type, protocol in (
        ("ArithmeticError", False),
        ("TypeError", True),
        ("ValueError", True),
    ):
        fake = {
            "stable": False,
            "protocol_failure": protocol,
            "status": "protocol_failure" if protocol else "numerically_unresolved",
            "entries": [
                {
                    "h": h,
                    "derivative": None,
                    "propagated_error": None,
                    "plus": {"error": {"type": error_type}, "protocol_failure": protocol},
                    "minus": {"error": {"type": error_type}, "protocol_failure": protocol},
                }
                for h in [0.001, 0.0005]
            ],
        }
        a = Audit()
        fd_audit(a, "invented", fake, [0, 255], invented_plan)
        check("FD_classifies_" + error_type, all(c["passed"] for c in a.checks))
        if protocol:
            bad = copy.deepcopy(fake)
            bad["status"] = "numerically_unresolved"
            b = Audit()
            fd_audit(b, "invented_bad", bad, [0, 255], invented_plan)
            check(
                "FD_detects_hidden_protocol_" + error_type, any(not c["passed"] for c in b.checks)
            )
    for name, raw in (
        ("duplicate_key", '{"a":1,"a":2}'),
        ("nan", '{"a":NaN}'),
        ("infinity", '{"a":Infinity}'),
        ("overflow", '{"a":1e400}'),
    ):
        refused = False
        try:
            strict_loads(raw)
        except ValueError:
            refused = True
        check("strict_json_" + name, refused)
    for name, value in (("boolean", [True]), ("nonfinite", [math.inf])):
        refused = False
        try:
            vector(value)
        except ValueError:
            refused = True
        check("array_refuses_" + name, refused)
    return {
        "format": "pictures-to-cad-residual-auditor-algebra-sentinels",
        "version": 1,
        "scope": "Invented stdlib-only arrays; no study numerical data, model imports, forward calls, fitting or timing.",
        "checks": checks,
        "all_passed": all(row["passed"] for row in checks),
        "auditor_sha256": sha(__file__),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--report", type=Path)
    parser.add_argument("--expected-runner-sha")
    parser.add_argument("--expected-report-sha")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        parser.error("fresh output in an existing directory required")
    if args.self_test:
        result = self_test()
    else:
        if not args.expected_runner_sha or not args.expected_report_sha:
            parser.error("report audit requires explicit expected runner and report hashes")
        if sha(args.report) != args.expected_report_sha:
            parser.error("saved report hash differs from the explicitly authorized artifact")
        result = audit_report(read(args.report), read(PLAN), args.expected_runner_sha)
        result.update(
            report_sha256=sha(args.report),
            runner_sha256=args.expected_runner_sha,
            plan_sha256=sha(PLAN),
        )
    encoded = json.dumps(result, indent=2, allow_nan=False) + "\n"
    with args.output.open("x") as stream:
        stream.write(encoded)
    print(encoded, end="")
    return 0 if result.get("all_passed", result.get("all_integrity_checks_passed", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
