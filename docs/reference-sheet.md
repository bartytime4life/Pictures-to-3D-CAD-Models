# Reference-sheet tracing: method, mathematics and evidence

Lay the part on a sheet of known size, photograph the whole sheet, and choose that sheet as the **Scale reference**. The photo then supplies more than an outline:

- **Scale** from the sheet's stated size, so no calipered outside width is needed. Your own width measurement becomes an independent check.
- **Perspective and lens correction** from the sheet's four edges.
- **Thickness parallax correction**: the camera's position, recovered from the sheet, together with the thickness you enter, removes the visible side walls of a thick part.
- **Exact geometry**: lines, tangent arcs and circles fitted with residuals, then exported as true cylinders (STEP), `ARC`/`CIRCLE` entities (DXF) and `circle()` calls (OpenSCAD).
- **A check of the sheet you chose**: its proportions, though not its scale, are measured from the photo.

![The workbench after tracing a tilted phone photo of a 4 mm plate on an A4 sheet: the rectified, axis-aligned view with the fitted outline, the 120.00 mm width taken from the sheet, and the built model](images/reference-sheet.png)

The screenshot shows the browser-test fixture `tests/e2e/fixtures/plate-on-a4.jpg`, a rendered photo, after building with a 4 mm thickness.

This page describes each stage, the mathematics it depends on, and the tests that check that mathematics. The code is in `backend/sheet.py`, `backend/edges.py`, `backend/fitting.py` and `backend/reference.py`. The tests are in `tests/test_fidelity_math.py` (mathematical verification) and `tests/test_sheet_reference.py` (measurement accuracy against rendered photographs).

## Evidence boundary

The accuracy figures here come from **synthetic photographs** with exact ground truth (`tests/synthetic.py`). The renderer models a pinhole camera with radial distortion, uneven light, vignetting, a soft shadow, optical blur, noise, JPEG compression and the walls of a thick part. It also uses the same single-coefficient lens model the estimator fits. The sheet is exactly its nominal size and perfectly flat, and the walls are vertical with uniform tone.

Real lenses, paper tolerance, a curled sheet, chamfered or shiny edges will all do worse. These figures show which error sources each stage removes and the floor it reaches. They are not a physical accuracy claim. A measured-photo benchmark with calipered parts and real phones remains necessary.

## Pipeline

```text
photo (full resolution, <= 16 MP)
  -> find the sheet: largest convex quadrilateral (bright first, then dark) holding contrasting content
  -> sub-pixel points on each sheet edge (two passes)
  -> radial lens coefficient k1 from edge straightness (plumb-line)
  -> homography H: sheet millimetres -> undistorted photo pixels
  -> sheet-proportions check, and camera pose if a thickness is entered
  -> exact cubic resampling onto a millimetre grid (analysis), fast resampling (display)
  -> illumination-flattened part/sheet classification
  -> sub-pixel boundary at the local mid-level (two passes), edge blur sigma
  -> thick parts: two-step wall model on narrow wall bands, then top-face parallax correction
  -> circles / lines / arcs, design-intent snapping, constrained fillets, blur-curvature correction
  -> rotate to the part's own axes, display crop, Profile (polygons + exact primitives + evidence)
```

Coordinates follow the repository convention: pixel *i* spans [*i*, *i* + 1], so its centre is *i* + 0.5. The rectified image is addressed in millimetres times pixels per millimetre (`ppm`). That is 1.25 × the photo's native resolution at the sheet centre, clamped to 4–12 px/mm and to at most 12 MP.

## 1. Sheet and lens

**Edges.** Each sheet side is sampled from 6 % to 94 % of its length, clear of the corners. Each sample moves along the side normal to the local mid-level crossing (§3). A second pass re-centres on the first crossings. Lens distortion bows a real edge several pixels away from the corner-to-corner chord, which would otherwise put one level window on the transition. With one pass, k₁ was underestimated by 8–16 %; with two, corners are within 0.05 px.

