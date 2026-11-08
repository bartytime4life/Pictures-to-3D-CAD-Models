import struct
import tempfile
import unittest
from pathlib import Path

import _helpers  # noqa: F401
from cadkit import stl


class Analyze(unittest.TestCase):
    def test_unit_cube(self):
        r = stl.analyze(stl.box())
        self.assertEqual(r["triangles"], 12)
        self.assertEqual(r["vertices"], 8)
        self.assertAlmostEqual(r["volume"], 1.0)
        self.assertAlmostEqual(r["surface_area"], 6.0)
        self.assertEqual(r["extents"], [1.0, 1.0, 1.0])
        self.assertTrue(r["watertight"])
        self.assertTrue(r["orientation_consistent"])
        self.assertEqual((r["components"], r["boundary_edges"], r["nonmanifold_edges"]), (1, 0, 0))
        self.assertEqual((r["euler_characteristic"], r["genus"]), (2, 0))

    def test_volume_is_translation_invariant(self):
        r = stl.analyze(stl.box((60, 30, 4), (1e5, -2e5, 3e5)))
        self.assertAlmostEqual(r["volume"], 7200.0, places=4)
        self.assertEqual(r["bbox_min"], [1e5, -2e5, 3e5])

    def test_open_mesh(self):
        r = stl.analyze(stl.box()[:-1])
        self.assertFalse(r["watertight"])
        self.assertEqual(r["boundary_edges"], 3)
        self.assertIsNone(r["genus"])

    def test_flipped_triangle_breaks_orientation(self):
        tris = stl.box()
        a, b, c = tris[0]
        tris[0] = (a, c, b)
        r = stl.analyze(tris)
        self.assertTrue(r["watertight"])
        self.assertFalse(r["orientation_consistent"])

    def test_inverted_mesh_has_negative_volume(self):
        r = stl.analyze([(a, c, b) for a, b, c in stl.box()])
        self.assertAlmostEqual(r["volume"], -1.0)
        self.assertTrue(r["orientation_consistent"])

    def test_two_components(self):
        r = stl.analyze(stl.box() + stl.box(origin=(5, 0, 0)))
        self.assertEqual(r["components"], 2)
        self.assertAlmostEqual(r["volume"], 2.0)
        self.assertEqual(r["genus"], 0)

    def test_nonmanifold_edge(self):
        tris = stl.box() + [((0, 0, 0), (1, 0, 0), (0.5, -1, 0.5))]
        r = stl.analyze(tris)
        self.assertGreater(r["nonmanifold_edges"], 0)
        self.assertFalse(r["watertight"])

    def test_degenerate_triangles_counted(self):
        tris = stl.box() + [((0, 0, 0), (0, 0, 0), (1, 1, 1))]
        r = stl.analyze(tris)
        self.assertEqual(r["degenerate_triangles"], 1)
        self.assertTrue(r["watertight"])  # degenerate faces are excluded from topology

    def test_weld_tolerance(self):
        tris = stl.box()
        jitter = [tuple(tuple(c + 1e-9 if i == 0 else c for c in p) for i, p in enumerate(t)) for t in tris]
        self.assertTrue(stl.analyze(jitter, weld_tol=1e-6)["watertight"])
        with self.assertRaises(ValueError):
            stl.analyze(tris, weld_tol=0)
        with self.assertRaises(ValueError):
            stl.analyze([])


class ReadWrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_ascii_round_trip(self):
        path = self.dir / "cube.stl"
        stl.write_stl_ascii(path, stl.box((2, 3, 4)))
        r = stl.analyze(stl.read_stl(path))
        self.assertAlmostEqual(r["volume"], 24.0)

    def test_binary_round_trip(self):
        path = self.dir / "cube-bin.stl"
        stl.write_stl_binary(path, stl.box((2, 3, 4)))
        self.assertEqual(path.stat().st_size, 84 + 50 * 12)
        self.assertAlmostEqual(stl.analyze(stl.read_stl(path))["volume"], 24.0, places=5)

    def test_binary_with_solid_header_is_detected_as_binary(self):
        path = self.dir / "tricky.stl"
        stl.write_stl_binary(path, stl.box(), header=b"solid looks like ascii but is binary")
        self.assertEqual(len(stl.read_stl(path)), 12)

    def test_ascii_scientific_notation(self):
        path = self.dir / "sci.stl"
        path.write_text(
            "solid s\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1E+0 0 0\nvertex 0 1.0e0 -0.0\n"
            "endloop\nendfacet\nendsolid s\n")
        self.assertEqual(stl.read_stl(path)[0][1], (1.0, 0.0, 0.0))

    def test_garbage_rejected(self):
        path = self.dir / "bad.stl"
        path.write_bytes(b"not a mesh at all, just text")
        with self.assertRaises(ValueError):
            stl.read_stl(path)
        path.write_text("solid s\nvertex 0 0 0\nvertex 1 0 0\nendsolid s\n")
        with self.assertRaises(ValueError):
            stl.read_stl(path)


class UnitHints(unittest.TestCase):
    def test_metres(self):
        hints = stl.unit_hints([0.06, 0.03, 0.004], expected_mm=60)
        self.assertTrue(any("file units are m" in h for h in hints))
        self.assertTrue(any("metres" in h for h in hints))

    def test_inches_doubled(self):
        hints = stl.unit_hints([1524, 762, 101.6], expected_mm=60)
        self.assertIn("as if it were in", hints[0])

    def test_agreement_and_near_miss(self):
        self.assertIn("agrees", stl.unit_hints([60.1, 30, 4], expected_mm=60)[0])
        self.assertIn("differs", stl.unit_hints([62, 30, 4], expected_mm=60)[0])
        self.assertIn("does not match", stl.unit_hints([300, 30, 4], expected_mm=60)[0])

    def test_without_expectation(self):
        self.assertEqual(stl.unit_hints([60, 30, 4]), [])
        self.assertTrue(stl.unit_hints([5000, 1, 1]))
        self.assertTrue(stl.unit_hints([5, 1, 1]))


if __name__ == "__main__":
    unittest.main()
