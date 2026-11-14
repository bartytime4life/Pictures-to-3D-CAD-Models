# First full live-restoration result

The first fresh original 24-case study completes at **11/12 matched passes,
exit 1**. Middle PNG reaches zero image residuals but still misses the
fraction target. This is a completed negative recovery result, not an unrun
draft or an all-target success. The [current method](../finite-acquisition-restoration-result.md)
explains the controller and its limits.

Dates here use November 14, 2026 UTC, still November 13 in America/Chicago.
The runtime is separate local research, outside the main-based documentation
checkout and workbench interface.

## Source and first controls

| Stage | Frozen source | First terminal outcome |
| --- | --- | --- |
| Live restoration v1 | `7a126d47607ac759b21b388f3194ae6984546e7b`, 126 inputs | 1,138 tests pass, one fails, 33 subtests pass; exit 1 |
| Additive controls v2 | `e677039274707f8c19e3efaa005f69d74b393868`, 131 inputs | 1,169 tests pass, one predecessor node deselected, 33 subtests pass; exit 0 |
| First full v2 study | Same 131-input freeze | 11/12 matched, all 24 cases retained; exit 1 |

V1's malformed dependent-tight-normal fixture expands a one-row matrix to
three rows but omits the corresponding three-value optical anchor. Shape
validation raises `ValueError: z0 must contain3 coordinates` before the
intended mathematical assertions. Its first log, test, admission, guide and
all 126 source inputs remain unchanged. No v1 full study ran.

The separately admitted equivalent control supplies all three zero anchors
and retains the original dependent-normal obstruction. Only the exact
malformed node is deselected. Its independent replacement and 30 rebound
protocol controls are required; all other selected cases remain. The v2
command selects 34 files. The four backend modules are unchanged from v1.
The arithmetic is `1139 - 1 + 1 + 30 = 1169` selected passing cases.

Both source additions were independently reviewed, committed and combined-
hashed before their first subject execution. The v2 tree is
`a981dc46ede1cb628c4e780c09cef3c57385b8ee`; its 131-path closure is
`33ce7a777b732e6970092c119bb18f7b72e234a2b15ca37c92ba2c9274136576`.
See [v1 freeze](evidence/acquisition-restoration-20261114/v1-freeze.json),
[v2 freeze](evidence/acquisition-restoration-20261114/v2-freeze.json) and
[v2 admission](evidence/acquisition-restoration-20261114/controls-v2-admission.json).

## Original recovery result

All 12 matched and 12 adverse identities, order, numerical targets,
observations, masks, reference orders, kernels/maps, level rules, seeds and
adverse work limits are retained. Full fits are saved before opening truth
dimensions. There are 23 completed rows, 17 fit files and one retained
singular-map exception. One adverse case passes all targets; it is not
included in the 11/12 matched count. Global protocol errors are empty,
source checks pass and interpretation is not withheld.

| Middle-PNG diagnostic | First result |
| --- | --- |
| Training samples | 135, all residuals exactly zero |
| Conditional reserved samples | 34, all residuals exactly zero |
| Full output | 169/169 float32 pixels equal saved reference bytes |
| Source encoded field | 169/169 codes equal saved reference bytes |
| Chord-fraction error | **0.00320694906346225 > 0.002 — fails** |
| Centre error | 0.007574318437095146 pitch — passes |
| Radius error | 0.0016426599167358447 pitch — passes |
| Wrapped-angle error | 0.03695307004350863 degrees — passes |
| Conditional reserved-dimension error | 0.009019052130506466 pitch — passes |
| Sampled bidirectional boundary error | 0.005931632881079452 pitch — passes |
| Completed-search linkage | `poll_resolution`, no exhaustion; ties retained |
| Full-fit charged work | 992 evaluations / 135,369 cells / 25,569,832 stages |

Reserved residual checks are conditional because observed initialization used
those intensities. Boundary error is a sampled diagnostic, not a continuous
Hausdorff guarantee. Zero objective value does not establish unique geometry,
observation rank, a global-search certificate or unknown-camera accuracy.

One generic live episode makes two actual trials. Anchor cost
`0.302031169350812` rises to `0.40923713513984694` at inward `p1`, which is
rejected. Corrected `p2` costs `0.0` and is strictly accepted against the
anchor. Its actual source codes change only at source 62. All raw source
bands pass; source 109 still misses storage erosion. No reference geometry,
case name or source-62 condition selects these proposals.

