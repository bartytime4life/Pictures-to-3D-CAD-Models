# Resolving the reference sheet's physical axes

[Reference-sheet method](../reference-sheet.md) · [Engineering checks](../engineering-model.md)

## Defect and consequence

The former calibration assigned the sheet's long dimension to the pair of edges
that looked longer in the photo. Perspective does not preserve lengths or their
ordering. When the long side is sufficiently foreshortened, this assigns the
wrong millimetres to both axes, producing an anisotropic distortion that a later
uniform width adjustment cannot undo.

For an A4 sheet whose true axes are 210 × 297 mm, swapping them multiplies one
axis by `297 / 210` and the other by `210 / 297`. A reserved 100 × 70 mm rectangle
therefore becomes **141.4286 × 49.4949 mm**. The product of these scale factors is
one: an area or volume check alone can miss this error entirely. Independent
lengths, hole diameters and aspect ratios are necessary checks.

## Camera constraints

First fit a homography `Q` from the unit square to the four undistorted sheet
corners. Subtract the assumed principal point from its first two rows. Let the
first two columns of this shifted homography be `u` and `v`. For a pinhole camera
with square pixels, zero skew, centred principal point and focal length `f`,

```
K = diag(f, f, 1)
(K^-1 u) dot (K^-1 v) = 0
norm(K^-1 u) / norm(K^-1 v) = sheet_width / sheet_height.
```

