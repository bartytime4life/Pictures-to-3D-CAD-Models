# Initial analytic-fit source support

This repair prevents a small point residual from justifying geometry far beyond
the observed boundary. Initial development used `6fbff38` (the documentation
review merged over tracing source `5588a52`). Integration with the subsequent
wall/height changes is recorded below. It does not change the interface,
measurement scale or file formats.

## Problem and resulting behavior

The [original finding](scientific-model-review.md#whole-circle-extrapolation)
specified a closed circular segment measuring 0.37977 × 8.68241 mm. The fitter
replaced it with a whole circle of radius 49.61052 mm, without a radius note.
Rejecting only an outside-center circle is insufficient: fallback lines can
intersect beyond their measured spans. A 10° segment of radius 300 px produced
three lines whose largest point residual was only 0.19033 px, while their
assembled boundary extended 4.40791 px from the source.

Whole-circle candidates now require an enclosed center. Every candidate initial
circle or line/arc cycle must also have complete assembled-boundary support.
An unsupported or over-budget analytic candidate retains the traced polyline.
Sparse polygons with vertices on a circle remain polygons. Dense circles and
the existing slightly out-of-round-hole interpretation remain supported.

The source-tube check precedes design-intent snapping and Gaussian reconstruction.
A deblurred sharp corner deliberately differs from blurred observations: for an
ideal Gaussian-blurred right angle, the observed half-level is
`Φ(x/σ) Φ(y/σ) = 1/2`. Its bisector is at `x = y = 0.544952σ`; true-apex to
observed-contour distance is `0.770679σ`. A final raw-distance test would reject
that correct reconstruction. This patch does not make that conceptual mistake
or certify later reconstruction. The existing exact corner fit computes model
residuals, but does not impose a separate residual-adequacy acceptance gate;
forward-model validation remains further work.

## Coverage is separate from precision

Subpixel edge searches reject weak profiles. Joining their remaining points
can create a long artificial chord across a real round hole. The complete
classified contour is therefore retained as coverage evidence, with the original
point indices transported through both rejection passes. Only accepted subpixel
points enter the geometric least-squares fit.

For thick parts, both accepted measurements and the complete support contour
receive their appropriate material-normal/parallax transformation. Their matched
positions supply the maximum observed coarse-to-fine displacement, after the
final camera/wall correction. This allowance is independent of the candidate's
fit mismatch. It is empirical localization evidence, not a physical uncertainty
or a guarantee for every rejected profile.

This distinction has a paired counterexample. Retain the same measured 270° arc
of a 100 px circle in both cases. Complete support that is a full circle permits
the circle fit; complete support that closes with a real straight chord does
not. Allowing arbitrary coarse-to-candidate residual as a budget would wrongly
pay for the 29.2893 px extrapolation across that chord.

## Geometry and work bound

Let `M` be the accepted measurements, `C` the complete source boundary,
`P` the polyline sampling the assembled fitted boundary, and `u` the separately
measured coarse/fine displacement allowance. Define

```text
d = max { distance(m, P) : m in M }
b = d + line_tolerance + u
```

Require the **entire** `P` to lie inside a round buffer of `C` with radius `b`.
This checks joins and segment interiors. [Shapely's Hausdorff calculation](https://shapely.readthedocs.io/en/stable/reference/shapely.hausdorff_distance.html)
is discrete by default and can miss a segment interior; it is not used as a
continuous-boundary certificate. The [buffer operation](https://shapely.readthedocs.io/en/stable/reference/shapely.buffer.html)
approximates circular neighborhoods with polygons. Its round joins are
conservative for this containment check; there is no outward numerical padding.

Circular segments are sampled to sagitta `e = line_tolerance / 16`, without
silently imposing the ordinary display sampler's segment caps. For radius `r`,
choose angular spacing at most `4 asin(sqrt(e/(2r)))`, from
`e = 2r sin²(step/4)`. Triangle inequality then bounds analytic-fit distance
to `C` by `d + line_tolerance + u + e`, subject to floating-point evaluation.
The forward allowance comes from observed **vertices**, not the Hausdorff
deviation of long interpolating source edges, which could bless a sparse
triangle as a whole circle.

At most **8192 support-sampling points** are allocated per candidate. An
over-budget or numerically failed construction retains the source outline
instead of coarsening the curve and invalidating the sampling bound. This is
an initial geometric-model support test, not a manufacturing tolerance,
universal reconstruction guarantee or physical error budget.

## Independent verification

`tests/test_fit_support.py` specifies geometry independently of the fitter:

- Closed minor segments at two radii, opposite windings, rotated/translated
  copies and cyclic starting points: bounds, boundary distance and area remain
  within the existing polyline approximation budget.
- Sparse triangles, squares and hexagons on a circle retain their straight
  boundaries; dense circles and 2% ellipse-like rings remain circles.
- The identical-measurement/different-support major-segment pair above rejects
  the real closing chord while accepting full circular coverage.
- A known coarse radial offset needs its independently supplied localization
  allowance, without changing the fitted radius.
- Separate rejection masks verify the original contour-index mapping through
  both subpixel passes.
- Two fitter-boundary integration cases run the real wall-refinement control
  flow with explicit pose and photometry fixtures. They verify that both contour
  tracks use the final hole-derived camera exactly once, that paired indices
  survive and that the allowance uses the final refinement. The zero-blur case
  transports geometry without fitting a wall profile. These are transport tests,
  not image-inference accuracy tests.
- Sampling-limit refusal and recomputed deviations after circle-radius changes
  remain explicit checks.
- A rendered 120 × 70 mm plate with a thin circular-segment aperture passes the
  real tracer, profile validation and actual CAD build with one through-hole,
  expected dimensions and volume. The earlier fitter fails this photo at profile
  validation. Sharp tip recovery is not claimed; aperture area and plausible
  size are checked separately.

The tiny-chamfer regression now permits preserving its observed polyline when
joining the true lines would extrapolate past the support allowance. It still
rejects the former invented large arc and checks retained bounds, area and
boundary agreement.

## Recorded checks and limits

Before integrating later tracing changes, the source candidate passed **519
Python tests** in the full invocation. Two subsequent independent regressions
were added; the complete focused support file passed **19 tests**. Ten selected
support regressions failed when the original `5588a52` fitter was loaded in
process memory, including the real-tracer aperture case; source files were not
replaced for that control. Ruff and the production frontend build passed.

After integration with `main` at `eec45d04cf767f2a55e8581a009b8052fe349180`,
the complete Python invocation passed **529 tests** in 160.31 seconds. All
**74 browser scenarios** passed in 6.0 minutes against a freshly built frontend
and this checkout's CAD service. Ruff and frontend formatting checks passed.
The later correlation-helper edit corrects its docstring only: this is a
truncated autocorrelation heuristic, not Geyer's paired estimator. It changes
no calculation. The [documentation review](documentation-review-2026-11-12.md)
records the separate all-document and generated-library checks.

PR #43 was subsequently merged at `d6a657f93f13b818a8e44e2ace219b2d4598b4ef`.
After integrating that benchmark script/test/documentation change, the final
complete Python invocation passed **579 tests** in 138.39 seconds. The
74-scenario browser run precedes that merge; API/frontend sources are unchanged
by it. The regenerated three-photo benchmark retained 48/48 comparisons and the
guide's 0.004/0.014/0.015 mm rounded median/p95/worst matched errors.

Ignored local logs and receipts live in `.local/verification/`. These checks
use synthetic geometry and generated images; no measured-photo accuracy,
native-tool acceptance or physical fit is established. Directional blur,
shared lens-renderer code, camera-model observability and downstream
forward-model adequacy remain separate scientific work.
