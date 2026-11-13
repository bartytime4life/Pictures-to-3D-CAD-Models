# Finite-material intensity fitting

This developer model fits the centre, radius and chord position of one circular
segment to a fixed set of image intensities. It is conditional numerical research.
The workbench does not select it automatically, and it adds no HTTP mode or
capture control. Its supplied optics, constant brightness levels and finite-shape
hypothesis need separate evidence before use on a photograph.

## Observation model

The material is the complete set

```text
K(C, R, f) = {x : ||x-C|| <= R, n dot (x-C) <= R*f}.
P_i = integral over H(K) of Gaussian_Sigma(p_i - u) du.
mu_i = b*(1-P_i) + a*P_i.
```

The unknown geometry is `(Cx, Cy, R, f)`; the two shared foreground/background
levels `a,b` are bounded nuisance parameters. The caller supplies a unit chord
normal `n`, homography `H`, constant observation-frame covariance `Sigma`, fixed
integer pixel indices and fixed residual metric. Pixel centres are indices plus
`0.5`. The tracer's ring coordinates already use this convention; its sampling
functions convert to array-index coordinates internally.

The model integrates both the curved boundary and its closing chord. Treating
the same observations as an isolated disk can change the result when the chord
is near the measured arc. Holes, other nearby material, walls, illumination
gradients, nonlinear response and pixel-aperture integration require their own
models; they are not inferred here.

The separate [source-cell acquisition API](finite-acquisition-mean.md) now
integrates pixel areas and supplied discrete stages. This Gaussian fitter does
not use it. Its rounded unquantized and sRGB8 paths need their own objective,
derivative and recovery qualification before a fitter can adopt them.

In the workbench, `g` is a Keys-resampled linear-light mix followed by smoothing.
Its empirical rectified covariance is not a calibrated sensor PSF. Passing `g`
and an identity homography to this model is an effective-Gaussian hypothesis;
it does not reproduce the complete acquisition operator. Missing covariance
remains unknown. A fixed-covariance study cannot establish its value for a
different photograph.

In particular, the current edge pipeline uses `covariance=None` for both an
unavailable directional fit and a fitted covariance below its anisotropy switch.
It does not preserve a reason that would authorize `sigma**2 * I` as calibrated
optics. A positive-definite moment proposal also needs independent source-model
checks; positive definiteness alone is insufficient.

### Coordinate example

Run this from the repository root after workbench setup. It evaluates a supplied
model at four integer pixel indices; it neither fits a photograph nor builds CAD.

```python
import numpy as np
from backend.finite_centre_fit import circular_segment_probabilities

result = circular_segment_probabilities(
    np.array([[12, 12], [18, 12], [12, 18], [20, 20]]),
    6.5, 0.25,
    centre=(16.0, 16.0),
    normal=(1.0, 0.0),
    sensor_shape=(32, 32),  # height, width
    homography=np.eye(3),
    psf_covariance=np.array([[1.0, 0.2], [0.2, 2.0]]),
)
print(result.statuses)  # inspect every status before using probabilities
```

`H` maps geometry-plane coordinates to the observation field. If a caller crops
an already rectified field at integer array origin `(x0,y0)` while retaining
global geometry coordinates, the mapping is
`H_crop = [[1,0,-x0],[0,1,-y0],[0,0,1]]`. Supply local integer pixel indices and
the cropped `(height,width)`. The translation leaves covariance unchanged; it
does not add another half-pixel shift. Snapshot the crop, pixels, values, bounds
and transform before fitting, and keep validation pixels disjoint from training.
PR #88 leaves observation preparation to the caller. The subsequent developer
bridge below implements a declared measured-ring policy; neither path changes
automatic workbench tracing.

### Prepare a measured-ring observation set

