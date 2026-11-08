import math
import random
import unittest

import _helpers  # noqa: F401
from cadkit import homography as hg

# A synthetic image -> plane mapping with real perspective terms (pixels -> mm).
H_TRUE = [[0.052, 0.004, -12.0], [-0.003, 0.049, -8.0], [1.2e-5, -2.0e-5, 1.0]]
GRID = [(u, v) for u in (100, 900, 1700, 2500) for v in (150, 1100, 2050)]


def mapped(points, H=H_TRUE):
    return [hg.apply(H, p) for p in points]


class Fit(unittest.TestCase):
    def assertMatrixClose(self, a, b, rel=1e-8):
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                self.assertLessEqual(abs(x - y), rel * max(1.0, abs(y)), msg=f"{a} vs {b}")

    def test_recovers_known_h_with_four_points(self):
        src = [(100, 150), (2500, 150), (2500, 2050), (100, 2050)]
        H = hg.fit(src, mapped(src))
        self.assertMatrixClose(H, H_TRUE, rel=1e-9)
        self.assertEqual(H[2][2], 1.0)

    def test_recovers_known_h_with_many_points(self):
        H = hg.fit(GRID, mapped(GRID))
        self.assertMatrixClose(H, H_TRUE, rel=1e-9)
        _, rms = hg.residuals(H, GRID, mapped(GRID))
        self.assertLess(rms, 1e-9)

    def test_noisy_points_give_noise_level_residuals(self):
        rng = random.Random(20261108)
        dst = [(x + rng.gauss(0, 0.05), y + rng.gauss(0, 0.05)) for x, y in mapped(GRID)]
        report = hg.fit_report(GRID, dst)
        self.assertEqual(report["points"], 12)
        self.assertGreater(report["rms_residual"], 0.01)
        self.assertLess(report["rms_residual"], 0.08)  # least squares cannot beat the 0.05 mm noise much
        self.assertNotIn(hg.FOUR_POINT_WARNING, report["warnings"])
        # The fitted mapping stays close to the truth inside the controlled region.
        for p in [(1300, 1100), (500, 600)]:
            a, b = hg.apply(report["H"], p), hg.apply(H_TRUE, p)
            self.assertLess(math.hypot(a[0] - b[0], a[1] - b[1]), 0.1)

    def test_four_point_warning(self):
        src = [(0, 0), (1000, 0), (1000, 800), (0, 800)]
        dst = [(0, 0), (50, 0), (50, 40), (0, 40)]
        report = hg.fit_report(src, dst, at=(500, 400))
        self.assertIn(hg.FOUR_POINT_WARNING, report["warnings"])
        self.assertLess(report["rms_residual"], 1e-9)
        self.assertAlmostEqual(report["local_scale_u"], 0.05)
        self.assertAlmostEqual(report["local_scale_v"], 0.05)
        self.assertAlmostEqual(report["mapped"][0], 25.0)
        self.assertAlmostEqual(report["local_anisotropy_percent"], 0.0, places=6)

    def test_jacobian_matches_finite_differences(self):
        for p in [(300.0, 400.0), (2200.0, 1900.0)]:
            J = hg.jacobian(H_TRUE, p)
            h = 1e-3
            for col, (du, dv) in enumerate(((h, 0.0), (0.0, h))):
                plus = hg.apply(H_TRUE, (p[0] + du, p[1] + dv))
                minus = hg.apply(H_TRUE, (p[0] - du, p[1] - dv))
                for row in range(2):
                    fd = (plus[row] - minus[row]) / (2 * h)
                    self.assertAlmostEqual(J[row][col], fd, delta=1e-9)
            sx, sy = hg.local_scale(H_TRUE, p)
            self.assertAlmostEqual(sx, math.hypot(J[0][0], J[1][0]))
            self.assertAlmostEqual(sy, math.hypot(J[0][1], J[1][1]))

    def test_perspective_changes_local_scale_across_the_image(self):
        a = hg.local_scale(H_TRUE, (100, 150))
        b = hg.local_scale(H_TRUE, (2500, 2050))
        self.assertGreater(abs(a[0] - b[0]) / a[0], 0.01)


class Degenerate(unittest.TestCase):
    def test_too_few_points(self):
        with self.assertRaises(ValueError):
            hg.fit([(0, 0), (1, 0), (0, 1)], [(0, 0), (1, 0), (0, 1)])

    def test_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            hg.fit([(0, 0), (1, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (0, 1)])

    def test_collinear_points(self):
        line = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]
        with self.assertRaises(ValueError):
            hg.fit(line, [(0, 0), (1, 0), (0, 1), (1, 1), (2, 1)])

    def test_three_collinear_of_four(self):
        src = [(0, 0), (1, 0), (2, 0), (0, 1)]
        with self.assertRaises(ValueError):
            hg.fit(src, [(0, 0), (1, 0), (0, 1), (1, 1)])

    def test_duplicates(self):
        with self.assertRaises(ValueError):
            hg.fit([(0, 0), (0, 0), (1, 0), (0, 1)], [(0, 0), (1, 1), (1, 0), (0, 1)])

    def test_jacobi_solver_on_known_matrix(self):
        values, vectors = hg.jacobi_eigen([[2.0, 1.0], [1.0, 2.0]])
        self.assertEqual(sorted(round(v, 12) for v in values), [1.0, 3.0])
        for i, lam in enumerate(values):
            vec = [vectors[0][i], vectors[1][i]]
            self.assertAlmostEqual(2 * vec[0] + vec[1], lam * vec[0])


if __name__ == "__main__":
    unittest.main()
