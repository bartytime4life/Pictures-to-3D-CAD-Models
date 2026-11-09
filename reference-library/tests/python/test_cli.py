import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import _helpers
from cadkit import __version__, stl
from cadkit.cli import main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


def run_json(*argv):
    code, out, err = run(*argv, "--json")
    return code, json.loads(out)


class NumericCommands(unittest.TestCase):
    def test_scale(self):
        code, r = run_json("scale", "--known-mm", "50", "--reference-px", "1000", "--feature-px", "640")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(r["feature_length_mm"], 32.0)
        code, out, _ = run("scale", "--known-mm", "50", "--reference-px", "100", "--feature-px", "640")
        self.assertIn("warning: Reference spans 100 px", out)

    def test_uncertainty(self):
        code, r = run_json("uncertainty", "--p", "640", "--up", "2", "--pref", "1000", "--upref", "2",
                           "--lref", "50", "--ulref", "0.05")
        self.assertAlmostEqual(r["u"], 0.12296, places=5)

    def test_chord(self):
        self.assertEqual(run_json("chord", "--radius", "10", "--error", "0.02")[1]["segments"], 50)
        self.assertAlmostEqual(run_json("chord", "--radius", "10", "--segments", "50")[1]["chord_error_mm"], 0.019733, places=6)

    def test_depth_with_ranges(self):
        code, r = run_json("depth", "--z", "500", "--delta", "60", "--size", "40",
                           "--z-range", "350", "800", "--delta-range", "30", "80")
        self.assertAlmostEqual(r["corrected_size_mm"], 44.8)
        self.assertAlmostEqual(r["factor_range"][0], 1.0375)

    def test_camera_aspect_label_coating_gear_wind(self):
        self.assertEqual(round(run_json("camera", "--f35", "26", "--width-px", "4000", "--height-px", "3000",
                                        "--length-mm", "100", "--length-px", "500")[1]["camera_distance_mm"]), 601)
        self.assertAlmostEqual(run_json("aspect", "--known", "50", "90", "--pixels", "400", "675")[1]["squat_percent"], 6.25)
        self.assertAlmostEqual(run_json("label", "--value", "3.25", "--unit", "in", "--decimals", "2")[1]["half_interval_mm"], 0.127)
        self.assertAlmostEqual(run_json("coating", "--per-face", "0.08")[1]["width_loss_mm"], 0.16)
        self.assertEqual(run_json("gear", "--module", "2", "--teeth", "20", "40")[1]["center_distance"], 60.0)
        r = run_json("wind", "--diameter", "1", "--v", "5", "--cp", "0.3")[1]
        self.assertAlmostEqual(r["area_m2"], 0.785398, places=6)
        self.assertAlmostEqual(r["power_w"], 0.5 * 1.225 * r["area_m2"] * 125 * 0.3)

    def test_coupon_units_evidence(self):
        rows = run_json("coupon")[1]["rows"]
        self.assertEqual([row["hole_diameter"] for row in rows], [5.1, 5.2, 5.3, 5.4, 5.5])
        r = run_json("units", "--observed", "0.06", "--expected-mm", "60")[1]
        self.assertEqual(r["candidates"][0]["unit"], "m")
        code, out, _ = run("units", "--observed", "60", "--expected-mm", "60")
        self.assertIn("best: file units are mm", out)
        self.assertEqual(run_json("evidence", "measured", "proposed")[1]["weakest"], "inferred")

    def test_homography_inline_and_file(self):
        pairs = [[[0, 0], [0, 0]], [[1000, 0], [50, 0]], [[1000, 800], [50, 40]], [[0, 800], [0, 40]]]
        code, r = run_json("homography", "--points", json.dumps(pairs), "--at", "500", "400")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(r["local_scale_u"], 0.05)
        self.assertEqual(len(r["warnings"]), 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pts.json"
            path.write_text(json.dumps({"src": [p[0] for p in pairs], "dst": [p[1] for p in pairs]}))
            code, out, _ = run("homography", "--points", str(path))
            self.assertIn("RMS residual", out)

    def test_invalid_input_exit_code(self):
        code, _, err = run("chord", "--radius", "1", "--error", "2")
        self.assertEqual(code, 2)
        self.assertIn("error:", err)
        self.assertEqual(run("homography", "--points", "[not json")[0], 2)
        self.assertEqual(run("evidence", "guessed")[0], 2)

    def test_version(self):
        self.assertEqual(run_json("version")[1]["cadkit"], __version__)


class FileCommands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_meshcheck_pass_and_fail(self):
        good = self.dir / "good.stl"
        stl.write_stl_binary(good, stl.box((60, 30, 4)))
        code, r = run_json("meshcheck", str(good), "--expect-mm", "60")
        self.assertEqual((code, r["status"], r["components"]), (0, "pass", 1))
        self.assertIn("agrees", r["unit_hints"][0])
        open_mesh = self.dir / "open.stl"
        stl.write_stl_ascii(open_mesh, stl.box()[:-2])
        self.assertEqual(run("meshcheck", str(open_mesh))[0], 1)
        self.assertEqual(run("meshcheck", str(open_mesh), "--allow-open")[0], 0)
        tiny = self.dir / "metres.stl"
        stl.write_stl_ascii(tiny, stl.box((0.06, 0.03, 0.004)))
        code, out, _ = run("meshcheck", str(tiny), "--expect-mm", "60")
        self.assertIn("file units are m", out)
        self.assertEqual(run("meshcheck", str(self.dir / "missing.stl"))[0], 2)

    def test_meshcheck_fails_a_vertex_pinch(self):
        pinch = self.dir / "pinch.stl"
        stl.write_stl_binary(pinch, stl.box() + stl.box(origin=(1, 1, 1)))
        code, r = run_json("meshcheck", str(pinch))
        self.assertEqual((code, r["status"], r["watertight"], r["manifold"]), (1, "fail", True, False))
        code, out, _ = run("meshcheck", str(pinch))
        self.assertIn("manifold: False (non-manifold vertices 1)", out)
        self.assertIn("through-holes (genus): n/a", out)
        code, r = run_json("meshcheck", str(pinch), "--allow-open")
        self.assertEqual((code, r["status"]), (0, "fail"))

    def test_meshcheck_rejects_non_finite_coordinates(self):
        tris = stl.box()
        tris[0] = ((float("inf"), 0.0, 0.0), tris[0][1], tris[0][2])
        path = self.dir / "inf.stl"
        stl.write_stl_binary(path, tris)
        code, _, err = run("meshcheck", str(path))
        self.assertEqual(code, 2)  # invalid input, not a traceback
        self.assertIn("not finite", err)

    def test_params(self):
        code, out, _ = run("params", str(_helpers.EXAMPLES / "plate-parameters.csv"), "--require", "plate_length")
        self.assertEqual(code, 0)
        self.assertIn("7 parameters; 0 problems", out)
        code, out, _ = run("params", str(_helpers.EXAMPLES / "plate-parameters.csv"), "--require", "absent")
        self.assertEqual(code, 1)

    def test_new_project(self):
        dest = self.dir / "proj"
        code, r = run_json("new-project", str(dest), "--name", "Test part")
        self.assertEqual(code, 0)
        self.assertTrue((dest / "PROJECT-BRIEF.md").exists())
        self.assertEqual(run("new-project", str(dest), "--name", "Again")[0], 2)


# The homography from the review: a trapezoid imaged in perspective, with the plane's
# vanishing line between image rows 50 and 300 (w changes sign there).
VANISHING = json.dumps({"src": [[200, 800], [800, 800], [700, 400], [300, 400], [500, 600], [350, 650]],
                        "dst": [[-60, 0], [60, 0], [93.333333, 266.666667], [-93.333333, 266.666667], [0, 80],
                                [-38.181818, 54.545455]]})


class InvalidInputExitCodes(unittest.TestCase):
    """Review of Revision 4: invalid input exits 2 with one ``error:`` line, never a traceback (exit 1)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def assertInvalid(self, *argv, says=""):
        code, out, err = run(*argv)
        self.assertEqual(code, 2, f"{argv}: {err}")
        self.assertTrue(err.startswith("error: ") and err.count("\n") == 1, f"{argv}: {err!r}")
        self.assertIn(says, err)
        self.assertEqual(out, "")

    def test_malformed_point_json(self):
        for spec in ("[1,2,3,4]", "[[[0,0]],[[1,0]],[[1,1]],[[0,1]]]", '{"src":[[0,0],[1,0],[1,1],[0,1]],"dst":5}',
                     '{"src":null,"dst":null}', '{"src":[[0,0],[1,0],[1,1],[0,1]]}', "[null,null,null,null]",
                     "[[null,[0,0]],[[1,0],[1,0]],[[1,1],[1,1]],[[0,1],[0,1]]]",
                     '[[["a","b"],[0,0]],[[1,0],[1,0]],[[1,1],[1,1]],[[0,1],[0,1]]]', "5", '"text"'):
            self.assertInvalid("homography", "--points", spec)
        self.assertInvalid("homography", "--points", "[1,2,3,4]", says="[[u, v], [x, y]]")
        path = self.dir / "null.json"
        path.write_text("null", encoding="utf-8")
        self.assertInvalid("homography", "--points", str(path))

    def test_points_file_with_a_byte_order_mark(self):
        path = self.dir / "pts.json"
        pairs = [[[0, 0], [0, 0]], [[1000, 0], [50, 0]], [[1000, 800], [50, 40]], [[0, 800], [0, 40]]]
        path.write_text(json.dumps(pairs), encoding="utf-8-sig")
        self.assertEqual(run("homography", "--points", str(path))[0], 0)

    def test_file_system_errors(self):
        self.assertInvalid("meshcheck", str(self.dir), says="directory")
        afile = self.dir / "box.stl"
        stl.write_stl_binary(afile, stl.box())
        self.assertInvalid("new-project", str(afile / "sub"), "--name", "x")
        self.assertInvalid("params", str(self.dir))

    def test_unreadable_file(self):
        path = self.dir / "locked.stl"
        stl.write_stl_binary(path, stl.box())
        path.chmod(0)
        try:
            if os.access(path, os.R_OK):
                self.skipTest("running with privileges that ignore file permissions")
            self.assertInvalid("meshcheck", str(path), says="ermission")
        finally:
            path.chmod(0o600)

    def test_overflow(self):
        self.assertInvalid("uncertainty", "--p", "1", "--up", "1e200", "--pref", "1", "--upref", "1",
                           "--lref", "1", "--ulref", "1", says="too large")
        self.assertInvalid("wind", "--area", "1", "--v", "1e110", "--cp", "0.3", says="too large")
        self.assertInvalid("wind", "--diameter", "1e200", "--v", "1", "--cp", "0.3")
        box = self.dir / "box.stl"
        stl.write_stl_binary(box, stl.box((10, 10, 10)))
        self.assertInvalid("meshcheck", str(box), "--weld-tol", "1e-320", says="too small")
        for tol in ("inf", "nan", "0", "-1"):
            self.assertInvalid("meshcheck", str(box), "--weld-tol", tol, says="weld_tol")

    def test_ascii_stl_with_a_garbage_facet(self):
        good = self.dir / "box.stl"
        stl.write_stl_ascii(good, stl.box((10, 10, 10)))
        bad = self.dir / "box-plus-nan.stl"
        bad.write_text(good.read_text(encoding="ascii").replace(
            "endsolid", "facet normal 0 0 1\nouter loop\nvertex nan nan nan\nvertex 1 0 0\nvertex 0 1 0\n"
            "endloop\nendfacet\nendsolid"), encoding="ascii")
        self.assertEqual(run("meshcheck", str(good))[0], 0)
        self.assertInvalid("meshcheck", str(bad), says="not finite")

    def test_sliver_fails_the_mesh_check(self):
        path = self.dir / "sliver.stl"
        stl.write_stl_binary(path, stl.box() + [((0, 0, 0), (0.5, 0, 0), (1, 0, 0))])
        code, r = run_json("meshcheck", str(path))
        self.assertEqual((code, r["status"], r["degenerate_triangles"]), (1, "fail", 1))

    def test_homography_query_point(self):
        code, _, err = run("homography", "--points", VANISHING, "--at", "nan", "nan", "--json")
        self.assertEqual(code, 2, err)
        self.assertInvalid("homography", "--points", VANISHING, "--at", "inf", "0", says="finite")
        self.assertInvalid("homography", "--points", VANISHING, "--at", "500", "50", says="vanishing line")
        code, r = run_json("homography", "--points", VANISHING, "--at", "500", "600")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(r["mapped"][1], 80.0, places=4)

    def test_wind_needs_a_positive_diameter(self):
        for diameter in ("-2", "0", "nan"):
            self.assertInvalid("wind", "--diameter", diameter, "--v", "5", "--cp", "0.3", says="diameter")

    def test_gear_pressure_angle_range(self):
        for angle in ("95", "180", "90", "0", "-20"):
            self.assertInvalid("gear", "--module", "2", "--teeth", "20", "40", "--pressure-angle", angle,
                               says="pressure")
        self.assertEqual(run_json("gear", "--module", "2", "--teeth", "20", "40", "--pressure-angle", "25")[0], 0)

    def test_depth_ranges_come_together(self):
        base = ("depth", "--z", "500", "--delta", "60")
        self.assertInvalid(*base, "--z-range", "350", "800", says="--delta-range")
        self.assertInvalid(*base, "--delta-range", "30", "80", says="--z-range")


if __name__ == "__main__":
    unittest.main()
