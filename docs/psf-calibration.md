# Fit a conditional Gaussian blur model from straight targets

The developer [edge-spread fitter](../backend/edge_spread.py) estimates a straight
edge's offset and Gaussian width from fixed prewarp working pixels. The
[covariance module](../backend/psf_calibration.py) combines directional variances
into a common two-dimensional Gaussian candidate and plans an additional edge
direction. These are Python research tools, not a workbench calibration button,
automatic correction or physical-camera qualification.

A useful optical investigation needs **independently specified straight target
geometry**, fixed observations and justified response/noise assumptions. Fitting
the same part edges whose geometry is being recovered does not independently
calibrate that recovery. The source context's `psf_calibrated`,
`response_calibrated`, `noise_calibrated` and `pose_calibrated` flags remain false.
Successful numerical fits do not change them.

## Fit the source field, not the rectified rise width

For a supplied unit normal `n` and anchor in continuous working-photo coordinates,
the model at each integer working-image index is

```text
q_i = pixels_xy_i + (0.5, 0.5)
d_i = n dot (q_i - anchor)
p_i = Phi((d_i - offset) / sigma)
mean_i = background * (1 - p_i) + material * p_i
```

`anchor`, `offset` and `sigma` use **working-image pixels**, not display pixels or
sheet millimetres. `normal` is a direction in that same working-photo frame;
`sensor_shape` is `(height, width)` of the working image, not a physical sensor
specification. The material probability increases along `normal`. Both mean
levels are fitted inside supplied bounds; their ordering is not constrained.

This model evaluates the Gaussian CDF directly at the fixed source pixels. It
does not infer sigma from the production 25–75% edge-rise diagnostic, sample a
rectified image at finer intervals, or subtract the added smoothing from
`edge_blur_mm`. That scalar diagnostic belongs to a different processing stage.
The [source-context guide](source-context.md) explains what prewarp data is
available; it is decoded camera output, not sensor RAW or recovered radiance.

The direct API is:

```python
fit_edge_spread(
    pixels_xy, raw_values, noise, *, sensor_shape, normal, anchor,
    offset_bounds, sigma_bounds, level_bounds=(0.0, 255.0),
    grid_points=5, refinement_iterations=32, max_basins=8, max_evaluations=512,
)
```

`noise` must be a supplied `PixelNoise` factor whose source columns match the
ordered unique pixel indices and values. Both target and model use its fixed
`whiten_source` projection. Retaining fewer modes changes the objective; a
small projected residual need not explain omitted source directions. Supplied
independent working-pixel deviations are hypotheses, not noise estimates
produced by this fitter. See [fixed observations](profile-observations.md).

The search is rectangular in **offset and log sigma**, with increasing offset
bounds inside `[-1e9, 1e9]` and sigma bounds inside `[1e-3, 1e3]`. Brightness
bounds lie inside `[-1e6, 1e6]`. Bounds, including the log-sigma domain, must
contain a representable floating-point interior. A search endpoint is a prior
limit, not an image-derived bound on blur.

For each geometry the fitter solves the bounded two-level linear subproblem.
Local refinement uses analytic CDF derivatives in domain-scaled coordinates,
projecting out only free brightness coefficients. This is an approximate
variable-projection Gauss–Newton direction, with actual-cost backtracking and a
fresh bounded-level fit at each accepted step. It is not the full
residual-dependent reduced-objective Jacobian or a global optimization method.

The complete coarse grid and represented basin/face candidates remain visible.
Supported settings are 3–11 grid points per axis, 0–64 refinement iterations,
0–16 refined basins and `grid_points**2`–4,096 geometry evaluations. A separate
fixed allowance of 100,000,000 declared dense-projection work units includes
derivative work. It is not a wall-clock performance guarantee.

`best` can be `None`; unresolved grid entries retain `None` with `work_limit` or
`numerical` status instead of disappearing. Inspect flat/tied/endpoint flags,
work and numerical limits, represented basins not locally converged and
`refinement_limited`. `geometry_rank` concerns the **two** local parameters
offset/log sigma. A missing diagnostic is `None`, not automatically rank
deficiency; a false `rank_deficient` flag with unknown rank is not a full-rank
finding. `global_search_certified=False` remains explicit.

