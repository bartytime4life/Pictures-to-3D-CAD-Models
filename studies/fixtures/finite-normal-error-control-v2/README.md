# Finite-normal error control: complete original V2 archive

The single frozen-source canonical execution **exited 0** and retains all
417 scenes, 4,832 queries and 72 positive-area checks. Read the
[qualification and remaining oracle limit](../../../docs/validation/finite-normal-error-control.md)
and [mathematics](../../../docs/finite-normal-error-control.md). Original V1
failures and source snapshots remain in their separate archive.

The [main plan](../../finite-normal-error-control-v2.json) predates every V2
candidate/oracle call. Its [software addendum](../../finite-normal-error-control-inverse-addendum-v2.json)
preserves the subsequently found whitening-inverse issue before repaired calls.
The [readable index](../../results/finite-normal-error-control-v2-summary.json)
binds all source hashes and compressed/decoded artifacts. The
[complete report](../../results/finite-normal-error-control-v2.json.gz) decodes to
128,302,342 bytes, SHA-256
`603a39888033cb6db21eb164fbc517ca3cafba942d30fe09321d0028aafecf6e`.
Gzip uses level 9, zero mtime and no embedded filename. Compression removes no
scene, query, oracle panel, work count, area mean or failed/preflight receipt.

This archive contains synthetic geometry and software evidence. The four
post-hoc Decimal identity evaluations are separate from the canonical protocol;
they confirm the two original candidate controls and expose an optimistic oracle
allowance. No private photograph, optimizer replay or physical accuracy result
is included. Provenance `.py.txt` archives retain their original invocation
locations; they are not additional supported replay CLIs.

## Verify saved evidence without model calls

Run from this source revision's repository root, using a fresh review directory:

```bash
mkdir -p .local/verification/normal-error-review
python3 - <<'PY'
from pathlib import Path
import gzip
import hashlib
import json

index = json.loads(Path("studies/results/finite-normal-error-control-v2-summary.json").read_text())
for item in index["artifacts"]:
    saved = Path(item["path"]).read_bytes()
    assert len(saved) == item["bytes"]
    assert hashlib.sha256(saved).hexdigest() == item["sha256"]
    decoded = gzip.decompress(saved) if item["encoding"] == "gzip" else saved
    assert len(decoded) == item["decoded_bytes"]
    assert hashlib.sha256(decoded).hexdigest() == item["decoded_sha256"]
    if item["kind"] == "complete_original_canonical_report":
        with Path(".local/verification/normal-error-review/canonical.json").open("xb") as handle:
            handle.write(decoded)
print("All compressed and decoded artifact hashes verified")
PY
python3 studies/verification/finite-normal-error-control-report-audit-v2.py \
  --input .local/verification/normal-error-review/canonical.json \
  --input-sha256 603a39888033cb6db21eb164fbc517ca3cafba942d30fe09321d0028aafecf6e \
  --expected-api-sha256 5038ebe359ae0b3e4e158273ae145a0991feb93258fe723eca942ac49017425f \
  --expected-test-sha256 e4e278ae3077eb1bb6096bb25e557168f1f4baf8b590ee7a679717c6621c6c16 \
  --output .local/verification/normal-error-review/saved-audit.json
```

The standard-library auditor makes no backend or NumPy import. It refuses an
existing output, including a dangling symlink, and requires its parent. Exit 0
means saved arithmetic and bindings reconcile; it does not certify numerical
estimates, fix an oracle allowance or qualify a physical acquisition. Its own
`--help` and the scientific runner's `--help` are read-only parser checks.

## Explicit new numerical execution

The following runs a new complete scientific comparison, rather than reviewing
the saved result. It requires the workbench environment and a fresh destination:

```bash
.venv/bin/python -W error::RuntimeWarning \
  studies/verification/finite-normal-error-control-v2.py \
  --output .local/verification/normal-error-review/new-study.json
```

It reevaluates 337 post-hoc synthetic regression scenes and 80 prospective-plan
scenes under the pinned source, with no optimizer or automatic app integration.
Exit 0 requires the full frozen criteria; exit 1 preserves a scientific/protocol
failure; exit 2 refuses invalid CLI/input/fresh-destination conditions. Never
overwrite the original result or tune its thresholds to replace an outcome.

The older V1 auditor binds the earlier operator bytes. Use a checkout at
`d40502fed3de93989c73d4c8cf614f6f6b6d7e45` for its original archive commands;
do not rebind its report to this changed operator.
