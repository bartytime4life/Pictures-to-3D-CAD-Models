# Predict a finite shape in the source image

**Developer research candidate — November 12, 2026.** The forward evaluator and
bounded circular-segment fitter have source-bound independent controls in the
[validation record](validation/finite-shape-source.md). The Python API remains a
research prototype. Production integration and general physical recovery remain
open; the published-source documentation audit retains its separate binding.

The developer-only [finite-shape evaluator](../backend/finite_shape.py) predicts
Gaussian-blurred material coverage from a complete supplied boundary. A nearby
chord, corner, opposite edge or hole contributes to the same prediction. This is
the forward model needed to investigate interactions that independent local
half-plane or isolated-circle corrections cannot represent.

The evaluator does not change a trace, recover camera calibration or accept CAD.
The [conditional circular-segment fitter](../backend/finite_shape_fit.py) builds
on it, with a fixed pose and supplied optical/noise inputs. Its candidate-search
API is described below; recovery and accuracy claims require separate recorded
experiments. Neither module adds an HTTP endpoint, workbench control or automatic
image correction.

## One material region, one source prediction

Let `Omega` be a simple closed plane region with contained, disjoint holes. Let
`h` be the supplied lens-free homography into continuous working-image
coordinates, and `Sigma_raw` a supplied spatially constant positive-definite
Gaussian covariance in working-image pixels squared. The model is

```text
q_i = pixels_xy_i + (0.5, 0.5)
p_i = integral over h(Omega) of N(q_i - u; 0, Sigma_raw) du
mean_i = background * (1 - p_i) + material * p_i
```

The geometry is projected before convolution. The integration region includes
the whole supplied shape, even material outside the sensor. `sensor_shape`
restricts query indices; it does not clip the material. Holes subtract material
before the mean is formed. Summing independent edge probabilities, omitting a
nearby boundary or blurring an already rectified binary mask generally describes
a different source field.

Here a probability is normalized Gaussian mass of the declared material region,
not a probability that the proposed geometry is correct. The two-level mean
assumes constant background and material radiance in this source model. It does
not represent a spatial illumination field.

## Coordinate and geometry contract

Call `finite_shape_probabilities` with unique integer `[x, y]` working-image
indices and `sensor_shape=(height, width)`. The implementation evaluates at
their continuous centres `+0.5`; callers must use this convention for the image,
homography and any independent oracle. There are 1–2,048 queries per call.

`rings` contains the outer ring first, then at most 32 holes, with at most 128
analytic segments in total. Each ring is a sequence of canonical tuples:

```python
("line", start, end)
("arc", start, mid, end)
("circle", centre, radius)  # Must describe the entire ring alone.
```

An arc follows the circle and signed sweep through its three points. Line/arc
rings must share consecutive endpoints exactly, including the closing join.
The evaluator invents no closing segment or circle intersection. It normalizes
outer/hole orientation, so reversing a valid ring's winding does not change the
material prediction.

Closure, nonzero signed area and orientation checks do **not** validate analytic
topology. The caller must establish that the outer ring is simple and holes are
contained, disjoint and correctly assigned. Intersecting rings can describe a
winding field rather than the intended binary material. The result therefore
keeps `topology_validated=False`.

`homography` maps the supplied plane-coordinate length unit to working-image
pixels. Radius and all boundary coordinates must use that plane unit. A
nonzero scalar multiple of `H` represents the same map. The implementation
checks invertibility and the projective denominator over each **whole curve**,
including arc extrema. A horizon crossing or an unresolved positive chart is
refused. A reflection is handled in the boundary orientation and reported by
`reflected`; it does not require callers to reverse their material labels.
`chart_margin` records the resolved denominator range ratio, not calibration
uncertainty or a confidence score.

`psf_covariance` is a finite, exactly symmetric 2-by-2 positive-definite matrix
in the same working-image frame. Numerically unsupported covariance scales or
conditioning are refused. It is not the trace's scalar `edge_blur_mm`, nor that
scalar multiplied by pixels per millimetre. A perspective warp, anisotropic
optics, resampling and digital smoothing cannot generally be summarized by one
rectified Gaussian spread; see the [known-warp model](warp-observations.md).

## Boundary integral and numerical resolution

