"""Personal native builds must not travel with the portable teaching library."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _helpers


class Packaging(unittest.TestCase):
    def test_personal_builds_are_excluded_but_handbook_and_synthetic_starters_remain(self):
        spec = importlib.util.spec_from_file_location("make_dist",_helpers.ROOT/"scripts/make-dist.py")
        dist = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dist)
        with tempfile.TemporaryDirectory() as folder:
            top = Path(folder)
            library = top/"reference-library"
            for relative in ("output/my-measured-part/parameters.csv","output/my-measured-part/model.stl",".venv/lib/private.py",".cache/file",
                             "output/pdf/pictures-to-printable-cad.pdf","examples/openscad-starter/plate/model.stl",
                             "assets/data/openscad-models.json"):
                path = library/relative
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text("fixture")
            with mock.patch.multiple(dist,TOP=top,LIB_DIR=library):
                names = {p.relative_to(library).as_posix() for p in dist.library_files()}
            self.assertEqual(names,{"output/pdf/pictures-to-printable-cad.pdf",
                                    "examples/openscad-starter/plate/model.stl","assets/data/openscad-models.json"})


if __name__ == "__main__":
    unittest.main()
