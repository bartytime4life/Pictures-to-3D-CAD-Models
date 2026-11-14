# Protected source-bin proposals

A separate [restoration controller draft](finite-acquisition-restoration.md)
is now authored in local research. It has not been committed, frozen or
executed. Its proposed live accounting differs from the completed standalone
probe; the earlier result does not validate that policy. There is no new
software-test result, recovery score or available main command.

The subsequent [observed-defect correction](finite-acquisition-defect-corrector.md)
uses one fixed equality-restoration step and one nearest physical tuple. Its
first actual pair reduces training cost **0.302031169350812 to 0.0** on the
135 supplied synthetic PNG training samples. Only source 62 changes code
(93 to 92), with no collateral code change. [Complete paired result](validation/finite-acquisition-defect-corrector.md).
This is a local training result; full recovery has not been rerun, and the
original failed 11/12 protocol and main runtime remain unchanged.

The first frozen software checks **fail: eight failures, 752 passes and 33
passing subtests**, exit 1. Seven known-feasible projection controls reach the
iteration limit; an overflow case escapes numerical-error handling. The full
protected recovery study **has not run**. See the [first outcome and exact
source bindings](validation/finite-acquisition-protected.md). This is a local
research design, outside main's runtime and automatic tracing.

A separately frozen [exact active-face follow-up](finite-acquisition-protected-active.md)
passes the 53 original controls when rebound to the new implementation. Its
[first selected outcome](validation/finite-acquisition-protected-active.md)
retains 820 passes, one failed test expectation and 33 passing subtests. A
separately frozen corrected selection passes 821 tests and 33 subtests; the
subsequent complete original 24-case study still fails at 11/12 matched passes.
The [new result and saved-only physical census](validation/finite-acquisition-physical-rounding.md)
preserve every first failure. The original protected-v1 full study remains
unrun; only the active-face follow-up has completed a full recovery protocol.

The separately frozen [inward-margin construction](finite-acquisition-inward-margin.md)
passes 103 selected controls and all five gates for all 128 new adjacent
corners; an independent saved-data audit passes 8,030 checks. The old 0/128
result remains unchanged. The later [paired literal check](finite-acquisition-inward-literal.md)
exactly reproduces the baseline but raises actual training cost from
0.302031169350812 to 0.40923713513984694, so its predetermined candidate is
rejected. Target source cell 62 reaches code 92; collateral cell 33 changes
106 to 105. [Complete negative result](validation/finite-acquisition-inward-literal.md).
Full recovery remains 11/12; acquisition-aware fitter integration is absent from main.

It keeps the earlier full-protocol failures:
4/12 original matched passes, 9/12 after the predictor, and 11/12 after both the
[coupled](finite-acquisition-coupled.md) and
[source-event](finite-acquisition-events.md) strategies. Those experiments do
not establish that the remaining failure is unavoidable. The historical
saved-data audit's 28 required unverified comparisons also remain unverified.

The new question is whether an adjacent source-code event can be proposed
while protecting the other incumbent source bins. A local convex projection is
used to select a seven-coordinate trial. Its feasibility and optimality concern
that linearized problem, not the nonlinear, rounded acquisition or unique
geometry. There is no promised 12/12 outcome or physical camera qualification.

The exact coupled-v1 strategy supplies the initial phase. The protected phase
replaces the unconstrained source-event crossing; it does not first execute the
failed source-events-v1 phase. That earlier 11/12 result remains an immutable
comparison. At most 12 protected cycles each offer the 12 most negative-score
events, also bounded by the caller's iteration allowance.

## One local model, all seven unknowns

Let x contain five geometry coordinates `(Cx,Cy,R,f,theta)` and two explicit
brightness levels `(a,b)`, normalized by their original domain spans. At the
literal incumbent, retain actual source optical values z0 and encoded codes q
from charged evaluations. The local source-optical model is

```text
zhat(delta) = z0 + G delta,
G = [(b-a) KJc, K(1-c), Kc] diag(original_spans).
```

K is the supplied optical correlation. Its computed K1 is preserved rather
than forced to one. G is unweighted at the source; the supplied positive output
residual weights enter the event score. Fixed coordinates have zero spans and
zero delta. Neither brightness level is reprofiled or projected away.

The anchor is the **actual stored optical image**, not an independently
recomputed ideal source mean. The cell sensitivity and optical propagation
still supply an ideal continuous mean proposal map. They are not derivatives
of the float32/PNG objective. Undefined sensitivities remain unknown.

In PNG mode, encoding occurs at the source, before decoding, signed Keys
resampling, post correlation and final queries. Staged mode bypasses that
source encode/decode pair. A final resampled observation cannot be inverted as
one source quantization bin.

## Operational bins and a declared target interior

Adjacent float32 optical-input witnesses use the actual source encoder and
retain code probes, endpoint bits and source bindings. Nearest-even ownership
belongs to the computed encoded scalar: an interior even code owns both half
endpoints, an odd code owns neither; saturation is one-sided. Ideal inverse
sRGB thresholds do not reproduce every cast, power or ordered decoding sum.
Consecutive represented crossing witnesses are not a certified global inverse
bin or the first event along a nonlinear geometry path.

For one chosen adjacent target code, use its represented bin endpoints L,U and
the central half `[L+(U-L)/4,U-(U-L)/4]` as a **proposal interval**. Other
source cells retain their full inclusive incumbent bin endpoints without
erosion. This avoids silently excluding an incumbent lying at its own endpoint.
An unselected saturated code has its genuinely missing side unbounded.

