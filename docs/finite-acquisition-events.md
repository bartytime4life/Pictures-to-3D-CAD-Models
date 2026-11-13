# Source-code event proposals for rounded acquisition

The first separately frozen source-event study at `cd85ef9` stays at **11/12
matched passes**, with all 24 cases and original targets retained. The complete
protocol exits 1. Its first software suite passes 653 tests and 21 subtests.
Middle PNG accepts no event improvement and retains the same fraction and
conditional reserved-residual misses as the coupled study. See the
[result and evidence](validation/finite-acquisition-continuations.md) and
[frozen admission](validation/evidence/acquisition-continuations-20261113/events-admission.json).

This is local research outside the documented main revision `81248a7`, HTTP routes and workbench UI.
The original 4/12, predictor 9/12 and coupled 11/12 failed protocols are retained.
The [coupled saved-only audit](finite-acquisition-saved-audit.md) does not cover
the new event-phase ledger. No physical camera/CAD qualification follows.

A later [protected-source-bin design](finite-acquisition-protected.md) attempts
to retain other incumbent bins. Its [first software checks fail eight cases](validation/finite-acquisition-protected.md);
no full recovery study has run for that strategy.

## The event belongs to a source code

In PNG mode, the declared acquisition first mixes cell coverage with two levels,
applies optical correlation and encodes each **source** cell as sRGB8. It then
decodes and forms the ordered float32 Rec.709 mixture, performs signed Keys
resampling and post correlation, and selects queries. Float32 storage rounds
remain at the original stages. Staged mode bypasses source encoding/decoding.
A final PNG-mode observation is therefore not one sRGB
code and cannot be inverted as one quantization bin.

