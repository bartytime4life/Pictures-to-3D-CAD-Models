# Completed active-face recovery and physical-rounding diagnosis

This record follows the unchanged [first active-face software failure](finite-acquisition-protected-active.md).
Three separate outcomes must be read together:

| Evidence | Frozen source | First result | Meaning |
| --- | --- | --- | --- |
| Corrected selected controls | `c1a933099d34475bb1bbfb04de17fa41b61b4d42` | 821 passed, 33 subtests passed; exit 0 | The added expectation-only test copy and selected software controls pass |
| Complete original recovery study | Same source, 100 governing inputs | 11/12 matched passes, 24 rows; exit 1 | Recovery protocol remains failed |
| Saved physical-rounding diagnostic | `b649ea3e09c5c6e1b772d1bc3f0f5a378f764b33`, 104 inputs | 49 controls pass; diagnostic checks 128 corners, accepts none; exit 1 | Complete negative adjacent-box result, zero arithmetic unknowns |

The [evidence inventory](evidence/acquisition-physical-rounding-20261113/manifest.json)
contains 20 verbatim records and an explicitly derived saved-field extract.
The original 820-pass/one-failure result and the earlier protected design's
eight failures remain preserved. This documentation refresh reruns no scientific
test, study, solver, model or diagnostic. Candidate implementations remain
local research, absent from this main runtime, HTTP routes and workbench UI.

## Separately admitted expectation-only correction

The invented fixture supplies two finite target sides plus 14 box sides:
16 raw rows, requiring `16*(512+512) = 16,384` work units. The separately
added test copy changes only its expected row count from 15 to 16. It does
not edit the original test, solver, work charges, targets or case population.
The new admission, runner metadata and guide were frozen with all 100 inputs
before the corrected selection ran.

The first selected command records **821 passed and 33 subtests passed in
16.06 seconds**, native session 99257, exit 0. This is a selected-suite pass;
the unrestricted suite still contains the original failing expectation.
Assertions after that old failure now execute in the corrected copy.
See the [unaltered log](evidence/acquisition-physical-rounding-20261113/controls-v2-first-tests.log),
[terminal receipt](evidence/acquisition-physical-rounding-20261113/controls-v2-first-tests-receipt.json)
and [combined freeze](evidence/acquisition-physical-rounding-20261113/controls-v2-freeze.json).

## Complete original 24-case outcome

The first full run is native session 74108, exit 1. It retains all original
cases, their order, targets, reference checks and adverse cases. There are
23 completed rows and one singular-map exception, 17 fit attempts, six
pre-fit refusals and one adverse case meeting all targets. All 106 reported
artifact hashes/sizes and all 24 saved row records were read back unchanged.

| Case | Family | Saved status | Fit attempted | All targets |
| --- | --- | --- | --- | --- |
| minor-smooth | matched | completed | yes | yes |
| minor-staged | matched | completed | yes | yes |
| minor-png | matched | completed | yes | yes |
| middle-smooth | matched | completed | yes | yes |
| middle-staged | matched | completed | yes | yes |
| middle-png | matched | completed | yes | no |
| major-smooth | matched | completed | yes | yes |
| major-staged | matched | completed | yes | yes |
| major-png | matched | completed | yes | yes |
| wrapped-major-smooth | matched | completed | yes | yes |
| wrapped-major-staged | matched | completed | yes | yes |
| wrapped-major-png | matched | completed | yes | yes |
| zero-smooth | adverse | completed | no | no |
| zero-png | adverse | completed | no | no |
| low-staged | adverse | completed | no | no |
| cropped-smooth | adverse | completed | no | no |
| thin-png | adverse | completed | no | no |
| almost-circle-smooth | adverse | completed | no | no |
| wrong-optics-smooth | adverse | completed | yes | no |
| gradient-staged | adverse | completed | yes | no |
| singular-map-png | adverse | exception | no | no |
| five-queries-smooth | adverse | completed | yes | no |
| coincident-smooth | adverse | completed | yes | yes |
| budget-png | adverse | completed | yes | no |

The [verbatim full report](evidence/acquisition-physical-rounding-20261113/recovery-report.json)
retains per-target flags, errors, reference checks, exceptions and source hashes.
The [first terminal receipt](evidence/acquisition-physical-rounding-20261113/recovery-first-receipt.json)
binds native completion and artifact checks. A completed row is not necessarily
a target pass; the adverse coincident-smooth case's all-target pass is retained.

