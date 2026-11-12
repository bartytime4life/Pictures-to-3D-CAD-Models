"""Mathematical verification of the reference-sheet pipeline.

Four kinds of evidence, each named in its test:

* Exact algebra. Identities between rational functions are checked in exact rational
  arithmetic (fractions.Fraction) at random rational points, with rational rotations
  from the Cayley transform. A nonzero rational function vanishes at a random point
  with negligible probability (Schwartz-Zippel), so exact agreement at independent
  random points is strong evidence that the identity holds everywhere.
* Numerical analysis. Integrals are evaluated by Gauss-Legendre quadrature and checked
  first against a closed form; derived approximations are checked for their stated
  order of accuracy.
* Properties. Invariance and equivariance under rigid and similarity transforms,
  inverse consistency, and exact recovery from noise-free data.
* Statistics. Monte Carlo estimates of estimator bias and spread, with tolerances set
  from the standard error.
"""

from __future__ import annotations

import math
import random
import statistics
from fractions import Fraction as Q

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon

from backend import edges, fitting, sheet, tone
from backend.models import Primitives, ring_polygon
from backend.worker import extrude_fitted, model_rings, write_fitted_dxf
from tests import synthetic

# ------------------------------------------------------------- exact-arithmetic helpers


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def mat_inv3(m):
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    adj = [
        [e * i - f * h, c * h - b * i, b * f - c * e],
        [f * g - d * i, a * i - c * g, c * d - a * f],
        [d * h - e * g, b * g - a * h, a * e - b * d],
    ]
    return [[v / det for v in row] for row in adj]


def transpose(m):
    return [list(row) for row in zip(*m)]


def cayley_rotation(a, b, c):
    """Exact rational rotation R = (I - A)^-1 (I + A) for the skew matrix of (a, b, c)."""
    skew = [[Q(0), -c, b], [c, Q(0), -a], [-b, a, Q(0)]]
    eye = [[Q(int(i == j)) for j in range(3)] for i in range(3)]
    minus = [[eye[i][j] - skew[i][j] for j in range(3)] for i in range(3)]
    plus = [[eye[i][j] + skew[i][j] for j in range(3)] for i in range(3)]
    return mat_mul(mat_inv3(minus), plus)


def random_rational(rng, low, high, denominator=97):
    return Q(rng.randint(int(low * denominator), int(high * denominator)), denominator)


def random_exact_camera(rng):
    """Rational intrinsics, a rational rotation tilted toward a plane, rational translation."""
    rotation = cayley_rotation(
        random_rational(rng, -0.3, 0.3), random_rational(rng, -0.3, 0.3), random_rational(rng, -0.2, 0.2)
    )
    focal = random_rational(rng, 1500, 4000, 7)
    k = [[focal, Q(0), Q(2000)], [Q(0), focal, Q(1500)], [Q(0), Q(0), Q(1)]]
    t = [random_rational(rng, -60, 60), random_rational(rng, -60, 60), random_rational(rng, 300, 600)]
    return k, rotation, t, focal


def column(m, j):
    return [m[i][j] for i in range(3)]


def plane_homography(k, rotation, t, height=Q(0), up=Q(-1)):
    """K [r1 r2 t + up*height*r3]: the plane z = up*height in plane-x,y coordinates."""
    r1, r2, r3 = column(rotation, 0), column(rotation, 1), column(rotation, 2)
    shifted = [t[i] + up * height * r3[i] for i in range(3)]
    return mat_mul(k, transpose([r1, r2, shifted]))


# ------------------------------------------------------------------- exact algebra


def test_exact_top_face_projection_is_a_homothety_about_the_nadir():
    """Exact algebra: H0^-1 H_t = homothety(N, D / (D - t)) for any camera and thickness.

    This is the identity behind edges.correct_thickness: a plane parallel to the sheet at
    height t, seen from camera centre C at height D above nadir N, maps onto the sheet
    plane by a central similarity with ratio D / (D - t).
    """
    rng = random.Random(20261110)
    for _ in range(12):
        k, rotation, t, _ = random_exact_camera(rng)
        centre = [-sum(rotation[i][j] * t[i] for i in range(3)) for j in range(3)]  # -R^T t
        up = Q(-1) if centre[2] < 0 else Q(1)
        height_d = abs(centre[2])
        thickness = random_rational(rng, 0.5, 20)
        g = mat_mul(mat_inv3(plane_homography(k, rotation, t)), plane_homography(k, rotation, t, thickness, up))
        g = [[v / g[2][2] for v in row] for row in g]
        ratio = height_d / (height_d - thickness)
        expected = [
            [ratio, Q(0), (1 - ratio) * centre[0]],
            [Q(0), ratio, (1 - ratio) * centre[1]],
            [Q(0), Q(0), Q(1)],
        ]
        assert g == expected  # exact rational equality, entry by entry


def test_correct_thickness_inverts_the_homothety():
    """Property: correct_thickness undoes the projection for top-edge points and leaves
    bottom-edge points alone."""
    rng = np.random.default_rng(3)
    nadir, height, thickness = np.array([40.0, -15.0]), 410.0, 6.0
    points = rng.uniform(-80, 180, (200, 2))
    outward = rng.normal(size=(200, 2))
    outward /= np.linalg.norm(outward, axis=1, keepdims=True)
    away = np.einsum("ij,ij->i", outward, points - nadir) > 0
    projected = points.copy()
    projected[away] = nadir + (points[away] - nadir) * height / (height - thickness)
    corrected, top = edges.correct_thickness(projected, outward, nadir, height, thickness)
    assert np.array_equal(top, away)
    assert np.abs(corrected - points).max() < 1e-12


def test_exact_focal_length_constraints():
    """Exact algebra: with the principal point removed, the columns of H = K[r1 r2 t]
    satisfy (h11 h12 + h21 h22)/f^2 + h31 h32 = 0 and
    (h11^2 + h21^2 - h12^2 - h22^2)/f^2 + h31^2 - h32^2 = 0 (orthonormal r1, r2),
    at any overall scale of H. sheet.camera_pose solves these for f."""
    rng = random.Random(7)
    for _ in range(12):
        k, rotation, t, focal = random_exact_camera(rng)
        h = plane_homography(k, rotation, t)
        scale = random_rational(rng, 0.1, 9)
        shift = [[Q(1), Q(0), -k[0][2]], [Q(0), Q(1), -k[1][2]], [Q(0), Q(0), Q(1)]]
        (h11, h12, _), (h21, h22, _), (h31, h32, _) = [[v * scale for v in row] for row in mat_mul(shift, h)]
        u = 1 / (focal * focal)
        assert (h11 * h12 + h21 * h22) * u + h31 * h32 == 0
        assert (h11**2 + h21**2 - h12**2 - h22**2) * u + h31**2 - h32**2 == 0


def test_camera_pose_recovers_random_cameras_and_refuses_frontal_ones():
    """Property: 200 random tilted cameras are recovered (focal 1e-9 relative, centre
    1e-6 mm); for a frontal view the focal length is unobservable and is not taken
    from the sheet."""
    rng = np.random.default_rng(11)
    from tests.synthetic import _rot

    for _ in range(200):
        tilt = (rng.uniform(5, 40) * rng.choice([-1, 1]), rng.uniform(-25, 25), rng.uniform(-30, 30))
        focal = rng.uniform(1500, 5000)
        k = np.array([[focal, 0, 2000], [0, focal, 1500], [0, 0, 1.0]])
        rotation = _rot("z", tilt[2]) @ _rot("x", tilt[0]) @ _rot("y", tilt[1])
        t = np.array([0, 0, rng.uniform(250, 700)]) - rotation @ np.array([105, 148, 0.0])
        h = k @ np.column_stack([rotation[:, 0], rotation[:, 1], t])
        pose = sheet.camera_pose(h / h[2, 2], (4000, 3000))
        assert pose["focal_source"] == "sheet"
        assert abs(pose["focal_px"] - focal) < 1e-9 * focal
        assert np.abs(pose["centre_mm"] - (-rotation.T @ t)).max() < 1e-6
    k = np.array([[3000.0, 0, 2000], [0, 3000.0, 1500], [0, 0, 1.0]])
    h = k @ np.column_stack([[1, 0, 0], [0, 1, 0], [-105, -148, 450.0]])
    assert sheet.camera_pose(h, (4000, 3000))["focal_source"] == "assumed"


def test_sheet_proportions_are_measurable_and_focal_length_ignores_them():
    """Property: if the stated sheet axes are scaled by (a, b) relative to the true
    millimetres, i.e. H' = H diag(a, b, 1), the orthogonality-only focal length is
    unchanged and the column-norm ratio of K^-1 H' equals a / b. 200 random cameras,
    a and b within +-10 %."""
    rng = np.random.default_rng(13)
    from tests.synthetic import _rot

    for _ in range(200):
        tilt = (rng.uniform(5, 40) * rng.choice([-1, 1]), rng.uniform(4, 25) * rng.choice([-1, 1]), rng.uniform(-30, 30))
        focal = rng.uniform(1500, 5000)
        k = np.array([[focal, 0, 2000], [0, focal, 1500], [0, 0, 1.0]])
        rotation = _rot("z", tilt[2]) @ _rot("x", tilt[0]) @ _rot("y", tilt[1])
        t = np.array([0, 0, rng.uniform(250, 700)]) - rotation @ np.array([105, 148, 0.0])
        h = k @ np.column_stack([rotation[:, 0], rotation[:, 1], t])
        a, b = rng.uniform(0.9, 1.1, 2)
        scaled = h @ np.diag([a, b, 1.0])
        assert abs(sheet.orthogonal_focal(scaled, (4000, 3000)) - focal) < 1e-9 * focal
        assert abs(sheet.aspect_ratio_check(scaled, (4000, 3000), focal) - a / b) < 1e-12


