#!/usr/bin/env python3
"""Extract a factual, offline printer catalog from a pinned OrcaSlicer checkout.

This original importer does not copy G-code, macros, profile descriptions, or
filament/print recipes. It uses only Python's standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path
from urllib.parse import quote

SOURCE_COMMIT = "f55615d7488fe570942f5e25548b8ab9b30778d0"
SOURCE_REPOSITORY = "https://github.com/SoftFever/OrcaSlicer"
RETRIEVED_ON = "2026-11-08"


def numbers(value: object) -> list[float]:
    """Read finite numeric profile values; percentages are not absolute lengths."""
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    values = [
        part
        for item in raw_values
        for part in (item.split(",") if isinstance(item, str) else [item])
    ]
    result = []
    for item in values:
        if isinstance(item, bool):
            return []
        try:
            number = float(item)
        except (ValueError, TypeError):
            return []
        if not math.isfinite(number):
            return []
        result.append(number)
    return result


def one_number(value: object) -> float | None:
    values = numbers(value)
    if not values or len(set(values)) != 1:
        return None
    return values[0]


def profile_bool(value: object) -> bool | None:
    if value in (True, "true", "1", 1):
        return True
    if value in (False, "false", "0", 0):
        return False
    return None


def points(value: object) -> list[list[float]]:
    if value is None:
        return []
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list):
        raise TypeError("area is not a point list")
    result = []
    for point in value:
        if not isinstance(point, str):
            raise TypeError("point is not text")
        for part in point.split(","):
            pair = part.strip().split("x")
            xy = numbers(pair)
            if len(xy) != 2:
                raise ValueError("invalid XY point")
            result.append(xy)
    return result


def area(points_mm: list[list[float]]) -> float:
    if not points_mm:
        return 0.0
    return abs(
        sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(points_mm, points_mm[1:] + points_mm[:1])
        )
        / 2
    )


def geometry(profile: dict) -> dict:
    polygon = points(profile.get("printable_area"))
    if len(polygon) < 3 or area(polygon) <= 0:
        raise ValueError("missing or degenerate printable area")
    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    width, depth = max(xs) - min(xs), max(ys) - min(ys)
    height = one_number(profile.get("printable_height"))
    if min(width, depth) <= 0 or height is None or height <= 0:
        raise ValueError("missing positive build dimensions")
    unique = {tuple(p) for p in polygon}
    corners = {
        (min(xs), min(ys)),
        (min(xs), max(ys)),
        (max(xs), min(ys)),
        (max(xs), max(ys)),
    }
    shape = "polygon"
    if unique == corners and math.isclose(area(polygon), width * depth):
        shape = "rectangular"
    elif len(unique) >= 12 and math.isclose(width, depth, rel_tol=0.01):
        center = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
        radii = [math.hypot(x - center[0], y - center[1]) for x, y in unique]
        if max(radii) - min(radii) <= max(radii) * 0.01:
            shape = "circular"
    excluded = points(profile.get("bed_exclude_area"))
    # Orca also uses a single 0x0 point as an empty placeholder. Nontrivial
    # compound paths are retained in source order, not guessed into rectangles.
    exclusions = [excluded] if len({tuple(p) for p in excluded}) >= 3 else []
    return {
        "bed_shape": shape,
        "build_volume": {
            "x_mm": round(width, 6),
            "y_mm": round(depth, 6),
            "z_mm": height,
        },
        "printable_area_mm": polygon,
        "excluded_areas_mm": exclusions,
        "exclusion_geometry_requires_review": bool(exclusions),
    }


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "printer"


def build_catalog(checkout: Path) -> dict:
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != SOURCE_COMMIT:
        raise ValueError(f"checkout must be pinned to {SOURCE_COMMIT}; found {actual}")
    # Reject modified source files: a recorded commit must describe the bytes read.
    changed = subprocess.check_output(
        [
            "git",
            "-C",
            str(checkout),
            "status",
            "--porcelain",
            "--",
            "resources/profiles",
            "LICENSE.txt",
        ],
        text=True,
    ).strip()
    if changed:
        raise ValueError("source profile checkout has uncommitted changes")

    base = checkout / "resources/profiles"
    records: dict[tuple[str, str], tuple[Path, dict]] = {}
    manufacturers = {}
    registered: set[Path] = set()
    for index_path in sorted(base.glob("*.json")):
        index = json.loads(index_path.read_text())
        vendor = index_path.stem
        manufacturers[vendor] = index.get("name", vendor)
        for entry in index.get("machine_list", []):
            registered.add(base / vendor / entry["sub_path"])
    manufacturers["BBL"] = "Bambu Lab"
    for path in sorted(base.glob("*/machine/*.json")):
        record = json.loads(path.read_text())
        key = (path.parent.parent.name, record.get("name", path.stem))
        if key in records:
            raise ValueError(f"duplicate source profile name: {key}")
        records[key] = (path, record)

    @cache
    def resolve(vendor: str, name: str, trail: tuple = ()) -> tuple[dict, tuple]:
        key = (vendor, name)
        if key in trail:
            raise ValueError("cyclic profile inheritance")
        if key not in records:
            raise ValueError("unresolved profile inheritance")
        path, child = records[key]
        parent_name = child.get("inherits")
        if parent_name:
            parent, sources = resolve(vendor, parent_name, trail + (key,))
            merged = {**parent, **child}
        else:
            merged, sources = dict(child), ()
        return merged, sources + (path,)

    def source_url(path: Path) -> str:
        return f"{SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/" + quote(
            path.relative_to(checkout).as_posix()
        )

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    skipped = []
    candidates = 0
    for (vendor, name), (path, child) in sorted(records.items()):
        if (
            child.get("type") != "machine"
            or profile_bool(child.get("instantiation")) is not True
            or path not in registered
        ):
            continue
        candidates += 1
        try:
            profile, sources = resolve(vendor, name)
            model_name = profile.get("printer_model")
            if not isinstance(model_name, str) or not model_name:
                raise ValueError("missing printer model")
            model = records.get((vendor, model_name), (None, {}))[1]
            technology = profile.get("printer_technology", model.get("machine_tech"))
            if technology not in ("FFF", "FDM"):
                raise ValueError("unverified FFF technology")
            nozzle_values = sorted(set(numbers(profile.get("nozzle_diameter"))))
            if not nozzle_values or any(n <= 0 for n in nozzle_values):
                raise ValueError("missing positive nozzle diameter")
            dimensions = geometry(profile)
            minimum = one_number(profile.get("min_layer_height"))
            maximum = one_number(profile.get("max_layer_height"))
            if minimum is not None and minimum <= 0:
                minimum = None
            if maximum is not None and maximum <= 0:
                maximum = None
            structure = profile.get("printer_structure")
            if structure in (None, "undefine", "undefined", ""):
                structure = None
            extruders = profile.get("extruder_type", [])
            if isinstance(extruders, str):
                extruders = [extruders]
            groups[(vendor, model_name)].append(
                {
                    "id": "orca:" + path.relative_to(base).as_posix(),
                    "name": name,
                    "nozzle_diameters_mm": nozzle_values,
                    **dimensions,
                    "min_layer_height_mm": minimum,
                    "max_layer_height_mm": maximum,
                    "printer_structure": structure,
                    "extruder_types": extruders,
                    "single_extruder_multi_material_profile": profile_bool(
                        profile.get("single_extruder_multi_material")
                    ),
                    "chamber_temperature_control_profile": profile_bool(
                        profile.get("support_chamber_temp_control")
                    ),
                    "source_url": source_url(path),
                    "inherited_source_urls": [source_url(p) for p in sources[:-1]],
                }
            )
        except (ValueError, TypeError) as exc:
            skipped.append({"source": path.relative_to(checkout).as_posix(), "reason": str(exc)})

    printers = []
    used_ids: set[str] = set()
    for (vendor, model_name), profiles in sorted(groups.items()):
        profiles.sort(key=lambda p: (0.4 not in p["nozzle_diameters_mm"], p["name"]))
        default = profiles[0]
        nozzles = sorted({n for p in profiles for n in p["nozzle_diameters_mm"]})
        printer_id = f"orca/{slug(vendor)}/{slug(model_name)}"
        if printer_id in used_ids:
            digest = hashlib.sha256(f"{vendor}/{model_name}".encode()).hexdigest()[:8]
            printer_id += "-" + digest
        used_ids.add(printer_id)
        printers.append(
            {
                "id": printer_id,
                "name": model_name,
                "manufacturer": manufacturers.get(vendor, vendor),
                "technology": "FFF",
                **{
                    field: default[field]
                    for field in (
                        "bed_shape",
                        "build_volume",
                        "printable_area_mm",
                        "excluded_areas_mm",
                        "exclusion_geometry_requires_review",
                    )
                },
                "nozzle_diameters_mm": nozzles,
                "default_nozzle_mm": 0.4 if 0.4 in nozzles else nozzles[0],
                "features": {
                    "enclosure": None,
                    "heated_bed": None,
                    "automatic_bed_leveling": None,
                    "multimaterial": None,
                },
                "profiles": profiles,
            }
        )
    printers.sort(key=lambda p: (p["manufacturer"].casefold(), p["name"].casefold()))
    return {
        "schema_version": 1,
        "source": {
            "name": "OrcaSlicer machine profiles",
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "license": "AGPL-3.0 (upstream repository; see PRINTER_SOURCES.md)",
            "license_url": f"{SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/LICENSE.txt",
            "retrieved_on": RETRIEVED_ON,
        },
        "statistics": {
            "printers": len(printers),
            "manufacturers": len({p["manufacturer"] for p in printers}),
            "profiles": sum(len(p["profiles"]) for p in printers),
            "candidate_profiles": candidates,
            "skipped_profiles": len(skipped),
            "bed_shapes": dict(Counter(p["bed_shape"] for p in printers)),
        },
        "printers": printers,
        "skipped_profiles": skipped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_checkout", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/printers.json"))
    args = parser.parse_args()
    catalog = build_catalog(args.source_checkout.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(catalog["statistics"], indent=2))


if __name__ == "__main__":
    main()
