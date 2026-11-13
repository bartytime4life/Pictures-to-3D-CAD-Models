# Complete source-cell acquisition-mean evidence

The [method](../../../docs/finite-acquisition-mean.md) and
[complete validation record](../../../docs/validation/finite-acquisition-mean.md)
describe the independent analytic-cell/staged mean. All 128 saved-capture
comparisons pass their frozen checks. Maximum analytic-D query discrepancies
are `7.62939453125e-5` unquantized and `3.0517578125e-5` encoded intensity levels.
All 64 encoding comparisons retain identical codes. These are supplied synthetic
forward means, not recovered geometry or real-camera accuracy.

The [index](../../results/finite-acquisition-mean-v1-summary.json) binds **182
artifacts**, including all 128 stage archives, 16 coverage arrays, 56,448
residuals, the raw strict-JSON report, complete progress/census records, reviews,
and an eight-file numerical source ZIP. The original 12 failed controls,
32 first-audit arithmetic mismatches and workspace undercount remain explicit.
No failed record or original result is overwritten.

## Verify saved data without a model call

Run from the repository root with its existing Python environment. This block
uses a fresh directory, refuses replacement, verifies all indexed hashes and
reconstructs the complete saved run. The auditor uses NumPy for saved numeric
archives but blocks backend, test-generator and OpenCV imports. It reads the
historical source ZIP as data; it does not need the local source-freeze Git
commit or activate that source.

```bash
set -e
mkdir -p .local/verification
python3 - <<'PY'
from pathlib import Path
import gzip, hashlib, json

root = Path.cwd()
review = root / '.local/verification/acquisition-mean-archive-review-v1'
review.mkdir(exist_ok=False)
index = json.loads((root / 'studies/results/finite-acquisition-mean-v1-summary.json').read_text())
assert len(index['artifacts']) == 182
for item in index['artifacts']:
    data = (root / item['path']).read_bytes()
    assert len(data) == item['stored_bytes']
    assert hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
    decoded = gzip.decompress(data) if item['encoding'] == 'gzip' else data
    assert len(decoded) == item['decoded_bytes']
    assert hashlib.sha256(decoded).hexdigest() == item['decoded_sha256'], item['path']
    if 'run_relative_path' in item:
        relative = Path(item['run_relative_path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        target = review / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(decoded)
print('Verified all 182 artifacts; reconstructed complete saved run.')
PY
.venv/bin/python studies/verification/finite-acquisition-mean-artifact-audit-v1.py \
  --root . \
  --recorded-source studies/fixtures/finite-acquisition-mean-v1/recorded-source.zip \
  --report .local/verification/acquisition-mean-archive-review-v1/report.json \
  --output .local/verification/acquisition-mean-archive-review-v1/audit.json
python3 - <<'PY'
from pathlib import Path
import json
r = json.loads(Path('.local/verification/acquisition-mean-archive-review-v1/audit.json').read_text())
assert r['passed'] is True
assert r['counts']['checks'] == r['counts']['passed'] == 2816
assert r['counts']['rows'] == 128 and r['counts']['stage_arrays'] == 768
assert r['png_code_changes']['total_changed_entries'] == 0
assert r['audit_scope']['new_scientific_model_calls'] == 0
print('All 2816 saved-data checks pass; zero model/capture/optimizer calls.')
PY
```

## Source and failure boundaries

The raw experiment binds numerical source `521c318`, with report SHA-256
`bd8127cc84999e7c5572797c46c2ba62bda29e2262ce57375c1e9745ce9133c3`.
The eight-file ZIP preserves those exact bytes. Current code additionally fixes
the workspace estimate; its [separate admission](../../finite-acquisition-mean-v1-workspace-repair-v1.json)
and 22-check source comparison prove the numerical code is unchanged. Archived
workspace fields retain their original values. The old estimate is valid for
these study shapes but understated a supported extreme aspect ratio.

The [control continuation](../../finite-acquisition-mean-v1-continuation-v1.json)
retains the first failed 134-case run and admits a bounded higher-precision
interior-root representation without snapping or relaxed tolerances. The first
mathematical audit's 32 mismatches are also retained; the separate second audit
checks operational binary32 and independent exact/binary64 allowance arithmetic.
Every adequacy outcome passes both. These are estimated engineering checks.

Historical `.py.txt.gz` reviews preserve original invocation paths. The supported
portable command above replaces only local-Git source lookup with ZIP-byte
verification; its independent saved arithmetic is preserved. A fresh explicit
execution of the capture-mean runner evaluates new forward means and is a
separate source-bound experiment. It never replaces these saved results.

Current main's shadow-lighting pipeline, inverse fitting, camera calibration,
physical dimensions and CAD/print acceptance need their own evidence. No new
interface controls or automatic correction are introduced by this archive.