def test_exact_fillet_centre_is_tangent_to_both_lines_for_every_radius():
    """Exact algebra: with unit directions from Pythagorean triples, c(r) = c0 + r v is at
    distance exactly r from both lines for every r, so a fillet stays tangent while its
    radius is fitted, corrected or equalised. Floats: fitting.fit_fillets agrees."""
    d1, d2 = (Q(3, 5), Q(4, 5)), (Q(-5, 13), Q(12, 13))
    n1, n2 = (-d1[1], d1[0]), (-d2[1], d2[0])
    c1, c2 = (Q(1, 3), Q(-2, 7)), (Q(11, 2), Q(9, 4))

    def intersect(p, d, q, e):
        det = d[0] * (-e[1]) - d[1] * (-e[0])
        s = ((q[0] - p[0]) * (-e[1]) - (q[1] - p[1]) * (-e[0])) / det
        return (p[0] + s * d[0], p[1] + s * d[1])

    c0 = intersect(c1, d1, c2, d2)
    shifted = intersect((c1[0] + n1[0], c1[1] + n1[1]), d1, (c2[0] + n2[0], c2[1] + n2[1]), d2)
    v = (shifted[0] - c0[0], shifted[1] - c0[1])
    for r in (Q(1, 10), Q(3), Q(17, 4), Q(250)):
        c = (c0[0] + r * v[0], c0[1] + r * v[1])
        assert (c[0] - c1[0]) * n1[0] + (c[1] - c1[1]) * n1[1] == r
        assert (c[0] - c2[0]) * n2[0] + (c[1] - c2[1]) * n2[1] == r


def test_exact_circumcentre_of_three_arc_points():
    """Exact algebra: fitting.arc_geometry's circumcentre formula returns the centre
    exactly for rational points on a circle (Pythagorean-triple angles)."""
    centre, radius = (Q(7, 3), Q(-5, 2)), Q(13, 4)
    triples = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)]
    points = [
        (centre[0] + radius * Q(a, c) * sx, centre[1] + radius * Q(b, c) * sy)
        for (a, b, c), (sx, sy) in zip(triples, [(1, 1), (-1, 1), (-1, -1), (1, -1)])
    ]
    for a, m, b in [(points[0], points[1], points[2]), (points[1], points[3], points[0])]:
        (ux, uy), r, _, _ = fitting.arc_geometry(a, m, b)
        assert (ux, uy) == centre
        assert abs(r - float(radius)) < 1e-12


# -------------------------------------------------------------- numerical analysis


def blurred_disc(rho, radius, sigma, nodes=400):
    """Value at distance rho from the centre of a unit disc blurred by an isotropic
    Gaussian: integral over x of N(x - rho; sigma) * erf(sqrt(R^2 - x^2) / (sigma sqrt 2)).

    Gauss-Legendre in theta with x = R sin(theta), which removes the square-root
    endpoint singularity; outside rho +- 12 sigma the Gaussian weight is below 1e-31.
    """
    lo = math.asin(max(-1.0, (rho - 12 * sigma) / radius))
    hi = math.asin(min(1.0, (rho + 12 * sigma) / radius))
    t, w = np.polynomial.legendre.leggauss(nodes)
    theta = (hi - lo) / 2 * t + (hi + lo) / 2
    x, dx = radius * np.sin(theta), radius * np.cos(theta) * (hi - lo) / 2
    gauss = np.exp(-((x - rho) ** 2) / (2 * sigma * sigma)) / (sigma * math.sqrt(2 * math.pi))
    erf = np.array([math.erf(v) for v in radius * np.cos(theta) / (sigma * math.sqrt(2))])
    return float(np.sum(w * gauss * erf * dx))


def half_level_radius(radius, sigma):
    lo, hi = radius - 5 * sigma, radius + 5 * sigma
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if blurred_disc(mid, radius, sigma) > 0.5 else (lo, mid)
    return (lo + hi) / 2


def test_quadrature_matches_the_closed_form_at_the_centre():
    """Numerical analysis: at the centre the blurred disc is 1 - exp(-R^2 / 2 sigma^2)."""
    for radius, sigma in [(3.0, 1.0), (5.0, 2.0), (10.0, 4.0)]:
        exact = 1 - math.exp(-radius * radius / (2 * sigma * sigma))
        assert abs(blurred_disc(0.0, radius, sigma) - exact) < 1e-12


def test_blur_curvature_series_and_its_inversion():
    """Numerical analysis of fitting.blur_corrected_radius.

    Series (derived by expanding P(|X| <= R) = 1/2 in sigma/R; E v^2 = 1, E v^4 = 3,
    E v^6 = 15 for the tangential offset v):
    half-level radius = R - sigma^2/(2R) - (5/24) sigma^4/R^3 + O(sigma^6/R^5).
    Checked: the third-order coefficient converges to -5/24, the residual after the
    second-order term has order -3 in R, and the inverted correction leaves an error of
    order sigma^6/R^5 that is at least ten times smaller than first order's.
    """
    sigma = 1.0
    radii = np.array([6.0, 9.0, 13.5, 20.0, 30.0])
    half = np.array([half_level_radius(r, sigma) for r in radii])
    residual = half - (radii - sigma * sigma / (2 * radii))
    slope = np.polyfit(np.log(radii), np.log(np.abs(residual)), 1)[0]
    assert -3.1 < slope < -2.9
    coefficient = residual * radii**3 / sigma**4
    assert abs(coefficient[-1] + 5 / 24) < 0.01 * 5 / 24
    assert np.all(np.diff(np.abs(coefficient + 5 / 24)) < 0)  # converging as R grows
    for radius, r in zip(radii, half):
        third = fitting.blur_corrected_radius(r, sigma) - radius
        first = r + sigma * sigma / (2 * r) - radius
        assert abs(third) < 0.05 * sigma**6 / radius**5
        assert abs(third) < 0.1 * abs(first)


def test_newton_undistortion_is_the_inverse_of_the_lens_model():
    """Property: undistort(distort(p)) = p within 2e-12 px over the whole frame for every
    radial coefficient the estimator may return."""
    size = (4000, 3000)
    w, h = size
    cx, cy, s = w / 2, h / 2, math.hypot(w, h) / 2
    grid = np.stack(np.meshgrid(np.linspace(0, w, 41), np.linspace(0, h, 31)), -1).reshape(-1, 2)
    for k1 in np.linspace(*sheet.K1_RANGE, 11):
        x, y = (grid[:, 0] - cx) / s, (grid[:, 1] - cy) / s
        f = 1 + k1 * (x * x + y * y)
        distorted = np.column_stack([cx + x * f * s, cy + y * f * s])
        assert np.abs(sheet.undistort_points(distorted, k1, size) - grid).max() < 2e-12


def test_plumb_line_recovers_the_radial_coefficient_from_noise_free_edges():
    """Property: distorted images of four straight sheet edges give back k1 (1e-6)."""
    size = (4000, 3000)
    w, h = size
    cx, cy, s = w / 2, h / 2, math.hypot(w, h) / 2
    corners = np.array([[700, 300], [3300, 380], [3450, 2700], [600, 2650]], float)
    for k1 in (-0.12, -0.035, 0.06):
        sides = []
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            p = a + np.linspace(0.06, 0.94, 300)[:, None] * (b - a)
            x, y = (p[:, 0] - cx) / s, (p[:, 1] - cy) / s
            f = 1 + k1 * (x * x + y * y)
            sides.append(np.column_stack([cx + x * f * s, cy + y * f * s]))
        estimate, before, after = sheet.estimate_k1(sheet.Sheet(corners, sides, 1), size)
        assert abs(estimate - k1) < 1e-6 and after < 1e-6 < before


def stepped_row(edge, kernel):
    """A straight step edge sampled by area (pixel i spans [i, i + 1]), then blurred."""
    columns = np.arange(96, dtype=np.float64)
    image = np.tile(230 - 180 * np.clip(edge - columns, 0, 1), (40, 1)).astype(np.float32)
    if kernel == "gaussian":
        return cv2.GaussianBlur(image, (0, 0), 1.7, borderType=cv2.BORDER_REPLICATE)
    once = cv2.blur(image, (5, 1), borderType=cv2.BORDER_REPLICATE)
    return once if kernel == "box" else cv2.blur(once, (5, 1), borderType=cv2.BORDER_REPLICATE)


@pytest.mark.parametrize("kernel", ["gaussian", "box", "triangle"])
def test_half_level_crossing_on_symmetric_blur_is_unbiased_on_average(kernel):
    """Property and bound. For a straight edge blurred by a symmetric point-spread
    function the mid-level crossing of the continuous profile is the edge itself.
    Sampling the pixel-integrated image adds a phase-dependent error (pixel locking):
    zero for a box blur (the interpolated profile is exact), bounded by 0.03 px for
    Gaussian or triangular blur, and zero-mean over the sub-pixel phase, so it averages
    out along any edge not aligned with the pixel grid."""
    errors = []
    for edge in np.linspace(40.0, 41.0, 17)[:-1]:
        points = np.column_stack([np.full(6, edge + 0.6), np.linspace(10.5, 29.5, 6)])
        moved, keep = sheet.half_level_search(
            stepped_row(edge, kernel), points, np.tile([1.0, 0.0], (6, 1)), half=8.0, step=0.0625
        )
        assert keep.all()
        errors.append(moved[0, 0] - edge)
    errors = np.array(errors)
    if kernel == "box":
        assert np.abs(errors).max() < 1e-9
    else:
        assert np.abs(errors).max() < 0.03
        assert abs(errors.mean()) < 1e-3


def test_sloped_plateau_levels_put_the_crossing_on_the_edge():
    """Numerical analysis of sheet.half_level_search with sigma. The exact profile of a
    Gaussian-blurred step between two linear plateaus (the one above: light a on the
    part, b0 + b (t - e) beyond) crosses (A(e) + B(e)) / 2 + (b1 - a1) sigma / sqrt(2 pi)
    at its edge e, and the search finds that crossing within 0.002 px for every slope,
    flat included (the end medians are 0.003 px off even there, and moved it by up to
    0.18 px on the slopes). On blurred discs of 7.5 to 55 sigma radius the traced radius
    is within 0.005 px of the blur-curvature series R - s^2/2R - 5 s^4/24 R^3 that the
    radius correction assumes, and closer to it than the end-median level's."""
    sigma, a, b0, edge = 2.0, 20.0, 200.0, 200.3
    t = np.arange(400) + 0.5 - edge
    points = np.column_stack([np.full(4, edge + 0.1), [3.0, 5.0, 7.0, 9.0]])
    normals = np.tile([1.0, 0.0], (4, 1))
    for b in (0.0, 0.5, 1.0, 2.0):
        cdf = edges.normal_cdf(t / sigma)
        density = np.exp(-0.5 * (t / sigma) ** 2) / math.sqrt(2 * math.pi)
        row = a * (1 - cdf) + b0 * cdf + b * (t * cdf + sigma * density)
        image = np.tile(row, (12, 1))
        moved, keep = sheet.half_level_search(image, points, normals, half=3.5 * sigma, step=0.0625, sigma=sigma)
        assert keep.all() and np.abs(moved[:, 0] - edge).max() < 0.002

    from shapely.geometry import Point

    sigma = 1.6
    for radius in (12.0, 24.0, 88.0):
        size = int(2 * radius + 80)
        centre = np.array([size / 2 + 0.3, size / 2 - 0.2])
        image = synthetic.coverage(Point(*centre).buffer(radius, 2048), 1.0, 0.0, 0.0, (size, size))
        image = cv2.GaussianBlur((236 - 188 * image).astype(np.float32), (0, 0), sigma)
        angle = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        normals = np.column_stack([np.cos(angle), np.sin(angle)])
        start = centre + 0.5 + radius * normals
        sloped, _ = sheet.half_level_search(image, start, normals, half=3.5 * sigma, sigma=sigma)
        median, _ = sheet.half_level_search(image, start, normals, half=3.5 * sigma)
        series = radius - sigma**2 / (2 * radius) - 5 * sigma**4 / (24 * radius**3)
        sloped_error = abs(np.linalg.norm(sloped - centre - 0.5, axis=1).mean() - series)
        median_error = abs(np.linalg.norm(median - centre - 0.5, axis=1).mean() - series)
        assert sloped_error < 0.005 and sloped_error <= median_error


