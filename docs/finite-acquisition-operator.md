# Finite-material acquisition operators

The completed continuation evaluates **16 new synthetic source scenes at two
output scales, giving 32 records**, with supplied true geometry, levels and a
known map. On the decoded-PNG lane, the nominal Gaussian is incompatible with
the one-level criterion in **27/32** records and compatible in five. Matching
second moments leaves **16 incompatible, 15 compatible and one inconclusive**.
The moment-matched unquantized lane still has nine incompatible comparisons.
Second-moment closure therefore does not reproduce this complete acquisition
operator. Read the [full record](validation/finite-acquisition-operator.md) and
[portable archive workflow](../studies/fixtures/finite-acquisition-operator-v1/README.md).

The [analytic-normal experiment](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/blob/0f1adbd391f7fa015f458cca60dcfe2a0e2dad9e/docs/validation/finite-analytic-normal-information.md)
motivated this forward check: smaller fitted intensity residuals did not always
improve synthetic geometry. The new
[frozen plan](../studies/finite-acquisition-operator-v1.json) crosses two finite-D
geometries, two discrete blur kernels and four subpixel placements. No inverse
fit, new derivative or covariance estimate is evaluated. These results add no
acquisition-aware mean, inverse or automatic workbench correction.

The study is bound to its recorded source, not the newer publication base
`68a67e766956ac41a3b73ae73d4ac553ef47db26`, which includes the soft-shadow
model. The archive includes all 87 recorded source/input files for saved-data
verification. It does not retest current main or alter its tracing pipeline.

## Preserve both execution and serialization failures

The first execution **exited 1 before any capture**: the stage helper listed a
nonexistent `tests/__init__.py`. Its exact Keys, production Keys and four
independent Gaussian controls passed. All 32 failed rows and 128 unknown cells
remain in the
[immutable first-attempt archive](../studies/fixtures/finite-acquisition-operator-v1/bootstrap-failure/manifest.json).
The [separately frozen continuation](../studies/finite-acquisition-operator-v1-continuation-v1.json)
repairs source bootstrap only and reuses those completed controls explicitly.
It performs 64 new main forward batches/28,224 queries; the four reused
control batches/24 queries have separate provenance and work totals.

The continuation process exited 0 and its in-memory protocol flag was true,
but its raw report **fails the native JSON scalar contract at 320 fields**.
It retains 32 NumPy booleans and 288 float32 allowances as explicit
`invalid_python_value` markers. A separate saved-only conversion restores
native scalar representations at strictly enumerated paths; it replaces no raw
report, performs no scientific replay and changes none of the 128 adequacy
categories. Independent saved-data arithmetic checks corroborate those
categories. A process exit, serialization integrity and model adequacy remain
distinct results.

For saved review, use the archive workflow above. The historical continuation
entry point, `studies/verification/finite-acquisition-operator-v1-continuation-v1.py`,
generates scenes and evaluates forward models when explicitly executed. It is
retained with its frozen plan and source admission checks for provenance.
Current main has changed since that freeze; fresh numerical execution needs a
separately qualified source/environment and a new experiment record. It cannot
replace the first attempt or its completed continuation. The continuation's
source-admission checks reject the changed current-main closure before capture;
the saved-only archive workflow is the supported review path here.

## Completed forward comparisons

Each cell below compares 441 fixed query points at the supplied geometry and
levels. The 32 records share 16 source scenes; the two output scales are derived
views, not independent captures.

| Gaussian hypothesis / stage | Compatible | Incompatible | Inconclusive |
| --- | ---: | ---: | ---: |
| Nominal / unquantized | 7 | 24 | 1 |
| Nominal / decoded PNG | 5 | 27 | 0 |
| Moment-matched / unquantized | 23 | 9 | 0 |
| Moment-matched / decoded PNG | 15 | 16 | 1 |

Moment matching improves maximum residuals in many records but worsens them in
two unquantized and three decoded-PNG comparisons. Its largest discrepancies
are 2.21467 and 2.32389 intensity levels respectively, at the same major-isotropic
scene and output scale 1.25. The unquantized failures establish mismatch without
the PNG round-trip. This combined operator experiment does not isolate each
stage's causal contribution, recover geometry or explain historical fit errors.

## Follow the actual source semantics

The historical fields used `tests.synthetic._flat_photo`, rather than its
separate general `render` function. The flat path computes polygon pixel
coverage, mixes constant linear-light colors, applies a discrete blur, encodes
sRGB and rounds to an 8-bit PNG. The subsequent reference-sheet measurement
path decodes a channel mix, applies Keys rectification and adds 0.7-pixel Gaussian
smoothing. Those historical scenes contain no JPEG compression, random noise,
lighting gradient or finite wall model.

The new experiment makes every stage explicit:

