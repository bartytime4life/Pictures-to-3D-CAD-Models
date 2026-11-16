# Mathematics and science audit — November 16, 2026

This review starts from main `40cfbe480d603976264c04c3b3031146fd1e8a01`
(PR #154). It checks the current reconstruction assumptions, supplies reproducible
Gaussian identities, repairs one constrained-optimization defect in a separate
change, and records an unresolved two-dimensional lighting counterexample.
It is a bounded review of the methods below, not a proof of every program path
or a measured-camera accuracy qualification. Earlier failed studies remain intact.

This documentation is stacked on the proposed [shadow-solver repair, PR #155](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/155).
Its verified runtime tree is `4ba0f20f17953c3e39e2771604bbddae59bb9b36`.
The [local verification record](validation/evidence/science-audit-20261116/verification.json)
contains the final test commands, exclusions and source/log hashes.

## Method-to-evidence map

| Stage                       | Mathematical model and check                                                                                                                                                                  | What the result does not identify                                                                             |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Reference-sheet calibration | A planar homography and square-pixel, centered camera constraints; axis assignment must survive the declared corner box. [Method and tests](validation/sheet-axis-orientation.md)             | Full camera calibration, principal-point error, sheet curl, or actual paper-size tolerance                    |
| Lens correction             | Central-branch inverse of `r_d=r_u+k1*r_u^3`, with a sign bracket and a finite domain. [Independent numerical checks](validation/radial-inverse.md)                                           | A real lens with additional radial/tangential terms or computational-camera warps                             |
| Intensity and color         | Decode the stated sRGB curve before linear mixing; luma reconstruction addresses selected subsampled formats. [Current tracing method](reference-sheet.md#3-segmentation-and-sub-pixel-edges) | Unknown local tone mapping, sharpening, or recovery of missing chroma samples                                 |
| Resampling and blur         | Pixel-center conventions, Keys cubic interpolation, normal-profile widths, and conditional covariance transport                                                                               | Complete spatially varying PSF identification; small covariance residual is not physical adequacy             |
| Shadow fitting              | Quadratic paper light plus a nonnegative footprint-convolution kernel, with a regularizer                                                                                                     | A unique hidden shadow under the part, or an independent validation set: the near band also selects the prior |
| Constrained optimization    | Primal feasibility, dual feasibility, stationarity and complementarity; [solver repair and evidence](validation/shadow-kkt.md)                                                                | Correctness of the optical model or a guaranteed dimensional improvement                                      |
| Edge lighting               | Truncated Gaussian moments give exact affine/quadratic one-dimensional identities; script below                                                                                               | A normal-line integral is not a general two-dimensional lighting model                                        |
| Thick parts                 | Parallel planes, vertical walls, known entered thickness and conditional camera pose; two-step profiles                                                                                       | Chamfers, filleted walls, nonuniform wall color, or well-conditioned wall/edge separation in every opening    |
| Circles, corners and arcs   | Finite support, canonical joins, conditional Gaussian curvature/corner models and radius diagnostics                                                                                          | Hidden geometry, true design intent, or a manufacturing confidence interval                                   |
| Finite-material inverse     | Supplied geometry class, optics and observation contract; [developer model](finite-shape-inverse.md)                                                                                          | A generally selected production model or arbitrary-photo optical calibration                                  |
| CAD and printing            | Analytic primitives, units, boundary validity, tessellation and conservative bed envelopes                                                                                                    | Physical fit, strength, slicer interpretation or a printed specimen                                           |
| AI relief                   | Affine-invariant inverse-depth prediction, mapped to the entered relief range                                                                                                                 | Metric 3-D, guaranteed depth ordering, hidden surfaces or physical height ratios                              |
| Measurement uncertainty     | Separate calibration dimensions from reserved dimensions; [engineering checks](engineering-model.md)                                                                                          | A numerical physical uncertainty budget from synthetic seeds or fit residuals alone                           |

[Zhang's primary calibration paper](https://www.microsoft.com/en-us/research/publication/a-flexible-new-technique-for-camera-calibration/)
uses multiple planar views for full calibration. This project's conditional
single-image focal calculation fixes additional intrinsic assumptions; citing
Zhang does not remove them. [W3C's conversion code](https://www.w3.org/TR/css-color-4/#color-conversion-code)
specifies the transfer function used here, rather than certifying a phone's
processing pipeline.

## Quadratic illumination: avoid counting blur twice

Let an edge lie at zero, with sharp material light
`A(t)=a0+a1*t+a2*t²` on the negative side and paper light
`B(t)=b0+b1*t+b2*t²` on the positive side. Under a centered one-dimensional
Gaussian of standard deviation `s`, its value at the geometric edge is

```text
I(0) = (a0+b0)/2 + (b1-a1)*s/sqrt(2*pi) + (a2+b2)*s²/2.
```

This follows by integrating `1`, `t` and `t²` over each Gaussian half-line.
But the observed full-plateau quadratics are `P=A+a2*s²` and `Q=B+b2*s²`.
In terms of these observed plateaus, the same identity is

```text
I(0) = (P(0)+Q(0))/2 + (Q'(0)-P'(0))*s/sqrt(2*pi).
```

Adding another `(a2+b2)*s²/2` to that second expression would double-count
curvature. This corrects the earlier proposed extension before adoption. A
quadratic fitted to finite, step-contaminated windows need not recover either
full plateau; the identity alone does not justify changing the tracer.

`scripts/science_model_audit.py` checks 12 coefficient/width cases against
independent 128/256-point Gauss–Legendre quadrature over ten Gaussian widths.
It reports order convergence separately from error against the identity.
No quadratic edge estimator is enabled by this review.

## A remaining two-dimensional light term

For a locally straight edge with unit normal `n` pointing into paper, Gaussian
covariance `S`, flat material level `A`, and affine sharp paper light `L` with
gradient `g`, integrating the two-dimensional half-plane gives

```text
s² = nᵀ S n
I(edge) = (A+L(edge))/2 + gᵀ S n / (sqrt(2*pi)*s).
```

The production normal-line approximation instead contributes
`(gᵀ n)*s/sqrt(2*pi)`. It misses the tangent/normal covariance term. Even with
isotropic blur, non-affine light can require integration across the tangent;
sampling only the normal does not perform that integral.

The committed counterexample uses `S=[[4,3],[3,9]] px²`, `n=(1,0)`, `g=(0,1)`
light units per pixel, material 20, and paper 180 at the edge. The exact
two-dimensional level is **100.5984134206**; the current routine returns
**99.9999478413**, including its finite quadrature/truncation error.
An independent conditional-Gaussian integral agrees with the exact level.
The leading displacement estimate is **0.01875 px**, using the step's central
slope; this is not a measured final trace error. The example supplies the light
field directly, isolating the edge-level routine from shadow estimation.

A candidate replacement would integrate
`L(p + n*t + (S*n/s)*z + tangent*sqrt(det(S)/s²)*v)` for `z>0`,
where `z` and `v` have standard-normal densities. It must also bind the covariance
to the local frame, model both sides where necessary, and pass independent
convergence, lighting-mismatch and latency checks before changing production.
The present solver repair does not deliver this correction.

The conditional-tangent variance `det(S)/(nᵀ S n)` also explains why normal
variance alone is insufficient for curvature. [Elsey and Esedoğlu's appendix](https://websites.umich.edu/~esedoglu/Papers_Preprints/elsey_esedoglu_anisotropy.pdf)
gives the related leading-order threshold-motion expansion; it is not an
end-to-end camera error bound.

## Optimization, conditioning and uncertainty

[Variable projection](https://www.nist.gov/publications/variable-projection-nonlinear-least-squares-problems)
can eliminate linear brightness parameters for each geometry candidate. It does
not make the remaining nonlinear geometry problem identifiable or globally solved.
Regularization changes the objective, and normal equations can amplify poor
conditioning. The repaired shadow solve equilibrates coefficient units, checks
KKT conditions to a scaled floating tolerance, and retains the profile-line path
if the numerical solve fails. These are numerical safeguards, not optical evidence.

Radius residuals, seeded Monte Carlo spreads, interval corner screens and physical
uncertainty answer different questions. The corner screen encloses a declared
perturbation scenario; the seed studies cover their simulated noise/model; neither
supplies an empirical distribution of actual sheet, lens and part errors.
[JCGM GUM-6:2020](https://www.bipm.org/documents/20126/2071204/JCGM_GUM_6_2020.pdf)
provides primary guidance on constructing measurement models.
[JCGM's publication list](https://www.bipm.org/en/committees/jc/jcgm/publications)
also identifies the distribution-propagation and conformity-assessment guides.
A physical uncertainty budget needs measured inputs and model-discrepancy evidence;
arbitrarily chosen synthetic noise distributions cannot supply that evidence.

## Relief depth and bas-relief ambiguity

[Depth Anything V2, §5.2](https://arxiv.org/html/2406.09414v2)
describes affine-invariant inverse depth. Under the ideal model `d=a/z+b`, two
distinct measured camera depths can determine `a,b` algebraically. The training
objective does not guarantee that the entire predicted map satisfies that model;
reserved depths are still needed to check it. Normalizing disparity directly to
a relief height also does not preserve metric depth ratios.

[Belhumeur, Kriegman and Yuille](https://www.cs.jhu.edu/~ayuille1/PubsJournal/J52BelhumeurKriegmanYuille99.pdf)
establish generalized bas-relief ambiguity for orthographic Lambertian imaging
with corresponding changes to illumination **and albedo**. It is a conditional
nonuniqueness result, not permission to treat any flattened relief as the measured
shape of a shiny, textured or perspective-viewed object.

## Reproduction and next acceptance checks

```bash
.venv/bin/python -m pytest -q tests/test_shadow_optimality.py
.venv/bin/python -m scripts.shadow_solver_audit /tmp/shadow-replay.json
.venv/bin/python -m scripts.science_model_audit /tmp/science-identities.json
```

The [saved model-identity report](validation/evidence/science-audit-20261116/model-identities.json)
binds the numerical examples to source hashes. Its successful identity checks
are separate from its explicitly unresolved model counterexample. The
[solver record](validation/shadow-kkt.md) records regression checks and test
changes. Current CI, installation, real photographs and physical fitting remain
separate evidence.

The next optical change should first freeze independent two-dimensional light
fields, covariance orientations and non-Gaussian controls, then compare both
edge displacement and downstream dimensions. A measured-photo study should
reserve caliper dimensions from calibration and report refusals and unmatched
features along with scored results. General 3-D reconstruction additionally
needs new views, known shape constraints or explicitly labeled learned priors;
extra equations cannot identify unseen surfaces from this input alone.
