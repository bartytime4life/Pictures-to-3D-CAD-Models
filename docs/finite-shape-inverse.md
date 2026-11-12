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

In the workbench, `g` is a Keys-resampled linear-light mix followed by smoothing.
Its empirical rectified covariance is not a calibrated sensor PSF. Passing `g`
and an identity homography to this model is an effective-Gaussian hypothesis;
it does not reproduce the complete acquisition operator. Missing covariance
remains unknown. A fixed-covariance study cannot establish its value for a
different photograph.

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
identifiability certificate. Its condition number uses parameter columns scaled
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
paths share the finite-Gaussian evaluator. Extreme coordinates and requested
derivative tolerances can still be numerically unresolved.

## Developer contract and interpretation

`backend.finite_centre_fit.fit_circular_segment` accepts `pixels_xy`, `raw_values`
and keyword arguments `sensor_shape`, `homography`, `psf_covariance`,
`centre_bounds`, `radius_bounds`, `chord_fraction_bounds`, `normal`,
`level_bounds`, `residual_transform` and explicit search/work settings.
Domains and pixels must be defined from observations or independent knowledge,
before comparing a result with evaluation truth.

All four-dimensional coarse-grid evaluations retain their outcome. Represented local
basins, candidate costs, numerical guards, endpoint/tie/flat flags, unresolved
rank, unrefined basins and exhausted work remain visible. A work-limited or
unresolved result must not be turned into a successful photograph correction.
No finite grid or local refinement proves a global minimum. Quadrature guards
are engineering estimates, not certified bounds. The PSF and chord normal are
supplied hypotheses, not fitted outputs.

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
