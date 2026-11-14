# Diagnostic for geometries with the same image

The separate research diagnostic is committed and frozen at `44ad56c`, with
144 governing inputs. Its corrected selected controls pass **1,417 tests and
33 subtests**, with three malformed predecessor nodes deselected and equivalent
replacements selected. Its first actual probe completes successfully and finds
**168 distinct alternative parameter tuples** across four eligible PNG fits.
Every alternative reproduces its fresh baseline's complete source codes and
final output bytes. The [complete result](validation/finite-acquisition-codecell-result.md)
retains all 24 original case identities, first failures and interpretation limits.

The original recovery study remains **11/12 matched passes, exit 1**. This
diagnostic neither selects a new recovered best nor changes its targets.
The runtime, tests and runner remain outside this main-based documentation
checkout; there is no workbench control, HTTP mode or new main command.
The [earlier draft review](validation/documentation-codecell-draft.md) and
[exact prospective documentation](validation/evidence/acquisition-codecell-result-20261114/prospective-documentation-guide.txt)
retain their dated, unrun status.

## Inputs and eligibility

The diagnostic reads observed training inputs, the saved best and its used work.
A safe, completed PNG fit must have zero cost and zero raw and weighted training
residuals, matching observed targets, a valid domain, and a selected best linked
to a completed bounded search. Case identity, reference geometry and reserved
evaluation dimensions do not select proposals. Ineligible and absent fits stay
in the population report.

A fresh charged baseline first reproduces the saved seven-coordinate tuple,
cost, predictions, residuals and input hash. Historical complete source codes
are compared only when retained; missing historical codes are explicitly
`not_retained`. Fresh complete baseline codes define the subsequent cell.

## Fixed affine proposals, actual image checks

The seven coordinates are center x, center y, radius, chord fraction, normal
angle in radians and two intensity levels. With anchor `p0`, declared spans
`s` and normalized displacement `u`, the proposal is

```text
p = p0 + diag(s) u
z(u) ≈ z0 + G u
```

One actual baseline `z0` and one fresh unrounded source-optical sensitivity
matrix `G`, already scaled by spans, stay fixed across seven axes. `G` is not
a derivative of the stored float32 field or literal quantized map. For each
free axis `j`, fix `d[j]=1` and compensate with the other free columns using
numerical least squares at `rcond=128*epsilon*max(matrix_shape)`. Fixed
coordinates remain zero. Numerical rank is a proposal diagnostic, not an
exact rank or physical identifiability certificate.

Rational arithmetic intersects `u=t*d` against every stored affine source
encoder band and the physical box. One-sided saturated bands keep their
one-sided bounds. For the resulting endpoints `a,b`, the seven slots are
`a/4,a/2,3*a/4,b/4,b/2,3*b/4,(a+b)/2`. Each gets one nearest physical binary64
tuple and the original exact/computed normalization, domain, raw-band and
arithmetic-floor gates. There is no clipping, adaptive reranking or fallback.
The affine interval is not a nonlinear inclusion bound.

Only actual calls through the same acquisition engine can qualify a witness:
complete source codes and final output bytes must match the baseline, training
predictions must match, and cost and raw/weighted residuals must be zero.
All seven stages and raw binary64 coverage are retained. Distinct represented
five-coordinate geometry tuples count separately; angle aliases can still
describe the same physical shape.

## Interfaces, work and qualification

The research Python interfaces are `profile_direction(G, axis, fixed, *, reserve)`,
`ray_points(G, z0, lower, upper, anchor, spans, actual_lower, actual_upper,
direction, *, reserve)` and `probe_codecell(inputs, saved_best, used, limits,
*, expected_codes)`. Keyword arguments after `*` are optional. Invalid input
raises `ValueError`; denied reservations and numerical obstructions remain
explicit results. See the [frozen governing method](validation/evidence/acquisition-codecell-result-20261114/v1-prospective-method.txt)
for the exact contract and [additive control repair](validation/evidence/acquisition-codecell-result-20261114/v2-control-repair.txt).

At most 49 proposals plus one baseline use the original remaining budget after
the saved fit. Baseline, sensitivity, encoder, direction, exact-ray and literal
work all share the original caps: 2,048 evaluations, 1,000,000 cell units and
100,000,000 stage units. Per direction, reserve `65536+128*N*49`; per ray,
reserve `65536+512*(2*N+14)*7` before calculation, with no refund on expected
unknowns. Exact rational intermediates have a 32,768-bit bound. The helper
accepts at most 4,096 source rows. Aggregate capture entries obey
`50*(6*N+2*M)<=1048576`; complete codes have a separate entry cap. These
units are not elapsed time, measured memory or bit-complexity guarantees.

The runner checks committed source and saved bindings before subject imports
and again afterward. Each raw case remains `interpretation_withheld=true`.
Only the complete population report can qualify it after source, auxiliary,
artifact and accounting gates. Protocol completion and finding an actual
alternative are distinct outcomes; diagnostic exit 0 does not mean recovery
passed. The original best, ties and full-study score remain unchanged.

## What the result establishes

Sampled compatible extrema give a lower bound on possible extent, not an outer
bound, confidence interval, complete feasible interval or recovered geometry.
The space between extrema need not be feasible. The same-source-code subset is
only part of all states compatible with the observed output.

For minor PNG, two actual equal-output witnesses differ in fraction by about
0.007982898. By the triangle inequality, any common image-only fraction estimate
must err by at least half that separation, about **0.003991449**, for one of
the two alternatives. This conditional statement assumes the declared numerical
operator/domain and permits both unknown brightness levels. It does not prove
the original 12-record benchmark impossible, resolve the middle case, or bound
real-camera error or physical fit. [Exact values and evidence](validation/finite-acquisition-codecell-result.md).

Follow-up work needs observed-data-only decision rules, qualified nonlinear
bounds or genuinely independent measured features under declared error bounds.
The [engineering model](engineering-model.md) keeps image evidence and physical
measurements distinct. No truth-selected endpoint or reserved dimension is fed
back as a new measurement.
