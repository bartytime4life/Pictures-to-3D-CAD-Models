# An inward margin before physical floating-point rounding

The saved-data construction at `66df525` finds a changed rational point whose
**128 adjacent physical binary64 candidates all pass the five unchanged local
feasibility gates**. Its 103 selected software controls pass. An independent
saved-data audit passes 8,030 checks, with two earlier auditor schema failures
retained separately. The [result and evidence record](validation/finite-acquisition-inward-margin.md)
gives the source and artifact bindings.

This resolves the represented-feasibility obstruction in the preceding
[physical-rounding diagnostic](finite-acquisition-physical-rounding.md).
It makes no forward-model or literal PNG call, runs no new QP optimization and
does not integrate a fitter. The original full recovery protocol remains
**11/12 matched passes, exit 1**. No actual-cost improvement, nonlinear
source-code preservation, geometry recovery or physical accuracy is established.
The implementation remains separately frozen local research, outside this
main-based runtime, HTTP API and UI.

## Keep the original certificate and the new point separate

Let `F(x)` denote the exact rational value of a stored binary64 input. The
retained local problem minimizes `1/2 ||d||²` subject to `A d <= b`. Its
seven coordinates are normalized changes in five geometry parameters and two
brightness levels. The saved source predictions are locally modeled by
`z0 + G d`; they are not new evaluations of the nonlinear acquisition chain.

The diagnostic reconstructs all 352 original source and normalized-box
halfspaces, converting each input before subtraction. It independently checks
the saved point `d*` and dual multipliers for primal feasibility, dual
nonnegativity, complementarity and stationarity. That KKT certificate applies
to the original local QP only.

For construction, add 14 physical-bound rows. With incumbent `p0`, stored
domain span `s`, and original physical limits `L,U`, these are

```text
 F(s_j) d_j <= F(U_j) - F(p0_j),
-F(s_j) d_j <= F(p0_j) - F(L_j).
```

The old point must also satisfy these added rows exactly. Thus the construction
checks 366 rows; the original certificate is not silently extended to a new
problem. A fixed span requires `d*_j = h_j = 0`. After removing fixed
coordinates, a structural zero row has zero margin and remains an exact
feasibility check. It must not be tightened into an impossible strict inequality.

## Full-ULP proposal budgets

All quantities below use exact rational arithmetic on the represented inputs.
For nonnegative `x`, let `ceil64(x)` be its upward binary64 ceiling and define
`u(x) = F(ulp(ceil64(x)))`. Overflow or unsupported arithmetic produces an
unknown, not a passed bound. The recorded assumptions are binary64 nearest
rounding and gradual underflow.

For a positive stored span `s_j`, compute

```text
up_j  = u(max(abs(F(L_j)), abs(F(U_j)), abs(F(p0_j)))),
D_j   = max(abs(F(L_j)-F(p0_j)), abs(F(U_j)-F(p0_j))),
us_j  = u(D_j),
ud_j  = u((D_j + us_j) / F(s_j)),
rho_j = up_j/F(s_j) + us_j/F(s_j) + ud_j,
M_j   = (D_j + us_j)/F(s_j) + ud_j.
```

The physical full-ULP term allows for either adjacent physical rounding
choice while the target and candidate remain within the original bounds.
The other terms budget represented subtraction and division. Fixed
coordinates use zero budgets. Original normalized-box rows receive margin
`rho_j`; added physical-bound rows receive `up_j`.

For source row `i`, start with `sum_j abs(F(G_ij))*rho_j`. For each nonzero
product bound `w_ij = abs(F(G_ij))*M_j`, add `u(w_ij)`; an exact zero product
has zero allowance. Finally add

```text
2 * u(abs(F(z0_i)) + sum_j(w_ij + product_allowance_ij)).
```

This last reduction allowance is an **engineering proposal margin**, not a
global enclosure theorem for `math.fsum`. It does not certify every stage of
the acquisition arithmetic. The separately checked candidate gates below
remain decisive. These margins strengthen the original inequalities; no
source bin or original parameter bound is widened.

## One direction, one scalar interval

Collect every exactly tight nonstructural row at `d*`. In original row order,
choose an exact independent basis `B`, of rank at most seven, and solve once:

```text
(B B.T) y = 1,
h = -B.T y.
```