All three residual norms are standardized source norms: for
`r = (raw_values - predicted_mean) / input_std`, they report `||r||`, its retained
right-singular projection and the omitted orthogonal component. In particular,
`raw_residual_l2` is not an unscaled intensity norm. Arithmetic cost guards and
the numerical comparison tolerance do not provide physical confidence intervals
or establish that the Gaussian mean model is adequate.

## Recover covariance only when directions identify it

For a stationary Gaussian covariance `Sigma` in working pixels squared, a
straight edge with unit raw-image normal `n` has directional variance

```text
v(n) = sigma_n**2 = n.T @ Sigma @ n
theta = (Sigma_xx, sqrt(2)*Sigma_xy, Sigma_yy)
design_row(n) = (n_x**2, sqrt(2)*n_x*n_y, n_y**2)
v(n) = design_row(n) dot theta
```

These coordinates are orthonormal for the Frobenius matrix norm, so rotating the
image axes does not arbitrarily change the design's condition number. Normals
`n` and `-n` give the same variance row. Four rectangle sides therefore supply
only two directions, not four independent covariance constraints.

A constructive alias makes the missing information explicit. Measurements
`v_x > 0` and `v_y > 0` along the two image axes permit every covariance

```text
Sigma(c) = [[v_x, c], [c, v_y]], with abs(c) < sqrt(v_x*v_y).
```

All those matrices are positive definite and give the same two axis variances,
while their diagonal-edge predictions differ. At 45 degrees,
`v_45 = (v_x + v_y)/2 + c`. A third oblique direction can identify the cross term
under this model; nearly repeated directions can remain ill-conditioned.
Equal-noise normal orientations `0`, `60` and `120` degrees give rank three and
Frobenius-coordinate condition number `sqrt(2)`. This is an ideal design
calculation, not a physical target-placement guarantee.

Call
`covariance_from_edge_spreads(normals, variances, *, variance_std=None)` with
1–128 finite unit normal pairs and one nonnegative finite variance per row.
`variances` and `variance_std` both use **working pixels squared**. The latter is
the supplied standard deviation of a variance summary, not the edge's sigma or
an uncertainty automatically obtained from the width optimizer. `None` selects
equal unit weights. It does not assert measured uncertainty. Only diagonal
summary weighting is modelled; shared-image or shared-geometry correlations
need additional treatment.

The result retains every supplied row, fitted variances, residuals and supplied
weights. Read its outputs separately:

| Output | Meaning |
| --- | --- |
| `candidate` | Minimum-Frobenius-norm unconstrained weighted least-squares matrix, if numerically representable. It can be rank-unidentified or indefinite. |
| `covariance` | Returned only for weighted numerical rank three and a numerically positive-definite, representable parameter reconstruction. Residual diagnostics can still be unsupported. |
| `rank`, `condition` | Weighted design rank and full-rank condition; condition is `None` below rank three. |
| `geometric_rank`, `geometric_condition` | Corresponding unweighted direction-coverage diagnostics. |
| `nullspace` | Unidentified directions in the three Frobenius coordinates. |
| `eigenvalues`, `positive_definite` | Candidate eigenvalues and the relative floating-point positive-definiteness check, when available. |
| `weighted_residual_l2`, `maximum_standardized_residual` | Norm and largest magnitude after division by supplied variance-summary deviations; `None` when that diagnostic arithmetic is unsupported. |
| `numerically_supported` | Whether both parameter and standardized-residual arithmetic remained supported. A false flag can coexist with a retained `covariance`. |

A rank-two candidate can itself be SPD while `covariance` remains `None`.
Missing information is not supplied by setting the cross term to zero. An
indefinite candidate is not repaired by eigenvalue clipping. Conversely, a
refused/non-SPD estimate is not a general proof that no optical model or noisy
SPD fit could explain the image. Inspect the stated model and row residuals.
`gaussian_model_validated=False` and `physically_calibrated=False` remain explicit.