```text
analytic finite D -> inscribed polygon -> source pixel coverage
  -> fixed discrete blur -> unquantized linear field
  -> optional sRGB encoding / 8-bit rounding / PNG / decoding
  -> known affine Keys resampling -> 0.7-pixel smoothing.
```

The two source brightness values are **encoded** material 40 and background 230.
They are decoded with the generator's `srgb_to_linear` before the source mix.
Metadata uses linear levels in `[background, material]` order. These numeric
inputs are neither inferred plateaus nor a camera-response calibration.

The source polygon has 8,193 arc vertices. The Gaussian comparator uses the
analytic arc/chord D, so the polygon approximation needs its own bound and
independent coverage checks. Known maps replace sheet detection for this
experiment; a small detected-sheet error is a competing mechanism left out of
this first controlled comparison.

The earlier portable archives retain processed fields, but not all original
source PNGs, actual estimated maps and intermediate stage arrays. The new study
cannot establish the cause of their historical residuals or geometry errors.
It must preserve those earlier results.

## Keep pixel centres and transformations explicit

The coverage rasterizer labels array index `j` by a physical centre `j/ppm+x0`.
Its internal half-pixel shift turns polygon area into the fraction of that
pixel's square. Photo geometric coordinates instead label the centre by
`j+0.5`.

For this new unit-pitch source with a 16-pixel margin, the plane-to-photo map is

```text
M = [[1,0,16.5], [0,1,16.5], [0,0,1]].
```

That `+0.5` records the generator convention. It is not another shift to apply
to existing traced rings. `sheet.rectify_gray` queries plane positions
`((i+0.5)/q,(j+0.5)/q)` and subtracts 0.5 before sampling array indices. The
continuous-Gaussian API queries integer index pairs at index plus 0.5 and uses
`Hout=diag(q,q,1)`. The two output scales are `q=1` and `q=1.25`.

Every query, crop/map, array dtype and kernel must stay bound to this convention.
The same 441 output indices are used for both stage lanes and both Gaussian
comparators within a record. They are forward diagnostic samples, not training
and held-out data.

## An unrounded linear model before encoding

Let `c_k(theta)` be the fraction of source cell `Q_k` inside the finite material:

```text
c_k(theta) = area(Q_k intersect K(theta)) / area(Q_k).
A = G R W,
y_ideal(theta) = A [b*1 + (a-b)*c(theta)],
```

where `b` is linear background, `a` linear material, `W` the supplied discrete
optical kernel, `R` the known Keys map and `G` the post-resampling smoother.
The two brightness columns are `[A*1-A*c, A*c]`. Simplifying to
`b+(a-b)*A*c` requires `A*1=1`; raw finite kernel coefficients need not preserve
constants exactly. Plateau controls test the actual floating implementation.
Replicated/reflected borders and finite support remain part of the operator.

For fixed geometry, map and kernels, this **ideal unrounded expression** is
separable in the two levels. Actual stored float32 stages introduce rounding,
so the executable unquantized chain is not literally affine in the levels.
The following PNG expression is likewise schematic, omitting those casts:

```text
y_PNG = G R decode(round8(encode(W [b*1+(a-b)*c]))).
```

Rounding and transfer functions sit before rectification. They are nonlinear
in the source levels, so a two-column variable-projection solve would not be
an exact photometric model of that branch. This study supplies the levels and
performs no brightness solve.

## Signed Keys weights and formal moments