For the computed encoded scalar t, nearest-even rounding assigns an interior
even code k both endpoints k±0.5; an odd code owns neither. Code 0 includes
t<=0.5, and code 255 includes t>254.5. These rules include the encoder's
one-sided saturation. They follow the supplied [sRGB transfer definition](https://registry.color.org/rgb-registry/srgb)
and [nearest-even rounding operation](https://numpy.org/doc/stable/reference/generated/numpy.rint.html).
They do not invert all preceding arithmetic.

The boundary helper searches the positive float32 optical-input
bit lattice using the actual encoder, retaining code probes and neighboring
represented inputs. A returned adjacent-input transition is an operational
crossing witness. An ideal inverse-sRGB value is not a substitute. Binary
search relies on the computed encoder's ordering; local neighbor checks are
not an interval certificate of every libm result or of the first event along a
nonlinear geometry ray. Source geometry, brightness and optical casts can move
several codes at once or make a predicted crossing unavailable.

Each adjacent-code search has at most 40 scalar encoder probes. Four declared
stage-work units are charged per probe; probes have their own recorded census
and do not create a source-geometry evaluation unit. This is an explicit work
convention, not a count of machine instructions. Saturated codes have no
outward adjacent-code event. Unknown boundaries and exhausted probe budgets
remain explicit.

## Score a latent source event using training residuals

At the retained incumbent, capture actual source optical values and encoded
codes from a charged literal evaluation. Reference codes, truth geometry and
reserved observations are unavailable to event selection. For a source index j
and adjacent code k±1, compute the decoded difference ΔD with the actual
float32 lookup and ordered Rec.709 products and sums.

Let B_j be that source cell's response under the fixed **unrounded** downstream
Keys/post operator, W the supplied positive row multipliers, and
r=W(y−F_literal) the current weighted training residual. Define

```text
d_j = W (ΔD B_j),
score_j = ||d_j||² − 2 r·d_j.
```

This equals the squared-residual change for the ideal fixed linear downstream
operator. The residual is already weighted; multiplying it by W again changes
the objective. Signed Keys coefficients must keep their signs. Downstream
float32 rounds mean a negative score need not lower actual PNG cost. A useful
latent code substitution also need not be realizable by any allowed geometry
and levels. Neither the score nor a code pattern is a geometry certificate.

The response payload is bounded by 1,048,576 entries, or 8 MiB of float64
values. Computation is grouped in at most six caller fields plus the charged
constant channel; response construction and operator work stay in the original
global ledger. This payload cap does not describe total process memory.

## Cross the source threshold with seven coordinates

Let p=(Cx,Cy,R,f,theta), ideal coverage c(p), optical correlation K, background
level a and material level b. Retain raw K1 rather than forcing it to one.
The ideal source-optical mean and normalized full Jacobian are

```text
z = a K(1−c) + b Kc,
G = [(b−a) KJc, K(1−c), Kc] diag(original_parameter_spans).
```

This matrix has all five geometry columns and both brightness columns. It is
unweighted at the source; W acts on selected output residuals in the score.
Fixed coordinates have zero spans. There is no brightness reprofiling or
nuisance projection. Undefined cell derivatives remain unknown. The continuous
stored-normal family used by the area derivative does not turn this matrix
into a derivative of the actual rounded encoder/objective.

For a selected event's signed optical gap g and source row h, the unconstrained
minimum Euclidean-norm normalized linear crossing is

```text
delta = g h / ||h||².
```

For nonzero h this solves h·delta=g and is orthogonal to the row's nullspace.
Its norm preference is a declared proposal choice, not identifiable geometry.
Zero or numerically unsupported h supplies no direction. Feasible clipping and
the factors 1.001, 1.1 and 1.5 offer bounded trial candidates. Clipping can
prevent the linearized crossing; nonlinearity and casts can invalidate it even
without clipping. An overshoot is not a feasibility proof or a guarantee of
strict improvement.

## Actual acceptance, stopping and retained failures

The exact preceding coupled-v1 strategy runs first. Only a safe positive-cost
PNG result enters this event phase. Each cycle offers at most the 12 most
negative-score adjacent events, for at most 12 cycles, under the caller's
declared iteration limit. A new incumbent requires strict decrease of actual
complete PNG cost at the original training queries. The original coordinate
search supplies final polish and its separate local-resolution status.

All initial phases, source snapshots, optical sensitivity propagation,
downstream response construction, scalar probes, literal trials and polish
share the unchanged global evaluation, cell and stage caps. Failures, unknown
work and unstarted events cannot be reported as stationarity. Equal-cost
alternatives stay ambiguity evidence. Local poll resolution, a tiny proposed
gap or zero training cost does not prove uniqueness, global optimality, all-five
geometry identifiability or dimensional uncertainty.

The first full protocol preserves all 24 original cases, targets, observed-only
initializers/bounds, query split and failure records. Reserved checks remain
conditional because initialization used the full observed field. No truth,
reserved or reference data ranks events, chooses a step or alters bounds. The
executed mathematical controls and failed model-recovery protocol have separate
results in the [validation record](validation/finite-acquisition-continuations.md).

## Relation to primary research

[Mukherjee and Seelamantula](https://arxiv.org/html/1810.01097v1) use
quantization-bin consistency for quadratic phase retrieval;
[Jacques, Hammond and Fadili](https://arxiv.org/abs/1206.6003) study
quantization-aware fidelity for nonuniform compressive sensing.
[Rencker et al.](https://arxiv.org/abs/1809.09639) minimize distance to known
convex measurement-feasibility sets, and [Liu and Wright](https://arxiv.org/abs/1207.0577)
explicitly constrain quantization and saturation in linear compressive sensing.
These motivate respecting the encoder, not assuming that our latent source
codes and nonlinear geometry yield a known convex inverse set.

[Arjas, Sillanpää and Hauptmann](https://arxiv.org/html/2301.10094v2) analyze
sequential model correction under stated regularity/approximation assumptions.
[Yin et al.](https://arxiv.org/abs/1903.05662) distinguish a straight-through
coarse gradient from a true gradient and analyze a particular binarized network
with Gaussian population inputs. Neither establishes convergence for this
source-event strategy. The displayed proposal derivation is ours; strict
literal-cost acceptance establishes only decreasing accepted evaluated costs.
