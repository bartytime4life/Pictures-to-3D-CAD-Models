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
        self.assertEqual((r["manifold"], r["nonmanifold_vertices"]), (True, 0))
        self.assertEqual((r["euler_characteristic"], r["genus"]), (2, 0))

    def test_volume_is_translation_invariant(self):
        r = stl.analyze(stl.box((60, 30, 4), (1e5, -2e5, 3e5)))
        self.assertAlmostEqual(r["volume"], 7200.0, places=4)
        self.assertEqual(r["bbox_min"], [1e5, -2e5, 3e5])

    def test_open_mesh(self):
        r = stl.analyze(stl.box()[:-1])
        self.assertFalse(r["watertight"])
        self.assertEqual(r["boundary_edges"], 3)
        self.assertEqual(r["nonmanifold_vertices"], 0)  # each rim vertex still has one open fan
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
        self.assertTrue(r["watertight"])  # collapsed faces are excluded from topology

    def test_weld_tolerance(self):
        tris = stl.box()
        jitter = [tuple(tuple(c + 1e-9 if i == 0 else c for c in p) for i, p in enumerate(t)) for t in tris]
        self.assertTrue(stl.analyze(jitter, weld_tol=1e-6)["watertight"])
        with self.assertRaises(ValueError):
            stl.analyze(tris, weld_tol=0)
        with self.assertRaises(ValueError):
            stl.analyze([])

    def test_non_finite_coordinates_are_invalid_input(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            tris = stl.box()
            tris[3] = (tris[3][0], (bad, 0.0, 0.0), tris[3][2])
            with self.assertRaisesRegex(ValueError, "not finite"):
                stl.analyze(tris)


class Welding(unittest.TestCase):
    """Codex review of PR #2: welding must not depend on where points fall on a grid."""

    def test_points_straddling_a_cell_boundary_are_welded(self):
        # Shifted by half a tolerance cell, then jittered by 1e-9: rounding to a grid split
        # these into 10 boundary edges and two components.
        moved = [tuple((p[0] + 5e-7, p[1], p[2]) for p in t) for t in stl.box()]
        jitter = [tuple(((p[0] + 1e-9, p[1], p[2]) if i == 0 else p) for i, p in enumerate(t)) for t in moved]
        r = stl.analyze(jitter, weld_tol=1e-6)
        self.assertEqual((r["vertices"], r["boundary_edges"], r["components"]), (8, 0, 1))
        self.assertTrue(r["watertight"] and r["manifold"] and r["orientation_consistent"])
        self.assertEqual(r["genus"], 0)

    def test_weld_is_a_distance_not_a_cell(self):
        tris = stl.box()
        for gap, closed in ((0.9e-6, True), (1.1e-6, False), (5e-6, False)):
            # Move one corner of the first triangle off its neighbours by `gap` along a diagonal.
            a, b, c = tris[0]
            d = gap / 3 ** 0.5
            nudged = [((a[0] + d, a[1] + d, a[2] + d), b, c)] + tris[1:]
            self.assertEqual(stl.analyze(nudged, weld_tol=1e-6)["watertight"], closed, gap)

    def test_grid_offset_does_not_change_the_answer(self):
        base = stl.analyze(stl.box((60, 30, 4)))
        for offset in (0.0, 5e-7, 4.9999e-7, -5e-7, 123.4565):
            shifted = [tuple((p[0] + offset, p[1] + offset, p[2] + offset) for p in t) for t in stl.box((60, 30, 4))]
            r = stl.analyze(shifted)
            self.assertEqual((r["vertices"], r["boundary_edges"], r["components"], r["genus"]),
                             (base["vertices"], 0, 1, 0), offset)


class VertexManifold(unittest.TestCase):
    """Codex review of PR #2: shells that touch at one vertex are not a 2-manifold."""

    def test_boxes_touching_at_a_vertex(self):
        r = stl.analyze(stl.box() + stl.box(origin=(1, 1, 1)))
        self.assertEqual((r["boundary_edges"], r["nonmanifold_edges"]), (0, 0))
        self.assertTrue(r["watertight"])  # every edge has two faces...
        self.assertEqual(r["nonmanifold_vertices"], 1)  # ...but the shared corner has two fans
        self.assertFalse(r["manifold"])
        self.assertIsNone(r["genus"])

    def test_boxes_sharing_an_edge(self):
        r = stl.analyze(stl.box() + stl.box(origin=(1, 1, 0)))
        self.assertGreater(r["nonmanifold_edges"], 0)
        self.assertEqual(r["nonmanifold_vertices"], 2)
        self.assertFalse(r["watertight"] or r["manifold"])

    def test_separate_boxes_stay_manifold(self):
        r = stl.analyze(stl.box() + stl.box(origin=(1.5, 1.5, 1.5)))
        self.assertTrue(r["manifold"])
        self.assertEqual((r["components"], r["genus"]), (2, 0))


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


def _ascii_facet(*vertex_lines: str) -> str:
    return "facet normal 0 0 1\nouter loop\n" + "".join(f"vertex {v}\n" for v in vertex_lines) + "endloop\nendfacet\n"


class AsciiStructure(unittest.TestCase):
    """Review of Revision 4: a malformed ASCII facet must be invalid input, never a passing mesh."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.path = self.dir / "m.stl"
        box = self.dir / "box.stl"
        stl.write_stl_ascii(box, stl.box((10, 10, 10)))
        self.box = box.read_text(encoding="ascii").replace("endsolid cadkit\n", "")

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, extra: str):
        self.path.write_text(self.box + extra + "endsolid cadkit\n", encoding="ascii")
        return stl.read_stl(self.path)

    def test_unparsable_coordinates_are_rejected(self):
        # The old reader skipped tokens it could not match, so the next facet's vertices
        # regrouped into this one: a box plus a "nan nan nan" facet reported status: pass.
        with self.assertRaises(ValueError):
            self.read(_ascii_facet("nan nan nan", "inf 0 0", "1,5 2 3"))  # the reviewer's file
        for coords in ("1,5 0 0", "1D+01 0 0", "0 0 zero", "0x1 0 0"):
            with self.assertRaises(ValueError, msg=coords):
                self.read(_ascii_facet(coords, coords, coords))
            with self.assertRaises(ValueError, msg=coords):
                self.read(_ascii_facet("0 0 0", coords, "10 10 0"))

    def test_non_finite_coordinates_are_rejected_like_binary(self):
        for coords in ("nan 0 0", "inf 0 0", "0 -Infinity 0"):
            with self.assertRaisesRegex(ValueError, "not finite", msg=coords):
                self.read(_ascii_facet(coords, "0 10 0", "10 10 0"))

    def test_every_facet_has_exactly_three_vertices(self):
        for vertices in (("0 0 0", "0 10 0"), ("0 0 0", "0 10 0", "10 10 0", "10 0 0"), ("0 0 0 0", "0 10 0", "10 10 0"),
                         ("0 0", "0 10 0", "10 10 0")):
            with self.assertRaises(ValueError, msg=vertices):
                self.read(_ascii_facet(*vertices))

    def test_vertex_count_is_three_per_facet(self):
        with self.assertRaisesRegex(ValueError, "endfacet"):  # truncated inside the last facet
            self.read("facet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 0 10 0\nvertex 10 10 0\n")
        with self.assertRaisesRegex(ValueError, "outside a facet"):
            self.read("vertex 0 0 0\nvertex 0 10 0\nvertex 10 10 0\n")

    def test_well_formed_files_still_read(self):
        self.assertEqual(len(self.read("")), 12)
        tris = self.read(_ascii_facet("  1.5e+1\t-0 +2", "0 1E1 0", "1000 .5 5."))
        self.assertEqual(tris[-1], ((15.0, 0.0, 2.0), (0.0, 10.0, 0.0), (1000.0, 0.5, 5.0)))
        two_solids = self.box + "endsolid cadkit\nsolid second\n" + _ascii_facet("0 0 0", "1 0 0", "0 1 0")
        self.path.write_text(two_solids + "endsolid second\n", encoding="ascii")
        self.assertEqual(len(stl.read_stl(self.path)), 13)


class DegenerateTopology(unittest.TestCase):
    """Review of Revision 4: which degenerate faces the topology checks exclude (cadkit/README.md)."""

    def test_collapsed_faces_are_excluded_from_topology(self):
        r = stl.analyze(stl.box() + [((0, 0, 0), (0, 0, 0), (1, 1, 1))])  # two corners weld together
        self.assertEqual(r["degenerate_triangles"], 1)
        self.assertEqual((r["boundary_edges"], r["nonmanifold_edges"], r["components"]), (0, 0, 1))
        self.assertTrue(r["watertight"] and r["manifold"])

    def test_slivers_are_degenerate_and_keep_their_edges(self):
        # Three distinct, collinear vertices: zero area, so the face is degenerate, but it
        # still has three welded corners and its edges take part in the topology checks.
        r = stl.analyze(stl.box() + [((0, 0, 0), (0.5, 0, 0), (1, 0, 0))])
        self.assertEqual(r["degenerate_triangles"], 1)
        self.assertEqual(r["vertices"], 9)
        self.assertEqual((r["boundary_edges"], r["nonmanifold_edges"]), (2, 1))
        self.assertFalse(r["watertight"])
        self.assertIsNone(r["genus"])


class WeldToleranceBounds(unittest.TestCase):
    """Review of Revision 4: the weld tolerance must be a usable positive finite length."""

    def test_non_finite_or_non_positive_tolerances_are_rejected(self):
        for tol in (float("inf"), float("nan"), 0.0, -1e-6):
            with self.assertRaisesRegex(ValueError, "weld_tol must be a positive finite number", msg=tol):
                stl.analyze(stl.box(), weld_tol=tol)

    def test_a_tolerance_too_small_for_the_coordinates_is_invalid_input(self):
        # 10 / 1e-320 overflows the welding grid; it used to raise OverflowError.
        with self.assertRaisesRegex(ValueError, "too small"):
            stl.analyze(stl.box((10, 10, 10)), weld_tol=1e-320)
        with self.assertRaisesRegex(ValueError, "too small"):
            stl.analyze(stl.box(origin=(1e303, 0, 0)), weld_tol=1e-6)
        self.assertTrue(stl.analyze(stl.box(origin=(1e9, 0, 0)), weld_tol=1e-6)["watertight"])

    def test_a_huge_tolerance_is_bounded_instead_of_overflowing(self):
        r = stl.analyze(stl.box(), weld_tol=stl.MAX_WELD_TOL)  # welds every corner into one point
        self.assertEqual((r["vertices"], r["degenerate_triangles"]), (1, 12))
        self.assertFalse(r["watertight"])
        with self.assertRaisesRegex(ValueError, "no larger than"):  # 1e200 ** 2 used to raise OverflowError
            stl.analyze(stl.box(), weld_tol=1e200)


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
