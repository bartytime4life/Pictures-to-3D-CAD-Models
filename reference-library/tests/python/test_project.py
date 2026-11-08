import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import _helpers  # noqa: F401
from cadkit import params, project


class NewProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_scaffold(self):
        dest = self.dir / "bracket"
        created = project.new_project(dest, "Shelf bracket", today=date(2026, 11, 8))
        for folder in project.FOLDERS:
            self.assertTrue((dest / folder / "README.md").exists(), folder)
        for template, folder in project.PLACEMENT.items():
            target = dest / folder / template if folder else dest / template
            self.assertEqual(target.read_bytes(), (project.TEMPLATES / template).read_bytes())
        readme = (dest / "README.md").read_text()
        self.assertIn("# Shelf bracket", readme)
        self.assertIn("`shelf-bracket`", readme)
        self.assertIn("2026-11-08", readme)
        with (dest / "source-manifest.csv").open() as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(tuple(rows[0]), project.MANIFEST_COLUMNS)
        self.assertEqual(len(created), len(project.FOLDERS) + len(project.PLACEMENT) + 2)
        self.assertEqual(params.load_register(dest / "design-parameters.csv"), {})

    def test_existing_empty_directory_is_allowed(self):
        dest = self.dir / "empty"
        dest.mkdir()
        project.new_project(dest, "Knob")
        self.assertTrue((dest / "cad").is_dir())

    def test_refuses_non_empty_destination(self):
        dest = self.dir / "busy"
        dest.mkdir()
        (dest / "keep.txt").write_text("do not overwrite")
        with self.assertRaises(FileExistsError):
            project.new_project(dest, "Busy")
        self.assertEqual((dest / "keep.txt").read_text(), "do not overwrite")

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            project.new_project(self.dir / "x", "  ")
        with self.assertRaises(FileNotFoundError):
            project.new_project(self.dir / "y", "Y", templates=self.dir / "no-templates")
        self.assertEqual(project.slugify("  Ünïcode / Part #2 "), "unicode-part-2")
        self.assertEqual(project.slugify("!!!"), "project")


if __name__ == "__main__":
    unittest.main()
