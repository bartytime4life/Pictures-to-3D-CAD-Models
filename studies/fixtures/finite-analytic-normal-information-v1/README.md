# Analytic-normal residual information: complete original archive

The first frozen-source execution **exited 0**, with all 12 original records,
578 new derivative comparisons and ten single joint trials retained. Read the
[method](../../../docs/finite-analytic-normal-information.md) and
[complete results and geometric counterexamples](../../../docs/validation/finite-analytic-normal-information.md).
The original failed residual protocol and its unknown finite-difference normal
columns remain unchanged. No new fit-pass count or automatic correction follows.

The [frozen plan](../../finite-analytic-normal-information-v1.json) predates all
new scientific calculations. The
[readable index](../../results/finite-analytic-normal-information-v1-summary.json)
binds all **36 artifacts**, with compressed and decoded sizes/hashes. The
[complete report](../../results/finite-analytic-normal-information-v1.json.gz)
decodes to 270,836,922 bytes, SHA-256
`11607377de1a98446c07e53be67c01cf669fd99dca6f1ea0abf8284a1a47d387`.
Its gzip bytes have SHA-256
`7ad761e4cb2d86faa29ebad7f8a0696699ea1d37fb435e037a4ce14aa8c07324`.
Compression uses zero mtime and no embedded filename; it removes no row, panel,
old result, work count or precision record. The inputs are public synthetic
fields, with no private photos.

The index also retains the failed first routing-test fixture and its corrected
version. `.py.txt` files preserve historical invocation locations; they are
provenance records, not additional supported replay commands. The public
saved-data auditor below is a separate, portable standard-library CLI.

## Verify and audit saved values without model calls

Run from this source revision's repository root with a fresh review directory:

```bash
mkdir -p .local/verification/analytic-normal-review
python3 - <<'PY'
from pathlib import Path
import gzip
import hashlib
import json

index = json.loads(Path("studies/results/finite-analytic-normal-information-v1-summary.json").read_text())
for item in index["artifacts"]:
    saved = Path(item["path"]).read_bytes()
    assert len(saved) == item["bytes"]
    assert hashlib.sha256(saved).hexdigest() == item["sha256"]
    decoded = gzip.decompress(saved) if item["encoding"] == "gzip" else saved
    assert len(decoded) == item["decoded_bytes"]
    assert hashlib.sha256(decoded).hexdigest() == item["decoded_sha256"]
    if item["kind"] == "complete_original_canonical_report":
        with Path(".local/verification/analytic-normal-review/canonical.json").open("xb") as handle:
            handle.write(decoded)
print("All compressed and decoded artifact hashes verified")
PY
python3 studies/verification/finite-analytic-normal-report-audit-v1.py \
  --input .local/verification/analytic-normal-review/canonical.json \
  --input-sha256 11607377de1a98446c07e53be67c01cf669fd99dca6f1ea0abf8284a1a47d387 \
  --output .local/verification/analytic-normal-review/saved-audit.json
```

This auditor imports no backend or numerical package. It checks complete saved
rows, source bytes, exact error arithmetic, call/work accounting, rank/cutoff
metadata and retained trial decisions. It generates no nodes, references,
derivatives, SVDs or model predictions. A consistent, honestly failed scientific
result can pass an integrity audit; the audit does not certify numerical bounds
or physical accuracy. Independent QR and NumPy-based saved-array reviews have
separate archived scopes.

Both the public auditor and scientific runner refuse existing output paths,
including dangling symlinks, and require an existing parent directory. Their
help modes are read-only. Exit 0 means the respective audit/protocol criteria
pass; exit 1 retains a failed result; exit 2 rejects invalid CLI/destination
arguments. The auditor requires the exact decoded input hash and has an explicit
2 GiB loading cap. Use fresh paths for a repeat review.

## Explicit new numerical execution

This command performs a new complete numerical experiment. It requires the
workbench environment and a fresh destination:

```bash
.venv/bin/python -W error::RuntimeWarning \
  studies/verification/finite-analytic-normal-information-v1.py \
  --output .local/verification/analytic-normal-review/new-study.json
```

It repeats the frozen 15 normal batches/578 queries, independent chord and
elementary references, matrix calculations, and at most ten qualified joint
trial means. It regenerates no baseline, covariance finite difference, inverse
fit, renderer or observation preparation. The ten archived hypotheses and old
six-point control remain post-hoc; the four additional sign/crop controls were
declared before their first evaluations. A new execution cannot replace the
first report or make those cases unseen. Saved review above needs no new
scientific execution.