Middle PNG retains training cost `0.302031169350812`, fraction error
`0.003528725623290513 > 0.002`, and conditional reserved-query maximum
residual `0.06518173217773438 > 0.01`. Work is 990/2,048 evaluations,
135,031/1,000,000 cell evaluations and 54,520,546/100,000,000 stage units,
without exhaustion. No protected trial reaches literal evaluation. Its three
events retain `rounded_point_unavailable`, `exact_face_unresolved` and
`exact_face_unresolved`; unknown face searches are not infeasibility proofs.
The reserved checks are conditional residual diagnostics, not independent
camera predictions. The sampled boundary metric is not a certified supremum.

## Independent saved certificate and complete physical census

The separately frozen diagnostic reads all 24 report rows and 17 fit files.
Sixteen fits have no qualified certificate. For the one qualified event,
middle PNG / source 62 / code 93 to 92, it reconstructs the original local
problem and independently verifies all rational KKT conditions over 352 raw
halfspaces. A rational optimum does not guarantee a feasible binary64 trial.

The first 49 controls pass in 0.06 seconds. They include independent exact
examples, equality gaps, nonunit/fixed spans, representation-gate differences,
strict arithmetic-floor boundaries, bounded arithmetic and serialization.
The saved census then runs once as native session 51773 and exits 1. Its
status is `diagnostic_not_qualified`, with `diagnostic_complete=true` and no
errors. Every one of 128 distinct adjacent corners is retained and checked:

| Gate | Passing corners |
| --- | --- |
| Original physical bounds | 128/128 |
| Selected-source arithmetic floor | 128/128 |
| Exact physical-normalized membership | 0/128 |
| Exact membership of computed displacement | 0/128 |
| Existing computed source/box gate | 0/128 |
| All gates together | 0/128 |

Arithmetic unknowns: **zero**. Only the five rationally tight source sides
are violated. Independent saved-output reviews confirm the original anchor,
spans, arrays, code identities and all recorded gates; no reconstruction
mismatch was found. Normalized nearest rounding and physical rounding followed
by renormalization concern different represented points, so their computed-gate
outcomes need not match.

The [saved-field extract](evidence/acquisition-physical-rounding-20261113/rounding-saved-extract.json)
preserves all 24 inventory rows, the certificate flags and all 128 candidates'
physical bits, gates and violation identities. It omits full rational arrays
and residuals and is explicitly not the full diagnostic. That unchanged
9,669,740-byte diagnostic has SHA-256
`fcf64aa7549f35b6edd27fc38104aef69ead6053469980486b4b0edcdd1c5443`.
See the [first receipt](evidence/acquisition-physical-rounding-20261113/rounding-first-receipt.json)
and [104-input freeze](evidence/acquisition-physical-rounding-20261113/rounding-freeze.json).

This establishes no accepted point in the checked adjacent physical box under
the unchanged gates. It does not prove global float nonexistence, nonlinear
infeasibility or a recovery improvement. The
[inward-point proposal and proof obligations](../finite-acquisition-physical-rounding.md#an-inward-point-is-future-work)
remain unexecuted and require a new admission before numerical work.

## Local packaging and publication boundary

The [recovery archive readback](evidence/acquisition-physical-rounding-20261113/recovery-archive-readback.json)
verifies 121 members in an 18,096,291-byte complete ZIP and 101 members in
its recorded-source ZIP. The
[rounding archive readback](evidence/acquisition-physical-rounding-20261113/rounding-archive-readback.json)
verifies 13 members in a 19,502,334-byte complete ZIP, including that unchanged
recovery ZIP, plus a 105-member recorded-source ZIP containing all 104 inputs.
Both are local artifacts; paths in receipts identify that research checkout.
Complete ZIPs, full arrays, tests and executable runners are outside this
documentation publication. Member readback establishes byte consistency,
not a complete ledger, model, runtime or physical audit.

The first recorded commands are provenance for their frozen checkout. Their
paths are absent from this main-based source; follow
[developer-tool availability](../developer-tools.md) rather than trying them
as main-branch commands. No scientific rerun is needed to read these results.
The earlier coupled saved-only audit does not extend to the active full ledger;
this independent KKT/corner check has its own narrower scope. No installed
runtime, deployment, native slicer or physical CAD/print qualification follows.
