# Coupled and source-event acquisition-recovery results

The separately frozen [coupled proposal](../finite-acquisition-coupled.md)
was first executed at `b9fe285f7c634d050a735489aafcf161d1a98295`, tree
`6a756c61928b0dce99d99763d1776ef226947145`. Its complete 24-case study reports
**11/12 matched passes, exit 1**. All original targets, observed-only starts and
bounds, 135 training/34 conditional reserved matched-query split, reference
values and global work caps remain unchanged. The complete protocol still fails.

The first focused software run passes **548 tests and nine subtests** under
Python 3.12.3, NumPy 2.5.4 and OpenCV 4.14.0, with BLAS/OpenMP threads set to one
and runtime warnings treated as errors. These are software checks, separate
from the failed scientific protocol and from application/browser checks.

## Complete census

| Case | Population | All original targets | Retained status |
| --- | --- | --- | --- |
| minor-smooth | matched | Pass | Completed; initial strategy retained |
| minor-staged | matched | Pass | Completed; initial strategy retained |
| minor-png | matched | Pass | Coupled improvement; zero training and conditional reserved residual |
| middle-smooth | matched | Pass | Completed; initial strategy retained |
| middle-staged | matched | Pass | Completed; initial strategy retained |
| middle-png | matched | Fail | Fraction and conditional reserved-residual targets miss |
| major-smooth | matched | Pass | Completed; initial strategy retained |
| major-staged | matched | Pass | Completed; initial strategy retained |
| major-png | matched | Pass | Coupled improvement then literal polish; zero training and conditional reserved residual |
| wrapped-major-smooth | matched | Pass | Completed; initial strategy retained |
| wrapped-major-staged | matched | Pass | Completed; initial strategy retained |
| wrapped-major-png | matched | Pass | Initial zero-cost tied result retained |
| zero-smooth | adverse | Fail | No fit; refusal retained |
| zero-png | adverse | Fail | No fit; refusal retained |
| low-staged | adverse | Fail | No fit; refusal retained |
| cropped-smooth | adverse | Fail | No fit; refusal retained |
| thin-png | adverse | Fail | No fit; refusal retained |
| almost-circle-smooth | adverse | Fail | No fit; ambiguous preparation retained |
| wrong-optics-smooth | adverse | Fail | Geometry, dimension, boundary and residual misses retained |
| gradient-staged | adverse | Fail | Centre, angle and conditional residual misses retained |
| singular-map-png | adverse | Fail | Original exception retained |
| five-queries-smooth | adverse | Fail | Geometry, dimension, boundary, residual, rank and completion misses retained |
| coincident-smooth | adverse | Pass | Completed; adverse row remains outside matched denominator |
| budget-png | adverse | Fail | Original budget and target failures retained |

There are 23 completed rows, one exception and 17 attempted fits. Six adverse
rows stop before fitting. All 17 embedded initial strategy results match their
preceding predictor outputs in the saved-only comparison. No adverse row is
promoted to the 12-row matched recovery denominator.

## What changed and what did not

The [admission](evidence/acquisition-continuations-20261113/coupled-admission.json)
adds simultaneous geometry/brightness proposals from a separately unrounded
seven-column mean surrogate. Only strict reduction of actual PNG training cost
accepts a coupled trial. Surrogates, rejected rays and final literal coordinate
polish share the original total limits: 2,048 evaluations, 1,000,000 source-cell
units and 100,000,000 stage-product units. Iteration limits are per phase/seed,
not an aggregate wall-time bound.

Across the complete study, 42 surrogate records and 42 coupled iteration
records retain two strict coupled acceptances. Smooth, staged, zero-cost and
unsafe/unavailable cases pass through the preceding strategy without coupled
model work. Minor and major PNG now pass; middle PNG remains unchanged.

Middle PNG uses 720/2,048 evaluations, 103,090/1,000,000 cell units and
4,866,862/100,000,000 stage units. It accepts no improvement in 24 coupled
iterations, then resolves locally by coordinate polling. Its fraction error
is `0.003528725623290513` against `0.002`; its conditional reserved maximum
residual is `0.06518173217773438` against `0.01`.
The final cost is `0.302031169350812`, equal to the initial cost.

Saved trial predictions show that the first direction's factors 1, 2 and 4
change none of the 135 training predictions. Factor 8 changes 26 predictions
but worsens cost to about 3.30361. Increasing damping then shrinks directions
into the same plateau. This motivates source-threshold proposals; it does not
identify a unique wrong source code or prove that a better geometry exists.
The current fit records did not retain the incumbent optical/code snapshots.

## Retained archives, audits and limits

