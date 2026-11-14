# Proposed diagnostic for geometries with the same image

**Local authoring draft; uncommitted and unrun at this documentation snapshot.**
The draft follows research source `e677039`, whose
[first full restoration study](validation/finite-acquisition-restoration-result.md)
still fails at **11/12 matched passes, exit 1**. No new recovery score,
compatible geometry, uncertainty bound or application feature is established.
The [documentation review](validation/documentation-codecell-draft.md) records
the exact draft files inspected. Their runtime and tests are absent from this
main-based documentation checkout.

## Why investigate image-equivalent geometries?

Middle PNG in the completed study matches all 169 reference output pixels,
including 135 training and 34 conditional reserved samples. Its fraction error
is nevertheless 0.00320694906346225, above the original 0.002 target.
This motivates testing whether other geometries produce the same source codes
and zero training residual. An unsuccessful local search would not establish
that no such geometry exists.

The draft proposes a bounded diagnostic after a safe, completed PNG fit with
zero cost and zero raw and weighted training residuals. Its selected best must
be linked to a completed bounded search; other cases remain recorded and
unprobed. It would keep
the original best candidate, ties, geometry targets and full-study result.
It consumes observed training inputs, the saved best and existing work ledger;
reference geometry and reserved evaluation dimensions are not proposal inputs.
All 24 original case identities would remain visible, including exceptions,
absent fits, ineligible rows and refusals. Eligibility depends on recorded
completion and data checks rather than selecting the known failing case.

## Local proposal mathematics

The seven coordinates are center x, center y, radius, chord fraction, normal
angle in radians and two intensity levels. Let `p0` be the saved physical tuple, `s` its
declared coordinate spans, and `u` normalized displacement:

```text
p = p0 + diag(s) u
z(u) ≈ z0 + G u
```

`z0` is the actual baseline source-optical field before source encoding.
`G` is the sensitivity of the corresponding unrounded source-optical model,
expressed in normalized coordinates and including coordinate spans. It is not
a derivative of the stored float32 field or the literal PNG map.
One baseline and one `G` remain fixed across all axes.
The second equation
is a local affine proposal, not an inclusion bound for the nonlinear operator.

For each nonfixed coordinate `j`, the direction fixes `d[j] = 1`, keeps fixed
coordinates zero, and solves `G[:, K] d[K] ≈ -G[:, j]` for the other free
coordinates `K`. The draft uses numerical least squares with
`rcond = 128 * binary64_epsilon * max(N, len(K))`. The
[NumPy least-squares contract](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)
describes its residual and minimum-norm solution convention. Numerical rank
here is a proposal diagnostic; it does not certify physical information rank
or an exact mathematical minimum.

Along `u = t d`, rational arithmetic would intersect the stored affine field
with every source encoder band and the declared physical box. Saturated
encoder bands retain their one-sided bounds. This exact interval belongs only
to the stored affine surrogate. The seven declared slots are one quarter,
one half and three quarters of each signed interval endpoint, plus the
interval midpoint. Each slot gets one nearest represented physical tuple,
subject to the existing domain, round-trip, band and arithmetic-floor checks.
There is no clipping, adjacent-float search or adaptive reranking.

## What would qualify an actual witness?

A fresh, charged baseline would first reproduce the saved parameters, levels,
predictions, residuals, zero cost and input hash. Historical complete codes
would be compared when retained; their absence would be recorded explicitly.
Fresh complete baseline codes define all subsequent code comparisons.

Every eligible proposed tuple would then need an actual call through the
same numerical acquisition operator. A compatible witness requires equal
complete source codes, equal complete final output bytes, equal training
predictions, zero raw and weighted training residuals, and zero cost.
The proposed record retains all seven acquisition stages and raw binary64
coverage. A surrogate pass alone cannot qualify a witness.

## Limits, accounting and failure records

The draft Python interfaces are `profile_direction(G, axis, fixed, *, reserve)`,
`ray_points(G, z0, lower, upper, anchor, spans, actual_lower, actual_upper,
direction, *, reserve)`, and `probe_codecell(inputs, saved_best, used, limits,
*, expected_codes)`. The keyword arguments shown after `*` are optional.
Invalid input raises `ValueError`; numerical obstructions and denied work
reservations remain explicit results, and protocol failures withhold
interpretation. These interfaces are not installed or exported in main.
The direction axis is a nonboolean integer in `0..6`; fixed flags are seven
actual booleans, and spans are nonnegative. A missing source-band side uses
`None`, negative infinity for a lower side, or positive infinity for an upper
side. Proposal arithmetic assumes binary64 nearest rounding and gradual
underflow; those assumptions are not a hardware qualification.

The draft allows at most 49 proposal trials plus one baseline. All baseline,
sensitivity, band, direction, rational-ray and actual-trial work uses the
original remaining budget after the saved fit; it would not reset the fit's
2,048 evaluations, 1,000,000 cell units or 100,000,000 stage-unit caps.
Direction and ray calculations reserve respectively `65536 + 128*N*49` and
`65536 + 512*(2*N+14)*7` stage units before the corresponding calculation.
Rational intermediates have a 32,768-bit cap. Those units are not elapsed time,
memory measurements or a proof of bit complexity.

The standalone helper accepts 1–4,096 source rows. The controller additionally
preflights aggregate capture entries using `50 * (6*N + 2*M) <= 1,048,576`,
where `N` and `M` are source and output cell counts. It also caps complete
code entries. Budget refusals, arithmetic unknowns, unattempted slots and
protocol failures would remain explicit. Source changes or incomplete
accounting would withhold interpretation while retaining raw records.

The planned runner checks committed source and saved-input bindings before
subject imports, verifies consumed metadata and source again afterward,
and writes only to a new confined local output directory. An individual raw
case file cannot establish qualification without the complete final report.
The admission, combined source freeze, first controls and first probe result
do not yet exist at this snapshot. There is no ready-to-run reproduction
command in this guide, and exit-status policy remains subject to review.

## How to interpret a future result

Verified compatible tuples would be sampled witnesses inside the set admitted
by this fixed numerical operator and domain. Their observed coordinate span
would be a **lower bound on possible extent**, not an upper bound, confidence
interval or enclosure of all admissible geometry. Duplicate slots need not
yield distinct tuples; the interval between sampled extrema need not be
feasible. The fixed source-code pattern is only part of the full set compatible
with the training output. No successful witness search would establish real-camera
accuracy, physical fit or a better choice of recovered geometry.

The distinction between finding examples and enclosing every data-consistent
parameter is central to
[Jaulin and Walter's bounded-error set-inversion method](https://webperso.ensta.fr/Jaulin/paper_automatica93.pdf).
Its interval guarantees require a valid inclusion method; this local affine
diagnostic does not implement one for the quantized acquisition pipeline.
Independent measured features and qualified nonlinear bounds remain possible
follow-up work. Original reserved dimensions remain evaluation evidence.

Until the new source is reviewed, committed, frozen and executed under its
admission, use the [executed restoration result](finite-acquisition-restoration-result.md)
for conclusions. The original geometry miss remains unresolved.
