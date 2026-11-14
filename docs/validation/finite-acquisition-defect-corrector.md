# Observed-defect correction: first actual training improvement

One fixed correction reduces cost **0.302031169350812 to 0.0** at all
135 saved training queries in the supplied synthetic PNG context. The
incumbent replay qualifies on all nine exact checks. Only source cell 62
changes encoded value, **93 to 92**; protected cell 33 stays at 106.
Status is `literal_training_improvement`, passed, terminal exit 0, with no
protocol failure or source/input changes.

This is a paired training result, not a new full-recovery score. No reserved
scoring, reference generation, fitter run, new Jacobian or new inequality QP
is performed. The original complete 24-case recovery remains failed at 11/12
matched passes. Zero quantized training error does not establish unique or
true geometry, camera accuracy, a physical tolerance or workbench integration.

## Keep the three tuples distinct

| Tuple | Role | Actual training cost | Code changes from incumbent |
| --- | --- | --- | --- |
| Accepted `p0` | Sole acceptance comparator; replay qualifies exactly | 0.302031169350812 | None |
| Rejected `p1` | Saved optical anchor only | 0.40923713513984694 | 33: 106→105; 62: 93→92 |
| New nearest tuple | Accepted for this training comparison | 0.0 | Only 62: 93→92 |

The [negative literal result](finite-acquisition-inward-literal.md) is
unchanged. The [new method](../finite-acquisition-defect-corrector.md)
interpolates that rejected optical field, retains the old local matrix and
original bounds, and makes one equality-restoration step. No retrospective
best-point choice, alternate corner or retry selects the outcome.

## Source and complete first-record binding

Research commit `d986f1f2db12791b96aad21dcc4f1e7977029c40` has tree
`83e1635eb176c0776ec62ee6f442abb85b2e4ed7`.
All preceding 112 inputs retain their bytes and modes. Four new files make
the independently reviewed **116-input closure**, frozen before any new
subject import, collection, test, solve, point or model evaluation.

| New governing file in research | SHA-256 |
| --- | --- |
| `studies/verification/finite-acquisition-defect-corrector-v1.py` | `b2c2651f466588a19e8bfd7a77f1a56c8bd8093a3b87d2795924a46e32ffaf7b` |
| `tests/test_finite_acquisition_defect_corrector.py` | `5e359e5dd14f999d8a72ef4867c59185258672a6bb6941df4d0e3ff0cb65dad6` |
| `studies/finite-acquisition-defect-corrector-v1.json` | `b6f1d5dcc59032d7cfbde196adae76d1fb82d76ff802b252c48ed2686b74439a` |
| `docs/finite-acquisition-defect-corrector.md` | `fdc20be6b4d7cf9594178b70665569091a65e8f86b24ece972ecf7e83fc3900e` |

The [freeze](evidence/acquisition-defect-corrector-20261114/corrector-freeze.json)
records closure SHA-256
`f52f39e6fdc96092a1197a36e9ad0c2fbb8df60e0f685714eff84c68d3b2ace5`:
SHA-256 of compact ASCII JSON sorted `[path, Git mode, SHA-256]` rows,
without a trailing newline. The
[prospective guide](evidence/acquisition-defect-corrector-20261114/corrector-prospective-method.txt)
remains verbatim; the later reader-facing guide is outside that frozen closure.

The **complete first output**, not an extract, is
[corrector-first.json](evidence/acquisition-defect-corrector-20261114/corrector-first.json):
1,826,974 bytes, SHA-256
`1738ab1ef1e5784dac9381c558a8f0947fbcf15b72208e432e7c8785f312c34d`.
It retains the exact proof, correction inputs, target/weights, raw coverage,
all seven stages of both forwards, predictions/residuals/costs, code changes,
work and complete inventory and binding checks.

All **116 source** and **114 saved bindings**, including **106 original
artifacts**, agree before and after. Inventory remains 24 rows, 17 fits,
16 without a qualifying certificate and one eligible context. Those rows
are retained inventory, not 24 newly executed fits.

## Recorded commands and first results

These commands record the frozen research checkout and fresh destinations.
The runner and tests are absent from main. Do not use these commands to
overwrite first records or rerun the scientific result.

Selected controls:

~~~bash
set -o pipefail
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -W error::RuntimeWarning -m pytest -q tests/test_finite_acquisition_defect_corrector.py tests/test_finite_acquisition_inward_literal.py tests/test_finite_acquisition_inward.py tests/test_finite_acquisition_physical_rounding.py 2>&1 | tee .local/verification/finite-acquisition-defect-corrector-v1-first-tests.log
~~~

The first [log](evidence/acquisition-defect-corrector-20261114/corrector-first-tests.log)
records **220 passed in 0.30 seconds**, exit 0 on the initial call, no
native session ID. No collection or test rerun followed. Frozen sources
contain 58 new cases plus predecessor suites of 59, 54 and 49 cases:
**58 + 162 = 220**. The prospective review receipt's 218 total is an
addition error, retained unchanged and corrected explicitly in the
[native controls receipt](evidence/acquisition-defect-corrector-20261114/corrector-first-tests-receipt.json).
One inherited one-cell PNG control invokes the real operator; the new controls
use invented arithmetic and mocked routing, separately from the saved-case run.

