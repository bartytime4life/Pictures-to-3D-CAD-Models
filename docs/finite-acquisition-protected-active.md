# Exact active-face checks for protected source-bin proposals

The first selected software run at `1dade8a` ends **exit 1: 820 passed,
one failed and 33 subtests passed**. The sole failure is a test expectation
that counts 15 halfspaces where its fixture supplies 16. The
[first outcome, exact source bindings and pending correction](validation/finite-acquisition-protected-active.md)
retain that failure. No full active-method recovery study has run, and no
control-only correction has yet been admitted or executed.

This additive local implementation follows the
[protected-source-bin design](finite-acquisition-protected.md). That original
source at `79522b5` remains unchanged, including its eight failed first controls.
The new implementation passes all 53 original controls when they are rebound
to the new subject; that does not change the original source's result.
Candidate runtime, tests and runner are outside this main-based publication,
automatic tracing and the workbench UI.

The local problem has seven original domain-normalized coordinates: five
geometry parameters and two explicit brightness levels. Numerical dual
iterations suggest a face; separate rational arithmetic checks the proposed
certificate. All 96 governing inputs were committed and hashed before the first
software execution. The
[frozen admission](validation/evidence/acquisition-protected-active-20261113/admission.json)
retains the original 24 recovery cases, targets, observed-only preparation and
global caps. Its prospective wording is preserved verbatim, separately from
this current guide.

## The exact local problem

Let `F(x)` denote the exact rational value of a supplied finite binary64 number.
The supplied local model is `z0 + G d`, anchored at the actual incumbent source
optical image. Convert each represented input separately, before subtraction:

```text
upper source side:   F(G_i) d <= F(U_i) - F(z0_i),
lower source side:  -F(G_i) d <= F(z0_i) - F(L_i).
```

Omit genuinely infinite source sides. Add both original displacement-box sides
for every coordinate, including fixed coordinates. The resulting rational
halfspaces are `A d <= b`; the objective is `1/2 ||d||^2`.

`F(U-z0)` is generally a different bound from `F(U)-F(z0)`. Floating row
normalization also changes the represented coefficients. Neither operation may
define the exact problem used by the certificate. Exact arithmetic here means
exactness for these supplied dyadic inputs. It does not remove error in the
source-optical surrogate, cell sensitivity, encoder witnesses or camera model.

## Candidate face and sufficient certificate

For a proposed independent set S of at most seven rows, solve

```text
M = A_S A_S.T,
y = M^(-1) b_S,
d = A_S.T y,
lambda_S = -y.
```

This notation means a rational linear solve, not an explicit floating inverse.
A dependent face has singular M and supplies no certificate through this
formula. Opposite rows, redundant rows and fixed-coordinate equalities must
not be mistaken for independent rows. An empty face proposes `d=0`.

Extend the face multipliers by zero on all other rows and independently check
every condition using the original rational halfspaces:

```text
A d <= b,                 lambda >= 0,
lambda_i (A_i d-b_i) = 0, d + A.T lambda = 0.
```

Feasibility on the selected face alone is insufficient. A feasible point with
negative multipliers or incorrect stationarity is also not an optimality
certificate. For any feasible x, these conditions give the direct proof

```text
1/2 ||x||^2 - 1/2 ||d||^2
  = lambda.T (b-Ax) + 1/2 ||x-d||^2
  >= 1/2 ||x-d||^2.
```

Thus a verified certificate proves the unique optimum of the supplied local
QP. This sufficiency needs no strictly feasible point; it also applies when
fixed coordinates or opposite halfspaces leave an empty interior. It is not
an infeasibility certificate, a nonlinear code-preservation proof, or a
geometry-identifiability statement.

At a local polyhedral optimum, the negative displacement belongs to the cone
of active row normals. A dependent positive support can be reduced: move its
nonnegative coefficients along a dependence until at least one becomes zero,
without changing their weighted normal. Repeating leaves at most seven
independent normals. This motivates small candidate faces; it does not make a
bounded search over numerically suggested faces complete.