def test_ring_smoothing_averages_the_slope_correction_round_a_closed_ring():
    """Properties of the smoothing applied to the slope correction: it keeps a constant,
    wraps round the ring's ends, and skips missing values."""
    values = np.full(200, 0.07)
    values[[5, 150]] = np.nan
    smoothed = sheet._smooth_along_ring(values, 20.0)
    assert np.isnan(smoothed[[5, 150]]).all() and np.allclose(np.delete(smoothed, [5, 150]), 0.07)
    wave = np.cos(np.linspace(0, 2 * np.pi, 400, endpoint=False))
    smoothed = sheet._smooth_along_ring(wave, 20.0)
    # A slow wave keeps its shape (attenuated by the Gaussian's transfer exp(-k^2 s^2 / 2)).
    expected = wave * math.exp(-0.5 * (2 * math.pi / 400 * 20.0) ** 2)
    assert np.abs(smoothed - expected).max() < 2e-3


def test_srgb_decoding_matches_the_standard_and_inverts_its_encoding():
    """Property: tone.linear_from_encoded is the IEC 61966-2-1 decoding. It agrees with
    the renderer's separately written copy and with the standard's own values (a saved
    0.5 is 0.21404 of full light; the two segments meet at 0.04045), it is increasing,
    it fixes 0 and 255, and encoding inverts it. A grey pixel's luminance is its
    decoded value."""
    codes = np.arange(256.0)
    linear = tone.linear_from_encoded(codes)
    assert linear[0] == 0 and abs(linear[255] - 255) < 1e-12
    assert np.all(np.diff(linear) > 0)
    assert np.abs(linear - synthetic.srgb_to_linear(codes)).max() < 1e-12
    assert abs(tone.linear_from_encoded(127.5) / 255 - 0.21404114) < 1e-8
    assert abs(tone.linear_from_encoded(0.04045 * 255) / 255 - 0.04045 / 12.92) < 1e-12
    assert np.abs(tone.encoded_from_linear(linear) - codes).max() < 1e-9
    assert tone.encoded_from_linear(-3.0) == 0
    grey = np.repeat(np.arange(256, dtype=np.uint8)[:, None], 3, axis=1)[None]
    assert np.abs(tone.linear_luminance(grey)[0] - linear).max() < 1e-3  # float32


def test_saved_values_bias_the_half_level_as_predicted_and_linear_light_removes_it():
    """Numerical analysis. A lens blurs in linear light and the camera then saves
    through a tone curve. On saved values, the mid-level of an edge between linear tones
    L < H is the linear level lin((enc(L) + enc(H)) / 2). A Gaussian edge reaches that
    level at sigma * Phi^-1(its share of the step) from the edge: inside the darker
    side, by 0.53 sigma for the test plate's saved tones 48 and 236. The crossing
    measured on saved values matches that prediction; on linear light it is the edge."""
    sigma = 1.7
    low, high = tone.linear_from_encoded(48.0), tone.linear_from_encoded(236.0)
    share = (tone.linear_from_encoded((48.0 + 236.0) / 2) - low) / (high - low)
    spread = math.hypot(sigma, 1 / math.sqrt(12))  # the blur plus the pixel's own width
    predicted = spread * statistics.NormalDist().inv_cdf(share)
    assert -0.56 * sigma < predicted < -0.52 * sigma
    columns = np.arange(96, dtype=np.float64)
    normals = np.tile([1.0, 0.0], (6, 1))
    on_saved, on_linear = [], []
    for edge in np.linspace(40.0, 41.0, 17)[:-1]:
        light = np.tile(high - (high - low) * np.clip(edge - columns, 0, 1), (40, 1))
        light = cv2.GaussianBlur(light.astype(np.float32), (0, 0), sigma, borderType=cv2.BORDER_REPLICATE)
        saved = synthetic.linear_to_srgb(light)
        points = np.column_stack([np.full(6, edge + 0.6), np.linspace(10.5, 29.5, 6)])
        for image, errors in ((saved, on_saved), (tone.linear_from_encoded(saved), on_linear)):
            moved, keep = sheet.half_level_search(image, points, normals, half=8.0, step=0.0625)
            assert keep.all()
            errors.append(moved[0, 0] - edge)
    assert abs(np.mean(on_saved) - predicted) < 0.02 * sigma
    assert np.abs(on_linear).max() < 0.03 and abs(np.mean(on_linear)) < 2e-3


def test_the_measurement_mix_is_judged_by_the_boundary_s_weakest_stretch():
    """Property. Luminance is kept when every stretch of a boundary has adequate
    contrast in it. Pure green and a 220 grey have equal luminance; the mix then takes
    the channels that differ, with non-negative weights summing to 1, whichever side is
    named first. A part of two colours keeps luminance when both are measurable in it,
    where a mix chosen from its main colour alone would erase the other. Any such fixed
    mix keeps a blurred edge's half-level on the edge."""

    def rows(colour, count):
        return np.tile(tone.linear_from_encoded(np.array(colour, float)), (count, 1))

    grey = rows((220, 220, 220), 100)
    assert tone.choose_mix(rows((48, 46, 44), 100), rows((236, 229, 217), 100)) == tone.LUMINANCE
    assert tone.choose_mix(grey, grey) == tone.LUMINANCE

    green = rows((0, 255, 0), 100)
    assert tone.saved_contrast(green, grey, tone.LUMINANCE).max() < 1
    weights = tone.choose_mix(green, grey)
    assert weights == tone.choose_mix(grey, green) == (0.5, 0.0, 0.5)
    assert tone.saved_contrast(green, grey, weights).min() > 200

    # A pale pink part with a green patch on that grey: both are 27 to 30 saved levels
    # from the sheet in luminance, and the pink's own difference mix is green alone.
    pink, patch = rows((220, 180, 220), 80), rows((40, 220, 40), 20)
    assert tone.difference_mix(pink[0], grey[0]) == (0.0, 1.0, 0.0)
    assert tone.saved_contrast(patch, grey[:20], (0.0, 1.0, 0.0)).max() < 1
    assert tone.choose_mix(np.vstack([pink, patch]), grey) == tone.LUMINANCE

    # Where luminance loses one stretch, the mix must still serve every stretch.
    mixed = tone.choose_mix(np.vstack([rows((40, 40, 40), 90), rows((0, 255, 0), 10)]), grey)
    assert mixed != tone.LUMINANCE and abs(sum(mixed) - 1) < 1e-12 and min(mixed) >= 0
    assert tone.saved_contrast(rows((40, 40, 40), 1), grey[:1], mixed)[0] > 24
    assert tone.saved_contrast(rows((0, 255, 0), 1), grey[:1], mixed)[0] > 24

    columns = np.arange(96, dtype=np.float64)
    points = np.column_stack([np.full(6, 40.9), np.linspace(10.5, 29.5, 6)])
    errors = []
    for edge in np.linspace(40.0, 41.0, 9)[:-1]:
        cover = np.tile(np.clip(edge - columns, 0, 1), (40, 1))[..., None]
        light = cv2.GaussianBlur((grey[0] + (green[0] - grey[0]) * cover).astype(np.float32), (0, 0), 1.7)
        rgb = np.clip(synthetic.linear_to_srgb(light), 0, 255).round().astype(np.uint8)
        moved, keep = sheet.half_level_search(
            tone.linear_mix(rgb, weights), points, np.tile([1.0, 0.0], (6, 1)), half=8.0, step=0.0625
        )
        assert keep.all()
        errors.append(moved[0, 0] - edge)
    assert np.abs(errors).max() < 0.03 and abs(np.mean(errors)) < 5e-3


@pytest.mark.parametrize("megapixels", [24, 50])
def test_reducing_a_photo_in_linear_light_keeps_edges_in_place(megapixels):
    """Property. A photo above 16 megapixels is reduced before tracing. Averaging linear
    light is a symmetric blur, so an edge's half-level stays put: its mean position over
    all pixel phases is within 0.015 source pixels. Averaging the saved values instead
    mixes tones on the wrong scale and moves the edge toward the lighter side."""
    scale = math.sqrt(16 / megapixels)
    low, high = float(tone.linear_from_encoded(48.0)), float(tone.linear_from_encoded(236.0))
    columns = np.arange(200, dtype=np.float64)
    normals = np.tile([1.0, 0.0], (4, 1))
    shifts = {"linear": [], "saved": []}
    for edge in np.linspace(90.0, 97.0, 57)[:-1]:
        light = np.tile(high - (high - low) * np.clip(edge - columns, 0, 1), (60, 1))
        light = cv2.GaussianBlur(light.astype(np.float32), (0, 0), 1.5, borderType=cv2.BORDER_REPLICATE)
        saved = np.clip(np.rint(synthetic.linear_to_srgb(light)), 0, 255).astype(np.uint8)
        photo = np.dstack([saved] * 3)
        size = (round(200 * scale), round(60 * scale))
        reduced = {
            "linear": tone.reduce_in_linear_light(photo, scale),
            "saved": cv2.resize(photo, size, interpolation=cv2.INTER_AREA),
        }
        for name, small in reduced.items():
            assert small.shape[:2] == size[::-1]
            ratio = small.shape[1] / 200
            points = np.column_stack(
                [np.full(4, edge * ratio + 0.3), np.linspace(6.5, small.shape[0] - 6.5, 4)]
            )
            moved, keep = sheet.half_level_search(
                tone.linear_luminance(small), points, normals, half=6.0, step=0.0625
            )
            assert keep.all()
            shifts[name].append(moved[0, 0] / ratio - edge)
    assert abs(np.mean(shifts["linear"])) < 0.015
    assert np.mean(shifts["saved"]) > 0.02


