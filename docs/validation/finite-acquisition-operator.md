# Finite-material acquisition: second-moment closure is insufficient

Matching second moments did **not** make a continuous-Gaussian point model
reproduce the declared acquisition chain at supplied true geometry and levels.
The moment-matched comparator is incompatible with the one-level criterion in
**9 of 32 unquantized comparisons** and **16 of 32 decoded-PNG comparisons**.
This is a forward-model result on new synthetic scenes, with no fitted geometry.

The evidence is historical and source-bound. Its 87-file recorded-source
snapshot preserves the experiment's runtime/input bytes. The publication base
is main `68a67e766956ac41a3b73ae73d4ac553ef47db26`, including newer soft-shadow
changes that this experiment does not retest. The current production backend
is preserved; portable saved-data review reads the recorded source as data.

| Gaussian hypothesis / observed stage | Compatible | Incompatible | Inconclusive | Largest absolute discrepancy, levels |
| --- | ---: | ---: | ---: | ---: |
| Nominal / unquantized | 7 | 24 | 1 | 3.489105 |
| Nominal / decoded PNG | 5 | 27 | 0 | 3.662663 |
| Moment-matched / unquantized | 23 | 9 | 0 | 2.214669 |
| Moment-matched / decoded PNG | 15 | 16 | 1 | 2.323890 |

The [method guide](../finite-acquisition-operator.md) describes the signed Keys
operator, coordinate conventions, Gaussian hypotheses and engineering allowances.
Numerical qualification, model adequacy and artifact serialization have separate
outcomes here. In particular, the continuation's exit 0 does not erase either
the original bootstrap failure or its own scalar-serialization failure.

## Frozen design and represented observations

The [original plan](../../studies/finite-acquisition-operator-v1.json), SHA-256
`bf12681eeda0c44552a94ea5f033424bf20aca2f9f56c83ed9226b404675989e`,
was frozen before scientific execution. Its pre-execution amendment retains
the earlier plan and records the static-review changes. It declares 16 new
source scenes: two finite-D geometries, two discrete blur kernels and four
subpixel placements. Output scales `q=1` and `q=1.25` give **32 records**.
Each record retains both observed stage lanes and both supplied Gaussian
hypotheses, giving **128 adequacy cells**. These are paired observations, not
128 independent photographs.

Source material 40 and background 230 are encoded values, decoded to linear
light before mixing pixel coverage. The chain uses an 8,193-vertex source
polygon and retains its configuration and contour hash, pixel coverage,
actual discrete optical kernel, unquantized field,
original PNG bytes, decoded field, known-map Keys resampling and 0.7-pixel
smoothing. The continuous Gaussian comparator uses the analytic D, with its
polygon-tessellation allowance retained separately.

Both stages and both hypotheses use the same 441 query indices within each
record. There are 28,224 main probability predictions and 56,448 retained
intensity residuals. These are forward diagnostic queries, not training or
held-out observations. There are no optimizer, geometry-Jacobian or
normal-derivative calls, and no covariance or brightness fitting.

The nominal covariance is `q^2*Sigma_nominal + 0.7^2*I`. The moment hypothesis
uses `q^2*(Cov(W)+I/12)+Cov(G)` from the saved normalized discrete kernels.
Keys has zero formal second central moment because it reproduces quadratics;
its signed higher moments and phase dependence remain. This is a declared
Gaussian second-moment hypothesis, not an exact positive optical PSF or an
assertion that continuous box-Gaussian convolution equals the sampled chain.

## First failure and separately admitted continuation

The first execution at local source
`4e111997d0495f695f9d6adbcf2741dea73c44b9` **exited 1 before any capture**.
Its stage helper attempted to hash nonexistent `tests/__init__.py` before
creating a scene directory or entering its numerical stages. All 32
`scene_exception` records and 128 unknown cells are retained. Exact Keys,
production Keys and all four independent Gaussian rectangle controls had
already passed; their four API calls covered 24 queries.

The immutable first report decodes to 492,192 bytes, SHA-256
`c5cef04f49969d607fb85c425bb6b1192e4ef60e373f6412eaf55cc664a2ffc0`.
Its [archive](../../studies/fixtures/finite-acquisition-operator-v1/bootstrap-failure/manifest.json)
includes the original helper, source bindings, logs and bootstrap-only patch.
The driver and failed report were not overwritten.

The [continuation plan](../../studies/finite-acquisition-operator-v1-continuation-v1.json),
SHA-256 `846d1f26635122a6b5038a5f9347421edc8f61181478702e8e602b99b8994e88`,
was frozen before the first capture execution. It admits only the recorded
helper repair: remove the nonexistent source entry and load the declared
`tests/synthetic.py` directly, avoiding an installed `tests` package shadowing
the repository namespace. Scientific formulas, scenes, thresholds and budgets
are unchanged.

The adapter invokes the original driver with deep copies of its three completed
global-control records. Four copied rectangle-call records are explicitly
tagged `performed_this_continuation=false` and bound to the first report's hash.
Constants, coverage, post-kernel, quantization and tessellation checks still
execute for the new scenes. No Gaussian control is rerun.

The continuation at local source
`0714aadf04f6af2130bfe5af70d9dafbbe4677a7` **exited 0**, with its recorded
numerical protocol flag true. All 16 captures, 32 records, 128 cells and 64 new
main API calls are retained. Its raw report is 14,242,714 bytes, SHA-256
`15df34975e0d2c56325a8e4efbea07145a6f0958133e4413a1b36f2ae5a29078`.