**Lens model.** x_d = x_u (1 + k₁ r_u²), with r normalised by the image half-diagonal and centred on the image. A golden-section search over k₁ ∈ [−0.25, 0.25] minimises the RMS straightness of the four undistorted edges. A correction is kept only if it reduces that RMS by at least 20 %.

**Inverse.** Undistorting solves r_u + k₁ r_u³ = r_d by Newton's method. The forward map is monotonic while 1 + 3 k₁ r_u² > 0, which holds over the whole frame for |k₁| ≤ 0.25. The earlier fixed-point inverse x = x_d / (1 + k₁ r²) contracts slowly at strong distortion. At k₁ = −0.25 it left a 4.6 px error at the image corners; Newton's method leaves ≤ 1.4 × 10⁻¹² px for every allowed k₁ (`test_newton_undistortion_is_the_inverse_of_the_lens_model`). Noise-free distorted edges give back k₁ within 10⁻⁶ (`test_plumb_line_recovers_the_radial_coefficient_from_noise_free_edges`).

**Homography.** Total-least-squares lines through the undistorted edge points are intersected for the four corners, and `cv2.findHomography` maps the sheet's millimetre corners onto them. The longer pair of opposite sides is matched to the sheet's long dimension.

## 2. Resampling without positional quantisation

`cv2.remap` quantises interpolation positions to 1/32 pixel. Measured with an intensity ramp, which cubic interpolation must reproduce exactly, it moved rectified content by up to 0.086 photo px (RMS 0.036). That is the same size as the edge noise being measured. The measurement image is therefore resampled in float64 with the Keys cubic kernel (a = −½), which reproduces polynomials up to degree two. Linear and quadratic photo intensity fields are returned to float32 precision at every mapped position (`test_measurement_resampling_reproduces_quadratic_fields_exactly`). An A4 sheet at 11 px/mm takes 0.9 s. The display image still uses `cv2.remap`, which affects nothing measured. Rectification follows the pixel-centre convention: an analytic feature at plane point *c* lands at *c* · ppm within 0.02 px (`test_rectification_follows_the_pixel_centre_convention`).

## 3. Segmentation and sub-pixel edges

**Classification.** After an initial Otsu split, a robust cubic polynomial surface is fitted to the sheet (pixels at least 4 mm from the part) and a plane to the part. Each pixel is normalised as (sheet − value) / (sheet − part) and classified at 0.5. Gradients, vignetting and soft shadow therefore do not move the threshold. Only the largest region is kept, and a 3 mm sheet margin is excluded.

**Mid-level crossing.** Each boundary point is moved along its normal to where the profile crosses the mean of its two end medians. Profiles are sampled with exact float64 bilinear interpolation (§2). For a straight edge blurred by any symmetric point-spread function, the crossing of the continuous profile is the edge itself, whatever the blur width.

Sampling a pixel-integrated image adds a phase-dependent error ("pixel locking"):

- zero for a box blur, because the interpolated profile is exact;
- at most 0.03 px for Gaussian or triangular blur;
- zero-mean over the sub-pixel phase, so it averages out along any edge that is not aligned with the pixel grid.

This is checked at 16 phases by `test_half_level_crossing_on_symmetric_blur_is_unbiased_on_average`. Cubic profile interpolation did not reduce it. An area (moment) estimator removes it on noise-free data, but with realistic sensor noise its per-point spread was larger (0.052 against 0.043 px), so the crossing is kept.

**Two passes.** Pass 1 starts from boundary-pixel centres, about half a pixel inside one side, so its level windows are asymmetric. That grew holes by about 0.09 px at σ = 2 px. Pass 2 re-centres every point, with windows beyond 3.5 σ on both sides.

**Edge blur.** σ is the 25–75 % rise distance divided by 1.349 (the Gaussian value), taken as the median over the outer boundary.

## 4. Blur–curvature correction

A blurred curved edge's half-level contour moves toward its centre of curvature, for either polarity. Let X be the blurred position of a point at distance ρ from a disc's centre. Write the half-level condition P(|X| ≤ R) = ½ with tangential offset v ~ N(0, 1), and expand √(R² − σ² v²) in ε = σ/R. Using E v² = 1, E v⁴ = 3 and E v⁶ = 15 gives