`backend.finite_observations.prepare_segment_observations(field, ring_points,
normal=..., blur_sigma=..., polarity="dark")` prepares a crop and observations
without calling an inverse fitter. Supply the saved rectified measurement
field, its already measured ring in global geometric pixels, a fixed unit chord
normal and an explicit common blur width in pixels. `polarity="light"` is also
supported. The function does not infer covariance, a physical material boundary
or the intended chord normal. `blur_sigma` controls padding, centre-search bounds
and the sampling-region margin; it is a preparation input, not an estimated PSF.

The integer padding is `ceil(max(16,8*blur_sigma))`. Lower bounds are
`floor(min(ring_points))-padding`; exclusive upper bounds are
`ceil(max(ring_points))+padding+1`. The full crop must fit the field, and its
threshold material must not reach the border. Neither clipping nor a search
for more favorable padding repairs a refused crop. Within the crop, border
medians, robust material levels, threshold crossings and a centered circle seed
define bounds and fixed samples from observations alone.

The result retains these distinct frames and data:

| Result | Contract |
| --- | --- |
| `field`, `training_values`, `heldout_values` | Preserve the source crop/selected values' dtype and bytes; initializer arithmetic uses a separate float64 buffer |
| `training_pixels`, `heldout_pixels` | Local integer indices; exactly 40 and 16 unique, disjoint samples with edge/material/background strata |
| `homography`, `crop_origin`, `crop_bounds` | Explicit global-to-crop translation and half-open crop bounds; pixel centres remain index plus 0.5 |
| `sensor_shape` | Cropped `(height,width)` for the later forward/fit call, rather than the original field dimensions |
| `seed_centre`, `bounds` | Global geometry coordinates; radius, fraction and their bounds retain their geometric units |
| `metadata()` | Detached provenance including field/ring/crop/selection hashes, estimates, policy and content binding |

Stored array descriptors and bytes are immutable; each exposed NumPy view is
read-only and fresh. Reshaping or changing the dtype of a caller's view cannot
alter the stored observation or reported sensor shape. Copy a view when mutable
working data is needed. `bounds` and metadata also return detached values.

`ObservationPreparationError.reason` distinguishes `invalid_input`, `nonfinite`,
`work_limit`, `crop_edge`, `contrast`, `insufficient_contour`, `seed_rank` and
`insufficient_stratum`. Limits are 16 million source pixels, one million crop
pixels, 20,000 ring points and 100,000 threshold crossings; blur width must lie
in `[0.001,1000]` pixels and observed contrast must reach 12 linear-light levels.
A returned seed is not a guarantee of truth containment, correct topology,
Gaussian optics or adequate illumination.

The [paired captured-field experiment](validation/finite-photo-intensity-v2.md)
uses one common preparation for both supplied covariance hypotheses. Its
held-out pixels are omitted from the nonlinear fitting objective; the same
image values still influence initialization and moment estimates. They are
not independent evaluation captures.

### Replay preparation without fitting

This example uses the bundled synthetic field and the saved **observational**
normal/common-width policy for the first version 2 case. It uses no fitted
geometry or evaluation truth and runs no inverse optimizer. Run from the
repository root after setup:

```python
import json
from pathlib import Path
import numpy as np
from backend.finite_observations import prepare_segment_observations

row = json.loads(Path("studies/results/finite-photo-intensity-v2.json").read_text())["rows"][0]
with np.load(row["capture_path"], allow_pickle=False) as saved:
    observations = prepare_segment_observations(
        saved["g"], saved["points"],
        normal=row["normal_from_observations"]["normal"],
        blur_sigma=row["common_sigma"],
        polarity="dark",
    )
assert observations.metadata() == row["preparation_metadata"]
assert observations.training_pixels.shape == (40, 2)
assert observations.heldout_pixels.shape == (16, 2)
print(observations.crop_origin, observations.sensor_shape)
```

For a new field, supply its own measured ring, fixed normal and declared width.
Catch `ObservationPreparationError` and retain its `reason` when preparation is
refused. A refused crop or stratum is not permission to silently clip padding,
drop samples or borrow a covariance from this synthetic example. The returned
`bounds` mapping can be passed explicitly to a later fit together with the
training arrays, crop `sensor_shape`, crop `homography` and supplied optics;
preparation itself does not make that fit or select a CAD boundary.

