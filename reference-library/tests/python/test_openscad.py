"""Real exports, provenance, invalid handoffs and preservation of earlier work."""
import csv
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import _helpers
from cadkit import openscad, scad


class Parameters(unittest.TestCase):
    def test_invalid_handoffs_fail_before_render(self):
        for changes in ({"plate_width": 6}, {"hole_spacing": 4}, {"chord_error": 1e-14},
                        {"plate_thickness": None}, {"plate_length": "60; cube(100);"}):
            register = openscad.default_register("plate")
            for name,value in changes.items():
                register[name] = replace(register[name], value=value)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                openscad.geometry("plate", register)
        for changes in ({"clearance_count": 2.5}, {"clearance_count": 101},
                        {"end_wall": 1}, {"notch_size": 20}):
            register = openscad.default_register("coupon")
            for name,value in changes.items():
                register[name] = replace(register[name], value=value)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                openscad.geometry("coupon", register)

    def test_wrong_units_unknown_fields_and_missing_evidence_are_rejected(self):
        for change in ("units", "extra", "source", "missing"):
            register = openscad.default_register("plate")
            if change == "units":
                register["plate_length"] = replace(register["plate_length"],unit="in")
            elif change == "source":
                register["plate_length"] = replace(register["plate_length"],source_or_rationale="")
            elif change == "extra":
                register["not_a_model_parameter"] = replace(register["plate_length"],parameter_id="not_a_model_parameter")
            else:
                del register["plate_length"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                openscad.geometry("plate", register)

    def test_defaults_are_synthetic_and_match_register_contract(self):
        self.assertEqual(list(openscad.catalog()["csv_columns"]),list(openscad.params.COLUMNS))
        for model in ("plate", "coupon"):
            register = openscad.default_register(model)
            self.assertTrue(all(p.evidence_class == "inferred" for p in register.values()))
            self.assertTrue(all(p.source_or_rationale for p in register.values()))
            self.assertGreater(openscad.geometry(model,register)["volume"],0)


@unittest.skipUnless(_helpers.HAS_OPENSCAD, "OpenSCAD is not installed")
class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_actual_models_and_hashes(self):
        for model in ("plate", "coupon"):
            dest = self.root/model
            record = openscad.build(model,dest)
            self.assertEqual(record["status"],"passed")
            self.assertTrue(all(c["status"] == "pass" for c in record["checks"]))
            self.assertTrue(record["mesh"]["watertight"])
            self.assertEqual(record["mesh"]["components"],1)
            saved = json.loads((dest/"build.json").read_text())
            self.assertEqual(saved,record)
            for name,digest in record["outputs_sha256"].items():
                self.assertEqual(hashlib.sha256((dest/name).read_bytes()).hexdigest(),digest)
            with (dest/"validation-results.csv").open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows),len(record["checks"]))

    def test_custom_csv_changes_geometry_and_complete_revision(self):
        first = openscad.build("plate",self.root/"first")
        register = openscad.default_register("plate")
        register["plate_length"] = replace(register["plate_length"],value=80,evidence_class="measured",
                                            source_or_rationale="Synthetic test fixture simulating a reading; no actual part")
        path = self.root/"custom.csv"
        path.write_text(openscad.register_csv(register))
        second = openscad.build("plate",self.root/"second",path)
        self.assertEqual(second["mesh"]["extents"],[80,30,4])
        self.assertNotEqual(first["model_revision_sha256"],second["model_revision_sha256"])
        self.assertEqual(second["parameters"]["plate_length"]["evidence_class"],"measured")
        self.assertEqual((self.root/"second/parameters.csv").read_bytes(),path.read_bytes())

    def test_existing_build_and_failed_build_leave_data_intact(self):
        dest = self.root/"existing"
        openscad.build("plate",dest)
        before = {p.name:p.read_bytes() for p in dest.iterdir()}
        with self.assertRaises(FileExistsError):
            openscad.build("coupon",dest)
        self.assertEqual(before,{p.name:p.read_bytes() for p in dest.iterdir()})
        with mock.patch.object(scad,"render",side_effect=RuntimeError("fixture render failed")):
            with self.assertRaises(RuntimeError):
                openscad.build("plate",self.root/"failed")
        self.assertFalse((self.root/"failed").exists())
        self.assertFalse(list(self.root.glob(".cadkit-build-*")))
        self.assertEqual(before,{p.name:p.read_bytes() for p in dest.iterdir()})

    def test_mesh_mismatch_does_not_publish_a_build(self):
        with mock.patch.object(openscad,"check_mesh",return_value=({},[{"feature_id":"fixture","status":"fail"}])):
            with self.assertRaisesRegex(RuntimeError,"fixture"):
                openscad.build("plate",self.root/"wrong")
        self.assertFalse((self.root/"wrong").exists())

    def test_parameter_bytes_are_captured_once_for_render_and_receipt(self):
        path = self.root/"params.csv"
        original = openscad.register_csv(openscad.default_register("plate")).encode()
        path.write_bytes(original)
        read_bytes = Path.read_bytes
        reads = []

        def snapshot(file):
            if file == path:
                reads.append(file)
                if len(reads) > 1:
                    raise AssertionError("Input CSV was read twice; concurrent edits could change the receipt")
            return read_bytes(file)

        with mock.patch.object(Path,"read_bytes",snapshot):
            record = openscad.build("plate",self.root/"snapshot",path)
        self.assertEqual(len(reads),1)
        self.assertEqual((self.root/"snapshot/parameters.csv").read_bytes(),original)
        self.assertEqual(record["input_sha256"]["parameters"],hashlib.sha256(original).hexdigest())


if __name__ == "__main__":
    unittest.main()