def test_a_sloped_plateau_shifts_the_half_level_by_the_predicted_amount():
    """Numerical analysis of a known limit. A soft shadow makes the paper brighter away
    from an edge: light a on the part, b0 + b (t - e) beyond it. Blurred by a Gaussian,
    the profile at the edge is (a + b0) / 2 + b sigma / sqrt(2 pi). The level taken
    from the profile's ends, whose medians lie at 85 % of the half-window H, is
    (a + b0 + 0.85 b H) / 2. The crossing therefore moves out of the part by
    b (0.425 H - sigma / sqrt(2 pi)) / slope: about 2.7 sigma^2 b / (b0 - a) for the
    H = 3.5 sigma used on part boundaries."""
    sigma, a, b0, edge = 2.0, 20.0, 200.0, 200.3
    half = 3.5 * sigma
    t = np.arange(400) + 0.5 - edge
    points = np.column_stack([np.full(4, edge + 0.1), [3.0, 5.0, 7.0, 9.0]])
    normals = np.tile([1.0, 0.0], (4, 1))
    for b in (0.5, 1.0, 2.0):
        cdf = edges.normal_cdf(t / sigma)
        density = np.exp(-0.5 * (t / sigma) ** 2) / math.sqrt(2 * math.pi)
        row = a * (1 - cdf) + b0 * cdf + b * (t * cdf + sigma * density)
        moved, keep = sheet.half_level_search(np.tile(row, (12, 1)), points, normals, half=half, step=0.0625)
        assert keep.all()
        slope = (b0 - a) / (sigma * math.sqrt(2 * math.pi)) + b / 2
        predicted = b * (0.425 * half - sigma / math.sqrt(2 * math.pi)) / slope
        assert abs(moved[0, 0] - edge - predicted) < 0.004  # px; pixel phase adds a little
        assert abs(predicted - 2.7 * sigma**2 * b / (b0 - a)) < 0.02 * predicted


def test_rectification_follows_the_pixel_centre_convention():
    """Property: an analytic scene photographed through a known homography and lens is
    resampled so that a feature at plane point c (mm) is centred at c * ppm in the
    rectified image's continuous coordinates (pixel i spans [i, i + 1])."""
    from tests.synthetic import _rot

    size = (1600, 1200)
    k = np.array([[1400.0, 0, 800], [0, 1400.0, 600], [0, 0, 1]])
    rotation = _rot("z", 3) @ _rot("x", 15) @ _rot("y", -6)
    t = np.array([0, 0, 420.0]) - rotation @ np.array([105, 148, 0.0])
    h = k @ np.column_stack([rotation[:, 0], rotation[:, 1], t])
    h /= h[2, 2]
    centres = np.array([[40.0, 60.0], [150.0, 70.0], [100.0, 150.0], [55.0, 240.0], [170.0, 230.0]])
    k1 = -0.04
    from tests.synthetic import undistort_grid

    u, v = np.meshgrid(np.arange(size[0]) + 0.5, np.arange(size[1]) + 0.5)
    iu, iv = undistort_grid(u, v, k1, size)
    inv = np.linalg.inv(h)
    den = inv[2, 0] * iu + inv[2, 1] * iv + inv[2, 2]
    px = (inv[0, 0] * iu + inv[0, 1] * iv + inv[0, 2]) / den
    py = (inv[1, 0] * iu + inv[1, 1] * iv + inv[1, 2]) / den
    photo = sum(np.exp(-((px - cx) ** 2 + (py - cy) ** 2) / (2 * 3.0**2)) for cx, cy in centres)
    rgb = np.repeat((photo * 200)[..., None], 3, axis=2).astype(np.float32)
    ppm = 4.0
    rect = sheet.rectify(rgb, h, k1, (210.0, 297.0), ppm)[..., 0].astype(np.float64)
    for cx, cy in centres:
        x0, y0 = int(cx * ppm) - 24, int(cy * ppm) - 24
        window = rect[y0 : y0 + 48, x0 : x0 + 48]
        jj, ii = np.mgrid[0:48, 0:48]
        weight = window / window.sum()
        mx = (weight * (ii + x0 + 0.5)).sum()
        my = (weight * (jj + y0 + 0.5)).sum()
        assert math.hypot(mx - cx * ppm, my - cy * ppm) < 0.02


def test_measurement_resampling_reproduces_quadratic_fields_exactly():
    """Numerical analysis: the Keys cubic kernel reproduces polynomials up to degree 2,
    so rectify_gray must return a linear or quadratic photo intensity field exactly at
    every mapped position. Any positional quantisation (cv2.remap's 1/32 pixel moved
    content by up to 0.09 px in the same test) would show here as a value error."""
    from tests.synthetic import _rot

    size = (1600, 1200)
    k = np.array([[1400.0, 0, 800], [0, 1400.0, 600], [0, 0, 1]])
    rotation = _rot("z", 3) @ _rot("x", 15) @ _rot("y", -6)
    t = np.array([0, 0, 420.0]) - rotation @ np.array([105, 148, 0.0])
    h = k @ np.column_stack([rotation[:, 0], rotation[:, 1], t])
    h /= h[2, 2]
    u, v = np.meshgrid(np.arange(size[0]) + 0.5, np.arange(size[1]) + 0.5)

    def fields(x, y):
        return [0.37 * x + 0.21 * y, 4e-4 * (x - 700) ** 2 + 2e-4 * (y - 500) ** 2 + 0.3 * x - 0.1 * y]

    ppm, k1 = 6.0, -0.04
    for photo_field, index in zip(fields(u, v), range(2)):
        rect = sheet.rectify_gray(photo_field, h, k1, (210.0, 297.0), ppm).astype(np.float64)
        gx, gy = np.meshgrid((np.arange(rect.shape[1]) + 0.5) / ppm, (np.arange(rect.shape[0]) + 0.5) / ppm)
        du, dv = sheet.plane_to_photo(h, k1, size, gx, gy)
        inside = (du > 4) & (du < size[0] - 4) & (dv > 4) & (dv < size[1] - 4)
        expected = fields(du, dv)[index]
        assert np.abs(rect - expected)[inside].max() < 1e-3  # float32 output rounding


def test_normal_cdf_approximation_error_is_below_its_published_bound():
    """Numerical analysis: Abramowitz & Stegun 7.1.26 has |erf error| < 1.5e-7, i.e. a
    normal-CDF error below 7.5e-8, checked on a dense grid against math.erf."""
    z = np.linspace(-8, 8, 20001)
    exact = np.array([0.5 * (1 + math.erf(v / math.sqrt(2))) for v in z])
    assert np.abs(edges.normal_cdf(z) - exact).max() < 7.5e-8


def two_step_image(edge, band, sigma, tones=(236.0, 78.0, 48.0)):
    background, wall, top = tones
    t = np.arange(200) + 0.5 - edge  # material for t < 0, wall band in [-band, 0]
    row = top + (wall - top) * edges.normal_cdf((t + band) / sigma) + (background - wall) * edges.normal_cdf(t / sigma)
    return np.tile(row, (20, 1))


def test_two_step_wall_model_is_unbiased_with_a_known_wall_tone_and_degenerate_without():
    """Numerical analysis of edges.two_step_refine on exact profiles (sigma = 1.6 px):
    the single crossing's analytic bias for a 1-3 sigma band is removed when the wall
    tone is known (|error| < 0.01 sigma), while a free three-tone fit cannot separate a
    narrow band's tone from the edge offset (error > 0.05 sigma at 0.5 sigma)."""
    sigma, edge = 1.6, 100.3
    points = np.column_stack([np.full(4, edge - 0.2 * sigma), [5.0, 8.0, 11.0, 14.0]])
    normals = np.tile([1.0, 0.0], (4, 1))
    for width in (1.0, 1.6, 2.5, 3.0):
        image = two_step_image(edge, width * sigma, sigma)
        moved, _ = edges.two_step_refine(image, points, normals, np.full(4, width * sigma), sigma, wall_tone=78.0)
        assert abs(moved[0, 0] - edge) < 0.01 * sigma
        crossing, _ = sheet.half_level_search(image, points, normals, half=3.5 * sigma, step=0.0625)
        assert edge - crossing[0, 0] > 0.1 * sigma  # the bias the model removes
    image = two_step_image(edge, 0.5 * sigma, sigma)
    free, tones = edges.two_step_refine(image, points, normals, np.full(4, 0.5 * sigma), sigma)
    assert abs(free[0, 0] - edge) > 0.05 * sigma and abs(tones[0] - 78.0) > 20


# ---------------------------------------------------------------------- properties


def test_circle_fit_is_exact_and_similarity_equivariant():
    """Property: noise-free arcs from 20 to 360 degrees are fitted exactly, and fitting
    transformed points equals transforming the fit (rotation, translation, scale)."""
    rng = np.random.default_rng(5)
    for sweep in (20, 45, 90, 180, 270, 360):
        theta = np.radians(np.linspace(0, sweep, 60, endpoint=sweep < 360)) + rng.uniform(0, 6)
        centre, radius = rng.uniform(-50, 50, 2), rng.uniform(1, 80)
        points = centre + radius * np.column_stack([np.cos(theta), np.sin(theta)])
        cx, cy, r, rms, _ = fitting.fit_circle(points)
        assert math.hypot(cx - centre[0], cy - centre[1]) < 1e-8 * radius
        assert abs(r - radius) < 1e-8 * radius and rms < 1e-8 * radius
        angle, scale, shift = rng.uniform(0, 2 * math.pi), rng.uniform(0.2, 5), rng.uniform(-90, 90, 2)
        rot = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
        moved = fitting.fit_circle(scale * points @ rot.T + shift)
        expected = scale * rot @ np.array([cx, cy]) + shift
        assert math.hypot(moved[0] - expected[0], moved[1] - expected[1]) < 1e-8 * scale * radius
        assert abs(moved[2] - scale * r) < 1e-8 * scale * radius


def test_dominant_axis_ignores_line_direction_and_quarter_turns():
    """Property: the 4-theta circular mean is unchanged by reversing any line or turning
    it by a multiple of 90 degrees, and is exact for noise-free sets."""
    true_axis = math.radians(23.0)
    rng = np.random.default_rng(2)
    for _ in range(20):
        prims = []
        for _ in range(6):
            a = true_axis + rng.integers(0, 4) * math.pi / 2 + (math.pi if rng.random() < 0.5 else 0)
            prims.append(fitting.Primitive("line", {"c": np.zeros(2), "d": np.array([math.cos(a), math.sin(a)])}, 0, 0))
        _, axis = fitting.snap_axes([prims])
        assert abs(axis - true_axis) < 1e-12


