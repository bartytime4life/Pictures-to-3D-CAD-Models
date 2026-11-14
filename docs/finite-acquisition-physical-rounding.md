# Rational local optima and physical floating-point trials

The subsequent [observed-defect correction](finite-acquisition-defect-corrector.md)
uses one fixed equality-restoration step and one nearest physical tuple. Its
first actual pair reduces training cost **0.302031169350812 to 0.0** on the
135 supplied synthetic PNG training samples. Only source 62 changes code
(93 to 92), with no collateral code change. [Complete paired result](validation/finite-acquisition-defect-corrector.md).
That standalone probe did not rerun full recovery. The later
[live restoration study](finite-acquisition-restoration-result.md) has now
completed at 11/12, exit 1, with zero image residuals and a geometry miss.
The earlier failed protocols and main runtime remain unchanged.

The completed saved-data diagnostic at `b649ea3` independently verifies one
rational local-QP optimum, but **none of 128 adjacent physical binary64
candidates passes the unchanged constraints**. All corners were checked; there
are no arithmetic unknowns. Its 49 software controls pass. This diagnostic
makes no fitter, QP-solver, forward-model or literal PNG call.

The preceding [active-face recovery method](finite-acquisition-protected-active.md)
passes its separately frozen corrected selection of 821 tests and 33 subtests,
then still fails the complete original recovery protocol at 11/12 matched
passes. The [result and evidence inventory](validation/finite-acquisition-physical-rounding.md)
retain both outcomes and all earlier failures. These implementations remain
separate local research, absent from this main-based runtime, HTTP API and UI.

## Why the rational certificate is insufficient

Write `F(x)` for the exact rational value of a supplied binary64 input. The
saved local problem minimizes `1/2 ||d||²` over the original rational
halfspaces `A d <= b`, using separate input conversion before subtraction.
Primal feasibility, nonnegative dual multipliers, complementarity and
stationarity independently verify its unique rational optimum `d*`.

For the middle-PNG source-62 event, code 93 to 92, the certificate satisfies
all 352 raw halfspaces. The five tight source sides are
`source_lower(33)`, `source_lower(61)`, `source_upper(62)`,
`source_upper(94)` and `source_lower(109)`.

Rounding a point on a tight face can move it outside a halfspace. The earlier
nearest normalized displacement fails exact membership even though its
computed band check passes. Rounding physical parameters and then computing
their normalized displacement produces a different represented vector; its
computed gate need not have that same outcome. Neither check contradicts the
rational certificate or the other representation's result.

## Census in physical coordinates

Let `p0` be the actual incumbent physical parameter vector and `s` its
represented domain spans. Form each exact physical target

```text
p*_j = F(p0_j) + F(s_j) d*_j.
```

For each coordinate retain the nearest binary64 value and its adjacent
neighbor on the other side of the target. An exactly represented target needs
one value; a fixed span retains the incumbent and requires zero normalized
displacement. Seven varying coordinates give at most `2^7 = 128` corners.
Nearest values come first, followed by the frozen mask order. This exhausts
only that adjacent box, not a larger neighborhood or the feasible polyhedron.

Every candidate `p` keeps five separate gates:

| Gate | Required condition |
| --- | --- |
| Physical bounds | Each represented parameter lies within its original bounds |
| Exact physical normalization | `d_phys = (F(p)-F(p0))/F(s)` satisfies every original rational source and displacement-box halfspace |
| Exact membership of computed displacement | Compute binary64 `d_comp = (p-p0)/s`, then check its exact dyadic value against every original halfspace |
| Existing computed gate | Finite source products and `math.fsum` predictions stay in their unchanged raw bands, and computed displacement stays within its box |
| Arithmetic floor | For the selected source, `128*eps*max(1,abs(z0),math.fsum(abs(G*d_comp)))` is strictly less than half the unchanged target interval width |

