# Saved recovery archives and proposed paired audit

The [completed recovery record](validation/finite-acquisition-recovery.md)
retains the original 4/12 and predictor 9/12 matched results. Both full
24-case protocols failed. Their complete archives have now been packaged and
read back locally. A second, paired auditor has been authored, but **has not
executed**. Packaging integrity and an audit design are separate from an
independent scientific result.

This main-based documentation contains the plans, source-file hashes and
packaging receipt linked below. It does not contain the candidate modules,
the new auditor, or either complete recovery ZIP. Paths inside those records
refer to the separate local research checkout, not runnable paths in main.

## Complete local archive inventory

| Recorded experiment | Complete ZIP bytes | Members | SHA-256 |
| --- | --- | --- | --- |
| Original, source `7ec6803` | 27,710,505 | 114 | `e25fe8a0ca8675daafed1b0b577de1d68f4d42e21bf91ee3ba72d43fcb98e724` |
| Predictor, source `e6e2c2` | 8,428,126 | 113 | `7372f87859538dc675dba6f35b4c8e9e141893c312f32ccb0e9fd9473f886119` |

The [readback receipt](validation/evidence/acquisition-coupled-authoring-20261113/archive-readback.json)
records successful comparison of every decoded member's hash and size. This
checks the packaged data against its manifests; it does not verify the forward
model or restore discarded precision. The predictor archive retains all 24
rows, phase ledgers and arrays, its exact 60-file source snapshot, freeze,
first test/study logs and terminal receipt. The original archive and first
failed audit remain unchanged. Publication of these complete archives remains
separate from this documentation update.

## First audit and missing precision

The original auditor executed 5,740,807 checks and exited 1 with 14 failures.
Every failure concerns the pre-cast GL64/96 area-order difference for a
staged/PNG row. The runner computed that difference before float32 storage;
the saved arrays cannot recover those discarded bits. Preserve the reported
reference gate, but mark its missing independent verification explicitly.
Changing a tolerance or comparing a different rounded quantity cannot supply
the missing evidence.

The first auditor does not understand the predictor's composite phase ledger.
Its result therefore does not independently audit the predictor continuation.

## Proposed paired audit

The [unexecuted audit admission](validation/evidence/acquisition-coupled-authoring-20261113/paired-audit-admission.json)
pins both reports, both recorded-source ZIPs and the first failed audit. The
proposed standard-library auditor reads saved data only, without NumPy,
backend, optimizer or reference-generator imports. Its intended scope includes:

- All 48 recorded rows, artifact/source hashes, paired capture identity,
  observed inputs, seeds, bounds and training/reserved-query splits.
- Candidate prediction/residual/cost arithmetic, cache/work histories,
  resource charges and local-status consistency within each recorded phase.
- Predictor quarter quotas, proposal selection, fallback, seven-coordinate
  warm start, phase hashes, selected index space and completion withholding.
- Saved geometry/dimension errors, conditional reserved-residual maxima,
  target arithmetic and population counts.

The proposed precision policy requests 24 pre-cast comparisons per run. Ten
smooth rows per run retain the needed precision; 14 rounded rows per run do
not. **28 unverified comparisons are therefore expected**, not an observed
audit result. Rounded stored-array differences are a separate check.

| Proposed audit outcome | Exit | Meaning |
| --- | --- | --- |
| `inconsistent` | 1 | At least one implemented saved-record check disagrees |
| `consistent_with_unverified_records` | 1 | No implemented inconsistency, but required comparisons remain unverified |
| Fully verified implemented scope | 0 | No implemented inconsistency or required unverified comparison; not expected for these historical captures |

Invented controls for malformed JSON/ZIP/NPY inputs, phase and work-accounting
tampering, precision gaps and output safety are authored but unrun. The
[authoring inventory](validation/evidence/acquisition-coupled-authoring-20261113/manifest.json)
identifies their exact snapshot. No test pass or audit count is inferred from
static inspection.

## Limits and next evidence

Even the proposed audit does not independently recompute forward/reserved
predictions, sampled boundary discrepancy, Jacobians, SVD/rank, brightness
optimality or stopping calculus. It covers the original and predictor schemas,
not the newer coupled strategy. Reserved pixels influenced initialization,
so their residuals remain conditional diagnostics.

The [coupled continuation proposal](finite-acquisition-coupled.md) preserves
float64 coverage before rounded reference storage in future captures, while
retaining the original reference values and thresholds. This cannot repair
old archives. The complete source/test/plan closure must be committed and
hashed before first execution, and first outcomes must be retained. No camera,
installed-tool, interactive-latency or physical-print qualification follows.
