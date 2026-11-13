# Projective-node arithmetic: complete original diagnostic

The first frozen-source execution **exited 0** and retains all 26 scenes:
two post-hoc known controls and 24 new declared controls. Read the
[mathematics](../../../docs/finite-normal-oracle-conditioning.md) and
[complete outcome and remaining limits](../../../docs/validation/finite-normal-oracle-conditioning.md).
The original V2 study and its optimistic reference-error allowance remain intact.

The [plan](../../finite-normal-oracle-conditioning-v1.json) predates every
diagnostic node/reference evaluation. The
[readable index](../../results/finite-normal-oracle-conditioning-v1-summary.json)
binds all 35 compressed/decoded artifacts, source hashes, work counts and
independent saved-data reviews. The
[complete report](../../results/finite-normal-oracle-conditioning-v1.json.gz)
decodes to 4,970,145 bytes, SHA-256
`cd0c2eac7b7062d4cda480c995094293fc9b5991fb55b4c2a86e735aa92bca93`.
Gzip uses level 9, zero mtime and no embedded filename. Every scene, fixed panel,
newly generated hexadecimal rule array, precision result and signed error is
retained. This archive contains synthetic and software evidence, with no photos.

Provenance `.py.txt` files preserve their original local invocation locations.
They are historical execution records, not additional supported replay CLIs.
The public saved-data auditor is independently implemented and included in the
artifact manifest; it imports neither the numerical runner nor production code.

## Verify and audit saved values without model calls

Run from this source revision's repository root with a fresh review directory:

```bash
mkdir -p .local/verification/conditioning-review
python3 - <<'PY'
from pathlib import Path
import gzip
import hashlib
import json

index = json.loads(Path("studies/results/finite-normal-oracle-conditioning-v1-summary.json").read_text())
for item in index["artifacts"]:
    saved = Path(item["path"]).read_bytes()
    assert len(saved) == item["bytes"]
    assert hashlib.sha256(saved).hexdigest() == item["sha256"]
    decoded = gzip.decompress(saved) if item["encoding"] == "gzip" else saved
    assert len(decoded) == item["decoded_bytes"]
    assert hashlib.sha256(decoded).hexdigest() == item["decoded_sha256"]
    if item["kind"] == "complete_original_canonical_diagnostic":
        with Path(".local/verification/conditioning-review/canonical.json").open("xb") as handle:
            handle.write(decoded)
print("All compressed and decoded artifact hashes verified")
PY
python3 studies/verification/finite-normal-oracle-conditioning-report-audit-v1.py \
  --input .local/verification/conditioning-review/canonical.json \
  --input-sha256 cd0c2eac7b7062d4cda480c995094293fc9b5991fb55b4c2a86e735aa92bca93 \
  --output .local/verification/conditioning-review/saved-audit.json
```

The auditor uses standard-library arithmetic on saved values only. It checks
source/identity bindings, partitions, rule hashes, panel sums, work counts and
all comparison flags. It does not generate rules, evaluate density nodes,
exponentials, π, scientific references or physical models. Its pass does not
certify arithmetic bounds, quadrature coefficients or truncation error.

Both public scripts refuse existing output paths, including dangling symlinks,
and require an existing parent directory. Their exit 0 requires the respective
saved audit or diagnostic criteria; exit 1 retains a failed result; exit 2
rejects invalid arguments or destinations. Help modes are read-only.

## Explicit new numerical execution

This separate command performs a new complete arithmetic diagnostic. It
requires the workbench environment and a fresh destination:

```bash
.venv/bin/python -W error::RuntimeWarning \
  studies/verification/finite-normal-oracle-conditioning-v1.py \
  --output .local/verification/conditioning-review/new-study.json
```

It reevaluates the declared 2 post-hoc and 24 prospective-plan scenes with the
same fixed partitions and criteria. It makes no production derivative, inverse,
positive-area, renderer or photo-analysis call. Preserve the first original
result; a subsequent execution cannot replace it or make known cases unseen.
The portable saved audit above needs no new numerical execution.