## Rational optimum and a represented trial are different

A rational optimum can be known even when conversion to binary64 loses
feasibility. For example, `3 d=1` has the exact optimum `d=1/3`; no binary64
number satisfies that equality exactly. A certificate for the rational point
must remain separate from the feasibility status of a rounded displacement.

Keep separate statuses for exact optimality of the rational point, exact
raw-halfspace membership of a proposed binary64 displacement interpreted as
dyadic values, and the existing computed raw-band check after reconstructing
physical parameters. Physical reconstruction and clipping can change the
normalized displacement again. For an active-polished proposal, the represented
displacement then requires a separately charged exact raw-halfspace check as
well as the existing computed gate. Hildreth fast-path proposals retain their
engineering-only qualification. A rounded dot product that falls in a band
does not by itself prove exact rational membership. No tolerance expansion may
be renamed exact feasibility.

Even an exactly feasible represented local trial need not preserve the actual
nonlinear source codes. The complete literal PNG evaluation still determines
acceptance by strict training-cost decrease. All seven coordinates remain
unknown; no brightness reprofiling, truth-derived bound or reserved residual
may select the face or trial.

## Bounded search and preserved unknowns

The 256-sweep Hildreth path, with explicit Python-float arithmetic guards,
supplies a numerical hint. Only a full iteration-limit outcome admits the new
exact active-set stage. Positive independent support may suggest a face; an
exact dual-start search can instead
enter a violated row and exchange or drop rows through dual ratio pivots.
Numerical support selection is only a proposal mechanism, never a certificate.

The implementation limits are 64 face/pivot attempts, rank seven and a 32,768-bit
pre-operation growth cap. Setup and each complete raw-halfspace verification
reserve 512 declared stage-work units per row; each face/pivot reserves 65,536.
Physical-roundtrip membership separately reserves 512 per raw row for setup
and another 512 per row for verification.
These are engineering accounting units, not processor instructions or time
bounds. A capped search may miss a valid certificate, revisit dependent faces
or exhaust its work. Partial attempts and explicit cap reasons remain retained.

Failure to find a certificate means unknown. It does not establish infeasibility,
absence of a better literal solution, or stationary geometry. The rational
certificate and any represented trial need distinct retained statuses. A
Hildreth fast-path result remains an engineering result unless separately
checked; the new stage does not retroactively certify that path. Neither status
may erase the original Hildreth failure or silently widen a source-code band.

The first run passes 26 independent mathematical controls covering known
KKT solutions, bound subtraction before rounding, dependent/opposite faces,
fixed coordinates, incorrect certificates, bounded unknowns and the
rational-to-binary64 gap. Its 22 new protocol controls and all 53 rebound
original controls also pass. The complete selected command still fails its one
new controller assertion. Assertions after that failure were not executed.

Before another control run, admit and freeze the proposed expectation-only
correction separately, retaining every original input and first outcome. Only
after its software gate passes may the unchanged 24-case recovery protocol run.
Neither gate has occurred yet. There is no new matched-case score, global
recovery guarantee, camera/noise qualification or GUI/HTTP mode.

## Primary background

[Boyd and Vandenberghe, section 5.5.3](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf)
describe KKT sufficiency for convex optimization. Here the displayed proof is
specialized to the identity-Hessian local QP; strict feasibility is not required
for sufficiency of an already verified certificate.

The official [CGAL solution and certificate reference](https://doc.cgal.org/latest/QP_solver/classCGAL_1_1Quadratic__program__solution.html)
distinguishes a proposed solution from checks of feasibility and optimality.
We do not adopt CGAL, its solver, or its implementation guarantees. Our bounded
face proposal and rational verification require their own frozen controls.

[Weber, Sager and Gleixner, section 4](https://arxiv.org/html/1803.07178v2)
use numerical basis information to form and verify a rational linear solve.
Their scaled-refinement convergence assumes a specified QP-oracle accuracy.
We neither assume that accuracy nor implement their refinement algorithm;
those convergence guarantees do not transfer to this bounded proposal.
