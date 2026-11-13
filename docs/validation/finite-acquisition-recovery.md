# Local acquisition-recovery research record — November 13, 2026

This is a report of separately frozen local research, not a new main-branch
fitting API. The documentation base is main
`e0b16e0a0a0d9e16477442b622c32ad0868c062e`. Its runtime contains the forward
area/acquisition operators and unrounded sensitivities, but none of the new
photometry, observation-preparation, fitting or predictor modules. See the
[method and mathematical limits](../finite-acquisition-recovery.md).

Both complete recovery protocols fail. A smooth proposal before literal rounded
fitting improves the **reported matched count from 4/12 to 9/12**, while three
PNG cases still miss the original targets. This documentation pass does not
rerun the models or independently reproduce those numerical results.

## Sources and retained evidence

| Record | Frozen source or binding | Recorded outcome |
| --- | --- | --- |
| Original protocol and fit | `7ec680386f75e44415aeb4c83552aa723399c0bc`, tree `e182dc7d4da20fc825a5ff01f3d241c8a0b743a3` | 24 cases, 4/12 matched passes, exit 1 |
| Original first focused tests | Same original source | 404 passed, 1 failed |
| Separately admitted predictor continuation | `e6e2c2881add2cc594f4a59d713edf8a9ddde665`, tree `6186793e71eac4df7d5779c685203ab97b6dad02` | 24 cases, 9/12 matched passes, exit 1 |
| First focused candidate tests | Same continuation source | 459 passed in 16.33 seconds, exit 0 |
| Original-run saved-data auditor | Auditor SHA-256 `749cb6b9a158b81891cb58109b114b2a18bf4aca1933c8268beca2bfa00a0373` | 5,740,807 checks, 14 failures, exit 1 |

The [evidence manifest](evidence/acquisition-recovery-20261113/manifest.json)
binds verbatim reports, logs, frozen plans, a terminal receipt and three static
source excerpts. It includes the [original report](evidence/acquisition-recovery-20261113/original-report.json),
[continuation report](evidence/acquisition-recovery-20261113/continuation-report.json),
[first audit output](evidence/acquisition-recovery-20261113/original-audit.json)
and [focused-test log](evidence/acquisition-recovery-20261113/focused-tests.log).
The reports retain all 24 rows, error vectors, target flags, exceptions and
artifact hashes. These extracts contain no photographs or user models.

This extract is **not the full raw-data archive**. Original captures, full
candidate ledgers and the recorded-source ZIP remain in the separate local
research checkout. Its complete original archive is 27,710,505 bytes, SHA-256
`e25fe8a0ca8675daafed1b0b577de1d68f4d42e21bf91ee3ba72d43fcb98e724`.
That archive and the candidate runtime are not published by this documentation
change. The extract alone cannot rerun the saved-data auditor or scientific study.

Report SHA-256 bindings are:

- Original: `30a3e30f26150124da22d76cc3b7c36aaf2212d094a1a5601253722442edad28`.
- Continuation: `f73120151fb709521417f07ff7bc3ac82f3039e5170fc912bd692429bd4f949e`.
- First saved-data audit: `dc2b0b454c2be8cb9025d5f444deba23dbd15563fb7a786871f63b7ceea90533`.

