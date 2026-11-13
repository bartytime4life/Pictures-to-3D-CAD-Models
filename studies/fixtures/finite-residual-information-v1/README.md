# Residual information: preserved failed protocol and saved-data review

This archive accompanies the [frozen plan](../../finite-residual-information-v1.json),
[diagnostic runner](../../verification/finite-residual-information-v1.py),
[mathematical method](../../../docs/finite-residual-information.md), and
[complete validation record](../../../docs/validation/finite-residual-information.md).
The [readable index](../../results/finite-residual-information-v1-summary.json)
contains all 12 identities, conditional summaries and the artifact manifest.
Inputs are the existing archived synthetic measurement fields; no private photos
or new image captures are included.

The original full replay **exited 1**. Its normal-angle positive-area control
misses the frozen absolute step/half-step criterion; all ten archived normal
columns also fail their declared stability guard. All 12 records and all old
pass/completion flags remain. The independent saved-data audit passes 9,683
checks and confirms the failed protocol; it does not turn that failure into a
scientific pass. The post-hoc rotation analysis is separate, uses saved arrays
only and does not replace the unknown normal columns.

## Complete artifacts

- [Canonical JSON, lossless gzip](../../results/finite-residual-information-v1.json.gz):
  all means, derivatives, finite-difference sides/errors, spectra, residuals,
  one-step predictions, refusals and work logs. Decoded SHA-256 is
  `b1d15d4e006d1f65823cb6bd20810cd127d6d6ac6912973d590f38bd8acc6c74`;
  decoded length is 8,973,743 bytes.
- [Prospective plan freeze](prospective-plan-freeze-v1.json),
  [final preflight freeze](canonical-preflight-freeze-v1.json),
  [terminal receipt](canonical-terminal-v1.json),
  [stdout](canonical-v1.stdout.log), [stderr](canonical-v1.stderr.log), and
  [launcher provenance](canonical-launcher-v1.py.txt). The launcher retains its
  original local destinations; its `.py.txt` copy is not a replay CLI.
- [Six algebra and ten safe contracts](no-optimizer-contracts-v1.json.gz),
  [11 external contracts](external-contracts-v1.json),
  [42 auditor sentinels](independent-auditor-sentinels-v1.json), and
  [complete independent audit](independent-saved-audit-v1.json.gz).
- [Earlier preflight runner](preflight-runner-4453703.py.txt): provenance for the
  caught ceiling/status defects, not the frozen runner used for the replay.
- [Post-hoc saved-rotation report](../../results/finite-normal-rotation-saved-v1.json.gz)
  and [separate source freeze](saved-rotation-freeze-v1.json). Its consistency
  comparison imports no model and performs no new forward evaluation or trial.
- [Initial rotation audit](rotation-independent-audit-v1.json),
  [corrected 13-check audit](rotation-independent-audit-v2.json), and
  [independent audit provenance](rotation-independent-audit-v2.py.txt).
  The initial closure-reader schema failure remains; numeric checks are unchanged.

Gzip files use level 9, zero mtime and no embedded filename. The manifest records
compressed and decoded lengths and SHA-256. No raw arrays are removed.

## Verify and audit without model calls

From the repository root, use a fresh review directory. The following checks
every manifest artifact and writes the two decoded analysis reports exclusively:

```bash
mkdir -p .local/verification/residual-review
python3 - <<'PY'
from pathlib import Path
import gzip
import hashlib
import json

index = json.loads(Path("studies/results/finite-residual-information-v1-summary.json").read_text())
reports = {
    "studies/results/finite-residual-information-v1.json.gz": "canonical.json",
    "studies/results/finite-normal-rotation-saved-v1.json.gz": "rotation.json",
}
for item in index["artifacts"]:
    saved = Path(item["path"]).read_bytes()
    assert len(saved) == item["bytes"]
    assert hashlib.sha256(saved).hexdigest() == item["sha256"]
    decoded = gzip.decompress(saved) if item["encoding"] == "gzip" else saved
    assert len(decoded) == item["decoded_bytes"]
    assert hashlib.sha256(decoded).hexdigest() == item["decoded_sha256"]
    if item["path"] in reports:
        target = Path(".local/verification/residual-review") / reports[item["path"]]
        with target.open("xb") as handle:
            handle.write(decoded)
print("All compressed and decoded artifact hashes verified")
PY
python3 studies/verification/finite-residual-report-audit-v1.py \
  --report .local/verification/residual-review/canonical.json \
  --expected-runner-sha c4da819d3bf34bc4183fe55529d87acedc2946bf0fcdcd878ae2fd20eb3e7d69 \
  --expected-report-sha b1d15d4e006d1f65823cb6bd20810cd127d6d6ac6912973d590f38bd8acc6c74 \
  --output .local/verification/residual-review/saved-audit.json
python3 studies/verification/finite-normal-rotation-saved-v1.py \
  --report .local/verification/residual-review/canonical.json \
  --output .local/verification/residual-review/new-saved-rotation.json
```

The auditor uses standard-library Jacobi SVD and separate pivoted QR checks
away from numerical cutoffs. Exit 0 means the saved arithmetic/source checks
agree, including the original failed control. The rotation script is post-hoc
arithmetic, not independent optical validation; its exit 0 does not qualify `N`.
Both commands refuse an existing output and require an existing parent.

## Explicit numerical replay

Help runs before numerical imports. The contracts-only mode imports NumPy but
no backend and performs no archived forward, derivative, optimizer or trial:

```bash
.venv/bin/python studies/verification/finite-residual-information-v1.py --help
.venv/bin/python studies/verification/finite-residual-information-v1.py \
  --contracts-only --output .local/verification/residual-review/new-contracts.json
```

The default mode performs actual forward/Jacobian/finite-difference evaluations
and at most one eligible trial per model, but no inverse optimizer:

```bash
.venv/bin/python -W error::RuntimeWarning \
  studies/verification/finite-residual-information-v1.py \
  --output .local/verification/residual-review/new-diagnostic.json
```

The governing replay is already complete; these instructions do not imply a
second run. Keep the original failed artifact. Exit 0 is protocol integrity,
including numerical unknowns and upstream rows; exit 1 is control/source/protocol
failure; exit 2 is an explicit parser or fresh-destination refusal. Unexpected
FD/step payload errors are protocol failures; represented numerical uncertainty
can remain unknown. Source/plan failures retain the readable 12-row population
and old flags before NumPy/backend imports. Later source changes invalidate the
binding rather than authorizing new thresholds or replacement evidence.