The handoff can be written as a caller-controlled function. Defining it below
does not run a fit; calling it performs the bounded inverse search described
later in this guide. Supply a separately justified covariance in squared
crop-pixel units (px²) and brightness bounds appropriate to the field:

```python
from backend.finite_centre_fit import fit_circular_segment

def fit_prepared(observations, covariance, *, level_bounds):
    return fit_circular_segment(
        observations.training_pixels,
        observations.training_values,
        sensor_shape=observations.sensor_shape,
        homography=observations.homography,
        psf_covariance=covariance,
        normal=observations.normal,
        level_bounds=level_bounds,
        **observations.bounds,
    )
```

Keep the held-out arrays outside that call. Geometry bounds already use global
coordinates; do not add the crop origin again or replace the crop transform
with an identity matrix while retaining those bounds. Inspect every completion
and ambiguity flag before interpreting a returned `best` result.

## Separable least squares

For each geometry, the two brightness columns are `A=T[1-P,P]`, with target
`z=T*y`. The code solves the bounded two-level linear problem directly by SVD
and enumerates its active faces. It then refines geometry against the actual
profiled residual cost. The supplied transform `T` can weight or project
observations; the result retains both raw and transformed residual norms and
its numerical residual rank. A projection does not establish agreement on
omitted image modes or a calibrated noise likelihood.

