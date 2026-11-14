# Paired literal PNG test: completed negative result

The first actual paired test **reproduces the incumbent exactly and rejects
the predetermined candidate on higher training cost**. It completes at
`complete_no_improvement`, exit 1, with `paired_probe_complete=true`,
`baseline_qualified=true` and `protocol_failure=false`.

| Observation | First retained result |
| --- | --- |
| Replayed incumbent cost | 0.302031169350812 |
| Candidate cost | 0.40923713513984694 |
| Cost increase | 0.10720596578903496 |
| Exact baseline checks | 9 of 9 pass |
| Selected source cell 62 | Code 93 to intended 92 |
| Collateral source cell 33 | Protected code 106 to 105 |
| Selected controls | 162 pass in 0.22 seconds, exit 0 |
| Independent saved mathematical audit | 841 checks pass |
| Full recovery | Not rerun; original 11/12 result remains failed |

This is a research result, not a main-branch runtime, HTTP or UI feature. See
the [method and interpretation](../finite-acquisition-inward-literal.md) and
[current source status](../project-status.md). Dates below use UTC; the first
pair completed on November 14, 2026 UTC, still November 13 in America/Chicago.

## Exact source and saved-input bindings

The separate research source is
`98fb1aeeb54bd13d3c4dd324f323736109d17d0d`, tree
`40f54d13a2e5bdc7723f2a59ae86589dea6e1cff`. Its four new governing files are:

| Frozen research file | SHA-256 |
| --- | --- |
| `studies/verification/finite-acquisition-inward-literal-v1.py` | `841cb7655ab52313c13a168d70d9cb81fd17d81ebc164e55766a99f480e9f01a` |
| `tests/test_finite_acquisition_inward_literal.py` | `65760a51b4b7deb515ba70b176a4ce8e123f053f581238abf84d79071ac9b87b` |
| `studies/finite-acquisition-inward-literal-v1.json` | `20a3ddf3cfa10ace6685155277c11da7c9ead021e1f6f6264082282ab98973ed` |
| `docs/finite-acquisition-inward-literal.md` | `2daa126f513b16356ebc265a815ba0a1b40387082a97b5182a2e9306b4fa4b17` |

Those paths identify the research checkout. Its frozen prospective guide is
published as [verbatim text](evidence/acquisition-inward-literal-20261113/literal-prospective-method.txt);
the current main-based method guide is a later account, not a replacement
for that governing input. All 108 preceding inputs remain unchanged in the
112-file [combined freeze](evidence/acquisition-inward-literal-20261113/literal-freeze.json).
Static reviews preceded the freeze and first subject execution.

The [full first output](evidence/acquisition-inward-literal-20261113/literal-first.json)
is 324,890 bytes, SHA-256
`e09b56e646459f90b0371a9ec5bacaecbaf7fc5146c577687b5f7a8cd6e22307`.
It retains all 24 inventory rows, 17 fit-file contexts, 16 without a qualifying
certificate and the single eligible pair. Both forwards' raw coverage,
seven staged arrays, training predictions, residuals, costs and work metadata
are retained. The runner verifies all 112 source and 106 original artifact
bindings before and after, and changes no original outcome.

The previous full report, negative corner census and inward diagnostic keep
their own hashes and admissions. This new freeze does not retroactively bind
older experiments to new source. No new point, QP, event ranking, alternate
corner, brightness profile, preparation, reserved scoring or reference call
occurs in the actual paired probe.

## Recorded commands and terminal results

These are the exact historical commands in the separate frozen research
checkout. The runner and tests are absent from this main-based source. They
are provenance, not setup instructions or commands executed for this
documentation refresh. First-output destinations and governing inputs remain
immutable; later experiments need their own admission and fresh paths.

```bash
set -o pipefail
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -W error::RuntimeWarning -m pytest -q tests/test_finite_acquisition_inward_literal.py tests/test_finite_acquisition_inward.py tests/test_finite_acquisition_physical_rounding.py 2>&1 | tee .local/verification/finite-acquisition-inward-literal-v1-first-tests.log
```

The selected suite passes **162 tests in 0.22 seconds**: 59 new cases and
103 unchanged preceding cases. The new controls include one actual one-cell
zero-image PNG acquisition-operator check; the rest exercise mathematical,
mocked-forward and protocol behavior. This selection is neither wholly
saved-only arithmetic nor an application-wide regression run.