Fixed coordinates require separate zero-span handling. The actual saved
diagnostic always supplies the selected source and checks the floor. A pure
helper call without it explicitly labels that gate unchecked.

The diagnostic visits all 24 saved rows and all 17 fit files, retaining the
16 fits without a qualified certificate. It reconstructs the one qualified
event from saved arrays and checks its KKT certificate before the census.
Source and saved-artifact hashes are checked before and after reading.
Rational operations and comparisons have a 32,768-bit pre-operation cap;
capped arithmetic is an unknown, never a feasibility pass.

## What the completed census establishes

All 128 corners pass physical bounds and the arithmetic floor. None passes
exact physical membership, exact membership of the computed displacement or
the computed source-band gate. Violations are confined to the same five tight
source sides. No tolerance, target, work cap or source-code interval changed.

This excludes accepted points in that adjacent physical box under these
gates. It does not exclude other floating-point feasible points, prove the
nonlinear problem impossible or improve the full recovery result. There is
no literal PNG evaluation or accepted trial in this diagnostic. A represented
feasible nearby point, if later found, would also need its own status; it
would not inherit the rational point's minimum-norm optimality certificate.

<a id="an-inward-point-is-future-work"></a>

## From the proposal to a separately verified inward point

The proposal below describes the next step after the original negative
census. A separately admitted [inward-margin construction](finite-acquisition-inward-margin.md)
at `66df525` has now executed: 103 selected controls pass, and all five gates
pass at all 128 new adjacent corners, with zero arithmetic unknowns. An
independent saved-only audit passes 8,030 checks. The original 0/128 result
is unchanged because the new census surrounds a different rational point.
See [its result and evidence](validation/finite-acquisition-inward-margin.md).
A separately frozen [paired literal check](finite-acquisition-inward-literal.md)
has now tested the predetermined candidate: exact baseline, higher actual
training cost and rejection. [Complete negative result](validation/finite-acquisition-inward-literal.md).
A later [live restoration integration](finite-acquisition-restoration-result.md)
has completed a fresh full recovery protocol, still failed at 11/12. This
earlier physical census remains unchanged.

Let `T` contain **every** tight row. A rational direction must satisfy
`A_T h < 0`. If those normals are independently verified and their Gram
matrix is nonsingular, one possible construction is the rational linear solve

```text
(A_T A_T.T) y = 1,
h = -A_T.T y.
```

This yields `A_T h = -1` under that rank assumption. It does not establish
that a suitable step or rounding margin exists for the saved event. For each
inactive row with slack `q_i = b_i - A_i d*`, a positive step `t` must preserve
`t A_i h <= q_i` whenever `A_i h > 0`, including displacement bounds.
Fixed-coordinate equalities can prevent strict interior motion and need
affine-hull handling; indiscriminately tightening all rows is invalid.

For physical rounding errors bounded by `r_j`, triangle inequality gives the
sufficient exact-physical margin at `d_new = d* + t h`:

```text
b_i - A_i d_new >= sum_{j: s_j != 0} |A_ij| r_j / |s_j|.
```

This bound tightens the original problem. It covers exact physical
normalization only; rounded subtraction/division, computed sums and the
arithmetic-floor gate still require separate checks. Shrinking toward the
incumbent is not generally valid: the selected target bin excludes it.

The saved-only construction has its own admission, 108-input combined freeze
and independent controls. Runtime integration still requires a separate
admission, bounded work reservations and another complete original 24-case
protocol. The unchanged literal image-cost check must still decide
acceptance by strict training-cost decrease. Neither a local certificate nor
a represented feasible point establishes nonlinear code preservation,
unique geometry, camera accuracy or physical CAD/print acceptance.

The [verbatim prospective guide](validation/evidence/acquisition-physical-rounding-20261113/rounding-prospective-method.txt)
retains its pre-execution wording. Use this page and the
[completed result](validation/finite-acquisition-physical-rounding.md) for current status.