Variance residuals use working pixels squared. Dividing by `variance_std` gives
dimensionless standardized diagnostics under that supplied scale. Extreme units
or deviations can make a nonzero residual underflow to zero, or make a
standardized norm overflow, even when the parameter reconstruction is usable.
The module keeps a representable identified SPD covariance but returns `None`
for those diagnostics and sets `numerically_supported=False`. Do not read that
combination as a zero residual or complete numerical acceptance.
`positive_definite=True` concerns the matrix; it does not override the diagnostic
flag. Neither flag establishes Gaussian adequacy or physical calibration.

### Pool fitted edges without dropping unresolved attempts

`covariance_from_edge_fits(normals, fits, *, variance_std=None)` is an optional
explicit numerical-readiness gate for one `EdgeSpreadFit` per planned normal.
It retains every row in `directional_variances` and `edge_statuses`. A resolved
best candidate contributes `best.sigma**2` even when another diagnostic prevents
pooling; a missing best candidate contributes `None`.

The helper withholds `reconstruction` if any edge has no best candidate, a
flat/tied/endpoint result, rank deficiency, geometry rank unavailable or unequal
to two, work exhaustion, numerical unsupportedness, limited refinement or any
unrefined represented basin. Status tuples name those reasons; an empty tuple
means that row passed this numerical gate. Unresolved rows are never silently
dropped to make the remaining directions reconstruct a covariance.

`all_edges_resolved=True` means every edge passed the gate, not that the joint
covariance is identified. Inspect the returned reconstruction's direction rank,
SPD result and arithmetic flags separately. The helper does not verify that
the fits share one stationary PSF, source-processing scope or independently
specified target; callers must retain those bindings. Passing this optional
gate validates neither Gaussian profile shape nor physical optics, and its
`gaussian_model_validated` and `physically_calibrated` flags remain false.

## Plan one additional direction

`plan_edge_orientation(normals, *, variance_std=None, candidate_angles=None,
candidate_std=1.0)` searches a finite list of prospective **normal** angles in
radians in `[0, pi)`. The default contains 720 angles at quarter-degree spacing;
custom lists allow 1–4,096 angles, with duplicates removed. Planning accepts
0–127 existing edges and supplied positive variance-summary deviations.

It first maximizes numerical rank, then the sum of logs of retained singular
values of the weighted design. Equal-score candidates use a floating comparison
allowance and the smallest angle for deterministic reporting. With existing
axis normals `0` and `90` degrees and equal weights, it recommends `45` degrees.
This is a greedy one-edge finite-design choice. It does not optimize a physical
capture globally, predict pixel-phase coverage, validate target straightness or
account for spatially varying optics. The returned
`continuous_optimality_certified` and `physical_capture_qualified` flags are false.

This executable arithmetic example uses supplied exact-model variances, not a
photograph or an independent recovery experiment:

```python
import math
import numpy as np
from backend.psf_calibration import (
    covariance_from_edge_spreads, plan_edge_orientation,
)

angles = np.deg2rad([0.0, 60.0, 120.0])
normals = np.column_stack((np.cos(angles), np.sin(angles)))
supplied = np.array([[1.0, 0.3], [0.3, 2.0]])  # Working pixels squared.
variances = np.einsum("ij,jk,ik->i", normals, supplied, normals)
result = covariance_from_edge_spreads(normals, variances)
print(result.covariance, result.rank, result.condition)

axis_result = covariance_from_edge_spreads([[1.0, 0.0], [0.0, 1.0]], [1.0, 2.0])
print(axis_result.covariance, axis_result.rank, axis_result.nullspace)
plan = plan_edge_orientation([[1.0, 0.0], [0.0, 1.0]])
print(math.degrees(plan.angle_rad), plan.rank_before, plan.rank_after)
```

## Use the source-context bridge explicitly

`context.fit_edge_spread(observation, *, profile, input_std, **fit_options)`
connects the fitter to actual captured working values. Supply `normal`, `anchor`,
`offset_bounds` and `sigma_bounds` in `fit_options`. The normal and anchor are
already in the **raw working-photo geometric frame**; the method does not infer
them from the accepted part outline or convert a sheet normal automatically.

