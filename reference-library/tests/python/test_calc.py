import json
import math
import unittest

import _helpers  # noqa: F401
from cadkit import calc

GOLD = json.loads(_helpers.GOLDEN.read_text(encoding="utf-8"))


class GoldenValues(unittest.TestCase):
    """The handbook's worked numbers, reproduced from calculation-results.json."""

    def test_planar_scale_and_length(self):
        scale = calc.planar_scale(50, 1000)
        self.assertEqual(scale, GOLD["scale_mm_per_pixel"])
        self.assertEqual(calc.scaled_length(640, scale), GOLD["feature_length_mm"])

    def test_uncertainty(self):
        r = calc.ratio_uncertainty(640, 2, 1000, 2, 50, 0.05)
        self.assertEqual(r["u"], GOLD["standard_uncertainty_mm_independent_small_error_model"])
        self.assertAlmostEqual(r["u"], 0.123, places=3)  # handbook: uL ~ 0.123 mm
        self.assertAlmostEqual(r["expanded_k2"], 2 * r["u"])
        self.assertAlmostEqual(r["relative"], r["u"] / r["length"])

    def test_tessellation(self):
        n = calc.min_segments(10, 0.02)
        self.assertEqual(n, GOLD["minimum_circle_segments"])
        self.assertEqual(n, 50)
        self.assertEqual(calc.chord_error(10, n), GOLD["actual_chord_error_mm"])
        self.assertEqual(calc.chord_error(10, n - 1), GOLD["previous_segment_count_error_mm"])
        self.assertLessEqual(calc.chord_error(10, n), 0.02)
        self.assertGreater(calc.chord_error(10, n - 1), 0.02)

    def test_gear(self):
        g = calc.gear_pair(2, 20, 40)
        self.assertEqual([g["d1"], g["d2"]], GOLD["gear_pitch_diameters_mm"])
        self.assertEqual(g["center_distance"], GOLD["gear_nominal_center_distance_mm"])
        self.assertEqual(g["speed_ratio"], GOLD["gear_output_input_speed_ratio"])
        self.assertEqual(g["warnings"], [])

    def test_aspect(self):
        a = calc.aspect_check(50, 90, 400, 675)
        self.assertEqual(a["known_aspect"], GOLD["calibration_check_known_aspect"])
        self.assertEqual(a["image_aspect"], GOLD["calibration_check_image_aspect"])
        self.assertEqual(a["squat_percent"], GOLD["calibration_check_squat_percent"])
        self.assertEqual(a["scale_h"], GOLD["calibration_check_scale_mm_per_pixel_horizontal"])
        self.assertEqual(a["scale_v"], GOLD["calibration_check_scale_mm_per_pixel_vertical"])
        self.assertEqual(a["stretch_percent"], GOLD["calibration_check_vertical_stretch_percent"])
        self.assertEqual(len(a["warnings"]), 1)

    def test_depth(self):
        self.assertEqual(calc.depth_factor(500, 60), GOLD["off_plane_depth_factor"])
        self.assertEqual(40.0 * calc.depth_factor(500, 60), GOLD["off_plane_corrected_size_mm"])
        self.assertEqual(list(calc.depth_factor_range(350, 800, 30, 80)), GOLD["off_plane_factor_range"])

    def test_camera(self):
        f = calc.focal_px_from_35mm(26, 4000, 3000)
        self.assertEqual(f, GOLD["camera_focal_length_px"])
        self.assertEqual(calc.camera_distance(f, 100, 500), GOLD["camera_distance_mm"])
        self.assertAlmostEqual(calc.FULL_FRAME_DIAGONAL_MM, 43.2666, places=4)

    def test_label(self):
        r = calc.rounding_uncertainty(3.25, "in", 2)
        self.assertEqual(r["value_mm"], GOLD["label_mm"])
        self.assertEqual(r["half_interval_mm"], GOLD["label_rounding_half_interval_mm"])
        self.assertEqual(r["standard_uncertainty_mm"], GOLD["label_rounding_standard_uncertainty_mm"])

    def test_coating(self):
        self.assertEqual(calc.coating_loss(0.08), GOLD["coated_slot_width_loss_mm"])
        self.assertEqual(calc.coating_loss(0.08, faces=1), 0.08)