def outline_points(shape, turn_deg=0.0, step=0.2):
    """Noise-free points at most `step` apart along a shapely outline, after turning it."""
    import shapely
    from shapely import affinity

    turned = affinity.rotate(shape, turn_deg, origin=(0, 0))
    return np.asarray(shapely.segmentize(turned.exterior, step).coords)[:-1]


def arc_points(centre, radius, start_deg, sweep_deg, step=0.2):
    """Exact points at most `step` apart along an arc, from start_deg through sweep_deg."""
    count = math.ceil(radius * math.radians(abs(sweep_deg)) / step) + 1
    angles = np.radians(start_deg + np.linspace(0, sweep_deg, count))
    return [(centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)) for a in angles]


@pytest.mark.parametrize(
    ("radius", "tol", "min_line"),
    [(20.0, 0.05, 3.0), (60.0, 0.05, 3.0), (150.0, 0.03, 3.0), (400.0, 0.05, 3.0), (5.0, 0.03, 1.0)],
)
def test_arc_chords_long_enough_to_pass_for_lines_are_recovered_as_one_arc(radius, tol, min_line):
    """Property: exact recovery from noise-free data. Breakpoints at 1.5 tol cut an arc
    of radius R into chords of up to sqrt(12 R tol). Here that is over min_line, so the
    chords pass the line test, and fit_ring has to give them back to their arc. A plate
    with rounded corners then comes out as four lines and four arcs, and every arc has
    its exact radius and centre."""
    assert math.sqrt(12 * radius * tol) > min_line
    width, height = 2 * radius + 60, 2 * radius + 30
    corners = [(width - radius, height - radius), (radius, height - radius), (radius, radius), (width - radius, radius)]
    outline = [p for k, c in enumerate(corners) for p in arc_points(c, radius, 90 * k, 90)]
    prims = fitting.fit_ring(outline_points(Polygon(outline)), tol, min_line)
    assert [p.kind for p in prims] == ["line", "arc"] * 4
    for arc in prims[1::2]:
        assert abs(arc.data["r"] - radius) < 1e-6
        assert min(math.dist(arc.data["c"], c) for c in corners) < 1e-6


def test_straight_edges_no_longer_than_an_arcs_chords_stay_lines():
    """Property: a straight edge next to an arc is not taken for one of its chords,
    even when it is no longer than they are, because it does not lie on the arc's
    circle. A stadium's 4 mm sides between R30 ends, whose chords reach 4.2 mm, stay
    lines. So does a 4 mm flat that runs tangentially off the end of an R60 arc, whose
    chords reach 4.6 mm."""
    stadium = synthetic.stadium(0.0, 0.0, 64.0, 60.0)
    prims = fitting.fit_ring(outline_points(stadium), 0.05, 1.6)
    assert [p.kind for p in prims] == ["line", "arc"] * 2
    assert all(abs(p.data["r"] - 30) < 1e-6 for p in prims[1::2])
    assert all(abs(p.data["d"][1]) < 1e-3 for p in prims[::2])

    # Clockwise from the top edge: an R60 arc that turns 60 degrees, the flat, then a
    # sharp corner with the right-hand edge.
    arc = arc_points((0.0, -60.0), 60.0, 90, -60)
    along = np.array([math.sin(math.radians(30)), -math.cos(math.radians(30))])
    end = np.array(arc[-1]) + 4.0 * along
    plate = Polygon([(-70, 0), *arc, tuple(end), (end[0], -90), (-70, -90)])
    turn = math.radians(10)
    prims = fitting.fit_ring(outline_points(plate, 10), 0.03, 3.0)
    assert [p.kind for p in prims].count("line") == 5
    (arc_fit,) = [p for p in prims if p.kind == "arc"]
    assert abs(arc_fit.data["r"] - 60) < 1e-3
    expected = np.array([[math.cos(turn), -math.sin(turn)], [math.sin(turn), math.cos(turn)]]) @ along
    assert any(abs(abs(p.data["d"] @ expected) - 1) < 1e-4 for p in prims if p.kind == "line")


def test_one_chord_between_two_lines_is_not_an_arc():
    """Property: a corner turned by three 4 mm facets stays three lines. At this
    tolerance each middle facet lies on the circle through its two neighbours (it bows
    1.3 tol from it), but its neighbours do not follow it, and a single chord left
    between two lines is a line."""
    step = math.radians(22.5)
    corner = np.cumsum([(4 * math.cos(-k * step), 4 * math.sin(-k * step)) for k in (1, 2, 3)], axis=0)
    reach = corner[-1][0]
    quarter = [(60 - reach, 35.0), *((60 - reach + x, 35 + y) for x, y in corner)]
    outline = []
    for sx, sy in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        outline.extend([(sx * x, sy * y) for x, y in quarter][:: sx * sy])
    prims = fitting.fit_ring(outline_points(Polygon(outline), 10), 0.15, 3.0)
    assert [p.kind for p in prims] == ["line"] * 16


def turned(points, turn_deg):
    """Points turned about the origin, as outline_points turns its shape."""
    turn = math.radians(turn_deg)
    return np.asarray(points) @ np.array([[math.cos(turn), math.sin(turn)], [-math.sin(turn), math.cos(turn)]])


def test_a_stub_cut_off_by_the_rings_first_point_is_part_of_its_edge():
    """Property: exact recovery wherever the ring starts. A ring's first point is always
    a breakpoint. On a straight edge within min_line of a corner it cuts off a stub that
    is too short to be a line, and the stub was fitted as an arc with a radius in the
    millions. It is part of the edge it was cut from, whether the ring starts before the
    corner or past it, so a rectangle is four lines that meet at its corners."""
    corners = [(0, 0), (100, 0), (100, 60), (0, 60)]
    ring = outline_points(Polygon(corners), 10)
    for start in (-14, -5, -2, 0, 2, 5, 14):  # points 0.2 apart: up to 2.8 before or past a corner
        prims = fitting.fit_ring(np.roll(ring, -start, axis=0), 0.03, 3.0)
        assert [p.kind for p in prims] == ["line"] * 4
        ends = [segment[1] for segment in fitting.segments(prims)]
        assert max(min(math.dist(end, corner) for corner in turned(corners, 10)) for end in ends) < 1e-9
        # Every point is on one of the four lines, and each corner on two.
        assert sum((p.span[1] - p.span[0]) % len(ring) + 1 for p in prims) == len(ring) + 4


def blurred_rectangle_points(width, height, sigma, step, start=0.0, turn_deg=0.0):
    """Points `step` apart along the half-level outline of a sharp-cornered plate under a
    Gaussian blur, beginning `start` along it. Near a corner the blurred plate's level is
    Phi(x / sigma) Phi(y / sigma), where x and y are the depths inside its two edges, and
    the outline is where that product is 1/2. It follows each edge and rounds the corner."""
    normal = statistics.NormalDist()
    depth = np.linspace(6.0, normal.inv_cdf(math.sqrt(0.5)), 400)  # in sigma, down to the diagonal
    other = np.array([normal.inv_cdf(0.5 / normal.cdf(v)) for v in depth])
    half = sigma * np.column_stack([depth, other])
    corner = np.vstack([half, half[-2::-1, ::-1]])  # in along one edge, out along the next
    w, h = width / 2, height / 2
    outline = []
    for sx, sy, swap in ((1, 1, True), (-1, 1, False), (-1, -1, True), (1, -1, False)):
        outline.extend((sx * (w - x), sy * (h - y)) for x, y in (corner[:, ::-1] if swap else corner))
    xy = np.array(outline + outline[:1])
    along = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    at = (start + np.arange(0, along[-1] - step / 2, step)) % along[-1]
    return turned(np.column_stack([np.interp(at, along, xy[:, 0]), np.interp(at, along, xy[:, 1])]), turn_deg)


def test_a_blurred_sharp_corner_is_fitted_alike_wherever_the_ring_starts():
    """Numerical analysis, then statistics. Under a Gaussian blur of sigma the outline of
    a sharp-cornered plate follows its edges and rounds each corner. fit_ring describes
    the rounding as an arc, and its radius is 1.55 to 2 sigma wherever the ring starts.
    The start matters because a ring's first point is always a breakpoint, and on a
    straight edge just short of a corner it cuts off a stub that is too short to be a
    line. Fitted with the corner as one arc, the stub gave radii of up to 20 sigma here,
    by nothing but where the ring began. The edges do not move: opposite ones are the
    plate's width and height apart within 0.001. With edge noise of a fifth of the
    tolerance, about what a rendered photo's outline carries, the radii stay within 1.5
    to 2.5 sigma, where every third outline had stayed a polyline."""
    sigma, size = 0.3, (100.0, 60.0)
    tol = max(0.03, 0.15 * sigma)  # as backend.reference
    rng = np.random.default_rng(3)
    for noise, low, high in ((0.0, 1.55, 2.0), (tol / 5, 1.5, 2.5)):
        for start in np.arange(0, 6.01, 0.25):
            ring = blurred_rectangle_points(*size, sigma, 0.2, start, 10)
            prims = fitting.fit_ring(ring + rng.normal(0, noise, ring.shape), tol, 3.0)
            assert [p.kind for p in prims] == ["line", "arc"] * 4
            # Each line and arc begins on the point where the one before it ends.
            assert all(0 <= index < len(ring) for p in prims for index in p.span)
            assert sum((p.span[1] - p.span[0]) % len(ring) for p in prims) == len(ring)
            radii = np.array([p.data["r"] for p in prims[1::2]]) / sigma
            assert low < radii.min() and radii.max() < high
            lines = prims[::2]
            for near, far in ((lines[0], lines[2]), (lines[1], lines[3])):
                normal = np.array([-near.data["d"][1], near.data["d"][0]])
                apart = abs((np.asarray(far.data["c"]) - np.asarray(near.data["c"])) @ normal)
                assert min(abs(apart - side) for side in size) < (0.001 if noise == 0 else 0.005)