Reinsert fixed-coordinate zeros and require `A_i h < 0` for **every** tight
nonstructural row, including dependent rows outside the basis. A failed sign
means this chosen direction is unknown; it is not proof that no other inward
direction exists. The saved case has five tight rows, all independent. The
audit verifies their exact Gram matrix, nonsingularity, saved solution and
direction identities without solving another direction.

For each row write `q_i = b_i - A_i d*`, `v_i = A_i h`, and let `m_i` be its
proposal margin. The condition at `d_new = d* + t h` is

```text
q_i - t v_i >= m_i.
```

A negative `v_i` gives a lower bound `(m_i-q_i)/(-v_i)` on `t`; a positive
`v_i` gives an upper bound `(q_i-m_i)/v_i`. A zero slope requires
`q_i >= m_i`. Choose exactly the maximum of zero and all lower bounds, only
if it is no greater than every upper bound. Recheck all 366 strengthened
inequalities exactly at the saved new point. There is no alternate ray,
multiplier schedule or retry.

In the completed case, `t` is approximately `4.663575870208473e-12`; the maximum normalized
coordinate movement from `d*` is `7.871766933207491e-14`. These are local
construction quantities, not physical error bars. The new point does not
inherit minimum-norm optimality from `d*`.

The implementation caps input source rows and augmented rows at 4,096,
basis rank at seven, and rational integer sizes at 32,768 bits, with
pre-operation guards. A cap, singular basis, failed tight-row sign, empty
chosen interval or unchanged point is an explicit construction unknown.
None is a general infeasibility certificate.

## Check the physical candidates directly

For the one changed rational point, form each exact physical target
`F(p0_j) + F(s_j)*d_new_j`. Retain the nearest binary64 value and its adjacent
neighbor across the target, then check all 128 corners in the frozen order.
The preceding negative census of the old point is retained unchanged.
The divisions below apply to positive spans. For a fixed span retain `p0` and
set both displacements to zero without division. The saved case has seven
positive spans.

| Gate | Separate requirement |
| --- | --- |
| Physical bounds | Every represented physical parameter stays within its original bounds |
| Exact physical displacement | `(F(p)-F(p0))/F(s)` satisfies all 352 original rational halfspaces |
| Exact computed displacement | The exact dyadic value of computed binary64 `(p-p0)/s` independently satisfies those halfspaces |
| Computed bands and box | Finite binary64 source products, `math.fsum` predictions and computed displacement satisfy the unchanged bands and box |
| Selected arithmetic floor | `128*eps*max(1,abs(z0),math.fsum(abs(G*d_comp)))` is strictly less than half the unchanged selected target-band width |

All 128 saved corners pass all five gates, with zero arithmetic unknowns.
The independent audit reconstructs the original arrays, physical bounds and
anchor, verifies all strengthened rows, and checks the retained brackets,
candidate bits, displacements, exact residuals, computed sums and floor.
The smallest raw halfspace slack in the exact-physical-displacement gate is
`4.592103535128858e-12`; its meaning follows that row's scaling, not a physical
geometry-error unit.

The selected software command passes 54 new controls and 49 prior controls.
The final saved-data audit passes 8,030 checks. Its two earlier exit-1
receipts remain preserved: one compared the old `point` key with the renamed
`original_point` key; the other expected a scalar binding flag where the
report retains per-artifact flags. Those were auditor schema errors, not
changes to the construction, gates or scientific evidence.

The diagnostic retains all 24 original rows, 17 fits and 16 fits without a
qualified certificate. It verifies 108 source inputs and 106 saved artifacts
before and after. It makes no old-point census call or new model call. This
establishes represented feasibility for the saved local surrogate. The later
separately frozen [paired literal test](finite-acquisition-inward-literal.md)
now supplies the actual-cost check: it exactly reproduces the incumbent but
rejects the selected corner because training cost increases. Its target code
changes as intended, and one protected code changes too. See the
[complete negative result](validation/finite-acquisition-inward-literal.md).
This later evaluation does not change the 108-input diagnostic's zero-call
scope or the original failed full recovery. Runtime integration still needs
separate admission and a complete original 24-case protocol. No automatic
trace/CAD change, camera qualification or physical-fit claim follows here.
