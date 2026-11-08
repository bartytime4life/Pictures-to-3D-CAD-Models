"""Offline regressions for source-specific printer facts and inheritance."""

import json
import subprocess
from pathlib import Path

import pytest

from scripts import import_printers as importer


@pytest.fixture
def source_checkout(tmp_path, monkeypatch):
    """Commit tiny source fixtures so production integrity checks still run."""

    def create(vendors):
        root = tmp_path / "upstream"
        root.mkdir()
        base = root / "resources/profiles"
        for vendor, records in vendors.items():
            folder = base / vendor / "machine"
            folder.mkdir(parents=True)
            machine_list = []
            for record in records:
                filename = record["name"] + ".json"
                (folder / filename).write_text(json.dumps(record))
                if record.get("instantiation") == "true":
                    machine_list.append({"name": record["name"], "sub_path": "machine/" + filename})
            (base / (vendor + ".json")).write_text(
                json.dumps({"name": vendor, "machine_list": machine_list})
            )
        for arguments in (
            ["init", "-q"],
            ["add", "resources"],
            [
                "-c",
                "user.name=Catalog test",
                "-c",
                "user.email=catalog-test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
        ):
            subprocess.run(["git", "-C", str(root), *arguments], check=True)
        commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        monkeypatch.setattr(importer, "SOURCE_COMMIT", commit)
        return root

    return create


def common(width, depth=180, height=190):
    return {
        "type": "machine",
        "name": "fdm_machine_common",
        "instantiation": "false",
        "printer_technology": "FFF",
        "nozzle_diameter": ["0.4"],
        "printable_area": ["0x0", f"{width}x0", f"{width}x{depth}", f"0x{depth}"],
        "printable_height": str(height),
    }


def variant(name="Model 0.4", **changes):
    return {
        "type": "machine",
        "name": name,
        "instantiation": "true",
        "inherits": "fdm_machine_common",
        "printer_model": "Model",
        **changes,
    }


def test_vendor_scoping_and_variant_bounds_are_preserved(source_checkout):
    root = source_checkout(
        {
            "First": [
                common(110),
                variant(),
                variant("Model 0.6", nozzle_diameter=["0.6"], printable_height="170"),
            ],
            "Second": [common(260, 240, 300), variant()],
        }
    )
    catalog = importer.build_catalog(root)
    first, second = catalog["printers"]
    assert first["build_volume"] == {"x_mm": 110, "y_mm": 180, "z_mm": 190}
    assert second["build_volume"] == {"x_mm": 260, "y_mm": 240, "z_mm": 300}
    assert first["nozzle_diameters_mm"] == [0.4, 0.6]
    assert first["profiles"][1]["build_volume"]["z_mm"] == 170
    assert "/First/machine/" in first["profiles"][0]["inherited_source_urls"][0]
    assert "/Second/machine/" in second["profiles"][0]["inherited_source_urls"][0]


def test_missing_and_cyclic_inheritance_are_reported_not_guessed(source_checkout):
    root = source_checkout(
        {
            "Broken": [
                variant("Missing", inherits="not_present"),
                {"type": "machine", "name": "A", "inherits": "B"},
                {"type": "machine", "name": "B", "inherits": "A"},
                variant("Cyclic", inherits="A"),
            ]
        }
    )
    catalog = importer.build_catalog(root)
    assert catalog["printers"] == []
    assert {entry["reason"] for entry in catalog["skipped_profiles"]} == {
        "unresolved profile inheritance",
        "cyclic profile inheritance",
    }
    assert catalog["statistics"]["skipped_profiles"] == 2


def test_mixed_coordinate_serializations_preserve_exclusion_path(source_checkout):
    excluded = ["0x0,11x0,11x16,0x16,0x0"]
    root = source_checkout(
        {
            "Mixed": [
                common(270),
                variant(
                    printable_area="0x0,270x0,270x270,0x270",
                    bed_exclude_area=excluded,
                    nozzle_diameter=["0.4,0.4"],
                ),
            ]
        }
    )
    printer = importer.build_catalog(root)["printers"][0]
    assert printer["build_volume"] == {"x_mm": 270, "y_mm": 270, "z_mm": 190}
    assert printer["excluded_areas_mm"] == [[[0, 0], [11, 0], [11, 16], [0, 16], [0, 0]]]
    assert printer["exclusion_geometry_requires_review"] is True
    assert printer["nozzle_diameters_mm"] == [0.4]


def test_unverified_technology_and_invalid_geometry_are_not_admitted(source_checkout):
    root = source_checkout(
        {
            "UnsafeDefaults": [
                common(200),
                variant("Resin", printer_technology="SLA"),
                variant("Missing height", printable_height=""),
                variant("Nonfinite", printable_height="nan"),
            ]
        }
    )
    catalog = importer.build_catalog(root)
    assert catalog["statistics"]["printers"] == 0
    assert catalog["statistics"]["skipped_profiles"] == 3


def test_import_rejects_uncommitted_source_changes(source_checkout):
    root = source_checkout({"Stable": [common(200), variant()]})
    source = root / "resources/profiles/Stable/machine/Model 0.4.json"
    source.write_text(source.read_text().replace('"Model"', '"Changed Model"'))
    with pytest.raises(ValueError, match="uncommitted changes"):
        importer.build_catalog(root)


def test_bundled_facts_match_independently_checked_source_profiles():
    path = Path(__file__).resolve().parents[1] / "data/printers.json"
    catalog = json.loads(path.read_text())
    assert catalog["source"]["commit"] == "f55615d7488fe570942f5e25548b8ab9b30778d0"
    known = {
        "orca/bbl/bambu-lab-a1": (256, 256, 256),
        "orca/prusa/prusa-mk4s": (250, 210, 220),
        "orca/creality/creality-ender-3-v2": (220, 220, 250),
    }
    indexed = {printer["id"]: printer for printer in catalog["printers"]}
    for printer_id, expected in known.items():
        printer = indexed[printer_id]
        volume = printer["build_volume"]
        assert (volume["x_mm"], volume["y_mm"], volume["z_mm"]) == expected
        assert printer["default_nozzle_mm"] == 0.4
        assert printer["bed_shape"] == "rectangular"
        assert printer["features"]["enclosure"] is None
    assert catalog["statistics"]["profiles"] == 1106
    assert catalog["skipped_profiles"] == []