> half-level radius = R − σ²/(2R) − (5/24) σ⁴/R³ + O(σ⁶/R⁵),

and inverting the series gives the correction used for every fitted arc and circle:

> R = r + σ²/(2r) − σ⁴/(24 r³) + O(σ⁶/r⁵).

`test_blur_curvature_series_and_its_inversion` evaluates the blurred disc by Gauss–Legendre quadrature, with x = R sin θ removing the square-root endpoint singularity. The integrator is first checked against the closed form at the centre, 1 − exp(−R²/2σ²), to 10⁻¹². The test then finds:

- the third-order coefficient converging to −5/24 (−0.20855 at R = 30σ);
- the residual after the second-order term falling as R⁻³ (slope −3.02);
- the inverted correction leaving an error of about 0.03 σ⁶/R⁵, which is 10–1000 times smaller than the first-order correction (for example 1.7 × 10⁻⁴ σ at R = 3σ).

Slot end caps take their radius from the spacing of their straight sides, which blur does not bias, and are not corrected.

## 5. Camera pose and thickness parallax

**Focal length.** Remove the principal point (taken as the image centre, with square pixels). The columns of H = K[r₁ r₂ t] then satisfy two constraints at any overall scale of H:

> (h₁₁h₁₂ + h₂₁h₂₂)/f² + h₃₁h₃₂ = 0 (r₁ ⊥ r₂),
> (h₁₁² + h₂₁² − h₁₂² − h₂₂²)/f² + h₃₁² − h₃₂² = 0 (|r₁| = |r₂|).

`test_exact_focal_length_constraints` checks both exactly, in rational arithmetic, for random rational cameras built with Cayley-transform rotations. The pose uses the least-squares solution when the two individual estimates agree within 15 %. Otherwise, as in a frontal or cropped view, it uses the EXIF 35 mm-equivalent focal length, and failing that a typical 26 mm phone lens, which is reported. Over 200 random tilted cameras, focal length is recovered to 10⁻⁹ and the camera centre C = −Rᵀt to 10⁻⁶ mm (`test_camera_pose_recovers_random_cameras_and_refuses_frontal_ones`).

**Top-face parallax.** Seen from C, at height D above the nadir N, a face at height t projects onto the sheet plane by a central similarity:

> q = N + (p − N) · D/(D − t).

`test_exact_top_face_projection_is_a_homothety_about_the_nadir` verifies H₀⁻¹H_t equals exactly this homothety matrix, in rational arithmetic, for random cameras and thicknesses. A silhouette point whose material-outward normal faces away from N is formed by the top edge and is scaled back by (D − t)/D. A point facing N is formed by the bottom edge and is left unchanged. The same rule applies to holes, using the material's outward normal, which points into the hole.

**Walls narrower than the blur.** Where the bottom edge forms the silhouette, the visible wall lies between it and the top edge in a band of width w = (D/(D − t) − 1)·|(p − N)·n|. The profile is then a blurred two-step (sheet → wall → top face). A single mid-level crossing is biased into the material by:

| w / σ | 0.25 | 0.5 | 1.0 | 1.6 | 2.5 | 4.0 | 6.0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bias / σ | −0.040 | −0.078 | −0.144 | −0.196 | −0.202 | −0.082 | −0.002 |

The profile is therefore modelled as I(t) = C(1 − P₁) + B(P₁ − P₂) + A P₂, with P₁ = Φ((t + w − e)/σ) and P₂ = Φ((t − e)/σ). This is linear in the tones A (sheet), B (wall) and C (top face) for a given edge offset e. Each candidate e is solved by least squares (variable projection), and the residual minimum is refined by a parabola.

As w → 0 the wall term tends to (B − C)(w/σ)φ, which is indistinguishable from a shift of e: the wall tone and the edge position are confounded. The fit is therefore made well-posed in three steps:

