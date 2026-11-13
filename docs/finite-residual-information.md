# Separate blur sensitivity from geometric sensitivity

This prospective developer study asks what the existing circular-segment
observations can distinguish locally. It retains every archived case and
covariance lane from the [measured-ring replay](validation/finite-photo-intensity-v2.md).
It does not rerun the inverse, reselect samples, calibrate a camera or change
photo tracing. A separate local plan has been frozen before new archived derivative or trial-step
calculations. The work-in-progress plan and runner are not included in this source.

**Status: research proposal; no archived-data result or runnable command in this
source.** The separate implementation remains under review. The sections below
describe a planned protocol, not a completed 12-row replay or a validated optical
correction. Read the [source status](project-status.md) and
[completed affine evidence](validation/finite-affine-batch.md) for current capabilities.

## Project nuisance directions before interpreting blur

For a supplied Gaussian covariance and geometry, write the predicted intensity
vector as `mu = a*(1-P) + b*P`. At the archived fitted point, the derivative
blocks are

```text
B = [1-P, P]                     # only free brightness levels
G = (b-a) * dP/d(Cx,Cy,R,f)      # existing mean-shape derivatives
S = (b-a) * dP/dq                # three covariance-chart directions
N = (b-a) * dP/dphi              # rotation of the supplied chord normal
```

Geometry columns are scaled by their observed search-domain widths. This makes
their coordinates fractions of those widths; it does not introduce a physical
prior. Brightness at an active bound has no free tangent column for that face.
This fixed-active-face diagnostic is not the full feasible inward tangent cone.
The diagnostic uses mean derivatives, rather than the residual-dependent
Jacobian of a profiled optimization objective.

Let `T` contain the nuisance columns, and let `Q` span their supported column
space with orthonormal columns. The distinct covariance directions are

```text
C = (I - Q Q^T) S.
r_perp = (I - Q Q^T) (y - mu).
```

A covariance direction lying in the nuisance span supplies no additional local
information. More samples than parameters is insufficient: the sampled
geometric directions must support the missing components. A single straight
edge mainly constrains the normal variance `n^T Sigma n`; its three matrix
entries cannot be recovered separately from that one direction.

The singular values of `C`, its rank relative to the original unprojected
scale, and its overlap with the geometric space matter more than an automatic
reduction in residual sum of squares. Renormalizing a nearly zero projected
column can turn floating-point noise into apparent information. The planned experiment will
retain the full spectra, finite-difference discrepancies, cutoffs and uncertain
rank cutoff-sensitivity intervals. Neither full numerical rank nor a small residual establishes a
global solution or a physical uncertainty bound.

Nuisance derivatives also have numerical error. If the nuisance matrix has
full column rank, its smallest singular value is `smin`, and its estimated
matrix-error allowance `etaT` is below `smin`, a conservative projector guard is

```text
etaP = min(1, 2*etaT/(smin-etaT)),
etaC = etaS + etaP*(||S||2 + etaS).
```

For an actual matrix perturbation bounded by `etaT`, full rank persists by the
singular-value perturbation inequality. Projecting a unit vector in the
perturbed span onto the original span bounds the sine of their largest principal angle by
`etaT/(smin-etaT)`; the factor two leaves a conservative allowance. The second
expression propagates that projector difference into the covariance columns.
The computation also retains SVD/projection roundoff. Because the forward and
derivative allowances are engineering estimates, these expressions are used
as estimated guards rather than certified rank bounds. A missing rank gap
leaves covariance uniqueness and the trial step unknown.

Reported rank intervals describe sensitivity to the declared cutoff, not a
confidence interval or a rigorous interval for true rank. A reported zero
means no directions resolved under that guard. It does not prove the data
contain no physical covariance information.