With `Sigma_raw = L L^T`, whiten the projected boundary around each query:
`u = L^-1 (h(x) - q)`. The evaluator uses the radial Green flux

```text
p(q) = (1 / (2*pi)) integral_boundary a(u dot u) cross(u, du)
a(s) = -expm1(-s/2) / s, with a(0) = 1/2
```

Outer, hole and reflection signs are included. The parameterized implementation
uses the transformed curve velocity in `cross(u, du/dt) dt`; the curve measure
must not be dropped. The [DiffVG authors' measure erratum](https://people.csail.mit.edu/tzumao/diffvg/)
is a useful independent reminder of this requirement in boundary-based rendering.
The Gaussian-convolution-to-boundary-integral principle also appears in
[Sun et al., GauWN (2024), author paper](https://www.cad.zju.edu.cn/home/hj/24/GauWN.pdf)
([publication](https://doi.org/10.1145/3680528.3687569)). This evaluator uses its
own radial flux, analytic line/arc/circle paths and numerical safeguards; it does
not import GauWN's polygon implementation or its performance claims.

Far panels retain their complete angular winding contribution. Only the
Gaussian remainder is omitted, with a tail calculation based on the whole-panel
distance and travel cover. Dropping a distant panel's entire flux would lose
winding information. Near panels must first have a whitened travel bound no
larger than `0.5`; only then can the embedded 12/24-point Gauss–Legendre rules
accept a panel. Agreement of two rules alone could miss a narrow contribution.

Whole-panel floating covers, embedded-rule differences and roundoff allowances
are engineering estimates. They are **not** certified interval integration,
physical error bounds or camera uncertainty. `quadrature_certified=False`
remains explicit. `tail_bounds` accounts for the omitted far Gaussian remainder
under those covers; it is not the complete integration error.

## Developer call and result handling

This example supplies a circle and two point-detector queries in a declared
32-by-32 working image. It does not load a photograph or estimate its optics.

```python
from backend.finite_shape import finite_shape_probabilities

result = finite_shape_probabilities(
    [[15, 15], [20, 15]],
    [[("circle", (16.0, 16.0), 4.0)]],
    sensor_shape=(32, 32),
    homography=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    psf_covariance=[[1.0, 0.0], [0.0, 1.0]],
)
for index, probability, status in zip(
    [[15, 15], [20, 15]], result.probabilities, result.statuses
):
    print(index, probability, status)
```

The function's keyword options are `probability_tolerance=1e-8`,
`max_panels=4096` and `max_evaluations=2_000_000`. Tolerance must be finite in
`[1e-12, 1e-3]`. The panel cap is 1–8,192 **per query**; the evaluation cap is
1–20,000,000 **across the call**. Boolean caps and pixel indices are refused.
Extreme geometry and numerically unresolved projective/PSF scales can also be
refused even when their mathematical model would be defined.

Every requested query retains its position in the output:

| Status | Meaning |
| --- | --- |
| `resolved` | The numerical procedure met its engineering acceptance criterion. |
| `work_limit` | A query exhausted a panel or shared evaluation allowance. |
| `numerical` | The transformed panel or subdivision could not be resolved. |
| `invalid_winding` | The computed mass lay outside `[0, 1]` beyond its estimated error. |

Unresolved probabilities are `None`; they must not become zero, disappear from
the denominator or be accepted as material measurements. The evaluator does not
clip a numerical result to `[0, 1]`. `estimated_errors`, `tail_bounds`, total
`evaluations` and total `panels` accompany the query statuses. Invalid inputs
raise `ValueError`. A resolved value establishes numerical completion for the
supplied model, not an accepted boundary or an accuracy label.

## Conditional radius and chord fitting

`circular_segment_ring(radius, chord_fraction, *, centre=(0, 0), normal=(1, 0))`
constructs the exact boundary of

```text
disc(centre, R) intersect {normal dot (x - centre) <= R*f}
f = chord_fraction
h = R*f = chord_offset
```

The supplied chord normal is a unit vector; centre and normal remain fixed.
`fit_circular_segment(pixels_xy, raw_values, noise, *, sensor_shape, homography,
psf_covariance, radius_bounds, chord_fraction_bounds, ...)` jointly searches
radius and chord fraction. Its rectangular domain is **`(R, f)`**, not `(R, h)`.
It supports increasing radius bounds within `[1e-3, 1e6]` and increasing fraction
bounds within `[-0.999, 0.999]`. It fits one circular segment; the more general
forward evaluator's holes do not imply a general shape-fitting API.

Geometry and brightness bounds must contain a representable floating-point
interior point, not just two adjacent numbers. Before searching, the fitter
checks the whole `(R, f)` domain's projective chart. Circular segments are nested
in `f`, and the homogeneous denominator is affine in `R` for each point of the
unit shape. Checking the largest fraction at both radius endpoints, with a
consistent chart, covers this domain; validating only its lowest corner would
not. Unsupported input or preflight geometry is refused before candidate search.

At each represented geometry, the two shared mean levels are fitted within
`level_bounds` (default `[0, 255]`). The bounded linear subproblem considers
active faces; simply clipping an unconstrained solution would not generally
solve it. Noisy observed values are not clipped to the allowed mean range.
This separation of nonlinear geometry from linear brightness follows the
[variable-projection principle described by O'Leary and Rust](https://www.cs.umd.edu/users/oleary/software/varpro.pdf).
It does not imply that their sample solver, constraints or global-convergence
properties have been reproduced here.

A complete `grid_points`-by-`grid_points` coarse grid supplies represented local
basins and domain-face candidates. Selected basins receive a domain-scaled
approximate variable-projection Gauss–Newton direction: finite differences of
the source probabilities give derivatives with respect to normalized radius and
fraction. Only brightness columns whose coefficients are **free** of their
bounds are projected out as nuisance directions. An active bounded brightness
coefficient is not treated as freely adjustable.

This direction omits the full residual-dependent variable-projection Jacobian.
It is a proposal for a local step, not an exact reduced-objective derivative.
The step is damped and capped in normalized domain coordinates. Backtracking
refits the bounded levels and accepts only a decrease in the actual evaluated
cost beyond the arithmetic allowance. It does not accept a step solely because
the local linear model predicts improvement.

The defaults are `grid_points=5`, `refinement_iterations=32`, `max_basins=8`,
`max_evaluations=512` and `forward_work_limit=20_000_000`. Supported ranges are
3–11 grid points per axis, 0–64 refinement iterations, 0–16 refined basins,
`grid_points**2`–4,096 geometry evaluations and 1–100,000,000 forward evaluations.
Derivative and diagnostic calls consume those geometry/forward budgets too.
Disabling refinement leaves a grid search; increasing a cap does not provide a
global optimization certificate.

The supplied `PixelNoise` factor defines a fixed source projection. For
`A D = U diag(d) V^T`, where `D` contains supplied independent source standard
deviations, both observations and predictions use `T = V^T D^-1`. The pixels
must match the sampling-matrix columns exactly and remain fixed for all
candidates. This is an all-source-pixel objective only when all source modes are
retained; see [source projection and omitted residuals](raw-source-fit.md).

The result retains the complete coarse grid and its statuses, represented
basins/domain faces, candidates and work accounting. `grid_statuses` preserves
`resolved`, `work_limit` or `numerical` for every planned cell; an unresolved
cell has a `None` entry in `grid`. `best` may also be `None`. The candidate list
retains resolved coarse-grid face and basin representatives as well as selected
refinement results; it does not enumerate every possible continuous basin.

Inspect `flat`, `tied`, `endpoint`, `unrefined_basins`, `refinement_limited`,
`work_exhausted` and `numerically_unsupported`, not just the lowest sampled cost.
`flat` requires the complete grid to resolve; a false flag on an incomplete grid
does not establish an informative objective. `unrefined_basins` is the represented
seed count minus the number of selected basins that reached local convergence.
It includes unstarted seeds and selected attempts that failed, exhausted work or
reached an iteration limit. `refinement_limited` records selected refinement
ending without its local convergence criterion; it is distinct from a global
work-budget exhaustion.
A supplied domain boundary is a search prior, not an image-derived radius bound.

`geometry_rank` is `None` when the local derivative diagnostic is unavailable,
not automatically deficient. `rank_deficient` identifies a deficient brightness
design or an evaluated geometry rank below two. A false flag together with an
unknown geometry rank is not a full-rank finding. `geometry_condition` is
available only for a rank-two geometry diagnostic. These are local numerical
sensitivity diagnostics, not a physical uncertainty calculation.

Candidate cost guards propagate estimated forward error through the maximum
allowed contrast and supplied noise scaling. They do not certify feasibility or
provide confidence intervals. All three residual norms are **standardized
source** diagnostics. With `r = (raw_values - predicted_mean) / input_std` and
the retained right singular vectors written as `V^T`, they are

```text
raw_residual_l2            = ||r||
retained_residual_l2       = ||V^T r||
omitted_source_residual_l2 = ||r - V V^T r||
```

Despite its name, `raw_residual_l2` is not an unscaled intensity norm. A small
retained cost can coexist with substantial omitted-source discrepancy.
Stable norms preserve large representable discrepancies. If a residual norm
itself exceeds floating-point range, its field is `None` and
`numerically_unsupported=True`; the available projected fit remains visible.
An unavailable norm must not be interpreted as zero residual.
`global_search_certified`, `pose_fitted` and `psf_fitted` remain false.

Blur is already inside the prediction. Applying the production generic
`correct_blur` to a fitted candidate would introduce another correction with a
different model and is not part of this API.

## Evidence and a credible integration seam

Generating intensities with this same boundary evaluator and fitting them back
is a self-consistency check. Independent forward evidence should use another
formulation, such as a one-dimensional area integral for a circular segment,
then vary the independently integrated tolerance. Keep the same declared
homography, query-centre convention, Gaussian and intensity units. Retain all
planned cases, including unresolved work, competing minima, boundary solutions,
wrong-model controls and adverse geometry outcomes. Such synthetic evidence
still does not qualify a photographed part or printer fit.

Production reference tracing currently has access to working RGB and its
linear-light channel mixture before rectification and added smoothing. That
array is captured by the opt-in [source-context API](source-context.md), which
binds the actual trace to fixed observations and an explicit conditional fit.
Here “raw” means this available prewarp working array, **not camera RAW or
recovered scene radiance**. Image decoding, orientation, resizing, tone handling
and quantization are already part of its history.

Saved `Profile.reference` records sheet/scale, a lens coefficient, scalar blur
and notes. It does not retain the source array, homography, channel weights,
sampling support, PSF or noise factor. A saved profile therefore cannot recreate
this fit from its blur summary. The private in-memory context now binds those
working pixels, coordinate frames, processing stages and profile/request identity;
it does not supply a calibrated PSF or noise factor. Candidate geometry and residual evidence
should remain separate from the accepted profile until explicitly reviewed;
unsupported candidates must retain the current boundary and an actionable
explanation. Persistent source sessions, automatic refinement and a candidate
review/acceptance flow remain open. The opt-in capture does not change the HTTP
response, saved profile or accepted CAD geometry.

The [edge-width and covariance APIs](psf-calibration.md) can now construct a
conditional Gaussian hypothesis from separately declared straight target edges.
Their rank, search and response ambiguities remain part of the input evidence;
they do not silently promote a fitted matrix to known physical optics.

The remaining model assumptions are substantive:

- `H` and the Gaussian covariance are supplied hypotheses. Sheet-derived pose,
  image-derived channel weights or a measured edge rise do not make them known
  independently of the same observations.
- Point samples omit detector-area averaging. Known aperture or signed digital
  stencils need their actual measurement operator; they cannot be silently
  absorbed into a scalar PSF.
- Constant levels omit material/paper gradients, exposure changes, clipping,
  nonlinear response and spatially varying optics. Standard sRGB decoding does
  not establish radiometric camera calibration.
- Nonzero radial distortion `k1`, visible walls, thickness, shadows, occlusion
  and height parallax are outside this flat, lens-free model. Their appearance
  cannot be corrected merely by moving a two-dimensional boundary.
- Supplied independent source-noise scaling omits unknown correlation, shared
  calibration errors and parameter-selection uncertainty. Numerical fit rank
  and cost are conditional on that fixed metric.

These limits identify the inputs and evidence needed before production
integration; they are not additional workbench settings for ordinary users.