def test_two_points_between_two_lines_are_a_corner():
    """Property: exact recovery. Where a corner is cut by one step from a point to the
    next, those two points are all that lies between its edges. Two points define no
    circle, and they were fitted with one of radius 60 that swept out from the middle of
    both edges. The edges meet at the corner instead."""
    cut = 0.1  # shorter than the spacing of the points, so none falls on it
    corners = [(0, 0), (100, 0), (100, 60), (0, 60)]
    ring = outline_points(Polygon([(0, 0), (100, 0), (100, 60 - cut), (100 - cut, 60), (0, 60)]), 10)
    prims = fitting.fit_ring(ring, 0.03, 3.0)
    assert [p.kind for p in prims] == ["line"] * 4
    ends = [segment[1] for segment in fitting.segments(prims)]
    assert max(min(math.dist(end, corner) for corner in turned(corners, 10)) for end in ends) < 1e-9


def segment_area(ring):
    """Green's theorem for a boundary of lines and arcs: shoelace over the segment
    endpoints plus, for each arc of signed sweep phi, the circular segment
    r^2 (phi - sin phi) / 2. Positive for a counter-clockwise ring."""
    if ring[0][0] == "circle":
        return math.pi * ring[0][2] ** 2
    total = 0.0
    for s in ring:
        a, b = s[1], s[-1]
        total += (a[0] * b[1] - b[0] * a[1]) / 2
        if s[0] == "arc":
            _, r, _, phi = fitting.arc_geometry(s[1], s[2], s[3])
            total += r * r * (phi - math.sin(phi)) / 2
    return total


def plate_primitives():
    """Exact plate description in a y-down frame (like a traced profile)."""
    def rounded_rectangle(w, h, r):
        x0, y0, x1, y1 = -w / 2, -h / 2, w / 2, h / 2
        c = math.cos(math.pi / 4)
        segs = []
        corners = [((x1 - r, y0 + r), -90), ((x1 - r, y1 - r), 0), ((x0 + r, y1 - r), 90), ((x0 + r, y0 + r), 180)]
        for (ccx, ccy), start in corners:
            a0 = math.radians(start)
            a1 = a0 + math.pi / 2
            am = a0 + math.pi / 4
            segs.append({"kind": "arc", "start": [ccx + r * math.cos(a0), ccy + r * math.sin(a0)],
                         "mid": [ccx + r * math.cos(am), ccy + r * math.sin(am)],
                         "end": [ccx + r * math.cos(a1), ccy + r * math.sin(a1)]})
        ring = []
        for k, arc in enumerate(segs):
            ring.append(arc)
            ring.append({"kind": "line", "start": arc["end"], "end": segs[(k + 1) % 4]["start"]})
        del c
        return ring

    holes = [[{"kind": "circle", "center": [x, y], "radius": 3.0}] for x in (-48.0, 48.0) for y in (-25.0, 25.0)]
    holes.append([{"kind": "circle", "center": [-20.0, 0.0], "radius": 11.0}])
    slot = [
        {"kind": "line", "start": [17.0, -4.0], "end": [33.0, -4.0]},
        {"kind": "arc", "start": [33.0, -4.0], "mid": [37.0, 0.0], "end": [33.0, 4.0]},
        {"kind": "line", "start": [33.0, 4.0], "end": [17.0, 4.0]},
        {"kind": "arc", "start": [17.0, 4.0], "mid": [13.0, 0.0], "end": [17.0, -4.0]},
    ]
    holes.append(slot)
    return Primitives.model_validate({"outer": rounded_rectangle(120.0, 70.0, 8.0), "holes": holes})


def test_greens_theorem_area_matches_the_cad_kernel_and_the_design():
    """Exact geometry: the fitted solid's face area equals the Green's-theorem area of its
    segments and the plate's closed-form area; volume = area x thickness."""
    primitives = plate_primitives()
    rings = model_rings(primitives, lambda pts: [(x, -y) for x, y in pts], 1.0)
    outer = abs(segment_area(rings[0]))
    holes = sum(abs(segment_area(r)) for r in rings[1:])
    closed_form = (120 * 70 - (4 - math.pi) * 64) - (4 * math.pi * 9 + math.pi * 121 + (16 * 8 + math.pi * 16))
    assert abs((outer - holes) - closed_form) < 1e-9 * closed_form
    sampled = Polygon(
        ring_polygon(primitives.outer, 1e-4), [ring_polygon(h, 1e-4) for h in primitives.holes]
    )
    shape, face_area = extrude_fitted(rings, 4.0, Polygon([(x, -y) for x, y in sampled.exterior.coords],
                                                          [[(x, -y) for x, y in r.coords] for r in sampled.interiors]))
    assert abs(face_area - closed_form) < 1e-9 * closed_form
    assert abs(shape.Volume() - 4.0 * closed_form) < 1e-9 * 4.0 * closed_form


def test_sampled_arcs_stay_within_the_requested_sagitta():
    """Exact geometry: every chord of ring_polygon lies within the tolerance of its arc,
    so the sampled area error is at most perimeter x tolerance."""
    primitives = plate_primitives()
    for tolerance in (0.1, 0.01, 0.001):
        for ring in [primitives.outer, *primitives.holes]:
            points = np.array(ring_polygon(ring, tolerance))
            if ring[0].kind == "circle":
                c, r = np.array(ring[0].center), ring[0].radius
                mids = (points + np.roll(points, -1, axis=0)) / 2
                assert (r - np.linalg.norm(mids - c, axis=1)).max() <= tolerance + 1e-12
        sampled = Polygon(ring_polygon(primitives.outer, tolerance))
        exact = 120 * 70 - (4 - math.pi) * 64
        assert 0 <= exact - sampled.area <= sampled.length * tolerance


def test_dxf_arcs_reproduce_their_endpoints(tmp_path):
    """Exact geometry: counter-clockwise DXF start/end angles reproduce every fitted
    arc's endpoints, whichever way the arc was traversed."""
    import ezdxf

    rings = model_rings(plate_primitives(), lambda pts: [(x, -y) for x, y in pts], 1.0)
    path = tmp_path / "plate.dxf"
    write_fitted_dxf(path, rings)
    arcs = [e for e in ezdxf.readfile(path).modelspace() if e.dxftype() == "ARC"]
    expected = [s for ring in rings for s in ring if s[0] == "arc"]
    assert len(arcs) == len(expected) == 6
    for entity, segment in zip(arcs, expected):
        c, r = entity.dxf.center, entity.dxf.radius
        ends = {
            tuple(np.round([c.x + r * math.cos(math.radians(a)), c.y + r * math.sin(math.radians(a))], 9))
            for a in (entity.dxf.start_angle, entity.dxf.end_angle)
        }
        assert ends == {tuple(np.round(segment[1], 9)), tuple(np.round(segment[3], 9))}


# ---------------------------------------------------------------------- statistics


def test_geometric_circle_fit_bias_is_second_order_in_noise():
    """Statistics: over 2000 noisy full circles the radius bias is within
    sigma^2 / R + 4 standard errors, i.e. negligible at sub-pixel edge noise."""
    rng = np.random.default_rng(9)
    radius, noise = 30.0, 0.1
    theta = np.linspace(0, 2 * math.pi, 180, endpoint=False)
    estimates = []
    for _ in range(2000):
        points = radius * np.column_stack([np.cos(theta), np.sin(theta)]) + rng.normal(0, noise, (180, 2))
        estimates.append(fitting.fit_circle(points)[2])
    estimates = np.array(estimates)
    standard_error = estimates.std(ddof=1) / math.sqrt(len(estimates))
    assert abs(estimates.mean() - radius) < noise**2 / radius + 4 * standard_error


def test_tangent_constrained_fillet_fit_is_more_precise_than_a_free_arc():
    """Statistics: fitting only the radius of a fillet tangent to its two fitted edges
    has less than half the spread of a free three-parameter arc fit (300 trials)."""
    import shapely
    from shapely.geometry import box

    shape = box(-50, -30, 50, 30).buffer(-8).buffer(8, 128)
    ring = np.asarray(shapely.segmentize(shape.exterior, 0.5).coords)[:-1]
    rng = np.random.default_rng(4)
    free, constrained = [], []
    for _ in range(300):
        noisy = ring + rng.normal(0, 0.05, ring.shape)
        prims = fitting.fit_ring(noisy, 0.15, 5.0)
        free.extend(p.data["r"] for p in prims if p.kind == "arc")
        fitting.snap_axes([prims])
        fitting.refit_lines(noisy, prims)
        fitting.fit_fillets(noisy, prims, 0.15)
        constrained.extend(p.data["r"] for p in prims if p.kind == "arc")
    assert np.std(constrained) < 0.5 * np.std(free)
    standard_error = np.std(constrained) / math.sqrt(len(constrained))
    assert abs(np.mean(constrained) - 8.0) < 4 * standard_error + 0.005


def blurred_corner_ring(radius, sigma, size=(100.0, 60.0), step=0.2):
    """The outline of a rounded rectangle as blur leaves it, in exact form: its straight
    edges in place, and each corner arc about its true centre but inside its true radius
    by the blur-curvature shrink (fitting.blur_shrink). Points every `step`."""
    shrink = sigma**2 / (2 * radius) + 5 * sigma**4 / (24 * radius**3)
    w, h = size[0] / 2, size[1] / 2
    corners = [((w - radius, h - radius), 0), ((radius - w, h - radius), 90), ((radius - w, radius - h), 180), ((w - radius, radius - h), 270)]
    points = []
    for index, ((cx, cy), start) in enumerate(corners):
        angles = np.radians(start + np.arange(0, 90, math.degrees(step / radius)))
        points.extend(zip(cx + (radius - shrink) * np.cos(angles), cy + (radius - shrink) * np.sin(angles)))
        # The straight edge from this corner to the next, counter-clockwise.
        (nx, ny), _ = corners[(index + 1) % 4]
        a = np.array([cx + radius * math.cos(math.radians(start + 90)), cy + radius * math.sin(math.radians(start + 90))])
        b = np.array([nx + radius * math.cos(math.radians(start + 90)), ny + radius * math.sin(math.radians(start + 90))])
        count = max(2, round(float(np.linalg.norm(b - a)) / step))
        points.extend(tuple(a + (b - a) * k / count) for k in range(count))
    return np.array(points), shrink


