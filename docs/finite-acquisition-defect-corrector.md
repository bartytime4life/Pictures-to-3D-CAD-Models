# One observed-defect correction for the saved PNG case

The first fixed correction at research `d986f1f` reduces actual training cost
from **0.302031169350812 to 0.0** at all 135 supplied synthetic PNG queries.
It changes only source 62's code, 93 to 92; source 33 retains code 106.
The accepted incumbent is replayed exactly on all nine checks. The
[complete first result](validation/finite-acquisition-defect-corrector.md)
retains 220 passing controls, one exact Gram solve, one nearest physical tuple,
all local gates, both actual forwards and their stages.

This is separate local research. Main has no five-geometry-parameter
acquisition-aware recovery fitter or workbench control for this correction.
Zero quantized training residual does not establish unique geometry, a reserved
prediction, full recovery, camera accuracy or a physical tolerance. The original
11/12 full-recovery result remains failed. This standalone experiment did
not rerun it; the later live study has a separate result below.
The preceding [literal pair](finite-acquisition-inward-literal.md), cost
0.40923713513984694 and collateral code change, remains rejected and unchanged.

The following method describes the frozen 116-input admission. Its original
prospective guide is preserved as
[verbatim text](validation/evidence/acquisition-defect-corrector-20261114/corrector-prospective-method.txt);
this reader-facing explanation is a later document, outside that frozen closure.

The saved-data audit also finds all 169 actual optical values inside the
original raw source bands, including source 62's central-half proposal slice.
Only 168 actual values retain the full proposed storage guard; source 109
has lower slack `0.00022125244140625`, below `2^-12`, with its code preserved.
This diagnostic illustrates why a proposed storage allowance is separate
from an observed nonlinear result or a uniform remainder guarantee.

The later [live controller](finite-acquisition-restoration-result.md) is
frozen and executed using fresh fit context and a distinct per-operation
charging policy. Its 1,169 selected controls and 33 subtests pass. The fresh
24-case study still fails at 11/12; zero training and conditional reserved
residuals leave a fraction error above its original target. This standalone
single-context record retains its own source and accounting.

## Keep the accepted and rejected points distinct

Let `p0` be the saved accepted incumbent, `p1` the rejected literal candidate,
and `z1` its saved actual source-optical field. Keep the original stored
normalization spans `s`, old local matrix `G`, original raw source bands,
normalized bounds and physical limits unchanged. No reference geometry,
reserved residual or new derivative selects this correction.

For positive spans use the centered correction chart

```text
u_j = (p_j - p1_j) / s_j,
m1(u) = z1 + G u.
```

All rational gates convert each represented operand before subtraction or
division. A zero span requires the physical coordinate to remain fixed and
its correction to be zero. The original normalized-domain coordinate remains
`d_j=(p_j-p0_j)/s_j`. It is not replaced by the correction coordinate.

The exact rejected displacement is
`d1_j=(F(p1_j)-F(p0_j))/F(s_j)`, where `F` denotes the exact rational value
of a stored binary64 input. The original domain is checked using this exact
relationship or directly from `p0`. No rounded `z1-G*d1` intercept or rounded
shifted box is substituted to satisfy an old helper's binary64 interface.
The model interpolates the observed rejected optical field at `u=0`; this
does not make `p1` accepted or make `G` a derivative of the rounded pipeline.

## One equality-restoration proposal

Reverify the original saved KKT witness under its own unchanged local model.
That certificate does not qualify the new model. From every exactly tight
original nonstructural row, retain the first independent normals in original
row order after removing fixed coordinates. Keep all other tight and inactive
rows for final checks. The saved context has five independent tight source
rows; neither source 33 nor 62 is singled out as the only constraint.

For an upper source row use normal `G_i` and new bound `U_i-z1_i`; for a lower
row use normal `-G_i` and new bound `z1_i-L_i`. Original box and physical rows
keep their exact bounds expressed in the centered chart. Call the selected
normal matrix `B` and these new bounds `beta`.

For the selected equalities compute exactly once

```text
(B B^T) lambda = beta - storage_guard - representation_margin,
u = B^T lambda.
```

