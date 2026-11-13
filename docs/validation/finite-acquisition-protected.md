# First protected-source-bin controls — November 13, 2026

The first software run **fails: eight failures, 752 passes and 33 passing
subtests**, exit 1 in 15.96 seconds. **No full protected recovery study ran.**
This method has no new matched-case recovery score. The earlier coupled and
source-event studies each remain at 11/12, with both complete protocols failed.

## Frozen source and first execution

The separate local research checkout was committed at
`79522b5ad47ea747d644a55e3c0fe468e7d30bde`, tree
`9e3eee8936ea6f6d880c9a7287bb2f085f6908e9`. Its
[combined freeze](evidence/acquisition-protected-20261113/source-freeze.json)
binds all 88 governing inputs before any new test, projection or model call.
All 81 preceding inputs remained unchanged. The
[admission](evidence/acquisition-protected-20261113/admission.json) and
[prospective method](evidence/acquisition-protected-20261113/prospective-method.txt)
retain their original wording; they describe planned execution, not a completed
recovery experiment.

The [first command and native handle](evidence/acquisition-protected-20261113/first-tests-handle.json)
record the complete test scope and warnings-as-errors policy. Native session
16989 was polled to its terminal exit 1 without a restart. The
[unaltered log](evidence/acquisition-protected-20261113/first-tests.log) contains
every failure; the [terminal receipt](evidence/acquisition-protected-20261113/first-terminal-receipt.json)
records the result and rechecks all 88 input hashes. Passing software controls
do not erase the eight failures or test physical recovery.

## What failed

| Control family | Failed cases | Recorded result |
| --- | --- | --- |
| Unrepresentable predicted optical value | 1 | A scalar product overflows; `RuntimeWarning` escapes instead of returning the required numerical-unknown result |
| Protective nullspace motion | 1 | The feasible problem with nearest point `(1,-1)` returns `iteration_limit` |
| Positive row scaling and reversed slab signs | 4 | Equivalent feasible constraints return `iteration_limit` at the original test expectations |
| Fixed coordinates | 1 | The constrained feasible projection returns `iteration_limit` |
| Correlated active rows | 1 | A problem with an independently checked analytical optimum returns `iteration_limit` |

For example, the constraints `x>=1` and `x+y=0` have nearest point `(1,-1)`.
The first implementation does not resolve that control within its fixed
limit. The log records statuses and a traceback; it does not retain a complete
numerical iteration trace establishing the cause of each stall. A finite limit
does not prove these feasible sets empty. Neither the code bins nor the
expected mathematical solutions are widened to obtain a pass.

The overflow traceback points to the saved optical prediction in
`backend/finite_acquisition_protected.py`, line 231 at this exact source.
Warnings are promoted to errors by the recorded command, so the numerical
exception is a software failure. Suppressing the warning would not establish
a valid finite prediction or correct unknown handling.

## What the design proposes

The [method guide](../finite-acquisition-protected.md) explains a local
seven-coordinate minimum-norm projection. It selects an adjacent source code
while keeping other source optical predictions inside their incumbent bins,
then requires a strict decrease in the actual rounded training cost for
acceptance. Its cyclic dual projection, bin witnesses, diagnostics and shared
work caps are prospective engineering choices. Mathematical convergence for an
ideal convex projection does not establish finite-budget success for this
implementation or the nonlinear rounded inverse.

Any correction must preserve this first source, tests, admission, log and
receipt. A separate source/test/plan admission and hash freeze precede its
first execution. Resolve the software failures before attempting the original
24-case recovery protocol; retain all original cases, targets and outcomes.
This page does not report an executed correction.

## Evidence and limits

The [inventory](evidence/acquisition-protected-20261113/manifest.json) provides
SHA-256 hashes and sizes for six verbatim records. Research-checkout paths
inside them are provenance, not runnable paths in this main-based checkout.
The method's runtime, tests and runner are outside this documentation
publication. The copied pre-execution method is text so that its historical
status is not mistaken for the current guide.

No protected full-study row, model result, reference evaluation or saved-ledger
audit is claimed. Earlier [results](finite-acquisition-continuations.md) and
[audit exclusions](../finite-acquisition-saved-audit.md) remain intact. There is
no new workbench/HTTP integration, camera/noise qualification, latency claim,
CAD fit or physical-print acceptance.
