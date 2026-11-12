# Raw-source fitting: controls and remaining limits

This candidate is based on published PR #63 at
`ad7cc00fed4b2e7006aae957758a12b2f9f15528`. It adds a developer-only numerical
primitive and reproducible experiments. Production tracing, API, frontend,
dependencies and existing study results retain their baseline bytes. The primary
checkout and earlier development evidence remain preserved.

The [method](../raw-source-fit.md) defines the source projection, optics,
brightness constraints, finite search and interpretation. `best` remains a
numerical candidate, including when ambiguity or work flags are set. No result
here accepts physical geometry or changes the workbench trace.

## Source and reproduction

The new `backend/raw_source_fit.py` is bound by SHA-256
`6a877bc15759076adf95dbbb521c04d110b20e8ed397637148c2e87b3ba8b6af`.
The unchanged sampling/covariance module is
`7eee8b71fc9024cb5c8453ec67aab75f2c21c8c77e975c1fba41b1e3be9f873b`.
The [main artifact](../../studies/results/raw-source-fit-v1.json) binds its
runner, frozen plan and every relevant source by hash. Its Git revision field
records the parent checkout at execution; the new implementation was then
uncommitted. Those source hashes, rather than the parent commit alone, identify
what ran. The regression receipt separately binds the frozen source snapshot.

```bash
make raw-source-fit-study OUTPUT=.local/raw-source-fit-new.json
.venv/bin/python studies/verification/raw-source-fit-oracle-v1.py --output .local/raw-source-oracle-new.json
```

Use fresh JSON destinations. Both runners refuse existing outputs, retain
runtime versions and check source hashes before and after execution. The main
experiment uses Python 3.12.3, NumPy 2.5.4 and OpenCV 4.14.0 in its recorded run.
Its 6.44-second duration describes that fixed plan and machine, not whole-photo
latency or a capacity guarantee. It uses no CAD server or private photographs.

## Matched source and processed comparisons

The plan declares six maps (identity, three nonidentity affine, two projective),
three normals and two off-grid offsets with alternating brightness polarity:
**36 matched source fields**. Geometry, optical spread and noise are supplied;
only offset and two brightness levels are fitted. The independent source renderer
crosses two forward-projected boundary points; fitting uses inverse-transpose
lines. Raw Gaussian covariance is isotropic in this study, while unit tests and
the separate oracle also check anisotropic covariance.

| Path and observation | Maximum absolute offset error, rectified px | Scope |
| --- | --- | --- |
| Retained-source fit of the available ideal source | 7.44e-13 | Numerical recovery with exact declared source/optics |
| Exact raw model through full digital operator, fitted to processed float32 profiles by OLS | 6.93e-7 | Rounding/model-discrepancy diagnostic, not independent-noise inference |
| Frozen-Jacobian raw model through full digital operator, processed OLS | 0.002963 | A single local optical approximation |
| Rectified scalar source with finite smoothing/final sampling, processed OLS | 0.003795 | Omits earlier warp from the optical source prediction |

The source and processed paths observe different stages of the same synthetic
field. These values do not establish a physical accuracy gain or a quality
ranking on real photographs. All 36 source fits retain their complete sampled
costs, candidates, flags, operator hashes and source-array hashes. None is omitted.

## Weak-mode conditioning control

The identity/37-degree case retains 98 modes; its smallest retained singular value
is about `1.56e-13`. The exact stored matrix product already exposes finite
whitening arithmetic. Relative to that product, float64 staged processing differs
by only `1.42e-13` intensity levels; its whitened discrepancy norm is about 0.527.
The actual float32 staged profile differs by `2.55e-5` levels, amplified to a
whitened norm of about 2,487. The processed-target fit moves by **0.3172 rectified
pixels**, while the range diagnostic still passes.

Using the original available samples for both target and model avoids this
processed-profile division and recovers the supplied off-grid truth in the
matched case. This does not remove prior source quantization, validate optics,
calibrate supplied noise, or justify geometry estimated from the same image.
The artifact retains all three processing observations and their diagnostics.

## Adverse source and identification controls

Six source fields at 37 degrees are reused for the following supplied stresses.
They are development controls, not reserved real-camera evaluations.