This use of separable structure is motivated by the
[variable-projection treatment by O'Leary and Rust](https://www.cs.umd.edu/users/oleary/software/varpro.pdf).
The sample implementation omits constrained linear variables; the proposed
brightness-face treatment needs its own checks.
[Berisha, Nagy and Plemmons](https://scispace.com/papers/estimation-of-atmospheric-psf-parameters-for-hyperspectral-1fahvmg6oj)
also identify ill-conditioned Jacobians in a different PSF-estimation problem.
Their abstract motivates checking conditioning here; their recovery results do
not validate this part model.

The proposed covariance-specific residual energy is `||Q_C^T r_perp||²`,
where `Q_C` contains the retained orthonormal directions of the guarded projected
matrix `C`. It must be withheld if used finite differences, nuisance projection
or rank sensitivity remain unresolved. A zero retained rank means zero resolved
energy under the numerical guard, not zero physical information. Subtracting the
residual sums from two independently truncated SVD solves is only a raw diagnostic:
the retained spaces need not be nested. A dimension ceiling must not hide an
unstable raw rank interval or qualify more basis vectors than the reported rank.

## Keep covariance perturbations positive definite

With `Sigma0 = L L^T`, use the local chart

```text
Sigma(q) = L exp(q1 E1 + q2 E2 + q3 E3) L^T,
E1 = [[1,0],[0,0]],
E2 = [[0,0],[0,1]],
E3 = [[0,1/sqrt(2)],[1/sqrt(2),0]].
```

The symmetric bases are orthonormal in Frobenius norm. Every finite symmetric
chart value gives a positive-definite covariance in exact arithmetic; numerical
finite and conditioning checks remain necessary. Central differences at the
fixed step and half step will be compared before a direction is interpreted.
The protocol requires an independent positive-area conic check of the covariance
perturbations, separate from the production Green-boundary kernel.

## A local trial is not a recovered optical model

The proposed one-step coefficient vector would be selected from the 40 training intensities
only. A fixed common damping factor limits covariance, geometry, normal and
brightness changes and keeps the trial inside the original domains. There is
no line search, repeated correction or new nonlinear fit. Each eligible actual bounded
trial would be evaluated once, retaining its discrepancy from the linear prediction.
The original 16 held-out values would be scored without refitting the trial.

Those held-out pixels already influence preparation and moment proposals.
They remain useful conditional diagnostics, with edge/material/background
residuals reported separately, but are not independent optical calibration or
external prediction. Truth would be read only after trial predictions are selected,
for descriptive synthetic evaluation; it does not choose the step or domains.

The saved photo fields include detector-area coverage, sampled blur, encoding,
resampling and smoothing. A fitted effective Gaussian can absorb discrepancies
from those operations. Resampling itself can alter effective resolution and
aliasing, as discussed by [Cardoso and colleagues](https://arxiv.org/pdf/2101.06440).
A covariance direction that explains a residual therefore identifies a useful
model extension to test, rather than the physical cause of that residual.
A future acquisition-matched experiment needs its actual source samples,
transform, finite kernels and stage bytes preserved; the current portable
archives do not contain enough information to reconstruct that old chain exactly.

## Evidence needed before using the diagnostic

| Stage | Required record |
| --- | --- |
| Prospective review | Fixed source and input hashes, all 12 identities, original pass flags, sample indices, numerical guards and refusal rules |
| Archived replay | All ten eligible and two upstream rows; raw means, derivatives, estimated errors, spectra, residual strata, step choices and refusals; no new optimizer |
| Independent saved-data audit | Recomputed arithmetic and source closure, independent subspace checks away from cutoffs, preserved failures and unknowns |
| Acquisition-matched experiment | Raw source samples, actual transform, finite kernels, encoding/resampling details and stage bytes; separately declared matched and adverse controls |
| Product adoption | Supported optics and thickness frames, measured-photo checks, bounded latency, and one accepted boundary preserved through preview and exports |

Neither a passed parser contract nor this derivation substitutes for the archived
replay. A successful local diagnostic would still need the acquisition-matched
and physical checks above. Current replay commands remain in
[developer tools](developer-tools.md); this proposal adds no command to that list.
