# Frozen source-cell sensitivity evidence

This archive preserves the first study at
`c47214d098a234f28784cb174429e687e799a2bf`: 18 regular cells, four whole grids,
11 special cases, all 25 invariant variants and 58 returned API calls. All
prescribed row conditions pass, including deliberate unknown/refusal cases.
It is supplied-model derivative evidence, not geometry recovery or camera
qualification. Read the [complete result and limits](../../../docs/validation/finite-cell-sensitivity.md)
and [mathematics/API](../../../docs/finite-cell-sensitivity.md).

The [summary and 14-artifact manifest](../../results/finite-cell-sensitivity-v1-summary.json)
bind stored and decoded bytes. Lossless gzip preserves the 4,236,100-byte raw
report, software/run logs and larger audit receipts. The recorded source ZIP
contains 41 exact files plus its manifest, including all backend source, six
focused test files, the governing plan/runner and dependency metadata. Source
bytes are read as data by the saved-only auditors; no local Git freeze is needed.

## Verify saved data without a model call

Run this Python block from the repository root using Python 3.12. It refuses
an existing review directory. The tools use the standard library and make no
model, derivative, renderer or optimizer calls. No source ZIP is extracted or
imported. Repeating the workflow requires a new output-directory name.

```python
from pathlib import Path
import gzip
import hashlib
import json
import subprocess
import sys

root = Path.cwd()
index = json.loads((root / "studies/results/finite-cell-sensitivity-v1-summary.json").read_text())
for item in index["artifacts"]:
    stored = (root / item["path"]).read_bytes()
    assert len(stored) == item["stored_bytes"]
    assert hashlib.sha256(stored).hexdigest() == item["sha256"]
    decoded = gzip.decompress(stored) if item["encoding"] == "gzip" else stored
    assert len(decoded) == item["decoded_bytes"]
    assert hashlib.sha256(decoded).hexdigest() == item["decoded_sha256"]

out = root / ".local/verification/cell-sensitivity-portable-review-v1"
if out.exists() or out.is_symlink():
    raise SystemExit("Choose a fresh review directory.")
out.mkdir(parents=True)
report = out / "report.json"
report.write_bytes(gzip.decompress((root / "studies/results/finite-cell-sensitivity-v1.json.gz").read_bytes()))
source = root / "studies/fixtures/finite-cell-sensitivity-v1/recorded-source.zip"
subprocess.run([
    sys.executable,
    str(root / "studies/verification/finite-cell-sensitivity-artifact-audit-v1.py"),
    "--report", str(report), "--root", str(root),
    "--recorded-source", str(source), "--output", str(out / "artifact-audit.json"),
], check=True)
subprocess.run([
    sys.executable,
    str(root / "studies/fixtures/finite-cell-sensitivity-v1/review/math-audit.py.txt"),
    "--report", str(report), "--root", str(root),
    "--recorded-source", str(source),
    "--input-sha256", "d72bff9c6a7f8b96b540a006623a59f8dfcc9b969f69e97f885eca09bec7be59",
    "--output", str(out / "math-audit.json"),
], check=True)
print(f"Verified {len(index['artifacts'])} artifact files and both saved-only audits.")
```

The artifact auditor passes 315,826 checks; the portable mathematical audit
passes 57,970. The original and final artifact tools/receipts remain distinct.
The separate implementation/static audit retains its original Git-bound receipt
and source; that audit is not rerun by this portable block.

## Retained limitations

- Four complement comparisons save candidate arrays and independent reference
  maxima, but omit the reference's per-cell arrays. Those coverage/centre/radius
  maxima cannot be independently reconstructed by saved-only review. The
  receipts explicitly set `all_reference_maxima_independently_recomputed=false`.
- The frozen plan's “exact/decimal” description overstates the general linear
  oracle: it uses binary64 stencil arithmetic and `math.fsum`, alongside exact
  elementary dyadic controls. The [scope clarification](qualification-scope.json)
  preserves this distinction without editing the plan or changing any outcome.
- Five-query coupled controls do not establish five-parameter rank with two
  free brightness levels. No inverse optimizer was run. Unknown contacts,
  rounded source encoding, camera calibration and physical dimensions still
  need their own treatment and evidence.

These checks do not rerun the original acquisition experiments or full
application/browser suites. No automatic tracing, installation, deployment,
native slicer or physical-print acceptance follows from the archive.