## Recorded execution

These are historical commands from the exact separate frozen research
checkout, not additional commands available in main. The full selected
control commands are retained verbatim in the
[v1 launch](evidence/acquisition-restoration-20261114/v1-first-tests-launch.json)
and [v2 launch](evidence/acquisition-restoration-20261114/v2-first-tests-launch.json).
Do not overwrite their first destinations or rerun them as documentation QA.

```bash
set -o pipefail
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python studies/verification/finite-acquisition-recovery-restoration-controls-v2.py --output-dir .local/verification/finite-acquisition-recovery-restoration-controls-v2-first 2>&1 | tee .local/verification/finite-acquisition-recovery-restoration-controls-v2-first.log
```

Python 3.12.3 and NumPy 2.5.4 execute the study. Native sessions 51215
(v1 controls), 39267 (v2 controls) and 28887 (full study) each retain their
initial result, observations and terminal exit, with attempt 1 and no restart.
Their respective exits are 1, 0 and 1. The
[full terminal receipt](evidence/acquisition-restoration-20261114/v2-first-full-terminal-receipt.json)
binds the complete report, log, launch, terminal record and freeze.

The [unaltered first report](evidence/acquisition-restoration-20261114/report.json)
is 264,057 bytes, SHA-256
`4eadc2057ded427a4727cb2e14cae0aac153907fd511252423529dcd612fc982`.
All 131 governing source bytes/modes and 106 raw artifact hashes are checked.
Raw artifacts and full candidate ledgers remain local; paths inside copied
records refer to that research checkout.

## Saved-only reviews and first auditor failures

| Review | Completed saved checks | Scope |
| --- | --- | --- |
| Mathematical v3 | 29,022, zero failures | Saved KKT/Gram/row-space identities, inward interval, nearest gates, stage hashes, residual/cost arithmetic and charges |
| Accounting | 19,362, zero inconsistencies | Shared ledger, captures, stage/code records, completion linkage and source/artifact bindings |
| Provenance supplement | 620, zero inconsistencies | First attempts, native chain, predecessor failure and 131-source closure |
| Record/lifecycle | 1,333, zero failures | All case identities, outcomes, work limits, nested labels and retained evidence |

The mathematical auditor's first attempt retains one metadata-comparison
assertion failure after 28,887 checks. Its second attempt retains a KeyError
on an omitted optional metadata key after nine checks. V3 handles that
optional field correctly, retaining source fingerprints, committed Git-blob
verification and every mathematical check. No scientific source or result
was changed to repair these auditors. All three scripts, receipts and logs
are retained in the [mathematical audit manifest](evidence/acquisition-restoration-20261114/math-manifest-v1.json).

These checks are independent readings of saved records, not independent
forward/reference recomputation, new experiments or a qualified public
auditor. No subject imports, model calls, new points or solves occur during
those reviews. The separate [identification check](evidence/acquisition-restoration-20261114/identification-v1.json)
compares saved bytes and ten distinct code-equivalent parameter witnesses;
their extent is not a feasible-set or confidence bound.

## Retained packages and remaining work

The [archive readback](evidence/acquisition-restoration-20261114/archive-readback.json)
verifies ZIP CRCs and member hashes/sizes:

| Local package | Bytes / members | SHA-256 |
| --- | --- | --- |
| Source ZIP | 832,932 / 132 | `4a4c8c4738a5375a6c27dcae805f858d33f9202f80253e13f9203299011c6bea` |
| Complete first ZIP | 42,357,190 / 138 | `f9569d7313f69a101de6aea3391e9f4c906fdf58fab4858b890ee592a92f0597` |

The complete ZIP retains the first raw results and nested predecessor
archive. Later saved audits remain separate; they do not rewrite that first
package. The [publication manifest](evidence/acquisition-restoration-20261114/manifest.json)
lists verbatim copies and exclusions. Runtime, scientific tests, full raw
arrays and ZIP payloads are not published by this documentation change.

The earlier five full-protocol failures remain unchanged; this sixth complete
protocol also fails. Next work concerns quantized geometry identifiability
and genuinely independent dimensional evidence, alongside the unmet
acceptance target. No impossibility proof, valid interval inclusion model,
main integration, real-camera qualification, installed-machine behavior,
native slicer import, physical fit, strength or printing result is supplied.