The following is a call outline with **caller-supplied data**, not a runnable
target example:

```python
edge = context.fit_edge_spread(
    target_observation,
    profile=current_profile,
    input_std=declared_source_std,
    normal=independent_raw_unit_normal,
    anchor=independent_raw_anchor,
    offset_bounds=declared_offset_bounds,
    sigma_bounds=declared_sigma_bounds,
)
```

The bridge checks current profile equality, the request-bound observation label,
integer source indices and their actual values against the immutable field,
then factors the declared sampling matrix. A source label does not certify that
a separately replaced matrix came from a particular display-sampling path.
The existing point-Gaussian guard refuses nonzero recorded lens distortion,
prior reduction/re-encoding and nonzero entered thickness. Passing it supplies
neither physical optics calibration nor proof of an independently known target.
No profile, geometry or calibration flag is changed.

## A good Gaussian fit can still be the wrong explanation

Unknown response creates an exact constructive ambiguity. For normalized common
black/white levels, take any `a > 0` and finite `b`, and define

```text
h(u) = Phi(a * Phi_inverse(u) + b)
h(Phi((d-e)/sigma)) = Phi((d - (e - b*sigma/a)) / (sigma/a))
```

This common increasing response preserves the limiting black/white anchors but
changes every fitted width to `sigma/a` and the reconstructed covariance to
`Sigma/a**2`. Free edge offsets absorb the `b` term. Even with known edge
positions, `b=0` leaves the width ambiguity. Additional edge orientations alone
do not distinguish it. A perfect Gaussian fit therefore does not identify the
optical covariance independently of response. The [response tools](response-calibration.md)
check externally supplied response constraints; they do not automatically
calibrate a photographed target.

Gaussian mixtures give another limitation. Their directional second moments
still obey `n.T @ Sigma_mix @ n`, although their edge profiles need not be
Gaussian CDFs. Thus quadratic directional summaries and an SPD matrix do not
validate Gaussian profile shape. A width fitted by a Gaussian CDF is also not
automatically the true line-spread second moment of a non-Gaussian kernel.
Keep profile residual structure and held-out response predictions, not only the
covariance reconstruction's small residual.

The primary [VIGRA slanted-edge documentation](https://ukoethe.github.io/vigra/doc-release/vigra/group__SlantedEdgeMTF.html)
explains that an edge measures response perpendicular to itself and anisotropic
response needs multiple orientations. Its MTF algorithm and sampling conditions
are not implemented or certified by these CDF fits. [Claxton and Staunton's
primary abstract](https://pubmed.ncbi.nlm.nih.gov/18157223/)
([author reprint](https://wrap.warwick.ac.uk/30614/1/WRAP_Staunton_091211-local_version.pdf))
describes an ensemble of edge measurements and compares several PSF models,
with a generalized Gaussian fitting their tested system better than a Gaussian.
That supports checking the model, not assuming their result transfers to a phone.

## A practical calibration investigation

Start with a recorded independent target, raw-frame geometry and fixed ROIs away
from corners and other boundaries. Keep the camera settings, working-image
processing, channel mix and investigated image region explicit. Long edges with
useful subpixel-phase coverage and unsaturated, adequately separated levels are
preferable to merely increasing the number of resampled profile points.

Use sufficiently separated directions and reserve additional edges or captures
for checking predictions. Repeated parallel edges can test repeatability but do
not fill the missing covariance direction. Retain all fit attempts, prior limits,
rank/conditioning results, model disagreements and held-out errors. Any transfer
to another capture, focus setting, processing path or image region needs its own
justification and source binding.

Target sharpness, detector-area averaging, nonlinear or spatial response,
sharpening, illumination gradients, noise correlation and geometry uncertainty
remain substantive assumptions. An aperture contribution cannot generally be
removed from a Gaussian-CDF fitted width by subtracting a scalar variance.
For the [finite-shape model](finite-shape-source.md), a reviewed covariance is
still a supplied conditional hypothesis. Automatic candidate generation,
acceptance, persistence and real-camera qualification remain separate work.
