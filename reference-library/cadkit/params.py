"""Design-parameter register loader (``templates/design-parameters.csv`` format).

Columns: ``parameter_id, value, unit, evidence_class, source_or_rationale,
decided_on, supersedes, used_by, notes``. One row per governing value
(handbook section 17: one parameter source). A blank value means unknown and
is loaded as ``None``, never as zero. Rows whose id is ``EXAMPLE_ONLY`` or
starts with ``#`` are skipped.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

from . import calc

COLUMNS = (
    "parameter_id", "value", "unit", "evidence_class", "source_or_rationale",
    "decided_on", "supersedes", "used_by", "notes",
)
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Param:
    parameter_id: str
    value: float | str | None
    unit: str
    evidence_class: str
    source_or_rationale: str = ""
    decided_on: str = ""
    supersedes: str = ""
    used_by: str = ""
    notes: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _parse_value(text: str) -> float | str | None:
    text = (text or "").strip()
    if text == "":
        return None
    try:
        value = float(text)
    except ValueError:
        return text
    if not math.isfinite(value):
        raise ValueError(f"non-finite parameter value {text!r}")
    return value


def load_register(path: str | Path) -> dict[str, Param]:
    """Load a register into ``{parameter_id: Param}``; duplicate ids raise ``ValueError``."""
    path = Path(path)
    # utf-8-sig: spreadsheets save "CSV UTF-8" with a byte-order mark, which would
    # otherwise become part of the first column name.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(missing)}")
        params: dict[str, Param] = {}
        for line, row in enumerate(reader, start=2):
            pid = (row.get("parameter_id") or "").strip()
            if not pid or pid == "EXAMPLE_ONLY" or pid.startswith("#"):
                continue
            if pid in params:
                raise ValueError(f"{path}:{line}: duplicate parameter_id {pid!r}")
            params[pid] = Param(
                parameter_id=pid,
                value=_parse_value(row.get("value", "")),
                unit=(row.get("unit") or "").strip(),
                evidence_class=(row.get("evidence_class") or "").strip(),
                source_or_rationale=(row.get("source_or_rationale") or "").strip(),
                decided_on=(row.get("decided_on") or "").strip(),
                supersedes=(row.get("supersedes") or "").strip(),
                used_by=(row.get("used_by") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            )
    return params


def validate(params: Mapping[str, Param], required: Iterable[str] = ()) -> list[str]:
    """Return a list of problems (empty when the register is usable)."""
    problems = []
    for pid, p in params.items():
        if not _ID.match(pid):
            problems.append(f"{pid}: id must be an identifier-style name (letters, digits, underscore)")
        try:
            calc.normalize_evidence(p.evidence_class)
        except ValueError as exc:
            problems.append(f"{pid}: {exc}")
        if isinstance(p.value, float) and not p.unit:
            problems.append(f"{pid}: numeric value needs a unit (use '1' for dimensionless)")
        if p.decided_on and not _DATE.match(p.decided_on):
            problems.append(f"{pid}: decided_on must be YYYY-MM-DD")
        if p.supersedes == pid:
            problems.append(f"{pid}: a parameter cannot supersede itself")
    for pid in required:
        if pid not in params:
            problems.append(f"{pid}: required parameter is missing")
        elif params[pid].value is None:
            problems.append(f"{pid}: required parameter has no value (unknown)")
    return problems


def values(params: Mapping[str, Param]) -> dict[str, float | str | None]:
    return {pid: p.value for pid, p in params.items()}


def to_openscad_defines(params: Mapping[str, Param], mapping: Mapping[str, str] | None = None) -> dict:
    """``{scad_variable: value}`` for ``openscad -D``.

    Without a mapping, every parameter with a known value is passed under its
    own id. With a mapping ``{parameter_id: scad_name}``, only those are passed
    and each must have a value.
    """
    if mapping is None:
        return {pid: p.value for pid, p in params.items() if p.value is not None}
    out = {}
    for pid, name in mapping.items():
        if pid not in params:
            raise KeyError(f"parameter {pid!r} is not in the register")
        if params[pid].value is None:
            raise ValueError(f"parameter {pid!r} is unknown (blank); refusing to pass it to OpenSCAD")
        out[name] = params[pid].value
    return out
