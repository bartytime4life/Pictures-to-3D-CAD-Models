# Finite-normal derivative: complete original qualification

The original study **exited 1**. It retains all 337 planned scenes and 3,886
queries, including one panel-budget unknown. All independent chord oracles
converge; 3,885 candidate comparisons and 36 positive-area checks pass their
frozen criteria. A resolved compressed-map discrepancy also exceeds the
candidate's error estimate, so this is not uniform absolute accuracy evidence.
Read the [complete result and limits](../../../docs/validation/finite-normal-derivative.md)
and [operator contract](../../../docs/finite-normal-derivative.md).

The [main plan](../../finite-normal-derivative-v1.json) and
[static-review supplement](../../finite-normal-derivative-compressed-chart-v1.json)
predate every new operator/oracle evaluation. The
[runner](../../verification/finite-normal-derivative-v1.py) and
[readable index](../../results/finite-normal-derivative-v1-summary.json)
bind exact sources, settings and all retained results. This archive contains
synthetic inputs and software evidence; no private photograph is included.

## Lossless report and receipts

The [full report](../../results/finite-normal-derivative-v1.json.gz) is a lossless
gzip of 91,924,054 bytes, decoded SHA-256
`d31fcb0436daee9e91bd21d78c1650901916a8c2c77bf6c7e351da61c04e113f`.
It retains every scene, query-role mapping, candidate status/error/work record,
independent source partition, quadrature order, tail bound and positive-area
mean. Compression uses level 9, zero mtime and no embedded filename.

The index manifests compressed and decoded hashes for the canonical preflight,
terminal receipt, stdout/stderr, 94-test focused run, 1,037-test full Python run,
build, runner contracts and saved-data audits. Provenance `.py.txt` files retain
their original invocation locations; use the portable auditor below instead of
renaming them into supported CLIs.

## Verify without a new model call

From the repository root, use a fresh review directory:

```bash
mkdir -p .local/verification/normal-review
python3 - <<'PY'
from pathlib import Path
import gzip
import hashlib
import json

index = json.loads(Path("studies/results/finite-normal-derivative-v1-summary.json").read_text())
for item in index["artifacts"]:
    saved = Path(item["path"]).read_bytes()
    assert len(saved) == item["bytes"]
    assert hashlib.sha256(saved).hexdigest() == item["sha256"]
    decoded = gzip.decompress(saved) if item["encoding"] == "gzip" else saved
    assert len(decoded) == item["decoded_bytes"]
    assert hashlib.sha256(decoded).hexdigest() == item["decoded_sha256"]
    if item["path"] == "studies/results/finite-normal-derivative-v1.json.gz":
        with Path(".local/verification/normal-review/canonical.json").open("xb") as handle:
            handle.write(decoded)
print("All compressed and decoded artifact hashes verified")
PY
python3 studies/verification/finite-normal-report-audit-v1.py \
  --report .local/verification/normal-review/canonical.json \
  --output .local/verification/normal-review/saved-audit.json
```

The standard-library auditor makes no backend import or model call. Exit 0
means saved arithmetic and bindings reconcile, including the original failed
protocol. It does not certify density evaluations or repair the error estimator.
It refuses existing output paths, including dangling symlinks, and requires an
existing parent. Both new scripts provide read-only `--help`.

## Explicit numerical replay

The complete scientific study is already retained. The following is an explicit
new numerical execution, not an archive audit:

```bash
.venv/bin/python -W error::RuntimeWarning \
  studies/verification/finite-normal-derivative-v1.py \
  --output .local/verification/normal-review/new-study.json
```

It imports the candidate and independent quadrature/positive-area calculations,
but runs no optimizer, renderer or old archived-data analysis. Exit 0 requires
the full frozen protocol, exit 1 retains a scientific/protocol failure, and
exit 2 refuses invalid CLI/input/fresh-destination conditions. Never overwrite
the original report, remove its unknown query or change its thresholds to
replace the failed result. Algorithm improvements need separately bound evidence.
