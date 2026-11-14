# Live restoration: current method and limits

The separate research controller is implemented and tested at `e677039`.
Its first fresh full study still fails at **11/12 matched passes**: middle
PNG exactly reproduces the supplied image but misses the chord-fraction
accuracy target. Read the [complete first result and evidence](validation/finite-acquisition-restoration-result.md)
for the source freeze, failed controls, corrected selection and terminal exits.

A [later actual diagnostic](validation/finite-acquisition-codecell-result.md)
now records alternative geometries with the same images, while leaving this
full recovery result and its middle-case miss unchanged. The saved-ten-tuple
check described below is the earlier restoration record, not the later probe.

This main-based checkout publishes documentation and saved evidence only.
`fit_acquisition_segment_restoration(...)`, its scientific tests and its
runner are absent here. It adds no HTTP mode, tracing option or workbench
control. Use the normal [capture and measurement workflow](capture-guide.md)
for parts; physical dimensions still require measurements.

## From a local certificate to an actual image test

The controller retains the coupled initial phase once, the protected event
order and the original final coordinate polish. Only the first eligible exact
certificate in a complete positive-cost PNG fit can trigger one optional
restoration episode. The event comes from the live fit; no archived point,
case name, source index, reference geometry or reserved dimension selects it.

Let `p0` be the accepted seven-coordinate tuple: five geometry parameters
and two brightness levels. Keep its source optics, local matrix `G`, spans,
domain, exact certificate and source bands bound to that live context.
Zero-span coordinates remain fixed. The episode proceeds as follows:

1. Verify the exact local certificate. Construct one rational inward
   displacement using every original halfspace and physical-domain row.
   Convert it to one nearest binary64 physical tuple, `p1`.
2. Require all five original representation, domain, source and arithmetic
   gates. Evaluate the qualified tuple through the same live acquisition
   engine and original training samples. Accept only a resolved strict cost
   decrease relative to `p0`.
3. If the actual `p1` evaluation is resolved but rejected, retain its observed
   source optics `z1`. Reanchor the old `G` through that observation and
   construct one minimum-norm correction for the selected equalities.
4. Take one nearest corrected tuple, `p2`; repeat all gates and the actual
   engine evaluation. Compare with accepted `p0`, not rejected `p1`.
5. Resume the ordinary event controller and original final polish. Zero cost
   does not waive completed-search linkage, work limits or source checks.

There is no 128-corner search, clipping, basis exchange, brightness refit or
fallback point inside this episode. A failed local construction is an unknown
for that event, not proof of global infeasibility. Source-code changes are
diagnostics; actual cost determines acceptance.

The [historical authoring explanation](finite-acquisition-restoration.md)
and [verbatim governing guide](validation/evidence/acquisition-restoration-20261114/v1-prospective-method.txt)
retain the pre-execution design. The governing guide and all other source
inputs remain unchanged after first execution.

## Exact local algebra has a limited meaning

The inward construction retains the tight-row basis, Gram witness, strict
inward signs, rational ray interval and all row slacks. The correction uses
the first independent original tight normals in original order. With their
matrix `B`, it solves one saved equality system and represents the correction
as `u = B^T lambda`. The equations and row-space identity establish minimum
Euclidean norm in normalized coordinates **for those equalities**. Every
dependent, inactive and physical row still participates in final checks.

This is neither full inequality-QP optimality for the correction nor a
nonlinear convergence or identifiability result. Tight-basis rank is not
observation rank. The fixed source guard `2^-12` and binary64 representation
allowance do not bound stale derivatives, mixed geometry/brightness errors
or nonlinear model remainder. Exact and computed normalization are checked
separately; neither is substituted for the other.

The numerical contract assumes radix-2, 53-bit binary64 arithmetic, nearest
rounding and gradual underflow. The `math.fsum` allowance is an engineering
proposal allowance, not a global enclosure theorem for `math.fsum`; final
five-gate verification remains authoritative.

In the retained actual corrected trial, **169/169 raw source bands pass**,
including the selected central-half slice. Only **168/169 storage-eroded
bands pass**: source 109 has lower slack `0.00022125244140625`, below
`2^-12 = 0.000244140625`. Its encoded code remains unchanged. This miss is
preserved; the bin and guard were not widened after execution.

## Shared work and stopping

Ordinary study ceilings are 2,048 evaluations, 1,000,000 cell units and
100,000,000 stage units per fit; adverse cases retain their lower original
limits. Initial search, events, both constructions, actual trials and final
polish share one live ledger. These study ceilings differ from API validation
maxima for caller-supplied budgets.

For `S` finite source-band sides, `R=S+14` and `A=R+14`, each invoked
construction prepays `T=65536+512*(R+9*A)` stage units before rational work,
with `A<=4096`. Exact arithmetic has seven coordinates and a 32,768-bit
pre-operation bound. Each invoked tariff is charged even on failure.

For `N` source cells, `M` output pixels and kernel entry counts `Ko,Kp`, one
literal forward costs `W=N*(1+Ko+4)+M*(16+Kp)` stage units. Worst-case
episode preflight `[2,2*N,2*T+2*W]` checks affordability only. It is not an
extra debit or escrow. Each actual forward uses the ordinary engine's
reservation; the accepted anchor is not replayed separately.

Trial-stage capture is bounded to 1,048,576 numeric entries, requested as
`2*(6*N+2*M)` for at most two trials. These accounting units and payload
limits are not elapsed-time, process-memory or bit-complexity bounds.
Source/protocol failure or opaque work withholds qualification.

The actual middle-PNG episode costs **2 evaluations / 338 cell units /
3,875,054 stage units**. The complete fresh fit costs **992 / 135,369 /
25,569,832**. Both are distinct from the earlier standalone probe's ledger.
Its zero-cost best retains the original completed-search link,
`poll_resolution` stop and tied candidates, with no exhaustion.

## Image agreement and geometry ambiguity

The retained best has zero residual at all 135 training and 34 conditional
reserved samples; its full 169-pixel float32 output equals the saved reference
bytes. Reserved checks remain conditional because initialization already used
those intensities. Fraction error remains **0.00320694906346225**, above the
original **0.002** target. Other middle-PNG targets pass.

The squared-residual objective is nonnegative, so a point with cost zero
already minimizes its objective value. This does not certify the global
inverse search or select true or unique geometry. Further strict cost
reduction cannot improve a zero objective.

A [saved-data check](validation/evidence/acquisition-restoration-20261114/identification-v1.json)
finds ten distinct saved parameter tuples with the same complete source-code
pattern. Their observed fraction range is
`[0.16679305093653773, 0.1668006421840963]`. These are sampled witnesses,
not an outer feasible-set bound, confidence interval or worst-case error
enclosure. They do not prove the 0.002 target unattainable. Direct full-field
equality is retained for the accepted trial; equal downstream outputs for
the other code-identical tuples are conditional on the fixed deterministic
downstream operator.

Further research should characterize data-consistent geometry or add genuinely
independent measured features under declared error bounds. An interval method
would require a valid inclusion model for the rounded acquisition chain;
that model is not implemented or qualified here. No new parameter search,
measurement result or uncertainty bound is claimed by this documentation.
Real-camera calibration, main integration, native slicing, CAD fit, strength
and physical acceptance remain separate work.