Verify the equality and row-space identities independently. With full row
rank they establish minimum Euclidean norm **for those selected equalities**.
Indeed, any other equality-feasible correction is `u+h` with `B h=0`.
Since `u=B^T lambda`, `u^T h=0`, and therefore
`||u+h||^2=||u||^2+||h||^2`. This proves the stated equality-only minimum.
They do not establish minimum norm for the complete reanchored inequality
problem, transfer the old QP optimum or prove nonlinear feasibility. Rank,
rational-cap, inactive-row, fixed-coordinate or representational obstructions
produce an explicit unknown. There is no face exchange, second solve,
clipping, backtracking, alternate corner or fallback point.

The two margins in the displayed system are row-specific vectors, not scalar
offsets applied indiscriminately. Only source rows receive the intensity
storage allowance. Box and physical rows use their corresponding binary64
representation allowance, and structural/fixed rows receive no strict margin.

This design draws on the minimum-norm correction in
[Byrd, Nocedal, Waltz and Wu, section 2.5](https://optimization-online.org/wp-content/uploads/2011/04/3003.pdf):
use an old working-set Jacobian and actual trial constraint residual, then
test the corrected trial's actual objective. Our rounded acquisition chain
does not satisfy the paper's smoothness assumptions. We do not identify a
Maratos effect, implement its full algorithm or borrow convergence results.

## A global storage allowance, separate from model error

Use the fixed exact intensity allowance **`2^-12 = 1/4096`** on nonstructural
source rows. This is 16 full float32 ULPs at the declared global scale 255.
Sixteen ULPs at a small local optical value would not bound upstream casts
at a much larger source scale. Structural rows receive zero strict margin
and remain exact feasibility checks; impossible bands are not relaxed.

The representation argument assumes nearest binary32/binary64 rounding and
gradual underflow, raw coverage in `[0,1]`, brightness levels in `[0,255]`,
nonnegative optical coefficients with exact sum at most `1.000003`, and at
most 961 kernel entries. Numerical input bounds are checked; nearest rounding
and gradual-underflow behavior are assumed. Optical magnitude remains below
256 under that envelope.

For one endpoint chain, a conservative storage/arithmetic envelope is

```text
E <= K1*(255*2^-23 + 2^-16 + gamma_4*255)
     + 2^-16 + gamma_(2*Ko)*256*K1,
gamma_n = n*2^-53 / (1-n*2^-53).
E_under = (4+2*Ko)*(1+K1)*(1+gamma_(2*Ko+4))*2^-1074.
```

The terms cover coverage storage, source storage, binary64 mixing, optical
storage and binary64 multiply/add correlation. The mixed absolute/relative
rounding model adds `E_under` for gradual binary64 underflow. The standard
`gamma_n` accumulation model is described in
[Higham and Mary, section 2.2](https://eprints.maths.manchester.ac.uk/2780/1/paper.pdf);
only that arithmetic model is used here, not their linear-system theorem.
Two endpoint envelopes `2*(E+E_under)` fit within the fixed `2^-12` allowance
under the stated limits. This concerns
represented stages at supplied coverages. It does **not** bound aperture
integration error, geometry linearization, mixed geometry/brightness terms,
stale `G`, or the unobserved nonlinear remainder of a new point. Actual
code and cost evidence is still necessary.

Recompute the earlier binary64 physical/subtraction/division/product/`fsum`
proposal margin with `p1` as anchor and the original spans/physical limits.
Add it to the active rational construction target. After nearest physical
rounding, require the storage allowance alone in source membership, so the
pre-round representation allowance may absorb rounding. Keep both sets of
slacks. This representation allowance is an engineering proposal, not a
global `math.fsum` enclosure theorem; the final computed gates decide.

## One physical tuple and separate gates

Convert the single rational physical target `F(p1)+F(s)*u` to its nearest
binary64 tuple. Do not enumerate its adjacent corners or select by cost.
Retain its exact target, physical values/bits and all of:

- Unchanged physical limits and fixed-coordinate identity.
- Exact centered correction from the physical tuple, original `p0`-normalized
  domain, and every source band with its storage allowance.
- The exact values of computed binary64 correction/domain coordinates, with
  their corresponding source and original-domain checks.
- Computed centered source predictions and original-domain bounds, without
  source-band tolerance expansion.
- The unchanged selected-band arithmetic-floor formula and strict half-width
  comparison, now evaluated in the centered model.

Any failed or unknown gate prevents a literal call. It does not prove that
no feasible correction exists. The selected source-62 interval remains its
original central-half proposal slice, not the full code-92 encoder bin.

## Hold the entire experiment before constructing the point

Start from the completed preceding pair's actual aggregate:
**992 evaluations, 135,369 cell units, 54,531,024 stage units**. The original
caps remain **2,048 / 1,000,000 / 100,000,000**. Do not restart at the earlier
990-evaluation fitter total or refund its rejected trial.

For `R` original rows and `A=R+14` augmented rows, reserve the conservative
mathematical tariff

```text
math_stage_units = 512*(R + 9*A) + 65536.
```

The 512-per-row and 65,536-per-face tariffs come from the frozen active
engine. They provision original-witness verification, centered setup,
representation work, the one Gram solve and all-row roundtrip checks. They
are abstract accounting units, not measured elapsed time, memory or a
bit-complexity theorem. Rational inputs, results and pre-operation temporaries
are bounded at 32,768 bits, with at most 4,096 **augmented** rows including
the 14 physical-bound rows, and seven coordinates.

For the saved context `R=352`, `A=366`, mathematical reservation is
**1,932,288 stage units**. The unchanged direct literal pair additionally
requires **2 evaluations, 338 cell units and 10,478 stage units**. Preflight,
hold and charge the whole mathematical-plus-pair reservation before original
KKT reverification or any source-margin, basis, Gram or construction arithmetic.
No refund follows a failure or an unattempted pair.
Nested forward accounting is a view of that precharged pair, not an extra
charge. Retain reservations, attempts, reports, unavailable counters and
unattempted work separately.

## Actual acceptance remains a paired training-only test

Only a fully constructed, represented and qualified point reaches the two
direct forwards. Replay original incumbent `p0` under the exact saved training
inputs; evaluate the corrected nearest tuple under the same acquisition
chain. Keep each tuple's own two brightness levels without profiling.

Use the unchanged raw residual `y-prediction`, multiplied directly by the
saved positive residual weights, and the guarded `hypot`-then-square cost.
All nine archived incumbent qualifications must match exactly. Accept only
if the corrected cost is **strictly less than `p0`'s cost**. Merely improving
on rejected `p1` is insufficient. Target and collateral source-code changes
remain separate diagnostics and do not veto a strict actual-cost decrease.

Retain both forward attempts, raw coverage, all seven stages, predictions,
raw/weighted residuals, costs, input bits, work and every code change. Do not
retry after a failure or use a later best-fit incumbent. Missing returned
payloads stay explicitly unavailable; their held work is not reported as zero.

## Identity, first outcomes and limits

The [new admission](validation/evidence/acquisition-defect-corrector-20261114/corrector-admission.json)
separately binds the 100-input full recovery, 104-input negative census,
108-input inward construction, 112-input negative literal pair and this new
116-input closure. All 24 rows, 17 fits, 16 no-certificate dispositions and
one eligible context must remain present. First establish known expected
paths and all 106 artifact identities, then verify exact bytes before use.
Independently repeat all known source/saved after-checks even on early failure.
Late identity failure quarantines top and nested acceptance/completion labels
without erasing raw computed facts.

The CLI rejects an existing output, symlink or missing parent before
frozen-helper/backend imports or construction/model evaluation. Source gates
also precede frozen-helper and backend imports; no
old driver or old census runs, and no frozen module global is patched. First
run only the independently authored invented-data controls and unchanged
selected predecessor controls after the 116-input freeze. Only their terminal
pass permits one saved correction/probe execution. Preserve commands, native
handles where present, logs, result and terminal exits. Any post-execution
correction requires new source files and a separate admission.

`correction_not_constructed` or an arithmetic/work unknown is not
`complete_no_improvement`; that label requires a complete qualified actual
comparison. A local proposal can fail without a protocol defect. No old result
or input is amended. Fitter integration and a new complete original 24-case
protocol remain separate, as do rank/forward-model qualification, camera
accuracy, GUI/HTTP availability, installation, deployment, slicing and physical
CAD/print acceptance.