| API work lane | Calls | Queries | Evaluations | Panels |
| --- | ---: | ---: | ---: | ---: |
| New main predictions in continuation | 64 | 28,224 | 41,806,468 | 2,406,722 |
| Reused rectangle controls from first execution | 4 | 24 | 41,604 | 2,316 |

Reused work is not reported as newly executed work. All 72 original-driver
runtime source bindings and 19 continuation bindings match before and after
the continuation. Cache admission also checks the original source closure,
the exact old/new helper pair, and Python/NumPy/OpenCV versions. Original
package-binary hashes were not captured: matching source and recorded versions
does not prove installed binary immutability.

## Adequacy criterion and adverse cells

For each stage/covariance cell, `D` is the maximum absolute intensity residual
over 441 queries. The frozen allowance is

```text
E = max_API_intensity_error + tessellation_level_bound
    + 64*eps32*(25/16)*max(1, optical_source_peak, decoded_source_peak).
```

Compatible means `D+E<=1`; incompatible means `D-E>1`; otherwise the cell is
inconclusive. API errors and arithmetic allowances are engineering estimates,
not rigorous enclosures. Quantization is an intentional stage difference,
not extra random uncertainty used to excuse the Gaussian discrepancy.

All main API queries resolve, and the source-area, constant, post-kernel,
tessellation and quantization-envelope checks pass. Nevertheless, the table's
incompatible Gaussian outcomes remain. In the isotropic family, the moment
hypothesis has 8/16 incompatible unquantized cells and 15/16 incompatible PNG
cells. The corresponding directional counts are 1/16 and 1/16, with one PNG
inconclusive. These finite populations do not imply a general ordering of
camera or blur-model accuracy.

Both inconclusive cells are `minor-rotated-directional-phase0`, `q=1.25`:
nominal/unquantized has maximum discrepancy 1.000239620 levels, and
moment/PNG has 0.999718404 levels. Their allowance is about 0.002414486 levels.
No lane is selected to discard these boundary outcomes.

## Raw scalar failure and reversible normalized artifact

The raw report is syntactically valid JSON but fails its ordinary scalar
contract. Its serializer stored **320 marker objects** instead of native
numbers/booleans: **288 finite `np.float32` values and 32 `np.True_` values**.
They occur in arithmetic allowances/envelopes and quantization pass flags.
They are not nonfinite model results. The raw exit 0 and protocol flag remain
recorded; they are not a claim that the raw serialization contract passed.

The separate [normalizer](../../studies/verification/finite-acquisition-normalize-v1.py)
accepts only that exact raw-report hash and the whitelisted marker paths and
representations. It recovers the represented binary32 bits and native booleans,
retains every original marker/path in a conversion ledger, and assigns no
scientific qualification. Fifteen normalization/refusal contracts pass,
including exact parsed-report reversibility. It performs no scientific calls.
No result, failure, array, prediction or work count is removed.

The [normalized artifact](../../studies/results/finite-acquisition-operator-v1-normalized.json.gz)
has decoded SHA-256
`90a7d6db7f9555c3f06c22b269897e72b50a4f9453eb5f1952acc3e5b9631f6b`.
It explicitly records `raw_scalar_serialization_passed=false` and renames the
old flag to `execution_declared_protocol_passed`, rather than promoting the
conversion into a new protocol pass. The
[raw artifact](../../studies/results/finite-acquisition-operator-v1-raw.json.gz)
remains byte-bound and unchanged.

The operational allowances and threshold arithmetic used binary32. Independent
saved-data recomputation verifies those operations and also evaluates the
declared binary64 formula and native arithmetic on the recovered values. The
largest allowance difference is `1.264e-10` levels; **no adequacy classification
changes**. This consistency check does not turn the allowances into certified
bounds.

## Independent saved-data audits and scope

The mathematical saved-data audit passes **148,471 checks with zero failures**.
It independently recomputes kernel moments using scalar `fsum`, query frames
and phases, supplied covariance matrices, intensity predictions, all residuals,
RMS/maxima, allowances, classifications, source/artifact hashes and carried/new
work totals. Its largest arithmetic recomputation discrepancy is
`1.78e-15`. It recovers the known scalar markers explicitly and separately
records the raw scalar contract as false.

The independent UX audit performs **33,100 checks and retains 320 failures**,
all in raw scalar serialization. Its other 32,780 integrity, artifact,
arithmetic and reconstruction checks pass. These outcomes are complementary:
the mathematical audit's success does not erase the raw-contract failures.
Neither audit imports a renderer, source generator, Gaussian model or optimizer.

The [archive index](../../studies/results/finite-acquisition-operator-v1-summary.json)
and [portable archive instructions](../../studies/fixtures/finite-acquisition-operator-v1/README.md)
bind complete reports, numeric stage archives, original PNGs, source snapshots,
auditor receipts and the retained bootstrap failure. Saved-data auditing and
normalization are separate from explicitly executing a new acquisition study.
The index contains **123 artifacts**. The independent portable artifact auditor
passes **1,294 binding/integrity checks with zero artifact failures** and exits
1 because the original raw scalar contract fails. This is an expected retained
failure, not an all-contract pass.

This experiment falsifies universal one-level Gaussian moment closure for its
declared finite-D acquisition family. It does not identify the cause of older
photo residuals: their original PNGs, actual estimated maps and intermediate
stages are not all present in the historical portable archives. It establishes
no geometry-recovery gain, physical camera PSF, camera-response calibration or
automatic production correction. Supplied maps/levels and new synthetic forward
checks are not physical measurements or CAD/print acceptance.