@pytest.mark.parametrize(("radius", "sigma"), [(8.0, 0.34), (8.0, 0.6), (4.0, 0.34), (2.5, 0.34)])
def test_a_fillet_fitted_with_the_blur_in_its_model_keeps_its_true_radius(radius, sigma):
    """Numerical analysis of fitting.fit_fillets. Blur draws a corner arc toward its
    centre by s while its edges and its centre stay put. A fillet's centre is tied to
    its radius, so a fit that ignores the blur cannot follow the points by shrinking:
    it moves the centre too and settles near r + 3 s, and the correction meant for a
    free circle adds another s. With the blur in the model the radius comes out within
    a third of s; what is left comes from arc points that the edges' own fits take in
    where arc and edge meet."""
    ring, shrink = blurred_corner_ring(radius, sigma)
    tol = max(0.03, 0.15 * sigma)

    def fitted(blur):
        prims = fitting.fit_ring(ring, tol, 3.0)
        fitting.snap_axes([prims])
        fitting.refit_lines(ring, prims)
        fitting.fit_fillets(ring, prims, tol, blur)
        fitting.correct_blur(prims, sigma)
        radii = np.array([p.data["r"] for p in prims if p.kind == "arc"])
        assert len(radii) == 4 and [p.kind for p in prims].count("line") == 4
        return radii - radius

    assert np.abs(fitted(sigma)).max() < 0.35 * shrink
    ignored = fitted(0.0)
    assert (ignored > 3.5 * shrink).all() and (ignored < 4.5 * shrink).all()


def test_repeated_photos_are_precise_as_well_as_accurate():
    """Statistics: three photos differing only in sensor noise give hole diameters whose
    spread (precision) is far below the accuracy limit used elsewhere."""
    from backend.tracing import trace_image
    from tests import synthetic as S

    diameters = []
    for seed in (1, 2, 3):
        data, _ = S.render(tilt=(10.0, -4.0, 4.0), k1=-0.02, seed=seed)
        circles, _ = S.measure(trace_image(data, reference="a4")["profile"])
        diameters.append([c["diameter"] for c in circles])
    spread = np.array(diameters).std(axis=0, ddof=1)
    assert spread.max() < 0.02


# -------------------------------------------------- the exactly blurred corner (fillets)


def rounded_polygon(vertices, radius):
    """A convex polygon (counter-clockwise) with every corner filleted at `radius`:
    vertices, inner vertices (fillet centres), unit edge directions, outward normals."""
    p = np.asarray(vertices, dtype=np.float64)
    d = np.roll(p, -1, axis=0) - p
    d /= np.linalg.norm(d, axis=1)[:, None]
    out = np.column_stack([d[:, 1], -d[:, 0]])
    centres = np.array([
        np.linalg.solve(np.array([out[i - 1], out[i]]), [out[i - 1] @ p[i] - radius, out[i] @ p[i] - radius])
        for i in range(len(p))
    ])
    return p, centres, d, out


def house(apex_deg, width=300.0, height=200.0):
    """A pentagon with two right-angled base corners, two wall corners of
    90 + (90 - apex/2) degrees and an apex of `apex_deg`."""
    rise = width / 2 * math.tan(math.radians(90 - apex_deg / 2))
    return [(0, 0), (width, 0), (width, height), (width / 2, height + rise), (0, height)]


_ERF = np.frompyfunc(math.erf, 1, 1)


