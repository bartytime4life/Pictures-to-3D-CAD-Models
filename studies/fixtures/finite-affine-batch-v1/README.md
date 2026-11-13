# Affine finite-material study: sources and complete evidence

The [prospective plan](../../finite-affine-batch-v1.json) and frozen
[runner](../../verification/finite-affine-batch-v1.py) compare shared affine
quadrature with the original finite-material implementation. The
[readable result index](../../results/finite-affine-batch-v1-summary.json)
contains source hashes, environment, medians, summary and an archive manifest.
The [validation guide](../../../docs/validation/finite-affine-batch.md) explains
results and limits. All inputs are archived synthetic data; no private photos
are added by this study.

## What is preserved

| Artifact | Scope |
| --- | --- |
| [Complete canonical JSON, gzip](../../results/finite-affine-batch-v1.json.gz) | All 16 operator, six resource and six derivative controls; 36 accuracy rows; all 192 kernel and 24 whole-fit warm/timed samples with complete outputs |
| [Complete failure continuation, gzip](first-fit-failure-v1.json.gz) | One injected first-fit exception, 31 later real accuracy fits, four retained ineligible records and no timing repeats |
| [Original built-in continuation audit](first-fit-failure-built-in-audit-v1.json) | Eight of nine checks pass; its tuple/list equality defect and failed result are retained |
| [Canonical terminal receipt](canonical-terminal-audit-v1.json) | Original exit 0, stdout equality, source closure and measurement counts |
| [Independent canonical audit](independent-canonical-audit-v1.json) | 942/942 saved-data arithmetic, source and accounting checks |
| [Independent continuation audit](independent-continuation-audit-v1.json) | 1,018/1,018 checks, including all 35 later saved rows |
| [Container-comparison control](comparator-container-control-v1.json) | Standard-library reproduction of tuple/list comparison sensitivity; no original process-memory reconstruction |
| [No-optimizer contract receipt](no-optimizer-contracts-v5.json) | 33 parser, routing, serialization, entry-count and qualification controls; explicitly no inverse fits |
| [Full Python JUnit, gzip](python-regression-v1.xml.gz), [interval binding](python-regression-binding-v1.json) | 943 tests; before/after 284 software and 22 built-file hashes; separate from benchmark timing |
| [Initial plan](initial-plan-v1.json), [pre-integration plan](pre-integration-plan-v1.json) | Earlier prospective freezes; final plan includes the declared integration amendment |
| Original fitter, Green and sheet `.py.txt` files in this directory | Byte-identical comparator sources loaded in an isolated namespace; original sheet loads first |
| [Canonical progress log](canonical-progress-v1.log), [continuation progress log](first-fit-failure-progress-v1.log), [continuation command](first-fit-failure-command-v1.json) | Execution provenance; stdout is byte-identical to each saved full JSON and is not counted as independent evidence |

Gzip archives are lossless, with level 9, `mtime=0` and no embedded filename.
The manifest records both compressed and decoded byte lengths and SHA-256.
The canonical full JSON has **16,356,486 bytes**, SHA-256
`aa46038d893ad18ccc6b7e2fb4d5af562d6fe73b7a50f5d17274bbd253b6d544`.
Its compressed form has **1,200,825 bytes**, SHA-256
`630c7c7efd90b114d4cd37caaa53de7dc0c4a6218bb3517a3aff167fd3a35228`.
No rows, arrays, warmups or output fields were removed to reduce its size.

The no-optimizer harness is retained as
[`no-optimizer-contracts-v5.py.txt`](no-optimizer-contracts-v5.py.txt), an exact
provenance archive. It has a fixed local output path and no argparse interface;
it is not advertised as a fresh-output CLI. Its receipt distinguishes sentinels
from actual preparation/numerical controls.

## Verify the saved report without fitting

From the repository root, use a fresh review directory. This checks every
manifest artifact and decompresses the two full reports into new local files:

