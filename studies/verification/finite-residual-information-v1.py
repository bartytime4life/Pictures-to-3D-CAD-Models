#!/usr/bin/env python3
"""Replay a source-bound LOCAL residual-information diagnostic, without fitting.

The default run evaluates the prospective plan at archived best parameters.
``--contracts-only`` runs algebra/serialization/sentinel controls without any
production import, forward call, derivative, renderer, preparation or optimizer.
An exclusive output is reserved before NumPy or production imports. Exit zero
means protocol integrity only; it is not optical qualification or a new fit pass.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).resolve()
PLAN = ROOT / "studies/finite-residual-information-v1.json"
ARCHIVE = "studies/results/finite-photo-intensity-v2.json"
ORACLE = "studies/verification/finite-free-centre-v1.py"
ORACLE_PLAN = "studies/finite-free-centre-v1.json"
EXPECTED_PLAN_SHA256 = "837c626d7add9ebc6927d60245b85c1ad9bd361adaf8205e4bf62a4efd322532"
MODEL_ORDER = ("B", "G", "N", "S")
VALID_ROW_STATUSES = frozenset(
    ("diagnostic_evaluated", "diagnostic_unknown", "upstream_ineligible")
)
np = None  # Imported only after destination and source checks.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reject_constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON floating-point conversion is not finite")
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_load(path):
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("JSON input exceeds the declared 64 MiB loading cap")
    return json.loads(
        path.read_text(),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
        parse_float=finite_float,
    )


def strict_dump(value):
    return json.dumps(value, allow_nan=False, sort_keys=True, indent=2) + "\n"


def error_record(exc, stage):
    return {"stage": stage, "type": type(exc).__name__, "message": str(exc)}


def failed_row(identity, partial, exc, stage):
    """Never retain a NaN/unsafe field hidden behind an exception record."""
    result = {**identity, "status": "diagnostic_failure", "error": error_record(exc, stage)}
    withheld = []
    for key, value in partial.items():
        if key in result:
            continue
        try:
            strict_dump(value)
        except (ValueError, TypeError, OverflowError):
            withheld.append(key)
        else:
            result[key] = value
    result["withheld_unsafe_fields"] = withheld
    result["local_linearization_qualified"] = False
    return result


def step_failure(result, exc):
    """A represented numerical unknown differs from an unexpected protocol bug."""
    numerical = isinstance(exc, ArithmeticError)
    result.update(
        status="withheld_numerical_failure" if numerical else "protocol_failure",
        error=error_record(exc, "single_tangent_step"),
        protocol_failure=not numerical,
        local_linearization_qualified=False,
    )


def analysis_status(fd_records, steps, numerical_unknown):
    """Unexpected FD/trial failures must never become a green unknown row."""
    if any(record.get("protocol_failure", False) for record in (*fd_records, *steps)):
        return "diagnostic_protocol_failure"
    return "diagnostic_unknown" if numerical_unknown else "diagnostic_evaluated"


def destination(path):
    """Reserve NEW output before numerical imports or any model work."""
    target = Path(path).absolute()
    if target.is_symlink() or target.exists():
        raise ValueError("--output must be a new nonsymlink path")
    if not target.parent.is_dir():
        raise ValueError("--output parent must already exist")
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    return target, descriptor


def manifest(paths):
    result = {}
    for name in sorted(set(paths)):
        try:
            result[name] = {"sha256": sha(ROOT / name), "bytes": (ROOT / name).stat().st_size}
        except OSError as exc:
            result[name] = {"error": error_record(exc, "source_binding")}
    return result


def source_paths(plan):
    return [
        *plan["source_sha256"],
        *plan["input_sha256"],
        str(PLAN.relative_to(ROOT)),
        str(RUNNER.relative_to(ROOT)),
        "uv.lock",
    ]


def binding_errors(plan, before):
    errors = []
    for group in ("source_sha256", "input_sha256"):
        for name, expected in plan[group].items():
            actual = before.get(name, {}).get("sha256")
            if actual != expected:
                errors.append({"path": name, "expected": expected, "actual": actual})
    return errors


class Calls:
    """Only this adapter can call the supplied two numerical entry points."""

    def __init__(self, core):
        self.core = core
        self.log = []
        self.optimizer_attempts = 0
        self.context = {"scope": "unassigned"}

    def forbidden(self, *args, **kwargs):
        self.optimizer_attempts += 1
        raise AssertionError("an optimizer is forbidden in this diagnostic")

    def evaluate(self, kind, pixels, parameters, settings, label):
        record = {
            "kind": kind,
            "label": label,
            "queries": len(pixels),
            "returned": False,
            "context": copy.deepcopy(self.context),
        }
        self.log.append(record)
        try:
            function = (
                self.core.circular_segment_probabilities
                if kind == "mean"
                else self.core.circular_segment_jacobian
            )
            result = function(
                pixels,
                parameters["radius"],
                parameters["fraction"],
                centre=parameters["centre"],
                normal=parameters["normal"],
                sensor_shape=parameters["sensor_shape"],
                homography=parameters["homography"],
                psf_covariance=parameters["covariance"],
                **settings,
            )
            payload = asdict(result)
            strict_dump(payload)
            record.update(
                returned=True,
                evaluations=payload["evaluations"],
                panels=payload["panels"],
                statuses=payload["statuses"],
            )
            return payload
        except Exception as exc:
            record["error"] = error_record(exc, label)
            raise

    def summary(self):
        return {
            "calls": self.log,
            "mean_calls_attempted": sum(x["kind"] == "mean" for x in self.log),
            "jacobian_calls_attempted": sum(x["kind"] == "jacobian" for x in self.log),
            "returned_evaluations": sum(x.get("evaluations", 0) for x in self.log),
            "returned_panels": sum(x.get("panels", 0) for x in self.log),
            "failed_call_work": "unknown if the public API raised before returning counters",
            "optimizer_calls": 0,
            "optimizer_attempts": self.optimizer_attempts,
            "renderer_calls": 0,
            "preparation_calls": 0,
        }


def array(value, shape=None):
    result = np.asarray(value, dtype=float)
    if shape is not None and result.shape != shape:
        raise ValueError(f"array shape {result.shape} differs from {shape}")
    if not np.isfinite(result).all():
        raise ValueError("nonfinite numerical array")
    return result


def norm(value):
    value = np.asarray(value)
    return 0.0 if not value.size else float(np.linalg.norm(value, 2))


def resolved(payload, key, columns=None):
    if any(
        status not in {"resolved", "work_limit", "numerical", "invalid_winding"}
        for status in payload["statuses"]
    ):
        raise ValueError("unrecognized numerical status in forward payload")
    if any(status != "resolved" for status in payload["statuses"]):
        raise ArithmeticError(f"numerical status is unresolved: {payload['statuses']}")
    n = len(payload["statuses"])
    values = array(payload[key], (n,) if columns is None else (n, columns))
    errors = array(payload["estimated_errors"], (n,))
    if np.any(errors < 0):
        raise ValueError("negative numerical error estimate")
    return values, errors


def chart(covariance, coefficients, basis):
    """SPD chart, with only explicitly bounded ARITHMETIC symmetrization."""
    covariance = array(covariance, (2, 2))
    # Supplied Sigma must already be exactly symmetric. Only newly computed
    # chart roundoff is eligible for the following narrow normalization.
    if not np.array_equal(covariance, covariance.T):
        raise ValueError("supplied covariance is not exactly symmetric")
    lower = np.linalg.cholesky(covariance)
    tangent = np.einsum("i,ijk->jk", array(coefficients, (3,)), array(basis, (3, 2, 2)))
    eigenvalues, vectors = np.linalg.eigh(tangent)
    raw = lower @ ((vectors * np.exp(eigenvalues)) @ vectors.T) @ lower.T
    scale = float(np.max(np.abs(raw)))
    asymmetry = float(np.max(np.abs(raw - raw.T)))
    guard = 64 * np.finfo(float).eps * scale
    if not np.isfinite(raw).all() or asymmetry > guard:
        raise ArithmeticError("generated covariance exceeds arithmetic symmetry guard")
    canonical = (raw + raw.T) / 2
    if np.linalg.eigvalsh(canonical)[0] <= 0:
        raise ArithmeticError("generated covariance is not SPD")
    return canonical, {
        "coefficients": np.asarray(coefficients).tolist(),
        "raw": raw.tolist(),
        "canonical": canonical.tolist(),
        "asymmetry": asymmetry,
        "arithmetic_guard": guard,
        "maximum_representation_change": float(np.max(np.abs(raw - canonical))),
    }


def rotated(normal, angle):
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array([[cosine, -sine], [sine, cosine]]) @ np.asarray(normal)


def free_brightness(probabilities, levels):
    guard = 64 * np.finfo(float).eps * 255
    columns, labels, faces = [], [], []
    for index, (level, column) in enumerate(
        zip(levels, (1 - probabilities, probabilities), strict=True)
    ):
        if not 0 <= level <= 255:
            raise ValueError("archived brightness lies outside declared bounds")
        face = "lower" if level <= guard else "upper" if level >= 255 - guard else "free"
        faces.append({"level_index": index, "value": float(level), "face": face})
        if face == "free":
            columns.append(column)
            labels.append(f"level_{index}")
    return (
        np.column_stack(columns) if columns else np.empty((len(probabilities), 0)),
        labels,
        faces,
        guard,
    )


def decompose(matrix, errors, policy, *, reference=None, cutoff=None):
    matrix, errors = array(matrix), array(errors)
    if matrix.shape != errors.shape or matrix.ndim != 2:
        raise ValueError("matrix/error shape mismatch")
    if np.any(errors < 0):
        raise ValueError("negative matrix error")
    reference = (matrix, errors) if reference is None else reference
    reference_norm, error_norm = norm(reference[0]), norm(reference[1])
    roundoff = (
        policy["roundoff_multiplier"]
        * np.finfo(float).eps
        * max(1, *reference[0].shape)
        * reference_norm
    )
    computed = max(roundoff, policy["derivative_discrepancy_multiplier"] * error_norm)
    cutoff = computed if cutoff is None else float(cutoff)
    if matrix.shape[1]:
        u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
    else:
        u, singular, vh = np.empty((len(matrix), 0)), np.empty(0), np.empty((0, 0))
    lower, upper = (
        int(np.count_nonzero(singular > 2 * cutoff)),
        int(np.count_nonzero(singular > cutoff / 2)),
    )
    rank = int(np.count_nonzero(singular > cutoff))
    public = {
        "shape": list(matrix.shape),
        "spectral_norm": float(singular[0]) if len(singular) else 0.0,
        "column_norms": np.linalg.norm(matrix, axis=0).tolist(),
        "singular_values": singular.tolist(),
        "cutoff": cutoff,
        "unprojected_reference_norm": reference_norm,
        "unprojected_error_norm": error_norm,
        "roundoff_cutoff": roundoff,
        "rank_interval": [lower, upper],
        "retained_rank": rank,
        "rank_resolved": lower == upper,
        "full_column_rank_resolved": lower == upper == matrix.shape[1],
        "rank_interval_interpretation": "cutoff sensitivity only, not a rigorous true-rank or confidence interval",
        "zero_rank_interpretation": "no directions resolved under the estimated guard, not absence of physical information",
    }
    return public, u[:, :rank], (u, singular, vh)


def block_matrix(blocks, names, *, training=False):
    indices = slice(0, 40) if training else slice(None)
    values = np.concatenate([array(blocks[name]["values"])[indices] for name in names], axis=1)
    errors = np.concatenate([array(blocks[name]["errors"])[indices] for name in names], axis=1)
    labels = [label for name in names for label in blocks[name]["labels"]]
    return values, errors, labels


def projected_residual(residual, basis):
    return residual - basis @ (basis.T @ residual)


def projected_rank_policy(
    report, basis, ceiling, *, projector_known, fd_qualified, nuisance_rank_resolved
):
    """Apply a display ceiling without promoting an uncertain/inconsistent rank.

    Original sensitivity and retained counts survive unchanged in raw_* fields.
    The sliced basis is the ONLY basis subsequently used for unique energy.
    """
    raw_interval = list(report["rank_interval"])
    raw_retained = report["retained_rank"]
    raw_resolved = report["rank_resolved"]
    report.update(
        raw_rank_interval=raw_interval,
        raw_retained_rank=raw_retained,
        raw_rank_resolved=raw_resolved,
        raw_full_column_rank_resolved=report["full_column_rank_resolved"],
        ceiling_consistent=raw_retained <= ceiling and raw_interval[1] <= ceiling,
        rank_interval=[min(ceiling, rank) for rank in raw_interval],
        retained_rank=min(ceiling, raw_retained),
    )
    basis = basis[:, : report["retained_rank"]]
    report["basis_columns_used"] = basis.shape[1]
    report["rank_resolved"] = bool(
        projector_known
        and fd_qualified
        and nuisance_rank_resolved
        and raw_resolved
        and report["ceiling_consistent"]
    )
    report["full_column_rank_resolved"] = bool(
        report["rank_resolved"] and report["retained_rank"] == report["shape"][1]
    )
    return basis


def covariance_comparison(
    nuisance, nuisance_errors, covariance, covariance_errors, residual, policy, *, fd_qualified=True
):
    joined = np.column_stack((nuisance, covariance))
    joined_errors = np.column_stack((nuisance_errors, covariance_errors))
    augmented, all_basis, _ = decompose(joined, joined_errors, policy)
    base, nuisance_basis, _ = decompose(
        nuisance, nuisance_errors, policy, reference=(joined, joined_errors)
    )
    unique = covariance - nuisance_basis @ (nuisance_basis.T @ covariance)
    # Estimated arithmetic and derivative guards are ADDED, never cancelled.
    # This is a conditioning qualification, not certified interval arithmetic.
    arithmetic_factor = policy["roundoff_multiplier"] * np.finfo(float).eps * max(1, *joined.shape)
    t_arithmetic = arithmetic_factor * norm(nuisance)
    s_arithmetic = arithmetic_factor * norm(covariance)
    eta_t, eta_s = norm(nuisance_errors) + t_arithmetic, norm(covariance_errors) + s_arithmetic
    minimum = (
        base["singular_values"][-1]
        if base["full_column_rank_resolved"] and nuisance.shape[1]
        else None
    )
    gap_known = nuisance.shape[1] == 0 or minimum is not None and minimum > eta_t
    projector_error = (
        0.0
        if nuisance.shape[1] == 0
        else min(1.0, 2 * eta_t / (minimum - eta_t))
        if gap_known
        else None
    )
    projector_known = bool(gap_known and projector_error < 1)
    projection_arithmetic = arithmetic_factor * (norm(covariance) + eta_s)
    unique_error = (
        eta_s + projector_error * (norm(covariance) + eta_s) + projection_arithmetic
        if projector_known
        else None
    )
    unique_cutoff = (
        max(augmented["cutoff"], policy["derivative_discrepancy_multiplier"] * unique_error)
        if projector_known
        else augmented["cutoff"]
    )
    unique_report, unique_basis, _ = decompose(
        unique,
        np.zeros_like(unique),
        policy,
        reference=(joined, joined_errors),
        cutoff=unique_cutoff,
    )
    ceiling = max(0, len(residual) - base["retained_rank"])
    unique_basis = projected_rank_policy(
        unique_report,
        unique_basis,
        ceiling,
        projector_known=projector_known,
        fd_qualified=fd_qualified,
        nuisance_rank_resolved=base["rank_resolved"],
    )
    r_base, r_all = (
        projected_residual(residual, nuisance_basis),
        projected_residual(residual, all_basis),
    )
    unique_qualified = bool(unique_report["rank_resolved"])
    unique_projection = unique_basis @ (unique_basis.T @ r_base)
    unique_energy = float((unique_basis.T @ r_base) @ (unique_basis.T @ r_base))
    covariance_report, covariance_basis, _ = decompose(
        covariance, covariance_errors, policy, reference=(joined, joined_errors)
    )
    angle_singular = np.linalg.svd(nuisance_basis.T @ covariance_basis, compute_uv=False)
    return {
        "nuisance": base,
        "augmented": augmented,
        "projected_covariance": unique.tolist(),
        "projected_covariance_spectrum": unique_report,
        "residual_dimension_ceiling": ceiling,
        "augmented_minus_nuisance_retained_rank": augmented["retained_rank"]
        - base["retained_rank"],
        "rank_gain_cutoff_sensitivity_interval": [
            max(0, augmented["rank_interval"][0] - base["rank_interval"][1]),
            min(ceiling, max(0, augmented["rank_interval"][1] - base["rank_interval"][0])),
        ],
        "projector_error_estimate": projector_error,
        "projector_error_qualified": projector_known,
        "nuisance_error_estimate": eta_t,
        "nuisance_SVD_arithmetic_estimate": t_arithmetic,
        "covariance_unprojected_error_estimate": eta_s,
        "covariance_SVD_arithmetic_estimate": s_arithmetic,
        "projection_arithmetic_estimate": projection_arithmetic,
        "nuisance_smallest_singular_value": minimum,
        "covariance_error_estimate": unique_error,
        "nuisance_projected_residual": r_base.tolist(),
        "augmented_projected_residual": r_all.tolist(),
        "nuisance_residual_energy": float(r_base @ r_base),
        "augmented_residual_energy": float(r_all @ r_all),
        "raw_separately_truncated_residual_energy_difference": float(
            r_base @ r_base - r_all @ r_all
        ),
        "raw_difference_interpretation": "separately truncated spaces need not nest; this difference is NOT qualified unique covariance energy",
        "qualified_unique_covariance_residual_energy": unique_energy if unique_qualified else None,
        "qualified_unique_covariance_residual_projection": unique_projection.tolist()
        if unique_qualified
        else None,
        "qualified_unique_covariance_rank": unique_report["retained_rank"]
        if unique_qualified
        else None,
        "finite_difference_qualified": bool(fd_qualified),
        "covariance_uniqueness_status": "resolved_under_estimated_guard"
        if unique_qualified
        else "unknown",
        "covariance_unprojected": covariance_report,
        "principal_angles_radians": np.arccos(np.clip(angle_singular, 0, 1)).tolist(),
        "principal_angles_qualified": fd_qualified
        and projector_known
        and base["rank_resolved"]
        and covariance_report["rank_resolved"],
        "fixed_active_face_only": True,
        "physical_identifiability_claim": False,
    }


def summaries(residual):
    residual = array(residual, (56,))
    groups = {
        "all": list(range(56)),
        "training": list(range(40)),
        "heldout": list(range(40, 56)),
        "training_edge": list(range(24)),
        "training_material": list(range(24, 32)),
        "training_background": list(range(32, 40)),
        "heldout_edge": list(range(40, 48)),
        "heldout_material": list(range(48, 52)),
        "heldout_background": list(range(52, 56)),
    }
    return {
        name: {
            "count": len(indices),
            "max_abs": float(np.max(np.abs(residual[indices]))),
            "rms": math.sqrt(float(np.mean(residual[indices] ** 2))),
        }
        for name, indices in groups.items()
    }


def fd_column(data, baseline, calls, plan, direction, partial):
    contrast = data["levels"][1] - data["levels"][0]
    entries = []
    basis = plan["covariance_chart"]["basis"]
    for h in plan["finite_differences"]["central_steps"]:
        pair = {}
        for sign, name in ((1, "plus"), (-1, "minus")):
            parameters = copy.deepcopy(data["parameters"])
            if direction == "normal":
                parameters["normal"] = rotated(parameters["normal"], sign * h).tolist()
                description = {"angle_radians": sign * h, "normal": parameters["normal"]}
            else:
                coefficients = np.zeros(3)
                coefficients[direction] = sign * h
                covariance, description = chart(parameters["covariance"], coefficients, basis)
                parameters["covariance"] = covariance.tolist()
            pair[name] = {"parameters": description}
            partial.append({"direction": direction, "h": h, "side": name, "result": pair[name]})
            try:
                payload = calls.evaluate(
                    "mean",
                    data["pixels"],
                    parameters,
                    plan["mean_settings"],
                    f"FD_{direction}_{h}_{name}",
                )
                strict_dump(payload)
                pair[name]["forward"] = payload
                probability, error = resolved(payload, "probabilities")
                pair[name].update(
                    probabilities=probability.tolist(),
                    mean=(data["levels"][0] + contrast * probability).tolist(),
                    level_errors=(abs(contrast) * error).tolist(),
                )
            except Exception as exc:  # noqa: BLE001 -- retain each side and continue the other planned calls
                pair[name]["error"] = error_record(exc, "finite_difference_forward")
                pair[name]["protocol_failure"] = not isinstance(exc, ArithmeticError)
        if any("error" in pair[name] for name in ("plus", "minus")):
            entries.append({"h": h, **pair, "derivative": None, "propagated_error": None})
            continue
        plus, minus = array(pair["plus"]["mean"]), array(pair["minus"]["mean"])
        derivative = (plus - minus) / (2 * h)
        propagated = (
            array(pair["plus"]["level_errors"]) + array(pair["minus"]["level_errors"])
        ) / (2 * h)
        entries.append(
            {
                "h": h,
                "plus": pair["plus"],
                "minus": pair["minus"],
                "derivative": derivative.tolist(),
                "propagated_error": propagated.tolist(),
            }
        )
    if any(item["derivative"] is None for item in entries):
        protocol_failure = any(
            item[side].get("protocol_failure", False)
            for item in entries
            for side in ("plus", "minus")
        )
        return (
            None,
            None,
            {
                "direction": direction,
                "entries": entries,
                "stable": False,
                "status": "protocol_failure" if protocol_failure else "numerically_unresolved",
                "protocol_failure": protocol_failure,
                "estimated_not_certified": True,
            },
        )
    coarse, fine = (array(x["derivative"]) for x in entries)
    discrepancy = np.abs(coarse - fine)
    errors = (
        discrepancy + array(entries[0]["propagated_error"]) + array(entries[1]["propagated_error"])
    )
    settings = plan["finite_differences"]
    allowance = settings["absolute_level_derivative_discrepancy"] + settings[
        "relative_level_derivative_discrepancy"
    ] * np.abs(fine)
    return (
        fine,
        errors,
        {
            "direction": direction,
            "entries": entries,
            "h_half_h_discrepancy": discrepancy.tolist(),
            "stability_allowance": allowance.tolist(),
            "combined_estimated_error": errors.tolist(),
            "stable": bool(np.all(errors <= allowance)),
            "estimated_not_certified": True,
        },
    )


def tangent_step(data, blocks, names, baseline, calls, plan, fd_stable, result=None):
    matrix, errors, labels = block_matrix(blocks, names)
    training, training_errors = matrix[:40], errors[:40]
    report, _, (u, singular, vh) = decompose(training, training_errors, plan["rank_policy"])
    residual = array(data["values"]) - baseline
    retained = report["retained_rank"]
    coefficients = vh[:retained].T @ ((u[:, :retained].T @ residual[:40]) / singular[:retained])
    result = {} if result is None else result
    result.update(
        model=list(names),
        column_labels=labels,
        training_matrix=report,
        training_only_coefficients=coefficients.tolist(),
        status="withheld",
        fixed_active_face_only=True,
        new_fit_pass=False,
    )
    if not np.isfinite(coefficients).all():
        result["reason"] = "nonfinite_coefficients"
        result["training_only_coefficients"] = None
        return result
    if not fd_stable or not report["full_column_rank_resolved"]:
        result["reason"] = (
            "FD_unknown" if not fd_stable else "training_rank_not_resolved_full_column"
        )
        return result
    nuisance_names = [name for name in names if name != "S"]
    nuisance, nuisance_errors, _ = block_matrix(blocks, nuisance_names, training=True)
    covariance_block, covariance_errors, _ = block_matrix(blocks, ["S"], training=True)
    comparison = covariance_comparison(
        nuisance,
        nuisance_errors,
        covariance_block,
        covariance_errors,
        residual[:40],
        plan["rank_policy"],
    )
    result["projector_condition_qualification"] = {
        key: comparison[key]
        for key in (
            "projector_error_estimate",
            "projector_error_qualified",
            "nuisance_error_estimate",
            "nuisance_smallest_singular_value",
        )
    }
    if not comparison["projector_error_qualified"]:
        result["reason"] = "nuisance_projector_condition_unknown"
        return result
    settings = plan["steps"]
    by_label = dict(zip(labels, coefficients, strict=True))
    geometry = np.array([by_label[label] for label in blocks["G"]["labels"]])
    covariance = np.array([by_label[label] for label in blocks["S"]["labels"]])
    angle = float(by_label.get("normal_angle", 0.0))
    factors = [{"constraint": "unit", "factor": 1.0}]
    for description, cap, magnitude in (
        (
            "geometry_normalized_max",
            settings["geometry_normalized_max_cap"],
            float(np.max(np.abs(geometry))),
        ),
        ("covariance_Frobenius", settings["covariance_norm_cap"], norm(covariance)),
        ("normal_angle", settings["normal_angle_cap_radians"], abs(angle)),
    ):
        if magnitude:
            factors.append({"constraint": description, "factor": cap / magnitude})
    widths, bounds = array(data["domain_widths"]), array(data["bounds"])
    base_geometry = array(
        [
            *data["parameters"]["centre"],
            data["parameters"]["radius"],
            data["parameters"]["fraction"],
        ]
    )
    geometry_delta = geometry * widths
    level_delta = np.array([by_label.get(f"level_{i}", 0.0) for i in range(2)])
    for label, value, delta, (low, high) in zip(
        blocks["G"]["labels"] + ["level_0", "level_1"],
        np.r_[base_geometry, data["levels"]],
        np.r_[geometry_delta, level_delta],
        np.vstack((bounds, [[0, 255], [0, 255]])),
        strict=True,
    ):
        if delta:
            distance = high - value if delta > 0 else value - low
            if distance < 0:
                raise ValueError("baseline lies outside declared domain")
            factors.append(
                {
                    "constraint": f"domain_{label}",
                    "factor": settings["domain_distance_fraction"] * distance / abs(delta),
                }
            )
    alpha = max(0.0, min(item["factor"] for item in factors))
    result.update(
        common_alpha=alpha,
        alpha_constraints=factors,
        geometry_normalized_delta=geometry.tolist(),
        covariance_delta=covariance.tolist(),
        normal_angle_delta=angle,
        level_delta=level_delta.tolist(),
    )
    if alpha == 0:
        result["reason"] = "bound_limited_alpha_zero"
        return result
    changed = base_geometry + alpha * geometry_delta
    levels = array(data["levels"]) + alpha * level_delta
    if (
        np.any(changed < bounds[:, 0])
        or np.any(changed > bounds[:, 1])
        or np.any(levels < 0)
        or np.any(levels > 255)
    ):
        raise ArithmeticError("common-alpha trial left a declared bound")
    parameters = copy.deepcopy(data["parameters"])
    parameters.update(
        centre=changed[:2].tolist(),
        radius=float(changed[2]),
        fraction=float(changed[3]),
        normal=rotated(parameters["normal"], alpha * angle).tolist(),
    )
    covariance_trial, chart_record = chart(
        parameters["covariance"], alpha * covariance, plan["covariance_chart"]["basis"]
    )
    parameters["covariance"] = covariance_trial.tolist()
    linear_delta = alpha * (matrix @ coefficients)
    linear = baseline + linear_delta
    result.update(
        trial_parameters=parameters,
        trial_levels=levels.tolist(),
        covariance_chart=chart_record,
        linear_delta=linear_delta.tolist(),
        linear_prediction=linear.tolist(),
    )
    if np.count_nonzero(coefficients) == 0:
        actual = baseline.copy()
        result.update(status="zero_step", actual_forward=None)
    else:
        payload = calls.evaluate(
            "mean",
            data["pixels"],
            parameters,
            plan["mean_settings"],
            "single_tangent_trial_" + "".join(names),
        )
        result["actual_forward"] = payload
        probability, _ = resolved(payload, "probabilities")
        actual = levels[0] + (levels[1] - levels[0]) * probability
        result["status"] = "evaluated_once"
    denominator = float(np.max(np.abs(linear_delta)))
    difference = actual - baseline - linear_delta
    allowance = (
        settings["actual_vs_linear_absolute_level_allowance"]
        + settings["actual_vs_linear_relative_allowance"] * denominator
    )
    result.update(
        actual_prediction=actual.tolist(),
        actual_minus_linear=difference.tolist(),
        linearity_denominator=denominator,
        linearity_allowance=allowance,
        maximum_linearity_discrepancy=float(np.max(np.abs(difference))),
        local_linearization_qualified=bool(np.max(np.abs(difference)) <= allowance),
        baseline_residual_summary=summaries(residual),
        linear_residual_summary=summaries(array(data["values"]) - linear),
        actual_residual_summary=summaries(array(data["values"]) - actual),
        linearity_summary=summaries(difference),
    )
    return result


def analyze_row(data, calls, plan, partial=None):
    """Only sanitized observed data enter here; truth/old pass flags are absent."""
    if any("truth" in key or "scoring" in key for key in data):
        raise ValueError("truth is forbidden in analyze_row")
    partial = {} if partial is None else partial
    partial["stage"] = "baseline_forward"
    partial["observations"] = {
        "pixels_xy": data["pixels"],
        "values": data["values"],
        "split": ["training"] * 40 + ["heldout"] * 16,
        "strata": ["edge"] * 24
        + ["material"] * 8
        + ["background"] * 8
        + ["edge"] * 8
        + ["material"] * 4
        + ["background"] * 4,
        "indices": list(range(56)),
        "training_indices": list(range(40)),
        "heldout_indices": list(range(40, 56)),
    }
    partial["baseline"] = {
        "parameters": data["parameters"],
        "levels": data["levels"],
        "bounds": data["bounds"],
        "domain_widths": data["domain_widths"],
    }
    payload = calls.evaluate(
        "mean", data["pixels"], data["parameters"], plan["mean_settings"], "archived_best_baseline"
    )
    partial["baseline_forward"] = payload
    try:
        probability, error = resolved(payload, "probabilities")
    except ArithmeticError as exc:
        partial.update(
            status="diagnostic_unknown",
            stage="baseline_numerical_unknown",
            error=error_record(exc, "baseline_forward"),
            local_linearization_qualified=False,
            steps=[
                {"model": names, "status": "withheld", "reason": "baseline_numerical_unknown"}
                for names in plan["steps"]["models"]
            ],
            new_fit_pass=False,
        )
        return partial
    contrast = data["levels"][1] - data["levels"][0]
    mean = data["levels"][0] + contrast * probability
    residual = array(data["values"], (56,)) - mean
    partial["baseline"].update(
        {
            "probabilities": probability.tolist(),
            "mean": mean.tolist(),
            "residual": residual.tolist(),
            "residual_sign": "observed minus predicted",
            "level_error_estimates": (abs(contrast) * error).tolist(),
            "summary": summaries(residual),
        }
    )
    brightness, labels, faces, guard = free_brightness(probability, data["levels"])
    partial["active_brightness"] = {
        "faces": faces,
        "arithmetic_guard": guard,
        "level_bounds": [0, 255],
        "scope": "fixed active face, not feasible inward tangent cone",
    }
    blocks = {
        "B": {
            "values": brightness.tolist(),
            "errors": np.column_stack([error] * len(labels)).tolist()
            if labels
            else [[] for _ in range(56)],
            "labels": labels,
            "scales": [1.0] * len(labels),
        }
    }
    partial["blocks"] = blocks
    partial["stage"] = "analytic_geometry_derivative"
    jacobian = calls.evaluate(
        "jacobian", data["pixels"], data["parameters"], plan["mean_settings"], "geometry_derivative"
    )
    partial["geometry_derivative"] = jacobian
    widths = array(data["domain_widths"], (4,))
    try:
        geometric, geometry_error = resolved(jacobian, "jacobian", 4)
    except ArithmeticError as exc:
        blocks["G"] = {
            "values": None,
            "errors": None,
            "labels": list(plan["geometry_order"]),
            "scales": widths.tolist(),
            "error": error_record(exc, "analytic_geometry_derivative"),
        }
    else:
        blocks["G"] = {
            "values": (contrast * geometric * widths).tolist(),
            "errors": (abs(contrast) * geometry_error[:, None] * widths).tolist(),
            "labels": list(plan["geometry_order"]),
            "scales": widths.tolist(),
        }
    partial["stage"] = "covariance_and_normal_FD"
    partial["partial_FD_calls"] = []
    derivatives, errors, records = [], [], []
    for direction in (0, 1, 2, "normal"):
        derivative, estimate, record = fd_column(
            data, mean, calls, plan, direction, partial["partial_FD_calls"]
        )
        derivatives.append(derivative)
        errors.append(estimate)
        records.append(record)
    partial["finite_differences"] = records
    s_resolved = all(item is not None for item in derivatives[:3])
    n_resolved = derivatives[3] is not None
    blocks["S"] = {
        "values": np.column_stack(derivatives[:3]).tolist() if s_resolved else None,
        "errors": np.column_stack(errors[:3]).tolist() if s_resolved else None,
        "labels": ["covariance_q0", "covariance_q1", "covariance_q2"],
        "scales": [1, 1, 1],
        "basis": plan["covariance_chart"]["basis"],
        "base_cholesky": np.linalg.cholesky(array(data["parameters"]["covariance"])).tolist(),
        "chart": plan["covariance_chart"]["formula"],
    }
    blocks["N"] = {
        "values": derivatives[3][:, None].tolist() if n_resolved else None,
        "errors": errors[3][:, None].tolist() if n_resolved else None,
        "labels": ["normal_angle"],
        "scales": [1],
        "units": "radians",
    }
    fd_stable = all(record["stable"] for record in records)
    partial["FD_stable"] = fd_stable
    partial["stage"] = "information_algebra"
    models, comparisons = {}, {}
    for training in (False, True):
        scope = "training40" if training else "all56"
        models[scope], comparisons[scope] = {}, {}
        active_residual = residual[:40] if training else residual
        for names in plan["models"]:
            missing = [name for name in names if blocks[name]["values"] is None]
            if missing:
                models[scope]["".join(names)] = {
                    "status": "unknown",
                    "numerically_unresolved_blocks": missing,
                }
                continue
            values, estimates, column_labels = block_matrix(blocks, names, training=training)
            report, basis, _ = decompose(values, estimates, plan["rank_policy"])
            used_records = records if "N" in names else records[:3] if "S" in names else []
            model_fd_qualified = all(record["stable"] for record in used_records)
            report.update(
                raw_rank_resolved=report["rank_resolved"],
                raw_full_column_rank_resolved=report["full_column_rank_resolved"],
                finite_difference_qualified=model_fd_qualified,
                rank_resolved=bool(report["rank_resolved"] and model_fd_qualified),
                full_column_rank_resolved=bool(
                    report["full_column_rank_resolved"] and model_fd_qualified
                ),
                status="evaluated" if model_fd_qualified else "unknown_used_FD_guard",
            )
            projected = projected_residual(active_residual, basis)
            report.update(
                column_labels=column_labels,
                projected_residual=projected.tolist(),
                projected_residual_energy=float(projected @ projected),
            )
            models[scope]["".join(names)] = report
        for nuisance_names in (("B",), ("B", "G"), ("B", "G", "N")):
            missing = [name for name in (*nuisance_names, "S") if blocks[name]["values"] is None]
            if missing:
                comparisons[scope]["".join(nuisance_names) + "_versus_S"] = {
                    "status": "unknown",
                    "numerically_unresolved_blocks": missing,
                }
                continue
            nuisance, nuisance_errors, _ = block_matrix(blocks, nuisance_names, training=training)
            covariance, covariance_errors, _ = block_matrix(blocks, ("S",), training=training)
            required_fd = records if "N" in nuisance_names else records[:3]
            comparisons[scope]["".join(nuisance_names) + "_versus_S"] = covariance_comparison(
                nuisance,
                nuisance_errors,
                covariance,
                covariance_errors,
                active_residual,
                plan["rank_policy"],
                fd_qualified=all(record["stable"] for record in required_fd),
            )
    partial.update(models=models, covariance_comparisons=comparisons)
    partial["stage"] = "training_only_single_steps"
    partial["steps"] = []
    for names in plan["steps"]["models"]:
        step = {"model": names}
        partial["steps"].append(step)
        missing = [name for name in names if blocks[name]["values"] is None]
        if missing:
            step.update(
                status="withheld",
                reason="numerically_unresolved_derivative",
                numerically_unresolved_blocks=missing,
                local_linearization_qualified=False,
            )
            continue
        needed_records = records if "N" in names else records[:3]
        try:
            tangent_step(
                data,
                blocks,
                names,
                mean,
                calls,
                plan,
                all(record["stable"] for record in needed_records),
                step,
            )
        except Exception as exc:  # noqa: BLE001 -- one failed trial must not remove the second model
            step_failure(step, exc)
    any_unresolved = not fd_stable or any(block["values"] is None for block in blocks.values())
    partial.update(
        status=analysis_status(records, partial["steps"], any_unresolved),
        stage="complete",
        local_linearization_qualified=all(
            step.get("local_linearization_qualified", False) for step in partial["steps"]
        ),
        new_fit_pass=False,
    )
    return partial


def sanitized_data(row):
    observed, best = row["observed"], row["fit"]["best"]
    bounds = observed["bounds"]
    intervals = [*bounds["centre_bounds"], bounds["radius_bounds"], bounds["chord_fraction_bounds"]]
    pixels = observed["training_pixels"] + observed["heldout_pixels"]
    values = observed["training_values"] + observed["heldout_values"]
    if (
        len(observed["training_pixels"]) != 40
        or len(observed["heldout_pixels"]) != 16
        or len({tuple(p) for p in pixels}) != 56
    ):
        raise ValueError("archived sample population differs from fixed40/16 contract")
    covariance = row["covariance_record"]["canonical"]
    if not row["covariance_record"]["valid"]:
        raise ValueError("archived covariance was not valid")
    return {
        "pixels": pixels,
        "values": values,
        "levels": best["levels"],
        "bounds": intervals,
        "domain_widths": [high - low for low, high in intervals],
        "parameters": {
            "centre": best["centre"],
            "radius": best["radius"],
            "fraction": best["chord_fraction"],
            "normal": observed["normal"],
            "covariance": covariance,
            "homography": observed["homography"],
            "sensor_shape": observed["field_shape"],
        },
    }


def verify_pixels(row):
    """Read saved crop only; never run its observation preparer."""
    path = ROOT / "studies/fixtures/finite-moment-photo-v1" / (row["name"] + "-measurement.npz")
    with np.load(path, allow_pickle=False) as saved:
        field = saved["g"]
    observed = row["observed"]
    x0, y0, x1, y1 = observed["crop_bounds"]
    crop = np.ascontiguousarray(field[y0:y1, x0:x1])
    if (
        list(crop.shape) != observed["field_shape"]
        or crop.dtype.str != observed["field_dtype"]
        or hashlib.sha256(crop.tobytes()).hexdigest() != observed["field_sha256"]
    ):
        raise ValueError("archived crop does not match the pinned saved field")
    for split in ("training", "heldout"):
        pixels = np.asarray(observed[split + "_pixels"])
        if (
            pixels.dtype.kind not in "iu"
            or np.any(pixels < 0)
            or np.any(pixels >= np.array([crop.shape[1], crop.shape[0]]))
        ):
            raise ValueError("saved pixel is not an inbounds integer crop index")
        if not np.array_equal(crop[pixels[:, 1], pixels[:, 0]], observed[split + "_values"]):
            raise ValueError("saved observed value differs from pinned crop")
    expected_h = [[1.0, 0.0, -float(x0)], [0.0, 1.0, -float(y0)], [0.0, 0.0, 1.0]]
    if observed["homography"] != expected_h or observed["crop_origin"] != [x0, y0]:
        raise ValueError("crop/global coordinate binding differs")
    return {
        "fixture": str(path.relative_to(ROOT)),
        "crop_dtype": crop.dtype.str,
        "crop_raw_sha256": hashlib.sha256(crop.tobytes()).hexdigest(),
        "selected_values_exact": True,
        "homography_exact": True,
        "preparation_calls": 0,
    }


def descriptive_evaluation(row, analysis):
    """This is the ONLY truth access, after all coefficients/predictions exist."""
    truth = row.get("truth_after_scoring")
    result = {
        "old_targets_passed": row["targets_passed"],
        "old_completion_passed": row["completion_passed"],
        "old_geometry_after_scoring": row.get("geometry_after_scoring"),
        "old_truth_in_observed_domain_after_scoring": row.get(
            "truth_in_observed_domain_after_scoring"
        ),
        "scope": "descriptive evaluation after all step choices; no new scientific pass",
    }
    if truth is None:
        return result
    result["truth_after_predictions"] = truth
    ppm = row["ppm"]
    evaluations = []
    for step in analysis.get("steps", []):
        if step.get("status") not in ("evaluated_once", "zero_step"):
            evaluations.append({"model": step["model"], "available": False})
            continue
        parameters = step["trial_parameters"]
        evaluations.append(
            {
                "model": step["model"],
                "available": True,
                "centre_error_mm": float(
                    np.linalg.norm(np.asarray(parameters["centre"]) / ppm - truth["centre_mm"])
                ),
                "radius_error_mm": abs(parameters["radius"] / ppm - truth["radius_mm"]),
                "fraction_error": abs(parameters["fraction"] - truth["fraction"]),
            }
        )
    result["single_step_descriptive_geometry"] = evaluations
    return result


def algebra_controls(plan):
    policy = plan["rank_policy"]
    cases = []

    def check(name, callback):
        try:
            detail = callback()
            strict_dump(detail)
            cases.append({"name": name, "passed": True, "details": detail})
        except Exception as exc:  # noqa: BLE001 -- every declared control retains its failure
            cases.append(
                {"name": name, "passed": False, "error": error_record(exc, "algebra_control")}
            )

    def comparison(t, s, residual):
        return covariance_comparison(t, np.zeros_like(t), s, np.zeros_like(s), residual, policy)

    def in_span():
        t = np.eye(8)[:, :2]
        detail = comparison(t, t @ np.array([[1, 2, 3], [2, -1, 4]]), np.arange(8.0))
        assert detail["projected_covariance_spectrum"]["rank_interval"] == [0, 0]
        return detail

    def orthogonal():
        detail = comparison(np.eye(8)[:, :2], np.eye(8)[:, 2:5], np.arange(8.0))
        assert detail["projected_covariance_spectrum"]["rank_interval"] == [3, 3]
        assert abs(detail["qualified_unique_covariance_residual_energy"] - 29) < 1e-12
        return detail

    def nuisance_residual():
        detail = comparison(np.eye(8)[:, :2], np.eye(8)[:, 2:5], np.r_[3.0, 4.0, np.zeros(6)])
        assert detail["qualified_unique_covariance_residual_energy"] == 0
        return detail

    def roundoff():
        t = np.eye(8)[:, :2]
        s = np.column_stack((t[:, 0], t[:, 1], t[:, 0] + 1e-15 * np.eye(8)[:, 3]))
        detail = comparison(t, s, np.arange(8.0))
        assert detail["projected_covariance_spectrum"]["rank_interval"] == [0, 0]
        assert detail["projected_covariance_spectrum"]["unprojected_reference_norm"] > 1
        nearparallel = comparison(np.array([[1.0], [0.0]]), np.array([[1.0], [1e-14]]), np.ones(2))
        assert nearparallel["qualified_unique_covariance_residual_energy"] == 0
        assert nearparallel["raw_separately_truncated_residual_energy_difference"] != 0
        detail["nearparallel_under_cutoff"] = nearparallel
        return detail

    def ceiling():
        detail = comparison(np.eye(4)[:, :3], np.eye(4)[:, 1:4], np.arange(4.0))
        assert detail["residual_dimension_ceiling"] == 1
        assert detail["projected_covariance_spectrum"]["rank_interval"] == [1, 1]
        regressions = []
        for singular_values, expected_interval in (([3.0, 0.75], [1, 2]), ([3.0, 3.0], [2, 2])):
            matrix = np.diag(singular_values)
            report, basis, _ = decompose(matrix, np.zeros_like(matrix), policy, cutoff=1.0)
            assert report["rank_interval"] == expected_interval
            basis = projected_rank_policy(
                report,
                basis,
                1,
                projector_known=True,
                fd_qualified=True,
                nuisance_rank_resolved=True,
            )
            assert report["raw_rank_interval"] == expected_interval
            assert report["rank_interval"] == [1, 1]
            assert report["ceiling_consistent"] is False
            assert report["rank_resolved"] is False
            assert report["full_column_rank_resolved"] is False
            assert basis.shape[1] == report["retained_rank"] == report["basis_columns_used"] == 1
            regressions.append(
                {
                    "spectrum": report,
                    "basis": basis.tolist(),
                    "qualified_unique_energy_available": report["rank_resolved"],
                }
            )
        detail["ceiling_never_promotes_unresolved_or_inconsistent_rank"] = regressions
        return detail

    def brightness():
        values, labels, faces, guard = free_brightness(np.linspace(0, 1, 8), [0, 125])
        assert labels == ["level_1"] and values.shape == (8, 1)
        assert faces[0]["face"] == "lower"
        return {"values": values.tolist(), "labels": labels, "faces": faces, "guard": guard}

    for name, callback in zip(
        plan["algebra_controls"],
        (in_span, orthogonal, nuisance_residual, roundoff, ceiling, brightness),
        strict=True,
    ):
        check(name, callback)
    return cases


def contract_controls(plan):
    cases = []
    for name, text in (
        ("nested_duplicate", '{"a":{"x":1,"x":2}}'),
        ("nonfinite_constant", '{"a":NaN}'),
        ("overflow_float", '{"a":1e999}'),
    ):
        try:
            json.loads(
                text,
                object_pairs_hook=unique_object,
                parse_constant=reject_constant,
                parse_float=finite_float,
            )
        except ValueError:
            cases.append({"name": name, "passed": True})
        else:
            cases.append({"name": name, "passed": False})
    unsafe = failed_row(
        {"index": 0},
        {"safe": [1, 2], "unsafe": [math.nan], "local_linearization_qualified": True},
        ValueError("injected"),
        "sentinel",
    )
    cases.append(
        {
            "name": "unsafe_failure_field_withheld_and_pass_reset",
            "passed": "unsafe" not in unsafe
            and unsafe["safe"] == [1, 2]
            and unsafe["local_linearization_qualified"] is False,
            "details": unsafe,
        }
    )
    try:
        analyze_row({"truth_after_scoring": {}}, None, {})
    except ValueError:
        cases.append({"name": "truth_rejected_before_model_call", "passed": True})
    else:
        cases.append({"name": "truth_rejected_before_model_call", "passed": False})
    # These are invented orthogonal arrays, not archived photo parameters and
    # not a production forward call. Exercise the real step-retention path
    # AFTER it has chosen coefficients, alpha and bounded trial parameters.
    for exception_type in (TypeError, ValueError):
        name = "unexpected_trial_" + exception_type.__name__ + "_is_protocol_failure"
        result = {}
        try:
            identity = np.eye(56)
            blocks = {}
            for block, columns, labels in (
                ("B", slice(0, 2), ["level_0", "level_1"]),
                ("G", slice(2, 6), plan["geometry_order"]),
                ("S", slice(6, 9), ["covariance_q0", "covariance_q1", "covariance_q2"]),
            ):
                matrix = identity[:, columns]
                blocks[block] = {
                    "values": matrix.tolist(),
                    "errors": np.zeros_like(matrix).tolist(),
                    "labels": labels,
                }
            parameters = {
                "centre": [10.0, 10.0],
                "radius": 4.0,
                "fraction": 0.2,
                "normal": [1.0, 0.0],
                "covariance": [[1.0, 0.0], [0.0, 1.0]],
                "sensor_shape": [20, 20],
                "homography": np.eye(3).tolist(),
            }
            data = {
                "parameters": parameters,
                "pixels": [[i % 20, i // 20] for i in range(56)],
                "values": [100.1] * 56,
                "levels": [100.0, 120.0],
                "bounds": [[5, 15], [5, 15], [1, 8], [-0.5, 0.8]],
                "domain_widths": [10, 10, 7, 1.3],
            }

            class PayloadFailure:
                def __init__(self, error_type):
                    self.error_type = error_type
                    self.calls = 0

                def evaluate(self, *args):
                    self.calls += 1
                    raise self.error_type("injected malformed actual-trial payload")

            callback = PayloadFailure(exception_type)
            try:
                tangent_step(
                    data, blocks, ["B", "G", "S"], np.full(56, 100.0), callback, plan, True, result
                )
            except exception_type as exc:
                step_failure(result, exc)
            assert callback.calls == 1 and result["protocol_failure"] is True
            assert result["status"] == "protocol_failure" and result["common_alpha"] > 0
            assert len(result["training_only_coefficients"]) == 9
            assert "trial_parameters" in result and "actual_prediction" not in result
            strict_dump(result)
            cases.append(
                {"name": name, "passed": True, "details": result, "production_forward_calls": 0}
            )
        except Exception as exc:  # noqa: BLE001 -- retain synthetic callback failures too
            cases.append(
                {
                    "name": name,
                    "passed": False,
                    "error": error_record(exc, "synthetic_trial_contract"),
                }
            )
    # Four planned sides are attempted even after each callback fails. These
    # callbacks never import/call production or receive archived observations.
    for exception_type in (TypeError, ValueError, ArithmeticError):
        name = "FD_" + exception_type.__name__ + "_classification_retains_calls"
        try:

            class FDFailure:
                def __init__(self, error_type):
                    self.error_type = error_type
                    self.calls = 0

                def evaluate(self, *args):
                    self.calls += 1
                    if self.error_type is ValueError:
                        return {
                            "probabilities": [math.nan, 0.5],
                            "statuses": ["resolved"] * 2,
                            "estimated_errors": [0.0] * 2,
                        }
                    raise self.error_type("injected FD callback failure")

            callback = FDFailure(exception_type)
            data = {
                "parameters": {"covariance": [[1.0, 0.0], [0.0, 1.0]], "normal": [1.0, 0.0]},
                "pixels": [[0, 0], [1, 0]],
                "levels": [10.0, 20.0],
            }
            partial = []
            values, estimates, record = fd_column(data, None, callback, plan, 0, partial)
            expected_protocol_failure = exception_type is not ArithmeticError
            row_status = analysis_status([record], [], True)
            assert values is None and estimates is None
            assert callback.calls == len(partial) == 4 and len(record["entries"]) == 2
            assert record["protocol_failure"] is expected_protocol_failure
            assert (row_status in VALID_ROW_STATUSES) is not expected_protocol_failure
            assert row_status == (
                "diagnostic_protocol_failure" if expected_protocol_failure else "diagnostic_unknown"
            )
            strict_dump(record)
            cases.append(
                {
                    "name": name,
                    "passed": True,
                    "details": record,
                    "row_status": row_status,
                    "eligible_for_protocol_exit0": row_status in VALID_ROW_STATUSES,
                    "invented_callback_attempts": callback.calls,
                    "production_forward_calls": 0,
                }
            )
        except Exception as exc:  # noqa: BLE001 -- retain failed invented contracts
            cases.append(
                {"name": name, "passed": False, "error": error_record(exc, "invented_FD_contract")}
            )
    return cases


def independent_controls(plan, calls):
    config = plan["independent_forward_controls"]["config"]
    settings = plan["independent_forward_controls"]
    specification = importlib.util.spec_from_file_location(
        "finite_residual_independent_area", ROOT / ORACLE
    )
    oracle = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = oracle
    specification.loader.exec_module(oracle)
    oracle_plan = strict_load(ROOT / ORACLE_PLAN)
    pixels = settings["pixels"]
    points = np.asarray(pixels, float) + 0.5
    parameters = {
        "centre": config["centre"],
        "radius": config["radius"],
        "fraction": config["fraction"],
        "normal": oracle.normal(config).tolist(),
        "sensor_shape": config["sensor_shape"],
        "homography": config["homography"],
        "covariance": config["covariance"],
    }
    data = {"parameters": parameters, "levels": config["levels"], "pixels": pixels}
    results = []
    for direction in (0, 1, 2, "normal"):
        calls.context = {"scope": "independent_positive_area_control", "direction": direction}
        detail = {"name": str(direction), "passed": False, "oracle_calls": 0, "entries": []}
        results.append(detail)
        try:
            columns = []
            for h in settings["central_steps"]:
                by_order = []
                for order in settings["orders"]:
                    pair = []
                    for sign in (1, -1):
                        altered = copy.deepcopy(config)
                        if direction == "normal":
                            altered["normal_degrees"] += math.degrees(sign * h)
                        else:
                            coefficients = np.zeros(3)
                            coefficients[direction] = sign * h
                            covariance, _ = chart(
                                config["covariance"],
                                coefficients,
                                plan["covariance_chart"]["basis"],
                            )
                            altered["covariance"] = covariance.tolist()
                        detail["oracle_calls"] += 1
                        means = oracle.independent_means(points, altered, order, oracle_plan)
                        pair.append(array(means, (len(points),)))
                    by_order.append(pair)
                    detail["entries"].append(
                        {
                            "h": h,
                            "order": order,
                            "plus": pair[0].tolist(),
                            "minus": pair[1].tolist(),
                            "derivative": ((pair[0] - pair[1]) / (2 * h)).tolist(),
                        }
                    )
                order_delta = max(
                    float(np.max(np.abs(a - b)))
                    for a, b in zip(by_order[0], by_order[1], strict=True)
                )
                if order_delta > settings["level_order_allowance"]:
                    raise AssertionError("independent positive-area orders disagree")
                columns.append((by_order[-1][0] - by_order[-1][1]) / (2 * h))
            derivative, _, actual = fd_column(data, None, calls, plan, direction, [])
            detail.update(
                production_FD=actual,
                independent_derivative=columns[-1].tolist(),
                independent_h_half_discrepancy=float(np.max(np.abs(columns[0] - columns[1]))),
                maximum_production_oracle_derivative_difference=float(
                    np.max(np.abs(derivative - columns[-1]))
                ),
            )
            if (
                detail["independent_h_half_discrepancy"] > settings["level_derivative_allowance"]
                or detail["maximum_production_oracle_derivative_difference"]
                > settings["level_derivative_allowance"]
                or not actual["stable"]
            ):
                raise AssertionError(
                    "covariance/normal derivative control exceeds frozen allowance"
                )
            detail["passed"] = True
        except Exception as exc:  # noqa: BLE001 -- retain failed directions independently
            detail["error"] = error_record(exc, "independent_forward_control")
    return results


def run(plan, archive, calls, *, contracts_only=False):
    report = {
        "algebra_controls": algebra_controls(plan),
        "contract_controls": contract_controls(plan),
        "independent_forward_controls": [],
        "rows": [],
    }
    if contracts_only:
        report["mode"] = "contracts_only_no_production_import_or_forward"
        return report
    report["mode"] = "prospective_archived_parameter_diagnostic"
    if len(archive["rows"]) != len(plan["population"]):
        raise ValueError("archived row population changed")
    for expected, row in zip(plan["population"], archive["rows"], strict=True):
        if any(row[key] != expected[key] for key in ("index", "name", "lane")):
            raise ValueError("archived population order changed")
        if expected["expected_eligible"] != bool(row["fit_attempted"]):
            raise ValueError("archived eligibility differs from the frozen population")
    report["independent_forward_controls"] = independent_controls(plan, calls)
    for expected, row in zip(plan["population"], archive["rows"], strict=True):
        identity = {key: row[key] for key in ("index", "name", "lane")}
        if any(identity[key] != expected[key] for key in identity):
            raise ValueError("archived population order changed")
        old_flags = {
            "old_targets_passed": row["targets_passed"],
            "old_completion_passed": row["completion_passed"],
        }
        partial = {}
        if not expected["expected_eligible"]:
            report["rows"].append(
                {
                    **identity,
                    **old_flags,
                    "status": "upstream_ineligible",
                    "reason": row.get("reason"),
                    "forward_calls": 0,
                    "new_fit_pass": False,
                }
            )
            continue
        start = len(calls.log)
        calls.context = {"scope": "archived_row", **identity}
        try:
            partial["stage"] = "saved_pixel_binding"
            partial["input_binding"] = verify_pixels(row)
            data = sanitized_data(row)
            analysis = analyze_row(data, calls, plan, partial)
            # No truth or previous pass flags were supplied to analyze_row.
            analysis["evaluation_after_predictions"] = descriptive_evaluation(row, analysis)
            strict_dump(analysis)
            analysis = {**identity, **analysis}
        except Exception as exc:  # noqa: BLE001 -- all planned rows must survive an unexpected failure
            analysis = failed_row(identity, partial, exc, partial.get("stage", "row_setup"))
        analysis.update(old_flags)
        analysis["work_log_indices"] = list(range(start, len(calls.log)))
        report["rows"].append(analysis)
    return report


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, help="NEW strict-JSON report in an existing directory"
    )
    parser.add_argument(
        "--contracts-only",
        action="store_true",
        help="algebra/serialization only; no backend import or archived numerical evaluation",
    )
    options = parser.parse_args(arguments)
    try:
        target, descriptor = destination(options.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    start, stage = time.perf_counter(), "plan_loading"
    report = {
        "format": "pictures-to-cad-finite-residual-information",
        "version": 1,
        "protocol_passed": False,
        "optimizer_calls": 0,
        "renderer_calls": 0,
        "preparation_calls": 0,
        "python": platform.python_version(),
        "scope": "local fixed-active-face conditional residual diagnostic; no new fit, optical cause, confidence, global or physical accuracy certificate",
    }
    paths, before, calls, plan, archive = [], {}, None, None, None
    try:
        plan = strict_load(PLAN)
        report.update(
            plan=plan,
            plan_sha256=sha(PLAN),
            expected_plan_sha256=EXPECTED_PLAN_SHA256,
            runner_sha256=sha(RUNNER),
        )
        # A changed scientific knob must fail even when every referenced file
        # still matches hashes copied from a changed plan.
        stage = "archive_loading"
        archive = strict_load(ROOT / ARCHIVE)
        if sha(PLAN) != EXPECTED_PLAN_SHA256:
            stage = "plan_binding"
            paths = [str(PLAN.relative_to(ROOT)), str(RUNNER.relative_to(ROOT)), ARCHIVE]
            before = manifest(paths)
            report.update(
                source_before=before,
                binding_errors=[
                    {
                        "path": str(PLAN.relative_to(ROOT)),
                        "expected": EXPECTED_PLAN_SHA256,
                        "actual": sha(PLAN),
                    }
                ],
            )
            raise ValueError("prospective plan bytes differ from the frozen plan")
        paths = source_paths(plan)
        before = manifest(paths)
        report.update(
            plan=plan, plan_sha256=sha(PLAN), runner_sha256=sha(RUNNER), source_before=before
        )
        # Preserve readable old flags even if a different source pin fails.
        # Nothing from this unverified read is used by a numerical call.
        stage = "source_binding"
        mismatches = binding_errors(plan, before)
        if mismatches:
            report["binding_errors"] = mismatches
            raise ValueError("source/input hashes differ from the prospective plan")
        global np
        import numpy

        np = numpy
        report["numpy"] = np.__version__
        if not options.contracts_only:
            sys.path.insert(0, str(ROOT))
            from backend import finite_centre_fit as core

            calls = Calls(core)
            core.fit_circular_segment = calls.forbidden
        stage = "diagnostic"
        report.update(run(plan, archive, calls, contracts_only=options.contracts_only))
        controls = (
            report["algebra_controls"]
            + report["contract_controls"]
            + report["independent_forward_controls"]
        )
        expected_rows = 0 if options.contracts_only else len(plan["population"])
        report["protocol_passed"] = (
            len(report["rows"]) == expected_rows
            and all(c["passed"] for c in controls)
            and all(r["status"] in VALID_ROW_STATUSES for r in report["rows"])
        )
    except Exception as exc:  # noqa: BLE001 -- write a durable failure report instead of losing the population
        report["error"] = error_record(exc, stage)
        if plan is not None and "rows" not in report:
            old_rows = {row["index"]: row for row in archive.get("rows", [])} if archive else {}
            population = (
                archive["rows"]
                if archive and isinstance(archive.get("rows"), list)
                else plan.get("population", [])
                if isinstance(plan, dict)
                else []
            )
            report["rows"] = [
                {
                    **{key: item[key] for key in ("index", "name", "lane")},
                    "status": "not_evaluated_protocol_failure",
                    "error": error_record(exc, stage),
                    "old_targets_passed": old_rows.get(item["index"], {}).get("targets_passed"),
                    "old_completion_passed": old_rows.get(item["index"], {}).get(
                        "completion_passed"
                    ),
                    "forward_calls": 0,
                }
                for item in population
            ]
    finally:
        after = manifest(paths)
        report.update(
            source_after=after,
            source_unchanged=before == after,
            work=calls.summary()
            if calls
            else {
                "calls": [],
                "mean_calls_attempted": 0,
                "jacobian_calls_attempted": 0,
                "optimizer_calls": 0,
                "optimizer_attempts": 0,
                "renderer_calls": 0,
                "preparation_calls": 0,
            },
            runtime_seconds=time.perf_counter() - start,
        )
        report["protocol_passed"] = bool(
            report["protocol_passed"]
            and before == after
            and (calls is None or calls.optimizer_attempts == 0)
        )
        report["summary"] = {
            "rows_retained": len(report.get("rows", [])),
            "diagnostic_evaluated": sum(
                r["status"] == "diagnostic_evaluated" for r in report.get("rows", [])
            ),
            "diagnostic_unknown": sum(
                r["status"] == "diagnostic_unknown" for r in report.get("rows", [])
            ),
            "upstream_ineligible": sum(
                r["status"] == "upstream_ineligible" for r in report.get("rows", [])
            ),
            "failures": sum(r["status"] not in VALID_ROW_STATUSES for r in report.get("rows", [])),
            "controls_passed": sum(
                c.get("passed", False)
                for group in (
                    "algebra_controls",
                    "contract_controls",
                    "independent_forward_controls",
                )
                for c in report.get(group, [])
            ),
            "old_targets_passed": sum(
                r.get("old_targets_passed") is True for r in report.get("rows", [])
            ),
            "old_completion_passed": sum(
                r.get("old_completion_passed") is True for r in report.get("rows", [])
            ),
            "new_fit_pass_count": None,
        }
        try:
            output = strict_dump(report)
        except (ValueError, TypeError, OverflowError) as exc:
            report = {
                "format": report["format"],
                "version": 1,
                "protocol_passed": False,
                "error": error_record(exc, "final_strict_serialization"),
                "rows": [
                    failed_row(
                        {key: r[key] for key in ("index", "name", "lane") if key in r},
                        r,
                        exc,
                        "final_strict_serialization",
                    )
                    for r in report.get("rows", [])
                ],
                "work": calls.summary() if calls else {},
                "source_before": before,
                "source_after": after,
            }
            output = strict_dump(report)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(output)
            handle.flush()
            os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "output": str(target),
                "protocol_passed": report["protocol_passed"],
                "summary": report.get("summary"),
            },
            allow_nan=False,
        )
    )
    return 0 if report["protocol_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
