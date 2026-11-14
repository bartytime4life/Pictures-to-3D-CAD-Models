# Acquisition-aware geometry recovery

This page records a separately frozen local research candidate, not an API
installed or merged into the [current main runtime](project-status.md). The candidate
source is retained locally; this documentation change does not publish its
runtime, full raw captures or candidate ledgers. See the
[result, source bindings and audit limits](validation/finite-acquisition-recovery.md).

Those experimental Python tools estimate the centre `(Cx,Cy)`, radius `R`,
chord fraction `f`, normal angle `theta` and two bounded brightness levels for
one circular segment. They are local supplied-acquisition experiments. They do
not select optics from a photograph or run through automatic tracing, an HTTP
route or the workbench interface.

The [first frozen protocol](validation/evidence/acquisition-recovery-20261113/original-plan.json)
retains **24 cases**, including all **12 matched** and **12 adverse** rows.
At source `7ec6803`, all four smooth matched cases pass every target; none of
the eight rounded matched cases does. The complete experiment exits **1**.
A separate [continuation admission](validation/evidence/acquisition-recovery-20261113/continuation-admission.json)
changes the search strategy while preserving the population, original targets,
observation-only inputs and independent reference. At frozen source `e6e2c2`, it records **9/12** matched passes: **4/4 smooth,
4/4 staged and 1/4 PNG**. It also exits **1**; minor and major PNG miss the
conditional reserved-residual target, and middle PNG misses that target and the
fraction target. The **459 focused tests** pass, separately from the failed
scientific protocol. The failed first result remains evidence for that version.
The original saved-data auditor also exits **1**, with 14 pre-cast area-order
deltas not reconstructible from rounded saved arrays; it is not an all-green audit.

The later [coupled search](finite-acquisition-coupled.md) reaches **11/12**
matched target passes; the [source-event continuation](finite-acquisition-events.md)
stays at **11/12**. Both complete 24-case protocols still exit 1. Their first
focused suites pass 548 tests/nine subtests and 653 tests/21 subtests, respectively.
The [completed results](validation/finite-acquisition-continuations.md) and
[saved-only audits](finite-acquisition-saved-audit.md) retain the remaining PNG
miss, first failures and 28 historical precision unknowns. Candidate code and
complete local ZIPs remain separate from this main runtime and workbench UI.

The [protected-source-bin design](finite-acquisition-protected.md) retains its
eight failed first controls. The [exact active-face follow-up](finite-acquisition-protected-active.md)
preserves its first test-expectation failure; a separately frozen corrected
selection passes **821 tests and 33 subtests**. Its complete original 24-case
study still fails at **11/12 matched passes**. The later saved-only
[physical-rounding diagnostic](finite-acquisition-physical-rounding.md) verifies
one rational local optimum but finds **zero accepted candidates among 128
adjacent physical corners**, with no arithmetic unknowns. See the
[complete results and source bindings](validation/finite-acquisition-physical-rounding.md).
The separately frozen [inward-margin construction](finite-acquisition-inward-margin.md)
passes 103 selected controls and all five gates for all 128 new adjacent
corners; an independent saved-data audit passes 8,030 checks. The old 0/128
result remains unchanged. The later [paired literal check](finite-acquisition-inward-literal.md)
exactly reproduces the baseline but raises actual training cost from
0.302031169350812 to 0.40923713513984694, so its predetermined candidate is
rejected. Target source cell 62 reaches code 92; collateral cell 33 changes
106 to 105. [Complete negative result](validation/finite-acquisition-inward-literal.md).
Full recovery remains 11/12; acquisition-aware fitter integration is absent from main.

The subsequent [observed-defect correction](finite-acquisition-defect-corrector.md)
uses one fixed equality-restoration step and one nearest physical tuple. Its
first actual pair reduces training cost **0.302031169350812 to 0.0** on the
135 supplied synthetic PNG training samples. Only source 62 changes code
(93 to 92), with no collateral code change. [Complete paired result](validation/finite-acquisition-defect-corrector.md).
That standalone probe did not rerun full recovery. The subsequent live study
has its own source freeze and result; the earlier failed protocols
and main runtime remain unchanged.

