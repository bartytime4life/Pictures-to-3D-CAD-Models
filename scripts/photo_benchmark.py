"""Compare reference-sheet traces of your own photos with your own caliper measurements.

Run with .venv/bin/python scripts/photo_benchmark.py FOLDER, or
`make photo-benchmark PHOTOS=FOLDER`. FOLDER holds the photos and a benchmark.json that
names, for each part, its photos and the dimensions you measured; see
docs/photo-benchmark.md. `--example FOLDER` writes a rendered example to copy from.

Each photo is traced by the function the workbench's own upload uses. Everything runs
on this computer. Reports hold file names, dimensions and trace notes; they hold no
image data, camera metadata or folder path.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import re
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MANIFEST = "benchmark.json"
SHEETS = ("a4", "letter")
KINDS = ("outline", "diameters", "openings", "radii", "centre_distances")
# Legacy manifest name; this only controls display emphasis, not a metrological
# uncertainty budget, confidence interval or manufacturing acceptance rule.
CALIPER_UNCERTAINTY_MM = 0.03
SAMPLE_SAGITTA_MM = 0.0005
PART_KEYS = {"name", "photos", "measured", "thickness_mm", "light_part", "sheet"}
MAX_MATCH_EXPECTED = 128
MAX_MATCH_CANDIDATES = 2048
MAX_MATCH_PAIRS = 131_072


class ManifestError(ValueError):
    """The folder or its benchmark.json cannot be used; the message says why."""


# --- the manifest -------------------------------------------------------------------


def _number(value, what, low=0.0, high=2000.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestError(f"{what} must be a number in millimetres.")
    if not (math.isfinite(value) and low < value <= high):
        raise ManifestError(f"{what} must be above {low:g} and at most {high:g} mm.")
    return float(value)


def _sheet(value, what):
    if value in SHEETS:
        return value
    if isinstance(value, list) and len(value) == 2:
        return [_number(v, f"{what} side", 10.0 - 1e-9) for v in value]
    raise ManifestError(
        f'{what} must be "a4", "letter" or the sheet\'s measured [width, height] in mm.'
    )


def _measured(value, part):
    if not isinstance(value, dict) or not value:
        raise ManifestError(f'Part "{part}" needs "measured" dimensions.')
    unknown = sorted(set(value) - set(KINDS))
    if unknown:
        raise ManifestError(
            f'Part "{part}": unknown measurement {unknown[0]!r}. Use {", ".join(KINDS)}.'
        )
    out = {}
    for kind, entry in value.items():
        what = f'Part "{part}" {kind}'
        if kind == "outline":
            entry = [entry]
        if not isinstance(entry, list) or not entry:
            raise ManifestError(f"{what} must be a list of measurements.")
        if len(entry) > MAX_MATCH_EXPECTED:
            raise ManifestError(
                f"{what}: use at most {MAX_MATCH_EXPECTED} features per kind in one part. "
                "Split the measurements into separately named part entries."
            )
        if kind in ("outline", "openings"):
            pairs = []
            for pair in entry:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ManifestError(f"{what} needs [length, width] pairs.")
                pairs.append(sorted((_number(v, what) for v in pair), reverse=True))
            out[kind] = pairs
        else:
            out[kind] = [_number(v, what) for v in entry]
    return out


def load_manifest(folder):
    """The folder's benchmark.json, checked, with each part's photos resolved to files."""
    folder = Path(folder)
    path = folder / MANIFEST
    if not path.is_file():
        raise ManifestError(f"No {MANIFEST} in {folder.name or folder}. See docs/photo-benchmark.md.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"{MANIFEST} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("parts"), list) or not raw["parts"]:
        raise ManifestError(f'{MANIFEST} needs a "parts" list.')
    unknown = sorted(set(raw) - {"sheet", "caliper_uncertainty_mm", "parts"})
    if unknown:
        raise ManifestError(f"{MANIFEST}: unknown setting {unknown[0]!r}.")
    sheet = _sheet(raw.get("sheet", "a4"), '"sheet"')
    uncertainty = _number(
        raw.get("caliper_uncertainty_mm", CALIPER_UNCERTAINTY_MM), '"caliper_uncertainty_mm"', high=5
    )
    parts, names = [], set()
    for entry in raw["parts"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"].strip():
            raise ManifestError('Every part needs a "name".')
        name = entry["name"].strip()
        if name in names:
            raise ManifestError(f'Two parts are named "{name}".')
        names.add(name)
        unknown = sorted(set(entry) - PART_KEYS)
        if unknown:
            raise ManifestError(f'Part "{name}": unknown setting {unknown[0]!r}.')
        patterns = entry.get("photos")
        if isinstance(patterns, str):
            patterns = [patterns]
        if not isinstance(patterns, list) or not patterns or not all(isinstance(p, str) for p in patterns):
            raise ManifestError(f'Part "{name}" needs "photos": file names or patterns such as "bracket-*.jpg".')
        photos = []
        for pattern in patterns:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
                raise ManifestError(f'Part "{name}": photos must be inside the benchmark folder.')
            try:
                found = sorted(p for p in folder.glob(pattern) if p.is_file() and p.name != MANIFEST)
            except (ValueError, NotImplementedError):
                found = []
            if not found:
                raise ManifestError(f'Part "{name}": no photo matches {pattern!r}.')
            photos.extend(p for p in found if p not in photos)
        thickness = entry.get("thickness_mm")
        light = entry.get("light_part", False)
        if not isinstance(light, bool):
            raise ManifestError(f'Part "{name}": "light_part" must be true or false.')
        parts.append(
            {
                "name": name,
                "photos": photos,
                "measured": _measured(entry.get("measured"), name),
                "thickness_mm": None
                if thickness is None
                else _number(thickness, f'Part "{name}" thickness_mm', high=500),
                "light_part": light,
                "sheet": _sheet(entry["sheet"], f'Part "{name}" sheet') if "sheet" in entry else sheet,
            }
        )
    return {"caliper_uncertainty_mm": uncertainty, "parts": parts}


# --- what a trace measured ----------------------------------------------------------


def _ring_points(ring, mm):
    """Vertices (mm) within SAMPLE_SAGITTA_MM of a ring of fitted segments."""
    from backend.fitting import arc_geometry

    points = []
    for segment in ring:
        if segment["kind"] == "line":
            points.append(segment["start"])
            continue
        if segment["kind"] == "circle":
            centre, radius, start, sweep = segment["center"], segment["radius"], 0.0, 2 * math.pi
        else:
            centre, radius, start, sweep = arc_geometry(segment["start"], segment["mid"], segment["end"])
        step = 2 * math.acos(max(-1.0, 1 - min(SAMPLE_SAGITTA_MM / (radius * mm), 1)))
        count = max(2, math.ceil(abs(sweep) / max(step, 1e-6)))
        points.extend(
            (centre[0] + radius * math.cos(start + sweep * k / count), centre[1] + radius * math.sin(start + sweep * k / count))
            for k in range(count)
        )
    return np.asarray(points, np.float64) * mm


def _box(points):
    """(long, short) sides of the smallest rectangle enclosing the points."""
    centre = points.mean(axis=0)  # centred, so float32 keeps about a micrometre
    (_, _), sides, _ = cv2.minAreaRect((points - centre).astype(np.float32))
    return (float(max(sides)), float(min(sides)))


def features(profile):
    """Millimetre dimensions of a reference-sheet trace, by the kinds a manifest names.

    outline and openings are the sides of the smallest enclosing rectangle, which is
    what calipers read across parallel sides. diameters are the boundaries fitted as
    one circle, each with whether it is the part's outside. radii are the fitted arcs.
    centre_distances are between the centres of every two circular holes.
    """
    from backend.fitting import arc_geometry

    mm = profile["reference"]["mm_per_px"]
    primitives = profile["primitives"]
    rings = [(primitives["outer"], True)] + [(ring, False) for ring in primitives.get("holes", [])]
    found = {"outline": [], "diameters": [], "openings": [], "radii": [], "centre_distances": []}
    centres = []
    for ring, outer in rings:
        if len(ring) == 1 and ring[0]["kind"] == "circle":
            found["diameters"].append((2 * ring[0]["radius"] * mm, outer))
            if not outer:
                centres.append(np.asarray(ring[0]["center"], np.float64) * mm)
        elif not outer:
            found["openings"].append(_box(_ring_points(ring, mm)))
        if outer:
            found["outline"].append(_box(_ring_points(ring, mm)))
        for segment in ring:
            if segment["kind"] == "arc":
                found["radii"].append(arc_geometry(segment["start"], segment["mid"], segment["end"])[1] * mm)
    for i, a in enumerate(centres):
        for b in centres[i + 1 :]:
            found["centre_distances"].append(float(np.linalg.norm(a - b)))
    return found


def tolerance(expected):
    """How far a traced feature may lie from a caliper value and still be taken for it."""
    return max(1.0, 0.15 * expected)


def match(expected, candidates, cost):
    """Maximize admitted match count, then minimize total admitted size error.

    Returns, per expected value, the index of its candidate or None. `cost` gives a
    pair's distance, or None when the candidate is too far to be the same feature.

    Unit-capacity min-cost flow uses shortest augmenting paths and integer reduced
    costs. Float costs are scaled to their exact common binary denominator, without
    quantization or epsilon tie penalties. Canonical value order and stable graph
    traversal resolve equal optima deterministically; they do not identify physical
    features of equal size. Work is O(K E log V), K <= min(n, m), with explicit bounds.
    """
    n, m = len(expected), len(candidates)
    chosen = [None] * n
    if not n:
        return chosen
    if n > MAX_MATCH_EXPECTED or m > MAX_MATCH_CANDIDATES or n * m > MAX_MATCH_PAIRS:
        raise ManifestError(
            "Benchmark correspondence exceeds its work limit "
            f"({MAX_MATCH_EXPECTED} expected features, {MAX_MATCH_CANDIDATES} candidates, "
            f"{MAX_MATCH_PAIRS} candidate pairs per kind). "
            "Split the measurement list into smaller named part entries or simplify the outline."
        )
    if not m:
        return chosen
    expected_order = sorted(range(n), key=lambda i: expected[i])
    candidate_order = sorted(range(m), key=lambda j: candidates[j])
    pairs, denominator = [], 1
    for i, original_i in enumerate(expected_order):
        for j, original_j in enumerate(candidate_order):
            value = cost(expected[original_i], candidates[original_j])
            if value is None:
                continue
            if not math.isfinite(value) or value < 0:
                raise ManifestError(
                    "Benchmark correspondence costs must be finite and nonnegative."
                )
            numerator, divisor = float(value).as_integer_ratio()
            denominator = max(denominator, divisor)  # float denominators are powers of two
            pairs.append((i, j, numerator, divisor))
    if not pairs:
        return chosen

    source, sink = n + m, n + m + 1
    graph = [[] for _ in range(sink + 1)]

    def edge(a, b, value):
        forward = [b, len(graph[b]), 1, value]
        graph[a].append(forward)
        graph[b].append([a, len(graph[a]) - 1, 0, -value])
        return forward

    for i in range(n):
        edge(source, i, 0)
    for j in range(m):
        edge(n + j, sink, 0)
    admitted = [
        (i, j, edge(i, n + j, numerator * (denominator // divisor)))
        for i, j, numerator, divisor in pairs
    ]
    potential = [0] * len(graph)
    while True:
        distance, previous = [None] * len(graph), [None] * len(graph)
        distance[source] = 0
        queue = [(0, source)]
        while queue:
            current, a = heapq.heappop(queue)
            if distance[a] != current:
                continue
            for index, (b, _, capacity, value) in enumerate(graph[a]):
                if not capacity:
                    continue
                trial = current + value + potential[a] - potential[b]
                if distance[b] is None or trial < distance[b]:
                    distance[b], previous[b] = trial, (a, index)
                    heapq.heappush(queue, (trial, b))
        if distance[sink] is None:
            break
        # Truncation also preserves nonnegative reduced costs on edges from nodes
        # unreachable this round, without assigning infinity to their potentials.
        for a, value in enumerate(distance):
            potential[a] += distance[sink] if value is None else min(value, distance[sink])
        b = sink
        while b != source:
            a, index = previous[b]
            forward = graph[a][index]
            forward[2] -= 1
            graph[b][forward[1]][2] += 1
            b = a
    for i, j, forward in admitted:
        if not forward[2]:
            chosen[expected_order[i]] = candidate_order[j]
    return chosen


def _scalar_cost(e, m):
    return abs(e - m) if abs(e - m) <= tolerance(e) else None


def _pair_cost(e, m):
    if all(abs(a - b) <= tolerance(a) for a, b in zip(e, m)):
        return abs(e[0] - m[0]) + abs(e[1] - m[1])
    return None


def samples(measured, found):
    """One sample per caliper value: its label, the traced value (None when no traced
    feature matches) and `edge`, the number of boundaries by which it grows when every
    boundary moves outward from the material: +2 across the outside, -2 across a hole,
    0 between centres, None for radii, which the scale and edge fit leaves out."""
    out = []

    def add(kind, label, expected, value, edge):
        out.append({"kind": kind, "label": label, "expected_mm": expected, "measured_mm": value, "edge": edge})

    for kind in KINDS:
        wanted = measured.get(kind)
        if not wanted:
            continue
        if kind in ("outline", "openings"):
            chosen = match(wanted, found[kind], _pair_cost)
            for pair, j in zip(wanted, chosen):
                name = "Outline" if kind == "outline" else f"Opening {pair[0]:g} × {pair[1]:g}"
                for side, k in (("length", 0), ("width", 1)):
                    value = None if j is None else found[kind][j][k]
                    add(kind, f"{name} {side}", pair[k], value, 2 if kind == "outline" else -2)
        elif kind == "diameters":
            chosen = match(wanted, [d for d, _ in found[kind]], _scalar_cost)
            for expected, j in zip(wanted, chosen):
                value, outer = (None, False) if j is None else found[kind][j]
                add(kind, f"Ø{expected:g}", expected, value, 2 if outer else -2)
        else:
            chosen = match(wanted, found[kind], _scalar_cost)
            for expected, j in zip(wanted, chosen):
                label = f"R{expected:g}" if kind == "radii" else f"Centres {expected:g}"
                add(kind, label, expected, None if j is None else found[kind][j], None if kind == "radii" else 0)
    return out


def scale_and_edge(found_samples):
    """Split one photo's errors into a scale error and an edge offset.

    A wrong scale (the sheet's stated size, or the perspective correction) changes
    every dimension in proportion to its size. A boundary found off the true edge (blur,
    shadow, tone) grows outside dimensions and shrinks holes by twice the offset, and
    leaves distances between centres alone. Least squares over
    error = scale * size + edge * offset. Returns None unless at least four samples
    determine both.
    """
    rows = [s for s in found_samples if s["measured_mm"] is not None and s["edge"] is not None]
    if len(rows) < 4:
        return None
    design = np.array([[s["expected_mm"], s["edge"]] for s in rows], np.float64)
    errors = np.array([s["measured_mm"] - s["expected_mm"] for s in rows])
    norms = np.linalg.norm(design, axis=0)
    if not norms.all() or np.linalg.cond(design / norms) > 10:
        return None
    (scale, offset), *_ = np.linalg.lstsq(design, errors, rcond=None)
    residual = errors - design @ np.array([scale, offset])
    return {
        "scale_percent": float(100 * scale),
        "edge_offset_mm": float(offset),
        "residual_mm": float(np.sqrt(np.mean(residual**2))),
    }


_PROPORTIONS = re.compile(r"(?:within|by) ([+-]?\d+(?:\.\d+)?) %")


def sheet_proportions(notes):
    """Percent by which the sheet's proportions in the photo differ from the stated
    size, from the trace's own note; None when the trace did not say."""
    for note in notes:
        if note.startswith(("Sheet proportions check", "The sheet's proportions")):
            found = _PROPORTIONS.search(note)
            if found:
                return float(found.group(1))
    return None


# --- running ------------------------------------------------------------------------


def trace_photo(path, part, snap, name=None):
    """One photo's record: its samples and conditions, or why it could not be traced.
    `name` is how the report calls the photo; its file name unless given."""
    from backend.tracing import TraceError, trace_image

    record = {"file": name or path.name}
    sheet = part["sheet"]
    try:
        result = trace_image(
            path.read_bytes(),
            inverted=part["light_part"],
            reference=sheet if isinstance(sheet, str) else "custom",
            sheet_mm=None if isinstance(sheet, str) else tuple(sheet),
            thickness_mm=part["thickness_mm"],
            snap=snap,
        )
    except (TraceError, OSError) as exc:
        return {**record, "traced": False, "reason": str(exc)}
    reference = result["profile"]["reference"]
    found = samples(part["measured"], features(result["profile"]))
    return {
        **record,
        "traced": True,
        "edge_blur_mm": reference["edge_blur_mm"],
        "mm_per_px": reference["mm_per_px"],
        "lens_k1": reference["lens_k1"],
        "camera_height_mm": reference.get("camera_height_mm"),
        "sheet_proportions_percent": sheet_proportions(reference["notes"]),
        "notes": reference["notes"],
        "samples": found,
        "fit": scale_and_edge(found),
    }


def _spread(values):
    return statistics.stdev(values) if len(values) > 1 else None


def rows_of(photos):
    """A part's table: one row per caliper value, equal values of a kind sharing a row.

    `spread_mm` is the sample standard deviation of the row's errors. For one feature
    that is the repeat-shot spread; for several equal features it also holds the
    differences between them.
    """
    rows = {}
    for photo in photos:
        for sample in photo.get("samples", []):
            row = rows.setdefault(
                (sample["kind"], sample["label"]),
                {
                    "kind": sample["kind"],
                    "label": sample["label"],
                    "expected_mm": sample["expected_mm"],
                    "features": 0,
                    "errors": [],
                    "missing": 0,
                    "photos": set(),
                },
            )
            row["photos"].add(photo["file"])
            if sample["measured_mm"] is None:
                row["missing"] += 1
            else:
                row["errors"].append((sample["measured_mm"] - sample["expected_mm"], photo["file"]))
    out = []
    for row in rows.values():
        errors = [e for e, _ in row["errors"]]
        worst = max(row["errors"], key=lambda e: abs(e[0]), default=(None, None))
        photos_seen = len(row.pop("photos"))
        out.append(
            {
                **row,
                "features": (len(errors) + row["missing"]) // max(photos_seen, 1),
                "errors": errors,
                "photos": photos_seen,
                "mean_error_mm": statistics.fmean(errors) if errors else None,
                "spread_mm": _spread(errors),
                "worst_error_mm": worst[0],
                "worst_photo": worst[1],
            }
        )
    return out


def dimension_count(measured):
    """Requested scalar comparisons per photo, including both sides of a pair."""
    return sum(
        len(values) * (2 if kind in ("outline", "openings") else 1)
        for kind, values in measured.items()
    )


def photo_coverage(photo, requested):
    """Keep failed traces distinct from unmatched features in successful traces."""
    compared = (
        sum(s["measured_mm"] is not None for s in photo.get("samples", []))
        if photo["traced"]
        else 0
    )
    return {
        "requested": requested,
        "compared": compared,
        "unmatched": requested - compared if photo["traced"] else 0,
        "unavailable": 0 if photo["traced"] else requested,
    }


def total_coverage(records):
    return {
        key: sum(record["coverage"][key] for record in records)
        for key in ("requested", "compared", "unmatched", "unavailable")
    }


def run(folder, snap=True, progress=None):
    """Trace every photo the folder's manifest names and collect the report."""
    folder = Path(folder)
    manifest = load_manifest(folder)
    parts = []
    for part in manifest["parts"]:
        photos = []
        requested = dimension_count(part["measured"])
        for path in part["photos"]:
            name = path.relative_to(folder).as_posix()  # tells apart subfolders' photos
            if progress:
                progress(f"{part['name']}: {name}")
            photo = trace_photo(path, part, snap, name)
            photo["coverage"] = photo_coverage(photo, requested)
            photos.append(photo)
        fits = [p["fit"] for p in photos if p.get("fit")]
        parts.append(
            {
                "name": part["name"],
                "sheet": part["sheet"],
                "thickness_mm": part["thickness_mm"],
                "photos": photos,
                "coverage": total_coverage(photos),
                "rows": rows_of(photos),
                "fit": {
                    key: {
                        "mean": statistics.fmean(f[key] for f in fits),
                        "spread": _spread([f[key] for f in fits]),
                    }
                    for key in ("scale_percent", "edge_offset_mm", "residual_mm")
                }
                if fits
                else None,
            }
        )
    errors = sorted(abs(e) for part in parts for row in part["rows"] for e in row["errors"])
    traced = sum(p["traced"] for part in parts for p in part["photos"])
    return {
        "generated": datetime.now(UTC).isoformat(timespec="seconds"),
        "snap": snap,
        "caliper_uncertainty_mm": manifest["caliper_uncertainty_mm"],
        "parts": parts,
        "summary": {
            **total_coverage(parts),
            "photos": sum(len(part["photos"]) for part in parts),
            "traced": traced,
            # Retain these legacy aliases. Missing still means unmatched in a
            # successful trace, while unavailable counts wholly failed photos.
            "samples": len(errors),
            "missing": sum(row["missing"] for part in parts for row in part["rows"]),
            "median_abs_error_mm": statistics.median(errors) if errors else None,
            "p95_abs_error_mm": float(np.percentile(errors, 95)) if errors else None,
            "worst_abs_error_mm": errors[-1] if errors else None,
        },
    }


# --- reporting ----------------------------------------------------------------------


def _signed(value, digits=3):
    # Adding 0.0 turns a rounded -0.0 into 0.0, so no error prints as "-0.000".
    return "—" if value is None else f"{round(value, digits) + 0.0:+.{digits}f}"


def _plain(value, digits=3):
    return "—" if value is None else f"{value:.{digits}f}"


def render(report):
    """The report as Markdown."""
    summary = report["summary"]
    lines = [
        "# Photo benchmark",
        "",
        f"{summary['traced']} of {summary['photos']} photos traced.",
        (
            f"Dimensions: {summary['compared']} of {summary['requested']} requested compared; "
            f"{summary['unmatched']} unmatched in successful traces; "
            f"{summary['unavailable']} unavailable in failed traces."
        ),
    ]
    if summary["samples"]:
        lines.append(
            f"Matched dimensions only: absolute error median {summary['median_abs_error_mm']:.3f} mm, 95th percentile"
            f" {summary['p95_abs_error_mm']:.3f} mm, worst {summary['worst_abs_error_mm']:.3f} mm."
        )
    else:
        lines.append("No dimensions matched; absolute-error statistics are unavailable.")
    lines += [
        (
            "Errors are the trace minus your reference measurement. "
            f"Display threshold (caliper_uncertainty_mm): {report['caliper_uncertainty_mm']:g} mm; "
            "mean errors beyond it are in bold. This input is not a propagated uncertainty, "
            "confidence level or manufacturing acceptance rule."
        ),
        (
            "Size correspondence maximizes admitted match count, then minimizes total absolute size error. "
            "Each expected scalar uses a max(1 mm, 15%) correspondence gate; paired dimensions must both pass. "
            "The gate and equal-size tie choices do not establish accuracy or physical feature identity."
        ),
        (
            "Spread is the observed sample SD. Equal-size features and shared calibration can correlate "
            "readings; pooled readings are not independent captures."
        ),
        "Design-intent snapping was " + ("on, as in the workbench." if report["snap"] else "off."),
    ]
    for part in report["parts"]:
        sheet = part["sheet"]
        described = sheet.upper() if isinstance(sheet, str) else f"{sheet[0]:g} × {sheet[1]:g} mm"
        lines += [
            "",
            f"## {part['name']}",
            "",
            (
                f"Dimensions: {part['coverage']['compared']} of {part['coverage']['requested']} requested compared; "
                f"{part['coverage']['unmatched']} unmatched; {part['coverage']['unavailable']} unavailable in failed traces."
            ),
            f"Sheet: {described}."
            + (
                f" Thickness: {part['thickness_mm']:g} mm."
                if part["thickness_mm"]
                else " No thickness given."
            ),
            "",
            "| Dimension | Reference (mm) | Readings | Mean error (mm) | Spread, SD (mm) | Worst (mm) | Unmatched |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in part["rows"]:
            label = row["label"] + (f" (×{row['features']})" if row["features"] > 1 else "")
            mean = _signed(row["mean_error_mm"])
            if row["errors"] and abs(row["mean_error_mm"]) > report["caliper_uncertainty_mm"]:
                mean = f"**{mean}**"
            lines.append(
                f"| {label} | {row['expected_mm']:.2f} | {len(row['errors'])} | {mean}"
                f" | {_plain(row['spread_mm'])} | {_signed(row['worst_error_mm'])} | {row['missing'] or ''} |"
            )
        fit = part["fit"]
        if fit:
            scale, edge = fit["scale_percent"], fit["edge_offset_mm"]

            def between(value, unit, digits):
                spread = (
                    ""
                    if value["spread"] is None
                    else f" (SD {value['spread']:.{digits}f} between photos)"
                )
                return f"{value['mean']:+.{digits}f} {unit}{spread}"

            lines += [
                "",
                (
                    f"Fitted scale term {between(scale, '%', 3)}; edge term {between(edge, 'mm', 3)},"
                    " positive when boundaries are found outside the material."
                    f" In-sample residual: {fit['residual_mm']['mean']:.3f} mm RMS. "
                    "These diagnostic terms do not identify physical causes or predict held-out error."
                ),
            ]
        lines += [
            "",
            "| Photo | Edge blur (mm) | Sheet proportions (%) | Worst error (mm) | Result |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
        for photo in part["photos"]:
            if not photo["traced"]:
                lines.append(
                    f"| {photo['file']} | | | | Not traced: {photo['reason']} "
                    f"({photo['coverage']['unavailable']} dimensions unavailable) |"
                )
                continue
            errors = [
                s["measured_mm"] - s["expected_mm"]
                for s in photo["samples"]
                if s["measured_mm"] is not None
            ]
            missing = len(photo["samples"]) - len(errors)
            lines.append(
                f"| {photo['file']} | {photo['edge_blur_mm']:.3f} | {_plain(photo['sheet_proportions_percent'], 2)}"
                f" | {_signed(max(errors, key=abs, default=None))}"
                f" | {'Traced' if not missing else f'Traced; {missing} dimension(s) unmatched'} |"
            )
    return "\n".join(lines) + "\n"


# --- a rendered example -------------------------------------------------------------


# Camera tilts (degrees about x, y and the lens axis) and noise seeds of the example.
EXAMPLE_SHOTS = (((22.0, -9.0, 4.0), 7), ((9.0, 6.0, -12.0), 8), ((0.0, 0.0, 30.0), 9))


def write_example(folder, thickness=4.0, shots=EXAMPLE_SHOTS):
    """A folder to copy from: rendered photos of the test plate and a manifest holding
    its design dimensions. Rendered, so it shows the format and not real accuracy."""
    from tests import synthetic

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if any(folder.iterdir()):
        raise ManifestError(f"{folder.name} is not empty; choose a new folder for the example.")
    for index, (tilt, seed) in enumerate(shots, start=1):
        photo, _ = synthetic.render(tilt=tilt, seed=seed, thickness=thickness)
        (folder / f"plate-{index}.jpg").write_bytes(photo)
    (hx, hy), bore, slot = synthetic.SMALL_HOLES[-1], synthetic.BORE, synthetic.SLOT
    part = {
        "name": "plate",
        "photos": ["plate-*.jpg"],
        "thickness_mm": thickness,
        "measured": {
            "outline": [synthetic.PART["width"], synthetic.PART["height"]],
            "diameters": [bore[2], 6.0, 6.0, 6.0, 6.0],
            "openings": [[slot[2], slot[3]]],
            "radii": [synthetic.PART["corner"]] * 4,
            "centre_distances": [2 * hx, 2 * hy, round(2 * math.hypot(hx, hy), 3)],
        },
    }
    if not thickness:
        del part["thickness_mm"]
    manifest = {"sheet": "a4", "caliper_uncertainty_mm": CALIPER_UNCERTAINTY_MM, "parts": [part]}
    (folder / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, nargs="?", help=f"folder holding the photos and {MANIFEST}")
    parser.add_argument("--example", type=Path, metavar="FOLDER", help="write a rendered example folder and stop")
    parser.add_argument("--json", type=Path, metavar="FILE", help="also save the full report as JSON")
    parser.add_argument("--markdown", type=Path, metavar="FILE", help="also save the printed tables")
    parser.add_argument(
        "--no-snap",
        action="store_true",
        help="trace without design-intent snapping (equal radii, squared edges)",
    )
    options = parser.parse_args(arguments)
    try:
        if options.example:
            write_example(options.example)
            print(f"Wrote a rendered example to {options.example}. Run this script on that folder to see its report.")
            return 0
        if not options.folder:
            parser.error("give the folder that holds the photos, or --example FOLDER")
        report = run(options.folder, snap=not options.no_snap, progress=lambda text: print(text, file=sys.stderr))
    except ManifestError as exc:
        print(exc, file=sys.stderr)
        return 1
    text = render(report)
    print(text, end="")
    if options.markdown:
        options.markdown.write_text(text, encoding="utf-8")
    if options.json:
        options.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["summary"]["traced"] else 1


if __name__ == "__main__":
    sys.exit(main())