The interpolation family follows [Keys's original paper](https://ncorr.com/download/publications/keysbicubic.pdf).
The moment identities here are derived and checked for this experiment.
For Keys parameter `a=-1/2`, interpolation at fractional index `f` uses source
nodes `k=-1,0,1,2`. With weights `w_k`, exact algebra gives

```text
sum(w_k) = 1,
sum(w_k*(k-f)) = 0,
sum(w_k*(k-f)^2) = 0,
sum(w_k*(k-f)^3) = f*(1-f)*(1-2*f),
sum(w_k*(k-f)^4) = -9*f^2*(1-f)^2.
```

Thus exact constant, linear and quadratic reproduction does not make the
resampling kernel Gaussian, nonnegative or symmetric. Its third moment is
phase-dependent; its fourth moment can be negative because this is a signed
linear functional, not a probability distribution.

For `0<=f<=1`, the two outer weights are nonpositive and the two inner weights
nonnegative. This follows over the whole phase interval from

```text
w[-1] = -f*(1-f)^2/2,
w[2]  = -f^2*(1-f)/2,
w[0]  = (1-f)*((1-f)^2+3*f*(1-f)+f^2/2),
w[1]  = f*((1-f)^2/2+3*f*(1-f)+f^2).
```

Every factor in the inner-weight sums is nonnegative. The absolute row sum is

```text
sum(abs(w_k)) = 1+f*(1-f) <= 5/4,
sum(abs(w_k))-1 = f*(1-f) >= 0,
5/4-sum(abs(w_k)) = (f-1/2)^2.
```

The tensor-product two-dimensional row has absolute sum at most `25/16`.
Combining repeated border indices cannot increase that bound. Composing a
normalized nonnegative discrete kernel also cannot increase this sup-norm error
gain. Neither result makes signed resampling a nonnegative pixel aperture.
Values outside the physical plateau range must not be clamped to conceal it.

The [independent exact controls](../studies/verification/finite-acquisition-controls-v1.py)
use only standard-library `Fraction` arithmetic. They retain the quarter-phase
controls and every phase of the known maps: `1/2` for output scale `1`, and
`0,1/5,2/5,3/5,4/5` for scale `5/4`. Their union gives eight exact phase rows,
their tensor products, complete rational polynomial identities proving the
all-phase bound, and linear/quadratic reproduction checks. A separate half-plane
control uses exact cell coverage and a rational binomial blur to compare staged
and composed evaluation, including an
unblurred Keys undershoot and complementary overshoot. That binomial kernel is an
algebra toy, not the study's Gaussian kernel or a camera qualification.
Importing the module does not execute these controls.

## Test moment closure rather than assuming it

The nominal Gaussian comparator uses

```text
Sigma_nominal = q^2*Sigma_optical_nominal + 0.7^2*I.
```

The moment-matched comparator is a declared second-moment Gaussian hypothesis,
built from the actual normalized discrete kernel covariances and the unit
source-cell contribution:

```text
Sigma_moment = q^2*(Cov(W)+I/12) + Cov(G).
```

Here `I/12` is the unit cell's second moment. This does not assert that a
continuous box-Gaussian convolution reproduces the sampled acquisition chain.
For this known affine interior map, Keys contributes zero formal second central
moment because it reproduces quadratics. These are not optical-PSF estimates.
Higher moments, signed weights, phase dependence, discrete sampling and
quantization remain. A common covariance can match second moments without
matching finite-boundary intensities. The two comparators therefore use the
same supplied true geometry and levels, with no covariance fit or best-lane
selection.

## Separate numerical qualification from adequacy

The frozen controls independently check source pixel areas, Gaussian rectangle
means, production Keys coefficients, constant fields, post-smoothing kernel
composition, polygon tessellation and stage/source preservation. Failing one of
these controls withholds the corresponding model comparison; it is not evidence
that a Gaussian physical model failed.

For arc sweep `theta` approximated by `N` equal-angle chords, the missing area
obeys

```text
area_loss <= R^2*theta^3/(12*N^2).
```

It follows from `delta-sin(delta)<=delta^3/6`. Positive discrete blur and the
signed Keys row bound propagate this small source-area difference into a
level allowance. The plan retains that bound instead of confusing inscribed
polygon geometry with an exact circular source.

For the ideal linear stages, a source decoding/rounding perturbation `delta`
satisfies `||G R delta||inf <= (25/16)*||delta||inf`. The actual float32 path
adds the plan's explicit engineering arithmetic allowance. The saved difference
between decoded and unquantized source arrays supplies `delta`; it is not an
assumed independent random noise distribution or a guaranteed real-camera bound.

At each query the continuous Gaussian API supplies a probability and estimated
numerical error. For each stage/covariance cell, let `D` be the maximum absolute
intensity discrepancy over the 441 queries. The amended plan declares

```text
E = max_API_intensity_error + tessellation_level_bound
    + 64*eps32*(25/16)*max(1, optical_source_peak, decoded_source_peak).
```

The peaks are maximum absolute source values. The fixed one-level comparison
reports compatible when `D+E<=1`, incompatible when `D-E>1`, and inconclusive
otherwise. These engineering allowances are not rigorous enclosures.
Quantization remains an intentional stage difference and is not added as random
uncertainty. This criterion is distinct from protocol success. All 32 records,
both Gaussian choices and both stage lanes remain, including numerical unknowns
and incompatible model outcomes.

A compatible comparison concerns these supplied synthetic stages and the
declared one-level criterion. It does not identify a real camera's PSF,
response, illumination or pixel response.

The subsequent [source-cell acquisition mean](finite-acquisition-mean.md) now
preserves those source-cell, finite-kernel, resampling, smoothing and encoding
semantics. Its [qualification](validation/finite-acquisition-mean.md) supplies
independent synthetic numerical and work checks; it does not fit geometry.
The [subsequent area-sensitivity qualification](validation/finite-cell-sensitivity.md)
checks five columns and separate signed linear propagation. An inverse still
needs an objective distinguishing its unrounded model from rounded stages,
an explicit policy for undefined cell derivatives, and prospective
geometry-recovery checks, observation-derived
bounds, reserved independent dimensions and one accepted boundary preserved
through preview and exports. The existing upload, measurement and review flow
remains unchanged; this study adds no new interface controls or physical
accuracy claim.