All 60 governing continuation files matched their pre-execution hashes after the
tests, study and auditor finished. The [freeze](evidence/acquisition-recovery-20261113/continuation-freeze.json)
and [terminal receipt](evidence/acquisition-recovery-20261113/continuation-terminal-receipt.json)
retain that binding. The
[original study freeze](evidence/acquisition-recovery-20261113/original-study-freeze.json)
and [continuation study freeze](evidence/acquisition-recovery-20261113/continuation-study-freeze.json)
record Python 3.12.3 for both studies, with NumPy 2.5.4,
OpenCV 4.14.0, `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. The separate
standard-library saved-data auditor records Python 3.14.4. These environments
belong to their individual records; the workbench setup still requires Python 3.12.

## Unchanged population and targets

The [original plan](evidence/acquisition-recovery-20261113/original-plan.json)
contains four matched circular-segment geometries, each evaluated as smooth
float64, literal staged float32 and PNG acquisition: 12 matched rows. Another
12 adverse rows retain low/zero contrast, cropping, thin/almost-complete
segments, wrong optics, a brightness gradient, singular mapping, few queries,
chord/cell-side coincidence and a tiny budget. Refusing an adverse fit does not count as recovery.

Matched source/output fields are 13 × 13 with unit source pitch and supplied
kernels/affine map. The unknowns are five geometry parameters and two bounded
brightness levels. Full-field observation preparation retains up to 32 hypotheses
and four observed-only starts; its operational bounds are not proved enclosures.
Truth is opened for evaluation after fitting inputs and outputs are saved.

| Per-row target | Required limit |
| --- | --- |
| Centre and radius errors | Each at most 0.02 source pitches |
| Chord-fraction error | At most 0.002 |
| Wrapped normal-angle error | At most 0.2 degrees |
| Reserved dimension error | At most 0.03 source pitches |
| Sampled bidirectional boundary error | At most 0.03 source pitches; a lower approximation, not a certified supremum |
| Maximum conditional reserved-query residual | At most 0.01 linear intensity levels |
| Smooth conservative geometry rank | Five after both unknown brightness directions |
| Local completion | Best candidate linked to a resolved projected-gradient/poll search, without total work exhaustion, protocol failure or continuation completion withholding |
| Independent-reference diagnostic | GL64/96 area-order delta at most `1e-9`; matching encoded order codes where relevant; agreement is not a certified error bound |

For ordinary matched rows, 135 queries enter the fit and 34 are reserved by
`(x + 2*y) % 5 == 0`. Reserved pixels already entered full-field initialization,
so their residuals are conditional diagnostics, not independent holdout evidence.

## Complete reported row census

The table below is generated from the two unchanged reports. “Pass” means every
declared row target is reported satisfied, not global, optical or physical
acceptance. No adverse row enters the 12-row matched denominator.

| Case | Population | Original all targets | Continuation all targets | Continuation status or remaining miss |
| --- | --- | --- | --- | --- |
| minor-smooth | matched | Pass | Pass | completed |
| minor-staged | matched | Fail | Pass | completed |
| minor-png | matched | Fail | Fail | conditional residual |
| middle-smooth | matched | Pass | Pass | completed |
| middle-staged | matched | Fail | Pass | completed |
| middle-png | matched | Fail | Fail | fraction, conditional residual |
| major-smooth | matched | Pass | Pass | completed |
| major-staged | matched | Fail | Pass | completed |
| major-png | matched | Fail | Fail | conditional residual |
| wrapped-major-smooth | matched | Pass | Pass | completed |
| wrapped-major-staged | matched | Fail | Pass | completed |
| wrapped-major-png | matched | Fail | Pass | completed |
| zero-smooth | adverse | Fail | Fail | no fit; refused |
| zero-png | adverse | Fail | Fail | no fit; refused |
| low-staged | adverse | Fail | Fail | no fit; refused |
| cropped-smooth | adverse | Fail | Fail | no fit; refused |
| thin-png | adverse | Fail | Fail | no fit; refused |
| almost-circle-smooth | adverse | Fail | Fail | no fit; ambiguous |
| wrong-optics-smooth | adverse | Fail | Fail | centre, radius, fraction, angle, dimensions, sampled boundary, conditional residual |
| gradient-staged | adverse | Fail | Fail | centre, angle, conditional residual |
| singular-map-png | adverse | Fail | Fail | exception retained |
| five-queries-smooth | adverse | Fail | Fail | centre, radius, fraction, angle, dimensions, sampled boundary, conditional residual, local completion, rank |
| coincident-smooth | adverse | Pass | Pass | completed |
| budget-png | adverse | Fail | Fail | centre, radius, fraction, angle, dimensions, sampled boundary, conditional residual, local completion |

Both reports retain 23 completed rows and one `singular-map-png` exception.
Each attempts 17 fits. Six adverse rows stop before fitting, and only
`coincident-smooth` records all targets among the adverse population. That does
not turn the adverse population into a recovery success rate.

## What changed in the continuation

The [admission](evidence/acquisition-recovery-20261113/continuation-admission.json)
preserves the original reference, population, target values, observation-only
initialization, query split and total operator caps. Smooth mode uses the
original fitter. Rounded modes may spend `floor(cap/4)` of each evaluation,
cell-work and stage-product cap on a smooth proposal, then pass one selected
geometry/brightness start to the literal rounded fitter. All proposal
alternatives and selection origins remain recorded. Unavailable proposals fall
back to the original starts; charged work reduces the second phase's budget.

This is a different search strategy, not a larger total operator allowance or
a theorem about the discontinuous objective. Iteration limits apply per seed
within each original-fitter phase; aggregate iterations and wall time are not held equal. Proposal
rank and Jacobians do not become rank or derivatives of rounded acquisition.
The continuation also withholds completion on protocol/source/unknown-work
problems and prevents a late exception from retaining a counted row pass.

The original first test failure required a work-limit status for an already
locally resolved truth-valued unit-test seed. The separately admitted test
correction preserves that valid local status, a later denied search, explicit
unstarted seeds and overall budget incompleteness. It changes no solver
threshold, scientific target or original result. Both the first failed test log
and subsequent 459-test pass remain in the evidence extract.

## Remaining PNG failures and ties

| Continuation row | Failed target and saved error | Original target |
| --- | --- | --- |
| Minor PNG | Conditional reserved maximum residual `0.0590057373` | `0.01` linear intensity levels |
| Middle PNG | Fraction error `0.0035287256`; conditional residual `0.0651817322` | `0.002`; `0.01` linear intensity levels |
| Major PNG | Conditional reserved maximum residual `0.0669751167` | `0.01` linear intensity levels |

All three searches report local poll resolution without total work exhaustion,
and all retain tied candidates. This rules out calling a local plateau sufficient
for every recovery target; it does not isolate the physical cause of the error.
Wrapped-major PNG passes all declared targets but is also tied. Its zero training
cost and zero reserved residual coexist with a normal-angle error of about
0.171 degrees. Matching quantized data therefore does not establish unique geometry.

## First saved-data audit: retained failure

The auditor reads the original saved run and its recorded-source ZIP as data,
without model, optimizer, reference-generator or current-checkout-source calls.
Its first execution reports **14 failures out of 5,740,807 checks**, with no
truncation. Every failure is `rows/<case>/reference/area_delta`, across the
14 staged/PNG rows. The exit status and output remain unchanged.

Static inspection explains the representation mismatch:

1. The [original runner excerpt](evidence/acquisition-recovery-20261113/finite-acquisition-recovery-v1.py.txt)
   computes `max_area_order_delta` from its uncast GL64/96 cell arrays.
2. The [reference excerpt](evidence/acquisition-recovery-20261113/finite-acquisition-recovery-reference-v1.py.txt)
   casts coverage to float32 for staged/PNG mode and saves that rounded coverage.
3. The [auditor excerpt](evidence/acquisition-recovery-20261113/finite-acquisition-recovery-audit-v1.py.txt)
   tries to reconstruct the pre-cast delta from those saved rounded arrays.

Those arrays cannot recover the discarded bits. The original reported pre-cast
delta remains **not independently verified for those 14 rows**. This diagnosis
does not provide missing float64 arrays, change the original reference gate,
convert the auditor to a pass or establish a fitter defect. A corrected audit
would require separate admission and retained coverage limits; none is run here.

No other inconsistency is reported by that first auditor in its implemented
artifact, input, residual/cost, ledger, resource, local-status and target checks.
It does **not** independently recompute forward predictions, reserved predictions,
sampled boundary discrepancies, Jacobians, SVD/rank, brightness optimality or
stopping calculus. It is specific to the original fit schema and has not audited
the continuation's composite phase ledger. Reading the two reports is not a
replacement for that missing independent continuation audit.

## Qualification boundary and next engineering work

The [model guide](../finite-acquisition-recovery.md) derives an ideal smooth
angle-information bound and explains the nonzero-residual term in brightness
variable projection. A chord wholly within one source cell can have a zero
angle column before blur, even with nonzero centre/radius sensitivities. At
least seven independent samples are necessary for five geometry directions
after two independent brightness directions; that count is not sufficient.

Further work needs separately admitted quantization-consistency/feasible-set
methods, complete precision-preserving reference capture and independent
composite-ledger auditing. Broader supplied-optics recovery, estimated camera
models, noise/model adequacy, interactive latency and common-boundary preservation
through CAD/export remain open. No live-camera/caliper benchmark, installed
slicer result or physical print/fit acceptance is supplied by these records.