def slice_level(vertices, radius, points, sigma):
    """Blurred indicator of a filleted convex polygon by vertical slices, independent of
    fitting.corner_level: each vertical line meets the shape in one interval
    [bot(x), top(x)], so u(p) = int phi(x - px) [Phi((top - py)/s) - Phi((bot - py)/s)] dx.
    top and bot are the max and min over the fillet discs and offset edges, which all lie
    in the shape and make up its boundary. Gauss-Legendre between breakpoints, under a
    cosine substitution that removes the square-root ends of the discs."""
    _, centres, _, out = rounded_polygon(vertices, radius)
    seg_a, seg_b = centres + radius * out, np.roll(centres, -1, axis=0) + radius * out
    xs = np.concatenate([seg_a[:, 0], seg_b[:, 0], centres[:, 0] - radius, centres[:, 0] + radius])
    xmin, xmax = xs.min(), xs.max()
    breaks = np.unique(np.clip(xs, xmin, xmax))

    def top_bot(x):
        top, bot = np.full(x.shape, -np.inf), np.full(x.shape, np.inf)
        for cx, cy in centres:
            ok = np.abs(x - cx) <= radius
            h = np.sqrt(np.clip(radius * radius - (x - cx) ** 2, 0, None))
            top, bot = np.where(ok, np.maximum(top, cy + h), top), np.where(ok, np.minimum(bot, cy - h), bot)
        for a, b in zip(seg_a, seg_b):
            if abs(b[0] - a[0]) < 1e-12:
                continue
            ok = (x >= min(a[0], b[0])) & (x <= max(a[0], b[0]))
            y = a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0])
            top, bot = np.where(ok, np.maximum(top, y), top), np.where(ok, np.minimum(bot, y), bot)
        return top, bot

    def phi_cdf(z):
        return 0.5 * (1 + _ERF(z / math.sqrt(2)).astype(np.float64))

    points = np.atleast_2d(points)
    px, py = points[:, 0], points[:, 1]
    lo, hi = np.clip(px - 9 * sigma, xmin, xmax), np.clip(px + 9 * sigma, xmin, xmax)
    cuts = np.sort(np.concatenate([lo[:, None], np.clip(breaks[None], lo[:, None], hi[:, None]), hi[:, None]], 1), 1)
    a, b = cuts[:, :-1], cuts[:, 1:]
    f = np.linspace(0, 1, 7)
    sa = a[..., None] + (b - a)[..., None] * f[:-1]
    sb = a[..., None] + (b - a)[..., None] * f[1:]
    nodes, weights = np.polynomial.legendre.leggauss(16)
    s = (nodes + 1) / 2
    x = sa[..., None] + (sb - sa)[..., None] * (1 - np.cos(np.pi * s)) / 2
    jac = (sb - sa)[..., None] * (np.pi / 2) * np.sin(np.pi * s) * weights / 2
    top, bot = top_bot(x)
    inside = np.isfinite(top)
    pyb = py[:, None, None, None]
    cross = np.where(
        inside, phi_cdf((np.where(inside, top, 0) - pyb) / sigma) - phi_cdf((np.where(inside, bot, 0) - pyb) / sigma), 0
    )
    gauss = np.exp(-0.5 * ((x - px[:, None, None, None]) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    return np.sum(gauss * cross * jac, axis=(1, 2, 3))


def corner_geometry(vertices, radius, i):
    """centre, start angle and sweep of corner i's fillet, as fitting.corner_level takes them."""
    _, centres, _, out = rounded_polygon(vertices, radius)
    start = math.atan2(out[i - 1][1], out[i - 1][0])
    sweep = (math.atan2(out[i][1], out[i][0]) - start) % (2 * math.pi)
    return centres[i], start, sweep


def blurred_polygon_ring(vertices, radius, sigma, step=1.0):
    """The traced outline of a filleted polygon blurred by sigma: true boundary points
    moved along their normals to the blurred half-level, solved by bisection on
    fitting.corner_level of the nearest corner (exact while corners lie more than about
    ten sigma apart). Returns (points, normals)."""
    p, centres, _, out = rounded_polygon(vertices, radius)
    n = len(p)
    pts, nrm, owner = [], [], []
    for i in range(n):
        centre, start, sweep = corner_geometry(vertices, radius, i)
        k = max(2, round(sweep * radius / step))
        for t in start + sweep * (np.arange(k) + 0.5) / k:
            u = np.array([math.cos(t), math.sin(t)])
            pts.append(centre + radius * u), nrm.append(u), owner.append(i)
        a, b = centres[i] + radius * out[i], centres[(i + 1) % n] + radius * out[i]
        k = max(2, round(float(np.linalg.norm(b - a)) / step))
        for s in (np.arange(k) + 0.5) / k:
            q = a + s * (b - a)
            # nearer corner of this edge, if within 8 sigma of its tangent point
            ends = ((i, float(np.linalg.norm(q - a))), ((i + 1) % n, float(np.linalg.norm(q - b))))
            corner, gap = min(ends, key=lambda e: e[1])
            pts.append(q), nrm.append(out[i]), owner.append(corner if gap < 8 * sigma else -1)
    pts, nrm, owner = np.array(pts), np.array(nrm), np.array(owner)
    shift = np.zeros(len(pts))
    for i in range(n):
        sel = owner == i
        centre, start, sweep = corner_geometry(vertices, radius, i)
        lo, hi = np.full(sel.sum(), -3 * sigma), np.full(sel.sum(), 3 * sigma)
        for _ in range(60):
            mid = (lo + hi) / 2
            inside = fitting.corner_level(pts[sel] + mid[:, None] * nrm[sel], centre, radius, start, sweep, sigma) > 0.5
            lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
        shift[sel] = (lo + hi) / 2
    return pts + shift[:, None] * nrm, nrm


def fit_snapped(ring, sigma, ppm=5.0):
    """The fitting chain of backend.reference with snapping on, in pixels at `ppm`."""
    tol = max(0.03, 0.15 * sigma / ppm) * ppm
    min_line = min(max(0.025 * float(np.ptp(ring, axis=0).max()) / ppm, 1.0), 3.0) * ppm
    prims = fitting.fit_ring(ring, tol, min_line)
    assert prims is not None
    fitting.snap_axes([prims])
    fitting.refit_lines(ring, prims, margin=3 * sigma)
    fitting.fit_fillets(ring, prims, tol, sigma)
    fitting.correct_blur(prims, sigma)
    return prims


def test_erfc_matches_the_standard_library_within_its_stated_accuracy():
    """Numerical analysis: fitting.erfc against math.erfc, fractional error < 1.2e-7,
    out to where erfc underflows; and its limits."""
    x = np.linspace(-6, 26, 64001)
    exact = np.array([math.erfc(v) for v in x])
    assert (np.abs(fitting.erfc(x) - exact) / exact).max() < 1.2e-7
    assert list(fitting.erfc(np.array([np.inf, -np.inf, 0.0]))) == [0.0, 2.0, pytest.approx(1.0, abs=1e-7)]


def test_blurred_corner_matches_closed_forms_and_an_independent_integral():
    """Numerical analysis of fitting.corner_level. A sharp right-angled corner blurs to
    Phi(x/s) Phi(y/s); far along an edge it is the half-plane Phi(d/s). Around every
    corner of two filleted pentagons (corners of 60, 90, 120 and 150 degrees; r from one
    to twelve sigma) it agrees with the vertical-slice integral, which shares no code
    with it, to 1e-6 at the points the fillet fit uses."""
    rng = np.random.default_rng(0)
    sigma = 1.7
    pts = rng.uniform(-6, 6, (300, 2))
    sharp = fitting.corner_level(pts, (1e-7, 1e-7), 1e-7, math.pi, math.pi / 2, sigma)
    phi = 0.5 * (1 + _ERF(pts / (sigma * math.sqrt(2))).astype(np.float64))
    assert np.abs(sharp - phi[:, 0] * phi[:, 1]).max() < 1e-6
    along = fitting.corner_level(np.array([[10.4, -30.0]]), (0, 0), 10.0, 0.0, math.pi / 2, sigma)
    assert along[0] == pytest.approx(0.5 * (1 + math.erf(-0.4 / (sigma * math.sqrt(2)))), abs=1e-6)

    sigma = 1.6
    for apex in (60, 120):
        for multiple in (1.0, 3.0, 12.0):
            radius = multiple * sigma
            vertices = house(apex)
            _, _, d, out = rounded_polygon(vertices, radius)
            for i in range(len(vertices)):
                centre, start, sweep = corner_geometry(vertices, radius, i)
                t1, t2 = centre + radius * out[i - 1], centre + radius * out[i]
                offsets = np.linspace(-2 * sigma, 2 * sigma, 5)
                probe = [t1 - a * d[i - 1] + o * out[i - 1] for a in np.linspace(0, 5 * sigma, 6) for o in offsets]
                probe += [t2 + a * d[i] + o * out[i] for a in np.linspace(0, 5 * sigma, 6) for o in offsets]
                for angle in np.linspace(start, start + sweep, 5):
                    u = np.array([math.cos(angle), math.sin(angle)])
                    probe += [centre + (radius + o) * u for o in offsets if radius + o > 0]
                probe = np.array(probe)
                model = fitting.corner_level(probe, centre, radius, start, sweep, sigma)
                assert np.abs(model - slice_level(vertices, radius, probe, sigma)).max() < 1e-6


@pytest.mark.parametrize("apex", [60, 120])
@pytest.mark.parametrize("multiple", [2.0, 5.0, 25.0, 50.0])
def test_fillets_keep_their_radius_at_every_corner_angle_and_size(apex, multiple):
    """Exact recovery. The traced outline of a blurred, filleted pentagon (corners of 60,
    90 and 150, or 90 and 120 degrees), fitted as backend.reference does: every corner
    is one arc between two lines, and every fillet's outline is within 0.001 px of the
    truth (at 150 degrees a radius error moves the outline only 0.035 times as far), its
    radius within 0.005 px + 0.1 % up to 120 degrees. The one exception is a 150 degree
    fillet of two sigma, which moves the outline less than the edges' own uncertainty:
    it is reported sharp, with a bound above its true radius. Before the exact corner model the
    150 degree fillets read up to 19 blur shrinks large; before chords were merged,
    radii of 25 sigma and more were cut into runs of short lines."""
    sigma = 1.6
    radius = multiple * sigma
    vertices = house(apex)
    ring, _ = blurred_polygon_ring(vertices, radius, sigma)
    prims = fit_snapped(ring, sigma)
    kinds = "".join(p.kind[0] for p in prims)
    assert kinds.count("l") == 5 and "aa" not in kinds
    for k, p in enumerate(prims):
        if p.kind == "line" and prims[k - 1].kind == "line":
            # A corner reported sharp never hides a fillet larger than its stated bound,
            # and only a wide corner's small fillet can be hidden.
            assert p.data["sharp_bound"] > radius and multiple <= 2.0 and apex == 60
        if p.kind == "arc":
            error = abs(p.data["r"] - radius)
            theta = math.radians(p.data["corner_deg"])
            # How far the outline itself moves at the corner's midpoint.
            assert error * (1 / math.sin(theta / 2) - 1) < 1e-3
            if p.data["corner_deg"] < 121:
                assert error < 0.005 + 0.001 * radius
            assert p.data["blur_modelled"] and math.isfinite(p.data["r_sd"])


@pytest.mark.parametrize(("apex", "multiple"), [(60, 16.0), (120, 5.0)])
def test_an_arc_cut_into_two_chords_stays_one_arc(apex, multiple):
    """Exact recovery under a wide blur (2.5 px). A 150 degree R40 px corner and a
    120 degree R12.5 px corner are each cut into just two chords that pass for lines.
    The large-radius rule sends a lone chord between two lines back, and these corners
    became sharp, moving the outline 1.4 and 1.9 px; fitting._curved_runs keeps them as
    one arc each, with their radius."""
    sigma = 2.5
    radius = multiple * sigma
    ring, _ = blurred_polygon_ring(house(apex), radius, sigma)
    prims = fit_snapped(ring, sigma)
    assert "".join(p.kind[0] for p in prims) == "la" * 5
    radii = np.array([p.data["r"] for p in prims if p.kind == "arc"])
    assert np.abs(radii - radius).max() < 0.01


def correlated_noise(rng, n, scale, length=2.0):
    """Edge noise of standard deviation `scale` correlated along the ring over `length` points."""
    kernel = np.exp(-0.5 * (np.arange(-4 * length, 4 * length + 1) / length) ** 2)
    kernel /= np.sqrt((kernel * kernel).sum())
    w = rng.normal(0, 1, n + 2 * len(kernel))
    return scale * np.convolve(w, kernel, "same")[len(kernel) : len(kernel) + n]


def test_reported_fillet_uncertainty_matches_its_monte_carlo_spread():
    """Statistics. Forty noisy tracings (0.1 px noise correlated over four points along
    the edge) of a pentagon with 90 and 120 degree corners: each corner's mean radius is
    within four standard errors of the truth, and the reported standard deviation is
    within a factor of 0.75 to 3 of the observed spread. It includes the blur's and the
    edges' systematic uncertainty, which this experiment leaves out, so it errs high;
    without the correlation measured on the edges (fitting.correlation_factor) it would
    read under half the spread."""
    sigma, radius = 1.6, 8.0
    ring, normals = blurred_polygon_ring(house(120), radius, sigma)
    rng = np.random.default_rng(11)
    radii, reported = {}, {}
    for _ in range(40):
        noisy = ring + correlated_noise(rng, len(ring), 0.1, 4.0)[:, None] * normals
        for p in fit_snapped(noisy, sigma):
            if p.kind == "arc":
                angle = round(p.data["corner_deg"])
                radii.setdefault(angle, []).append(p.data["r"])
                reported.setdefault(angle, []).append(p.data["r_sd"])
    assert sorted(radii) == [90, 120]
    for angle, values in radii.items():
        spread = statistics.stdev(values)
        assert abs(statistics.fmean(values) - radius) < 4 * spread / math.sqrt(len(values))
        assert 0.75 < statistics.median(reported[angle]) / spread < 3


def test_a_wide_fillet_the_photo_cannot_resolve_is_reported():
    """Properties. At a 150 degree corner the outline moves only 0.035 times a change of
    radius; with 0.03 px of edge noise a radius of five sigma is not determined, and the
    trace says so (with the outline's own, much smaller, uncertainty), in each of six
    noisy tracings. The right-angled and 60 degree corners of the same outline are
    determined and are never named."""
    sigma, radius = 1.6, 8.0
    ring, normals = blurred_polygon_ring(house(60), radius, sigma)
    for seed in range(6):
        noisy = ring + correlated_noise(np.random.default_rng(seed), len(ring), 0.03)[:, None] * normals
        prims = fit_snapped(noisy, sigma)
        notes = fitting.undetermined_radii([prims], sigma, scale=0.2)
        assert len(notes) >= 1 and all("90°" not in n and "60°" not in n for n in notes)
        for p in prims:
            if p.kind == "arc" and "r_sd" in p.data:
                wide = round(p.data["corner_deg"]) == 150
                assert (p.data["r_sd"] > fitting.UNDETERMINED_REL * p.data["r"]) == wide
    assert any("150° corner" in n and "or more" in n for n in notes)
    square = blurred_polygon_ring([(0, 0), (300, 0), (300, 200), (0, 200)], radius, sigma)[0]
    assert fitting.undetermined_radii([fit_snapped(square, sigma)], sigma) == []


def test_rendered_coverage_is_exact_and_edges_keep_their_place_at_any_phase():
    """Exact geometry and properties of the test renderer. synthetic.coverage gives each
    pixel square's exact area inside a turned plate with a hole and a slot that crosses
    the image's left border (shapely's intersection area, to 1e-6). Sampling coverage on
    sub-rows instead moved a traced 45 degree edge by up to 0.027 px depending on its
    sub-pixel phase; rendered exactly, a square at 45 and 26.6 degrees (slopes 1 and
    1/2, where every pixel along an edge has the same phase) traces within 0.006 px of
    its true size at each of two phases."""
    from shapely import affinity
    from shapely.geometry import Point, box

    part = affinity.rotate(box(-3, 4, 40, 30).buffer(-3).buffer(3, 64), 23, origin=(18, 17))
    part = part.difference(Point(20, 17).buffer(5, 64)).difference(box(28, 10, 33, 22))
    cov = synthetic.coverage(part, 4.0, 0.0, 0.0, (160, 200))
    rng = np.random.default_rng(0)
    for _ in range(500):
        i, j = int(rng.integers(0, 200)), int(rng.integers(0, 160))
        pixel = box((i - 0.5) / 4, (j - 0.5) / 4, (i + 0.5) / 4, (j + 0.5) / 4)
        assert abs(pixel.intersection(part).area * 16 - cov[j, i]) < 1e-6

    ppm = 5.0
    for angle in (45.0, math.degrees(math.atan(0.5))):
        for shift in (0.0, 0.25):
            square = affinity.translate(affinity.rotate(box(30, 30, 110, 110), angle, origin=(70, 70)), shift / ppm, 0.37 * shift / ppm)
            image = cv2.GaussianBlur((236 - 188 * synthetic.coverage(square, ppm, 0.0, 0.0, (700, 700))).astype(np.float32), (0, 0), 1.6)
            rings, _, _ = edges.subpixel_rings((image < 142).astype(np.uint8), image, ppm)
            points = next(r for r in rings if r["outer"])["points"] / ppm - (np.array([70.0, 70.0]) + np.array([shift, 0.37 * shift]) / ppm)
            t = math.radians(angle)
            for axis in (np.array([math.cos(t), math.sin(t)]), np.array([-math.sin(t), math.cos(t)])):
                # Opposite edges together: their mean offset is the size error, free of any shift.
                offsets = []
                for n in (axis, -axis):
                    along, dist = points @ np.array([-n[1], n[0]]), points @ n - 40.0
                    offsets.append(dist[(np.abs(along) < 30) & (np.abs(dist) < 1.5)].mean() * ppm)
                assert abs(sum(offsets) / 2) < 0.006
