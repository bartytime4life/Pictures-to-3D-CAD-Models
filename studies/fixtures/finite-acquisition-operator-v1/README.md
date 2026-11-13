# Complete acquisition-operator evidence

The [method](../../../docs/finite-acquisition-operator.md) and
[validation record](../../../docs/validation/finite-acquisition-operator.md)
describe 16 new synthetic scenes, 32 output-scale rows and 128 Gaussian/stage
comparisons. Matching second moments remains incompatible in 9/32 unquantized
and 16/32 PNG comparisons under the frozen one-level criterion.

The [index](../../results/finite-acquisition-operator-v1-summary.json) binds
**123 artifacts**, with complete stored/decoded byte counts and SHA-256 hashes.
It includes every source PNG, numeric stage/kernel NPZ and scene metadata, the
original failed bootstrap attempt, the completed continuation, and saved reviews.
No observation, prediction, failed row, unknown, work count or scalar marker is
removed. Gzip files use zero mtime and no embedded filename.

The package includes an **87-file recorded source snapshot** from the experiment.
Current main includes newer shadow-lighting changes; those are not the source
tested by this study. The workflow below checks the recorded source as data,
without importing it or replacing the current backend.

The original attempt exited 1 before capture. Its four completed Gaussian
controls are reused by the continuation, separately from 64 new main calls.
The continuation exited 0 under its in-memory numerical gates, but its raw
report has **320 scalar serialization markers**. The artifact auditor therefore
deliberately exits 1: artifact binding passes, while raw scalar integrity fails.
This failure remains in the archive. The separate normalizer reconstructs the
represented 288 binary32 numbers and 32 booleans without new scientific calls
or new qualification. Independent checks find no change in the 128 categories.

## Verify and reconstruct saved data

Run this block from the repository root with the existing project environment.
The artifact auditor uses standard-library NPY parsing and Pillow for PNG
decoding; it imports no NumPy, backend, generator or reference. The normalizer
uses only the standard library. The block writes a fresh review directory and
refuses an existing destination. It performs no new capture or model evaluation.

```bash
set -e
mkdir -p .local/verification
python3 - <<'PY'
from pathlib import Path
import gzip, hashlib, io, json, zipfile

root = Path.cwd()
review = root / '.local/verification/acquisition-archive-review-v1'
review.mkdir(exist_ok=False)
index = json.loads((root / 'studies/results/finite-acquisition-operator-v1-summary.json').read_text())
assert len(index['artifacts']) == 123
for item in index['artifacts']:
    stored = (root / item['path']).read_bytes()
    assert len(stored) == item['stored_bytes'], item['path']
    assert hashlib.sha256(stored).hexdigest() == item['sha256'], item['path']
    decoded = gzip.decompress(stored) if item['encoding'] == 'gzip' else stored
    assert len(decoded) == item['decoded_bytes'], item['path']
    assert hashlib.sha256(decoded).hexdigest() == item['decoded_sha256'], item['path']
    if 'run_relative_path' in item:
        relative = Path(item['run_relative_path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        target = review / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(decoded)
    if item['kind'] == 'recorded_source_snapshot':
        source = review / 'recorded-source'
        source.mkdir(exist_ok=False)
        with zipfile.ZipFile(io.BytesIO(decoded)) as archive:
            for member in archive.infolist():
                relative = Path(member.filename)
                assert not relative.is_absolute() and '..' not in relative.parts
                assert not member.is_dir()
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(archive.read(member))
        manifest = json.loads((source / 'recorded-source-manifest.json').read_text())
        assert len(manifest['files']) == 87
        for name, digest in manifest['files'].items():
            assert hashlib.sha256((source / name).read_bytes()).hexdigest() == digest, name
print('Verified all 123 artifacts and 87 recorded source files; reconstructed saved run.')
PY
set +e
.venv/bin/python studies/verification/finite-acquisition-artifact-audit-v1.py \
  --root .local/verification/acquisition-archive-review-v1/recorded-source \
  --run-dir .local/verification/acquisition-archive-review-v1 \
  --output .local/verification/acquisition-archive-review-v1/artifact-audit.json
acquisition_audit_status=$?
set -e
test "$acquisition_audit_status" -eq 1
python3 - <<'PY'
from pathlib import Path
import json
r = json.loads(Path('.local/verification/acquisition-archive-review-v1/artifact-audit.json').read_text())
assert r['artifact_checks_passed'] is True
assert r['artifact_failures'] == []
assert r['raw_serialization_contract_passed'] is False
assert r['passed'] is False
print('Artifact bindings pass; original scalar serialization failure retained.')
PY
python3 studies/verification/finite-acquisition-normalize-v1.py \
  --input .local/verification/acquisition-archive-review-v1/report.json \
  --output .local/verification/acquisition-archive-review-v1/normalized.json
python3 - <<'PY'
from pathlib import Path
import hashlib, json
p = Path('.local/verification/acquisition-archive-review-v1/normalized.json')
assert hashlib.sha256(p.read_bytes()).hexdigest() == '90a7d6db7f9555c3f06c22b269897e72b50a4f9453eb5f1952acc3e5b9631f6b'
r = json.loads(p.read_text())
assert r['normalization']['changed_scalar_count'] == 320
assert r['raw_scalar_serialization_passed'] is False
print('Derived native-scalar report matches; no scientific qualification assigned.')
PY
```

## Source and reproduction boundaries

The original scientific plan and failed execution remain unchanged. The
[continuation plan](../../finite-acquisition-operator-v1-continuation-v1.json)
admits one exact helper bootstrap repair and reuses only already qualified
global controls. Its recorded source commit is a local pre-execution freeze;
file hashes and the archived original helper bind the published evidence.
The source snapshot contains the exact union of the 72 driver and 19
continuation bindings, with overlap removed. Its local source-freeze commit
is `0714aadf04f6af2130bfe5af70d9dafbbe4677a7`; it is not a claim that the
publication branch's backend has those bytes. The snapshot's manifest and the
artifact auditor independently verify the recorded file hashes.

Historical `.py.txt.gz` files retain their original invocation paths and are
evidence snapshots. The supported review commands above use repository-relative
paths and fresh outputs. The normalizer accepts only the exact archived raw
report and a small whitelist of tagged fields; it rejects arbitrary expressions,
nonfinite markers and unrelated reports.

A fresh numerical execution requires a separately qualified environment and
source, and is a separate experiment. The historical capture scripts are retained
for provenance; running them against current main does not reproduce the
recorded source closure. The archived serializer
bug and supplied geometry/map assumptions are not a production fitting feature.
The data do not qualify physical optics, dimensional recovery or automatic CAD
correction, and cannot establish the causes of the older photo-fit failures.