The separate [live restoration controller](finite-acquisition-restoration-result.md)
is now frozen and executed in local research. Its selected controls pass
1,169 tests and 33 subtests, with one malformed predecessor node deselected
and independently replaced. The fresh original 24-case study remains
**11/12 matched passes, exit 1**. Middle PNG has zero training and conditional
reserved residuals but misses the fraction target: 0.003206949 > 0.002.
It adds no main runtime, HTTP mode or workbench control.

These separate local studies add no main runtime or workbench integration.

## Model and brightness elimination

For the [source-cell area model](finite-acquisition-mean.md), let `c(p)` contain
the material fractions and let `A` be the separately declared fixed float64
[linear acquisition operator](finite-cell-sensitivity.md). Define

```text
v(p) = A c(p),        a0 = A 1,
mu(p,a,b) = a * (a0-v(p)) + b * v(p).
E(p) = W [a0-v(p), v(p)],       z = W y,
r(p) = z - E(p) beta(p),        beta = [a,b].
```

`W` contains supplied positive residual multipliers; they are not calibrated
noise variances. Raw coefficient sums and border conventions are preserved, so
`a0` is computed rather than silently replaced by one.

`backend.finite_photometry.profile_levels` minimizes the represented weighted
residual over a two-dimensional brightness box. It explicitly compares all
nine free/lower/upper face combinations using direct SVD/least-squares solves.
Fixed levels, tied alternatives, rank changes, low contrast and numerical
failures remain visible. The levels are nuisance parameters, not inferred
material properties or camera calibration.

On a unique stable active face, let `E_F` contain the free brightness columns
and let `E'_F` denote their geometry derivative. With the fixed brightness
contributions included in the mean derivative `K`, the complete residual
Jacobian has both terms

```text
Jr = -P_F K - E_F^(+T) (E'_F)^T r,
P_F = I - E_F E_F^+.
```

