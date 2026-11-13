# Affine finite-material evaluation and fitter qualification

Exactly affine queries share transformed curve samples while retaining the
finite-Gaussian Green model, numerical guards and scalar fallback. The
[algorithm guide](../finite-affine-evaluation.md) derives the method and work/
memory contracts. The circular-segment API preserves its original result type;
the explicit general-ring API exposes batch diagnostics. Automatic photo tracing
and CAD selection do not adopt this observation model.

## Prospective design and source isolation

The [frozen plan](../../studies/finite-affine-batch-v1.json) retains 16 operator
cases, six resource controls and six independent derivative checks. Its final
integration amendment has SHA-256
`a43e2d97a32e6bd4822dfff9d7c090f9b469c7ac0bbf92caa35173de0d37d0bd`.
The amendment integrates main's shadow change before any candidate performance
timing or new optimizer recovery; cases, budgets, targets and both 3× goals
remain unchanged. Earlier plan freezes are preserved in the
[portable evidence directory](../../studies/fixtures/finite-affine-batch-v1/README.md).

The comparator loads byte-identical original fitter `e2019bcc…`, Green evaluator
`9102f9e1…` and sheet code `e18cbe44…` in a separate namespace, with the original
sheet loaded first. It does not emulate the original with candidate flags.
The candidate contains main's sheet code `cbb2f4ae…`. Later documentation-only
main integration changes none of the bound scientific or software inputs.

The runner is frozen at SHA-256
`baf0a00bd45d639da22aeaeaa052b52ab41e49e8376010901720aac7a059d7ca`.
Before recovery, **33 metadata, routing, serialization and CLI contracts pass**
with zero inverse optimizers. Denied affinity, incomplete returns, explicit
real-function entry counts and continuation scope are covered. Sentinel controls
are distinct from numerical recovery and timing evidence.

## Numerical behavior

The canonical run passes all **28 controls**: 16 operators, six resource checks
and six independent derivative comparisons. Thirteen operator cases use batching;
a giant-radius partition limit and two projective maps retain scalar fallback.
A nonzero raw perspective term is never approximated as affine, including a
regression where normalization would underflow it to zero.

| Comparison | Maximum observed discrepancy |
| --- | --- |
| Original versus batch probability | `3.83e-12` |
| Kernel versus independent positive-area intensity | `1.383e-9` levels |
| Independent 32/64-order intensity comparison | `3.849e-11` levels |
| Direct Jacobian versus independent finite difference | `8.989e-9` |
| Independent finite-difference step comparison | `2.702e-8` |

All six direct Jacobians are bit-identical to the original evaluator. Resource
controls retain low-work, panel, memory and query-count refusals. Unit checks
also cover large coordinates, reflections, holes, raw perspective underflow,
discarded-work accounting and the unchanged public circular-segment schema.
These numerical estimates are not certified integration or physical uncertainty
bounds. The earlier integrated no-timing replay also passes all 28 controls;
its original runner interval remains separately hash-bound.

## Complete recovery and timing experiment

The [complete canonical archive](../../studies/results/finite-affine-batch-v1.json.gz)
and [readable result index](../../studies/results/finite-affine-batch-v1-summary.json)
retain all 24 original cases and 12 measured-ring records. Saved pixels, values,
transforms, supplied optics, domains, settings and failure injections are reused;
no images are rendered and no observation preparation is repeated. All **32
eligible accuracy fits** return; **four original ineligible/upstream records**
remain explicit. All prior **12 matched original** and **three measured-ring**
all-target passes are preserved, with **every archived completion flag equal**.
Model-mismatch misses remain misses; this is not an all-36-target success.

The three fixed whole-fit datasets each use 40 training samples, one warmup and
three paired timed repeats per implementation. Public mean/Jacobian calls use
seven paired timed repeats after one warmup, at 40 and 56 queries. Repeat order
alternates original/candidate and candidate/original. Instrumented warmups and
profiled accuracy fits never enter timing medians. All **192 kernel samples**,
**24 whole-fit samples** and full outputs remain in the archive; the explicit
entry log records **56 real fitter entries**, 32 accuracy plus 24 warm/timed.

The run uses CPU 0 from the allowed affinity set, Python 3.12.3 and NumPy 2.5.4.
All five declared numerical-library thread settings are 1. Affinity succeeds,
all requested calls return, every required fit-completion check passes, and all
eight fit outputs per workload agree with their corresponding candidate
accuracy fit or original warmup. These conditions qualify this recorded fixed
comparison; a saved-report audit cannot independently prove host quietness.

| Fixed dataset and supplied-covariance lane | Original median | Candidate median | Paired-median speedup |
| --- | --- | --- | --- |
| Small isotropic; scalar identity | 13.4318 s | 2.7542 s | 4.8768× |
| Medium directional; nominal observed moment | 12.9174 s | 3.9109 s | 3.3030× |
| Rotated major directional; nominal observed moment | 12.8640 s | 3.6588 s | 3.5159× |