```bash
set -o pipefail
.venv/bin/python studies/verification/finite-acquisition-inward-literal-v1.py --output .local/verification/finite-acquisition-inward-literal-v1-first.json 2>&1 | tee .local/verification/finite-acquisition-inward-literal-v1-first.log
```

The actual probe uses Python 3.12.3 and NumPy 2.5.4. The
[controls terminal receipt](evidence/acquisition-inward-literal-20261113/literal-first-tests-terminal-receipt.json)
records exit 0; the [paired terminal receipt](evidence/acquisition-inward-literal-20261113/literal-first-terminal-receipt.json)
records exit 1. Both finish on their initial native tool calls, with no native
session ID and no restart. The complete pair has zero protocol errors and
zero opaque failed work. Its higher cost is a valid negative result.

## Work and actual code diagnostics

| Ledger quantity | Evaluations | Cell units | Stage units |
| --- | --- | --- | --- |
| Original saved work | 990 | 135,031 | 54,520,546 |
| Entire pair reserved and charged before first call | 2 | 338 | 10,478 |
| Aggregate | 992 | 135,369 | 54,531,024 |
| Unchanged original caps | 2,048 | 1,000,000 | 100,000,000 |

Two logical forwards complete two aperture and two acquisition calls. The
caller accounts for 169 cells per aperture attempt; that API's reported cell
counter is absent, not a measured zero. Each acquisition reports 5,239 stage
units. Pair charges are not refunded on failures. No new full recovery or
runtime-integrated shared ledger is implied by this standalone probe.

Only source cells 33 and 62 change encoded codes. Cell 62 reaches code 92 but
misses its deliberately narrowed central-half proposal slice. Cell 33 leaves
its protected code 106. The independent saved audit finds all 169 local
optical predictions inside their declared bands, versus 167 actual optical
values. The [method's comparison](../finite-acquisition-inward-literal.md#why-local-feasibility-did-not-transfer)
reports the actual-minus-local defects. Their causes are not individually
isolated. Neither a target-code hit nor represented feasibility overrides
strict actual-cost acceptance.

## Independent checks and retained packages

The [first mathematical receipt](evidence/acquisition-inward-literal-20261113/math-audit-v1-receipt.json)
passes **841 saved-data checks**, with zero discrepancies. Its
[auditor source](evidence/acquisition-inward-literal-20261113/math-audit-v1.py.txt)
and [interpretation note](evidence/acquisition-inward-literal-20261113/math-interpretation-v1.txt)
are copied verbatim. It reconstructs saved residual/cost/hash facts, baseline
qualifications, optical-band comparisons and work bindings without importing
the subject, evaluating a model, producing a point or solving a new system.

A separate [record-consistency receipt](evidence/acquisition-inward-literal-20261113/ux-audit-v1-receipt.json)
and [native terminal supplement](evidence/acquisition-inward-literal-20261113/ux-audit-v1-native-supplement.json)
agree. That audit's large check count mainly enumerates finite JSON scalars;
it does not represent that many independent scientific assertions or trials.
These audits check saved records, not an independent forward model.

The [package readback](evidence/acquisition-inward-literal-20261113/literal-archive-readback.json)
verifies the local 113-member source ZIP, SHA-256
`9975f48280ae60ccc7e660aa2d0d24ffb52cfa18665d89fd52548523b8d78ddf`,
and 13-member complete ZIP, SHA-256
`00e05652a1ab037b44f9d502cfface4bfa4d677dc69beac6ab2f3ee349b8cd7f`.
The complete ZIP retains the first pair and the unchanged previous complete
archive. Later independent audits remain separately saved; they do not alter
that first package.

The [publication inventory](evidence/acquisition-inward-literal-20261113/manifest.json)
contains 19 verbatim records plus its manifest, including the complete first
paired JSON rather than a derived extract. Research runtime/tests, full source
payload, original raw recovery artifacts, full preceding diagnostics and
local ZIPs are outside this publication. The copied prospective text and
absolute paths are historical provenance, not runnable paths in main.

## What remains unresolved

The represented local obstruction is resolved for the earlier inward point;
actual nonlinear band preservation and cost improvement fail for the selected
candidate. The original 11/12 full recovery, first failures and earlier
0/128 corner census remain unchanged. A future nonlinear correction is
unimplemented. Runtime integration, an unchanged full 24-case acceptance run,
independent forward/rank qualification, real-camera measurements, installed
behavior and physical CAD/print acceptance remain separate work.
