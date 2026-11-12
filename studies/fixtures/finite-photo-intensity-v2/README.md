# Paired measured-ring replay evidence

These are source-bound receipts from the archived synthetic rendered fields in
the preceding moment/photo experiments. No new photograph is rendered or traced.
The [plan](../../finite-photo-intensity-v2.json),
[main runner](../../verification/finite-photo-intensity-v2.py),
[canonical result](../../results/finite-photo-intensity-v2.json) and
[validation guide](../../../docs/validation/finite-photo-intensity-v2.md) define
the experiment and its limits.

The [manifest](manifest.json) binds the original 38 source/input files, portable
contract runners, full reports, progress logs and independent audits. The
scientific result retains exit 1: three of twelve declared case/lane records
meet all targets, ten fits complete and two upstream refusals remain. No rows,
criteria, old version 1 results or supplied covariance hypotheses are replaced.

| Receipt | Scope |
| --- | --- |
| [No-fit contracts](no-fit-contracts-v1.json) | 30 actual observation/forward checks and 18 parser/routing/serialization checks; zero inverse optimizers |
| [Actual continuation result](first-fit-failure-result-v1.json), [audit](first-fit-failure-audit-v1.json) | First fit-entry exception injected; nine later real optimizers run; all eleven later parsed rows match canonical except timing; ten continuation assertions pass |
| [Canonical progress](canonical-progress-v1.jsonl), [continuation progress](first-fit-failure-progress-v1.jsonl) | Complete original per-row progress streams, including upstream refusals and the injected failure |
| [Canonical independent audit](canonical-independent-audit-v1.json), [continuation independent audit](continuation-independent-audit-v1.json) | Recalculated target/completion/domain and row-preservation checks on saved reports; no refits |
| [Independent contracts](independent-contracts-v2.json) | Separate unsafe-payload, parser and routing checks with explicit optimizer sentinels; no numerical recovery claim |

Run from the repository root after setup, using fresh output paths in existing
directories. `--help` is read-only for all three runners.

```bash
mkdir -p .local/verification
.venv/bin/python studies/verification/finite-photo-intensity-v2.py --output .local/verification/new-photo-v2.json
.venv/bin/python studies/verification/finite-photo-intensity-v2-contracts-v1.py --output .local/verification/new-photo-v2-contracts.json
.venv/bin/python studies/verification/finite-photo-intensity-v2-continuation-v1.py --canonical studies/results/finite-photo-intensity-v2.json --output .local/verification/new-photo-v2-failure.json --audit .local/verification/new-photo-v2-failure-audit.json
```

The main runner's exit 1 preserves the failed scientific targets. A no-fit or
continuation harness exit 0 means its declared contracts pass, not that all
scientific targets do. The continuation harness performs real fitting and takes
roughly two minutes on the recorded machine; it is not a lightweight check.

Reports retain original local receipt-path labels where present. Their public
byte-identical counterparts and checksums are in this directory and manifest.
Full JSON stdout bodies were verified identical to their saved reports and are
stored once. Earlier local preflight revisions remain preserved locally; they
are not substituted for the final source-bound qualification.

Crop and common-width preparation change together between version 1 and 2.
Held-out pixels are disjoint from fitting cost but influence initialization and
moments. Neither effective covariance is a calibrated PSF; local completion,
small geometry errors and strict JSON do not establish automatic CAD acceptance,
real-camera accuracy, interactive latency or physical fit.