This follows the variable-projection principle described by
[O'Leary and Rust, section 2](https://www.cs.umd.edu/~oleary/software/varpro/varpro.pdf).
Their sample implementation leaves constrained linear variables out of the
inner solve. The bounded active-face extension here has separate derivative
controls; it is not supplied by that implementation.

On a fixed active face, let `A_F` contain its free brightness columns,
`r=z-A*c`, `B_j=A'_j*c`, and `P_F=I-A_F*A_F+`. The residual derivative is

```text
dr/dtheta_j = -P_F*B_j - (A_F+)^T*(A'_F,j)^T*r.
```

Both terms enter optimization. Only `P_F*B_j` measures the local change in the
mean after eliminating free brightness levels. Using the residual-dependent
second term as information could invent geometric identifiability from noise.
The reported geometry rank uses the projected mean, an arithmetic floor and
the ceiling `rank(T)-rank(A_F)`. It is not an uncertainty interval or a global
identifiability certificate. This rank is conditional on the selected brightness
face; at active bounds it does not describe the full feasible nuisance tangent
cone. Its condition number uses parameter columns scaled
by the supplied domain widths, so it depends on that parameterization.
Active-face transitions are piecewise smooth;
actual-cost checks remain necessary.

## Geometry derivatives and numerical coordinates

Reynolds transport gives probability derivatives as Gaussian boundary integrals.
For a fixed chord normal, outward normal velocities in parameter order
`(Cx,Cy,R,f)` are

| Boundary | Normal velocities |
| --- | --- |
| Circle arc, outward unit normal `u` | `(ux,uy,1,0)` |
| Closing chord | `(nx,ny,f,R)` |

With a supplied homography, the plane integral includes
`abs(det(DH))`. The moving endpoints have zero area measure. Derivatives are
integrated directly, rather than differentiating the adaptive quadrature program.
Their error estimates and finite-work statuses remain explicit.

The parameterized operator constructs its arc and chord in local coordinates
about `C`. It does not round three world-coordinate witnesses and reconstruct
a different circle. The general ring API retains its existing contract; both
paths use the same finite-Gaussian Green kernel. Exactly affine probability
queries can [share transformed curve panels](finite-affine-evaluation.md);
nonzero perspective terms retain the original scalar evaluator. The direct
shape Jacobian keeps its boundary integral and reuses existing curve samples
without dropping mapped-velocity finite checks. Extreme coordinates and requested
derivative tolerances can still be numerically unresolved.

## Developer contract and interpretation

`backend.finite_centre_fit.fit_circular_segment` accepts `pixels_xy`, `raw_values`
and keyword arguments `sensor_shape`, `homography`, `psf_covariance`,
`centre_bounds`, `radius_bounds`, `chord_fraction_bounds`, `normal`,
`level_bounds`, `residual_transform` and explicit search/work settings.
Domains and pixels must be defined from observations or independent knowledge,
before comparing a result with evaluation truth.

The validated input ranges are:

| Input | Contract |
| --- | --- |
| `pixels_xy`, `raw_values` | `N` unique in-frame integer `(x,y)` pairs, `1 <= N <= 2048`, and `N` finite real observations in the same order |
| `sensor_shape` | `(height,width)`, each an integer from 1 to `10**9` |
| `centre_bounds` | Two increasing `[low,high]` pairs, for global `x,y`, within `[-1e9,1e9]` |
| `radius_bounds` | Increasing pair within `[1e-3,1e6]` in geometry-plane units |
| `chord_fraction_bounds` | Increasing pair within `[-0.999,0.999]` |
| `level_bounds` | Shared increasing bounds for both brightness levels, within `[-1e6,1e6]`; default `(0,255)` |
| `normal`, `homography`, `psf_covariance` | Fixed unit pair, finite nonsingular 3×3 plane-to-observation map, and exactly symmetric positive-definite 2×2 observation-frame covariance; numerical conditioning and whole-domain chart checks also apply |

Every bounds pair must contain a representable interior float; adjacent-float
endpoints are refused. Numeric inputs must be finite real values, not booleans;
pixel indices, sensor dimensions and integer controls require integer types.
Covariance is not repaired by symmetrization or eigenvalue clipping.

| Search control | Default | Accepted range |
| --- | --- | --- |
| `grid_points` | 3 | Integer 3–5; the grid has `grid_points**4` entries |
| `refinement_iterations` | 32 | Integer 0–64 per selected seed |
| `max_basins` | 8 | Integer 0–16 |
| `max_evaluations` | 512 | Integer from `grid_points**4` through 4096; uncached objective attempts across the search |
| `forward_work_limit` | 20,000,000 | Integer 1–100,000,000; shared mean and derivative kernel work across the search |
| `probability_tolerance` | `1e-8` | `1e-12`–`1e-3`; an engineering numerical target, not physical uncertainty |

`residual_transform=None` uses the identity metric. A finite nonnegative vector
of length `N` multiplies each residual by that entry; these are residual
multipliers, not variances or automatically interpreted inverse standard
deviations. A finite real `M×N` matrix can mix or project observations, including
with signed entries. It requires `1 <= M <= 2048`, `M*N <= 500000` and
`M*N*max_evaluations <= 100000000`, using the declared objective-attempt budget.
The same fixed transform acts on the target and every model column. Zero weights
and discarded modes remain visible through `residual_rank`; they do not establish
agreement on the omitted observations or a calibrated noise model.

The standalone `circular_segment_probabilities` and `circular_segment_jacobian`
operators have different budget names/scopes from the inverse: `max_panels`
defaults to 4096 and accepts 1–8192 **per queried pixel**, while their
`max_evaluations` defaults to 2,000,000 and accepts 1–20,000,000 boundary/query-node
work units **across one operator call**. `fit_circular_segment` has no
`max_panels` argument and uses that 4096-per-pixel default. Each mean call receives
at most two million work units and each derivative call at most twenty million,
both reduced to the remaining shared `forward_work_limit`. Derivative calls do
not increment the inverse's objective-attempt counter. Cached reuse consumes no
new objective attempt or kernel work. Inspect returned work and statuses rather
than treating a cap as completed computation.

All four-dimensional coarse-grid evaluations retain their outcome. Represented local
basins, candidate costs, numerical guards, endpoint/tie/flat flags, unresolved
rank, unrefined basins and exhausted work remain visible. A work-limited or
unresolved result must not be turned into a successful photograph correction.
No finite grid or local refinement proves a global minimum. Quadrature guards
are engineering estimates, not certified bounds. The PSF and chord normal are
supplied hypotheses, not fitted outputs.

`fit_circular_segment` returns a `CentreFit` record, not a pass/fail certificate.
`best` can be absent, or present while `work_exhausted`,
`numerically_unsupported`, `refinement_limited` or `unrefined_basins` reports
incomplete work. Inspect `flat`, `tied`, `endpoint`, `rank_deficient` and
`geometry_rank` separately, together with held-out source residuals and the
declared model assumptions. `raw_residual_l2` and `transformed_residual_l2`
describe different metrics. A finite four-dimensional grid retains evaluated
points, not a certificate covering every cell. `global_search_certified`,
`psf_fitted` and `normal_fitted` remain false.

At defaults, `grid_points=3` proposes 81 coarse-grid points and requires
`max_evaluations >= 81`, though work exhaustion can prevent completing the grid.
At most eight seeds are selected for up to 32 refinement iterations each, with
512 objective attempts and a shared 20-million kernel-work cap. Derivative work
uses that shared cap and is counted separately from objective attempts. More
basins can remain represented and unrefined. These caps are resource limits,
not completion guarantees; callers can
set them explicitly. The independent study uses its own frozen settings. A
fit's latency depends on its observations, optics and search settings. The
original study's roughly 20-second fits remain historical results. The
[affine comparison](validation/finite-affine-batch.md) records 3.84× faster
complete fits across three fixed 40-training-pixel datasets, with candidate
medians of 2.75–3.91 seconds. It does not qualify interactive latency or all
supported transforms; projective evaluation retains the scalar path.

Measurements only along one level contour are insufficient when the two levels
are free: for constant observed value `c`, choosing `a=b=c` gives zero residual
for every geometry. A fixed observation region must include useful contrast and
both material/background support. Even then, short or cropped support, wrong
optics and model mismatch can leave geometry weak or biased.

The prospective experiment is specified in
[`studies/finite-free-centre-v1.json`](../studies/finite-free-centre-v1.json).
Its independent means use positive-area conic slices and conditional Gaussian
CDFs, separate from the production Green-boundary integral. Results and source
bindings belong to the [validation record](validation/finite-free-centre.md). The separate
[moment experiment](validation/finite-moment-photo.md) investigates a possible
initializer when covariance is missing; its background-sensitive proposals are
not accepted optical calibration or automatic CAD geometry.

## Requirements before automatic trace integration

The captured-field diagnostic retains two failures whose whole-sheet initializer
selects the reference border and excludes the actual part from the search box.
The [complete record](validation/finite-free-centre.md#captured-field-integration-diagnostic)
keeps these initialization failures separate from converged model bias. A
ring-conditioned developer bridge now supplies the explicit crop and snapshots
above. Its [new experiment](validation/finite-photo-intensity-v2.md) retains the
old diagnostic rather than substituting corrected results into it. Automatic
trace integration and physical/model qualification remain further work.

Integration also needs a supported thickness frame. The trace endpoint accepts
an omitted thickness or a positive value; omission means unknown thickness.
CAD builds require positive thickness and can retrace from the source photo.
The experiment's no-thickness correction is not evidence that a photographed
part has zero thickness or that a finite wall can be ignored.

An accepted intensity-fit boundary would need to preserve its centre, radius,
chord and source support through final assembly. Reapplying snapping, line or
fillet refitting, scalar blur correction or radius equalization can change the
chosen model. The polygon, analytic primitives, display bounds, notes and native
exports must describe the same final geometry. Optional-model rejection must
retain the existing trace or its ordinary actionable refusal; it must not be
misreported as missing reference paper. These are integration requirements,
not capabilities added by this developer API.
