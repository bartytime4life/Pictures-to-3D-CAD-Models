# Independent acquisition mean: complete saved-capture comparison

The independent source-cell model reproduces all 32 saved output records under
the frozen engineering checks. Its 16 analytic finite-D area sums differ from
the closed-form segment areas by at most `5.684341886080802e-14` square plane
units. It uses supplied geometry, levels, kernels and maps; it does not fit or
recover geometry.

| Coverage / encoding lane | Records | Largest query discrepancy, levels | Largest full-field discrepancy, levels |
| --- | ---: | ---: | ---: |
| Saved polygon / unquantized | 32 | 0.0000610352 | 0.0000762939 |
| Saved polygon / sRGB8 | 32 | 0.0000305176 | 0.0000305176 |
| Analytic D / unquantized | 32 | 0.0000762939 | 0.0000762939 |
| Analytic D / sRGB8 | 32 | 0.0000305176 | 0.0000305176 |

All 128 comparisons meet the retained raw one-level check. All 64 encoding
comparisons have **zero changed 8-bit codes**. This dataset contains no observed
encoding-bin crossing; it does not establish continuity of quantized predictions.
The earlier Gaussian counterexamples remain unchanged in the
[original acquisition record](finite-acquisition-operator.md).

## Frozen design, calls and sources

The [original plan](../../studies/finite-acquisition-mean-v1.json), implementation,
tests and runner were committed before numerical execution at `489990e`.
The study separately replays saved polygon coverage through independent stages,
then replaces it with analytic disk/half-plane/cell overlap. Both output scales
and both encoding lanes are retained for every source scene.

After the admitted root-parameter repair below, the complete study ran once at
`521c318bcb10975643a1396547e4ab1f41c7da9e`, exiting **0**. It retains
**128 new acquisition-mean calls**, **56,448 query residuals**, **768 stage arrays**,
16 analytic coverage arrays and **487,211,008 declared stage-work units**.
The work count excludes separately bounded coverage geometry and is not a
performance benchmark. There are no new captures, old Gaussian-reference calls
or inverse-optimizer calls in this experiment. Full software tests are a separate
lane and exercise their own existing synthetic/model cases.

The raw report is strict native JSON, SHA-256
`bd8127cc84999e7c5572797c46c2ba62bda29e2262ce57375c1e9745ce9133c3`.
All seven recorded runtime/input source pins match before and after execution.
An eight-file source ZIP also includes the control-continuation admission.
The [complete archive](../../studies/fixtures/finite-acquisition-mean-v1/README.md)
preserves the exact source independently of later metadata changes.

## Preserve the first failed controls

The first focused run exits **1**, with **122 passing and 12 failing cases**.
Every failure involves an admitted interior circle crossing that binary64 rounds
onto a cell endpoint. For a represented `(-0.8,0.6)` corner, the upper root lies
only about `1.63e-17` below one. Exact topology correctly places it inside; a
binary64 parameter cannot represent that cut.

The [control continuation](../../studies/finite-acquisition-mean-v1-continuation-v1.json)
admits bounded 128/256/512-bit integer-square-root brackets and rational interior
cuts when the fast binary64 cuts collapse. It does not snap endpoints or change
test populations or tolerances. The unchanged **134 focused controls pass**
afterward, including six independent positive-area slice integrations, exact
elementary areas, complements/partitions, frame, border and signed-Keys controls.
The complete first log, original helper and failure receipt remain archived.

## Independent saved-data audits

The first mathematical audit retains **32 allowance-scalar mismatches among
7,678,371 checks**. The governing runner's mixed Python/NumPy expression evaluates
some allowance arithmetic in binary32. It differs from an exact-rational/binary64
interpretation by `-2.58045545e-10` to `+2.10722015e-10` levels. This is a retained
arithmetic distinction, not a changed threshold or a missing data row.

A separately retained mathematical audit verifies the actual operational
arithmetic and the independent formula: **7,678,499 checks pass**. Every comparison
passes both allowances, with no outcome change. The original audit is unchanged.
These allowances remain engineering comparisons, not certified enclosures.

An independent artifact audit passes **2,815 checks**, including all original
123 artifact bindings, source pins, complete census, input hashes and strict JSON.
The portable version reads the recorded source ZIP as data and passes
**2,816 checks** without requiring the local source-freeze Git commit. Neither
auditor imports a candidate, generator or reference model or evaluates a stage.

## Workspace correction and software checks

The full software suite at numerical source `521c318` passes **1,173 tests** with
runtime warnings treated as errors. Ruff lint/format checks also pass. No new
frontend/browser or installed-tool qualification is added.

A later static review finds a real resource-accounting defect outside the study
shapes: a valid `(1,65536)` source and 31×31 kernel require at least 34,086,160
simultaneously live numeric bytes, exceeding the former 33,686,016-byte estimate.
The [separate workspace repair](../../studies/finite-acquisition-mean-v1-workspace-repair-v1.json)
adds both intermediate reflected-padding sizes explicitly. It excludes caller
inputs and Python/allocator overhead, so it is not an RSS guarantee.

At `906197f6537a529ab852c25e8659bc25cbad4820`, **145 focused tests pass**, including
11 new resource-accounting cases. An independent **22-check AST comparison**
verifies that only the workspace assignment changes: every numerical stage,
input hash, work expression and original test remains unchanged. The complete
capture predictions are not rerun or rewritten to update a metadata field.
The 1,173-test result belongs to its earlier exact source; it is not relabeled
as a full-suite run on this later revision.

The result establishes a supplied discrete forward mean for these scenes.
It does not qualify a physical camera, unknown illumination, current main's
shadow model, geometry recovery, an inverse Jacobian, automatic CAD correction
or printing. Subsequent inverse work needs its own prospective recovery and
independent dimensional checks. See the [method and API boundary](../finite-acquisition-mean.md).