```bash
mkdir -p .local/verification/affine-review
python3 - <<'PY'
from pathlib import Path
import gzip
import hashlib
import json

index = json.loads(Path("studies/results/finite-affine-batch-v1-summary.json").read_text())
reports = {
    "studies/results/finite-affine-batch-v1.json.gz": "canonical.json",
    "studies/fixtures/finite-affine-batch-v1/first-fit-failure-v1.json.gz": "continuation.json",
}
for item in index["artifacts"]:
    saved = Path(item["path"]).read_bytes()
    assert len(saved) == item["bytes"]
    assert hashlib.sha256(saved).hexdigest() == item["sha256"]
    decoded = gzip.decompress(saved) if item["encoding"] == "gzip" else saved
    assert len(decoded) == item["decoded_bytes"]
    assert hashlib.sha256(decoded).hexdigest() == item["decoded_sha256"]
    if item["path"] in reports:
        target = Path(".local/verification/affine-review") / reports[item["path"]]
        with target.open("xb") as handle:
            handle.write(decoded)
print("All archive hashes and decoded bytes verified")
PY
python3 studies/verification/finite-affine-report-audit-v1.py \
  .local/verification/affine-review/canonical.json \
  --continuation .local/verification/affine-review/continuation.json \
  --expected-plan-sha a43e2d97a32e6bd4822dfff9d7c090f9b469c7ac0bbf92caa35173de0d37d0bd \
  --expected-runner-sha baf0a00bd45d639da22aeaeaa052b52ab41e49e8376010901720aac7a059d7ca \
  --output .local/verification/affine-review/saved-audit.json
```

This standard-library-only auditor imports no fitter, performs no new forward
calculation and runs no benchmark. Exit 0 means the saved integrity checks pass.
It is not a physical-model check, a proof of host quietness or a replacement for
a missed performance/scientific target. Historical `original24` held-out
prediction arrays were not archived; that older target subcheck uses its
source-bound saved scalar. Current predictions and paired photo deltas are
checked from the retained arrays.

## Reproduce numerical or optimizer work deliberately

A quick numerical replay runs the 28 controls without inverse optimization:

```bash
.venv/bin/python studies/verification/finite-affine-batch-v1.py \
  --no-timing --output .local/verification/affine-review/new-controls.json
```

The complete comparison also runs 32 accuracy fits and 24 whole-fit warm/timed
entries. Use a separate quiet interval for the fixed-CPU, single-threaded timing
protocol; an unavailable affinity setting withholds timing qualification:

```bash
.venv/bin/python studies/verification/finite-affine-batch-v1.py \
  --complete --quiet-interval \
  --output .local/verification/affine-review/new-complete.json
```

All destinations must be fresh `.json` files with existing parent directories.
`--complete --no-timing` keeps the accuracy fits while omitting benchmark repeats.
[Developer tools](../../../docs/developer-tools.md) documents exit codes and the
first-fit-injection command. The saved-report verification above is sufficient
to inspect the recorded evidence and avoids repeating these expensive fits.

## Retained continuation comparator failure

The actual injected-failure process exited **1**. The first row correctly records
`execution_failure`, with no fabricated fit and false target flags. All 31 later
real fits returned, four original ineligible records remain, and no timed fits
ran. Its original built-in audit reports eight of nine checks passing.

The failed check compared a JSON-loaded canonical row with an in-memory
`dataclasses.asdict` row. Dataclass tuple fields remain tuples in memory but
become lists in JSON. The frozen comparator descends into lists, so equal-valued
containers can compare unequal while their JSON hashes match. The independent
saved-report auditor loads **both** full JSON files and confirms all **35 later
rows match exactly**, removing only `runtime_seconds`, `seconds`,
`inclusive_seconds`, `exclusive_seconds`, `fit_seconds`, and
`remaining_validation_search_refinement_seconds`.

The frozen runner, raw exit 1 and original failed audit are unchanged. The
separate saved-data pass does not relabel the original run as successful. A
future correction should receive a new study version and a tuple/list control;
no optimizer rerun or governing-source edit was used to produce this audit.