- The wall tone is measured only where bands are at least 2.5 σ wide, where a free fit recovers it.
- That tone is then held fixed for the narrower bands.
- The refinement is applied with full weight for 1.5–2.5 σ, tapering to zero at 0.5 and 3.5 σ so the boundary stays continuous.

On exact profiles the fixed-tone fit is unbiased within 0.01 σ, while the free fit is biased (`test_two_step_wall_model_is_unbiased_with_a_known_wall_tone_and_degenerate_without`). In rendered photos, refinement over the whole 0.25–4 σ range made strongly tilted shots worse, because soft shadow and uneven wall shading break the flat-tone model. The tapered 1–3 σ range was better on every feature at 9° and on four of five features at 22° (Results, below).

In a near-frontal photo the walls are too narrow to measure their tone. No refinement is attempted, and the trace notes the bound instead: edges facing the camera may read up to 0.2 σ into the part. A slightly tilted photo shows wider walls and avoids it.

## 6. Sheet proportions check

Scaling the stated plane axes by (a, b) multiplies the columns of H by a and b. That cannot change whether r₁ and r₂ are orthogonal, so the orthogonality constraint alone gives a focal length that is independent of the stated sheet size. With that focal length, the ratio of the first two column norms of K⁻¹H equals (true aspect)/(stated aspect). In a frontal view the ratio barely depends on the focal length, so the check works for any view.

Over 200 random cameras, the focal length is invariant and the ratio equals a/b to 10⁻¹² (`test_sheet_proportions_are_measurable_and_focal_length_ignores_them`). On rendered photos the measured ratio matched within 0.01 % at every tilt from 0° to 22°. An A4 photo traced as US Letter reads 0.9151 (theory 0.91503), and a custom width entered 1 % too large reads 0.9901. Every trace reports the check. A difference above 1 % becomes a visible warning, because every dimension scales with the chosen sheet.

## 7. Lines, arcs and circles

- **Circles.** A Kåsa algebraic fit, then Gauss–Newton on geometric distance. A circle is accepted when its RMS residual is below max(tol, 1 % r) and its largest residual below four times that. Noise-free arcs of 20–360° are recovered exactly, and the fit is equivariant under rotation, translation and scale (`test_circle_fit_is_exact_and_similarity_equivariant`). Its radius bias over 2000 noisy circles is within σ²/R + 4 standard errors (`test_geometric_circle_fit_bias_is_second_order_in_noise`).
- **Lines and arcs.** Douglas–Peucker breakpoints at 1.5 × tolerance split each ring. Breakpoint edges of at least `min_line` (2.5 % of the part, clamped to 1–3 mm) with a total-least-squares RMS below tolerance become lines. Consecutive line edges that still fit one line are merged, and runs between lines become arcs. An "arc" between two lines running the same way is a noise bump and is merged into one line. Points within tolerance of a neighbouring line are trimmed before an arc's fit, because tangent-region points pull its centre. Rings that cannot be described within tolerance stay as traced polylines.
- **Design intent** (optional, reported):
  - Lines within 0.6° of the dominant axis are made exact. The axis is the circular mean of 4θ, invariant to line direction and to quarter turns (`test_dominant_axis_ignores_line_direction_and_quarter_turns`).
  - An arc between non-parallel lines becomes a fillet whose centre lies on the corner bisector, c(r) = c₀ + r v. Only r is fitted. c(r) stays at distance exactly r from both lines for every r, which is verified in rational arithmetic (`test_exact_fillet_centre_is_tangent_to_both_lines_for_every_radius`). Over 300 noisy trials this constrained fit has less than half the spread of a free three-parameter arc (`test_tangent_constrained_fillet_fit_is_more_precise_than_a_free_arc`).
  - Between parallel lines the arc becomes a slot end cap: radius half the spacing, centre on the mid-line.
  - Radii within 3 % become equal.
  - The model is rotated so its straight edges lie along X and Y.
- **Sampling.** Polygon rings sample every arc within a stated sagitta. Every chord lies within the tolerance and the area error is at most perimeter × tolerance (`test_sampled_arcs_stay_within_the_requested_sagitta`).