class Behaviour(unittest.TestCase):
    def test_invalid_inputs_raise(self):
        bad = [
            lambda: calc.planar_scale(0, 10),
            lambda: calc.planar_scale(10, -1),
            lambda: calc.planar_scale(float("nan"), 1),
            lambda: calc.min_segments(1, 1),
            lambda: calc.min_segments(1, 0),
            lambda: calc.chord_error(1, 2),
            lambda: calc.chord_error(1, 3.5),
            lambda: calc.depth_factor(100, -100),
            lambda: calc.depth_factor_range(800, 350, 30, 80),
            lambda: calc.rounding_uncertainty(1, "furlong", 2),
            lambda: calc.rounding_uncertainty(1, "in", -1),
            lambda: calc.gear_pair(2, 0, 40),
            lambda: calc.wind_power(1.225, 1, 5, 0.6),
            lambda: calc.clearance_series(5, 0.1, 0.1, 0),
            lambda: calc.clearance_series(1, -2, 0.1, 1),
            lambda: calc.coating_loss(-0.1),
            lambda: calc.weakest_evidence([]),
            lambda: calc.weakest_evidence(["guessed"]),
            lambda: calc.suggest_unit_conversion(0, 10),
            lambda: calc.chord_report(10),
            lambda: calc.chord_report(10, error=0.1, segments=8),
        ]
        for fn in bad:
            with self.assertRaises(ValueError):
                fn()

    def test_scale_warnings(self):
        self.assertEqual(calc.scale_report(50, 1000, 640)["warnings"], [])
        r = calc.scale_report(50, 150, 640)
        self.assertEqual(len(r["warnings"]), 2)
        self.assertIn("200 px", r["warnings"][0])
        self.assertIn("4.3x", r["warnings"][1])
        self.assertNotIn("feature_length_mm", calc.scale_report(50, 1000))

    def test_chord_report(self):
        r = calc.chord_report(10, error=0.02)
        self.assertEqual(r["segments"], 50)
        self.assertAlmostEqual(r["flat_to_flat_diameter_mm"], 20 * math.cos(math.pi / 50))
        self.assertEqual(calc.chord_report(10, segments=8)["segments"], 8)
        self.assertEqual(len(calc.chord_report(100, error=0.0001)["warnings"]), 1)
        self.assertEqual(calc.min_segments(1, 0.9999), 3)

    def test_tessellation_formula_is_tight_over_a_sweep(self):
        for radius in (0.5, 2.5, 10, 75):
            for error in (0.001, 0.01, 0.05, 0.2):
                if error >= radius:
                    continue
                n = calc.min_segments(radius, error)
                self.assertLessEqual(calc.chord_error(radius, n), error * (1 + 1e-12))
                if n > 3:
                    self.assertGreater(calc.chord_error(radius, n - 1), error)

    def test_depth_report_and_range(self):
        self.assertEqual(calc.depth_report(500, 60)["warnings"], [])
        r = calc.depth_report(500, 150, 40)
        self.assertAlmostEqual(r["corrected_size_mm"], 52.0)
        self.assertEqual(len(r["warnings"]), 1)
        self.assertAlmostEqual(calc.depth_factor(500, -50), 0.9)  # in front of the plane: smaller
        low, high = calc.depth_factor_range(400, 600, -20, 40)
        self.assertAlmostEqual(low, (400 - 20) / 400)
        self.assertAlmostEqual(high, (400 + 40) / 400)

    def test_label_other_units(self):
        r = calc.rounding_uncertainty(82.6, "mm", 1)
        self.assertAlmostEqual(r["half_interval_mm"], 0.05)
        self.assertAlmostEqual(r["standard_uncertainty_mm"], 0.05 / math.sqrt(3))
        self.assertAlmostEqual(calc.rounding_uncertainty(8, "cm", 0)["half_interval_mm"], 5.0)

    def test_gear_undercut_warning(self):
        g = calc.gear_pair(1, 12, 40)
        self.assertAlmostEqual(g["undercut_limit_teeth"], 2 / math.sin(math.radians(20)) ** 2)
        self.assertAlmostEqual(g["undercut_limit_teeth"], 17.097, places=3)
        self.assertEqual(len(g["warnings"]), 1)
        self.assertIn("z1 = 12", g["warnings"][0])

    def test_wind(self):
        self.assertAlmostEqual(calc.wind_power(1.225, 1.0, 10.0, 0.4), 245.0)
        self.assertEqual(calc.wind_power(1.225, 1.0, 0.0, 0.4), 0.0)
        self.assertAlmostEqual(calc.wind_power(1.2, 1, 1, calc.BETZ_LIMIT), 0.6 * 16 / 27)
        self.assertEqual(len(calc.wind_report(1.225, 1, 5, 0.3)["warnings"]), 1)

    def test_clearance_series(self):
        rows = calc.clearance_series(5, 0.10, 0.10, 5)
        self.assertEqual([r["diametral"] for r in rows], [0.1, 0.2, 0.3, 0.4, 0.5])
        self.assertEqual([r["hole_diameter"] for r in rows], [5.1, 5.2, 5.3, 5.4, 5.5])
        self.assertEqual([r["radial"] for r in rows], [0.05, 0.1, 0.15, 0.2, 0.25])
        neg = calc.clearance_series(5, -0.1, 0.05, 3)  # interference rows are allowed
        self.assertEqual([r["diametral"] for r in neg], [-0.1, -0.05, 0.0])

    def test_evidence_propagation(self):
        self.assertEqual(calc.weakest_evidence(["measured", "measured"]), "measured")
        self.assertEqual(calc.weakest_evidence(["measured", "image-derived"]), "image-derived")
        self.assertEqual(calc.weakest_evidence(["image-derived", "inferred", "measured"]), "inferred")
        self.assertEqual(calc.weakest_evidence(["measured", "unknown"]), "unknown")
        self.assertEqual(calc.weakest_evidence(["Measured", "Image derived"]), "image-derived")
        self.assertEqual(calc.weakest_evidence(["confirmed"]), "measured")
        self.assertEqual(calc.weakest_evidence(["estimated", "measured"]), "image-derived")
        for alias in ("nominal", "proposed", "synthetic"):
            self.assertEqual(calc.weakest_evidence(["measured", alias]), "inferred")
        self.assertEqual(calc.weakest_evidence(["proposed", "unknown"]), "unknown")

    def test_unit_suggestions(self):
        best = calc.suggest_unit_conversion(0.06, 60)[0]
        self.assertEqual((best["unit"], best["factor"]), ("m", 1000.0))
        self.assertAlmostEqual(best["corrected_mm"], 60.0)
        self.assertEqual(calc.suggest_unit_conversion(2.3622, 60)[0]["unit"], "in")
        self.assertEqual(calc.suggest_unit_conversion(6, 60)[0]["unit"], "cm")
        self.assertEqual(calc.suggest_unit_conversion(60, 60)[0]["factor"], 1.0)
        self.assertEqual(calc.suggest_unit_conversion(1524, 60)[0]["unit"], "1/in")
        ranked = calc.suggest_unit_conversion(123, 45)
        self.assertEqual(len(ranked), 9)
        self.assertEqual(ranked, sorted(ranked, key=lambda c: c["relative_error"]))


if __name__ == "__main__":
    unittest.main()


class ReviewRegressions(unittest.TestCase):
    """Inputs that used to escape as OverflowError / ZeroDivisionError."""

    def test_tiny_chord_error_is_a_value_error(self):
        with self.assertRaises(ValueError):
            calc.min_segments(10, 1e-17)

    def test_absurd_decimal_count_is_a_value_error(self):
        with self.assertRaises(ValueError):
            calc.rounding_uncertainty(1, "in", 400)
        self.assertAlmostEqual(calc.rounding_uncertainty(1, "IN", 12)["half_interval_mm"], 0.5e-12 * 25.4)