The second term depends on the residual. Omitting it is generally an
approximation. This follows the variable-projection framework discussed by
[O'Leary and Rust](https://www.cs.umd.edu/users/oleary/software/varpro.pdf).
Their sample linear subproblem is unconstrained; the bounded nine-face
extension and transition/refusal policies here are separate work.

## Local fitting and observed-only starts

`backend.finite_acquisition_observations.prepare_acquisition_segment` consumes
an observed output field, declared polarity and fixed acquisition settings.
It uses threshold crossings, line/circle hypotheses and a bidirectional finite
boundary score. Its output snapshots queries, observations, operational bounds,
all retained hypotheses and up to four starting geometries. Full-field
preparation uses the eventual reserved pixels too; their later residuals are
conditional checks, not independent predictions.

Output extrema are recorded as brightness hints. They do not bound source
brightness: in the first minor-segment experiment the material hint is about
79 while the source level, opened only after fitting, is 27. The runner clips
hints only to the declared `[0,255]` seed interval, without tightening the
brightness search bounds to those hints.

`backend.finite_acquisition_fit.fit_acquisition_segment` accepts explicit
samples, bounds and seeds. Smooth mode uses bounded brightness elimination,
the full fixed-face Jacobian and dimensionless damped least-squares proposals.
It evaluates actual smooth cost during backtracking and uses bounded objective
polls when derivatives are unavailable. The stopping measure is an undamped
projected-gradient mapping, separate from a clipped or tiny damped step.

Staged and PNG modes evaluate the literal float32/encoding chain and poll seven
bounded geometry/brightness coordinates. Their brightness search is not exact
variable projection. A local poll plateau does not establish recovery: two
first-run PNG rows stop locally despite missing the geometry targets.

The unit budget test initially required the first search to report `work_limit`
even when its one allowed, truth-valued test seed had already resolved locally.
The retained first test run is **404 passed, 1 failed**. The separately admitted
test correction preserves that local status, a later budget-denied search,
explicit unstarted seeds and overall incompleteness. It changes no solver
threshold, budget, original experiment or scientific target.

## Smooth proposal followed by literal rounded cost

`backend.finite_acquisition_predictor.fit_acquisition_segment_predictor` is a
separate local strategy with the same public fitting arguments. For smooth
mode it passes through the original fitter. For staged/PNG mode it can allocate
one quarter of each global evaluation, cell-work and stage-product cap to the
smooth proposal phase, using all supplied observed-only starts.

The represented minimum smooth cost, with candidate index as deterministic
tie-breaker, supplies one geometry/brightness start for the literal objective.
Every alternative and selection origin remains recorded. If no safe proposal
is available, the literal phase uses the original starts. Both phases share
the original total operator budgets; charged reservations, including opaque
failures, are deducted before the second phase. This is not a claim of equal
aggregate iteration count or wall time.

The result retains complete phase outputs, ledgers, charged/reported work,
source bindings, skipped/unstarted work and completion-withheld reasons. A
proposal quota ending is distinct from the total budget ending. Literal local
stopping evidence remains unchanged; unknown work or source/protocol failures
also withhold overall completion. Proposal rank or derivatives never become
rank or derivatives of the rounded objective.

This approach is motivated by the successful smooth fits and poor cold-start
rounded searches. It does not implement the strongly convex nonsmooth
variable-projection theory of
[van Leeuwen and Aravkin](https://arxiv.org/html/1601.05011v6), nor assume that
those convergence results apply to discontinuous PNG encoding.

## Angle information can disappear before blur

The following is an independent geometric derivation for the ideal smooth
model. Let `m` be the stored canonical normal, `q=m dot m`, `n=m/sqrt(q)` and
`g=f/sqrt(q)`. Binary64 canonicalization need not give exact `q=1`. For
`|g|<1`, write the physical chord as

```text
x(s) = C + R*g*n + s*J*n,       -ell <= s <= ell,
ell^2 = R^2 * (1-g^2).
```

Continuous rotation at fixed norm gives normal velocity `-s`. For fixed source
cells of pitch `p`, the coverage angle column therefore satisfies

```text
Jtheta,j = -(1/p^2) integral_(chord intersect cell j) s ds,
sum_j |Jtheta,j| <= ell^2/p^2.
```

If the entire chord lies strictly inside one source cell, its odd first moment
cancels in that cell and there is no chord contribution elsewhere. Every angle
column is then zero even when the disk crosses many cells and centre/radius
retain nonzero sensitivities. Nearby rotations that keep the chord in that cell preserve
its cell areas in the ideal geometry. A fixed later blur or resampling cannot
restore this missing first-order angle information.

For brightness contrast `Delta=b-a` and a fixed acquisition operator with
absolute row-sum gain `G=max_i sum_j |Aij|`,

```text
||W Delta A Jtheta||2 <= |Delta| ||w||2 G ell^2/p^2.
```

A sufficient gain uses optical-kernel L1 times Keys L1 times post-kernel L1;
signed Keys coefficients require absolute sums. Orthogonal projection against
brightness nuisance columns in the weighted residual frame cannot increase
this mean-column norm. The bound does not cover the additional residual term
of the complete variable-projection Jacobian, arithmetic/camera error or
rounded operations. Unknown cell derivatives at contacts/endpoints stay unknown.

Equivalently `ell^2=L_chord^2/4=d*(2R-d)`, where `d=R-|R*g|` is the smaller
circular-cap depth. This differs from the study's reserved material normal span
`R*(1+f)` in its declared unit-angle family. The bound collapses near either
segment endpoint. For five domain-scaled geometry columns, the smallest
singular value is at most the scaled angle-column norm; good circle-radius
information therefore does not imply good chord-angle information.

## Rank, quantization and what remains unknown

Projecting against two independent unknown brightness columns leaves at most
`N-2` residual dimensions. Five geometry directions require at least seven
independent samples, and seven alone does not guarantee rank five. Zero
contrast annihilates mean geometry information. A fixed active-face rank and
the conservative rank after both brightness directions answer different
questions; neither is a global uncertainty or physical-accuracy certificate.

PNG encoding maps intervals to codes. Distinct shapes can yield the same
quantized data, so even zero training residual need not select a unique shape.
[Quantization-aware phase retrieval](https://arxiv.org/html/1810.01097v1)
uses measurement consistency and discusses indistinguishability for a different,
quadratic inverse problem. Its accuracy and convergence results are not results
for this acquisition model. A future geometry-feasible-set treatment must retain
actual encoding thresholds, tie conventions, saturation and float32 stages;
that algorithm is not supplied by the smooth-proposal continuation.

The original reference uses independent positive-slice GL64/96 areas, scalar
stencils and explicit casts/encoding. Order agreement is a diagnostic rather
than a certified bound. Geometry, reserved dimensions, sampled boundary error,
conditional reserved residuals and local completion all have unchanged declared
targets. Source tests, numerical recovery, optics/noise adequacy, installed-tool
behavior and physical acceptance remain separate evidence.