The fitted CAD face area equals both the Green's-theorem area of its segments and the plate's closed-form area. The theorem's form is the shoelace sum over segment endpoints plus r²(φ − sin φ)/2 for each arc. The solid's volume is area × thickness, all to 10⁻⁹ (`test_greens_theorem_area_matches_the_cad_kernel_and_the_design`). DXF arc angles reproduce every arc's endpoints (`test_dxf_arcs_reproduce_their_endpoints`).

## Results on rendered photographs

The plate is 120 × 70 mm with R8 corners, 4 × Ø6 holes, a Ø22 bore and a 24 × 8 slot. Figures are maximum absolute errors in mm, measured on the fitted geometry after a rigid fit of the six hole centres; no scale is fitted. Runs recorded on 2026-11-10:

| Photo | Ø6 | Ø22 | Slot | Hole position | Outer |
| --- | --- | --- | --- | --- | --- |
| 2400 × 1800, overhead, ideal light | 0.0013 | 0.0002 | 0.0052 | 0.0021 | 0.0063 |
| 2400 × 1800, 22° tilt, lens, shadow | 0.0118 | 0.0295 | 0.0360 | 0.0065 | 0.0255 |
| 2400 × 1800, 22° tilt, 4 mm thick | 0.0076 | 0.0260 | 0.0294 | 0.0111 | 0.0059 |
| 2400 × 1800, 9° tilt, 4 mm thick | 0.0076 | 0.0065 | 0.0225 | 0.0067 | 0.0252 |
| 2400 × 1800, 5° tilt, 4 mm thick (walls too narrow, bound noted) | 0.0429 | 0.0244 | 0.0642 | 0.0388 | 0.0258 |
| 4000 × 3000, overhead, ideal light | 0.0003 | 0.0009 | 0.0052 | 0.0021 | 0.0020 |
| 4000 × 3000, 22° tilt, lens, shadow | 0.0060 | 0.0119 | 0.0162 | 0.0039 | 0.0105 |

For comparison, at 9° tilt on a 4 mm plate, the trace without the two-step wall model had errors of 0.039 (Ø6), 0.029, 0.060, 0.026 and 0.025 mm.

The same full-frame photos cannot be traced without a reference at all ("The outline touches the image edge"). Cropped inside the sheet by hand and traced the original way, with the best two-point scale a user could supply (endpoints exactly on the two diagonal Ø6 hole centroids, 108.24 mm apart), the 2400 × 1800 tilted photos gave:

| Photo | Ø6 | Ø22 | Outer |
| --- | --- | --- | --- |
| 22° tilt, thin | 1.041 | 0.811 | 2.808 |
| 22° tilt, 4 mm thick | 2.327 | 1.801 | 1.754 |

`tests/test_sheet_reference.py` asserts limits of 0.03 (Ø6), 0.05 (Ø22), 0.06 (slot), 0.05 (position) and 0.05 mm (outer) on the 2400 × 1800 cases, plus the 0.2 σ narrow-wall bound for frontal thick views. Those limits are regression guards, not accuracy claims.

## Limits

- The stated sheet size sets the scale. ISO 216 allows ±2 mm on 297 mm (about 0.7 %). The proportions check catches a wrong choice or a mistyped side, but not a uniformly wrong size: measure your sheet once.
- The sheet must be flat, fully visible, and contrast with the surface under it. The part must sit wholly on the sheet with a margin, and its brightness must differ from the sheet's.
- One radial coefficient about the image centre; no tangential distortion or k₂. Cropped photos and screenshots break the principal-point assumption, which leaves the focal estimate inconsistent and falls back to EXIF or an assumed lens.
- Vertical walls of constant thickness. Chamfers, draft, countersinks and shiny edges are not modelled. With walls too narrow to measure, an edge may read up to 0.2 σ into the part.
- Fitted lines, arcs and circles are descriptions of the photograph, not recovered design intent; review the snap list. Split output uses the traced polygon.
