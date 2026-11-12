# Nearest crossing and unresolved-contact verification

This candidate is based on published `a5f99e5a4180ec2437c08215faa12058b6b490a9`
([PR #55](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/55)).
It repairs the actual edge-profile selector after the earlier symmetric-grid
repair. The [method guide](../edge-crossings.md) defines physical-distance
ranking, verified crossings, unresolved contacts and numerical limits.

## Reproduced defects and resulting behavior

All image fixtures below use bounded linear-light values except the explicitly
invalid-data case. The actual production bilinear sampler, default 0.125-pixel
step and half-level selector are exercised; these are not real photographs.

| Evidence | Baseline behavior | New behavior |
| --- | --- | --- |
| Seed at `(16.5,1)`, local roots `-0.01`, `+0.10` and a farther root | Selected `+0.10` for one normal and `-0.01` for its reverse, a 0.11-pixel discrepancy | Both normals select the uniquely nearer `-0.01` crossing |
| Distinct equally nearest roots at `±0.0625` px | Chose according to normal/index order | Unresolved; original point retained with `keep=False` |
| Nearest target-level tangency with a farther crossing | One direction could use the contact while its reverse jumped to the farther edge | Unresolved; no silent jump to another edge |
| Whole interval at target level | Selected different plateau endpoints under reversal | Unresolved; no midpoint or endpoint is invented |
| Non-finite residual inside the searched region | Could reject in one direction yet retain an invalid interpolation in the other | Reject both directions |
| One confirmed zero between opposite signs | Boolean endpoint handling could count contacts inconsistently | Count the crossing once |

Rejected points are unchanged. A mixed-profile test checks that an independent
resolved point remains available while an ambiguous point is rejected.
The existing trace/support machinery receives the same `keep` interface.
Median and sloped searches must both resolve before ring smoothing, whose
behavior is retained. This does not add an image-accuracy classification.

## Independent numerical evidence

The complete Python suite passed **1,111 tests in 205.28 s**, including **36 new
crossing tests**. The new tests independently compute roots from original binary
samples with rational arithmetic, cover 128 randomized profiles with exact
contrast scaling and mirror checks, and retain the actual image counterexamples.
Their tiny-root assertions use a relative comparison with zero absolute allowance,
so cancellation to zero cannot pass a normal pixel-scale tolerance.

An additional [independent contact oracle](../../studies/verification/nearest-crossing-oracle.py)
constructs searched domains and contact components separately from production.
It exhaustively checks all `3^5 × 2^4 = 3,888` combinations of five residuals
from `{-1,0,1}` and four searched-segment flags, including their reflections.
Resolve/reject decisions agree throughout; returned roots and reflections match
exactly in that finite enumeration. Its [source-bound result](../../studies/results/nearest-crossing-oracle.json)
also retains tiny, subnormal, overflow-scale and bounded three-crossing cases.

To rerun this extra check in an isolated checkout:

```bash
.venv/bin/python studies/verification/nearest-crossing-oracle.py
```

It writes a JSON result beside the script and refuses an existing result file.
The separately committed result is under `studies/results/`. The included
entrypoint reproduced that result byte for byte before commit. The result's
Git revision is the base checkout; its source hashes bind the executed dirty
candidate rather than attributing modified code to the base revision.

These finite-data checks are not a universal proof about noisy images. Exact
ranking applies to represented residual samples, not unknown radiance or edge
positions. Small upstream perturbations near competing roots can still change
their order.

## Preservation of the previous profile census

The prior 576-scene cohort was reused unchanged as a preservation regression.
It is development evidence already examined in PR #55, not a new evaluation
population or a test of the new adversarial contact cases.

| Quantity | Recorded result |
| --- | --- |
| Complete Cartesian rows | 9,216 |
| Kept crossings | 8,448 |
| Low-contrast rejections | 768 |
| Measurement failures | 0 |
| Acceptance or measured-sigma changes | 0 |
| Largest offset change | 5.10702591328e-15 px |
| Largest normal-reversal difference | 9.99200722163e-15 px |

All 96 summary groups were independently reconciled against complete CSVs;
keys are unique, rejected offsets remain empty and accepted values are finite.
Only 51 offset strings differ from the preceding run. Runner, plan, edge/tone
source and runtime match; only the sheet selector changes. The [complete summary](../../studies/results/nearest-crossing-preservation.json)
and [reconciliation](../../studies/results/nearest-crossing-preservation-audit.json)
are committed. Complete CSV rows remain local at
`.local/verification/nearest-crossing-final/cases.csv`, hash-bound in those
records and regenerated by the existing material-gradient study command.

Material-gradient bias and pre-refinement wall offsets remain. This selector
repair does not requalify the optical model, recover a true object boundary,
correct wall geometry or establish final CAD accuracy.

## Computation cost

The [local timing record](../../studies/results/nearest-crossing-performance.json)
includes bilinear sampling and level selection for 1,000 repeated profiles per
call, with three repetitions and a 16-pixel half-window. The measuring process recorded Python 3.12.3 and NumPy 2.5.4. Median times were:

| Fixture | Baseline, ms per 1,000 profiles | Candidate, ms per 1,000 profiles |
| --- | --- | --- |
| Single crossing | 17.0 | 20.6 |
| Three crossings | 10.0 | 29.1 |
| Alternating band with ambiguous nearest roots | 9.7 | 101.0 |

The candidate rejects all ambiguous-band profiles; the baseline accepted them.
Exact comparisons add work for competing candidates, while a single candidate
uses no rational ranking. These are local repeated-fixture timings, not a
browser, full-photo latency or hardware-capacity qualification.

## Verification boundaries

Ruff and whitespace checks passed. The seven source/plan/test files were frozen
through the final full suite and preservation census. Earlier verification was
stopped to replace cancellation-prone interpolation with directly computed
barycentric weights; interrupted logs and the incomplete study directory are
retained locally, not presented as completed evidence.

The repository-wide Markdown audit passed for 71 documents, 711 local links,
53 heading fragments and 116 tables. Historical figures and their source-bound
records remain intact; current guides link the later selector repair.

No frontend, API schema, dependency, export-code or reference-library change is
introduced. Existing full-photo Python tests are regression coverage; this new
study itself concerns local profiles. Browser/build, hosted CI, actual camera
calibration and physical fit remain separate evidence.

## Source and artifact binding

| Artifact | SHA-256 |
| --- | --- |
| `backend/sheet.py` | `a086d7216256726a0e392bd98cbdb1274f5cb5eb096802c17c805349a7747e31` |
| `tests/test_edge_crossings.py` | `91238ec81f0a603b694dce7235657633a2e2941b2af1e2b5fb8b1f1cbad78fbb` |
| `studies/verification/nearest-crossing-oracle.py` | `489dfb0ad059c7b7b1d5b6e13c85d7568470dabcef4de46a107fe44f6d79330b` |
| `studies/results/nearest-crossing-oracle.json` | `3085e46a61efa94ca5b532d98a0bffba4acec5d713c49b9af2ef228b0921473c` |
| `studies/results/nearest-crossing-preservation.json` | `2f2c30135afbe1bba7ac3307171077d10879742ebd641c25b8c7588a3dbbb463` |
| `studies/results/nearest-crossing-preservation-audit.json` | `e7e685b3bd0f25af1d4d2bee140f3041e0206ab5619e43d4f862dc196f0759f8` |
| `studies/results/nearest-crossing-performance.json` | `cb568cc8f42c88eb83df2b042cc275d940afb1d510b58751797d68bd1134bc82` |
