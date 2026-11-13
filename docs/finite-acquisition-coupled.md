# Coupled proposals for rounded acquisition

The first separately frozen coupled study at `b9fe285` reaches **11/12 matched
passes**, retaining all 24 original cases and targets. Its complete protocol
still exits 1: middle PNG misses fraction and conditional reserved-residual
targets. The first software run passes 548 tests and nine subtests. See the
[result, full census and evidence](validation/finite-acquisition-continuations.md)
and [frozen admission](validation/evidence/acquisition-continuations-20261113/coupled-admission.json).

This candidate remains local research outside the documented main runtime
`20cc57c`, HTTP routes and workbench UI. Its unrounded mean is a proposal
surrogate, not a derivative or convergence certificate for PNG acquisition.
The preceding 4/12 original and 9/12 predictor protocols remain unchanged.
The later [source-event method](finite-acquisition-events.md) also stays at 11/12.

## Encoding occurs before output sampling

For PNG mode, the supplied acquisition model preserves this order:

```text
cell coverage -> float32 coverage -> two-level source mix -> float32
-> optical correlation -> float32 -> source sRGB8 encoding
-> float32 decoded Rec.709 mix -> Keys resampling -> float32
-> post correlation -> float32 -> selected output queries.
```

Staged mode bypasses sRGB8 encoding and decoding while retaining its float32
storage stages. The extra coupled refinement applies only to PNG.

The transfer branches follow the [ICC sRGB definition](https://registry.color.org/rgb-registry/srgb).
For the computed finite encoded scalar `t` before clipping, the final
`rint(clip(t,0,255))` uses
[nearest-even rounding](https://numpy.org/doc/stable/reference/generated/numpy.rint.html):

| Code | Computed encoded values assigned to it |
| --- | --- |
| 0 | `t <= 0.5`, including the lower saturated range |
| Interior even `k` | `[k-0.5,k+0.5]` |
| Interior odd `k` | `(k-0.5,k+0.5)` |
| 255 | `t > 254.5`, including the upper saturated range |

In this encoder, negative linear inputs are clamped before the transfer function.
These are endpoint rules for the computed encoded scalar. Ideal inverse-sRGB
thresholds do not by themselves reproduce the floating-point power, preceding
casts, or the decoder's ordered float32 products and sums.

Each final observation is a mixture of decoded source codes, with signed Keys
coefficients and further storage rounds. Applying one inverse-sRGB bin directly
to a final query constrains the wrong quantity. A fixed complete source-code
pattern gives the same literal output under the same deterministic downstream
stages; different code patterns can also agree at the selected queries.

## Seven-dimensional mean proposals

Let `p=(Cx,Cy,R,f,theta)`, `c(p)` be ideal cell coverage, and `A` the separately
declared fixed unrounded linear acquisition operator. Set `v=A c(p)` and
`a0=A1`. At current brightness levels `(a,b)`, use the smooth mean columns

```text
Jmean = [(b-a) A Jc, a0-v, v],
Js = W Jmean diag(parameter_spans),
r = W (observed - literal_prediction).
```

The five geometry and two brightness coordinates remain coupled unknowns. A
fixed brightness span contributes a zero column and must not be divided by.
The computed `A1` is retained rather than replaced by one. Positive supplied
row multipliers are a residual metric, not inferred noise calibration.

A damped augmented least-squares solve proposes `Js delta` approximately equal
to `+r`, followed by feasible clipping. This sign is for a mean Jacobian; a
residual Jacobian uses the opposite convention. Neither brightness variable is
reprofiled or projected away in the rounded proposal. The smooth two-level
variable-projection formula is not an exact elimination for PNG acquisition.

This matrix is a surrogate. It is not a derivative of the literal float32/PNG
objective, a projected-gradient stationarity test for that objective, or a
geometry-identification certificate. Undefined cell sensitivities must remain
unknown and trigger the declared literal-search fallback.

## Bounded rays and literal acceptance

The first strategy uses at most 24 coupled iterations, bounded also by the
caller's iteration limit. The augmented-SVD damping starts at `1e-3`. Each
direction offers factors `1,2,4,8,1/2,...,1/256`, clipped to the original box
and deduplicated. There is no source-code-boundary step helper in this version;
these factors do not promise to locate or cross a particular threshold.

Only a safe, positive-cost PNG incumbent enters this extra phase. Smooth,
staged, zero-cost and unsafe/no-candidate results pass through the preceding
predictor without coupled model work. Only a strict decrease in actual PNG cost
accepts a coupled candidate. A
smaller surrogate cost, a small coupled step, or an unchanged code pattern does
not establish literal convergence. Equal-cost alternatives remain ambiguity
evidence. The original literal coordinate search supplies the separately
declared final polish and stopping checks.

The initial predictor, additional sensitivity/linear evaluations, literal ray
trials and final polish share the original global evaluation, source-cell and
stage-product caps. Skipped work, failures and unavailable actual counters must
stay explicit. A phase limit is distinct from exhausting a global cap; the
caller iteration limit is not an aggregate wall-time or total-iteration bound.
Source bindings and every original scientific target remain part of the next
prospective admission. No held-out residual, truth dimension or reference code
array may select a proposal or alter its bounds.

## Consistency is not unique geometry

[Mukherjee and Seelamantula](https://arxiv.org/html/1810.01097v1) enforce
quantization-bin consistency with one-sided costs for quadratic phase retrieval.
[Jacques, Hammond and Fadili](https://arxiv.org/abs/1206.6003) distinguish
quantization-aware fidelity from a generic squared-error distortion model.
These motivate respecting the supplied encoder. Their sensing assumptions and
recovery guarantees do not establish convergence or accuracy for this nonlinear
seven-parameter, rounded acquisition chain.

[Arjas, Sillanpää and Hauptmann](https://arxiv.org/html/2301.10094v2) study
sequential correction of an approximate model under stated regularity and
approximation assumptions. [Yin et al.](https://arxiv.org/abs/1903.05662)
distinguish a straight-through coarse gradient from a true gradient; their
convergence analysis concerns a particular binarized network and Gaussian
population model. These support examining approximate proposals with the more
accurate model, but neither proof transfers to this acquisition chain. Here
strict literal-cost acceptance supplies only the monotonicity of accepted
evaluated costs, not convergence or geometric accuracy.

For a known latent code pattern and fixed geometry, an ideal pre-encoding
optical model gives linear interval constraints on the two levels. Here the
code pattern is unobserved and the intermediate casts remain, so the complete
problem is not one convex brightness-feasibility problem. A zero training cost
can retain several geometries. A finite collection of such candidates is not
an exhaustive feasible set, and current engineering arithmetic estimates do not
certify excluded geometry boxes or dimensional uncertainty.

The executed mathematical controls include nearest-even endpoints, saturation,
source/output ordering and an invented coordinate-flat sensor with an improving
coupled ray. That toy illustrates a possible mechanism; it does not establish
seven identifiable parameters. The complete source, tests and admission were
committed and hashed before first execution. All original cases, targets and
work caps remain in the [first result](validation/finite-acquisition-continuations.md).

For complete local packaging, the corrected coupled audit and the historical
precision unknowns, see [saved recovery archives and audit scope](finite-acquisition-saved-audit.md).
