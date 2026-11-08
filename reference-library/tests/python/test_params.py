import tempfile
import unittest
from pathlib import Path

import _helpers
from cadkit import params

HEADER = ",".join(params.COLUMNS) + "\n"


class Register(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, body: str) -> Path:
        path = self.dir / "p.csv"
        path.write_text(HEADER + body, encoding="utf-8")
        return path

    def test_plate_register(self):
        reg = params.load_register(_helpers.EXAMPLES / "plate-parameters.csv")
        self.assertEqual(reg["plate_length"].value, 60.0)
        self.assertEqual(reg["chord_error"].value, 0.02)
        self.assertEqual(reg["hole_spacing"].unit, "mm")
        self.assertEqual(params.validate(reg, ["plate_length", "min_wall"]), [])

    def test_template_has_only_the_example_row(self):
        self.assertEqual(params.load_register(_helpers.TEMPLATES / "design-parameters.csv"), {})

    def test_blank_means_unknown_not_zero(self):
        reg = params.load_register(self.write("depth,,mm,unknown,not visible,,,,\n"))
        self.assertIsNone(reg["depth"].value)
        self.assertIn("depth: required parameter has no value (unknown)", params.validate(reg, ["depth"]))
        with self.assertRaises(ValueError):
            params.to_openscad_defines(reg, {"depth": "depth"})
        self.assertEqual(params.to_openscad_defines(reg), {})

    def test_strings_and_comments(self):
        reg = params.load_register(self.write(
            "# comment row,,,,,,,,\nlabel_mode,engrave,1,proposed,style choice,2026-11-08,,coupon,\n"))
        self.assertEqual(list(reg), ["label_mode"])
        self.assertEqual(reg["label_mode"].value, "engrave")

    def test_duplicates_raise(self):
        with self.assertRaises(ValueError):
            params.load_register(self.write("a,1,mm,measured,,,,,\na,2,mm,measured,,,,,\n"))

    def test_missing_columns_raise(self):
        path = self.dir / "short.csv"
        path.write_text("parameter_id,value\na,1\n")
        with self.assertRaises(ValueError):
            params.load_register(path)

    def test_validation_problems(self):
        reg = params.load_register(self.write(
            "bad-id,1,mm,measured,,,,,\nnounit,2,,measured,,,,,\nclass,3,mm,guessed,,,,,\n"
            "when,4,mm,measured,,08/11/2026,,,\nself,5,mm,measured,,,self,,\n"))
        problems = " | ".join(params.validate(reg, ["absent"]))
        for text in ("bad-id: id must", "nounit: numeric value needs a unit", "class: unknown evidence class",
                     "when: decided_on", "self: a parameter cannot supersede itself", "absent: required parameter is missing"):
            self.assertIn(text, problems)

    def test_defines_mapping(self):
        reg = params.load_register(_helpers.EXAMPLES / "plate-parameters.csv")
        defines = params.to_openscad_defines(reg, {"plate_length": "plate_length", "hole_diameter": "d"})
        self.assertEqual(defines, {"plate_length": 60.0, "d": 5.0})
        with self.assertRaises(KeyError):
            params.to_openscad_defines(reg, {"nope": "nope"})
        self.assertIn("min_wall", params.to_openscad_defines(reg))


if __name__ == "__main__":
    unittest.main()
