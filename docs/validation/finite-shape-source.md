# Finite-shape source modeling — November 12, 2026

This developer candidate is based on published
[PR #73](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/pull/73)
at `fa853df69e6c279ab63404cf1c4b9d989bd13ed2`, tree
`023c6af1ecb39c9286784e7a3ad5ddfaa34ba5fc`. Work is isolated on
`codex/finite-shape-source`; the primary checkout remains at `d747e306`.
The [API and integration guide](../finite-shape-source.md) defines supplied
inputs, numerical statuses, resource limits and the production capture seam.

## Problem and mathematical change

The [canonical-arc controls](canonical-arcs.md) leave finite Gaussian-blurred
circular segments with nonzero boundary discrepancies even when emitted arcs
preserve their declared circles. A local half-plane or isolated-circle model
omits the influence of nearby chord ends, corners, opposite boundaries and
holes. Representation correctness alone does not identify the source shape.

The new forward evaluator projects the entire supplied finite material before
Gaussian convolution and point sampling. It includes off-sensor material rather
than clipping the region to the detector. A fixed positive-definite raw Gaussian
covariance is whitened once; a radial Green flux integrates the closed boundary,
including subtractive holes and projective orientation.

The radial coefficient is `-expm1(-s/2)/s`, with limit `1/2` at `s=0`.
Far panels retain their angular winding contribution; their Gaussian remainder
is bounded using a whole-panel distance and length cover. Near panels must
resolve whitened travel before embedded quadrature agreement is accepted.
Fixed quadrature alone can miss the narrow boundary layer of a radius-10,000
disk and incorrectly agree at `0.5`; the independent control resolves the
different finite-disk value. These are engineering numerical checks, not formal
quadrature certificates or physical measurement bounds.

The circular-segment fitter searches a supplied `(R, f=h/R)` rectangle. Fixed
pose and pixels, raw covariance, noise factor and bounded brightness apply to
every candidate. At each geometry, a two-column bounded least-squares subproblem
fits the shared levels by considering its active faces. Domain-scaled local
Gauss–Newton steps project out only free brightness columns; actual profiled
cost backtracking accepts each step. This is an approximate variable-projection
direction, not the full residual-dependent Jacobian or a global-search proof.

The complete coarse grid, represented basin/face candidates and unresolved
statuses remain visible. Whole-domain projective validation uses the largest
fraction shape at both radius endpoints on a common chart. Unknown local rank
is distinct from demonstrated deficiency. Raw, retained and omitted residual
norms all use the same supplied source standard deviations.

## Independent forward evidence

The committed [plan](../../studies/finite-shape-source-v1.json),
[independent runner](../../studies/verification/finite-shape-oracle-v1.py) and
[complete result](../../studies/results/finite-shape-source-oracle-v1.json)
retain **28 rows and 182 checks**, with zero failures or execution errors.
Maximum probability discrepancy is **2.9133e-12**; maximum independent
quadrature-order delta is **5.7621e-14**. Order agreement is a numerical
cross-check, not a rigorous integration error estimate.

The reference uses positive area/slice integrals, standard-library `erfc` and
targeted cuts near Gaussian tails and circle intersections. Affine controls pull
back the Gaussian exactly; projective controls integrate the raw Gaussian with
the projective area Jacobian. They do not reuse the production Green flux.
Controls include minor/half/major segments, disks/annuli, multiple holes,
off-sensor material, correlated blur, reflections, homography rescaling,
whole-curve horizon refusal and exhausted work.

Nine command/failure controls pass: early help/destination refusals start no
analysis, fresh output matches stdout and overwrite refusal preserves it. An
injected first-case failure retains all 28 rows; the later 27 execute and pass.

```bash
.venv/bin/python studies/verification/finite-shape-oracle-v1.py --output .local/finite-shape-new.json
```

## Independent inverse evidence

The fixed [inverse plan](../../studies/finite-shape-fit-v1.json) and
[runner](../../studies/verification/finite-shape-fit-oracle-v1.py) retain 29 cases:
12 matched controls, two noise-unit controls, seven model-mismatch controls,
three ambiguity controls, three search-limit controls, discarded-source texture
and a two-pixel active-brightness constraint control. Training support is fixed
before search; independent held-out pixels test the fitted prediction.

The matched thresholds were fixed before execution: radius error at most
`2e-5`, fraction error at most `2e-6`, chord-offset error at most `2e-5`,
sampled whole-boundary distance at most `3e-5` plane units, and held-out level
error at most `5e-4`. Sampled boundary comparison is not a certified continuous
Hausdorff bound. Fixed pose and optics supply additional information; these
controls are not a general before/after photo-accuracy comparison.

The [final-source replay](../../studies/results/finite-shape-fit-oracle-v2.json)
passes **all 256 checks**, retaining **29/29 rows** with zero execution or
noise-unit-control failures. Source is unchanged before/after. It includes
genuine perspective, correlated blur, reversed contrast and the three historical
finite circular segments. Maximum matched errors are approximately `1.47e-9`
in radius, `2.55e-9` in fraction, `2.39e-8` in chord offset and sampled boundary
distance, and `6.79e-7` in held-out intensity units.

All 12 matched rows meet the predeclared reconstruction thresholds. Eleven
finish with local rank two and no work exhaustion; the broad-PSF row meets the
targets while retaining exhausted work, incomplete refinement, one unrefined
basin and unknown geometry rank. Target agreement does not prove complete basin
search, unique identification or convergence of every represented hypothesis.
The initial replay is preserved in local review evidence under its earlier
implementation hash. Its receipt SHA-256 is
`3242692947b1a90961d11f9636def18aa01db6cbf29b35445a0115e670826994`.
Its geometric results and
checks agree with the final replay; stable residual norms change at most
`1.78e-15` on these ordinary rows.

The adverse cases retain wrong scalar blur, anisotropic truth, a normalized
Gaussian mixture, uniform pixel means fitted as points, nonlinear response,
material gradients and omitted texture. A low retained cost is not an absolute
source-model adequacy test. Constant and one-pixel observations demonstrate
nonidentification. The chord-only case remains tied even with local rank two.
The active-level case improves cost while retaining exhausted work and unknown
geometry rank; it makes no local/global optimum claim.

| Adverse source/model pair | Sampled boundary error, plane units | Maximum held-out level error |
| --- | --- | --- |
| Supplied Gaussian too narrow | 0.3313 | 16.86 |
| Supplied Gaussian too broad | 0.1987 | 9.63 |
| Anisotropic truth fitted isotropically | 0.5018 | 38.74 |
| Gaussian mixture fitted by its moment-matched Gaussian | 0.1434 | 9.76 |
| Uniform pixel means fitted as point samples | 0.05006 | 4.55 |
| Nonlinear response fitted with linear levels | 0.6464 | 4.50 |
| Bounded material gradient fitted with constant levels | 0.1070 | 6.42 |

Every adverse row also retains work exhaustion and incomplete refinement. These
are errors of the best represented candidates within the declared budget, not
converged model-bias estimates or evidence of an irreducible error minimum.
The source assumptions are deliberately mismatched by construction. Both their
model discrepancy and incomplete optimization must remain visible.

```bash
.venv/bin/python studies/verification/finite-shape-fit-oracle-v1.py --output .local/finite-shape-fit-new.json
```

Use new output paths. Both scientific runners bind their plans, independent
reference and imported implementation before and after execution. They require
no server, personal photo, model inference or native application launch.

The inverse runner's early help/destination and exclusive-save controls pass.
A separate strong comparison passes **10 failure-retention checks**: it visits
all 29 planned cases, retains an injected first-row `ValueError`, then executes
the later **28 actual independent-render/production-fit cases**. Every later
row matches the canonical replay exactly after excluding runtime. This is
separate from the cheaper in-memory exception-flow check. The full failed-row
report and stdout match byte for byte, with SHA-256
`f3e6bd6a5f52fd983b66ea0cb3a645e4c2bd0fcd064cd1b49d7e81dcefa1108e`.

## Regression and numerical repairs

The first inverse smoke run exposed a NumPy boolean that prevented ordinary JSON
serialization. The repaired result uses native scalar/boolean fields. Focused
controls also require noise-unit invariance, standardized residual accounting,
complete grid retention, whole-domain horizon refusal and unknown-rank handling.

An additional zero-data control with supplied standard deviation `1e-300`
reproduced infinite error/cost guards labeled resolved. The repair uses a stable
norm and retains numerical unknowns when squared-cost units cannot represent a
nonzero guard or residual. The corresponding `1e300` underflow control also
retains all nine grid entries as unknown; neither manufactures a zero-cost
geometry result. The repaired code passes all 45 inverse tests, including both
new cases, without changing the earlier recovery tolerances.

Final review also reproduced overflow in the omitted-source diagnostic with
observations `[0, 1e200]` and retained projection `[[1, 0]]`: the projected cost
was zero but naïve squared-sum norms became infinity. Stable norms now preserve
the representable raw/omitted value `1e200`. A norm beyond floating-point range
is explicitly unavailable with a numerical-support flag, while the available
projected result remains visible. Neither case hides omitted information or
relabels it as zero.

The first full development run passes 1,710 tests in 316.93 seconds. Its 330 other
frozen product files are unchanged; the inverse test file was extended after
collection, so that run is not described as an unchanged 331-file final freeze.
The next full run passes **1,712 tests in 294.03 seconds** with all 331 files
unchanged. It precedes the stable omitted-norm repair. The final source and
expanded test file are frozen separately. The final run passes **all 1,714
Python tests**, with **zero failures, errors or skips**, in **303.45 seconds**.
All **331 frozen product files** match before/after; the **327 pre-existing
product files** remain byte-identical to PR #73. The 105 new regression cases
comprise 58 forward and 47 inverse tests. Earlier receipts remain preserved.

The frontend build and Python lint/format checks pass. The runnable circle
example in the API guide executes and retains both resolved queries. Product
source, tests, scientific results, documentation and browser evidence retain
their own bindings; no historical workbench browser result is relabeled as a
run of these new developer modules.

## Documentation and command coverage

All **99 Markdown documents**, **1,766 local Markdown references**, **119
heading fragments** and **164 tables** pass structural/navigation checks. The
additional local HTML image also resolves. The affected method, architecture, research, roadmap, status and
task-navigation guides describe the developer scope; historical evidence and
companion-library artifacts retain their prior bindings.

All **43 argparse command-help paths**, root `make help` and **26 API/signature/
example checks** pass. Both documented API maps match the 11 OpenAPI operations;
the response/rectangle/Gaussian examples run and refuse overwrite without losing
the original report. All **441 non-Markdown files**, including the new plans,
runners and complete results, match before/after these checks. The library's
existing **19 documentation tests** also pass. Generated-reader inputs are
unchanged, so no new library rebuild or release is claimed.

## Remaining integration and qualification

These modules do not run in the production trace/API/frontend and do not change
CAD geometry. A real request needs an immutable working-image context before
warp/smoothing: pixel frame and image identity, reduction chain, homography,
channel mixing, selected source support, raw covariance/noise assumptions and
the geometry revision. Serialized `Profile` data cannot reconstruct it.

Production integration, joint or uncertain pose/PSF/response inference, pixel
apertures and reduction operators, nonuniform lighting, lens distortion and
wall geometry remain separate work. The current method fits one circular
segment with supplied pose; the general boundary evaluator is not a general
shape-reconstruction optimizer. Neither numerical agreement nor a small cost
qualifies a camera, physical dimension, fitted joint, slicer or print.

## Source and artifact binding

The scientific reports bind the complete imported implementation and fixed
plans before/after execution. The final product freeze manifest has SHA-256
`eef176440d417ee9e94f3e60d0099c1498e01921ffb16681db5e4864cde873fa`.
The final JUnit report has SHA-256
`570712c211f838092c12310a7e85433e14afac8b9abaa962f182bc625085e84b`. Detailed command, failure,
build and regression receipts are retained in ignored `.local/verification/`.

| New implementation, controls or result | SHA-256 |
| --- | --- |
| [backend/finite_shape.py](../../backend/finite_shape.py) | `07e0a2bb0d03b7e4f12f4a9b0675b3f7598d54587d746c07c502ea83623d29d8` |
| [backend/finite_shape_fit.py](../../backend/finite_shape_fit.py) | `9d476751d3863ab71cea606fbb490edc0177a6ceee4bf656775e78ec14f6dd82` |
| [tests/test_finite_shape.py](../../tests/test_finite_shape.py) | `bc176531b77b38efb94de99a13c3770d11fffdba2861f1ce5685cde6723cab6e` |
| [tests/test_finite_shape_fit.py](../../tests/test_finite_shape_fit.py) | `9c1e346c354a7534d1485eafe37c2650424d252f1b91991c014565a4cd02d54f` |
| [studies/finite-shape-source-v1.json](../../studies/finite-shape-source-v1.json) | `fe18367b4112ca18aee1e8da0d2b0e7a4b1f7efce79e5f6917c78f22cb9d7978` |
| [studies/verification/finite-shape-oracle-v1.py](../../studies/verification/finite-shape-oracle-v1.py) | `912c7cd63c30e0b26b0dabdbc65c0cf2152966897b30fc44de26ca18448b2b3a` |
| [studies/results/finite-shape-source-oracle-v1.json](../../studies/results/finite-shape-source-oracle-v1.json) | `8398782eed367cfbf3e206fb2088c8d7c9a6e39c9443c99b4dc37b3a955d2e00` |
| [studies/finite-shape-fit-v1.json](../../studies/finite-shape-fit-v1.json) | `093c15a2956b7d91847d23931ec2176b47e73a5d17b4f8edf31a5bbbc6b939d3` |
| [studies/verification/finite-shape-fit-oracle-v1.py](../../studies/verification/finite-shape-fit-oracle-v1.py) | `3ab48933f479ca2033be31f80222b29ec229837562d91286be7a4f24b5a76385` |
| [studies/results/finite-shape-fit-oracle-v2.json](../../studies/results/finite-shape-fit-oracle-v2.json) | `7120132afcdb59e0cd0b9f07bc551d8ffe8b356eab00d3f8e6eb3cb84ffb096f` |