First saved correction and actual pair:

~~~bash
set -o pipefail
.venv/bin/python studies/verification/finite-acquisition-defect-corrector-v1.py --output .local/verification/finite-acquisition-defect-corrector-v1-first.json 2>&1 | tee .local/verification/finite-acquisition-defect-corrector-v1-first.log
~~~

The [launch](evidence/acquisition-defect-corrector-20261114/corrector-first-native-launch.json)
returns native session **63113**. Polling that same handle returns terminal
exit **0**, `literal_training_improvement`. The
[terminal receipt](evidence/acquisition-defect-corrector-20261114/corrector-first-terminal-receipt.json)
retains both observations, file hashes, attempt 1 and zero reruns.
Current direct-operator versions are Python 3.12.3, NumPy 2.5.4 and binary64
radix 2, precision 53, nearest rounding. Prior versions stay historical.

## Mathematical and actual results

Five independent old tight normals are retained at rows **67, 123, 124,
188 and 219**. One exact Gram solve produces one rational correction and
one nearest binary64 physical tuple:

~~~text
[5.870124148570346, 6.117573300926215, 3.411642659916736,
 0.16679305093653776, 1.1306449527409792,
 21.9872555740398, 218.25931253499678]
~~~

Equality and row-space identities prove minimum norm for the **selected
equality system only**. They do not prove full inequality-QP optimality or
nonlinear convergence. The old KKT witness qualifies only for its old model.
All five post-construction gates pass: physical limits, exact centered
membership, membership of computed coordinates, computed source/domain
checks and selected-band arithmetic floor. The exact storage guard `2^-12`
does not bound geometry-linearization error or an unknown camera.

Both forwards use identical saved acquisition inputs and 135 ordered queries.
The incumbent matches its archived input hash, optical/encoded/decoded
snapshots, prediction, raw/weighted residuals and cost. Corrected predictions
equal every target; all raw and weighted residuals and the guarded
`hypot`-squared cost are zero. Strict acceptance compares with `p0`, not
merely rejected `p1`. Code diagnostics do not decide acceptance.

Each retained stage sequence is coverage, source linear, optical linear,
encoded, decoded linear, rectified and final. Raw bytes, shapes, dtypes and
hashes are included. Multiple geometric tuples can share quantized training
values; this equality does not establish rank or unique geometry.

All **169 actual optical values pass the original raw source bands**. The
local model passes all storage-eroded bands; the actual pipeline passes
**168 of 169 storage-eroded bands**. At source 109, actual raw lower slack
is `0.00022125244140625`, below the `0.000244140625` storage guard, while
its protected code 117 is preserved. The largest absolute actual-minus-centered
model discrepancy is `0.00012837167371415603`, at source 80. This observed
comparison does not establish a uniform nonlinear remainder bound. The
eroded-band diagnostic is separate from strict actual-cost acceptance.

## Work and remaining scope

| Work | Evaluations | Cell units | Stage units |
| --- | --- | --- | --- |
| Prior completed work, including rejected pair | 992 | 135,369 | 54,531,024 |
| Whole new reservation, held and charged | 2 | 338 | 1,942,766 |
| New aggregate | 994 | 135,707 | 56,473,790 |
| Original caps | 2,048 | 1,000,000 | 100,000,000 |

Whole prepayment includes **1,932,288 mathematical stage units** and the
pair's 10,478 stage units, before KKT or construction arithmetic. The pair
ledger is a view of that prepaid work, not another debit. Two coverage and
two acquisition attempts complete, with no opaque failed work. Tariffs are
accounting units, not elapsed time or a complexity theorem.

Fitter integration, a separately admitted complete original 24-case protocol,
reserved checks, rank/forward qualification and real captures remain future
work. No new main UI/HTTP control, installation, deployment, native slicing
or physical CAD/print acceptance is added by this record.

## Later saved-only audits and packaging

Independent reviews use retained arrays and arithmetic without another subject
import, solve, optimizer or optical call. The record-consistency review
passes **433 checks**, with a separate **eight-check native supplement**.
The independent source/provenance review passes **40,227 checks**, including
source bytes/modes, stage bytes, residual/cost arithmetic, exact saved algebra
and work accounting. Counts describe implemented checks, not independent
experiments or geometry qualification. Their scripts and receipts are listed
separately in the
[manifest](evidence/acquisition-defect-corrector-20261114/manifest.json).
The independent mathematical audit passes **10,560 checks**, reconstructing
352 original and 14 physical rows, the old KKT witness, rank-five basis,
Gram/RHS/row-space identities, pre-slacks, nearest tuple and all final gates.
It also verifies actual raw-band membership and preserves the source-109
storage-margin limitation above. No new system is solved or model evaluated.

The [archive readback](evidence/acquisition-defect-corrector-20261114/corrector-archive-readback.json)
verifies the local 117-member source ZIP and 15-member complete first-record
ZIP, including the prior literal archive. Source bytes, hashes and Git modes,
and complete-archive member bytes/hashes agree. Later audits do not amend the
first archive. ZIPs and research runtime stay outside documentation publication;
their bindings are distinct from the verbatim records published here.
