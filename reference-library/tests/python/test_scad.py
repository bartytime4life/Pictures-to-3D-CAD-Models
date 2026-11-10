import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _helpers
from cadkit import calc, openscad, scad, stl

PLATE = _helpers.EXAMPLES / "two-hole-plate.scad"
COUPON = _helpers.EXAMPLES / "clearance-coupon.scad"


def coupon_geometry(pin=5.0, start=0.10, step=0.10, count=5, min_wall=2.0, end_wall=3.0,
                    chord_error=0.02, label_band=0.0):
    """Python mirror of clearance-coupon.scad's layout arithmetic."""
    holes = [pin + start + i * step for i in range(count)]
    segs = [max(16, calc.min_segments(d / 2, chord_error)) for d in holes]
    poly_r = [d / 2 / math.cos(math.pi / n) for d, n in zip(holes, segs)]
    max_r = max(poly_r)
    pitch = 2 * max_r + min_wall
    length = 2 * (end_wall + max_r) + (count - 1) * pitch
    width = 2 * (min_wall + max_r) + label_band
    centres = [(end_wall + max_r + i * pitch, min_wall + max_r) for i in range(count)]
    return holes, segs, poly_r, length, width, centres


class Defines(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(scad.format_define("a", 60.0), "a=60.0")
        self.assertEqual(scad.format_define("a", 3), "a=3")
        self.assertEqual(scad.format_define("a", 0.1), "a=0.1")
        self.assertEqual(scad.format_define("flag", True), "flag=true")
        self.assertEqual(scad.format_define("mode", 'en"grave\\'), 'mode="en\\"grave\\\\"')
        for bad in (lambda: scad.format_define("1x", 1), lambda: scad.format_define("a b", 1),
                    lambda: scad.format_define("a", float("inf")), lambda: scad.format_define("a", None)):
            with self.assertRaises(ValueError):
                bad()
        with self.assertRaises(TypeError):
            scad.format_define("a", [1, 2])

    def test_missing_executable(self):
        with mock.patch.dict(os.environ, {"CADKIT_OPENSCAD": "/nonexistent/openscad"}):
            self.assertIsNone(scad.find_openscad())
            with self.assertRaises(FileNotFoundError):
                scad.render(PLATE, Path(tempfile.gettempdir()) / "never.stl")


class Discovery(unittest.TestCase):
    def test_directory_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.dict(os.environ, {"CADKIT_OPENSCAD": directory}):
            self.assertIsNone(scad.find_openscad())
            self.assertEqual(openscad.doctor()["status"], "missing")

    @unittest.skipUnless(os.name == "posix", "POSIX execute permission semantics")
    def test_non_executable_file_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "openscad"
            executable.write_text("not an executable")
            executable.chmod(0o644)
            with mock.patch.dict(os.environ, {"CADKIT_OPENSCAD": str(executable)}):
                self.assertIsNone(scad.find_openscad())

    def test_unrelated_executable_is_not_ready(self):
        with mock.patch.dict(os.environ, {"CADKIT_OPENSCAD": sys.executable}):
            self.assertIsNotNone(scad.find_openscad())
            report = openscad.doctor()
            self.assertEqual(report["status"], "error")
            self.assertIsNone(report["version"])

    def test_version_recognizes_openscad_output_on_stderr(self):
        result = subprocess.CompletedProcess([], 0, "", "OpenSCAD version 2021.01\n")
        with mock.patch.object(scad.subprocess, "run", return_value=result):
            self.assertEqual(scad.version("openscad-test"), "2021.01")


class RenderSafety(unittest.TestCase):
    """Exercise failure paths without depending on an installed OpenSCAD."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "part.scad"
        self.source.write_text("cube([1, 2, 3]);")
        self.output = self.dir / "part.stl"
        self.original = b"previous good export"
        self.output.write_bytes(self.original)

    def assert_preserved(self):
        self.assertEqual(self.output.read_bytes(), self.original)
        self.assertEqual(set(self.dir.iterdir()), {self.source, self.output})

    def test_invalid_defines_preserve_previous_export_without_launching(self):
        with mock.patch.object(scad.subprocess, "run") as run:
            for defines in ({"invalid-name": 1}, {"width": None}, {"width": float("nan")}):
                with self.subTest(defines=defines), self.assertRaises(ValueError):
                    scad.render(self.source, self.output, defines, executable="openscad-test")
                self.assert_preserved()
            run.assert_not_called()

    def test_source_cannot_be_used_as_output(self):
        original = self.source.read_bytes()
        with mock.patch.object(scad.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "different files"):
                scad.render(self.source, self.dir / "." / self.source.name, executable="openscad-test")
            alias = self.dir / "source-alias.scad"
            alias.symlink_to(self.source)
            with self.assertRaisesRegex(ValueError, "different files"):
                scad.render(self.source, alias, executable="openscad-test")
            run.assert_not_called()
        self.assertEqual(self.source.read_bytes(), original)

    def test_failure_error_log_and_empty_output_never_accept_stale_export(self):
        for returncode, stderr, data in (
                (1, "render failed", b"partial candidate"),
                (0, "  ERROR: invalid geometry", b"partial candidate"),
                (0, "", b"")):
            def renderer(command, **kwargs):
                Path(command[command.index("-o") + 1]).write_bytes(data)
                return subprocess.CompletedProcess(command, returncode, "", stderr)

            with self.subTest(returncode=returncode, stderr=stderr, data=data):
                with mock.patch.object(scad.subprocess, "run", side_effect=renderer), \
                        mock.patch.object(scad, "version", return_value="test"):
                    result = scad.render(self.source, self.output, executable="openscad-test")
                self.assertFalse(result.ok)
                self.assertEqual(result.output, self.output)
                if returncode == 0:
                    self.assertTrue(result.errors)
                self.assert_preserved()

    def test_timeout_and_launch_error_clean_staging_and_preserve_export(self):
        for error in (subprocess.TimeoutExpired("openscad-test", 1), OSError("launch failed")):
            def renderer(command, **kwargs):
                Path(command[command.index("-o") + 1]).write_bytes(b"partial candidate")
                raise error

            with self.subTest(error=error), mock.patch.object(scad.subprocess, "run", side_effect=renderer):
                with self.assertRaises(type(error)):
                    scad.render(self.source, self.output, executable="openscad-test")
            self.assert_preserved()

    def test_success_replaces_export_and_records_actual_command(self):
        def renderer(command, **kwargs):
            staged = Path(command[command.index("-o") + 1])
            self.assertEqual(staged.parent, self.output.parent)
            self.assertEqual(staged.suffix, ".stl")
            self.assertNotEqual(staged, self.output)
            self.assertEqual(self.output.read_bytes(), self.original)
            staged.write_bytes(b"new export")
            return subprocess.CompletedProcess(command, 0, "", "WARNING: test warning")

        with mock.patch.object(scad.subprocess, "run", side_effect=renderer), \
                mock.patch.object(scad, "version", return_value="test"):
            result = scad.render(self.source, self.output, {"width": 12}, executable="openscad-test")
        self.assertTrue(result.ok)
        self.assertEqual(self.output.read_bytes(), b"new export")
        self.assertIn("width=12", result.command)
        self.assertIn("binstl", result.command)
        self.assertEqual(result.warnings, ["WARNING: test warning"])
        self.assertFalse(Path(result.command[result.command.index("-o") + 1]).exists())
        self.assertEqual(set(self.dir.iterdir()), {self.source, self.output})

    def test_version_probe_failure_is_unknown(self):
        for error in (subprocess.TimeoutExpired("openscad-test", 30), FileNotFoundError("missing")):
            with self.subTest(error=error), mock.patch.object(scad.subprocess, "run", side_effect=error):
                self.assertIsNone(scad.version("openscad-test"))
        with mock.patch.object(scad.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "failed")):
            self.assertIsNone(scad.version("openscad-test"))


@unittest.skipUnless(_helpers.HAS_OPENSCAD, "OpenSCAD is not installed")
class Render(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, source, name, **defines):
        result = scad.render(source, self.dir / name, defines)
        self.assertTrue(result.ok, result.stderr)
        return stl.read_stl(result.output), result

    def test_plate_default(self):
        tris, result = self.render(PLATE, "plate.stl")
        self.assertTrue(result.version)
        r = stl.analyze(tris)
        self.assertTrue(r["watertight"] and r["orientation_consistent"])
        self.assertEqual((r["components"], r["genus"]), (1, 2))
        self.assertEqual(r["extents"], [60.0, 30.0, 4.0])
        n = max(16, calc.min_segments(2.5, 0.02))
        expected = 60 * 30 * 4 - 2 * 4 * 0.5 * n * 2.5 ** 2 * math.sin(2 * math.pi / n)
        self.assertAlmostEqual(r["volume"], expected, delta=expected * 1e-5)

    def test_plate_overrides_and_failed_assertion(self):
        tris, _ = self.render(PLATE, "long.stl", plate_length=80.0, hole_spacing=60.0)
        self.assertAlmostEqual(stl.analyze(tris)["extents"][0], 80.0, places=5)
        bad = scad.render(PLATE, self.dir / "bad.stl", {"hole_spacing": 70.0})
        self.assertFalse(bad.ok)
        self.assertTrue(any("Assertion" in e for e in bad.errors))
        self.assertFalse(bad.output.exists())

    def test_coupon_layout_and_polygon_compensation(self):
        tris, result = self.render(COUPON, "coupon.stl")
        r = stl.analyze(tris)
        holes, segs, poly_r, length, width, centres = coupon_geometry()
        self.assertTrue(r["watertight"] and r["orientation_consistent"])
        self.assertEqual((r["components"], r["genus"]), (1, len(holes)))
        self.assertAlmostEqual(r["extents"][0], length, places=4)
        self.assertAlmostEqual(r["extents"][1], width, places=4)
        self.assertAlmostEqual(r["extents"][2], 4.0, places=6)
        # Every hole vertex lies on its enlarged radius, so the polygon's flats
        # (inscribed circle) equal the intended hole diameter.
        interior = {v for t in tris for v in t if 0.01 < v[0] < length - 0.01 and 0.01 < v[1] < width - 0.01}
        for (cx, cy), d, n, rp in zip(centres, holes, segs, poly_r):
            ring = [v for v in interior if math.hypot(v[0] - cx, v[1] - cy) < rp + 0.05]
            self.assertEqual(len(ring), 2 * n)
            for v in ring:
                self.assertAlmostEqual(math.hypot(v[0] - cx, v[1] - cy), rp, delta=2e-5)
            self.assertAlmostEqual(rp * math.cos(math.pi / n), d / 2, places=12)
        notch = 0.5 * 2.0 ** 2 * 4.0
        hole_volume = sum(0.5 * n * rp * rp * math.sin(2 * math.pi / n) * 4.0 for n, rp in zip(segs, poly_r))
        expected = length * width * 4.0 - hole_volume - notch
        self.assertAlmostEqual(r["volume"], expected, delta=expected * 1e-5)
        self.assertIn("COUPON length=", result.stderr + result.stdout)

    def test_coupon_overrides(self):
        tris, _ = self.render(COUPON, "small.stl", pin_diameter=3.0, clearance_count=3, clearance_step=0.15)
        r = stl.analyze(tris)
        _, _, _, length, _, _ = coupon_geometry(pin=3.0, count=3, step=0.15)
        self.assertEqual(r["genus"], 3)
        self.assertAlmostEqual(r["extents"][0], length, places=4)

    def test_coupon_engraved_labels(self):
        result = scad.render(COUPON, self.dir / "engraved.stl", {"label_mode": "engrave"})
        if not result.ok and "font" in (result.stderr + result.stdout).lower():
            self.skipTest("no usable font for OpenSCAD text()")
        self.assertTrue(result.ok, result.stderr)
        r = stl.analyze(stl.read_stl(result.output))
        self.assertTrue(r["watertight"])
        self.assertEqual((r["components"], r["genus"]), (1, 5))
        self.assertAlmostEqual(r["extents"][1], coupon_geometry(label_band=3.0 + 2.0)[4], places=4)

    def test_coupon_assertions(self):
        for defines in ({"notch_size": 9.0}, {"end_wall": 1.0}, {"label_mode": "paint"}, {"clearance_count": 0}):
            result = scad.render(COUPON, self.dir / "bad.stl", defines)
            self.assertFalse(result.ok, defines)


if __name__ == "__main__":
    unittest.main()