The [evidence inventory](evidence/acquisition-continuations-20261113/manifest.json)
contains verbatim reports, admissions, freezes, first logs, terminal receipts
and archive metadata. The complete local coupled fixture contains all arrays,
candidate/phase/work ledgers and its exact 69-file source snapshot; it is not
published by this documentation change. Its report SHA-256 is
`a1394780cf73b99a321741cd9f56d0c36d55cd094587f7bb355b88df9a414bb6`.
The [coupled report](evidence/acquisition-continuations-20261113/coupled-report.json)
is a result extract, not a replacement for full candidate ledgers and arrays.

The historical paired auditor records 6,595,622 implemented checks, zero
inconsistencies and 28 required unverified pre-cast comparisons, exit 1.
The coupled auditor first fails 17 input-hash framing checks. Its separately
admitted correction verifies all 1,191,323 current implemented checks, with
24/24 current pre-cast comparisons, exit 0. All 28 historical unknowns remain visible.
See [first failures, correction and exact audit exclusions](../finite-acquisition-saved-audit.md).

A [post-run read-only source/ledger review](evidence/acquisition-continuations-20261113/coupled-read-only-ledger-review.json) performed 28,396 structural checks
with zero discrepancies, including source bindings, budgets, 4,536 ledger
entries, surrogate statuses, strict acceptance and selected-phase ties. That
review has no separately admitted corruption-control matrix and does not
qualify a general auditor or the scientific model.

Raw source-cell and `Ac/AD/A1` component fields of the surrogate Jacobian were
not archived, so saved-only work cannot independently reconstruct that matrix.
Its unrounded columns are not derivatives or rank certificates of PNG
acquisition. Candidate ties and zero residuals do not establish unique geometry.
Reserved pixels influenced initialization; their later residuals remain
conditional. No independent forward/reference accuracy, certified boundary
supremum, rank/stopping calculus, unknown-camera adequacy, interactive latency,
native slicer or physical CAD/print qualification follows from this study.

## Source-event continuation: no further recovery

The separately [admitted event strategy](evidence/acquisition-continuations-20261113/events-admission.json)
first executes at `cd85ef937e3d3a49aace45217c902e484f3ac615`, tree
`e067594cad63ecec30a6c264e7f046592f7f7bab`. It retains every row in the census
above with the same population, completion/exception status and all-target
outcome: **11/12 matched passes, exit 1**. There are 23 completed rows, one
singular-map exception, 17 attempted fits, six pre-fit stops and one adverse
all-target pass. The adverse coincident row stays outside the matched denominator.

Its first focused suite passes **653 tests and 21 subtests** in the same
Python/NumPy/OpenCV environment. Software controls and the retained failed
scientific protocol are separate evidence. No full application/browser or
physical run is inferred from either.

The [source-code event method](../finite-acquisition-events.md) uses actual
incumbent optical/code snapshots and a fixed unrounded downstream response
to score adjacent source-code substitutions. A full seven-coordinate optical
surrogate proposes crossings; only strict decrease of actual PNG training
cost can accept one. All initial coupled work, response/sensitivity calls,
encoder probes, rejected trials and polish share the original global caps.

The [saved middle-PNG extract](evidence/acquisition-continuations-20261113/middle-png-event-extract.json) retains three negative-score latent events and nine actual candidates
in one event cycle, with **zero acceptances**. The final cost remains
`0.302031169350812`; fraction error stays `0.003528725623290513` against
`0.002`, and conditional reserved maximum stays `0.06518173217773438` against
`0.01`. Work increases to 1,000/2,048 evaluations, 136,214/1,000,000 cell
units and 6,840,536/100,000,000 stage units, without exhaustion.

The most favorable isolated source substitution, cell 62 code 93→92, has a
surrogate score about −0.3020311693. Its three actual trial costs are about
2.87538, 2.57335 and 8.23765, all worse. Its source-optical row has zero
fraction/angle columns, so the declared minimum-norm crossing sets both moves
to zero. This diagnoses a limitation of that local proposal; it does not
prove a better geometry exists. Actual trial source codes were not retained,
so these data cannot establish which collateral code changes caused rejection.

The complete local event archive has 115 members and the exact 78-file source
snapshot. Its [report](evidence/acquisition-continuations-20261113/events-report.json)
has SHA-256 `9773319dcfdf17473d07fc4aa948c8f4ba90696f801120015653900c0fab3159`.
The [archive inventory](../finite-acquisition-saved-audit.md) provides sizes and
hashes; the full archive and candidate source remain local. The corrected
coupled auditor covers coupled-v1 only; it has not audited this new event-phase
ledger. All reference, model, conditional-residual, identifiability and physical
limitations above remain in force. No unexecuted follow-up is a new result.