When the selected target is saturated, an explicit finite proposal window is
used: `[0,U]` for code 0 or `[L,256]` for code 255, followed by the same
central-half rule. This is a chosen slice of a one-sided bin, not a claim that
the entire saturated bin is bounded. Unsupported optical values, unavailable
endpoints or empty/unrepresentable target interiors stay unknown.

The local projection is

```text
minimize    1/2 ||delta||^2
subject to L_i <= z0_i + G_i delta <= U_i  for every source cell,
           original normalized parameter box, including fixed coordinates.
```

Here the selected row uses the target proposal interval and all others use
their incumbent code intervals. The minimum-norm metric is a declared choice
in original domain coordinates. It is not a statistical confidence or a
measurement of physical identifiability.

## Bounded cyclic dual projection

Represent finite source bounds and the seven-coordinate box as halfspaces
`a_i dot delta <= b_i`. With zero initial delta and nonnegative multipliers,
the scalar Hildreth/Dykstra update is

```text
lambda_new = max(0, lambda_i + (a_i dot delta - b_i) / ||a_i||^2),
delta_new = delta - (lambda_new-lambda_i) a_i.
```

The retained correction/multiplier is essential. Plain alternating projection
can find a feasible point without finding the closest feasible point. The
prospective limit is 256 sweeps, with 128 declared stage-work units reserved per
constraint update, alongside setup and encoder probes. These are bounded
engineering work units, not processor instruction or wall-time claims.

Small movement between sweeps does not establish convergence. Moreover,
`delta + A.T lambda` is an arithmetic invariant from zero initialization, so a
small stationarity residual alone is not an optimality test. Current primal
violations, multiplier nonnegativity, complementarity and dual-gap diagnostics
must also be retained and assessed. A dual gap computed at an infeasible point
does not establish a valid primal error bound.

Constraint scaling must not widen a source bin. A fixed unit-normalized
tolerance can exceed a small optical margin after division by the source-row
norm. Retain original-unit residuals and the original slabs, and require final
predicted optical values within the unexpanded bands. Arithmetic-resolution
failures remain unknown; no tolerance repair changes a code interval.

Finite sweep/work limits, correlated rows, stalling or growing corrections do
not prove infeasibility. An infeasibility statement requires a separately
validated analytic certificate, such as an exactly zero row with an impossible
bound or a nonnegative Farkas combination with zero combined normal and
negative combined bound. Such a certificate would concern only the supplied
local halfspaces, not all allowed nonlinear geometries or observations.

## Why protective nullspace motion matters

In the exact toy problem `delta_x>=1`, `delta_x+delta_y=0`, the unconstrained
single-row move `(1,0)` violates protection. The closest protected move is
`(1,-1)`: the correction uses the target row's nullspace. The same idea permits
all seven coordinates to cooperate instead of fixing a coordinate merely
because its selected source-row derivative is zero.

Conversely, identical local source rows cannot be assigned disjoint target and
protected intervals. That is a local linear contradiction. It does not prove
that nonlinear geometry cannot break the equality away from the incumbent.
The prospective controls include both examples, row scaling/signs, fixed
spans, zero rows, correlated constraints and finite iteration limits.

## Literal validation and research limits

The projected point has no post-QP overshoot. Reaching a local target interval
does not prove that the actual target code changed or that every other code
remained fixed. Every newly computed literal trial retains its actual encoded
uint8 source-code array, including rejected trials and polish; cache hits refer
to the retained array. Actual optical/decoded arrays are retained for incumbent
anchors with a two-entry live cache, not for every trial. Failed/missing stages
retain explicit reasons. Predicted versus actual code-pattern differences stay
recorded, and a strict actual-cost improvement may be accepted even when the
local protected pattern was not realized. The original literal coordinate
search supplies final polish and separate stopping status.

Trial-code storage is reserved before new literal work and capped at 1,048,576
code entries. This bounds that uint8 payload, not total process memory. Per-code
encoder intervals are reused only under fixed encoder/source bindings, with
charged witnesses and explicit incumbent-membership checks.

All preceding phases, source captures, source sensitivity, optical/downstream
propagation, scalar probes, QP updates, literal trials and polish share the
original global caps: 2048 evaluations, 1,000,000 cell units and 100,000,000
stage units. Truth geometry, reference code arrays and reserved
residuals may not select a bin pattern, direction, margin or bound. The original
24 cases, numerical targets and observed-only preparation remain unchanged.
Reserved checks remain conditional because full-field initialization already
used those observed intensities.

The source, tests and plan were committed and hashed before first execution.
The controls then failed; no protected recovery calculation followed. The
[unchanged prospective method](validation/evidence/acquisition-protected-20261113/prospective-method.txt)
retains its original pre-execution wording. This design remains a proposal,
not an experimentally qualified projection implementation. A successful local projection or lower training cost
would not by itself qualify all-five geometry recovery, uniqueness, global
optimality, camera/noise adequacy, GUI/HTTP integration or physical CAD/print.

## Mathematical background

[Dykstra](https://doi.org/10.1080/01621459.1983.10477029) introduced corrected
cyclic projection for restricted least squares.
[Tibshirani](https://arxiv.org/html/1705.04768v1) describes its connections with
dual coordinate descent and convergence for closed convex sets with nonempty
intersection. Those exact convex results motivate the local solver, not a
finite-budget guarantee for this rounded nonlinear inverse.
[Bauschke et al.](https://arxiv.org/html/2001.06747v1) demonstrate arbitrarily
long stalling, supporting explicit residual checks and an unknown outcome at
the fixed limit. The source-optical and protected-bin construction above is
our own proposal model; strict literal-cost acceptance remains its only
accepted-cost monotonicity invariant.
