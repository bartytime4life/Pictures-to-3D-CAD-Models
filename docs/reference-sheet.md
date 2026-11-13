# Reference-sheet tracing: method, mathematics and evidence

[Documentation index](README.md) · [Guided workbench review](validation/guided-workbench.md)

Lay the part on a sheet of known size, photograph the whole sheet, and choose that sheet as the **Scale reference** before loading the photo. For an already loaded photo, choose it under **Adjust outline** and apply the new trace. The photo then supplies more than an outline, subject to the camera and part assumptions below:

- **Scale** from the sheet's stated size, so no calipered outside width is needed. Your own width measurement becomes an independent check.
- **Estimated perspective and lens correction** from the sheet's four edges, using the stated camera model.
- **Thickness parallax correction**: an estimated camera position and the thickness you enter correct the top-face boundary for the modelled vertical walls. When thickness changes, building retraces from the source photo if it is still available; a restored outline without its photo instead reports that its earlier correction cannot be refreshed.
- **Analytic fitted geometry**: accepted lines, tangent arcs and circles carry residuals and become exact entities in STEP and DXF. OpenSCAD retains fitted circles as `circle()` calls and samples other fitted curves; see [export representation limits](exports.md#openscad-editable-profile-extrusion). A fitted entity is not an exact measurement of the physical part.
- **A check of the sheet you chose**: its proportions, though not its scale, are measured from the photo.

![The workbench after tracing a tilted phone photo of a 4 mm plate on an A4 sheet: the rectified, axis-aligned view with the fitted outline, the 120.02 mm width taken from the sheet, and the built model](images/reference-sheet.png)

The screenshot shows the browser-test fixture `tests/e2e/fixtures/plate-on-a4.jpg`, a rendered photo, after building with a 4 mm thickness.

This page describes each stage, the mathematics it depends on, and the tests that check that mathematics. The code is in `backend/sheet.py`, `backend/edges.py`, `backend/fitting.py` and `backend/reference.py`. The tests are in `tests/test_fidelity_math.py` (mathematical verification) and `tests/test_sheet_reference.py` (measurement accuracy against rendered photographs).

## Evidence boundary

The accuracy figures here come from **synthetic photographs** with exact ground truth (`tests/synthetic.py`). The renderer models a pinhole camera with radial distortion, uneven light, vignetting, a soft shadow, optical blur, noise, JPEG compression and the walls of a thick part. Its default lens model has the same single coefficient the estimator fits; an optional test-only second term supplies mismatch cases. Light is mixed and blurred in linear light and saved through the sRGB tone curve, the same curve the tracer decodes. A real camera adds its own tone mapping, which neither side models; §3 gives the cost of a mismatched curve. The sheet is exactly its nominal size and perfectly flat, and the walls are vertical with uniform tone.

Real lenses, paper tolerance, a curled sheet, chamfered or shiny edges introduce model mismatch that these renders do not establish a bound for. These figures report observed errors under the tested rendering conditions, not a universal error floor or a physical accuracy claim. A measured-photo benchmark with calipered parts and real phones remains necessary; [the photo benchmark](photo-benchmark.md) runs one on your own photos, and no result from real photos is recorded yet. Use [independent engineering checks](engineering-model.md) for dimensions reserved from calibration.

Earlier lens tables used the production radial inverse in the renderer. The
[radial-inverse repair](validation/radial-inverse.md) now uses separate cubic
identities and a bracketed higher-order inverse in the renderer, with independent
Decimal checks. This removes a code dependency, while the common camera
assumptions remain. Its higher-order stress cases show that a small sheet-edge
residual can coexist with substantial reserved-dimension errors. The initial
extrapolation failure has a [source-support guard](validation/fit-support.md);
the [directional-spread experiment](validation/directional-spread-qualification.md)
remains a research record, and a separate covariance fit with the orientation-support
and adequacy rules that record called for now traces a uniform directional blur by
direction (§3). Existing tables below retain their original conditions.

## Pipeline

```text
photo (full resolution, <= 16 MP)
  -> linear-light copy of the photo (sRGB decoding), used for every sub-pixel measurement
  -> find the sheet: largest convex quadrilateral (bright first, then dark) holding contrasting content
  -> sub-pixel points on each sheet edge (two passes)
  -> radial lens coefficient k1 from edge straightness (plumb-line)
  -> homography H: sheet millimetres -> undistorted photo pixels
  -> sheet-proportions check, and camera pose if a thickness is entered
  -> exact cubic resampling of linear light onto a millimetre grid (analysis), fast resampling (display)
  -> illumination-flattened part/sheet classification, on saved values
  -> sub-pixel boundary at the local mid-level (two passes), edge blur sigma
  -> thick parts: two-step wall model on narrow wall bands, then top-face parallax correction
  -> circles / lines / arcs, design-intent snapping, constrained fillets, blur-curvature correction
  -> circle-consistent final joins, or retain the affected source boundary as lines
  -> common source-derived display rotation, crop, Profile (polygons + final primitives + evidence)
```

Coordinates follow the repository convention: pixel *i* spans [*i*, *i* + 1], so its centre is *i* + 0.5. The rectified image is addressed in millimetres times pixels per millimetre (`ppm`). That is 1.25 × the photo's native resolution at the sheet centre, clamped to 4–12 px/mm and to at most 12 MP.

## 1. Sheet and lens

**Edges.** Each sheet side is sampled from 6 % to 94 % of its length, clear of the corners. Each sample moves along the side normal to the local mid-level crossing (§3). A second pass re-centres on the first crossings. Lens distortion bows a real edge several pixels away from the corner-to-corner chord, which would otherwise put one level window on the transition. With one pass, k₁ was underestimated by 8–16 %; with two, corners are within 0.05 px.

**Lens model.** x_d = x_u (1 + k₁ r_u²), with r normalised by the image half-diagonal and centred on the image. A golden-section search within k₁ ∈ [−0.25, 0.25] minimises the RMS straightness of the four undistorted edges. Trial coefficients must also have a central-branch inverse for every measured sheet corner and edge sample. A correction is kept only if it reduces that RMS by at least 20 %. These coefficients use a different normalization from OpenCV's focal-normalized coefficients.

**Inverse.** Undistorting solves r_u + k₁ r_u³ = r_d by safeguarded Newton steps inside a sign bracket, with bisection when a step leaves it. For negative k₁, the increasing branch ends at r_u = 1/√(−3k₁), corresponding to r_d,max = 2/(3√(−3k₁)). At k₁ = −0.25 that observed-radius limit is approximately 0.769800359: a sensor radius of 0.9 has no central inverse. Such inputs are refused. If the largest reference radius is R, plumb-line search restricts k₁ to values above −4/(27R²), within its existing range. Near the turning point the inverse remains ill-conditioned; numerical convergence does not bound image or camera error. [Domain derivation, counterexamples and Decimal checks](validation/radial-inverse.md) replace the earlier whole-frame claim. The existing `test_newton_undistortion_is_the_inverse_of_the_lens_model` checks sampled forward-generated rays, while `test_plumb_line_recovers_the_radial_coefficient_from_noise_free_edges` recovers k₁ within 10⁻⁶ under its noise-free model.

**Homography.** Total-least-squares lines through the undistorted edge points are intersected for the four corners, and `cv2.findHomography` maps the sheet's millimetre corners onto them. The longer pair of opposite sides is matched to the sheet's long dimension.

## 2. Resampling without positional quantisation

`cv2.remap` quantises interpolation positions to 1/32 pixel. Measured with an intensity ramp, which cubic interpolation must reproduce exactly, it moved rectified content by up to 0.086 photo px (RMS 0.036). That is the same size as the edge noise being measured. The measurement image is therefore resampled in float64 with the Keys cubic kernel (a = −½), which reproduces polynomials up to degree two. Linear and quadratic photo intensity fields are returned to float32 precision at every mapped position (`test_measurement_resampling_reproduces_quadratic_fields_exactly`). An A4 sheet at 11 px/mm takes 0.9 s. The display image still uses `cv2.remap`, which affects nothing measured. Rectification follows the pixel-centre convention: an analytic feature at plane point *c* lands at *c* · ppm within 0.02 px (`test_rectification_follows_the_pixel_centre_convention`).

## 3. Segmentation and sub-pixel edges

**Classification.** After an initial Otsu split, a robust cubic polynomial surface is fitted to sheet samples outside the initial part mask expanded by a square kernel about 4 mm across, and a plane to the part. Each pixel is normalised as (sheet − value) / (sheet − part) and classified at 0.5. This compensates smooth lighting variations represented by the fitted surfaces; unmodelled gradients, vignetting and shadows can still bias classification. Only the largest region is kept, and a 3 mm sheet margin is excluded.

**Linear light.** A lens and sensor blur the scene in linear light. The camera then saves each value through a tone curve, close to a 2.2 gamma, which bends a blurred edge's profile. The mid-level property below holds only in linear light.

On saved values, the mid-level between linear tones L < H is the linear level lin((enc(L) + enc(H)) / 2). A Gaussian edge reaches that level at σ · Φ⁻¹(s) from the edge, where s is the level's share of the step. For the test plate's saved tones (48 on 236), s = 0.30 and the crossing sits 0.53 σ inside the darker side. In the rendered photos that made holes read about 0.25 mm too large and the outline about 0.3 mm too small. `test_saved_values_bias_the_half_level_as_predicted_and_linear_light_removes_it` checks the prediction and its removal.

The tracer therefore decodes the photo with the sRGB curve (IEC 61966-2-1; `backend/tone.py`) and makes every sub-pixel measurement on linear light: the sheet's edges, the resampling onto the millimetre grid, the part's boundary, the edge blur and the wall model. Finding the sheet and classifying the part still use saved values, the scale their thresholds were set on. Contrast limits are stated on that scale too, because a processed photo's noise is roughly even there. Any fixed mix of linear colour channels keeps an edge's mid-level in place, so the photo's colour primaries do not matter; only its tone curve does.

That freedom also chooses the mix. Luminance is used while it leaves at least 24 saved grey levels across the boundary at its weakest stretch (the 5th percentile along it), twice the 12 a measurement needs. Two colours can differ clearly in the saved photo and still have the same luminance: pure green and a 220 grey are 70 grey levels apart there. The tracer then takes the candidate mix with the best weakest stretch: each channel weighted by its own difference between the two sides' typical colours, an even mix, or one channel alone. It does this for the part against the sheet and for the sheet against the surface under it, and the trace notes a colour mix.

Judging by the weakest stretch matters for a part of two colours. A mix chosen from the main colour alone can make the other colour equal to the sheet; a pale pink plate with a green patch then read 66 mm wide, not 80, and lost a hole. On lossless rendered photos that plate, a green part on the grey sheet and a grey sheet on a green table all trace within 0.01 mm (`test_a_two_colour_part_keeps_the_boundary_of_its_smaller_colour`, `test_parts_and_sheets_that_differ_in_colour_are_measured_on_the_channels_that_differ`).

A camera whose curve differs from sRGB leaves part of the bias. On the overhead rendered photo (ideal light, 2400 × 1800), the largest of the five errors reported under Results was:

| Camera's curve | Largest error (mm) |
| --- | --- |
| sRGB | 0.003 |
| Plain gamma 2.2 | 0.019 |
| Plain gamma 2.4 | 0.027 |
| Plain gamma 2.0 | 0.065 |
| Plain gamma 1.8 | 0.114 |
| Linear (no curve) | 0.318 |

Phone cameras also apply their own tone mapping, which the file does not record. Its cost is not measured here.

**Mid-level crossing.** Each boundary point is moved along its normal to where the profile crosses the mean of its two end medians. Profiles are sampled with exact float64 bilinear interpolation (§2). For an isolated straight edge with constant levels on either side and a symmetric point-spread function, the continuous profile crosses their mid-level at the edge. Its curvature vanishes there, suppressing the leading bilinear interpolation error, but finite sampling phase and higher-order terms can still shift the interpolated crossing. The phase-bias checks below quantify the tested cases. The blur measurement and the wall model (§5), which use whole profiles, sample them cubically.

In the tested pixel-integrated profiles, sampling adds a phase-dependent error ("pixel locking"):

- zero for a box blur, because the interpolated profile is exact;
- below 0.03 px for the tested Gaussian or triangular blur;
- a mean error magnitude below 0.001 px across the 16 sampled phases. Varying phase along an edge can reduce the average bias; pixel-grid alignment can preserve it.

This is checked at 16 phases by `test_half_level_crossing_on_symmetric_blur_is_unbiased_on_average`. Cubic profile interpolation did not reduce it. An area (moment) estimator removes it on noise-free data, but with realistic sensor noise its per-point spread was larger (0.052 against 0.043 px), so the crossing is kept.

**Two passes.** Pass 1 starts from boundary-pixel centres, about half a pixel inside one side, so its level windows are asymmetric. That grew holes by about 0.09 px at σ = 2 px. Pass 2 re-centres every point, with windows beyond 3.5 σ on both sides.

**Edge blur.** σ is the 25–75 % rise distance divided by 1.349 (the Gaussian value), taken as the median over the outer boundary. Its profiles are read by Keys cubic sampling (`sheet.sample_keys`, the kernel of §2). Bilinear sampling, used here before 2026-11-11, blurs what it reads by a variance of f(1 − f) at sub-pixel phase f, 1/6 px² on average, so it measured about √(σ² + 1/6). On exactly blurred straight edges at 0–45° and four phases it read σ 2.2–4.2 % high at 1.6 px and up to 8.4 % at 1.2 px. Cubic sampling measures the blur, a pixel's own box included, within 0.6 % and 2.3 % (`test_edge_blur_is_measured_without_the_samplers_own_blur`). Every model that takes σ, from the exact corner of §4 to the wall model of §5, had been given the larger blur. The reported `edge_blur_mm` is a Gaussian-equivalent edge spread, not a complete measurement of the point-spread function. A blur that differs by direction is measured separately (below); spatial variation is not. Even isotropic blur in the camera image can become anisotropic and vary across the rectified plane. Each profile's plateaus are read at the ends of its window, which must reach well beyond the blur: a fixed ±8 px window (2.2 σ at 3.7 px) read a 3 px photo blur 11 % narrow and a 2 px one 1.7 % narrow. The window is therefore widened to 5 σ and the blur measured again; up to 1.6 px the first window already reaches that far.

**Directional blur.** A shaken camera blurs more along its motion than across it. A Gaussian blur of covariance S spreads an edge with unit normal n by σₙ² = nᵀSn, so every profile's width gives one linear equation in (S_xx, S_xy, S_yy) (`edges.edge_covariance`), in the rectified image the edges are traced in. On a photo blurred 1 × 3 px, every hole gave the same S ≈ [[2.9, 0.8], [0.8, 14.2]] px², and σₙ² = nᵀSn fitted each profile within 0.03 px; the off-diagonal term is the sheet's 4° turn in the photo, (14.2 − 2.9) sin 4° cos 4° = 0.79. The fit takes the rules the [directional-spread qualification](validation/directional-spread-qualification.md) found necessary:

- **Clean steps only.** A profile that falls back after its rise or overshoots its plateaus has reached another edge (across a thin hole, at a sharp corner) and is left out. An evenly blurred thin circular-segment hole had read as a blur 2.45 times wider one way.
- **Supported directions.** The normals are grouped into six bins of 30°, modulo 180°, and a bin counts with 15 clean profiles. Three unknowns need three counted bins and a numerically rank-three weighted covariance design, checked at every fit including after trimming. Bins alone do not establish rank: opposite normals can straddle a bin boundary through floating angle rounding while giving identical covariance equations. A two-direction design cannot separate the cross term from the rest; see the [rank regression](validation/directional-blur-rank.md). Each counted bin weighs the same in the least squares: a long outline gives two bins most of the profiles, and on a rendered tilted photo an unweighted fit followed them and left another direction 11.5 % off (7 % weighted).
- **Adequacy per direction.** One profile's width is good to a few per cent, so a bin's median absolute residual is mostly noise; a wrong model shifts a whole bin. A bin whose median relative variance residual is beyond both 10 % and three standard errors of that median means the blur is not one Gaussian covariance, and the fit is rejected. Each bin is judged alone, so a dominant direction cannot hide a minority one's disagreement in a pooled statistic. Bins of 30° do not see a variation that repeats within one.
- **A switch, not a blend.** Rendered photos tilted up to 22° fit principal spreads 1.00–1.05 apart, the larger from foreshortening; shaken ones 1.25–2.56. Above a ratio of 1.15 (`edges.DIRECTIONAL_RATIO`) the trace works by direction; below it, or without an accepted fit, the one measured σ stands and the trace is as before.

Internally, a missing covariance can mean either insufficient/rejected fit
support or a fitted covariance below the directional-ratio switch. The return
value alone does not distinguish those cases. The scalar fallback preserves
the existing tracer; it does not calibrate isotropic optics for a different
inverse model. The separate [finite-material developer API](finite-shape-inverse.md)
requires an explicitly supplied covariance and is not called by this pipeline.

Working by direction:

- Each point's second-pass level search (its windows, the step's tail and the paper's slope) uses its own σₙ, and so does the wall model of §5.
- Free arcs and circles need another width. A curved edge of radius R is drawn in by the median of w_n + w_t²/(2R), where w_n and w_t are the blur's components across and along it. To first order that is the variance of w_t given w_n = 0, Σ_tt − Σ_tn²/Σ_nn = det S / nᵀSn, so the shrink at direction n is det S / (2R nᵀSn), not S_tt / (2R); the [directional-blur experiment](research.md#directional-blur-experiment-status--november-12-2026) derived the same leading term. Round a circle it averages √det S / (2R), because the mean of 1/(nᵀSn) over all directions is 1/√det S. The existing free-curve corrections of §4 take σ = (det S)^¼, the geometric mean of the principal spreads. This scalar approximation is not the nonparallel-corner model below. On exactly blurred holes of 34 and 68 px under a 1.7 × 3.77 px blur the exact mid-level contour's mean shrink agrees with √det S / (2R) within 5 %, where tr S / (4R) is 30 % too large; the fit recovers S within 5 %, and the traced hole, corrected, is within 0.01 px of its radius (`test_a_directional_blur_shrinks_a_circle_by_its_geometric_mean_variance`).
- Nonparallel fillets use the full covariance in the rounded-corner forward model (§4), preserving its orientation instead of replacing it by the scalar summary. The [anisotropic-corner guide](anisotropic-corners.md) describes the geometry, numerical refusal and traced-boundary recovery.
- A slot end cap is placed mostly by its tip (§7), so its points take their own first-order shrink, det S / (2r nᵀSn).
- The trace notes the blur's range across directions.

**Stage boundaries.** Here `S` describes empirical rise widths in the rectified
measurement field, after Keys resampling, float32 storage and the additional
0.7 px Gaussian smoothing. It is not a calibrated covariance in the original
camera frame; a projective warp can change both its direction and its spatial
variation. `sigma_n` is used for each second-pass edge search and wall profile.
`subpixel_rings` also returns the scalar `(det S)^¼` for later fitting and
`reference.edge_blur_mm` when a directional fit is accepted.

Supported nonparallel fillets now pass the full covariance into the whitened
`corner_level` forward model. A known uniform thickness scale transports it by
its square; mixed scales or unresolved numerical inference retain the affected
source outline when valid. If that corrected ring is invalid, the narrow
[line-only recovery](anisotropic-corners.md#when-the-corrected-source-ring-is-invalid)
requires a frozen accepted initial fit, a valid bounded polygon and
bidirectional whole-boundary tolerance checks; otherwise the profile is refused.
Neither recovery determines the corner radius. The slot-end axial fit still uses directional first-order shrink
with an isotropic higher-order term, and a partial free arc still uses the
circle-average scalar approximation. These distinct models do not supply physical
uncertainty bounds; see the [complete corner evidence](validation/anisotropic-corners.md).

**Blur frames after thickness correction.** The point map carries its known
scale into free-curve correction, slot-cap fitting and line-refit windows.
Uniform support scale k requires σ′ = kσ and S′ = k²S, including scalar paths;
free arcs use their own cyclic support spans, circles the whole ring and caps
the adjacent lines' context. Mixed free curves, caps and scalar-only corner
fits retain the older geometry approximation with a visible warning on emitted
geometry. Mixed scalar corners remain radius-undetermined without a sharp-bound
or sharp-deletion claim. An unusable scalar-model radius keeps an eligible
positive initial geometric arc without another generic blur correction, or is
marked unresolved if no such arc exists. Mixed supplied-covariance nonparallel corners remain
withheld under the existing recovery policy. No average Gaussian frame or
confidence bound is inferred. See [blur frames](blur-frames.md) for
the equations, window tie guard and remaining model limits. Existing tables
below are not new evaluations of this frame-transport change.

Correcting curvature alone does not work: with every edge still traced with one width, a curvature-only σ made a 1 × 3 px render's outline worse, 0.106 mm against 0.038 mm. The level search across each edge needs its own σₙ.

The following table and directional-photo observations retain the original
slot-cap/scalar-corner implementation and its capture conditions. They are not
a fresh qualification of the covariance-aware nonparallel-corner model.

| Synthetic case (worst errors in mm; before in brackets) | Ø6 | Ø22 | Slot | Hole position | Outer |
| --- | --- | --- | --- | --- | --- |
| 1 × 1.6 px blur, overhead, clean | 0.0001 (0.0102) | 0.0016 (0.0008) | 0.0016 (0.0033) | 0.0015 (0.0015) | 0.0034 (0.0075) |
| 1 × 3 px, overhead, clean | 0.0126 (0.0673) | 0.0024 (0.0230) | 0.0071 (0.0336) | 0.0034 (0.0032) | 0.0058 (0.0378) |
| 1 × 3 px, 22°, clean | 0.0178 (0.0805) | 0.0023 (0.0301) | 0.0113 (0.0659) | 0.0028 (0.0043) | 0.0082 (0.0662) |
| 3 × 1 px, overhead, clean | 0.0122 (not traced) | 0.0010 | 0.0072 | 0.0033 | 0.0046 |
| 3 × 1 px turned 30°, overhead, clean | 0.0135 (not traced) | 0.0020 | 0.0094 | 0.0031 | 0.0053 |
| 3 × 1 px turned 45°, 22°, clean | 0.0276 (0.0978) | 0.0026 (0.0517) | 0.0155 (0.1147) | 0.0043 (0.0047) | 0.0045 (0.0485) |
| 2 × 1 px turned 37°, overhead, noise, JPEG, lens, light, shadow | 0.0008 (0.0179) | 0.0008 (0.0213) | 0.0081 (0.0312) | 0.0054 (0.0067) | 0.0077 (0.0459) |
| 3 × 1 px turned 45°, 22°, noise, JPEG, lens, light, shadow | 0.0005 (0.0613) | 0.0088 (0.0329) | 0.0344 (0.0770) | 0.0102 (0.0119) | 0.0268 (0.0308) |
| 1 × 3 px, 22°, noise, JPEG, lens, light | 0.0153 (0.0728) | 0.0072 (0.0322) | 0.0228 (0.0617) | 0.0051 (0.0077) | 0.0161 (0.0701) |
| The same with the 25 % shadow | 0.0115 (0.0466) | 0.0101 (0.0197) | 0.0511 (0.0289) | 0.0069 (0.0157) | 0.0294 (0.0457) |
| 3 px isotropic, 22°, clean | 0.0189 (0.0185) | 0.0059 (0.0252) | 0.0165 (0.0563) | 0.0053 (0.0056) | 0.0183 (0.0567) |
| The same with the 25 % shadow | 0.0141 (0.0158) | 0.0158 (0.0134) | 0.0244 (0.0315) | 0.0088 (0.0192) | 0.0277 (0.0305) |

"Clean" is without noise, JPEG loss, lens distortion, uneven light or shadow; "before" has slot end caps placed with their radius fixed (§7) and one blur width. The current figures keep the shadow correction's first harmonic round each ring (**Shadows**, below), which in this table changed the hole positions, and other figures by at most 0.0007 mm. On the qualification's other kinds of case, outline error in mm, with `main` in brackets: a sharp-cornered 120 × 70 rectangle is never traced by direction (two directions): 0.0036 (0.0036) isotropic, 0.0084 (0.0375) under 1 × 3 px through the widened window alone, and 0.079 (0.079) under 3 × 1 px turned 30°, which stays unsolved. With R8 corners, which face every way, it is traced by direction under those blurs: 0.0073 (0.0378) and 0.0047 (0.420). A 100 × 40 capsule: 0.0040 (0.0344) and 0.0034 (0.440). Motion streaks, which are not Gaussian, pass the adequacy rule and improve: a 6 px streak at 23° reads Ø6, Ø22, slot, position and outline 0.0029, 0.0057, 0.0086, 0.0030 and 0.0137 mm (0.122, 0.134, 0.268, 0.004, 0.356); a 10 px streak at 83° 0.0031, 0.0090, 0.0190, 0.0050 and 0.0257 mm (0.086, 0.018, 0.098, 0.004, 0.014). A defocus disk of 2.5 or 4 px is isotropic and keeps one width.

Under a wide blur and a soft shadow the slot got worse (under 1 × 3 px 0.051 mm, against 0.029 mm before), and the slot and outline still read up to 0.051 and 0.029 mm off: the shadow's slope is fitted over 2.5–5 σₙ, and with the blur measured right that window reaches the cast shadow's own edge, 1.6–1.9 mm out, where its light is not linear. The narrower windows of the underestimated blur had missed it. Hole positions had also read 0.021–0.027 mm off; that had another cause, now corrected (**Shadows**, below). The remaining errors are the paper model's: with the renderer's own shadowed paper light in place of the fitted lines, a test-only oracle, the noise-free 3 px photo with the shadow read its slot and outline 0.004 and 0.008 mm off, against 0.024 and 0.028 mm. A quadratic fitted to each profile's paper side does not get there. It read Ø6 0.078 mm off on the same photo without a shadow and without noise: at that blur the window reaches past a 6 mm hole's centre, and the profile there is not a quadratic. A thick, tilted part under a 1 × 3 px blur distorts its small holes 0.25–0.5 px RMS from round; one had been fitted as an arc closing on itself, which stopped the trace, and such a ring now keeps its traced outline. The covariance fit adds about 0.15 s to a trace (0.82 s against 0.67 s on the tilted photo).

If no sampled profile meets the blur estimator's contrast requirement, it returns
zero. The edge search then keeps the median-level method instead of attempting
the sloped Gaussian calculation with a zero divisor
(`test_a_zero_blur_estimate_keeps_the_median_level_search`, added in PR #39).
Zero here means the blur was not estimated; it does not prove a perfectly sharp
edge or establish that the Gaussian corrections are physically supported.

**Shadows.** A soft shadow makes the paper brighter away from an edge, with slope b per pixel. The blurred profile at the edge is (a + b₀)/2 + b σ/√(2π) for part light a and paper light b₀ at the edge. The level taken from the profile's ends, whose medians lie at 85 % of the half-window H, is (a + b₀ + 0.85 b H)/2. The crossing therefore moves out of the part by b (0.425 H − σ/√(2π)) divided by the edge's slope, about 2.7 σ² b / (b₀ − a) for H = 3.5 σ (`test_a_sloped_plateau_shifts_the_half_level_by_the_predicted_amount`).

The second edge pass therefore takes the paper's slope into the level (`sheet.half_level_search` with σ). A Gaussian-blurred step between two linear plateaus A(t) and B(t), with slopes a₁ and b₁, has the value (A(e) + B(e))/2 + (b₁ − a₁) σ/√(2π) at its edge e. The crossing of the profile with that level, as a function of t, is the edge itself. The steps:

- **Sampling:** each profile is sampled out to 5 σ, and the step's own blurred tail, (B − A) Q(|t|/σ), is removed from it.
- **Paper side:** a line is fitted to the profile beyond 2.5 σ. A shadow is cast on the paper, not on the part.
- **Material side:** a flat level is taken there, its median. A thick part's narrow side wall would read as a slope on that side.
- **Smoothing:** a line extrapolated from one profile is noisier than a median, while a shadow's slope changes slowly along an edge. So the correction from the median crossing to the sloped one is smoothed along each ring with a Gaussian of 20 points before it is applied, all but its first harmonic round the ring, which is kept where it is significant (below).

On exact sloped profiles the crossing lands within 0.002 px of the edge, flat plateaus included, where the end medians moved it by up to 0.18 px. On blurred discs of 7.5–55 σ radius, the traced radius is within 0.005 px of the blur-curvature series the radius correction assumes (`test_sloped_plateau_levels_put_the_crossing_on_the_edge`).

In the tilted rendered photo the shadow's effect is now small:

| Light the shadow removes | Ø6 | Ø22 | Slot | Outer |
| --- | --- | --- | --- | --- |
| None | 0.0002 (0.001 before) | 0.005 (0.004) | 0.006 (0.005) | 0.005 (0.004) |
| 25 % (the test photos) | 0.002 (0.012) | 0.008 (0.025) | 0.008 (0.025) | 0.009 (0.026) |
| 47 % (25 % darker in the saved photo) | 0.002 (0.024) | 0.009 (0.054) | 0.016 (0.061) | 0.010 (0.054) |

Over six noise seeds of the tilted photo with a 25 % shadow, the mean errors fell:

| | Ø6 | Ø22 | Slot | Hole position | Outer |
| --- | --- | --- | --- | --- | --- |
| Before | 0.0103 | 0.0244 | 0.0290 | 0.0044 | 0.0234 |
| After | 0.0026 | 0.0055 | 0.0126 | 0.0054 | 0.0046 |

Without a shadow they are unchanged within 0.002 mm. `test_a_soft_shadow_no_longer_pushes_edges_out` holds the 25 % and 47 % photos within 0.0125 mm on the holes and the outline. The model assumes the paper's light is linear over 2.5–5 σ; a shadow edge that falls inside that band is a curved trend, and is corrected only in part.

**A shadow's push on a hole's centre.** A shadow falls deeper on one side of a hole than on the other, so the slope correction differs round the hole; its first harmonic round the ring is the shift of the hole's centre. A Gaussian of s points keeps a ring of N points' first harmonic by exp(−(2πs/N)²/2), and a ring of fewer than 6 s points was given its mean alone. A 6 mm hole is 99 points round at the workbench's scale, so its centre kept the shadow's whole push. On the noise-free 3 px photo with the 25 % shadow, against the same photo without it, each Ø6 hole's shadowed wall read 0.04–0.06 mm further into the hole and its opposite wall up to 0.02 mm into the material, and the holes read 0.027 mm out of position. The Ø22 bore, 301 points round, kept 92 % of its harmonic.

`sheet._smooth_along_ring` therefore fits the harmonic, a cos θ + b sin θ with θ the angle round the ring in arc length, and smooths only the rest. Neighbouring profiles share pixels, so their noise is correlated; the variance V of the estimate (a, b) is taken from a jackknife over eight contiguous sectors of the ring. The harmonic is kept with the gain max(0, 1 − 9V/|d|²), where |d|² = a² + b²: one within three standard errors of zero is noise, and is dropped as before. At one standard error, max(0, 1 − V/|d|²), pure noise passes one time in three. In the six-seed runs that chose the threshold (the tilted 1 px photo), the mean hole position read 0.0042 mm as before, 0.0052 mm with the harmonic kept beyond one standard error, 0.0049 at two and 0.0045 at three. With a significant harmonic a ring of N ≥ 6 s points keeps exp(−(2πs/N)²/2) of it plus the gain times the rest (`test_ring_smoothing_keeps_a_significant_first_harmonic`).

| Photo (worst hole position error in mm) | Before | Now |
| --- | --- | --- |
| 3 px isotropic, 22°, clean, 25 % shadow | 0.0273 | 0.0088 |
| 2 px isotropic, 22°, clean, 25 % shadow | 0.0107 | 0.0038 |
| 1 × 3 px, 22°, noise, JPEG, lens, light, 25 % shadow | 0.0212 | 0.0069 |
| 3 × 1 px turned 30°, overhead, the same | 0.0220 | 0.0093 |
| 3 × 1 px turned 60°, 22°, the same | 0.0225 | 0.0101 |
| 1 px, 22°, the same (the test photo) | 0.0045 | 0.0045 |
| 1 px, 22°, the same with the 47 % shadow | 0.0125 | 0.0111 |

Sizes and the outline moved by at most 0.0008 mm. Over 12 noise seeds of the 1 × 3 px photo the mean hole-position error fell from 0.0253 to 0.0147 mm. Each feature's systematic error, its mean over the seeds, fell from 0.011–0.023 to 0.003–0.008 mm, while its random part grew from a standard deviation of 0.004–0.007 to 0.005–0.012 mm: the harmonic kept carries its own noise. On the 1 px photo over the same seeds the mean went from 0.0053 to 0.0055 mm, and overhead from 0.0053 to 0.0054 mm. Some noise-free renders without a shadow keep a small harmonic that is not a shadow's, and their hole positions moved by up to 0.0011 mm: a 6 px motion streak 0.0019 to 0.0030 mm, a 2.5 px defocus disk 0.0030 to 0.0040 mm. `test_a_soft_shadow_under_a_wide_blur_keeps_the_holes_in_place` holds the 3 px and 1 × 3 px photos under 0.014 mm.

## 4. Blur–curvature correction

A blurred curved edge's half-level contour moves toward its centre of curvature, for either polarity. Let X be the blurred position of a point at distance ρ from a disc's centre. Write the half-level condition P(|X| ≤ R) = ½ with tangential offset v ~ N(0, 1), and expand √(R² − σ² v²) in ε = σ/R. Using E v² = 1, E v⁴ = 3 and E v⁶ = 15 gives

> half-level radius = R − σ²/(2R) − (5/24) σ⁴/R³ + O(σ⁶/R⁵),

and inverting the series gives the correction used for every freely fitted arc and circle:

> R = r + σ²/(2r) − σ⁴/(24 r³) + O(σ⁶/r⁵).

`test_blur_curvature_series_and_its_inversion` evaluates the blurred disc by Gauss–Legendre quadrature, with x = R sin θ removing the square-root endpoint singularity. The integrator is first checked against the closed form at the centre, 1 − exp(−R²/2σ²), to 10⁻¹². The test then finds:

- the third-order coefficient converging to −5/24 (−0.20855 at R = 30σ);
- the residual after the second-order term falling as R⁻³ (slope −3.02);
- the inverted correction leaving an error of about 0.03 σ⁶/R⁵, which is 10–1000 times smaller than the first-order correction (for example 1.7 × 10⁻⁴ σ at R = 3σ).

Slot end caps take their radius from the spacing of their straight sides, which blur does not bias, and are not corrected.

**A fillet needs the blur in its fit, not a correction after it.** A fillet's centre is tied to its radius (§7): c(r) = c₀ + r v. Blur draws the traced arc toward its centre by s = σ²/(2R) and leaves the centre and both edges where they are. A fit of r alone cannot follow those points by shrinking, because shrinking r also moves the centre toward the corner. For a right-angle corner the mismatch along the arc, at angle θ from the bisector, is s + e (1 − √2 cos θ) for a radius error e. Least squares over the quarter turn gives e = +3.0 s: the fillet reads three shrinks too large, where a free circle reads one too small. The free-circle correction then added a fourth.

Fillets are therefore fitted to a circle of radius r − s(r) about c(r), with s(r) the series above, and are not corrected afterwards. Within about 2.5 σ of where the arc meets an edge the traced curve is neither arc nor line; those points are left out of the fit.

- On exact geometry (`test_a_fillet_fitted_with_the_blur_in_its_model_keeps_its_true_radius`), ignoring the blur leaves fillets 3.7 to 4.0 s large, and the fit with it is within 0.3 s.
- On rendered, blurred plates (`test_blurred_fillets_keep_their_radius_when_snapped`), R8, R4 and R2.5 corners read within 0.007 mm at blurs of 0.34 and 0.46 mm. Before, they read 0.027, 0.053 and 0.16 mm large.
- On the rendered photos of the test plate, the R8 corners' mean error fell from +0.029 to +0.005 mm, with every other dimension unchanged ([photo benchmark](photo-benchmark.md)).

**The scalar-Gaussian corner model.** The shrink s(r) is the disc's, and a fillet is a disc only in the middle of a long arc. Near its ends, and over the whole of a short arc, the blurred edge is neither arc nor line. At a 150° corner a fillet's arc spans only 30°, and on exact outlines the fit above read radii up to 19 s large, with nothing flagging them. Fillets are therefore refined against the blurred corner under an isotropic Gaussian hypothesis, `fitting.corner_level`. “Exact” in the implementation refers to that assumed corner model rather than an arbitrary camera image or certified numerical quadrature. It treats the corner as an arc of radius r about c, from angle a₁ through a sweep β < π, plus the two tangent lines running away from it. The corner is star-shaped from c. A ray at angle α leaves it at:

- R(α) = r across the arc;
- R(α) = r / cos(α − aᵢ) beyond each tangent point, for a quarter turn;
- nowhere (R = ∞) in the opening between the lines.

With q = c − p, b = q·e(α) and h² = |q|² − b², the radial integral of the Gaussian has a closed form. That leaves one smooth integral over the angle:

> u(p) = ∫ { [e^(−|q|²/2σ²) − e^(−((R+b)² + h²)/2σ²)] / 2π − b/(σ√2π) · e^(−h²/2σ²) · [Q(b/σ) − Q((R+b)/σ)] } dα,

with Q the upper normal tail. The integral runs over the directions within 9 σ of p (all directions when p is that close to c), by composite Gauss–Legendre broken at the arc's ends. It is 160 pieces when rays from c graze the edges and 40 otherwise. Q uses a Chebyshev erfc with fractional error below 1.2 × 10⁻⁷ (`test_erfc_matches_the_standard_library_within_its_stated_accuracy`). The traced edge is u = ½ whichever side the material is on, because the two blurred indicators sum to one.

The model is checked against a separate computation that shares no code with it. For a convex shape each vertical line meets the shape in one interval [bot(x), top(x)], so u(p) = ∫ φ(x − pₓ)[Φ((top − p_y)/σ) − Φ((bot − p_y)/σ)] dx. Around every corner of two filleted pentagons (corners of 60°, 90°, 120° and 150°; r from one to twelve σ), the two agree to 10⁻⁶ at the points the fit uses. A sharp right angle gives exactly Φ(x/σ)Φ(y/σ) (`test_blurred_corner_matches_closed_forms_and_an_independent_integral`).

**A supplied directional covariance.** The formula above describes the scalar
Gaussian branch. With an empirical rectified covariance S = LLᵀ,
`corner_level(..., covariance=S)` instead whitens the Gaussian and transforms the
geometry: a whitened unit ray e has reach R(arg Le)/|Le|. It compares successive
angular quadratures within bounded work, and an unresolved result is refused;
this is numerical convergence, not a certified error enclosure. A uniform
thickness-map scale k transports the matrix to k²S. A corner support containing
different such scales, or a failed covariance refinement, retains its whole
boundary as a traced outline when valid, rather than accepting a scalar
replacement. If the corrected trace is invalid, only a frozen accepted initial
fit sampled into lines may be used, after valid-ring, point-cap and
bidirectional whole-boundary checks within the existing geometric-fit
tolerance. This does not enlarge the standard `0.05 mm` polyline-detail
tolerance or use a generic topology-repair operator or component deletion.
Tube proximity cannot certify the invalid source's intended topology, and final
profile validation still applies; failure preserves normal profile refusal. A
notice identifies the nearby polygon and its undetermined radius. Other
supported rings can still be fitted. See the
[anisotropic-corner model](anisotropic-corners.md) for its frame, recovery and
finite-shape limits. The scalar results below retain their original conditions.

Each fillet's radius is then found by Gauss–Newton. The fit uses the arc's points and the edges' points out to 5 σ beyond the tangent points. Each point's residual is (u − ½)/|∇u|, its distance from the model's edge to first order. The fit's own derivatives carry four uncertainties into the radius's standard deviation r_sd:

- the residual noise;
- that noise's correlation along the edge, estimated on neighbouring straight edges by the heuristic 1 + 2Σρₖ, stopping at the first nonpositive lag or the smaller of 25 lags and one quarter of the residual count;
- a 5 % common blur-scale heuristic; in the covariance branch it scales all
  principal spreads together, rather than estimating covariance-entry or
  orientation uncertainty;
- a 0.03 px systematic error in each edge's position.

The correlation rule is bounded and heuristic. It differs from
[Geyer's initial-positive estimator](https://www.stat.umn.edu/geyer/mcmc/library/mcmc/html/initseq.html),
which truncates consecutive autocovariance pairs under reversible-chain
assumptions. The synthetic Monte Carlo check below supports its behavior in
that experiment; it does not validate general covariance coverage on photos.

A wide corner magnifies the last of these most. On exactly rendered edges the tracer is within 0.004 px at any angle and sub-pixel phase; the 0.03 px is an allowance for what rendering leaves out (demosaicing, JPEG, a lens blur that is not Gaussian) and has not been measured on real photos. A rendered octagon's 135° fillets read 0.022 mm small, within their reported ± 0.078 mm.

**Sharp corners.** Blur rounds a sharp corner too, and the same model at r = 0 describes it. A fitted fillet is kept only if its outline differs somewhere from the sharp corner's by twice the edge uncertainty. Otherwise the corner is traced as sharp. Its reported radius-resolution estimate is conditional on that model and heuristic noise floor, not a physical upper bound on rounding. The covariance branch must find an actual residual crossing before bisection; reaching a search cap alone establishes no bound and leaves the fit unresolved. In the earlier scalar regression, a sharp 120 × 70 mm plate at a 0.32 mm blur changed from fitted R0.4–R0.6 mm fillets to sharp corners with a conditional estimate below R0.23 mm (`test_sharp_corners_are_traced_sharp`).

**What the photo cannot resolve.** At the corner's midpoint a radius error moves the outline only (1/sin(θ/2) − 1) times as far: 1.0 at 60°, 0.41 at 90°, 0.15 at 120°, 0.035 at 150°. A radius whose r_sd exceeds 10 % of it is named in the trace's notes and warnings, with the outline's own uncertainty. The note says "or more", because once r_sd is a large share of r the fit is no longer linear and the spread is larger still.

Evidence:

- **Exact recovery** (`test_fillets_keep_their_radius_at_every_corner_angle_and_size`). On exact blurred outlines of filleted pentagons, with r from 2 to 50 σ, every fillet's outline is within 0.001 px. Every radius up to 120° is within 0.005 px + 0.1 %. The one exception is a 150° fillet of 2 σ, which moves the outline less than the edge uncertainty: it is traced as sharp, with a bound above its true radius.
- **Statistics** (`test_reported_fillet_uncertainty_matches_its_monte_carlo_spread`). Over forty tracings with 0.1 px noise correlated over four points, radii are unbiased within four standard errors. The reported r_sd is 1.3 to 1.4 times the observed spread. Without the measured correlation it would read under half.
- **Reporting** (`test_a_wide_fillet_the_photo_cannot_resolve_is_reported`). With 0.03 px of edge noise, R8 px fillets at 150° are reported in each of six tracings; the 60° and 90° corners never are.

| Corner | Before, r/σ < 5 | Before, r/σ ≥ 5 | Exact corner, r/σ < 5 | Exact corner, r/σ ≥ 5 |
| --- | --- | --- | --- | --- |
| 60° | 0.05 s | 1.1 s | 0.00 s | 0.00 s |
| 90° | 0.25 s | 2.5 s | 0.01 s | 0.01 s |
| 120° | 4.7 s | 8.0 s | 0.03 s | 0.03 s |
| 150° | 13 s | 19 s | 0.28 s | 0.22 s |

The table gives the worst radius errors on exact blurred pentagons (σ = 1.6 and 2.5 px, r = 5 to 80 px), in units of the shrink s. `scripts/corner_sweep.py` (`make corner-sweep`) traced them with its own continuum integral, independently of `corner_level`. With `--backend` it runs another checkout's fitting chain, which gave the "before" column. Smaller 150° fillets (r = 5 px at both blurs, and 8 px at σ = 2.5 px) were traced as sharp. Their bounds, 6.4, 8.0 and 8.04 px, are each above the true radius. The table's "before" is `main` with the large-radius and stub fixes. On rendered plates (`test_wide_corner_fillets_keep_their_radius_within_the_reported_uncertainty`), 150° R4 fillets read within 0.11 mm (0.13 mm before), inside their reported ±0.19 mm.

## 5. Camera pose and thickness parallax

**Focal length.** Remove the principal point (taken as the image centre, with square pixels). The columns of H = K[r₁ r₂ t] then satisfy two constraints at any overall scale of H:

> (h₁₁h₁₂ + h₂₁h₂₂)/f² + h₃₁h₃₂ = 0 (r₁ ⊥ r₂),
> (h₁₁² + h₂₁² − h₁₂² − h₂₂²)/f² + h₃₁² − h₃₂² = 0 (|r₁| = |r₂|).

`test_exact_focal_length_constraints` checks both exactly, in rational arithmetic, for random rational cameras built with Cayley-transform rotations. The pose uses the least-squares solution when the two individual estimates agree within 15 %. Otherwise, as in a frontal or cropped view, it uses the EXIF 35 mm-equivalent focal length. Failing that, a thick part's holes fix it (below), and failing those a typical 26 mm phone lens is assumed and reported. Over 200 random tilted cameras, focal length is recovered to 10⁻⁹ and the camera centre C = −Rᵀt to 10⁻⁶ mm (`test_camera_pose_recovers_random_cameras_and_refuses_frontal_ones`).

**Top-face parallax.** Seen from C, at height D above the nadir N, a face at height t projects onto the sheet plane by a central similarity:

> q = N + (p − N) · D/(D − t).

`test_exact_top_face_projection_is_a_homothety_about_the_nadir` verifies H₀⁻¹H_t equals exactly this homothety matrix, in rational arithmetic, for random cameras and thicknesses. A silhouette point whose material-outward normal faces away from N is formed by the top edge and is scaled back by (D − t)/D. A point facing N is formed by the bottom edge and is left unchanged. The same rule applies to holes, using the material's outward normal, which points into the hole.

**Camera height from the holes.** In a frontal view the sheet fixes neither the focal length nor, with it, the camera height D, and an assumed lens is typically 10 % off. A hole's silhouette is formed by the top edge on the side nearer the nadir and by the bottom edge on the far side, so the correction above scales only part of it. With a wrong height that part lands off the true circle by t |p − N| (1/D_true − 1/D), and the corrected hole is stretched along the direction from the nadir: 0.04 mm on a hole 50 mm out at 4 mm thickness and a 10 % error. Its roundness therefore measures D (`edges.roundness_focal`):

- For each focal length on a geometric grid of 10–200 mm (35 mm equivalent), the camera is posed from the sheet, every hole is corrected and fitted as a circle, and the squared residuals of the holes that are round at some focal length are summed, each hole's points counted.
- The least total is refined on a finer grid and by a parabola in log focal length. A minimum at an end of the grid, or not under half of both ends, determines nothing.
- A candidate needs at least 20 accepted points. It is retained only if its best circle-fit RMS passes the larger of the circle tolerance (max(0.03 mm, 0.15 σ)) and 1 % of its radius. The tested slot fails that gate; this is approximate-roundness screening, not a semantic classifier of every noncircular hole. A hole centred on the nadir has no stretch and adds nothing.
- The walls are then refined again with the new camera, and the trace reports the focal length found and how many holes gave it.

On exact silhouettes, the visible floor where a hole's bottom outline and its magnified top outline overlap, the focal length is recovered within 0.05 % (`test_the_camera_height_makes_thick_holes_round_again`). The holes are assumed round: a hole made oval along the direction from the nadir would bias the height.

**Walls narrower than the blur.** Where the bottom edge forms the silhouette, the visible wall lies between it and the top edge in a band of width w = (D/(D − t) − 1)·|(p − N)·n|. The profile is then a blurred two-step (sheet → wall → top face). For a wall whose step above the top face is 16 % of the sheet-to-top contrast in linear light, a single mid-level crossing is biased into the material by:

| w / σ | 0.25 | 0.5 | 1.0 | 1.6 | 2.5 | 4.0 | 6.0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bias / σ | −0.040 | −0.078 | −0.144 | −0.196 | −0.202 | −0.082 | −0.002 |

The bias grows roughly in proportion to the wall's share of the contrast. The rendered plate's dark walls (saved tone 78, top face 48, paper 236) have a 6 % share in linear light, so their bias is about a third of the table's.

The profile is therefore modelled as I(t) = C(1 − P₁) + B(P₁ − P₂) + A P₂, with P₁ = Φ((t + w − e)/σ) and P₂ = Φ((t − e)/σ). This is linear in the tones A (sheet), B (wall) and C (top face) for a given edge offset e. Each candidate e is solved by least squares (variable projection), and the residual minimum is refined by a parabola. For a fixed e, with A and C fitted for each B, the residual is exactly a quadratic in the wall tone, c₀ + c₁B + c₂B². Its coefficients are found once per point and offset (`edges._wall_tone_parabolas`); a free fit takes the vertex, and c₂ ≥ 0 is what is left of the wall term after projecting out the other two. Profiles are read by cubic sampling: the fit uses every sample, and bilinear sampling's error at the shoulders of a blurred edge, up to 2.1 grey levels in 200 at σ = 1.7 px against cubic sampling's 0.33, biased it.

As w → 0 the wall term tends to (B − C)(w/σ)φ, which is indistinguishable from a shift of e: the wall tone and the edge position are confounded. The fit is therefore made well-posed in three steps:

- The wall tone is measured only where bands are at least 2.5 σ wide, where a free fit recovers it. Where fewer than 30 points have bands that wide, one tone shared by all bands of 1–3.5 σ is estimated instead (below).
- That tone is then held fixed for the narrower bands.
- The refinement is applied with full weight for 1.5–2.5 σ, tapering to zero at 0.5 and 3.5 σ so the boundary stays continuous.

On exact profiles the fixed-tone fit is unbiased within 0.01 σ. With half a grey level of noise on a band of 0.5 σ, the free fit's edges scatter by 0.14 σ (SD) and its tones by 53 levels, while the fixed-tone fit keeps every edge within 0.01 σ (`test_two_step_wall_model_is_unbiased_with_a_known_wall_tone_and_degenerate_without`). The taper was chosen on 2026-11-10 with an earlier renderer that mixed tones on the saved scale: refinement over the whole 0.25–4 σ range made strongly tilted shots worse, because soft shadow and uneven wall shading break the flat-tone model, and the tapered 1–3 σ range was better on every feature at 9° and on four of five at 22°. That comparison has not been repeated in linear light.

On the 9° photo of the 4 mm plate (2400 × 1800, linear light), the model's effect depends on the shadow:

| 9° tilt, 4 mm thick | Ø6 | Ø22 | Slot | Hole position | Outer |
| --- | --- | --- | --- | --- | --- |
| No shadow, wall model | 0.0012 | 0.0016 | 0.0174 | 0.0051 | 0.0060 |
| No shadow, without it | 0.0101 | 0.0143 | 0.0395 | 0.0058 | 0.0122 |
| 25 % shadow, wall model | 0.0073 | 0.0184 | 0.0212 | 0.0058 | 0.0234 |
| 25 % shadow, without it | 0.0029 | 0.0051 | 0.0303 | 0.0066 | 0.0233 |

Without a shadow the model cuts the hole errors about eightfold. With the shadow, the uncorrected trace read these holes better only because two biases cancelled: the dark wall pulls the edge into the material and the shadow pushed it out. That table was recorded before the sloped paper levels of §3. With them, and with the blur of §3 measured by cubic sampling, the shadow's push is gone, and the wall-model trace of the same photo reads 0.0001 (Ø6), 0.0047 (Ø22), 0.0074 (slot), 0.0069 (position) and 0.0074 mm (outer) with the shadow, and 0.0012, 0.0033, 0.0056, 0.0032 and 0.0067 mm without it (with the slot end caps of §7 placed with their radius fixed). With a lighter wall (saved tone 110) the model wins in both cases; with the shadow it takes Ø6 from 0.040 to 0.006 mm.

**Near-frontal photos.** Seen from nearly straight above, the walls are under 2.5 σ almost everywhere, and a free fit cannot measure their tone. One tone for the whole part is still identifiable from many narrow bands (`edges.pooled_wall_tone`). For each candidate tone B, every band's edge offset is fitted with B fixed, and the total residual over up to 160 bands of 1–3.5 σ is least at the true tone. Each band's residual is a quadratic in B for every offset, so the total costs little to evaluate. It is taken on 17 tones from black to the image's 99.5th percentile, then on a finer grid around the least value, whose minimum is refined by a parabola. The edges facing the camera are then refined as in a tilted photo, and the trace notes that the walls' tone was estimated jointly.

The tone is not trusted in three cases: fewer than 30 bands qualify, the least total lies at an end of the grid, or it is not under 0.8 times both ends. The trace then notes the old bound instead: edges facing the camera may read up to 0.2 σ into the part. That figure is the table's maximum, so it assumes a wall share of at most 16 %; a brighter wall can exceed it. Bands under σ never take part, because there a wall differs from an edge shift only at second order in w/σ. On noise-free profiles with bands under 0.4 σ, cubic sampling's 0.3-level error alone made a false minimum that passed the test above: a tone of 186 for 15, which moved edges by 0.18 σ.

On exact profiles with bands of 1–3.5 σ, a wall tone of 15 is recovered as 15.11, and fixing it puts every edge within 0.001 σ. With a grey level of noise the tone stays within 10 % of the wall's contrast with the top face. With 10 levels of noise on bands of 1–2 σ the residual is flat, and the estimate says the tone is not determined (`test_one_wall_tone_shared_by_narrow_bands_is_recovered`).

On rendered photos of the 4 mm plate (worst errors in mm; Ø6, Ø22, slot, hole position, outer):

| Photo | Before | Joint wall tone |
| --- | --- | --- |
| 5° tilt, 25 % shadow | 0.0205, 0.0130, 0.0466, 0.0125, 0.0072 | 0.0068, 0.0025, 0.0184, 0.0062, 0.0063 |
| 5° tilt, no shadow | 0.0161, 0.0134, 0.0448, 0.0111, 0.0028 | 0.0042, 0.0053, 0.0189, 0.0052, 0.0020 |
| Overhead, focal length from EXIF | 0.0159, 0.0099, 0.0305, 0.0164, 0.0203 | 0.0009, 0.0049, 0.0105, 0.0087, 0.0193 |
| Overhead, phone lens assumed | 0.0505, 0.0138, 0.0475, 0.0149, 0.1048 | 0.0361, 0.0074, 0.0257, 0.0256, 0.1058 |
| Overhead, height from the holes | (lens assumed, as above) | 0.0077, 0.0054, 0.0135, 0.0078, 0.0047 |

"Before" includes the blur measured by bilinear sampling. With the assumed lens alone the holes and the slot improve, but hole positions read worse: the guessed camera height made the parallax correction misplace each hole's near side, and the wall's pull on its far side had partly offset that. With the height from the holes (above) the positions read 0.0078 mm and the outline, which the same guess had left 0.10 mm off, 0.0047 mm. The tone search adds about 0.05 s to a trace, and the height search about 0.1 s.

## 6. Sheet proportions check

Scaling the stated plane axes by (a, b) multiplies the columns of H by a and b. That cannot change whether r₁ and r₂ are orthogonal, so the orthogonality constraint alone gives a focal length that is independent of the stated sheet size. With that focal length, the ratio of the first two column norms of K⁻¹H equals (true aspect)/(stated aspect). In a frontal view the ratio barely depends on the focal length, so the check works for any view.

Over 200 random cameras, the focal length is invariant and the ratio equals a/b to 10⁻¹² (`test_sheet_proportions_are_measurable_and_focal_length_ignores_them`). On rendered photos the measured ratio matched within 0.01 % at every tilt from 0° to 22°. An A4 photo traced as US Letter reads 0.9151 (theory 0.91503), and a custom width entered 1 % too large reads 0.9901. Every trace reports the check. A difference above 1 % becomes a visible warning, because every dimension scales with the chosen sheet.

## 7. Lines, arcs and circles

**Initial-fit source support.** A small radial or line residual alone does not
establish boundary coverage. Whole circles now require an enclosed center, and
the complete assembled initial boundary must pass a bounded source-tube check.
Rejected subpixel profiles remain missing measurements; the complete classified
contour supplies separate coverage, with a positional allowance measured from
matched coarse/fine points rather than from the candidate's mismatch. Fits that
lack support retain the traced polyline. The [repair record](validation/fit-support.md)
derives the check and preserves the original counterexamples.

This check precedes design-intent snapping and Gaussian reconstruction. A
correctly deblurred sharp apex intentionally differs from the blurred contour;
the initial-fit check is not a final physical accuracy or model-adequacy test.
Continue to compare important boundaries and independent dimensions.

- **Circles.** A Kåsa algebraic fit, then Gauss–Newton on geometric distance. A circle is accepted when its RMS residual is below max(tol, 1 % r) and its largest residual below four times that. The 1 % allowance keeps a slightly out-of-round hole a circle, but a rounded polygon can pass it too: a 12-gon on a 45 mm circle with R12 corners lies 0.39 mm RMS from one circle, eight times the line tolerance. A ring that passes only by that allowance is therefore also described as lines and arcs, and that description wins when it has straight edges and its worst residual is under a third of the circle's (`test_a_rounded_polygon_close_to_a_circle_is_not_taken_for_one`). A disc, and a hole 2 % out of round, stay circles. The low-level `fit_circle` test recovers noise-free arcs of 20–360° exactly, and that optimizer is equivariant under rotation, translation and scale (`test_circle_fit_is_exact_and_similarity_equivariant`). Its radius bias over 2000 noisy circles is within σ²/R + 4 standard errors (`test_geometric_circle_fit_bias_is_second_order_in_noise`).
- **Lines and arcs.** Douglas–Peucker breakpoints at 1.5 × tolerance split each ring. Breakpoint edges of at least `min_line` (2.5 % of the part, clamped to 1–3 mm) with a total-least-squares RMS below tolerance are taken as lines, unless they turn out to be chords of an arc (next item). Consecutive line edges that still fit one line are merged, and runs between lines become arcs. An "arc" between two lines running the same way is a noise bump and is merged into one line. Points within tolerance of a neighbouring line are trimmed before an arc's fit, because tangent-region points pull its centre. An arc too small to trim that way gives the straight run at each end back to its line (the item after next). Rings that cannot be described within tolerance stay as traced polylines.
- **Chords that pass for lines.** A chord of length c on an arc of radius R bows c²/(8R) from the arc, and a breakpoint is placed only where that exceeds 1.5 × tolerance. Breakpoints therefore leave chords of up to √(12 R tol), and those chords are straight enough to pass the line test. Once √(12 R tol) reaches `min_line`, an arc would be cut into short straight pieces. With `min_line` at 3 mm that is from R25 at the 0.03 mm tolerance floor and from about R15 at a 0.34 mm blur. On a part under 40 mm across, where `min_line` is 1 mm, it is from about R3.
  - Each edge taken as a line is therefore tested against the circle fitted to its neighbours. The neighbours are the arc edges that adjoin it. Where a side has none and the others are too straight to define a circle (a line fits them within tolerance), the line edge on that side stands in. The edge is a chord when its own points lie on that circle to an RMS of half the tolerance.
  - Edges are tested in order round the ring until none changes, so an arc grows chord by chord and later chords are judged against the arc so far. An edge absorbed on its own, still between two lines, becomes a line again: one chord is not an arc.
  - A straight edge is absorbed only if it lies on its neighbours' circle to half the tolerance. A slot side, or any flat between two arcs with different centres, does not, because no one circle follows both arcs and the flat. A flat that runs tangentially off the end of an arc leaves the circle by L²/(2R) at its far end and is kept once it is about as long as the arc's longest chord. A shorter one leaves the circle by only a few times the tolerance, the breakpoints often do not separate it from the arc, and it is absorbed. Facets are absorbed only where the run stays within about 1.5 × tolerance of one circle.
  - On exact geometry, plates with R5 to R400 corners come out as four lines and four arcs with every radius and centre exact to 10⁻⁶ (`test_arc_chords_long_enough_to_pass_for_lines_are_recovered_as_one_arc`). A stadium's 4 mm sides between R30 ends, a 4 mm flat off the end of an R60 arc and a corner of three 4 mm facets stay lines (`test_straight_edges_no_longer_than_an_arcs_chords_stay_lines`, `test_one_chord_between_two_lines_is_not_an_arc`).
  - On rendered, blurred plates, R20 and R30 corners at a 0.34 mm blur, R25 at 0.23 mm and R6 on a 36 mm plate read within 0.01 mm, fitted freely and as fillets (`test_corners_whose_chords_pass_for_lines_are_fitted_as_arcs`). A corner turned by five 3.2 mm facets, which bow twice the tolerance from a circle at that blur, stays five lines (`test_blurred_facets_are_not_taken_for_an_arc`). On rendered photos of the test plate with R20 and R25 corners the outline is four lines and four arcs, where it was a polyline of 67 or 77 segments (`test_large_corner_radii_trace_as_arcs`).
  - Two chords. An arc that the breakpoints cut into only two chords, each passing for a line, goes back to being two lines under the rule above. That happens at wide corners and under a wide blur: on exact outlines (§4) a 150° R40 px corner at σ = 2.5 px and a 120° R12.5 px corner lost their arcs, which moves the outline 1.4 and 1.9 px. Before edges are merged, each longest run of two or more edges is therefore marked curved when it contains a line and meets three conditions (`fitting._curved_runs`). One circle fits it, with RMS under half the tolerance and worst point under 1.5 tolerances. One line does not. And each of its line edges is itself bowed along that circle: its own points lie closer to the circle than to their own best line. A chord of an arc bows by L²/8r and passes. A straight facet or flat does not, however well the run as a whole fits a circle, so the facets and flats the rule above keeps as lines stay lines (`test_an_arc_cut_into_two_chords_stays_one_arc`).
- **Small arcs, sharp corners and stubs.** An arc is trimmed as above only when at least eight of its points are clear of its lines. A smaller one is fitted to all of its points. Most of these are sharp corners that only the blur rounds: under a blur of σ the outline of a sharp corner leaves each edge within about 3 σ of the corner.
  - A breakpoint can fall anywhere on a straight edge. The ring's first point is always one, and so is the farthest point from a chord that runs parallel to the edge. Within `min_line` of a corner it cuts off a stub that is too short to be a line, and the stub was fitted with the corner as one arc. That arc either failed the residual check, which left the whole ring a polyline, or passed it with a radius many times too large.
  - Each line beside a small arc therefore runs on to the last of the arc's points that lies within half the tolerance of it, and the arc is fitted to the points between. Fewer than three points define no circle: the arc is dropped and its two lines meet at a corner.
  - The test is made on single points and not on whole breakpoint edges, because a stub often runs on into the rise of the corner within one edge. Two tests on edges were tried first. Joining a short edge to the line beside it when the two together still fit one line within tolerance ends the polylines, but a long line outweighs what it takes in: on rendered 60 × 40 mm plates that turned 15 of 24 R1 corners into sharp ones and left points 9 to 14 tolerances off a line in its fit. Testing the short edge's own points against the line, more strictly the shorter it is, spared the fillets but left a stub wherever it shared an edge with the rise: on nine outlines from rendered photos of a sharp-cornered plate the size was still up to 1.5 mm off, against 0.05 mm with the test on points.
  - Larger arcs need none of this. Their points near a line are trimmed already, a stub's among them.
  - On exact geometry a rectangle is four lines that meet at its corners wherever its ring starts, where a stub had been an arc with a radius in the millions (`test_a_stub_cut_off_by_the_rings_first_point_is_part_of_its_edge`). A tiny one-step corner cut may remain its measured polyline when joining the fitted lines would exceed the source-support allowance; it must not become an invented large arc (`test_two_points_between_two_lines_are_a_corner`). On the exact outline of a blurred sharp-cornered plate, the corners' radius is 1.7 to 1.9 σ at 25 ring starts, where it had been 1.7 to 20 σ, and 1.6 to 2.2 σ with edge noise of a fifth of the tolerance (`test_a_blurred_sharp_corner_is_fitted_alike_wherever_the_ring_starts`).
  - On rendered plates with sharp corners, an R30 arc and a stub of 2.4 mm, the initial fit is five lines and five arcs with the candidate R30 radius within 0.03 mm, where fitting had previously failed (`test_a_stub_cut_off_a_straight_edge_is_fitted_as_part_of_it`). Final assembly separately requires actual circle-consistent joins; incompatible free candidates retain a bounded source outline rather than exporting a different circle. Rounded corners with eight or more clear points are fitted exactly as before.
- **Lines on their straight parts.** Douglas–Peucker hands a line the start of the next arc, up to where the arc leaves it by 1.5 tolerances; for a large radius that stretch is long. Fitted with it, the edges beside R80 px corners were tilted by 0.24°. Snapping then kept the tilt, and the fillets built tangent to those edges were up to 0.9 % off in radius. Each line is therefore refit before snapping on its points short of the neighbouring arcs' tangent points (less 3 σ in the trace): by total least squares, or for a snapped line by offset only.
- **Design intent** (optional, reported):
  - The current corner/cap classifier treats lines as near-parallel when `abs(cross(d1,d2)) < sin(5 degrees)`. Opposite traversal selects the inherited slot-cap path; same-direction near-parallel neighbors are skipped. This heuristic includes small tapers; it does not establish true parallelism.
  - Lines within 0.6° of the dominant axis are made exact. The axis is the circular mean of 4θ, invariant to line direction and to quarter turns (`test_dominant_axis_ignores_line_direction_and_quarter_turns`).
  - Outside that near-parallel classification, an arc between lines becomes a fillet whose centre lies on the corner bisector, c(r) = c₀ + r v. Only r is fitted against the blurred corner (§4), using the full supplied covariance when available and retaining conditional heuristic radius diagnostics. A supported fillet indistinguishable from the sharp model is traced sharp. An unresolved covariance fit normally retains the affected traced boundary; an invalid corrected ring may use only the bounded line-only recovery described above, without determining a radius. c(r) stays at distance exactly r from both lines for every r, which is verified in rational arithmetic (`test_exact_fillet_centre_is_tangent_to_both_lines_for_every_radius`). Over 300 noisy scalar-model trials this constrained fit has less than half the spread of a free three-parameter arc (`test_tangent_constrained_fillet_fit_is_more_precise_than_a_free_arc`).
  - When a changed radius moves a constrained arc's centre, its angular sweep witness moves with it. This prevents an unintended switch to the complementary sector while preserving genuine major arcs; [the regression record](validation/fillet-sweep.md) separates this representation repair from remaining blur-model mismatch.
  - For truly parallel lines the slot-cap model has radius half the spacing, which blur does not bias, and centre on the mid-line. The current heuristic also admits near-parallel lines; its fixed-spacing model then remains an approximation, without an exact tangency or radius claim. The centre's place along the slot is then fitted with that radius fixed, to the blurred radius r − s(r) and without the points within 2.5 σ of the tangent points (`fitting._end_cap_axial`). It used to come from the arc's free three-parameter fit. Over a half turn the free fit couples the centre's axial place with its own radius: the Fisher information gives the axial centre a variance of 1/(½ − (2/π)²) = 10.6 noise units, against 2 with the radius fixed, 2.3 times the standard deviation. On blurred slot outlines with correlated noise the slot length's spread fell from 0.032 to 0.017 px, and with one whole side moved out by 0.1 px the length is 0.064 px off, where it was 0.104 px (`test_slot_end_caps_are_placed_with_their_radius_fixed`). On a thick part the two flanks of a cap differ, one traced on the top edge and one beside a visible wall, which had moved the free fit's centres apart: the 24 × 8 slot read 0.018–0.022 mm long at 5° and 9° tilt.
  - Radii within 3 % become equal.
  - The detected straight-edge direction supplies a common rigid display/profile rotation. This source-derived frame can remain available when final analytic assembly retains a boundary as lines; rotation does not make that retained outline snapped. Width is the span in the chosen frame, and an uncorrected thick-part preview remains provisional.
- **Final circle-consistent joins.** [Canonical assembly](curved-joins.md) uses actual line/circle intersections, ordered source witnesses and a selected cyclic traversal. Its emitted arc must reconstruct the stored circle. Initial support may use a historical eligibility proxy, but final export cannot use that proxy as the fitted circle. An unavailable join retains only the affected boundary as traced LINE geometry with a targeted notice; invalid retained profiles are refused. Final snapping, radius and fit-count notes describe only accepted geometry. The [current source-bound record](validation/directional-free-arcs.md) separates these representation checks from conditional optical-model research.
- **Sampling.** Polygon rings target a stated sagitta. When the required sample count is below the implementation's segment cap, each chord stays within that tolerance and the area error is bounded by perimeter × tolerance. `test_sampled_arcs_stay_within_the_requested_sagitta` checks the plate fixture at 0.1, 0.01 and 0.001 units; it does not establish a universal bound for every imported radius. Trace sampling, CAD validation sampling and OpenSCAD use finite sample caps. [Export limits](exports.md#openscad-editable-profile-extrusion) explain the OpenSCAD target separately from the analytic STEP/DXF representation.

The fitted CAD face area equals both the Green's-theorem area of its segments and the plate's closed-form area. The theorem's form is the shoelace sum over segment endpoints plus r²(φ − sin φ)/2 for each arc. The solid's volume is area × thickness, all to 10⁻⁹ (`test_greens_theorem_area_matches_the_cad_kernel_and_the_design`). DXF arc angles reproduce every arc's endpoints (`test_dxf_arcs_reproduce_their_endpoints`).

## Results on rendered photographs

The plate is 120 × 70 mm with R8 corners, 4 × Ø6 holes, a Ø22 bore and a 24 × 8 slot. Figures are maximum absolute errors in mm, measured on the fitted geometry after a rigid fit of the six hole centres; no scale is fitted. Runs recorded on 2026-11-11 with sloped paper levels and the blur measured by cubic sampling (§3), the jointly estimated wall tone of near-frontal photos (§5), slot end caps placed with their radius fixed (§7), and exact pixel coverage (`synthetic.coverage`), light mixed in linear light, saved through the sRGB curve, and a shadow that removes 25 % of the light:

| Photo | Ø6 | Ø22 | Slot | Hole position | Outer |
| --- | --- | --- | --- | --- | --- |
| 2400 × 1800, overhead, ideal light | 0.0001 | 0.0022 | 0.0033 | 0.0015 | 0.0009 |
| 2400 × 1800, 22° tilt, lens, shadow | 0.0036 | 0.0077 | 0.0073 | 0.0044 | 0.0074 |
| 2400 × 1800, 22° tilt, 4 mm thick | 0.0038 | 0.0050 | 0.0038 | 0.0073 | 0.0074 |
| 2400 × 1800, 9° tilt, 4 mm thick | 0.0001 | 0.0047 | 0.0074 | 0.0069 | 0.0074 |
| 2400 × 1800, 5° tilt, 4 mm thick (wall tone estimated jointly) | 0.0068 | 0.0025 | 0.0021 | 0.0054 | 0.0063 |
| 4000 × 3000, overhead, ideal light | 0.0002 | 0.0015 | 0.0053 | 0.0031 | 0.0007 |
| 4000 × 3000, 22° tilt, lens, shadow | 0.0001 | 0.0006 | 0.0020 | 0.0019 | 0.0002 |

Rerun on 2026-11-12 with the shadow correction's first harmonic kept (§3), every figure is within 0.0005 mm of this table; against `main` at `f1679bb` only the 9° and 5° rows moved, the 5° hole position most (0.0054 to 0.0059 mm). The 2400 × 1800 rows other than 5° are the cases in `tests/test_sheet_reference.py`. The 5° row is `render(tilt=(5.0, -2.0, 4.0), thickness=4.0)`, and the 4000 × 3000 rows add `size=(4000, 3000)`, which shows the same field of view in more pixels. Before the cubic blur measurement, the joint wall tone and the end caps' fixed radius, the 5° row read 0.0205, 0.0130, 0.0466, 0.0125 and 0.0072 mm and the 9° slot 0.0175 mm. No other figure was more than 0.002 mm better than now. The largest such change is the 4000 × 3000 overhead slot, 0.0034 mm then and 0.0053 mm now, which is within the slot length's spread between noise seeds: over three more seeds it read 0.0015, 0.0004 and 0.0042 mm, against 0.0020, 0.0028 and 0.0080 mm before.

Traced on saved values, as before this correction, the same overhead photo gave 0.263 (Ø6), 0.250 (Ø22), 0.257 (slot) and 0.353 mm (outer): the tone-curve bias of §3. The table recorded on 2026-11-10 did not show it, because that renderer mixed tones on the saved scale.

The same full-frame photos cannot be traced without a reference at all ("The outline touches the image edge"). Cropped inside the sheet by hand and traced the original way, with the best two-point scale a user could supply (endpoints exactly on the two diagonal Ø6 hole centroids, 108.24 mm apart), the 2400 × 1800 tilted photos gave the errors below. They were recorded on 2026-11-10 with the earlier renderer and have not been repeated; perspective dominates them.

| Photo | Ø6 | Ø22 | Outer |
| --- | --- | --- | --- |
| 22° tilt, thin | 1.041 | 0.811 | 2.808 |
| 22° tilt, 4 mm thick | 2.327 | 1.801 | 1.754 |

`tests/test_sheet_reference.py` asserts limits of 0.03 (Ø6), 0.05 (Ø22), 0.06 (slot), 0.05 (position) and 0.05 mm (outer) on the 2400 × 1800 cases, plus the 0.2 σ narrow-wall bound for frontal thick views, and 0.01 (Ø6 and Ø22) and 0.025 mm (slot) on the 5° photo. Those limits are regression guards, not accuracy claims.

## Limits

- The stated sheet size sets the scale. ISO 216 allows ±2 mm on 297 mm (about 0.7 %). The proportions check catches a wrong choice or a mistyped side, but not a uniformly wrong size: measure your sheet once.
- The sheet must be flat, fully visible, and contrast with the surface under it. The part must sit wholly on the sheet with a margin, and its brightness must differ from the sheet's.
- The photo is decoded as sRGB. A camera's own tone mapping is not undone; §3 gives the cost of a plain-gamma camera (0.02 mm at 2.2, 0.11 mm at 1.8).
- An edge carried by colour and not by brightness is measured on the colour channels. A JPEG stores colour at lower resolution than brightness, and that case is tested only on lossless renders.
- A soft shadow beside an edge is corrected where the paper's light is close to linear over 2.5–5 σ (§3): on the rendered photo, Ø22 reads 0.008 mm off under a shadow removing a quarter of the light, where it read 0.026 mm. A sharper shadow, or one whose edge falls within a few σ of the part, is corrected only in part. Diffuse light is still best.
- One radial coefficient about the image centre; no tangential distortion or k₂. Cropped photos and screenshots break the principal-point assumption. An inconsistent sheet focal estimate initially falls back to EXIF or an assumed lens; with entered thickness, suitable holes can replace the assumed height (§5). Hole roundness does not repair a wrong principal point or a mismatched lens model.
- Vertical walls of constant thickness. Chamfers, draft, countersinks and shiny edges are not modelled. Where even one tone shared by the narrow walls is not determined (§5), the tabulated wall-share cases of at most 16% reach about 0.2 σ into the part; brighter walls can exceed this figure. It is not a general error bound. Overhead with no known focal length, qualifying off-center holes assumed round can determine camera height if the search accepts a sufficiently identifiable minimum (§5). Otherwise a typical lens is assumed. One earlier rendered example was 0.10 mm off with that assumption; this is not a general error bound.
- Fitted lines, arcs and circles are descriptions of the photograph, not recovered design intent; review the snap list. Split output uses the traced polygon.
- A run of short straight facets that stays within about 1.5 × tolerance of one circle is fitted as an arc, and so is a flat shorter than an arc's longest chord that runs tangentially off its end: neither can be told from that arc's own chords (§7). A large-radius corner whose traced edge wanders from its circle by more than half the tolerance over one chord is not recognised as one arc, and its outline stays a polyline.
- With snapping on and a supported common Gaussian frame, a sharp corner between two fitted edges can be traced sharp by the corner model (§4). Mixed scalar corners retain only a warned, radius-undetermined approximation; mixed supplied-covariance corners are withheld. An unconstrained fit to a blurred sharp corner can instead produce an arc about 1.8 times the edge blur, 0.5 mm at a 0.3 mm blur in an earlier example. That arc is the blur's rounding, not the part's. The generic radius correction of §4 can enlarge it about its centre and leave it proud of the neighboring edges; the earlier outline error was 0.04–0.1 mm across that corner.
- A straight edge shorter than `min_line` is a line only as part of a longer one. A chamfer under `min_line`, or a short flat between two arcs that a breakpoint cuts in two, is fitted as an arc of a radius far larger than anything in the part (§7).
- A fillet at a wide corner is barely constrained by its outline (at 150° the outline moves 0.035 times a change of radius). The trace names radii it cannot determine and corners it traced sharp, with a conditional model-resolution estimate; measure those if they matter. With snapping off, short free arcs at such corners do not use the full corner forward fit. The generic circular-edge series is still applied and those arcs are named in the notes; that approximation does not remove the corner-model mismatch.
- The fillet uncertainty assumes a Gaussian blur and a 0.03 px systematic edge error; a real lens's blur is not exactly Gaussian.
- A blur whose principal spreads differ by more than 15 % is measured as a covariance and traced by direction when edges face at least three ways and the covariance explains each (§3). A part whose edges face two ways keeps one width, and under a blur turned from its edges it is not corrected (a sharp-cornered rectangle under 3 × 1 px turned 30° reads 0.079 mm off). Under a soft shadow and a blur wider than about 0.35 mm the shadow's slope is fitted where its light is curved, and the slot can read up to 0.05 mm off and the outline 0.03 mm (hole positions 0.006–0.014 mm). A blur that varies across the photo and sharpening are not modelled; every case here comes from this repository's renderer.
- Initial circle/piece fits require [source support](#7-lines-arcs-and-circles). Sparse, unsupported or over-budget fits retain the polyline. Later design-intent and Gaussian corrections remain model-dependent; the support test does not certify their physical accuracy.