These are the orthogonality and equal-norm calibration constraints in
[Zhang's calibration report, section 2.3, equations 3–4](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr98-71.pdf).
The same paper is indexed in [SciSpace](https://scispace.com/papers/a-flexible-new-technique-for-camera-calibration-4wlhr0wn09).
The constraints are used here to resolve an axis assignment, not to claim a full
multi-view camera calibration from one photo.

Orthogonality gives

```
f² = -(u_x v_x + u_y v_y) / (u_z v_z).
```

This equation does not use the stated sheet aspect ratio: rescaling either
column cancels between numerator and denominator. With an adequately supported
positive focal estimate, the metric column norms determine which physical side
is longer. Usable original-image focal metadata supplies another conditional
route. When both sources are usable, conflicting assignments stop the trace;
otherwise metadata takes precedence. This does not establish that metadata from
a cropped or processed photo is correct.

### Sensitivity to corner placement

A merely nonzero orthogonality constraint can still be unusably sensitive. The
initial fix at `e9bb5c8` required a normalized numerator of at least 0.001, but an
independent review reproduced a failure just outside its camera grid: A4 at
`(75°, 0.1°, 4°)`, true focal 5000 px, distance 2000 mm, and seeded 0.05 px edge
coordinate noise. It inferred 2224.274 px and accepted the wrong axes. The
reserved 100 × 70 mm rectangle became **141.4358 × 49.4930 mm**, yet the independent
proportion check was **0.997028**, within its 1% warning threshold. A residual
check does not cure an ill-conditioned inverse problem.

`backend/calibration_bounds.py` replaces that numerator threshold with
outward-rounded interval arithmetic. Each of the eight fitted, undistorted
corner coordinates varies independently within a declared box. For corner
coordinates `(x0,y0),...,(x3,y3)`, centred on the assumed principal point, write

```
dx1 = x1-x2; dx2 = x3-x2; dx3 = x0-x1+x2-x3
dy1 = y1-y2; dy2 = y3-y2; dy3 = y0-y1+y2-y3
det = dx1*dy2 - dx2*dy1
g = (dx3*dy2 - dx2*dy3) / det
h = (dx1*dy3 - dx3*dy1) / det
u = (x1-x0+g*x1, y1-y0+g*y1, g)
v = (x3-x0+h*x3, y3-y0+h*y3, h).
```

These are the first two columns of the unit-square homography with its last
entry normalized to one. Its denominator is affine: requiring positive lower
bounds on `1+g`, `1+h` and `1+g+h` keeps the whole square within a finite
projective chart. Define `N = u_x*v_x + u_y*v_y` and `Z = u_z*v_z`. Eliminating
`f² = -N/Z` from the metric squared-length difference gives

```
D = [N*(Z1-Z2) - (P1-P2)*Z] / N.
```

Every operation rounds both interval endpoints outward. A denominator that
contains zero, an unsupported focal interval, or a `D` interval that contains
zero makes this inference unresolved. A strictly signed `D` interval resolves
the order throughout the chosen corner box; no random sampling is used in the
production decision. Dependency overestimation can conservatively reject a
view whose true set of possibilities is narrower than its computed intervals.

An unresolved inference cannot veto usable original focal metadata. Without
metadata, the existing focal-envelope/aspect checks still apply; if those also
cannot resolve the axes, the app requests a new photo. The reported noisy case
now refuses instead of exporting distorted dimensions; correct focal metadata
recovers the held-out lengths within 0.03 mm in the seeded regression.

## Unknown focal length and ambiguity

A frontal or single-axis view can leave orthogonality uninformative. A guessed
phone focal length must not silently decide the sheet's orientation. Define

```
P1 = u_x² + u_y²;  Z1 = u_z²
P2 = v_x² + v_y²;  Z2 = v_z²
D(f) = (P1 - P2) / f² + Z1 - Z2.
```

The sign of `D(f)` determines the physical side ordering. It is affine in
`1/f²`, so evaluating the endpoints of a declared focal interval checks the
entire interval, not just a few sampled lenses. If the ordering changes, test
each possible sheet aspect `q` using

```
f² = (P1 - q² P2) / (q² Z2 - Z1).
```

Two admissible candidates mean the photograph has more than one camera/scale
explanation. The app should request a more overhead photograph instead of
returning one arbitrarily. A square sheet has no long/short assignment ambiguity.

For an ideal A4 sheet tilted only about its short axis, true focal 1980 px,
and angle `theta`, the alternative assignment requires

```
f_wrong² / f_true² = ((210/297)^4 - cos(theta)^2) / sin(theta)^2.
```

At 50° there is no positive alternative focal. At 70°, both the true 1980 px
focal and an alternative of approximately 768.348 px can explain the quadrilateral.
This is geometric non-identifiability, not a software precision problem.

A focal derived by imposing the sheet aspect must **not** be reused to claim
that the sheet independently passed an aspect check: that would force agreement
by construction. The separate proportion check retains its own focal source.

## Explicit support policies

- The focal envelope is **5–600 mm in 35 mm-equivalent units**, converted to
  photo pixels by the ratio of image diagonal to the 36 × 24 mm diagonal. This
  reuses the range accepted for EXIF; it is an application assumption, not a
  measured bound on the camera.
- The corner scenario is **±0.25 pixels per 3000-pixel image diagonal**, per
  coordinate. Scaling its radius with the image preserves the policy when the
  same image is resized. The entire inferred focal interval must remain within
  the existing **0.3–5 image diagonals** plausibility range, and the metric-axis
  difference must keep one sign. This scenario is a sensitivity screen, not a
  claim that actual corner error is bounded by that radius.
- A non-square reference with `long / short < 1.02` cannot use either EXIF-based
  or inferred-focal norm ordering, or the aspect-feasibility route. It can only
  proceed when the ordering is invariant over the focal envelope. This is a
  conservative support restriction: some mathematically identifiable views are
  deliberately refused. It avoids known noisy near-square reversals even when
  focal metadata is exact. Equal measured sides bypass long/short assignment.
- A support-policy refusal explains how to retake the photo or choose a
  reference with more distinct sides. A genuinely ambiguous camera solution
  and conflicting focal evidence have separate messages. These failures do not
  silently invoke ordinary tracing via the missing-sheet fallback.

The focal-envelope reasoning uses the **measured homography**. Only the inferred
axis route additionally encloses the declared corner scenario, with lens
correction and principal point fixed. Neither is a bound against arbitrary
corner-placement, camera-model or lens errors. No policy threshold above is a
probability, a confidence interval, or a physical uncertainty estimate.

## Reproduced checks

The baseline is repository commit `9337800`. A clean rendered photo of the
existing 120 × 70 mm plate, at camera tilt `(50°, 10°, 0°)`, yielded:

| Measurement | Before | After | Ground truth |
| --- | ---: | ---: | ---: |
| Outside long dimension | 169.6933 mm | 119.9673 mm | 120 mm |
| Outside short dimension | 49.5079 mm | 70.0105 mm | 70 mm |

This uses `tests.synthetic.render` with zero radial coefficient, shadow,
lighting gradient, noise and dither, lossless PNG, zero in-plane part angle,
and `trace_image(..., reference="a4", snap=False)`. Remaining errors include
rendering, detection and contour approximation. The more complex noisy JPEG
regression uses the ordinary renderer and checks every supported feature within
0.15 mm; these thresholds describe these fixtures only.

The permanent checks are:

- `tests/test_sheet_axis_assignment.py`: exact projected edge clouds, reserved
  100 × 70 mm dimensions, cyclic corner starts, image/homography rescaling,
  single-axis ambiguity, metadata conflicts, square/near-square policy and a
  full rendered photo through tracing. Noisy weak-secondary-tilt cases cover
  the reproduced failure and the 2% sheet-ratio policy boundary, with each
  cyclic corner start and metadata present/absent.
- `tests/test_calibration_bounds.py`: high-precision decimal arithmetic checks
  outward enclosure, and independent eight-equation homography solves at every
  corner-box vertex check the derived column bounds for three camera poses.
  Degenerate and horizon-crossing scenarios cannot supply inferred ordering.
- `tests/test_sheet_axis_sweep.py`: an independently written pinhole projection
  over **3,168 cases**, with exact edges or seeded 0.05 px edge-coordinate noise,
  six sheet shapes, eleven poses, three focal lengths, metadata present/absent
  and four cyclic corner starts. The expanded grid includes small nonzero
  secondary tilts and sheets on either side of the 2% support boundary.
  **1,702 accepted; 1,466 refused; no wrong accepted axis assignments.** Every
  accepted held-out dimension remained within the fixture's 0.1 mm bound with
  noise, or 0.0001 mm with exact edges.
  Rejections include the conservative near-square policy; they are not all
  proofs of physical non-identifiability.
- `tests/test_sheet_axis_flow.py`: the actual API returns an actionable 422
  for exact ambiguous and noisy unstable detected geometry, with and without
  requested fallback. Only detection and lens estimation are supplied as
  fixtures; axis selection is exercised.

Run the dedicated regression set with:

```sh
.venv/bin/python -m pytest -q tests/test_calibration_bounds.py tests/test_sheet_axis_assignment.py tests/test_sheet_axis_sweep.py tests/test_sheet_axis_flow.py
```

The initial local verification on 2026-11-16 passed **365 targeted Python tests**: 36 axis
assignment/sweep tests, 84 fidelity-math tests, 126 existing sheet/photo/lens
tests, 90 backend/API-flow tests, and 29 blur/support integration tests. The
frontend production build, TypeScript check, Python lint, changed frontend
formatting and diff checks passed. A fresh local server's `/api/trace` response
also reproduced the corrected dimensions above and the axis-correction note.
These were targeted regressions, not the entire repository suite. Browser
interaction/visual verification was unavailable because browser navigation
failed; no new CI, merge, deployment or physical-print result is claimed.
The original 1,344-case grid had no wrong accepted axes but missed the weak-tilt
failure above; that finite result was not a general correctness guarantee.

The follow-up interval implementation passed **398 targeted Python tests**:
67 axis/sweep/interval tests, 4 API calibration-refusal cases, 201 fidelity,
backend and blur/support integration tests, and 126 sheet/photo/lens tests.
Python lint and whitespace checks passed. The frontend was unchanged in this
follow-up. These are local results; browser interaction, CI and physical-camera
accuracy remain unverified for this change.

## Scope of the evidence

Exact-camera tests isolate assignment mathematics. Rendered-photo tests also
exercise sheet detection, rectification and tracing. Neither establishes
real-camera accuracy. Cropping, incorrect EXIF, off-centre principal points,
non-square pixels, unmodelled lens effects and non-flat paper can violate the
model. A lens envelope or numerical conditioning threshold is an implementation
policy, not a statistical confidence interval or measurement error bound.

Use the [measured-photo benchmark](../photo-benchmark.md) with reserved caliper
dimensions before making physical-accuracy claims. Do not relabel fit residuals
or endpoint-placement scenarios as uncertainty; a full measurement model must
include correlated calibration errors, as described in the
[JCGM measurement-uncertainty publications](https://www.bipm.org/en/committees/jc/jcgm/publications).