| Control | Recorded outcome | Interpretation |
| --- | --- | --- |
| Supplied raw sigma 20% too small | Maximum offset bias 0.01647 rectified px | Access to source samples does not determine the PSF |
| Supplied raw sigma 25% too large | Maximum offset bias 0.02474 rectified px | Fixed optical error remains in fitted geometry |
| Source rounded to float32 before fitting | Maximum offset error 5.70e-8 rectified px | Earlier rounding is retained, not undone |
| Actual eight-bit sRGB encode/round/decode with `tone.linear_mix` | Maximum offset error 0.005544 rectified px | Available prewarp samples need not match a continuous Gaussian source exactly |
| Monotone nonlinear response `p + 0.15 p(1-p)` | Absolute offset errors about 0.102–0.237 rectified px | Source-space fitting does not repair an incorrect response model |
| Constant zero/128 source | Flat, plateau and tied flags | Exact no-contrast nonidentification, despite a rank-two level design |
| Raw optical sigma `1e-4` | Plateau and tied flags | Represented numerical saturation ambiguity; no unique physical offset follows |
| Near-zero contrast | Flat, plateau and tied flags | Arithmetic/conditional ambiguity; not a proof of exact equal continuous means |
| True source edge outside declared interval | Endpoint flag | Search bounds cannot certify an interior solution |
| No evaluations left after complete grid | Work-exhausted flag | Unrefined sampled minimum remains a candidate |

All six constructed wall controls also retain two silhouette labels separated
by about **3.09524 rectified pixels** with source means differing only at floating
roundoff. Their retained projections are likewise equivalent at that scale.
A sharp local step fit does not distinguish which physical wall label generated
that same field.

An additional bounded source texture lies in the omitted source subspace. Its
maximum perturbation is 20 intensity levels and L2 norm is about 63.10, while
the ideal profile perturbation is only about `2.09e-14` levels. The source fit
still has a tiny projected residual. Its reported standardized raw and omitted
residual norms both remain about 63.10 under supplied unit deviations. These
norms use `(observed-predicted)/input_std`, not unscaled intensity units. No
physical rejection threshold is inferred and the objective is not silently changed.
The artifact's explicit `source_levels` pair records the brightness override for
this texture control's reused geometry scene.

## Conditional noise experiment

The plan generates **24 common full-sensor Gaussian noise arrays**, reused across
six mean fields, for **144 source fits** with supplied unit independent raw noise.
This is not 144 independent camera scenes. All fit errors, sampled costs,
candidates and flags are retained. Observed RMSE ranges from about 0.00805 to
0.01786 rectified pixels across those six configurations; finite-run biases and
extremes remain in the artifact. The experiment does not estimate real sensor
noise or demonstrate interval coverage, confidence, physical accuracy or a
universal noise tolerance.

## Independent and regression verification

The [independent verifier](../../studies/verification/raw-source-fit-oracle-v1.py)
and [its results](../../studies/results/raw-source-fit-oracle-v1.json) retain
**14 source controls and four 90-digit Decimal box-fit oracles**. They cover
anisotropic/nonidentity geometry, positive/negative homography scaling,
noise-unit scaling, normal reversal, sensor-axis exchange, source permutation,
constant data, work exhaustion and observed values outside mean bounds. The
probability comparison differs by at most `1.22e-14`. These invariance checks
include identity/orthogonal full source spaces; the main experiment separately
uses declared truncated full-chain operators.

The new focused suite passed **24 tests**. The full suite passed **1,273 tests
in 226.55 seconds**, with no failures, errors or skips. The
[regression receipt](../../studies/results/raw-source-fit-regression-v1.json)
binds the JUnit/log hashes and all **146 frozen source/input files**. All 136
existing backend/frontend/script/test files match the PR #63 baseline; the new
Python files are developer tools and tests. Frontend typecheck/build,
Ruff for backend/scripts/tests and the independent oracle, and existing library
documentation checks passed. Production/frontend source is unchanged; no new
browser, native-slicer, live-model or physical-fit result is inferred.

## Documentation coverage

All **85 Markdown documents**, **1,097 local links**, **69 heading fragments**
and **135 tables** passed the structural audit. The existing companion-library
documentation suite passed **19 tests**. Fresh-output and help/refusal contracts
were separately checked. These documentation checks are not additional product
or physical tests. The [earlier complete inventory](documentation-alignment.md)
retains its 83-document PR #62 scope; this candidate adds the method and validation
guides above. Historical reports retain their own source hashes, dates, counts
and failures. New source-space inference remains separate from production tracing.

The separately observed [PR #62 hosted run](https://github.com/bartytime4life/Pictures-to-3D-CAD-Models/actions/runs/43221471259)
completed successfully at `ca321442bd276c177c31f00bcd62fb0ea27b2e0e`, with
1,249 Python tests and all 74 browser scenarios passed. That is the parent
implementation, before this new fitter; it does not verify this candidate's
hosted execution. [Project status](../project-status.md#evidence-by-scope) retains
the exact-head observations and the earlier cancelled PR #61 run separately.
