# Separate blur sensitivity from geometric sensitivity

This developer study asks what the existing circular-segment observations can
distinguish locally. The [frozen plan](../studies/finite-residual-information-v1.json)
and [runner](../studies/verification/finite-residual-information-v1.py) retain
all 12 archived case/lane records, using the existing samples and fitted points.
They run no inverse optimizer, renderer, re-preparation or automatic correction.

**Status: the fixed replay is complete and its overall protocol failed.** The
normal-angle control exceeds the frozen absolute step/half-step criterion, and
all ten eligible normal columns fail their stability guard. The covariance-only
calculations remain conditional on the supplied normal. Read the
[full results, retained unknowns and limits](validation/finite-residual-information.md)
and [lossless archive/review commands](../studies/fixtures/finite-residual-information-v1/README.md).
A separate post-hoc rotation identity below motivates the next independent
experiment; it does not replace the failed control or unknown normal columns.

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
column can turn floating-point noise into apparent information. The saved experiment retains
the full spectra, finite-difference discrepancies, cutoffs and uncertain
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
The sample implementation omits constrained linear variables; the fixed-face
brightness treatment needs its own checks.
[Berisha, Nagy and Plemmons](https://scispace.com/papers/estimation-of-atmospheric-psf-parameters-for-hyperspectral-1fahvmg6oj)
also identify ill-conditioned Jacobians in a different PSF-estimation problem.
Their abstract motivates checking conditioning here; their recovery results do
not validate this part model.

The reported covariance-specific residual energy is `||Q_C^T r_perp||²`,
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
fixed step and half step are compared before a direction is interpreted.
The protocol requires an independent positive-area conic check of the covariance
perturbations, separate from the production Green-boundary kernel.

## A local trial is not a recovered optical model

Each one-step coefficient vector was selected from the 40 training intensities
only. A fixed common damping factor limits covariance, geometry, normal and
brightness changes and keeps the trial inside the original domains. There is
no line search, repeated correction or new nonlinear fit. Each eligible actual bounded
trial was evaluated once, retaining its discrepancy from the linear prediction.
The original 16 held-out values were scored without refitting the trial.

Those held-out pixels already influence preparation and moment proposals.
They remain useful conditional diagnostics, with edge/material/background
residuals reported separately, but are not independent optical calibration or
external prediction. Truth was read only after trial predictions were selected,
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

## Analytic rotation sensitivity: a post-hoc next hypothesis

For a translation-only image map, let `q` be the global pixel centre, `C` the
segment centre, and `J = [[0,-1],[1,0]]`. Rotating the material by `phi` around
`C` is equivalent to rotating the query and covariance back into the original
shape frame:

```text
P_phi(q, Sigma) = P_0(C + R(-phi)*(q-C), R(-phi)*Sigma*R(-phi)^T),
dP/dphi = dP/dC dot J*(q-C) + D_Sigma P : (Sigma*J-J*Sigma).
```

The identity follows by a change of variables in the Gaussian area integral.
At zero rotation, `dR(-phi)/dphi = -J`; translation invariance gives
`dP/dq = -dP/dC`. The covariance derivative follows the matrix product rule.
For the supplied chart `Sigma = L L^T`, express
`L^-1*(Sigma*J-J*Sigma)*L^-T` in the three symmetric bases above to combine the
saved `S` columns with the centre derivatives. Unscale centre derivatives and
their error estimates by their domain widths. Both saved blocks already carry
the brightness contrast; do not multiply it again.

The frame is essential: for the archived crop translation `b`, use
`q_global = pixel_local + 0.5 - b`, or use `q_local-H(C)` consistently.
Subtracting a global centre from a local pixel gives a different derivative.
This expression is restricted here to the archived translation-only maps;
a general affine map needs covariance/coordinate transport, and a perspective
map needs a separate derivation.

The [separate saved-array script](../studies/verification/finite-normal-rotation-saved-v1.py)
retains all 12 records and compares the identity with the saved coarse and fine
normal differences. Its coarse/fine maximum discrepancies have ratios
**3.9991–4.0020**, consistent with second-order central-difference truncation.
This is post-hoc consistency using shared production derivatives, not an
independent test or a new `N` qualification. The full original failure remains.

## Finite-chord shape derivative: a derived proposal

Let the complete material be `K = disc(C,R) intersect {n dot (x-C) <= R*f}`,
with unit normal `n`, `R>0`, and `-1<f<1`. Rotate `n` counterclockwise about the
fixed centre while holding `R` and `f` fixed. With `t=J*n`, `h=R*f`, and
`ell=R*sqrt(1-f²)`, the chord is `X(s)=C+h*n+s*t`. Its outward normal velocity
is `-s`; the circular boundary has zero normal velocity.

For a fixed nonsingular homography `H` from the shape plane to the observation frame, the
Gaussian point-probability derivative is

```text
dP/dphi = -integral(s * Gaussian_Sigma(p-H(X(s))) * abs(det DH(X(s))),
                   s=-ell..ell).
```

Here `p` is an observation pixel centre and `Sigma` is a supplied, fixed SPD
Gaussian covariance in that same frame, in pixel-squared units. `dP/dphi` is
signed probability per radian; it is not restricted to `[0,1]`. The intensity
derivative also multiplies by `b-a`.
This assumes the entire finite material domain and a Gaussian point observation,
not a threshold contour or an unspecified resampling/pixel-aperture operator.
A nonlinear lens map is outside this homography derivation.

The projective chart must stay strictly away from its horizon over the **whole
shape**, not just the chord. Normalize its denominator to `w(x)>0` on that
domain, so `abs(det DH)=abs(det H)/w³`. A reflected map still uses the absolute
Jacobian; changing the homogeneous sign or scale of `H` changes no result.

An exact reparameterization reduces both affine and projective maps to one
Gaussian first moment. Set `X0=C+h*n`, `w(X0+s*t)=w0+s*w1`, `k=w1/w0`,
`y0=H(X0)`, `V=DH(X0)*t`, and `J0=abs(det DH(X0))`. Then

```text
z = s/(1+k*s),       zlo = -ell/(1-k*ell),   zhi = ell/(1+k*ell),
H(X(s)) = y0+z*V,
dP/dphi = -J0 * integral(z * Gaussian_Sigma(p-y0-z*V), z=zlo..zhi).
```

For `Sigma=L*L^T`, define `W=L^-1*V`, `r=L^-1*(p-y0)`, `lambda=||W||`,
`b0=(W/lambda) dot r`, `c0=cross(W/lambda,r)`,
`ulo=lambda*zlo-b0`, and `uhi=lambda*zhi-b0`.
Writing `Phi` and `varphi` for the standard normal CDF and density gives

```text
dP/dphi = -J0 * exp(-c0²/2) / (sqrt(2*pi)*sqrt(det Sigma)*lambda²)
          * (b0*(Phi(uhi)-Phi(ulo)) + varphi(ulo)-varphi(uhi)).
```

Affine maps have `k=0`. Projective limits are generally asymmetric, so an affine
oddness or zero-symmetry shortcut cannot be reused without its assumptions.
This identity is not a numerically qualified evaluator. Tail-safe CDF
differences, narrow-interval and first-moment cancellation, representability,
and charged fallback work still need checks. [Weckesser's numerical note](https://warrenweckesser.github.io/notes/truncnorm.html)
explains why tail reformulations alone do not cure narrow-interval subtraction;
[Apache's implementation discussion](https://commons.apache.org/proper/commons-statistics/commons-statistics-distribution/javadocs/api-1.3/src-html/org/apache/commons/statistics/distribution/TruncatedNormalDistribution.html)
also records moment cancellation. These are numerical background, not validation
of this derivative.

Independent quadrature in the original `s` coordinate and positive-area angular
differences at new synthetic scenes remain prospective checks. No new API,
numerical qualification or production correction is established here, and the
[original failed protocol](validation/finite-residual-information.md) remains
unchanged. Real acquisition, illumination, thickness and calibration assumptions
remain separate from this conditional Gaussian derivation.

## Remaining evidence

The saved-data audit verifies arithmetic and source binding, not physical PSF
causation. Normal sensitivity still needs independent numerical validation.
An acquisition-matched experiment needs actual source samples, transforms,
finite kernels, encoding/resampling details and stage bytes. Product adoption
also needs supported optics/thickness frames, measured-photo checks, bounded
latency and one accepted boundary preserved through preview and exports.