The geometric mean of complete-fit speedups is **3.84022×**, meeting the fixed
3× goal. Mean-kernel speedup is **10.1285×** in the geometric mean, also meeting
its fixed 3× goal; individual mean cases span 7.19–15.31×. Direct Jacobian reuse
improves its cases by approximately 1.12–1.14×. Mean and derivative evaluation
remain substantial costs. A faster kernel alone would not qualify fitting.

An independent standard-library saved-data auditor passes **942/942 checks**,
recomputing controls, arrays, counts, pair order, medians, geometric means,
completion checks and repeated-output consistency. Historical original-24
held-out prediction arrays were not archived: that older target subcheck uses
its source-bound saved scalar. Current predictions and paired photo prediction
deltas are recomputed from saved arrays. No forward model or fit is rerun by
this audit. See [reproducible archive verification](../../studies/fixtures/finite-affine-batch-v1/README.md#verify-the-saved-report-without-fitting).

## Actual failure continuation and retained audit defect

A separate run injects one exception at the first candidate fit entry, with
benchmark timing disabled. It retains all 36 records, a truthful first-row
failure, **31 later real accuracy-fit returns** and four original ineligible
outcomes. The source/input closure is unchanged. The process exits **1** because
the frozen runner's built-in comparison mixes in-memory dataclass tuples and
JSON lists; eight of its nine checks pass. Its raw failed audit is preserved.

The independent auditor compares both saved JSON files and passes **1,018/1,018
checks**. All **35 later records match exactly** after excluding only six named
clock fields. This verifies saved-result continuation; it does not turn the
original failed process into a pass. A standard-library control separately
reproduces the container sensitivity without importing the fitter. The
[artifact guide](../../studies/fixtures/finite-affine-batch-v1/README.md#retained-continuation-comparator-failure)
explains the original defect, allowed exclusions and separate audit workflow.
The frozen runner was not edited and no optimizer rerun was used to resolve it.

## Software regression

The full Python suite passes **943 tests**, with zero failures, errors or skips
and runtime warnings treated as errors. The JUnit interval is **555.750 seconds**
and the wrapper interval **556.504 seconds**; these are regression-run durations,
not latency benchmarks. All **284 software inputs** and **22 built frontend
files** remain unchanged during the run. Production frontend build and full
`make lint` pass. The 42 affine/integration controls are included in that total.

The later documentation-only main merge leaves every software/build hash
unchanged. JUnit and the complete before/after interval binding are in the
[portable evidence directory](../../studies/fixtures/finite-affine-batch-v1/README.md).
No new browser, installed-machine, native-slicer or physical-print result is
claimed. The original [paired-field failures](finite-photo-intensity-v2.md)
and [failed aperture-order comparison](finite-free-centre.md) retain their
original evidence and scope. The supplied covariance, acquisition and thickness
models still need independent adequacy checks before automatic trace adoption.

| Source or receipt | SHA-256 |
| --- | --- |
| `backend/finite_affine.py` | `d4eb540f6a654178fca41b4be416bd4ad6ebb6b3f645bc78b5383b18b8caa653` |
| `backend/finite_centre_fit.py` | `df8a057abefe983ee951c894a9ae44e0c6b0f472d3419578be505973ea3a8bfb` |
| `tests/test_finite_affine.py` | `58661c00edc78de9f316a61998c3c74f7c562be3e0bf32919edb994eb7cac30e` |
| Full decoded Python JUnit | `c61918d008c729cd1efef0e72666111c396ac63494263d085ec4d9c1efa4ae3e` |
| Software interval binding | `928848d222286b7638c0f7e11022e20376b0c2182ad2a45e93a6af0871811640` |
| Complete decoded canonical JSON | `aa46038d893ad18ccc6b7e2fb4d5af562d6fe73b7a50f5d17274bbd253b6d544` |
| Complete decoded continuation JSON | `82563273cb34cd51890fcb54bfff82eb1dd6967124429215191dce0fb21abf82` |
| Original failed continuation audit | `f80547ffb3034c1c9660a268b81c02554325d6f2eceb1dfea558856c078428d9` |
| Independent canonical audit | `d4de0df5e8eb8f844574c922f3eeeecc8b08d1b4627e6a356bb5ba81278107db` |
| Independent continuation audit | `8d1ec1421d898b0a29e0f967b973598f7a364bbb8770b51b891608963465ff50` |
| Local integrated no-timing numerical receipt | `b3efef4e1223e270cbe4bb66912233846bab6523cf40fa8da57df8bf3e2e08ad` |
| No-optimizer contract receipt | `1d7cb286d9e0555ea7becb26c398dac487c6f604d924eee28de8d28f29b0b779` |
